# Phase 2.1: Independent Review of Phase 2

**Scope.** This is a critical review of my own Phase 2 outputs: what holds, what is wrong, and what is overstated. Nothing in the Phase 2 reports or CSVs has been changed yet. Corrections are only *proposed* here (§5) and wait for PM approval.

**Basis.**
- All 8 Phase 2 outputs, the 3 audit logs and the README were read in full.
- Every number in this review was re-derived from `data/raw` by a separate script, `src/review_phase2_1.py`. It does not import `src/metrics.py` or `src/audit.py`. Its output is `outputs/phase2_1_checks.csv`, 124 checks, cited below as `[R…]`.
- No API calls were made. Raw checksums are unchanged (§7).

**Labels:**
- **Verified** means recomputed from records in this review.
- **Assumption** means it is not provable from the data.
- *Interpretation* means analyst judgement.

---

## 1. Summary

| Result | Count |
|---|---:|
| Review issues found | 19 (RV-01 to RV-19) |
| High | 5 |
| Medium | 7 |
| Low or informational | 7 |
| Errors of fact in the Phase 2 reports | 2 (RV-01, RV-02) |
| Decisions contradicted by evidence | 1 (DEC-015, RV-03) |
| Interpretations overstated | 2 (RV-04 Referral, RV-05 confidence intervals) |

**Headline numbers that hold.** All were re-derived and match Phase 2:
- 26.9% = 7/26;
- 72.2% = 26/36;
- 83.9% = 26/31;
- the funnel 350 → 279 → 143 → 36 → 26;
- the 26/5/5 offer split;
- the 23.1%–30.8% Claim A range.

**What changes:**
- **Claim A verdict.** It still stands, but rests on Job Board's low yield, which is robust at 2.7–3.4%. It cannot rest on Referral's strength, because none of the 7 Referral-labelled hires has a referrer link (RV-04).
- **Uncertainty.** It should be reported as definitional sensitivity, not as Wilson intervals (RV-05).
- **Copied date fields.** It is not established that they are less reliable than the source tables. In the disagreements I checked, the evidence points the other way (RV-03).
- **Three data issues were not reported** (RV-09, RV-10, RV-17).

## 2. Review issue register

Severity uses the same scale as D4:
- **Critical:** changes a VP verdict or headline metric.
- **High:** materially changes a reported conclusion.
- **Medium:** affects a secondary metric or the audit trail.
- **Low:** wording or hygiene.

