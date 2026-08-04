"""
JSON analytics endpoints consumed by the dashboard's Chart.js widgets.
Kept separate from admin.py so the "data layer" for charts is easy to
find and reuse (e.g. if this were ever exposed to another internal tool).
"""

from collections import Counter, defaultdict

from flask import Blueprint, jsonify
from flask_login import login_required

from ..models import Campaign, Event

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/campaigns/<int:campaign_id>/funnel")
@login_required
def funnel(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    counts = Counter(ct.latest_stage() for ct in campaign.campaign_targets)
    order = ["not_sent", "sent", "opened", "clicked", "submitted", "reported"]
    return jsonify({"labels": order, "values": [counts.get(k, 0) for k in order]})


@bp.route("/campaigns/<int:campaign_id>/mitre")
@login_required
def mitre_breakdown(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    tech_counts = Counter()
    for ct in campaign.campaign_targets:
        for e in ct.events:
            tech_counts[e.technique_id] += 1

    labels = list(tech_counts.keys())
    values = [tech_counts[k] for k in labels]
    return jsonify({"labels": labels, "values": values})


@bp.route("/campaigns/<int:campaign_id>/timeline")
@login_required
def timeline(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    by_day = defaultdict(lambda: defaultdict(int))

    for ct in campaign.campaign_targets:
        for e in ct.events:
            day = e.timestamp.strftime("%Y-%m-%d") if e.timestamp else "unknown"
            by_day[day][e.event_type] += 1

    days = sorted(by_day.keys())
    event_types = ["sent", "opened", "clicked", "submitted", "reported"]
    series = {et: [by_day[d].get(et, 0) for d in days] for et in event_types}

    return jsonify({"days": days, "series": series})