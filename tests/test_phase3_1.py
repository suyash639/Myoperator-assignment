"""Phase 3.1 tests: offer lifecycle transitions, duplicate warnings and attribution, D3 consistency rules."""
from __future__ import annotations

from pathlib import Path

import pytest

from src import duplicate_warning as dw, offer_lifecycle as lc, offer_metrics, phase3_plan
from src.data import load
from tests.test_phase2 import base_world, snap

HAVE_DATA = Path("data/raw/manifest.json").is_file()
T = "2026-03-10T12:00:00Z"


def offer(**kw):
    return lc.Offer(id=kw.pop("id", "o1"), application_id=kw.pop("app", "a1"), offered_on=kw.pop("offered_on", "2026-03-01"), **kw)


# ------------------------------------------------------------------ lifecycle: allowed transitions
@pytest.mark.parametrize("frm,to", list(lc.TRANSITIONS))
def test_every_allowed_transition_succeeds_for_a_permitted_role(frm, to):
    o = offer()
    if frm == lc.ACCEPTED:
        lc.transition(o, lc.ACCEPTED, actor="r1", role="recruiter", business_date="2026-03-03", recorded_at=T)
    roles, date_field, _, _ = lc.TRANSITIONS[(frm, to)]
    role = sorted(roles)[0]
    lc.transition(o, to, actor="u", role=role, business_date="2026-03-05", recorded_at=T, reason="r",
                  superseded_by="o2" if to == lc.SUPERSEDED else None)
    assert o.status == to and getattr(o, date_field) == "2026-03-05"
    assert lc.violations(o) == []
    assert o.events[-1]["from_status"] == frm and o.events[-1]["to_status"] == to and o.events[-1]["recorded_at"] == T


@pytest.mark.parametrize("frm,to,role", [(lc.PENDING, lc.RESCINDED, "recruiter"), (lc.PENDING, lc.SUPERSEDED, "recruiter"),
                                         (lc.PENDING, lc.ACCEPTED, "hiring_manager"), (lc.PENDING, lc.EXPIRED, "hiring_manager")])
def test_transition_rejected_for_unauthorised_role(frm, to, role):
    with pytest.raises(lc.LifecycleError, match="may not"):
        lc.transition(offer(), to, actor="u", role=role, business_date="2026-03-05", recorded_at=T, reason="r", superseded_by="o2")


@pytest.mark.parametrize("frm,to", [(lc.DECLINED, lc.ACCEPTED), (lc.EXPIRED, lc.PENDING), (lc.ACCEPTED, lc.PENDING),
                                    (lc.SUPERSEDED, lc.ACCEPTED), (lc.ACCEPTED, lc.DECLINED), (lc.WITHDRAWN, lc.ACCEPTED)])
def test_disallowed_transitions(frm, to):
    o = offer(status=frm)
    with pytest.raises(lc.LifecycleError, match="not allowed"):
        lc.transition(o, to, actor="u", role="recruiting_ops_lead", business_date="2026-03-05", recorded_at=T, reason="r")


def test_reason_and_dates_are_enforced():
    with pytest.raises(lc.LifecycleError, match="requires a reason"):
        lc.transition(offer(), lc.DECLINED, actor="u", role="recruiter", business_date="2026-03-05", recorded_at=T)
    with pytest.raises(lc.LifecycleError, match="before offered_on"):
        lc.transition(offer(), lc.ACCEPTED, actor="u", role="recruiter", business_date="2026-02-01", recorded_at=T)
    with pytest.raises(lc.LifecycleError, match="future"):
        lc.transition(offer(), lc.ACCEPTED, actor="u", role="recruiter", business_date="2026-04-01", recorded_at=T)


def test_pending_with_decision_date_is_a_violation():
    assert any("Pending offer carries a resolution date" in v for v in lc.violations(offer(decision_on="2026-03-04")))
    assert any("without decision_on" in v for v in lc.violations(offer(status=lc.ACCEPTED, decision_outcome=lc.ACCEPTED)))


