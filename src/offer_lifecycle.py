"""B1 offer lifecycle: executable reference model (specification for engineering, not product code).

Defines the offer statuses, allowed transitions, who may trigger each, which dates are recorded, the field
invariants that make contradictory records impossible, and the append-only audit event. Tests in
tests/test_phase3_1.py exercise every rule; `audit_legacy()` applies the invariants to the Phase 1 snapshot
read-only and must flag exactly the Phase 2.2 conflicts (DQ-06 / OAM-03c).

Two date kinds are recorded on every event:
  business_date  the date the event happened in the real world (entered or system-derived), used by metrics
  recorded_at    system timestamp of the write, never editable, used for audit and as-of reconstruction
"""
from __future__ import annotations

from dataclasses import dataclass, field

PENDING, ACCEPTED, DECLINED = "Pending", "Accepted", "Declined"
EXPIRED, WITHDRAWN, RESCINDED, SUPERSEDED = "Expired", "Withdrawn", "Rescinded", "Superseded"
STATUSES = [PENDING, ACCEPTED, DECLINED, EXPIRED, WITHDRAWN, RESCINDED, SUPERSEDED]
TERMINAL = {DECLINED, EXPIRED, WITHDRAWN, RESCINDED, SUPERSEDED}   # Accepted is terminal except for renege/rescind

ROLES = {"recruiter", "hiring_manager", "recruiting_ops_lead", "system"}

# (from, to): (allowed roles, business-date field set, reason required, note)
TRANSITIONS = {
    (PENDING, ACCEPTED):   ({"recruiter", "recruiting_ops_lead"}, "decision_on", False, "Candidate accepted"),
    (PENDING, DECLINED):   ({"recruiter", "recruiting_ops_lead"}, "decision_on", True, "Candidate declined; decline_reason from controlled list"),
    (PENDING, EXPIRED):    ({"recruiter", "recruiting_ops_lead", "system"}, "expired_on", False,
                            "Offer lapsed without a decision. 'system' only when expires_on is set and auto-expiry is enabled (conditional scope, C-03)"),
    (PENDING, WITHDRAWN):  ({"recruiter", "recruiting_ops_lead"}, "withdrawn_on", True, "Candidate withdrew before deciding"),
    (PENDING, RESCINDED):  ({"hiring_manager", "recruiting_ops_lead"}, "rescinded_on", True, "Company withdrew the offer before a decision"),
    (PENDING, SUPERSEDED): ({"system"}, "superseded_on", False,
                            "Set automatically when a new offer is created on the same application; superseded_on = new offer's offered_on"),
    (ACCEPTED, WITHDRAWN): ({"recruiter", "recruiting_ops_lead"}, "withdrawn_on", True, "Candidate reneged after accepting; decision is retained"),
    (ACCEPTED, RESCINDED): ({"hiring_manager", "recruiting_ops_lead"}, "rescinded_on", True, "Company rescinded after acceptance; decision is retained"),
}
DATE_FIELDS = ["decision_on", "expired_on", "withdrawn_on", "rescinded_on", "superseded_on"]


class LifecycleError(ValueError):
    pass


@dataclass
class Offer:
    id: str
    application_id: str
    offered_on: str
    status: str = PENDING
    decision_outcome: str | None = None      # Accepted/Declined, set once, immutable afterwards
    decision_on: str | None = None
    expired_on: str | None = None
    withdrawn_on: str | None = None
    rescinded_on: str | None = None
    superseded_on: str | None = None
    superseded_by: str | None = None
    expires_on: str | None = None
    decline_reason: str | None = None
    events: list[dict] = field(default_factory=list)


def violations(o: Offer) -> list[str]:
    """Field invariants. Any non-empty result means the record is contradictory."""
    v = []
    if o.status not in STATUSES:
        v.append(f"invalid status {o.status}")
    dates = {f: getattr(o, f) for f in DATE_FIELDS}
    if o.status == PENDING and any(dates.values()):
        v.append("Pending offer carries a resolution date: " + ", ".join(f for f, d in dates.items() if d))
    if o.status in (ACCEPTED, DECLINED):
        if not o.decision_on:
            v.append(f"{o.status} without decision_on")
        if o.decision_outcome != o.status:
            v.append("decision_outcome does not match status")
    if o.status == DECLINED and not o.decline_reason:
        v.append("Declined without decline_reason")
    if o.status == EXPIRED and (not o.expired_on or o.decision_on):
        v.append("Expired requires expired_on and no decision_on")
    if o.status == SUPERSEDED and (not o.superseded_by or not o.superseded_on or o.decision_on):
        v.append("Superseded requires superseded_by, superseded_on and no decision_on")
    if o.status == WITHDRAWN and not o.withdrawn_on:
        v.append("Withdrawn without withdrawn_on")
    if o.status == RESCINDED and not o.rescinded_on:
        v.append("Rescinded without rescinded_on")
    if o.status in (WITHDRAWN, RESCINDED) and o.decision_on and o.decision_outcome != ACCEPTED:
        v.append("only a previously Accepted offer may keep decision_on after withdrawal/rescission")
    for f, d in dates.items():
        if d and d < o.offered_on:
            v.append(f"{f} before offered_on")
    return v


