# Phase 3: Product Strategy and Q3 Prioritisation (D1, D2)

**Product:** TalentFlow (recruiting operations).

**Design partner:** Acme Corp.

**Capacity:** 6 engineer-weeks for Q3 (ASM-001).

**Evidence base:** the corrected Phase 2.2 outputs: `metric_calculations.csv` (M-*), `dq_issues.csv` (DQ-*) and `offer_metric_baseline.csv` (OAM-*, the D3 reference implementation).

**Status:**
- These are **PM recommendations awaiting your approval.** They are logged as DEC-025 to DEC-031 (*Proposed*), refined in Phase 3.1 by DEC-032 to DEC-037 (see `phase3_1_review.md`).
- **Effort figures are PM planning estimates, not engineering estimates** (DEC-008, ASM-022). Engineering must validate them before sprint 1 is committed.

> **Evidence discipline.** Every recommendation below states:
> - the observed evidence;
> - what that evidence does **not** prove;
> - the assumptions it relies on;
> - the customer validation needed;
> - why the build addresses the problem.
>
> All data describes **one customer's snapshot** (Acme, unconfirmed scope ASM-010, unconfirmed cutoff DEC-020). Patterns are not proven to be product-wide.

---

## 1. Decision summary

| | Initiative | Decision | Planning effort (engineer-weeks) |
|---|---|---|---:|
| **B1** | Offer lifecycle integrity and acceptance reporting | **Build** | 2.5 |
| **B2** | Pipeline hygiene: inactivity flags and opening-status review | **Build** | 2.0 |
| **B3** | Source attribution integrity and intake instrumentation | **Build** | 1.5 |
| | **Total committed** | | **6.0** |
| **N1** | Job-board integration (new or deeper board connectors) | **Do not build in Q3: defer pending validation** | 0 |
| **N2** | Offer-acceptance improvement tooling (comp intelligence, candidate nudges, counter-offer playbooks) | **Do not build** | 0 |
| **N3** | Referral programme features | **Do not build** | 0 |

**The theme for Q3:** *make the numbers leadership already uses trustworthy, and remove the operational debris that hides real pipeline state.*

None of the three builds assumes that a VP claim is true or false. Each one fixes a **confirmed or strongly evidenced data-capture defect** that currently prevents Acme, and us, from answering the VP's two questions correctly.

## 2. D1: decisions on the two VP claims

| VP claim | Evidence | PM verdict | Build decision | Rationale | Confidence |
|---|---|---|---|---|---|
| **A.** "Job boards contribute 26.9% of hires; prioritise job-board integration." | See the breakdown below | **The figure is correct; the priority does not follow from it.** Share of hires measures volume, not the return on integration | **Defer pending validation** (N1). Build the measurement instead: B3 captures application-level source and *intake method*, which gives the first friction evidence | Integrating a channel that already supplies 67.4% of applications at the lowest yield optimises volume, which the data does not show to be the constraint. The real gap is that channel data is unreliable and friction is unmeasured | **High** that share ≠ return on integration. **Medium** on attribution |
| **B.** "Offer acceptance is ~72% and needs improvement." | See the breakdown below | **72% is a definition artefact, and "needs improvement" is not demonstrated.** The measurable problem is offer-status integrity | **Build differently** (B1): an offer lifecycle model, a pending-offer resolution queue, and the D3 metric. **Do not build** acceptance-improvement tooling (N2) | You cannot manage a metric whose status data is wrong in 4 of 5 open records. Fixing the lifecycle makes the rate trustworthy and resolves the 5-offer gap between 72.2% and 83.9% | **Medium-high.** n = 31 decided offers |

**Evidence for claim A:**

| Dimension | Observed | Source |
|---|---|---|
| Application volume | 236/350 = 67.4% of applications | M-A5 |
| Hire contribution | 7/26 = 26.9%, Source as recorded. Range 23.1%–30.8% across definitions | M-A0, M-A2, M-A8, M-A9, M-A10 |
| Conversion efficiency | 7/236 = 3.0% per application; 2.7%–3.4% across every attribution; lowest of any channel with hires (next lowest 9.7%) | M-A7, M-A7s, M-A7m, M-A7f |
| Quality signal | Offer rate after interview 13/90 = 14.4%, the lowest | M-Q2-Job Board |
| Integration friction | **Not measured.** The base has no intake method, ingestion timestamp, import error, manual-entry time or lost-applicant data | C-12 |
| Engineering and maintenance cost | **Not estimated.** It depends on which boards and what "integration" means. Third-party connectors carry ongoing maintenance | C-12; engineering |
| Data reliability | Source contradicts Referred By on 34/350 applications | DQ-01 |

