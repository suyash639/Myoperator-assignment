# Data Quality and Reliability Audit (D4): TalentFlow / Acme Corp

**Version:** Phase 2.2 (corrected 2026-11-24). Corrections are listed in `phase2_2_correction_report.md`.

**Snapshot dates (DEC-020):**

| Date | Meaning |
|---|---|
| 2026-11-24 | **Extraction date** (Airtable read, Phase 1) |
| 2026-08-27 | **Apparent bulk-import timestamp**: every record was created 16:39–16:40 UTC |
| *Business reporting cutoff* | **Unconfirmed** (customer question C-01). Ages use 2026-08-27 as a *provisional* cutoff; sensitivity at 2026-08-30 and 2026-11-24 is shown wherever a result depends on it |

**Snapshot:** Airtable base `<AIRTABLE_BASE_ID>`, 892 records in 8 tables (72/72 extraction checks passed).

**Reproduce:** `uv run python -m src.run_phase2` (no API calls; re-verifies raw checksums before and after).

**Companions:**
- `dq_issues.csv` (every affected record ID)
- `table_profiles.csv`
- `relationship_integrity.csv`
- `metric_calculations.csv`
- `verification.csv`
- `decision_traceability.csv`

> **Statement types.** Plain statements are **facts** computed from records. *Interpretation* marks analyst judgement. *Hypothesis* marks an explanation not verified by the data. Recommendations are deferred to Phase 3.

---

## 0. Bottom line

1. **The structure is sound; the content is not.**
   - All 11 linked relationships resolve: 0 orphans, 0 asymmetric links, 0 cardinality violations.
   - There are 0 blank strings, and every missing value is explained by the record's state.
   - The defects are **contradictions between fields that each look valid on their own.**
2. **Both VP metrics depend on defective fields:**
   - **Claim A** depends on `Candidates.Source`. It contradicts the `Referred By` link on 34/350 applications (DQ-01), and **none of the 7 Referral-labelled hires has a referrer link**.
   - **Claim B** depends on `Offers.Status`. 4/5 Pending offers carry a decision date (DQ-06), and there is no Expired or Withdrawn state (DQ-07).
3. **Dates are internally inconsistent.**
   - Application copied stage dates disagree with the Interviews and Offers tables (DQ-15).
   - Impossible chronology occurs in both sources (DQ-13).
   - Neither source is treated as authoritative (DEC-019).
4. **Application and requisition statuses are not maintained.**
   - 15/24 openings contradict their applications (DQ-11).
   - 50/105 Active applications show no activity for more than 90 days (DQ-28).

## 1. Method

### 1.1 Approach
- **Raw data is immutable.**
  - `data/raw/*.json` is read-only (DEC-012).
  - `src/data.py` refuses to load if any SHA-256 differs from the manifest.
  - `run_phase2` re-hashes after running.
- **Nothing is corrected.** Each issue has a *treatment*. Affected metrics are reported under alternative definitions rather than silently fixed.
- **Field types are inferred from values** (the schema endpoint returned 403). An absent field means an empty cell.
- **Linked records:** a relationship is broken only if an ID does not resolve, or if the two sides disagree.
- **Independent verification:** headline metrics, attribution variants, the department and cohort funnels, and 15 data-quality counts are recomputed in DuckDB SQL from the raw JSON (`queries/verify_phase2.sql`), sharing no code with the Python implementation. **54/54 match** (`verification.csv`). Other checks are single-implementation.
- **Uncertainty (DEC-018).** Rates are reported as observed values, with definition sensitivity (variant rows) and single-record sensitivity (`single_record_pp` in `metric_calculations.csv`). No sampling intervals are reported.

