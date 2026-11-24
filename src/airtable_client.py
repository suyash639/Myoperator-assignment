"""Read-only Airtable REST client.

Safety properties (DEC-005):
  * GET is the only HTTP method that can reach the network (`_request` refuses anything else).
  * The token is read from the environment / .env only, held in a private attribute, and
    never appears in reprs, exception messages, or log records (all pass through `redact`).
  * Pagination follows `offset` until absent; a repeated offset or runaway page count is an error,
    never a silent stop.
  * Requests are spaced to <= `max_rps` (default 4/s; Airtable's limit is 5/s per base).
  * HTTP 429 -> fixed wait (default 30 s, per Airtable guidance), bounded retries.
  * Network errors / 5xx -> exponential backoff, bounded retries.
  * 401/403/404 fail fast (retrying cannot fix them).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Iterable
from urllib.parse import quote

import requests

API_ROOT = "https://api.airtable.com/v0"
PAGE_SIZE_MAX = 100

_PAT_RE = re.compile(r"pat[A-Za-z0-9]{14}\.[A-Za-z0-9]{64}")
_BEARER_RE = re.compile(r"(?i)(bearer\s+)[^\s'\"]+")
_BASE_ID_RE = re.compile(r"app[A-Za-z0-9]{14}")
REDACTED = "[REDACTED]"

log = logging.getLogger("airtable")


# --------------------------------------------------------------------------- errors
class AirtableError(Exception):
    """Base class. Messages are always redacted before construction."""


class ConfigError(AirtableError):
    pass


class AuthError(AirtableError):
    """401/403 — invalid, expired, revoked or under-scoped token."""


class NotFoundError(AirtableError):
    pass


class RetryExhaustedError(AirtableError):
    pass


class PaginationError(AirtableError):
    pass


class IteratorExpiredError(PaginationError):
    """Airtable LIST_RECORDS_ITERATOR_NOT_AVAILABLE — the offset chain expired; restart the table."""


class ReadOnlyViolation(AirtableError):
    pass


# --------------------------------------------------------------------------- redaction
def redact(text: object, secrets: Iterable[str] = ()) -> str:
    """Remove secrets, PAT-shaped strings and bearer values from any text."""
    s = str(text)
    for secret in secrets:
        if secret and len(secret) >= 8:
            s = s.replace(secret, REDACTED)
    s = _PAT_RE.sub(REDACTED, s)
    s = _BEARER_RE.sub(r"\1" + REDACTED, s)
    return s


class RedactingFilter(logging.Filter):
    """Attach to every log handler; rewrites the fully formatted message through `redact`."""

    def __init__(self, secrets: Iterable[str] = ()):
        super().__init__()
        self._secrets = tuple(secrets)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if record.exc_info:
            msg = msg + "\n" + logging.Formatter().formatException(record.exc_info)
            record.exc_info = None
            record.exc_text = None
        record.msg = redact(msg, self._secrets)
        record.args = ()
        return True


# --------------------------------------------------------------------------- config
def load_config(env_file: str | os.PathLike | None = ".env",
                environ: dict | None = None) -> tuple[str, str]:
    """Return (token, base_id). Process env takes precedence over the .env file.

    Error messages name missing/invalid variables but never echo their values.
    """
    environ = os.environ if environ is None else environ
    file_vals: dict = {}
    if env_file and Path(env_file).is_file():
        from dotenv import dotenv_values
        file_vals = {k: v for k, v in dotenv_values(env_file).items() if v is not None}

    def get(name: str) -> str:
        return (environ.get(name) or file_vals.get(name) or "").strip()

    token, base_id = get("AIRTABLE_TOKEN"), get("AIRTABLE_BASE_ID")
    missing = [n for n, v in (("AIRTABLE_TOKEN", token), ("AIRTABLE_BASE_ID", base_id)) if not v]
    if missing:
        raise ConfigError(f"Missing required environment variable(s): {', '.join(missing)}. "
                          f"Set them in the environment or in .env (see .env.example).")
    if not _BASE_ID_RE.fullmatch(base_id):
        raise ConfigError("AIRTABLE_BASE_ID is not a valid base ID (expected 'app' + 14 characters).")
    return token, base_id


def token_fingerprint(token: str) -> str:
    """Non-reversible 8-hex fingerprint so runs can be tied to a token without storing it."""
    return hashlib.sha256(token.encode()).hexdigest()[:8]


# --------------------------------------------------------------------------- rate limiting
class RateLimiter:
    """Enforces a minimum interval between requests (max_rps requests per second)."""

    def __init__(self, max_rps: float = 4.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        if max_rps <= 0 or max_rps > 5:
            raise ValueError("max_rps must be in (0, 5] — Airtable allows 5 req/s per base")
        self.min_interval = 1.0 / max_rps
        self._clock, self._sleep = clock, sleep
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            delay = self.min_interval - (now - self._last)
            if delay > 0:
                self._sleep(delay)
                now = self._clock()
        self._last = now


# --------------------------------------------------------------------------- results
@dataclass
class Page:
    raw: bytes            # exact response body bytes — never modified
    body: dict            # parsed view of `raw`, for control flow only
    sha256: str
    attempts: int


@dataclass
class TableExtract:
    table: str
    pages: list[Page] = field(default_factory=list)
    restarts: int = 0
    pagination_terminated: bool = False

    @property
    def record_count(self) -> int:
        return sum(len(p.body["records"]) for p in self.pages)

    @property
    def attempts_total(self) -> int:
        return sum(p.attempts for p in self.pages)

    def raw_bytes(self) -> bytes:
        """A JSON array whose elements are the untouched page bodies, byte-for-byte."""
        return b"[\n" + b",\n".join(p.raw for p in self.pages) + b"\n]\n"


# --------------------------------------------------------------------------- client
class AirtableClient:
    def __init__(self, token: str, base_id: str, *, session: requests.Session | None = None,
                 max_rps: float = 4.0, max_retries: int = 5, rate_limit_wait: float = 30.0,
                 backoff_base: float = 1.0, backoff_max: float = 30.0, timeout: float = 30.0,
                 max_pages: int = 10_000, max_table_restarts: int = 2,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        if not token or not base_id:
            raise ConfigError("token and base_id are required")
        self.__token = token
        self.base_id = base_id
        self._session = session or requests.Session()
        self._limiter = RateLimiter(max_rps, clock=clock, sleep=sleep)
        self._sleep = sleep
        self.max_retries = max_retries
        self.rate_limit_wait = rate_limit_wait
        self.backoff_base, self.backoff_max = backoff_base, backoff_max
        self.timeout = timeout
        self.max_pages = max_pages
        self.max_table_restarts = max_table_restarts
        self.request_count = 0

    def __repr__(self) -> str:
        return f"AirtableClient(base_id={self.base_id!r}, token={REDACTED})"

    __str__ = __repr__

    @property
    def secrets(self) -> tuple[str]:
        return (self.__token,)

    def _r(self, text: object) -> str:
        return redact(text, self.secrets)

    # -- transport ---------------------------------------------------------
    def _request(self, method: str, url: str, params: dict | None = None) -> requests.Response:
        if method.upper() != "GET":
            raise ReadOnlyViolation(f"Refusing HTTP {method.upper()}: this client is read-only (GET only).")
        self._limiter.wait()
        self.request_count += 1
        return self._session.request(
            "GET", url, params=params, timeout=self.timeout,
            headers={"Authorization": f"Bearer {self.__token}", "Accept": "application/json"},
        )

    def _backoff(self, attempt: int) -> float:
        return min(self.backoff_max, self.backoff_base * (2 ** (attempt - 1)))

    @staticmethod
    def _error_type(resp: requests.Response) -> str:
        try:
            err = resp.json().get("error")
            if isinstance(err, dict):
                return f"{err.get('type', '')}: {err.get('message', '')}".strip(": ")
            return str(err or "")
        except Exception:
            return ""

    def get_json(self, url: str, params: dict | None = None) -> tuple[bytes, dict, int]:
        """GET with bounded retries. Returns (raw_bytes, parsed_body, attempts)."""
        last_problem = "no attempt made"
        total_attempts = self.max_retries + 1
        for attempt in range(1, total_attempts + 1):
            try:
                resp = self._request("GET", url, params)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_problem = f"network error ({type(exc).__name__}): {self._r(exc)}"
                log.warning("GET %s attempt %d/%d failed: %s", url, attempt, total_attempts, last_problem)
                if attempt < total_attempts:
                    self._sleep(self._backoff(attempt))
                continue

            status = resp.status_code
            if status == 200:
                raw = resp.content
                try:
                    body = json.loads(raw)
                except ValueError:
                    last_problem = "HTTP 200 with unparseable JSON body"
                    log.warning("GET %s attempt %d/%d: %s", url, attempt, total_attempts, last_problem)
                    if attempt < total_attempts:
                        self._sleep(self._backoff(attempt))
                    continue
                return raw, body, attempt

            detail = self._r(self._error_type(resp))
            if status == 401:
                raise AuthError(f"HTTP 401 Unauthorized — token is invalid, expired or revoked. {detail}".strip())
            if status == 403:
                raise AuthError(f"HTTP 403 Forbidden — token lacks scope or access to this base/resource. {detail}".strip())
            if status == 404:
                raise NotFoundError(f"HTTP 404 Not Found — {url}. {detail}".strip())
            if status == 422 and "LIST_RECORDS_ITERATOR_NOT_AVAILABLE" in detail:
                raise IteratorExpiredError(f"Pagination iterator expired: {detail}")
            if status == 429:
                last_problem = f"HTTP 429 rate limited {detail}".strip()
                log.warning("GET %s attempt %d/%d: %s — waiting %.0fs",
                            url, attempt, total_attempts, last_problem, self.rate_limit_wait)
                if attempt < total_attempts:
                    self._sleep(self.rate_limit_wait)
                continue
            if 500 <= status < 600:
                last_problem = f"HTTP {status} server error {detail}".strip()
                log.warning("GET %s attempt %d/%d: %s", url, attempt, total_attempts, last_problem)
                if attempt < total_attempts:
                    self._sleep(self._backoff(attempt))
                continue
            raise AirtableError(f"HTTP {status} — {url}. {detail}".strip())

        raise RetryExhaustedError(self._r(
            f"GET {url} failed after {total_attempts} attempts; last error: {last_problem}"))

    # -- endpoints ---------------------------------------------------------
    def table_url(self, table: str) -> str:
        return f"{API_ROOT}/{self.base_id}/{quote(table, safe='')}"

    def iter_pages(self, table: str, page_size: int = PAGE_SIZE_MAX) -> Iterator[Page]:
        if not 1 <= page_size <= PAGE_SIZE_MAX:
            raise ValueError(f"page_size must be 1..{PAGE_SIZE_MAX}")
        url = self.table_url(table)
        offset: str | None = None
        seen: set[str] = set()
        n = 0
        while True:
            params = {"pageSize": page_size}
            if offset:
                params["offset"] = offset
            raw, body, attempts = self.get_json(url, params)
            records = body.get("records")
            if not isinstance(records, list):
                raise PaginationError(f"{table}: page {n + 1} has no 'records' list — malformed response")
            n += 1
            yield Page(raw=raw, body=body, sha256=hashlib.sha256(raw).hexdigest(), attempts=attempts)
            offset = body.get("offset")
            if not offset:
                return
            if offset in seen:
                raise PaginationError(f"{table}: offset repeated at page {n} — pagination loop")
            seen.add(offset)
            if n >= self.max_pages:
                raise PaginationError(f"{table}: exceeded max_pages={self.max_pages} with offset still present")

    def extract_table(self, table: str, page_size: int = PAGE_SIZE_MAX) -> TableExtract:
        """Fetch every page of a table. If the offset chain expires mid-way, restart the
        whole table (bounded) — partial chains are never stitched together."""
        restarts = 0
        while True:
            result = TableExtract(table=table, restarts=restarts)
            try:
                for page in self.iter_pages(table, page_size):
                    result.pages.append(page)
                    log.info("%s: page %d — %d records (attempts=%d)",
                             table, len(result.pages), len(page.body["records"]), page.attempts)
                result.pagination_terminated = True
                return result
            except IteratorExpiredError:
                restarts += 1
                if restarts > self.max_table_restarts:
                    raise
                log.warning("%s: iterator expired after %d pages — restarting table (%d/%d)",
                            table, len(result.pages), restarts, self.max_table_restarts)

    def whoami(self) -> dict:
        _, body, _ = self.get_json(f"{API_ROOT}/meta/whoami")
        return body

    def base_schema(self) -> tuple[bytes, dict]:
        raw, body, _ = self.get_json(f"{API_ROOT}/meta/bases/{self.base_id}/tables")
        return raw, body
