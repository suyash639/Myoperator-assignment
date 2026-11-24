# D3: Offer Acceptance Metric Specification

**Status:** proposed for PM ratification (DEC-029, amended in Phase 3.1 by DEC-033 and DEC-034). It formalises the provisional DEC-016.

**Phase 3.1 changes:**
- Status is evaluated as of the as-of date (§3.5).
- Lifecycle effects on the metric are defined (§8).
- Reliability tiers and privacy suppression are separated (§3.12, §3.14).

**Phase 3.2 changes:**
- **Event time:** every metric is computed from the offer's event history at the as-of date, never from its latest status.
- **Acceptance stands:** OAM-01 counts acceptance at the decision event; a later renege or rescission does not erase it.
- **Post-acceptance metrics:** OAM-13a and OAM-13b are defined.
- **Privacy:** the threshold is a configurable *proposed* policy pending Acme privacy/legal approval.
- **Roles:** the roles are proposals; the Acme role mapping is unresolved (C-17).

**Reference implementation:** `src/offer_metrics.py`, which produces `outputs/offer_metric_baseline.csv`. Every value quoted below comes from it and is reconciled by test against `metric_calculations.csv`.

**Grain:** **offer-level** throughout, except OAM-09, which is labelled candidate-level and is never combined with offer-level figures.

## 1. Primary metric: Decided Offer Acceptance Rate (OAM-01)

| Field | Definition |
|---|---|
| **Metric name** | Decided Offer Acceptance Rate |
| **Business purpose** | Of the offers on which a candidate has reached a recorded decision, what share were accepted? It tells hiring leadership whether offers that get decided convert. It deliberately excludes unresolved offers, which are tracked separately (OAM-03, OAM-04) so the backlog is not hidden |
| **Numerator** | Count of counted offers (§3.3, §3.6) whose **decision outcome** is Accepted with a valid `Decision On` ≤ as-of date. Today the decision outcome is `Status`; after B1 it is the immutable `decision_outcome` field (§8) |
| **Denominator** | Count of counted offers whose decision outcome is Accepted or Declined with a valid `Decision On` ≤ as-of date |
| **Grain** | One row per offer record. A candidate with two decided offers contributes two rows |
| **Eligible statuses** | Accepted, Declined |
| **Excluded statuses** | Pending at the as-of date (§3.5). After B1: Expired, Withdrawn-before-decision and Rescinded-before-decision are **excluded from OAM-01** and counted in OAM-06x; Superseded is excluded from every metric (§3.6, §8). A *reneged* or *rescinded-after-acceptance* offer keeps its Accepted decision in OAM-01 and is counted in OAM-13a/13b (§8) |
| **Unit** | Percentage to 1 decimal, always shown with its counts, e.g. "83.9% (26/31)" |
| **Current observed value** | **26/31 = 83.9%** at the provisional cutoff 2026-08-27. One decided offer = 3.2 percentage points |
| **Measurability** | **Measurable with a data-quality caveat:** 4/5 Pending offers carry a decision date (DQ-06), and the cutoff is unconfirmed (DEC-020) |

## 2. Supporting metrics

