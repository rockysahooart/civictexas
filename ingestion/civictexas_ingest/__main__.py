"""Command line entry point.

    python -m civictexas_ingest sync --session 90R --mode sample
    python -m civictexas_ingest sync --session 89R --mode incremental
    python -m civictexas_ingest sync --session 90R --mode full --limit 50
    python -m civictexas_ingest sync --session 89R --bills "HB 2,SB 1"
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from . import db
from .config import Config
from .fetch import Fetcher
from .models import BillRef
from .providers.tlc_ftp import TlcFtpProvider, parse_bill_id
from .sync import should_skip, sync_bills

SAMPLE_FILE = Path(__file__).resolve().parent.parent / "sample_bills.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="civictexas_ingest")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sync", help="synchronize bills from the official TLC bulk files")
    s.add_argument("--session", required=True, help="TLC session code, e.g. 89R, 891, 90R")
    s.add_argument("--mode", choices=["sample", "incremental", "full"], default="sample")
    s.add_argument("--bills", help="comma-separated bill ids (overrides --mode sample list)")
    s.add_argument("--limit", type=int, help="maximum bills to process (full mode)")
    s.add_argument("--refresh-documents", action="store_true",
                   help="re-download stored document versions to detect corrections")
    s.add_argument("--force", action="store_true", help="ignore SYNC_MIN_INTERVAL_MINUTES")
    s.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")
    config = Config.from_env()
    fetcher = Fetcher(min_interval=config.request_interval_seconds, max_retries=config.max_retries,
                      timeout=config.request_timeout_seconds)
    provider = TlcFtpProvider(fetcher, base_url=config.tlc_ftp_base)

    with db.connect(config.database_url) as conn:
        if args.mode == "incremental" and not args.force and \
                should_skip(conn, provider, args.session, config.min_sync_interval_minutes):
            print(f"Skipping {args.session}: last successful sync was under "
                  f"{config.min_sync_interval_minutes} minutes ago (use --force to override).")
            return 0

        cursor = None
        if args.bills:
            refs = [BillRef(args.session, *parse_bill_id(b)) for b in args.bills.split(",") if b.strip()]
            mode = "sample"
        elif args.mode == "sample":
            sample = json.loads(SAMPLE_FILE.read_text())
            if args.session not in sample:
                print(f"No sample bills defined for {args.session} in {SAMPLE_FILE.name}", file=sys.stderr)
                return 2
            refs = [BillRef(args.session, *parse_bill_id(b)) for b in sample[args.session]]
            mode = "sample"
        elif args.mode == "incremental":
            _, previous = db.get_sync_state(conn, provider.source_id, args.session)
            refs, cursor = provider.list_changed_bills(args.session, previous)
            mode = "incremental"
        else:
            refs = provider.list_bills(args.session, limit=args.limit)
            mode = "full"

        result = sync_bills(conn, provider, args.session, refs, mode=mode,
                            fetch_documents=config.fetch_documents, refresh_documents=args.refresh_documents,
                            max_document_bytes=config.max_document_bytes, cursor=cursor)

    print(f"{args.session} {mode}: {result.status} - {result.seen} seen, {result.changed} changed, "
          f"{result.documents_added} documents added, {len(result.errors)} errors, "
          f"{fetcher.request_count} requests")
    for error in result.errors:
        print(f"  error: {error}", file=sys.stderr)
    return 0 if result.status in ("succeeded", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
