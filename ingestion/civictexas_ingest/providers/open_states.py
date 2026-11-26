"""Supplementary source: Open States API v3 (not implemented yet).

Planned use: floor vote details and legislator metadata (party, district),
which the official bill history files do not include. Requires a free API key
(OPEN_STATES_API_KEY) from https://open.pluralpolicy.com/.

This placeholder exists so the provider interface is exercised by more than
one implementation. It deliberately raises instead of returning partial data.
"""
from typing import Iterable, Iterator, List, Optional, Tuple

from ..models import BillRef, NormalizedBill
from .base import LegislativeProvider


class OpenStatesProvider(LegislativeProvider):
    source_id = "open_states"
    is_authoritative = False

    def __init__(self, api_key: Optional[str]):
        if not api_key:
            raise RuntimeError("OPEN_STATES_API_KEY is not set")
        self.api_key = api_key

    def list_bills(self, session_id: str, bill_types: Optional[Iterable[str]] = None,
                   limit: Optional[int] = None) -> Iterator[BillRef]:
        raise NotImplementedError("Open States provider is planned; see docs/data-sources.md")

    def list_changed_bills(self, session_id: str, since_cursor: Optional[str]) -> Tuple[List[BillRef], Optional[str]]:
        raise NotImplementedError("Open States provider is planned; see docs/data-sources.md")

    def fetch_bill(self, ref: BillRef) -> NormalizedBill:
        raise NotImplementedError("Open States provider is planned; see docs/data-sources.md")

    def fetch_document(self, url: str) -> bytes:
        raise NotImplementedError("Open States provider is planned; see docs/data-sources.md")