| ID | Metric | Definition | Current value | Measurability |
|---|---|---|---|---|
| OAM-02 | **All-Issued Offer Acceptance Ratio** | Accepted ÷ all counted offers with Offered On ≤ as-of (Pending included in the denominator) | 26/36 = 72.2% | Measurable with caveat. **Always labelled "ratio", never "acceptance rate"** |
| OAM-03 | **Pending offer count** | Counted offers with Status = Pending | 5 | Measurable with caveat |
| OAM-03c | Pending offers with a status/date conflict | Pending AND Decision On present | 4/5 | Measurable (data-quality indicator) |
| OAM-04 | **Pending offer ageing** | as-of minus Offered On, in days, per Pending offer, bucketed 0–14 / 15–30 / 31–60 / over 60, plus the oldest | 0 / 2 / 0 / 3; oldest 222 days | Measurable with caveat (cutoff-dependent: at 2026-11-24 all 5 are over 30 days) |
| OAM-05 | **Decision turnaround** | Median and p75 of (Decision On minus Offered On) in days, over OAM-01 denominator offers | Median 10, p75 15 (n = 31) | Measurable |
| OAM-06 | **Offer Decline Rate** | Declined ÷ OAM-01 denominator (equals 1 minus OAM-01) | 5/31 = 16.1% | Measurable with caveat |
| OAM-06-reason | Declines by recorded Decline Reason | Count per category; **counts only, no causal reading** | Counter Offer 3, Location 1, Compensation 1 | Measurable (categories as recorded) |
| OAM-07 | **Acceptance by department** | OAM-01 restricted to the opening's department | Every department has fewer than 10 decided offers, so **all are suppressed** (counts shown) | Measurable; **not interpretable at current volume** |
| OAM-08 | Acceptance by decision period | OAM-01 by half-year of Decision On | 2025-H2: 6 decided (suppressed); 2026-H1: 14/19 = 73.7%; 2026-H2: 6 decided (suppressed) | Measurable with caveat |
| OAM-09 | Candidate-level decided acceptance (**secondary**) | Candidates with at least 1 Accepted ÷ candidates with at least 1 decided offer | 24/28 = 85.7% | Measurable with caveat. **Different grain; never shown in the same tile as OAM-01** |
| OAM-01b | OAM-01 excluding offers to previously hired candidates | OAM-01 minus §3.7-flagged offers | 24/28 = 85.7%, offer-level (coincidentally the same counts as OAM-09) | Measurable; variant pending C-08 |
| OAM-10 | Accepted offers whose application is not Stage = Hired | Consistency check | 0/26 | Measurable |
| OAM-11 | Decline explanation beyond the category | — | n/a | **Not currently measurable** (one category per offer; no detail) |
| OAM-13a | **Post-acceptance reneging rate** | Offers accepted at a decision event on or before the as-of date AND followed by a candidate withdrawal (Accepted → Withdrawn) dated on or before the as-of date ÷ offers accepted at a decision event on or before the as-of date | n/a | **Not currently measurable** (legacy data cannot represent it); measurable after B1 |
| OAM-13b | **Post-acceptance rescission rate** | Same, for a company rescission after acceptance (Accepted → Rescinded) | n/a | **Not currently measurable**; measurable after B1 |
| OAM-06x | Offers resolved without a decision | Expired, Withdrawn or Rescinded *before* any decision event, on or before the as-of date ÷ counted offers | n/a | **Not currently measurable**; measurable after B1 |
| OAM-12 | Expiry adherence | Share of Pending offers past Expires On | n/a | **Not currently measurable** until B1 adds Expires On and Expired |

**§2.5, after B1 (future rows, not computable today):**
- **OAM-06x:** offers resolved without a decision (Expired, Withdrawn-before-decision, Rescinded-before-decision), shown beside OAM-01 as counts.
- **OAM-13a and OAM-13b:** post-acceptance reneges and rescissions, defined in §2. These offers **stay in the OAM-01 numerator**, because OAM-01 records the decision event.
- **OAM-02** keeps every non-Superseded offer issued in the period in its denominator, whatever its status at the as-of date.

## 3. Rules

### §3.1 Data source
- **Today:** the Airtable `Offers` table (Status, Offered On, Decision On, Decline Reason, Application link), joined to `Applications` (Candidate, Opening, Stage) and `Job Openings → Departments`.
- **After B1:** the TalentFlow offer entity with the extended status model.

### §3.2 As-of date
- Every computation takes an explicit `as_of` parameter.
- An offer is visible only if Offered On ≤ as_of, and a decision counts only if Decision On ≤ as_of.
- Because the business cutoff is unconfirmed (DEC-020), reports state the as-of date. Cutoff-dependent metrics (OAM-04) are shown at the provisional 2026-08-27, with sensitivity at 2026-08-30 and 2026-11-24.
- In production, `as_of` = the refresh timestamp.

### §3.3 Eligibility
- An offer is counted if it has an Application link and Offered On ≤ as_of.
- An offer with no Offered On is excluded and counted as `MISSING_OFFER_DATE` (currently 0).

