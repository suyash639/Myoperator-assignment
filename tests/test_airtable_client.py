"""Offline tests for the read-only Airtable client and extraction pipeline.
No test touches the network: a FakeSession stands in for requests.Session, and sleep/clock
are injected so 30-second waits are asserted rather than performed."""
from __future__ import annotations

import json
import logging

import pytest
import requests

from src.airtable_client import (REDACTED, AirtableClient, AuthError, ConfigError, PaginationError,
                                 RateLimiter, ReadOnlyViolation, RedactingFilter, RetryExhaustedError,
                                 load_config, redact)
from src import extract, validate_extraction

TOKEN = "pat" + "A1b2C3d4E5f6G7" + "." + "0123456789abcdef" * 4      # PAT-shaped, fake
BASE = "appTESTBASE000001"


# --------------------------------------------------------------------------- fakes
class FakeResponse:
    def __init__(self, status: int, body: dict | bytes | None = None):
        self.status_code = status
        self.content = body if isinstance(body, bytes) else json.dumps(body or {}).encode()

    def json(self):
        return json.loads(self.content)


class FakeSession:
    """Pops scripted responses (or exceptions) per call; records every call."""

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []

    def request(self, method, url, params=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "params": dict(params or {}), "headers": headers})
        item = self.script.pop(0)
        if callable(item):
            item = item(url, params)
        if isinstance(item, BaseException):
            raise item
        return item


def recs(n, start=0):
    return [{"id": f"rec{start + i:014d}", "createdTime": "2026-01-01T00:00:00.000Z", "fields": {"n": start + i}}
            for i in range(n)]


def page(n, start=0, offset=None):
    body = {"records": recs(n, start)}
    if offset:
        body["offset"] = offset
    return FakeResponse(200, body)


class Sleeps(list):
    def __call__(self, s):
        self.append(s)


def client(script, **kw):
    sleeps = Sleeps()
    c = AirtableClient(TOKEN, BASE, session=FakeSession(script), sleep=sleeps, clock=lambda: 0.0, **kw)
    return c, c._session, sleeps


# --------------------------------------------------------------------------- pagination
def test_pagination_follows_offset_across_multiple_pages():
    c, s, _ = client([page(100, 0, "itrA/rec1"), page(100, 100, "itrB/rec2"), page(37, 200)])
    res = c.extract_table("Job Openings")
    assert len(res.pages) == 3 and res.record_count == 237 and res.pagination_terminated
    assert [call["params"].get("offset") for call in s.calls] == [None, "itrA/rec1", "itrB/rec2"]
    assert all(call["params"]["pageSize"] == 100 for call in s.calls)
    assert s.calls[0]["url"].endswith(f"/{BASE}/Job%20Openings")
    # raw bytes: valid JSON array whose elements are the untouched page bodies
    parsed = json.loads(res.raw_bytes())
    assert [len(p["records"]) for p in parsed] == [100, 100, 37]
    for p, raw in zip(res.pages, [x.content for x in [page(100, 0, "itrA/rec1"), page(100, 100, "itrB/rec2"), page(37, 200)]]):
        assert p.raw == raw


def test_exactly_100_records_does_not_stop_early_when_offset_present():
    c, s, _ = client([page(100, 0, "next"), page(0)])
    res = c.extract_table("People")
    assert res.record_count == 100 and len(res.pages) == 2 and len(s.calls) == 2


def test_empty_table():
    c, s, _ = client([page(0)])
    res = c.extract_table("Findings")
    assert res.record_count == 0 and len(res.pages) == 1 and res.pagination_terminated
    assert json.loads(res.raw_bytes()) == [{"records": []}]


def test_repeated_offset_is_an_error_not_a_silent_stop():
    c, _, _ = client([page(100, 0, "same"), page(100, 100, "same")])
    with pytest.raises(PaginationError, match="repeated"):
        c.extract_table("People")


def test_malformed_page_raises():
    c, _, _ = client([FakeResponse(200, {"oops": 1})])
    with pytest.raises(PaginationError, match="malformed"):
        c.extract_table("People")