| ID | Severity | Issue | Exact evidence | Where |
|---|---|---|---|---|
| RV-01 | **High** | Wrong number typed by hand: "Engineering has 0 hires from **20** applications". Engineering has **30**. The number appears in no CSV, which breaks the claim on summary line 5 that every number is traceable. | `[R9-Engineering]` 0/30. Openings 3, headcount 5, interviewed 3, offered 1, Rejected 17, Withdrawn 3, Applied 5, Screening 2, Interview 2, Offer 1 | `phase2_summary.md:112`; also the Phase 2 terminal summary |
| RV-02 | **High** | The DQ-13 detail says "checks that passed with 0 violations: applied ≤ screened ≤ first interview ≤ final interview ≤ offered…". This was **typed by hand, never computed**, and is true only for the *copied* fields. On the source tables it is false. | `[R10-dates]`: Applied On ≤ Interviews.Scheduled On fails 9/160; Screened On ≤ Scheduled On fails 9/160; Final Interview On ≤ Offers.Offered On fails 3/36 | `src/audit.py:277` → `dq_issues.csv` DQ-13; `data_quality_audit.md:228` |
| RV-03 | **High** | DEC-015 and the DQ-15 treatment assume the Interviews and Offers tables are authoritative over the copied Application fields. **The evidence contradicts this.** In 12 of the 16 disagreements, the source record breaks the date sequence and the copy does not. In the other 4, neither side breaks the sequence. | `[R10-copy-vs-source-first-interview]`: in 9/13 First Interview On mismatches, the source interview predates Applied On, while the copy is plausible in 13/13. `[R10-copy-vs-source-offered]`: in 3/3 Offered On mismatches, the source offer date precedes Final Interview On. All 12 are on APP-00001 to APP-00019 | `decision_log.md` DEC-015; `data_quality_audit.md` §DQ-15 |
| RV-04 | **High** | The Referral comparison is overstated. "Referral contributes the same 26.9%" and "Referral leads on every measure" rest on **7 Referral-labelled hires, none of which has a Referred By link**. 4 of the 7 come from 2 people (DQ-04). | `[R3-referral-hires-without-link]` 7/7. `[R3-referrer-linked-hires]`: only 3/26 hires have a referrer, all with non-Referral Source. `[R3-strict-referral]`: under strict attribution Referral has 3 hires, Job Board 6/26 = 23.1%, and 7 hires are "Referral label, no referrer" | `phase2_summary.md:48, 106`; `findings_table.csv` F-A |
| RV-05 | **High** | Wilson 95% intervals are presented as the uncertainty of rates computed on what is presumed to be a complete snapshot. They answer a sampling question nobody asked. They also assume independence, which repeat candidates violate. The assumption was not recorded. | 4 candidates hold 2 offers each, and 2 candidates hold 2 hires each (`[R4-multi-offer-candidates]`, DQ-04). Intervals appear in the F-B row of `findings_table.csv`, in `phase2_summary.md` §2–5 and in `data_quality_audit.md` §7.2 | §3.6 |
| RV-06 | Medium | The as-of date (DEC-010) is the bulk-import date, not a verified business date. It is logged as "Active" although its assumption ASM-006 is "Open". The stated rationale, "latest business event = Applied On 2026-08-27", ignores 3 Candidate Created On values *after* the import. That rationale rests on a single application. | `[R1-date-after-import]`: Created On reaches 2026-08-30 (3/300). `[R1-max-applied]`: 1/350 applications on 2026-08-27. Sensitivity: §3.1 | `decision_log.md` DEC-010; `assumptions_register.md` ASM-006; `src/data.py:19` |
| RV-07 | Medium | The duplicate evidence is uneven. Identity fields match on all 6 pairs, but in 4 of the 6 the Years Experience is impossible for one person. M-A8 uses Created On as "first touch", which DQ-14 shows is unreliable. The audit's APP-00002 example only holds under Created On. A link to DQ-03 was missed. | `[R2-pair-1…6]`. All 8 reused Application IDs (DQ-03) belong to duplicate-pair candidates. `[R3-first-touch-applied]` also gives 8/26, but through a different hire (pair 6 instead of pair 3) | `data_quality_audit.md` §DQ-02; `metric_calculations.csv` M-A8 |
| RV-08 | Medium | The DQ-25 framing ("compensation units?") is likely wrong. The units look internally consistent. The 0.29–5.4× spread comes from comparing a *person's* expectation with a *role's* pay band. | `[R7-*]`: 300/300 +91 phones; 0/636 values below 100,000; Expected/Current median 1.30 (range 0.62–1.66); r = 0.87 between experience and Expected CTC; 29/36 offers inside the band; only 93/350 applications have Expected CTC inside the opening's band | `dq_issues.csv` DQ-25; open question Q7 |
| RV-09 | Medium | Not reported: applications closed before the offer decision also affect **declines**, not just hires (DQ-18 covers hires only). Also, interviews were scheduled *after* rejection or withdrawal. | `[R10-dates]`: Decision On ≤ Closed On fails for 4/5 declined; last interview ≤ Closed On fails for 7/84 rejected or withdrawn | Proposed new DQ-26 and DQ-27 |
| RV-10 | Medium | Not reported: **stale Active applications**. Treating Active as "in flight" and Closed as "outcome complete" (M-FCc-*) assumes Status is current. It often is not. The funnel is a mixed snapshot of applications at different stages of maturity, not a cohort. | `[R5-stale-active]`: 50/105 Active have no activity for more than 90 days (Applied 27/45, maximum 401 days). `[R5-active-on-filled]`: 55/105 are on Filled openings. `[R5-cohort-mix]`: applications span 2025-Q2 to 2026-Q3 | Proposed new DQ-28 |
| RV-11 | Medium | Decision-trail gaps: | | `decision_log.md` |
| | | • DEC-010, DEC-011 and DEC-015 change metrics, yet are logged "Active" with approval "Analyst (proposed)" | | |
| | | • the decision log has no alternatives-considered field | | |
| | | • at least 10 working assumptions are unregistered (§4.2) | | |
| RV-12 | Low | `dq_issues.csv` is described as holding "all record IDs", but DQ-14 lists 40 of 90. DQ-22 and DQ-24 list none. | `src/audit.py:286` (`ca[:40]`) | README; `data_quality_audit.md:6, 129` |
| RV-13 | Low | README, DEC-004 and the test docstring say "pandas + DuckDB". The Python implementation uses no pandas (it is pinned but unused). | `grep` finds no pandas import in `src/` | `README.md:14` |
| RV-14 | Low | DuckDB verification covers 36 headline checkpoints only. The following are single-implementation numbers: | `queries/verify_phase2.sql` | `phase2_summary.md` §5 |
| | | • M-Q, M-T, M-D, M-I, M-R2, M-B5, M-A3 and M-A4 | | |
| | | • 15 DQ checks | | |
| | | • everything in summary §5 | | |
| | | Phase 2.1 independently re-derives funnel, department, attribution and offer counts. | | |
| RV-15 | Low | "Job Board candidates reach interview at a similar rate to other channels" stretches the data. Job Board is 38.1%, against 38.7–48.4% for other non-referral channels and 76.9% for Referral. | `metric_calculations.csv` M-Q1-* | `phase2_summary.md:105` |
| RV-16 | Low | M-T0 says "DQ-13 records excluded", but the code excludes only 2 of the 6 DQ-13 conditions. Per-department n uses 22 of 26 hires (Product 3/5, Data 4/5, Finance 2/3). | `src/metrics.py:233-240` | `metric_calculations.csv` M-T0, M-T1 |
| RV-17 | Low | Not reported: 4 of 36 offers went to candidates **already hired** through another application, including 1 Pending and 1 Declined. This could be internal mobility, and it bears on how acceptance should be read. | `[R4-offer-after-prior-hire]`: OFF-00005, OFF-00006 (Declined), OFF-00007 (Pending), OFF-00035 | Proposed new DQ-29 |
| RV-18 | Info | The INV-007 QC claim "every x/y fraction is traced" did not cover numbers written in prose, which is how RV-01 slipped through. The process gap is free-text numbers in markdown. | INV-007 | `investigation_log.md` |
| RV-19 | Info | The pending-offer text is precise but incomplete. The 4 Pending offers with decision dates were decided 11–16 days after the offer, inside the 2–20-day range of decided offers. That supports "status not updated" over "date wrong". | `[R4-pending-with-decision]`, `[R4-decided-lag]` | `data_quality_audit.md` §DQ-06 |

