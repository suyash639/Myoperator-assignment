"""Offline completeness check of the Phase 1 snapshot. Makes NO API calls.

Usage:  uv run python -m src.validate_extraction [--raw-dir data/raw]

Checks (each reported PASS/FAIL per table):
  C1  all 8 expected tables present in manifest (none silently skipped)
  C2  manifest status == success
  C3  raw file exists and its SHA-256 matches the manifest
  C4  raw file is valid JSON: an array of page objects each with a 'records' list
  C5  page count in file == manifest pages_fetched
  C6  record count in file == manifest records_fetched
  C7  pagination terminated: every page except the last has 'offset'; the last has none
  C8  every record has id / createdTime / fields; ids are well-formed and unique in the table
      (a duplicate id across pages would indicate a pagination fault, not a data defect)
  C9  per-page SHA-256 list length matches page count
  S   schema status is reported (unavailability is documented, not a failure)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from src.extract import EXPECTED_TABLES

REC_ID = re.compile(r"rec[A-Za-z0-9]{14}")


def validate(raw_dir: Path) -> tuple[bool, list[dict], dict]:
    mpath = raw_dir / "manifest.json"
    if not mpath.is_file():
        return False, [{"table": "*", "check": "manifest", "ok": False, "detail": "manifest.json missing"}], {}
    m = json.loads(mpath.read_text())
    rows: list[dict] = []

    def add(table, check, ok, detail=""):
        rows.append({"table": table, "check": check, "ok": bool(ok), "detail": detail})

    for t in EXPECTED_TABLES:
        e = m.get("tables", {}).get(t)
        add(t, "C1 in manifest", e is not None)
        if e is None:
            continue
        add(t, "C2 status success", e.get("status") == "success", e.get("error", ""))
        if e.get("status") != "success":
            continue
        f = raw_dir / e["file"]
        if not f.is_file():
            add(t, "C3 file exists + sha256", False, "file missing")
            continue
        data = f.read_bytes()
        add(t, "C3 file exists + sha256", hashlib.sha256(data).hexdigest() == e["sha256"])
        try:
            pages = json.loads(data)
            ok = isinstance(pages, list) and all(isinstance(p, dict) and isinstance(p.get("records"), list) for p in pages)
        except ValueError as ex:
            add(t, "C4 valid JSON structure", False, str(ex))
            continue
        add(t, "C4 valid JSON structure", ok)
        if not ok:
            continue
        n_rec = sum(len(p["records"]) for p in pages)
        add(t, "C5 pages match manifest", len(pages) == e["pages_fetched"], f"{len(pages)} vs {e['pages_fetched']}")
        add(t, "C6 records match manifest", n_rec == e["records_fetched"], f"{n_rec} vs {e['records_fetched']}")
        term = (len(pages) >= 1 and all(p.get("offset") for p in pages[:-1]) and not pages[-1].get("offset"))
        add(t, "C7 pagination terminated", term and e.get("pagination_terminated") is True)
        recs = [r for p in pages for r in p["records"]]
        shape = all(isinstance(r, dict) and {"id", "createdTime", "fields"} <= r.keys() for r in recs)
        ids = [r.get("id") for r in recs]
        wellformed = all(isinstance(i, str) and REC_ID.fullmatch(i) for i in ids)
        dupes = len(ids) - len(set(ids))
        add(t, "C8 record shape + unique ids", shape and wellformed and dupes == 0,
            f"shape={shape} wellformed={wellformed} duplicate_ids={dupes}")
        add(t, "C9 page checksums recorded", len(e.get("page_sha256", [])) == len(pages))

    schema = m.get("schema") or {"status": "not checked"}
    info = {"schema_status": schema.get("status"), "schema_reason": schema.get("reason"),
            "schema_tables_missing": schema.get("expected_missing_from_base"),
            "schema_tables_unexpected": schema.get("in_base_not_expected")}
    if schema.get("status") == "available":
        sf = raw_dir / schema["file"]
        add("_schema", "S schema file sha256",
            sf.is_file() and hashlib.sha256(sf.read_bytes()).hexdigest() == schema["sha256"])
    return all(r["ok"] for r in rows), rows, {**info, "summary": m.get("summary")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default="data/raw")
    args = ap.parse_args(argv)
    ok, rows, info = validate(Path(args.raw_dir))
    for r in rows:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['table']:<14} {r['check']:<30} {r['detail']}")
    print(f"\nschema: {info.get('schema_status')}  {info.get('schema_reason') or ''}")
    if info.get("schema_tables_missing") or info.get("schema_tables_unexpected"):
        print(f"  expected-but-missing: {info['schema_tables_missing']}  unexpected: {info['schema_tables_unexpected']}")
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
