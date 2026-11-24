# Customer Validation Plan (Phase 3)

**Source:** `open_questions_for_customer.md` (C-01 to C-16; full evidence there).

**Principle:** no committed Q3 scope depends on an unanswered question. Answers change *conditional* scope, metric labels, or the Q4 job-board decision. Each question is classified by what it blocks:

| Code | Blocks |
|---|---|
| **S** | Product scope |
| **M** | Metric correctness |
| **D** | Data-model decisions |
| **R** | Release readiness |

## 1. Validation table

| ID | Question | Why it matters | Decision affected | Blocks | Priority | Can work proceed without an answer? |
|---|---|---|---|---|---|---|
| C-12 | What does "job-board integration" mean, and is there measurable friction (manual entry time, latency, lost applicants)? | The only evidence that could justify N1 | N1 (Q4 decision), DEC-025, DEC-028 | S | **P1** | **Yes.** N1 is already deferred; B3 collects intake data meanwhile |
| C-13 | How did the VP compute 26.9% and 72%? Is there an acceptance target or benchmark? | Confirms we are testing the same metric; without a target, "needs improvement" can't be evaluated | D1 verdicts, D3 dashboard target line, N2 reconsideration | M | **P1** | **Yes.** D3 ships with no target line (spec §7) |
| C-02 | True outcome of the 5 Pending offers, 4 with decision dates | Resolves OAM-01 in the range 72.2%–86.1%; validates B1's diagnosis | B1 backlog resolution (SM-B1-2), Pilot 2 | M, R | **P1** | **Yes.** The B1 build doesn't need it; the backlog is resolved by recruiters through the B1 queue |
| C-03 | Offer-expiry policy (does a default expiry exist?) | Sets the default Expires On and the SM-B1-4 threshold | B1 conditional scope (auto-expire), SM-B1-4 | S, M | P2 | **Yes.** Expires On is optional and blank by default; auto-expire is conditional |
| C-04 | Which channel field is authoritative? Is Source first touch or per application? | Decides back-fill of historical Source and the primary attribution label | B3 conditional back-fill, DEC-017 | D, M | **P1** | **Yes.** B3 captures application-level Source going forward; history stays "Source as recorded" |
| C-11 | How are application and requisition statuses maintained? Are stalled applications tracked elsewhere? | Determines whether B2 solves hygiene or reveals a sync gap; gates auto-close | B2 scope (Pilot 1 stop condition), conditional auto-close | S, R | **P1** | **Partly.** Sprint 1 rules proceed; the sprint 2 usability review and Pilot 1 answer it in practice before release |
| C-06 | What does Applications.Closed On mean? (It precedes decisions in 21/31 decided offers) | The B2 close disposition must write the right fields | B2.2 behaviour, DEC-011 hire date | D, R | P2 | **Yes.** Disposition writes Status and a reason, and leaves Closed On semantics unchanged |
| C-08 | Are offers to already-hired candidates internal moves? | Whether OAM-01b becomes the default | D3 §3.7 | M | P2 | **Yes.** Included and flagged by default |
| C-15 | Is a "hire" an accepted offer or a start? | Hire definition in D3 and the Claim A denominator | DEC-011, D3 | M | P2 | **Yes.** D3 measures offer decisions, not starts |
| C-07 | Are the 6 name+phone pairs the same people? Is the CAND-00035 double hire real? | Whether to build a recruiter-initiated merge tool (never automatic merging); duplicate-warning tuning | B3 conditional scope, SM-B3-4 | D | P3 | **Yes.** The warning doesn't merge; recruiters decide |
| C-05 | Should Interviews hold every round? Where do First and Final Interview On come from? | Sizes X1 (interview tooling); decides the date source | X1 backlog, DEC-019 | S | P3 for Q3 (P1 for Q4 X1) | **Yes.** No Q3 build uses interview data |
| C-01 | Export or business cutoff date | Ages in OAM-04, SM-B1-4, SM-B2-2 | Baseline interpretation | M | P3 | **Yes.** Live baselines replace snapshot ones at release |
| C-10 | Why does Engineering have 0 hires from 30 applications? | Context; possible missing data | None in Q3 | — | P3 | **Yes** |
| C-09 | INR annual CTC? Correct candidate–opening links? | Only for compensation analysis (N2) | N2 reconsideration | — | P3 | **Yes** |
| C-14 | Is the base Acme-only? | Scope of every baseline | Release readiness of baselines | R | P2 | **Yes**, with baselines labelled "this base" |
| C-17 | Which Acme roles map to the proposed TalentFlow roles (recruiter, hiring manager, recruiting-ops lead), and who may perform each offer transition, especially rescind and correct? | Permissions in B1 must reflect Acme's real approval chain; we have not assumed it | B1.1 permission configuration, DEC-032 | D, R | **P1** | **Partly.** B1.1 builds role-checked transitions as configuration; the Acme mapping must be set before pilot release |
| C-18 | Does Acme privacy/legal approve suppressing breakdown cells below k = 5 for aggregate-only viewers, a different k, or none? | The privacy rule is a proposed policy, not a confirmed or regulatory requirement | D3 §3.14, DEC-034, leadership dashboard release | M, R | P2 | **Yes.** k is a parameter; the leadership dashboard is not released to aggregate-only viewers until approved |
| C-16 | Is this production data or a prepared sample? | Whether frequencies generalise | Targets and generalisation beyond Acme | M | P2 | **Yes.** Live-data baselines in sprint 3 supersede the snapshot |

## 2. What can be built now, and what waits

| Safe to build now (committed) | Needs confirmation first (conditional or backlog) |
|---|---|
| Offer status model, transitions and constraint; conflict flags (B1.1) | Auto-expiry of offers (C-03) |
| Pending-offer queue and D3 metrics (B1.2, B1.3) | OAM-01b as the default definition (C-08) |
| Configurable inactivity flags and opening review flags (never auto-corrected); disposition queue (B2.1, B2.2) | Auto-close of inactivity-flagged applications (C-11, C-06) |
| Application-level acquisition source (controlled taxonomy), system-derived intake method, referral attribution rules, warning-only duplicate check (B3.1–B3.3b) | Back-fill of historical source (C-04); a recruiter-initiated merge tool, never automatic (C-07) |
| Attribution report (B3.4) | Job-board connectors (C-12 plus B3 data; Q4 decision) |
| | Interview-capture tooling (C-05) |

## 3. Sequence

| When | Questions | Channel | Owner |
|---|---|---|---|
| Week 0 | P1: C-12, C-13, C-02, C-04, C-11 | 45-minute session with the Acme recruiting-ops lead and the VP of People | PM |
| Sprint 2 | C-11 in practice: Pilot 1 sample review; C-06 | Recruiter usability review | PM + design |
| Sprint 3 | C-03, C-08, C-15, C-14, C-16 | Written follow-up | PM |
| Q4 planning | C-05, C-07, C-09, C-10, and the C-12 evidence | Planning review | PM |
