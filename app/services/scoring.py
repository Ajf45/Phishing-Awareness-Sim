"""
Behavioral susceptibility scoring.

Turns raw event streams into risk numbers a security team can act on:
per-target risk score, per-department rollups, and an overall campaign
"human risk index". The weighting reflects real-world impact — submitting
credentials is far worse than opening an email, and reporting the email
is rewarded (drives the score down) since that's the behavior the
training program is trying to reinforce.
"""

from collections import defaultdict

EVENT_WEIGHTS = {
    "sent": 0,
    "opened": 1,
    "clicked": 3,
    "submitted": 6,
    "reported": -3,
}

MAX_REASONABLE_SCORE = 10  # used to normalize to a 0-100 scale


def score_campaign_target(events) -> int:
    raw = sum(EVENT_WEIGHTS.get(e.event_type, 0) for e in events)
    return max(raw, 0)


def normalize(score: int) -> int:
    return min(100, round((score / MAX_REASONABLE_SCORE) * 100))


def risk_band(normalized_score: int) -> str:
    if normalized_score >= 66:
        return "high"
    if normalized_score >= 33:
        return "medium"
    return "low"


def campaign_summary(campaign_targets):
    """Given a list of CampaignTarget objects (with .events loaded),
    return funnel counts, human risk index, and per-department breakdown."""
    funnel = defaultdict(int)
    dept_scores = defaultdict(list)
    total_score = 0
    reported_count = 0

    for ct in campaign_targets:
        stage = ct.latest_stage()
        funnel[stage] += 1
        if stage == "reported":
            reported_count += 1

        raw_score = score_campaign_target(ct.events)
        norm = normalize(raw_score)
        total_score += norm

        dept_name = ct.target.department.name if ct.target.department else "Unassigned"
        dept_scores[dept_name].append(norm)

    n = len(campaign_targets) or 1
    human_risk_index = round(total_score / n)

    department_breakdown = [
        {
            "department": dept,
            "avg_score": round(sum(scores) / len(scores)) if scores else 0,
            "target_count": len(scores),
        }
        for dept, scores in dept_scores.items()
    ]
    department_breakdown.sort(key=lambda d: d["avg_score"], reverse=True)

    return {
        "funnel": dict(funnel),
        "human_risk_index": human_risk_index,
        "risk_band": risk_band(human_risk_index),
        "reported_count": reported_count,
        "total_targets": len(campaign_targets),
        "department_breakdown": department_breakdown,
    }