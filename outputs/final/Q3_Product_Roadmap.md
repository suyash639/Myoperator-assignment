# TalentFlow Q3 Product Roadmap: Acme Corp

**Capacity:** 6.0 engineer-weeks.

**Estimate status:** every effort figure is a **PM planning estimate, not an engineering-validated commitment** (DEC-008, ASM-022).

**Decision status:** the builds and non-builds are **proposals** (DEC-025 to DEC-037) awaiting PM approval. DEC-038, acceptance at the decision event, is approved.

**Evidence:** finding IDs (FND-*) refer to `Findings_and_Data_Audit.csv`; metric IDs (OAM-*, SM-*) to `Metrics_Specification.md`.

## 1. Summary

| | Initiative | Decision | Effort (engineer-weeks) |
|---|---|---|---:|
| **B1** | Offer lifecycle management and reliable offer metrics | Build | 2.5 |
| **B2** | Application inactivity and opening-status visibility | Build | 2.0 |
| **B3** | Acquisition-source and intake tracking with duplicate warnings | Build | 1.5 |
| | **Total** | | **6.0** |
| **N1** | Job-board integration | Deferred to Q4 | 0 |
| **N2** | Candidate offer-acceptance improvement tools | Deferred | 0 |
| **N3** | Referral-programme features | Deferred | 0 |

**Why these three.** Each fixes a defect that stops Acme, and us, from answering the VP's two questions correctly:
- B1: offer status (FND-09);
- B2: pipeline status (FND-14, FND-15);
- B3: channel attribution (FND-05).

All three are the top three under every weighting tested (§5). None depends on an unanswered customer question for its committed scope.

**Priority ranking vs delivery sequence.** These answer different questions, and the plan uses both.

| | What it decides | Order | Source |
|---|---|---|---|
| **Priority ranking** | Which initiatives are funded | B1 (4.20), **B3 (3.80)**, B2 (3.55). B3 outranks B2 because its defect is confirmed (DQ-01) while B2's main signal is a suspicious pattern (DQ-28) | `../phase3_prioritisation_scores.csv`; Phase 3 strategy §6 |
| **Delivery sequence** | When work happens | All three builds run **in parallel in every sprint**, layered as rules → workflows → metrics/QA (§4). The B1/B2/B3 order in this document is ID order only; no build waits for another | Phase 3 roadmap §1–3 |
| **Cut order** | What goes first if estimates exceed 6.0 | **B3's duplicate warning first**, even though B3 outranks B2. The cut is made *within* B3, on its weakest-evidence component: DQ-02 is a suspicious pattern, with experience values implausible for one person in 4/6 pairs. B3's confirmed-defect rule (B3.1) is never cut. The PM instructed this in Phase 3.1 | Phase 3 strategy §6; DEC-036 |

So the ranking does not imply B2 is delivered before B3, and the cut order does not contradict the ranking.

## 2. The three builds

### B1. Offer lifecycle management and reliable offer metrics (2.5 engineer-weeks)
| | |
|---|---|
| **User problem** | Recruiters and leadership can't tell which offers are open. Offers stay "Pending" after a decision, or after a withdrawal, because no status exists for that. The reported acceptance figure counts unresolved offers as failures |
| **Evidence** | 4/5 Pending offers carry a decision date, and 3/5 are older than 30 days at the provisional cutoff (FND-09). Statuses are only Accepted, Declined and Pending. The all-issued ratio is 26/36 and decided-offer acceptance 26/31 (FND-06, FND-07). 3/31 decided offers went to already-hired candidates (FND-10) |
| **Proposed solution** | Offer statuses add Expired, Withdrawn, Rescinded and Superseded. There are 8 allowed transitions, each with *proposed* roles and a named business date. Invariants make a Pending offer with a decision date unsavable. Every change is an append-only audit event; corrections are by the recruiting-ops lead only. Plus a pending-offer queue and the D3 metrics, computed at event time |
| **In scope** | Status model and invariants; event log; audited correction; flags on legacy conflicts (no rewrite); pending-offer queue; metric tiles OAM-01 to OAM-13b with reliability tiers |
| **Excluded** | Auto-expiry (conditional on C-03); any change to legacy records except through audited correction; any tool aimed at raising acceptance (N2) |
| **User value** | One place to resolve open offers. Leadership sees acceptance at the decision event, the all-issued ratio and the pending backlog side by side. A renege no longer erases an acceptance (DEC-038) |
| **Success metrics** | See below |
| **Dependencies and risks** | Acme role mapping (C-17) before pilot. Event-log and schema feasibility (engineering). Risk: recruiters clearing the queue with wrong statuses, guarded by SM-B1-G1 |
| **Validation** | Pilot 2: record the true outcomes of the conflicting Pending offers, then count how many were wrong in status vs wrong in date |

