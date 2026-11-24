# Open Questions for Acme Corp (and the VP of People)

**Purpose.** The data cannot answer these questions. Each one names the decision or metric it blocks and the exact evidence behind it. Record IDs are Airtable IDs or business IDs; no personal data is included.

**Priority:**
- **P1:** blocks a D1 verdict or the D3 definition.
- **P2:** changes a D2 priority.
- **P3:** hygiene or context.

**Mapping.** Supersedes and extends Q1–Q8 in `data_quality_audit.md` §8:

| Old | New |
|---|---|
| Q1 | C-04 |
| Q2 | C-02 |
| Q3 | C-03 |
| Q4 | C-05 |
| Q5 | C-06 |
| Q6 | C-07 |
| Q7 | C-09 |
| Q8 | C-12 |

---

## P1: blocks D1 or D3

### C-13. How were the VP's figures, 26.9% and 72%, calculated?
- **Who to ask:** VP of People.
- **Evidence:**
  - Both figures reproduce exactly under specific definitions: Source as recorded ÷ all hires, and Accepted ÷ all offers *including Pending*.
  - Neither definition was stated.
- **Blocks:** D1 (whether we are testing the same metric), D3.
- **Ask:** which report or view produced each figure, for what period, and was Pending counted as not accepted? Is there a target or benchmark for acceptance?

### C-02. What is the true state of the 5 Pending offers?
- **Who to ask:** Acme recruiting ops.
- **Evidence:**
  - 4 of the 5 have a Decision On date 11–16 days after the offer, within the 2–20-day range of decided offers: OFF-00002, OFF-00007, OFF-00013 and OFF-00020.
  - OFF-00002 is 222 days old, and its application (APP-00001, `reckLPXA8xRgWsC1l`) carries Rejection Reason "Withdrew".
  - OFF-00021 (Engineering) is 117 days old with no decision date.
  - OFF-00007 went to a candidate already hired via another application.
- **Blocks:** D1 Claim B (the range is 72.2%–86.1%), D3 denominator rules.
- **Ask:** for each of the 5, was it accepted, declined, withdrawn or rescinded, and when?

### C-03. Does Acme have an offer-expiry policy?
- **Who to ask:** Acme People team.
- **Evidence:**
  - Offers.Status allows only Accepted, Declined and Pending; there is no Expired, Withdrawn or Rescinded.
  - The 30-day threshold in M-B3 is my assumption (ASM-007).
- **Blocks:** D3 (treatment of stale offers), D2 (whether offer-lifecycle states are a priority).

### C-04. Which field is authoritative for channel: Candidates.Source or Applications.Referred By?
- **Who to ask:** Acme recruiting ops.
- **Evidence:**
  - The two contradict each other on 34 of 350 applications (DQ-01).
  - 17 referred applications are labelled Job Board.
  - **None of the 7 hires labelled Referral has a referrer link.** Only 3 hires have a referrer link, and all 3 have a non-Referral Source.
  - Applications has no Source field; Source is stored once per candidate.
- **Blocks:** D1 Claim A. The range across definitions is 23.1%–30.8%.
- **Ask:**
  - Is Source the first touch, the latest touch, or entered once?
  - Is Referred By filled for every employee referral?

### C-15. What counts as a "hire": accepted offer or start date?
- **Who to ask:** VP of People.
- **Evidence:**
  - Hire = Stage Hired is identical to the Accepted-offer set (26 = 26).
  - No Started or Joined status exists.
  - 2 Accepted offers have proposed start dates after the import date.
- **Blocks:** D1 Claim A denominator, D3.

## P2: changes D2 priorities

### C-12. What does "job-board integration work" mean, and is there evidence of friction?
- **Who to ask:** VP of People, Acme recruiting ops, TalentFlow engineering.
- **Evidence:** the base contains no measure of integration friction: no ingestion timestamps, no import errors, no duplicate-from-board flags, no time spent on manual entry. Job boards already supply 67.4% of applications at the lowest hire rate per application (2.7–3.4%).
- **Blocks:** D2. The VP's priority can't be evaluated without it.
- **Ask:**
  - Which boards are involved?
  - How are their applicants entered today, and how many hours a week does that take?
  - Are applicants lost or delayed?

### C-05. Should the Interviews table hold every round? Where do First and Final Interview On come from?
- **Who to ask:** Acme recruiting ops, TalentFlow engineering.
- **Evidence:**
  - 126 of 143 interviewed applications have exactly 1 interview record.
  - 11 of 26 hires have only a Screen round recorded.
  - Final Interview On is later than every recorded interview in 44 of 50 cases.
  - In 9 of 13 cases where First Interview On differs from the Interviews table, the Interviews record is dated *before the application* and the copied field is plausible. In all 3 Offered On disagreements, the Offers record predates Final Interview On.
- **Blocks:** D4 (DQ-16 classification), D2 (interview-capture priority), and which date source is used for durations (DEC-015).
- **Ask:** are the Application date fields typed in by hand, synced, or automated? Which source is correct when they disagree?

### C-06. What does Applications.Closed On mean?
- **Who to ask:** Acme recruiting ops.
- **Evidence:** applications are closed *before* the offer decision in 17 of 26 hires and 4 of 5 declines. 7 of 84 rejected or withdrawn applications have an interview scheduled after Closed On.
- **Blocks:** D3 (hire date and time-to-hire), D2 (application-lifecycle priority).

