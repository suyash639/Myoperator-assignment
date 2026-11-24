"""Build the public GitHub submission in release/Myoperator-assignment/ and audit what git would publish.

    uv run python -m src.build_submission            # build + git init + git add + staged-file audit (no commit)

* Copies an explicit ALLOW-LIST of files (never a wildcard copy of the project).
* Applies public redaction to text files: token fingerprint, token length/prefix metadata, Airtable base ID.
  Local originals (including the append-only audit logs and Phase 2.2 outputs) are NOT modified.
* Initialises a separate git repository there, stages everything, and audits the STAGED file list and contents:
  forbidden paths, credential values/patterns, personal data from the snapshot, raw-record shapes, binaries, sizes.
* Writes release/STAGING_AUDIT.md (outside the published directory). Exit code 1 if anything fails.
Never commits, adds a remote or pushes.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from src.final_package import archive_refs, public_redact

ROOT = Path(".").resolve()
DEST = ROOT / "release" / "Myoperator-assignment"
REPORT = ROOT / "release" / "STAGING_AUDIT.md"

ALLOW = (["pyproject.toml", "uv.lock", "requirements.txt", ".python-version", ".env.example", ".gitignore"]
         + sorted(str(p) for p in Path("src").glob("*.py"))
         + sorted(str(p) for p in Path("queries").glob("*.sql"))
         + sorted(str(p) for p in Path("tests").glob("*.py"))
         + sorted(str(p) for p in Path("audit").glob("*.md"))
         + sorted(str(p) for p in Path("outputs").glob("*.md")) + sorted(str(p) for p in Path("outputs").glob("*.csv"))
         + sorted(str(p) for p in Path("outputs/final").glob("*.md")) + sorted(str(p) for p in Path("outputs/final").glob("*.csv"))
         + sorted(str(p) for p in Path("outputs/final/pdf").glob("*.pdf")))
PLACEHOLDERS = ["data/raw/.gitkeep", "data/processed/.gitkeep", "logs/.gitkeep", "outputs/private/.gitkeep"]
TEXT_EXT = {".md", ".csv", ".py", ".sql", ".toml", ".txt", ".example", ".gitignore", ".lock", ""}
FORBIDDEN = [r"(^|/)\.env$", r"^data/raw/(?!\.gitkeep$)", r"^data/processed/(?!\.gitkeep$)", r"^logs/(?!\.gitkeep$)",
             r"^outputs/private/(?!\.gitkeep$)", r"\.jsonl$", r"(^|/)\.venv/", r"__pycache__", r"(^|/)\.claude/", r"\.duckdb",
             r"(^|/)\.pytest_cache/", r"scratchpad", r"(^|/)transcripts/raw/", r"\.pem$|\.key$", r"manifest\.json$"]

ROOT_README = """# Myoperator-assignment: TalentFlow Q3 Product Exercise (Acme Corp)

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
"""


def git(*args, cwd=DEST) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def build() -> dict[str, int]:
    if DEST.exists():
        keep_git = DEST / ".git"
        for p in DEST.iterdir():
            if p != keep_git:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    DEST.mkdir(parents=True, exist_ok=True)
    redactions = {}
    for rel in ALLOW:
        src, dst = ROOT / rel, DEST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in TEXT_EXT or src.name.startswith("."):
            t = src.read_text(encoding="utf-8")
            r = public_redact(t)
            if src.suffix == ".md" and not rel.startswith("audit/"):
                r = archive_refs(r)   # audit logs keep historical references verbatim
            if r != t:
                redactions[rel] = sum(1 for a, b in zip(t.splitlines(), r.splitlines()) if a != b)
            dst.write_text(r, encoding="utf-8")
        else:
            shutil.copy2(src, dst)
    for rel in PLACEHOLDERS:
        (DEST / rel).parent.mkdir(parents=True, exist_ok=True)
        (DEST / rel).write_text("")
    (DEST / "README.md").write_text(ROOT_README, encoding="utf-8")
    return redactions


def audit() -> tuple[list[str], list[str], dict]:
    if not (DEST / ".git").exists():
        git("init", "-q", "-b", "main")
    git("add", "-A")
    _, out = git("ls-files")   # everything the next commit would contain (not just the diff; deletions excluded)
    staged = [l for l in out.splitlines() if l.strip()]
    problems = []
    # path rules
    for f in staged:
        if any(re.search(rx, f) for rx in FORBIDDEN):
            problems.append(f"forbidden path staged: {f}")
    # .gitignore effectiveness inside the published repo (files that must never be addable)
    probes = [".env", "data/raw/applications.json", "data/processed/x.parquet", "logs/extraction_x.log", "session.jsonl",
              "outputs/private/x.csv", ".venv/bin/python", "transcripts/raw/x.md", ".claude/settings.local.json"]
    ignore_res = {}
    for pth in probes:
        rc, _ = git("check-ignore", "-q", "--no-index", pth)
        ignore_res[pth] = rc == 0
        if rc != 0:
            problems.append(f".gitignore does not exclude {pth}")
    # secrets from the local environment (values never printed)
    token = base_id = ""
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            if line.startswith("AIRTABLE_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("AIRTABLE_BASE_ID="):
                base_id = line.split("=", 1)[1].strip().strip('"').strip("'")
    from src.airtable_client import token_fingerprint
    fp = token_fingerprint(token) if token else ""
    pii, rec_ids, info_notes = set(), set(), []
    try:
        from src.data import load
        s = load()
        pii = {v for t in ("Candidates", "People") for fl in s.f(t).values()
               for k in ("Full Name", "Email", "Work Email", "Phone") if (v := fl.get(k))}
        rec_ids = {r["id"] for t in s.raw.values() for r in t}
    except Exception as e:  # snapshot unavailable: the PII value scan cannot run
        problems.append(f"PII value scan could not load snapshot: {type(e).__name__}")
    sizes = {}
    for f in staged:
        p = DEST / f
        b = p.read_bytes()
        sizes[f] = len(b)
        if len(b) > 5_000_000:
            problems.append(f"large file {f} ({len(b)} bytes)")
        if p.suffix not in (".md", ".csv", ".py", ".sql", ".toml", ".txt", ".lock", ".pdf", ".example", "") and not p.name.startswith("."):
            problems.append(f"unexpected file type {f}")
        if token and token.encode() in b:
            problems.append(f"{f}: contains the configured token value")
        if base_id and base_id.encode() in b:
            problems.append(f"{f}: contains the Airtable base ID")
        if fp and fp.encode() in b:
            problems.append(f"{f}: contains the token fingerprint")
        txt = b.decode("utf-8", "ignore")
        if re.search(r"pat[A-Za-z0-9]{14}\.[a-f0-9]{64}", txt):
            problems.append(f"{f}: PAT-shaped string")
        if re.search(r"Bearer\s+[A-Za-z0-9._\-]{20,}", txt):
            problems.append(f"{f}: bearer credential")
        if p.suffix != ".pdf":
            code = f.startswith(("src/", "tests/"))
            if re.search(r"\(len \d+, `?pat`? prefix\)", txt):
                problems.append(f"{f}: token length/prefix metadata")
            leaked = [x for x in pii if x in txt]
            real_ids = [x for x in rec_ids if x in txt] if code else []
            if leaked:
                problems.append(f"{f}: {len(leaked)} personal values from the snapshot")
            if real_ids:
                problems.append(f"{f}: {len(real_ids)} real Airtable record IDs in source code")
            emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", txt)) - {"noreply@anthropic.com"}
            phone = re.search(r"\+91[\s\d]{8,}", txt)
            raw_shape = '"createdTime"' in txt and '"fields"' in txt
            if code:   # generic patterns in code/tests are synthetic fixtures or parser keys IF no real value is present
                for what, hit in (("email-shaped", emails), ("phone-shaped", phone), ("record-key", raw_shape)):
                    if hit:
                        info_notes.append(f"{f}: {what} pattern; verified 0 real snapshot values / record IDs (synthetic fixture or parser code)")
            else:
                if emails:
                    problems.append(f"{f}: email-shaped strings {sorted(emails)[:3]}")
                if phone:
                    problems.append(f"{f}: phone-shaped string")
                if raw_shape:
                    problems.append(f"{f}: raw Airtable record JSON")
    return staged, problems, {"ignore": ignore_res, "sizes": sizes, "info": info_notes}


def main() -> int:
    redactions = build()
    staged, problems, info = audit()
    rc, remote = git("remote", "-v")
    rc2, log = git("log", "--oneline", "-1")
    L = ["# Staging audit: release/Myoperator-assignment", "",
         f"**Result: {'PASS' if not problems else 'FAIL'}** — {len(staged)} staged files, {sum(info['sizes'].values()) // 1024} KB total.", "",
         f"- Commits in staging repo: {'none' if 'does not have any commits' in log or rc2 != 0 else log}",
         f"- Remotes: {remote or 'none'}", "",
         "## Problems", ""] + ([f"- {p}" for p in problems] or ["- none"]) + [
         "", "## Informational (verified, not problems)", ""] + ([f"- {n}" for n in info["info"]] or ["- none"]) + [
         "", "## .gitignore effectiveness (paths that must be excluded)", "",
         "| Path | Excluded |", "|---|---|"] + [f"| `{k}` | {'yes' if v else '**NO**'} |" for k, v in info["ignore"].items()] + [
         "", "## Public redactions applied (local originals unchanged)", "",
         "| File | Lines changed |", "|---|---|"] + ([f"| `{k}` | {v} |" for k, v in sorted(redactions.items())] or ["| none | |"]) + [
         "", "## Staged files", "", "| File | Bytes |", "|---|---:|"] + [f"| `{f}` | {info['sizes'][f]} |" for f in staged]
    REPORT.write_text("\n".join(L) + "\n")
    print(f"staged={len(staged)} problems={len(problems)} redacted_files={len(redactions)}")
    for p in problems:
        print("PROBLEM", p)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
