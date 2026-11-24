# Phase 3.1: Focused Review and Correction of Phase 3

**Scope:** a targeted correction pass. The **three builds, three non-builds, 6.0 engineer-week total, per-build totals (B1 2.5, B2 2.0, B3 1.5) and the prioritisation scores are unchanged.** Only B3's component split changed: B3.3 became B3.3a (0.25) and B3.3b (0.25), so the duplicate warning is a self-contained 0.5 cut.

**Status:** every change is a **proposal awaiting PM approval** (DEC-032 to DEC-037). All effort figures remain **PM planning estimates** until engineering validates them (ASM-022).

## 1. Changes by review point

### 1. B1: offer lifecycle (DEC-032, DEC-033)
| Requirement | What was done | Where |
|---|---|---|
| Precise transitions into Expired, Withdrawn, Rescinded, Superseded | 8 allowed transitions. Accepted is terminal except for a renege (→ Withdrawn) or a rescission (→ Rescinded). There is no return to Pending, and all other transitions are rejected | Spec §8; `src/offer_lifecycle.py` |
| Who triggers each, and which timestamp | Each transition lists its permitted roles: recruiter, hiring manager, recruiting-ops lead or system. Superseded is system-only. Rescinded needs the hiring-manager or recruiting-ops-lead role. Each transition records one named business date. Every event also records an uneditable `recorded_at` | Spec §8 table, §8.2 |
| Prevent contradictions such as Pending with a decision date | Field invariants (spec §8.1): a Pending offer cannot carry any resolution date; `decision_on` exists only on decided or reneged offers; every date ≥ `offered_on`. Invalid saves are rejected | `violations()` |
| Revised and superseded offers in the metric | A Pending offer becomes Superseded when revised and is excluded from every metric. A resolved offer keeps its status, and only the latest offer per application counts (REVISED_AFTER_RESOLUTION counter). An Accepted offer cannot be revised. A revision after the as-of date supersedes nothing at that date | Spec §3.6, §8.3 |
| Auditable status changes | Status changes only through an append-only event log (actor, role, from, to, business_date, recorded_at, reason). Corrections are by the recruiting-ops lead only, are logged with before/after values, and are rolled back if they would leave a contradiction. Legacy conflicts are flagged, never rewritten. New guardrail SM-B1-G3: 0 status changes without an event | Spec §8.2; `correct()` |

### 2. B2: inactivity queue (DEC-035)
| Requirement | What was done |
|---|---|
| Configurable threshold | Configurable per stage at org level: default 90 days, range 14–365, changes audited. Evidence that this matters: on the snapshot, 93/105 Active applications are inactive at 30 days, 71/105 at 60, 50/105 at 90, 43/105 at 120 and 29/105 at 180 (E-B2-*). The default reproduces DQ-28 |
| Inactivity is not abandonment | The flag reads "Inactive > N days". "Abandoned" exists only as a **recruiter-confirmed disposition**. SM-B2-2 is renamed to the inactivity-flag share. New SM-B2-5 measures the share of reviewed flags that recruiters confirm as abandoned. "Stalled" wording removed from the Phase 3 documents |
| Opening contradictions are review flags, never corrections | The system never writes an application or opening status; the recruiter resolves or dismisses with a reason. A roadmap acceptance criterion asserts no automatic status write. Review flags reproduce DQ-11 (15/24) |
| 20-application pilot | Retained unchanged, with its stop condition (under 50% confirmed abandoned → cut the queue to opening flags), now measured by SM-B2-5 |

