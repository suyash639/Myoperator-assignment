# Customer Validation Plan: Acme Corp

**What the dataset demonstrates vs what Acme must confirm.**
- The data shows record-level contradictions and rates; the findings are in `Findings_and_Data_Audit.csv`.
- It cannot show intent, policy, permissions or what happens outside TalentFlow. Those need Acme.
- **No committed Q3 scope waits on these answers.** They gate the pilot release, conditional scope, metric labels and the Q4 job-board decision.

**Source:** `../open_questions_for_customer.md` (C-01 to C-18, with full evidence).

## Priority 1: blocks implementation or pilot release

**Decision owner** is the stakeholder already named in `../open_questions_for_customer.md` ("Who to ask"). **Required milestone** is the point in `Q3_Product_Roadmap.md` §6 or the documented dependency by which the answer is needed. No new stakeholders are introduced.

| ID | Question to ask Acme | Why it matters | Decision affected | Decision owner | Required milestone | Evidence available now | Answer that would change the plan |
|---|---|---|---|---|---|---|---|
| C-17 | Which Acme roles map to the proposed roles (recruiter, hiring manager, recruiting-ops lead)? Who may record acceptances and declines, rescind an offer, and correct a record? | B1 permissions must match Acme's real approval chain; none has been assumed | DEC-032, B1.1 configuration, pilot release | Acme recruiting ops and the People team | Before pilot release (end of sprint 3); the mapping must be set before the pilot (roadmap sprint 1 criterion; DEC-032) | The data has job titles (Recruiter, Interviewer, Hiring Manager), not permissions (ASM-031) | A different approval chain (e.g. rescission needs HR) changes the permission configuration, not the build |
| C-18 | Does Acme privacy/legal approve hiding breakdown cells below k = 5 for aggregate-only viewers, a different k, or no suppression? | Proposed policy only; **not** a known regulatory requirement | DEC-034, D3 §3.14, leadership dashboard | Acme privacy/legal, plus TalentFlow privacy | Before breakdowns are shown to aggregate-only viewers (pilot release, end of sprint 3) | Breakdowns like "3 of 3 accepted" can reveal individual decisions (OAM-07 counts) | A different k changes one parameter. "No dashboard breakdowns" removes OAM-07 and OAM-08 from aggregate views |
| C-15 | Is a "hire" an accepted offer or a confirmed start? | Defines hire counts and how a renege is read | DEC-011, D3, Claim A denominator | VP of People | VP review at end of sprint 3 (D3 adoption) | Stage = Hired matches Accepted offers 26/26; no start status exists | "Start" adds a start-confirmation event to B1 (conditional scope) and changes the hire definition |
| C-02 | What is the true outcome of the 5 Pending offers, 4 of which carry a decision date? | Resolves the gap between 26/36 and 26/31; validates the B1 diagnosis | B1 backlog resolution (SM-B1-2), Pilot 2 | Acme recruiting ops | Pilot day 0–30 (SM-B1-2 backlog resolution window) | 4/5 decided-looking dates, 11–16 days after the offer (FND-09) | If most were "date wrong" rather than "status wrong", the B1 constraint is still right but the queue copy changes |
| C-03 | Does Acme have an offer-expiry policy? | Default Expires On; threshold for stale-offer metrics | B1 conditional auto-expiry, SM-B1-4 | Acme People team | Before auto-expiry is enabled (conditional scope); SM-B1-4 threshold at the first month-end after release | No expiry field; the 30-day threshold is an assumption (ASM-007) | A policy enables auto-expiry (swapped in only by de-scoping equal effort) |
| C-12 | What does "job-board integration" mean, and is there measurable friction (manual entry time, delay, lost applicants)? | The only evidence that could justify N1 | DEC-025, DEC-028, Q4 N1 decision | VP of People, Acme recruiting ops, TalentFlow engineering | Q4 planning (N1 decision) | Friction is unmeasured; Job Board yield is lowest (FND-03) | Evidence of material manual effort or loss moves N1 into Q4 scope |
| C-13 | How did the VP compute 26.9% and 72%? Is there an acceptance target? | Confirms like-for-like; enables a target | D1 verdicts; D3 target line; N2 criteria | VP of People | VP review at end of sprint 3 (target line for OAM-01) | Both figures reproduce under specific definitions (FND-01, FND-07) | A target allows a success criterion for OAM-01; a different VP definition changes the D1 wording, not the builds |
| C-04 | Which field is authoritative for channel: Source or Referred By? Is Source first touch or per application? | Primary attribution label; back-fill | DEC-017, B3 conditional back-fill | Acme recruiting ops | Before any source back-fill (conditional scope); attribution label at the end-of-sprint-3 VP review | 34/350 conflicts; 7/7 Referral hires unlinked (FND-05) | "Referred By is authoritative" makes the referrer-override view primary and enables back-fill |
| C-11 | How are application and requisition statuses maintained? Are inactive applications tracked elsewhere? | Whether B2 fixes hygiene or exposes a sync gap | B2 scope, Pilot 1 stop condition, conditional auto-close | Acme recruiting ops | End of sprint 2 (recruiter usability review and Pilot 1) | 50/105 inactive > 90 days; 55/105 on Filled openings (FND-14) | "Tracked elsewhere" cuts the B2 queue to opening flags (Pilot 1 rule) |

