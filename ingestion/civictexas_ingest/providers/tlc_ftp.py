"""Official source: Texas Legislative Council bulk downloads (anonymous FTP).

Layout (verified 2026-11-26):
  ftp://ftp.legis.state.tx.us/bills/{session}/billhistory/history.xml
      recently changed bills with timestamps (incremental sync cursor)
  .../billhistory/{house_bills|senate_bills|...}/{HB00100_HB00199}/HB 101.xml
      one XML record per bill
  .../billtext/html/... , .../fiscalnotes/html/...
      documents, linked from each bill's XML

The Council publishes these files specifically so automated users do not
scrape the Texas Legislature Online website.
"""
import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Iterable, Iterator, List, Optional, Tuple

from ..fetch import Fetcher
from ..models import (BILL_TYPES, Action, BillRef, CommitteeReferral, DocumentRef,
                      FloorVoteRef, NormalizedBill, Sponsor)
from .base import LegislativeProvider, ValidationError

DEFAULT_BASE = "ftp://ftp.legis.state.tx.us/bills"
# TLC timestamps carry no zone; they are Austin (Central) local time.
CENTRAL = ZoneInfo("America/Chicago")

_FOLDERS = {
    "HB": "house_bills", "SB": "senate_bills",
    "HJR": "house_joint_resolutions", "SJR": "senate_joint_resolutions",
    "HCR": "house_concurrent_resolutions", "SCR": "senate_concurrent_resolutions",
    "HR": "house_resolutions", "SR": "senate_resolutions",
}
_BILL_ATTR = re.compile(r"^(\d{2,3})\((R|\d)\) (HB|SB|HJR|SJR|HCR|SCR|HR|SR) (\d+)$")
_BILL_ID = re.compile(r"^(HB|SB|HJR|SJR|HCR|SCR|HR|SR) ?(\d+)$")
_FILE_IN_LISTING = re.compile(r"((?:HB|SB|HJR|SJR|HCR|SCR|HR|SR) \d+)\.xml\s*$", re.I)
_DIR_IN_LISTING = re.compile(r"<DIR>\s+(\S+)\s*$")
_VERSION_FROM_URL = re.compile(r"\d{5}([A-Z]{1,2})\.(?:HTM|PDF)$", re.I)
_RECORD_VOTE = re.compile(r"RV#\s*\d+", re.I)


def session_code(label: str) -> str:
    """'89(R)' -> '89R', '89(1)' -> '891'."""
    match = re.match(r"^(\d{2,3})\((R|\d)\)$", label)
    if not match:
        raise ValidationError(f"unrecognized session label {label!r}")
    return match.group(1) + match.group(2)


def parse_bill_id(text: str) -> Tuple[str, int]:
    match = _BILL_ID.match(text.strip().upper())
    if not match:
        raise ValueError(f"unrecognized bill identifier {text!r}")
    return match.group(1), int(match.group(2))


def range_folder(bill_type: str, number: int) -> str:
    start = (number // 100) * 100 or 1
    end = (number // 100) * 100 + 99
    width = 5
    return f"{bill_type}{start:0{width}d}_{bill_type}{end:0{width}d}"


def _parse_date(text: Optional[str]) -> Optional[date]:
    text = (text or "").strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"unrecognized date {text!r}")


def _parse_timestamp(text: Optional[str]) -> Optional[datetime]:
    text = (text or "").strip()
    if not text:
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=CENTRAL)
        except ValueError:
            continue
    raise ValidationError(f"unrecognized timestamp {text!r}")


def _split_names(text: Optional[str]) -> List[str]:
    return [name.strip() for name in (text or "").split("|") if name.strip()]


def _actor(code: Optional[str]) -> str:
    prefix = (code or "")[:1].upper()
    return {"H": "house", "S": "senate", "E": "executive"}.get(prefix, "other")


def official_history_url(ref: BillRef) -> str:
    return ("https://capitol.texas.gov/BillLookup/History.aspx?"
            + urllib.parse.urlencode({"LegSess": ref.session_id, "Bill": f"{ref.bill_type}{ref.bill_number}"}))


def _https(url: Optional[str]) -> Optional[str]:
    if url and url.startswith("http://capitol.texas.gov/"):
        return "https://" + url[len("http://"):]
    return url or None


