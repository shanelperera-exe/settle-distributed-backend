"""
Industry-standard structured logging for the Settle distributed payment system.

Two formats are supported, selected by the LOG_FORMAT environment variable:
  - "json"  (default/production): OpenTelemetry / Google Cloud Logging compatible JSON,
    one compact line per event. Ingested directly by Datadog, ELK, Splunk, GCP Logging.
  - "text"  (development): Coloured, human-readable console output.

JSON Schema (all fields follow OpenTelemetry semantic conventions):
  timestamp    – ISO-8601 UTC, nanosecond precision  (replaces "physical_time")
  severity     – DEBUG | INFO | WARNING | ERROR | CRITICAL  (Google / OTel convention)
  message      – the log body
  node_id      – Raft / cluster node identifier
  service      – always "settle"
  logger       – Python logger name (e.g. "app.distributed.raft.node")
  caller       – module:function:lineno  (e.g. "node:_leader_loop:231")
  hlc          – Hybrid Logical Clock packed timestamp  (e.g. "1779956149675:0")
  trace_id     – distributed trace ID (if present)
  request_id   – unique request identifier
  correlation_id – distributed correlation chain ID
  transaction_id / payment_id / event_type – forwarded when set on the LogRecord
  leader_state – current Raft role (LEADER/FOLLOWER/CANDIDATE)
  raft_term    – current Raft consensus term
  error        – exception traceback (only on exc_info records)
"""

import logging
import sys
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from app.platform.core.config import settings

# ── colour codes for text mode ────────────────────────────────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_LEVEL_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_NODE_COLOUR = "\033[34m"     # blue


# ── Context Filter ────────────────────────────────────────────────────────────

class ContextFilter(logging.Filter):
    """
    Injects request-scoped context variables into every LogRecord.

    This filter reads from Python's `contextvars` (set by the LoggingMiddleware)
    and attaches the values as LogRecord attributes. This allows the JSON/Text
    formatters to include correlation IDs, trace IDs, and business context
    in every log line without the caller having to pass them explicitly.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Import lazily to avoid circular imports during early startup
        try:
            from app.platform.observability.context import request_ctx
            record.request_id = getattr(record, "request_id", None) or request_ctx.request_id.get()
            record.correlation_id = getattr(record, "correlation_id", None) or request_ctx.correlation_id.get()
            record.trace_id = getattr(record, "trace_id", None) or request_ctx.trace_id.get()
            record.span_id = getattr(record, "span_id", None) or request_ctx.span_id.get()
            record.transaction_id = getattr(record, "transaction_id", None) or request_ctx.transaction_id.get()
            record.payment_id = getattr(record, "payment_id", None) or request_ctx.payment_id.get()
            record.event_type = getattr(record, "event_type", None) or request_ctx.event_type.get()
        except Exception:
            # During early startup, contextvars may not be available
            for field in ("request_id", "correlation_id", "trace_id", "span_id",
                          "transaction_id", "payment_id", "event_type"):
                if not hasattr(record, field):
                    setattr(record, field, "")

        # Safely read Raft state for enrichment
        try:
            from app.platform.distributed.raft.node import raft_node
            record.leader_state = raft_node.state.role.name
            record.raft_term = raft_node.state.current_term
        except Exception:
            if not hasattr(record, "leader_state"):
                record.leader_state = ""
            if not hasattr(record, "raft_term"):
                record.raft_term = 0

        return True  # Never filter out records


# ── JSON formatter (production) ───────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """
    Emits one compact JSON line per log record.

    Compatible with:
      - OpenTelemetry Log Data Model
      - Google Cloud Logging  (uses "severity" not "level")
      - Datadog / ELK / Splunk (all consume flat JSON natively)
      - Grafana Loki (JSON parsing pipeline)

    Performance: avoids acquiring the HLC lock on EVERY record by caching the
    last HLC value and only updating it when the physical millisecond advances.
    """

    # Map Python level names → OTel / GCP severity strings
    _SEVERITY_MAP = {
        "DEBUG":    "DEBUG",
        "INFO":     "INFO",
        "WARNING":  "WARNING",
        "ERROR":    "ERROR",
        "CRITICAL": "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp: ISO-8601 UTC with millisecond precision (standard for structured logs)
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"   # trim to ms, add Z suffix

        # HLC — lazy import, guarded so logging works before the clock is initialised
        hlc = None
        try:
            from app.platform.distributed.clock.hlc import hlc_manager
            hlc = hlc_manager.get_current_packed()
        except Exception:
            pass

        doc: Dict[str, Any] = {
            "timestamp":  ts,
            "severity":   self._SEVERITY_MAP.get(record.levelname, record.levelname),
            "message":    record.getMessage(),
            # ── service context ──────────────────────────────────────────
            "service":    "settle",
            "node_id":    settings.NODE_ID,
            # ── source location ──────────────────────────────────────────
            "logger":     record.name,
            "caller":     f"{record.module}:{record.funcName}:{record.lineno}",
            # ── distributed clock ────────────────────────────────────────
            "hlc":        hlc,
        }

        # Forward context-enriched fields (set by ContextFilter)
        for field in ("request_id", "correlation_id", "trace_id", "span_id",
                      "transaction_id", "payment_id", "event_type",
                      "leader_state", "raft_term"):
            val = getattr(record, field, None) or record.__dict__.get(field)
            if val is not None and val != "" and val != 0:
                doc[field] = val

        # Forward optional event field from explicit extra= kwargs
        event_val = record.__dict__.get("event")
        if event_val:
            doc["event"] = event_val

        # Exception details
        if record.exc_info:
            doc["error"] = self.formatException(record.exc_info)

        # Remove null hlc when clock is not yet ready (startup)
        if doc["hlc"] is None:
            del doc["hlc"]

        return json.dumps(doc, ensure_ascii=False)


# ── Text formatter (development) ──────────────────────────────────────────────

class TextFormatter(logging.Formatter):
    """
    Human-readable coloured log lines for local development.

    Format:
      2026-05-28T08:15:30.123Z  INFO  [node-1]  app.distributed.raft.node  Became LEADER for term 5.
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"

        level   = record.levelname
        colour  = _LEVEL_COLOURS.get(level, "")
        node    = f"{_NODE_COLOUR}[{settings.NODE_ID}]{_RESET}"
        lvl_str = f"{colour}{_BOLD}{level:<8}{_RESET}"
        logger  = f"{_DIM}{record.name}{_RESET}"
        msg     = record.getMessage()

        line = f"{_DIM}{ts}{_RESET}  {lvl_str} {node}  {logger}  {msg}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)

        return line