### 1.2 Snapshot and cutoff
- Every record's `createdTime` is 2026-08-27 between 16:39 and 16:40 UTC: a bulk import (DQ-22).
- The latest Applied On is 2026-08-27, on a single application. 3 Candidate Created On values are later, up to 2026-08-30.
- Because the business cutoff is unconfirmed, cutoff-dependent results are shown at three dates:

  | Result | 2026-08-27 (provisional) | 2026-08-30 | 2026-11-24 (extraction) |
  |---|---|---|---|
  | Stale Pending offers (DQ-07) | 3 of 5 | 3 of 5 | 5 of 5 |
  | M-B3 (stale Pending treated as expired) | 26/34 = 76.5% | 26/34 = 76.5% | 26/36 = 72.2% |
  | Open openings past Target Close (DQ-12) | 10/11 | 10/11 | 11/11 |
  | Stalled Active applications (DQ-28) | 50/105 | 51/105 | 104/105 |
  | Completed cohort stalled Active (M-K) | 35/35 | 35/35 | 35/35 |

### 1.3 Classification and severity
| Classification | Meaning |
|---|---|
| Confirmed defect | Values contradict each other or are impossible; at least one is wrong |
| Suspicious pattern | Likely wrong, but a legitimate explanation exists |
| Legitimate business case | Real behaviour the data represents correctly |
| Model limitation | Data is consistent, but the schema cannot express something the business needs |
| Informational | Context for interpreting other findings |

| Severity | Meaning |
|---|---|
| Critical | Changes a VP-claim verdict or headline metric |
| High | Materially biases a funnel, hire or cycle-time metric |
| Medium | Affects a secondary metric or one table's reliability |
| Low | Hygiene; no material metric impact |

## 2. Table profiles (summary; full detail in `table_profiles.csv`, 80 fields)

| Table | Records | Fields | Notes |
|---|---:|---:|---|
| Departments | 8 | 6 | 8 unique names and codes |
| People | 14 | 10 | Staff only: 6 Interviewers, 4 Recruiters, 4 Hiring Managers. **Not hires.** |
| Job Openings | 24 | 15 | Status: Open 11, Filled 8, On Hold 3, Cancelled 2 |
| Candidates | 300 | 14 | Source: Job Board 191, Agency 35, LinkedIn 31, Career Site 31, Referral 8, Campus 4 |
| Applications | 350 | 16 | Stage: Rejected 200, Applied 45, Screening 32, Hired 26, Interview 23, Withdrawn 14, Offer 10. **No Source field** |
| Interviews | 160 | 10 | Outcome: Completed 138, No Show 10, Cancelled 7, Rescheduled 5 |
| Offers | 36 | 9 | Status: Accepted 26, Pending 5, Declined 5 |
| Findings | 0 | 0 | Empty (DQ-23) |

**Formats:**
- All date fields are ISO `YYYY-MM-DD`, and all numeric fields are JSON numbers.
- There are no blank strings and no categorical variants.

**Every missing value follows the record's state:**

| Field | Missing when |
|---|---|
| `Closed On` | the application is Active |
| `Rejection Reason` | the stage is not Rejected or Withdrawn |
| `Screened On` | the application is not yet screened, or was rejected before screening |
| `Score`, `Recommendation`, `Feedback` | the interview was not completed |
| `Decline Reason` | the offer was not Declined |

**Business keys:** all are unique except Application ID (DQ-03).

## 3. Relationship integrity (`relationship_integrity.csv`)

All **11 relationships PASS**:
- Every Application has exactly one Candidate, Opening and Recruiter.
- Every Interview and every Offer has exactly one Application.
- No Application has more than one Offer.
- Every Candidate has at least one Application, and no referenced candidate is missing from the snapshot. This independently confirms the 300-record page boundary.
- Link targets have the right roles.

*Interpretation:* broken links are not a data quality problem in this base.

## 4. Issue register (29 issues)