def parse_bill_xml(raw: bytes, source_url: str, expected: Optional[BillRef] = None) -> NormalizedBill:
    """Validate and normalize one TLC bill history XML document."""
    try:
        root = ET.fromstring(raw.decode("utf-8-sig"))
    except (ET.ParseError, UnicodeDecodeError) as error:
        raise ValidationError(f"malformed XML: {error}") from error
    if root.tag != "billhistory":
        raise ValidationError(f"unexpected root element <{root.tag}>")

    match = _BILL_ATTR.match(root.get("bill", "").strip())
    if not match:
        raise ValidationError(f"unrecognized bill attribute {root.get('bill')!r}")
    ref = BillRef(match.group(1) + match.group(2), match.group(3), int(match.group(4)))
    if expected and expected != ref:
        raise ValidationError(f"expected {expected} but file describes {ref}")

    caption_el = root.find("caption")
    caption = (caption_el.text or "").strip() if caption_el is not None else ""
    if not caption:
        raise ValidationError(f"{ref}: missing caption")

    # Sponsors. Authors/coauthors belong to the chamber of origin; sponsors
    # and cosponsors to the second chamber.
    origin = ref.chamber
    second = "senate" if origin == "house" else "house"
    sponsors: List[Sponsor] = []
    for tag, role, chamber in (("authors", "author", origin), ("coauthors", "coauthor", origin),
                               ("sponsors", "sponsor", second), ("cosponsors", "cosponsor", second)):
        for position, name in enumerate(_split_names(root.findtext(tag))):
            sponsors.append(Sponsor(name=name, role=role, chamber=chamber, position=position))

    committees: List[CommitteeReferral] = []
    for chamber in ("house", "senate"):
        el = root.find(f"committees/{chamber}")
        if el is not None and (el.get("name") or "").strip():
            committees.append(CommitteeReferral(
                chamber=chamber,
                name=el.get("name").strip(),
                status=(el.get("status") or "").strip() or None,
                ayes=int(el.get("ayeVotes") or 0),
                nays=int(el.get("nayVotes") or 0),
                present_not_voting=int(el.get("presentNotVotingVotes") or 0),
                absent=int(el.get("absentVotes") or 0),
            ))

    actions: List[Action] = []
    floor_votes: List[FloorVoteRef] = []
    previous_description = ""
    for sequence, el in enumerate(root.findall("actions/action")):
        description = (el.findtext("description") or "").strip()
        if not description:
            raise ValidationError(f"{ref}: action {sequence} has no description")
        code = (el.findtext("actionNumber") or "").strip() or None
        comment = (el.findtext("comment") or "").strip() or None
        action = Action(
            sequence=sequence,
            action_code=code,
            actor=_actor(code),
            action_date=_parse_date(el.findtext("date")),
            action_timestamp=_parse_timestamp(el.findtext("actionTimestamp")),
            description=description,
            comment=comment,
        )
        actions.append(action)
        if description.lower().startswith("record vote") and comment and _RECORD_VOTE.search(comment):
            if action.actor in ("house", "senate"):
                floor_votes.append(FloorVoteRef(
                    chamber=action.actor, vote_date=action.action_date,
                    reference=_RECORD_VOTE.search(comment).group(0).replace(" ", ""),
                    motion=previous_description or "Record vote"))
        previous_description = description

    documents: List[DocumentRef] = []
    for doc_tag, doc_type in (("bill", "bill_text"), ("analysis", "analysis"), ("fiscalNote", "fiscal_note")):
        for ordinal, el in enumerate(root.findall(f"billtext/docTypes/{doc_tag}/versions/version")):
            ftp_html = (el.findtext("FTPHTMLURL") or "").strip() or None
            web_html = _https((el.findtext("WebHTMLURL") or "").strip())
            web_pdf = _https((el.findtext("WebPDFURL") or "").strip())
            any_url = ftp_html or web_html or web_pdf or ""
            version = _VERSION_FROM_URL.search(any_url)
            if not version:
                raise ValidationError(f"{ref}: cannot determine version code from {any_url!r}")
            documents.append(DocumentRef(
                doc_type=doc_type,
                version_code=version.group(1).upper(),
                description=(el.findtext("versionDescription") or "").strip() or version.group(1),
                ordinal=ordinal,
                source_html_url=ftp_html,
                official_html_url=web_html,
                official_pdf_url=web_pdf,
            ))

    last_action_text = (root.findtext("lastaction") or "").strip() or None
    last_action_date = actions[-1].action_date if actions else None

    bill = NormalizedBill(
        ref=ref,
        caption=caption,
        caption_version=(caption_el.get("version") or None) if caption_el is not None else None,
        last_action_text=last_action_text,
        last_action_date=last_action_date,
        subjects=[(s.text or "").strip() for s in root.findall("subjects/subject") if (s.text or "").strip()],
        companions=(root.findtext("companions") or "").strip() or None,
        sponsors=sponsors,
        committees=committees,
        actions=actions,
        documents=documents,
        floor_votes=floor_votes,
        source_id=TlcFtpProvider.source_id,
        source_url=source_url,
        official_url=official_history_url(ref),
        source_updated_at=_parse_timestamp(root.get("lastUpdate")),
    )
    bill.content_hash = record_hash(bill)
    return bill


