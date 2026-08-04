"""
Authenticated analyst-facing routes: the "SOC dashboard" side of the
platform. Everything under here requires login via Flask-Login.
"""

import csv
import io

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request,
    url_for, Response,
)
from flask_login import login_required, login_user, logout_user, current_user

from ..models import AdminUser, Campaign, CampaignTarget, Department, Target, Template, db
from ..services.mailer import send_campaign
from ..services.scoring import campaign_summary
from ..services.mitre_mapper import TECHNIQUE_LIBRARY

bp = Blueprint("admin", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials", "error")

    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def dashboard():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    total_targets = Target.query.count()
    total_events = sum(len(ct.events) for c in campaigns for ct in c.campaign_targets)

    summaries = {}
    for c in campaigns:
        summaries[c.id] = campaign_summary(c.campaign_targets)

    org_risk = 0
    if summaries:
        org_risk = round(sum(s["human_risk_index"] for s in summaries.values()) / len(summaries))

    return render_template(
        "dashboard.html",
        campaigns=campaigns,
        summaries=summaries,
        total_targets=total_targets,
        total_events=total_events,
        org_risk=org_risk,
    )


@bp.route("/campaigns/new", methods=["GET", "POST"])
@login_required
def new_campaign():
    templates = Template.query.all()
    targets = Target.query.all()

    if request.method == "POST":
        name = request.form["name"]
        template_id = int(request.form["template_id"])
        target_ids = request.form.getlist("target_ids")

        campaign = Campaign(name=name, template_id=template_id, status="draft")
        db.session.add(campaign)
        db.session.flush()  # get campaign.id before commit

        for tid in target_ids:
            db.session.add(CampaignTarget(campaign_id=campaign.id, target_id=int(tid)))

        db.session.commit()
        flash(f"Campaign '{name}' created with {len(target_ids)} target(s).", "success")
        return redirect(url_for("admin.campaign_detail", campaign_id=campaign.id))

    return render_template("new_campaign.html", templates=templates, targets=targets)


@bp.route("/campaigns/<int:campaign_id>")
@login_required
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    summary = campaign_summary(campaign.campaign_targets)
    technique_library = TECHNIQUE_LIBRARY

    # Per-target rows for the table
    rows = []
    for ct in campaign.campaign_targets:
        from ..services.scoring import score_campaign_target, normalize
        raw = score_campaign_target(ct.events)
        rows.append({
            "target": ct.target,
            "stage": ct.latest_stage(),
            "score": normalize(raw),
            "event_count": len(ct.events),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)

    return render_template(
        "campaign_detail.html",
        campaign=campaign,
        summary=summary,
        rows=rows,
        technique_library=technique_library,
    )


@bp.route("/campaigns/<int:campaign_id>/launch", methods=["POST"])
@login_required
def launch_campaign(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    if campaign.status != "draft":
        flash("Campaign has already been launched.", "error")
        return redirect(url_for("admin.campaign_detail", campaign_id=campaign_id))

    results = send_campaign(campaign)
    campaign.status = "sent"
    campaign.launched_at = db.func.now()
    db.session.commit()

    if results["mode"] == "simulate":
        flash(
            f"Simulated send complete — {results['sent']} email(s) rendered to data/outbox/ "
            f"(no real mail sent).",
            "success",
        )
    else:
        flash(f"Sent {results['sent']} email(s) via AWS SES.", "success")

    return redirect(url_for("admin.campaign_detail", campaign_id=campaign_id))


@bp.route("/campaigns/<int:campaign_id>/report.csv")
@login_required
def campaign_report_csv(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["target_name", "email", "department", "stage_reached", "event_count", "risk_score"])

    from ..services.scoring import score_campaign_target, normalize

    for ct in campaign.campaign_targets:
        dept = ct.target.department.name if ct.target.department else ""
        writer.writerow([
            ct.target.full_name,
            ct.target.email,
            dept,
            ct.latest_stage(),
            len(ct.events),
            normalize(score_campaign_target(ct.events)),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_report.csv"},
    )


@bp.route("/roster")
@login_required
def roster():
    targets = Target.query.all()
    departments = Department.query.all()
    return render_template("roster.html", targets=targets, departments=departments)