### §3.4 Decided offers
- Status ∈ {Accepted, Declined} **and** Decision On present **and** Decision On ≤ as_of.
- A decided status *without* Decision On is excluded from OAM-01 and counted as `DECIDED_NO_DATE` (currently 0).
- *Rationale:* a decision must be dated to be attributed to a period.

### §3.5 Pending treatment, evaluated as of the as-of date
- An offer is **pending at the as-of date** if it was offered on or before that date and had no decision or resolution dated on or before it.
- Today that means Status = Pending, **or** a decided status whose Decision On is after the as-of date. On the snapshot the second group is 0 (E-D3-1).
- **Event-time rule (Phase 3.2).** The state at the as-of date is reconstructed from the offer's event log in business-date order (`event_state` in `src/offer_metrics.py`).
  - The **first decision event** (Accepted or Declined) dated on or before the as-of date sets the decision outcome.
  - Later events never change that outcome; they set only post-acceptance or resolution flags.
  - The latest status is **never** read for a metric.
  - Legacy records are converted to events first: a decision event exists only when Status is Accepted or Declined *and* a Decision On is present. A legacy Pending offer with a Decision On gets no decision event and is flagged.
- Pending is **excluded** from OAM-01 and appears in OAM-03 and OAM-04.
- A Pending offer *with* Decision On is still treated as Pending, because **Status is authoritative for eligibility**. It is flagged `STATUS_DATE_CONFLICT` (OAM-03c).
- It is **not** reclassified, because we do not know the outcome (C-02).
- After B1 such records cannot be created.

### §3.6 Duplicate and revised offers
- If an application has more than one offer issued on or before the as-of date, **only the latest by Offered On counts**; ties are broken by record ID, latest wins.
- **Pending earlier offers:** they become `Superseded` (system transition, §8) and are excluded from every metric.
- **Decided or resolved earlier offers** (Declined, Expired, Withdrawn, Rescinded): they keep their status and are counted only in a revision counter, `REVISED_AFTER_RESOLUTION`. So the application contributes exactly one offer, the latest, to OAM-01 and OAM-02.
- **Accepted offers cannot be revised.** They must first be withdrawn or rescinded.
- *Consistency:* a revision issued after the as-of date does not supersede anything at that date, because only offers with Offered On on or before the as-of date are considered.
- **Today:** no application has more than one offer, so 0 are superseded.
- Offers on *different* applications of the same candidate are separate offers (offer-level grain).

### §3.7 Offers to previously hired candidates
- These are offers where the same candidate has another application at Stage = Hired whose offer Decision On is earlier than this offer's Offered On.
- They are **included** in OAM-01 and flagged. OAM-01b shows the rate without them.
- *Current:* 3 of the 31 decided offers.
- They are not excluded by default, because whether they are internal moves is unconfirmed (C-08).

### §3.8 Date attribution and reporting period
- OAM-01, OAM-05 and OAM-06 attribute each decided offer to the period containing its **Decision On**.
- OAM-02, OAM-03 and OAM-04 use **Offered On** and the as-of date.
- **Default period:** a rolling 2 quarters. Half-years are used for history while volume is low.
- *Why Decision On:* attributing by Offered On would leave recent cohorts permanently incomplete while their offers are pending.

### §3.9 Missing or invalid status
- A status outside the allowed vocabulary, or missing, is excluded from every rate and counted as `INVALID_STATUS` (currently 0).
- Any non-zero exception count is shown on the dashboard.

### §3.10 Refresh frequency
- **Daily**, at 02:00 local time, recomputed from source records with no incremental state.
- The dashboard shows the last refresh timestamp.

### §3.11 Department and level breakdowns
- These use the opening's department (ASM-018) and level.

### §3.12 Reliability tiers (small-sample rule, DEC-034)
This rule is about **statistical reliability**. It applies to every rate, for every viewer.

| Denominator | Display | One record moves the rate by |
|---|---|---|
| n < 10 | **Counts only**, e.g. "3 of 4 accepted"; no percentage | more than 10 points |
| 10 ≤ n < 30 | Rate **with a low-sample label** stating the one-record swing, e.g. "73.7% (14 of 19), low sample: 1 offer = 5.3 points" | 3.4 to 10 points |
| n ≥ 30 | Rate with counts | 3.3 points or less |