## 3. Recheck of the critical analysis (Part 2)

### 3.1 Snapshot date
**Verified:**
- All 892 `createdTime` values fall between 2026-08-27T16:39:09Z and 16:40:02Z.
- The maximum business dates are:

  | Field | Maximum |
  |---|---|
  | Applied On | 2026-08-27 (1 record) |
  | Closed On | 08-17 |
  | Decision On | 08-20 |
  | Interviews.Scheduled On | 08-06 |
  | Candidates.Created On | **08-30** (3 records after the import) |

- Future-dated fields that are legitimate: Target Close (1, up to 09-04) and Proposed Start Date (4, up to 10-01).

**Conclusion.** 2026-08-27 is the **bulk-import date**. It is not a verified business as-of date. The data's own "now" is at least 2026-08-27 and possibly 2026-08-30, unless the 3 future Created On values are entry errors.

**DQ-13.** It calls those 3 values impossible "after snapshot date". That is circular, because the snapshot date was itself inferred. They are better described as "after the import timestamp".

**Sensitivity** `[R1-sens-*]`:

| As-of date | Pending ages (days) | Stale (>30 days) | M-B3 | DQ-12 |
|---|---|---:|---:|---:|
| 2026-08-27 | 20, 23, 69, 117, 222 | 3 | 76.5% | 10/11 |
| 2026-08-30 | 23, 26, 72, 120, 225 | 3 | 76.5% | 10/11 |
| 2026-11-24 (extraction) | 109–311 | 5 | **72.2%** | 11/11 |

Headline results are unchanged within 08-27 to 08-30. Only an extraction-date view changes M-B3, and it then *coincides* with the VP's 72.2%.

**Assumption:** ASM-006 stays Open (customer question C-01).

