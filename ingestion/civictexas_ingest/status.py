"""Map official action histories to a normalized legislative status.

The status is derived only from actions recorded in the official history. It
never guesses: if no rule matches, the status is 'unknown'.

Rules (Texas Legislature):
- Bills and concurrent resolutions pass the chamber of origin, then the second
  chamber, then go to the Governor.
- Joint resolutions (HJR/SJR, constitutional amendments) do not go to the
  Governor; after passing both chambers they are filed with the Secretary of
  State and go to voters.
- Simple resolutions (HR/SR) are adopted by one chamber.
- When a session ends, bills that had not passed both chambers are dead.
"""
import re
from datetime import date
from typing import Iterable, Optional, Tuple

from .models import Action

STATUS_LABELS = {
    "filed": "Filed",
    "in_committee": "In committee",
    "reported_from_committee": "Reported from committee",
    "passed_origin_chamber": "Passed chamber of origin",
    "in_committee_second_chamber": "In committee (second chamber)",
    "reported_from_committee_second_chamber": "Reported from committee (second chamber)",
    "amendments_pending": "Passed both chambers in different versions",
    "passed_both_chambers": "Passed both chambers",
    "sent_to_governor": "Sent to the Governor",
    "signed": "Signed by the Governor",
    "vetoed": "Vetoed by the Governor",
    "became_law_without_signature": "Became law without signature",
    "adopted": "Adopted",
    "filed_with_secretary_of_state": "Filed with the Secretary of State",
    "not_passed_session_ended": "Did not pass (session ended)",
    "unknown": "Unknown",
}

# Progression order. Terminal outcomes are handled separately.
_RANK = {
    "unknown": 0,
    "filed": 1,
    "in_committee": 2,
    "reported_from_committee": 3,
    "passed_origin_chamber": 4,
    "in_committee_second_chamber": 5,
    "reported_from_committee_second_chamber": 6,
    "amendments_pending": 7,
    "passed_both_chambers": 8,
    "sent_to_governor": 9,
}
_TERMINAL = {"signed", "vetoed", "became_law_without_signature", "adopted", "filed_with_secretary_of_state"}

_RE_FILED = re.compile(r"^Filed$", re.I)
_RE_REFERRED = re.compile(r"^Referred to ", re.I)
# Committee reports. Note: 'Reported engrossed' / 'Reported enrolled' are
# clerical steps, not committee reports, and are intentionally not matched.
_RE_REPORTED = re.compile(r"^(Reported (favorably|from committee|w/o|without|with|as substituted|adversely))|^Committee report", re.I)
# Final passage. 'Passed to engrossment' / 'Passed to third reading' are
# second-reading steps, not final passage. Resolutions are 'Adopted'.
_RE_PASSAGE = re.compile(r"^(Passed|Adopted)(?! to)(?P<amended> as (amended|substituted))?", re.I)
# Agreement on the final text after the second chamber amended the bill.
# '-reported' entries are the other chamber's notice of the same event.
_RE_CONCURS = re.compile(r"^(House|Senate) concurs in (House|Senate) amendment(?!.*-reported)", re.I)
# Evidence that the second chamber changed the bill. The second chamber's
# final vote is often recorded as plain 'Passed' when amendments were adopted
# at second reading, so the passage line alone is not enough.
_RE_AMENDED_EVIDENCE = re.compile(
    r"passage as amended|amendments distributed|refuses to concur|requests conference committee"
    r"|concurs in (House|Senate) amendment", re.I)
_RE_CONF_ADOPTED = re.compile(r"^(House|Senate) adopts conf(erence|\.) comm(ittee|\.) report(?!.*-reported)", re.I)
_RE_SENT_TO_GOVERNOR = re.compile(r"^Sent to the Governor", re.I)
_RE_SIGNED = re.compile(r"^Signed by the Governor", re.I)
_RE_VETOED = re.compile(r"^Vetoed by the Governor", re.I)
_RE_NO_SIGNATURE = re.compile(r"^Filed without the Governor'?s signature", re.I)
_RE_SOS = re.compile(r"^Filed with the Secretary of State", re.I)


def derive_status(
    bill_type: str,
    actions: Iterable[Action],
    session_end_date: Optional[date] = None,
    today: Optional[date] = None,
) -> Tuple[str, Optional[date]]:
    """Return (status, date of the action that determined it)."""
    origin = "house" if bill_type.startswith("H") else "senate"
    second = "senate" if origin == "house" else "house"
    is_simple_resolution = bill_type in ("HR", "SR")
    is_joint_resolution = bill_type in ("HJR", "SJR")

    status, status_date = "unknown", None
    conference_adopted = set()
    actions = list(actions)
    amended_in_second_chamber = any(_RE_AMENDED_EVIDENCE.search(a.description) for a in actions)

    def advance(candidate: str, when: Optional[date]) -> None:
        nonlocal status, status_date
        if status in _TERMINAL:
            return
        if candidate in _TERMINAL or _RANK[candidate] >= _RANK.get(status, 0):
            status, status_date = candidate, when

    for action in actions:
        text = action.description.strip()
        actor = action.actor
        when = action.action_date

        if _RE_SIGNED.match(text):
            advance("signed", when)
        elif _RE_VETOED.match(text):
            advance("vetoed", when)
        elif _RE_NO_SIGNATURE.match(text):
            advance("became_law_without_signature", when)
        elif _RE_SOS.match(text) and is_joint_resolution:
            advance("filed_with_secretary_of_state", when)
        elif _RE_SENT_TO_GOVERNOR.match(text):
            advance("sent_to_governor", when)
        elif _RE_FILED.match(text):
            advance("filed", when)
        elif _RE_REFERRED.match(text):
            advance("in_committee" if actor == origin else "in_committee_second_chamber", when)
        elif _RE_REPORTED.match(text):
            advance("reported_from_committee" if actor == origin else "reported_from_committee_second_chamber", when)
        elif _RE_CONCURS.match(text) and actor == origin:
            advance("passed_both_chambers", when)
        elif _RE_CONF_ADOPTED.match(text) and actor in ("house", "senate"):
            conference_adopted.add(actor)
            if conference_adopted == {"house", "senate"}:
                advance("passed_both_chambers", when)
        elif _RE_PASSAGE.match(text):
            amended = bool(_RE_PASSAGE.match(text).group("amended"))
            if is_simple_resolution:
                if actor == origin:
                    advance("adopted", when)
            elif actor == origin:
                advance("passed_origin_chamber", when)
            elif actor == second:
                # Amended in the second chamber: the origin chamber must agree
                # (or a conference report must be adopted) before it has passed.
                needs_agreement = amended or amended_in_second_chamber
                advance("amendments_pending" if needs_agreement else "passed_both_chambers", when)

    today = today or date.today()
    session_over = session_end_date is not None and today > session_end_date
    if session_over and status not in _TERMINAL:
        finished = status in ("passed_both_chambers", "sent_to_governor")
        if not finished:
            status = "not_passed_session_ended"
            status_date = session_end_date

    return status, status_date