<!-- GEN:sm_B1 -->
| ID | Type | Metric | Baseline | Target or decision rule | Status |
|---|---|---|---|---|---|
| SM-B1-1 | data_quality | New offers saved with a status/decision-date contradiction | 4/5 Pending offers carry a Decision On (snapshot) | 0 after release | Firm (enforced by B1.1 constraint) |
| SM-B1-2 | adoption | Share of pre-existing Pending offers resolved (true status + date) within 30 days of pilot start | 5 Pending, of which 4 conflicting (snapshot); live count recorded at release | Decision rule: >= 80% resolved in 30 days -> queue works; below -> interview recruiters on blockers | Provisional decision rule |
| SM-B1-3 | outcome | Reported acceptance figure in VP review uses OAM-01 with counts, OAM-02 labelled as ratio, and pending backlog | VP currently quotes ~72% (all-issued ratio) as 'acceptance' | Yes/No at the end-of-Q3 VP review | Firm (binary) |
| SM-B1-4 | outcome | Pending offers older than 30 days with no Expires On and no update in 30 days, at month end | 3/5 Pending older than 30 days at provisional cutoff 2026-08-27 (5/5 at 2026-11-24) | 0 at each month end after the backlog is resolved | Provisional (threshold depends on expiry policy C-03) |
| SM-B1-G1 | guardrail | Status accuracy: share of queue resolutions confirmed correct in a monthly 10-offer audit sample | No baseline (new workflow) | Threshold: < 90% confirmed -> pause bulk resolution, review reasons | Provisional guardrail |
| SM-B1-G3 | guardrail | Offer status changes without an audit event | Not measurable today (no event log exists) | 0 | Firm (enforced: status changes only via the event log) |
| SM-B1-G2 | guardrail | Accepted offers whose application is not Hired (consistency) | 0/26 (snapshot) | Remains 0 | Firm |
<!-- /GEN:sm_B1 -->

### B2. Application inactivity and opening-status visibility (2.0 engineer-weeks)
| | |
|---|---|
| **User problem** | Active pipelines contain applications nobody is working, and openings whose status contradicts their hires. Pipeline and workload counts are overstated |
| **Evidence** | 50/105 Active applications show no recorded activity for more than 90 days; 55/105 are on Filled openings (FND-14). 15/24 openings contradict their applications (FND-15). The share is threshold-sensitive: 93/105 at 30 days, 29/105 at 180 |
| **Proposed solution** | An inactivity flag with a threshold **configurable per application stage** (provisional default 90 days; range 14–365). Opening-status **review** flags. A recruiter queue with dispositions |
| **In scope** | Inactivity detector; opening-status rules (Filled or Cancelled with Active applications; Open with hires ≥ headcount; Cancelled with hires); review queue; reversible closes; live baseline |
| **Excluded** | Automatic closing (conditional on C-11 and C-06). **Any automatic change to an application or opening status.** Treating a flag as abandonment: "abandoned" is only a recruiter-confirmed disposition |
| **User value** | An honest active pipeline and opening list, without silent data changes |
| **Success metrics** | See below |
| **Dependencies and risks** | Live baseline (the snapshot is old). Applications may be tracked outside TalentFlow (C-11). Alert fatigue. Wrongful closes, guarded by SM-B2-G1 |
| **Validation** | **Pilot 1** (sprint 2): 2 Acme recruiters classify 20 randomly sampled inactivity-flagged applications. **Stop condition:** if fewer than 50% are confirmed abandoned, the queue is cut to opening flags only (SM-B2-5) |