### 3.2 Duplicate candidates: evidence for each pair `[R2-pair-n]`
All 6 pairs share the normalised name, phone, city, current company and email domain. Name collisions and phone collisions are exactly the same 6 groups. The `f.last@` email pattern occurs on only 6 of 300 candidates, exactly one record in each pair.

| Pair | Records | Source | Years Experience | Created apart | Same person plausible? | Hire |
|---|---|---|---|---|---|---|
| P1 | CAND-00009 / 00010 | JB / JB | 8.8 / 5.1 | 90 days | **No** (−3.7 years in 3 months) | APP-00310 |
| P2 | CAND-00012 / 00011 | JB / JB | 8.7 / 5.3 | 114 days | **No** | none |
| P3 | CAND-00001 / 00002 | **JB / Referral** | 3.2 / 1.1 | 425 days | **No** | APP-00002 |
| P4 | CAND-00006 / 00005 | JB / JB | 7.4 / 7.9 | 155 days | Yes (same Current CTC and notice period) | none |
| P5 | CAND-00008 / 00007 | JB / JB | 0.9 / 8.4 | 439 days | **No** (+7.5 years in 14 months) | none |
| P6 | CAND-00004 / 00003 | **Referral / JB** | 7.6 / 7.6 | 46 days | Yes | APP-00004 |

**Reading:**
- *Interpretation:* the identity evidence is strong for all 6 pairs. The profile attributes contradict a single person in 4 of them.
- So these are **identity collisions with conflicting profile data**: either duplicate records where one profile is wrong, or seeded test data. The data cannot tell which.
- "Probable duplicate" stays a *Suspicious pattern*. It is strong for P4 and P6 and weaker for P1, P2, P3 and P5.

**Also verified:** all 8 reused Application IDs (DQ-03: APP-00001, -05, -07, -10) belong to duplicate-pair candidates.

**Hires at each level:**

| Level | Hires |
|---|---:|
| Application | 26 |
| Distinct candidate records | 24 |
| Distinct persons after merging pairs | **24** |

No pair has a hire on both records, so merging moves attribution but not counts.

### 3.3 Channel attribution (every variant and its denominator)
**Verified:** Applications has **no Source field** `[R3-app-source-field]` 0/350. Source exists only per candidate, and Referred By exists only per application. Referred By is constant across all applications of every candidate with more than one application (50/50), so in practice it behaves like a *candidate* attribute.

| Variant | Rule | Numerator / denominator | Job Board share | Metric |
|---|---|---|---:|---|
| V0 as recorded | Candidates.Source | JB hires / all 26 hire applications | **7/26 = 26.9%** | M-A0 |
| V1 distinct candidates | V0, one row per hired candidate record | / 24 hired candidates | 7/24 = 29.2% | M-A1 |
| V2 referrer override | Referred By present → Referral, else Source. Referral-labelled applications with no referrer *stay* Referral (asymmetric, unregistered: ASM-P11) | / 26 | 6/26 = 23.1% | M-A2 |
| V3 = V1 + V2 | | / 24 | 6/24 = 25.0% | M-A3 |
| V4 strict referral (new) | Referral only with a referrer link. Referral label without link is shown separately | / 26 | 6/26 = 23.1% (Referral 3; "label, no link" 7) | `[R3-strict-referral]` |
| V5 merged, first touch by Created On | Duplicate pairs merged; the earliest-created record's Source wins | / 26 | 8/26 = 30.8% | M-A8 |
| V6 merged, first touch by earliest Applied On (new) | as V5 but by first application | / 26 | 8/26 = 30.8% (via P6, not P3) | `[R3-first-touch-applied]` |

**Hires by Source and referrer link** `[R3-xtab-hires]`:

| Source | No referrer link | With referrer link |
|---|---:|---:|
| Job Board | 6 | 1 |
| Referral | **7** | **0** |
| Career Site | 4 | 1 |
| Agency | 3 | 1 |
| LinkedIn | 3 | 0 |

**Robust across every variant:** Job Board's hire rate per application is 2.7–3.4%, the lowest of any channel with hires (the next lowest is 9.7%), on 67.4% of applications `[R3-rate-V0/V4/V5/V6-*]`:

| Variant | Job Board rate |
|---|---|
| V0 | 7/236 = 3.0% |
| V4 | 6/219 = 2.7% |
| V5, V6 | 8/236 = 3.4% |

