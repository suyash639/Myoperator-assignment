"""Phase 2 orchestrator. Reads data/raw (checksum-verified) and writes outputs/*.csv. No API calls.

    uv run python -m src.run_phase2

Writes table_profiles.csv, relationship_integrity.csv, metric_calculations.csv, dq_issues.csv,
findings_table.csv, decision_traceability.csv and verification.csv. Raw files are re-hashed after the run to prove they
were not modified.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from src import audit, integrity, metrics, profile, traceability, verify_sql
from src.data import RAW_DIR, load

OUT = Path("outputs")


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def python_checkpoints(snap=None) -> dict[str, tuple[int, int]]:
    snap = snap or load()
    m = metrics.compute(snap)
    out = {r["metric_id"]: (r["numerator"], r["denominator"]) for r in m.rows if r["numerator"] != ""}
    out.update({i.id: (i.affected, i.denominator) for i in audit.run_checks(snap)})
    rel = integrity.check_relationships(snap)
    want = {"Applications.Candidate -> Candidates", "Offers.Application -> Applications", "Interviews.Application -> Applications"}
    out["REL-orphans"] = (sum(r["orphans"] for r in rel if r["relationship"] in want),
                          sum(r["source_records"] for r in rel if r["relationship"] in want))
    return out


# ------------------------------------------------------------------ findings table
CONF = {"Confirmed defect": "High", "Suspicious pattern": "Medium", "Legitimate business case": "High",
        "Model limitation": "High", "Informational": "High"}


def findings(issues, m) -> list[dict]:
    v = m.value
    rows = []

    def add(fid, kind, claim, metric, value, method, evidence, severity, confidence, implication, fact_or_interp):
        rows.append({"finding_id": fid, "type": kind, "claim_or_issue": claim, "metric": metric,
                     "actual_value": value, "calculation_method": method, "evidence": evidence,
                     "severity": severity, "confidence": confidence,
                     "statement_type": fact_or_interp, "product_implication": implication})

    a0, a5 = v("M-A0"), v("M-A5")
    variants = [v(x) for x in ("M-A0", "M-A1", "M-A2", "M-A3", "M-A8", "M-A9", "M-A10")]
    lo, hi = min(variants, key=lambda r: r["value"]), max(variants, key=lambda r: r["value"])
    jb = [v(f"{p}-Job Board") for p in ("M-A7", "M-A7r", "M-A7s", "M-A7m", "M-A7f")]
    jlo, jhi = min(jb, key=lambda r: r["value"]), max(jb, key=lambda r: r["value"])
    others = [r for r in m.rows if r["metric_id"].startswith("M-A7") and not r["metric_id"].endswith("Job Board")
              and r["numerator"] not in ("", 0)]
    next_low = min(others, key=lambda r: r["value"])
    add("F-A", "VP claim", "Job boards contribute 26.9% of hires and should be prioritised",
        "Job Board share of hires (Source as recorded, primary; DEC-017)",
        f"{a0['value_pct']} ({a0['numerator']}/{a0['denominator']}) Source as recorded; definition sensitivity {lo['value_pct']} "
        f"({lo['metric_id']}) to {hi['value_pct']} ({hi['metric_id']}); one hire = {a0['single_record_pp']} pp",
        "Stage=Hired joined to Candidates.Source; variants M-A1, M-A2, M-A3, M-A8, M-A9, M-A10 (metric_calculations.csv)",
        "M-A0, M-A1, M-A2, M-A3, M-A8, M-A9, M-A10, M-A5, M-A7*-Job Board, M-A9n; DQ-01, DQ-02, DQ-04",
        "Critical", "High (arithmetic); Medium (attribution)",
        f"The share reproduces, but prioritisation does not follow from it: Job Board is {a5['value_pct']} of applications and converts at "
        f"{jlo['value_pct']} to {jhi['value_pct']} per application across all attribution variants, the lowest of any channel with hires "
        f"(next lowest {next_low['value_pct']}). Referral is NOT a proven high-performing channel: {v('M-A9n')['numerator']}/{v('M-A9n')['denominator']} "
        "Referral-labelled hires have no referrer link. No data measures integration friction.",
        "Fact (values) + interpretation (inference)")
    b0, b1, b2, b3, b4 = v("M-B0"), v("M-B1"), v("M-B2"), v("M-B3"), v("M-B4")
    bx = v("M-B3-2026-11-24")
    add("F-B", "VP claim", "Offer acceptance is approximately 72% and needs improvement",
        "Decided-offer acceptance rate, offer-level (provisional primary; DEC-016)",
        f"{b1['value_pct']} ({b1['numerator']}/{b1['denominator']}) decided offers, offer-level; all-issued-offer ratio {b0['value_pct']} "
        f"({b0['numerator']}/{b0['denominator']}); candidate-level {b4['value_pct']} ({b4['numerator']}/{b4['denominator']}); scenarios "
        f"{b3['value_pct']} (stale Pending as expired, provisional cutoff), {bx['value_pct']} (same, extraction-date cutoff), {b2['value_pct']} (upper bound); "
        f"one decided offer = {b1['single_record_pp']} pp",
        "Offers.Status; variants M-B0..M-B5, M-B9, M-B10",
        "M-B0, M-B1, M-B2, M-B3, M-B3-2026-11-24, M-B4, M-B9, M-B10; DQ-06, DQ-07, DQ-29",
        "Critical", "Medium (4 of 5 Pending carry decision dates)",
        f"The VP's ~72% is the all-issued-offer ratio ({b0['numerator']}/{b0['denominator']}), which counts {b0['denominator'] - b1['denominator']} unresolved Pending "
        f"offers as non-acceptance. The provisional decided-offer rate is {b1['value_pct']}. Whether that needs improvement cannot be judged "
        "(no target or benchmark). The data does show unreliable offer-status records (DQ-06, DQ-07).",
        "Fact (values) + interpretation (verdict)")
    for i in issues:
        rows.append({"finding_id": i.id, "type": "Data quality", "claim_or_issue": i.title,
                     "metric": f"{i.affected}/{i.denominator} {i.denominator_desc}", "actual_value": f"{i.pct}%",
                     "calculation_method": i.method,
                     "evidence": ("; ".join(i.evidence[:12]) + (f" (+{len(i.evidence) - 12} more in dq_issues.csv)" if len(i.evidence) > 12 else "")) or i.detail,
                     "severity": i.severity, "confidence": CONF[i.classification],
                     "statement_type": f"Fact ({i.classification})", "product_implication": i.decision_impacted})
    return rows


def main() -> int:
    OUT.mkdir(exist_ok=True)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW_DIR.glob("*.json"))}
    snap = load()
    write_csv("table_profiles.csv", profile.profile(snap))
    write_csv("relationship_integrity.csv", integrity.check_relationships(snap) + integrity.coverage(snap))
    m = metrics.compute(snap)
    write_csv("metric_calculations.csv", m.rows)
    issues = audit.run_checks(snap)
    write_csv("dq_issues.csv", [i.row() for i in issues])
    write_csv("findings_table.csv", findings(issues, m))
    write_csv("decision_traceability.csv", traceability.rows())
    ver = verify_sql.compare(python_checkpoints(snap), verify_sql.sql_results())
    verify_sql.write(ver)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW_DIR.glob("*.json"))}
    mism = [r for r in ver if r["match"] != "MATCH"]
    print(f"profiles={sum(1 for _ in open(OUT / 'table_profiles.csv')) - 1} metrics={len(m.rows)} issues={len(issues)} "
          f"verification={len(ver) - len(mism)}/{len(ver)} match; raw unchanged={before == after}")
    for r in mism:
        print("MISMATCH", r)
    return 0 if (not mism and before == after) else 1


if __name__ == "__main__":
    sys.exit(main())