### C-11. How are application and requisition statuses maintained?
- **Who to ask:** Acme recruiting ops.
- **Evidence:**
  - 15 of 24 openings have a status that contradicts their applications. For example, REQ-2025-015 is Cancelled with 3 hires, and REQ-2026-017 (Engineering, Lead) is Filled with 0 hires.
  - 50 of 105 Active applications show no activity for more than 90 days; the oldest is 401 days.
  - 55 of 105 Active applications sit on Filled openings.
- **Blocks:** D2 (status-automation priority), the funnel cohort definition.

### C-10. Why has Engineering made no hires?
- **Who to ask:** Acme Engineering hiring manager, recruiting ops.
- **Evidence:**
  - 30 applications reached 3 interviews and 1 offer (OFF-00021, Pending for 117 days).
  - The 3 openings are REQ-2025-001 (Junior, headcount 3, Open), REQ-2025-009 (Senior, Open, past target since 2025-07-29) and REQ-2026-017 (Lead, Filled with 0 hires).
- **Blocks:** context for D2; possibly a missing-data issue.

## P3: hygiene and context

### C-07. Are these duplicate identities real people?
- **Who to ask:** Acme recruiting ops.
- **Evidence:**
  - Six pairs share name, phone, city, employer and email domain: CAND-00001/00002, 00003/00004, 00005/00006, 00007/00008, 00009/00010 and 00011/00012.
  - In 4 of those pairs, the Years Experience values can't belong to one person. For example, CAND-00008 and CAND-00007 have 0.9 and 8.4 years, created 14 months apart.
  - All 8 reused Application IDs (APP-00001, -05, -07, -10) belong to these candidates.
  - CAND-00035 has 2 Accepted offers on the same requisition (REQ-2025-019). CAND-00015 was hired into 2 requisitions.
- **Blocks:** Claim A variants M-A1 and M-A8; whether de-duplication belongs in D2.

### C-08. Are offers to people who were already hired internal moves?
- **Who to ask:** Acme People team.
- **Evidence:** 4 of 36 offers went to candidates already hired through another application: OFF-00005 (Accepted), OFF-00006 (Declined), OFF-00007 (Pending) and OFF-00035 (Accepted).
- **Blocks:** D3. Should internal moves count in external offer acceptance?

### C-09. Is compensation recorded in INR as annual CTC, and are candidates linked to the right openings?
- **Who to ask:** Acme People team.
- **Evidence:**
  - There is no currency field.
  - All phones are +91, and no value is below 100,000, which is consistent with annual INR.
  - Expected CTC tracks experience (r = 0.87), and 29 of 36 offers fall inside the pay band.
  - Only 93 of 350 applications have the candidate's Expected CTC inside the opening's band. For example, a candidate with 0 years' experience received a Senior offer at 4.9× their expectation.
- **Blocks:** any compensation-related analysis (DQ-25). It does not block D1.

### C-01. What date was the data exported from Acme's system?
- **Who to ask:** whoever loaded the base.
- **Evidence:**
  - All 892 records were created in Airtable between 16:39 and 16:40 UTC on 2026-08-27.
  - 3 candidates have a Created On after that, the latest being 2026-08-30.
  - The latest Applied On is 2026-08-27, a single application.
- **Blocks:** pending-offer ages and overdue checks. Headline results are unchanged between 08-27 and 08-30. Using the extraction date (2026-11-24) would make all 5 Pending stale, and M-B3 would become 72.2%.

### C-14. Does the base contain only Acme Corp data?
- **Who to ask:** TalentFlow (base owner).
- **Evidence:** there is no tenant or customer field (ASM-010).
- **Blocks:** the scope of every number.

### C-16. Is this production data or a prepared sample?
- **Who to ask:** TalentFlow (base owner).
- **Evidence:**
  - The base was bulk-loaded within one minute.
  - Repeat applications are numbered APP-003xx, i.e. n + 300.
  - Duplicates, reused IDs and source-table date conflicts cluster in the lowest IDs (CAND-00001 to 00012, APP-00001 to 00019).
- **Blocks:** how far frequencies can be generalised. It does not change the defect findings.
- **How to ask:** phrase it neutrally, as a question about scope.

---

## Decisions for the PM, not the customer
The seven PM decisions originally listed here were all **taken in Phase 2.2**: DEC-016 to DEC-021 and DEC-023 (see `../audit/decision_log.md`). They are no longer open.

---

## Added in Phase 3.2 (cross-reference; earlier entries unchanged)

### C-17. Which Acme roles map to the proposed TalentFlow offer roles?
- **Who to ask:** Acme recruiting ops and the People team.
- **Evidence:** the B1 lifecycle uses *proposed* roles (recruiter, hiring manager, recruiting-ops lead, system); the data contains no permission information. People.Role holds Recruiter, Interviewer and Hiring Manager, which shows job roles, not permissions.
- **Blocks:** B1 permission configuration and pilot release (DEC-032, ASM-031).
- **Ask:** who may record acceptances and declines, who may rescind an offer, and who may correct a record?

### C-18. Does Acme privacy/legal approve the proposed small-cell suppression policy?
- **Who to ask:** Acme privacy/legal, plus TalentFlow privacy.
- **Evidence:** breakdowns such as "Sales: 3 of 3 accepted" reveal individual decisions to aggregate-only viewers. The proposed default k = 5 is a policy proposal, not a known regulatory requirement.
- **Blocks:** release of breakdowns to aggregate-only viewers (D3 §3.14, DEC-034, ASM-028).
