# Phase 3 Review: Decisions, Allocation, Trade-offs, Risks, Coverage

**Status:** every Phase 3 decision is a **proposal awaiting PM approval** (DEC-025 to DEC-031; refined in Phase 3.1 by DEC-032 to DEC-037, see `phase3_1_review.md`). Effort figures are **PM planning estimates** that engineering must validate before sprint 1 (DEC-008, ASM-022).

## 1. Decisions

| Area | Decision | Evidence anchor |
|---|---|---|
| Claim A: job boards 26.9% of hires | The figure is correct (7/26, Source as recorded). **Job-board integration is deferred pending validation**; build the measurement (B3) and decide at Q4 planning | 236/350 applications at 2.7%–3.4% yield, the lowest of any channel with hires under every attribution; friction and cost unmeasured (C-12) |
| Claim B: acceptance ~72% | 72.2% is the all-issued-offer ratio (26/36). The provisional decided-offer rate is 83.9% (26/31). **Build differently:** offer lifecycle integrity and reporting (B1); no acceptance-improvement tooling | 4/5 Pending carry decision dates (DQ-06); no terminal states (DQ-07); 5 declines; no benchmark |
| Builds | B1 offer lifecycle (2.5), B2 pipeline hygiene (2.0), B3 attribution integrity (1.5) | Ranked 1–3 under weighted, equal-weight and no-effort scoring |
| Non-builds | N1 job-board integration (defer), N2 acceptance-improvement tooling, N3 referral programme features | Each with reconsideration criteria (strategy §5) |
| D3 | OAM-01 Decided Offer Acceptance Rate, offer-level, plus 11 supporting or diagnostic metrics; reference implementation reconciles with Phase 2.2 | `offer_acceptance_metric_spec.md`, `offer_metric_baseline.csv` |

## 2. Engineering allocation (6.0 engineer-weeks, planning estimates)

| | Backend | Frontend | Data/analytics | QA | Total | Sprint 1 / 2 / 3 |
|---|---:|---:|---:|---:|---:|---|
| B1 | 1.00 | 0.50 | 0.50 | 0.50 | 2.5 | 1.00 / 0.50 / 1.00 |
| B2 | 0.75 | 0.75 | 0.25 | 0.25 | 2.0 | 0.75 / 0.75 / 0.50 |
| B3 | 0.50 | 0.50 | 0.25 | 0.25 | 1.5 | 0.25 / 0.75 / 0.50 |
| **Total** | 2.25 | 1.75 | 1.00 | 1.00 | **6.0** | 2.0 / 2.0 / 2.0 |

**What the 6.0 covers:**
- There is no hidden capacity and no contingency buffer.
- A **cut line** protects the rules that stop new bad data (B1.1, B2.1, B3.1).
- Conditional scope is outside the 6.0 and enters only by swapping out equal effort.

## 3. Main trade-offs
1. **Trustworthy measurement before new capability.** Q3 adds nothing for candidates. In return, it makes the two numbers leadership argues about reliable, and it starts collecting the evidence the job-board decision needs.
2. **Flags and queues, not automation.** This avoids silent data changes while the meanings of Closed On, statuses and expiry are unconfirmed (C-06, C-11, C-03).
3. **Saying "not yet" to the VP's priority.** It is converted into a dated Q4 decision with explicit criteria, rather than a refusal.
4. **B3 ranks above B2** because its defect is confirmed (DQ-01) and B2's main signal is a suspicious pattern (DQ-28). If the cut line applies, B3's duplicate warning is cut before B2's queue.

## 4. Unresolved risks

| Risk | Severity | Mitigation |
|---|---|---|
| Planning estimates exceed real effort (ASM-022) | High | Engineering validation in week 0; cut line |
| Stalled applications are tracked outside TalentFlow, so B2 solves the wrong problem (C-11) | Medium | Pilot 1 sample review in sprint 2 with a stop condition |
| The snapshot is old and the cutoff is unconfirmed, so baselines may not hold (C-01, C-16) | Medium | Live baselines in sprint 3; no improvement targets before them |
| Recruiters clear queues with the wrong statuses | Medium | Reason fields; SM-B1-G1 audit guardrail |
| The data is one customer, possibly not Acme-only or production (ASM-010, C-14, C-16) | Medium | All baselines labelled "this base"; no product-wide claims |
| The VP disagrees with deferring job boards | Medium | Q4 decision with reconsideration criteria; B3 produces friction data |
| Extra intake fields add friction | Low | SM-B3-G1 guardrail |

## 5. Assignment coverage

| Deliverable | Status after Phase 3 | Where |
|---|---|---|
| D1 Verdicts on both claims | **Complete**, pending PM approval | `phase3_product_strategy.md` §2 |
| D2 3 builds + 3 non-builds within 6 engineer-weeks | **Complete**, pending PM approval; estimates need engineering validation | strategy §3–5; `q3_roadmap.md` |
| D3 Acceptance metric specification | **Complete**, pending ratification (DEC-029) | `offer_acceptance_metric_spec.md`, `src/offer_metrics.py` |
| D4 Data quality audit | Complete (Phase 2.2) | `data_quality_audit.md` |
| D5 One-page memo | **Not started.** It is Phase 4 by instruction | — |
| Success metrics and pilot design | Complete | `product_success_metrics.csv`; strategy §8 |
| Customer validation plan | Complete | `customer_validation_plan.md` |
| Traceability | Complete | `phase3_decision_traceability.csv` (14 chains) |
| Transcript export, insights appendix | Not started | — |

## 6. Quality control
These checks are run by `src/phase3_checks.py`, `tests/test_phase3.py` and `tests/test_phase3_1.py` (103 tests in the full suite after Phase 3.1):
- **Builds and non-builds:** exactly three of each, in both the strategy and the scores CSV.
- **Ranking:** the top three are the builds under all three weightings.
- **Capacity:** the total is 6.0. Per-build, per-sprint and per-discipline sums agree across the allocation CSV, the strategy and the roadmap, and there are no duplicate components.
- **Scorecard:** every build has adoption, outcome and guardrail metrics. Every quoted baseline matches the numerator and denominator of its cited source ID. No firm target exists without a baseline.
- **References:** every metric, issue, assumption, decision, customer-question and success-metric reference in the traceability CSV and the Phase 3 documents resolves. All 16 customer questions are in the validation plan.
- **D3 reconciliation:** OAM-01, OAM-02, OAM-09 and OAM-01b equal M-B1, M-B0, M-B4 and M-B10.
- **Wording:** every fraction in the Phase 3 documents exists in a generated CSV. There are no sampling intervals. Offer-level and candidate-level figures are labelled. There are no causal acceptance claims.
