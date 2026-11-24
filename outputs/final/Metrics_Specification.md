# Metrics Specification: Offer Acceptance (D3) and Q3 Success Metrics

**Authority:**
- Consolidates `../offer_acceptance_metric_spec.md` (DEC-029, amended by DEC-033, DEC-034 and DEC-038).
- **Reference implementation:** `src/offer_metrics.py` (event-time), which produces `../offer_metric_baseline.csv`.
- Values are reconciled by test with `../metric_calculations.csv`.

**Status:**
- **Approved:** DEC-038, which counts acceptance at the decision event.
- **Proposed, awaiting PM approval:** everything else here.

**Labels used on every metric:**

| Label | Meaning |
|---|---|
| **Historical baseline** | Observed in the legacy snapshot at the provisional cutoff 2026-08-27 |
| **Proposed product metric** | Defined here; computed by TalentFlow after B1 |
| **Future success criterion** | A decision rule or target, only where already supported |
| **Unmeasurable in legacy data** | Becomes measurable only after the named build ships |

## 1. Rules that apply to every offer metric

| Rule | Definition |
|---|---|
| **Grain** | Offer-level (one row per offer record), except OAM-09, which is candidate-level and is **never combined** with offer-level figures |
| **Event time** | State is reconstructed from the offer's events, in business-date order, on or before the as-of date (`event_state`). The **first decision event** (Accepted or Declined) sets the outcome. Later events never change it. **The latest status is never read for a metric** |
| **As-of date** | Explicit parameter. An offer exists only if Offered On ≤ as-of. A decision dated after the as-of date makes the offer **pending at that date**. In production, as-of = refresh time. For the snapshot: provisional cutoff 2026-08-27, with sensitivity at 2026-08-30 and 2026-11-24 (DEC-020) |
| **Legacy conversion** | A legacy offer gets a decision event only if Status is Accepted or Declined **and** Decision On is present. A Pending offer with a Decision On gets no event and is flagged `STATUS_DATE_CONFLICT` |
| **Revised and superseded offers** | Only the latest offer per application issued on or before the as-of date counts. A Pending earlier offer becomes Superseded and is excluded everywhere. A resolved earlier offer keeps its status and is counted only in `REVISED_AFTER_RESOLUTION`. An Accepted offer cannot be revised (B1) |
| **Period attribution** | Decision-based metrics (OAM-01, 05, 06, 07, 08) use the decision-event date. Issue-based metrics (OAM-02, 03, 04) use Offered On and the as-of date |
| **Reliability tiers** (all viewers, DEC-034) | n < 10: counts only, no rate. 10 ≤ n < 30: rate with a low-sample label stating the one-record swing. n ≥ 30: rate |
| **Privacy suppression** (separate, DEC-034) | **A proposed, configurable policy, not a confirmed or regulatory requirement.** For viewers without record-level access only, breakdown cells with any count below `privacy_k` (proposed default 5) are hidden. **Requires Acme privacy/legal approval (C-18)** |
| **Exception counters** (always shown) | `STATUS_DATE_CONFLICT`, `DECIDED_NO_DATE`, `MISSING_OFFER_DATE`, `INVALID_STATUS`, `SUPERSEDED`, `REVISED_AFTER_RESOLUTION`, prior-hire flag |
| **Data source** | Today: the Airtable `Offers` table, joined to `Applications`, `Job Openings` and `Departments`. After B1: the TalentFlow offer entity and its event log |

## 2. Offer metrics

