"""Read-only access to the Phase 1 snapshot.

* Raw files are opened read-only and never written.
* Every load re-verifies each file's SHA-256 against data/raw/manifest.json, so analysis can
  never silently run on modified raw data.
* No cleaning happens here: values are returned exactly as Airtable sent them. Any
  normalisation is done explicitly, and separately, by the caller.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

RAW_DIR = Path("data/raw")

# Snapshot dates (DEC-020, PM-approved 2026-11-24; supersedes DEC-010).
#   EXTRACTION_DATE   date the Airtable API was read (Phase 1).
#   IMPORT_TIMESTAMP  apparent bulk-import time: every createdTime is 2026-08-27T16:39–16:40Z (DQ-22).
#   AS_OF             PROVISIONAL analysis cutoff used for ages and overdue checks. It equals the import
#                     date. It is NOT a confirmed business reporting cutoff (customer question C-01):
#                     3 Candidates.Created On values are later (up to 2026-08-30).
#   CUTOFF_SENSITIVITY  alternative cutoffs reported wherever a metric depends on the cutoff.
EXTRACTION_DATE = "2026-11-24"
IMPORT_TIMESTAMP = "2026-08-27T16:39Z..16:40Z"
AS_OF = "2026-08-27"
CUTOFF_SENSITIVITY = ("2026-08-30", EXTRACTION_DATE)

TABLES = {
    "Departments": "departments", "People": "people", "Job Openings": "job_openings",
    "Candidates": "candidates", "Applications": "applications", "Interviews": "interviews",
    "Offers": "offers", "Findings": "findings",
}


class IntegrityError(Exception):
    pass


@dataclass
class Snapshot:
    raw: dict[str, list[dict]]          # table -> list of untouched record dicts
    by_id: dict[str, dict[str, dict]]   # table -> record_id -> fields (same objects; do not mutate)
    manifest: dict

    def f(self, table: str) -> dict[str, dict]:
        return self.by_id[table]


def load(raw_dir: Path = RAW_DIR) -> Snapshot:
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    raw, by_id = {}, {}
    for table, slug in TABLES.items():
        entry = manifest["tables"][table]
        path = raw_dir / entry["file"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise IntegrityError(f"{path} checksum does not match manifest; raw data has changed")
        records = [r for page in json.loads(data) for r in page["records"]]
        raw[table] = records
        by_id[table] = {r["id"]: r["fields"] for r in records}
    return Snapshot(raw=raw, by_id=by_id, manifest=manifest)


def one(fields: dict, key: str) -> str | None:
    """Single linked record ID (Airtable links are arrays of record IDs). None if empty."""
    v = fields.get(key)
    return v[0] if v else None


def days(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
