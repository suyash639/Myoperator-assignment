"""Phase 3 plan data: prioritisation scores and capacity allocation (single source of truth).

    uv run python -m src.phase3_plan     # writes outputs/phase3_prioritisation_scores.csv, outputs/phase3_capacity_allocation.csv

Scores are judgements against written anchors (outputs/phase3_product_strategy.md §4); this module only makes the
arithmetic, ranking and weight-sensitivity reproducible. Effort figures are PM PLANNING ESTIMATES, not engineering
estimates (DEC-008, ASM-022): they must be validated by engineering before sprint 1 is committed.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

OUT = Path("outputs")

CRITERIA = ["user_value", "evidence_strength", "business_impact", "time_to_value", "effort", "delivery_risk", "dependency_risk"]
WEIGHTS = {"user_value": 0.20, "evidence_strength": 0.20, "business_impact": 0.15, "time_to_value": 0.10,
           "effort": 0.15, "delivery_risk": 0.10, "dependency_risk": 0.10}

# id: (name, decision, scores in CRITERIA order, one-line justification per score is in the strategy doc)
CANDIDATES = {
    "B1": ("Offer lifecycle integrity and acceptance reporting", "Build", (4, 5, 5, 4, 3, 4, 4)),
    "B2": ("Pipeline hygiene: inactivity flags and opening-status review", "Build", (4, 3, 4, 4, 3, 4, 3)),
    "B3": ("Source attribution integrity and intake instrumentation", "Build", (3, 5, 4, 3, 4, 4, 3)),
    "N1": ("Job-board integration (new or deeper board connectors)", "Non-build (defer pending validation)", (2, 1, 2, 2, 1, 2, 1)),
    "N2": ("Offer-acceptance improvement tooling (comp intelligence, candidate nudges)", "Non-build", (2, 1, 2, 2, 2, 3, 2)),
    "N3": ("Referral programme features", "Non-build", (2, 1, 2, 3, 3, 4, 3)),
    "X1": ("Interview scheduling and feedback-latency tooling", "Backlog (not prioritised)", (3, 2, 3, 3, 2, 3, 2)),
    "X2": ("Department cycle-time analytics", "Backlog (not prioritised)", (2, 1, 2, 4, 4, 4, 3)),
}

BUILD_EFFORT = {"B1": 2.5, "B2": 2.0, "B3": 1.5}
TOTAL_CAPACITY = 6.0

# component id, build, sprint, discipline, engineer-weeks, description
ESTIMATE_STATUS = "PM planning estimate (not validated by engineering)"

ALLOCATION = [
    ("B1.1", "B1", 1, "Backend", 1.00, "Offer lifecycle per src/offer_lifecycle.py: statuses Expired, Withdrawn, Rescinded, Superseded; role-checked transitions; "
                                       "field invariants (no resolution date on Pending, decision_on only for decided/reneged offers); append-only event log "
                                       "(business_date + recorded_at); audited correction; legacy conflicts flagged, never rewritten"),
    ("B2.1", "B2", 1, "Backend", 0.75, "Inactivity detector with org-level, per-stage configurable threshold (default 90 days, range 14-365, changes audited) "
                                       "and opening-status review flags (Filled/Cancelled with Active applications; Open with hires >= headcount; Cancelled with hires). "
                                       "Flags only: the system never changes an application or opening status"),
    ("B3.1", "B3", 1, "Backend", 0.25, "Application-level acquisition source (controlled taxonomy, src/duplicate_warning.py), system-derived intake method, "
                                       "referral attribution rules (direct referral vs endorsement)"),
    ("B1.2", "B1", 2, "Frontend", 0.50, "Pending-offer queue: age buckets, conflict badge, resolve via allowed transitions only (reason where required)"),
    ("B2.2", "B2", 2, "Frontend", 0.75, "Inactivity review queue (flag labelled 'Inactive > N days', never 'abandoned'); dispositions: still active (snooze with reason), "
                                        "close - recruiter-confirmed abandoned, close - other reason, advance; reversible 30 days; opening review banner with "
                                        "resolve/dismiss-with-reason"),
    ("B3.2", "B3", 2, "Backend", 0.25, "Duplicate warning service (name AND phone match; remembered 'different person' pairs; ops review queue). WARNING ONLY. First cut"),
    ("B3.3a", "B3", 2, "Frontend", 0.25, "Intake form: source picker from taxonomy, source detail, referrer picker, endorsement confirmation"),
    ("B3.3b", "B3", 2, "Frontend", 0.25, "Duplicate warning dialog: same person (attach to existing record) / different person (reason) / unsure. No merge. First cut"),
    ("B1.3", "B1", 3, "Data/analytics", 0.50, "D3 metrics (OAM-01..OAM-13b) computed at event time, with reliability tiers and the proposed privacy policy; dashboard tiles; reconciliation"),
    ("B1.4", "B1", 3, "QA", 0.50, "Transition, role, invariant and audit-log tests; legacy flag check (expect 4 conflicts on snapshot); metric reconciliation"),
    ("B2.3", "B2", 3, "Data/analytics", 0.25, "Live baseline capture (inactivity at 60/90/120 days) and hygiene scorecard"),
    ("B2.4", "B2", 3, "QA", 0.25, "Threshold configuration, flag-not-correct and reversible-close tests"),
    ("B3.4", "B3", 3, "Data/analytics", 0.25, "Attribution report: source as recorded, direct referrals vs endorsements, intake-method mix, conflict count"),
    ("B3.5", "B3", 3, "QA", 0.25, "Taxonomy/referral validation and duplicate-warning tests (no-merge guarantee, remembered pairs)"),
]


# Success metrics. baseline_ref must name metric/check IDs whose numerator/denominator equal the quoted baseline.
SM_COLS = ["metric_id", "build", "metric", "metric_type", "baseline", "baseline_ref", "baseline_status",
           "target_or_decision_rule", "target_status", "measurement_method", "data_source", "evaluation_window",
           "owner", "guardrail_for"]
SUCCESS_METRICS = [
    ("SM-B1-1", "B1", "New offers saved with a status/decision-date contradiction", "data_quality",
     "4/5 Pending offers carry a Decision On (snapshot)", "OAM-03c;DQ-06", "Measured on snapshot; re-measure on live data at release",
     "0 after release", "Firm (enforced by B1.1 constraint)", "Count of offers created or updated after release violating the rule",
     "TalentFlow offers table (audit log)", "Continuous from release", "Engineering lead", ""),
    ("SM-B1-2", "B1", "Share of pre-existing Pending offers resolved (true status + date) within 30 days of pilot start", "adoption",
     "5 Pending, of which 4 conflicting (snapshot); live count recorded at release", "OAM-03;OAM-03c", "Live baseline at release",
     "Decision rule: >= 80% resolved in 30 days -> queue works; below -> interview recruiters on blockers", "Provisional decision rule",
     "Resolved / Pending at pilot start", "Pending-offer queue events", "Pilot day 0-30", "Acme recruiting ops lead", ""),
    ("SM-B1-3", "B1", "Reported acceptance figure in VP review uses OAM-01 with counts, OAM-02 labelled as ratio, and pending backlog", "outcome",
     "VP currently quotes ~72% (all-issued ratio) as 'acceptance'", "OAM-02;M-B0", "Observed (VP claim)",
     "Yes/No at the end-of-Q3 VP review", "Firm (binary)", "Review of the deck/report used", "VP review materials", "End of sprint 3 review",
     "PM", ""),
    ("SM-B1-4", "B1", "Pending offers older than 30 days with no Expires On and no update in 30 days, at month end", "outcome",
     "3/5 Pending older than 30 days at provisional cutoff 2026-08-27 (5/5 at 2026-11-24)", "DQ-07;OAM-04-over30-2026-11-24",
     "Snapshot; cutoff-sensitive; live baseline at release", "0 at each month end after the backlog is resolved",
     "Provisional (threshold depends on expiry policy C-03)", "Month-end count", "TalentFlow offers", "Monthly, 2 months post-release",
     "Acme recruiting ops lead", ""),
    ("SM-B1-G1", "B1", "Status accuracy: share of queue resolutions confirmed correct in a monthly 10-offer audit sample", "guardrail",
     "No baseline (new workflow)", "", "None; measured from first audit", "Threshold: < 90% confirmed -> pause bulk resolution, review reasons",
     "Provisional guardrail", "Recruiting-ops lead reviews 10 random resolutions vs email/ATS evidence", "Queue events + manual review",
     "Monthly", "Acme recruiting ops lead", "SM-B1-2"),
    ("SM-B1-G3", "B1", "Offer status changes without an audit event", "guardrail",
     "Not measurable today (no event log exists)", "", "None", "0", "Firm (enforced: status changes only via the event log)",
     "Reconcile current status with last event per offer", "Offer event log", "Continuous", "Engineering lead", "SM-B1-1"),
    ("SM-B1-G2", "B1", "Accepted offers whose application is not Hired (consistency)", "guardrail",
     "0/26 (snapshot)", "OAM-10", "Measured on snapshot", "Remains 0", "Firm", "Daily metric job", "TalentFlow offers + applications",
     "Continuous", "Engineering lead", "SM-B1-1"),
    ("SM-B2-1", "B2", "Share of inactivity-flagged applications dispositioned within 30 days of being flagged", "adoption",
     "No baseline (feature does not exist)", "", "None", "Decision rule: >= 50% in pilot -> continue; < 50% -> review UX and threshold with recruiters",
     "Provisional decision rule", "Dispositioned / flagged, per flag cohort", "Stalled-queue events", "Pilot day 0-30 and 31-60",
     "PM", ""),
    ("SM-B2-2", "B2", "Inactivity-flag share of Active applications (no recorded activity > configured threshold, default 90 days; a flag, not confirmed abandonment)", "outcome",
     "50/105 Active (snapshot, provisional cutoff); 104/105 at extraction date", "DQ-28",
     "Snapshot is ~3 months old: live baseline required (B2.3, sprint 3)",
     "No numerical target until live baseline; proposed intent: halve the live baseline within one quarter of pilot", "Not set (pending live baseline)",
     "Stall detector, weekly", "TalentFlow applications", "Weekly for 1 quarter post-release", "Acme recruiting ops lead", ""),
    ("SM-B2-3", "B2", "Openings whose Status contradicts their applications and are not flagged", "data_quality",
     "15/24 openings contradictory (snapshot)", "DQ-11", "Measured on snapshot", "0 unflagged after release; decision rule: >= 50% of flags resolved within 14 days",
     "Firm (flags) / Provisional (resolution rule)", "Requisition rule job", "TalentFlow job openings + applications", "Continuous; resolution reviewed at day 14 and 30",
     "Acme recruiting ops lead", ""),
    ("SM-B2-4", "B2", "Active applications on Filled openings", "outcome",
     "55/105 Active applications (snapshot)", "R5-active-on-filled;DQ-28", "Snapshot; live baseline at release", "No numerical target until live baseline",
     "Not set (pending live baseline)", "Requisition rule job", "TalentFlow applications + job openings", "Weekly for 1 quarter", "PM", ""),
    ("SM-B2-5", "B2", "Share of reviewed inactivity flags that the recruiter confirms as abandoned (pilot: 20 sampled applications)", "outcome",
     "No baseline: inactivity flags are not abandonment (50/105 flagged at 90 days is a flag rate)", "", "None; measured in Pilot 1",
     "Decision rule: < 50% confirmed abandoned in the 20-application pilot -> cut the queue to opening flags only", "Provisional decision rule",
     "Recruiter classification of 20 randomly sampled flagged applications", "Pilot 1 review sheet", "Sprint 2", "PM", ""),
    ("SM-B2-G1", "B2", "Closed-by-disposition applications reopened within 30 days", "guardrail",
     "No baseline (new workflow)", "", "None", "Threshold: > 5% -> raise stall threshold / review reasons", "Provisional guardrail",
     "Reopen events / disposition closes", "Stalled-queue events", "Rolling 30 days", "PM", "SM-B2-1;SM-B2-2"),
    ("SM-B3-1", "B3", "New applications with Source/Referred By contradiction", "data_quality",
     "34/350 applications (9.7%, snapshot)", "DQ-01", "Measured on snapshot", "0 for applications created after release",
     "Firm (enforced by B3.1 validation)", "Rule check on new applications", "TalentFlow applications", "Continuous from release",
     "Engineering lead", ""),
    ("SM-B3-2", "B3", "New applications with application-level Source and Intake Method captured", "adoption",
     "0/350 (field does not exist)", "R3-app-source-field", "Measured on snapshot",
     "100% of UI-created applications (mandatory fields); imports tracked separately", "Firm for UI path; imports provisional",
     "Field completeness on new applications", "TalentFlow applications", "Weekly, first 4 weeks", "Engineering lead", ""),
    ("SM-B3-3", "B3", "Intake-method mix for Job Board applications (share entered manually)", "outcome",
     "Not measurable today (no intake data, C-12)", "", "None", "No target: measurement input to the N1 decision at Q4 planning",
     "Not set (measurement)", "Share by Intake Method", "TalentFlow applications", ">= 1 quarter after release", "PM", ""),
    ("SM-B3-4", "B3", "Duplicate-warning precision: share of warnings the recruiter resolves as 'same person' (attach to existing record; no merge)", "outcome",
     "No baseline; snapshot has 12/300 candidates in name+phone pairs", "DQ-02", "Snapshot context only",
     "Decision rule: < 50% over first 50 warnings -> tighten match rule", "Provisional decision rule", "Warning outcomes",
     "Duplicate-warning events", "Until 50 warnings", "PM", ""),
    ("SM-B3-G2", "B3", "Duplicate warnings re-shown for a pair already marked 'different person'", "guardrail",
     "Not measurable today (no warning exists)", "", "None", "0", "Firm (enforced by remembered pair decisions)",
     "Count of warnings on pairs in the not-duplicate list", "Duplicate-warning events", "Continuous", "Engineering lead", "SM-B3-4"),
    ("SM-B3-G3", "B3", "Candidate records merged or deleted by the duplicate feature", "guardrail",
     "Not applicable today", "", "None", "0", "Firm (enforced: feature has no merge or delete path)",
     "Audit of candidate record deletions/merges attributed to the feature", "Candidate audit log", "Continuous", "Engineering lead", "SM-B3-4"),
    ("SM-B3-G1", "B3", "Median time to create an application", "guardrail",
     "No baseline: instrument 2 weeks before release", "", "To be measured pre-release",
     "Threshold: > 20% increase vs pre-release baseline -> simplify form", "Provisional guardrail", "Form start->save timing events",
     "Front-end telemetry", "2 weeks pre-release vs 4 weeks post-release", "Engineering lead", "SM-B3-2"),
]


def success_rows() -> list[dict]:
    return [dict(zip(SM_COLS, r)) for r in SUCCESS_METRICS]


# Phase 3 traceability: finding -> evidence -> metric -> assumption -> decision -> initiative -> success metric
TR_COLS = ["trace_id", "finding", "evidence", "metric_ids", "assumption_ids", "decision_ids", "initiative",
           "success_metric_ids", "customer_questions", "what_evidence_does_not_prove"]
TRACE = [
    ("T-01", "Pending offers carry decision dates; no terminal states beyond Accepted/Declined", "DQ-06;DQ-07;DQ-08",
     "M-B0;M-B1;M-B2;M-B3;OAM-03;OAM-03c;OAM-04-max", "ASM-007;ASM-023", "DEC-026;DEC-027;DEC-029", "B1",
     "SM-B1-1;SM-B1-2;SM-B1-4;SM-B1-G1", "C-02;C-03", "That recruiters experience it as pain; the true outcomes of the 5 offers"),
    ("T-02", "VP's 72% is the all-issued ratio; decided-offer rate is 83.9%", "DQ-06", "M-B0;M-B1;OAM-01;OAM-02",
     "ASM-020;ASM-025", "DEC-016;DEC-026;DEC-029;DEC-030", "B1", "SM-B1-3;SM-B1-G2", "C-13;C-15",
     "That acceptance is good or bad (no benchmark)"),
    ("T-03", "Offers to already-hired candidates inside the decided denominator", "DQ-29", "M-B9;M-B10;OAM-01b", "ASM-020",
     "DEC-029", "B1", "SM-B1-3", "C-08", "Whether these are internal moves"),
    ("T-04", "Declines are few; reasons are single categories", "DQ-25", "OAM-06;M-B6-Counter Offer;M-B7-Accepted", "ASM-016",
     "DEC-026;DEC-028", "N2", "", "C-09;C-13", "Why candidates decline"),
    ("T-05", "Stalled Active applications", "DQ-28", "M-FCc-hired;M-K-eligible", "ASM-021;ASM-017;ASM-024", "DEC-027", "B2",
     "SM-B2-1;SM-B2-2;SM-B2-G1", "C-11;C-01", "That applications are abandoned rather than tracked elsewhere; cutoff-sensitive"),
    ("T-06", "Requisition status contradicts applications; Active applications on Filled openings", "DQ-11;DQ-12;DQ-28",
     "M-DF-Engineering-hired", "ASM-023", "DEC-027", "B2", "SM-B2-3;SM-B2-4", "C-11;C-06", "How Acme maintains statuses"),
    ("T-07", "Closed On precedes the offer decision", "DQ-18;DQ-26", "M-T0", "ASM-020", "DEC-011;DEC-027", "B2",
     "SM-B2-G1", "C-06", "What Closed On means"),
    ("T-08", "Source contradicts Referred By; Referral hires unlinked", "DQ-01", "M-A0;M-A2;M-A9;M-A9n;M-A7s-Job Board",
     "ASM-011;ASM-013", "DEC-017;DEC-025;DEC-027", "B3", "SM-B3-1;SM-B3-2;SM-B3-G1", "C-04", "Which field is correct"),
    ("T-09", "Probable duplicate candidate identities", "DQ-02;DQ-03;DQ-04", "M-A1;M-A4;M-A8;M-A10", "ASM-008;ASM-012",
     "DEC-027", "B3", "SM-B3-4", "C-07", "That pairs are the same people"),
    ("T-10", "Job boards: high volume, lowest yield; friction unmeasured", "DQ-01", "M-A5;M-A0;M-A7-Job Board;M-A7s-Job Board;M-A7m-Job Board;M-A7f-Job Board;M-Q2-Job Board",
     "ASM-013;ASM-019", "DEC-025;DEC-028", "N1", "SM-B3-3", "C-12;C-04",
     "That integration would not help: the friction it would remove is unmeasured"),
    ("T-11", "Referral appears strong only as labelled", "DQ-01;DQ-04", "M-A7-Referral;M-A9n;M-A7s-Referral (linked)", "ASM-011",
     "DEC-017;DEC-028", "N3", "SM-B3-1", "C-04", "That referrals are weak: linked sample is small"),
    ("T-12", "Interview capture possibly incomplete; feedback latency unmeasurable", "DQ-16;DQ-24", "M-I0;M-T2-Offer -> decision",
     "ASM-009", "DEC-031", "X1 (backlog)", "", "C-05", "Size of the scheduling problem"),
    ("T-13", "Department samples too small", "DQ-11", "M-T1-Product;M-DF-Engineering-hired;OAM-07-Data", "ASM-018;ASM-025",
     "DEC-030;DEC-031", "X2 (backlog)", "", "C-10", "Department differences"),
    ("T-15", "No auditable offer lifecycle; contradictory status/date combinations possible", "DQ-06;DQ-07;DQ-08", "OAM-03c;OAM-12",
     "ASM-030", "DEC-032;DEC-033", "B1", "SM-B1-1;SM-B1-G3", "C-02;C-03", "Which roles Acme wants to own each transition"),
    ("T-16", "Small samples and individual-level visibility in breakdowns", "DQ-04", "OAM-07-Data;OAM-08-2026-H1;OAM-06-reason-Counter Offer",
     "ASM-025;ASM-028", "DEC-034", "B1", "SM-B1-3", "C-14", "The privacy threshold Acme/legal require"),
    ("T-17", "Inactivity is threshold-sensitive and is not abandonment", "DQ-28", "M-K-eligible", "ASM-021;ASM-024", "DEC-035", "B2",
     "SM-B2-5", "C-11", "That flagged applications are abandoned"),
    ("T-18", "Acquisition source and intake method are conflated; referrals unlinked", "DQ-01;DQ-02", "M-A9n;M-A9r",
     "ASM-029;ASM-008", "DEC-036", "B3", "SM-B3-G2;SM-B3-G3", "C-04;C-07", "Which channel is right for legacy records"),
    ("T-14", "Effort figures are planning estimates", "", "", "ASM-022;ASM-026;ASM-027", "DEC-008;DEC-027;DEC-037", "B1;B2;B3", "", "",
     "That scope fits 6.0 engineer-weeks: engineering validation required"),
]


def trace_rows() -> list[dict]:
    return [dict(zip(TR_COLS, r)) for r in TRACE]


def score_rows() -> list[dict]:
    rows = []
    for cid, (name, decision, sc) in CANDIDATES.items():
        d = dict(zip(CRITERIA, sc))
        rows.append({"candidate_id": cid, "initiative": name, "decision": decision, **d,
                     "weighted_score": round(sum(WEIGHTS[c] * d[c] for c in CRITERIA), 2),
                     "equal_weight_score": round(sum(d.values()) / len(CRITERIA), 2),
                     "score_without_effort": round(sum(WEIGHTS[c] * d[c] for c in CRITERIA if c != "effort") / (1 - WEIGHTS["effort"]), 2)})
    for key in ("weighted_score", "equal_weight_score", "score_without_effort"):
        for rank, r in enumerate(sorted(rows, key=lambda r: -r[key]), 1):
            r[key.replace("score", "rank")] = rank
    return rows


def allocation_rows() -> list[dict]:
    return [{"component_id": c, "build": b, "sprint": s, "discipline": d, "engineer_weeks": ew,
             "estimate_status": ESTIMATE_STATUS, "first_cut": "yes" if c in ("B3.2", "B3.3b") else "", "description": desc}
            for c, b, s, d, ew, desc in ALLOCATION]


def write(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    s, a = score_rows(), allocation_rows()
    write("phase3_prioritisation_scores.csv", s)
    write("phase3_capacity_allocation.csv", a)
    write("product_success_metrics.csv", success_rows())
    write("phase3_decision_traceability.csv", trace_rows())
    for r in sorted(s, key=lambda r: r["weighted_rank"]):
        print(f"{r['candidate_id']} weighted {r['weighted_score']:.2f} (#{r['weighted_rank']}) | equal {r['equal_weight_score']:.2f} "
              f"(#{r['equal_weight_rank']}) | without effort {r['score_without_effort']:.2f} (#{r['rank_without_effort']}) | {r['decision']}")
    print("total ew", sum(x["engineer_weeks"] for x in a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
