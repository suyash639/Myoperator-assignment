"""Phase 3.1 evidence: verifies each Phase 3.1 rule against the Phase 1 snapshot (read-only) and Phase 2.2 findings.

    uv run python -m src.phase3_1_evidence     # writes outputs/phase3_1_evidence.csv

Rows: evidence_id, check, numerator, denominator, phase2_2_ref, expected_match, detail.
`expected_match` names the Phase 2.2 count the rule must reproduce (blank where the row is new sensitivity evidence).
"""
from __future__ import annotations

import collections
import csv
import sys
from pathlib import Path

from src import audit, duplicate_warning as dw, inactivity, offer_lifecycle as lc
from src.data import AS_OF, days, load, one
from src.metrics import last_activity

OUT = Path("outputs/phase3_1_evidence.csv")


def rows() -> list[dict]:
    s = load()
    A, C, O, I, J = (s.f(t) for t in ("Applications", "Candidates", "Offers", "Interviews", "Job Openings"))
    out = []

    def add(eid, check, num, den, ref="", expect="", detail=""):
        out.append({"evidence_id": eid, "check": check, "numerator": num, "denominator": den,
                    "phase2_2_ref": ref, "expected_match": expect, "detail": detail})

    # B1 lifecycle invariants on legacy offers
    leg = lc.audit_legacy(s)
    pend = [k for k, o in O.items() if o["Status"] == "Pending"]
    add("E-B1-1", "Legacy offers violating the B1 invariants (flagged, not modified)", len(leg), len(O), "DQ-06;OAM-03c",
        "4 (the Pending offers with a Decision On)", "; ".join(f"{r['offer_business_id']}: {r['violations']}" for r in leg))
    add("E-B1-2", "Pending offers violating the 'no resolution date' invariant", sum(1 for r in leg if r["status"] == "Pending"),
        len(pend), "DQ-06", "4/5")
    add("E-B1-3", "Applications with more than one offer (revisions/superseded today)",
        sum(len(a.get("Offers", [])) > 1 for a in A.values()), sum(bool(a.get("Offers")) for a in A.values()), "R4-offers-per-app", "0/36")
    late = sum(1 for o in O.values() if o["Status"] in ("Accepted", "Declined") and o.get("Decision On", "") > AS_OF)
    add("E-D3-1", "Decided offers with Decision On after the provisional cutoff (pending at as-of)", late,
        sum(o["Status"] in ("Accepted", "Declined") for o in O.values()), "OAM-01", "0 (so OAM-01 stays 26/31)")

    # B2 inactivity threshold sensitivity
    act = [k for k, a in A.items() if a["Status"] == "Active"]
    for t in (30, 60, 90, 120, 180):
        add(f"E-B2-{t}", f"Active applications with no recorded activity for more than {t} days at {AS_OF}",
            sum(days(last_activity(A[k], I, O), AS_OF) > t for k in act), len(act), "DQ-28" if t == 90 else "",
            "50/105" if t == 90 else "")
    cfg = inactivity.thresholds()
    add("E-B2-cfg", "Active applications flagged with the per-stage config at the provisional default (90 days every stage)",
        sum(inactivity.flag(A[k]["Stage"], last_activity(A[k], I, O), AS_OF, cfg) is not None for k in act), len(act), "DQ-28", "50/105")
    cfg2 = inactivity.thresholds({"Applied": 60})
    add("E-B2-cfg-applied60", "Same, with only the Applied stage overridden to 60 days (other stages 90)",
        sum(inactivity.flag(A[k]["Stage"], last_activity(A[k], I, O), AS_OF, cfg2) is not None for k in act), len(act))
    by = collections.defaultdict(lambda: [0, 0])
    for k in act:
        by[A[k]["Stage"]][1] += 1
        by[A[k]["Stage"]][0] += days(last_activity(A[k], I, O), AS_OF) > 90
    for st, (n, d) in sorted(by.items()):
        add(f"E-B2-stage-{st}", f"Active at stage {st} inactive > 90 days", n, d, "DQ-28")
    dq11 = next(i for i in audit.run_checks(s) if i.id == "DQ-11")
    add("E-B2-req", "Openings with a status contradiction -> review flags (never auto-corrected)",
        dq11.affected, dq11.denominator, "DQ-11", "15/24", "Flag types: " + dq11.detail)

    # B3 duplicate warning on the snapshot
    pairs = dw.scan(s)
    add("E-B3-dup-1", "Name+phone groups the warning would fire on", len(pairs), len(C), "DQ-02", "6 groups / 12 records",
        "; ".join("/".join(C[x].get("Candidate ID", x) for x in p) for p in pairs))
    names = collections.Counter(dw.norm_name(c.get("Full Name", "")) for c in C.values())
    phones = collections.Counter(dw.norm_phone(c.get("Phone", "")) for c in C.values())
    add("E-B3-dup-2", "Name-only collision groups that would NOT warn (beyond name+phone groups)",
        sum(1 for v in names.values() if v > 1) - len(pairs), len(C), "R2-name-only", "0")
    add("E-B3-dup-3", "Phone-only collision groups that would NOT warn (beyond name+phone groups)",
        sum(1 for v in phones.values() if v > 1) - len(pairs), len(C), "R2-name-only", "0")
    cls = collections.Counter(dw.legacy_attribution(C[one(a, "Candidate")]["Source"], bool(a.get("Referred By"))) for a in A.values())
    for k, v in sorted(cls.items()):
        add(f"E-B3-src-{k}", f"Legacy applications classified as '{k}' under the new referral rules (not rewritten)", v, len(A), "DQ-01")
    hires = [a for a in A.values() if a["Stage"] == "Hired"]
    hc = collections.Counter(dw.legacy_attribution(C[one(a, "Candidate")]["Source"], bool(a.get("Referred By"))) for a in hires)
    for k, v in sorted(hc.items()):
        add(f"E-B3-hire-{k}", f"Hires classified as '{k}' under the new referral rules", v, len(hires), "M-A9n;M-A9r")
    return out


def main() -> int:
    r = rows()
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(r[0]))
        w.writeheader()
        w.writerows(r)
    for x in r:
        print(f"{x['evidence_id']:38} {x['numerator']}/{x['denominator']}  expect {x['expected_match']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