| ID | Issue | Class | Affected | % | Severity | Metric impacted |
|---|---|---|---:|---:|---|---|
| DQ-01 | Candidate Source contradicts Referred By link | Confirmed defect | 34/350 apps | 9.7 | **Critical** | Hires by channel (Claim A) |
| DQ-06 | Pending offers carrying a Decision On date | Confirmed defect | 4/5 pending | 80.0 | **Critical** | Acceptance (Claim B) |
| DQ-07 | Pending unresolved >30 days; no Expired/Withdrawn state | Suspicious | 3/5 pending | 60.0 | **Critical** | Acceptance (Claim B) |
| DQ-02 | Probable duplicate candidates (identity collisions) | Suspicious | 12/300 cands | 4.0 | High | Channel attribution; unique counts |
| DQ-04 | Same candidate hired more than once | Suspicious | 4/26 hires | 15.4 | High | Hire count |
| DQ-11 | Opening Status contradicts its applications | Confirmed defect | 15/24 openings | 62.5 | High | Fill rate; time-to-fill |
| DQ-15 | Copied date fields contradict source tables | Confirmed defect | 13/143 apps | 9.1 | High | Stage lags |
| DQ-16 | Final Interview On after last recorded interview | Suspicious | 44/50 apps | 88.0 | High | Interview counts and rounds |
| DQ-03 | Application ID reused by different applications | Confirmed defect | 8/350 apps | 2.3 | Medium | Joins on business key |
| DQ-08 | Stage 'Offer' covers both pending and declined | Model limitation | 5/10 apps | 50.0 | Medium | Stage-based funnel |
| DQ-10 | 'Position Cancelled' on non-cancelled openings | Suspicious | 18/18 apps | 100.0 | Medium | Rejection reasons |
| DQ-12 | Open openings past Target Close | Suspicious | 10/11 open | 90.9 | Medium | Requisition ageing |
| DQ-13 | Impossible chronology (within one provenance) | Confirmed defect | 23/846 recs | 2.7 | Medium | Cycle times |
| DQ-18 | Hired application closed before offer accepted | Suspicious | 17/26 hires | 65.4 | Medium | Time-to-hire end date |
| DQ-24 | Completed On = Scheduled On; no feedback timestamp | Model limitation | 138/142 | 97.2 | Medium | Feedback latency |
| DQ-25 | Offer Base CTC far from Expected CTC | Suspicious | 23/36 offers | 63.9 | Medium | Compensation analysis |
| **DQ-26** | Declined offer: application closed before decision | Suspicious | 4/5 declined | 80.0 | Medium | Decision timing; Closed On meaning |
| **DQ-28** | Active applications stalled >90 days | Suspicious | 50/105 active | 47.6 | Medium | Closed-only funnel; pipeline counts |
| DQ-05 | Same candidate, same opening, multiple applications | Suspicious | 6/350 apps | 1.7 | Low | Application volume |
| DQ-09 | Rejection Reason on non-rejected applications | Confirmed defect | 4/218 | 1.8 | Low | Rejection reasons |
| DQ-14 | Candidate Created On after Applied On | Suspicious | 90/350 apps | 25.7 | Low | First-touch variant M-A8 |
| DQ-17 | Interview Outcome contradicts completion data | Confirmed defect | 4/160 | 2.5 | Low | No-show rate |
| DQ-19 | Offer Base CTC outside salary band | Suspicious | 7/36 offers | 19.4 | Low | Compensation |
| DQ-20 | Non-round compensation values | Suspicious | 6/336 | 1.8 | Low | Compensation |
| DQ-21 | Application recruiter differs from opening's | Legitimate | 4/350 | 1.1 | Low | Recruiter workload |
| **DQ-27** | Interview after a rejected/withdrawn application closed | Confirmed defect | 7/84 | 8.3 | Low | Rejection timing |
| **DQ-29** | Offer to a candidate already hired elsewhere | Suspicious | 4/36 offers | 11.1 | Low | Offer acceptance scope |
| DQ-22 | All records bulk-created within 1 minute | Informational | 892/892 | 100 | Low | Never use createdTime |
| DQ-23 | Findings table is empty | Informational | 0 | n/a | Low | Nothing to reconcile |

Issues in **bold** are new in Phase 2.2. Existing IDs are unchanged.

## 5. Issue detail (critical and high first)

Each entry covers evidence (full ID list in `dq_issues.csv`), metric, decision and treatment.

### DQ-01: Candidate Source contradicts the Referred By link. Critical, confirmed defect.
- **Evidence:**
  - 27 applications name a referrer, but only 3 of those candidates have Source = Referral. The rest are labelled Job Board 17, Agency 4, Career Site 3.
  - 10 Source = Referral applications have no referrer.
  - Total affected: 34/350.