Under V4, linked referrals convert at 3/27 = 11.1%, while Referral-labelled applications with no referrer convert at 7/10 = 70.0%.

**Not robust:** any statement about Referral's share or yield (RV-04).

### 3.4 Offer acceptance
**Verified:**
- **Counts:** 26 Accepted, 5 Declined, 5 Pending.
- **Structure:**
  - 36 offers on 36 applications (no application has 2 offers, so there are no revised or duplicate offers);
  - 32 candidates;
  - all unique Offer IDs.
- **Offer and application states:**

  | Offer status | Application Stage / Status |
  |---|---|
  | Accepted | Hired / Closed (26) |
  | Declined | Offer / Closed (5) |
  | Pending | Offer / Active (5) |

- **Dates:**
  - every decided offer has Offered On ≤ Decision On, 2–20 days apart;
  - 4 of the 5 Pending have a Decision On 11–16 days after the offer (OFF-00002, -07, -13, -20);
  - OFF-00021 has none.
- **Copied dates:** 3 Offered On values on Applications differ from Offers (RV-03).
- **Repeat offers:**
  - 4 candidates have 2 offers;
  - 4 offers went to already-hired candidates (RV-17);
  - CAND-00035 has 2 Accepted offers on the same requisition.

**What 26/31 measures, exactly.** Among the 31 offers made between 2025-10-14 and 2026-08-07 whose recorded Status is Accepted or Declined, 26 (83.9%) are recorded as Accepted.

**What it is:**
- offer-level, not candidate-level. Candidate-level is 24/28 = 85.7% (M-B4);
- Status as recorded;
- it includes 3 offers to already-hired candidates: 2 Accepted, 1 Declined (`[R4-offer-after-prior-hire]`);
- it excludes all 5 Pending, including the 4 that carry a decision date.

**What it is not:**
- acceptance within a time window;
- acceptance for a Q3 cohort;
- acceptance of *started* employees. There is no Started status, and 2 Accepted offers have a start date after the import (`[R4-start-after-import]`).

**On the Pending offers.** Whether they belong in the denominator depends on their true state (C-02).

### 3.5 Funnel
**Verified:**
- Stage reach is perfectly nested: 0 applications are interviewed but not screened, offered but not interviewed, or hired but not offered `[R5-nesting]`.
- Stage and evidence agree. Every Stage = Interview application has an interview record, and no Applied-stage application has a Screened On.

| Stage | Reached | Overall (÷ 350) | Previous-stage conversion |
|---|---:|---:|---:|
| Screened | 279 | 79.7% | 279/350 = 79.7% |
| Interviewed | 143 | 40.9% | 143/279 = 51.3% |
| Offered | 36 | 10.3% | 36/143 = 25.2% |
| Hired | 26 | 7.4% | 26/36 = 72.2% |

**The cohort is not consistent.** These are 350 applications from 2025-05-06 to 2026-08-27 at very different maturities:

| Applied | Active | Closed |
|---|---:|---:|
| 2025-Q3 | 9 | 17 |
| 2026-Q2 | 48 | 118 |
| 2026-Q3 | 22 | 24 |

The "closed only" variant assumes Closed means outcome-complete and Active means in flight. In fact 50 of the 105 Active applications have had no activity for more than 90 days (RV-10). Step conversions are therefore snapshot ratios, not cohort conversion rates.

**Proposed:** report a cohort of applications from 2025-Q3 to 2026-Q1, which is mature, alongside the snapshot. This needs PM approval.

### 3.6 Confidence intervals
A Wilson interval answers: if these records were a random sample from a stable process, where might the process rate lie?

**Two problems:**
1. **For describing what happened**, the snapshot is presumed complete (ASM-010), so 26/31 has no sampling error. The uncertainty that matters is **definitional** (72.2–86.1%), **data quality** (4/5 Pending carry decision dates) and **small-number volatility**.
2. **For forecasting Q3**, an interval is defensible, but only with stated assumptions: stationarity, which is doubtful across 15 months, and independence, which repeat candidates violate. Neither was registered.

**Recommendation (needs PM decision):**
- In D1, D3 and D5, report **observed rate with counts**, the **definitional sensitivity range**, and the **one-record swing**: 1 hire = 3.8 percentage points (n = 26), 1 decided offer = 3.2 points (n = 31) `[R6-*]`.
- Keep Wilson intervals only in the appendix, labelled "process-variability indication, assumes independence", or drop them.
- Do not delete the CSV columns without approval.

