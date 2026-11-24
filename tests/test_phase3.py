"""Phase 3 tests: plan arithmetic, D3 reference implementation, and the Phase 3 QC checker.

The mutation tests copy the outputs to a temp directory, break one thing, and assert the checker catches it,
so the checker is shown to detect what it claims.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src import offer_metrics, phase3_checks, phase3_plan
from tests.test_phase2 import base_world, rid, snap

HAVE_OUT = Path("outputs/phase3_product_strategy.md").is_file() and Path("outputs/offer_metric_baseline.csv").is_file()


def test_allocation_totals():
    a = phase3_plan.allocation_rows()
    assert sum(r["engineer_weeks"] for r in a) == 6.0
    for b, ew in phase3_plan.BUILD_EFFORT.items():
        assert sum(r["engineer_weeks"] for r in a if r["build"] == b) == ew
    for sp in (1, 2, 3):
        assert sum(r["engineer_weeks"] for r in a if r["sprint"] == sp) == 2.0


def test_builds_rank_top_three_under_every_weighting():
    rows = phase3_plan.score_rows()
    for key in ("weighted_rank", "equal_weight_rank", "rank_without_effort"):
        assert sorted(r["candidate_id"] for r in rows if r[key] <= 3) == ["B1", "B2", "B3"]


def test_offer_metric_rules_on_synthetic_data():
    w = base_world()                                   # offer 41 Accepted (decided); offer 42 Pending WITH a decision date
    rows = {r["metric_id"]: r for r in offer_metrics.compute(snap(**w))}
    assert (rows["OAM-01"]["numerator"], rows["OAM-01"]["denominator"]) == (1, 1)     # pending excluded
    assert (rows["OAM-02"]["numerator"], rows["OAM-02"]["denominator"]) == (1, 2)
    assert rows["OAM-03c"]["numerator"] == 1                                          # status/date conflict flagged
    assert rows["OAM-01"]["display"].startswith("counts only")                       # n < 10 (Phase 3.1 wording)
    # revised offer: a second offer on the same application supersedes the first
    w["Offers"][rid(43)] = {"Application": [rid(31)], "Status": "Declined", "Offered On": "2026-03-03",
                            "Decision On": "2026-03-06", "Proposed Start Date": "2026-04-01", "Base CTC": 150}
    w["Applications"][rid(31)]["Offers"] = [rid(41), rid(43)]
    rows = {r["metric_id"]: r for r in offer_metrics.compute(snap(**w))}
    assert (rows["OAM-01"]["numerator"], rows["OAM-01"]["denominator"]) == (0, 1)
    assert "superseded (revised) 1" in rows["OAM-01"]["notes"]


def test_offer_metric_as_of_excludes_future_offers():
    rows = {r["metric_id"]: r for r in offer_metrics.compute(snap(**base_world()), as_of="2026-02-15")}
    assert rows["OAM-02"]["denominator"] == 0


@pytest.mark.skipif(not HAVE_OUT, reason="phase 3 outputs not generated")
def test_phase3_checks_pass():
    assert phase3_checks.check() == []


def _copy_env(tmp_path, monkeypatch):
    out, aud = tmp_path / "outputs", tmp_path / "audit"
    shutil.copytree("outputs", out, ignore=shutil.ignore_patterns("private"))
    shutil.copytree("audit", aud)
    monkeypatch.setattr(phase3_checks, "OUT", out)
    monkeypatch.setattr(phase3_checks, "AUDIT", aud)
    return out


@pytest.mark.skipif(not HAVE_OUT, reason="phase 3 outputs not generated")
def test_checker_catches_wrong_roadmap_effort(tmp_path, monkeypatch):
    out = _copy_env(tmp_path, monkeypatch)
    p = out / "q3_roadmap.md"
    p.write_text(p.read_text().replace("| **Build total** | **2.5** | **2.0** | **1.5** | **6.0** |",
                                       "| **Build total** | **3.0** | **2.0** | **1.5** | **6.5** |"))
    assert any("roadmap build totals" in f for f in phase3_checks.check())


@pytest.mark.skipif(not HAVE_OUT, reason="phase 3 outputs not generated")
def test_checker_catches_untraceable_number_and_fourth_build(tmp_path, monkeypatch):
    out = _copy_env(tmp_path, monkeypatch)
    p = out / "phase3_product_strategy.md"
    p.write_text(p.read_text() + "\n### B4: Extra build\nJob boards convert at 9/41.\n")
    f = phase3_checks.check()
    assert any("build sections" in x for x in f) and any("9/41" in x for x in f)