- **At the hire level:** **7/7 Source = Referral hires have no referrer link.** Only 3 hires have a referrer link, all with a non-Referral Source.
- **Metric:**

  | Attribution | Job Board share of hires |
  |---|---|
  | Source as recorded (M-A0) | 26.9% |
  | Referrer override (M-A2) | 23.1% |
  | Strict referral (M-A9) | 23.1% |

  Referral's per-application hire rate depends on the definition:

  | Definition | Referral hire rate |
  |---|---|
  | As recorded | 7/13 |
  | Linked referrals only | 3/27 |
  | Referral label without a link | 7/10 |

- **Treatment:** Source as recorded is the primary reported attribution (DEC-017); the alternatives are shown separately. Which field is correct cannot be determined (C-04). Referral is **not** treated as a proven high-performing channel.

### DQ-06: Pending offers carrying a Decision On date. Critical, confirmed defect.
- **Evidence:** 4/5 Pending offers have `Decision On`: `rec5GeU3frNNkZrws`, `recMJLFhIqQcUh6A9`, `recQq6ghz7ksCfsKV`, `recUzh2Vj5NyAPwRO`.
- **Timing:** their offer-to-decision lags (11, 13, 16, 16 days) sit within the 2–20-day range of decided offers.
- *Interpretation:* "status not updated" fits better than "date wrong", but the data cannot prove it.
- **Treatment:** Status as recorded is used. The decided-offer rate M-B1 excludes Pending; scenarios M-B0, M-B2 and M-B3 bound it.

### DQ-07: Pending offers unresolved for more than 30 days; no terminal states. Critical, suspicious.
- **Evidence:**
  - Pending ages at the provisional cutoff are 20, 23, 69, 117 and 222 days.
  - Status allows only Accepted, Declined and Pending.
  - The 222-day offer `recUzh2Vj5NyAPwRO` belongs to application `reckLPXA8xRgWsC1l`, whose Rejection Reason is "Withdrew".
- **Cutoff sensitivity:** 3 of 5 are stale at 2026-08-30; 5 of 5 at 2026-11-24.
- **Severity rationale:** Critical, because this issue alone moves the Claim B scenario range.
- **Treatment:** scenario reporting. The 30-day threshold is ASM-007.

### DQ-02: Probable duplicate candidates (identity collisions). High, suspicious.
- **Identity evidence (all 6 pairs):**
  - same normalised name and phone, city, current company and email domain;
  - the `f.last@` email pattern occurs on only 6 of the 300 candidates, one record in each pair.
- **Profile evidence (mixed):**

  | Pair | Source | Years Experience | Created apart | One person plausible? | Hire |
  |---|---|---|---|---|---|
  | CAND-00009 / 00010 | Job Board / Job Board | 8.8 / 5.1 | 90 days | No | APP-00310 |
  | CAND-00012 / 00011 | Job Board / Job Board | 8.7 / 5.3 | 114 days | No | none |
  | CAND-00001 / 00002 | **Job Board / Referral** | 3.2 / 1.1 | 425 days | No | APP-00002 |
  | CAND-00006 / 00005 | Job Board / Job Board | 7.4 / 7.9 | 155 days | Yes | none |
  | CAND-00008 / 00007 | Job Board / Job Board | 0.9 / 8.4 | 439 days | No | none |
  | CAND-00004 / 00003 | **Referral / Job Board** | 7.6 / 7.6 | 46 days | Yes | APP-00004 |

- **Metric:**
  - Hires are 26 at application level, 24 distinct hired candidate records, and 24 persons after merging. No pair has two hires.
  - Merging pairs moves Job Board to 30.8%, under either first-touch rule:
    - **by Created On** (M-A8): the CAND-00001/00002 hire moves;
    - **by earliest Applied On** (M-A10): the CAND-00003/00004 hire moves instead.
  - The total is robust; which hire moves is not. Created On is unreliable as first touch (DQ-14).
- **Treatment:** records are kept separate; merged variants are reported as sensitivity (ASM-008, ASM-012).

### DQ-04: Same candidate hired more than once. High, suspicious.
- **Evidence:** 2 candidates hold 4 of the 26 hires.
  - `CAND-00015` was hired into REQ-2026-008 and REQ-2025-024.
  - `CAND-00035` was hired twice into REQ-2025-019.
  - Both are Source = Referral; none of the 4 hires has a referrer link.
