"""Funnel, VP-claim and supporting metrics → outputs/metric_calculations.csv.

Each row records its definition, numerator, denominator, unit level and method so it can be
recomputed by hand. Alternative definitions are separate rows linked by `variant_of`.

Uncertainty (DEC-018, PM-approved). The snapshot is treated as the complete record of the period,
so rates are reported as OBSERVED values with:
  * definition sensitivity   variant rows (variant_of) show how the value moves under other definitions;
  * single-record sensitivity  `single_record_pp` = percentage points moved by one record (100 / denominator).
Wilson sampling intervals are not reported: no valid sampling interpretation has been justified
(repeat candidates break independence; ASM-014). `wilson()` is retained only as a utility.

Definitions used throughout (PM decisions DEC-016..DEC-021, decision_log.md):
  hire        Application Stage = 'Hired' (identical to Offers.Status = 'Accepted', M-H0). ASM-020.
  channel     PRIMARY: Candidates.Source, labelled "Source as recorded" (DEC-017). Variants:
              referrer override (M-A2, ASM-011), strict referral (M-A9), duplicates merged (M-A8, M-A10).
  reached X   evidence-based: screened = Screened On present; interviewed = at least 1 Interviews
              record; offered = at least 1 Offers record; hired = Stage Hired
  level       application | hire (hired applications) | offer | candidate | interview
"""
from __future__ import annotations

import collections
import math
import statistics

from src.data import AS_OF, CUTOFF_SENSITIVITY, Snapshot, days, one

SOURCES = ["Job Board", "Agency", "LinkedIn", "Career Site", "Referral", "Campus"]
COHORT = ("2025-07-01", "2026-03-31")   # completed-cohort window (DEC-021)
STALL_DAYS = 90                         # ASM-021


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Utility only; not used in reported outputs (DEC-018)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


GROUP_LEVEL = {"definitions": "hire", "funnel": "application", "claim_A": "hire", "claim_B": "offer",
               "channel_quality": "application", "cycle_time": "hire", "declines": "offer",
               "interviews": "interview", "departments": "application", "cohort": "application"}


class M:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, mid, group, metric, definition, num, den, method, variant_of="", notes="", level=""):
        val = num / den if den else None
        self.rows.append({
            "metric_id": mid, "group": group, "level": level or GROUP_LEVEL[group], "metric": metric,
            "definition": definition, "numerator": num, "denominator": den,
            "value": round(val, 4) if val is not None else "",
            "value_pct": f"{100 * val:.1f}%" if val is not None else "",
            "single_record_pp": f"{100 / den:.1f}" if den else "",
            "method": method, "variant_of": variant_of, "notes": notes,
        })

    def value(self, mid):
        return next(r for r in self.rows if r["metric_id"] == mid)

    def stat(self, mid, group, metric, definition, value, n, method, notes="", level="", variant_of=""):
        self.rows.append({"metric_id": mid, "group": group, "level": level or GROUP_LEVEL[group], "metric": metric,
                          "definition": definition, "numerator": "", "denominator": n, "value": value,
                          "value_pct": "", "single_record_pp": "", "method": method, "variant_of": variant_of,
                          "notes": notes})


def last_activity(a: dict, I: dict, O: dict) -> str:
    """Latest recorded event date on an application (Applied, Screened, interviews, offer, decision)."""
    ds = [a["Applied On"], a.get("Screened On")]
    ds += [I[i]["Scheduled On"] for i in a.get("Interviews", [])]
    ds += [O[o]["Offered On"] for o in a.get("Offers", [])] + [O[o].get("Decision On") for o in a.get("Offers", [])]
    return max(d for d in ds if d)


