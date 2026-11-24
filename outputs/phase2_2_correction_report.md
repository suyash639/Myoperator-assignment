# Phase 2.2: Approved Corrections and Decision Governance

**Basis:** the PM decisions of 2026-11-24 (numbered 1–7 below) on the Phase 2.1 review (`phase2_1_review.md`, which is left unchanged as a historical record).

**Scope:** corrections to the Phase 2 outputs and the decision trail. No Phase 3 work; no roadmap decisions. No Airtable calls. Raw data untouched.

## 1. Headline impact

**No headline value changed.** Each was re-derived and matches:

| Metric | Value | Now labelled |
|---|---|---|
| Job Board share of hires | 26.9% (7/26) | Source as recorded, primary |
| Decided-offer acceptance | 83.9% (26/31) | offer-level, provisional primary |
| All-issued-offer ratio | 72.2% (26/36) | — |
| Funnel | 350 → 279 → 143 → 36 → 26 | — |

What changed:
- **Labelling:** primary, variant and level are now explicit on every metric.
- **Uncertainty:** Wilson intervals removed. Each rate now reports single-record and definition sensitivity.
- **Two factual errors fixed:** the Engineering count, and the DQ-13 text.
- **Date governance:** DEC-015 was replaced by DEC-019.
- **New evidence:** 4 new issues, 66 new metric rows, and 18 new SQL checkpoints.

| Item | Phase 2 | Phase 2.2 |
|---|---:|---:|
| Metric rows | 116 | 182 |
| DQ issues | 25 | 29 |
| SQL checkpoints (all match) | 36 | 54 |
| Tests (all pass) | 48 | 59 |
| Traceability rows (0 dangling references) | n/a | 38 |

## 2. PM decisions and how each was implemented

| # | PM decision | Decision ID | Implementation |
|---|---|---|---|
| 1 | Approve factual corrections supported by independent evidence; do not auto-approve interpretations | DEC-023 | §3 classification; §5 interpretations not adopted |
| 2 | 26/31 is the provisional offer-level decided-offer metric; keep 26/36 as the all-issued ratio; distinguish offer-level from candidate-level | DEC-016 (supersedes DEC-014) | M-B1 and M-B0 relabelled. New `level` column on every metric. M-B4 labelled candidate-level, "not comparable". M-B9 and M-B10 added for offers to already-hired candidates |
| 3 | Source as recorded is primary; alternatives shown separately; Referral not a proven high performer | DEC-017, REJ-011 | M-A0 relabelled primary. Variants M-A1/2/3/8/9/10 and channel rates M-A7r/s/m/f. A Referral caveat on M-A0r, M-A7-Referral and M-Q*-Referral. Summary and F-A rewritten |
| 4 | Remove Wilson intervals unless a sampling interpretation is justified | DEC-018 | Not justified (ASM-014), so the `ci95_low`/`ci95_high` columns are removed from `metric_calculations.csv`, F-B and both reports. `single_record_pp` is added. `wilson()` is kept only as an unused utility |
| 5 | Neither date source universally authoritative; retain both; flag contradictions and impossible chronology separately | DEC-019 (supersedes DEC-015), REJ-010 | DQ-15 = copy-vs-source contradictions, with a computed "which side fits the chronology" count. DQ-13 = impossible chronology within one provenance. M-T2 lags reported under both sources |
| 6 | Record 2026-11-24 as extraction and 2026-08-27 as apparent import; neither is the confirmed cutoff; show impact | DEC-020 (supersedes DEC-010) | `src/data.py` constants. Cutoff sensitivity at 2026-08-30 and 2026-11-24 in M-B3, DQ-07, DQ-12, DQ-28 and M-K. ASM-006 reworded |
| 7 | Keep the full funnel; add a completed cohort only after verifying sufficiency; document the rules | DEC-021 (PM) + DEC-022 (analyst rules, *Proposed*) | Sufficiency verified (§4). M-K* rows added. Eligibility, exclusion and stall rule documented |

## 3. Classification of the Phase 2.1 proposed corrections (P1–P13)

