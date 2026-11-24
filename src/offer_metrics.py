"""Reference implementation of the D3 offer-acceptance metric specification
(outputs/offer_acceptance_metric_spec.md) → outputs/offer_metric_baseline.csv.

    uv run python -m src.offer_metrics

Purpose: prove the specification is implementable exactly as written, and produce the Phase 3
baselines from the raw snapshot. Independent of src/metrics.py; tests reconcile the two.
Reads data/raw only through src.data.load (checksum-verified). No API calls.

Rules implemented (spec section references in brackets):
  eligibility   offer counted only if Offered On <= as_of                                   [§3.3]
  decided       Status in {Accepted, Declined} AND Decision On present AND Decision On <= as_of [§3.4]
  pending       pending AT as_of = Status Pending, OR decided with Decision On > as_of            [§3.5]
                Status Pending with a Decision On present -> flagged STATUS_DATE_CONFLICT
  revised       if an application has >1 offer, only the latest Offered On counts            [§3.6]
  prior hire    flagged, INCLUDED in the primary metric, excluded only in OAM-01b             [§3.7]
  period        decided offers attributed to the period of Decision On                       [§3.8]
  reliability   n < 10 counts only; 10 <= n < 30 rate with low-sample label; n >= 30 normal    [§3.12]
  privacy       PROPOSED, configurable policy (default k=5, pending Acme privacy/legal approval): breakdown
                cells with any count < k hidden from viewers without record access          [§3.14]
  event time    every metric is computed from the offer's event log at as_of (event_state), never from the
                latest status; a renege/rescission after acceptance does not erase the acceptance [§8.3]
                (a separate rule from reliability; applies to breakdown rows only)
"""
from __future__ import annotations

import collections
import csv
import statistics
import sys
from pathlib import Path

from src import offer_lifecycle as lc
from src.data import AS_OF, CUTOFF_SENSITIVITY, days, load, one

OUT = Path("outputs/offer_metric_baseline.csv")
MIN_N = 10        # reliability: below this, counts only (ASM-025)
LOW_N = 30        # reliability: below this, rate carries a low-sample label (ASM-025)
PRIVACY_K = 5     # PROPOSED privacy policy, configurable via compute(privacy_k=...). Requires Acme privacy/legal approval;
                  # not a confirmed regulatory requirement (DEC-034, ASM-028, C-18)
BREAKDOWN_PREFIXES = ("OAM-06-reason", "OAM-07", "OAM-08")
AGE_BUCKETS = [(0, 14, "0-14d"), (15, 30, "15-30d"), (31, 60, "31-60d"), (61, 10 ** 6, ">60d")]
DECIDED, VALID = {"Accepted", "Declined"}, {"Accepted", "Declined", "Pending"}


def half(d: str) -> str:
    return f"{d[:4]}-H{1 if int(d[5:7]) <= 6 else 2}"


def legacy_offer(k: str, f: dict) -> lc.Offer:
    """Convert a legacy (Airtable) offer into the B1 lifecycle model with SYNTHESISED events.
    A decision event is created only when Status is Accepted/Declined AND Decision On is present. A Pending
    offer that carries a Decision On gets NO decision event (it stays pending and is flagged as a conflict)."""
    st = f.get("Status")
    o = lc.Offer(id=k, application_id=one(f, "Application"), offered_on=f.get("Offered On", ""), status=st,
                 decision_on=f.get("Decision On"), decline_reason=f.get("Decline Reason"),
                 decision_outcome=st if st in DECIDED else None)
    if st in DECIDED and f.get("Decision On"):
        o.events.append({"offer_id": k, "event_type": "legacy_import", "from_status": lc.PENDING, "to_status": st,
                         "actor": "legacy", "role": "system", "business_date": f["Decision On"], "recorded_at": None,
                         "reason": f.get("Decline Reason")})
    return o


