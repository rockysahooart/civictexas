"""Database writes. All statements are idempotent so re-running a sync is safe."""
import json
import re
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import psycopg

from .models import DocumentRef, NormalizedBill
from .status import derive_status
from .text import decode_html, html_to_text, sha256


def connect(database_url: str) -> psycopg.Connection:
    # prepare_threshold=None keeps this compatible with Supabase's transaction pooler.
    return psycopg.connect(database_url, autocommit=False, prepare_threshold=None)


def ensure_session(conn: psycopg.Connection, session_id: str) -> Optional[date]:
    """Create the session row if missing. Returns its end date (if known)."""
    row = conn.execute("select end_date from legislative_sessions where id = %s", (session_id,)).fetchone()
    if row:
        return row[0]
    match = re.match(r"^(\d{2,3})(R|\d)$", session_id)
    if not match:
        raise ValueError(f"bad session id {session_id!r}")
    number, kind = int(match.group(1)), match.group(2)
    ordinal = f"{number}{'th' if 10 <= number % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')}"
    if kind == "R":
        name, session_type, special = f"{ordinal} Legislature, Regular Session", "regular", None
    else:
        name, session_type, special = f"{ordinal} Legislature, Special Session {kind}", "special", int(kind)
    conn.execute(
        "insert into legislative_sessions (id, legislature_number, session_type, special_number, name) "
        "values (%s, %s, %s, %s, %s) on conflict (id) do nothing",
        (session_id, number, session_type, special, name))
    return None


def get_bill_hash(conn: psycopg.Connection, bill: NormalizedBill) -> Optional[Tuple[str, str, str]]:
    """Return (id, content_hash, status) for a stored bill, if any."""
    row = conn.execute(
        "select id, content_hash, status from bills where session_id = %s and bill_type = %s and bill_number = %s",
        (bill.ref.session_id, bill.ref.bill_type, bill.ref.bill_number)).fetchone()
    return (str(row[0]), row[1], row[2]) if row else None


def touch_bill(conn: psycopg.Connection, bill_id: str, synced_at: datetime) -> None:
    conn.execute("update bills set last_synced_at = %s where id = %s", (synced_at, bill_id))


