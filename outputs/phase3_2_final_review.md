# Phase 3.2: Final Clarifications Before Phase 4

**Unchanged:** the roadmap, the three builds, the three non-builds, the 6.0 engineer-week allocation (B1 2.5, B2 2.0, B3 1.5), and all Phase 2.2 outputs.

## 1. Clarifications made

| # | Instruction | What changed | Evidence / test |
|---|---|---|---|
| 1 | **Renege treatment** | **DEC-038 (PM-approved):** OAM-01 counts acceptance **at the decision event**; a later renege or rescission does not erase it. New separate metrics: **OAM-13a** post-acceptance reneging and **OAM-13b** post-acceptance rescission, plus OAM-06x for offers resolved *without* a decision. The reference implementation now computes everything from **event-time state at the as-of date** (`event_state`, `event_metrics` in `src/offer_metrics.py`) and never reads the latest status. Legacy records are converted to events first; a Pending offer carrying a Decision On gets no decision event | Every existing OAM value is unchanged (26/31, 26/36, 24/28 at candidate level). On legacy data OAM-13a, OAM-13b and OAM-06x are "not currently measurable". Tests: accept → renege, accept → company rescission, as-of before and between events, withdrawal or rescission before a decision, superseded revision, corrected decision date |
| 2 | **Privacy** | The threshold is a **configurable parameter** (`privacy_k`, default 5) and is labelled a **proposed policy requiring Acme privacy/legal approval**. The spec states it is **not** presented as a regulatory requirement. New customer dependency C-18; ASM-028 reworded | Tests: k changes results; the wording is present in the spec |
| 3 | **Permissions** | recruiter, hiring manager and recruiting-ops lead are kept as **proposed TalentFlow roles**. Acme's real mapping is an **unresolved customer dependency** (C-17, ASM-031, P1, must be set before pilot release). No Acme permission is assumed; the permission table is configuration | Test: proposal wording, C-17 and ASM-031 present |
| 4 | **Inactivity** | 90 days is the **provisional default for every stage**; the threshold is **configurable per application stage** (14–365 days). Flags never say "abandoned"; abandonment needs a recruiter disposition with a reason. Pilot 1 (20 applications) and its stop condition are retained | `src/inactivity.py`. The per-stage default reproduces DQ-28 (50/105, E-B2-cfg); overriding only Applied to 60 days gives 54/105. Tests cover overrides, range limits, the disposition rules and the pilot text |
| 5 | **Decision status** | DEC-025 to DEC-037 **remain Proposed**. A readiness table is added (`decision_log.md` §G). No Phase 3 assumption (ASM-021 to ASM-031) is marked confirmed | Tests parse the log and register to enforce both |

## 2. Decision readiness

| Can be approved now (PM judgement only) | Needs Acme input | Needs engineering input |
|---|---|---|
| DEC-025 defer job-board integration | DEC-032 permissions (C-17) | DEC-027 allocation (estimate validation, ASM-022) |
| DEC-026 Claim B: build differently | DEC-034 privacy k (C-18) | DEC-037 delivery model (ASM-026, ASM-027) |
| DEC-028 non-builds | DEC-029 refinements (C-03, C-08, C-15) | DEC-032 event log and schema feasibility |
| DEC-031 scoring framework | DEC-011 hire definition (C-15) | DEC-036 intake-method derivation (ASM-029) |
| DEC-033 event-time consistency | | |
| DEC-034 reliability tiers (not privacy) | | |
| DEC-035 inactivity rules (provisional default) | | |
| DEC-022 cohort rules; DEC-029 core definition (provisional) | | |

Already PM-approved: DEC-016 to DEC-021, DEC-023 and DEC-038.

## 3. Quality control

| Check | Result |
|---|---|
| Full test suite | **All 120 pass**: 103 earlier tests, no assertion changed, plus 17 new |
| Phase 3 checker | PASS (this file included) |
| DuckDB verification | All 54 checkpoints match |
| Phase 2.2 outputs | Byte-identical to pre-Phase-3 copies |
| Raw data | SHA-256 identical; files read-only |
| Airtable calls, commits, pushes | None |

## 4. Files
**New:**
- `src/inactivity.py`
- `tests/test_phase3_2.py`
- this file

**Updated:**
- `src/offer_metrics.py` (event-time engine; OAM-06x and OAM-13a/b; configurable `privacy_k`)
- `src/phase3_1_evidence.py`
- `outputs/offer_acceptance_metric_spec.md`
- `outputs/customer_validation_plan.md` (C-17, C-18)
- `outputs/open_questions_for_customer.md` (C-17 and C-18 appended; earlier entries unchanged)
- `outputs/phase3_product_strategy.md`
- `outputs/q3_roadmap.md`
- the logs and the README

Phase 4 has not been started.
