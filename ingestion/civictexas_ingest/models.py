"""Provider-neutral data structures.

Every provider (official TLC bulk files, Open States, LegiScan, ...) converts
its records into these shapes. Nothing downstream of a provider should know
which provider produced a record, apart from `source_id`.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

BILL_TYPES = ("HB", "SB", "HJR", "SJR", "HCR", "SCR", "HR", "SR")


@dataclass(frozen=True)
class BillRef:
    """Identifies a bill. Bill numbers are only unique within a session."""

    session_id: str  # TLC session code, e.g. '89R', '891', '90R'
    bill_type: str  # one of BILL_TYPES
    bill_number: int

    @property
    def identifier(self) -> str:
        return f"{self.bill_type} {self.bill_number}"

    @property
    def chamber(self) -> str:
        return "house" if self.bill_type.startswith("H") else "senate"

    def __str__(self) -> str:
        return f"{self.session_id} {self.identifier}"


@dataclass
class Action:
    sequence: int
    action_code: Optional[str]
    actor: str  # 'house' | 'senate' | 'executive' | 'other'
    action_date: Optional[date]
    action_timestamp: Optional[datetime]
    description: str
    comment: Optional[str]


@dataclass
class Sponsor:
    name: str
    role: str  # 'author' | 'coauthor' | 'sponsor' | 'cosponsor'
    chamber: str
    position: int


@dataclass
class CommitteeReferral:
    chamber: str
    name: str
    status: Optional[str]
    ayes: int
    nays: int
    present_not_voting: int
    absent: int

    @property
    def has_vote(self) -> bool:
        return (self.ayes + self.nays + self.present_not_voting + self.absent) > 0


@dataclass
class DocumentRef:
    doc_type: str  # 'bill_text' | 'analysis' | 'fiscal_note'
    version_code: str  # TLC suffix letter(s): I, H, E, S, F, ...
    description: str
    ordinal: int
    source_html_url: Optional[str]  # machine source (FTP)
    official_html_url: Optional[str]  # public web page
    official_pdf_url: Optional[str]


@dataclass
class FloorVoteRef:
    chamber: str
    vote_date: Optional[date]
    reference: str  # e.g. 'RV#4015'
    motion: str


@dataclass
class NormalizedBill:
    ref: BillRef
    caption: str
    caption_version: Optional[str]
    last_action_text: Optional[str]
    last_action_date: Optional[date]
    subjects: List[str]
    companions: Optional[str]
    sponsors: List[Sponsor]
    committees: List[CommitteeReferral]
    actions: List[Action]
    documents: List[DocumentRef]
    floor_votes: List[FloorVoteRef]
    source_id: str
    source_url: str
    official_url: str
    source_updated_at: Optional[datetime]
    content_hash: str = ""
    status: str = "unknown"
    status_date: Optional[date] = None
    extra: dict = field(default_factory=dict)