**Evidence for claim B:**

| Dimension | Observed | Source |
|---|---|---|
| All-issued-offer ratio | 26/36 = 72.2% (the VP's figure) | M-B0, OAM-02 |
| Decided-offer acceptance (offer-level, provisional primary) | 26/31 = 83.9% | M-B1, OAM-01 |
| Pending backlog | 5 Pending; ages 20, 23, 69, 117 and 222 days at the provisional cutoff | OAM-03, OAM-04, DQ-07 |
| Lifecycle and status quality | 4/5 Pending carry a Decision On. No Expired or Withdrawn state exists. 4/5 declined-offer applications were closed before the decision | DQ-06, DQ-07, DQ-26 |
| Candidate decline reasons | 5 declines: Counter Offer 3/5, Location 1, Compensation 1. These are recorded categories only | OAM-06-reason-* |
| Benchmark or target | None in the data | — |

**Claim A: what the evidence does not prove.**
- It does not show that integration would *fail* to help. It shows only that the case is unmade.
- If manual entry of board applicants is a large recruiter time sink, an integration could still be worthwhile. That is exactly what B3's intake-method capture and the C-12 interview will test.

**Claim B: what the evidence does not prove.**
- It does not show that acceptance is fine. 83.9% has no benchmark, and the Pending outcomes could pull it down to the all-issued 72.2% (OAM-02) or push it up to the 86.1% upper bound (M-B2).

## 3. D2: the three builds

All three are built for the recruiter or recruiting-ops lead as the primary user. Hiring managers and leadership consume their outputs.

### B1: Offer lifecycle integrity and acceptance reporting (2.5 engineer-weeks)

| Dimension | Detail |
|---|---|
| **User problem** | Recruiters and leadership cannot tell which offers are actually open. An offer stays "Pending" after a decision, or after the candidate withdraws, because there is no status for that. Leadership is quoted a 72% "acceptance rate" that counts unresolved offers as failures |
| **Evidence** | **Confirmed defect:** 4/5 Pending offers carry a Decision On (DQ-06). The status vocabulary has no terminal state other than Accepted or Declined; the 222-day offer belongs to an application marked "Withdrew" (DQ-07). Stage "Offer" covers both pending and declined (DQ-08). 3/31 decided offers went to already-hired candidates (M-B9, DQ-29) |
| **Proves** | Offer status data is internally inconsistent today, and the metric that leadership uses is definition-sensitive. Pending offers span 72.2%–86.1% |
| **Does not prove** | That recruiters *experience* this as pain (C-02), or that acceptance is low |
| **Assumptions** | ASM-023: the Airtable fields mirror TalentFlow's offer model. ASM-007: the 30-day expiry is only a default until C-03. ASM-022: effort |
| **Proposed solution** | Lifecycle model per `offer_acceptance_metric_spec.md` §8 (executable reference `src/offer_lifecycle.py`): (1) statuses **Expired**, **Withdrawn**, **Rescinded** and **Superseded**, with 8 allowed transitions, each restricted to named *proposed* roles (the Acme role mapping is unresolved, C-17) and recording a named business date; no return to Pending. (2) **Field invariants:** a Pending offer cannot carry any resolution date, and `decision_on` exists only on decided or reneged offers. (3) An optional **Expires On**. (4) An **append-only event log** (business_date + recorded_at, actor, role, reason); corrections only by the recruiting-ops lead, with before/after values. (5) Legacy conflicts **flagged, not auto-fixed**. (6) A **pending-offer queue**. (7) The **D3 metrics**, computed at event time (an acceptance stays counted after a later renege, which is measured separately by OAM-13a), with reliability tiers and the *proposed* privacy policy (pending Acme approval, C-18) |
| **User workflow** | The recruiter opens the pending-offer queue, sorted by age with a conflict badge, and picks the true outcome from the transitions allowed for their role. Accepted and Declined need a decision date; Declined, Withdrawn and Rescinded need a reason. Under the proposed roles, rescinding needs the hiring-manager or recruiting-ops-lead role; Acme's actual mapping is C-17. Creating a revised offer automatically supersedes the pending one. Leadership sees: "Decided offer acceptance 26/31 (83.9%) · 5 pending · 4 with status conflicts" |
| **Expected outcome** | Zero new status/date contradictions. The historical backlog is resolved. Leadership reports decided-offer acceptance next to the all-issued ratio, with the pending backlog visible. **It is not expected to change acceptance itself** |
| **Effort breakdown** | Backend 1.0 (B1.1) · Frontend 0.5 (B1.2) · Data/analytics 0.5 (B1.3) · QA 0.5 (B1.4) |
| **Dependencies** | C-02 (true state of the 5 Pending) for backlog resolution, not for the build. C-03 (expiry policy) for a default Expires On, which is otherwise left blank. C-08 (internal moves) for the OAM-01b variant label |
| **Risks** | Recruiters close offers with the wrong status to clear the queue (accuracy). Mitigation: a reason field for Withdrawn or Rescinded, plus a guardrail audit sample. The migration could misflag records; mitigated because records are flagged, never rewritten |
| **Success metrics** | SM-B1-1 to SM-B1-4 (§6 and `product_success_metrics.csv`) |
| **Confidence** | **High** on the problem (confirmed defect). Medium on adoption |

### B2: Pipeline hygiene: inactivity flags and opening-status review (2.0 engineer-weeks)

| Dimension | Detail |
|---|---|
| **User problem** | Recruiters' active pipelines are cluttered with applications that nobody is working, many on requisitions that are already filled. Pipeline counts, workload and "open requisitions" are overstated, and candidates may be left without a response |
| **Evidence** | 50/105 Active applications had no recorded activity for over 90 days at the provisional cutoff (DQ-28). 55/105 Active applications sit on Filled openings (DQ-28 detail). 15/24 openings have a status that contradicts their applications (DQ-11, confirmed defect). 10/11 Open openings are past Target Close (DQ-12) |
| **Proves** | Statuses in this snapshot do not track activity. The requisition contradictions are certain |
| **Does not prove** | That the applications are genuinely abandoned. Acme might track them elsewhere (C-11). The 90-day rule is an assumption (ASM-021). The share is **cutoff-sensitive**: 104/105 at the extraction date |
| **Assumptions** | ASM-021, ASM-023, ASM-024 (recruiters act on queues) |
| **Proposed solution** | (1) An **inactivity detector**. The threshold is **configurable per application stage** at org level (provisional default 90 days for every stage, range 14–365, changes audited; reference `src/inactivity.py`), based on the latest of applied, screened, interview, offer and decision dates. (2) The flag reads **"Inactive > N days"**, never "abandoned". (3) **Opening-status review flags**: Filled or Cancelled with Active applications; Open with hires ≥ headcount; Cancelled with hires. **The system never changes an application or opening status**; the recruiter resolves the flag or dismisses it with a reason. (4) A **recruiter review queue** with dispositions: still active (snooze with reason), close as recruiter-confirmed abandoned, close for another reason, or advance |
| **User workflow** | A weekly queue: "12 applications inactive > 90 days · 3 on filled openings". The recruiter reviews each and picks a disposition. **"Abandoned" is recorded only when the recruiter confirms it.** Bulk actions need a reason, and closes are reversible for 30 days. On the opening page a banner reads: "Marked Filled but 4 applications still Active: review". Resolving is a manual status change or a dismissal with a reason |
| **Expected outcome** | A lower inactivity-flag share; every opening contradiction reviewed; a truthful active-pipeline count. Scope is flags and review only; **auto-closing is conditional** (C-11). The 20-application pilot (§8, Pilot 1) decides whether flags reflect real abandonment |
| **Effort breakdown** | Backend 0.75 (B2.1) · Frontend 0.75 (B2.2) · Data/analytics 0.25 (B2.3) · QA 0.25 (B2.4) |
| **Dependencies** | A live-data baseline (the snapshot is old). C-11 (how statuses are maintained) for auto-closure, which is not committed. C-06 (Closed On meaning) for close semantics |
| **Risks** | Wrongful closure of genuinely live candidates (guardrail SM-B2-G1, reopen rate). Alert fatigue (adoption). Flags may not reflect abandonment: the share is threshold-sensitive (93/105 at 30 days, 50/105 at 90, 29/105 at 180; E-B2-*), and Pilot 1 is the stop condition (SM-B2-5). The live share may be lower than the snapshot |
| **Success metrics** | SM-B2-1 to SM-B2-4 |
| **Confidence** | **Medium.** The requisition contradictions are a confirmed defect; the inactivity-flag share is a suspicious pattern |

### B3: Source attribution integrity and intake instrumentation (1.5 engineer-weeks)

| Dimension | Detail |
|---|---|
| **User problem** | Leadership makes channel investment decisions, including this VP's job-board request, on a Source field that contradicts the referral link and is stored once per person rather than per application. Nobody can say whether job-board intake costs recruiters time |
| **Evidence** | **Confirmed defect:** Source contradicts Referred By on 34/350 applications (DQ-01). 7/7 Referral-labelled hires lack a referrer link (M-A9n). Applications has no Source field (ASM-013). 12/300 candidates are in probable duplicate pairs, and 2 pairs have different Sources (DQ-02). Integration friction is unmeasured (C-12) |
| **Proves** | Channel attribution is unreliable at the record level. Channel ROI cannot be computed today |
| **Does not prove** | Which field is right (C-04); that duplicates are the same people (C-07); that job-board intake is manual |
| **Assumptions** | ASM-013, ASM-008, ASM-023 |
| **Proposed solution** | Rules per `src/duplicate_warning.py`. (1) **Acquisition source** (how the candidate came to this application), chosen by the recruiter from a **controlled taxonomy**: Job Board (board name), LinkedIn, Career Site, Agency (agency name), Employee Referral, Campus, Other (describe). Legacy values map 1:1. (2) **Intake method** (how the record entered TalentFlow: manual entry, file import, integration/API, career-site form, agency submission, referral submission) is **system-derived from the creation path and never chosen by the recruiter** (ASM-029). (3) **Referral attribution:** an *Employee Referral* requires a referrer (direct referral); a referrer on any other source is allowed only as a confirmed *endorsement*, which is reported separately and never counted as a referral hire. (4) A **duplicate warning**: warning-only, name AND phone match, no merge (below). (5) An **attribution report** |
| **User workflow** | When adding an application the recruiter picks the source (and detail). Choosing Employee Referral reveals a required referrer. Adding a referrer to another source asks "Endorsement?". If name and phone match an existing candidate, a warning shows the match. **Same person** attaches the new application to the existing record (no records merged). **Different person** needs a reason, and the pair is remembered so the warning doesn't repeat. **Unsure** creates the record and queues the pair for recruiting-ops review. False positives (e.g. family members sharing a phone) are handled by the "different person" path and measured by SM-B3-4 |
| **Expected outcome** | Zero new Source/referrer conflicts. Application-level attribution exists for the first time. After one quarter we can see what share of job-board applications are entered manually, which is the first friction evidence for the N1 decision |
| **Effort breakdown** | Backend 0.5 (B3.1 0.25, B3.2 0.25) · Frontend 0.5 (B3.3a intake form 0.25, B3.3b duplicate dialog 0.25) · Data/analytics 0.25 (B3.4) · QA 0.25 (B3.5). **First cut if estimates exceed 1.5:** the duplicate warning, B3.2 + B3.3b = 0.5 |
| **Dependencies** | C-04 decides whether historical records are back-filled (conditional, not committed). C-07 decides whether to build merging (backlog) |
| **Risks** | Extra intake friction (guardrail SM-B3-G1); because intake method is system-derived, only the source is entered by hand. Duplicate-warning false positives, controlled by the strict match rule (name AND phone), remembered decisions (SM-B3-G2) and the precision decision rule (SM-B3-4). No merge path exists (SM-B3-G3) |
| **Success metrics** | SM-B3-1 to SM-B3-4 |
| **Confidence** | **High** on the defect. Medium on how much value the instrumentation yields |

### 3.4 Capacity allocation (planning estimates, must total 6.0)

| Build | Backend | Frontend | Data/analytics | QA | **Total** |
|---|---:|---:|---:|---:|---:|
| B1 | 1.00 | 0.50 | 0.50 | 0.50 | **2.5** |
| B2 | 0.75 | 0.75 | 0.25 | 0.25 | **2.0** |
| B3 | 0.50 | 0.50 | 0.25 | 0.25 | **1.5** |
| **Total** | 2.25 | 1.75 | 1.00 | 1.00 | **6.0** |

The component level is in `phase3_capacity_allocation.csv`, and the sprint view is in `q3_roadmap.md`.

**Not hidden in the 6.0:**
- **PM, design and customer-validation time** are not engineering capacity; they are listed as dependencies with owners.
- **There is no contingency buffer.** Instead there is an explicit **cut line** (`q3_roadmap.md` §4). If engineering validation finds the scope exceeds 6.0, scope is cut, not capacity added.
- **No integration** with external systems is required by any build.

## 4. Prioritisation method

**Criteria.** Each is scored 1–5, where 5 is most favourable. These are written anchors, not arbitrary scores:

| Criterion | Weight | 5 = | 3 = | 1 = |
|---|---:|---|---|---|
| User value | 0.20 | Problem affects most open records or the core weekly workflow | Affects a material minority | Asserted, not observed |
| Evidence strength | 0.20 | Confirmed defect, consistent across definitions | Suspicious pattern or single definition | No data, or n < 10 |
| Business impact | 0.15 | Directly changes a leadership decision or metric in use | Improves an operational metric | Speculative |
| Time to value | 0.10 | Value at release | Value after 1 quarter of new data | Value after more than 1 quarter, or unclear |
| Effort (planning estimate) | 0.15 | ≤ 1 engineer-week | 2–2.5 engineer-weeks | > 6 engineer-weeks or unestimated |
| Delivery risk | 0.10 | Internal, well-understood change | Moderate unknowns | Third-party APIs or new infrastructure |
| Dependency risk | 0.10 | No blocking customer answer | Answers affect scope, not the build | Build is blocked by an unanswered question |

**Why these weights.** Value and evidence carry 40%, because the brief is to solve a *verified* problem. Effort carries 15%, because capacity is the hard constraint. This is a judgement, so the ranking is checked under two alternatives.

**Results** (`phase3_prioritisation_scores.csv`, computed by `src/phase3_plan.py`):

| ID | Initiative | Value | Evidence | Impact | Time to value | Effort | Delivery | Dependency | Weighted (rank) | Equal-weight rank | Rank without effort |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Offer lifecycle | 4 | 5 | 5 | 4 | 3 | 4 | 4 | **4.20 (1)** | 1 | 1 |
| B3 | Attribution integrity | 3 | 5 | 4 | 3 | 4 | 4 | 3 | **3.80 (2)** | 2 | 2 |
| B2 | Pipeline hygiene | 4 | 3 | 4 | 4 | 3 | 4 | 3 | **3.55 (3)** | 3 | 3 |
| X2 | Department cycle-time analytics | 2 | 1 | 2 | 4 | 4 | 4 | 3 | 2.60 (4) | 4 | 5 |
| X1 | Interview scheduling and feedback tooling | 3 | 2 | 3 | 3 | 2 | 3 | 2 | 2.55 (5) | 6 | 4 |
| N3 | Referral programme features | 2 | 1 | 2 | 3 | 3 | 4 | 3 | 2.35 (6) | 5 | 6 |
| N2 | Offer-acceptance improvement tooling | 2 | 1 | 2 | 2 | 2 | 3 | 2 | 1.90 (7) | 7 | 7 |
| N1 | Job-board integration | 2 | 1 | 2 | 2 | 1 | 2 | 1 | 1.55 (8) | 8 | 8 |

**Key score justifications** (the full list is in `phase3_decision_traceability.csv`):

| Initiative | Score | Justification |
|---|---|---|
| B1 | Evidence 5 | DQ-06 confirmed defect, robust to every definition |
| B1 | Impact 5 | It determines the answer to claim B |
| B2 | Evidence 3 | DQ-28 is a suspicious pattern; DQ-11 is confirmed |
| B3 | Time to value 3 | Value accrues as new data is captured |
| N1 | Evidence 1 | Friction is unmeasured |
| N1 | Effort 1 | Unestimated |
| N1 | Dependency 1 | Blocked by C-12 |
| X2 | Evidence 1 | n = 2–5 hires per department (M-T1) |

**Robustness.** The top three are the same three builds, in the same order, under the weighted, equal-weight and no-effort schemes. *Interpretation:* the choice does not depend on the exact weights.

**X1 and X2 are not non-builds, and why they lost:**
- **X1 (interview scheduling and feedback tooling):** 22/160 interviews not completed (M-I0) is a real signal. But the Interviews table may be incomplete (DQ-16, 44/50), and feedback latency is unmeasurable (DQ-24), so the problem is not yet sized. It goes to the backlog behind C-05.
- **X2 (department cycle-time analytics):** cheap, but n is too small to be meaningful for Acme today.

## 5. The three non-builds

### N1: Job-board integration (defer pending validation)

| Question | Answer |
|---|---|
| **What is deferred** | Building new or deeper job-board connectors (automated applicant import and status sync) in Q3 |
| **Why stakeholders want it** | Job boards are the largest source: 236/350 applications and 7/26 hires as recorded. The VP sees them as the channel that matters most, and integrations are a visible, demo-able feature |
| **Evidence against building now** | (1) Volume is already high: integration targets the input that is least constrained. (2) Lowest conversion of any channel with hires: 2.7%–3.4% per application under every attribution, and 13/90 offers after interview. (3) **No measurement of friction exists**: manual effort, latency, lost applicants. (4) Hire attribution itself is unreliable (DQ-01). (5) Cost is unestimated, and connectors add permanent maintenance |
| **Opportunity cost** | A plausible connector scope for even one board is unestimated. Any realistic version would take most or all of the 6 engineer-weeks (an *assumption*, to be checked with engineering), displacing all three builds, including the fix to the metric leadership is using |
| **What would make me reconsider** | Any of these: (a) B3 intake data or the C-12 interview shows manual board entry costs at least an agreed threshold of recruiter hours per week, or measurable applicant loss or delay; (b) engineering estimates a single-board connector at ≤ 2 engineer-weeks with low maintenance; (c) attribution is resolved (C-04) and job-board yield is no longer the lowest. **Decision point:** Q4 planning, with one quarter of B3 data |

### N2: Offer-acceptance improvement tooling (do not build)

| Question | Answer |
|---|---|
| **What is rejected** | Compensation benchmarking or "offer intelligence", candidate engagement nudges between offer and decision, and counter-offer playbooks aimed at raising acceptance |
| **Why stakeholders want it** | The VP says acceptance "needs improvement", and Counter Offer is the most common recorded decline reason (3/5) |
| **Evidence against** | (1) The "low" rate is largely a definition artefact (72.2% vs 83.9%). (2) There are 5 declines in total, so one decline moves the decline rate by 3.2 points. (3) Compensation data cannot be interpreted against expectations (DQ-25; M-B7 and M-B8 are not interpretable). (4) There is no benchmark or target (C-13). (5) The decline-reason taxonomy is a single category per offer (OAM-11 is not measurable) |
| **Opportunity cost** | Building it before B1 would optimise a metric we cannot measure correctly yet |
| **What would make me reconsider** | B1 live for one quarter with clean statuses; at least 30 decided offers in a period; an agreed benchmark or target; a decided-offer rate below that target; and decline reasons pointing to a fixable cause |

### N3: Referral programme features (do not build)

| Question | Answer |
|---|---|
| **What is rejected** | Referral portals, referral bonus tracking and employee referral campaigns |
| **Why stakeholders want it** | As recorded, Referral looks outstanding: a 7/13 hire rate per application, and it ties Job Board on hires (7/26) from 13 applications |
| **Evidence against** | 7/7 Referral-labelled hires have **no referrer link** (M-A9n). 4 of them come from 2 candidates (DQ-04). Applications with a referrer link convert at 3/27 (M-A7s-Referral (linked)). The apparent advantage rests on the field B3 is fixing. REJ-011: Referral is not a proven high performer |
| **Opportunity cost** | It would invest in a channel whose performance is an artefact of mislabelled data |
| **What would make me reconsider** | After B3, at least one quarter of applications with validated referral links showing linked referrals convert materially above other channels, on enough hires to survive one-record swings |

## 6. Trade-offs

**1. Measurement over feature growth.**
- *What we give up:* nothing in Q3 is directly "new capability" for candidates.
- *What we get:* the two numbers leadership argues about become trustworthy. Every later investment decision, including job boards, gets a real basis.

**2. Flags and queues, not automation.**
- *What we give up:* B2 and B1 never auto-close or auto-change statuses. That costs some potential efficiency.
- *What we get:* no silent data changes on unconfirmed semantics (C-06, C-11). Automation is conditional scope.

**3. B3 over B2 at the margin.**
- B3 scores above B2 because its defect is confirmed and it unblocks the VP's own question.
- B2 has more immediate user value, but its core signal is a suspicious pattern.
- Both are funded; if the cut line is triggered, B3's duplicate warning goes before B2's queue.

**4. Saying no to the VP's request.**
- This is mitigated by turning it into a **dated decision** (Q4) with explicit reconsideration criteria, fed by data that B3 starts collecting in Q3.

## 7. Assumptions and validations this strategy depends on
**New assumptions:**
- **ASM-022:** effort figures are planning estimates.
- **ASM-023:** the Airtable base mirrors TalentFlow's data model.
- **ASM-024:** recruiters will act on queues.
- **ASM-025:** the n ≥ 10 display threshold.
- **ASM-026:** capacity is 2 engineers × 3 weeks, fungible across front end and back end.

**Existing assumptions still relied on:** ASM-007, ASM-008, ASM-013, ASM-021.

**Customer validation:** see `customer_validation_plan.md`. No committed scope depends on an unanswered question.

## 8. Success metrics, pilot and experiment design

**The scorecard** is in `product_success_metrics.csv`: 16 metrics, at least one adoption, one outcome or data-quality, and one guardrail per build. Each row gives its baseline, the baseline source ID, a target or decision rule with its status, the measurement method, data source, evaluation window and owner.

**Kinds of metric:**
- **Adoption metrics** (SM-B1-2, SM-B2-1, SM-B3-2): are recruiters using the workflow?
- **Outcome and data-quality metrics** (SM-B1-1, SM-B1-3, SM-B1-4, SM-B2-2 to SM-B2-4, SM-B3-1, SM-B3-3, SM-B3-4): did the record state or the decision improve?

**Rules for targets:**
- **Firm targets** exist only where the build *enforces* the outcome. For example, 0 new status/date contradictions after B1.1, or 0 new Source/referrer conflicts after B3.1.
- **No improvement target** is set where only a 3-month-old snapshot baseline exists (SM-B2-2, SM-B2-4). A live baseline is measured in sprint 3 first.
- **Adoption thresholds** are stated as *decision rules* (continue or investigate), not as forecasts.

**Pilot 1: does B2 address a real workflow problem? (validates C-11)**
- **Before the build:** in sprint 2, review 20 randomly sampled inactivity-flagged applications with 2 Acme recruiters and classify each:

  | Classification | What it means |
  |---|---|
  | (a) Truly abandoned | The problem is real |
  | (b) Tracked outside TalentFlow | The problem is a sync or adoption gap, not hygiene |
  | (c) Legitimately waiting | The stall rule is too aggressive |

- **Stop condition:** if (a) is under 50% of the sample, B2's committed scope is cut to the requisition flags and the queue is reconsidered.
- **After release:** stepped rollout by recruiter. Half of Acme's recruiters get the queue in week 1, the rest in week 3. Their disposition and stalled-share trajectories are compared over weeks 1–3.
- **Not a causal estimate:** with 4 recruiters this is a *directional* check, not an effect size.

**Pilot 2: what is actually wrong with the conflicting Pending offers? (validates C-02 and DQ-06)**
- For the conflicting offers, the recruiter records the true outcome through the B1 queue. We then count how many were wrong in status vs wrong in date.
- This tells us whether the B1 constraint, which forces the status to change when a date is entered, addresses the dominant failure.

**Pilot 3: does job-board intake cost recruiter time? (feeds N1 and C-12)**
- B3's Intake Method plus the SM-B3-G1 form-timing telemetry give, for the first time, the share of job-board applications entered by hand and the time spent per entry.
- Combined with the C-12 interview, this is the evidence the N1 reconsideration criteria require at Q4 planning.

**On causality:**
- Before/after changes in OAM-01 are **not** attributed to B1. B1 changes how offers are *recorded*, not candidate behaviour.
- Any OAM-01 movement after the backlog is cleaned is a measurement correction, and will be reported as such.
