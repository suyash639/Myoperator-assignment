# Investigation Log

Chronological, append-only record of questions investigated, the queries and calculations run,
what was found, and how it was independently verified. Each entry references the script or
query file that reproduces it.

Entry format:

```
## INV-NNN — <question>  (YYYY-MM-DD, phase N)
Why it matters:   <business decision it informs>
Method:           <script / query path, definitions used>
Result:           <numbers, with denominators>
Verification:     <independent method + match/mismatch>
Classification:   fact | hypothesis | assumption
Limitations:      <what could make this wrong>
Next:             <follow-up investigation>
```

---

## INV-000 — Environment inspection  (2026-11-24, phase 0)
Why it matters:   Reproducibility and credential safety before any customer data is touched.
Method:           Manual inspection of project directory; `.env` inspected for key names and value
                  lengths only (values never printed).
Result:           Empty scaffold (src/, queries/, data/raw, data/processed, outputs/, logs/).
                  `.env` defines AIRTABLE_BASE_ID (length and prefix checked locally) and AIRTABLE_TOKEN
                  (length and prefix checked locally). `.gitignore` was empty (0 bytes) — credential-leak risk.
                  Not a git repository. System Python 3.9.6; uv 0.12.10 available.
Verification:     n/a (environment facts).
Classification:   fact
Limitations:      Token scopes (e.g. schema.bases:read) unknown until Phase 1.
Next:             Phase 0 setup (see DEC-001..DEC-006).

## INV-001 — Does the pre-commit secret guard work?  (2026-11-24, phase 0)
Why it matters:   Defence-in-depth against committing credentials or customer data (DEC-006).
Method:           Throwaway repo in session scratchpad; staged (1) PAT-shaped string, (2) force-added
                  `.env`, (3) force-added `data/raw/*.json`, (4) the configured token value, (5) a clean file.
Result:           First run: tests 1–3 blocked correctly; clean-file test FAILED (false positive).
                  Cause: test used a 1-char dummy token (`x`), which matched git diff header text.
                  Fix: compare configured token only if length ≥ 20 and only against added (`+`) lines.
                  Re-run: 5/5 pass.
Verification:     Re-run of full suite after patch; throwaway repo deleted.
Classification:   fact
Limitations:      Hook is local (`.git/hooks`), not versioned; a fresh clone does not inherit it.
Next:             Phase 1.

## INV-002 — Phase 1 extraction client: build and offline verification  (2026-11-24, phase 1)
Why it matters:   Every downstream metric depends on a complete, untouched snapshot.
Method:           `src/airtable_client.py`, `src/extract.py`, `src/validate_extraction.py`;
                  `tests/test_airtable_client.py` (28 offline tests, FakeSession, injected sleep/clock).
Result:           28/28 pass. Covered: multi-page pagination (incl. exactly-100 boundary), empty
                  table, repeated offset, malformed page, expired iterator → table restart, 429 → 30 s
                  wait + bounded retries, 5xx backoff, transient + persistent network failure, 401/403
                  fail-fast, missing env vars, bad base ID (value not echoed), token redaction in
                  repr/errors/logs/exceptions, non-GET refused, ≤4 req/s spacing, end-to-end
                  extract+validate, failed-table-only retry, skip-on-rerun, schema-unavailable path,
                  tamper detection, preflight 401 abort.
                  One test failed on first run (backoff assertion) — a test artefact: the frozen fake clock
                  makes the rate limiter's 0.25 s spacing sleeps interleave with backoff sleeps. Client
                  behaviour was correct; the assertion now isolates backoff sleeps.
                  Code fix during review: schema discovery would have been re-requested on every rerun;
                  now fetched only if not already cached (or --force).
Verification:     Static grep: the only network call in src/ is `session.request("GET", …)`; no
                  PAT-shaped strings in src/ or tests/; real token value present in no file except `.env`.
                  `--dry-run` confirmed config and plan with zero network calls.
Classification:   fact
Limitations:      Tests use a fake transport; real Airtable behaviour (e.g. exact 429 payload, schema
                  scope) is only observed on the live run. Whether the token is the *rotated* one cannot
                  be determined locally (see INV-003).
Next:             PM approval → single live extraction.

## INV-003 — Is the configured token the newly rotated read-only token?  (2026-11-24, phase 1)
Why it matters:   PM indicated a previous token was exposed; using it would be a security failure.
Method:           Local inspection only (no API call): format, fingerprint, .env modification time.
Result:           Token is well-formed (PAT format, no whitespace/quotes); fingerprint (recorded locally only);
                  `.env` last modified 2026-11-24T06:33:18Z, i.e. before this session began, and unchanged since.
                  Base ID matches the PM-supplied <AIRTABLE_BASE_ID>.