- **Current examples:**
  - OAM-01 (31) displays normally.
  - OAM-01b and OAM-09 (28) and OAM-08 2026-H1 (19) carry the low-sample label.
  - Every department (OAM-07) is counts only.
- No sampling intervals are shown (DEC-018). Thresholds are ASM-025.

### §3.14 Privacy suppression: PROPOSED, configurable policy (separate from reliability, DEC-034)
> **Status: proposed policy, not a confirmed requirement.** The threshold is a configurable parameter (`privacy_k`, default 5). It **requires Acme privacy/legal approval** (customer dependency C-18, ASM-028). It is **not presented as a regulatory requirement**; no regulation has been identified or assessed.

This rule is about **individual visibility**, not reliability.
- It applies only to **breakdown cells**: department, level, period, decline reason.
- It applies only to **viewers without record-level offer access**, such as leadership dashboards and exported summaries.
- **The proposed rule:** any cell where the accepted, declined or total count is below `privacy_k` is shown as "<k" (counts hidden too) for those viewers.
- Recruiters with record-level access already see the offers, so they get the reliability rule only.
- *Example:* "Sales: 3 of 3 accepted" would reveal each candidate's decision, so it is hidden for aggregate-only viewers.
- **Under the proposed default:** all OAM-07 departments, the OAM-06 decline reasons, and OAM-08 2025-H2 and 2026-H2 would be restricted.
- If Acme approves a different value, or no suppression, only `privacy_k` changes.
- The `offer_metric_baseline.csv` column `privacy` shows the result per row.

### §3.13 Data-quality exception counters
- These are always computed and shown beside the metric: `STATUS_DATE_CONFLICT`, `DECIDED_NO_DATE`, `MISSING_OFFER_DATE`, `INVALID_STATUS`, `SUPERSEDED`, prior-hire flag.

## 4. SQL-style pseudocode

```sql
-- parameters: :as_of (date), :period_start, :period_end
WITH counted AS (                        -- §3.3 eligibility, §3.6 revised offers
  SELECT o.*, a.candidate_id, a.stage, j.department,
         row_number() OVER (PARTITION BY o.application_id ORDER BY o.offered_on DESC, o.id DESC) AS rn
  FROM offers o
  JOIN applications a ON a.id = o.application_id
  JOIN job_openings j ON j.id = a.opening_id
  WHERE o.offered_on IS NOT NULL AND o.offered_on <= :as_of
),
cur AS (SELECT * FROM counted WHERE rn = 1),
decided AS (                             -- §3.4
  SELECT * FROM cur
  WHERE status IN ('Accepted', 'Declined')
    AND decision_on IS NOT NULL AND decision_on <= :as_of
    AND decision_on BETWEEN :period_start AND :period_end      -- §3.8
)
SELECT
  count(*) FILTER (WHERE status = 'Accepted')                        AS oam01_numerator,
  count(*)                                                           AS oam01_denominator,
  CASE WHEN count(*) >= 10
       THEN round(100.0 * count(*) FILTER (WHERE status = 'Accepted') / count(*), 1)
  END                                                                AS oam01_pct,       -- NULL = suppressed (§3.12)
  (SELECT count(*) FROM cur WHERE status = 'Pending')                AS oam03_pending,
  (SELECT count(*) FROM cur WHERE status = 'Pending' AND decision_on IS NOT NULL) AS status_date_conflict,
  (SELECT count(*) FROM cur WHERE status IN ('Accepted','Declined') AND decision_on IS NULL) AS decided_no_date,
  (SELECT count(*) FROM counted WHERE rn > 1)                        AS superseded
FROM decided;

-- §3.7 prior-hire flag (per offer)
-- EXISTS (SELECT 1 FROM applications h JOIN offers ho ON ho.application_id = h.id
--         WHERE h.candidate_id = cur.candidate_id AND h.id <> cur.application_id
--           AND h.stage = 'Hired' AND ho.decision_on < cur.offered_on)
```

## 5. Example calculation (snapshot, as-of 2026-08-27)

