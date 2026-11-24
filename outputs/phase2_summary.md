# Phase 2 Summary: Profiling, Data Quality, VP Claim Verification

**Version:** Phase 2.2 (corrected 2026-11-24). See `phase2_2_correction_report.md` for every change from the original Phase 2 text.

**Scope:** analysis only. No roadmap decisions; those are Phase 3.

**Snapshot dates (DEC-020):**
- Extraction: 2026-11-24.
- Apparent bulk-import timestamp: 2026-08-27.
- The business reporting cutoff is **unconfirmed**. 2026-08-27 is used as a provisional cutoff, with sensitivity where relevant.

**Traceability:**
- Every number appears in `metric_calculations.csv` (metric IDs in brackets) or `dq_issues.csv`. A test enforces this for every fraction in this file.
- 54/54 DuckDB checkpoints match (`verification.csv`).
- The full chain from finding to evidence, metric, assumption, decision and product implication is in `decision_traceability.csv`.

**Uncertainty (DEC-018):** observed values, definition sensitivity and single-record sensitivity. No sampling intervals.

**Labels:** **Fact** = computed from records. *Interpretation* = analyst judgement.

---

## 1. Definitions used

| Term | Definition | Status |
|---|---|---|
| Hire | Application `Stage = Hired`. This is identical to the set of applications with an Accepted offer: 26 = 26 [M-H0] | Analyst proposal (DEC-011); assumes accepted offer = hire (ASM-020) |
| Channel | **Source as recorded** (`Candidates.Source`) is primary. Variants are shown separately | PM-approved (DEC-017) |
| Stage reached | Evidence-based: Screened On present; at least 1 Interviews record; at least 1 Offers record | — |
| Offer acceptance | **Decided-offer acceptance, offer-level** is the provisional primary. The all-issued-offer ratio is kept. Candidate-level is labelled separately | PM-approved, provisional (DEC-016) |
| Hire date | `Offers.Decision On` of the accepted offer | Analyst proposal (DEC-011) |
| Stage dates | Both source tables and Application copies are retained; neither is authoritative | PM-approved (DEC-019) |
| Metric level | Every metric row states its level: application, hire, offer, candidate or interview | — |

## 2. VP claim A: "Job boards contribute 26.9% of hires and their integration work should be prioritised"

**Primary reported value: Source as recorded.** 7/26 = **26.9%** [M-A0]. One hire moves this by 3.8 percentage points.

**Definition sensitivity** (shown separately; not replacements):

| Definition | Job Board share | ID |
|---|---|---|
| **Source as recorded (primary)** | **7/26 = 26.9%** | M-A0 |
| Distinct hired candidate records | 7/24 = 29.2% | M-A1 |
| Referred By overrides Source (asymmetric, ASM-011) | 6/26 = 23.1% | M-A2 |
| Strict referral (Referral only with a referrer link) | 6/26 = 23.1% | M-A9 |
| Distinct candidates + override | 6/24 = 25.0% | M-A3 |
| Duplicates merged, first touch by Created On | 8/26 = 30.8% | M-A8 |
| Duplicates merged, first touch by earliest Applied On | 8/26 = 30.8% | M-A10 |

**Hire rate per application, Source as recorded** [M-A5, M-A7]. Rates under the other variants are in the `M-A7r`, `M-A7s`, `M-A7m` and `M-A7f` rows.

| Channel | Applications | Hires | Hire rate per application |
|---|---:|---:|---:|
| Job Board | 236 (67.4%) | 7 | **7/236 = 3.0%** |
| Career Site | 31 | 5 | 5/31 = 16.1% |
| Agency | 35 | 4 | 4/35 = 11.4% |
| LinkedIn | 31 | 3 | 3/31 = 9.7% |
| Referral (label) | 13 | 7 | 7/13, see the caveat below |
| Campus | 4 | 0 | 0/4 |