Verification:     —
Classification:   fact (format/fingerprint/mtime); **unverified** (rotation status)
Limitations:      Rotation cannot be proven locally — the analyst has never seen the old token. The
                  preflight `whoami` call will show the token's scopes (read-only vs write) but cannot
                  distinguish old from new. Only the PM can confirm by (a) comparing the fingerprint with
                  the new token, and/or (b) confirming the old token is revoked in Airtable.
Next:             PM confirmation before the live run.

## INV-004 — Live extraction of base <AIRTABLE_BASE_ID>  (2026-11-24, phase 1)
Why it matters:   Establishes the single snapshot all later analysis reads from.
Method:           Pre-checks: `load_config` (both vars present, base ID matches assignment, token
                  fingerprint (recorded locally only)), 28/28 offline tests, data/raw empty. Then one run of
                  `uv run python -m src.extract` (log: logs/extraction_20261124T065922Z.log), then
                  `uv run python -m src.validate_extraction`.
Result:           8/8 tables success, 892 records, 14 pages, 16 HTTP requests (2 meta + 14 pages),
                  0 retries, 0 table restarts, exit 0. Departments 8 · People 14 · Job Openings 24 ·
                  Candidates 300 (3 pp) · Applications 350 (4 pp) · Interviews 160 (2 pp) · Offers 36 ·
                  Findings 0. Validator C1–C9: 72/72 PASS.
                  Warnings: (a) schema endpoint HTTP 403 → schema unavailable (documented, not a failure);
                  (b) whoami returned HTTP 200 but no `scopes` list → token scope set (read vs write) not
                  confirmable via API; client is GET-only regardless; (c) Findings table is empty
                  (HTTP 200, `[{"records":[]}]`) — an access problem would have returned 403/404;
                  (d) Candidates = exactly 300 = 3 full pages; Airtable omitted `offset` on page 3, which is
                  the termination signal.
Verification:     Independent of Python: `jq` record/page recount and `shasum -a 256` match manifest for
                  all 8 files; last page of every file has no `offset`; no `.tmp` leftovers; token value
                  and PAT/Bearer patterns found in 0 files under data/, logs/, src/, tests/, audit/;
                  git shows all raw files, manifest and log as ignored; 0 remotes, 0 commits.
Classification:   fact
Limitations:      Completeness is proven relative to what the API returned. Independent evidence of no
                  missing records (esp. the 300 boundary) comes in Phase 2 via referential-integrity checks
                  (links pointing to record IDs absent from the snapshot).
Next:             Phase 2 data-quality audit, on PM approval.

## INV-005 — Phase 2 profiling, integrity and data-quality audit  (2026-11-24, phase 2)
Why it matters:   Both VP claims and every roadmap argument rest on field reliability.
Method:           Exploratory passes over data/raw (read-only), then codified in src/profile.py, src/integrity.py,
                  src/audit.py. Orchestrated by `uv run python -m src.run_phase2`.
Result:           80 fields profiled; 0 blank strings; every missing value explained by record state. 11/11 linked
                  relationships PASS (0 orphans, 0 asymmetric, 0 cardinality violations); no referenced candidate missing,
                  which independently confirms the 300-record page boundary. 25 issues logged (DQ-01..DQ-25): 3 Critical,
                  5 High. Detail in outputs/data_quality_audit.md.
Verification:     DuckDB SQL over the raw JSON (queries/verify_phase2.sql) re-derives the DQ-01/02/03/04/06/07/15/16/18/25
                  counts and the orphan total. All match.
Classification:   fact (counts); interpretation where marked in the audit document
Limitations:      No schema; no ground truth for conflicting fields; small n.
Next:             VP claim verification (INV-006).

## INV-006 — VP claims A (26.9% job boards) and B (~72% acceptance)  (2026-11-24, phase 2)
Why it matters:   D1 verdicts; the job-board integration priority.
Method:           src/metrics.py; definitions fixed before computing (DEC-007, DEC-011); alternative definitions as
                  `variant_of` rows; Wilson 95% intervals.
Result:           A: 7/26 = 26.9% reproduced exactly (Source as recorded). Range 23.1% (Referred By override) to 30.8%
                  (duplicates merged, first-touch). Referral is also 26.9% from 3.7% of applications. Job Board hire rate
                  per application 3.0% (lowest of any channel with hires). Verdict: figure supported, prioritisation inference not.
                  B: 26/36 = 72.2% reproduced only with Pending in the denominator; decided 26/31 = 83.9% (CI 67.4–92.9%).
                  4/5 Pending carry a decision date. Verdict: figure is a definition artefact; "needs improvement"
                  is not judgeable from the data.