def event_state(o: lc.Offer, as_of: str) -> dict:
    """State of one offer AT as_of, reconstructed from its event log in event (business-date) order.
    Never reads the latest status: a later renege or rescission cannot erase an earlier acceptance event."""
    st = {"offered": bool(o.offered_on) and o.offered_on <= as_of, "decision": None, "decision_on": None,
          "post_acceptance": None, "post_acceptance_on": None, "resolved_without_decision": None, "superseded": False}
    evs = []
    for e in o.events:
        if e["event_type"] == "correction":
            a = e.get("after", {})
            if a.get("decision_outcome") in DECIDED and a.get("decision_on"):
                evs.append((a["decision_on"], lc.PENDING, a["decision_outcome"]))
            continue
        if e.get("business_date"):
            evs.append((e["business_date"], e["from_status"], e["to_status"]))
    for d, frm, to in sorted(evs):
        if d > as_of:
            continue
        if to in DECIDED and not (st["decision"] or st["resolved_without_decision"] or st["superseded"]):
            st["decision"], st["decision_on"] = to, d
        elif frm == lc.ACCEPTED and to in (lc.WITHDRAWN, lc.RESCINDED):
            st["post_acceptance"] = "renege" if to == lc.WITHDRAWN else "rescinded_after_acceptance"
            st["post_acceptance_on"] = d
        elif to == lc.SUPERSEDED:
            st["superseded"] = True
        elif frm == lc.PENDING and to in (lc.EXPIRED, lc.WITHDRAWN, lc.RESCINDED):
            st["resolved_without_decision"] = to
    return st


def event_metrics(offers: dict[str, lc.Offer], as_of: str = AS_OF) -> dict:
    """Core D3 sets at as_of (spec §3.3-§3.6, §8.3), computed only from event-time state."""
    state = {k: event_state(o, as_of) for k, o in offers.items()}
    elig = [k for k in offers if state[k]["offered"]]
    by_app = collections.defaultdict(list)
    for k in elig:
        by_app[offers[k].application_id].append(k)
    earlier = {k for ks in by_app.values() if len(ks) > 1 for k in sorted(ks, key=lambda x: (offers[x].offered_on, x))[:-1]}
    sup = {k for k in elig if state[k]["superseded"]} | earlier
    counted = [k for k in elig if k not in sup]
    decided = [k for k in counted if state[k]["decision"]]
    accepted = [k for k in decided if state[k]["decision"] == lc.ACCEPTED]
    return {"state": state, "eligible": elig, "superseded": sup, "revised_earlier": earlier, "counted": counted,
            "decided": decided, "accepted": accepted,
            "pending": [k for k in counted if not state[k]["decision"] and not state[k]["resolved_without_decision"]],
            "resolved_without_decision": [k for k in counted if state[k]["resolved_without_decision"]],
            "renege": [k for k in accepted if state[k]["post_acceptance"] == "renege"],
            "rescinded_after": [k for k in accepted if state[k]["post_acceptance"] == "rescinded_after_acceptance"]}


