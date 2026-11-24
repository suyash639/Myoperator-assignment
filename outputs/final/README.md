# TalentFlow Q3 Product Exercise: Final Submission

**Customer:** Acme Corp.

**Status:** the analysis is final. Most product decisions are **proposals awaiting PM approval** (see `Decision_and_Assumption_Register.md`). Effort figures are **PM planning estimates**.

## 1. What this folder contains
| File | Purpose | Assignment deliverable |
|---|---|---|
| `Executive_Product_Memo.md` (PDF in `pdf/`) | One-page executive memo | D5 |
| `Q3_Product_Roadmap.md` (PDF in `pdf/`) | 3 builds, 3 non-builds, 6.0 engineer-week allocation, delivery plan | D2 |
| `Metrics_Specification.md` (PDF in `pdf/`) | Offer acceptance specification and Q3 success metrics | D3 |
| `Findings_and_Data_Audit.csv` | 21 decision-relevant findings with exact values and sources | D1 + D4 summary, findings table |
| `Decision_and_Assumption_Register.md` | Approved vs proposed decisions, readiness, assumptions | Decision trail |
| `Customer_Validation_Plan.md` | Acme questions by priority | Validation |
| `Claude_Code_Transcript.md` | **Reconstructed** session summary (not verbatim) | Session transcript |
| `Final_Submission_QA.md` | QA checklist with results | QA |
| `README.md` | This file: reproducibility and source index | Reproducible code |

**Full D4 data-quality audit (29 issues):** `../data_quality_audit.md` and `../dq_issues.csv`. The insights appendix (funnel, channel quality, cycle time, declines, interviews) is `../phase2_summary.md` §4–5.

## 2. How the data was obtained
- **One read-only extraction**, run on 2026-11-24 from the assignment's Airtable base (ID kept in the local `.env`, not published): 8 tables, 892 records.
- The client is **GET-only by construction** (`src/airtable_client.py` refuses any other HTTP method).
- **Pagination and limits:** it follows `offset` pagination, limits itself to 4 requests per second, waits 30 seconds on HTTP 429, and fails fast on 401, 403 and 404.
- **Storage:** the untouched responses are stored in `data/raw/`, with SHA-256 checksums in `data/raw/manifest.json`.

**Why read-only:** the base is the customer's system of record. The assignment and the PM required no writes. All analysis therefore runs on the local cached snapshot, and no further API calls were made after the extraction.

**Analysis:**
- Plain Python (`src/`), independently re-derived in DuckDB SQL (`queries/verify_phase2.sql`).
- `src/data.py` refuses to load if any raw checksum differs from the manifest.
- Raw files are read-only on disk.

## 3. Reproduce (no network access needed)
```bash
uv sync                                   # Python 3.11 + pinned dependencies (uv.lock)
uv run python -m src.validate_extraction  # offline completeness checks on data/raw
uv run python -m src.run_phase2           # Phase 2.2 outputs; verifies raw checksums before and after
uv run python -m src.verify_sql           # DuckDB re-derivation; fails on any mismatch (54 checkpoints)
uv run python -m src.review_phase2_1      # independent review checks
uv run python -m src.offer_metrics        # D3 event-time reference implementation -> outputs/offer_metric_baseline.csv
uv run python -m src.phase3_plan          # scores, allocation, success metrics, traceability
uv run python -m src.phase3_1_evidence    # lifecycle, inactivity and duplicate rules applied to the snapshot
uv run python -m src.phase3_checks        # programmatic QC of Phase 3 documents
uv run python -m src.final_package        # builds the findings CSV and generated tables in outputs/final/
uv run python -m src.render_pdf           # PDFs of memo, roadmap, metrics spec -> outputs/final/pdf/ (local headless Chrome)
uv run python -m src.final_qa             # runs every final check (incl. pytest, SQL, integrity) -> Final_Submission_QA.md
uv run pytest                             # full test suite (offline)
```
**Do not run `src.extract`.** It is the only command that calls Airtable, and it needs credentials in `.env`. The snapshot it produced is already cached.

## 4. Where the main results live (source index)
| Final document section | Underlying evidence | Produced by |
|---|---|---|
| Memo and roadmap: Claim A numbers | `../metric_calculations.csv` (M-A0 to M-A10, M-A5, M-A7*, M-Q2-*); `../verification.csv` | `src/metrics.py`; `queries/verify_phase2.sql` |
| Memo and roadmap: Claim B numbers | `../offer_metric_baseline.csv` (OAM-*); `../metric_calculations.csv` (M-B*) | `src/offer_metrics.py`; `src/metrics.py` |
| Data-quality findings | `../dq_issues.csv` (DQ-01 to DQ-29); `../data_quality_audit.md` | `src/audit.py` |
| Date-check and attribution detail | `../phase2_1_checks.csv` | `src/review_phase2_1.py` |
| B1, B2, B3 rule verification | `../phase3_1_evidence.csv` | `src/phase3_1_evidence.py`, `src/offer_lifecycle.py`, `src/inactivity.py`, `src/duplicate_warning.py` |
| Allocation, scores, success metrics | `../phase3_capacity_allocation.csv`, `../phase3_prioritisation_scores.csv`, `../product_success_metrics.csv` | `src/phase3_plan.py` |
| Traceability | `../decision_traceability.csv` (Phase 2), `../phase3_decision_traceability.csv` (Phase 3) | `src/traceability.py`, `src/phase3_plan.py` |
| Full strategy reasoning | `../phase3_product_strategy.md`, `../q3_roadmap.md`, `../offer_acceptance_metric_spec.md` | — |
| Corrections history | Summarised in `Claude_Code_Transcript.md` and `../../audit/investigation_log.md` (INV-008 to INV-012); the intermediate review reports are archived locally and not part of the submission | — |
| Decisions and assumptions | `../../audit/decision_log.md`, `../../audit/assumptions_register.md`, `../../audit/investigation_log.md` | — |
| Tests | `../../tests/` (6 files) | `uv run pytest` |

## 5. Privacy and credential handling
- **Credentials:** read only from `.env`, which is git-ignored and file mode 600. They are never printed, logged or written to outputs. Logs pass through a redaction filter, and no token, token fingerprint or token metadata appears in any published file.
- **Customer records:** `data/raw/`, `logs/` and `outputs/private/` are git-ignored. Shareable outputs contain aggregates, record IDs and business IDs only.
- **Personal fields** (names, emails, phones, notes, feedback) are suppressed. A test fails if any appears in `outputs/*.csv|md`, and the final QA repeats that scan on this folder.
- **Git:** local only. No remote, nothing pushed, nothing committed.

## 6. Known limitations
1. **One customer, one snapshot.** The business cutoff is unconfirmed (extraction 2026-11-24; apparent import 2026-08-27). Acme-only scope is unverified (C-14). The data may be a prepared sample (C-16).
2. **Small numbers.** 26 hires, 31 decided offers, 5 declines. Rates are shown with single-record sensitivity, not sampling intervals.
3. **No ground truth where fields conflict** (Source vs Referred By; Pending offers with decision dates; copied vs source dates).
4. **Unmeasurable today:** integration friction, feedback latency, post-acceptance reneging and rescission, and expiry adherence.
5. **Effort figures are PM planning estimates,** not engineering estimates.

## 7. Provisional decisions
- **Approved:** DEC-001 to DEC-009 (except DEC-006, which is analyst process), DEC-012, DEC-013, DEC-016 to DEC-021, DEC-023 and DEC-038.
- **Proposals awaiting PM approval:** DEC-011, DEC-022 and DEC-025 to DEC-037. Readiness for each is in the register.