def test_expired_iterator_restarts_whole_table_not_stitched():
    expired = FakeResponse(422, {"error": {"type": "LIST_RECORDS_ITERATOR_NOT_AVAILABLE", "message": "x"}})
    c, s, _ = client([page(100, 0, "o1"), expired, page(100, 0, "o2"), page(5, 100)])
    res = c.extract_table("Candidates")
    assert res.restarts == 1 and res.record_count == 105 and len(res.pages) == 2


# --------------------------------------------------------------------------- 429 / retries
def test_429_waits_30_seconds_then_succeeds():
    c, s, sleeps = client([FakeResponse(429, {"errors": "rate"}), page(3)])
    res = c.extract_table("Offers")
    assert res.record_count == 3 and res.pages[0].attempts == 2
    assert 30.0 in sleeps


def test_429_retries_are_bounded():
    c, s, sleeps = client([FakeResponse(429)] * 4, max_retries=3)
    with pytest.raises(RetryExhaustedError, match="4 attempts.*429"):
        c.extract_table("Offers")
    assert len(s.calls) == 4 and sleeps.count(30.0) == 3


def test_server_error_backoff_then_success():
    c, _, sleeps = client([FakeResponse(503), FakeResponse(500), page(2)])
    assert c.extract_table("Offers").record_count == 2
    # frozen fake clock => rate-limiter spacing sleeps (0.25 s) are interleaved; isolate backoff sleeps
    assert [x for x in sleeps if x != 0.25] == [1.0, 2.0]


# --------------------------------------------------------------------------- network failure
def test_transient_network_failure_recovers():
    c, _, _ = client([requests.ConnectionError("reset"), requests.Timeout("slow"), page(4)])
    assert c.extract_table("Interviews").record_count == 4


def test_persistent_network_failure_reports_clearly():
    c, s, _ = client([requests.ConnectionError("Name or service not known")] * 3, max_retries=2)
    with pytest.raises(RetryExhaustedError) as ei:
        c.extract_table("Interviews")
    msg = str(ei.value)
    assert "3 attempts" in msg and "ConnectionError" in msg and "Interviews" in msg


# --------------------------------------------------------------------------- credentials
def test_invalid_credentials_fail_fast_without_retry():
    c, s, sleeps = client([FakeResponse(401, {"error": {"type": "AUTHENTICATION_REQUIRED", "message": "bad"}})])
    with pytest.raises(AuthError, match="401"):
        c.extract_table("People")
    assert len(s.calls) == 1 and sleeps == []


def test_forbidden_fails_fast():
    c, s, _ = client([FakeResponse(403, {"error": {"type": "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND"}})])
    with pytest.raises(AuthError, match="403"):
        c.base_schema()
    assert len(s.calls) == 1


def test_missing_environment_variables(tmp_path):
    with pytest.raises(ConfigError, match="AIRTABLE_TOKEN, AIRTABLE_BASE_ID"):
        load_config(env_file=tmp_path / "nope.env", environ={})
    with pytest.raises(ConfigError, match="AIRTABLE_BASE_ID"):
        load_config(env_file=None, environ={"AIRTABLE_TOKEN": TOKEN})


def test_env_file_loaded_and_bad_base_id_message_hides_value(tmp_path):
    f = tmp_path / ".env"
    f.write_text(f"AIRTABLE_TOKEN={TOKEN}\nAIRTABLE_BASE_ID={BASE}\n")
    assert load_config(env_file=f, environ={}) == (TOKEN, BASE)
    with pytest.raises(ConfigError) as ei:
        load_config(env_file=None, environ={"AIRTABLE_TOKEN": TOKEN, "AIRTABLE_BASE_ID": "SECRETISHVALUE"})
    assert "SECRETISHVALUE" not in str(ei.value)


