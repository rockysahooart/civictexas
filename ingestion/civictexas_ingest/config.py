"""Configuration from environment variables. See ../.env.example."""
import os
from dataclasses import dataclass
from typing import Optional


def _float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


@dataclass
class Config:
    database_url: str
    tlc_ftp_base: str
    request_interval_seconds: float
    max_retries: int
    request_timeout_seconds: float
    min_sync_interval_minutes: int
    fetch_documents: bool
    max_document_bytes: int
    open_states_api_key: Optional[str]

    @classmethod
    def from_env(cls) -> "Config":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise SystemExit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
        return cls(
            database_url=database_url,
            tlc_ftp_base=os.environ.get("TLC_FTP_BASE", "ftp://ftp.legis.state.tx.us/bills"),
            request_interval_seconds=_float("INGEST_REQUEST_INTERVAL_SECONDS", 1.0),
            max_retries=_int("INGEST_MAX_RETRIES", 3),
            request_timeout_seconds=_float("INGEST_REQUEST_TIMEOUT_SECONDS", 60.0),
            min_sync_interval_minutes=_int("SYNC_MIN_INTERVAL_MINUTES", 60),
            fetch_documents=os.environ.get("INGEST_FETCH_DOCUMENTS", "true").lower() != "false",
            max_document_bytes=_int("INGEST_MAX_DOCUMENT_BYTES", 5_000_000),
            open_states_api_key=os.environ.get("OPEN_STATES_API_KEY") or None,
        )
