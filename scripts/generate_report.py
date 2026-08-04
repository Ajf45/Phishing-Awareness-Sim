"""
CLI utility to print a SOC-style summary report for a campaign straight to
the terminal — handy for a quick check without opening the dashboard, or
for piping into another tool.

Usage:
    python scripts/generate_report.py <campaign_id>
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Campaign
from app.services.scoring import campaign_summary


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_report.py <campaign_id>")
        sys.exit(1)

    campaign_id = int(sys.argv[1])
    app = create_app()

    with app.app_context():
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            print(f"No campaign with id {campaign_id}")
            sys.exit(1)

        summary = campaign_summary(campaign.campaign_targets)

        print(f"\n=== Campaign Report: {campaign.name} ===")
        print(f"Status: {campaign.status}")
        print(f"Targets enrolled: {summary['total_targets']}")
        print(f"Reported suspicious: {summary['reported_count']}")
        print(f"Human Risk Index: {summary['human_risk_index']} ({summary['risk_band']})")

        print("\n-- Funnel --")
        for stage, count in summary["funnel"].items():
            print(f"  {stage:12s}: {count}")

        print("\n-- Department Breakdown --")
        for d in summary["department_breakdown"]:
            print(f"  {d['department']:20s} avg_score={d['avg_score']:3d}  targets={d['target_count']}")
        print()


if __name__ == "__main__":
    main()