<!-- GEN:sm_B2 -->
| ID | Type | Metric | Baseline | Target or decision rule | Status |
|---|---|---|---|---|---|
| SM-B2-1 | adoption | Share of inactivity-flagged applications dispositioned within 30 days of being flagged | No baseline (feature does not exist) | Decision rule: >= 50% in pilot -> continue; < 50% -> review UX and threshold with recruiters | Provisional decision rule |
| SM-B2-2 | outcome | Inactivity-flag share of Active applications (no recorded activity > configured threshold, default 90 days; a flag, not confirmed abandonment) | 50/105 Active (snapshot, provisional cutoff); 104/105 at extraction date | No numerical target until live baseline; proposed intent: halve the live baseline within one quarter of pilot | Not set (pending live baseline) |
| SM-B2-3 | data_quality | Openings whose Status contradicts their applications and are not flagged | 15/24 openings contradictory (snapshot) | 0 unflagged after release; decision rule: >= 50% of flags resolved within 14 days | Firm (flags) / Provisional (resolution rule) |
| SM-B2-4 | outcome | Active applications on Filled openings | 55/105 Active applications (snapshot) | No numerical target until live baseline | Not set (pending live baseline) |
| SM-B2-5 | outcome | Share of reviewed inactivity flags that the recruiter confirms as abandoned (pilot: 20 sampled applications) | No baseline: inactivity flags are not abandonment (50/105 flagged at 90 days is a flag rate) | Decision rule: < 50% confirmed abandoned in the 20-application pilot -> cut the queue to opening flags only | Provisional decision rule |
| SM-B2-G1 | guardrail | Closed-by-disposition applications reopened within 30 days | No baseline (new workflow) | Threshold: > 5% -> raise stall threshold / review reasons | Provisional guardrail |
<!-- /GEN:sm_B2 -->

### B3. Acquisition-source and intake tracking with duplicate warnings (1.5 engineer-weeks)
| | |
|---|---|
| **User problem** | Channel decisions, including the job-board request, rest on a Source field that contradicts the referral link and is stored once per person. Nobody can say what job-board intake costs recruiters |
| **Evidence** | 34/350 Source/referrer conflicts; 7/7 Referral-labelled hires have no referrer (FND-05). 12/300 candidates are in name+phone pairs (FND-17) |
| **Proposed solution** | (1) An **acquisition source** per application from a controlled taxonomy. (2) An **intake method** derived by the system from the creation path. (3) Referral rules: a direct referral needs a referrer; a referrer on another source is an endorsement. (4) A **warning-only duplicate check** (name AND phone). (5) An attribution report |
| **In scope** | Taxonomy and validation; system-derived intake method; duplicate warning with the outcomes same person, different person (reason; remembered) or unsure (ops review); report |
| **Excluded** | **Automatic merging, and any merge or delete path.** Back-fill of historical source (conditional on C-04). A recruiter-initiated merge tool (conditional on C-07) |
| **User value** | Trustworthy channel data from release onwards, and the first intake evidence for the Q4 job-board decision |
| **Success metrics** | See below |
| **Dependencies and risks** | Engineering must confirm the creation path is known (ASM-029). Intake friction (SM-B3-G1). False-positive warnings (SM-B3-4) |
| **Validation** | Pilot 3: one quarter of intake-method data plus the C-12 interview feed the N1 decision. **The duplicate warning is the first scope cut** if B3 exceeds 1.5 |

