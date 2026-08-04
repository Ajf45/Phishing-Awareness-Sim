"""
Public, unauthenticated endpoints. These are the only URLs a simulated
target ever touches — everything is keyed off the unguessable
`tracking_token` embedded in their email, never off email address or
target id, so links can't be tampered with to spy on other targets.

Important safety property: the "credential submit" landing page NEVER
persists whatever the target typed. We only log the fact that a
submission happened (for the susceptibility score) and immediately
redirect to an in-the-moment training/education page. That's what makes
this a training tool and not a credential harvester.
"""

from datetime import datetime, timezone

from flask import Blueprint, abort, redirect, render_template, request, current_app, url_for

from ..models import CampaignTarget, Event, db
from ..services.mitre_mapper import resolve_event_technique, severity_for_event
from ..services.logger import log_event

bp = Blueprint("tracking", __name__)

# 1x1 transparent GIF, served for the open-tracking pixel
TRANSPARENT_GIF = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f90401000000002c00000000010001000002024401003b"
)


def _get_campaign_target_or_404(token):
    ct = CampaignTarget.query.filter_by(tracking_token=token).first()
    if ct is None:
        abort(404)
    return ct


def _record_event(campaign_target, event_type):
    template = campaign_target.campaign.template
    tech = resolve_event_technique(event_type, template.technique_id)

    event = Event(
        campaign_target_id=campaign_target.id,
        event_type=event_type,
        technique_id=tech["technique_id"],
        tactic=tech["tactic"],
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=request.headers.get("User-Agent", "")[:255],
        severity=severity_for_event(event_type),
    )
    db.session.add(event)
    db.session.commit()

    log_event(current_app._get_current_object(), {
        "timestamp": event.timestamp.isoformat(),
        "event_type": event_type,
        "campaign_id": campaign_target.campaign_id,
        "campaign_target_id": campaign_target.id,
        "technique_id": tech["technique_id"],
        "tactic": tech["tactic"],
        "severity": event.severity,
        "source_ip": event.ip_address,
        "user_agent": event.user_agent,
    })
    return event


@bp.route("/t/<token>/pixel.png")
def pixel(token):
    ct = _get_campaign_target_or_404(token)
    # Only log the first open per target to keep the funnel meaningful
    # (mail clients often re-fetch images on scroll/reopen).
    already = any(e.event_type == "opened" for e in ct.events)
    if not already:
        _record_event(ct, "opened")
    return TRANSPARENT_GIF, 200, {"Content-Type": "image/gif"}


@bp.route("/t/<token>/click")
def click(token):
    ct = _get_campaign_target_or_404(token)
    _record_event(ct, "clicked")
    return redirect(url_for("tracking.landing", token=token))


@bp.route("/t/<token>/landing")
def landing(token):
    ct = _get_campaign_target_or_404(token)
    template = ct.campaign.template
    return render_template(
        "landing.html",
        token=token,
        template=template,
        org_name=current_app.config["ORG_NAME"],
    )


@bp.route("/t/<token>/submit", methods=["POST"])
def submit(token):
    ct = _get_campaign_target_or_404(token)
    # Deliberately not reading/storing request.form values beyond the fact
    # a submission occurred — see module docstring.
    _record_event(ct, "submitted")
    return redirect(url_for("tracking.educate", token=token))


@bp.route("/t/<token>/educate")
def educate(token):
    ct = _get_campaign_target_or_404(token)
    return render_template(
        "educate.html",
        token=token,
        org_name=current_app.config["ORG_NAME"],
    )


@bp.route("/t/<token>/report")
def report(token):
    ct = _get_campaign_target_or_404(token)
    _record_event(ct, "reported")
    return render_template(
        "reported.html",
        org_name=current_app.config["ORG_NAME"],
    )