| Step | Count |
|---|---:|
| Offers with Offered On ≤ as-of | 36 |
| Superseded (revised) | 0 |
| Counted offers | 36 |
| Accepted with a decision date | 26 |
| Declined with a decision date | 5 |
| Pending (excluded from OAM-01) | 5, of which 4 have STATUS_DATE_CONFLICT |
| **OAM-01** | **26 / (26 + 5) = 26/31 = 83.9%** |
| OAM-02 | 26/36 = 72.2% |
| OAM-06 | 5/31 = 16.1% |
| Prior-hire offers in the OAM-01 denominator | 3; OAM-01b = 24/28 |

## 6. Edge cases

| Case | Treatment |
|---|---|
| Pending with a decision date | Pending; flagged (§3.5) |
| Accepted or Declined without a decision date | Excluded; counted `DECIDED_NO_DATE` (§3.4) |
| Decision On before Offered On | Excluded; counted as invalid chronology (0 today) |
| Decision On after as-of | Treated as not yet decided at that as-of |
| Offer revised while Pending | Earlier becomes Superseded (system); latest counts (§3.6) |
| Offer revised after a decline or expiry | Earlier keeps its status; only the latest counts; REVISED_AFTER_RESOLUTION counter (§3.6) |
| Attempt to revise an Accepted offer | Rejected by B1; withdraw or rescind first |
| Candidate accepts, then withdraws before starting (renege) | After B1: status Withdrawn, decision_outcome stays Accepted. It **stays in OAM-01 as accepted** (OAM-01 measures the decision) and is counted in OAM-13a/13b. *Today it cannot be represented* |
| Company rescinds before a decision | After B1: Rescinded; excluded from OAM-01; counted in OAM-06x |
| Company rescinds after acceptance | After B1: Rescinded, decision_outcome stays Accepted; stays in OAM-01; counted in OAM-13a/13b |
| Decision dated after the as-of date | Pending at that as-of date (§3.5) |
| Offer past expiry with no answer | After B1: Expired; excluded from OAM-01, counted in OAM-06x. Until C-03, no default expiry |
| Two offers to one candidate on different applications | Two offers (offer-level). OAM-09 collapses them at candidate level |
| Offer to an already-hired candidate | Included; flagged; OAM-01b variant (§3.7) |
| Department or level denominator under 10 | Counts only (§3.12) |
| Accepted offer whose application is not Hired | Counted in OAM-01; flagged by OAM-10 |

## 7. Dashboard presentation

1. **Headline tile:** "**Decided offer acceptance: 83.9% (26 of 31)**", with the period, as-of date and last refresh.
   - Subtitle: "5 offers pending (4 with status conflicts) · oldest 222 days".
2. **Second tile, same row, visually distinct:** "**All issued offers accepted: 72.2% (26 of 36)**".
   - Footnote: "includes pending offers; not a decision rate".
3. **Pending ageing bar:** the 0–14, 15–30, 31–60 and over-60-day buckets, linking to the B1 pending-offer queue.
4. **Decision turnaround:** median and p75 in days.
5. **Decline breakdown:** counts by recorded reason, labelled "as recorded". No percentages while declines are below 10.
6. **Breakdowns** by department, level and period: the reliability tiers (§3.12) for everyone; the privacy rule (§3.14) for aggregate-only viewers.
7. **Data-quality strip:** the §3.13 exception counters. Red if any is non-zero.
8. **Candidate-level OAM-09** appears only in a separate "candidate view" tab, never beside OAM-01.
9. **No sampling intervals, and no target line** until a target is agreed (C-13).

## 8. Offer lifecycle model (B1) and its effect on the metric

**Executable reference:** `src/offer_lifecycle.py`, tested in `tests/test_phase3_1.py`. The table below is generated from that model and checked verbatim by `src/phase3_checks.py`.

**Statuses:** Pending, Accepted, Declined, Expired, Withdrawn, Rescinded, Superseded.

**Roles are proposals.** "recruiter", "hiring_manager", "recruiting_ops_lead" and "system" are **proposed TalentFlow roles**. Acme's actual roles and who may perform each transition are **not known and have not been assumed**. Mapping them is an unresolved customer dependency (C-17, ASM-031), and the permission table is configuration, not a confirmed Acme policy.