def compute(s: Snapshot) -> M:
    C, A, I, O, J, D = (s.f(t) for t in ["Candidates", "Applications", "Interviews", "Offers", "Job Openings", "Departments"])
    m = M()
    src = lambda a: C[one(a, "Candidate")]["Source"]
    chan_ref = lambda a: "Referral" if a.get("Referred By") else src(a)
    chan_strict = lambda a: "Referral (linked)" if a.get("Referred By") else (
        "Referral label, no referrer" if src(a) == "Referral" else src(a))
    dept = lambda a: D[one(J[one(a, "Opening")], "Department")]["Name"]
    offer = lambda a: O[one(a, "Offers")] if a.get("Offers") else None
    hires = [k for k, a in A.items() if a["Stage"] == "Hired"]
    acc_apps = {one(o, "Application") for o in O.values() if o["Status"] == "Accepted"}

    # ---------------- hire-definition reconciliation
    m.add("M-H0", "definitions", "Hire definitions agree (Stage=Hired vs Offer Accepted)",
          "|Stage=Hired AND Accepted| / |Stage=Hired OR Accepted|",
          len(set(hires) & acc_apps), len(set(hires) | acc_apps), "Set comparison of application record IDs",
          notes=f"Stage=Hired: {len(hires)}; Accepted offers: {len(acc_apps)}. Accepted offer is treated as the hire (ASM-020); no start confirmation exists.")

    # ---------------- funnel (full snapshot; mixed maturity, not a cohort)
    n = len(A)
    screened = [k for k, a in A.items() if a.get("Screened On")]
    interviewed = [k for k, a in A.items() if a.get("Interviews")]
    offered = [k for k, a in A.items() if a.get("Offers")]
    steps = [("applications", list(A)), ("screened", screened), ("interviewed", interviewed),
             ("offered", offered), ("hired", hires)]
    for i, (name, ks) in enumerate(steps):
        m.add(f"M-F{i}", "funnel", f"Overall conversion: applications reaching '{name}'", f"count({name}) / all applications",
              len(ks), n, "Evidence-based stage reach; full snapshot (mixed maturity)")
    for (a_name, a_ks), (b_name, b_ks) in zip(steps, steps[1:]):
        m.add(f"M-FC-{b_name}", "funnel", f"Previous-stage conversion {a_name} -> {b_name}", f"count({b_name}) / count({a_name})",
              len(set(b_ks) & set(a_ks)), len(a_ks), "Step-wise conversion, all applications")
    closed = {k for k, a in A.items() if a["Status"] == "Closed"}
    for (a_name, a_ks), (b_name, b_ks) in zip(steps, steps[1:]):
        aa, bb = set(a_ks) & closed, set(b_ks) & closed
        m.add(f"M-FCc-{b_name}", "funnel", f"Previous-stage conversion {a_name} -> {b_name} (Status=Closed only)",
              f"count({b_name}) / count({a_name}) among Status=Closed", len(bb & aa), len(aa),
              "Excludes Active applications. Caveat: most Active applications are stalled, not in flight (DQ-28)",
              variant_of=f"M-FC-{b_name}")
    rej = [k for k, a in A.items() if a["Stage"] == "Rejected"]
    furthest = lambda a: ("offer" if a.get("Offers") else "interview" if a.get("Interviews") else "screen" if a.get("Screened On") else "application")
    rc = collections.Counter(furthest(A[k]) for k in rej)
    for st in ["application", "screen", "interview", "offer"]:
        m.add(f"M-R-{st}", "funnel", f"Rejected applications whose furthest stage was '{st}'",
              "count / all Stage=Rejected", rc[st], len(rej), "Furthest evidence-based stage reached")
    drops = [(b_name, len(a_ks) - len(set(b_ks) & set(a_ks))) for (a_name, a_ks), (b_name, b_ks) in zip(steps, steps[1:])]
    big = max(drops, key=lambda x: x[1])
    m.stat("M-F-leak", "funnel", "Largest absolute drop between consecutive stages",
           "max over stages of (reached previous stage minus reached this stage)", f"before '{big[0]}': {big[1]}", n,
           "Difference of consecutive funnel counts", notes="; ".join(f"before {b}: {d}" for b, d in drops))

    # ---------------- completed-cohort funnel (DEC-021)
    win = [k for k, a in A.items() if COHORT[0] <= a["Applied On"] <= COHORT[1]]
    stalled = {k for k in win if A[k]["Status"] == "Active" and days(last_activity(A[k], I, O), AS_OF) > STALL_DAYS}
    in_flight = [k for k in win if A[k]["Status"] == "Active" and k not in stalled]
    elig = [k for k in win if k not in in_flight]
    m.add("M-K-eligible", "cohort", f"Completed cohort: eligible applications (Applied On {COHORT[0]}..{COHORT[1]})",
          "eligible / applications in window", len(elig), len(win),
          f"Eligible = Status Closed, or Active with no recorded activity for >{STALL_DAYS} days before the provisional cutoff {AS_OF} (stalled; ASM-021). Excluded = Active with recent activity (in flight)",
          notes=f"window {len(win)}; closed {sum(A[k]['Status'] == 'Closed' for k in win)}; stalled Active {len(stalled)}; excluded in flight {len(in_flight)}; "
                f"share of all applications {len(win)}/{n}")
    csteps = [("applications", elig), ("screened", [k for k in elig if A[k].get("Screened On")]),
              ("interviewed", [k for k in elig if A[k].get("Interviews")]), ("offered", [k for k in elig if A[k].get("Offers")]),
              ("hired", [k for k in elig if A[k]["Stage"] == "Hired"])]
    for i, (name, ks) in enumerate(csteps):
        m.add(f"M-KF{i}", "cohort", f"Completed cohort overall conversion: reaching '{name}'", f"count({name}) / eligible",
              len(ks), len(elig), "Evidence-based stage reach, completed cohort", variant_of=f"M-F{i}")
    for (a_name, a_ks), (b_name, b_ks) in zip(csteps, csteps[1:]):
        m.add(f"M-KC-{b_name}", "cohort", f"Completed cohort previous-stage conversion {a_name} -> {b_name}",
              f"count({b_name}) / count({a_name})", len(set(b_ks) & set(a_ks)), len(a_ks), "Completed cohort",
              variant_of=f"M-FC-{b_name}")
    pend_in = sum(1 for k in elig if A[k].get("Offers") and offer(A[k])["Status"] == "Pending")
    m.add("M-K-pending", "cohort", "Completed cohort: offers still Pending", "Pending / offers in eligible cohort",
          pend_in, len(csteps[3][1]), "Offers.Status", level="offer",
          notes="Offer->hire step in the cohort is not fully resolved")
    for cut in CUTOFF_SENSITIVITY:
        st_c = sum(1 for k in win if A[k]["Status"] == "Active" and days(last_activity(A[k], I, O), cut) > STALL_DAYS)
        act_w = sum(A[k]["Status"] == "Active" for k in win)
        m.add(f"M-K-stalled-{cut}", "cohort", f"Completed cohort: Active applications counted as stalled at cutoff {cut}",
              "stalled Active / Active in window", st_c, act_w, "Cutoff sensitivity (DEC-020)", variant_of="M-K-eligible")

    # ---------------- Claim A: job boards = 26.9% of hires
    hs = collections.Counter(src(A[k]) for k in hires)
    m.add("M-A0", "claim_A", "Job Board share of hires: Source as recorded (PRIMARY reported attribution, DEC-017)",
          "hires whose candidate Source='Job Board' / all hires", hs["Job Board"], len(hires),
          "Stage=Hired applications joined to Candidates.Source",
          notes="Reproduces the VP figure. Hires by Source: " + ", ".join(f"{k} {v}" for k, v in hs.most_common()))
    ref_hires = [k for k in hires if src(A[k]) == "Referral"]
    m.add("M-A0r", "claim_A", "Referral share of hires: Source as recorded", "Source='Referral' hires / all hires",
          hs["Referral"], len(hires), "as M-A0",
          notes=f"Ties Job Board as recorded. NOT evidence that Referral performs well: "
                f"{sum(not A[k].get('Referred By') for k in ref_hires)}/{len(ref_hires)} Referral-labelled hires have no referrer link (M-A9n)")
    hcands = {one(A[k], "Candidate") for k in hires}
    hsd = collections.Counter(C[c]["Source"] for c in hcands)
    m.add("M-A1", "claim_A", "Job Board share of distinct hired candidate records", "distinct hired candidates with Source='Job Board' / distinct hired candidates",
          hsd["Job Board"], len(hcands), "Deduplicates the 2 candidates hired twice (DQ-04)", variant_of="M-A0", level="candidate")
    hr = collections.Counter(chan_ref(A[k]) for k in hires)
    m.add("M-A2", "claim_A", "Job Board share of hires: Referred By link overrides Source",
          "hires attributed to Job Board after reassigning referred applications to Referral / all hires",
          hr["Job Board"], len(hires), "Referred By present -> Referral; otherwise Source. Asymmetric: a Referral label without a link stays Referral (ASM-011)",
          variant_of="M-A0", notes="Hires by channel: " + ", ".join(f"{k} {v}" for k, v in hr.most_common()))
    hrd = collections.Counter(chan_ref(A[next(k for k in hires if one(A[k], 'Candidate') == c)]) for c in hcands)
    m.add("M-A3", "claim_A", "Job Board share, distinct hired candidate records + Referred By override",
          "M-A1 and M-A2 combined", hrd["Job Board"], len(hcands), "Both corrections applied", variant_of="M-A0", level="candidate")
    dup_groups = collections.defaultdict(list)
    for k, c in C.items():
        dup_groups[(c["Full Name"].strip().lower(), c["Phone"].replace(" ", ""))].append(k)
    dup_ids = {i for g in dup_groups.values() if len(g) > 1 for i in g}
    m.add("M-A4", "claim_A", "Hires involving a DQ-02 probable-duplicate candidate",
          "hires whose candidate is in a duplicate pair / all hires", sum(one(A[k], "Candidate") in dup_ids for k in hires),
          len(hires), "Hires whose attribution could change if duplicate candidates were merged", variant_of="M-A0")
    canon_c, canon_a = {}, {}
    for g in dup_groups.values():
        first_c = min(g, key=lambda k: (C[k]["Created On"], k))
        first_a = min(g, key=lambda k: (min(A[x]["Applied On"] for x in C[k]["Applications"]), k))
        for k in g:
            canon_c[k], canon_a[k] = C[first_c]["Source"], C[first_a]["Source"]
    merged_c = lambda a: canon_c.get(one(a, "Candidate"), src(a))
    merged_a = lambda a: canon_a.get(one(a, "Candidate"), src(a))
    ft = collections.Counter(merged_c(A[k]) for k in hires)
    m.add("M-A8", "claim_A", "Job Board share of hires, duplicates merged, first touch by Candidate Created On",
          "hires attributed to the Source of the earliest-created record of each duplicate pair / all hires",
          ft["Job Board"], len(hires), "Merge DQ-02 pairs; earliest Created On wins (ASM-008, ASM-012)",
          variant_of="M-A0", notes="Caveat: Created On is later than Applied On for 90/350 applications (DQ-14). Hires by channel: "
                                   + ", ".join(f"{k} {v}" for k, v in ft.most_common()))
    fa = collections.Counter(merged_a(A[k]) for k in hires)
    m.add("M-A10", "claim_A", "Job Board share of hires, duplicates merged, first touch by earliest Applied On",
          "hires attributed to the Source of the record with the earliest application in each duplicate pair / all hires",
          fa["Job Board"], len(hires), "Merge DQ-02 pairs; earliest Applied On wins (ASM-008)", variant_of="M-A0",
          notes="Same total as M-A8 but a different hire moves (pair CAND-00003/00004, not CAND-00001/00002). Hires by channel: "
                + ", ".join(f"{k} {v}" for k, v in fa.most_common()))
    hs4 = collections.Counter(chan_strict(A[k]) for k in hires)
    m.add("M-A9", "claim_A", "Job Board share of hires: strict referral (Referral only with a referrer link)",
          "hires attributed to Job Board when referred applications -> Referral (linked) and unlinked Referral labels are kept separate / all hires",
          hs4["Job Board"], len(hires), "Referred By present -> Referral (linked); Source=Referral without link -> 'Referral label, no referrer'",
          variant_of="M-A0", notes="Hires by channel: " + ", ".join(f"{k} {v}" for k, v in hs4.most_common()))
    m.add("M-A9r", "claim_A", "Linked-referral share of hires (strict referral)", "hires with a Referred By link / all hires",
          sum(bool(A[k].get("Referred By")) for k in hires), len(hires), "Applications.Referred By", variant_of="M-A0r")
    m.add("M-A9n", "claim_A", "Referral-labelled hires without a referrer link", "Source='Referral' hires with no Referred By / Source='Referral' hires",
          sum(not A[k].get("Referred By") for k in ref_hires), len(ref_hires), "Candidates.Source x Applications.Referred By",
          notes="4 of these hires belong to 2 candidates (DQ-04)")
    apps_by = collections.Counter(src(a) for a in A.values())
    m.add("M-A5", "claim_A", "Job Board share of applications: Source as recorded", "Source='Job Board' applications / all applications",
          apps_by["Job Board"], n, "Applications joined to Candidates.Source", level="application")
    m.add("M-A6", "claim_A", "Job Board share of candidates: Source as recorded", "Source='Job Board' candidates / all candidates",
          sum(c["Source"] == "Job Board" for c in C.values()), len(C), "Candidates.Source", level="candidate")
    variants = [("M-A7", "Source as recorded", src, ""), ("M-A7r", "Referred By override", chan_ref, "M-A7"),
                ("M-A7s", "strict referral", chan_strict, "M-A7"), ("M-A7m", "merged, first touch by Created On", merged_c, "M-A7"),
                ("M-A7f", "merged, first touch by earliest Applied On", merged_a, "M-A7")]
    for pre, label, fn, vo in variants:
        chans = SOURCES if pre != "M-A7s" else ["Job Board", "Agency", "LinkedIn", "Career Site", "Referral (linked)",
                                                 "Referral label, no referrer", "Campus"]
        for sname in chans:
            sa = [k for k, a in A.items() if fn(a) == sname]
            note = ""
            if sname == "Referral" and pre in ("M-A7", "M-A7m", "M-A7f"):
                note = "Not a proven high-performing channel: rests on Referral labels without referrer links (M-A9n) and 2 repeat-hire candidates (DQ-04)"
            m.add(f"{pre}-{sname}", "claim_A", f"Hire rate per application ({label}): {sname}", "hires / applications for channel",
                  sum(A[k]["Stage"] == "Hired" for k in sa), len(sa), label,
                  variant_of=f"{vo}-{'Referral' if sname.startswith('Referral') else sname}" if vo else "", level="application", notes=note)

    # ---------------- Claim B: offer acceptance ~72%
    st = collections.Counter(o["Status"] for o in O.values())
    acc, dec, pen = st["Accepted"], st["Declined"], st["Pending"]
    m.add("M-B0", "claim_B", "All-issued-offer ratio (offer-level): Accepted / all offers issued", "Accepted / (Accepted+Declined+Pending)",
          acc, len(O), "Offers.Status",
          notes="Reproduces the VP's ~72%. Not an acceptance rate in the decided sense: the 5 unresolved Pending offers are in the denominator.")
    m.add("M-B1", "claim_B", "Decided-offer acceptance rate (offer-level). PROVISIONAL PRIMARY (DEC-016)",
          "Accepted / (Accepted + Declined); Pending excluded", acc, acc + dec, "Offers.Status as recorded", variant_of="M-B0",
          notes="Offer-level: a candidate with 2 decided offers counts twice. Not comparable with candidate-level M-B4.")
    m.add("M-B2", "claim_B", "Upper bound: all Pending eventually accepted (offer-level)", "(Accepted + Pending) / all offers",
          acc + pen, len(O), "Scenario", variant_of="M-B0")
    for cut in (AS_OF,) + CUTOFF_SENSITIVITY:
        pend_age = {k: days(o["Offered On"], cut) for k, o in O.items() if o["Status"] == "Pending"}
        stale = [k for k, d in pend_age.items() if d > 30]
        mid = "M-B3" if cut == AS_OF else f"M-B3-{cut}"
        m.add(mid, "claim_B", f"Pending > 30 days counted as expired; fresh Pending excluded (offer-level; cutoff {cut})",
              "Accepted / (Accepted + Declined + stale Pending)", acc, acc + dec + len(stale),
              f"Pending age measured at {cut}" + (" (provisional cutoff)" if cut == AS_OF else " (cutoff sensitivity, DEC-020)"),
              variant_of="M-B0" if cut == AS_OF else "M-B3",
              notes=f"Stale pending: {len(stale)} ({sorted(pend_age[k] for k in stale)} days). 30-day threshold is ASM-007")
    ocands = collections.defaultdict(list)
    for k, o in O.items():
        ocands[one(A[one(o, "Application")], "Candidate")].append(o["Status"])
    cand_acc = sum("Accepted" in v for v in ocands.values())
    cand_dec = sum("Accepted" not in v and "Declined" in v for v in ocands.values())
    m.add("M-B4", "claim_B", "Candidate-level decided acceptance (secondary; not comparable with offer-level M-B1)",
          "candidates with at least 1 Accepted offer / candidates with at least 1 decided offer", cand_acc, cand_acc + cand_dec,
          "Collapses repeat offers to the same candidate", variant_of="M-B1", level="candidate",
          notes=f"{len(O)} offers to {len(ocands)} distinct candidates")
    prior_hire = {}
    for k, o in O.items():
        a_id = one(o, "Application")
        cand = one(A[a_id], "Candidate")
        prior_hire[k] = any(A[x]["Stage"] == "Hired" and offer(A[x])["Decision On"] < o["Offered On"]
                            for x in C[cand]["Applications"] if x != a_id)
    dec_set = [k for k, o in O.items() if o["Status"] in ("Accepted", "Declined")]
    m.add("M-B9", "claim_B", "Decided offers made to candidates already hired via another application",
          "decided offers to already-hired candidates / decided offers", sum(prior_hire[k] for k in dec_set), len(dec_set),
          "Earlier Hired application of the same candidate with Decision On before this Offered On (DQ-29)", variant_of="M-B1",
          notes="; ".join(f"{O[k]['Offer ID']}:{O[k]['Status']}" for k in dec_set if prior_hire[k]))
    ex = [k for k in dec_set if not prior_hire[k]]
    m.add("M-B10", "claim_B", "Decided-offer acceptance excluding offers to already-hired candidates (offer-level)",
          "Accepted / decided, excluding DQ-29 offers", sum(O[k]["Status"] == "Accepted" for k in ex), len(ex),
          "Definition sensitivity (possible internal moves; customer question C-08)", variant_of="M-B1")
    for h_lbl, cond in [("2025-H2", lambda d: d < "2026-01-01"), ("2026-H1", lambda d: "2026-01-01" <= d < "2026-07-01"),
                        ("2026-H2 (to provisional cutoff)", lambda d: d >= "2026-07-01")]:
        os_ = [o for o in O.values() if cond(o["Offered On"])]
        a_ = sum(o["Status"] == "Accepted" for o in os_)
        d_ = sum(o["Status"] == "Declined" for o in os_)
        m.add(f"M-B5-{h_lbl[:7]}", "claim_B", f"Decided acceptance, offers made in {h_lbl} (offer-level)",
              "Accepted / (Accepted+Declined) by Offered On period", a_, a_ + d_, "Offers.Offered On cohort",
              variant_of="M-B1", notes=f"Pending in cohort: {sum(o['Status'] == 'Pending' for o in os_)}")
    dr = collections.Counter(o.get("Decline Reason") for o in O.values() if o["Status"] == "Declined")
    for r, c in dr.most_common():
        m.add(f"M-B6-{r}", "claim_B", f"Decline reason share: {r}", "declines with reason / all declines",
              c, dec, "Offers.Decline Reason")
    for status in ["Accepted", "Declined", "Pending"]:
        ratios = [o["Base CTC"] / C[one(A[one(o, "Application")], "Candidate")]["Expected CTC"]
                  for o in O.values() if o["Status"] == status]
        if not ratios:
            continue
        m.stat(f"M-B7-{status}", "claim_B", f"Median Base CTC / candidate Expected CTC: {status} offers",
               "median(offer Base CTC / Expected CTC)", round(statistics.median(ratios), 3), len(ratios),
               "Offers joined to Candidates", notes=f"min {min(ratios):.2f}, max {max(ratios):.2f}. NOT INTERPRETABLE: see DQ-25")
        below = sum(r < 1 for r in ratios)
        m.add(f"M-B8-{status}", "claim_B", f"{status} offers below candidate's Expected CTC",
              "count(Base CTC < Expected CTC) / offers with status", below, len(ratios), "Offers joined to Candidates",
              notes="NOT INTERPRETABLE: see DQ-25")

    # ---------------- channel quality (Source as recorded)
    for sname in SOURCES:
        sa = [k for k, a in A.items() if src(a) == sname]
        if not sa:
            continue
        iv = [k for k in sa if A[k].get("Interviews")]
        scores = [I[i]["Score"] for k in sa for i in A[k].get("Interviews", []) if "Score" in I[i]]
        pos = [I[i] for k in sa for i in A[k].get("Interviews", []) if I[i].get("Recommendation")]
        note = "Referral label; 0 of 7 Referral hires have a referrer link (M-A9n)" if sname == "Referral" else ""
        m.add(f"M-Q1-{sname}", "channel_quality", f"Interview reach (Source as recorded): {sname}", "applications with at least 1 interview / applications",
              len(iv), len(sa), "Source as recorded", notes=note)
        m.add(f"M-Q2-{sname}", "channel_quality", f"Offer rate after interview (Source as recorded): {sname}",
              "offered / interviewed", sum(bool(A[k].get("Offers")) for k in iv), len(iv), "Source as recorded", notes=note)
        m.add(f"M-Q3-{sname}", "channel_quality", f"Positive interview recommendations (Source as recorded): {sname}",
              "Hire or Strong Hire / interviews with a recommendation",
              sum(p["Recommendation"] in ("Hire", "Strong Hire") for p in pos), len(pos), "Interviews.Recommendation", level="interview")
        if scores:
            m.stat(f"M-Q4-{sname}", "channel_quality", f"Mean interview score (Source as recorded): {sname}", "mean(Interviews.Score)",
                   round(statistics.mean(scores), 2), len(scores), "Interviews linked to channel's applications", level="interview")

    # ---------------- department funnel (makes department statements traceable)
    for dn in sorted({d["Name"] for d in D.values()}):
        da = [k for k, a in A.items() if dept(a) == dn]
        for sub, pred in (("interviewed", lambda a: a.get("Interviews")), ("offered", lambda a: a.get("Offers")),
                          ("hired", lambda a: a["Stage"] == "Hired")):
            m.add(f"M-DF-{dn}-{sub}", "departments", f"{dn}: applications {sub}", f"{sub} / applications for department",
                  sum(bool(pred(A[k])) for k in da), len(da), "Applications by opening department (ASM-018)")

    # ---------------- cycle time (Applied On -> accepted offer Decision On)
    bad_dates = set()
    for k, a in A.items():
        if a["Applied On"] < J[one(a, "Opening")]["Opened On"]:
            bad_dates.add(k)
    for i in I.values():
        if i["Scheduled On"] < A[one(i, "Application")]["Applied On"]:
            bad_dates.add(one(i, "Application"))
    by_dept = collections.defaultdict(list)
    hires_by_dept = collections.Counter(dept(A[k]) for k in hires)
    for k in hires:
        if k in bad_dates:
            continue
        by_dept[dept(A[k])].append(days(A[k]["Applied On"], offer(A[k])["Decision On"]))
    all_d = [d for v in by_dept.values() for d in v] or [float("nan")]
    m.stat("M-T0", "cycle_time", "Median days Applied -> offer accepted (all hires)",
           "median(Offers.Decision On - Applied On), Stage=Hired; excludes hires whose Applied On is contradicted by "
           "another record (Applied On before the opening's Opened On, or an Interviews record scheduled before Applied On)",
           statistics.median(all_d), len(all_d), "Offers.Decision On used as the hire date (DEC-011, DQ-18)",
           notes=f"{len(all_d)} of {len(hires)} hires measurable; excluded {sum(1 for k in hires if k in bad_dates)}")
    for dn, v in sorted(by_dept.items(), key=lambda x: -statistics.median(x[1])):
        m.stat(f"M-T1-{dn}", "cycle_time", f"Median days Applied -> accepted: {dn}", "as M-T0, by department",
               statistics.median(v), len(v), "as M-T0", notes=f"{len(v)} of {hires_by_dept[dn]} hires measurable; values {sorted(v)}")
    # stage lags: both date sources are reported (DEC-019); neither is treated as authoritative
    lags = {
        ("Applied -> Screened", "Applications.Applied On, Screened On"):
            [days(a["Applied On"], a.get("Screened On")) for a in A.values() if a.get("Screened On")],
        ("Screened -> first interview (source)", "Interviews.Scheduled On (min)"):
            [days(a["Screened On"], min(I[i]["Scheduled On"] for i in a["Interviews"])) for a in A.values() if a.get("Interviews") and a.get("Screened On")],
        ("Screened -> first interview (copy)", "Applications.First Interview On"):
            [days(a["Screened On"], a.get("First Interview On")) for a in A.values() if a.get("First Interview On") and a.get("Screened On")],
        ("Last recorded interview -> offer (source)", "Interviews.Scheduled On (max) -> Offers.Offered On"):
            [days(max(I[i]["Scheduled On"] for i in a["Interviews"]), offer(a)["Offered On"]) for a in A.values() if a.get("Offers") and a.get("Interviews")],
        ("Final interview -> offer (copy)", "Applications.Final Interview On -> Applications.Offered On"):
            [days(a["Final Interview On"], a["Offered On"]) for a in A.values() if a.get("Final Interview On") and a.get("Offered On")],
        ("Offer -> decision", "Offers.Offered On -> Decision On (decided offers)"):
            [days(o["Offered On"], o["Decision On"]) for o in O.values() if o.get("Decision On") and o["Status"] != "Pending"],
    }
    for (name, fields), v in lags.items():
        v2 = [x for x in v if x is not None and x >= 0]
        if not v2:
            continue
        m.stat(f"M-T2-{name}", "cycle_time", f"Median days {name}", "median of non-negative lags",
               statistics.median(v2), len(v2), fields, level="application",
               notes=f"p75={sorted(v2)[int(0.75 * (len(v2) - 1))]}, max={max(v2)}, negative excluded={len(v) - len(v2)}")

    # ---------------- offer declines by department / level
    dl = collections.defaultdict(lambda: [0, 0])
    for o in O.values():
        if o["Status"] in ("Accepted", "Declined"):
            dl[dept(A[one(o, "Application")])][o["Status"] == "Declined"] += 1
    for dn, (acc_n, dec_n) in sorted(dl.items()):
        m.add(f"M-D1-{dn}", "declines", f"Decline rate: {dn}", "Declined / decided offers", dec_n, acc_n + dec_n,
              "Offers by opening department")
    ll = collections.defaultdict(lambda: [0, 0])
    for o in O.values():
        if o["Status"] in ("Accepted", "Declined"):
            ll[J[one(A[one(o, "Application")], "Opening")]["Level"]][o["Status"] == "Declined"] += 1
    for lv, (acc_n, dec_n) in sorted(ll.items()):
        m.add(f"M-D2-{lv}", "declines", f"Decline rate: level {lv}", "Declined / decided offers", dec_n, acc_n + dec_n,
              "Offers by opening level")

    # ---------------- interview execution
    for rnd in sorted({i["Round"] for i in I.values()}):
        ri = [i for i in I.values() if i["Round"] == rnd]
        m.add(f"M-I1-{rnd}", "interviews", f"Interviews not completed (No Show/Cancelled/Rescheduled): {rnd}",
              "non-Completed / scheduled", sum(i["Outcome"] != "Completed" for i in ri), len(ri), "Interviews.Outcome")
    m.add("M-I0", "interviews", "Interviews not completed (all rounds)", "non-Completed / scheduled",
          sum(i["Outcome"] != "Completed" for i in I.values()), len(I), "Interviews.Outcome",
          notes=str(dict(collections.Counter(i["Outcome"] for i in I.values()))))
    m.add("M-I2", "interviews", "Rejection reason 'No Show' share of rejections",
          "Rejection Reason='No Show' / Stage=Rejected", sum(A[k].get("Rejection Reason") == "No Show" for k in rej), len(rej),
          "Applications.Rejection Reason", level="application")
    for reason, cnt in collections.Counter(A[k].get("Rejection Reason") for k in rej).most_common():
        m.add(f"M-R2-{reason}", "funnel", f"Rejection reason share: {reason}", "count / Stage=Rejected", cnt, len(rej),
              "Applications.Rejection Reason")
    return m