def test_renege_keeps_the_acceptance_decision():
    o = offer()
    lc.transition(o, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-03", recorded_at=T)
    lc.transition(o, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-08", recorded_at=T, reason="reneged")
    assert o.decision_outcome == lc.ACCEPTED and o.decision_on == "2026-03-03" and lc.violations(o) == []


def test_revision_supersedes_pending_and_blocks_accepted():
    old, new = offer(id="o1"), offer(id="o2", offered_on="2026-03-06")
    lc.create_revision(old, new, recorded_at=T)
    assert old.status == lc.SUPERSEDED and old.superseded_by == "o2" and old.superseded_on == "2026-03-06"
    assert old.events[-1]["role"] == "system"
    acc = offer(id="o3")
    lc.transition(acc, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-03", recorded_at=T)
    with pytest.raises(lc.LifecycleError, match="cannot revise an Accepted"):
        lc.create_revision(acc, offer(id="o4", offered_on="2026-03-07"), recorded_at=T)
    dec = offer(id="o5")
    lc.transition(dec, lc.DECLINED, actor="r", role="recruiter", business_date="2026-03-03", recorded_at=T, reason="Compensation")
    lc.create_revision(dec, offer(id="o6", offered_on="2026-03-07"), recorded_at=T)
    assert dec.status == lc.DECLINED          # resolved offers keep their status; the metric counts only the latest


def test_status_at_reconstructs_as_of():
    o = offer()
    lc.transition(o, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-05", recorded_at=T)
    assert lc.status_at(o, "2026-03-04") == lc.PENDING
    assert lc.status_at(o, "2026-03-05") == lc.ACCEPTED
    assert lc.status_at(o, "2026-02-01") == "not yet offered"


def test_corrections_are_restricted_and_audited():
    o = offer(decision_on="2026-03-04")                                  # legacy conflict
    with pytest.raises(lc.LifecycleError, match="only recruiting_ops_lead"):
        lc.correct(o, actor="r", role="recruiter", recorded_at=T, reason="x", status=lc.DECLINED)
    with pytest.raises(lc.LifecycleError, match="contradictory"):
        lc.correct(o, actor="ops", role="recruiting_ops_lead", recorded_at=T, reason="x", status=lc.DECLINED)  # no decline_reason
    assert o.status == lc.PENDING                                         # failed correction rolled back
    lc.correct(o, actor="ops", role="recruiting_ops_lead", recorded_at=T, reason="confirmed by email",
               status=lc.DECLINED, decision_outcome=lc.DECLINED, decline_reason="Counter Offer")
    e = o.events[-1]
    assert e["event_type"] == "correction" and e["before"]["status"] == lc.PENDING and e["after"]["status"] == lc.DECLINED


@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_legacy_audit_flags_exactly_the_phase2_conflicts():
    flagged = lc.audit_legacy(load())
    assert len(flagged) == 4 and all(r["status"] == "Pending" for r in flagged)


# ------------------------------------------------------------------ duplicate warning (warning-only)
def registry():
    r = dw.Registry()
    r.intake("c1", "Asha Rao", "+91 98000 00001")
    return r


def test_warning_requires_name_and_phone():
    r = registry()
    assert r.intake("c2", "Asha Rao", "+91 98000 00002")["warning"] == []           # name only: no warning
    assert r.intake("c3", "Someone Else", "+91 98000 00001")["warning"] == []       # phone only: no warning
    with pytest.raises(dw.AttributionError, match="decision is required"):
        r.intake("c4", " asha  RAO ", "+919800000001")                              # normalised name + phone: warns


def test_same_person_attaches_without_merging():
    r = registry()
    before = dict(r.candidates)
    out = r.intake("c2", "Asha Rao", "+91 98000 00001", decision="same_person", recruiter="rec1")
    assert out["warning"] == ["c1"] and out["candidate_id"] == "c1"
    assert r.candidates == before                                                   # no record created, merged or deleted


def test_different_person_needs_reason_and_is_remembered():
    r = registry()
    with pytest.raises(dw.AttributionError, match="requires a reason"):
        r.intake("c2", "Asha Rao", "+91 98000 00001", decision="different_person")
    r.intake("c2", "Asha Rao", "+91 98000 00001", decision="different_person", reason="mother and daughter share phone")
    assert set(r.candidates) == {"c1", "c2"} and frozenset({"c1", "c2"}) in r.not_duplicate
    assert r.matches("Asha Rao", "+91 98000 00001") == ["c1", "c2"]                 # both kept; nothing merged


def test_unsure_goes_to_review_queue():
    r = registry()
    r.intake("c2", "Asha Rao", "+91 98000 00001", decision="unsure")
    assert r.review_queue == [frozenset({"c1", "c2"})] and len(r.candidates) == 2


def test_registry_has_no_merge_or_delete_path():
    assert not any(hasattr(dw.Registry, n) for n in ("merge", "delete", "remove"))


@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_snapshot_scan_reproduces_dq02():
    groups = dw.scan(load())
    assert len(groups) == 6 and sum(len(g) for g in groups) == 12


# ------------------------------------------------------------------ source taxonomy and referral attribution
def test_referral_attribution_rules():
    assert dw.attribute("Employee Referral", "p1")["referral_type"] == "direct"
    with pytest.raises(dw.AttributionError, match="requires referred_by"):
        dw.attribute("Employee Referral", None)
    with pytest.raises(dw.AttributionError, match="endorsement"):
        dw.attribute("Job Board", "p1", source_detail="Naukri")
    assert dw.attribute("Job Board", "p1", source_detail="Naukri", endorsement_confirmed=True)["referral_type"] == "endorsement"
    with pytest.raises(dw.AttributionError, match="requires board name"):
        dw.attribute("Job Board", None)
    with pytest.raises(dw.AttributionError, match="not in taxonomy"):
        dw.attribute("Referral", "p1")                                              # legacy label not selectable


def test_intake_method_is_system_derived_and_distinct_from_source():
    assert dw.intake_method("ui_manual") == "Manual entry" and dw.intake_method("api") == "Integration/API"
    assert not set(dw.INTAKE_METHODS.values()) & set(dw.SOURCES)
    assert dw.legacy_attribution("Referral", False).startswith("referral label, no referrer")
    assert dw.legacy_attribution("Job Board", True) == "endorsement"


# ------------------------------------------------------------------ D3 consistency
def test_decided_after_as_of_counts_as_pending_at_as_of():
    rows = {r["metric_id"]: r for r in offer_metrics.compute(snap(**base_world()), as_of="2026-03-04")}
    # offer 41 Accepted on 2026-03-05 -> pending at 2026-03-04; offer 42 Pending (with a conflicting date)
    assert rows["OAM-01"]["denominator"] == 0 and rows["OAM-03"]["numerator"] == 2


def test_display_tiers_and_privacy_are_separate():
    assert offer_metrics.MIN_N == 10 and offer_metrics.LOW_N == 30 and offer_metrics.PRIVACY_K == 5
    rows = {r["metric_id"]: r for r in offer_metrics.compute(snap(**base_world()))}
    assert rows["OAM-01"]["display"].startswith("counts only") and rows["OAM-01"]["privacy"].startswith("none")


@pytest.mark.skipif(not HAVE_DATA, reason="no snapshot")
def test_snapshot_display_tiers():
    rows = {r["metric_id"]: r for r in offer_metrics.compute()}
    assert rows["OAM-01"]["display"] == "rate"
    assert rows["OAM-09"]["display"].startswith("rate with low-sample label") and "1 candidate" in rows["OAM-09"]["display"]
    assert rows["OAM-08-2026-H1"]["display"].startswith("rate with low-sample label")
    assert all(r["privacy"].startswith("restricted") for k, r in rows.items() if k.startswith("OAM-07"))


def test_plan_first_cut_is_duplicate_warning_and_all_estimates_labelled():
    a = phase3_plan.allocation_rows()
    assert sum(r["engineer_weeks"] for r in a) == 6.0
    assert {r["component_id"] for r in a if r["first_cut"]} == {"B3.2", "B3.3b"}
    assert sum(r["engineer_weeks"] for r in a if r["first_cut"]) == 0.5
    assert sum(r["engineer_weeks"] for r in a if r["build"] == "B3") == 1.5
    assert all(r["estimate_status"].startswith("PM planning estimate") for r in a)
