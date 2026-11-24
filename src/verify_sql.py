"""Run queries/verify_phase2.sql (DuckDB over the raw JSON) and compare it with the Python outputs.

Any mismatch is reported and makes the run fail (DEC-004). Writes outputs/verification.csv.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import duckdb

SQL = Path("queries/verify_phase2.sql")


def sql_results(raw_dir: Path = Path("data/raw")) -> dict[str, tuple[int, int]]:
    con = duckdb.connect(":memory:")
    text = SQL.read_text().replace("{RAW}", str(raw_dir))
    stmts = [x.strip() for x in text.split(";") if x.strip() and not all(l.strip().startswith("--") or not l.strip() for l in x.splitlines())]
    for st in stmts[:-1]:
        con.execute(st)
    rows = con.execute(stmts[-1]).fetchall()
    return {r[0]: (int(r[1]), int(r[2])) for r in rows}


def compare(py: dict[str, tuple[int, int]], sql: dict[str, tuple[int, int]]) -> list[dict]:
    out = []
    for k in sorted(sql):
        p = py.get(k)
        out.append({"check_id": k, "python_numerator": p[0] if p else "", "python_denominator": p[1] if p else "",
                    "sql_numerator": sql[k][0], "sql_denominator": sql[k][1],
                    "match": "MATCH" if p == sql[k] else "MISMATCH"})
    return out


def write(rows: list[dict], path: Path = Path("outputs/verification.csv")) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    from src.run_phase2 import python_checkpoints
    rows = compare(python_checkpoints(), sql_results())
    write(rows)
    bad = [r for r in rows if r["match"] != "MATCH"]
    for r in rows:
        print(f"{r['match']:8} {r['check_id']:20} py={r['python_numerator']}/{r['python_denominator']}  sql={r['sql_numerator']}/{r['sql_denominator']}")
    print(f"\n{len(rows) - len(bad)}/{len(rows)} match")
    sys.exit(1 if bad else 0)