### OAM-01 Decided Offer Acceptance Rate (primary)
| | |
|---|---|
| Business question | Of offers that reached a candidate decision, what share were accepted at the decision event? |
| Numerator | Counted offers whose first decision event, on or before the as-of date, is **Accepted** |
| Denominator | Counted offers with a decision event (Accepted or Declined) on or before the as-of date |
| Inclusion | Latest offer per application, Offered On ≤ as-of. **Accepted-then-reneged and accepted-then-rescinded offers stay in the numerator** (DEC-038). Offers to previously hired candidates are included and flagged |
| Exclusion | Pending at the as-of date; resolved without a decision (Expired, Withdrawn or Rescinded before deciding); Superseded; invalid status; decided without a date |
| Time window | Period of the decision event; default a rolling 2 quarters (half-years for history) |
| Edge cases | Pending with a decision date stays pending and is flagged. A decision after the as-of date is pending. A corrected record uses the corrected decision date |
| Limitations | Status data is unreliable today (FND-09); there is no benchmark (C-13); the cutoff is unconfirmed |
| **Historical baseline** | **26/31 = 83.9%**, the provisional primary (DEC-016). Rate tier n ≥ 30 |
| Target | **None.** No benchmark exists |

### OAM-02 All-Issued Offer Acceptance Ratio
| | |
|---|---|
| Business question | Of all offers issued, how many have been accepted so far? |
| Numerator | Accepted decision events on or before the as-of date |
| Denominator | All counted offers (any status at the as-of date, Superseded excluded) |
| Time window | Offers issued in the period (by Offered On), with status at the as-of date |
| Limitations | Pending offers count as non-acceptance, so this is **not** a decision rate. Always labelled "ratio" |
| **Historical baseline** | **26/36 = 72.2%**, which reproduces the VP's figure |
| Target | None |

### OAM-09 Candidate-level decided acceptance (secondary)
| | |
|---|---|
| Business question | Of candidates who decided on at least one offer, how many accepted at least one? |
| Numerator / denominator | Candidates with at least 1 accepted decision event ÷ candidates with at least 1 decision event |
| Limitations | Different grain from OAM-01. Shown only in a separate candidate view |
| **Historical baseline** | **24/28 = 85.7%**, candidate-level. Low-sample tier: 1 candidate = 3.6 points |

### OAM-01b Decided acceptance excluding offers to previously hired candidates (variant)
- **Definition:** OAM-01, excluding offers where the same candidate has an earlier Hired application whose acceptance preceded this offer.
- **Historical baseline:** 24/28 = 85.7%, **offer-level**. It shares counts with OAM-09 only by coincidence.
- **Why it's a variant:** whether these are internal moves is unconfirmed (C-08).

### OAM-03 Pending offers and OAM-04 pending ageing
- **Definition:**
  - **Pending at the as-of date:** offered, with no decision or resolution dated on or before the as-of date.
  - **Age:** as-of minus Offered On, bucketed 0–14, 15–30, 31–60 and over 60 days.
- **Historical baseline:**
  - 5 pending. 4/5 carry a conflicting decision date (OAM-03c, FND-09).
  - Buckets: 0, 2, 0 and 3; the oldest is 222 days.
  - Cutoff-sensitive: at 2026-11-24 all 5 are older than 30 days.
- **Limitation:** whether these offers are truly pending is unknown (C-02).

### OAM-05 Decision turnaround
- **Definition:** median and p75 of decision-event date minus Offered On, over the OAM-01 denominator.
- **Historical baseline:** median 10 days, p75 15 (n = 31). Measurable.

### OAM-06 Offer Decline Rate (and recorded reasons)
- **Definition:** Declined decision events ÷ OAM-01 denominator.
- **Historical baseline:** 5/31 = 16.1%. Reasons as recorded: Counter Offer 3, Location 1, Compensation 1.
- **Limitations:**
  - Counts only; no causal reading.
  - The reason breakdown is privacy-restricted under the proposed policy.
  - A decline *explanation* beyond the category (OAM-11) is **not measurable**.

### OAM-06x Offers resolved without a decision
- **Definition:** offers Expired, Withdrawn or Rescinded *before* any decision event, on or before the as-of date ÷ counted offers.
- **Excluded from OAM-01**; included in the OAM-02 denominator.
- **Unmeasurable in legacy data:** no such statuses exist. Measurable after **B1**.