| # | Proposed correction | Classification | Rationale | What was done |
|---|---|---|---|---|
| P1 | Engineering 20 → 30; add per-department funnel rows | **Approved factual correction** | Raw records give 0 hires from 30 applications. Verified in Python, DuckDB (M-DF-Engineering-hired, -interviewed) and the Phase 2.1 script (R9-Engineering) | M-DF-{department}-{interviewed, offered, hired} rows for all 8 departments. Summary §5.2 now says 0/30 hires, 3/30 interviewed, 1/30 offered (OFF-00021 Pending), REQ-2026-017 Filled with 0 hires. **No causal explanation given** (C-10) |
| P2 | Replace the hand-typed DQ-13 "0 violations" sentence with computed results | **Approved factual correction** | The sentence was never computed. Source-table checks fail 9/160 (interview before Applied On) | DQ-13 rebuilt: 16 computed checks, each labelled with its provenance, zero-violation checks included. Affected count unchanged (23/846); verified in SQL |
| P3 | Downgrade DEC-015 to Proposed; report durations under both sources | **Needs modification** | PM decision 5 goes further than "downgrade": neither source is authoritative | DEC-015 superseded by DEC-019. Both values retained; M-T2 source and copy rows; DQ-15 treatment rewritten |
| P4 | Restate Referral with the strict variant; base the Claim A verdict on Job Board yield | **Needs modification** | PM decision 3: Source as recorded stays primary. Strict referral is a sensitivity, not a replacement | M-A9, M-A9r, M-A9n and M-A7s-* added as variants. Verdict now rests on the Job Board yield range (2.7%–3.4% across 5 attributions). Referral is explicitly "not proven" |
| P5 | Observed + sensitivity + one-record swing; Wilson intervals to an appendix | **Approved, appendix option dropped** | PM decision 4. No sampling interpretation was justified, so the intervals are not kept anywhere in reporting | See PM decision 4 |
| P6 | DEC-010 → Proposed with alternatives; DQ-13 wording "after import timestamp" | **Needs modification** | PM decision 6 specifies the record: extraction date and import timestamp, no confirmed cutoff | DEC-020. The DQ-13 check is named "Candidate Created On ≤ bulk-import date". DQ-22 treatment and the DQ-12 title reworded |
| P7 | Pair-level DQ-02 evidence; DQ-03 link; V6 first-touch variant; M-A8 caveat | **Approved factual correction** | Each fact verified from records | DQ-02 detail is now fully computed (shared city, company and email domain 6/6; `f.last@` pattern 6/300; experience implausible in 4/6). DQ-03: 8 of 8 on duplicate-pair candidates. M-A10 and M-A7f-* added. The M-A8 note cites DQ-14 |
| P8 | Reframe DQ-25 as candidate-to-role mismatch; replace Q7 | **Needs modification** | The unit-consistency evidence is factual and approved. The *cause* ("candidate-to-role mismatch") is an interpretation, not proven | DQ-25 detail now lists computed unit checks. The cause is stated as a **hypothesis**. ASM-016 registered; C-09 covers the question |
| P9 | New issues DQ-26 to DQ-29 | **Approved factual correction** | Counts verified three ways | DQ-26 (4/5), DQ-27 (7/84), DQ-28 (50/105), DQ-29 (4/36). See the notes below this table |
| P10 | Register ASM-P11..P20; alternatives column | **Approved** (PM items H and I) | — | ASM-011 to ASM-020 (mapping in §7) and ASM-021. Decision log restructured (§6) |
| P11 | Hygiene: all DQ-14 IDs; pandas wording; M-T0 label; summary §5.1 wording | **Approved factual correction** | Each is a documented mismatch | Done; see the inconsistency table (§4.1) |
| P12 | Extend DuckDB verification; test that report numbers exist in CSVs | **Approved** (QC) | Prevents a repeat of the Engineering error (RV-01) | SQL extended to 54 checkpoints, 54/54 match. `tests/test_phase2_2.py` checks every fraction in both reports against the CSVs. `src/traceability.py` validates all references (DEC-024) |
| P13 | Mature-cohort funnel | **Approved conditionally**, then implemented | PM decision 7: verify sufficiency first | See §4 |

**Notes on P9:**
- **DQ-29 classification:** Suspicious pattern rather than Legitimate, because whether these are internal moves is unknown.
- **DQ-28 definition:** last activity now includes offer and decision dates, which the Phase 2.1 R5 check omitted. The count is the same, 50/105.

None of P1–P13 was rejected outright. Interpretations from Phase 2.1 that were **not** adopted are listed in §5.

## 4. Items C–J of the implementation brief

