"""Relationship integrity → outputs/relationship_integrity.csv.

Airtable linked-record fields are arrays of record IDs, normally kept in sync on both sides
(a link A.x → B implies B.y contains A). For each relationship we check:
  orphans          IDs on the forward side that do not exist in the target table
  asymmetric       forward link present but the target's back-link does not list the source
  reverse_unmatched  back-link lists a source that does not link forward
  reverse_orphans  back-link IDs absent from the source table
  cardinality      distribution of #links per source record vs the expected cardinality
"""
from __future__ import annotations

import collections

from src.data import Snapshot

# (source table, forward field, target table, back-link field, expected cardinality, required?)
RELATIONSHIPS = [
    ("Applications", "Candidate", "Candidates", "Applications", "exactly 1", True),
    ("Applications", "Opening", "Job Openings", "Applications", "exactly 1", True),
    ("Applications", "Recruiter", "People", "Applications as Recruiter", "exactly 1", True),
    ("Applications", "Referred By", "People", "Referrals Made", "0..1", False),
    ("Interviews", "Application", "Applications", "Interviews", "exactly 1", True),
    ("Interviews", "Interviewer", "People", "Interviews", "exactly 1", True),
    ("Offers", "Application", "Applications", "Offers", "exactly 1", True),
    ("Job Openings", "Department", "Departments", "Job Openings", "exactly 1", True),
    ("Job Openings", "Recruiter", "People", "Reqs as Recruiter", "exactly 1", True),
    ("Job Openings", "Hiring Manager", "People", "Reqs as Hiring Manager", "exactly 1", True),
    ("People", "Department", "Departments", "People", "exactly 1", True),
]


def check_relationships(snap: Snapshot) -> list[dict]:
    rows = []
    for st, sf, tt, tf, card_exp, required in RELATIONSHIPS:
        S, T = snap.f(st), snap.f(tt)
        links = orphans = asym = 0
        orphan_ids, asym_ids, card_bad = [], [], []
        card = collections.Counter()
        for rid, f in S.items():
            v = f.get(sf) or []
            card[len(v)] += 1
            if (required and len(v) != 1) or (not required and len(v) > 1):
                card_bad.append(rid)
            for x in v:
                links += 1
                if x not in T:
                    orphans += 1
                    orphan_ids.append(f"{rid}->{x}")
                elif rid not in (T[x].get(tf) or []):
                    asym += 1
                    asym_ids.append(f"{rid}->{x}")
        rev_unmatched = [f"{tid}->{s}" for tid, t in T.items() for s in (t.get(tf) or [])
                         if s in S and tid not in (S[s].get(sf) or [])]
        rev_orph = [f"{tid}->{s}" for tid, t in T.items() for s in (t.get(tf) or []) if s not in S]
        ok = not (orphans or asym or rev_unmatched or rev_orph or card_bad)
        rows.append({
            "relationship": f"{st}.{sf} -> {tt}", "back_link": f"{tt}.{tf}",
            "source_records": len(S), "links": links, "expected_cardinality": card_exp,
            "cardinality_observed": "; ".join(f"{k} link(s): {c}" for k, c in sorted(card.items())),
            "cardinality_violations": len(card_bad),
            "orphans": orphans, "asymmetric": asym,
            "reverse_unmatched": len(rev_unmatched), "reverse_orphans": len(rev_orph),
            "status": "PASS" if ok else "FAIL",
            "evidence": "; ".join((orphan_ids + asym_ids + rev_unmatched + rev_orph + card_bad)[:20]),
        })
    return rows


def coverage(snap: Snapshot) -> list[dict]:
    """Records with no inbound/outbound link where one is expected."""
    A, C, J = snap.f("Applications"), snap.f("Candidates"), snap.f("Job Openings")
    linked_c = {a["Candidate"][0] for a in A.values() if a.get("Candidate")}
    linked_j = {a["Opening"][0] for a in A.values() if a.get("Opening")}
    return [
        {"relationship": "Candidates without any Application", "back_link": "",
         "source_records": len(C), "links": "", "expected_cardinality": ">=1",
         "cardinality_observed": "", "cardinality_violations": len(set(C) - linked_c),
         "orphans": 0, "asymmetric": 0, "reverse_unmatched": 0, "reverse_orphans": 0,
         "status": "PASS" if not set(C) - linked_c else "FAIL",
         "evidence": "; ".join(sorted(set(C) - linked_c)[:20])},
        {"relationship": "Candidates referenced by Applications but missing from snapshot", "back_link": "",
         "source_records": len(linked_c), "links": "", "expected_cardinality": "0 missing",
         "cardinality_observed": "", "cardinality_violations": len(linked_c - set(C)),
         "orphans": len(linked_c - set(C)), "asymmetric": 0, "reverse_unmatched": 0, "reverse_orphans": 0,
         "status": "PASS" if not linked_c - set(C) else "FAIL",
         "evidence": "; ".join(sorted(linked_c - set(C))[:20])},
        {"relationship": "Job Openings without any Application", "back_link": "",
         "source_records": len(J), "links": "", "expected_cardinality": ">=0 (informational)",
         "cardinality_observed": "", "cardinality_violations": 0,
         "orphans": 0, "asymmetric": 0, "reverse_unmatched": 0, "reverse_orphans": 0,
         "status": "INFO", "evidence": f"{len(set(J) - linked_j)} openings with zero applications"},
    ]