### 3.7 Compensation
**Verified** `[R7-*]`:
- **Currency (no currency field exists):** all +91 phones, Indian cities and the term "CTC" suggest INR. This is an inference.
- **Period:** no value below 100,000, out of 636, which is consistent with annual figures.
- **Internal consistency:** Expected/Current CTC has a median of 1.30 (range 0.62–1.66), and Expected CTC tracks experience (r = 0.87).
- **Pay bands:** level bands are ordered (Junior 4–8 lakh, Mid 8–16, Senior 16–30, Lead 28–45; Senior and Lead overlap at 28–30), and 29/36 offers fall inside them.

**Why the 0.29–5.4× range is large.** Candidates' expectations often don't fit the role: only 93/350 applications have Expected CTC inside the opening's band. Examples are a candidate with 0 years' experience offered a Senior role at 4.9×, and one with 9.4 years offered a Junior role at 0.32×.

**Conclusion.** There is no evidence of a **units defect**. The ratio measures candidate-to-role level mismatch, not offer generosity. M-B7 and M-B8 remain unusable for decline analysis. The real question for the customer is whether candidates are linked to the right openings (C-09), not units.

### 3.8 Interview completeness
**Verified** `[R8-*]`:
- 126/143 interviewed applications have exactly 1 interview record, and none has more than 2.
- 11 of 26 hires have only a Screen round recorded.
- Final Interview On exists for exactly the 36 offered applications plus 14 rejected. It is later than the last recorded interview in 44/50 cases (median 8.5 days, maximum 54), and a median 6 days before the offer (`[R8-final-to-offer]`).

**Classification.** This stays a **Suspicious pattern, not a Confirmed defect.** A confirmed defect needs a contradiction that has no valid reading. Here, valid readings exist:
- the Interviews table may be designed to hold only some rounds;
- Final Interview On may itself be a drifted copy (First Interview On drifts by up to 40 days, `[R8-first-interview-drift]`).

It becomes a defect only if Acme confirms the table should hold every round (C-05).

*Interpretation:* hiring after a single Screen is implausible as a process, so the suspicion is strong.

### 3.9 Departments
**Verified** `[R9-*]`:
- **Engineering: 0 hires from 30 applications** (not 20, see RV-01).
  - Only 3/30 reached interview (10%, against 40.9% overall).
  - Its single offer is OFF-00021: Pending for 117 days, the only Pending offer with no decision date.
  - 17 applications were rejected and 3 withdrawn.
  - REQ-2026-017 (Lead) is marked **Filled with 0 hires** (part of DQ-11).
  - *Interpretation:* Engineering's zero is a top-of-funnel and screening drop, plus one unresolved offer. The data cannot say why.
- **Cycle-time sample sizes:** 22 of 26 hires are measurable.

  | Department | Measurable / hires |
  |---|---|
  | Product | 3/5 |
  | Data | 4/5 |
  | Marketing | 5/5 |
  | Finance | 2/3 |
  | Customer Support | 3/3 |
  | Sales | 3/3 |
  | People Operations | 2/2 |

  No department ranking is supportable. That is already stated in Phase 2, but the n per department should be shown against total hires.

### 3.10 Date consistency
All 21 comparisons are in `[R10-dates]`. Copied fields were *not* assumed authoritative, and neither were source tables.

| Comparison (expect left ≤ right) | Violations |
|---|---:|
| Opened On ≤ Applied On | 3/350 |
| Applied ≤ Screened; Applied ≤ Closed; Screened ≤ First Interview (copy); First ≤ Final (copy); Final ≤ Offered (copy) | **0** |
| Applied On ≤ Interviews.Scheduled On (source) | **9/160** |
| Screened On ≤ Interviews.Scheduled On (source) | **9/160** |
| Scheduled ≤ Completed | 4/142 (138 equal) |
| Final Interview On (copy) ≤ Offers.Offered On (source) | **3/36** |
| Last interview ≤ Offers.Offered On; Offered ≤ Decision; Offered ≤ Closed | 0 |
| Decision ≤ Proposed Start | 4/35 |
| Offered ≤ Proposed Start | 3/36 |
| Decision ≤ Closed (Hired) | 17/26 |
| Decision ≤ Closed (Declined) | **4/5** (new) |
| Last interview ≤ Closed (Rejected or Withdrawn) | **7/84** (new) |
| Created On ≤ Applied On | 90/350 |
| Created On ≤ import date | 3/300 |
| Applied On ≤ Target Close | 251/350 (informational: hiring continues past target) |

