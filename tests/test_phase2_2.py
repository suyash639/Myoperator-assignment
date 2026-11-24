"""Phase 2.2 tests: corrections, new checks and report/CSV/log consistency.

Synthetic tests show each new check detects exactly what it claims. Integration tests (skipped if
the snapshot or outputs are absent) pin the corrected values and enforce that every "x/y" fraction
written in the Phase 2 markdown reports exists in a generated CSV (DEC-024), so hand-typed numbers
cannot drift from the data again (Phase 2.1 RV-01).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

from src import audit, metrics, traceability
from src.data import load
from tests.test_phase2 import base_world, rid, snap

OUT = Path("outputs")
HAVE_DATA = Path("data/raw/manifest.json").is_file()
HAVE_OUT = (OUT / "metric_calculations.csv").is_file()


def issues(w):
    return {i.id: i for i in audit.run_checks(snap(**w))}


# ------------------------------------------------------------------ new checks (synthetic)
def test_dq26_declined_closed_before_decision():
    w = base_world()
    w["Offers"][rid(42)].update({"Status": "Declined", "Decline Reason": "Location"})
    w["Applications"][rid(32)].update({"Status": "Closed", "Closed On": "2026-03-02"})   # decision is 2026-03-04
    i = issues(w)["DQ-26"]
    assert (i.affected, i.denominator) == (1, 1)


def test_dq27_interview_after_closure():
    w = base_world()
    w["Interviews"] = {rid(51): {"Application": [rid(33)], "Scheduled On": "2026-02-10", "Completed On": "2026-02-10",
                                 "Outcome": "Completed", "Round": "Screen"}}
    w["Applications"][rid(33)].update({"Interviews": [rid(51)], "Screened On": "2026-02-02"})   # closed 2026-02-05
    assert issues(w)["DQ-27"].affected == 1


def test_dq28_stalled_vs_recent_active():
    w = base_world()                       # app 32 Active, last activity 2026-03-04 → stalled at 2026-08-27
    assert (issues(w)["DQ-28"].affected, issues(w)["DQ-28"].denominator) == (1, 1)
    w["Offers"][rid(42)].update({"Offered On": "2026-08-10", "Decision On": "2026-08-20"})
    assert issues(w)["DQ-28"].affected == 0


def test_dq29_offer_to_already_hired_candidate():
    w = base_world()
    w["Applications"][rid(34)] = {"Candidate": [rid(21)], "Opening": [rid(10)], "Recruiter": [rid(2)], "Stage": "Offer",
                                  "Status": "Active", "Applied On": "2026-03-20", "Application ID": "APP-34",
                                  "Offers": [rid(43)]}
    w["Candidates"][rid(21)]["Applications"].append(rid(34))
    w["Offers"][rid(43)] = {"Application": [rid(34)], "Status": "Pending", "Offered On": "2026-04-01",
                            "Proposed Start Date": "2026-05-01", "Base CTC": 150}
    i = issues(w)["DQ-29"]
    assert i.affected == 1 and rid(43) in i.evidence[0]


def test_dq13_reports_every_check_and_no_hand_typed_claim():
    i = issues(base_world())["DQ-13"]
    assert "0 violations" not in i.detail
    assert i.detail.count("]: ") >= 16       # every comparison reported with its own count


def test_metrics_have_levels_and_no_intervals():
    m = metrics.compute(snap(**base_world()))
    row = m.value("M-B1")
    assert row["level"] == "offer" and m.value("M-B4")["level"] == "candidate"
    assert "ci95_low" not in row and row["single_record_pp"] == "100.0"


def test_cohort_excludes_in_flight_active():
    w = base_world()
    for a in w["Applications"].values():
        a["Applied On"] = "2026-02-01"
    w["Offers"][rid(42)].update({"Offered On": "2026-08-10", "Decision On": "2026-08-20"})   # app 32 recently active
    m = metrics.compute(snap(**w))
    r = m.value("M-K-eligible")
    assert (r["numerator"], r["denominator"]) == (2, 3)


# ------------------------------------------------------------------ real snapshot
@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_corrected_values_regression():
    m = metrics.compute(load())
    pair = lambda k: (m.value(k)["numerator"], m.value(k)["denominator"])
    assert pair("M-DF-Engineering-hired") == (0, 30)
    assert pair("M-DF-Engineering-interviewed") == (3, 30)
    assert pair("M-A9n") == (7, 7)
    assert pair("M-A9") == (6, 26) and pair("M-A10") == (8, 26)
    assert pair("M-B1") == (26, 31) and pair("M-B0") == (26, 36) and pair("M-B4") == (24, 28)
    assert pair("M-B3-2026-11-24") == (26, 36)
    assert pair("M-K-eligible") == (134, 134) and pair("M-KF3") == (16, 134) and pair("M-KF4") == (12, 134)
    i = {x.id: x for x in audit.run_checks(load())}
    assert (i["DQ-26"].affected, i["DQ-26"].denominator) == (4, 5)
    assert (i["DQ-27"].affected, i["DQ-27"].denominator) == (7, 84)
    assert (i["DQ-28"].affected, i["DQ-28"].denominator) == (50, 105)
    assert (i["DQ-29"].affected, i["DQ-29"].denominator) == (4, 36)
    assert len(i["DQ-14"].evidence) == i["DQ-14"].affected


@pytest.mark.skipif(not HAVE_OUT, reason="outputs not generated")
def test_traceability_references_resolve():
    assert traceability.validate_files() == []


@pytest.mark.skipif(not HAVE_OUT, reason="outputs not generated")
def test_no_sampling_intervals_in_main_reporting():
    for name in ("metric_calculations.csv", "findings_table.csv"):
        text = (OUT / name).read_text()
        assert "ci95" not in text and "95% CI" not in text, name
    for name in ("phase2_summary.md", "data_quality_audit.md"):
        assert "95% CI" not in (OUT / name).read_text(), name


@pytest.mark.skipif(not HAVE_OUT, reason="outputs not generated")
def test_every_fraction_in_reports_exists_in_csv_outputs():
    known = set()
    for p in OUT.glob("*.csv"):
        for r in csv.DictReader(p.open()):
            for a, b in (("numerator", "denominator"), ("affected_records", "denominator"),
                         ("python_numerator", "python_denominator")):
                if r.get(a, "") != "" and r.get(b, "") != "":
                    known.add(f"{r[a]}/{r[b]}")
            for v in r.values():
                known.update(re.findall(r"\b\d+/\d+\b", v or ""))
    ver_rows = sum(1 for _ in csv.DictReader((OUT / "verification.csv").open()))
    known.add(f"{ver_rows}/{ver_rows}")           # verification tally
    known.add("72/72")                            # Phase 1 extraction validator tally (INV-004)
    missing = {}
    for name in ("phase2_summary.md", "data_quality_audit.md"):
        found = set(re.findall(r"(?<![\d.-])\d+/\d+(?![\d/])", (OUT / name).read_text()))
        bad = sorted(found - known)
        if bad:
            missing[name] = bad
    assert not missing, f"fractions not traceable to any CSV: {missing}"
