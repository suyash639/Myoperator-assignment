"""Phase 3.2 tests: event-time acceptance (renege / rescission), per-stage inactivity, configurable privacy,
proposed roles and decision-status governance."""
from __future__ import annotations

from pathlib import Path

import pytest

from src import inactivity, offer_lifecycle as lc, offer_metrics as om
from tests.test_phase2 import base_world, rid, snap

T = "2026-06-30T12:00:00Z"


def accepted_offer(oid="o1", app="a1", offered="2026-03-01", accepted="2026-03-05"):
    o = lc.Offer(id=oid, application_id=app, offered_on=offered)
    lc.transition(o, lc.ACCEPTED, actor="r", role="recruiter", business_date=accepted, recorded_at=T)
    return o


# ------------------------------------------------------------------ renege and rescission (event time)
def test_acceptance_then_renege_keeps_acceptance_and_counts_renege():
    o = accepted_offer()
    lc.transition(o, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-20", recorded_at=T, reason="reneged")
    assert o.status == lc.WITHDRAWN                                   # latest status says Withdrawn ...
    ev = om.event_metrics({"o1": o}, as_of="2026-04-01")
    assert ev["accepted"] == ["o1"] and ev["decided"] == ["o1"]      # ... but the acceptance event stands
    assert ev["renege"] == ["o1"] and ev["rescinded_after"] == []


def test_acceptance_then_company_rescission():
    o = accepted_offer()
    lc.transition(o, lc.RESCINDED, actor="hm", role="hiring_manager", business_date="2026-03-22", recorded_at=T, reason="role closed")
    ev = om.event_metrics({"o1": o}, as_of="2026-04-01")
    assert ev["accepted"] == ["o1"] and ev["rescinded_after"] == ["o1"] and ev["renege"] == []


def test_as_of_between_acceptance_and_renege():
    o = accepted_offer()
    lc.transition(o, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-20", recorded_at=T, reason="reneged")
    assert om.event_metrics({"o1": o}, as_of="2026-03-10")["renege"] == []      # renege not yet happened
    ev = om.event_metrics({"o1": o}, as_of="2026-03-03")                         # before the decision event
    assert ev["pending"] == ["o1"] and ev["decided"] == []


def test_withdrawal_or_rescission_before_decision_is_not_a_decision():
    w = lc.Offer(id="w", application_id="a1", offered_on="2026-03-01")
    lc.transition(w, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-04", recorded_at=T, reason="took other job")
    r = lc.Offer(id="r", application_id="a2", offered_on="2026-03-01")
    lc.transition(r, lc.RESCINDED, actor="hm", role="hiring_manager", business_date="2026-03-04", recorded_at=T, reason="budget")
    ev = om.event_metrics({"w": w, "r": r}, as_of="2026-04-01")
    assert ev["decided"] == [] and sorted(ev["resolved_without_decision"]) == ["r", "w"] and ev["pending"] == []


def test_superseded_offer_excluded_and_latest_counts():
    old = lc.Offer(id="o1", application_id="a1", offered_on="2026-03-01")
    new = lc.Offer(id="o2", application_id="a1", offered_on="2026-03-06")
    lc.create_revision(old, new, recorded_at=T)
    lc.transition(new, lc.ACCEPTED, actor="r", role="recruiter", business_date="2026-03-08", recorded_at=T)
    ev = om.event_metrics({"o1": old, "o2": new}, as_of="2026-04-01")
    assert ev["counted"] == ["o2"] and ev["accepted"] == ["o2"] and "o1" in ev["superseded"]


def test_corrected_legacy_decision_uses_corrected_business_date():
    o = lc.Offer(id="o1", application_id="a1", offered_on="2026-03-01")
    lc.correct(o, actor="ops", role="recruiting_ops_lead", recorded_at=T, reason="confirmed by email",
               status=lc.ACCEPTED, decision_outcome=lc.ACCEPTED, decision_on="2026-03-09")
    assert om.event_metrics({"o1": o}, as_of="2026-03-08")["decided"] == []
    assert om.event_metrics({"o1": o}, as_of="2026-03-09")["accepted"] == ["o1"]


def test_compute_rows_with_lifecycle_offers_use_event_time():
    w = base_world()                                     # applications rid(31) Hired, rid(32) Offer
    o1 = accepted_offer("x1", rid(31))
    lc.transition(o1, lc.WITHDRAWN, actor="r", role="recruiter", business_date="2026-03-20", recorded_at=T, reason="reneged")
    o2 = lc.Offer(id="x2", application_id=rid(32), offered_on="2026-03-01")
    lc.transition(o2, lc.DECLINED, actor="r", role="recruiter", business_date="2026-03-04", recorded_at=T, reason="Location")
    rows = {r["metric_id"]: r for r in om.compute(snap(**w), as_of="2026-04-01", offers={"x1": o1, "x2": o2})}
    assert (rows["OAM-01"]["numerator"], rows["OAM-01"]["denominator"]) == (1, 2)
    assert (rows["OAM-13a"]["numerator"], rows["OAM-13a"]["denominator"]) == (1, 1)
    assert rows["OAM-13a"]["measurability"] == "Measurable" and rows["OAM-13b"]["numerator"] == 0


def test_legacy_snapshot_marks_post_acceptance_metrics_not_measurable():
    rows = {r["metric_id"]: r for r in om.compute(snap(**base_world()))}
    assert rows["OAM-13a"]["value"] == "n/a" and rows["OAM-13a"]["measurability"] == "Not currently measurable"


def test_legacy_pending_with_decision_date_gets_no_decision_event():
    o = om.legacy_offer("k", {"Application": ["a"], "Status": "Pending", "Offered On": "2026-03-01", "Decision On": "2026-03-04"})
    assert o.events == [] and om.event_state(o, "2026-08-27")["decision"] is None


# ------------------------------------------------------------------ privacy is a configurable proposed policy
def test_privacy_threshold_is_configurable_and_labelled_proposed():
    w = base_world()
    rows5 = {r["metric_id"]: r for r in om.compute(snap(**w))}
    rows1 = {r["metric_id"]: r for r in om.compute(snap(**w), privacy_k=1)}
    k = next(x for x in rows5 if x.startswith("OAM-07"))
    assert "proposed policy k=5" in rows5[k]["privacy"] and "pending Acme privacy/legal approval" in rows5[k]["privacy"]
    assert rows1[k]["privacy"] != rows5[k]["privacy"]


def test_spec_does_not_present_privacy_as_regulatory_requirement():
    spec = Path("outputs/offer_acceptance_metric_spec.md").read_text()
    sec = spec[spec.index("### §3.14"):spec.index("### §3.13")]
    assert "requires Acme privacy/legal approval" in sec and "not presented as a regulatory requirement" in sec


# ------------------------------------------------------------------ roles are proposals
def test_roles_documented_as_proposals_with_customer_dependency():
    spec = Path("outputs/offer_acceptance_metric_spec.md").read_text()
    assert "proposed TalentFlow roles" in spec and "C-17" in spec
    assert "### C-17." in Path("outputs/open_questions_for_customer.md").read_text()
    assert "| ASM-031 |" in Path("audit/assumptions_register.md").read_text()


# ------------------------------------------------------------------ inactivity: per-stage, provisional 90 days
def test_inactivity_default_and_per_stage_override():
    cfg = inactivity.thresholds()
    assert set(cfg.values()) == {90}
    over = inactivity.thresholds({"Applied": 60})
    assert over["Applied"] == 60 and over["Screening"] == 90
    assert inactivity.flag("Applied", "2026-06-01", "2026-08-27", over) == "Inactive > 60 days"
    assert inactivity.flag("Screening", "2026-06-01", "2026-08-27", over) is None
    with pytest.raises(inactivity.ConfigError):
        inactivity.thresholds({"Applied": 7})
    with pytest.raises(inactivity.ConfigError):
        inactivity.thresholds({"Onboarding": 90})


def test_flag_is_never_abandonment_and_abandonment_needs_a_recruiter():
    label = inactivity.flag("Applied", "2026-01-01", "2026-08-27", inactivity.thresholds())
    assert "abandon" not in label.lower()
    with pytest.raises(inactivity.ConfigError):
        inactivity.dispose(label, "abandoned", None, "rec1")          # reason required
    with pytest.raises(inactivity.ConfigError):
        inactivity.dispose(label, "abandoned", "no reply to 3 emails", "")
    d = inactivity.dispose(label, "abandoned", "no reply to 3 emails", "rec1")
    assert d["by"] == "rec1" and d["reversible_days"] == 30


def test_pilot_and_stop_condition_retained():
    text = Path("outputs/phase3_product_strategy.md").read_text()
    assert "20 randomly sampled inactivity-flagged applications" in text and "Stop condition" in text


# ------------------------------------------------------------------ governance
def test_phase3_decisions_remain_proposals():
    log = Path("audit/decision_log.md").read_text()
    for n in range(25, 38):
        row = next(l for l in log.splitlines() if l.startswith(f"| DEC-0{n} |"))
        status = row.rstrip(" |").split(" | ")[-1]
        assert status.startswith(("Proposed", "**Superseded")), (n, status)
        assert "PM-approved" not in row.split(" | ")[3], n


def test_phase3_assumptions_not_marked_confirmed():
    reg = Path("audit/assumptions_register.md").read_text()
    for n in range(21, 32):
        row = next(l for l in reg.splitlines() if l.startswith(f"| ASM-0{n} |"))
        assert "Confirmed" not in row.rstrip(" |").split(" | ")[-1], n
