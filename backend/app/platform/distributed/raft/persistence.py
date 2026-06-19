import asyncio
import logging
from typing import List, Tuple, Dict, Any, Optional

from app.platform.infrastructure.db.session import SessionLocal
from app.platform.distributed.raft.models import RaftStateModel, RaftLogModel

logger = logging.getLogger(__name__)

def _load_raft_state_sync(node_id: str) -> Tuple[int, Optional[str]]:
    with SessionLocal() as db:
        state = db.query(RaftStateModel).filter(RaftStateModel.node_id == node_id).first()
        if state:
            return state.current_term, state.voted_for
        return 0, None

def _save_raft_state_sync(node_id: str, current_term: int, voted_for: Optional[str]):
    with SessionLocal() as db:
        state = db.query(RaftStateModel).filter(RaftStateModel.node_id == node_id).first()
        if not state:
            state = RaftStateModel(node_id=node_id, current_term=current_term, voted_for=voted_for)
            db.add(state)
        else:
            state.current_term = current_term
            state.voted_for = voted_for
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save Raft state for {node_id}: {e}")

def _load_raft_log_sync(node_id: str) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        # Load all log entries ordered by log_index.
        # This can be optimized with pagination/snapshots in the future if the log gets too big.
        logs = db.query(RaftLogModel).filter(RaftLogModel.node_id == node_id).order_by(RaftLogModel.log_index.asc()).all()
        
        if not logs:
            # Initialize with dummy entry at index 0 if not found
            dummy_entry = RaftLogModel(node_id=node_id, log_index=0, term=0, command={"type": "init"})
            db.add(dummy_entry)
            db.commit()
            return [{"index": 0, "term": 0, "command": {"type": "init"}}]
            
        return [{"index": log.log_index, "term": log.term, "command": log.command} for log in logs]

def _append_raft_log_entry_sync(node_id: str, index: int, term: int, command: dict):
    with SessionLocal() as db:
        entry = RaftLogModel(node_id=node_id, log_index=index, term=term, command=command)
        db.add(entry)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to append Raft log entry {index} for {node_id}: {e}")

def _truncate_and_append_raft_log_sync(node_id: str, truncate_from_index: int, entries: List[Tuple[int, int, dict]]):
    with SessionLocal() as db:
        try:
            # Truncate conflicting logs
            db.query(RaftLogModel).filter(
                RaftLogModel.node_id == node_id,
                RaftLogModel.log_index >= truncate_from_index
            ).delete()

            # Append new logs
            for idx, term, command in entries:
                entry = RaftLogModel(node_id=node_id, log_index=idx, term=term, command=command)
                db.add(entry)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to truncate and append Raft log for {node_id}: {e}")

def _compact_raft_log_sync(node_id: str, threshold_index: int):
    with SessionLocal() as db:
        try:
            # Delete entries strictly less than the threshold index
            deleted = db.query(RaftLogModel).filter(
                RaftLogModel.node_id == node_id,
                RaftLogModel.log_index < threshold_index
            ).delete()
            db.commit()
            if deleted > 0:
                logger.info(f"Compacted {deleted} old log entries up to index {threshold_index - 1} for {node_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to compact Raft log for {node_id}: {e}")

# Async wrappers using asyncio.to_thread

async def load_raft_state(node_id: str) -> Tuple[int, Optional[str]]:
    return await asyncio.to_thread(_load_raft_state_sync, node_id)

async def save_raft_state(node_id: str, current_term: int, voted_for: Optional[str]):
    await asyncio.to_thread(_save_raft_state_sync, node_id, current_term, voted_for)

async def load_raft_log(node_id: str) -> List[Dict[str, Any]]:
    return await asyncio.to_thread(_load_raft_log_sync, node_id)

async def append_raft_log_entry(node_id: str, index: int, term: int, command: dict):
    await asyncio.to_thread(_append_raft_log_entry_sync, node_id, index, term, command)

async def truncate_and_append_raft_log(node_id: str, truncate_from_index: int, entries: List[Tuple[int, int, dict]]):
    """entries is a list of (index, term, command) tuples"""
    await asyncio.to_thread(_truncate_and_append_raft_log_sync, node_id, truncate_from_index, entries)

async def compact_raft_log(node_id: str, threshold_index: int):
    await asyncio.to_thread(_compact_raft_log_sync, node_id, threshold_index)
