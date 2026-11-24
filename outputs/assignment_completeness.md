# Assignment Completeness: D1–D5 and Supporting Deliverables

**Status as of Phase 2.1 (2026-11-24).**

| Status | Meaning |
|---|---|
| **Complete** | Done and verified; only cosmetic corrections pending |
| **Partial** | Substance exists but needs corrections, PM ratification or customer answers |
| **Not started** | Nothing produced yet |

## 1. Summary

| Deliverable | Status | What exists | What is missing | Blocked by |
|---|---|---|---|---|
| **D1** Verdicts on both VP claims | **Partial** | Both verdicts are drafted with every variant computed (summary §2–3, `findings_table.csv` F-A and F-B). The headline numbers re-derived independently in 2.1 | Corrections RV-04 (Referral basis) and RV-05 (uncertainty framing); a chosen primary definition for each claim | PM decisions 1–3; customer C-13, C-04, C-02, C-15 |
| **D2** 3 priorities and 3 non-priorities within 6 engineer-weeks | **Not started** | Candidate investment areas are listed as observations only (summary §5.5) | Priorities, non-priorities, trade-offs, and effort, which must come from engineering or be explicitly provisional (DEC-008) | Phase 3 approval; C-12 (integration friction); engineering estimates |
| **D3** Acceptance metric specification | **Partial** | Proposed definition DEC-014; scenarios M-B0 to M-B5; exact statement of what 26/31 measures (review §3.4) | A specification covering name, purpose, formula, inclusions and exclusions (Pending, stale, internal moves, repeat candidates), data sources and field authority, edge cases, reporting window, owner, refresh cadence and guardrails | PM ratification of DEC-014; C-02, C-03, C-08, C-13, C-15 |
| **D4** Data quality audit | **Partial (substantially done)** | 25 issues with count, %, severity, class, metric, decision, treatment and record IDs; 11 relationship checks; profiles; 36/36 SQL match | Corrections RV-02, RV-03, RV-06, RV-07, RV-08, RV-12; proposed DQ-26 to DQ-29; pair-level evidence for DQ-02 | Approval of corrections P1–P13; C-05, C-06, C-07 for final classifications |
| **D5** One-page memo | **Not started** | n/a | Everything | D1 to D3 final |
| Reproducible code | **Complete** (Phases 1, 2, 2.1) | `src/`, `queries/`, `tests/` (48 tests), uv lockfile, README run instructions | Extending SQL verification beyond the headline (RV-14); a test that every number in the markdown reports appears in a CSV (RV-18) | n/a |
| Findings table | **Partial** | `findings_table.csv` (F-A, F-B, DQ-01 to DQ-25); `decision_traceability.csv` | Rows for RV findings and the new DQ issues; corrected F-A text | Approval of P4 and P9 |
| Session transcript | **Not started** | Raw session files exist outside the repo (git-ignored) | Redacted, reviewed export to `transcripts/` | PM approval (privacy review needed) |
| Insights appendix | **Partial** | Summary §4–5: funnel, channel quality, cycle time, declines, interviews | Engineering correction (RV-01); mature-cohort view; strict-referral view; uncertainty restated | P1, P4, P5, P13 |

## 2. Findings mapped to deliverables

| Finding | D1 | D2 | D3 | D4 | D5 |
|---|:-:|:-:|:-:|:-:|:-:|
| F-A Job Board share and yield | ● | ● | | | ● |
| F-B acceptance definitions | ● | | ● | | ● |
| DQ-01 Source vs referrer, RV-04 | ● | ● | | ● | ● |
| DQ-02, DQ-04 duplicate identities, RV-07 | ● | ○ | ● | ● | |
| DQ-06, DQ-07, DQ-08 offer status lifecycle | ● | ● | ● | ● | ● |
| DQ-11, DQ-12, RV-10 requisition and application status | | ● | | ● | ○ |
| DQ-13, DQ-15, DQ-18, RV-02, RV-03, RV-09 dates | | ○ | ● | ● | |
| DQ-16, DQ-24 interview capture | | ● | | ● | ○ |
| DQ-25, RV-08 compensation | | | | ● | |
| RV-17 offers to already-hired candidates | ○ | | ● | ● | |
| Funnel and channel quality | ● | ● | | | ● |
| Cycle time, declines, Engineering (RV-01) | | ○ | | ○ | |
| RV-05 uncertainty standard | ● | | ● | | ● |
| RV-06 as-of date | ● | | ● | ● | |

● primary input · ○ supporting input

## 3. Which evidence can support product decisions

| Strength | Evidence | Why it is decision-grade (or not) |
|---|---|---|
| **Strong** | Offer-status lifecycle is unreliable (DQ-06 4/5, DQ-07, DQ-08; RV-19) | Direct record contradictions, robust to every definition, and it distorts the metric leadership is using |
| **Strong** | Job boards are volume, not yield: 67.4% of applications at 2.7–3.4% hire rate per application | Holds under every attribution variant (V0 to V6) and every as-of date |
| **Strong** | Channel attribution is internally inconsistent (DQ-01 34/350; 0/7 Referral hires linked) | Direct contradiction between two fields |
| **Moderate** | Requisition and application status drift (DQ-11 15/24; stale Active 50/105) | Clear contradictions; impact on decisions is indirect |
| **Moderate** | Interview capture likely incomplete (DQ-16 44/50; 11/26 hires Screen-only) | Strong pattern, but not confirmed (C-05) |
| **Moderate** | Funnel leak points (screened → interviewed −136; interviewed → offered 25.2%) | Consistent nesting; mixed-maturity snapshot |
| **Weak** | Referral as the best channel | Rests on unlinked labels and 2 repeat-hire people |
| **Weak** | Department cycle-time ranking; decline drivers by role or level | n = 2–5 per group; 5 declines in total |
| **None** | Compensation-driven declines | Ratio reflects candidate-to-role mismatch (RV-08) |
| **None** | Feedback latency | No timestamp exists (DQ-24) |
| **None** | **Job-board integration friction** (the VP's proposed priority) | Not measured anywhere in the base (C-12) |

## 4. What needs customer clarification
Details are in `open_questions_for_customer.md`.
- **P1:** C-13, C-02, C-03, C-04, C-15.
- **P2:** C-12, C-05, C-06, C-11, C-10.
- **P3:** C-07, C-08, C-09, C-01, C-14, C-16.

## 5. Recommended path to completion
These are proposals, not decisions.
1. **PM reviews Phase 2.1** and approves or rejects corrections P1–P13 and decisions 1–7 (`open_questions_for_customer.md`, final section).
2. **Apply the approved corrections** to the Phase 2 outputs, append-only in the logs, then rerun tests and SQL verification.
3. **Send the P1 and P2 customer questions.**
4. **Phase 3, on approval:** D3 specification, then D1 final, then D2 (with engineering estimates or labelled placeholders), then D5, then the appendix and transcript.