**Terminal statuses:**
- Declined, Expired, Withdrawn, Rescinded and Superseded are final.
- Accepted is final except for a renege (→ Withdrawn) or a rescission (→ Rescinded).
- **No transition returns to Pending.** Mistakes are fixed by an audited correction (below).

| From | To | Who can trigger | Business date recorded | Reason required | Meaning |
|---|---|---|---|---|---|
| Pending | Accepted | recruiter, recruiting_ops_lead | `decision_on` | no | Candidate accepted |
| Pending | Declined | recruiter, recruiting_ops_lead | `decision_on` | yes | Candidate declined; decline_reason from controlled list |
| Pending | Expired | recruiter, recruiting_ops_lead, system | `expired_on` | no | Offer lapsed without a decision. 'system' only when expires_on is set and auto-expiry is enabled (conditional scope, C-03) |
| Pending | Withdrawn | recruiter, recruiting_ops_lead | `withdrawn_on` | yes | Candidate withdrew before deciding |
| Pending | Rescinded | hiring_manager, recruiting_ops_lead | `rescinded_on` | yes | Company withdrew the offer before a decision |
| Pending | Superseded | system | `superseded_on` | no | Set automatically when a new offer is created on the same application; superseded_on = new offer's offered_on |
| Accepted | Withdrawn | recruiter, recruiting_ops_lead | `withdrawn_on` | yes | Candidate reneged after accepting; decision is retained |
| Accepted | Rescinded | hiring_manager, recruiting_ops_lead | `rescinded_on` | yes | Company rescinded after acceptance; decision is retained |

### 8.1 Field invariants (contradictory records cannot be saved)
| Status | Required | Must be empty |
|---|---|---|
| Pending | — | `decision_on`, `expired_on`, `withdrawn_on`, `rescinded_on`, `superseded_on` (so **Pending with a decision date is impossible**) |
| Accepted / Declined | `decision_on`; `decision_outcome` = status; Declined also needs `decline_reason` | — |
| Expired | `expired_on` | `decision_on` |
| Withdrawn / Rescinded | `withdrawn_on` / `rescinded_on` | `decision_on`, unless the offer was previously Accepted (renege or rescission keeps the decision) |
| Superseded | `superseded_by` (an offer on the same application), `superseded_on` | `decision_on` |
| Any | every event date ≥ `offered_on`; business date ≤ the recording date | — |

### 8.2 Timestamps and audit
- **Two dates on every event:**
  - `business_date`: when it happened, entered by the recruiter or derived by the system. This is what metrics use.
  - `recorded_at`: the system write time, never editable. This is what audit and as-of reconstruction use.
- **Status changes only through events.** Each event records offer, from-status, to-status, actor, role, event type (transition / system / correction), business_date, recorded_at and reason. SM-B1-G3 enforces 0 status changes without an event.
- **Corrections:** only the recruiting-ops lead can correct a record. The correction must leave the record valid, and before/after values are logged. This is how the 4 legacy Pending offers with decision dates are resolved once their true outcome is known (C-02).
- **Legacy records** are flagged at migration and never rewritten. On the snapshot the invariants flag exactly those 4 offers (E-B1-1, matching DQ-06 and OAM-03c).

### 8.3 Effect on the metrics (all evaluated at the as-of date)
| Lifecycle situation | OAM-01 numerator | OAM-01 denominator | OAM-02 denominator | Counter |
|---|---|---|---|---|
| Accepted | ✓ | ✓ | ✓ | — |
| Declined | — | ✓ | ✓ | OAM-06 |
| Pending at the as-of date | — | — | ✓ | OAM-03, OAM-04 |
| Expired, Withdrawn or Rescinded before a decision | — | — | ✓ | OAM-06x |
| Accepted, then Withdrawn (renege) | ✓ | ✓ | ✓ | OAM-13a, if the withdrawal is dated on or before the as-of date |
| Accepted, then Rescinded by the company | ✓ | ✓ | ✓ | OAM-13b, if the rescission is dated on or before the as-of date |
| Superseded | — | — | — | SUPERSEDED |
| Earlier offer resolved, then revised | — (only the latest counts) | — | — | REVISED_AFTER_RESOLUTION |