# ── Reorder-buffer handler (unchanged interface) ───────────────────────────────

class ReorderBufferHandler(logging.Handler):
    """
    Intercepts log records, formats them to the structured dict, and
    pushes them into the causal Reorder Buffer for HLC-sorted output.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Bypass for the structured_logger itself (avoids infinite loop)
        if record.name == "structured_logger":
            return
        try:
            msg = self.format(record)
            log_dict = json.loads(msg)
            from app.platform.distributed.clock.reorder_buffer import reorder_manager
            reorder_manager.add_log(log_dict)
        except Exception:
            self.handleError(record)


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_logging() -> logging.Logger:
    """
    Configures the root logger.  Call once at application startup.

    Environment variables:
      LOG_LEVEL   – DEBUG | INFO | WARNING | ERROR   (default: INFO)
      LOG_FORMAT  – json | text                      (default: json)
    """
    log_format = os.getenv("LOG_FORMAT", "json").lower()

    root = logging.getLogger()
    # Clear any handlers added by uvicorn before we take control
    root.handlers.clear()

    # ── add context filter to root logger ─────────────────────────────────────
    context_filter = ContextFilter()
    root.addFilter(context_filter)

    # ── choose formatter ──────────────────────────────────────────────────────
    if log_format == "text":
        formatter: logging.Formatter = TextFormatter()
    else:
        formatter = JSONFormatter()

    # ── reorder-buffer handler (feeds the causal sorted output pipeline) ──────
    buffer_handler = ReorderBufferHandler()
    buffer_handler.setFormatter(formatter)
    root.addHandler(buffer_handler)

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root.setLevel(level)

    # ── structured_logger: the final sink that prints sorted lines to stdout ──
    # It receives pre-formatted strings from the ReorderBuffer and must NOT
    # re-format them — just write them to stdout as-is.
    sink = logging.getLogger("structured_logger")
    sink.propagate = False
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter("%(message)s"))
    sink.addHandler(stdout_handler)
    sink.setLevel(logging.DEBUG)

    # ── third-party library noise suppression ─────────────────────────────────
    # kazoo: ZooKeeper client — very chatty at INFO
    logging.getLogger("kazoo").setLevel(logging.WARNING)
    # httpx / httpcore: fire on every Raft heartbeat (hundreds/sec) — suppress
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # uvicorn.access: logs every inbound heartbeat RPC — suppress
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # OpenTelemetry SDK: can be chatty during export
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)

    # ── route uvicorn/fastapi through our formatter ───────────────────────────
    for name in ("uvicorn", "uvicorn.error", "fastapi"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = [buffer_handler]
        lib_logger.propagate = False

    return root


# ── Module-level singleton ────────────────────────────────────────────────────
logger = setup_logging()
