"""Data-quality and business-logic checks → issues for outputs/data_quality_audit.md and findings_table.csv.

Every check returns an Issue with the affected record IDs, a denominator, a classification
and the business impact. Nothing is corrected: the treatment column says how downstream
metrics handle the issue, and metrics.py implements that as sensitivity variants.

Classification
  Confirmed defect       values contradict each other or are impossible; at least one is wrong
  Suspicious pattern     unusual and likely wrong, but a legitimate explanation exists
  Legitimate business    real-world behaviour that the data represents correctly
  Model limitation       data is internally consistent, but the schema cannot express something needed
  Informational          context needed to interpret other findings
Severity
  Critical  changes a VP-claim verdict or a headline metric
  High      materially biases a funnel, hire or cycle-time metric
  Medium    affects a secondary metric or a single table's reliability
  Low       no material metric impact; hygiene
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field

from src.data import AS_OF, CUTOFF_SENSITIVITY, EXTRACTION_DATE, Snapshot, days, one
from src.metrics import STALL_DAYS, last_activity


@dataclass
class Issue:
    id: str
    title: str
    classification: str
    table: str
    affected: int
    denominator: int
    denominator_desc: str
    severity: str
    metric_impacted: str
    decision_impacted: str
    treatment: str
    method: str
    evidence: list[str] = field(default_factory=list)
    detail: str = ""

    @property
    def pct(self) -> float:
        return round(100 * self.affected / self.denominator, 1) if self.denominator else 0.0

    def row(self) -> dict:
        return {"issue_id": self.id, "title": self.title, "classification": self.classification,
                "table": self.table, "affected_records": self.affected, "denominator": self.denominator,
                "denominator_desc": self.denominator_desc, "pct_affected": self.pct,
                "severity": self.severity, "metric_impacted": self.metric_impacted,
                "decision_impacted": self.decision_impacted, "treatment": self.treatment,
                "method": self.method, "detail": self.detail,
                "evidence_record_ids": "; ".join(self.evidence)}


def run_checks(s: Snapshot) -> list[Issue]:
    C, A, I, O, J, P, D = (s.f(t) for t in ["Candidates", "Applications", "Interviews", "Offers",
                                             "Job Openings", "People", "Departments"])
    out: list[Issue] = []
    offer_of = lambda a: O[one(a, "Offers")] if a.get("Offers") else None
    src_of = lambda a: C[one(a, "Candidate")]["Source"]

    # DQ-01 Source vs Referred By
    referred = [k for k, a in A.items() if a.get("Referred By")]
    ref_not_src = [k for k in referred if src_of(A[k]) != "Referral"]
    src_no_ref = [k for k, a in A.items() if src_of(a) == "Referral" and not a.get("Referred By")]
    by_src = collections.Counter(src_of(A[k]) for k in ref_not_src)
    out.append(Issue(
        "DQ-01", "Candidate Source contradicts the application's Referred By link", "Confirmed defect",
        "Applications/Candidates", len(ref_not_src) + len(src_no_ref), len(A), "applications",
        "Critical", "Hires by channel (VP claim A); channel conversion",
        "Job-board integration prioritisation",
        "Do not overwrite. Primary reported attribution is Source as recorded (DEC-017); referrer override (M-A2) and strict referral (M-A9) are reported as sensitivity.",
        "Applications with Referred By where candidate Source != 'Referral', plus Source='Referral' applications with no Referred By.",
        sorted(ref_not_src + src_no_ref),
        f"{len(referred)} applications have a referrer; only {len(referred) - len(ref_not_src)} have Source=Referral. "
        f"Referred but labelled {dict(by_src)}. {len(src_no_ref)} Source=Referral applications have no referrer. "
        f"Hire level: {sum(1 for k in src_no_ref if A[k]['Stage'] == 'Hired')} of {sum(1 for k, a in A.items() if a['Stage'] == 'Hired' and src_of(a) == 'Referral')} "
        f"Source=Referral hires have no referrer; {sum(1 for k in referred if A[k]['Stage'] == 'Hired')} hires have a referrer link."))

    # DQ-02 probable duplicate candidates
    grp = collections.defaultdict(list)
    for k, c in C.items():
        grp[(c["Full Name"].strip().lower(), c["Phone"].replace(" ", ""))].append(k)
    dups = [ids for ids in grp.values() if len(ids) > 1]
    src_diff = [ids for ids in dups if len({C[i]["Source"] for i in ids}) > 1]
    exp_diff = [ids for ids in dups if len({C[i]["Years Experience"] for i in ids}) > 1]
    same = lambda ids, f: len({C[i].get(f) for i in ids}) == 1
    dom = lambda k: C[k].get("Email", "@").split("@")[1]
    fpat = [k for k, c in C.items() if c.get("Email") and len(c["Email"].split("@")[0].split(".")[0]) == 1]
    pair_txt, implaus = [], 0
    for ids in dups:
        a_, b_ = sorted(ids, key=lambda k: C[k]["Created On"])
        gap_y = abs(C[a_]["Years Experience"] - C[b_]["Years Experience"])
        apart = days(C[a_]["Created On"], C[b_]["Created On"])
        ok = gap_y <= apart / 365 + 0.5
        implaus += not ok
        pair_txt.append(f"{C[a_].get('Candidate ID', a_)}/{C[b_].get('Candidate ID', b_)}: Source {C[a_]['Source']}/{C[b_]['Source']}, "
                        f"YoE {C[a_]['Years Experience']}/{C[b_]['Years Experience']} created {apart}d apart "
                        f"({'plausible' if ok else 'implausible for one person'})")
    out.append(Issue(
        "DQ-02", "Probable duplicate candidate records (same name + phone, different email)", "Suspicious pattern",
        "Candidates", sum(len(x) for x in dups), len(C), "candidates", "High",
        "Unique-candidate counts; channel attribution; repeat-applicant analysis",
        "Candidate de-duplication as a product capability",
        "Keep both records. Sensitivity: collapse each pair to one person.",
        "Group by normalised (Full Name, Phone). Email, Candidate ID and record ID all differ.",
        [";".join(x) for x in dups],
        f"{len(dups)} pairs. Shared City: {sum(same(x, 'City') for x in dups)}/{len(dups)}; shared Current Company: "
        f"{sum(same(x, 'Current Company') for x in dups)}/{len(dups)}; shared email domain: "
        f"{sum(len({dom(i) for i in x}) == 1 for x in dups)}/{len(dups)}. "
        f"The f.last@ email pattern occurs on {len(fpat)}/{len(C)} candidates, {len(set(fpat) & {i for x in dups for i in x})} of them in these pairs. "
        f"Source differs in {len(src_diff)} pairs; Years Experience differs in {len(exp_diff)} and is implausible for one person "
        f"(gap > years between Created On + 0.5) in {implaus}. Pairs: " + "; ".join(pair_txt)))

    # DQ-03 duplicate Application ID business keys
    g = collections.defaultdict(list)
    for k, a in A.items():
        g[a["Application ID"]].append(k)
    dk = {b: ids for b, ids in g.items() if len(ids) > 1}
    nums = {int(a["Application ID"].split("-")[1]) for a in A.values()}
    missing = [f"APP-{n:05d}" for n in range(1, max(nums) + 1) if n not in nums]
    out.append(Issue(
        "DQ-03", "Application ID business key reused by different applications", "Confirmed defect",
        "Applications", sum(len(v) for v in dk.values()), len(A), "applications", "Medium",
        "Any join or report keyed on Application ID", "Unique business-key enforcement",
        "Use Airtable record ID as the key in all analysis.",
        "Group by Application ID; compare with gaps in the APP-00001..max sequence.",
        [f"{b}:{','.join(v)}" for b, v in dk.items()],
        f"{len(dk)} IDs each used twice by different candidate/opening pairs ({', '.join(dk)}). "
        f"Sequence gaps: {', '.join(missing)}. Gaps and duplicates match one-for-one, which points to ID assignment errors. "
        f"{sum(one(A[k], 'Candidate') in {i for x in dups for i in x} for v in dk.values() for k in v)} of the "
        f"{sum(len(v) for v in dk.values())} applications belong to DQ-02 duplicate-pair candidates."))

    # DQ-04 candidate hired more than once
    hires = [k for k, a in A.items() if a["Stage"] == "Hired"]
    hc = collections.defaultdict(list)
    for k in hires:
        hc[one(A[k], "Candidate")].append(k)
    multi = {c: ks for c, ks in hc.items() if len(ks) > 1}
    same_open = [c for c, ks in multi.items() if len({one(A[k], "Opening") for k in ks}) == 1]
    out.append(Issue(
        "DQ-04", "Same candidate hired more than once", "Suspicious pattern", "Applications/Offers",
        sum(len(v) for v in multi.values()), len(hires), "hired applications", "High",
        "Hire count (denominator of VP claim A); offer acceptance; channel yield",
        "Validity of hire-based channel metrics",
        "Count as recorded. Sensitivity: count distinct hired candidates.",
        "Hired applications grouped by Candidate link.",
        [f"{c}:{','.join(ks)}" for c, ks in multi.items()],
        f"{len(multi)} candidates hold {sum(len(v) for v in multi.values())} of {len(hires)} hires. "
        f"{len(same_open)} hired twice into the same opening. Sources: "
        f"{dict(collections.Counter(C[c]['Source'] for c in multi))}; with a Referred By link: "
        f"{sum(1 for ks in multi.values() for k in ks if A[k].get('Referred By'))} of {sum(len(v) for v in multi.values())} hires."))

    # DQ-05 repeat applications to the same opening
    pair = collections.defaultdict(list)
    for k, a in A.items():
        pair[(one(a, "Candidate"), one(a, "Opening"))].append(k)
    rp = {p: ks for p, ks in pair.items() if len(ks) > 1}
    kinds = collections.Counter()
    descr = []
    for (cand, opn), ks in rp.items():
        first, second = sorted(ks, key=lambda k: A[k]["Applied On"])
        f_close = A[first].get("Closed On")
        if A[first]["Stage"] == "Hired" and A[second]["Stage"] == "Hired":
            kind = "hired twice (see DQ-04)"
        elif f_close is None or A[second]["Applied On"] <= f_close:
            kind = "concurrent (second applied while first still open)"
        else:
            kind = f"reapplied {days(f_close, A[second]['Applied On'])} days after first closed ({A[first]['Stage']})"
        kinds["concurrent" if kind.startswith("concurrent") else "other"] += 1
        descr.append(f"{first}->{second}: {kind}")
    out.append(Issue(
        "DQ-05", "Candidate applied to the same opening more than once",
        "Suspicious pattern" if kinds["concurrent"] else "Legitimate business case",
        "Applications", sum(len(v) for v in rp.values()), len(A), "applications", "Low",
        "Application volume per opening", "Duplicate-application prevention",
        "Keep. Concurrent pairs are probable duplicates; a reapplication after closure is legitimate.",
        "Group applications by (Candidate, Opening); compare the second Applied On with the first Closed On.",
        [",".join(v) for v in rp.values()],
        f"{len(rp)} pairs. " + "; ".join(descr)))

    # DQ-06 Pending offers carrying a Decision On date
    pending = [k for k, o in O.items() if o["Status"] == "Pending"]
    pend_dec = [k for k in pending if O[k].get("Decision On")]
    out.append(Issue(
        "DQ-06", "Pending offers carrying a Decision On date", "Confirmed defect", "Offers",
        len(pend_dec), len(pending), "pending offers", "Critical",
        "Offer acceptance rate (VP claim B): denominator membership", "Offer-status tracking",
        "Treat Status as authoritative but report Pending under best, worst and excluded scenarios.",
        "Status = 'Pending' AND Decision On present.", pend_dec,
        f"{len(pend_dec)}/{len(pending)} pending offers have a decision date, so either the status or the date is wrong. "
        f"Their Offered->Decision lags {sorted(days(O[k]['Offered On'], O[k]['Decision On']) for k in pend_dec)} days lie within the "
        f"decided-offer range {min(days(o['Offered On'], o['Decision On']) for o in O.values() if o['Status'] != 'Pending')}-"
        f"{max(days(o['Offered On'], o['Decision On']) for o in O.values() if o['Status'] != 'Pending')} days."))

    # DQ-07 aged pending + no terminal statuses
    age = {k: days(O[k]["Offered On"], AS_OF) for k in pending}
    stale = [k for k, d in age.items() if d > 30]
    statuses = sorted({o["Status"] for o in O.values()})
    withdrew = [k for k in pending if A[one(O[k], "Application")].get("Rejection Reason") == "Withdrew"]
    out.append(Issue(
        "DQ-07", "Pending offers unresolved for more than 30 days; no Expired or Withdrawn status exists", "Suspicious pattern",
        "Offers", len(stale), len(pending), "pending offers", "Critical",
        "Offer acceptance rate (VP claim B)", "Offer lifecycle states and expiry",
        "Report a scenario in which stale pending offers count as not accepted.",
        f"Days from Offered On to the provisional cutoff {AS_OF} (not a confirmed business cutoff, DEC-020); inventory of distinct Status values.",
        [f"{k}:{age[k]}d" for k in sorted(stale, key=lambda x: -age[x])],
        f"Pending offer ages (days): {sorted(age.values())}. Status vocabulary: {statuses}, so there is no Expired, "
        f"Withdrawn or Rescinded state. {len(withdrew)} pending offer's application has Rejection Reason 'Withdrew': {withdrew}. "
        "Cutoff sensitivity: " + "; ".join(f"at {c}: {sum(days(O[k]['Offered On'], c) > 30 for k in pending)}/{len(pending)} stale" for c in CUTOFF_SENSITIVITY)
        + ". Severity Critical because this issue alone moves the Claim B scenario range (M-B0 vs M-B3)."))

    # DQ-08 Stage 'Offer' conflates pending and declined
    off_stage = [k for k, a in A.items() if a["Stage"] == "Offer"]
    mix = collections.Counter((A[k]["Status"], offer_of(A[k])["Status"]) for k in off_stage)
    out.append(Issue(
        "DQ-08", "Application Stage 'Offer' covers both pending and declined offers", "Model limitation",
        "Applications", sum(c for (st, os_), c in mix.items() if os_ == "Declined"), len(off_stage),
        "applications at Stage=Offer", "Medium",
        "Stage-based funnel and acceptance metrics", "Offer outcome modelling",
        "Derive offer outcome from Offers.Status, never from Application Stage.",
        "Cross-tab Stage=Offer by Application Status and Offer Status.",
        [k for k in off_stage if offer_of(A[k])["Status"] == "Declined"],
        f"{dict((f'{a}/{b}', c) for (a, b), c in mix.items())}. There is no 'Offer Declined' stage, so a declined offer stays at Stage=Offer with Status=Closed."))

    # DQ-09 Rejection Reason on non-rejected applications
    rr_bad = [k for k, a in A.items() if a.get("Rejection Reason") and a["Stage"] not in ("Rejected", "Withdrawn")]
    out.append(Issue(
        "DQ-09", "Rejection Reason set on applications that were not rejected or withdrawn", "Confirmed defect",
        "Applications", len(rr_bad), sum(1 for a in A.values() if a.get("Rejection Reason")),
        "applications with a Rejection Reason", "Low",
        "Rejection-reason distribution", "Rejection-reason capture",
        "Exclude from the rejection-reason analysis; flag.",
        "Rejection Reason present AND Stage not in (Rejected, Withdrawn).",
        [f"{k}:{A[k]['Stage']}/{A[k]['Rejection Reason']}" for k in rr_bad],
        f"By stage: {dict(collections.Counter(A[k]['Stage'] for k in rr_bad))}. "
        f"{sum(1 for a in A.values() if a['Stage'] == 'Withdrawn' and a.get('Rejection Reason'))} Withdrawn applications carry a reason "
        f"({dict(collections.Counter(a['Rejection Reason'] for a in A.values() if a['Stage'] == 'Withdrawn' and a.get('Rejection Reason')))}); these are not counted."))

    # DQ-10 'Position Cancelled' on openings not cancelled
    pc = [k for k, a in A.items() if a.get("Rejection Reason") == "Position Cancelled"]
    pc_bad = [k for k in pc if J[one(A[k], "Opening")]["Status"] != "Cancelled"]
    out.append(Issue(
        "DQ-10", "Rejection Reason 'Position Cancelled' on openings that are not Cancelled", "Suspicious pattern",
        "Applications/Job Openings", len(pc_bad), len(pc), "applications with reason Position Cancelled", "Medium",
        "Rejection-reason distribution; opening lifecycle", "Opening status tracking",
        "Report as recorded; flag the contradiction.",
        "Rejection Reason = 'Position Cancelled' joined to Opening Status.", pc_bad,
        f"Opening status of these applications: {dict(collections.Counter(J[one(A[k], 'Opening')]['Status'] for k in pc))}. "
        "Possible legitimate cause: the opening was cancelled and then reopened."))

    # DQ-11 opening status vs applications
    sub = collections.defaultdict(list)
    for k, j in J.items():
        apps = [A[x] for x in j.get("Applications", [])]
        h = sum(a["Stage"] == "Hired" for a in apps)
        act = sum(a["Status"] == "Active" for a in apps)
        if h > j["Headcount"]:
            sub["hires exceed headcount"].append(k)
        if j["Status"] == "Cancelled" and h:
            sub["Cancelled with hires"].append(k)
        if j["Status"] == "Filled" and h < j["Headcount"]:
            sub["Filled with fewer hires than headcount"].append(k)
        if j["Status"] == "Open" and h >= j["Headcount"]:
            sub["Open although hires >= headcount"].append(k)
        if j["Status"] in ("Filled", "Cancelled") and act:
            sub["Filled/Cancelled with Active applications"].append(k)
    affected = sorted({k for v in sub.values() for k in v})
    out.append(Issue(
        "DQ-11", "Job Opening Status contradicts its applications", "Confirmed defect", "Job Openings",
        len(affected), len(J), "job openings", "High",
        "Time-to-fill; fill rate; open-requisition counts", "Requisition status automation",
        "Derive fill state from hires; report the recorded Status separately.",
        "Compare Status and Headcount with the count of Hired and Active applications per opening.",
        affected, "; ".join(f"{name}: {len(v)}" for name, v in sub.items())))

    # DQ-12 Open openings past Target Close
    od = [k for k, j in J.items() if j["Status"] == "Open" and j["Target Close"] < AS_OF]
    n_open = sum(j["Status"] == "Open" for j in J.values())
    od_sens = "; ".join(f"at {c}: {sum(1 for j in J.values() if j['Status'] == 'Open' and j['Target Close'] < c)}/{n_open}" for c in CUTOFF_SENSITIVITY)
    out.append(Issue(
        "DQ-12", f"Open openings past their Target Close date (provisional cutoff {AS_OF})", "Suspicious pattern",
        "Job Openings", len(od), sum(j["Status"] == "Open" for j in J.values()), "open openings", "Medium",
        "Requisition ageing; time-to-fill", "Requisition hygiene",
        "Report as recorded.", "Status = Open AND Target Close < as-of date.",
        [f"{k}:{J[k]['Target Close']}" for k in od],
        f"A missed target is a plausible real situation; the share ({len(od)}/{n_open}) suggests targets or statuses are not maintained. "
        f"Cutoff sensitivity: {od_sens}."))

    # DQ-13 impossible chronology. Every comparison is computed and reported, including those with 0
    # violations. Each check compares fields of ONE provenance: source tables (Interviews, Offers,
    # Job Openings), or Applications' own fields, or Applications' copied stage-date fields among
    # themselves. Disagreements BETWEEN a copied field and its source table are contradictions and are
    # reported in DQ-15, not here (DEC-019).
    last_iv = lambda a: max(I[i]["Scheduled On"] for i in a["Interviews"]) if a.get("Interviews") else None
    chrono = [  # (name, provenance, [(record_id, earlier, later)])
        ("Opening Opened On <= Applied On", "source + application",
         [(k, J[one(a, "Opening")]["Opened On"], a["Applied On"]) for k, a in A.items()]),
        ("Applied On <= Screened On", "application", [(k, a["Applied On"], a.get("Screened On")) for k, a in A.items()]),
        ("Applied On <= Closed On", "application", [(k, a["Applied On"], a.get("Closed On")) for k, a in A.items()]),
        ("Screened On <= Closed On", "application", [(k, a.get("Screened On"), a.get("Closed On")) for k, a in A.items()]),
        ("Applied On <= Interviews.Scheduled On", "source + application",
         [(i, A[one(I[i], "Application")]["Applied On"], I[i]["Scheduled On"]) for i in I]),
        ("Screened On <= Interviews.Scheduled On", "source + application",
         [(i, A[one(I[i], "Application")].get("Screened On"), I[i]["Scheduled On"]) for i in I]),
        ("Interviews.Scheduled On <= Completed On", "source", [(k, i["Scheduled On"], i.get("Completed On")) for k, i in I.items()]),
        ("Last Interviews.Scheduled On <= Offers.Offered On", "source",
         [(one(o, "Application"), last_iv(A[one(o, "Application")]), o["Offered On"]) for o in O.values()]),
        ("Offers.Offered On <= Decision On", "source", [(k, o["Offered On"], o.get("Decision On")) for k, o in O.items()]),
        ("Offers.Offered On <= Proposed Start Date", "source", [(k, o["Offered On"], o["Proposed Start Date"]) for k, o in O.items()]),
        ("Offers.Decision On <= Proposed Start Date", "source", [(k, o.get("Decision On"), o["Proposed Start Date"]) for k, o in O.items()]),
        ("Applied On <= First Interview On (copy)", "copy", [(k, a["Applied On"], a.get("First Interview On")) for k, a in A.items()]),
        ("Screened On <= First Interview On (copy)", "copy", [(k, a.get("Screened On"), a.get("First Interview On")) for k, a in A.items()]),
        ("First Interview On <= Final Interview On (copy)", "copy", [(k, a.get("First Interview On"), a.get("Final Interview On")) for k, a in A.items()]),
        ("Final Interview On <= Offered On (copy)", "copy", [(k, a.get("Final Interview On"), a.get("Offered On")) for k, a in A.items()]),
        ("Candidate Created On <= bulk-import date", "candidate", [(k, c["Created On"], AS_OF) for k, c in C.items()]),
    ]
    viol, parts = {}, []
    for name, prov, pairs in chrono:
        comp = [(k, x, y) for k, x, y in pairs if x and y]
        v = sorted({k for k, x, y in comp if x > y})
        viol[name] = v
        parts.append(f"{name} [{prov}]: {len(v)}/{len(comp)}")
    ev = sorted({x for v in viol.values() for x in v})
    out.append(Issue(
        "DQ-13", "Impossible chronology (date order violated within one data provenance)", "Confirmed defect", "multiple", len(ev),
        len(A) + len(I) + len(O) + len(C), "applications + interviews + offers + candidates", "Medium",
        "Cycle-time metrics (time-to-interview, time-to-offer, time-to-start)", "Date validation at entry",
        "Flag; keep the records. Cycle-time metric M-T0 excludes hires whose Applied On is contradicted (Opened On or Interviews checks). "
        "Copy-vs-source disagreements are reported separately in DQ-15.",
        "Pairwise date comparisons; each check reports violations/comparable records. 'Candidate Created On <= bulk-import date' uses the "
        "apparent bulk-import date, not a confirmed business cutoff (DEC-020).", ev,
        "; ".join(parts) + ". Checks involving Closed On vs offer decisions are DQ-18 and DQ-26; interviews after closure are DQ-27; "
        "Created On vs Applied On is DQ-14."))

    # DQ-14 candidate Created On after application
    ca = [k for k, a in A.items() if C[one(a, "Candidate")]["Created On"] > a["Applied On"]]
    out.append(Issue(
        "DQ-14", "Candidate profile Created On later than the candidate's Applied On", "Suspicious pattern",
        "Candidates/Applications", len(ca), len(A), "applications", "Low",
        "Any metric using Candidate Created On (none of the headline metrics)", "None",
        "Do not use Candidate Created On as a funnel start; use Applied On.",
        "Candidate.Created On > Application.Applied On.", ca,
        "Could be legitimate if profiles are created when an application is processed. Too frequent to be random entry error."))

    # DQ-15 denormalised date drift
    off_mis = [k for k, a in A.items() if a.get("Offers") and a.get("Offered On") != offer_of(a)["Offered On"]]
    fi_mis = [k for k, a in A.items() if a.get("Interviews") and a.get("First Interview On") != min(I[i]["Scheduled On"] for i in a["Interviews"])]
    out.append(Issue(
        "DQ-15", "Copied date fields on Applications disagree with their source records", "Confirmed defect",
        "Applications", len(set(off_mis + fi_mis)), sum(1 for a in A.values() if a.get("Interviews") or a.get("Offers")),
        "applications with interviews or offers", "High",
        "Time-to-interview; time-to-offer; time-to-hire", "Single source of truth for stage dates",
        "Neither side is treated as authoritative (DEC-019). Both values are retained; duration metrics are reported under both sources (M-T2 source/copy rows).",
        "Applications.Offered On vs Offers.Offered On; Applications.First Interview On vs min(Interviews.Scheduled On).",
        sorted(set(off_mis + fi_mis)),
        f"Offered On mismatches: {len(off_mis)}/{sum(1 for a in A.values() if a.get('Offers'))}; "
        f"First Interview On mismatches: {len(fi_mis)}/{sum(1 for a in A.values() if a.get('Interviews'))}. "
        f"Which side fits the application's own chronology: First Interview On mismatches where the source interview predates Applied On: "
        f"{sum(1 for k in fi_mis if min(I[i]['Scheduled On'] for i in A[k]['Interviews']) < A[k]['Applied On'])}; "
        f"where the copy predates Screened/Applied On: {sum(1 for k in fi_mis if A[k].get('First Interview On') and A[k]['First Interview On'] < (A[k].get('Screened On') or A[k]['Applied On']))}. "
        f"Offered On mismatches where the source offer date precedes the copied Final Interview On: "
        f"{sum(1 for k in off_mis if A[k].get('Final Interview On') and offer_of(A[k])['Offered On'] < A[k]['Final Interview On'])}/{len(off_mis)}. "
        "The fields are returned as scalars, not lookup arrays, so they are static values, not live lookups."))

    # DQ-16 Final Interview On after any recorded interview
    fin = [k for k, a in A.items() if a.get("Final Interview On") and a.get("Interviews")]
    fin_late = [k for k in fin if A[k]["Final Interview On"] > max(I[i]["Scheduled On"] for i in A[k]["Interviews"])]
    hired_one = [k for k in hires if len(A[k].get("Interviews", [])) == 1]
    out.append(Issue(
        "DQ-16", "Final Interview On falls after the last recorded interview, so the Interviews table may be incomplete", "Suspicious pattern",
        "Applications/Interviews", len(fin_late), len(fin), "applications with Final Interview On", "High",
        "Interview counts, rounds per hire, interview-to-offer conversion", "Interview data capture completeness",
        "Treat interview counts as a lower bound; base conversion on 'has at least 1 interview'.",
        "Final Interview On > max(Interviews.Scheduled On) for the application.", fin_late,
        f"{len(hired_one)}/{len(hires)} hires have only one recorded interview "
        f"({dict(collections.Counter(I[A[k]['Interviews'][0]]['Round'] for k in hired_one))}); "
        f"{sum(1 for k in hires if A[k].get('Final Interview On'))}/{len(hires)} hires carry a Final Interview On. "
        "Consistent with later rounds missing from the Interviews table, but not confirmed: the intended scope of the table is unknown (C-05)."))

    # DQ-17 interview outcome vs completion fields
    oc = [k for k, i in I.items() if i["Outcome"] != "Completed" and (i.get("Completed On") or "Score" in i or i.get("Recommendation"))]
    oc2 = [k for k, i in I.items() if i["Outcome"] == "Completed" and not i.get("Completed On")]
    out.append(Issue(
        "DQ-17", "Interview Outcome contradicts its completion data", "Confirmed defect", "Interviews",
        len(oc) + len(oc2), len(I), "interviews", "Low",
        "Interview no-show and cancellation rates; score analysis", "Interview outcome capture",
        "Report as recorded; flag.",
        "Outcome != Completed but Completed On, Score or Recommendation present (and the reverse).",
        [f"{k}:{I[k]['Outcome']}" for k in oc + oc2],
        f"{len(oc)} No Show/Cancelled interviews carry a completion date, score and recommendation; {len(oc2)} completed interviews lack a date."))

    # DQ-18 hired application closed before the offer decision
    hcd = [k for k in hires if A[k]["Closed On"] < offer_of(A[k])["Decision On"]]
    out.append(Issue(
        "DQ-18", "Hired applications closed before the offer was accepted", "Suspicious pattern",
        "Applications/Offers", len(hcd), len(hires), "hired applications", "Medium",
        "Time-to-hire (which end date is used)", "Hire event definition",
        "Use Offers.Decision On (Accepted) as the hire date, not Applications.Closed On.",
        "Applications.Closed On < Offers.Decision On for Stage=Hired.",
        [f"{k}:{A[k]['Closed On']}<{offer_of(A[k])['Decision On']}" for k in hcd],
        "Closed On may record a verbal acceptance or an administrative close. The meaning of the field is undocumented."))

    # DQ-19 offer outside band
    ob = [k for k, o in O.items()
          if not J[one(A[one(o, "Application")], "Opening")]["Salary Band Min"] <= o["Base CTC"] <= J[one(A[one(o, "Application")], "Opening")]["Salary Band Max"]]
    out.append(Issue(
        "DQ-19", "Offer Base CTC outside the opening's salary band", "Suspicious pattern", "Offers",
        len(ob), len(O), "offers", "Low",
        "Compensation analysis; decline-reason interpretation", "Offer approval guardrails",
        "Report; do not exclude.", "Base CTC outside [Salary Band Min, Salary Band Max] of the linked opening.",
        [f"{k}:{O[k]['Base CTC']}" for k in ob],
        f"Status of these offers: {dict(collections.Counter(O[k]['Status'] for k in ob))}. Could be legitimate approved exceptions."))

    # DQ-20 non-round compensation values
    nr_c = [k for k, c in C.items() if c["Expected CTC"] % 1000 or c["Current CTC"] % 1000]
    nr_o = [k for k, o in O.items() if o["Base CTC"] % 1000]
    dup_ids = {i for ids in dups for i in ids}
    out.append(Issue(
        "DQ-20", "Non-round compensation values (possible entry or transformation errors)", "Suspicious pattern",
        "Candidates/Offers", len(nr_c) + len(nr_o), len(C) + len(O), "candidates + offers", "Low",
        "Compensation analysis", "None",
        "Report; do not exclude.", "CTC values not divisible by 1,000; every other value is.",
        nr_c + nr_o,
        f"{len(nr_c)} candidates, of which {len(set(nr_c) & dup_ids)} belong to the DQ-02 duplicate pairs and "
        f"{sum(C[k]['Expected CTC'] < C[k]['Current CTC'] for k in nr_c)} have Expected below Current CTC "
        f"(all candidates with Expected below Current: {sum(c['Expected CTC'] < c['Current CTC'] for c in C.values())}). {len(nr_o)} offers."))

    # DQ-25 offer compensation incoherent with candidate expectations
    ratio = {k: o["Base CTC"] / C[one(A[one(o, "Application")], "Candidate")]["Expected CTC"] for k, o in O.items()}
    far = [k for k, r in ratio.items() if r < 0.67 or r > 1.5]
    out.append(Issue(
        "DQ-25", "Offer Base CTC far from the candidate's Expected CTC (below 0.67x or above 1.5x)", "Suspicious pattern",
        "Offers/Candidates", len(far), len(O), "offers", "Medium",
        "Any compensation-driven decline analysis", "Comp-benchmarking or offer-intelligence features",
        "Do not draw compensation conclusions from this data (M-B7, M-B8 not interpretable).",
        "Base CTC / linked candidate Expected CTC; unit-consistency checks on all CTC fields.",
        [f"{k}:{ratio[k]:.2f}x" for k in sorted(far, key=lambda x: ratio[x])],
        f"Ratio range {min(ratio.values()):.2f}x to {max(ratio.values()):.2f}x; only {len(O) - len(far)}/{len(O)} fall within 0.67-1.5x. "
        f"Unit-consistency evidence: CTC values below 100,000: {sum(1 for c in C.values() for f in ('Current CTC', 'Expected CTC') if c[f] < 100000) + sum(1 for o in O.values() if o['Base CTC'] < 100000)}; "
        f"candidate Expected/Current ratio {min(c['Expected CTC'] / c['Current CTC'] for c in C.values()):.2f}-{max(c['Expected CTC'] / c['Current CTC'] for c in C.values()):.2f}; "
        f"offers inside the opening's band {len(O) - len(ob)}/{len(O)}; applications whose candidate Expected CTC is inside the opening's band "
        f"{sum(1 for a in A.values() if J[one(a, 'Opening')]['Salary Band Min'] <= C[one(a, 'Candidate')]['Expected CTC'] <= J[one(a, 'Opening')]['Salary Band Max'])}/{len(A)}. "
        "No evidence of a units or period defect (currency INR and annual period are assumed, ASM-016). Hypothesis, not verified: the spread reflects "
        "candidates applying to roles outside their pay level, or candidate-opening links (customer question C-09)."))

    # DQ-26 declined offers: application closed before the decision
    dcd = [k for k, a in A.items() if a.get("Offers") and offer_of(a)["Status"] == "Declined"
           and a.get("Closed On") and a["Closed On"] < offer_of(a)["Decision On"]]
    n_decl = sum(1 for a in A.values() if a.get("Offers") and offer_of(a)["Status"] == "Declined")
    out.append(Issue(
        "DQ-26", "Declined offers: application closed before the offer decision", "Suspicious pattern",
        "Applications/Offers", len(dcd), n_decl, "applications with a Declined offer", "Medium",
        "Time-to-decision; meaning of Closed On", "Application lifecycle / hire event definition",
        "Report; use Offers.Decision On for decision timing. Extends DQ-18 (hires) to declines.",
        "Applications.Closed On < Offers.Decision On where Offers.Status = Declined.",
        [f"{k}:{A[k]['Closed On']}<{offer_of(A[k])['Decision On']}" for k in dcd],
        f"Together with DQ-18 ({len(hcd)}/{len(hires)} hires), Closed On precedes the offer decision for {len(hcd) + len(dcd)}/{len(hires) + n_decl} "
        "decided offers; the meaning of Closed On is undocumented (C-06)."))

    # DQ-27 interview scheduled after the application was closed (rejected/withdrawn)
    rw = [k for k, a in A.items() if a["Stage"] in ("Rejected", "Withdrawn") and a.get("Interviews") and a.get("Closed On")]
    iac = [k for k in rw if max(I[i]["Scheduled On"] for i in A[k]["Interviews"]) > A[k]["Closed On"]]
    out.append(Issue(
        "DQ-27", "Interview scheduled after a rejected/withdrawn application was closed", "Confirmed defect",
        "Applications/Interviews", len(iac), len(rw), "rejected/withdrawn applications with interviews", "Low",
        "Rejection timing; furthest-stage-reached analysis", "Application lifecycle",
        "Flag; keep. Furthest stage reached is still evidence-based.",
        "max(Interviews.Scheduled On) > Applications.Closed On, Stage in (Rejected, Withdrawn).",
        iac, f"Stages: {dict(collections.Counter(A[k]['Stage'] for k in iac))}."))

    # DQ-28 stalled Active applications
    act = [k for k, a in A.items() if a["Status"] == "Active"]
    stall = [k for k in act if days(last_activity(A[k], I, O), AS_OF) > STALL_DAYS]
    on_filled = [k for k in act if J[one(A[k], "Opening")]["Status"] == "Filled"]
    by_stage = collections.Counter(A[k]["Stage"] for k in act)
    st_stage = collections.Counter(A[k]["Stage"] for k in stall)
    out.append(Issue(
        "DQ-28", f"Active applications with no recorded activity for more than {STALL_DAYS} days", "Suspicious pattern",
        "Applications", len(stall), len(act), "Active applications", "Medium",
        "Closed-only funnel variant (M-FCc); in-flight pipeline counts; completed-cohort eligibility (M-K)",
        "Application status hygiene / auto-closure",
        "Report; in the completed cohort, stalled Active applications are retained at their furthest evidence stage (ASM-021).",
        f"Last activity = latest of Applied, Screened, interview, offer and decision dates; age at provisional cutoff {AS_OF}.",
        stall,
        "By stage (stalled/Active): " + "; ".join(f"{k} {st_stage[k]}/{v}" for k, v in by_stage.items())
        + f". Oldest {max((days(last_activity(A[k], I, O), AS_OF) for k in act), default=0)} days. Active applications on Filled openings: {len(on_filled)}/{len(act)}. "
        + "Cutoff sensitivity: " + "; ".join(f"at {c}: {sum(days(last_activity(A[k], I, O), c) > STALL_DAYS for k in act)}/{len(act)}" for c in CUTOFF_SENSITIVITY)
        + f". The {STALL_DAYS}-day threshold is an assumption (ASM-021)."))

    # DQ-29 offers to candidates already hired via another application
    def prior(o_id):
        a_id = one(O[o_id], "Application")
        return [x for x in C[one(A[a_id], "Candidate")]["Applications"] if x != a_id and A[x]["Stage"] == "Hired"
                and offer_of(A[x])["Decision On"] < O[o_id]["Offered On"]]
    ph = [k for k in O if prior(k)]
    out.append(Issue(
        "DQ-29", "Offer made to a candidate already hired via another application", "Suspicious pattern",
        "Offers/Applications", len(ph), len(O), "offers", "Low",
        "Offer acceptance scope (M-B1 includes these); hire counts", "Internal-mobility handling in offer metrics",
        "Report; acceptance shown with and without these offers (M-B10).",
        "Another Hired application of the same candidate whose offer Decision On precedes this Offered On.",
        [f"{k}:{O[k].get('Offer ID', '')}:{O[k]['Status']}" for k in ph],
        f"Statuses: {dict(collections.Counter(O[k]['Status'] for k in ph))}. Possible internal moves (C-08). Same opening as the earlier hire: "
        f"{sum(1 for k in ph if any(one(A[x], 'Opening') == one(A[one(O[k], 'Application')], 'Opening') for x in prior(k)))} (DQ-04)."))

    # DQ-21 recruiter mismatch
    rm = [k for k, a in A.items() if a["Recruiter"] != J[one(a, "Opening")]["Recruiter"]]
    out.append(Issue(
        "DQ-21", "Application recruiter differs from the opening's recruiter", "Legitimate business case",
        "Applications", len(rm), len(A), "applications", "Low",
        "Recruiter workload metrics", "None",
        "Keep; probably reassignment.", "Applications.Recruiter != Job Openings.Recruiter.", rm, ""))

    # DQ-22 / 23 / 24 informational
    ct_all = sorted({r["createdTime"][:16] for t in s.raw.values() for r in t})
    out.append(Issue(
        "DQ-22", "Every record was bulk-created within one minute; createdTime is not an event date", "Informational",
        "all", sum(len(t) for t in s.raw.values()), sum(len(t) for t in s.raw.values()), "records", "Low",
        "Any metric that might use createdTime", "None",
        f"Never use createdTime for event timing. Extraction date {EXTRACTION_DATE}; apparent bulk-import date {AS_OF} is used as a provisional cutoff only (DEC-020).",
        "Distinct createdTime minutes across all tables.", [],
        f"createdTime minutes: {ct_all}"))
    out.append(Issue(
        "DQ-23", "Findings table is empty", "Informational", "Findings", 0, 0, "records", "Low",
        "Cannot reconcile against any prior analysis", "None",
        "Build the findings table locally (read-only base).", "Record count from manifest.", [], ""))
    out.append(Issue(
        "DQ-24", "Interview Completed On equals Scheduled On in every valid record, so feedback latency cannot be measured", "Model limitation",
        "Interviews", sum(1 for i in I.values() if i.get("Completed On") == i["Scheduled On"]),
        sum(1 for i in I.values() if i.get("Completed On")), "interviews with Completed On", "Medium",
        "Interview feedback turnaround", "Feedback-latency tooling claims",
        "Do not report feedback latency; it is unmeasurable in this data.",
        "Count of Completed On == Scheduled On.", [k for k, i in I.items() if i.get("Completed On") == i["Scheduled On"]],
        f"No feedback-submitted timestamp exists. Deviating records: {sum(1 for i in I.values() if i.get('Completed On') and i['Completed On'] != i['Scheduled On'])}, "
        f"of which completed before scheduled: {sum(1 for i in I.values() if i.get('Completed On') and i['Completed On'] < i['Scheduled On'])}."))
    return sorted(out, key=lambda i: i.id)
