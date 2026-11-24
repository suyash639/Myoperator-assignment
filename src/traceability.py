"""Traceability chain → outputs/decision_traceability.csv.

Finding → Evidence → Metric → Assumption → Decision → Product implication.

The chain is curated here (one row per finding). `validate()` checks that every metric ID, DQ ID,
assumption ID and decision ID referenced actually exists in metric_calculations / dq_issues /
assumptions_register.md / decision_log.md, so the matrix cannot silently drift from the outputs.
Metric references ending in '*' are prefix wildcards and must match at least one metric.
"""
from __future__ import annotations

import re
from pathlib import Path

COLS = ["finding_id", "finding", "evidence", "metric_ids", "assumption_ids", "decision_ids",
        "product_implication", "deliverables", "severity", "statement_type", "open_questions",
        "phase2_1_refs", "trace_status", "note"]

# finding, evidence, metrics, assumptions, decisions, implication, deliverables, severity, statement, open Qs, RV refs, note
CHAIN = {
    "F-A": ("VP claim A: Job Board 26.9% of hires; prioritise integration",
            "findings_table.csv F-A; verification.csv M-A0..M-A10; phase2_1_checks.csv R3-*",
            "M-A0;M-A0r;M-A1;M-A2;M-A3;M-A8;M-A9;M-A9n;M-A10;M-A5;M-A7*", "ASM-008;ASM-011;ASM-012;ASM-013;ASM-020",
            "DEC-007;DEC-017;REJ-001;REJ-004;REJ-009",
            "Share of hires does not justify job-board integration priority; Job Board yield per application is the lowest under every attribution",
            "D1;D2;D5", "Critical", "Fact (values) + interpretation (verdict)", "C-04;C-12;C-13", "RV-04", ""),
    "F-B": ("VP claim B: offer acceptance ~72% needs improvement",
            "findings_table.csv F-B; verification.csv M-B0..M-B10; phase2_1_checks.csv R4-*",
            "M-B0;M-B1;M-B2;M-B3;M-B3-2026-11-24;M-B4;M-B9;M-B10;M-B5*", "ASM-006;ASM-007;ASM-017;ASM-020",
            "DEC-016;DEC-020;REJ-001",
            "Offer-status lifecycle integrity is the actionable problem; acceptance definition to be finalised in D3",
            "D1;D3;D5", "Critical", "Fact (values) + interpretation (verdict)", "C-02;C-03;C-08;C-13;C-15", "RV-05;RV-17;RV-19", ""),
    "DQ-01": ("Source contradicts Referred By", "dq_issues.csv DQ-01; verification DQ-01", "M-A0;M-A2;M-A9;M-A9n;M-A7r*;M-A7s*",
              "ASM-011;ASM-013", "DEC-017;REJ-004", "Source attribution integrity as a candidate investment", "D1;D2;D4",
              "Critical", "Fact (Confirmed defect)", "C-04", "RV-04", ""),
    "DQ-02": ("Probable duplicate candidates (identity collisions)", "dq_issues.csv DQ-02; phase2_1_checks.csv R2-pair-*",
              "M-A1;M-A4;M-A8;M-A10", "ASM-008;ASM-012", "DEC-017", "Candidate de-duplication capability", "D2;D4",
              "High", "Fact (Suspicious pattern)", "C-07", "RV-07", "4/6 pairs have experience values implausible for one person"),
    "DQ-03": ("Application ID reused", "dq_issues.csv DQ-03; verification DQ-03", "", "", "",
              "Business-key uniqueness", "D4", "Medium", "Fact (Confirmed defect)", "C-07", "RV-07",
              "All 8 applications belong to DQ-02 candidates; analysis keys on Airtable record IDs"),
    "DQ-04": ("Same candidate hired more than once", "dq_issues.csv DQ-04; verification DQ-04", "M-A1;M-A3;M-B4",
              "ASM-020", "DEC-011", "Hire-count validity; repeat-hire handling", "D1;D4", "High", "Fact (Suspicious pattern)",
              "C-07", "", ""),
    "DQ-05": ("Same candidate, same opening, multiple applications", "dq_issues.csv DQ-05", "", "", "",
              "Duplicate-application prevention", "D4", "Low", "Fact (Suspicious pattern)", "", "", ""),
    "DQ-06": ("Pending offers with Decision On", "dq_issues.csv DQ-06; verification DQ-06", "M-B0;M-B1;M-B2", "ASM-017",
              "DEC-016", "Offer-status integrity (strongest product evidence)", "D1;D2;D3;D4", "Critical",
              "Fact (Confirmed defect)", "C-02", "RV-19", ""),
    "DQ-07": ("Stale Pending offers; no terminal states", "dq_issues.csv DQ-07; verification DQ-07", "M-B3;M-B3-2026-11-24",
              "ASM-006;ASM-007", "DEC-016;DEC-020", "Offer lifecycle states and expiry", "D2;D3;D4", "Critical",
              "Fact (Suspicious pattern)", "C-02;C-03;C-01", "RV-06", "Severity rationale recorded in dq_issues detail"),
    "DQ-08": ("Stage Offer covers pending and declined", "dq_issues.csv DQ-08", "M-B1", "", "DEC-016",
              "Offer outcome modelling", "D3;D4", "Medium", "Fact (Model limitation)", "", "", ""),
    "DQ-09": ("Rejection Reason on non-rejected applications", "dq_issues.csv DQ-09", "M-R2*", "", "",
              "Rejection-reason capture", "D4", "Low", "Fact (Confirmed defect)", "", "", ""),
    "DQ-10": ("Position Cancelled on non-cancelled openings", "dq_issues.csv DQ-10", "M-R2-Position Cancelled", "", "",
              "Opening status tracking", "D4", "Medium", "Fact (Suspicious pattern)", "C-11", "", ""),
    "DQ-11": ("Opening Status contradicts applications", "dq_issues.csv DQ-11", "M-DF*", "", "",
              "Requisition status automation", "D2;D4", "High", "Fact (Confirmed defect)", "C-11;C-10", "RV-01", ""),
    "DQ-12": ("Open openings past Target Close", "dq_issues.csv DQ-12", "", "ASM-006", "DEC-020",
              "Requisition hygiene", "D4", "Medium", "Fact (Suspicious pattern)", "C-01;C-11", "RV-06", "Cutoff sensitivity in detail"),
    "DQ-13": ("Impossible chronology", "dq_issues.csv DQ-13; phase2_1_checks.csv R10-dates", "M-T0;M-T1*", "ASM-006",
              "DEC-019;DEC-020", "Date validation at entry", "D4", "Medium", "Fact (Confirmed defect)", "C-05", "RV-02;RV-06;RV-16", ""),
    "DQ-14": ("Candidate Created On after Applied On", "dq_issues.csv DQ-14", "M-A8", "ASM-012", "",
              "None directly; undermines Created On as first touch", "D4", "Low", "Fact (Suspicious pattern)", "", "RV-07;RV-12", ""),
    "DQ-15": ("Copied date fields contradict source tables", "dq_issues.csv DQ-15; verification DQ-15; phase2_1_checks.csv R10-copy-vs-source-*",
              "M-T2*", "ASM-015", "DEC-019", "Single source of truth for stage dates is itself a product question", "D2;D4", "High",
              "Fact (Confirmed defect)", "C-05", "RV-03", ""),
    "DQ-16": ("Interviews table may lack later rounds", "dq_issues.csv DQ-16; verification DQ-16", "M-I0;M-T2*", "ASM-009", "",
              "Interview data capture completeness", "D2;D4", "High", "Fact (Suspicious pattern)", "C-05", "", "Not a confirmed defect"),
    "DQ-17": ("Interview Outcome contradicts completion data", "dq_issues.csv DQ-17", "M-I0;M-I1*", "", "",
              "Interview outcome capture", "D4", "Low", "Fact (Confirmed defect)", "", "", ""),
    "DQ-18": ("Hired applications closed before acceptance", "dq_issues.csv DQ-18; verification DQ-18", "M-T0;M-T1*", "ASM-020",
              "DEC-011;REJ-006", "Hire event definition", "D3;D4", "Medium", "Fact (Suspicious pattern)", "C-06", "RV-09", ""),
    "DQ-19": ("Offer outside salary band", "dq_issues.csv DQ-19", "", "ASM-016", "", "Offer approval guardrails", "D4", "Low",
              "Fact (Suspicious pattern)", "C-09", "", ""),
    "DQ-20": ("Non-round CTC values", "dq_issues.csv DQ-20", "", "ASM-016", "", "None", "D4", "Low", "Fact (Suspicious pattern)", "", "", ""),
    "DQ-21": ("Application recruiter differs from opening's", "dq_issues.csv DQ-21", "", "", "", "None", "D4", "Low",
              "Fact (Legitimate)", "", "", ""),
    "DQ-22": ("Bulk-created within one minute", "dq_issues.csv DQ-22", "", "ASM-006", "DEC-020;REJ-007",
              "Never use createdTime", "D4", "Low", "Fact (Informational)", "C-01", "RV-06", ""),
    "DQ-23": ("Findings table empty", "dq_issues.csv DQ-23", "", "", "REJ-002", "None", "D4", "Low", "Fact (Informational)", "", "", ""),
    "DQ-24": ("No feedback timestamp", "dq_issues.csv DQ-24", "", "", "",
              "Feedback-latency claims cannot be evidenced", "D2;D4", "Medium", "Fact (Model limitation)", "", "", ""),
    "DQ-25": ("Offer far from Expected CTC", "dq_issues.csv DQ-25; verification DQ-25; phase2_1_checks.csv R7-*",
              "M-B7*;M-B8*", "ASM-016", "", "No compensation-driven decline conclusions", "D4", "Medium",
              "Fact (Suspicious pattern); cause is a hypothesis", "C-09", "RV-08", ""),
    "DQ-26": ("Declined offers: application closed before decision", "dq_issues.csv DQ-26; verification DQ-26", "", "ASM-020",
              "DEC-011", "Application lifecycle / Closed On semantics", "D3;D4", "Medium", "Fact (Suspicious pattern)", "C-06", "RV-09", ""),
    "DQ-27": ("Interview after rejected/withdrawn application closed", "dq_issues.csv DQ-27; verification DQ-27", "M-R*", "", "",
              "Application lifecycle", "D4", "Low", "Fact (Confirmed defect)", "C-06", "RV-09", ""),
    "DQ-28": ("Stalled Active applications", "dq_issues.csv DQ-28; verification DQ-28", "M-FCc*;M-K-eligible;M-K-stalled*",
              "ASM-017;ASM-021", "DEC-021;DEC-022", "Application status hygiene / auto-closure", "D2;D4", "Medium",
              "Fact (Suspicious pattern)", "C-11", "RV-10", ""),
    "DQ-29": ("Offers to already-hired candidates", "dq_issues.csv DQ-29; verification DQ-29", "M-B9;M-B10", "ASM-020",
              "DEC-016", "Internal-mobility handling in offer metrics", "D3;D4", "Low", "Fact (Suspicious pattern)", "C-08", "RV-17", ""),
    "INS-FUNNEL": ("Largest drop screened->interviewed; lowest step interviewed->offered", "metric_calculations.csv M-F*, M-FC*; verification",
                   "M-F0;M-F4;M-FC*;M-FCc*;M-F-leak;M-R*", "ASM-017", "DEC-021",
                   "Screening-to-interview and interview-to-offer are the leak points", "D2;D5;appendix", "n/a", "Fact", "", "RV-10", ""),
    "INS-COHORT": ("Completed cohort 2025-Q3..2026-Q1", "metric_calculations.csv M-K*", "M-K*", "ASM-021", "DEC-021;DEC-022",
                   "Cohort view of conversion, insensitive to the unresolved cutoff", "D2;appendix", "n/a", "Fact", "C-01", "RV-10",
                   "Offer->hire step n is small; 2 offers still Pending"),
    "INS-CHANNEL-QUALITY": ("Channel quality, Source as recorded", "metric_calculations.csv M-Q*", "M-Q1*;M-Q2*;M-Q3*;M-Q4*", "ASM-013",
                            "DEC-017", "Job-board volume is not the constraint", "D1;D2;appendix", "n/a", "Fact + interpretation", "", "RV-04;RV-14;RV-15", ""),
    "INS-DEPARTMENTS": ("Department funnel incl. Engineering 0/30 hires", "metric_calculations.csv M-DF*; verification M-DF-Engineering-*",
                        "M-DF*", "ASM-018", "", "Engineering pipeline needs customer explanation", "appendix", "n/a", "Fact", "C-10", "RV-01", ""),
    "INS-CYCLE": ("Cycle time; department ranking unsupported", "metric_calculations.csv M-T*", "M-T0;M-T1*;M-T2*", "ASM-015;ASM-018",
                  "DEC-011;DEC-019", "No department-specific investment supported", "appendix", "n/a", "Fact", "", "RV-03;RV-16", ""),
    "INS-DECLINES": ("Declines not attributable (5 declines)", "metric_calculations.csv M-D*, M-B6*", "M-D1*;M-D2*;M-B6*", "ASM-018", "",
                     "No role/department decline intervention supported", "appendix", "n/a", "Fact", "", "", ""),
    "INS-INTERVIEWS": ("Interview non-completion; feedback latency unmeasurable", "metric_calculations.csv M-I*; DQ-24", "M-I0;M-I1*;M-I2",
                       "ASM-009", "", "Weak evidence for scheduling tooling; none for feedback latency", "D2;appendix", "n/a", "Fact", "C-05", "", ""),
}