Verification:     36/36 SQL checkpoints match (outputs/verification.csv); regression test pins the headline values.
Classification:   fact (values); interpretation (verdicts)
Limitations:      n=26 hires, 31 decided offers; attribution conflict unresolved (Q1).
Next:             Phase 3 (PM approval).

## INV-007 — QC corrections made during Phase 2  (2026-11-24, phase 2)
Why it matters:   Auditability; errors caught before reporting.
Result:           (1) DQ-05 description written by hand claimed "reapplied after rejection 9 days later"; the records show the
                  second application was submitted while the first was still open (concurrent). Replaced with text computed
                  from the records. (2) DQ-20 detail asserted an uncomputed count; replaced with a computed one.
                  (3) Profile would have written 16 staff/candidate names and emails into table_profiles.csv (People has
                  ≤30 distinct values); PII fields now suppressed; a mutation check confirmed the leak test fails without it.
                  (4) Claim A range was stale after adding the M-A8 variant; it is now computed across all variants. (5) Wilson
                  bound printed "-0.0%"; clamped. (6) Empty-list medians would crash on sparse data; guarded.
                  (7) Summary text: "±16pp" corrected to the asymmetric interval; decline-by-level range qualified.
                  (8) Overstated interpretations softened ("acceptance is not low" → not judgeable without a benchmark).
Verification:     Every x/y fraction in both markdown reports is traced to a computed output (2 exceptions are
                  verification tallies: 36/36, 72/72).
Classification:   fact

## INV-008 — Phase 2.1 independent review of Phase 2  (2026-11-24, phase 2.1)
Why it matters:   Phase 2 outputs feed D1–D5; errors must be found before Phase 3.
Method:           Read all Phase 2 outputs, logs, README. Re-derived evidence with src/review_phase2_1.py
                  (independent of src/metrics.py and src/audit.py) → outputs/phase2_1_checks.csv.
Result:           19 review issues (RV-01..RV-19; 5 High). Two factual errors in Phase 2 reports: Engineering
                  applications 20 → actually 30 (RV-01); DQ-13 "0 violations" sentence was never computed and is false
                  on source tables (RV-02). DEC-015 contradicted: copied date fields are sequence-consistent where source
                  tables are not in 12/16 disagreements (RV-03). All 7 Referral-labelled hires lack a referrer link
                  (RV-04). Headline numbers (26.9%, 72.2%, 83.9%, funnel, 26/5/5) re-derived and unchanged.
                  Outputs: phase2_1_review.md, decision_traceability.csv, open_questions_for_customer.md,
                  assignment_completeness.md. No Phase 2 report or CSV modified; corrections P1–P13 proposed only.
Verification:     Independent re-implementation; raw SHA-256 identical before/after; pytest run.
Classification:   fact (counts); interpretation where marked
Limitations:      Review script is itself single-implementation for the new checks (R1–R10).
Next:             PM approval of corrections and decisions 1–7.

## INV-009 — Phase 2.2 approved corrections and decision governance  (2026-11-24, phase 2.2)
Why it matters:   PM decisions 1–7 on the Phase 2.1 review; corrected Phase 2 outputs feed Phase 3.
Method:           Classified P1–P13 (outputs/phase2_2_correction_report.md). Code changes in src/data.py (snapshot dates),
                  src/metrics.py (levels, single-record sensitivity, no Wilson intervals, attribution variants M-A9/M-A10/
                  M-A7s/m/f, offer variants M-B3-cutoffs/M-B9/M-B10, department funnel M-DF, completed cohort M-K, dual-source
                  stage lags), src/audit.py (DQ-13 rebuilt from computed checks; DQ-15 treatment; computed text replacing
                  hand-typed claims in DQ-02/03/04/06/09/16/24/25; DQ-26..DQ-29), src/traceability.py, queries/verify_phase2.sql.
                  Logs: decision log restructured (approval type, alternatives, evidence; DEC-016..DEC-024; REJ-010, REJ-011;
                  IDs preserved); ASM-011..ASM-021 registered.
Result:           182 metrics, 29 DQ issues, 38 traceability rows with 0 dangling references. Headline values unchanged:
                  26.9% (7/26) Source as recorded; 83.9% (26/31) decided offer-level; 72.2% (26/36) all-issued ratio.
                  Corrected: Engineering 0 hires from 30 applications (was "20"); DQ-13 "0 violations" sentence replaced by 16
                  computed checks; DQ-14 lists all 90 IDs. Completed cohort 2025-07..2026-03: 134 eligible, 16 offers, 12 hires.
