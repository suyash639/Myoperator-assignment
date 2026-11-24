"""B2 inactivity flags: executable reference model (specification for engineering).

Threshold is configurable per application stage at org level. 90 days is the PROVISIONAL default for every stage
(ASM-021) until the live baseline and Pilot 1. A flag means only "no recorded activity for more than N days";
"abandoned" can only be set by a recruiter as a disposition. Nothing here changes an application's status.
"""
from __future__ import annotations

from src.data import days

DEFAULT_DAYS = 90
STAGES = ("Applied", "Screening", "Interview", "Offer")
MIN_DAYS, MAX_DAYS = 14, 365
DISPOSITIONS = {"still_active": "Still active (snooze)", "abandoned": "Closed: recruiter-confirmed abandoned",
                "closed_other": "Closed: other reason", "advanced": "Advanced to next stage"}


class ConfigError(ValueError):
    pass


def thresholds(overrides: dict[str, int] | None = None) -> dict[str, int]:
    t = {s: DEFAULT_DAYS for s in STAGES}
    for stage, n in (overrides or {}).items():
        if stage not in STAGES:
            raise ConfigError(f"unknown stage {stage}")
        if not MIN_DAYS <= n <= MAX_DAYS:
            raise ConfigError(f"threshold {n} outside {MIN_DAYS}-{MAX_DAYS} days")
        t[stage] = n
    return t


def flag(stage: str, last_activity: str, as_of: str, config: dict[str, int]) -> str | None:
    """Return the flag label or None. Never returns 'abandoned'."""
    n = config[stage]
    return f"Inactive > {n} days" if days(last_activity, as_of) > n else None


def dispose(flag_label: str | None, disposition: str, reason: str | None, recruiter: str) -> dict:
    """Record a recruiter disposition. 'abandoned' exists only here, chosen by a person."""
    if not flag_label:
        raise ConfigError("no flag to dispose")
    if disposition not in DISPOSITIONS:
        raise ConfigError(f"unknown disposition {disposition}")
    if disposition in ("still_active", "abandoned", "closed_other") and not reason:
        raise ConfigError("disposition requires a reason")
    if not recruiter:
        raise ConfigError("disposition requires the recruiter's identity")
    return {"flag": flag_label, "disposition": DISPOSITIONS[disposition], "reason": reason, "by": recruiter,
            "reversible_days": 30 if disposition in ("abandoned", "closed_other") else 0}
