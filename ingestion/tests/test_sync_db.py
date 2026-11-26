"""Integration tests against a real PostgreSQL database.

Set TEST_DATABASE_ADMIN_URL to a server where a throwaway database
`civictexas_test` may be created and dropped, e.g.
    postgresql://postgres@localhost:54329/postgres
Skipped when it is not set.
"""
import json
import os
from pathlib import Path

import psycopg
import pytest

from civictexas_ingest.models import BillRef
from civictexas_ingest.providers.base import LegislativeProvider, ValidationError
from civictexas_ingest.providers.tlc_ftp import parse_bill_xml
from civictexas_ingest.sync import sync_bills

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL = Path(__file__).parent / "fixtures" / "official"
ADMIN_URL = os.environ.get("TEST_DATABASE_ADMIN_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="TEST_DATABASE_ADMIN_URL not set")


class FixtureProvider(LegislativeProvider):
    """Serves the official fixture files instead of hitting the network."""
    source_id = "tlc_ftp"
    is_authoritative = True

    def __init__(self):
        self.bills = {BillRef("89R", "HB", 2): (OFFICIAL / "89R_HB_2.xml").read_bytes(),
                      BillRef("90R", "HB", 101): (OFFICIAL / "90R_HB_101.xml").read_bytes()}
        self.documents = {}
        self.default_document = (OFFICIAL / "90R_HB00101I.htm").read_bytes()

    def list_bills(self, session_id, bill_types=None, limit=None):
        return iter([r for r in self.bills if r.session_id == session_id])

    def list_changed_bills(self, session_id, since_cursor):
        return list(self.list_bills(session_id)), "cursor"

    def fetch_bill(self, ref):
        if ref not in self.bills:
            raise ValidationError(f"no fixture for {ref}")
        return parse_bill_xml(self.bills[ref], source_url=f"fixture://{ref}", expected=ref)

    def fetch_document(self, url):
        return self.documents.get(url, self.default_document)


@pytest.fixture()
def conn():
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute("drop database if exists civictexas_test")
        admin.execute("create database civictexas_test")
    url = ADMIN_URL.rsplit("/", 1)[0] + "/civictexas_test"
    with psycopg.connect(url, autocommit=True) as setup:
        setup.execute((ROOT / "supabase/local/supabase_shim.sql").read_text())
        for migration in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            setup.execute(migration.read_text())
    with psycopg.connect(url, prepare_threshold=None) as connection:
        yield connection
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute("drop database if exists civictexas_test with (force)")


def count(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


def test_sync_is_idempotent(conn):
    provider = FixtureProvider()
    first = sync_bills(conn, provider, "89R", [BillRef("89R", "HB", 2)], mode="sample")
    assert first.status == "succeeded" and first.changed == 1
    assert first.documents_added == 10  # 5 bill text versions + 5 fiscal notes
    assert count(conn, "select count(*) from bill_actions") > 100
    assert count(conn, "select status from bills where bill_number = 2") == "signed"
    assert count(conn, "select count(*) from votes where vote_type = 'committee'") == 2
    assert count(conn, "select count(*) from votes where vote_type = 'floor' and yeas is null") >= 1

    second = sync_bills(conn, provider, "89R", [BillRef("89R", "HB", 2)], mode="sample")
    assert (second.changed, second.documents_added) == (0, 0)
    assert count(conn, "select count(*) from bills") == 1
    assert count(conn, "select count(*) from source_documents") == 10
    assert count(conn, "select count(*) from sync_runs where status = 'succeeded'") == 2


def test_bill_numbers_are_scoped_to_sessions(conn):
    provider = FixtureProvider()
    xml = (OFFICIAL / "90R_HB_101.xml").read_bytes()
    provider.bills[BillRef("89R", "HB", 101)] = xml.replace(b'bill="90(R) HB 101"', b'bill="89(R) HB 101"')  # SYNTHETIC
    sync_bills(conn, provider, "90R", [BillRef("90R", "HB", 101)], mode="sample", fetch_documents=False)
    sync_bills(conn, provider, "89R", [BillRef("89R", "HB", 101)], mode="sample", fetch_documents=False)
    assert count(conn, "select count(*) from bills where bill_type = 'HB' and bill_number = 101") == 2


def test_changed_text_creates_new_version_and_supersedes_summary(conn):
    provider = FixtureProvider()
    ref = BillRef("90R", "HB", 101)
    sync_bills(conn, provider, "90R", [ref], mode="sample")
    doc_id, version_id, bill_id = conn.execute(
        "select id, bill_version_id, bill_id from source_documents where doc_type = 'bill_text'").fetchone()
    conn.execute(
        "insert into ai_summaries (bill_id, bill_version_id, source_document_id, source_content_hash, provider,"
        " model_id, prompt_version, content, validation, review_status)"
        " values (%s, %s, %s, 'h', 'test', 'test-model', 'v1', '{}', '{}', 'approved')",
        (bill_id, version_id, doc_id))
    conn.commit()

    # SYNTHETIC correction to the published text.
    url = next(d.source_html_url for d in provider.fetch_bill(ref).documents)
    provider.documents[url] = provider.default_document.replace(b"medical assistance", b"medical aid")
    result = sync_bills(conn, provider, "90R", [ref], mode="sample", refresh_documents=True)
    assert result.documents_added == 1

    rows = conn.execute("select is_current, supersedes_id from source_documents where doc_type = 'bill_text'"
                        " order by retrieved_at").fetchall()
    assert len(rows) == 2
    assert rows[0][0] is False and rows[1][0] is True
    assert rows[1][1] == doc_id
    assert count(conn, "select review_status from ai_summaries") == "superseded"


def test_source_documents_are_immutable(conn):
    sync_bills(conn, FixtureProvider(), "90R", [BillRef("90R", "HB", 101)], mode="sample")
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        conn.execute("update source_documents set plain_text = 'tampered'")
    conn.rollback()


def test_failures_are_logged_without_stopping_the_run(conn):
    refs = [BillRef("90R", "HB", 999), BillRef("90R", "HB", 101)]
    result = sync_bills(conn, FixtureProvider(), "90R", refs, mode="sample", fetch_documents=False,
                        cursor="new-cursor")
    assert result.status == "partial"
    errors = count(conn, "select errors from sync_runs")
    assert errors[0]["bill"] == "90R HB 999"
    # Cursor is not advanced on a partial run, so the failure is retried.
    assert count(conn, "select cursor from sync_state") is None


def as_role(conn, role, user_id=None):
    conn.execute(f"set local role {role}")
    if user_id:
        conn.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(user_id),))