**Verdict:**
- **The figure is supported. The prioritisation is not.**
- **Fact:** 26.9% reproduces exactly under Source as recorded. Across definitions it ranges from 23.1% to 30.8%.
- **Fact:** Job Board's per-application hire rate is between 2.7% (6/219, strict referral) and 3.4% (8/236, merged) under every attribution variant. That is the lowest of any channel with hires.
- **Fact (Referral caveat):** Referral is **not** a proven high-performing channel.
  - 7/7 Referral-labelled hires have no referrer link [M-A9n], and 4 of those hires belong to 2 candidates (DQ-04).
  - Linked referrals convert at 3/27 [M-A7s-Referral (linked)].
- *Interpretation:* a 26.9% share of hires shows that job boards deliver volume, not that integration work has high value. Nothing in this data measures integration friction (C-12).
- **Confidence:** high in the arithmetic, medium in the attribution (DQ-01).

## 3. VP claim B: "Offer acceptance rate is approximately 72% and needs improvement"

All rates are **offer-level** unless labelled otherwise.

| Metric | Value | ID |
|---|---|---|
| **Decided-offer acceptance (provisional primary)** | **26/31 = 83.9%** (one decided offer = 3.2 percentage points) | M-B1 |
| All-issued-offer ratio (VP's basis; Pending in the denominator) | 26/36 = 72.2% | M-B0 |
| Stale Pending (>30 days) as expired, provisional cutoff 2026-08-27 | 26/34 = 76.5% | M-B3 |
| Same at cutoff 2026-08-30 | 26/34 = 76.5% | M-B3-2026-08-30 |
| Same at extraction date 2026-11-24 | 26/36 = 72.2% | M-B3-2026-11-24 |
| Upper bound: all Pending accepted | 31/36 = 86.1% | M-B2 |
| Decided, excluding offers to already-hired candidates | 24/28 = 85.7% | M-B10 |
| **Candidate-level** decided acceptance (not comparable with M-B1) | 24/28 = 85.7% | M-B4 |
| By offer period, decided | 2025-H2 7/8; 2026-H1 13/17; 2026-H2 6/6 | M-B5 |

M-B10 and M-B4 happen to share 24/28 but count different things:
- **M-B10** counts offers, excluding the 3 decided offers to already-hired candidates [M-B9].
- **M-B4** counts candidates, collapsing repeat offers.

**What 26/31 measures, exactly.** Of the 31 offers whose recorded Status is Accepted or Declined, 26 are Accepted.
- It is offer-level, so the 4 candidates with 2 offers count twice.
- It includes 3 decided offers to candidates already hired through another application [M-B9].
- It excludes all 5 Pending offers, 4 of which carry a decision date (DQ-06).

**Declines:** 5 in total. Counter Offer 3, Location 1, Compensation 1 [M-B6].

**Verdict:**
- **The figure reflects a definition choice. "Needs improvement" can't be judged from this data.**
- **Fact:** 72.2% is the all-issued-offer ratio, which counts the 5 unresolved Pending offers as non-acceptance. On decided offers the rate is 83.9%.
- **Fact:** the status data behind either number is unreliable. 4/5 Pending offers carry a decision date (DQ-06), and 3/5 are more than 30 days old at the provisional cutoff (DQ-07).
- **Fact:** there is no target or benchmark in the data. The by-period figures rest on 6–17 decided offers each.
- *Interpretation:* the actionable problem shown here is **offer-status data integrity**.
- **Confidence:** medium.

## 4. Funnel

### 4.1 Full snapshot (all 350 applications; mixed maturity, not a cohort) [M-F, M-FC, M-FCc]

| Stage | Reached | Overall conversion | Previous-stage conversion | Previous-stage, Status = Closed only |
|---|---:|---:|---:|---:|
| Applied | 350 | n/a | n/a | n/a |
| Screened | 279 | 279/350 = 79.7% | 279/350 = 79.7% | 219/245 = 89.4% |
| Interviewed | 143 | 143/350 = 40.9% | 143/279 = **51.3%** | 115/219 = 52.5% |
| Offered | 36 | 36/350 = 10.3% | 36/143 = **25.2%** | 31/115 = 27.0% |
| Hired | 26 | 26/350 = 7.4% | 26/36 = 72.2% | 26/31 = 83.9% |

- **Fact:** stage reach is perfectly nested.
- **Fact:** the largest absolute drop is screened → interviewed: 136 applications [M-F-leak].
- **Fact:** the lowest step conversion is interviewed → offered.
- **Caveat:** the "Closed only" column assumes Active means in flight. In fact 50/105 Active applications are stalled for more than 90 days (DQ-28).
- **Fact:** where rejected applications stopped [M-R]:

  | Furthest stage | Rejected applications |
  |---|---|
  | Before screening | 26/200 |
  | After screening, before any interview | 90/200 |
  | After an interview | 84/200 |

- **Fact:** top rejection reasons are Skills Mismatch (49/200), Culture Fit (45/200) and Better Candidate (44/200) [M-R2].

### 4.2 Completed cohort (applications 2025-07-01 to 2026-03-31) [M-K]

**Sufficiency was verified before adding it (DEC-021, DEC-022):**
- 134/350 applications fall in the window.
- **Eligibility rule:** Status Closed, or Active but stalled, meaning no recorded activity for more than 90 days before the provisional cutoff (ASM-021).
- **Result:** 99 Closed plus 35 stalled Active; 0 excluded as in flight. All 35 are stalled at every sensitivity cutoff (35/35).
- **Criteria** (≥100 applications, ≥10 offers) are met: 134 applications, 16 offers.

| Stage | Reached | Overall | Previous-stage |
|---|---:|---:|---:|
| Applied | 134 | n/a | n/a |
| Screened | 106 | 106/134 | 106/134 = 79.1% |
| Interviewed | 50 | 50/134 | 50/106 = 47.2% |
| Offered | 16 | 16/134 | 16/50 = 32.0% |
| Hired | 12 | 12/134 = 9.0% | 12/16 = 75.0% |

- **Caveat:** 2/16 cohort offers are still Pending [M-K-pending]. One offer moves the offer → hire step by 6.2 percentage points.
- **Fact:** the cohort shows the same shape as the snapshot. The largest drop is screened → interviewed, and the lowest step conversion is interviewed → offered.

## 5. Supporting analysis

### 5.1 Which channels produce quality candidates, not just volume? [M-Q, Source as recorded]

| Channel | Interview reach | Offer rate after interview | Positive recommendations (interview-level) | Mean score |
|---|---:|---:|---:|---:|
| Job Board | 90/236 = 38.1% | **13/90 = 14.4%** | 30/97 | 2.67 |
| Agency | 16/35 | 6/16 | 8/13 | 3.38 |
| LinkedIn | 12/31 | 5/12 | 7/11 | 3.29 |
| Career Site | 15/31 | 5/15 | 5/13 | 2.58 |
| Referral (label) | 10/13 | 7/10 | 5/8 | 3.31 |

- **Fact:** Job Board's interview reach (38.1%) sits at the low end of the non-referral channels, alongside LinkedIn (12/31).
- **Fact:** Job Board's offer rate after interview is the lowest, 13/90, against 5/15 to 6/16 for the other non-referral channels.
- **Fact:** Referral rows rest on Referral labels without referrer links [M-A9n]. They do not show that Referral is a high-performing channel.

### 5.2 Which departments have the longest hiring cycle? [M-T1, M-DF]
- **Fact:** median Applied → accepted is 41.5 days [M-T0], over 22 of 26 hires. 4 are excluded because their Applied On is contradicted by another record.
- **Fact:** cycle time by department:

  | Department | Median days | Hires measurable |
  |---|---:|---|
  | Product | 55 | 3 of 5 |
  | People Operations | 48.5 | 2 of 2 |
  | Customer Support (shortest) | 24 | 3 of 3 |

- **Fact:** **Engineering has 0 hires from 30 applications** [M-DF-Engineering-hired].
  - Only 3/30 reached interview [M-DF-Engineering-interviewed], against 143/350 overall.
  - 1/30 received an offer [M-DF-Engineering-offered]. It is OFF-00021, still Pending.
  - REQ-2026-017 is Filled with 0 hires (DQ-11).
  - The data does not explain why (C-10).
- **Confidence: low.** With 2–5 hires per department, no ranking is supportable.

### 5.3 Are particular roles or departments behind the offer declines? [M-D1, M-D2]
- **Fact:** there are 5 declines. Data has 2/7 decided offers declined; Customer Support 1/4, Finance 1/4 and Product 1/6.
- **Fact:** by level, Junior 2/11, Mid 1/5, Senior 2/14, Lead 0/1.
- **Not supported.** One decline moves any department rate by 14 to 50 percentage points.
- **Not supported:** compensation explanations (DQ-25).

### 5.4 Are there bottlenecks in interview scheduling or feedback? [M-T2, M-I]
Both date sources are reported (DEC-019):

| Gap | Source tables (median days) | Application copies (median days) |
|---|---:|---:|
| Applied → screened | 6 | n/a |
| Screened → first interview | 9 (9 negative lags excluded) | 9 |
| Last interview → offer | 15.5 | 6 (final interview → offer) |
| Offer → decision | 10 | n/a |

- **Fact:** the two sources disagree most on last interview → offer. The source-table figure is likely overstated if later rounds are missing (DQ-16). Which source is right is unknown (C-05).
- **Fact:** 22/160 interviews were not completed (No Show 10, Cancelled 7, Rescheduled 5). The Screen round is worst at 13/74.
- **Fact:** feedback turnaround **cannot be measured**: there is no feedback timestamp (DQ-24).

### 5.5 Patterns that could justify a Q3 investment
These are observations for Phase 3, not decisions.
1. **Offer lifecycle and status integrity** (DQ-06, DQ-07, DQ-08, DQ-29).
2. **Source attribution integrity** (DQ-01, DQ-02, DQ-04).
3. **Requisition and application status keeping pace with activity** (DQ-11, DQ-12, DQ-28).
4. **A single, consistent capture of interview rounds and stage dates** (DQ-15, DQ-16, DQ-24).

**Counter-evidence for the VP's priority.** Job boards already supply 236/350 applications, at the lowest yield under every attribution.

## 6. Unresolved uncertainties
- **Attribution authority (C-04):** Claim A ranges from 23.1% to 30.8%.
- **True state of Pending offers and the expiry policy (C-02, C-03):** offer-level acceptance ranges from 72.2% to 86.1%.
- **Business reporting cutoff (C-01):** affects M-B3, DQ-07, DQ-12 and DQ-28 (§1.2 of the audit).
- **Interview completeness and which date source is right (C-05).** Also the meaning of Closed On (C-06).
- **Duplicate identities (C-07), internal moves (C-08), compensation and candidate–opening links (C-09).**
- **Integration friction (C-12):** not measured anywhere in this data.
- **Acme-only scope (C-14).**
- **Small numbers throughout:** 26 hires, 31 decided offers, 5 declines.

## 7. Files
- **Reports:**
  - `outputs/data_quality_audit.md`
  - `outputs/phase2_summary.md`
  - `outputs/phase2_2_correction_report.md`
- **Data:**
  - `outputs/findings_table.csv`
  - `outputs/dq_issues.csv`
  - `outputs/metric_calculations.csv`
  - `outputs/table_profiles.csv`
  - `outputs/relationship_integrity.csv`
  - `outputs/verification.csv`
  - `outputs/decision_traceability.csv`
- **Code:**
  - `src/data.py`
  - `src/profile.py`
  - `src/integrity.py`
  - `src/audit.py`
  - `src/metrics.py`
  - `src/traceability.py`
  - `src/run_phase2.py`
  - `src/verify_sql.py`
  - `queries/verify_phase2.sql`
- **Tests:**
  - `tests/test_phase2.py`
  - `tests/test_phase2_2.py`