Verification:     DuckDB 54/54 match (was 36); Phase 2.1 independent checks agree on every corrected number; pytest 59/59;
                  outputs byte-identical across two runs; raw SHA-256 unchanged.
Classification:   fact (counts); interpretation where marked
Limitations:      Cohort sufficiency thresholds and the 90-day stall rule are analyst choices (DEC-022, ASM-021).
Next:             PM approval → Phase 3.

## INV-010 — Phase 3 product strategy, roadmap and D3 specification  (2026-11-24, phase 3)
Why it matters:   D1–D3 decisions and the 6 engineer-week Q3 allocation.
Method:           Read Phase 2.2 outputs, logs and customer questions. D3 reference implementation src/offer_metrics.py
                  (independent of src/metrics.py). Scoring, allocation, scorecard and traceability as data in
                  src/phase3_plan.py; programmatic QC in src/phase3_checks.py; tests/test_phase3.py (7 tests, incl. 2
                  mutation tests showing the checker catches a wrong effort total, a fourth build and an untraceable number).
Result:           Builds B1 (2.5), B2 (2.0), B3 (1.5) = 6.0 planning engineer-weeks; non-builds N1 (defer), N2, N3.
                  Top three stable under weighted, equal-weight and no-effort scoring. OAM-01 26/31, OAM-02 26/36, OAM-09 24/28,
                  OAM-01b 24/28 reconcile with M-B1, M-B0, M-B4, M-B10. Decisions logged DEC-025..DEC-031 (Proposed);
                  assumptions ASM-022..ASM-026.
Verification:     phase3_checks PASS; pytest 66/66; DuckDB 54/54; Phase 2 outputs byte-identical before/after; raw SHA-256 unchanged.
Classification:   decisions = proposals (interpretation); baselines = fact
Limitations:      Effort is unvalidated by engineering; baselines come from a ~3-month-old single-customer snapshot.
Next:             PM approval of DEC-025..DEC-031; engineering estimate validation; P1 customer questions.

## INV-011 — Phase 3.1 focused review of B1, B2, B3, D3 and estimation  (2026-11-24, phase 3.1)
Why it matters:   Make the Phase 3 builds and D3 precise enough to implement and audit, without changing the plan.
Method:           Executable reference models src/offer_lifecycle.py and src/duplicate_warning.py; rules applied read-only to the
                  snapshot by src/phase3_1_evidence.py; D3 reference updated; checker extended; tests/test_phase3_1.py (37 tests).
Result:           Builds, non-builds, 6.0 total and per-build totals unchanged (B3.3 split into B3.3a/B3.3b). Lifecycle invariants flag
                  exactly the 4 DQ-06 offers; default inactivity threshold reproduces DQ-28 (50/105); opening flags reproduce DQ-11;
                  duplicate warning fires on exactly the 6 DQ-02 groups. Found and fixed an as-of inconsistency in the D3 reference
                  (decided-after-as-of offers dropped from both decided and pending), with 0 snapshot impact. Reliability tiers and
                  privacy suppression separated. Decisions DEC-032..DEC-037 (Proposed); assumptions ASM-027..ASM-030.
Verification:     pytest 103/103; phase3_checks PASS; DuckDB 54/54; Phase 2 outputs byte-identical; raw SHA-256 unchanged.
Classification:   rules = proposals; evidence counts = fact
Limitations:      Reference models are specifications, not product code; role names and privacy threshold need confirmation.
Next:             PM approval; engineering validation; Phase 4 only on instruction.

## INV-012 — Phase 3.2 final clarifications  (2026-11-24, phase 3.2)
Why it matters:   Renege treatment, privacy, permissions, inactivity and decision status settled before Phase 4.
Method:           Event-time engine in src/offer_metrics.py (legacy records converted to synthesised events); src/inactivity.py;
                  spec, validation plan and logs updated; tests/test_phase3_2.py (17 tests).
Result:           All existing OAM values unchanged; OAM-13a/13b/06x defined (not measurable on legacy data). DEC-038 PM-approved.
                  DEC-025..DEC-037 remain Proposed, with a readiness table. C-17 (role mapping) and C-18 (privacy approval) added.
                  Per-stage inactivity default reproduces DQ-28.
Verification:     pytest 120/120; phase3_checks PASS; DuckDB 54/54; Phase 2.2 outputs byte-identical; raw SHA-256 unchanged.
Classification:   fact (counts); decisions as labelled
Next:             PM approvals per decision_log.md §G; Phase 4 only on instruction.