def test_row_level_security(conn):
    sync_bills(conn, FixtureProvider(), "90R", [BillRef("90R", "HB", 101)], mode="sample")
    doc_id, version_id, bill_id = conn.execute(
        "select id, bill_version_id, bill_id from source_documents where doc_type = 'bill_text'").fetchone()
    for status in ("pending_review", "rejected"):
        conn.execute(
            "insert into ai_summaries (bill_id, bill_version_id, source_document_id, source_content_hash, provider,"
            " model_id, prompt_version, content, validation, review_status)"
            " values (%s, %s, %s, 'h', 'test', 'm', 'v1', '{}', '{}', %s)", (bill_id, version_id, doc_id, status))
    conn.commit()

    # Anonymous visitors can read legislative data without an account...
    as_role(conn, "anon")
    assert count(conn, "select count(*) from bills") == 1
    # ...but cannot see unreviewed summaries...
    assert count(conn, "select count(*) from ai_summaries") == 0
    # ...cannot write legislative data...
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("update bills set caption = 'x'")
    conn.rollback()
    # ...but can report an inaccurate summary.
    as_role(conn, "anon")
    conn.execute("insert into content_reports (target_type, target_id, reason, details)"
                 " values ('ai_summary', gen_random_uuid(), 'inaccurate', 'Section 2 is misdescribed')")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("insert into content_reports (target_type, target_id, reason, status)"
                     " values ('ai_summary', gen_random_uuid(), 'inaccurate', 'resolved')")
    conn.rollback()

    # Users only see their own saved bills.
    users = [conn.execute("insert into auth.users default values returning id").fetchone()[0] for _ in range(2)]
    for user in users:
        conn.execute("insert into profiles (id) values (%s)", (user,))
    conn.execute("insert into saved_bills (user_id, bill_id) values (%s, %s)", (users[0], bill_id))
    conn.commit()
    as_role(conn, "authenticated", users[1])
    assert count(conn, "select count(*) from saved_bills") == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("update profiles set role = 'admin' where id = %s", (users[1],))
    conn.rollback()
    as_role(conn, "authenticated", users[0])
    assert count(conn, "select count(*) from saved_bills") == 1
    conn.rollback()


def test_full_text_search(conn):
    sync_bills(conn, FixtureProvider(), "90R", [BillRef("90R", "HB", 101)], mode="sample", fetch_documents=False)
    found = conn.execute("select identifier from bills where search @@ websearch_to_tsquery('english', 'medicaid eligibility')").fetchall()
    assert found == [("HB 101",)]
    found = conn.execute("select identifier from bills where search @@ plainto_tsquery('simple', 'HB101')").fetchall()
    assert found == [("HB 101",)]