**Pattern.** The copied fields on Applications are internally sequence-consistent. Every violation sits on a source table, Interviews or Offers, or on fields that are not copies (Closed On, Created On). The 12 source records that conflict with their copies all sit on the lowest IDs (APP-00001 to APP-00019). *Interpretation:* this is consistent with seeded defects. Either way, DEC-015 cannot be justified as written (RV-03).

## 4. Decision trail audit (Part 3)
The full matrix is in `outputs/decision_traceability.csv`: 45 rows, each mapping finding → evidence → metric → assumption → decision → product implication, with a trace status.

### 4.1 Decisions made without sufficient evidence
| Decision | Problem |
|---|---|
| **DEC-015** (durations use source tables only) | Contradicted by RV-03 |
| **DEC-010** (as-of 2026-08-27) | Evidence is partial; its own assumption ASM-006 is Open; approval was "Analyst (proposed)" |
| **DEC-011** (hire = Stage Hired; hire date = Decision On) | Hire set is well supported (26 = 26). The date choice ignores Proposed Start Date and the fact that "hire" may mean start; alternatives were not logged |
| **DEC-014** (decided-only acceptance) | Correctly marked Proposed. Not a gap, but pending ratification |

### 4.2 Important assumptions not recorded
These are proposed register entries. They are **not added** until you approve.

| Proposed ID | Assumption | Used by |
|---|---|---|
| ASM-P11 | The referrer override is asymmetric: a Referral label without a link stays Referral | M-A2, M-A3, M-A7r |
| ASM-P12 | Candidate Created On represents first touch | M-A8 (contradicted by DQ-14) |
| ASM-P13 | A candidate's Source applies to all their applications | all channel metrics |
| ASM-P14 | Records are independent samples of a stable process | all Wilson intervals |
| ASM-P15 | Source tables are more reliable than copied fields | DEC-015, DQ-13 exclusions, M-T2 |
| ASM-P16 | CTC values are INR, annual | DQ-19, DQ-20, DQ-25, M-B7/B8 |
| ASM-P17 | Status Active means in flight and Closed means outcome-complete | M-FCc-*, M-B1 framing |
| ASM-P18 | An application's department is its opening's department | M-T1, M-D1 |
| ASM-P19 | The 2025-05 to 2026-08 history represents Q3 behaviour | any forward-looking use |
| ASM-P20 | Accepted offer = hire (no start confirmation) | M-H0, Claim A denominator |

### 4.3 Decisions recorded without alternatives
**All 15 DEC entries:** the log has no alternatives field. The material ones:

| Decision | Alternatives that should be recorded |
|---|---|
| DEC-010 | extraction date; 2026-08-30 |
| DEC-011 | Closed On (rejected as REJ-006); Proposed Start Date; Accepted offer |
| DEC-014 | the M-B0, M-B3 and M-B4 scenarios are computed, but not logged as considered alternatives |
| DEC-015 | copied fields; per-record "most consistent" rule; sensitivity both ways |

