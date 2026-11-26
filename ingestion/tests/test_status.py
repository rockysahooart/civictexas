"""Legislative status mapping. All action sequences here are SYNTHETIC."""
from datetime import date

import pytest

from civictexas_ingest.models import Action
from civictexas_ingest.status import STATUS_LABELS, derive_status


def acts(*rows):
    return [Action(sequence=i, action_code=None, actor=actor, action_date=date(2025, 3, 1 + i),
                   action_timestamp=None, description=text, comment=None)
            for i, (actor, text) in enumerate(rows)]


ONGOING = dict(session_end_date=None)


@pytest.mark.parametrize("bill_type, rows, expected", [
    ("HB", [("house", "Filed")], "filed"),
    ("HB", [("house", "Filed"), ("house", "Referred to Public Education")], "in_committee"),
    ("HB", [("house", "Referred to X"), ("house", "Reported favorably w/o amendment(s)")], "reported_from_committee"),
    ("HB", [("house", "Referred to X"), ("house", "Committee report sent to Calendars")], "reported_from_committee"),
    # Second reading is not final passage.
    ("HB", [("house", "Referred to X"), ("house", "Passed to engrossment")], "in_committee"),
    ("HB", [("house", "Passed to third reading")], "unknown"),
    ("HB", [("house", "Filed"), ("house", "Passed")], "passed_origin_chamber"),
    # Clerical 'Reported engrossed' is not a committee report.
    ("HB", [("house", "Passed"), ("house", "Reported engrossed")], "passed_origin_chamber"),
    ("HB", [("house", "Passed"), ("senate", "Referred to Finance")], "in_committee_second_chamber"),
    ("HB", [("house", "Passed"), ("senate", "Reported favorably as substituted")],
     "reported_from_committee_second_chamber"),
    ("HB", [("house", "Passed"), ("senate", "Passed")], "passed_both_chambers"),
    # Amended in the second chamber: not passed until the origin chamber agrees.
    ("HB", [("house", "Passed"), ("senate", "Passed as amended")], "amendments_pending"),
    ("HB", [("house", "Passed"), ("senate", "Passed as amended"),
            ("senate", "House concurs in Senate amendment(s)-reported")], "amendments_pending"),
    ("HB", [("house", "Passed"), ("senate", "Passed as amended"),
            ("house", "House concurs in Senate amendment(s)")], "passed_both_chambers"),
    ("HB", [("house", "Passed"), ("senate", "Passed as amended"),
            ("house", "House refuses to concur in Senate amendments"),
            ("house", "House adopts conference committee report")], "amendments_pending"),
    ("HB", [("house", "Passed"), ("senate", "Passed as amended"),
            ("house", "House adopts conference committee report"),
            ("senate", "Senate adopts conference committee report")], "passed_both_chambers"),
    ("SB", [("senate", "Passed"), ("house", "Passed as substituted")], "amendments_pending"),
    # Amended at second reading, so third reading is recorded as plain 'Passed'.
    ("HB", [("house", "Passed"), ("senate", "Passed"),
            ("house", "House refuses to concur in Senate amendments")], "amendments_pending"),
    ("HB", [("house", "Passed"), ("senate", "Passed"), ("house", "Senate passage as amended reported"),
            ("house", "House concurs in Senate amendment(s)")], "passed_both_chambers"),
    ("SB", [("senate", "Passed"), ("house", "Passed")], "passed_both_chambers"),
    ("SB", [("senate", "Passed"), ("house", "Passed"), ("executive", "Sent to the Governor")], "sent_to_governor"),
    ("SB", [("executive", "Sent to the Governor"), ("executive", "Signed by the Governor")], "signed"),
    ("SB", [("executive", "Sent to the Governor"), ("executive", "Vetoed by the Governor")], "vetoed"),
    ("SB", [("executive", "Filed without the Governor's signature")], "became_law_without_signature"),
    # Signed stays signed even if later clerical actions appear.
    ("HB", [("executive", "Signed by the Governor"), ("house", "Referred to X")], "signed"),
    ("HJR", [("house", "Passed"), ("senate", "Passed"), ("executive", "Filed with the Secretary of State")],
     "filed_with_secretary_of_state"),
    ("HR", [("house", "Filed"), ("house", "Adopted")], "adopted"),
    ("HCR", [("house", "Adopted"), ("senate", "Adopted")], "passed_both_chambers"),
    ("HB", [("house", "Something new and unrecognized")], "unknown"),
])
def test_status_mapping(bill_type, rows, expected):
    status, _ = derive_status(bill_type, acts(*rows), **ONGOING)
    assert status == expected
    assert status in STATUS_LABELS


def test_status_date_is_the_determining_action():
    status, when = derive_status("HB", acts(("house", "Filed"), ("house", "Referred to X")), **ONGOING)
    assert (status, when) == ("in_committee", date(2025, 3, 2))


def test_bills_die_when_session_ends():
    rows = acts(("house", "Filed"), ("house", "Referred to X"))
    status, when = derive_status("HB", rows, session_end_date=date(2025, 6, 2), today=date(2025, 7, 1))
    assert (status, when) == ("not_passed_session_ended", date(2025, 6, 2))


def test_session_still_running_does_not_kill_bills():
    rows = acts(("house", "Filed"))
    status, _ = derive_status("HB", rows, session_end_date=date(2025, 6, 2), today=date(2025, 5, 1))
    assert status == "filed"


@pytest.mark.parametrize("rows", [
    [("house", "Passed"), ("senate", "Passed")],
    [("executive", "Sent to the Governor")],
    [("executive", "Signed by the Governor")],
])
def test_finished_bills_are_not_marked_dead(rows):
    status, _ = derive_status("HB", acts(*rows), session_end_date=date(2025, 6, 2), today=date(2026, 1, 1))
    assert status != "not_passed_session_ended"


def test_bill_stuck_in_conference_dies_when_session_ends():
    rows = acts(("house", "Passed"), ("senate", "Passed as amended"),
                ("house", "House refuses to concur in Senate amendments"),
                ("house", "House requests conference committee"))
    status, _ = derive_status("HB", rows, session_end_date=date(2025, 6, 2), today=date(2025, 7, 1))
    assert status == "not_passed_session_ended"
