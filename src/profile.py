"""Field-level profile of every table → outputs/table_profiles.csv.

Field types are *inferred from values* (the schema endpoint returned 403). Airtable omits empty
fields from record JSON, so "missing" means the key is absent from the record: Airtable's
representation of an empty cell.
"""
from __future__ import annotations

import collections
import re

from src.data import Snapshot

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
REC_ID = re.compile(r"rec[A-Za-z0-9]{14}")
# Personal or free-text fields: values are never written to committable outputs.
PII_FIELDS = {"Full Name", "Email", "Work Email", "Phone", "Notes", "Feedback"}


def infer_type(values: list) -> str:
    kinds = set()
    for v in values:
        if isinstance(v, bool):
            kinds.add("boolean")
        elif isinstance(v, (int, float)):
            kinds.add("number")
        elif isinstance(v, list):
            kinds.add("link" if v and all(isinstance(x, str) and REC_ID.fullmatch(x) for x in v) else "list")
        elif isinstance(v, str):
            kinds.add("date" if ISO_DATE.fullmatch(v) else "text")
        else:
            kinds.add(type(v).__name__)
    return "|".join(sorted(kinds)) or "empty"


def profile(snap: Snapshot) -> list[dict]:
    rows = []
    for table, recs in snap.raw.items():
        n = len(recs)
        if n == 0:
            rows.append({"table": table, "field": "(no records)", "records": 0, "inferred_type": "",
                         "present": 0, "missing": 0, "pct_missing": "", "blank_strings": 0,
                         "distinct": 0, "unique_ratio": "", "min": "", "max": "", "top_values": "",
                         "duplicate_values": 0, "notes": "Table is empty (HTTP 200, zero records)"})
            continue
        fields = sorted({k for r in recs for k in r["fields"]})
        for fld in fields:
            vals = [r["fields"][fld] for r in recs if fld in r["fields"]]
            t = infer_type(vals)
            blanks = sum(1 for v in vals if isinstance(v, str) and not v.strip())
            hashable = [tuple(v) if isinstance(v, list) else v for v in vals]
            cnt = collections.Counter(hashable)
            dup_vals = sum(1 for c in cnt.values() if c > 1)
            scalar = [v for v in vals if isinstance(v, (int, float, str)) and not isinstance(v, bool)]
            mn = min(scalar) if scalar and t in ("number", "date") else ""
            mx = max(scalar) if scalar and t in ("number", "date") else ""
            top = "; ".join(f"{k}={c}" for k, c in cnt.most_common(8)) if t in ("text",) and len(cnt) <= 30 else ""
            notes = []
            if fld in PII_FIELDS:
                top = ""
                notes.append("personal/free-text field: values suppressed")
            if t == "link":
                notes.append("cardinality " + ", ".join(f"{k}:{c}" for k, c in sorted(collections.Counter(len(v) for v in vals).items())))
            if "|" in t:
                notes.append("mixed types")
            rows.append({
                "table": table, "field": fld, "records": n, "inferred_type": t,
                "present": len(vals), "missing": n - len(vals),
                "pct_missing": round(100 * (n - len(vals)) / n, 1), "blank_strings": blanks,
                "distinct": len(cnt), "unique_ratio": round(len(cnt) / len(vals), 3) if vals else "",
                "min": mn, "max": mx, "top_values": top, "duplicate_values": dup_vals,
                "notes": "; ".join(notes),
            })
    return rows
