"""Programmatic QC for Phase 3 outputs. Returns a list of failures (empty = pass).

    uv run python -m src.phase3_checks

Checks: exactly 3 builds / 3 non-builds; effort sums (6.0 total, per build, per sprint, per discipline) agree across
the allocation CSV, strategy and roadmap; the ranking supports the selection under every weighting; scorecard coverage
and baseline provenance; traceability references resolve; customer questions covered; D3 reference implementation
reconciles with Phase 2.2 metrics; every fraction in Phase 3 documents exists in a generated CSV; no sampling
intervals; offer-level and candidate-level figures are never presented unlabelled.
"""
from __future__ import annotations

import collections
import csv
import re
import sys
from pathlib import Path

from src import phase3_plan as plan
from src.offer_lifecycle import transition_table_md

OUT, AUDIT = Path("outputs"), Path("audit")
DOCS = ["phase3_product_strategy.md", "q3_roadmap.md", "offer_acceptance_metric_spec.md",
        "customer_validation_plan.md", "phase3_review.md", "phase3_1_review.md", "phase3_2_final_review.md"]


def rd(name):
    return list(csv.DictReader((OUT / name).open()))


def ids_from_outputs():
    mids = {r["metric_id"] for r in rd("metric_calculations.csv")} | {r["metric_id"] for r in rd("offer_metric_baseline.csv")}
    chk = {r["check_id"] for r in rd("phase2_1_checks.csv")}
    dqs = {r["issue_id"] for r in rd("dq_issues.csv")}
    asm = set(re.findall(r"\| (ASM-\d{3}) \|", (AUDIT / "assumptions_register.md").read_text()))
    dec = set(re.findall(r"\| ((?:DEC|REJ)-\d{3}) \|", (AUDIT / "decision_log.md").read_text()))
    cq = set(re.findall(r"### (C-\d{2})\.", (OUT / "open_questions_for_customer.md").read_text()))
    return mids, chk, dqs, asm, dec, cq


def pairs_index():
    """num/den pairs available in generated CSVs, keyed by ID."""
    idx = {}
    for name, idcol, a, b in (("metric_calculations.csv", "metric_id", "numerator", "denominator"),
                              ("offer_metric_baseline.csv", "metric_id", "numerator", "denominator"),
                              ("dq_issues.csv", "issue_id", "affected_records", "denominator"),
                              ("phase2_1_checks.csv", "check_id", "numerator", "denominator")):
        for r in rd(name):
            idx.setdefault(r[idcol], set()).add(f"{r[a]}/{r[b]}")
    return idx


def known_fractions():
    known = set()
    for p in OUT.glob("*.csv"):
        for r in csv.DictReader(p.open()):
            for a, b in (("numerator", "denominator"), ("affected_records", "denominator")):
                if r.get(a) not in (None, "") and r.get(b) not in (None, ""):
                    known.add(f"{r[a]}/{r[b]}")
            for v in r.values():
                known.update(re.findall(r"\b\d+/\d+\b", v or ""))
    return known