- **Metric:** 26 hires vs 24 distinct hired candidate records. Job Board share 7/24 = 29.2% (M-A1).
- **Treatment:** counted as recorded; a distinct-candidate variant is reported.

### DQ-11: Opening Status contradicts its applications. High, confirmed defect.
- **Evidence:** 15 of 24 openings are affected.

  | Problem | Openings |
  |---|---:|
  | Filled or Cancelled with Active applications | 9 |
  | Open although hires ≥ headcount | 5 |
  | Hires exceed headcount | 4 |
  | Cancelled with hires | 2 |
  | Filled with fewer hires than headcount | 2 |

- **Examples:** REQ-2025-015 is Cancelled with 3 hires. REQ-2026-017 (Engineering, Lead) is Filled with 0 hires.
- **Treatment:** fill state is derived from hires; the recorded Status is reported separately.

### DQ-15: Copied date fields contradict their source tables. High, confirmed defect.
- **Evidence:**
  - `Applications.Offered On` ≠ `Offers.Offered On` in 3/36.
  - `Applications.First Interview On` ≠ min(`Interviews.Scheduled On`) in 13/143.
  - The fields are scalars, so they are static copies, not lookups.
- **Which side fits the chronology:**
  - In 9 of the 13 First Interview mismatches, the *source* interview predates the application, while the copy fits the sequence in every case.
  - In all 3 Offered On mismatches, the *source* offer date precedes the copied Final Interview On.
- **Treatment (DEC-019):** neither source is authoritative.
  - Both values are retained.
  - Stage lags are reported under both sources. For example, last interview → offer is a median of 15.5 days from the source tables and 6 days from the copied fields.

### DQ-16: The Interviews table may lack later rounds. High, suspicious.
- **Evidence:**
  - In 44/50 applications with `Final Interview On`, that date is later than every recorded interview.
  - 23/26 hires have only one recorded interview (Technical 1: 12, Screen: 11), and 26/26 hires carry a Final Interview On.
- **Classification:** stays *suspicious*. Whether the table is meant to hold every round is unknown (C-05), and Final Interview On may itself be a drifted copy.
- **Treatment:** interview counts are treated as a lower bound; conversion uses "at least one interview".

### Medium and low issues (full detail in `dq_issues.csv`)
- **DQ-03:**
  - `APP-00001`, `-05`, `-07` and `-10` are each used twice; `APP-00003`, `-06`, `-09` and `-11` are missing.
  - All 8 of these applications belong to DQ-02 duplicate-pair candidates.
  - Analysis keys on Airtable record IDs.
- **DQ-08:** a declined offer stays at Stage = Offer (Closed). Offer outcomes come from `Offers.Status`.
- **DQ-10:** all 18 "Position Cancelled" rejections sit on openings that are not Cancelled.
- **DQ-12:** 10/11 Open openings are past Target Close at the provisional cutoff (11/11 at the extraction date).
- **DQ-13 (rebuilt in Phase 2.2):** every comparison is computed, including those with 0 violations. Each check stays within one provenance. Copy-vs-source disagreements are DQ-15.

  | Check | Provenance | Violations |
  |---|---|---:|
  | Opened On ≤ Applied On | source + application | 3/350 |
  | Applied ≤ Screened | application | 0/279 |
  | Applied ≤ Closed | application | 0/245 |
  | Screened ≤ Closed | application | 0/219 |
  | Applied ≤ Interviews.Scheduled | source + application | **9/160** |
  | Screened ≤ Interviews.Scheduled | source + application | **9/160** |
  | Scheduled ≤ Completed | source | 4/142 |
  | Last interview ≤ Offers.Offered | source | 0/36 |
  | Offered ≤ Decision | source | 0/35 |
  | Offered ≤ Proposed Start | source | 3/36 |
  | Decision ≤ Proposed Start | source | 4/35 |
  | Applied ≤ First Interview (copy) | copy | 0/143 |
  | Screened ≤ First Interview (copy) | copy | 0/143 |
  | First ≤ Final Interview (copy) | copy | 0/50 |
  | Final Interview ≤ Offered (copy) | copy | 0/36 |
  | Candidate Created On ≤ bulk-import date | candidate | 3/300 |

  The *Phase 2* text claimed "0 violations along the main sequence". That was true only for the copied fields and has been corrected.
