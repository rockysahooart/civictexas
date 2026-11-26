"""Generate, validate and store summaries; record human review decisions.

Lifecycle of a summary (public.ai_summaries.review_status):
  pending_review -> approved   (a reviewer checked it against the official text)
  pending_review -> rejected   (automatic validation failed, or a reviewer rejected it)
  approved       -> superseded (the official text changed; done by a database trigger)

Only 'approved' summaries are visible to the public (enforced by RLS).
"""
import json
from dataclasses import dataclass
from typing import List, Optional

import psycopg

from .prompt import build_prompt
from .providers import SummaryProvider
from .schema import SchemaError, parse_summary
from .validate import Issue, ValidationResult, validate_summary

STATUS_LABELS_FOR_PROMPT = {
    "signed": "Signed by the Governor (enacted)",
    "became_law_without_signature": "Became law without the Governor's signature (enacted)",
}


@dataclass
class GenerationResult:
    summary_id: Optional[str]
    review_status: str
    validation: ValidationResult


def _load_source(conn: psycopg.Connection, bill_version_id: str):
    row = conn.execute(
        """
        select b.id, b.identifier, s.name, b.status, v.description, d.id, d.content_hash, d.plain_text,
               exists(select 1 from fiscal_notes f where f.bill_id = b.id and f.version_code = v.version_code
                      and f.source_document_id is not null)
        from bill_versions v
        join bills b on b.id = v.bill_id
        join legislative_sessions s on s.id = b.session_id
        join source_documents d on d.bill_id = v.bill_id and d.doc_type = 'bill_text'
             and d.version_code = v.version_code and d.is_current
        where v.id = %s
        """, (bill_version_id,)).fetchone()
    if not row:
        raise LookupError("no stored official text for this bill version")
    return row


def generate_summary(conn: psycopg.Connection, bill_version_id: str, provider: SummaryProvider) -> GenerationResult:
    (bill_id, identifier, session_name, status, version_desc, doc_id, content_hash, text,
     has_fiscal) = _load_source(conn, bill_version_id)
    fiscal_text = ""
    if has_fiscal:
        fiscal_text = conn.execute(
            "select d.plain_text from fiscal_notes f join source_documents d on d.id = f.source_document_id "
            "join bill_versions v on v.bill_id = f.bill_id and v.version_code = f.version_code where v.id = %s",
            (bill_version_id,)).fetchone()[0]
    status_label = STATUS_LABELS_FOR_PROMPT.get(status, f"{status.replace('_', ' ')} (not enacted)")
    prompt = build_prompt(identifier, session_name, version_desc, status_label, text, fiscal_text)

    raw = provider.generate(prompt)
    try:
        summary = parse_summary(json.loads(raw))
        validation = validate_summary(summary, text, status, has_fiscal_note=has_fiscal)
        content = summary.to_json()
    except (json.JSONDecodeError, SchemaError) as error:
        validation = ValidationResult()
        validation.issues.append(Issue("invalid_output", str(error), "output"))
        content = {"raw_output": raw[:20000]}

    review_status = "pending_review" if validation.passed else "rejected"
    summary_id = conn.execute(
        """
        insert into ai_summaries (bill_id, bill_version_id, source_document_id, source_content_hash, provider,
                                  model_id, prompt_version, content, validation, review_status, review_notes)
        values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        returning id
        """,
        (bill_id, bill_version_id, doc_id, content_hash, provider.name, provider.model_id, prompt.prompt_version,
         json.dumps(content), json.dumps(validation.to_json()), review_status,
         None if validation.passed else "Rejected automatically: failed validation")).fetchone()[0]
    conn.commit()
    return GenerationResult(str(summary_id), review_status, validation)


def record_review(conn: psycopg.Connection, summary_id: str, decision: str, reviewer_id: Optional[str],
                  notes: str) -> None:
    """Record a human decision. Approving requires the summary to still match current text."""
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")
    row = conn.execute(
        """
        select s.review_status, s.validation->>'passed', d.is_current
        from ai_summaries s join source_documents d on d.id = s.source_document_id where s.id = %s
        """, (summary_id,)).fetchone()
    if not row:
        raise LookupError("summary not found")
    status, passed, is_current = row
    if status != "pending_review":
        raise ValueError(f"summary is {status}, not pending review")
    if decision == "approved" and (passed != "true" or not is_current):
        raise ValueError("only summaries that passed validation and match the current official text can be approved")
    if decision == "approved":
        # Only one approved summary per version; the newest approval wins.
        conn.execute(
            "update ai_summaries set review_status = 'superseded' where bill_version_id = "
            "(select bill_version_id from ai_summaries where id = %s) and review_status = 'approved'", (summary_id,))
    conn.execute(
        "update ai_summaries set review_status = %s, reviewed_by = %s, reviewed_at = now(), review_notes = %s "
        "where id = %s", (decision, reviewer_id, notes, summary_id))
    conn.commit()


def pending_reviews(conn: psycopg.Connection) -> List[tuple]:
    return conn.execute(
        """
        select s.id, b.session_id, b.identifier, v.description, s.model_id, s.generated_at
        from ai_summaries s join bills b on b.id = s.bill_id join bill_versions v on v.id = s.bill_version_id
        where s.review_status = 'pending_review' order by s.generated_at
        """).fetchall()
