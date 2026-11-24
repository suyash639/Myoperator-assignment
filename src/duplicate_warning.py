"""B3 duplicate-candidate warning and source attribution: executable reference model (specification for engineering).

Duplicate detection is WARNING-ONLY. Nothing here, and nothing in B3, merges, deletes or rewrites candidate
records. The only outcomes are recruiter decisions recorded with the warning:
  same_person        the new application is attached to the EXISTING candidate record (no record is merged)
  different_person   a new candidate is created; the pair is remembered so the warning is not repeated
  unsure             a new candidate is created and the pair is queued for recruiting-ops review

Match rule (deliberately conservative to limit false positives): normalised full name AND normalised phone
both equal. Name-only or phone-only matches never warn. `scan()` applied to the snapshot must reproduce DQ-02.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Controlled acquisition-source taxonomy (how the candidate came to this application). Legacy values map 1:1.
SOURCES = ["Job Board", "LinkedIn", "Career Site", "Agency", "Employee Referral", "Campus", "Other"]
LEGACY_SOURCE_MAP = {"Job Board": "Job Board", "LinkedIn": "LinkedIn", "Career Site": "Career Site", "Agency": "Agency",
                     "Referral": "Employee Referral", "Campus": "Campus"}
SOURCE_DETAIL_REQUIRED = {"Job Board": "board name", "Agency": "agency name", "Other": "free-text description"}
# Intake method (how the record entered TalentFlow). System-derived from the creation path, never chosen by the recruiter.
INTAKE_METHODS = {"ui_manual": "Manual entry", "file_import": "File import", "api": "Integration/API",
                  "career_form": "Career-site form", "agency_portal": "Agency submission", "referral_form": "Referral submission"}
DECISIONS = {"same_person", "different_person", "unsure"}


class AttributionError(ValueError):
    pass


def norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def norm_phone(s: str) -> str:
    return re.sub(r"[^\d+]", "", s or "")


def intake_method(creation_path: str) -> str:
    if creation_path not in INTAKE_METHODS:
        raise AttributionError(f"unknown creation path {creation_path}")
    return INTAKE_METHODS[creation_path]


def attribute(source: str, referred_by: str | None, source_detail: str | None = None,
              endorsement_confirmed: bool = False) -> dict:
    """Validate acquisition source and referral attribution for a NEW application.

    Employee Referral  requires referred_by; referral_type = 'direct'.
    other source + referred_by  allowed only as an endorsement (an employee vouched for someone who applied via that
                    channel); requires explicit confirmation; reported separately, never counted as a referral hire.
    """
    if source not in SOURCES:
        raise AttributionError(f"source {source!r} not in taxonomy")
    if source in SOURCE_DETAIL_REQUIRED and not source_detail:
        raise AttributionError(f"{source} requires {SOURCE_DETAIL_REQUIRED[source]}")
    if source == "Employee Referral":
        if not referred_by:
            raise AttributionError("Employee Referral requires referred_by")
        return {"source": source, "referred_by": referred_by, "referral_type": "direct"}
    if referred_by:
        if not endorsement_confirmed:
            raise AttributionError("referrer on a non-referral source must be confirmed as an endorsement")
        return {"source": source, "referred_by": referred_by, "referral_type": "endorsement"}
    return {"source": source, "referred_by": None, "referral_type": None}


def legacy_attribution(source: str, has_referrer: bool) -> str:
    """How a legacy (snapshot) application would be classified under the new rules, without rewriting it."""
    s = LEGACY_SOURCE_MAP.get(source, "Other")
    if s == "Employee Referral":
        return "direct referral" if has_referrer else "referral label, no referrer (needs review)"
    return "endorsement" if has_referrer else "non-referral"


@dataclass
class Registry:
    """Existing candidates plus remembered pair decisions."""
    candidates: dict[str, dict] = field(default_factory=dict)       # id -> {"name", "phone"}
    not_duplicate: set[frozenset] = field(default_factory=set)
    review_queue: list[frozenset] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)

    def matches(self, name: str, phone: str) -> list[str]:
        n, p = norm_name(name), norm_phone(phone)
        return [cid for cid, c in self.candidates.items() if norm_name(c["name"]) == n and norm_phone(c["phone"]) == p]

    def intake(self, new_id: str, name: str, phone: str, decision: str | None = None, match_choice: str | None = None,
               reason: str | None = None, recruiter: str = "") -> dict:
        """Returns {'warning': [...], 'candidate_id': id_used}. Never merges or deletes records."""
        hits = [h for h in self.matches(name, phone) if frozenset({h, new_id}) not in self.not_duplicate]
        if not hits:
            self.candidates[new_id] = {"name": name, "phone": phone}
            return {"warning": [], "candidate_id": new_id}
        if decision not in DECISIONS:
            raise AttributionError("a recruiter decision is required when a duplicate warning is shown")
        if decision == "different_person" and not reason:
            raise AttributionError("'different_person' requires a reason")
        self.log.append({"new": new_id, "matches": hits, "decision": decision, "reason": reason, "recruiter": recruiter})
        if decision == "same_person":
            target = match_choice or hits[0]
            if target not in hits:
                raise AttributionError("chosen existing record is not among the matches")
            return {"warning": hits, "candidate_id": target}          # attach to existing; nothing merged
        self.candidates[new_id] = {"name": name, "phone": phone}
        for h in hits:
            pair = frozenset({h, new_id})
            if decision == "different_person":
                self.not_duplicate.add(pair)
            else:
                self.review_queue.append(pair)
        return {"warning": hits, "candidate_id": new_id}


def scan(snapshot) -> list[tuple[str, ...]]:
    """Existing probable-duplicate groups in the snapshot (read-only; for the ops review list, never merged)."""
    g: dict[tuple, list[str]] = {}
    for k, c in snapshot.f("Candidates").items():
        g.setdefault((norm_name(c.get("Full Name", "")), norm_phone(c.get("Phone", ""))), []).append(k)
    return [tuple(sorted(v)) for v in g.values() if len(v) > 1]