def upsert_bill(conn: psycopg.Connection, bill: NormalizedBill, session_end: Optional[date],
                synced_at: datetime) -> str:
    """Write a bill and its related rows. Returns the bill id."""
    bill.status, bill.status_date = derive_status(bill.ref.bill_type, bill.actions, session_end)
    bill_id = conn.execute(
        """
        insert into bills (session_id, bill_type, bill_number, chamber, caption, caption_version, status,
                           status_date, last_action_text, last_action_date, subjects, companions, source_id,
                           source_url, official_url, source_updated_at, last_synced_at, content_hash)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (session_id, bill_type, bill_number) do update set
          caption = excluded.caption, caption_version = excluded.caption_version, status = excluded.status,
          status_date = excluded.status_date, last_action_text = excluded.last_action_text,
          last_action_date = excluded.last_action_date, subjects = excluded.subjects,
          companions = excluded.companions, source_id = excluded.source_id, source_url = excluded.source_url,
          official_url = excluded.official_url, source_updated_at = excluded.source_updated_at,
          last_synced_at = excluded.last_synced_at, content_hash = excluded.content_hash
        returning id
        """,
        (bill.ref.session_id, bill.ref.bill_type, bill.ref.bill_number, bill.ref.chamber, bill.caption,
         bill.caption_version, bill.status, bill.status_date, bill.last_action_text, bill.last_action_date,
         bill.subjects, bill.companions, bill.source_id, bill.source_url, bill.official_url,
         bill.source_updated_at, synced_at, bill.content_hash)).fetchone()[0]
    bill_id = str(bill_id)

    # Sponsors: the official record is the full current list, so replace it.
    conn.execute("delete from bill_sponsors where bill_id = %s", (bill_id,))
    for sponsor in bill.sponsors:
        legislator_id = conn.execute(
            "insert into legislators (display_name, chamber) values (%s, %s) "
            "on conflict (chamber, display_name) do update set display_name = excluded.display_name returning id",
            (sponsor.name, sponsor.chamber)).fetchone()[0]
        conn.execute(
            "insert into bill_sponsors (bill_id, legislator_id, role, position) values (%s, %s, %s, %s) "
            "on conflict do nothing", (bill_id, legislator_id, sponsor.role, sponsor.position))

    for referral in bill.committees:
        committee_id = conn.execute(
            "insert into committees (chamber, name) values (%s, %s) "
            "on conflict (chamber, name) do update set name = excluded.name returning id",
            (referral.chamber, referral.name)).fetchone()[0]
        conn.execute(
            "insert into bill_committee_referrals (bill_id, committee_id, status) values (%s, %s, %s) "
            "on conflict (bill_id, committee_id) do update set status = excluded.status, updated_at = now()",
            (bill_id, committee_id, referral.status))
        if referral.has_vote:
            conn.execute(
                """
                insert into votes (bill_id, chamber, vote_type, committee_id, motion, yeas, nays,
                                   present_not_voting, absent, source_reference, source_id)
                values (%s, %s, 'committee', %s, 'Committee vote', %s, %s, %s, %s, '', %s)
                on conflict (bill_id, chamber, vote_type,
                             coalesce(committee_id, '00000000-0000-0000-0000-000000000000'::uuid), source_reference)
                do update set yeas = excluded.yeas, nays = excluded.nays,
                              present_not_voting = excluded.present_not_voting, absent = excluded.absent
                """,
                (bill_id, referral.chamber, committee_id, referral.ayes, referral.nays,
                 referral.present_not_voting, referral.absent, bill.source_id))

    for vote in bill.floor_votes:
        conn.execute(
            """
            insert into votes (bill_id, chamber, vote_type, vote_date, motion, source_reference, source_id)
            values (%s, %s, 'floor', %s, %s, %s, %s)
            on conflict (bill_id, chamber, vote_type,
                         coalesce(committee_id, '00000000-0000-0000-0000-000000000000'::uuid), source_reference)
            do update set vote_date = excluded.vote_date, motion = excluded.motion
            """,
            (bill_id, vote.chamber, vote.vote_date, vote.motion, vote.reference, bill.source_id))

    # Actions: the official history is ordered; keep our copy identical to it.
    for action in bill.actions:
        conn.execute(
            """
            insert into bill_actions (bill_id, sequence, action_code, actor, action_date, action_timestamp,
                                      description, comment)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (bill_id, sequence) do update set
              action_code = excluded.action_code, actor = excluded.actor, action_date = excluded.action_date,
              action_timestamp = excluded.action_timestamp, description = excluded.description,
              comment = excluded.comment
            """,
            (bill_id, action.sequence, action.action_code, action.actor, action.action_date,
             action.action_timestamp, action.description, action.comment))
    conn.execute("delete from bill_actions where bill_id = %s and sequence >= %s", (bill_id, len(bill.actions)))

    for doc in bill.documents:
        if doc.doc_type == "bill_text":
            conn.execute(
                """
                insert into bill_versions (bill_id, version_code, description, ordinal, html_url, pdf_url)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (bill_id, version_code) do update set description = excluded.description,
                  ordinal = excluded.ordinal, html_url = excluded.html_url, pdf_url = excluded.pdf_url
                """,
                (bill_id, doc.version_code, doc.description, doc.ordinal, doc.official_html_url, doc.official_pdf_url))
        elif doc.doc_type == "fiscal_note":
            conn.execute(
                """
                insert into fiscal_notes (bill_id, version_code, description, html_url, pdf_url)
                values (%s, %s, %s, %s, %s)
                on conflict (bill_id, version_code) do update set description = excluded.description,
                  html_url = excluded.html_url, pdf_url = excluded.pdf_url
                """,
                (bill_id, doc.version_code, doc.description, doc.official_html_url, doc.official_pdf_url))
    return bill_id