def rows() -> list[dict]:
    out = []
    for fid, t in CHAIN.items():
        assert len(t) == 12, fid
        r = dict(zip(COLS, (fid,) + t[:11] + ("", t[11])))
        r["trace_status"] = "Complete" if all(r[c] for c in ("evidence", "product_implication")) and (r["metric_ids"] or r["decision_ids"] or r["assumption_ids"]) \
            else "Evidence-only (no metric/assumption/decision depends on it)"
        if r["open_questions"]:
            r["trace_status"] += f"; open: {r['open_questions']}"
        out.append(r)
    return out


def validate(metric_ids: set[str], dq_ids: set[str], asm_text: str, dec_text: str) -> list[str]:
    """Return a list of dangling references (empty = consistent)."""
    asm = set(re.findall(r"\| (ASM-\d{3}) \|", asm_text))
    dec = set(re.findall(r"\| ((?:DEC|REJ)-\d{3}) \|", dec_text))
    bad = []
    for r in rows():
        for mid in filter(None, r["metric_ids"].split(";")):
            ok = any(x.startswith(mid[:-1]) for x in metric_ids) if mid.endswith("*") else mid in metric_ids
            if not ok:
                bad.append(f"{r['finding_id']}: metric {mid}")
        for a in filter(None, r["assumption_ids"].split(";")):
            if a not in asm:
                bad.append(f"{r['finding_id']}: assumption {a}")
        for d in filter(None, r["decision_ids"].split(";")):
            if d not in dec:
                bad.append(f"{r['finding_id']}: decision {d}")
        if r["finding_id"].startswith("DQ-") and r["finding_id"] not in dq_ids:
            bad.append(f"{r['finding_id']}: not in dq_issues")
    for d in dq_ids:
        if d not in CHAIN:
            bad.append(f"{d}: missing from traceability chain")
    return bad


def validate_files(out_dir: Path = Path("outputs"), audit_dir: Path = Path("audit")) -> list[str]:
    import csv
    mids = {r["metric_id"] for r in csv.DictReader((out_dir / "metric_calculations.csv").open())}
    dqs = {r["issue_id"] for r in csv.DictReader((out_dir / "dq_issues.csv").open())}
    return validate(mids, dqs, (audit_dir / "assumptions_register.md").read_text(), (audit_dir / "decision_log.md").read_text())