### 4.4 Conclusions that changed but whose rationale is not preserved
| Change | Rationale preserved? |
|---|---|
| Claim A range widened 23.1–29.2% → 23.1–30.8% after M-A8 | Change logged (INV-007 #4). Why first touch uses Created On is **not** |
| Claim B wording "not low" → "not judgeable" | Logged (INV-007 #8), but the original wording and reasoning are **not** |
| DQ-07 rated Critical while classed Suspicious | **No** rationale recorded |
| Referral framed as the strongest channel | Emerged without the link check; **no** record of the alternative reading |
| DQ-05 reclassification | Preserved |

### 4.5 Disagreements between reports, CSVs and logs
1. **Engineering applications:** 20 in `phase2_summary.md:112`, but 30 in the data. There is no CSV row (RV-01).
2. **DQ-13 "0 violations":** stated in the `dq_issues.csv` detail and `data_quality_audit.md:228`, but computed checks show 9 and 3 violations (RV-02).
3. **"All record IDs" in `dq_issues.csv`:** stated in README and audit §1, but DQ-14 lists 40 of 90 (RV-12).
4. **"pandas":** README:14, DEC-004 and the test docstring mention it, but the code doesn't use it (RV-13).
5. **As-of status:** DEC-010 is "Active" while ASM-006 is "Open".
6. **Acme-only:** REJ-003 lists it as a *rejected assumption* while ASM-010 calls it *Open, unverified*. The meaning is the same, but the labels conflict.
7. **M-T0 exclusions:** the label "DQ-13 records excluded" doesn't match the code, which applies 2 of the 6 conditions (RV-16).
8. **DQ-02 example:** "APP-00002… the same person's earlier record says Job Board" only holds when first touch is defined by Created On (RV-07).
9. **No disagreement found** between `findings_table.csv`, `dq_issues.csv`, `metric_calculations.csv`, `verification.csv` and the headline numbers in either report. All 36 SQL checkpoints still match.

## 5. Proposed corrections (none applied, awaiting approval)
| # | Correction | Files | Type |
|---|---|---|---|
| P1 | Engineering 20 → 30. Add per-department funnel rows (applications, interviewed, offered, hires) so the figure is traceable | `phase2_summary.md`, `metrics.py` | Error fix |
| P2 | Replace the hand-typed DQ-13 "0 violations" sentence with computed results for every comparison, distinguishing copied from source fields | `audit.py`, `data_quality_audit.md` | Error fix |
| P3 | Downgrade DEC-015 to *Proposed*. Report duration metrics under both sources; note RV-03 in the DQ-15 treatment | `decision_log.md` (append), DQ-15, M-T2 | Decision change, needs PM |
| P4 | Restate the Referral comparison with the strict variant (V4). Make the Claim A verdict rest on Job Board yield | `phase2_summary.md`, `findings_table.csv` F-A | Interpretation fix |
| P5 | Reporting standard: observed + sensitivity range + one-record swing; Wilson intervals to the appendix | all reports | Method change, needs PM |
| P6 | DEC-010 → *Proposed*, with alternatives and sensitivity (§3.1). DQ-13 wording "after import timestamp" | logs, `audit.py` | Decision trail |
| P7 | Pair-level evidence table in DQ-02; add the DQ-03 link; add the V6 first-touch variant; caveat M-A8 | audit, `metrics.py` | Evidence |
| P8 | Reframe DQ-25 as candidate-to-role mismatch; replace Q7 with C-09 | audit, `dq_issues.csv` | Interpretation fix |
| P9 | New issues: DQ-26 (closed before decision, declines 4/5); DQ-27 (interview after closure 7/84); DQ-28 (stale Active 50/105); DQ-29 (offers to already-hired 4/36). Existing IDs unchanged | `audit.py` | Addition |
| P10 | Register ASM-P11 to P20; add an alternatives column to new decision entries (append-only) | logs | Decision trail |
| P11 | Write all DQ-14 evidence IDs; fix the pandas wording; fix the M-T0 label; reword summary §5.1 | `audit.py`, README, `metrics.py` | Hygiene |
| P12 | Extend the DuckDB verification to the department, channel-quality and new DQ checks; add a test that numbers in markdown appear in CSVs | `queries/`, `tests/` | QC |
| P13 | Add a mature-cohort funnel (applications 2025-Q3 to 2026-Q1) as a variant | `metrics.py` | Addition, needs PM |

## 6. Assignment completeness
See `outputs/assignment_completeness.md`. Customer questions are in `outputs/open_questions_for_customer.md`.

## 7. QC for this review
- **Raw data:** SHA-256 checksums of all 9 files in `data/raw` are identical before and after this review. Files remain `-r--r--r--`. `src.data.load` re-verified the manifest on every run.
- **Tests:** pytest 48/48 pass, unchanged (the run is in the final message). No new tests were added; the review script is evidence, not a deliverable metric.
- **Scope:** no Phase 2 report or CSV was modified. New files:
  - `src/review_phase2_1.py`
  - `outputs/phase2_1_checks.csv`
  - the 4 review documents
  - INV-008 appended to `audit/investigation_log.md`
- **Privacy:** no names, emails or phone numbers appear in any new file. Identity fields were compared in memory only. The PII leak test covers `outputs/*.csv|md`, including the new files.
