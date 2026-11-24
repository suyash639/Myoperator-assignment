"""Phase 2 tests.

Unit tests use small synthetic snapshots, so each check is shown to detect exactly what it claims.
Integration tests run on the real snapshot (skipped if data/raw is absent). They assert that the
Python and DuckDB numbers match, that raw data is unchanged, that headline values hold,
and that no personal data leaks into committable outputs.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from src import audit, integrity, metrics, profile
from src.data import IntegrityError, Snapshot, load

RAW = Path("data/raw")
HAVE_DATA = (RAW / "manifest.json").is_file()


def rid(n: int, p: str = "rec") -> str:
    return f"{p}{n:014d}"


def snap(**tables) -> Snapshot:
    names = ["Departments", "People", "Job Openings", "Candidates", "Applications", "Interviews", "Offers", "Findings"]
    raw = {t: [] for t in names}
    for t, recs in tables.items():
        raw[t.replace("_", " ")] = [{"id": k, "createdTime": "2026-08-27T16:39:00.000Z", "fields": f} for k, f in recs.items()]
    return Snapshot(raw=raw, by_id={t: {r["id"]: r["fields"] for r in rs} for t, rs in raw.items()}, manifest={})


def base_world():
    """1 department, 1 recruiter, 1 opening, 3 candidates, 3 applications, 2 offers."""
    D = {rid(1): {"Name": "Eng", "Job Openings": [rid(10)], "People": [rid(2)]}}
    P = {rid(2): {"Role": "Recruiter", "Department": [rid(1)], "Applications as Recruiter": [rid(31), rid(32), rid(33)],
                  "Reqs as Recruiter": [rid(10)], "Reqs as Hiring Manager": [rid(10)]}}
    J = {rid(10): {"Status": "Open", "Headcount": 1, "Opened On": "2026-01-01", "Target Close": "2026-12-01",
                   "Salary Band Min": 100, "Salary Band Max": 200, "Level": "Mid", "Department": [rid(1)],
                   "Recruiter": [rid(2)], "Hiring Manager": [rid(2)], "Applications": [rid(31), rid(32), rid(33)]}}
    C = {rid(21): {"Full Name": "A B", "Phone": "+91 1", "Source": "Job Board", "Created On": "2026-01-01", "Expected CTC": 150, "Current CTC": 100, "Years Experience": 1, "Applications": [rid(31)]},
         rid(22): {"Full Name": "C D", "Phone": "+91 2", "Source": "Referral", "Created On": "2026-01-01", "Expected CTC": 150, "Current CTC": 100, "Years Experience": 1, "Applications": [rid(32)]},
         rid(23): {"Full Name": "E F", "Phone": "+91 3", "Source": "Agency", "Created On": "2026-01-01", "Expected CTC": 150, "Current CTC": 100, "Years Experience": 1, "Applications": [rid(33)]}}
    app = lambda c, stage, status, **kw: {"Candidate": [c], "Opening": [rid(10)], "Recruiter": [rid(2)], "Stage": stage,
                                          "Status": status, "Applied On": "2026-02-01", "Application ID": f"APP-{c[-2:]}", **kw}
    A = {rid(31): app(rid(21), "Hired", "Closed", **{"Offers": [rid(41)], "Closed On": "2026-03-10", "Screened On": "2026-02-02"}),
         rid(32): app(rid(22), "Offer", "Active", **{"Offers": [rid(42)], "Screened On": "2026-02-02"}),
         rid(33): app(rid(23), "Rejected", "Closed", **{"Closed On": "2026-02-05", "Rejection Reason": "Skills Mismatch"})}
    O = {rid(41): {"Application": [rid(31)], "Status": "Accepted", "Offered On": "2026-03-01", "Decision On": "2026-03-05",
                   "Proposed Start Date": "2026-04-01", "Base CTC": 150},
         rid(42): {"Application": [rid(32)], "Status": "Pending", "Offered On": "2026-03-01", "Decision On": "2026-03-04",
                   "Proposed Start Date": "2026-04-01", "Base CTC": 150}}
    return dict(Departments=D, People=P, Job_Openings=J, Candidates=C, Applications=A, Interviews={}, Offers=O)


# ------------------------------------------------------------------ data loading
@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_load_refuses_modified_raw_data(tmp_path):
    d = tmp_path / "raw"
    shutil.copytree(RAW, d)
    for p in d.iterdir():
        p.chmod(0o644)
    f = d / "offers.json"
    f.write_bytes(f.read_bytes().replace(b'"Accepted"', b'"Declined"', 1))
    with pytest.raises(IntegrityError):
        load(d)


# ------------------------------------------------------------------ profile
def test_infer_type():
    assert profile.infer_type(["2026-01-01"]) == "date"
    assert profile.infer_type([rid(1)]) == "text"
    assert profile.infer_type([[rid(1)]]) == "link"
    assert profile.infer_type([1, 2.5]) == "number"
    assert profile.infer_type(["x", 1]) == "number|text"


def test_profile_suppresses_pii_values():
    w = base_world()
    w["People"][rid(2)].update({"Full Name": "Secret Person", "Work Email": "secret@example.com"})
    rows = profile.profile(snap(**w))
    blob = json.dumps(rows)
    assert "Secret Person" not in blob and "secret@example.com" not in blob


# ------------------------------------------------------------------ integrity
def test_integrity_clean_world_passes():
    rows = integrity.check_relationships(snap(**base_world()))
    assert all(r["status"] == "PASS" for r in rows), [r for r in rows if r["status"] != "PASS"]


def test_integrity_detects_orphan_and_asymmetric_link():
    w = base_world()
    w["Offers"][rid(42)]["Application"] = [rid(99)]                  # orphan
    w["Applications"][rid(33)]["Opening"] = [rid(10)]
    w["Job_Openings"][rid(10)]["Applications"] = [rid(31), rid(32)]  # 33 no longer listed: asymmetric
    rows = {r["relationship"]: r for r in integrity.check_relationships(snap(**w))}
    assert rows["Offers.Application -> Applications"]["orphans"] == 1
    assert rows["Applications.Opening -> Job Openings"]["asymmetric"] == 1


def test_integrity_detects_cardinality_violation():
    w = base_world()
    w["Applications"][rid(31)]["Candidate"] = [rid(21), rid(22)]
    rows = {r["relationship"]: r for r in integrity.check_relationships(snap(**w))}
    assert rows["Applications.Candidate -> Candidates"]["cardinality_violations"] == 1


# ------------------------------------------------------------------ audit checks
def issues(w):
    return {i.id: i for i in audit.run_checks(snap(**w))}


def test_pending_with_decision_date_detected():
    i = issues(base_world())["DQ-06"]
    assert (i.affected, i.denominator) == (1, 1) and i.evidence == [rid(42)]


def test_duplicate_candidates_by_name_and_phone():
    w = base_world()
    w["Candidates"][rid(23)].update({"Full Name": " a b ", "Phone": "+911"})
    i = issues(w)["DQ-02"]
    assert i.affected == 2 and "Source differs in 1" in i.detail


def test_source_vs_referrer_conflict():
    w = base_world()
    w["Applications"][rid(31)]["Referred By"] = [rid(2)]   # Job Board + referrer
    i = issues(w)["DQ-01"]
    assert i.affected == 2      # app 31 (referred, Source=Job Board) + app 32 (Source=Referral, no referrer)


def test_concurrent_vs_reapplication_classification():
    w = base_world()
    w["Applications"][rid(34)] = dict(w["Applications"][rid(33)], **{"Applied On": "2026-02-03", "Application ID": "APP-34"})
    i = issues(w)["DQ-05"]
    assert "concurrent" in i.detail and i.classification == "Suspicious pattern"
    w["Applications"][rid(34)]["Applied On"] = "2026-06-01"
    i = issues(w)["DQ-05"]
    assert "reapplied 116 days" in i.detail and i.classification == "Legitimate business case"


def test_impossible_dates_detected():
    w = base_world()
    w["Offers"][rid(41)]["Proposed Start Date"] = "2026-02-01"
    i = issues(w)["DQ-13"]
    assert rid(41) in i.evidence


def test_rejection_reason_on_hired_detected():
    w = base_world()
    w["Applications"][rid(31)]["Rejection Reason"] = "Culture Fit"
    assert issues(w)["DQ-09"].affected == 1


def test_opening_status_contradictions():
    w = base_world()
    w["Job_Openings"][rid(10)]["Status"] = "Cancelled"
    i = issues(w)["DQ-11"]
    assert i.affected == 1 and "Cancelled with hires: 1" in i.detail


# ------------------------------------------------------------------ metrics
def mrow(m, mid):
    r = m.value(mid)
    return r["numerator"], r["denominator"]


def test_acceptance_denominators():
    w = base_world()
    m = metrics.compute(snap(**w))
    assert mrow(m, "M-B0") == (1, 2)       # pending in denominator
    assert mrow(m, "M-B1") == (1, 1)       # decided only
    assert mrow(m, "M-B2") == (2, 2)


def test_hire_definitions_and_job_board_share():
    m = metrics.compute(snap(**base_world()))
    assert mrow(m, "M-H0") == (1, 1)
    assert mrow(m, "M-A0") == (1, 1)


def test_wilson_bounds():
    lo, hi = metrics.wilson(26, 31)
    assert 0.67 < lo < 0.68 and 0.92 < hi < 0.93
    assert metrics.wilson(0, 5)[0] == 0.0 and metrics.wilson(5, 5)[1] == 1.0


# ------------------------------------------------------------------ integration on the real snapshot
@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_python_and_sql_agree_on_every_checkpoint():
    from src.run_phase2 import python_checkpoints
    from src.verify_sql import compare, sql_results
    rows = compare(python_checkpoints(), sql_results())
    assert len(rows) >= 30
    assert [r for r in rows if r["match"] != "MATCH"] == []


@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_headline_values_regression():
    m = metrics.compute(load())
    assert mrow(m, "M-H0") == (26, 26)
    assert mrow(m, "M-A0") == (7, 26)
    assert mrow(m, "M-A0r") == (7, 26)
    assert mrow(m, "M-A2") == (6, 26)
    assert mrow(m, "M-A8") == (8, 26)
    assert mrow(m, "M-B0") == (26, 36)
    assert mrow(m, "M-B1") == (26, 31)
    assert mrow(m, "M-B3") == (26, 34)


@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_raw_snapshot_matches_manifest():
    man = json.loads((RAW / "manifest.json").read_text())
    for t, e in man["tables"].items():
        assert hashlib.sha256((RAW / e["file"]).read_bytes()).hexdigest() == e["sha256"], t


@pytest.mark.skipif(not (HAVE_DATA and Path("outputs/findings_table.csv").is_file()), reason="outputs not generated")
def test_no_personal_data_in_committable_outputs():
    s = load()
    pii = set()
    for t in ("Candidates", "People"):
        for f in s.f(t).values():
            for k in ("Full Name", "Email", "Work Email", "Phone"):
                if f.get(k):
                    pii.add(f[k])
    for p in Path("outputs").glob("*.*"):
        if p.suffix in (".csv", ".md"):
            text = p.read_text()
            leaked = [x for x in pii if x in text]
            assert not leaked, f"{p.name} contains personal data, e.g. {leaked[:2]}"