# --------------------------------------------------------------------------- redaction
def test_redact_removes_token_bearer_and_pat_shapes():
    other_pat = "pat" + "Z" * 14 + "." + "f" * 64
    s = redact(f"tok={TOKEN} hdr=Authorization: Bearer abc.def other={other_pat}", (TOKEN,))
    assert TOKEN not in s and other_pat not in s and "abc.def" not in s and s.count(REDACTED) == 3


def test_token_absent_from_repr_errors_and_logs(caplog):
    # error body and network exception both echo the token back
    echo = FakeResponse(500, {"error": {"type": "SERVER", "message": f"Bearer {TOKEN}"}})
    c, s, _ = client([echo, requests.ConnectionError(f"failed with Authorization: Bearer {TOKEN}"), echo], max_retries=2)
    caplog.set_level(logging.DEBUG)
    flt = RedactingFilter((TOKEN,))
    for h in logging.getLogger().handlers:
        h.addFilter(flt)
    caplog.handler.addFilter(flt)
    with pytest.raises(RetryExhaustedError) as ei:
        c.extract_table("People")
    assert TOKEN not in repr(c) and TOKEN not in str(c)
    assert TOKEN not in str(ei.value)
    assert caplog.records, "expected warning logs"
    assert TOKEN not in caplog.text
    # the token was actually sent — in the header only
    assert s.calls[0]["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in json.dumps([{k: v for k, v in call.items() if k != "headers"} for call in s.calls])


def test_redacting_filter_scrubs_args_and_exceptions():
    rec = logging.LogRecord("x", logging.ERROR, __file__, 1, "token %s", (TOKEN,), None)
    try:
        raise ValueError(f"boom {TOKEN}")
    except ValueError:
        import sys
        rec.exc_info = sys.exc_info()
    RedactingFilter((TOKEN,)).filter(rec)
    assert TOKEN not in rec.getMessage() and rec.exc_info is None


# --------------------------------------------------------------------------- read-only + rate limit
def test_non_get_methods_are_refused():
    c, s, _ = client([])
    for m in ("POST", "PATCH", "PUT", "DELETE", "post"):
        with pytest.raises(ReadOnlyViolation):
            c._request(m, "https://api.airtable.com/v0/x")
    assert s.calls == []


def test_all_requests_are_get():
    c, s, _ = client([page(100, 0, "o"), page(1, 100)])
    c.extract_table("People")
    assert {call["method"] for call in s.calls} == {"GET"}


def test_rate_limiter_spaces_requests_at_4_per_second():
    t = [0.0]
    sleeps = []

    def sleep(d):
        sleeps.append(d)
        t[0] += d

    rl = RateLimiter(4.0, clock=lambda: t[0], sleep=sleep)
    stamps = []
    for _ in range(9):
        rl.wait()
        stamps.append(t[0])
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert all(g >= 0.25 - 1e-9 for g in gaps)
    assert stamps[-1] >= 2.0            # 9 requests take >= 2 s => <= 4 req/s


def test_rate_limiter_rejects_above_airtable_limit():
    with pytest.raises(ValueError):
        RateLimiter(6)


# --------------------------------------------------------------------------- end-to-end extract + validate
def _router(tables_pages):
    """Routes by URL so scripted order doesn't matter."""
    state = {t: list(p) for t, p in tables_pages.items()}

    def handler(url, params):
        if url.endswith("/meta/whoami"):
            return FakeResponse(200, {"id": "usrX", "scopes": ["data.records:read", "schema.bases:read"]})
        if "/meta/bases/" in url:
            return FakeResponse(200, {"tables": [{"name": t} for t in extract.EXPECTED_TABLES]})
        name = requests.utils.unquote(url.rsplit("/", 1)[1])
        return state[name].pop(0)
    return handler


def test_run_writes_raw_manifest_and_validates(tmp_path):
    tp = {t: [page(2, 0)] for t in extract.EXPECTED_TABLES}
    tp["People"] = [page(100, 0, "o1"), page(100, 100, "o2"), page(50, 200)]
    tp["Findings"] = [page(0)]
    c, s, _ = client([_router(tp)] * 40)
    m = extract.run(c, tmp_path, token_fp="abcd1234")
    assert m["summary"]["tables_success"] == 8 and m["summary"]["tables_failed"] == []
    assert m["tables"]["People"]["pages_fetched"] == 3 and m["tables"]["People"]["records_fetched"] == 250
    assert m["tables"]["Findings"]["records_fetched"] == 0
    assert (tmp_path / "job_openings.json").is_file()
    assert m["runs"][-1]["token_scopes"] == ["data.records:read", "schema.bases:read"]
    assert "usrX" not in (tmp_path / "manifest.json").read_text()       # user id not stored
    assert TOKEN not in "".join(p.read_text() for p in tmp_path.iterdir())
    ok, rows, _ = validate_extraction.validate(tmp_path)
    assert ok, [r for r in rows if not r["ok"]]


def test_failed_table_reported_and_only_it_is_retried(tmp_path):
    tp = {t: [page(1)] for t in extract.EXPECTED_TABLES}
    tp["Offers"] = [FakeResponse(503)] * 3
    c, _, _ = client([_router(tp)] * 40, max_retries=2)
    m = extract.run(c, tmp_path)
    assert m["summary"]["tables_failed"] == ["Offers"] and m["tables"]["Offers"]["status"] == "failed"
    assert not (tmp_path / "offers.json").exists()               # no partial file
    assert validate_extraction.validate(tmp_path)[0] is False

    # retry only the failed table
    tp2 = {"Offers": [page(7)]}
    c2, s2, _ = client([_router(tp2)] * 5)
    m2 = extract.run(c2, tmp_path, tables=["Offers"])
    table_calls = [x for x in s2.calls if "/meta/" not in x["url"]]
    assert len(table_calls) == 1 and m2["summary"]["tables_success"] == 8
    assert m2["runs"][-1]["actions"] == {"Offers": "re-extracted (previous status: failed)"}
    assert validate_extraction.validate(tmp_path)[0] is True


def test_rerun_skips_already_extracted_tables(tmp_path):
    tp = {t: [page(1)] for t in extract.EXPECTED_TABLES}
    c, _, _ = client([_router(tp)] * 40)
    extract.run(c, tmp_path)
    c2, s2, _ = client([_router({})] * 5)
    m = extract.run(c2, tmp_path)
    assert all("skipped" in v for v in m["runs"][-1]["actions"].values())
    assert not [x for x in s2.calls if "/meta/" not in x["url"]]


def test_schema_unavailable_is_documented_not_a_failure(tmp_path):
    tp = {t: [page(1)] for t in extract.EXPECTED_TABLES}
    base = _router(tp)

    def handler(url, params):
        if "/meta/bases/" in url:
            return FakeResponse(403, {"error": {"type": "INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND"}})
        return base(url, params)
    c, _, _ = client([handler] * 40)
    m = extract.run(c, tmp_path)
    assert m["schema"]["status"] == "unavailable" and m["summary"]["tables_success"] == 8
    assert validate_extraction.validate(tmp_path)[0] is True


def test_validator_detects_tampering(tmp_path):
    tp = {t: [page(3)] for t in extract.EXPECTED_TABLES}
    c, _, _ = client([_router(tp)] * 40)
    extract.run(c, tmp_path)
    f = tmp_path / "offers.json"
    f.write_bytes(f.read_bytes().replace(b'"n": 2', b'"n": 99'))
    ok, rows, _ = validate_extraction.validate(tmp_path)
    assert not ok and any(r["check"].startswith("C3") and not r["ok"] for r in rows)


def test_preflight_401_aborts_before_any_table(tmp_path):
    c, s, _ = client([FakeResponse(401, {"error": {"type": "AUTHENTICATION_REQUIRED"}})])
    with pytest.raises(AuthError):
        extract.run(c, tmp_path)
    assert len(s.calls) == 1
    assert not [p for p in tmp_path.iterdir() if p.name != "manifest.json"]