def check() -> list[str]:
    fail = []
    strat = (OUT / "phase3_product_strategy.md").read_text()
    road = (OUT / "q3_roadmap.md").read_text()

    # 1. exactly three builds and three non-builds
    b_head = re.findall(r"^### (B\d):", strat, re.M)
    n_head = re.findall(r"^### (N\d):", strat, re.M)
    if b_head != ["B1", "B2", "B3"]:
        fail.append(f"build sections {b_head}")
    if n_head != ["N1", "N2", "N3"]:
        fail.append(f"non-build sections {n_head}")
    dec_rows = re.findall(r"^\| \*\*([BN]\d)\*\* \| .*? \| \*\*(.*?)\*\*", strat, re.M)
    builds = [i for i, d in dec_rows if d == "Build"]
    nonb = [i for i, d in dec_rows if d.startswith("Do not build")]
    if len(builds) != 3 or len(nonb) != 3:
        fail.append(f"decision table builds={builds} non-builds={nonb}")
    sc = rd("phase3_prioritisation_scores.csv")
    if sorted(r["candidate_id"] for r in sc if r["decision"] == "Build") != ["B1", "B2", "B3"]:
        fail.append("scores: builds mismatch")
    if sum(r["decision"].startswith("Non-build") for r in sc) != 3:
        fail.append("scores: non-build count")
    for key in ("weighted_rank", "equal_weight_rank", "rank_without_effort"):
        top = sorted(r["candidate_id"] for r in sc if int(r[key]) <= 3)
        if top != ["B1", "B2", "B3"]:
            fail.append(f"{key}: top three are {top}")

    # 2. capacity
    al = rd("phase3_capacity_allocation.csv")
    tot = round(sum(float(r["engineer_weeks"]) for r in al), 4)
    if tot != plan.TOTAL_CAPACITY:
        fail.append(f"allocation total {tot}")
    if len({r["component_id"] for r in al}) != len(al):
        fail.append("duplicate allocation component")
    by_b, by_s, by_bd, by_bs = (collections.defaultdict(float) for _ in range(4))
    for r in al:
        ew = float(r["engineer_weeks"])
        by_b[r["build"]] += ew
        by_s[r["sprint"]] += ew
        by_bd[(r["build"], r["discipline"])] += ew
        by_bs[(r["build"], r["sprint"])] += ew
    if dict(by_b) != plan.BUILD_EFFORT:
        fail.append(f"per-build {dict(by_b)}")
    for b, ew in plan.BUILD_EFFORT.items():
        if not re.search(rf"\| \*\*{b}\*\* \| .*? \| \*\*Build\*\* \| {ew} \|", strat):
            fail.append(f"strategy decision table effort for {b}")
        if not re.search(rf"^### {b}: .*\({ew} engineer-weeks\)", strat, re.M):
            fail.append(f"strategy heading effort for {b}")
        disc = [by_bd[(b, d)] for d in ("Backend", "Frontend", "Data/analytics", "QA")]
        row = f"| {b} | " + " | ".join(f"{x:.2f}" for x in disc) + f" | **{ew}** |"
        if row not in strat:
            fail.append(f"strategy discipline row for {b}: expected {row}")
    for sp in ("1", "2", "3"):
        cells = " | ".join(f"{by_bs[(b, sp)]:.2f}" for b in ("B1", "B2", "B3"))
        if not re.search(rf"^\| Sprint {sp}: .*? \| {re.escape(cells)} \| \*\*{by_s[sp]:.1f}\*\* \|", road, re.M):
            fail.append(f"roadmap sprint {sp} row: expected {cells} / {by_s[sp]}")
    if "| **Build total** | **2.5** | **2.0** | **1.5** | **6.0** |" not in road:
        fail.append("roadmap build totals row")

    # 2b. Phase 3.1: estimates labelled, first cut = duplicate warning (0.5, B3), lifecycle table embedded verbatim
    if any(r["estimate_status"] != plan.ESTIMATE_STATUS for r in al):
        fail.append("allocation row without PM planning estimate label")
    cut = [r for r in al if r["first_cut"] == "yes"]
    if sorted(r["component_id"] for r in cut) != ["B3.2", "B3.3b"] or round(sum(float(r["engineer_weeks"]) for r in cut), 4) != 0.5:
        fail.append("first cut is not the 0.5 engineer-week B3 duplicate warning")
    spec = (OUT / "offer_acceptance_metric_spec.md").read_text()
    if transition_table_md() not in spec:
        fail.append("spec transition table differs from src/offer_lifecycle.py")
    for x in ("Expired", "Withdrawn", "Rescinded", "Superseded"):
        if f"| {x} |" not in spec:
            fail.append(f"spec lacks transition into {x}")
    ev = {r["evidence_id"]: (r["numerator"], r["denominator"]) for r in rd("phase3_1_evidence.csv")}
    om0 = {r["metric_id"]: (r["numerator"], r["denominator"]) for r in rd("offer_metric_baseline.csv")}
    dq0 = {r["issue_id"]: (r["affected_records"], r["denominator"]) for r in rd("dq_issues.csv")}
    if ev["E-B1-2"] != om0["OAM-03c"]:
        fail.append(f"lifecycle legacy flags {ev['E-B1-2']} != OAM-03c {om0['OAM-03c']}")
    if ev["E-B2-90"] != dq0["DQ-28"]:
        fail.append("inactivity default threshold does not reproduce DQ-28")
    if int(ev["E-B3-dup-1"][0]) * 2 != int(dq0["DQ-02"][0]):
        fail.append("duplicate warning groups do not reproduce DQ-02")
    if ev["E-B2-req"] != dq0["DQ-11"]:
        fail.append("opening review flags do not reproduce DQ-11")

    # 3. success metrics
    mids, chk, dqs, asm, dec, cq = ids_from_outputs()
    idx = pairs_index()
    sm = rd("product_success_metrics.csv")
    smids = {r["metric_id"] for r in sm}
    for b in ("B1", "B2", "B3"):
        types = {r["metric_type"] for r in sm if r["build"] == b}
        if not ({"adoption", "guardrail"} <= types and types & {"outcome", "data_quality"}):
            fail.append(f"scorecard coverage {b}: {types}")
    for r in sm:
        for col in ("baseline", "target_or_decision_rule", "measurement_method", "data_source", "evaluation_window", "owner"):
            if not r[col]:
                fail.append(f"{r['metric_id']}: empty {col}")
        refs = [x for x in r["baseline_ref"].split(";") if x]
        for x in refs:
            if x not in mids | chk | dqs:
                fail.append(f"{r['metric_id']}: unknown baseline ref {x}")
        fr = re.findall(r"\b\d+/\d+\b", r["baseline"])
        if fr and refs and not any(f in idx.get(x, set()) for f in fr for x in refs):
            fail.append(f"{r['metric_id']}: baseline {fr} not found in {refs}")
        if (r["baseline"].startswith(("No baseline", "Not measurable", "Not applicable")) and r["target_status"].startswith("Firm")
                and "enforced" not in r["target_status"]):
            fail.append(f"{r['metric_id']}: firm target without baseline")
        if r["guardrail_for"]:
            for g in r["guardrail_for"].split(";"):
                if g not in smids:
                    fail.append(f"{r['metric_id']}: guardrail_for unknown {g}")

    # 4. traceability
    tr = rd("phase3_decision_traceability.csv")
    inits = {"B1", "B2", "B3", "N1", "N2", "N3", "X1 (backlog)", "X2 (backlog)"}
    traced_sm = set()
    for r in tr:
        for col, pool in (("metric_ids", mids), ("evidence", dqs), ("assumption_ids", asm), ("decision_ids", dec),
                          ("customer_questions", cq), ("success_metric_ids", smids)):
            for x in filter(None, r[col].split(";")):
                if x not in pool:
                    fail.append(f"{r['trace_id']}: {col} {x} unresolved")
        for x in filter(None, r["initiative"].split(";")):
            if x not in inits:
                fail.append(f"{r['trace_id']}: initiative {x}")
        traced_sm |= set(filter(None, r["success_metric_ids"].split(";")))
    if smids - traced_sm:
        fail.append(f"success metrics not traced: {sorted(smids - traced_sm)}")
    for b in ("B1", "B2", "B3", "N1", "N2", "N3"):
        if not any(b in r["initiative"].split(";") for r in tr):
            fail.append(f"initiative {b} not traced")

    # 5. customer questions
    cvp = (OUT / "customer_validation_plan.md").read_text()
    covered = set(re.findall(r"^\| (C-\d{2}) \|", cvp, re.M))
    if covered != cq:
        fail.append(f"validation plan missing {sorted(cq - covered)}")

    # 6. D3 reference implementation reconciles with Phase 2.2
    om = {r["metric_id"]: (r["numerator"], r["denominator"]) for r in rd("offer_metric_baseline.csv")}
    mc = {r["metric_id"]: (r["numerator"], r["denominator"]) for r in rd("metric_calculations.csv")}
    for a, b in (("OAM-01", "M-B1"), ("OAM-02", "M-B0"), ("OAM-09", "M-B4"), ("OAM-01b", "M-B10")):
        if om[a] != mc[b]:
            fail.append(f"{a} {om[a]} != {b} {mc[b]}")

    # 7. documents: fractions traceable, IDs resolve, no intervals, grain labelled
    known = known_fractions()
    for name in DOCS:
        p = OUT / name
        if not p.is_file():
            fail.append(f"missing {name}")
            continue
        text = p.read_text()
        bad = sorted(set(re.findall(r"(?<![\d.-])\d+/\d+(?![\d/])", text)) - known)
        if bad:
            fail.append(f"{name}: untraceable fractions {bad}")
        for x in set(re.findall(r"\b((?:DEC|REJ)-\d{3})\b", text)) - dec:
            fail.append(f"{name}: unknown decision {x}")
        for x in set(re.findall(r"\b(ASM-\d{3})\b", text)) - asm:
            fail.append(f"{name}: unknown assumption {x}")
        for x in set(re.findall(r"\b(DQ-\d{2})\b", text)) - dqs:
            fail.append(f"{name}: unknown DQ {x}")
        for x in set(re.findall(r"\b(C-\d{2})\b", text)) - cq:
            fail.append(f"{name}: unknown customer question {x}")
        for x in set(re.findall(r"\b(SM-B\d-[\dG]+\d?)\b", text)) - smids:
            fail.append(f"{name}: unknown success metric {x}")
        if re.search(r"95% CI|ci95|confidence interval", text, re.I):
            fail.append(f"{name}: sampling interval mentioned")
        for line in text.splitlines():
            if "24/28" in line and not re.search(r"candidate|excluding|OAM-01b|OAM-09|M-B4|M-B10|prior-hire", line, re.I):
                fail.append(f"{name}: unlabelled 24/28 -> {line[:80]}")
            if re.search(r"\bmerg", line, re.I) and not re.search(r"\b(no|never|not|nothing|without|warning-only)\b|n't", line, re.I):
                fail.append(f"{name}: merge mentioned without a no-merge qualifier -> {line[:80]}")
            if re.search(r"will (increase|improve|raise) (offer )?acceptance", line, re.I):
                fail.append(f"{name}: causal claim -> {line[:80]}")
    return fail


def main() -> int:
    f = check()
    for x in f:
        print("FAIL", x)
    print(f"phase3 checks: {'PASS' if not f else f'{len(f)} failures'}")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