### OAM-13a Post-acceptance reneging rate (proposed product metric)
| | |
|---|---|
| Business question | Of offers accepted, how many did the candidate later withdraw from? |
| Numerator | Offers with an Accepted decision event **and** a later Accepted → Withdrawn event, both on or before the as-of date |
| Denominator | Offers with an Accepted decision event on or before the as-of date |
| Note | These offers **remain in the OAM-01 numerator** (DEC-038) |
| Status | **Unmeasurable in legacy data**: an acceptance followed by withdrawal cannot be represented. Measurable after **B1** |

### OAM-13b Post-acceptance company rescission rate (proposed product metric)
- **Definition:** as OAM-13a, but the later event is Accepted → Rescinded by the company.
- **Status:** **unmeasurable in legacy data**; measurable after **B1**.

### Worked example: acceptance, then renege, then company rescission
Three offers, all issued 2026-03-01:
- **Offer A:** the candidate accepts on 2026-03-05, then **reneges** (withdraws) on 2026-03-20.
- **Offer B:** the candidate declines on 2026-03-04.
- **Offer C:** the candidate accepts on 2026-03-06, then the **company rescinds** on 2026-03-22.

The table is **generated by running the event-time reference implementation** (`event_metrics` in `src/offer_metrics.py`) at three as-of dates. It is not hand-calculated.

<!-- GEN:worked_example -->
| As-of date | Situation | OAM-01 accepted / decided | OAM-13a reneged / accepted | OAM-13b rescinded / accepted | Pending at as-of | Latest status (not used by any metric) |
|---|---|---|---|---|---|---|
| 2026-03-02 | all three offers issued, no decisions yet | 0 / 0 | 0 / 0 | 0 / 0 | A, B, C | A: Withdrawn, B: Declined, C: Rescinded |
| 2026-03-10 | A accepted, B declined, C accepted; no later events yet | 2 / 3 | 0 / 2 | 0 / 2 | none | A: Withdrawn, B: Declined, C: Rescinded |
| 2026-04-01 | A has since reneged, C has since been rescinded | 2 / 3 | 1 / 2 | 1 / 2 | none | A: Withdrawn, B: Declined, C: Rescinded |
<!-- /GEN:worked_example -->

**How to read it:**
- **OAM-01 records the decision event.** A and C count as accepted from their acceptance dates onwards, and **stay accepted** after the later renege and rescission (DEC-038). B counts as decided but not accepted.
- **OAM-13a and OAM-13b record what happened after acceptance.** A appears in OAM-13a and C in OAM-13b, but only once those events are dated on or before the as-of date.
- **The latest status is never used.** In the last column A shows *Withdrawn* and C *Rescinded*, yet OAM-01 still counts both as accepted. A metric that read the latest status would wrongly report 0 acceptances.

### OAM-07 and OAM-08 Breakdowns (department, level, period)
- **Definition:** OAM-01 restricted to a department (via the opening, ASM-018), a level, or a decision half-year.
- **Historical baseline:** every department has fewer than 10 decided offers, so all are **counts only**. The 2026-H1 period has 19 decided offers and carries a low-sample label (1 offer = 5.3 points).
- **Privacy:** most cells are restricted for aggregate-only viewers under the *proposed* k = 5 policy.

### OAM-10, OAM-12 Consistency and expiry
- **OAM-10:** Accepted offers whose application is not Hired: 0/26. Measurable.
- **OAM-12:** expiry adherence is **unmeasurable in legacy data** (no Expires On, no Expired status). Measurable after **B1**.

## 3. Q3 product success metrics (from `../product_success_metrics.csv`)

