import urllib.error
from pathlib import Path

import pytest

from civictexas_ingest.fetch import Fetcher, FetchError, PermanentFetchError
from civictexas_ingest.text import decode_html, html_to_text

OFFICIAL = Path(__file__).parent / "fixtures" / "official"


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))
        self.now += seconds


def test_rate_limit_spaces_requests():
    clock = FakeClock()
    fetcher = Fetcher(min_interval=1.0, opener=lambda url, t: b"ok", sleep=clock.sleep, clock=clock.time)
    for _ in range(3):
        fetcher.get("ftp://x")
    assert clock.sleeps == [1.0, 1.0]


def test_retries_transient_errors_then_succeeds():
    clock = FakeClock()
    calls = []

    def flaky(url, timeout):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.URLError("timed out")
        return b"data"

    fetcher = Fetcher(min_interval=0, max_retries=3, opener=flaky, sleep=clock.sleep, clock=clock.time)
    assert fetcher.get("ftp://x") == b"data"
    assert len(calls) == 3


def test_gives_up_after_max_retries():
    clock = FakeClock()

    def broken(url, timeout):
        raise urllib.error.URLError("connection reset")

    fetcher = Fetcher(min_interval=0, max_retries=2, opener=broken, sleep=clock.sleep, clock=clock.time)
    with pytest.raises(FetchError, match="3 attempts"):
        fetcher.get("ftp://x")


def test_missing_files_are_not_retried():
    clock = FakeClock()
    calls = []

    def missing(url, timeout):
        calls.append(url)
        raise urllib.error.URLError("ftp error: error_perm('550 The system cannot find the file specified.')")

    fetcher = Fetcher(min_interval=0, max_retries=3, opener=missing, sleep=clock.sleep, clock=clock.time)
    with pytest.raises(PermanentFetchError):
        fetcher.get("ftp://x")
    assert len(calls) == 1


def test_official_bill_text_extraction():
    text = html_to_text(decode_html((OFFICIAL / "90R_HB00101I.htm").read_bytes()))
    assert "BE IT ENACTED BY THE LEGISLATURE OF THE STATE OF TEXAS:" in text
    assert "SECTION 1." in text
    assert "{+Sec. 32.351. EXPANDED ELIGIBILITY FOR MEDICAL ASSISTANCE +}" in text
    assert "<" not in text


def test_amendment_markup_is_preserved():  # SYNTHETIC HTML
    html = "<p>Sec. 1. A person <s>may</s><u>shall</u> file a report.</p>"
    assert html_to_text(html) == "Sec. 1. A person [-may-]{+shall+} file a report."