def current_document_hashes(conn: psycopg.Connection, bill_id: str) -> Dict[Tuple[str, str], str]:
    rows = conn.execute(
        "select doc_type, version_code, content_hash from source_documents where bill_id = %s and is_current",
        (bill_id,)).fetchall()
    return {(r[0], r[1]): r[2] for r in rows}


def store_document(conn: psycopg.Connection, bill_id: str, doc: DocumentRef, raw: bytes,
                   source_id: str) -> bool:
    """Store a document snapshot. Returns True if a new snapshot was added.

    Unchanged content is not duplicated. Changed content becomes a new row and
    the previous snapshot is kept with is_current = false.
    """
    content_hash = sha256(raw)
    existing = conn.execute(
        "select id, content_hash from source_documents where bill_id = %s and doc_type = %s "
        "and version_code = %s and is_current", (bill_id, doc.doc_type, doc.version_code)).fetchone()
    if existing and existing[1] == content_hash:
        return False
    html = decode_html(raw)
    plain = html_to_text(html)
    version_id = None
    if doc.doc_type == "bill_text":
        row = conn.execute("select id from bill_versions where bill_id = %s and version_code = %s",
                           (bill_id, doc.version_code)).fetchone()
        version_id = row[0] if row else None
    if existing:
        conn.execute("update source_documents set is_current = false where id = %s", (existing[0],))
    new_id = conn.execute(
        """
        insert into source_documents (bill_id, bill_version_id, doc_type, version_code, source_id, source_url,
                                      official_url, content_hash, raw_content, plain_text, supersedes_id)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (bill_id, doc_type, version_code, content_hash) do update set is_current = true
        returning id
        """,
        (bill_id, version_id, doc.doc_type, doc.version_code, source_id, doc.source_html_url,
         doc.official_html_url, content_hash, html, plain, existing[0] if existing else None)).fetchone()[0]
    if doc.doc_type == "fiscal_note":
        conn.execute("update fiscal_notes set source_document_id = %s where bill_id = %s and version_code = %s",
                     (new_id, bill_id, doc.version_code))
    return True


# --- sync bookkeeping -------------------------------------------------------

def start_run(conn: psycopg.Connection, source_id: str, session_id: str, mode: str) -> str:
    run_id = conn.execute(
        "insert into sync_runs (source_id, session_id, mode) values (%s, %s, %s) returning id",
        (source_id, session_id, mode)).fetchone()[0]
    conn.commit()
    return str(run_id)


def finish_run(conn: psycopg.Connection, run_id: str, status: str, seen: int, changed: int, documents: int,
               errors: List[dict], notes: Optional[str] = None) -> None:
    conn.execute(
        "update sync_runs set status = %s, finished_at = now(), bills_seen = %s, bills_changed = %s, "
        "documents_added = %s, errors = %s::jsonb, notes = %s where id = %s",
        (status, seen, changed, documents, json.dumps(errors), notes, run_id))
    conn.commit()


def get_sync_state(conn: psycopg.Connection, source_id: str, session_id: str) -> Tuple[Optional[datetime], Optional[str]]:
    row = conn.execute("select last_successful_at, cursor from sync_state where source_id = %s and session_id = %s",
                       (source_id, session_id)).fetchone()
    return (row[0], row[1]) if row else (None, None)


def save_sync_state(conn: psycopg.Connection, source_id: str, session_id: str, run_id: str,
                    cursor: Optional[str]) -> None:
    conn.execute(
        """
        insert into sync_state (source_id, session_id, last_successful_run_id, last_successful_at, cursor)
        values (%s, %s, %s, now(), %s)
        on conflict (source_id, session_id) do update set last_successful_run_id = excluded.last_successful_run_id,
          last_successful_at = excluded.last_successful_at, cursor = coalesce(excluded.cursor, sync_state.cursor)
        """, (source_id, session_id, run_id, cursor))
    conn.commit()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
