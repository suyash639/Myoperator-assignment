"""Phase 1 — one-time, read-only extraction of the TalentFlow / Acme Corp Airtable base.

Usage:
    uv run python -m src.extract                    # extract every table not yet extracted
    uv run python -m src.extract --tables Offers    # retry only specific (e.g. failed) tables
    uv run python -m src.extract --force            # deliberately re-extract everything
    uv run python -m src.extract --dry-run          # show the plan; makes NO API calls

Outputs (local only, git-ignored):
    data/raw/<table_slug>.json   JSON array of untouched page bodies (byte-exact concatenation)
    data/raw/_schema.json        untouched metadata API response, if the token permits
    data/raw/manifest.json       counts, pagination status, checksums, run history
    logs/extraction_<UTC>.log    redacted run log
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import platform
import re
import sys
from pathlib import Path

import requests

from src.airtable_client import (AirtableClient, AirtableError, AuthError, NotFoundError,
                                 RedactingFilter, load_config, redact, token_fingerprint)

EXPECTED_TABLES = ["Departments", "People", "Job Openings", "Candidates",
                   "Applications", "Interviews", "Offers", "Findings"]
MANIFEST_VERSION = 1
log = logging.getLogger("extract")


def slug(table: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", table.lower()).strip("_")


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def load_manifest(raw_dir: Path) -> dict | None:
    p = raw_dir / "manifest.json"
    return json.loads(p.read_text()) if p.is_file() else None


def save_manifest(raw_dir: Path, manifest: dict) -> None:
    atomic_write(raw_dir / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())


def already_good(entry: dict | None, raw_dir: Path) -> bool:
    if not entry or entry.get("status") != "success":
        return False
    f = raw_dir / entry["file"]
    return f.is_file() and sha256_file(f) == entry.get("sha256")


def run(client: AirtableClient, raw_dir: Path, tables: list[str] | None = None,
        force: bool = False, token_fp: str | None = None) -> dict:
    raw_dir.mkdir(parents=True, exist_ok=True)
    prev = load_manifest(raw_dir)
    if prev and prev.get("base_id") != client.base_id:
        raise AirtableError("Existing manifest is for a different base_id; refusing to mix snapshots.")

    manifest = prev or {
        "manifest_version": MANIFEST_VERSION,
        "base_id": client.base_id,
        "expected_tables": EXPECTED_TABLES,
        "tables": {},
        "runs": [],
    }
    run_rec = {"run_started_utc": utcnow(), "token_fingerprint": token_fp,
               "python": platform.python_version(), "requests": requests.__version__,
               "requested_tables": tables or "all", "force": force,
               "actions": {}, "requests_made": 0}
    manifest["runs"].append(run_rec)

    # 1. Token scopes — confirms read-only scope set; stores scopes only (no user id / email).
    try:
        who = client.whoami()
        run_rec["token_scopes"] = sorted(who.get("scopes", [])) if isinstance(who.get("scopes"), list) else None
        log.info("whoami ok; scopes=%s", run_rec["token_scopes"])
    except AuthError as e:
        if "401" in str(e):
            run_rec["aborted"] = f"preflight failed: {e}"
            run_rec["run_finished_utc"] = utcnow()
            save_manifest(raw_dir, manifest)
            raise
        run_rec["token_scopes"] = None
        run_rec["whoami_error"] = str(e)
    except AirtableError as e:
        run_rec["token_scopes"] = None
        run_rec["whoami_error"] = str(e)

    # 2. Schema discovery — optional; unavailability is documented, not a failure.
    if force or (manifest.get("schema") or {}).get("status") != "available":
        try:
            raw, body = client.base_schema()
            atomic_write(raw_dir / "_schema.json", raw)
            names = [t.get("name") for t in body.get("tables", [])]
            manifest["schema"] = {
                "status": "available", "file": "_schema.json", "sha256": hashlib.sha256(raw).hexdigest(),
                "retrieved_utc": utcnow(), "tables_in_base": names,
                "expected_missing_from_base": [t for t in EXPECTED_TABLES if t not in names],
                "in_base_not_expected": [t for t in names if t not in EXPECTED_TABLES],
            }
            log.info("schema available; tables in base: %s", names)
        except (AuthError, NotFoundError) as e:
            manifest["schema"] = {"status": "unavailable", "reason": str(e), "checked_utc": utcnow(),
                                  "note": "Field types must be inferred from records; not an extraction failure."}
            log.warning("schema unavailable: %s", e)
        except AirtableError as e:
            manifest["schema"] = {"status": "error", "reason": str(e), "checked_utc": utcnow()}
            log.warning("schema discovery error: %s", e)
        save_manifest(raw_dir, manifest)

    # 3. Tables
    targets = tables or EXPECTED_TABLES
    unknown = [t for t in targets if t not in EXPECTED_TABLES]
    if unknown:
        raise AirtableError(f"Not an expected table: {unknown}")
    for table in targets:
        entry = manifest["tables"].get(table)
        if not force and already_good(entry, raw_dir):
            run_rec["actions"][table] = "skipped (already extracted, checksum verified)"
            log.info("%s: skipped — already extracted and checksum verified", table)
            continue
        started = utcnow()
        try:
            res = client.extract_table(table)
            data = res.raw_bytes()
            fname = f"{slug(table)}.json"
            atomic_write(raw_dir / fname, data)
            manifest["tables"][table] = {
                "file": fname, "status": "success",
                "pages_fetched": len(res.pages), "records_fetched": res.record_count,
                "pagination_terminated": res.pagination_terminated,
                "table_restarts": res.restarts, "http_attempts": res.attempts_total,
                "sha256": hashlib.sha256(data).hexdigest(),
                "page_sha256": [p.sha256 for p in res.pages],
                "started_utc": started, "finished_utc": utcnow(),
            }
            action = "extracted" if not entry else f"re-extracted (previous status: {entry.get('status')})"
            run_rec["actions"][table] = action
            log.info("%s: %s — %d pages, %d records", table, action, len(res.pages), res.record_count)
        except AirtableError as e:
            manifest["tables"][table] = {
                "file": None, "status": "failed", "error": f"{type(e).__name__}: {e}",
                "started_utc": started, "finished_utc": utcnow(),
            }
            run_rec["actions"][table] = "failed"
            log.error("%s: FAILED — %s: %s", table, type(e).__name__, e)
        save_manifest(raw_dir, manifest)

    run_rec["requests_made"] = client.request_count
    run_rec["run_finished_utc"] = utcnow()
    tbl = manifest["tables"]
    manifest["summary"] = {
        "tables_expected": len(EXPECTED_TABLES),
        "tables_success": sum(1 for t in EXPECTED_TABLES if (tbl.get(t) or {}).get("status") == "success"),
        "tables_failed": [t for t in EXPECTED_TABLES if (tbl.get(t) or {}).get("status") == "failed"],
        "tables_not_attempted": [t for t in EXPECTED_TABLES if t not in tbl],
        "total_records": sum((tbl.get(t) or {}).get("records_fetched", 0) for t in EXPECTED_TABLES),
        "last_updated_utc": utcnow(),
    }
    save_manifest(raw_dir, manifest)
    return manifest


def setup_logging(log_dir: Path, secrets: tuple[str, ...]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"extraction_{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.log"
    flt = RedactingFilter(secrets)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in (logging.FileHandler(path), logging.StreamHandler(sys.stdout)):
        h.addFilter(flt)
        h.setFormatter(fmt)
        root.addHandler(h)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", nargs="+", help="Subset of expected tables to (re)extract")
    ap.add_argument("--force", action="store_true", help="Re-extract even if already extracted")
    ap.add_argument("--dry-run", action="store_true", help="Print plan; make no API calls")
    ap.add_argument("--raw-dir", default="data/raw")
    ap.add_argument("--log-dir", default="logs")
    args = ap.parse_args(argv)

    raw_dir = Path(args.raw_dir)
    try:
        token, base_id = load_config()
    except AirtableError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        prev = load_manifest(raw_dir) or {"tables": {}}
        print(f"DRY RUN — no API calls. base_id={base_id} token_fingerprint={token_fingerprint(token)}")
        print("Preflight: GET /v0/meta/whoami ; schema: GET /v0/meta/bases/{base_id}/tables")
        for t in args.tables or EXPECTED_TABLES:
            e = prev["tables"].get(t)
            todo = "SKIP (already good)" if (not args.force and already_good(e, raw_dir)) else "EXTRACT"
            print(f"  {t:<14} -> data/raw/{slug(t)}.json   GET /v0/{base_id}/{t.replace(' ', '%20')}?pageSize=100  [{todo}]")
        return 0

    log_path = setup_logging(Path(args.log_dir), (token,))
    log.info("extraction start; base_id=%s token_fingerprint=%s log=%s", base_id, token_fingerprint(token), log_path)
    client = AirtableClient(token, base_id)
    try:
        m = run(client, raw_dir, args.tables, args.force, token_fingerprint(token))
    except AirtableError as e:
        log.error("ABORTED: %s", redact(e, (token,)))
        return 1
    s = m["summary"]
    log.info("summary: %d/%d tables ok; failed=%s; not attempted=%s; records=%d; requests=%d",
             s["tables_success"], s["tables_expected"], s["tables_failed"], s["tables_not_attempted"],
             s["total_records"], m["runs"][-1]["requests_made"])
    return 0 if s["tables_success"] == s["tables_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
