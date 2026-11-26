"""Summary generation and human review.

    python -m civictexas_summarize generate --session 90R --bill "HB 101" [--version I]
    python -m civictexas_summarize pending
    python -m civictexas_summarize show <summary-id>
    python -m civictexas_summarize review <summary-id> --approve|--reject --notes "..." [--reviewer <profile-uuid>]

Generation needs a configured provider (see providers.py). Review works now.
"""
import argparse
import json
import os
import sys

import psycopg

from .pipeline import generate_summary, pending_reviews, record_review
from .providers import NotConfiguredError, get_provider


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="civictexas_summarize")
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--session", required=True)
    g.add_argument("--bill", required=True, help='e.g. "HB 101"')
    g.add_argument("--version", help="version code (I, H, E, S, F); defaults to the latest")
    sub.add_parser("pending")
    s = sub.add_parser("show")
    s.add_argument("summary_id")
    r = sub.add_parser("review")
    r.add_argument("summary_id")
    decision = r.add_mutually_exclusive_group(required=True)
    decision.add_argument("--approve", action="store_true")
    decision.add_argument("--reject", action="store_true")
    r.add_argument("--notes", required=True, help="what you checked, or why you rejected it")
    r.add_argument("--reviewer", help="reviewer's profile id (optional)")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    with psycopg.connect(database_url, prepare_threshold=None) as conn:
        if args.command == "generate":
            try:
                provider = get_provider()
            except NotConfiguredError as error:
                print(error, file=sys.stderr)
                return 2
            bill_type, number = args.bill.upper().split()
            row = conn.execute(
                """
                select v.id from bill_versions v join bills b on b.id = v.bill_id
                where b.session_id = %s and b.bill_type = %s and b.bill_number = %s
                  and (%s::text is null or v.version_code = %s)
                order by v.ordinal desc limit 1
                """, (args.session, bill_type, int(number), args.version, args.version)).fetchone()
            if not row:
                print("bill version not found", file=sys.stderr)
                return 1
            result = generate_summary(conn, str(row[0]), provider)
            print(f"summary {result.summary_id}: {result.review_status}")
            for issue in result.validation.issues:
                print(f"  {issue.severity}: {issue.code} at {issue.where}: {issue.message}")
        elif args.command == "pending":
            for summary_id, session, identifier, version, model, generated in pending_reviews(conn):
                print(f"{summary_id}  {session} {identifier} ({version})  {model}  {generated:%Y-%m-%d %H:%M}")
        elif args.command == "show":
            row = conn.execute("select content, validation, review_status from ai_summaries where id = %s",
                               (args.summary_id,)).fetchone()
            if not row:
                print("not found", file=sys.stderr)
                return 1
            print(json.dumps({"review_status": row[2], "validation": row[1], "content": row[0]}, indent=2))
        elif args.command == "review":
            record_review(conn, args.summary_id, "approved" if args.approve else "rejected", args.reviewer, args.notes)
            print("recorded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
