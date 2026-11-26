"""Provider interface.

The app must not depend permanently on one data source. Each source is a
provider that turns its records into `NormalizedBill` objects. The sync job
only talks to this interface.
"""
from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List, Optional, Tuple

from ..models import BillRef, NormalizedBill


class ValidationError(ValueError):
    """A source record failed validation and must not be stored."""


class LegislativeProvider(ABC):
    #: Matches public.data_sources.id
    source_id: str = ""
    #: True only for official legislative records.
    is_authoritative: bool = False

    @abstractmethod
    def list_bills(self, session_id: str, bill_types: Optional[Iterable[str]] = None,
                   limit: Optional[int] = None) -> Iterator[BillRef]:
        """Yield every bill in a session (handles pagination internally)."""

    @abstractmethod
    def list_changed_bills(self, session_id: str, since_cursor: Optional[str]) -> Tuple[List[BillRef], Optional[str]]:
        """Return bills changed since `since_cursor` and the new cursor."""

    @abstractmethod
    def fetch_bill(self, ref: BillRef) -> NormalizedBill:
        """Fetch, validate and normalize one bill. Raise ValidationError on bad data."""

    @abstractmethod
    def fetch_document(self, url: str) -> bytes:
        """Fetch a document (bill text, fiscal note) by its source URL."""
