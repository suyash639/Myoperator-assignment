# Decision and Assumption Register

**Authority:** `audit/decision_log.md` and `audit/assumptions_register.md`. The tables below are **generated from those logs** by `src/final_package.py`. A decision appears as approved **only** if the log records PM approval.

**Current position:**
- **DEC-038 is approved.**
- **DEC-025 to DEC-037 remain proposals** until the PM approves them.
- Unresolved dependencies are in §4.

## 1. Approved decisions (PM-approved or implemented PM instruction)
<!-- GEN:dec_approved -->
| ID | Decision | Approval recorded in log | Status in log | Readiness (log §G) |
|---|---|---|---|---|
| DEC-001 | Populate `.gitignore` before `git init`; exclude credentials, `.venv`, `data/raw`, `data/processed`, `logs`, `outputs/private`, raw session transcripts (`transcripts/raw/`, `*.jsonl`). | PM-approved (Phase 0 message) | Active |  |
| DEC-002 | Local git only; no remote, no push. | PM-approved | Active |  |
| DEC-003 | uv-managed env, Python 3.11 pinned, exact dependency pins in `pyproject.toml` + `uv.lock`; `requirements.txt` exported. | PM-approved | Active |  |
| DEC-004 | DuckDB SQL (`queries/*.sql`) as independent verification of headline metrics. *Wording corrected in Phase 2.2: the primary implementation is plain Python, not pandas (pandas is pinned but unused).* | PM-approved | Active (scope extended by DEC-023) |  |
| DEC-005 | Airtable client GET-only, enforced in code; credentials only from environment; tokens never logged. | PM-approved | Active |  |
| DEC-007 | Metric definitions written before metrics are computed. | PM-approved | Active |  |
| DEC-008 | No engineering estimates invented; effort figures are provisional assumptions requiring engineering validation. | PM-approved | Active |  |
| DEC-009 | Use the original assignment token (fingerprint recorded locally only) for the live extraction; no rotation. | PM-approved | Active |  |
| DEC-012 | data/raw/*.json made read-only (chmod a-w); loader verifies SHA-256 on every load. | PM instruction (implemented): "treat data/raw as immutable" | Active |  |
| DEC-013 | Personal/free-text fields never written to outputs/*.csv|md; test enforces it. | PM instruction (implemented): "keep customer-level data local" | Active |  |
| DEC-016 | **Offer acceptance.** Provisional primary metric = **decided-offer acceptance, offer-level**: Accepted / (Accepted + Declined) = 26/31 = 83.9% (M-B1). Keep 26/36 = 72.2% as the **all-issued-offer ratio** (M-B0). Offer-level and … | PM-approved (Phase 2.2) | Active (provisional). **Supersedes DEC-014** |  |
| DEC-017 | **Channel attribution.** Primary reported attribution = `Candidates.Source`, labelled **"Source as recorded"**. Alternatives (referrer override M-A2, strict referral M-A9, distinct candidates M-A1/M-A3, duplicates merged … | PM-approved (Phase 2.2) | Active |  |
| DEC-018 | **Uncertainty.** Wilson intervals removed from main reporting (no valid sampling interpretation justified). Report observed rates, definition sensitivity (variant rows) and single-record sensitivity (`single_record_pp`). | PM-approved (Phase 2.2) | Active |  |
| DEC-019 | **Dates.** Neither the Interviews/Offers tables nor the Application copied fields are universally authoritative. Both are retained; copy-vs-source **contradictions** (DQ-15) and **impossible chronology** (DQ-13) are flagged … | PM-approved (Phase 2.2) | Active. **Supersedes DEC-015** |  |
| DEC-020 | **Snapshot dates.** Extraction date = 2026-11-24. Apparent bulk-import timestamp = 2026-08-27 16:39–16:40 UTC. Neither is claimed as the business reporting cutoff. 2026-08-27 is used as a **provisional cutoff** for ages, with … | PM-approved (Phase 2.2) | Active. **Supersedes DEC-010** |  |
| DEC-021 | **Funnel.** Keep the full-snapshot funnel. Add a completed-cohort funnel for applications 2025-07-01..2026-03-31 only after verifying sufficiency; document eligibility and exclusion rules. | PM-approved (Phase 2.2) | Active. Sufficiency verified; rules in DEC-022 |  |
| DEC-023 | Approve factual corrections supported by independent evidence; do not approve unsupported interpretations automatically. Classification of Phase 2.1 corrections P1–P13 in phase2_2_correction_report (archived process report; … | PM-approved (Phase 2.2) | Active |  |
| DEC-038 | **Renege treatment.** The primary acceptance metric (OAM-01) measures whether an offer was accepted **at the decision event**. A later candidate withdrawal (renege) or company rescission does not erase that acceptance. … | **PM-approved** (Phase 3.2 instruction) | Active |  |
<!-- /GEN:dec_approved -->

## 2. Proposed decisions (awaiting PM approval), with readiness
The "Readiness" column is taken from the log's readiness table (§G):
- **Approve now:** the PM can decide without outside input.
- **Acme:** needs a customer answer.
- **Engineering:** needs engineering validation.

<!-- GEN:dec_proposed -->
| ID | Decision | Approval recorded in log | Status in log | Readiness (log §G) |
|---|---|---|---|---|
| DEC-011 | Hire = Application Stage 'Hired' (identical to the Accepted-offer set, 26/26). Hire date = Offers.Decision On. | Analyst proposal, pending PM ratification in D3 | Proposed | Approve now: Provisionally; Acme: C-15; Engineering: — |
| DEC-022 | Completed-cohort rules. **Eligible** = Applied On 2025-07-01..2026-03-31 AND (Status Closed OR Active with no recorded activity for >90 days before the provisional cutoff, i.e. stalled, kept at furthest evidence stage). … | Analyst proposal, needs PM ratification | Proposed | Approve now: **Yes**; Acme: —; Engineering: — |
| DEC-025 | **Claim A (D1):** the 26.9% figure is accepted as Source-as-recorded hire share. Job-board integration is **deferred pending validation** (not Q3). Build B3 to measure intake method and friction; decide at Q4 planning. | Proposal, awaiting PM approval | Proposed | Approve now: **Yes**; Acme: C-12 only for the Q4 revisit, not for approval; Engineering: — |
| DEC-026 | **Claim B (D1):** "build differently". Fix the offer lifecycle and reporting (B1); do not build acceptance-improvement tooling. | Proposal, awaiting PM approval | Proposed | Approve now: **Yes**; Acme: —; Engineering: — |
| DEC-027 | **Q3 builds (D2):** B1 offer lifecycle integrity (2.5), B2 pipeline hygiene (2.0), B3 attribution integrity (1.5) = **6.0 engineer-weeks** of PM planning estimates; committed scope is flags, queues and validation only; cut line … | Proposal, awaiting PM approval; estimates need engineering validation (DEC-008) | Proposed | Approve now: Scope yes; **allocation needs validation**; Acme: —; Engineering: Estimate validation (ASM-022) |
| DEC-028 | **Non-builds (D2):** N1 job-board integration (defer, Q4 decision), N2 offer-acceptance improvement tooling, N3 referral programme features; each with reconsideration criteria. X1 and X2 go to the backlog. | Proposal, awaiting PM approval | Proposed | Approve now: **Yes**; Acme: —; Engineering: — |
| DEC-029 | **D3 metric spec:** OAM-01 Decided Offer Acceptance Rate (offer-level; Status authoritative; Pending excluded and flagged; latest offer per application; prior-hire offers included and flagged; period by Decision On); supporting … | Proposal, awaiting PM ratification | Proposed; amended by DEC-033 | Approve now: **Yes, provisionally** (core definition); Acme: C-08 (prior-hire default), C-15 (hire meaning), C-03 (expiry) refine it; Engineering: — |
| DEC-031 | **Prioritisation framework:** 7 criteria with written anchors and weights (value 0.20, evidence 0.20, impact 0.15, time to value 0.10, effort 0.15, delivery risk 0.10, dependency risk 0.10), with equal-weight and no-effort … | Proposal, awaiting PM approval | Proposed | Approve now: **Yes**; Acme: —; Engineering: — |
| DEC-032 | **B1 offer lifecycle model** (`src/offer_lifecycle.py`): 7 statuses; 8 allowed transitions, each with permitted roles, the business date it records and whether a reason is required; Accepted is terminal except renege (Withdrawn) … | Proposal, awaiting PM approval | Proposed. Phase 3.2: roles are proposals; the Acme role mapping is an unresolved customer dependency (C-17, ASM-031) | Approve now: Model yes; **permissions no**; Acme: C-17 (role mapping); Engineering: Event-log and schema feasibility |
| DEC-033 | **D3 consistency amendments:** status is evaluated **as of** the as-of date (an offer decided after as-of counts as Pending at as-of); a reneged or rescinded-after-acceptance offer keeps its Accepted decision in OAM-01 and is … | Proposal, awaiting PM approval | Proposed | Approve now: **Yes** (consistent with DEC-038); Acme: —; Engineering: — |
| DEC-034 | **Display rules, two separate rules.** *Reliability:* n < 10 shows counts only; 10 ≤ n < 30 shows the rate with a low-sample label giving the one-record swing; n ≥ 30 shows the rate. *Privacy:* breakdown cells (department, level, … | Proposal, awaiting PM approval; privacy threshold needs privacy/legal confirmation | Proposed. Phase 3.2: k is a configurable parameter (default 5); a proposed policy requiring Acme privacy/legal approval (C-18), not a regulatory requirement | Approve now: Reliability tiers **yes**; privacy k **no**; Acme: C-18 (privacy/legal); Engineering: — |
| DEC-035 | **B2 inactivity rules:** threshold configurable per stage at org level (default 90 days, range 14–365, changes audited); the flag is labelled "Inactive > N days" and is never called abandoned; "abandoned" exists only as a … | Proposal, awaiting PM approval | Proposed. Phase 3.2: 90 days is the provisional default for every stage; per-stage configuration implemented in `src/inactivity.py` | Approve now: **Yes** (default stays provisional); Acme: C-11 informs later defaults; Pilot 1; Engineering: — |
| DEC-036 | **B3 source intelligence:** acquisition source (a controlled taxonomy chosen by the recruiter, with detail for Job Board, Agency and Other) is separate from intake method (system-derived from the creation path, never chosen); … | Proposal, awaiting PM approval | Proposed | Approve now: Rules yes; **intake-method derivation needs confirmation**; Acme: C-04 for the legacy back-fill only; Engineering: Creation-path availability (ASM-029) |
| DEC-037 | **Delivery model:** 6.0 engineer-weeks delivered as 2 engineers × 3 one-week sprints under the stated assumptions (ASM-026, ASM-027); all figures are PM planning estimates until engineering validates them; if the assumptions … | Proposal, awaiting engineering validation | Proposed | Approve now: **No**; Acme: —; Engineering: Engineering manager (ASM-026, ASM-027) |
<!-- /GEN:dec_proposed -->

**Summary of readiness:**

| Can be approved now | Awaiting Acme input | Awaiting engineering validation |
|---|---|---|
| DEC-025, DEC-026, DEC-028, DEC-031, DEC-033, DEC-035, DEC-022; DEC-029 (core, provisional); DEC-034 (reliability tiers only) | DEC-032 role mapping (C-17); DEC-034 privacy policy (C-18); DEC-029 refinements (C-03, C-08, C-15); DEC-011 hire definition (C-15) | DEC-027 allocation; DEC-037 delivery model; DEC-032 event-log and schema feasibility; DEC-036 intake-method derivation (ASM-029) |

## 3. Superseded and process decisions (history preserved)
<!-- GEN:dec_superseded -->
| ID | Decision | Approval recorded in log | Status in log | Readiness (log §G) |
|---|---|---|---|---|
| DEC-010 | Analysis as-of date = 2026-08-27 (bulk-import createdTime; latest Applied On). | Analyst proposal | **Superseded by DEC-020** |  |
| DEC-014 | Offer acceptance primary definition = Accepted / (Accepted + Declined); scenarios reported alongside. | Analyst proposal | **Superseded by DEC-016** (PM adopted it provisionally, with labelling rules) |  |
| DEC-015 | Durations use only source-of-truth tables (Interviews, Offers); records with impossible dates excluded and counted. | Analyst proposal | **Superseded by DEC-019** |  |
| DEC-030 | **Small-sample display rule:** a rate is displayed only when its denominator is at least 10; otherwise counts are shown (ASM-025). | Proposal, awaiting PM approval | **Superseded by DEC-034** (Phase 3.1) |  |
<!-- /GEN:dec_superseded -->

<!-- GEN:dec_process -->
| ID | Decision | Approval recorded in log | Status in log | Readiness (log §G) |
|---|---|---|---|---|
| DEC-006 | Local git pre-commit hook blocks commits containing `.env`, raw/processed data, or Airtable PAT-shaped strings. | Analyst process | Active — local hook, not versioned |  |
| DEC-024 | Free-text numbers in reports are checked by test: every "x/y" fraction in the Phase 2 markdown reports must appear as a numerator/denominator in a generated CSV; traceability references are validated against the outputs and logs. | Analyst process | Active |  |
<!-- /GEN:dec_process -->

## 4. Unresolved dependencies at a glance
| Dependency | Owner | Blocks | See |
|---|---|---|---|
| Acme role and permission mapping for offer transitions | Acme recruiting ops / People | B1 pilot release (DEC-032) | C-17, ASM-031 |
| Privacy suppression policy (proposed k = 5) | Acme privacy/legal | Breakdowns for aggregate-only viewers (DEC-034) | C-18, ASM-028 |
| Hire definition: accepted offer or start | VP of People | DEC-011, D3 | C-15, ASM-020 |
| True state of the 5 Pending offers; expiry policy | Acme recruiting ops | B1 backlog; auto-expiry (conditional) | C-02, C-03 |
| Engineering validation of estimates and the delivery model | Engineering lead and manager | DEC-027, DEC-037 | ASM-022, ASM-026, ASM-027 |
| Creation path available for intake method | Engineering lead | DEC-036 | ASM-029 |
| Business reporting cutoff | Whoever loaded the base | Baseline interpretation | C-01, ASM-006 |

## 5. Analytical and delivery assumptions (status as recorded)
<!-- GEN:asm -->
| ID | Assumption | Type | Owner to validate | Status |
|---|---|---|---|---|
| ASM-001 | Capacity is 6 engineer-weeks for Q3. | Constraint (given) | PM | Given |
| ASM-002 | Airtable token has read access to all 8 tables. | Technical | Phase 1 extraction | **Confirmed** (INV-004): all 8 tables returned HTTP 200 |
| ASM-003 | Token may lack `schema.bases:read`; schema may need inferring from records. | Technical | Phase 1 | **Confirmed** (INV-004): schema endpoint 403; field types inferred from records |
| ASM-004 | Configured token (fingerprint recorded locally only) is the newly rotated read-only token; the previously exposed token is revoked. | Security | PM | **Resolved by PM decision** (DEC-009): original assignment token used; not rotated. Scopes not returned by whoami. |
| ASM-005 | Records are listed without a `view` parameter, so view filters cannot hide records. Airtable omits empty fields, so a missing key means empty. | Technical | Phase 2 | **Confirmed** (INV-005) |
| ASM-006 | The provisional cutoff 2026-08-27 (apparent bulk-import date) approximates the source system's business reporting cutoff. | Analytical | Acme (C-01) | **Open** — reworded in Phase 2.2 (DEC-020); sensitivity at 2026-08-30 and 2026-11-24 reported |
| ASM-007 | Pending offers older than 30 days are effectively expired (scenario M-B3). | Analytical | Acme offer-expiry policy (C-03) | Open |
| ASM-008 | Same normalised name + phone = same person (DQ-02, M-A8, M-A10). | Analytical | Acme (C-07) | Open |
| ASM-009 | Final Interview On reflects real rounds absent from the Interviews table (DQ-16). | Analytical | Acme / eng (C-05) | Open |
| ASM-010 | The base contains only Acme Corp data (no tenant field exists). | Scope | TalentFlow (C-14) | Open (see REJ-003 note) |
| ASM-011 | Referrer override is asymmetric: a Referred By link reassigns an application to Referral, but a Referral label without a link stays Referral. | Analytical | Acme (C-04) | Open — strict alternative M-A9 reported |
| ASM-012 | Candidate Created On represents first touch. | Analytical | Acme (C-07) | Open — alternative M-A10 (earliest Applied On) reported |
| ASM-013 | A candidate's Source applies to every one of their applications. | Analytical | Acme (C-04) | Open |
| ASM-014 | Records are independent samples of a stable process. | Statistical | — | **Not relied upon** (DEC-018: no sampling intervals reported) |
| ASM-015 | Interviews/Offers tables are more reliable than Application copied date fields. | Analytical | Acme / eng (C-05) | **Rejected** as a general rule (DEC-019, REJ-010); both sources reported |
| ASM-016 | CTC values are INR, annual. | Analytical | Acme (C-09) | Open |
| ASM-017 | Application Status Active means in flight; Closed means outcome-complete. | Analytical | Acme (C-11) | Open — partially contradicted; cohort uses an explicit stall rule (ASM-021) |
| ASM-018 | An application's department is its opening's department. | Analytical | — | Open (structural; every application links exactly one opening) |
| ASM-019 | The 2025-05..2026-08 history represents Q3 hiring behaviour. | Analytical | PM | Open |
| ASM-020 | An Accepted offer is a hire (no start confirmation exists). | Analytical | VP of People (C-15) | Open |
| ASM-021 | An Active application with no recorded activity for >90 days before the cutoff is stalled, not in flight. | Analytical | PM / Acme (C-11) | Open — new in Phase 2.2 |
| ASM-022 | Effort figures in Phase 3 (B1 2.5, B2 2.0, B3 1.5 engineer-weeks, and their components) are PM planning estimates sufficient for the committed scope. | Delivery | Engineering lead, before sprint 1 | Open (DEC-008); cut line defined if exceeded |
| ASM-023 | The Airtable base mirrors TalentFlow's data model and recruiter workflow closely enough that defects observed in the fields correspond to product capability gaps. | Product | Engineering / PM | Open |
| ASM-024 | Recruiters will act on queues and flags when they are surfaced (adoption). | Product | Pilot 1, SM-B1-2, SM-B2-1 | Open |
| ASM-025 | *(Revised Phase 3.1)* Reliability tiers for displaying a rate: n < 10 counts only; 10 ≤ n < 30 low-sample label; n ≥ 30 normal. | Analytical | PM | Open (originally a single n ≥ 10 threshold) |
| ASM-026 | *(Expanded Phase 3.1)* Capacity is 2 engineers × 3 one-week sprints; both can work backend and frontend; QA is done by the same engineers; one-week sprints are workable for this team. | Delivery | Engineering manager | Open |
| ASM-027 | An "engineer-week" means a full productive week: both engineers are dedicated (no support rotation or other project), and code review, sprint ceremonies, deployment and test-data setup fit inside the … | Delivery | Engineering manager | Open; if any fails, apply the cut line |
| ASM-028 | *(Revised Phase 3.2)* A configurable small-cell suppression threshold, proposed default k = 5, is an acceptable **proposed policy** for viewers without record-level offer access. It is **not** a … | Privacy | Acme privacy/legal (C-18); TalentFlow privacy | Open: requires Acme privacy/legal approval |
| ASM-029 | TalentFlow knows each record's creation path (UI, import, API, career form, agency portal, referral form), so intake method can be system-derived. | Technical | Engineering lead | Open |
| ASM-030 | Recruiters can enter accurate business dates for offer events (decision, withdrawal, rescission, expiry); recorded_at protects the audit trail but not the accuracy of the business date. | Data | Acme recruiting ops; SM-B1-G1 audit | Open |
| ASM-031 | The proposed TalentFlow roles (recruiter, hiring manager, recruiting-ops lead, system) can be mapped onto Acme's real roles and approval chain for offer transitions. No Acme permission is assumed. | Product | Acme recruiting ops / People team (C-17) | Open: unresolved customer dependency |
<!-- /GEN:asm -->

## 6. Unresolved customer questions
All 18 questions (C-01 to C-18) are open. Priorities and what each answer would change are in `Customer_Validation_Plan.md`.