def compute(s=None, as_of: str = AS_OF, offers: dict[str, lc.Offer] | None = None, privacy_k: int = PRIVACY_K) -> list[dict]:
    """D3 metrics. `offers` (lifecycle Offer objects with event logs) replaces the legacy conversion, as after B1;
    `privacy_k` is the configurable proposed privacy policy (DEC-034, ASM-028)."""
    s = s or load()
    A, C, O, J, D = (s.f(t) for t in ("Applications", "Candidates", "Offers", "Job Openings", "Departments"))
    legacy = offers is None
    offers = offers if offers is not None else {k: legacy_offer(k, f) for k, f in O.items()}
    rows: list[dict] = []

    def add(mid, name, grain, num, den, measurability, caveat="", notes="", value=None):
        is_rate = value is None
        if is_rate:
            value = f"{100 * num / den:.1f}%" if den else ""
        if not is_rate:
            display = "count (no rate)"
        elif not isinstance(den, int) or den < MIN_N:
            display = f"counts only (n<{MIN_N}: reliability)"
        elif den < LOW_N:
            display = f"rate with low-sample label (n<{LOW_N}; 1 {'candidate' if grain == 'candidate' else 'offer'} = {100 / den:.1f} pp)"
        else:
            display = "rate"
        privacy = "none (not a breakdown)"
        if mid.startswith(BREAKDOWN_PREFIXES):
            cells = [x for x in (num, den, (den - num) if isinstance(num, int) and isinstance(den, int) else None) if isinstance(x, int)]
            privacy = (f"restricted under proposed policy k={privacy_k} (pending Acme privacy/legal approval)"
                       if any(c < privacy_k for c in cells) else f"none under proposed policy k={privacy_k}")
        rows.append({"metric_id": mid, "metric": name, "grain": grain, "as_of": as_of, "numerator": num,
                     "denominator": den, "value": value, "display": display, "privacy": privacy,
                     "measurability": measurability, "caveat": caveat, "notes": notes})

    ev = event_metrics(offers, as_of)
    stt = ev["state"]
    counted, decided, accepted, pending = ev["counted"], ev["decided"], ev["accepted"], ev["pending"]
    acc, dec = len(accepted), len(decided) - len(accepted)
    status = lambda k: offers[k].status
    invalid = [k for k in counted if status(k) not in lc.STATUSES]
    decided_no_date = [k for k in counted if status(k) in DECIDED and not offers[k].decision_on]
    decided_later = [k for k in counted if status(k) in DECIDED and offers[k].decision_on and offers[k].decision_on > as_of]
    conflict = [k for k in pending if status(k) == lc.PENDING and offers[k].decision_on]
    app_offers = collections.defaultdict(list)
    for k, o in offers.items():
        app_offers[o.application_id].append(k)

    def prior_hire(k):
        a_id = offers[k].application_id
        for x in C[one(A[a_id], "Candidate")]["Applications"]:
            if x != a_id and A[x]["Stage"] == "Hired":
                for ok in app_offers.get(x, []):
                    d = event_state(offers[ok], as_of)
                    if d["decision"] == lc.ACCEPTED and d["decision_on"] < offers[k].offered_on:
                        return True
        return False

    ph = {k for k in decided if prior_hire(k)}
    dq_caveat = (f"Event-time decisions; {len(conflict)} Pending offers carry a Decision On (STATUS_DATE_CONFLICT, DQ-06); "
                 "reporting cutoff unconfirmed (DEC-020)")
    sup = ev["superseded"]
    add("OAM-01", "Decided Offer Acceptance Rate (PRIMARY): accepted at the decision event", "offer", acc, len(decided),
        "Measurable with a data-quality caveat", dq_caveat,
        f"eligible offers {len(ev['eligible'])}; superseded (revised) {len(sup)} "
        f"[pending earlier offers -> SUPERSEDED {sum(1 for k in sup if not stt[k]['decision'] and not stt[k]['resolved_without_decision'])}; "
        f"resolved earlier offers -> REVISED_AFTER_RESOLUTION {sum(1 for k in sup if stt[k]['decision'] or stt[k]['resolved_without_decision'])}]; "
        f"invalid status {len(invalid)}; decided without Decision On {len(decided_no_date)}; "
        f"decided after as-of (pending at as-of) {len(decided_later)}; offers to previously hired candidates in denominator {len(ph)}; "
        f"accepted then reneged/rescinded (still counted as accepted) {len(ev['renege']) + len(ev['rescinded_after'])}")
    ex = [k for k in decided if k not in ph]
    add("OAM-01b", "Decided Offer Acceptance Rate excluding offers to previously hired candidates (variant)", "offer",
        sum(stt[k]["decision"] == lc.ACCEPTED for k in ex), len(ex), "Measurable with a data-quality caveat",
        "Variant only; whether these are internal moves is unconfirmed (C-08)")
    add("OAM-02", "All-Issued Offer Acceptance Ratio", "offer", acc, len(counted),
        "Measurable with a data-quality caveat", "Pending offers in the denominator; not a decided-offer rate")
    add("OAM-03", "Pending offer count", "offer", len(pending), len(counted), "Measurable with a data-quality caveat",
        f"{len(conflict)} of these carry a Decision On", value=str(len(pending)))
    add("OAM-03c", "Pending offers with STATUS_DATE_CONFLICT", "offer", len(conflict), len(pending),
        "Measurable", "Data-quality indicator, not an outcome")
    ages = {k: days(offers[k].offered_on, as_of) for k in pending}
    for lo, hi, lbl in AGE_BUCKETS:
        n = sum(lo <= a <= hi for a in ages.values())
        add(f"OAM-04-{lbl}", f"Pending offer ageing: {lbl}", "offer", n, len(pending), "Measurable with a data-quality caveat",
            "Age depends on the unconfirmed cutoff (DEC-020)", value=str(n))
    add("OAM-04-max", "Pending offer ageing: oldest (days)", "offer", "", len(pending), "Measurable with a data-quality caveat",
        "Cutoff-dependent", value=str(max(ages.values(), default="")))
    for cut in CUTOFF_SENSITIVITY:
        add(f"OAM-04-over30-{cut}", f"Pending offers older than 30 days at cutoff {cut}", "offer",
            sum(days(offers[k].offered_on, cut) > 30 for k in pending), len(pending),
            "Measurable with a data-quality caveat", "Cutoff sensitivity", value=None)
    tt = sorted(days(offers[k].offered_on, stt[k]["decision_on"]) for k in decided)
    add("OAM-05", "Decision turnaround, median days (Offered On -> decision event, decided offers)", "offer", "", len(tt),
        "Measurable", "Only offers with a decision event; pending conflicts excluded",
        f"p75 {tt[int(0.75 * (len(tt) - 1))]}; min {tt[0]}; max {tt[-1]}" if tt else "no decided offers",
        value=str(statistics.median(tt)) if tt else "")
    add("OAM-06", "Offer Decline Rate", "offer", dec, len(decided), "Measurable with a data-quality caveat", dq_caveat)
    reasons = collections.Counter(offers[k].decline_reason or "(missing)" for k in decided if stt[k]["decision"] == lc.DECLINED)
    for r, n in reasons.most_common():
        add(f"OAM-06-reason-{r}", f"Declined offers with recorded Decline Reason: {r}", "offer", n, dec, "Measurable",
            "Counts only; reasons are as recorded, not explanations", value=str(n))
    rwd = ev["resolved_without_decision"]
    add("OAM-06x", "Offers resolved without a decision (Expired / Withdrawn / Rescinded before deciding)", "offer", len(rwd), len(counted),
        "Measurable" if not legacy else "Not currently measurable",
        "Legacy data has no such statuses; measurable after B1" if legacy else "",
        "; ".join(f"{x}={n}" for x, n in collections.Counter(stt[k]["resolved_without_decision"] for k in rwd).items()),
        value=None if not legacy else "n/a")
    for mid, key, label in (("OAM-13a", "renege", "Post-acceptance reneging rate (candidate withdrew after accepting)"),
                            ("OAM-13b", "rescinded_after", "Post-acceptance rescission rate (company rescinded after acceptance)")):
        if legacy:
            add(mid, label, "offer", "", acc, "Not currently measurable",
                "Legacy data cannot represent a withdrawal or rescission after acceptance; measurable after B1. The acceptance stays in OAM-01",
                value="n/a")
        else:
            add(mid, label, "offer", len(ev[key]), acc, "Measurable",
                "Denominator = offers accepted at a decision event on or before as-of; event dated on or before as-of",
                "; ".join(ev[key]))
    dept = lambda k: D[one(J[one(A[offers[k].application_id], "Opening")], "Department")]["Name"]
    by_d = collections.defaultdict(list)
    for k in decided:
        by_d[dept(k)].append(k)
    for dn in sorted(by_d):
        ks = by_d[dn]
        add(f"OAM-07-{dn}", f"Decided Offer Acceptance Rate: {dn}", "offer", sum(stt[k]["decision"] == lc.ACCEPTED for k in ks), len(ks),
            "Measurable; not interpretable at current volume", "Reliability tiers and proposed privacy policy apply")
    by_p = collections.defaultdict(list)
    for k in decided:
        by_p[half(stt[k]["decision_on"])].append(k)
    for p in sorted(by_p):
        ks = by_p[p]
        add(f"OAM-08-{p}", f"Decided Offer Acceptance Rate, decisions in {p}", "offer", sum(stt[k]["decision"] == lc.ACCEPTED for k in ks),
            len(ks), "Measurable with a data-quality caveat", "Period by decision-event date")
    cand = collections.defaultdict(set)
    for k in decided:
        cand[one(A[offers[k].application_id], "Candidate")].add(stt[k]["decision"])
    add("OAM-09", "Candidate-level decided acceptance (SECONDARY; never combined with OAM-01)", "candidate",
        sum(lc.ACCEPTED in v for v in cand.values()), len(cand), "Measurable with a data-quality caveat",
        "Different grain from OAM-01")
    add("OAM-10", "Accepted offers whose application is not Stage=Hired (consistency check)", "offer",
        sum(1 for k in accepted if A[offers[k].application_id]["Stage"] != "Hired"), acc,
        "Measurable", "Data-quality indicator")
    add("OAM-11", "Reason a candidate declined beyond the recorded Decline Reason category", "offer", "", "",
        "Not currently measurable", "No free-text or structured decline detail beyond one category per offer", value="n/a")
    add("OAM-12", "Offer expiry adherence", "offer", "", "", "Not currently measurable",
        "No expiry date field and no Expired status exist (DQ-07); requires Build B1", value="n/a")
    return rows


def main() -> int:
    rows = compute()
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['metric_id']:32} {str(r['numerator']):>4}/{str(r['denominator']):<4} {r['value']:>7}  {r['display'][:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