def transition(o: Offer, to: str, *, actor: str, role: str, business_date: str, recorded_at: str,
               reason: str | None = None, superseded_by: str | None = None) -> Offer:
    """Apply one transition, enforcing role, dates and invariants, and append the audit event."""
    key = (o.status, to)
    if key not in TRANSITIONS:
        raise LifecycleError(f"transition {o.status} -> {to} not allowed")
    roles, date_field, needs_reason, _ = TRANSITIONS[key]
    if role not in roles:
        raise LifecycleError(f"role {role} may not perform {o.status} -> {to}")
    if needs_reason and not reason:
        raise LifecycleError(f"{o.status} -> {to} requires a reason")
    if business_date < o.offered_on:
        raise LifecycleError("business_date before offered_on")
    if business_date > recorded_at[:10]:
        raise LifecycleError("business_date in the future relative to recorded_at")
    if to == SUPERSEDED and not superseded_by:
        raise LifecycleError("Superseded requires superseded_by")
    before = o.status
    setattr(o, date_field, business_date)
    if to in (ACCEPTED, DECLINED):
        o.decision_outcome = to
    if to == DECLINED:
        o.decline_reason = reason
    if to == SUPERSEDED:
        o.superseded_by = superseded_by
    o.status = to
    bad = violations(o)
    if bad:
        raise LifecycleError("; ".join(bad))
    o.events.append({"offer_id": o.id, "event_type": "system" if role == "system" else "transition",
                     "from_status": before, "to_status": to, "actor": actor, "role": role,
                     "business_date": business_date, "recorded_at": recorded_at, "reason": reason})
    return o


def correct(o: Offer, *, actor: str, role: str, recorded_at: str, reason: str, **fields) -> Offer:
    """Audited correction of a legacy or mistaken record (recruiting ops lead only). Before/after values are logged."""
    if role != "recruiting_ops_lead":
        raise LifecycleError("only recruiting_ops_lead may correct records")
    if not reason:
        raise LifecycleError("correction requires a reason")
    before = {k: getattr(o, k) for k in fields}
    for k, val in fields.items():
        setattr(o, k, val)
    bad = violations(o)
    if bad:
        for k, val in before.items():
            setattr(o, k, val)
        raise LifecycleError("correction leaves record contradictory: " + "; ".join(bad))
    o.events.append({"offer_id": o.id, "event_type": "correction", "from_status": before.get("status", o.status),
                     "to_status": o.status, "actor": actor, "role": role, "business_date": None,
                     "recorded_at": recorded_at, "reason": reason, "before": before, "after": dict(fields)})
    return o


def create_revision(old: Offer, new: Offer, *, recorded_at: str) -> None:
    """A new offer on the same application supersedes a Pending one; an Accepted one must be rescinded/withdrawn first.
    A Declined/Expired/Withdrawn/Rescinded offer keeps its status; the metric counts only the latest offer per application."""
    if new.application_id != old.application_id:
        raise LifecycleError("revision must be on the same application")
    if old.status == ACCEPTED:
        raise LifecycleError("cannot revise an Accepted offer; withdraw or rescind it first")
    if new.offered_on < old.offered_on:
        raise LifecycleError("revision offered before the original")
    if old.status == PENDING:
        transition(old, SUPERSEDED, actor="system", role="system", business_date=new.offered_on,
                   recorded_at=recorded_at, superseded_by=new.id)


def status_at(o: Offer, as_of: str) -> str:
    """Status as of a business date, reconstructed from the event log (used by metrics for as-of consistency)."""
    s = PENDING
    for e in o.events:
        if e["event_type"] != "correction" and e["business_date"] and e["business_date"] <= as_of:
            s = e["to_status"]
    return s if o.offered_on <= as_of else "not yet offered"


def audit_legacy(snapshot) -> list[dict]:
    """Apply the invariants to the snapshot's Offers (read-only). Legacy records are flagged, never modified."""
    out = []
    for k, f in snapshot.f("Offers").items():
        o = Offer(id=k, application_id=(f.get("Application") or [None])[0], offered_on=f.get("Offered On", ""),
                  status=f.get("Status"), decision_on=f.get("Decision On"), decline_reason=f.get("Decline Reason"),
                  decision_outcome=f.get("Status") if f.get("Status") in (ACCEPTED, DECLINED) else None)
        v = violations(o)
        if v:
            out.append({"offer_id": k, "offer_business_id": f.get("Offer ID", ""), "status": o.status, "violations": "; ".join(v)})
    return out


def transition_table_md() -> str:
    """Markdown transition table; the D3/B1 specification must contain it verbatim (checked by phase3_checks)."""
    lines = ["| From | To | Who can trigger | Business date recorded | Reason required | Meaning |", "|---|---|---|---|---|---|"]
    for (a, b), (roles, d, r, note) in TRANSITIONS.items():
        lines.append(f"| {a} | {b} | {', '.join(sorted(roles))} | `{d}` | {'yes' if r else 'no'} | {note} |")
    return "\n".join(lines)
