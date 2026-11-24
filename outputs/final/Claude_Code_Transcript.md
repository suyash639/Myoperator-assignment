# Claude Code Session: Reconstructed Summary

> **This is a reconstructed session summary, not a verbatim transcript.**
>
> **The raw log:** the complete raw Claude Code session log exists locally at `~/.claude/projects/<project>/3513ab50-….jsonl`. It has 2,078 log lines, timestamped 2026-11-24 06:34 to 10:15 UTC. It is **deliberately not included**, because raw session logs can contain record-level customer data read during analysis.
>
> **What this summary is based on:**
> - the session's own work products;
> - the append-only `audit/investigation_log.md` (INV-000 to INV-012);
> - the decision log;
> - for the early phases, the summary carried forward when the session context was compacted.
>
> **Commands:** they are quoted only where they are recorded in the README or the investigation log.

## Phase 0: Setup (INV-000, INV-001)
**Actions:**
- Inspected an empty scaffold. `.env` was checked for key names and value lengths only.
- Found that `.gitignore` was empty, a credential-leak risk.
- Populated `.gitignore` *before* `git init` (DEC-001).
- Set up local git only, with no remote (DEC-002).
- Pinned the uv environment on Python 3.11 (DEC-003).
- Added a local pre-commit hook that blocks `.env`, raw data and token-shaped strings (DEC-006).

**Error found and fixed:** the hook's first test produced a false positive, because a 1-character dummy token matched git diff header text. The match was restricted to added lines and tokens of 20+ characters; 5/5 hook tests then passed.

## Phase 1: Secure read-only extraction (INV-002 to INV-004)
**Client:**
- Built a GET-only Airtable client: rate-limited to 4 requests per second; 30-second wait on 429; bounded retries; fail-fast on 401, 403 and 404; table restart on an expired pagination iterator; token redaction in logs and errors.
- 28 offline tests (fake transport) passed.

**Errors found and fixed:**
- A backoff test assertion confused rate-limiter sleeps with backoff sleeps. This was a test artefact.
- Schema discovery would have re-run on every rerun.

**Extraction:** after PM approval and the PM's decision to use the original token (DEC-009), one live run: `uv run python -m src.extract`, then `uv run python -m src.validate_extraction`.
- 8/8 tables, 892 records, 16 HTTP requests, 0 retries.
- 72/72 validator checks passed.
- The schema endpoint returned 403 (types inferred from values).
- The Findings table was empty.

## Phase 2: Profiling, integrity, data quality, VP claims (INV-005 to INV-007)
**Work done:**
- Profiled 80 fields.
- Checked 11 relationships: all pass, 0 orphans.
- Logged 25 data-quality issues.
- Computed 116 metrics.
- Re-derived 36 checkpoints in DuckDB: all matched.
- Reproduced both VP figures and found them definition-dependent.

**Errors caught before reporting (INV-007):**
- A typed-by-hand DQ-05 description was wrong.
- A DQ-20 count was asserted, not computed.
- The table profile would have exposed 16 personal names and emails. These were suppressed, and a leak test was added.
- The Claim A range was stale after a new variant.
- "-0.0%" was printed, and medians on empty lists crashed.
- Some interpretations were overstated and were softened.

## Phase 2.1: Independent review of my own work (INV-008)
- **Method:** a separate script (`src/review_phase2_1.py`) re-derived evidence without the Phase 2 modules.
- **Result:** 19 review issues.
- **Two factual errors in my Phase 2 text:**
  - Engineering had 30 applications, not the "20" I had typed.
  - A DQ-13 "0 violations" sentence had never been computed.
- **Analytical problems:**
  - The decision to treat source tables as authoritative (DEC-015) was contradicted by the data.
  - The Referral comparison was overstated (7/7 Referral hires unlinked).
  - Wilson intervals were inappropriate for a presumed-complete snapshot.

## Phase 2.2: Approved corrections and governance (INV-009)
**PM decisions applied:** decided-offer acceptance 26/31 as the provisional primary; "Source as recorded" as primary attribution; Wilson intervals removed; dual date sources; extraction vs import dates; a completed cohort only after a sufficiency check.