### C. The 8 report/CSV/log inconsistencies from Phase 2.1 §4.5
| # | Inconsistency | Fixed in |
|---|---|---|
| 1 | Engineering applications "20" vs 30 | `phase2_summary.md` §5.2 now cites M-DF rows. A fraction test makes this class of error fail the test suite |
| 2 | DQ-13 "0 violations" vs computed violations | `src/audit.py` → `dq_issues.csv`; `data_quality_audit.md` §5 |
| 3 | "All record IDs" vs DQ-14 listing 40/90 | DQ-14 now lists all 90; DQ-24 lists its 138. DQ-22 lists none by design: it applies to all 892 records, stated in its denominator. Regression test added |
| 4 | "pandas + DuckDB" vs plain-Python code | README, DEC-004 (annotated), `tests/test_phase2.py` docstring |
| 5 | DEC-010 "Active" while ASM-006 "Open" | DEC-010 marked Superseded by DEC-020; ASM-006 reworded as provisional cutoff, Open |
| 6 | REJ-003 "rejected" vs ASM-010 "open, unverified" | REJ-003 annotated "reclassified: unverified, tracked as ASM-010" |
| 7 | M-T0 label "DQ-13 records excluded" vs code using 2 of 6 conditions | M-T0 definition now states the exact rule, and notes "22 of 26 hires measurable". M-T1 notes give measurable/total per department |
| 8 | DQ-02 example "APP-00002 … earlier record says Job Board" holds only under Created On | Example removed. The audit now shows both first-touch rules and which hire moves under each |

**Other hand-typed claims found and replaced with computed text:**
- **DQ-04:** "Both are Source=Referral with no Referred By link" is now computed; it is true.
- **DQ-09:** "Includes 2 Hired applications…" is now computed; it is true.
- **DQ-16:** "typically Screen or Technical 1" is now a computed round breakdown.
- **DQ-24:** "the only deviations are the 4 DQ-13 records" is now computed; it is true.
- **DQ-06:** the decision-lag comparison is computed.
- **DQ-07:** a severity rationale is recorded.

### D. Engineering
0 hires from 30 applications; 3 interviewed; 1 offered (Pending). Verified by M-DF-Engineering-*, DuckDB and Phase 2.1 R9. Interpretation is limited to the facts; the cause is asked of the customer (C-10).

### E. DQ-13 and new chronology issues
- DQ-13 is rebuilt as described under P2.
- New chronology-related issues: DQ-26 (declines closed before decision) and DQ-27 (interviews after closure).
- Cross-provenance conflicts (e.g. Final Interview On (copy) after Offers.Offered On (source), 3/36) are reported under **DQ-15 as contradictions**, not as impossible chronology (PM decision 5).

### F. DEC-015
Superseded by DEC-019. ASM-015 is registered and **rejected** as a general rule (REJ-010).

### G. Wilson intervals
Removed from main reporting (DEC-018), as described under PM decision 4.

### H. Assumptions
ASM-011 to ASM-021 are registered. Each was checked against ASM-001 to 010 and none duplicates an existing entry. ASM-006 was reworded, not duplicated.

### I. Decision log
- **Restructured into:**
  - A: PM-approved;
  - B: Analyst proposals;
  - C: Analyst process.
- **New columns:** approval type, alternatives considered, evidence and rationale.
- **History preserved:** all historical IDs and decision text are kept. Superseded entries (DEC-010, DEC-014, DEC-015) are marked, not deleted.
- **Added:** DEC-016 to DEC-024, REJ-010 and REJ-011.
- **Retrospective alternatives:** where alternatives for older decisions were not recorded at the time, the entry says so.

### J. Traceability
- `decision_traceability.csv` is now generated by `src/traceability.py` on every `run_phase2`.
- It has 38 rows: F-A, F-B, DQ-01 to DQ-29, and 7 insight rows.
- Each row carries the chain finding → evidence → metric → assumption → decision → product implication, plus open questions and Phase 2.1 references.
- `validate()` confirms every metric, DQ, ASM and DEC/REJ reference resolves: **0 dangling**.

### Completed-cohort sufficiency (DEC-021, DEC-022)
| Check | Result |
|---|---|
| Applications in window (Applied On 2025-07-01 to 2026-03-31) | 134 (38% of all) |
| Closed | 99 |
| Active | 35, all with no activity for more than 90 days at 2026-08-27 **and** at both sensitivity cutoffs |
| Excluded as in flight | 0 |
| Sufficiency criteria (≥100 applications, ≥10 offers) | Met: 134 applications, 16 offers, 12 hires |
| Limitations | 2/16 cohort offers are still Pending; offer → hire step n = 16 (one record = 6.2 percentage points) |