<!-- GEN:sm_B3 -->
| ID | Type | Metric | Baseline | Target or decision rule | Status |
|---|---|---|---|---|---|
| SM-B3-1 | data_quality | New applications with Source/Referred By contradiction | 34/350 applications (9.7%, snapshot) | 0 for applications created after release | Firm (enforced by B3.1 validation) |
| SM-B3-2 | adoption | New applications with application-level Source and Intake Method captured | 0/350 (field does not exist) | 100% of UI-created applications (mandatory fields); imports tracked separately | Firm for UI path; imports provisional |
| SM-B3-3 | outcome | Intake-method mix for Job Board applications (share entered manually) | Not measurable today (no intake data, C-12) | No target: measurement input to the N1 decision at Q4 planning | Not set (measurement) |
| SM-B3-4 | outcome | Duplicate-warning precision: share of warnings the recruiter resolves as 'same person' (attach to existing record; no merge) | No baseline; snapshot has 12/300 candidates in name+phone pairs | Decision rule: < 50% over first 50 warnings -> tighten match rule | Provisional decision rule |
| SM-B3-G2 | guardrail | Duplicate warnings re-shown for a pair already marked 'different person' | Not measurable today (no warning exists) | 0 | Firm (enforced by remembered pair decisions) |
| SM-B3-G3 | guardrail | Candidate records merged or deleted by the duplicate feature | Not applicable today | 0 | Firm (enforced: feature has no merge or delete path) |
| SM-B3-G1 | guardrail | Median time to create an application | No baseline: instrument 2 weeks before release | Threshold: > 20% increase vs pre-release baseline -> simplify form | Provisional guardrail |
<!-- /GEN:sm_B3 -->

## 3. The three non-builds

| | Why stakeholders want it | Why not in Q3 | Evidence that would justify revisiting |
|---|---|---|---|
| **N1 Job-board integration (deferred to Q4)** | Largest source of applications and hires (FND-01, FND-02) | It targets volume, which is not shown to be the constraint. Job boards have the lowest yield under every attribution (FND-03). Friction is unmeasured and cost is unestimated; realistically it would consume most of the 6 engineer-weeks (an assumption) | B3 intake data or the C-12 interview shows material manual-entry time or applicant loss; **or** engineering estimates a single-board connector at ≤ 2 engineer-weeks with low maintenance; **or** resolved attribution changes the yield ranking. **Decided at Q4 planning** |
| **N2 Candidate offer-acceptance improvement tools (deferred)** | "Acceptance needs improvement"; Counter Offer is the most common recorded decline reason (3 of 5) | The 72% largely reflects counting pending offers. There are only 5 declines, the pay data can't be interpreted (FND-19), and there is no benchmark (C-13) | B1 live for a quarter; at least 30 decided offers in a period; an agreed target that the decided rate falls below; decline reasons pointing to a fixable cause |
| **N3 Referral-programme features (deferred)** | As labelled, Referral looks outstanding | 7/7 Referral-labelled hires have no referrer link; 4 belong to 2 candidates (FND-05, FND-17) | After B3, a quarter of validated referral links showing a materially higher yield on enough hires to survive one-record swings |

## 4. Delivery plan

Sprints are one week each, 2.0 engineer-weeks per sprint:

| Sprint | Focus | Components |
|---|---|---|
| 1 | Foundations | B1.1, B2.1, B3.1 |
| 2 | Workflows | B1.2, B2.2, B3.2, B3.3a, B3.3b |
| 3 | Metrics, QA, pilot | B1.3, B1.4, B2.3, B2.4, B3.4, B3.5 |

