# PhishAware — Phishing Awareness Simulation Platform

A self-hosted platform for running internal phishing-awareness campaigns:
send simulated phishing lures to an authorized target roster, track every
interaction (open / click / credential-submit / report), log it in a
SOC-style structured format, map it to **MITRE ATT&CK** techniques, and
turn it into per-target and per-department **behavioral risk scores** on
a live dashboard.

Built as a portfolio project demonstrating security-engineering + cloud
fundamentals: Flask app design, structured security event logging,
MITRE ATT&CK-aligned analytics, and an optional AWS SES/CloudWatch
integration path.

> ⚠️ **Ethics/safety note:** this tool is for *simulated, internal,
> authorized* awareness testing only. It never stores real credentials
> (the "submit" endpoint logs only the fact of a submission — see
> `app/routes/tracking.py`), and email sending defaults to a `simulate`
> mode that writes `.eml` files locally instead of contacting real
> inboxes. Only target people/addresses you have explicit authorization
> to test, e.g. your own org with security-leadership sign-off.

---

## What it demonstrates (mapped to the project description)

**"Designed and deployed a phishing-simulation platform that tracked user
interaction across multiple simulated campaigns, producing behavioral
analytics mapped to MITRE ATT&CK social-engineering techniques."**
→ `app/models.py` (Campaign/Target/Event schema), `app/services/mitre_mapper.py`
(technique mapping), `app/services/scoring.py` (susceptibility scoring),
`campaign_detail.html` dashboard (funnel + MITRE + department breakdown).

**"Built event logging and monitoring into the platform to capture and
analyze simulated phishing interactions in real time, mirroring SOC-style
log analysis and reporting."**
→ `app/services/logger.py` (structured JSON event log + optional
CloudWatch shipping), `app/routes/tracking.py` (every interaction logged
at the moment it happens), `app/routes/api.py` (real-time analytics
queried by the dashboard), CSV export for reporting.

---

## Folder structure

```
phishaware/
├── README.md
├── requirements.txt
├── config.py                    # all settings, env-driven
├── .env.example
├── run.py                       # entrypoint
├── app/
│   ├── __init__.py              # app factory, blueprint registration
│   ├── models.py                # SQLAlchemy models
│   ├── routes/
│   │   ├── admin.py             # authenticated dashboard: campaigns, launch, CSV export
│   │   ├── tracking.py          # public: pixel/click/landing/submit/report
│   │   └── api.py               # JSON analytics for dashboard charts
│   ├── services/
│   │   ├── mailer.py            # simulate (.eml) or AWS SES send
│   │   ├── mitre_mapper.py      # event -> MITRE ATT&CK technique
│   │   ├── logger.py            # SOC-style structured logging (+ CloudWatch)
│   │   └── scoring.py           # susceptibility scoring engine
│   ├── templates/                # Jinja2 UI (dashboard + simulated target-facing pages)
│   ├── static/css, static/js
│   └── email_templates/          # sample lure pretexts (password reset, IT helpdesk, invoice)
├── aws/
│   ├── iam-policy-phishaware.json
│   └── README.md                # optional SES/CloudWatch deployment notes
├── scripts/
│   ├── seed_data.py              # demo departments/roster/templates
│   └── generate_report.py        # CLI campaign summary
├── tests/
│   └── test_tracking.py          # pytest: full open→click→submit→report flow
├── data/                         # sqlite db + simulated outbox (gitignored)
└── logs/                         # events.jsonl + app.log (gitignored)
```

---

## Setup (macOS, VS Code)

```bash
cd phishaware
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # optional — defaults work as-is

python3 scripts/seed_data.py   # creates demo departments/roster/templates
python3 run.py                 # http://127.0.0.1:5000
```

Log in with the default demo credentials: **admin / ChangeMe123!**
(set `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env` to change).

## Walkthrough

1. **Dashboard** — org-wide risk index and campaign list.
2. **New Campaign** — pick a lure template (each tagged with a MITRE
   technique) and select targets from the seeded roster.
3. **Launch Simulation** — renders each target's personalized email
   (tracking pixel + click link + report link) to `data/outbox/*.eml`.
   Open one in Mail.app / any email client to see exactly what a
   recipient would see.
4. **Act as the target** — open the `.eml`'s tracking link in a browser
   to simulate a click, land on the fake login page, "submit"
   credentials (nothing is stored), or hit the report-phishing link
   instead. Each action is logged immediately.
5. **Campaign detail page** — watch the funnel, MITRE ATT&CK technique
   breakdown, timeline, and department risk scores update live; export
   a CSV report.
6. **`logs/events.jsonl`** — the raw SOC-style event stream — and
   `python3 scripts/generate_report.py 1` for a terminal summary.

## Tests

```bash
pip install pytest
pytest -q
```

## Design notes / what's intentionally simplified

- Email delivery defaults to `simulate` mode (writes `.eml` files, sends
  nothing) so the project is safe to run and demo without any mail
  infrastructure. A real AWS SES path exists behind `MAIL_MODE=ses` — see
  `aws/README.md`.
- Attachment-style lures (`T1566.001`) are represented conceptually via a
  link-based "open the invoice" flow rather than a real file attachment
  with macro/payload tracking — building genuine attachment telemetry
  (e.g. a tracked "document open" beacon) was out of scope for this pass
  but would be the natural next feature.
- The roster is synthetic (`@example.com`) seed data. In a real deployment
  targets would be sourced from an authorized internal directory export.
- No rate limiting / CAPTCHA on the tracking endpoints — acceptable for an
  internal-only demo tool, but worth adding (e.g. Flask-Limiter) before
  exposing this beyond a trusted network.