def record_hash(bill: NormalizedBill) -> str:
    """Hash of the normalized record, excluding fetch metadata."""
    payload = {
        "caption": bill.caption, "caption_version": bill.caption_version,
        "last_action": bill.last_action_text, "subjects": bill.subjects, "companions": bill.companions,
        "sponsors": [(s.name, s.role) for s in bill.sponsors],
        "committees": [(c.chamber, c.name, c.status, c.ayes, c.nays, c.present_not_voting, c.absent) for c in bill.committees],
        "actions": [(a.action_code, str(a.action_date), a.description, a.comment) for a in bill.actions],
        "documents": [(d.doc_type, d.version_code, d.description) for d in bill.documents],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def parse_listing(text: str) -> Tuple[List[str], List[str]]:
    """Parse a Windows-style FTP directory listing into (directories, bill ids)."""
    dirs, bills = [], []
    for line in text.splitlines():
        d = _DIR_IN_LISTING.search(line)
        if d:
            dirs.append(d.group(1))
            continue
        f = _FILE_IN_LISTING.search(line)
        if f:
            bills.append(f.group(1).upper())
    return dirs, bills


def parse_history_index(raw: bytes) -> List[Tuple[str, str, str]]:
    """Parse history.xml -> [(bill id, path, timestamp)]."""
    try:
        root = ET.fromstring(raw.decode("utf-8-sig"))
    except (ET.ParseError, UnicodeDecodeError) as error:
        raise ValidationError(f"malformed history index: {error}") from error
    return [(b.get("id", ""), b.get("path", ""), b.get("timestamp", "")) for b in root.findall("bill")]


class TlcFtpProvider(LegislativeProvider):
    source_id = "tlc_ftp"
    is_authoritative = True

    def __init__(self, fetcher: Fetcher, base_url: str = DEFAULT_BASE):
        self.fetcher = fetcher
        self.base_url = base_url.rstrip("/")

    def bill_url(self, ref: BillRef) -> str:
        name = urllib.parse.quote(f"{ref.bill_type} {ref.bill_number}.xml")
        return (f"{self.base_url}/{ref.session_id}/billhistory/{_FOLDERS[ref.bill_type]}/"
                f"{range_folder(ref.bill_type, ref.bill_number)}/{name}")

    def list_bills(self, session_id: str, bill_types: Optional[Iterable[str]] = None,
                   limit: Optional[int] = None) -> Iterator[BillRef]:
        count = 0
        for bill_type in (bill_types or BILL_TYPES):
            folder_url = f"{self.base_url}/{session_id}/billhistory/{_FOLDERS[bill_type]}/"
            dirs, _ = parse_listing(self.fetcher.get(folder_url).decode("utf-8", "replace"))
            # Each range folder is one "page" of up to 100 bills.
            for directory in sorted(d for d in dirs if d.upper().startswith(bill_type)):
                _, ids = parse_listing(self.fetcher.get(folder_url + directory + "/").decode("utf-8", "replace"))
                for bill_id in sorted(ids, key=lambda i: parse_bill_id(i)[1]):
                    bt, number = parse_bill_id(bill_id)
                    if bt != bill_type:
                        continue
                    yield BillRef(session_id, bt, number)
                    count += 1
                    if limit is not None and count >= limit:
                        return

    def list_changed_bills(self, session_id: str, since_cursor: Optional[str]) -> Tuple[List[BillRef], Optional[str]]:
        raw = self.fetcher.get(f"{self.base_url}/{session_id}/billhistory/history.xml")
        entries = parse_history_index(raw)
        refs: List[BillRef] = []
        newest = since_cursor
        since = _parse_timestamp(since_cursor) if since_cursor else None
        for bill_id, _path, stamp in entries:
            when = _parse_timestamp(stamp) if stamp else None
            if since and when and when <= since:
                continue
            try:
                bill_type, number = parse_bill_id(bill_id)
            except ValueError:
                continue
            refs.append(BillRef(session_id, bill_type, number))
            if when and (newest is None or when > _parse_timestamp(newest)):
                newest = when.strftime("%m/%d/%Y %I:%M:%S %p")
        return refs, newest

    def fetch_bill(self, ref: BillRef) -> NormalizedBill:
        url = self.bill_url(ref)
        return parse_bill_xml(self.fetcher.get(url), source_url=url, expected=ref)

    def fetch_document(self, url: str) -> bytes:
        return self.fetcher.get(url)