### 3. B3: source intelligence (DEC-036)
| Requirement | What was done |
|---|---|
| Acquisition source vs intake method | **Acquisition source:** how the candidate came to this application, chosen by the recruiter. **Intake method:** how the record entered TalentFlow, *system-derived* from the creation path and never chosen (ASM-029). This also removes the self-reporting risk noted in Phase 3 |
| Controlled taxonomy and referral rules | Taxonomy: Job Board (board name), LinkedIn, Career Site, Agency (agency name), Employee Referral, Campus, Other (describe). Legacy values map 1:1 and history is not rewritten. A **direct referral** is Employee Referral plus a referrer. An **endorsement** is another source plus a confirmed referrer; it is reported separately and never counted as a referral hire. Applied read-only to the snapshot: 3 direct referrals, 24 endorsements, and 10 "referral label, no referrer" needing review. At hire level: 0 direct, 3 endorsements, 7 labels with no referrer (E-B3-src-*, E-B3-hire-*; consistent with M-A9r and M-A9n) |
| Warning-only duplicates | Match on name AND phone. The options are "same person" (attach the new application to the existing record; nothing merged), "different person" (reason required; the pair is remembered), or "unsure" (ops review queue). The reference model has no merge or delete path, and a test asserts it. Guardrails: SM-B3-G2 (0 repeat warnings on dismissed pairs), SM-B3-G3 (0 merges or deletions) |
| False-positive handling | Strict match rule. On the snapshot it fires on exactly the 6 DQ-02 groups, and on 0 additional name-only or phone-only collisions (E-B3-dup-*). Remembered "different person" decisions. Precision decision rule SM-B3-4 (under 50% "same person" over 50 warnings → tighten) |
| First cut if B3 exceeds 1.5 | The duplicate warning (B3.2 + B3.3b = 0.5) is flagged `first_cut` in `phase3_capacity_allocation.csv` and is cut-line order 1. B3.1 and B3.3a are kept |

### 4. D3: offer acceptance (DEC-033, DEC-034)
| Requirement | What was done |
|---|---|
| Review of the 10-offer threshold | Replaced by **reliability tiers**: n < 10 counts only; 10 ≤ n < 30 rate with a low-sample label stating the one-record swing; n ≥ 30 normal. OAM-01 (31) shows normally. OAM-09 and OAM-01b (28) and OAM-08 2026-H1 (19) are labelled. Departments are counts only. DEC-030 is superseded |
| Reliability vs privacy | **Privacy suppression is a separate rule** (spec §3.14). It applies only to breakdown cells and only for viewers without record-level offer access: any cell count below 5 is hidden. The threshold of 5 is ASM-028, pending privacy/legal confirmation. A new `privacy` column in `offer_metric_baseline.csv` shows the result per row |
| Period, as-of, pending and superseded consistent | **Fixed an inconsistency** in the Phase 3 reference implementation: an offer decided *after* the as-of date dropped out of both "decided" and "pending". It now counts as pending at the as-of date (§3.5). Snapshot impact: 0 offers (E-D3-1), so OAM-01 stays 26/31. OAM-01 is periodised by Decision On; OAM-02, OAM-03 and OAM-04 use Offered On and the as-of date; superseding is evaluated only among offers issued by the as-of date |
| Offer-level vs candidate-level | Preserved. The low-sample label names the unit ("1 offer" or "1 candidate"), and the checker still flags any unlabelled 24/28 |

### 5. Engineering estimation (DEC-037)
- All 6.0 engineer-weeks remain explicitly allocated. Every allocation row now carries `estimate_status = PM planning estimate (not validated by engineering)`.
- New `q3_roadmap.md` §0 lists the 8 assumptions behind the 2-engineer, 3-sprint model (ASM-026 expanded; ASM-027 new):
  - dedicated engineers;
  - both full-stack;
  - review, ceremonies and deployment inside the estimate;
  - existing CI/CD, staging and test data;
  - no platform-team migration dependency;
  - design ready by sprint 2;
  - creation path known (ASM-029);
  - all estimates unvalidated.
- If any assumption fails, scope is cut along the cut line, never stretched.

### 6. Verification against Phase 2.2 evidence (`phase3_1_evidence.csv`, `src/phase3_1_evidence.py`)
| New rule | Applied read-only to the snapshot | Phase 2.2 reference | Match |
|---|---|---|---|
| B1 invariants flag legacy offers | 4/5 Pending offers flagged; 4 offers flagged in total | DQ-06, OAM-03c | ✓ |
| Revisions in current data | 0/36 applications with more than one offer | R4-offers-per-app | ✓ |
| As-of pending rule | 0/31 decided offers dated after the cutoff | OAM-01 26/31 unchanged | ✓ |
| B2 default threshold | 50/105 | DQ-28 | ✓ |
| B2 opening review flags | 15/24 | DQ-11 | ✓ |
| B3 duplicate warning | 6 groups (12 records); 0 name-only or phone-only extras | DQ-02, R2-name-only | ✓ |
| B3 referral classification (hires) | 7/26 label with no referrer; 3/26 endorsements | M-A9n, M-A9r | ✓ |

