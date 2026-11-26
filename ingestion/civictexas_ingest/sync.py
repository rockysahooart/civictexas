"""Synchronization orchestrator.

Modes
- sample:      a fixed list of bills (see sample_bills.json). Used for the proof of concept.
- incremental: bills listed in the source's change index since the last cursor.
- full:        every bill in a session (paginated by range folder). Use --limit.

One bill failing does not stop the run. Each failure is logged in
sync_runs.errors and the run is marked 'partial'.
"""
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable, List, Optional

import psycopg

from . import db
from .fetch import FetchError
from .models import BillRef
from .providers.base import LegislativeProvider, ValidationError
from .status import derive_status

log = logging.getLogger(__name__)


@dataclass
class SyncResult:
    run_id: str
    status: str
    seen: int = 0
    changed: int = 0
    documents_added: int = 0
    errors: List[dict] = field(default_factory=list)


def should_skip(conn: psycopg.Connection, provider: LegislativeProvider, session_id: str,
                min_interval_minutes: int) -> bool:
    last_success, _ = db.get_sync_state(conn, provider.source_id, session_id)
    if last_success is None or min_interval_minutes <= 0:
        return False
    return db.utcnow() - last_success < timedelta(minutes=min_interval_minutes)


def sync_bills(conn: psycopg.Connection, provider: LegislativeProvider, session_id: str, refs: Iterable[BillRef],
               mode: str, fetch_documents: bool = True, refresh_documents: bool = False,
               max_document_bytes: int = 5_000_000, cursor: Optional[str] = None) -> SyncResult:
    session_end = db.ensure_session(conn, session_id)
    conn.commit()
    run_id = db.start_run(conn, provider.source_id, session_id, mode)
    result = SyncResult(run_id=run_id, status="running")

    for ref in refs:
        result.seen += 1
        try:
            bill = provider.fetch_bill(ref)
            synced_at = db.utcnow()
            bill.status, bill.status_date = derive_status(bill.ref.bill_type, bill.actions, session_end)
            existing = db.get_bill_hash(conn, bill)
            # Status can change without the record changing (e.g. the session ends).
            if existing and existing[1] == bill.content_hash and existing[2] == bill.status \
                    and not refresh_documents:
                bill_id = existing[0]
                db.touch_bill(conn, bill_id, synced_at)
                log.info("unchanged %s", ref)
            else:
                bill_id = db.upsert_bill(conn, bill, session_end, synced_at)
                result.changed += 1
                log.info("updated %s (%s)", ref, bill.status)

            if fetch_documents:
                have = db.current_document_hashes(conn, bill_id)
                for doc in bill.documents:
                    if doc.doc_type == "analysis" or not doc.source_html_url:
                        continue  # analyses are linked, not stored, in this phase
                    if (doc.doc_type, doc.version_code) in have and not refresh_documents:
                        continue
                    raw = provider.fetch_document(doc.source_html_url)
                    if len(raw) > max_document_bytes:
                        result.errors.append({"bill": str(ref), "document": doc.source_html_url,
                                              "error": f"skipped: {len(raw)} bytes exceeds limit"})
                        continue
                    if db.store_document(conn, bill_id, doc, raw, provider.source_id):
                        result.documents_added += 1
            conn.commit()
        except (ValidationError, FetchError, psycopg.Error, ValueError) as error:
            conn.rollback()
            log.error("failed %s: %s", ref, error)
            result.errors.append({"bill": str(ref), "error": f"{type(error).__name__}: {error}"})

    if result.seen == 0:
        result.status = "succeeded"
    elif len({e["bill"] for e in result.errors}) >= result.seen:
        result.status = "failed"
    else:
        result.status = "partial" if result.errors else "succeeded"

    db.finish_run(conn, run_id, result.status, result.seen, result.changed, result.documents_added, result.errors)
    if result.status in ("succeeded", "partial"):
        # Only advance the incremental cursor when every bill succeeded, so
        # failed bills are retried next time.
        db.save_sync_state(conn, provider.source_id, session_id, run_id,
                           cursor if result.status == "succeeded" else None)
    return result
