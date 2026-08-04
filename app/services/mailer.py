"""
Email delivery for a campaign launch.

MAIL_MODE=simulate (default): nothing is sent anywhere. Each target's
personalized email is rendered and written to an .eml file under
data/outbox/ so you can open it in Mail.app/any client and see exactly
what a recipient would have seen — pixel, click link, tracking token and
all — without ever touching a real inbox. This is the right default for
a portfolio/demo project.

MAIL_MODE=ses: sends via AWS SES using boto3. Intended only for real,
authorized internal awareness programs (e.g. SES sandbox + verified
company addresses, or a production SES setup with organizational
sign-off). Never point this at addresses you don't have explicit
authorization to test.
"""

import os
from email.message import EmailMessage

from flask import current_app, url_for

from ..models import Event, db
from .mitre_mapper import resolve_event_technique, severity_for_event
from .logger import log_event


def render_email_body(template, tracking_token: str) -> str:
    base_url = current_app.config["BASE_URL"]
    pixel_url = f"{base_url}/t/{tracking_token}/pixel.png"
    click_url = f"{base_url}/t/{tracking_token}/click"
    report_url = f"{base_url}/t/{tracking_token}/report"

    body = template.html_body
    body = body.replace("{{click_url}}", click_url)
    body = body.replace("{{report_url}}", report_url)
    body += f'\n<img src="{pixel_url}" width="1" height="1" alt="" style="display:none">'
    return body


def _record_sent_event(campaign_target, template):
    tech = resolve_event_technique("sent", template.technique_id)
    event = Event(
        campaign_target_id=campaign_target.id,
        event_type="sent",
        technique_id=tech["technique_id"],
        tactic=tech["tactic"],
        severity=severity_for_event("sent"),
    )
    db.session.add(event)
    db.session.commit()

    log_event(current_app._get_current_object(), {
        "timestamp": event.timestamp.isoformat(),
        "event_type": "sent",
        "campaign_id": campaign_target.campaign_id,
        "campaign_target_id": campaign_target.id,
        "technique_id": tech["technique_id"],
        "tactic": tech["tactic"],
        "severity": event.severity,
    })


def send_campaign(campaign):
    """Send (or simulate sending) every target enrolled in a campaign."""
    template = campaign.template
    mode = current_app.config["MAIL_MODE"]

    results = {"sent": 0, "mode": mode, "outbox": []}

    for ct in campaign.campaign_targets:
        body = render_email_body(template, ct.tracking_token)

        if mode == "ses":
            _send_via_ses(template, ct, body)
        else:
            path = _write_simulated_eml(template, ct, body)
            results["outbox"].append(path)

        ct.sent_at = db.func.now()
        _record_sent_event(ct, template)
        results["sent"] += 1

    db.session.commit()
    return results


def _write_simulated_eml(template, campaign_target, body):
    os.makedirs(current_app.config["OUTBOX_DIR"], exist_ok=True)

    msg = EmailMessage()
    msg["Subject"] = template.subject
    msg["From"] = f"{template.sender_display} <{current_app.config['SES_SENDER']}>"
    msg["To"] = campaign_target.target.email
    msg.set_content("This message requires an HTML-capable email client.")
    msg.add_alternative(body, subtype="html")

    filename = f"campaign{campaign_target.campaign_id}_target{campaign_target.target_id}.eml"
    path = os.path.join(current_app.config["OUTBOX_DIR"], filename)
    with open(path, "wb") as f:
        f.write(bytes(msg))
    return path


def _send_via_ses(template, campaign_target, body):  # pragma: no cover - requires AWS creds
    import boto3

    client = boto3.client("ses", region_name=current_app.config["AWS_REGION"])
    client.send_email(
        Source=current_app.config["SES_SENDER"],
        Destination={"ToAddresses": [campaign_target.target.email]},
        Message={
            "Subject": {"Data": template.subject},
            "Body": {"Html": {"Data": body}},
        },
    )