## 2. Files changed
**New:**
- `src/offer_lifecycle.py`
- `src/duplicate_warning.py`
- `src/phase3_1_evidence.py`
- `outputs/phase3_1_evidence.csv`
- `tests/test_phase3_1.py` (37 tests)
- this file

**Updated:**
- `src/offer_metrics.py`: as-of pending, reliability tiers, privacy column, revision counters.
- `src/phase3_plan.py`: B3.3 split, estimate labels, first-cut flags, SM-B1-G3, SM-B2-5, SM-B3-G2 and SM-B3-G3, trace T-15 to T-18.
- `src/phase3_checks.py`: new checks listed below.
- `outputs/offer_acceptance_metric_spec.md`
- `outputs/phase3_product_strategy.md`
- `outputs/q3_roadmap.md`
- `outputs/customer_validation_plan.md`
- `outputs/phase3_review.md`
- Regenerated CSVs.
- `audit/decision_log.md`: DEC-032 to DEC-037; DEC-030 superseded; DEC-029 amended.
- `audit/assumptions_register.md`: ASM-025 and ASM-026 revised; ASM-027 to ASM-030 added.
- `audit/investigation_log.md`: INV-011.
- `README.md`

**One existing assertion changed:** in `tests/test_phase3.py`, the display label `"suppressed"` became `"counts only"`, reflecting the reliability-tier wording. The test's logic is otherwise unchanged. No tests were removed.

**New checker rules:**
- the spec must contain the lifecycle transition table generated from the model, verbatim;
- every allocation row must be labelled as a planning estimate;
- the first cut must be the 0.5 engineer-week B3 duplicate warning;
- the evidence must reproduce DQ-02, DQ-11, DQ-28 and OAM-03c;
- any mention of "merge" must carry a no-merge qualifier. This caught two ambiguous lines in the validation plan, which are now fixed.

## 3. Quality control
| Check | Result |
|---|---|
| Full test suite | **All 103 pass**: 48 Phase 1–2, 11 Phase 2.2, 7 Phase 3, 37 Phase 3.1 |
| Phase 3 checker (`src.phase3_checks`) | PASS |
| DuckDB verification | All 54 checkpoints match |
| Phase 2.1 independent checks | Re-run, unchanged |
| Phase 2 outputs (audit, summary, findings, metrics, issues, traceability, verification) | Byte-identical to pre-Phase-3 copies |
| Raw data | SHA-256 identical; files read-only |
| Airtable calls, commits, pushes | None |

## 4. Unresolved decisions (need PM approval or external input)
1. **Approve DEC-032 to DEC-037**, plus the earlier Phase 3 proposals DEC-025 to DEC-029 and DEC-031, DEC-022 (cohort rules) and DEC-011 (hire definition).
2. **Renege treatment:** OAM-01 keeps a reneged offer as accepted, because it measures the decision, and counts it in OAM-13. The alternative is to treat it as a decline. This is a product judgement.
3. **Privacy threshold of 5** for aggregate-only viewers (ASM-028): needs TalentFlow privacy/legal and Acme confirmation.
4. **Role mapping:** which Acme roles map to recruiter, hiring manager and recruiting-ops lead for each transition (C-02 follow-up).
5. **Per-stage inactivity defaults:** keep 90 days for every stage until the live baseline and Pilot 1, or set stage-specific defaults.
6. **Engineering validation** of all estimates and the 8 delivery assumptions (ASM-022, ASM-026, ASM-027). Cut line order 1 is the duplicate warning.
7. **Conditional scope**, which stays out of the 6.0: auto-expiry (C-03), auto-close (C-11, C-06), source back-fill (C-04), and a recruiter-initiated merge tool (C-07; automatic merging is never in scope).

Phase 4 has not been started.
