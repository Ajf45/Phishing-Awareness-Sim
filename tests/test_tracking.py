"""
Basic test suite covering the core simulation flow:
  create campaign -> "send" -> open -> click -> submit -> report
and verifies both the event log and the scoring engine behave correctly.

Run with:  pytest -q
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Campaign, CampaignTarget, Department, Target, Template, db
from app.services.scoring import campaign_summary, normalize, score_campaign_target


class TestConfig:
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_URL = "http://testserver"
    ORG_NAME = "TestCo"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "test-pass"
    LOG_DIR = tempfile.mkdtemp()
    EVENT_LOG_FILE = os.path.join(LOG_DIR, "events.jsonl")
    APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")
    MAIL_MODE = "simulate"
    OUTBOX_DIR = tempfile.mkdtemp()
    AWS_REGION = "us-east-1"
    SES_SENDER = "test@phishaware.local"
    SHIP_TO_CLOUDWATCH = False
    CLOUDWATCH_LOG_GROUP = "/phishaware/test"
    CLOUDWATCH_LOG_STREAM = "test"


@pytest.fixture
def app():
    app = create_app(config_object=TestConfig)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def campaign_target(app):
    with app.app_context():
        dept = Department(name="Engineering")
        db.session.add(dept)
        db.session.flush()

        target = Target(first_name="Test", last_name="User", email="test@example.com", department_id=dept.id)
        db.session.add(target)

        template = Template(
            name="Demo Lure", subject="Subject", html_body="<p>{{click_url}} {{report_url}}</p>",
            technique_id="T1566.002",
        )
        db.session.add(template)
        db.session.flush()

        campaign = Campaign(name="Demo Campaign", template_id=template.id)
        db.session.add(campaign)
        db.session.flush()

        ct = CampaignTarget(campaign_id=campaign.id, target_id=target.id)
        db.session.add(ct)
        db.session.commit()

        return ct.id


def test_pixel_logs_opened_event(client, app, campaign_target):
    with app.app_context():
        token = CampaignTarget.query.get(campaign_target).tracking_token

    resp = client.get(f"/t/{token}/pixel.png")
    assert resp.status_code == 200
    assert resp.content_type == "image/gif"

    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        assert any(e.event_type == "opened" for e in ct.events)


def test_click_then_submit_then_report_full_flow(client, app, campaign_target):
    with app.app_context():
        token = CampaignTarget.query.get(campaign_target).tracking_token

    r1 = client.get(f"/t/{token}/click")
    assert r1.status_code == 302

    r2 = client.get(f"/t/{token}/landing")
    assert r2.status_code == 200

    r3 = client.post(f"/t/{token}/submit", data={"username": "should_not_be_stored", "password": "ignored"})
    assert r3.status_code == 302

    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        event_types = {e.event_type for e in ct.events}
        assert {"clicked", "submitted"}.issubset(event_types)
        assert ct.latest_stage() == "submitted"

        # Confirm no submitted form values ever get persisted anywhere on the Event model.
        for e in ct.events:
            assert not hasattr(e, "username")
            assert not hasattr(e, "password")

    r4 = client.get(f"/t/{token}/report")
    assert r4.status_code == 200

    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        assert ct.latest_stage() == "reported"


def test_unknown_token_returns_404(client):
    resp = client.get("/t/not-a-real-token/pixel.png")
    assert resp.status_code == 404


def test_scoring_weights_submitted_higher_than_opened(app, campaign_target):
    with app.app_context():
        token = CampaignTarget.query.get(campaign_target).tracking_token

    client = app.test_client()
    client.get(f"/t/{token}/pixel.png")

    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        opened_only_score = normalize(score_campaign_target(ct.events))

    client.get(f"/t/{token}/click")
    client.post(f"/t/{token}/submit", data={})

    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        submitted_score = normalize(score_campaign_target(ct.events))

    assert submitted_score > opened_only_score


def test_campaign_summary_reports_correct_funnel(app, campaign_target):
    with app.app_context():
        ct = CampaignTarget.query.get(campaign_target)
        summary = campaign_summary([ct])
        assert summary["total_targets"] == 1
        assert summary["funnel"]["not_sent"] == 1