**Governance note:** the thresholds were set by the analyst during this phase, after the window counts had been seen in Phase 2.1. They are not pre-registered. DEC-022 is therefore *Proposed*, pending PM ratification.

## 5. Interpretations not adopted (insufficient evidence)

| Source | Interpretation | Reason not adopted | Where it now appears |
|---|---|---|---|
| Phase 2.1 §3.10, audit §7 | "Defects appear seeded" | Cannot be verified from the data | Limitation only, labelled *interpretation*; C-16 |
| Phase 2.1 §3.8 | "Hiring after a single Screen is implausible, so the suspicion is strong" | A process judgement, not evidence | DQ-16 stays *Suspicious*, with no strength claim |
| Phase 2.1 RV-08 | DQ-25 is "candidate-to-role mismatch" | Cause unproven | DQ-25 states it as a *hypothesis* |
| Phase 2.1 RV-07 | 4/6 pairs "are not the same person" | Implausible experience values show conflicting profile data, not proof of different people | DQ-02: "implausible for one person" as a computed flag; ASM-008 stays Open |
| Phase 2.1 §3.9 | "Engineering's zero is a top-of-funnel and screening drop" | Partly causal | Only counts reported; C-10 |
| Phase 2.1 RV-19 | "Status not updated fits better than date wrong" | Supported but not proven | Kept only as a labelled *interpretation* in DQ-06 |

## 6. Files changed

**Code:**
- `src/data.py`: snapshot constants.
- `src/metrics.py`: rewritten. Existing metric IDs are preserved and new IDs added.
- `src/audit.py`
- `src/run_phase2.py`
- `src/traceability.py` (new)
- `queries/verify_phase2.sql`
- `tests/test_phase2_2.py` (new, 11 tests)
- `tests/test_phase2.py`: docstring only.
- `tests/__init__.py` (new, empty)

**Outputs** (regenerated or rewritten):
- `data_quality_audit.md`
- `phase2_summary.md`
- `findings_table.csv`
- `metric_calculations.csv`: columns changed. `ci95_*` removed; `level` and `single_record_pp` added.
- `dq_issues.csv`
- `decision_traceability.csv`
- `verification.csv`
- `phase2_1_checks.csv`: regenerated, unchanged.

**Audit trail:**
- `audit/decision_log.md`
- `audit/assumptions_register.md`
- `audit/investigation_log.md` (INV-009 appended)
- `README.md`

**Unchanged by design:**
- `phase2_1_review.md`
- `open_questions_for_customer.md`
- `assignment_completeness.md`
- `table_profiles.csv`
- `relationship_integrity.csv`

## 7. ID mapping (Phase 2.1 proposals → registered IDs)
| Proposed | Registered as |
|---|---|
| ASM-P11 to ASM-P20 | ASM-011 to ASM-020 (same order) |
| *(new in 2.2)* stall threshold | ASM-021 |
| DQ-26 proposed (closed before decision, declines) | DQ-26 |
| DQ-27 proposed (interview after closure) | DQ-27 |
| DQ-28 proposed (stale Active) | DQ-28 |
| DQ-29 proposed (offers to already-hired) | DQ-29 |

`phase2_1_review.md` and `open_questions_for_customer.md` still use the ASM-P labels, because they are historical.

## 8. Quality control
| Check | Result |
|---|---|
| Raw data | SHA-256 of all 9 files in `data/raw` identical to the pre-Phase-2.1 hashes; still `-r--r--r--` |
| Airtable API calls | 0 |
| Tests | **59/59 pass**: the original 48 plus 11 new |
| DuckDB independent verification | **54/54 match** |
| Phase 2.1 independent checks (`src.review_phase2_1`) | Re-run; they agree on every corrected number: Engineering, strict and merged attribution, DQ-14, DQ-26 to DQ-29, cutoff sensitivity, person-level hires |
| Report numbers traced to CSVs | Every fraction in both reports passes the test |
| Traceability references | 0 dangling |
| Determinism | Two consecutive runs produce byte-identical CSVs |
| Personal data | The PII test passes over all `outputs/*.csv` and `outputs/*.md`. New outputs carry only record IDs and business IDs |
| Git | Nothing committed or pushed; no remote |

## 9. Decisions still open for the PM
1. Ratify or amend **DEC-022**: cohort sufficiency thresholds and the 90-day stall rule (ASM-021).
2. Ratify **DEC-011**: hire = Stage Hired; hire date = Decision On.
3. The final D3 acceptance specification (DEC-016 is provisional).
4. Send the customer questions (C-01 to C-16).
