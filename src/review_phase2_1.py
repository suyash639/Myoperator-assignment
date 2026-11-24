"""Phase 2.1 independent review checks → outputs/phase2_1_checks.csv.

    uv run python -m src.review_phase2_1

Re-derives, from the raw snapshot only, the evidence used in outputs/phase2_1_review.md. It does
NOT import src.metrics or src.audit, so it is an independent re-implementation of the counts it
re-checks. It modifies no existing output and never writes to data/raw (raw checksums are verified
by src.data.load and re-hashed before and after).

Personal fields (names, emails, phones) are compared but never written; output carries record IDs,
business IDs (CAND-/APP-/OFF-/REQ-) and booleans only.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import math
import re
import statistics as st
import sys
from pathlib import Path

from src.data import AS_OF, RAW_DIR, days, load, one

OUT = Path("outputs/phase2_1_checks.csv")
IMPORT_DATE = "2026-08-27"          # every createdTime is 2026-08-27T16:39–16:40Z
EXTRACTION_DATE = "2026-11-24"


def run() -> list[dict]:
    s = load()
    C, A, O, I, J, D = (s.f(t) for t in ("Candidates", "Applications", "Offers", "Interviews", "Job Openings", "Departments"))
    rows: list[dict] = []

    def add(cid, area, check, num, den, detail="", evidence="", ratio=True):
        pct = f"{100 * num / den:.1f}%" if ratio and isinstance(num, int) and isinstance(den, int) and den else ""
        rows.append({"check_id": cid, "area": area, "check": check, "numerator": num, "denominator": den,
                     "pct": pct, "detail": detail, "evidence": evidence})

    ints = lambda a: [I[i] for i in a.get("Interviews", [])]
    off = lambda a: O[a["Offers"][0]] if a.get("Offers") else {}
    dept = lambda a: D[one(J[one(a, "Opening")], "Department")]["Name"]
    hires = [k for k, a in A.items() if a["Stage"] == "Hired"]

    # ---------------- R1 snapshot / as-of date
    D_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")
    for t, recs in s.raw.items():
        fields = collections.defaultdict(list)
        for r in recs:
            for k, v in r["fields"].items():
                if isinstance(v, str) and D_RE.match(v):
                    fields[k].append(v)
        for k, v in sorted(fields.items()):
            after = sorted(x for x in v if x > IMPORT_DATE)
            if after:
                add("R1-date-after-import", "as-of date", f"{t}.{k} values after the bulk-import date {IMPORT_DATE}",
                    len(after), len(v), f"max {max(v)}", "; ".join(after))
    ct = sorted({r["createdTime"] for rs in s.raw.values() for r in rs})
    add("R1-createdTime", "as-of date", "Airtable createdTime range (all records)", len(ct), sum(len(r) for r in s.raw.values()),
        f"{ct[0]} .. {ct[-1]}; numerator = distinct createdTime values", ratio=False)
    add("R1-max-applied", "as-of date", "Applications with Applied On = max(Applied On)",
        sum(1 for a in A.values() if a["Applied On"] == max(x["Applied On"] for x in A.values())), len(A),
        f"max Applied On {max(a['Applied On'] for a in A.values())}")
    pend = [o for o in O.values() if o["Status"] == "Pending"]
    for label, ref in (("as-of 2026-08-27", AS_OF), ("as-of 2026-08-30 (latest Created On)", "2026-08-30"),
                       ("as-of extraction 2026-11-24", EXTRACTION_DATE)):
        ages = sorted(days(o["Offered On"], ref) for o in pend)
        stale = sum(a > 30 for a in ages)
        acc = sum(o["Status"] == "Accepted" for o in O.values())
        dec = sum(o["Status"] == "Declined" for o in O.values())
        add("R1-sens-M-B3", "as-of date", f"M-B3 stale-as-expired acceptance, {label}", acc, acc + dec + stale,
            f"pending ages {ages}; stale>30d={stale}")
        op = [j for j in J.values() if j["Status"] == "Open"]
        add("R1-sens-DQ-12", "as-of date", f"Open openings past Target Close, {label}",
            sum(j["Target Close"] < ref for j in op), len(op))

    # ---------------- R2 duplicate candidates (identity fields compared, never written)
    norm = lambda c: (c["Full Name"].strip().lower(), c["Phone"].replace(" ", ""))
    grp = collections.defaultdict(list)
    for k, c in C.items():
        grp[norm(c)].append(k)
    pairs = [sorted(v, key=lambda x: C[x]["Created On"]) for v in grp.values() if len(v) > 1]
    epat = lambda e: "first.lastN" if re.fullmatch(r"[a-z]+\.[a-z]+\d+", e.split("@")[0]) else (
        "f.last" if re.fullmatch(r"[a-z]\.[a-z]+", e.split("@")[0]) else "other")
    add("R2-email-pattern", "duplicates", "Candidates whose email uses the f.last pattern",
        sum(epat(c["Email"]) == "f.last" for c in C.values()), len(C),
        "all 6 belong to the 6 name+phone pairs (one per pair)")
    add("R2-name-only", "duplicates", "Name collision groups / phone collision groups",
        sum(1 for v in collections.Counter(norm(c)[0] for c in C.values()).values() if v > 1),
        sum(1 for v in collections.Counter(norm(c)[1] for c in C.values()).values() if v > 1),
        "numerator = name groups, denominator = phone groups; identical sets", ratio=False)
    person = {k: tuple(p) for p in pairs for k in p}
    for i, (a_, b_) in enumerate(pairs, 1):
        ca, cb = C[a_], C[b_]
        same = {k: ca.get(k) == cb.get(k) for k in ("City", "Current Company", "Source", "Years Experience",
                                                       "Current CTC", "Expected CTC", "Notice Period Days")}
        same_dom = ca["Email"].split("@")[1] == cb["Email"].split("@")[1]
        yoe_gap = abs(ca["Years Experience"] - cb["Years Experience"])
        created_gap = days(ca["Created On"], cb["Created On"])
        hired = [A[x]["Application ID"] for x in ca["Applications"] + cb["Applications"] if A[x]["Stage"] == "Hired"]
        # identity evidence vs attribute consistency
        consistent = yoe_gap <= created_gap / 365 + 0.5
        add(f"R2-pair-{i}", "duplicates", f"{ca['Candidate ID']} vs {cb['Candidate ID']}",
            sum(same.values()), len(same),
            f"name=Y phone=Y city={'Y' if same['City'] else 'N'} company={'Y' if same['Current Company'] else 'N'} "
            f"email_domain={'Y' if same_dom else 'N'} email_patterns={epat(ca['Email'])}/{epat(cb['Email'])}; "
            f"Source {ca['Source']}/{cb['Source']}; YoE {ca['Years Experience']}/{cb['Years Experience']} "
            f"(gap {yoe_gap:.1f}y vs created {created_gap}d apart: {'plausible' if consistent else 'IMPLAUSIBLE for one person'}); "
            f"Current CTC {'same' if same['Current CTC'] else 'differs'}; hires {hired or 'none'}",
            f"{a_};{b_}")
    hired_recs = {one(A[k], "Candidate") for k in hires}
    add("R2-hires-app-level", "duplicates", "Hires (application level)", len(hires), len(hires))
    add("R2-hires-candidate-level", "duplicates", "Distinct hired candidate records", len(hired_recs), len(hires))
    add("R2-hires-person-level", "duplicates", "Distinct hired persons after merging name+phone pairs",
        len({person.get(c, (c,)) for c in hired_recs}), len(hires), "no pair has a hire on both records")

    # ---------------- R3 channel attribution
    add("R3-app-source-field", "attribution", "Applications carrying a Source field",
        sum("Source" in a for a in A.values()), len(A), "Source exists only on Candidates")
    xt = collections.Counter((C[one(a, "Candidate")]["Source"], bool(a.get("Referred By"))) for a in A.values())
    add("R3-xtab-apps", "attribution", "Applications by (Candidate Source, has Referred By)", len(A), len(A),
        "; ".join(f"{s_}/{'ref' if r else 'noref'}={n}" for (s_, r), n in sorted(xt.items())))
    xh = collections.Counter((C[one(A[k], "Candidate")]["Source"], bool(A[k].get("Referred By"))) for k in hires)
    add("R3-xtab-hires", "attribution", "Hires by (Candidate Source, has Referred By)", len(hires), len(hires),
        "; ".join(f"{s_}/{'ref' if r else 'noref'}={n}" for (s_, r), n in sorted(xh.items())))
    add("R3-referral-hires-without-link", "attribution", "Source=Referral hires with no Referred By link",
        sum(1 for k in hires if C[one(A[k], "Candidate")]["Source"] == "Referral" and not A[k].get("Referred By")),
        sum(1 for k in hires if C[one(A[k], "Candidate")]["Source"] == "Referral"))
    add("R3-referrer-linked-hires", "attribution", "Hires with a Referred By link (any Source)",
        sum(1 for k in hires if A[k].get("Referred By")), len(hires))
    multi = collections.Counter()
    for c in C.values():
        if len(c["Applications"]) > 1:
            multi[len({bool(A[x].get("Referred By")) for x in c["Applications"]}) == 1] += 1
    add("R3-referrer-consistent-per-candidate", "attribution",
        "Multi-application candidates whose Referred By presence is the same on every application",
        multi[True], multi[True] + multi[False])
    for name, key in (("Created On", lambda c: C[c]["Created On"]),
                      ("earliest Applied On", lambda c: min(A[x]["Applied On"] for x in C[c]["Applications"]))):
        cnt = collections.Counter(C[min(person.get(one(A[k], "Candidate"), (one(A[k], "Candidate"),)), key=key)]["Source"]
                                  for k in hires)
        add(f"R3-first-touch-{'created' if name == 'Created On' else 'applied'}", "attribution",
            f"Job Board hires, duplicates merged, first touch by {name}", cnt["Job Board"], len(hires),
            "; ".join(f"{k}={v}" for k, v in cnt.most_common()))
    strict = collections.Counter("Referral" if A[k].get("Referred By") else
                                 ("Referral label, no referrer" if C[one(A[k], "Candidate")]["Source"] == "Referral"
                                  else C[one(A[k], "Candidate")]["Source"]) for k in hires)
    add("R3-strict-referral", "attribution", "Job Board hires when Referral requires a referrer link (strict)",
        strict["Job Board"], len(hires), "; ".join(f"{k}={v}" for k, v in strict.most_common()))

    # per-application hire rate by channel under each attribution variant
    def rate_rows(tag, label, src):
        apps = collections.Counter(src(a) for a in A.values())
        h = collections.Counter(src(a) for a in A.values() if a["Stage"] == "Hired")
        for ch in sorted(apps):
            add(f"R3-rate-{tag}-{ch}", "attribution", f"Hire rate per application, {label}: {ch}", h[ch], apps[ch])
    rate_rows("V0", "V0 Source as recorded", lambda a: C[one(a, "Candidate")]["Source"])
    rate_rows("V4", "V4 strict referral", lambda a: "Referral" if a.get("Referred By") else (
        "Referral label, no referrer" if C[one(a, "Candidate")]["Source"] == "Referral" else C[one(a, "Candidate")]["Source"]))
    rate_rows("V5", "V5 merged first-touch (Created On)", lambda a: C[min(person.get(one(a, "Candidate"), (one(a, "Candidate"),)), key=lambda c: C[c]["Created On"])]["Source"])
    rate_rows("V6", "V6 merged first-touch (earliest Applied On)", lambda a: C[min(person.get(one(a, "Candidate"), (one(a, "Candidate"),)), key=lambda c: min(A[x]["Applied On"] for x in C[c]["Applications"]))]["Source"])

    # ---------------- R4 offers
    stc = collections.Counter(o["Status"] for o in O.values())
    add("R4-status", "offers", "Offers by Status", len(O), len(O), "; ".join(f"{k}={v}" for k, v in stc.most_common()))
    add("R4-offers-per-app", "offers", "Applications with more than one offer",
        sum(len(a.get("Offers", [])) > 1 for a in A.values()), sum(bool(a.get("Offers")) for a in A.values()))
    pc = collections.defaultdict(list)
    for o in O.values():
        pc[one(A[one(o, "Application")], "Candidate")].append(f"{o['Offer ID']}:{o['Status']}:{o['Offered On']}:"
                                                              f"{J[one(A[one(o, 'Application')], 'Opening')]['Req ID']}")
    add("R4-multi-offer-candidates", "offers", "Candidates with more than one offer",
        sum(len(v) > 1 for v in pc.values()), len(pc),
        " | ".join(f"{C[k]['Candidate ID']}: {', '.join(v)}" for k, v in pc.items() if len(v) > 1))
    for st_ in ("Accepted", "Declined", "Pending"):
        sub = [o for o in O.values() if o["Status"] == st_]
        stages = collections.Counter(f"{A[one(o, 'Application')]['Stage']}/{A[one(o, 'Application')]['Status']}" for o in sub)
        add(f"R4-{st_.lower()}-app-state", "offers", f"{st_} offers: linked application Stage/Status", len(sub), len(O),
            "; ".join(f"{k}={v}" for k, v in stages.items()))
    pend_dec = [o for o in pend if o.get("Decision On")]
    add("R4-pending-with-decision", "offers", "Pending offers with a Decision On", len(pend_dec), len(pend),
        "; ".join(f"{o['Offer ID']} offered {o['Offered On']} decided {o['Decision On']} "
                  f"(+{days(o['Offered On'], o['Decision On'])}d)" for o in pend_dec))
    dd = [days(o["Offered On"], o["Decision On"]) for o in O.values() if o["Status"] != "Pending"]
    add("R4-decided-lag", "offers", "Offered -> Decision days, decided offers (numerator=min, denominator=max)", min(dd), max(dd), ratio=False)
    already = [o for o in O.values() if any(
        A[x]["Stage"] == "Hired" and off(A[x]).get("Decision On", "9") < o["Offered On"]
        for x in C[one(A[one(o, "Application")], "Candidate")]["Applications"] if x != one(o, "Application"))]
    add("R4-offer-after-prior-hire", "offers", "Offers made to a candidate already hired via another application",
        len(already), len(O), "; ".join(f"{o['Offer ID']}:{o['Status']}" for o in already))

    # ---------------- R5 funnel nesting and cohort
    scr = {k for k, a in A.items() if a.get("Screened On")}
    iv = {k for k, a in A.items() if a.get("Interviews")}
    of = {k for k, a in A.items() if a.get("Offers")}
    hi = set(hires)
    add("R5-nesting", "funnel", "Stage-reach sets not nested (interviewed-not-screened + offered-not-interviewed + hired-not-offered)",
        len(iv - scr) + len(of - iv) + len(hi - of), len(A))
    for nm, ss, prev in (("screened", scr, set(A)), ("interviewed", iv, scr), ("offered", of, iv), ("hired", hi, of)):
        add(f"R5-overall-{nm}", "funnel", f"Overall conversion to {nm} (all applications)", len(ss), len(A))
        add(f"R5-step-{nm}", "funnel", f"Previous-stage conversion to {nm}", len(ss), len(prev))
    q = collections.defaultdict(collections.Counter)
    for a in A.values():
        y, m = a["Applied On"][:4], int(a["Applied On"][5:7])
        q[f"{y}Q{(m - 1) // 3 + 1}"][a["Status"]] += 1
    add("R5-cohort-mix", "funnel", "Applications by applied quarter (Active/Closed)", len(A), len(A),
        "; ".join(f"{k}: active {v['Active']} closed {v['Closed']}" for k, v in sorted(q.items())))
    stale = collections.Counter()
    tot = collections.Counter()
    for a in A.values():
        if a["Status"] == "Active":
            last = max(x for x in [a["Applied On"], a.get("Screened On")] + [i["Scheduled On"] for i in ints(a)] if x)
            tot[a["Stage"]] += 1
            stale[a["Stage"]] += days(last, AS_OF) > 90
    add("R5-stale-active", "funnel", "Active applications with no recorded activity for >90 days at as-of",
        sum(stale.values()), sum(tot.values()), "; ".join(f"{k} {stale[k]}/{tot[k]}" for k in tot))
    add("R5-active-on-filled", "funnel", "Active applications on openings whose Status is Filled",
        sum(1 for a in A.values() if a["Status"] == "Active" and J[one(a, "Opening")]["Status"] == "Filled"),
        sum(1 for a in A.values() if a["Status"] == "Active"))

    # ---------------- R6 sensitivity (one-record swing) instead of sampling intervals
    for mid, n in (("hire share (n=26)", 26), ("decided acceptance (n=31)", 31), ("all-offer acceptance (n=36)", 36)):
        add(f"R6-swing-{n}", "uncertainty", f"Percentage points moved by one record: {mid}", 1, n)

    # ---------------- R7 compensation units
    add("R7-phone-prefix", "compensation", "Candidates with +91 phone prefix",
        sum(c["Phone"].startswith("+91") for c in C.values()), len(C))
    r = [c["Expected CTC"] / c["Current CTC"] for c in C.values()]
    qs = st.quantiles(r, n=10)
    add("R7-expected-vs-current", "compensation", "Candidate Expected/Current CTC ratio (p10, median, p90)",
        round(qs[0], 2), round(qs[8], 2), f"median {st.median(r):.2f}; min {min(r):.2f}; max {max(r):.2f}")
    xs = [c["Years Experience"] for c in C.values()]
    ys = [c["Expected CTC"] for c in C.values()]
    mx, my = st.mean(xs), st.mean(ys)
    cor = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    add("R7-yoe-expected-corr", "compensation", "Pearson r, Years Experience vs Expected CTC (x100)", round(100 * cor), 100, ratio=False)
    inband = collections.Counter()
    for a in A.values():
        j, e = J[one(a, "Opening")], C[one(a, "Candidate")]["Expected CTC"]
        inband["below" if e < j["Salary Band Min"] else "above" if e > j["Salary Band Max"] else "in"] += 1
    add("R7-expected-in-band", "compensation", "Applications whose candidate Expected CTC is inside the opening's band",
        inband["in"], len(A), f"below {inband['below']}; above {inband['above']}")
    obd = sum(1 for o in O.values() if J[one(A[one(o, 'Application')], 'Opening')]["Salary Band Min"] <= o["Base CTC"]
              <= J[one(A[one(o, 'Application')], 'Opening')]["Salary Band Max"])
    add("R7-offer-in-band", "compensation", "Offers whose Base CTC is inside the opening's band", obd, len(O))
    small = sum(1 for c in C.values() for k in ("Current CTC", "Expected CTC") if c[k] < 100000) + \
        sum(1 for o in O.values() if o["Base CTC"] < 100000)
    add("R7-monthly-scale", "compensation", "CTC values below 100,000 (would suggest monthly figures)", small, 2 * len(C) + len(O))

    # ---------------- R8 interview completeness
    per = collections.Counter(len(a.get("Interviews", [])) for a in A.values() if a.get("Interviews"))
    add("R8-interviews-per-app", "interviews", "Interviewed applications with exactly 1 interview record", per[1], sum(per.values()),
        "; ".join(f"{k} interviews: {v}" for k, v in sorted(per.items())))
    rs = collections.Counter(tuple(sorted(i["Round"] for i in ints(A[k]))) for k in hires)
    add("R8-hire-rounds", "interviews", "Hires whose only recorded interview is a Screen", rs[("Screen",)], len(hires),
        "; ".join(f"{'+'.join(k) or 'none'}={v}" for k, v in rs.most_common()))
    fin = [k for k, a in A.items() if a.get("Final Interview On")]
    gaps = [days(max(i["Scheduled On"] for i in ints(A[k])), A[k]["Final Interview On"]) for k in fin]
    add("R8-final-after-last", "interviews", "Final Interview On later than last recorded interview",
        sum(g > 0 for g in gaps), len(fin), f"gap days median {st.median(gaps)}, max {max(gaps)}, equal {sum(g == 0 for g in gaps)}")
    add("R8-final-population", "interviews", "Applications with Final Interview On that reached an offer",
        sum(bool(A[k].get("Offers")) for k in fin), len(fin),
        "; ".join(f"{k}={v}" for k, v in collections.Counter(A[k]["Stage"] for k in fin).items()))

    fo = [days(A[k]["Final Interview On"], off(A[k])["Offered On"]) for k in fin if A[k].get("Offers")]
    add("R8-final-to-offer", "interviews", "Final Interview On -> Offers.Offered On days (numerator=median, denominator=n)",
        st.median(fo), len(fo), f"min {min(fo)}, max {max(fo)}", ratio=False)
    fid = [abs(days(min(i["Scheduled On"] for i in ints(a)), a["First Interview On"])) for a in A.values()
           if a.get("Interviews") and a["First Interview On"] != min(i["Scheduled On"] for i in ints(a))]
    add("R8-first-interview-drift", "interviews", "First Interview On copy vs source: max absolute drift days (denominator=mismatches)",
        max(fid), len(fid), ratio=False)
    fut = [o for o in O.values() if o["Proposed Start Date"] > IMPORT_DATE]
    add("R4-start-after-import", "offers", "Offers with Proposed Start Date after the import date, by Status", len(fut), len(O),
        "; ".join(f"{k}={v}" for k, v in collections.Counter(o["Status"] for o in fut).items()))

    # ---------------- R9 departments
    for dname in sorted({d["Name"] for d in D.values()}):
        apps = [a for a in A.values() if dept(a) == dname]
        js = [j for j in J.values() if D[one(j, "Department")]["Name"] == dname]
        add(f"R9-{dname}", "departments", f"{dname}: hires / applications", sum(a["Stage"] == "Hired" for a in apps), len(apps),
            f"openings {len(js)} ({dict(collections.Counter(j['Status'] for j in js))}); headcount {sum(j['Headcount'] for j in js)}; "
            f"interviewed {sum(bool(a.get('Interviews')) for a in apps)}; offered {sum(bool(a.get('Offers')) for a in apps)}; "
            f"stages {dict(collections.Counter(a['Stage'] for a in apps))}")

    # ---------------- R10 date comparisons (every pair; expect left <= right)
    def chk(name, pairs, note=""):
        comp = [(k, a, b) for k, a, b in pairs if a and b]
        v = [k for k, a, b in comp if a > b]
        add("R10-dates", "dates", name, len(v), len(comp), note + (f" equal={sum(1 for _, a, b in comp if a == b)}"), "; ".join(v))

    last_iv = lambda a: max(i["Scheduled On"] for i in ints(a)) if ints(a) else None
    chk("Opening Opened On <= Applied On", [(k, J[one(a, 'Opening')]['Opened On'], a['Applied On']) for k, a in A.items()])
    chk("Applied On <= Screened On", [(k, a['Applied On'], a.get('Screened On')) for k, a in A.items()])
    chk("Applied On <= Closed On", [(k, a['Applied On'], a.get('Closed On')) for k, a in A.items()])
    chk("Applied On <= Interviews.Scheduled On (source)", [(i, a['Applied On'], I[i]['Scheduled On']) for k, a in A.items() for i in a.get('Interviews', [])])
    chk("Screened On <= Interviews.Scheduled On (source)", [(i, a.get('Screened On'), I[i]['Scheduled On']) for k, a in A.items() for i in a.get('Interviews', [])])
    chk("Interviews Scheduled On <= Completed On", [(k, i['Scheduled On'], i.get('Completed On')) for k, i in I.items()])
    chk("Screened On <= First Interview On (copy)", [(k, a.get('Screened On'), a.get('First Interview On')) for k, a in A.items()])
    chk("First Interview On (copy) <= Final Interview On (copy)", [(k, a.get('First Interview On'), a.get('Final Interview On')) for k, a in A.items()])
    chk("Final Interview On (copy) <= Offered On (copy)", [(k, a.get('Final Interview On'), a.get('Offered On')) for k, a in A.items()])
    chk("Final Interview On (copy) <= Offers.Offered On (source)", [(k, a.get('Final Interview On'), off(a).get('Offered On')) for k, a in A.items()])
    chk("Last Interviews.Scheduled On <= Offers.Offered On", [(k, last_iv(a), off(a).get('Offered On')) for k, a in A.items()])
    chk("Offers Offered On <= Decision On", [(k, o['Offered On'], o.get('Decision On')) for k, o in O.items()])
    chk("Offers Decision On <= Proposed Start Date", [(k, o.get('Decision On'), o['Proposed Start Date']) for k, o in O.items()])
    chk("Offers Offered On <= Proposed Start Date", [(k, o['Offered On'], o['Proposed Start Date']) for k, o in O.items()])
    chk("Offers.Offered On <= Application Closed On", [(k, off(a).get('Offered On'), a.get('Closed On')) for k, a in A.items()])
    chk("Offers.Decision On <= Closed On (Hired)", [(k, off(a).get('Decision On'), a.get('Closed On')) for k, a in A.items() if a['Stage'] == 'Hired'])
    chk("Offers.Decision On <= Closed On (Declined)", [(k, off(a).get('Decision On'), a.get('Closed On')) for k, a in A.items() if off(a).get('Status') == 'Declined'])
    chk("Last Interviews.Scheduled On <= Closed On (Rejected/Withdrawn)", [(k, last_iv(a), a.get('Closed On')) for k, a in A.items() if a['Stage'] in ('Rejected', 'Withdrawn')])
    chk("Candidate Created On <= Applied On", [(k, C[one(a, 'Candidate')]['Created On'], a['Applied On']) for k, a in A.items()])
    chk("Candidate Created On <= bulk-import date", [(k, c['Created On'], IMPORT_DATE) for k, c in C.items()])
    chk("Applied On <= opening Target Close (informational)", [(k, a['Applied On'], J[one(a, 'Opening')]['Target Close']) for k, a in A.items()])

    # copy-vs-source plausibility: which side of each disagreement is sequence-consistent?
    fi = [k for k, a in A.items() if a.get("Interviews") and a["First Interview On"] != min(i["Scheduled On"] for i in ints(a))]
    src_bad = [k for k in fi if min(i["Scheduled On"] for i in ints(A[k])) < A[k]["Applied On"]]
    copy_bad = [k for k in fi if A[k]["First Interview On"] < (A[k].get("Screened On") or A[k]["Applied On"])]
    add("R10-copy-vs-source-first-interview", "dates",
        "First Interview On mismatches where the SOURCE interview predates Applied On (copy plausible)",
        len(src_bad), len(fi), f"copy implausible in {len(copy_bad)}", "; ".join(A[k]["Application ID"] for k in src_bad))
    om = [k for k, a in A.items() if a.get("Offers") and a["Offered On"] != off(a)["Offered On"]]
    src_bad_o = [k for k in om if A[k].get("Final Interview On") and off(A[k])["Offered On"] < A[k]["Final Interview On"]]
    add("R10-copy-vs-source-offered", "dates",
        "Offered On mismatches where the SOURCE offer date precedes Final Interview On (copy consistent)",
        len(src_bad_o), len(om), "", "; ".join(A[k]["Application ID"] for k in src_bad_o))
    return rows


def main() -> int:
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW_DIR.glob("*.json"))}
    rows = run()
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW_DIR.glob("*.json"))}
    print(f"checks={len(rows)} raw unchanged={before == after}")
    return 0 if before == after else 1


if __name__ == "__main__":
    sys.exit(main())