<!-- GEN:allocation -->
| Component | Build | Sprint | Discipline | Engineer-weeks | First cut | What |
|---|---|---|---|---|---|---|
| B1.1 | B1 | 1 | Backend | 1.00 |  | Offer lifecycle per src/offer_lifecycle.py: statuses Expired, Withdrawn, Rescinded, Superseded; role-checked transitions; field invariants (no resolution date on Pending, decision_on only for decided/reneged offers); append-only event log (business_date + recorded_at); audited correction; legacy conflicts flagged, never rewritten |
| B2.1 | B2 | 1 | Backend | 0.75 |  | Inactivity detector with org-level, per-stage configurable threshold (default 90 days, range 14-365, changes audited) and opening-status review flags (Filled/Cancelled with Active applications; Open with hires >= headcount; Cancelled with hires). Flags only: the system never changes an application or opening status |
| B3.1 | B3 | 1 | Backend | 0.25 |  | Application-level acquisition source (controlled taxonomy, src/duplicate_warning.py), system-derived intake method, referral attribution rules (direct referral vs endorsement) |
| B1.2 | B1 | 2 | Frontend | 0.50 |  | Pending-offer queue: age buckets, conflict badge, resolve via allowed transitions only (reason where required) |
| B2.2 | B2 | 2 | Frontend | 0.75 |  | Inactivity review queue (flag labelled 'Inactive > N days', never 'abandoned'); dispositions: still active (snooze with reason), close - recruiter-confirmed abandoned, close - other reason, advance; reversible 30 days; opening review banner with resolve/dismiss-with-reason |
| B3.2 | B3 | 2 | Backend | 0.25 | yes | Duplicate warning service (name AND phone match; remembered 'different person' pairs; ops review queue). WARNING ONLY. First cut |
| B3.3a | B3 | 2 | Frontend | 0.25 |  | Intake form: source picker from taxonomy, source detail, referrer picker, endorsement confirmation |
| B3.3b | B3 | 2 | Frontend | 0.25 | yes | Duplicate warning dialog: same person (attach to existing record) / different person (reason) / unsure. No merge. First cut |
| B1.3 | B1 | 3 | Data/analytics | 0.50 |  | D3 metrics (OAM-01..OAM-13b) computed at event time, with reliability tiers and the proposed privacy policy; dashboard tiles; reconciliation |
| B1.4 | B1 | 3 | QA | 0.50 |  | Transition, role, invariant and audit-log tests; legacy flag check (expect 4 conflicts on snapshot); metric reconciliation |
| B2.3 | B2 | 3 | Data/analytics | 0.25 |  | Live baseline capture (inactivity at 60/90/120 days) and hygiene scorecard |
| B2.4 | B2 | 3 | QA | 0.25 |  | Threshold configuration, flag-not-correct and reversible-close tests |
| B3.4 | B3 | 3 | Data/analytics | 0.25 |  | Attribution report: source as recorded, direct referrals vs endorsements, intake-method mix, conflict count |
| B3.5 | B3 | 3 | QA | 0.25 |  | Taxonomy/referral validation and duplicate-warning tests (no-merge guarantee, remembered pairs) |

**Total: 6.0 engineer-weeks.** Every row is labelled *PM planning estimate (not validated by engineering)*.
<!-- /GEN:allocation -->

**Delivery assumptions.** All of these must hold (ASM-026, ASM-027, ASM-029, DEC-037):
- two engineers, dedicated for 3 weeks;
- both work backend and frontend; QA by the same engineers;
- code review, ceremonies and deployment fit inside the estimates;
- CI/CD, staging and test data already exist;
- no platform-team dependency for migrations;
- design sketches ready by sprint 2 (PM/design time, not engineering capacity);
- the system knows each record's creation path.

**Rule if the assumptions fail: reduce scope, never silently extend the 6.0.** Cut in this order:

| Order | Cut | Saves |
|---|---|---|
| 1 | Duplicate warning (B3.2 + B3.3b) | 0.5 |
| 2 | B2 bulk actions | about 0.25 |
| 3 | B1 dashboard tiles; table export only | about 0.25 |

The rules that stop new bad data (B1.1, B2.1, B3.1) are never cut.

