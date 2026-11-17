"""A small, polite HTTP client shared by every source.

* Sequential requests, at least ``min_interval`` seconds apart per host.
* Descriptive, generic User-Agent (no personal data).
* Timeouts, and retries with exponential backoff on network errors, 429 and 5xx
  (``Retry-After`` is honoured, capped).
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlsplit

import httpx

from . import __version__

log = logging.getLogger(__name__)

USER_AGENT = f"radar-energia/{__version__} (+https://github.com/BEG-lag/radar-energia)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    """A source could not be read; callers log it and keep going."""


class PoliteClient:
    def __init__(
        self,
        *,
        min_interval: float = 1.0,
        timeout: float = 30.0,
        retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.min_interval = min_interval
        self.retries = retries
        self._last: dict[str, float] = {}
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            delay = self.min_interval - (time.monotonic() - last)
            if delay > 0:
                time.sleep(delay)
        self._last[host] = time.monotonic()

    def get(self, url: str, *, accept: str = "*/*") -> httpx.Response:
        host = urlsplit(url).netloc
        error: Exception | None = None
        for attempt in range(self.retries + 1):
            self._wait(host)
            try:
                response = self._client.get(url, headers={"Accept": accept})
            except httpx.HTTPError as exc:
                error = exc
                log.warning("GET %s failed (%s), attempt %d", url, exc, attempt + 1)
            else:
                if response.status_code not in RETRY_STATUS:
                    return response
                error = FetchError(f"HTTP {response.status_code} for {url}")
                log.warning("GET %s returned %d, attempt %d", url, response.status_code, attempt + 1)
                retry_after = response.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    time.sleep(min(int(retry_after), 60))
            if attempt < self.retries:
                time.sleep(min(2**attempt * 2, 30))
        raise FetchError(f"Giving up on {url}: {error}")

    def get_ok(self, url: str, *, accept: str = "*/*") -> httpx.Response:
        response = self.get(url, accept=accept)
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} for {url}")
        return response
