from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import secrets
import logging
import os

class Settings(BaseSettings):
    """
    Application settings derived from environment variables.
    This adheres to the 12-factor app principle: configuration in the environment.
    """
    APP_NAME: str = "SETTLE"
    # Every node needs a unique ID (e.g., node-1, node-2). Essential for distributed tracing and ZK paths.
    NODE_ID: str = Field(..., description="Unique identifier for this node")
    
    INTERNAL_PORT: int = Field(8000, description="Internal port for node-to-node communication")
    PUBLIC_BASE_URL: str = Field("http://localhost:8000", description="Public base URL for webhooks and client redirects")
    
    API_KEY: str = Field(..., description="API Key for public endpoints")
    RAFT_INTERNAL_TOKEN: str = Field(..., description="Shared secret for internal Raft RPCs")
    RAFT_CLUSTER_SIZE: int = Field(5, description="Expected total nodes in the cluster")

    # Raft Consensus Timings
    RAFT_HEARTBEAT_INTERVAL_SEC: float = Field(0.15, description="Interval between leader heartbeats in seconds")
    RAFT_RPC_TIMEOUT_SEC: float = Field(0.5, description="Timeout for Raft internal RPCs in seconds")
    RAFT_COMMIT_TIMEOUT_SEC: float = Field(8.0, description="Max wait time for quorum commit in seconds")
    RAFT_READ_INDEX_TIMEOUT_SEC: float = Field(5.0, description="Max wait time for ReadIndex protocol in seconds")
    RAFT_MIN_ELECTION_TIMEOUT_MS: int = Field(15000, description="Minimum election timeout in milliseconds")
    RAFT_MAX_ELECTION_TIMEOUT_MS: int = Field(20000, description="Maximum election timeout in milliseconds")

    # ZooKeeper settings
    ZOOKEEPER_HOST: str = Field(..., description="ZooKeeper host address")
    ZOOKEEPER_PORT: int = Field(2181, description="ZooKeeper port")
    SESSION_TIMEOUT: int = Field(15, description="ZooKeeper session timeout in seconds")
    HEARTBEAT_INTERVAL: int = Field(5, description="Node heartbeat interval in seconds")

    # PostgreSQL settings
    POSTGRES_HOST: str = Field(..., description="PostgreSQL host address")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field(..., description="PostgreSQL user")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name")

    # Failover and Logging
    FAILOVER_STRATEGY: str = Field("round_robin", description="Strategy for failover (round_robin, random, least_connections)")
    LOG_LEVEL: str = Field("INFO", description="Application log level")

    # Time Synchronization (NTP & HLC)
    NTP_SERVERS: str = Field("pool.ntp.org", description="Comma separated list of NTP servers")
    NTP_SYNC_INTERVAL_SECONDS: int = Field(60, description="Interval to query NTP servers")
    MAX_ALLOWED_SKEW_MS: int = Field(5000, description="Maximum allowed clock skew in ms before raising an alert")
    REORDER_BUFFER_FLUSH_INTERVAL_MS: int = Field(5000, description="How long to wait before flushing logs to ensure ordering")

    # Stripe Test Configuration
    STRIPE_SECRET_KEY: str = Field(..., description="Stripe Secret API Key (Test Mode)")
    STRIPE_PUBLISHABLE_KEY: str = Field(..., description="Stripe Publishable API Key (Test Mode)")
    STRIPE_WEBHOOK_SECRET: str = Field(..., description="Stripe Webhook Signing Secret")
    PAYMENT_CURRENCY: str = Field("usd", description="Default payment currency")
    PAYMENT_PROVIDER: str = Field("stripe", description="Default payment provider")

    # Email Service (Brevo)
    BREVO_API_KEY: str = Field("", description="Brevo (Sendinblue) API Key")
    BREVO_SENDER_EMAIL: str = Field("noreply@settle.com", description="Default sender email address")
    BREVO_SENDER_NAME: str = Field("Settle", description="Default sender name")

    # Monitoring & Observability
    JAEGER_OTLP_ENDPOINT: str = Field("localhost:4317", description="Jaeger OTLP gRPC endpoint for trace export")
    PROMETHEUS_ENABLED: bool = Field(True, description="Enable Prometheus metrics collection")
    TRACING_ENABLED: bool = Field(True, description="Enable OpenTelemetry distributed tracing")
    TRACING_SAMPLE_RATE: float = Field(1.0, description="Trace sampling rate (1.0 = sample everything)")
    LOKI_URL: str = Field("http://localhost:3100", description="Loki log aggregation endpoint")

    # Authentication & RBAC
    JWT_SECRET_KEY: str = Field(..., description="Secret key for signing JWT tokens")
    JWT_ALGORITHM: str = Field("HS256", description="Algorithm used for JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(1440, description="Access token expiration time (default 24h)")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def database_url(self) -> str:
        """Constructs the SQLAlchemy database URL safely encoding passwords."""
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

# Singleton instance of settings to be used throughout the app
try:
    settings = Settings()
except Exception as e:
    # Handle missing keys gracefully with a secure fallback
    missing = False
    
    if "API_KEY" not in os.environ:
        os.environ["API_KEY"] = secrets.token_hex(32)
        print(f"WARNING: API_KEY not provided! Generating an ephemeral instance-isolated secret key for security: {os.environ['API_KEY']}")
        missing = True
        
    if "RAFT_INTERNAL_TOKEN" not in os.environ:
        os.environ["RAFT_INTERNAL_TOKEN"] = secrets.token_hex(32)
        print(f"WARNING: RAFT_INTERNAL_TOKEN not provided! Generating an ephemeral instance-isolated secret key for security: {os.environ['RAFT_INTERNAL_TOKEN']}")
        missing = True
        
    if "JWT_SECRET_KEY" not in os.environ:
        os.environ["JWT_SECRET_KEY"] = secrets.token_hex(32)
        print(f"WARNING: JWT_SECRET_KEY not provided! Generating an ephemeral secret key.")
        missing = True
        
    if missing:
        settings = Settings()
    else:
        raise e
