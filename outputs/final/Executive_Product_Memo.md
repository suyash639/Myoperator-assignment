# TalentFlow Q3: Executive Product Memo

**To:** VP Product · **Re:** Acme Corp Q3 priorities (6 engineer-weeks) · **Date:** 2026-11-24 · **Basis:** Acme Airtable snapshot, extracted read-only 2026-11-24 (apparent import 2026-08-27; business cutoff unconfirmed)

## The answer
Both VP numbers reproduce, but neither supports the conclusion drawn from it.
- **Job boards** supply many hires because they supply most applications, yet they convert worst. Nothing shows an integration would change that.
- **The "72%"** counts unresolved offers as failures.

The urgent problem is that Acme's records don't reliably show **which offers are open, which applications are live, and where candidates came from**. Q3 should fix that visibility, not add an acquisition integration.

## What the data shows
| Question | Finding | Evidence |
|---|---|---|
| Job boards 26.9% of hires? | **Yes:** 7/26 hires (Source as recorded); 23.1%–30.8% across attribution methods | FND-01 |
| An efficient channel? | **No:** 236/350 applications (67.4%) but 3.0% hired per application (2.7%–3.4% across methods); the lowest of any channel with hires (next lowest 9.7%) | FND-02, FND-03 |
| Acceptance ~72%? | Only as the **all-issued-offer ratio**, 26/36 = 72.2% (5 pending offers counted as failures). **Decided-offer acceptance is 26/31 = 83.9%** | FND-06, FND-07 |
| Offer data reliable? | **No:** 4/5 "Pending" offers carry a decision date; no Expired or Withdrawn status exists | FND-09 |
| Pipeline current? | 50/105 Active applications idle > 90 days; 15/24 openings contradict their applications | FND-14, FND-15 |
| Channel data reliable? | Source contradicts the referral link on 34/350 applications; none of the 7 Referral-labelled hires has a referrer | FND-05 |

*Not established:* whether 83.9% is good or bad (no target or benchmark), or what job-board intake costs recruiters (unmeasured). *Provisional:* a hire means Application Stage = Hired, pending Acme confirmation (C-15).

## Q3 recommendation: three builds, 6.0 engineer-weeks
| Build | What it fixes | Effort* |
|---|---|---:|
| **B1** Offer lifecycle and reliable offer metrics | Valid statuses, dated events, audit trail. Acceptance at the decision event; pending offers and reneges shown separately | 2.5 |
| **B2** Application inactivity and opening-status visibility | Configurable inactivity flags and opening-status review flags; never automatic changes | 2.0 |
| **B3** Acquisition-source and intake tracking, with duplicate warnings | Per-application source, system-recorded intake method, referral rules, warning-only duplicate check | 1.5 |

*PM planning estimates, not engineering commitments. If they don't hold, scope is cut along a defined cut line; capacity is not extended.

## Not in Q3
1. **Job-board integration: deferred to Q4.** Volume isn't shown to be the constraint; friction is unmeasured; cost is unestimated. B3 starts collecting the evidence.
2. **Offer-acceptance improvement tools: deferred.** Only 5 declines, no benchmark, and the pay data can't be interpreted.
3. **Referral-programme features: deferred.** Referral's apparent strength comes from unlinked labels.

## What Acme should expect
- **At release:** decided rate, all-issued ratio and pending backlog reported side by side; **no new offer status/decision-date contradictions can be saved.**
- **After a quarter:** first intake-method measurements for the job-board decision.
- **Not promised:** higher acceptance or conversion. These builds change how events are *recorded*, not candidate behaviour.

## Decisions needed
1. **PM:** approve DEC-025 to DEC-037; most can be approved now (see the register). DEC-038, which keeps a reneged offer counted as accepted, is approved.
2. **Acme:** role mapping (C-17), privacy policy (C-18), hire definition (C-15), true state of the pending offers (C-02).
3. **Engineering:** validate the estimates and the delivery model (2 engineers × 3 one-week sprints).
