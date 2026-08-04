"""
PhishAware configuration.

All secrets/toggles are pulled from environment variables so the same
codebase can run purely locally (default, safe for a laptop demo) or be
pointed at real AWS services (SES for sending, CloudWatch-style JSON logs
for shipping to a log pipeline) for a more production-like deployment.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-before-any-real-use")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'phishaware.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Platform identity ---
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
    ORG_NAME = os.environ.get("ORG_NAME", "PhishAware Demo Org")

    # --- Admin bootstrap credentials (change via env in real use) ---
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

    # --- Logging ---
    LOG_DIR = os.environ.get("LOG_DIR", str(BASE_DIR / "logs"))
    EVENT_LOG_FILE = os.path.join(LOG_DIR, "events.jsonl")
    APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")

    # --- Email delivery mode ---
    # "simulate" (default): renders each target's email to an .eml file under
    #   outbox/ instead of sending anything — safe for a portfolio demo, no
    #   real mail is sent to anyone.
    # "ses": sends via AWS Simple Email Service using boto3. Only use this
    #   against addresses you are explicitly authorized to test, ideally
    #   inside an SES sandbox with verified recipients.
    MAIL_MODE = os.environ.get("MAIL_MODE", "simulate")
    OUTBOX_DIR = os.environ.get("OUTBOX_DIR", str(BASE_DIR / "data" / "outbox"))
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    SES_SENDER = os.environ.get("SES_SENDER", "security-awareness@phishaware.local")

    # --- CloudWatch-style structured logging toggle ---
    # When true, event logs are also shipped to a CloudWatch Logs group via
    # boto3 in addition to the local JSONL file. Requires AWS credentials
    # and CLOUDWATCH_LOG_GROUP to be set.
    SHIP_TO_CLOUDWATCH = os.environ.get("SHIP_TO_CLOUDWATCH", "false").lower() == "true"
    CLOUDWATCH_LOG_GROUP = os.environ.get("CLOUDWATCH_LOG_GROUP", "/phishaware/events")
    CLOUDWATCH_LOG_STREAM = os.environ.get("CLOUDWATCH_LOG_STREAM", "campaign-events")