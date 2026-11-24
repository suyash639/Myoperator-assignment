"""Phase 4 packaging: builds the generated parts of outputs/final/ from validated outputs (no new analysis).

    uv run python -m src.final_package

* Findings_and_Data_Audit.csv: every Observed_Value is read from a validated CSV by ID (never typed by hand).
* Fills <!-- GEN:name --> ... <!-- /GEN:name --> blocks in the final Markdown files with tables generated from
  phase3_capacity_allocation.csv, product_success_metrics.csv, decision_log.md, assumptions_register.md.
Reads only outputs/ and audit/. Does not touch data/raw.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

OUT, FINAL, AUDIT = Path("outputs"), Path("outputs/final"), Path("audit")


def _rows(name):
    return list(csv.DictReader((OUT / name).open()))


def sources() -> dict[str, dict]:
    """ID -> {num, den, pct, value, file}. Later files never overwrite an ID from an earlier file."""
    idx: dict[str, dict] = {}
    spec = [("metric_calculations.csv", "metric_id", "numerator", "denominator", "value_pct", "value"),
            ("offer_metric_baseline.csv", "metric_id", "numerator", "denominator", "value", "value"),
            ("dq_issues.csv", "issue_id", "affected_records", "denominator", "pct_affected", "pct_affected"),
            ("phase3_1_evidence.csv", "evidence_id", "numerator", "denominator", "", ""),
            ("phase2_1_checks.csv", "check_id", "numerator", "denominator", "pct", "pct")]
    for f, idc, n, d, p, v in spec:
        for r in _rows(f):
            key = r[idc] if f != "phase2_1_checks.csv" else f"{r[idc]}|{r['check']}"
            if key in idx:
                continue
            pct = r.get(p, "") if p else ""
            if f == "dq_issues.csv" and pct:
                pct = f"{pct}%"
            if not pct and r[n] not in ("", None) and r[d] not in ("", "0", None):
                try:
                    pct = f"{100 * int(r[n]) / int(r[d]):.1f}%"
                except ValueError:
                    pct = ""
            idx[key] = {"num": r[n], "den": r[d], "pct": pct, "value": r.get(v, ""), "file": f, "row": r}
    return idx


def fv(idx, key, label=True) -> str:
    """'num/den = pct [ID]' read from the source."""
    if key not in idx:
        raise KeyError(f"source id not found: {key}")
    s = idx[key]
    if s["num"] in ("", None):
        return f"{s['value']} (n={s['den']}) [{key.split('|')[0]}]" if label else s["value"]
    core = f"{s['num']}/{s['den']}" + (f" = {s['pct']}" if s["pct"] else "")
    return f"{core} [{key.split('|')[0]}]" if label else core


def chk(idx, cid, text):
    """phase2_1_checks lookup by id + check text fragment."""
    k = next(k for k in idx if k.startswith(cid + "|") and text in k)
    return fv(idx, k)


COLS = ["Finding_ID", "Theme", "Claim_or_Question", "Metric", "Observed_Value", "Calculation_or_Method", "Evidence_Source",
        "Statement_Type", "Confidence", "Data_Quality_Impact", "Product_Decision_Impact", "Caveat"]


def findings(idx) -> list[dict]:
    jb_rates = [idx[f"{p}-Job Board"] for p in ("M-A7", "M-A7r", "M-A7s", "M-A7m", "M-A7f")]
    lo = min(jb_rates, key=lambda r: int(r["num"]) / int(r["den"]))
    hi = max(jb_rates, key=lambda r: int(r["num"]) / int(r["den"]))
    others = [r for k, r in idx.items() if re.match(r"M-A7[rsmf]?-", k) and not k.endswith("Job Board") and r["num"] not in ("", "0")]
    next_low = min(others, key=lambda r: int(r["num"]) / int(r["den"]))
    share_vars = [idx[k] for k in ("M-A0", "M-A1", "M-A2", "M-A3", "M-A8", "M-A9", "M-A10")]
    s_lo = min(share_vars, key=lambda r: int(r["num"]) / int(r["den"]))
    s_hi = max(share_vars, key=lambda r: int(r["num"]) / int(r["den"]))
    F = []

    def add(theme, claim, metric, observed, method, src, stype, conf, dq, prod, cav):
        F.append(dict(zip(COLS, (f"FND-{len(F) + 1:02d}", theme, claim, metric, observed, method, src, stype, conf, dq, prod,
                                 cav or "No caveat beyond those in the evidence source"))))

    add("Claim A", "Do job boards contribute 26.9% of hires?", "Job Board share of hires (Source as recorded)",
        f"{fv(idx, 'M-A0')}; definition range {s_lo['pct']} to {s_hi['pct']} across 7 attribution variants",
        "Stage=Hired applications joined to Candidates.Source; variants M-A1, M-A2, M-A3, M-A8, M-A9, M-A10",
        "metric_calculations.csv M-A0..M-A10; verification.csv", "Fact", "High (arithmetic); Medium (attribution)",
        "Depends on Candidates.Source, which conflicts with Referred By (FND-05)", "Figure reproduced; does not by itself justify integration work",
        "One hire moves the share by 3.8 percentage points")
    add("Claim A", "Are job boards a high-volume channel?", "Job Board share of applications", fv(idx, "M-A5"),
        "Applications joined to Candidates.Source", "metric_calculations.csv M-A5", "Fact", "High",
        "Source is candidate-level, not application-level", "Volume is already the largest; volume is not shown to be the constraint", "")
    add("Claim A", "How efficiently do job-board applications convert to hires?", "Job Board hire rate per application",
        f"{fv(idx, 'M-A7-Job Board')}; range {lo['num']}/{lo['den']} = {lo['pct']} to {hi['num']}/{hi['den']} = {hi['pct']} across 5 attributions; "
        f"next-lowest channel with hires {next_low['pct']}",
        "Hires / applications per channel under Source as recorded, referrer override, strict referral, two merged first-touch rules",
        "metric_calculations.csv M-A7*, M-A7r*, M-A7s*, M-A7m*, M-A7f*", "Fact", "High",
        "Attribution conflicts move individual hires but not the ranking", "Primary evidence against prioritising job-board integration in Q3 (N1)",
        "Lowest yield does not show what an integration would change; integration friction is unmeasured (C-12)")
    add("Claim A", "Do job-board candidates fall behind at interview?", "Offer rate after interview: Job Board", fv(idx, "M-Q2-Job Board"),
        "Offered / interviewed applications, Source as recorded", "metric_calculations.csv M-Q2-*", "Fact", "Medium",
        "Interview records may be incomplete (FND-16)", "Context for N1; not a basis for an interview feature", "Other channels have n = 10-16 interviewed applications")
    add("Attribution", "Is the referral channel reliably attributed?", "Referral-labelled hires without a referrer link",
        f"{fv(idx, 'M-A9n')}; hires with any referrer link {fv(idx, 'M-A9r')}; Source vs Referred By conflicts {fv(idx, 'DQ-01')}",
        "Candidates.Source x Applications.Referred By", "metric_calculations.csv M-A9n, M-A9r; dq_issues.csv DQ-01", "Fact (Confirmed defect)", "High",
        "Channel attribution is unreliable at record level", "Motivates B3; Referral is not a proven high-performing channel (N3)",
        "Which field is authoritative is unknown (C-04)")
    add("Claim B", "What is offer acceptance at the decision event?", "Decided Offer Acceptance Rate (offer-level; provisional primary)",
        fv(idx, "OAM-01"), "Offers accepted at a decision event / offers with a decision event on or before the as-of date (event-time)",
        "offer_metric_baseline.csv OAM-01; metric_calculations.csv M-B1", "Fact", "Medium",
        "Status data unreliable (FND-09)", "Primary D3 metric (DEC-016, DEC-029, DEC-038)", "No target or benchmark exists (C-13)")
    add("Claim B", "Where does the VP's ~72% come from?", "All-Issued Offer Acceptance Ratio", fv(idx, "OAM-02"),
        "Accepted / all counted offers including Pending", "offer_metric_baseline.csv OAM-02; metric_calculations.csv M-B0", "Fact", "High",
        "Counts unresolved Pending offers as non-acceptance", "Kept as a separately labelled ratio, not the acceptance rate",
        f"Scenario range: stale Pending as expired {fv(idx, 'M-B3', False)}; upper bound {fv(idx, 'M-B2', False)}")
    add("Claim B", "Is candidate-level acceptance different?", "Candidate-level decided acceptance (secondary)", fv(idx, "OAM-09"),
        "Candidates with at least 1 accepted offer / candidates with at least 1 decided offer", "offer_metric_baseline.csv OAM-09; M-B4",
        "Fact", "Medium", "4 candidates hold 2 offers", "Reported separately; never combined with offer-level OAM-01", "Different grain from OAM-01")
    add("Offer lifecycle", "Are Pending offers really pending?", "Pending offers carrying a Decision On",
        f"{fv(idx, 'DQ-06')}; pending count {idx['OAM-03']['value']}; older than 30 days {fv(idx, 'DQ-07')}",
        "Status = Pending AND Decision On present; age at provisional cutoff 2026-08-27", "dq_issues.csv DQ-06, DQ-07; offer_metric_baseline.csv OAM-03",
        "Fact (Confirmed defect)", "High", "No Expired/Withdrawn/Rescinded status exists", "Core motivation for B1",
        f"Cutoff unconfirmed: at 2026-11-24 all 5 are older than 30 days and the stale-as-expired scenario equals {fv(idx, 'M-B3-2026-11-24', False)}")
    add("Offer lifecycle", "Are offers made to people already hired?", "Offers to candidates already hired via another application",
        f"{fv(idx, 'DQ-29')}; decided offers among them {fv(idx, 'M-B9')}", "Earlier Hired application with decision before this offer",
        "dq_issues.csv DQ-29; metric_calculations.csv M-B9, M-B10", "Fact (Suspicious pattern)", "Medium",
        "Inside the OAM-01 denominator", "Flagged in D3; OAM-01b variant excludes them", "Possibly internal moves (C-08)")
    add("Offer lifecycle", "Are offer and closing dates consistent?", "Applications closed before the offer decision",
        f"hires {fv(idx, 'DQ-18')}; declines {fv(idx, 'DQ-26')}; offer start before decision {chk(idx, 'R10-dates', 'Decision On <= Proposed Start')}",
        "Applications.Closed On vs Offers.Decision On; Offers date order", "dq_issues.csv DQ-18, DQ-26; phase2_1_checks.csv R10-dates",
        "Fact (Suspicious pattern)", "Medium", "Closed On meaning undocumented", "Hire date taken from the decision event (DEC-011); B1 records event dates", "C-06")
    add("Funnel", "Where does the funnel lose applications?", "Evidence-based stage reach (full snapshot)",
        f"{idx['M-F0']['num']} -> {idx['M-F1']['num']} -> {idx['M-F2']['num']} -> {idx['M-F3']['num']} -> {idx['M-F4']['num']}; "
        f"screened->interviewed {fv(idx, 'M-FC-interviewed', False)}; interviewed->offered {fv(idx, 'M-FC-offered', False)}; "
        f"largest drop {idx['M-F-leak']['value']}",
        "Screened On present; at least 1 interview; at least 1 offer; Stage Hired", "metric_calculations.csv M-F*, M-FC*, M-F-leak; verification.csv",
        "Fact", "High (counts)", "Mixed-maturity snapshot, not a cohort", "Context; no funnel feature is in Q3 scope", "Interview counts are a lower bound (FND-16)")
    add("Funnel", "Does a completed cohort tell the same story?", "Completed cohort (applications 2025-07-01 to 2026-03-31)",
        f"eligible {idx['M-K-eligible']['num']}; hired {fv(idx, 'M-KF4', False)}; interviewed->offered {fv(idx, 'M-KC-offered', False)}; "
        f"offers still pending {fv(idx, 'M-K-pending', False)}",
        "Closed or stalled (>90 days) applications in window (DEC-021, DEC-022)", "metric_calculations.csv M-K*", "Fact", "Medium",
        "Eligibility rule is an analyst proposal (DEC-022)", "Confirms the snapshot shape", f"Offer->hire step n = {idx['M-KC-hired']['den']}")
    add("Pipeline hygiene", "Are Active applications actually being worked?", "Active applications with no activity > 90 days",
        f"{fv(idx, 'DQ-28')}; at 30 days {fv(idx, 'E-B2-30')}; at 180 days {fv(idx, 'E-B2-180')}; on Filled openings "
        f"{chk(idx, 'R5-active-on-filled', 'Filled')}",
        "Latest of applied, screened, interview, offer, decision dates vs provisional cutoff", "dq_issues.csv DQ-28; phase3_1_evidence.csv E-B2-*",
        "Fact (Suspicious pattern)", "Medium", "Inactivity is a flag, not confirmed abandonment", "Motivates B2; Pilot 1 is the stop condition",
        "Highly threshold- and cutoff-sensitive (104/105 at 2026-11-24, DQ-28 detail)")
    add("Pipeline hygiene", "Does opening status match hiring activity?", "Openings whose Status contradicts their applications",
        f"{fv(idx, 'DQ-11')}; Open openings past Target Close {fv(idx, 'DQ-12')}", "Status and headcount vs hired/Active applications",
        "dq_issues.csv DQ-11, DQ-12", "Fact (Confirmed defect)", "High", "Fill rate and open-requisition counts unreliable",
        "B2 raises review flags; never auto-corrects", "DQ-12 is cutoff-sensitive")
    add("Dates", "Are interview dates consistent?", "Interview chronology and copy-vs-source agreement",
        f"interview before application {chk(idx, 'R10-dates', 'Applied On <= Interviews.Scheduled On')}; copied First Interview On differs "
        f"from Interviews table {fv(idx, 'DQ-15')}; Final Interview On after every recorded interview {fv(idx, 'DQ-16')}",
        "Pairwise date checks; Applications copied fields vs Interviews table", "dq_issues.csv DQ-13, DQ-15, DQ-16; phase2_1_checks.csv R10-*",
        "Fact (Confirmed defect / Suspicious pattern)", "Medium", "Neither source is authoritative (DEC-019)",
        "No interview feature in Q3 (X1 backlog)", "Interviews table may lack rounds; scope unknown (C-05)")
    add("Duplicates", "Are there duplicate candidate identities?", "Candidates in name+phone pairs",
        f"{fv(idx, 'DQ-02')}; same candidate hired twice {fv(idx, 'DQ-04')}; the name+phone warning would fire on {idx['E-B3-dup-1']['num']} groups and on {idx['E-B3-dup-2']['num']} name-only collisions",
        "Normalised full name AND phone", "dq_issues.csv DQ-02, DQ-04; phase3_1_evidence.csv E-B3-dup-*", "Fact (Suspicious pattern)", "Medium",
        "4/6 pairs have experience values implausible for one person (DQ-02 detail)", "B3 warning-only duplicate check; first scope cut",
        "Whether pairs are the same people is unconfirmed (C-07)")
    add("Departments", "Does any department explain outcomes?", "Engineering hires per application",
        f"{fv(idx, 'M-DF-Engineering-hired')}; interviewed {fv(idx, 'M-DF-Engineering-interviewed', False)}",
        "Applications by opening department", "metric_calculations.csv M-DF-*", "Fact", "Low (small n)",
        "Engineering opening REQ-2026-017 Filled with 0 hires (DQ-11)", "No department feature; question C-10", "Every department has fewer than 10 decided offers (OAM-07)")
    add("Compensation", "Can compensation explain declines?", "Offers far from candidate Expected CTC",
        f"{fv(idx, 'DQ-25')}", "Base CTC / Expected CTC outside 0.67-1.5x", "dq_issues.csv DQ-25", "Fact (Suspicious pattern)", "Medium",
        "No units defect found; candidates often outside the role's band", "Rules out comp-driven tooling (N2)", "Currency/period assumed INR annual (ASM-016)")
    add("Measurability", "Can feedback latency be measured?", "Interviews with Completed On equal to Scheduled On", fv(idx, "DQ-24"),
        "Count of equal dates; no feedback timestamp exists", "dq_issues.csv DQ-24", "Fact (Model limitation)", "High",
        "Feedback turnaround unmeasurable", "No feedback-latency feature can be evidenced", "")
    add("Snapshot", "What date does the data describe?", "Records bulk-created within one minute",
        f"{fv(idx, 'DQ-22')}; Candidate Created On after import {chk(idx, 'R10-dates', 'bulk-import')}",
        "createdTime range; date fields after import", "dq_issues.csv DQ-22; phase2_1_checks.csv R10-dates", "Fact", "High",
        "Business cutoff unconfirmed (DEC-020)", "Ages and stale counts shown at 3 cutoffs", "Extraction 2026-11-24; import 2026-08-27 (C-01)")
    return F


# ------------------------------------------------------------------ generated Markdown blocks
def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def gen_blocks() -> dict[str, str]:
    al = _rows("phase3_capacity_allocation.csv")
    sm = _rows("product_success_metrics.csv")
    blocks = {}
    blocks["allocation"] = md_table(
        ["Component", "Build", "Sprint", "Discipline", "Engineer-weeks", "First cut", "What"],
        [(r["component_id"], r["build"], r["sprint"], r["discipline"], f"{float(r['engineer_weeks']):.2f}", r["first_cut"] or "",
          r["description"]) for r in al]) + \
        f"\n\n**Total: {sum(float(r['engineer_weeks']) for r in al):.1f} engineer-weeks.** Every row is labelled *{al[0]['estimate_status']}*."
    for b in ("B1", "B2", "B3"):
        blocks[f"sm_{b}"] = md_table(["ID", "Type", "Metric", "Baseline", "Target or decision rule", "Status"],
                                     [(r["metric_id"], r["metric_type"], r["metric"], r["baseline"], r["target_or_decision_rule"], r["target_status"])
                                      for r in sm if r["build"] == b])
    blocks["sm_all"] = md_table(["ID", "Build", "Type", "Metric", "Baseline (source)", "Target or decision rule", "Window", "Owner", "Guardrail for"],
                                [(r["metric_id"], r["build"], r["metric_type"], r["metric"],
                                  f"{r['baseline']} ({r['baseline_ref'] or 'none'})", f"{r['target_or_decision_rule']} — *{r['target_status']}*",
                                  r["evaluation_window"], r["owner"], r["guardrail_for"] or "") for r in sm])
    sc = sorted(_rows("phase3_prioritisation_scores.csv"), key=lambda r: int(r["weighted_rank"]))
    blocks["scores"] = md_table(["ID", "Initiative", "Decision", "Weighted score (rank)", "Equal-weight rank", "Rank without effort"],
                                [(r["candidate_id"], r["initiative"], r["decision"], f"{r['weighted_score']} ({r['weighted_rank']})",
                                  r["equal_weight_rank"], r["rank_without_effort"]) for r in sc])
    blocks["worked_example"] = worked_example()
    log = (AUDIT / "decision_log.md").read_text()
    dec_rows = [l for l in log.splitlines() if re.match(r"^\| (DEC|REJ)-\d{3} \|", l)]
    parsed = {}
    for l in dec_rows:
        c = [x.strip() for x in l.strip().strip("|").split(" | ")]
        if c[0].startswith("DEC"):
            parsed[c[0]] = {"decision": c[2], "approval": c[3], "status": c[-1]}
    readiness = {}
    for l in log.splitlines():
        m = re.match(r"^\| (DEC-\d{3}) ([^|]*)\| ([^|]*)\| ([^|]*)\| ([^|]*)\|$", l)
        if m:
            readiness[m.group(1)] = (m.group(3).strip(), m.group(4).strip(), m.group(5).strip())

    def short(t, n=230):
        t = re.sub(r"\s+", " ", t)
        t = public_redact(t)
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"

    def cat(d):
        a, st = d["approval"], d["status"]
        if st.startswith("**Superseded") or st.startswith("Superseded"):
            return "Superseded"
        if a.startswith("PM-approved") or a.startswith("**PM-approved") or a.startswith("PM instruction"):
            return "Approved"
        if a.startswith("Analyst process"):
            return "Process (no metric impact)"
        return "Proposed"

    groups = {}
    for k in sorted(parsed):
        groups.setdefault(cat(parsed[k]), []).append(k)
    for g in ("Approved", "Proposed", "Superseded", "Process (no metric impact)"):
        rows = []
        for k in groups.get(g, []):
            d = parsed[k]
            r = readiness.get(k)
            extra = (f"Approve now: {r[0]}; Acme: {r[1]}; Engineering: {r[2]}" if r else "")
            rows.append((k, short(d["decision"]), d["approval"], short(d["status"], 160), extra))
        blocks[f"dec_{g.split()[0].lower()}"] = md_table(["ID", "Decision", "Approval recorded in log", "Status in log", "Readiness (log §G)"], rows)
    reg = (AUDIT / "assumptions_register.md").read_text()
    arows = []
    for l in reg.splitlines():
        if re.match(r"^\| ASM-\d{3} \|", l):
            c = [x.strip() for x in l.strip().strip("|").split(" | ")]
            arows.append((c[0], short(c[1], 200), c[2], short(c[-2], 80), short(c[-1], 140)))
    blocks["asm"] = md_table(["ID", "Assumption", "Type", "Owner to validate", "Status"], arows)
    return blocks


def worked_example() -> str:
    """OAM-01 / OAM-13a / OAM-13b computed by the event-time reference implementation (src/offer_metrics.event_metrics)."""
    from src import offer_lifecycle as lc
    from src.offer_metrics import event_metrics
    T = "2026-06-30T12:00:00Z"

    def offer(oid, app):
        return lc.Offer(id=oid, application_id=app, offered_on="2026-03-01")
    a = offer("A", "app-A")                       # accepted 03-05, candidate reneges 03-20
    lc.transition(a, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-05", recorded_at=T)
    lc.transition(a, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-20", recorded_at=T, reason="reneged")
    b = offer("B", "app-B")                       # declined 03-04
    lc.transition(b, lc.DECLINED, actor="r", role="recruiter", business_date="2026-03-04", recorded_at=T, reason="Location")
    c = offer("C", "app-C")                       # accepted 03-06, company rescinds 03-22
    lc.transition(c, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-06", recorded_at=T)
    lc.transition(c, lc.RESCINDED, actor="hm", role="hiring_manager", business_date="2026-03-22", recorded_at=T, reason="role closed")
    offers = {"A": a, "B": b, "C": c}
    rows = []
    for as_of, note in (("2026-03-02", "all three offers issued, no decisions yet"),
                        ("2026-03-10", "A accepted, B declined, C accepted; no later events yet"),
                        ("2026-04-01", "A has since reneged, C has since been rescinded")):
        ev = event_metrics(offers, as_of)
        acc, dec = len(ev["accepted"]), len(ev["decided"])
        rows.append((as_of, note, f"{acc} / {dec}", f"{len(ev['renege'])} / {acc}", f"{len(ev['rescinded_after'])} / {acc}",
                     ", ".join(sorted(ev["pending"])) or "none", ", ".join(f"{k}: {o.status}" for k, o in offers.items())))
    return md_table(["As-of date", "Situation", "OAM-01 accepted / decided", "OAM-13a reneged / accepted",
                     "OAM-13b rescinded / accepted", "Pending at as-of", "Latest status (not used by any metric)"], rows)


def _local_secret_values() -> list[tuple[str, str]]:
    """Exact local values to redact (base ID, token fingerprint), read from .env; never printed or written."""
    env = Path(".env")
    if not env.exists():
        return []
    vals = {}
    for line in env.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    out = []
    if vals.get("AIRTABLE_BASE_ID"):
        out.append((vals["AIRTABLE_BASE_ID"], "<AIRTABLE_BASE_ID>"))
    if vals.get("AIRTABLE_TOKEN"):
        from src.airtable_client import token_fingerprint
        out.append((token_fingerprint(vals["AIRTABLE_TOKEN"]), "(fingerprint recorded locally only)"))
    return out


def public_redact(t: str) -> str:
    """Remove credential metadata from public-facing text: the exact local base ID and token fingerprint, plus
    context-anchored fingerprint and token length/prefix phrases. Synthetic test values are left untouched."""
    t = re.sub(r"\(fingerprint [0-9a-f]{6,}\)", "(fingerprint recorded locally only)", t)
    t = re.sub(r"fingerprint(?: sha256\[:8\])? ?=? ?[0-9a-f]{8}\b", "fingerprint (recorded locally only)", t)
    t = re.sub(r"\(len \d+, `?(?:pat|app)`? prefix\)", "(length and prefix checked locally)", t)
    for value, repl in _local_secret_values():
        t = t.replace(value, repl)
    return t


def fill(path: Path, blocks: dict[str, str]) -> None:
    s = path.read_text()
    for name, body in blocks.items():
        s = re.sub(rf"<!-- GEN:{name} -->.*?<!-- /GEN:{name} -->",
                   lambda _m: f"<!-- GEN:{name} -->\n{body}\n<!-- /GEN:{name} -->", s, flags=re.S)
    path.write_text(s)


def main() -> int:
    FINAL.mkdir(exist_ok=True)
    idx = sources()
    F = findings(idx)
    with (FINAL / "Findings_and_Data_Audit.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(F)
    blocks = gen_blocks()
    for p in FINAL.glob("*.md"):
        fill(p, blocks)
    print(f"findings={len(F)}; generated blocks={len(blocks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
