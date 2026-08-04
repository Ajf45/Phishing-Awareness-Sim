"""
Database models.

Design notes:
- CampaignTarget holds a unique, unguessable `tracking_token` per
  (campaign, target) pair. That token — not the target's email or any
  personal identifier — is what appears in every tracking URL, so links
  can't be enumerated or used to leak who's in the campaign.
- Event stores one row per interaction (sent/opened/clicked/submitted/
  reported) so a full timeline can be reconstructed per target and per
  campaign, similar to how a SOC reconstructs an attack timeline from
  disparate log sources.
- We deliberately never persist any credential VALUE a target might type
  into the simulated landing page — only the fact that a submission event
  occurred. The platform measures susceptibility, not credentials.
"""

import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="security_analyst")
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)

    targets = db.relationship("Target", backref="department", lazy=True)


class Target(db.Model):
    """A simulated recipient. In a real deployment these come from an
    authorized internal roster (e.g. HRIS export), never a scraped list."""

    __tablename__ = "targets"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))

    campaign_links = db.relationship("CampaignTarget", backref="target", lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Template(db.Model):
    """A phishing pretext used for a campaign. `technique_id` maps the
    pretext itself to a MITRE ATT&CK initial-access technique so the
    dashboard can show which lure styles the org is most vulnerable to."""

    __tablename__ = "templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    html_body = db.Column(db.Text, nullable=False)
    sender_display = db.Column(db.String(150), default="IT Support")
    technique_id = db.Column(db.String(20), default="T1566.002")  # Spearphishing Link
    difficulty = db.Column(db.String(20), default="medium")  # easy/medium/hard
    lure_category = db.Column(db.String(50), default="credential_harvest")

    campaigns = db.relationship("Campaign", backref="template", lazy=True)


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("templates.id"), nullable=False)
    status = db.Column(db.String(20), default="draft")  # draft/sent/completed
    created_at = db.Column(db.DateTime, default=utcnow)
    launched_at = db.Column(db.DateTime, nullable=True)

    campaign_targets = db.relationship(
        "CampaignTarget", backref="campaign", lazy=True, cascade="all, delete-orphan"
    )


class CampaignTarget(db.Model):
    """Join row: one target enrolled in one campaign, with its own
    unguessable tracking token used across every tracking endpoint."""

    __tablename__ = "campaign_targets"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("targets.id"), nullable=False)
    tracking_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    sent_at = db.Column(db.DateTime, nullable=True)

    events = db.relationship(
        "Event", backref="campaign_target", lazy=True, cascade="all, delete-orphan"
    )

    def latest_stage(self):
        """Highest-severity event reached, used for the funnel / risk view."""
        order = ["sent", "opened", "clicked", "submitted"]
        reached = {e.event_type for e in self.events}
        stage = None
        for s in order:
            if s in reached:
                stage = s
        if "reported" in reached:
            return "reported"
        return stage or "not_sent"


class Event(db.Model):
    """One SOC-style log line per interaction. Mirrors real log analysis:
    timestamp, source, actor context, and a MITRE technique tag so the
    analytics layer can aggregate by tactic/technique instead of raw
    click counts alone."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    campaign_target_id = db.Column(db.Integer, db.ForeignKey("campaign_targets.id"), nullable=False)
    event_type = db.Column(db.String(30), nullable=False)
    # sent | opened | clicked | submitted | reported
    technique_id = db.Column(db.String(20))
    tactic = db.Column(db.String(60))
    timestamp = db.Column(db.DateTime, default=utcnow, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    severity = db.Column(db.String(10), default="info")  # info/low/medium/high