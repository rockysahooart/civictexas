"""Polite fetching with rate limiting and retries.

Works for ftp:// and https:// URLs using only the standard library.
"""
import logging
import random
import time
import urllib.error
import urllib.request
from typing import Callable, Optional

log = logging.getLogger(__name__)

USER_AGENT = "CivicTexasIngest/0.1 (+https://github.com/rockysahooart/civictexas)"


class FetchError(Exception):
    """Raised when a resource could not be fetched after all retries."""


class PermanentFetchError(FetchError):
    """Raised for errors that retrying will not fix (e.g. 404 / missing file)."""


def _default_opener(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


class Fetcher:
    """Fetches URLs one at a time with a minimum gap between requests.

    - `min_interval` seconds are left between the start of consecutive requests
      so we never hammer a government server.
    - Transient failures are retried with exponential backoff and jitter.
    - HTTP 404 / FTP "file not found" responses are not retried.
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        timeout: float = 60.0,
        opener: Optional[Callable[[str, float], bytes]] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self._open = opener or _default_opener
        self._sleep = sleep
        self._clock = clock
        self._last_request: Optional[float] = None
        self.request_count = 0

    def _wait_for_slot(self) -> None:
        if self._last_request is not None:
            elapsed = self._clock() - self._last_request
            if elapsed < self.min_interval:
                self._sleep(self.min_interval - elapsed)
        self._last_request = self._clock()

    @staticmethod
    def _is_permanent(error: Exception) -> bool:
        if isinstance(error, urllib.error.HTTPError):
            return error.code in (400, 401, 403, 404, 410)
        message = str(error)
        # FTP: "550 The system cannot find the file specified."
        return "550" in message and isinstance(error, urllib.error.URLError)

    def get(self, url: str) -> bytes:
        attempt = 0
        while True:
            self._wait_for_slot()
            self.request_count += 1
            try:
                return self._open(url, self.timeout)
            except Exception as error:  # noqa: BLE001 - classify below
                if self._is_permanent(error):
                    raise PermanentFetchError(f"{url}: {error}") from error
                if attempt >= self.max_retries:
                    raise FetchError(f"{url}: failed after {attempt + 1} attempts: {error}") from error
                delay = self.backoff_base ** attempt + random.uniform(0, 0.5)
                log.warning("fetch failed (%s), retrying in %.1fs: %s", error, delay, url)
                self._sleep(delay)
                attempt += 1