- **DQ-14:** 90 applications predate their candidate's Created On. All 90 IDs are now listed.
- **DQ-17:** 4 No Show or Cancelled interviews carry a completion date, score and recommendation.
- **DQ-18:** 17/26 hires were Closed before the offer decision. The hire date is `Offers.Decision On` (DEC-011).
- **DQ-19 to DQ-21:** see `dq_issues.csv`.
- **DQ-24:** feedback turnaround cannot be measured.
- **DQ-25 (reframed):** offer Base CTC ÷ candidate Expected CTC ranges from 0.29× to 5.40×; only 13/36 fall within 0.67–1.5×.
  - **Unit checks find no defect:**
    - 0 CTC values below 100,000;
    - Expected ÷ Current CTC ranges from 0.62 to 1.66;
    - 29/36 offers fall inside the opening's band;
    - but only 93/350 applications have the candidate's Expected CTC inside the opening's band.
  - **Assumption:** currency INR and annual period (ASM-016).
  - *Hypothesis:* candidates apply to roles outside their pay level, or candidate–opening links are wrong (C-09).
  - Compensation conclusions are not supportable (M-B7 and M-B8 are not interpretable).
- **DQ-26 (new):** 4/5 declined-offer applications were closed before the decision. With DQ-18, Closed On precedes the decision for 21/31 decided offers (C-06).
- **DQ-27 (new):** 7/84 rejected or withdrawn applications have an interview scheduled after Closed On.
- **DQ-28 (new):** 50/105 Active applications show no recorded activity for more than 90 days at the provisional cutoff.
  - **By stage:** Applied 27/45, Screening 15/32, Interview 6/23, Offer 2/5. The oldest is 401 days.
  - 55/105 Active applications sit on Filled openings.
  - The threshold is ASM-021.
- **DQ-29 (new):** 4/36 offers went to candidates already hired through another application: 2 Accepted, 1 Pending, 1 Declined. Possibly internal moves (C-08). 3 of them are decided offers inside M-B1 (M-B9).
- **DQ-05, DQ-09, DQ-20, DQ-22, DQ-23:** see `dq_issues.csv`.

## 6. Impact on the VP claims (detail in `phase2_summary.md`)

| Claim | As stated | Reproduced? | Primary reported value | Definition sensitivity |
|---|---|---|---|---|
| A: Job boards are 26.9% of hires | 26.9% | **Yes**, 7/26, Source as recorded | 26.9% (Source as recorded) | 23.1% to 30.8%; one hire = 3.8 percentage points |
| B: Offer acceptance ≈ 72% | ~72% | **Yes**, 26/36, but that is the all-issued-offer ratio | **83.9%** decided offers, offer-level (provisional, DEC-016) | 72.2% to 86.1% offer-level; candidate-level 85.7%; one decided offer = 3.2 percentage points |

## 7. Limitations
1. **No schema access (403).** Field types, lookup status and option lists are inferred, not declared.
2. **Small numbers.** 26 hires, 31 decided offers, 5 declines. Single-record sensitivity is reported for every rate (`single_record_pp`).
3. **No ground truth** where fields conflict (DQ-01, DQ-06, DQ-15).
4. **Unconfirmed cutoff** (DEC-020). Cutoff-dependent results are shown at three dates (§1.2).
5. **Synthetic-looking structure.** This is *interpretation*. The data was bulk-loaded within one minute; repeat applications are numbered n + 300; and duplicates, reused IDs and source-table date conflicts cluster in the lowest IDs. Frequencies may not reflect a real customer (C-16).
6. **Single base, no tenant field** (ASM-010).

## 8. Open questions
Details are in `open_questions_for_customer.md`.
- **C-04:** attribution authority.
- **C-02:** Pending offers.
- **C-03:** expiry policy.
- **C-05:** interview completeness and date provenance.
- **C-06:** Closed On meaning.
- **C-07:** duplicate identities.
- **C-09:** compensation and candidate–opening links.
- **C-01:** business cutoff.
- **C-11:** status maintenance.
