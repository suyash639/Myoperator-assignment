# Assumptions Register

Every assumption that a conclusion depends on. Nothing here is a fact until validated.
Engineering estimates are **provisional** and require engineering validation (DEC-008).
ASM-011..ASM-020 were proposed in Phase 2.1 as ASM-P11..ASM-P20 and registered in Phase 2.2 (each checked
against ASM-001..010 for duplication; none duplicates an existing entry). ASM-021 is new in Phase 2.2.

| ID | Assumption | Type | Depends on / blocks | Uncertainty | Owner to validate | Status |
|---|---|---|---|---|---|---|
| ASM-001 | Capacity is 6 engineer-weeks for Q3. | Constraint (given) | D2 | Low — stated by PM | PM | Given |
| ASM-002 | Airtable token has read access to all 8 tables. | Technical | Phase 1 | Medium | Phase 1 extraction | **Confirmed** (INV-004): all 8 tables returned HTTP 200 |
| ASM-003 | Token may lack `schema.bases:read`; schema may need inferring from records. | Technical | Phase 1 field-type audit | Medium | Phase 1 | **Confirmed** (INV-004): schema endpoint 403; field types inferred from records |
| ASM-004 | Configured token (fingerprint recorded locally only) is the newly rotated read-only token; the previously exposed token is revoked. | Security | Phase 1 live run | Cannot be verified locally | PM | **Resolved by PM decision** (DEC-009): original assignment token used; not rotated. Scopes not returned by whoami. |
| ASM-005 | Records are listed without a `view` parameter, so view filters cannot hide records. Airtable omits empty fields, so a missing key means empty. | Technical | Phase 2 completeness interpretation | Low | Phase 2 | **Confirmed** (INV-005) |
| ASM-006 | The provisional cutoff 2026-08-27 (apparent bulk-import date) approximates the source system's business reporting cutoff. | Analytical | Pending ages (M-B3, DQ-07), overdue reqs (DQ-12), stalled applications (DQ-28), cohort (M-K) | Medium: 3 Created On values are later (to 2026-08-30) | Acme (C-01) | **Open** — reworded in Phase 2.2 (DEC-020); sensitivity at 2026-08-30 and 2026-11-24 reported |
| ASM-007 | Pending offers older than 30 days are effectively expired (scenario M-B3). | Analytical | Claim B scenario | High: arbitrary threshold | Acme offer-expiry policy (C-03) | Open |
| ASM-008 | Same normalised name + phone = same person (DQ-02, M-A8, M-A10). | Analytical | Claim A variants | Medium: experience values implausible for one person in 4/6 pairs | Acme (C-07) | Open |
| ASM-009 | Final Interview On reflects real rounds absent from the Interviews table (DQ-16). | Analytical | Interview metrics | Medium | Acme / eng (C-05) | Open |
| ASM-010 | The base contains only Acme Corp data (no tenant field exists). | Scope | All | Medium | TalentFlow (C-14) | Open (see REJ-003 note) |
| ASM-011 | Referrer override is asymmetric: a Referred By link reassigns an application to Referral, but a Referral label without a link stays Referral. | Analytical | M-A2, M-A3, M-A7r-* | Medium | Acme (C-04) | Open — strict alternative M-A9 reported |
| ASM-012 | Candidate Created On represents first touch. | Analytical | M-A8, M-A7m-* | High: Created On is later than Applied On for 90/350 applications (DQ-14) | Acme (C-07) | Open — alternative M-A10 (earliest Applied On) reported |
| ASM-013 | A candidate's Source applies to every one of their applications. | Analytical | All channel metrics (M-A*, M-Q*) | Medium: Source is stored once per candidate; Applications has no Source field | Acme (C-04) | Open |
| ASM-014 | Records are independent samples of a stable process. | Statistical | Any sampling interval | High: 4 candidates hold 2 offers; 2 hold 2 hires | — | **Not relied upon** (DEC-018: no sampling intervals reported) |
| ASM-015 | Interviews/Offers tables are more reliable than Application copied date fields. | Analytical | Former DEC-015 | High | Acme / eng (C-05) | **Rejected** as a general rule (DEC-019, REJ-010); both sources reported |
| ASM-016 | CTC values are INR, annual. | Analytical | DQ-19, DQ-20, DQ-25, M-B7/M-B8 | Low-Medium: no currency field; 0/636 values below 100,000; all phones +91 | Acme (C-09) | Open |
| ASM-017 | Application Status Active means in flight; Closed means outcome-complete. | Analytical | M-FCc-*, M-K, framing of M-B1 | High: 50/105 Active are stalled >90 days (DQ-28) | Acme (C-11) | Open — partially contradicted; cohort uses an explicit stall rule (ASM-021) |
| ASM-018 | An application's department is its opening's department. | Analytical | M-T1-*, M-D1-*, M-DF-* | Low | — | Open (structural; every application links exactly one opening) |
| ASM-019 | The 2025-05..2026-08 history represents Q3 hiring behaviour. | Analytical | Any forward-looking use in D2/D5 | Medium-High: mixed maturity, 15 months | PM | Open |
| ASM-020 | An Accepted offer is a hire (no start confirmation exists). | Analytical | M-H0, Claim A denominator, DEC-011 | Medium: no Started status; 2 Accepted start dates after the import date | VP of People (C-15) | Open |
| ASM-021 | An Active application with no recorded activity for >90 days before the cutoff is stalled, not in flight. | Analytical | DQ-28, completed cohort (M-K, DEC-022) | Medium: threshold is analyst-chosen | PM / Acme (C-11) | Open — new in Phase 2.2 |
| ASM-022 | Effort figures in Phase 3 (B1 2.5, B2 2.0, B3 1.5 engineer-weeks, and their components) are PM planning estimates sufficient for the committed scope. | Delivery | DEC-027, q3_roadmap.md | High: not engineering estimates | Engineering lead, before sprint 1 | Open (DEC-008); cut line defined if exceeded |
| ASM-023 | The Airtable base mirrors TalentFlow's data model and recruiter workflow closely enough that defects observed in the fields correspond to product capability gaps. | Product | B1, B2, B3 | Medium | Engineering / PM | Open |
| ASM-024 | Recruiters will act on queues and flags when they are surfaced (adoption). | Product | B1, B2 success metrics | Medium | Pilot 1, SM-B1-2, SM-B2-1 | Open |
| ASM-025 | *(Revised Phase 3.1)* Reliability tiers for displaying a rate: n < 10 counts only; 10 ≤ n < 30 low-sample label; n ≥ 30 normal. | Analytical | DEC-034, D3 §3.12 | Medium: thresholds are a judgement based on the one-record swing | PM | Open (originally a single n ≥ 10 threshold) |
| ASM-026 | *(Expanded Phase 3.1)* Capacity is 2 engineers × 3 one-week sprints; both can work backend and frontend; QA is done by the same engineers; one-week sprints are workable for this team. | Delivery | q3_roadmap.md, DEC-037 | Medium | Engineering manager | Open |
| ASM-027 | An "engineer-week" means a full productive week: both engineers are dedicated (no support rotation or other project), and code review, sprint ceremonies, deployment and test-data setup fit inside the estimate; CI/CD and staging already exist; schema migrations need no separate platform-team work; design sketches are ready by sprint 2. | Delivery | DEC-037, every allocation figure | High | Engineering manager | Open; if any fails, apply the cut line |
| ASM-028 | *(Revised Phase 3.2)* A configurable small-cell suppression threshold, proposed default k = 5, is an acceptable **proposed policy** for viewers without record-level offer access. It is **not** a confirmed regulatory requirement. | Privacy | DEC-034, D3 §3.14 | Medium | Acme privacy/legal (C-18); TalentFlow privacy | Open: requires Acme privacy/legal approval |
| ASM-029 | TalentFlow knows each record's creation path (UI, import, API, career form, agency portal, referral form), so intake method can be system-derived. | Technical | B3, DEC-036 | Medium | Engineering lead | Open |
| ASM-030 | Recruiters can enter accurate business dates for offer events (decision, withdrawal, rescission, expiry); recorded_at protects the audit trail but not the accuracy of the business date. | Data | B1, OAM metrics | Medium | Acme recruiting ops; SM-B1-G1 audit | Open |
| ASM-031 | The proposed TalentFlow roles (recruiter, hiring manager, recruiting-ops lead, system) can be mapped onto Acme's real roles and approval chain for offer transitions. No Acme permission is assumed. | Product | DEC-032, B1.1 permission configuration | Medium | Acme recruiting ops / People team (C-17) | Open: unresolved customer dependency |
## Engineering estimates (PM planning placeholders, Phase 3 — none validated by engineering yet)

| Option | Estimate (eng-weeks) | Range | Dependencies | Source | Validated? |
|---|---|---|---|---|---|
| B1 Offer lifecycle integrity and acceptance reporting | 2.5 (PM planning placeholder) | not estimated | Schema change review | PM planning estimate (Phase 3) | **No** (ASM-022) |
| B2 Pipeline hygiene | 2.0 (PM planning placeholder) | not estimated | Live baseline | PM planning estimate (Phase 3) | **No** (ASM-022) |
| B3 Attribution integrity and intake instrumentation | 1.5 (PM planning placeholder) | not estimated | Intake form owners | PM planning estimate (Phase 3) | **No** (ASM-022) |
| N1 Job-board connector (any board) | **Not estimated** | — | Board APIs; C-12 | — | No |