**Internal (engineering, not Acme) items that also block commitment:**
- E-1: validate the planning estimates (ASM-022).
- E-2: confirm the delivery-model assumptions (ASM-026, ASM-027).
- E-3: confirm event-log and schema feasibility and that the creation path is available (DEC-032, ASM-029).

## Priority 2: changes metric labels or later scope

| ID | Question | Why it matters | Decision affected | Evidence | Answer that would change the plan |
|---|---|---|---|---|---|
| C-06 | What does Applications.Closed On mean? | Close dispositions must write the right fields | B2.2 behaviour; DEC-011 | Closed before the decision in 17/26 hires and 4/5 declines (FND-11) | A defined meaning changes what B2 writes on close |
| C-08 | Are offers to already-hired candidates internal moves? | Whether OAM-01b becomes the default | DEC-029 §3.7 | 4/36 offers; 3/31 decided (FND-10) | "Internal moves" makes the exclusion the default |
| C-05 | Should Interviews hold every round? Where do First and Final Interview On come from? | Sizes the interview-tooling backlog (X1); date source | X1; DEC-019 | 44/50 Final Interview On after every recorded interview (FND-16) | "All rounds expected" makes DQ-16 a confirmed defect and raises X1 for Q4 |
| C-14 | Is the base Acme-only? | Scope of every baseline | Labelling of baselines | No tenant field (ASM-010) | Multi-tenant data would require re-running all baselines per tenant |
| C-16 | Is this production data or a prepared sample? | Whether frequencies generalise | Targets beyond Acme | Bulk import; anomalies cluster in low IDs (FND-21) | "Sample" means baselines must come from live data before any target |
| C-10 | Why has Engineering made no hires from 30 applications? | Context; possible missing data | None in Q3 | 0/30 hired; 3/30 interviewed (FND-18) | Missing data would add a data-completeness item |

## Priority 3: hygiene and context

| ID | Question | Why it matters | Decision affected | Evidence | Answer that would change the plan |
|---|---|---|---|---|---|
| C-07 | Are the 6 name+phone pairs, and the double hire, real duplicates? | Whether to build a recruiter-initiated merge tool (never automatic) | B3 conditional | 12/300 candidates in pairs (FND-17) | "Yes, duplicates" raises the merge tool for Q4 |
| C-09 | Are CTC values INR annual, and are candidates linked to the right openings? | Any future compensation analysis | N2 criteria | No units defect found; 23/36 offers far from expectation (FND-19) | "Wrong links" adds a data-integrity item |
| C-01 | What date was the data exported? | Interpreting ages and stale counts | Baselines | Import 2026-08-27; extraction 2026-11-24 (FND-21) | It changes stale-offer and inactivity baselines, which live data replaces anyway |

## Sequence
| When | Questions | Format | Owner |
|---|---|---|---|
| Week 0 | C-17, C-18, C-15, C-02, C-03, C-12, C-13, C-04, C-11; engineering E-1 to E-3 | A 45-minute session with the Acme recruiting-ops lead and VP of People; written follow-up to privacy/legal; engineering planning | PM |
| Sprint 2 | C-11 in practice (Pilot 1), C-06 | Recruiter usability review | PM + design |
| Sprint 3 | C-08, C-05, C-14, C-16, C-10 | Written follow-up | PM |
| Q4 planning | C-07, C-09, C-01, plus the C-12 evidence | Planning review | PM |
