from datetime import date
from pathlib import Path

import pytest

from civictexas_ingest.models import BillRef
from civictexas_ingest.providers.base import ValidationError
from civictexas_ingest.providers.tlc_ftp import (TlcFtpProvider, parse_bill_id, parse_bill_xml,
                                                 parse_history_index, parse_listing, range_folder,
                                                 session_code)
from civictexas_ingest.status import derive_status

OFFICIAL = Path(__file__).parent / "fixtures" / "official"


def load(name: str) -> bytes:
    return (OFFICIAL / name).read_bytes()


# --- official records ---------------------------------------------------------

def test_parses_enrolled_bill_with_full_history():
    bill = parse_bill_xml(load("89R_HB_2.xml"), source_url="ftp://example/HB 2.xml")
    assert bill.ref == BillRef("89R", "HB", 2)
    assert bill.caption == "Relating to public education and public school finance."
    assert bill.caption_version == "Enrolled"
    assert [s.name for s in bill.sponsors if s.role == "author"] == ["Buckley", "Bernal", "Guillen"]
    assert all(s.chamber == "house" for s in bill.sponsors if s.role in ("author", "coauthor"))
    assert [s.name for s in bill.sponsors if s.role == "sponsor"] == ["Creighton"]
    assert all(s.chamber == "senate" for s in bill.sponsors if s.role in ("sponsor", "cosponsor"))

    house = next(c for c in bill.committees if c.chamber == "house")
    assert (house.name, house.ayes, house.nays) == ("Public Education", 13, 2)

    versions = [d.version_code for d in bill.documents if d.doc_type == "bill_text"]
    assert versions == ["I", "H", "E", "S", "F"]
    fiscal = [d.version_code for d in bill.documents if d.doc_type == "fiscal_note"]
    assert fiscal == ["I", "H", "E", "S", "F"]
    assert all(d.official_html_url.startswith("https://capitol.texas.gov/") for d in bill.documents)

    assert any(v.reference == "RV#4015" and v.chamber == "house" for v in bill.floor_votes)
    assert bill.actions[0].description == "Filed"
    assert bill.actions[-1].actor == "executive"
    assert bill.source_updated_at.isoformat().startswith("2025-06-23T02:00:05")
    assert bill.official_url == "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB2"


def test_enrolled_bill_status_is_signed():
    bill = parse_bill_xml(load("89R_HB_2.xml"), source_url="x")
    status, when = derive_status("HB", bill.actions, session_end_date=date(2025, 6, 2), today=date(2026, 11, 26))
    assert status == "signed"
    assert when is not None


def test_bill_that_died_in_conference():
    # 89R HB 4: the Senate amended it, the House refused to concur, and the
    # conference committee never reported before the session ended.
    bill = parse_bill_xml(load("89R_HB_4.xml"), source_url="x")
    assert derive_status("HB", bill.actions, session_end_date=None)[0] == "amendments_pending"
    status, when = derive_status("HB", bill.actions, session_end_date=date(2025, 6, 2), today=date(2026, 11, 26))
    assert (status, when) == ("not_passed_session_ended", date(2025, 6, 2))


def test_parses_prefiled_bill():
    bill = parse_bill_xml(load("90R_HB_101.xml"), source_url="x")
    assert bill.ref == BillRef("90R", "HB", 101)
    assert bill.companions.startswith("SB 31 by Zaffirini")
    assert len(bill.subjects) == 3
    assert [d.version_code for d in bill.documents] == ["I"]
    status, _ = derive_status("HB", bill.actions, session_end_date=None)
    assert status == "filed"


def test_content_hash_is_stable_and_sensitive():
    a = parse_bill_xml(load("90R_HB_101.xml"), source_url="x")
    b = parse_bill_xml(load("90R_HB_101.xml"), source_url="different-url")
    assert a.content_hash == b.content_hash
    changed = load("90R_HB_101.xml").replace(b"<description>Filed</description>",
                                             b"<description>Referred to Health</description>")
    assert parse_bill_xml(changed, source_url="x").content_hash != a.content_hash


def test_history_index_and_listing():
    entries = parse_history_index(load("90R_history.xml"))
    assert entries[0][0] == "HB 1282"
    dirs, bills = parse_listing(load("90R_senate_SB00001_SB00099_listing.txt").decode())
    assert dirs == []
    assert "SB 31" in bills


# --- validation (SYNTHETIC inputs) --------------------------------------------

@pytest.mark.parametrize("raw, message", [
    (b"<notabill/>", "unexpected root"),
    (b"<billhistory bill='garbage'><caption>x</caption></billhistory>", "unrecognized bill"),
    (b"<billhistory bill='90(R) HB 1'><caption></caption></billhistory>", "missing caption"),
    (b"<billhistory bill='90(R) HB 1'", "malformed XML"),
])
def test_rejects_invalid_records(raw, message):
    with pytest.raises(ValidationError, match=message):
        parse_bill_xml(raw, source_url="x")


def test_rejects_record_for_wrong_bill():
    with pytest.raises(ValidationError, match="expected"):
        parse_bill_xml(load("90R_HB_101.xml"), source_url="x", expected=BillRef("90R", "HB", 102))


# --- helpers ------------------------------------------------------------------

def test_identifiers_and_paths():
    assert session_code("89(R)") == "89R"
    assert session_code("89(2)") == "892"
    assert parse_bill_id("hb101") == ("HB", 101)
    assert parse_bill_id("HJR 1") == ("HJR", 1)
    assert range_folder("HB", 1) == "HB00001_HB00099"
    assert range_folder("HB", 101) == "HB00100_HB00199"
    assert range_folder("SB", 2500) == "SB02500_SB02599"
    provider = TlcFtpProvider(fetcher=None, base_url="ftp://host/bills")
    assert provider.bill_url(BillRef("90R", "HB", 101)) == \
        "ftp://host/bills/90R/billhistory/house_bills/HB00100_HB00199/HB%20101.xml"