**Conditional scope** (outside the 6.0; enters only by swapping out equal effort, with PM approval):
- auto-expiry (C-03);
- auto-close (C-11, C-06);
- source back-fill (C-04);
- a recruiter-initiated merge tool (C-07).

## 5. Prioritisation (unchanged from Phase 3)
Seven criteria, each with written anchors, scored 1–5:

| Criterion | Weight |
|---|---:|
| User value | 0.20 |
| Evidence strength | 0.20 |
| Business impact | 0.15 |
| Time to value | 0.10 |
| Effort | 0.15 |
| Delivery risk | 0.10 |
| Dependency risk | 0.10 |

The top three are the same under weighted, equal-weight and no-effort scoring. Full scores: `../phase3_prioritisation_scores.csv`.

The table keeps the **Phase 3 working names**. They map to the final names as follows:

| ID | Final name |
|---|---|
| B1 | Offer lifecycle management and reliable offer metrics |
| B2 | Application inactivity and opening-status visibility |
| B3 | Acquisition-source and intake tracking with duplicate warnings |

Scope and effort are identical.

<!-- GEN:scores -->
| ID | Initiative | Decision | Weighted score (rank) | Equal-weight rank | Rank without effort |
|---|---|---|---|---|---|
| B1 | Offer lifecycle integrity and acceptance reporting | Build | 4.2 (1) | 1 | 1 |
| B3 | Source attribution integrity and intake instrumentation | Build | 3.8 (2) | 2 | 2 |
| B2 | Pipeline hygiene: inactivity flags and opening-status review | Build | 3.55 (3) | 3 | 3 |
| X2 | Department cycle-time analytics | Backlog (not prioritised) | 2.6 (4) | 4 | 5 |
| X1 | Interview scheduling and feedback-latency tooling | Backlog (not prioritised) | 2.55 (5) | 6 | 4 |
| N3 | Referral programme features | Non-build | 2.35 (6) | 5 | 6 |
| N2 | Offer-acceptance improvement tooling (comp intelligence, candidate nudges) | Non-build | 1.9 (7) | 7 | 7 |
| N1 | Job-board integration (new or deeper board connectors) | Non-build (defer pending validation) | 1.55 (8) | 8 | 8 |
<!-- /GEN:scores -->

## 6. Milestones
| When | Milestone | Measurable acceptance criterion | Decision |
|---|---|---|---|
| Week 0 | Engineering validates estimates; P1 questions sent to Acme | Every component in `../phase3_capacity_allocation.csv` has an engineering estimate, and the total is ≤ 6.0 after the cut line | Commit or cut |
| End of sprint 1 | Rules demo on a copy of the snapshot | On the snapshot: the B1 invariants flag exactly **4** legacy offers (E-B1-1 = OAM-03c); the inactivity rule flags **50/105** at the 90-day default (E-B2-90 = DQ-28); opening flags cover **15/24** openings (DQ-11). Saving a Pending offer with a decision date, or a Referral with no referrer, is rejected, which enforces the 0-new-contradiction targets SM-B1-1 and SM-B3-1 | Proceed to UI |
| End of sprint 2 | Recruiter usability review and Pilot 1 | 20 inactivity-flagged applications classified by recruiters. Keep the queue only if **≥ 50%** are confirmed abandoned (SM-B2-5). The duplicate warning fires on **6/6** DQ-02 groups and **0** name-only collisions (E-B3-dup-1, E-B3-dup-2) | Keep or cut the B2 queue |
| End of sprint 3 | Pilot release; VP review of the D3 metrics | On the snapshot the dashboard equals the reference implementation: OAM-01 **26/31**, OAM-02 **26/36**, OAM-09 **24/28**; live baselines recorded for SM-B2-2 and SM-B2-4; every success metric has a working data source | Adopt OAM-01 as the reported acceptance figure |
| Q4 planning | N1 decision using B3 intake data and C-12 | At least one quarter of intake-method data available (SM-B3-3) | Build, defer or drop |