**Status of the metrics below:**
- These are **proposed metrics and future success criteria.**
- **Firm targets** exist only where the build *enforces* the outcome, such as 0 new contradictions after the B1.1 constraint.
- **Improvement targets are not set** where only the old snapshot baseline exists. A live baseline is taken in sprint 3 first.
- **Adoption thresholds** are decision rules (continue or investigate), not forecasts.
- **No metric claims** that a build will raise acceptance or conversion.

<!-- GEN:sm_all -->
| ID | Build | Type | Metric | Baseline (source) | Target or decision rule | Window | Owner | Guardrail for |
|---|---|---|---|---|---|---|---|---|
| SM-B1-1 | B1 | data_quality | New offers saved with a status/decision-date contradiction | 4/5 Pending offers carry a Decision On (snapshot) (OAM-03c;DQ-06) | 0 after release — *Firm (enforced by B1.1 constraint)* | Continuous from release | Engineering lead |  |
| SM-B1-2 | B1 | adoption | Share of pre-existing Pending offers resolved (true status + date) within 30 days of pilot start | 5 Pending, of which 4 conflicting (snapshot); live count recorded at release (OAM-03;OAM-03c) | Decision rule: >= 80% resolved in 30 days -> queue works; below -> interview recruiters on blockers — *Provisional decision rule* | Pilot day 0-30 | Acme recruiting ops lead |  |
| SM-B1-3 | B1 | outcome | Reported acceptance figure in VP review uses OAM-01 with counts, OAM-02 labelled as ratio, and pending backlog | VP currently quotes ~72% (all-issued ratio) as 'acceptance' (OAM-02;M-B0) | Yes/No at the end-of-Q3 VP review — *Firm (binary)* | End of sprint 3 review | PM |  |
| SM-B1-4 | B1 | outcome | Pending offers older than 30 days with no Expires On and no update in 30 days, at month end | 3/5 Pending older than 30 days at provisional cutoff 2026-08-27 (5/5 at 2026-11-24) (DQ-07;OAM-04-over30-2026-11-24) | 0 at each month end after the backlog is resolved — *Provisional (threshold depends on expiry policy C-03)* | Monthly, 2 months post-release | Acme recruiting ops lead |  |
| SM-B1-G1 | B1 | guardrail | Status accuracy: share of queue resolutions confirmed correct in a monthly 10-offer audit sample | No baseline (new workflow) (none) | Threshold: < 90% confirmed -> pause bulk resolution, review reasons — *Provisional guardrail* | Monthly | Acme recruiting ops lead | SM-B1-2 |
| SM-B1-G3 | B1 | guardrail | Offer status changes without an audit event | Not measurable today (no event log exists) (none) | 0 — *Firm (enforced: status changes only via the event log)* | Continuous | Engineering lead | SM-B1-1 |
| SM-B1-G2 | B1 | guardrail | Accepted offers whose application is not Hired (consistency) | 0/26 (snapshot) (OAM-10) | Remains 0 — *Firm* | Continuous | Engineering lead | SM-B1-1 |
| SM-B2-1 | B2 | adoption | Share of inactivity-flagged applications dispositioned within 30 days of being flagged | No baseline (feature does not exist) (none) | Decision rule: >= 50% in pilot -> continue; < 50% -> review UX and threshold with recruiters — *Provisional decision rule* | Pilot day 0-30 and 31-60 | PM |  |
| SM-B2-2 | B2 | outcome | Inactivity-flag share of Active applications (no recorded activity > configured threshold, default 90 days; a flag, not confirmed abandonment) | 50/105 Active (snapshot, provisional cutoff); 104/105 at extraction date (DQ-28) | No numerical target until live baseline; proposed intent: halve the live baseline within one quarter of pilot — *Not set (pending live baseline)* | Weekly for 1 quarter post-release | Acme recruiting ops lead |  |
| SM-B2-3 | B2 | data_quality | Openings whose Status contradicts their applications and are not flagged | 15/24 openings contradictory (snapshot) (DQ-11) | 0 unflagged after release; decision rule: >= 50% of flags resolved within 14 days — *Firm (flags) / Provisional (resolution rule)* | Continuous; resolution reviewed at day 14 and 30 | Acme recruiting ops lead |  |
| SM-B2-4 | B2 | outcome | Active applications on Filled openings | 55/105 Active applications (snapshot) (R5-active-on-filled;DQ-28) | No numerical target until live baseline — *Not set (pending live baseline)* | Weekly for 1 quarter | PM |  |
| SM-B2-5 | B2 | outcome | Share of reviewed inactivity flags that the recruiter confirms as abandoned (pilot: 20 sampled applications) | No baseline: inactivity flags are not abandonment (50/105 flagged at 90 days is a flag rate) (none) | Decision rule: < 50% confirmed abandoned in the 20-application pilot -> cut the queue to opening flags only — *Provisional decision rule* | Sprint 2 | PM |  |
| SM-B2-G1 | B2 | guardrail | Closed-by-disposition applications reopened within 30 days | No baseline (new workflow) (none) | Threshold: > 5% -> raise stall threshold / review reasons — *Provisional guardrail* | Rolling 30 days | PM | SM-B2-1;SM-B2-2 |
| SM-B3-1 | B3 | data_quality | New applications with Source/Referred By contradiction | 34/350 applications (9.7%, snapshot) (DQ-01) | 0 for applications created after release — *Firm (enforced by B3.1 validation)* | Continuous from release | Engineering lead |  |
| SM-B3-2 | B3 | adoption | New applications with application-level Source and Intake Method captured | 0/350 (field does not exist) (R3-app-source-field) | 100% of UI-created applications (mandatory fields); imports tracked separately — *Firm for UI path; imports provisional* | Weekly, first 4 weeks | Engineering lead |  |
| SM-B3-3 | B3 | outcome | Intake-method mix for Job Board applications (share entered manually) | Not measurable today (no intake data, C-12) (none) | No target: measurement input to the N1 decision at Q4 planning — *Not set (measurement)* | >= 1 quarter after release | PM |  |
| SM-B3-4 | B3 | outcome | Duplicate-warning precision: share of warnings the recruiter resolves as 'same person' (attach to existing record; no merge) | No baseline; snapshot has 12/300 candidates in name+phone pairs (DQ-02) | Decision rule: < 50% over first 50 warnings -> tighten match rule — *Provisional decision rule* | Until 50 warnings | PM |  |
| SM-B3-G2 | B3 | guardrail | Duplicate warnings re-shown for a pair already marked 'different person' | Not measurable today (no warning exists) (none) | 0 — *Firm (enforced by remembered pair decisions)* | Continuous | Engineering lead | SM-B3-4 |
| SM-B3-G3 | B3 | guardrail | Candidate records merged or deleted by the duplicate feature | Not applicable today (none) | 0 — *Firm (enforced: feature has no merge or delete path)* | Continuous | Engineering lead | SM-B3-4 |
| SM-B3-G1 | B3 | guardrail | Median time to create an application | No baseline: instrument 2 weeks before release (none) | Threshold: > 20% increase vs pre-release baseline -> simplify form — *Provisional guardrail* | 2 weeks pre-release vs 4 weeks post-release | Engineering lead | SM-B3-2 |
<!-- /GEN:sm_all -->

## 4. Implementation check
An implementation is correct if, on the legacy snapshot at as-of 2026-08-27, it returns exactly:

| Metric | Expected |
|---|---|
| OAM-01 | 26/31 |
| OAM-02 | 26/36 |
| OAM-09 | 24/28, candidate-level |
| OAM-03 | 5 pending, of which 4 conflicting |
| OAM-05 | median 10 days |
| OAM-06 | 5/31 |
| OAM-13a, OAM-13b, OAM-06x | "not currently measurable" |

The event-time behaviour (acceptance followed by a renege or a company rescission) is specified by the tests in `tests/test_phase3_2.py`.
