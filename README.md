# Myoperator-assignment: TalentFlow Q3 Product Exercise (Acme Corp)

Evidence-backed answer to the TalentFlow Q3 product exercise:
- verification of two VP claims (job-board share of hires; offer acceptance);
- a data-quality audit;
- an offer-acceptance metric specification;
- a 6-engineer-week Q3 roadmap (3 builds, 3 non-builds).

**Start here:** [`outputs/final/Executive_Product_Memo.md`](outputs/final/Executive_Product_Memo.md) ([PDF](outputs/final/pdf/Executive_Product_Memo.pdf)).

## Final deliverables (`outputs/final/`)
| File | What it is |
|---|---|
| [`Executive_Product_Memo.md`](outputs/final/Executive_Product_Memo.md) · [PDF](outputs/final/pdf/Executive_Product_Memo.pdf) | One-page executive memo |
| [`Q3_Product_Roadmap.md`](outputs/final/Q3_Product_Roadmap.md) · [PDF](outputs/final/pdf/Q3_Product_Roadmap.pdf) | 3 builds (6.0 engineer-weeks, PM planning estimates), 3 non-builds, delivery plan |
| [`Metrics_Specification.md`](outputs/final/Metrics_Specification.md) · [PDF](outputs/final/pdf/Metrics_Specification.pdf) | Offer-acceptance metric specification (event-time) and success metrics |
| [`Findings_and_Data_Audit.csv`](outputs/final/Findings_and_Data_Audit.csv) | 21 decision-relevant findings, each value traced to a source ID |
| [`Decision_and_Assumption_Register.md`](outputs/final/Decision_and_Assumption_Register.md) | Approved vs proposed decisions, assumptions, open dependencies |
| [`Customer_Validation_Plan.md`](outputs/final/Customer_Validation_Plan.md) | Questions for Acme, by priority |
| [`Final_Submission_QA.md`](outputs/final/Final_Submission_QA.md) | QA checklist with executed results |
| [`Claude_Code_Transcript.md`](outputs/final/Claude_Code_Transcript.md) | Reconstructed (not verbatim) session summary |
| [`README.md`](outputs/final/README.md) | Detailed reproducibility notes and source index |

## Repository structure
| Path | Contents |
|---|---|
| `src/` | Read-only Airtable extraction client; analysis, metric and audit code; reference models (offer lifecycle, duplicate warning, inactivity); QA and PDF scripts |
| `queries/` | DuckDB SQL used to re-derive headline numbers independently |
| `tests/` | pytest suite (offline) |
| `outputs/` | Phase 2–3 evidence (aggregate CSVs and reports) |
| `outputs/final/` | Final submission |
| `audit/` | Investigation log, decision log, assumptions register |
| `data/raw/`, `data/processed/`, `logs/`, `outputs/private/` | **Empty placeholders.** Customer data and logs are never published |

## Code map (`src/`)
| Stage | Modules |
|---|---|
| 1. Extraction (read-only, the only network step) | `airtable_client.py`, `extract.py`, `validate_extraction.py` |
| 2. Analysis and data quality | `data.py` (checksum-verified loader), `profile.py`, `integrity.py`, `audit.py`, `metrics.py`, `run_phase2.py`, `verify_sql.py` (+ `queries/verify_phase2.sql`), `review_phase2_1.py`, `traceability.py` |
| 3. Product decisions and metric spec | `offer_metrics.py` (event-time D3 metrics), `offer_lifecycle.py`, `duplicate_warning.py`, `inactivity.py` (reference models), `phase3_plan.py`, `phase3_1_evidence.py`, `phase3_checks.py` |
| 4. Packaging and QA | `final_package.py`, `render_pdf.py`, `final_qa.py`, `build_submission.py` |

## Supporting evidence (`outputs/`)
| File | Role |
|---|---|
| `data_quality_audit.md` | Full D4 data-quality audit (29 issues) |
| `phase2_summary.md` | Claim verification and insights appendix |
| `phase3_product_strategy.md`, `q3_roadmap.md` | Full prioritisation rationale and sprint plan behind the final roadmap |
| `offer_acceptance_metric_spec.md` | Authoritative offer-metric specification (lifecycle rules, edge cases) |
| `open_questions_for_customer.md` | All customer questions with evidence |
| `*.csv` | Machine-readable evidence every number traces to |

## Setup
```bash
uv sync                    # Python 3.11, pinned dependencies from uv.lock (or: pip install -r requirements.txt)
uv run pytest              # offline tests; tests that need the Airtable snapshot are skipped when data/raw is empty
uv run python -m src.phase3_checks
```

## Reproducing the numbers
The customer snapshot is **not** included. To reproduce the metrics you need read access to the assignment's Airtable base:
```bash
cp .env.example .env       # then set AIRTABLE_TOKEN and AIRTABLE_BASE_ID locally (never commit .env)
uv run python -m src.extract              # the ONLY network step: read-only, GET-only Airtable extraction into data/raw/
uv run python -m src.validate_extraction  # offline completeness checks
uv run python -m src.run_phase2           # Phase 2.2 metrics and data-quality audit (verifies raw checksums)
uv run python -m src.verify_sql           # DuckDB re-derivation (fails on any mismatch)
uv run python -m src.offer_metrics        # D3 event-time offer metrics
uv run python -m src.phase3_plan && uv run python -m src.phase3_1_evidence
uv run python -m src.final_package && uv run python -m src.render_pdf && uv run python -m src.final_qa
uv run pytest
```
A fresh extraction reflects the base at the time you run it, so counts may differ from the snapshot analysed here (extracted 2026-11-24).

## Privacy and security
- No credentials, `.env`, raw Airtable responses, logs or session transcripts are included; `.gitignore` excludes them.
- **Redactions in this public copy:**
  - the Airtable base ID, the token fingerprint and token length/prefix metadata are replaced in text files;
  - the local audit trail keeps the originals.
- **What is and isn't included:**
  - Outputs contain aggregates, Airtable record IDs and business IDs (e.g. `CAND-00015`) only.
  - Names, emails, phone numbers and free-text notes are suppressed and scanned for.

## Limitations
- One customer snapshot. The business reporting cutoff is unconfirmed (extraction 2026-11-24; apparent import 2026-08-27).
- Small numbers: 26 hires, 31 decided offers, 5 declines.
- No ground truth where fields conflict.
- Integration friction, feedback latency and post-acceptance reneging cannot be measured from the legacy data.
- Effort figures are **PM planning estimates**, not engineering estimates.
- Most product decisions (DEC-025 to DEC-037) are **proposals awaiting approval**; DEC-038 is approved.