**Changes:**
- DQ-13 rebuilt from computed checks.
- New issues DQ-26 to DQ-29.
- Every typed-by-hand detail replaced with computed text.
- Decision log restructured, with approval type and alternatives, and all IDs preserved.
- ASM-011 to ASM-021 registered.

**Verification:**
- SQL verification extended to 54 checkpoints.
- A test now checks every fraction in the reports against the CSVs.
- Tests: 59 passed.
- Headline numbers unchanged.

## Phase 3: Product strategy (INV-010)
- **D3 reference implementation:** `src/offer_metrics.py`.
- **Prioritisation:** scored and allocated as data (`src/phase3_plan.py`).
- **Programmatic checker:** `src/phase3_checks.py`, including mutation tests.
- **Builds:** B1 2.5, B2 2.0, B3 1.5 = 6.0 engineer-weeks (PM planning estimates).
- **Non-builds:** N1 (job boards, deferred), N2 and N3.
- **Robustness:** the top three were stable under three weighting schemes.
- **Bug fixed:** the reference code crashed on an empty as-of window.
- **Tests:** 66 passed.

## Phase 3.1: Focused correction pass (INV-011)
**Reference models:**
- the B1 offer lifecycle (`src/offer_lifecycle.py`: transitions, roles, invariants, audit events, corrections);
- the B3 source taxonomy, referral rules and **warning-only** duplicates (`src/duplicate_warning.py`).

**Applied to the snapshot:** the invariants flag exactly the 4 conflicting offers; the duplicate warning fires on exactly the 6 known pairs; the default inactivity threshold reproduces 50/105.

**Bug fixed:** offers decided after the as-of date had dropped out of both the decided and pending counts. Snapshot impact was zero.

**Rule changes:**
- Reliability tiers separated from privacy suppression.
- B3.3 split so the duplicate warning is a self-contained 0.5 first cut.

**Checker catch:** a new "merge must be qualified" rule caught two ambiguous lines.

**Tests:** 103 passed.

## Phase 3.2: Final clarifications (INV-012)
- **Event time (DEC-038, PM-approved):** offer metrics are now computed at event time from offer events. A renege or company rescission no longer erases the acceptance. OAM-13a and OAM-13b measure post-acceptance withdrawal and rescission.
- **Privacy:** made a configurable *proposed* policy pending Acme privacy/legal approval (C-18).
- **Roles:** kept as proposals; the Acme mapping is an open dependency (C-17).
- **Inactivity:** made configurable per stage, with a provisional 90-day default.
- **Decision status:** DEC-025 to DEC-037 kept as proposals, with a readiness table.
- **Tests:** 120 passed. Every existing metric value was unchanged.

## Phase 4: Final packaging and QA (this phase)
**Final package:** `outputs/final/`.
- **Generated, not typed:** the findings CSV and every generated table in the final documents come from the validated CSVs and logs (`src/final_package.py`).
- **Phase 4 itself was interrupted by a usage limit.** PDFs and the automated QA were completed in Phase 4.1.

## Phase 4.1: QA completion
- **PDFs:** rendered with a dependency-free Markdown renderer and local headless Chrome (`src/render_pdf.py`). The memo's first render was 2 pages; its spacing was tightened to fit one page.
- **QA:** `src/final_qa.py` runs 16 checks and writes `Final_Submission_QA.md`.
  - **Its first runs** reported 4 false positives in its own rules: a self-match, a Phase 1 tally kept in the log, a quoted .gitignore pattern, and the report's own "Bearer" wording. Each rule was tightened and documented.
  - **A self-test** planted a wrong fraction, a wrong effort figure and a fake email; all three were caught, then the files were restored.
- **Fixes:** two genuine inconsistencies (build naming in the scores table; B1.3 metric range) and 2 empty CSV caveats were fixed.

**No new analysis, scope or decisions** were introduced. No Airtable calls, commits or pushes were made at any point after the single Phase 1 extraction.
