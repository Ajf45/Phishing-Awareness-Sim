"""
SOC-style event logging.

Every simulated interaction (sent/opened/clicked/submitted/reported) is
written as a single structured JSON line to logs/events.jsonl — the same
shape you'd feed into Splunk, an ELK stack, or CloudWatch Logs Insights
for querying. A rotating handler also keeps application-level logs
(startup, errors) separate from the event stream, mirroring how SOCs keep
security event logs distinct from app/infra logs.

If SHIP_TO_CLOUDWATCH is enabled, each event is additionally pushed to a
CloudWatch Logs group via boto3 — this is what gives the project a genuine
"cloud security engineer" flavor beyond just writing to a local file, and
demonstrates the log-shipping pattern used in real detection pipelines.
"""

import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler

_cw_client = None
_cw_sequence_token = None


def setup_logging(app):
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)

    app_logger = logging.getLogger("phishaware.app")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = RotatingFileHandler(app.config["APP_LOG_FILE"], maxBytes=1_000_000, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
        app_logger.addHandler(logging.StreamHandler())

    # Ensure the event log file exists
    open(app.config["EVENT_LOG_FILE"], "a").close()

    if app.config.get("SHIP_TO_CLOUDWATCH"):
        _init_cloudwatch(app)

    return app_logger


def _init_cloudwatch(app):
    global _cw_client
    try:
        import boto3

        _cw_client = boto3.client("logs", region_name=app.config["AWS_REGION"])
        group = app.config["CLOUDWATCH_LOG_GROUP"]
        stream = app.config["CLOUDWATCH_LOG_STREAM"]
        try:
            _cw_client.create_log_group(logGroupName=group)
        except _cw_client.exceptions.ResourceAlreadyExistsException:
            pass
        try:
            _cw_client.create_log_stream(logGroupName=group, logStreamName=stream)
        except _cw_client.exceptions.ResourceAlreadyExistsException:
            pass
    except Exception as exc:  # pragma: no cover - only hit without AWS creds
        logging.getLogger("phishaware.app").warning("CloudWatch init failed, falling back to local logs only: %s", exc)
        _cw_client = None


def log_event(app, event_record: dict):
    """Write one structured event to the local JSONL file and, if enabled,
    ship it to CloudWatch Logs. `event_record` should already contain all
    fields you want persisted (timestamp, event_type, technique_id, etc.)."""
    line = json.dumps(event_record, default=str)

    with open(app.config["EVENT_LOG_FILE"], "a") as f:
        f.write(line + "\n")

    logging.getLogger("phishaware.app").info(
        "event=%s campaign_target_id=%s technique=%s",
        event_record.get("event_type"),
        event_record.get("campaign_target_id"),
        event_record.get("technique_id"),
    )

    if app.config.get("SHIP_TO_CLOUDWATCH") and _cw_client is not None:
        _ship_to_cloudwatch(app, line)


def _ship_to_cloudwatch(app, message: str):
    global _cw_sequence_token
    try:
        kwargs = {
            "logGroupName": app.config["CLOUDWATCH_LOG_GROUP"],
            "logStreamName": app.config["CLOUDWATCH_LOG_STREAM"],
            "logEvents": [{"timestamp": int(time.time() * 1000), "message": message}],
        }
        if _cw_sequence_token:
            kwargs["sequenceToken"] = _cw_sequence_token
        resp = _cw_client.put_log_events(**kwargs)
        _cw_sequence_token = resp.get("nextSequenceToken")
    except Exception as exc:  # pragma: no cover
        logging.getLogger("phishaware.app").warning("CloudWatch put_log_events failed: %s", exc)