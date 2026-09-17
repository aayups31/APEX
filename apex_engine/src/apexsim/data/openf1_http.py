"""Bounded, sequential HTTP acquisition for OpenF1's public historical API."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from apexsim import __version__

BASE_URL = "https://api.openf1.org/v1"


@dataclass(frozen=True)
class DownloadPolicy:
    """Seconds and bytes; default spacing stays below 30 requests per minute."""

    spacing_s: float = 2.1
    timeout_s: float = 60.0
    max_attempts: int = 4
    max_retry_wait_s: float = 60.0
    max_response_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        for name, minimum in (("spacing_s", 2.0), ("timeout_s", 0.001), ("max_retry_wait_s", 0.0)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
                raise ValueError(f"{name} must be finite and >= {minimum}")
        for name in ("max_attempts", "max_response_bytes"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")


class OpenF1Client:
    """Record successful response bodies and the attempt history; never follow redirects."""

    def __init__(self, policy: DownloadPolicy) -> None:
        self.policy = policy
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"APEX/{__version__} (historical research archive)",
                                     "Accept": "application/json"})
        self._last_start: float | None = None

    def close(self) -> None:
        self.session.close()

    def _retry_delay(self, value: str | None, attempt: int) -> float:
        delay = min(2.0 ** attempt, self.policy.max_retry_wait_s)
        if value:
            try:
                delay = float(value)
            except ValueError:
                try:
                    delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError) as exc:
                    raise ValueError("Invalid OpenF1 Retry-After header") from exc
            if not math.isfinite(delay) or delay > self.policy.max_retry_wait_s:
                raise RuntimeError("OpenF1 Retry-After exceeds the bounded wait; retry acquisition later")
        return max(0.0, delay)

    def get(self, endpoint: str, query: dict[str, int]) -> tuple[bytes, dict]:
        """Return decompressed HTTP body bytes, status, safe headers and attempt metadata.

        Timeouts/connection failures, 429 and 5xx get bounded retries. Other statuses
        are returned to the archive decoder, which distinguishes explicit empty results.
        """
        attempts = []
        for attempt in range(1, self.policy.max_attempts + 1):
            if self._last_start is not None:
                time.sleep(max(0.0, self.policy.spacing_s - (time.monotonic() - self._last_start)))
            self._last_start = time.monotonic()
            started = datetime.now(timezone.utc).isoformat()
            retry_after = None
            try:
                with self.session.get(f"{BASE_URL}/{endpoint}", params=query, stream=True,
                                      timeout=(10, self.policy.timeout_s), allow_redirects=False) as response:
                    entry = {"started_at_utc": started, "status_code": response.status_code}
                    attempts.append(entry)
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        retry_after = response.headers.get("Retry-After")
                    else:
                        body = bytearray()
                        for chunk in response.iter_content(chunk_size=65536):
                            body.extend(chunk)
                            if len(body) > self.policy.max_response_bytes:
                                raise ValueError(f"OpenF1 {endpoint} response exceeds byte limit")
                        return bytes(body), {"status_code": response.status_code,
                                             "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                                             "headers": {key.lower(): value for key, value in response.headers.items()
                                                         if key.lower() in {"content-type", "etag", "last-modified"}},
                                             "attempts": attempts}
            except (requests.Timeout, requests.ConnectionError) as exc:
                attempts.append({"started_at_utc": started, "error": type(exc).__name__})
            if attempt < self.policy.max_attempts:
                delay = self._retry_delay(retry_after, attempt)
                attempts[-1]["retry_wait_s"] = delay
                time.sleep(delay)
        raise RuntimeError(f"OpenF1 {endpoint} failed after {self.policy.max_attempts} attempts: {attempts}")
