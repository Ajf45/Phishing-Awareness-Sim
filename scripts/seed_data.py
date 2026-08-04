"""
Seeds the database with demo departments, a synthetic target roster, and
the three sample lure templates shipped under app/email_templates/.

Run from the project root:
    python scripts/seed_data.py

Every roster entry here is fictional / example.com — replace with a real,
authorized internal roster before using this against an actual organization.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Department, Target, Template, db

EMAIL_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "email_templates")


def read_template(filename):
    with open(os.path.join(EMAIL_TEMPLATES_DIR, filename)) as f:
        return f.read()


DEPARTMENTS = ["Engineering", "Finance", "Human Resources", "Sales", "IT Operations"]

TARGETS = [
    ("Alice", "Nguyen", "alice.nguyen@example.com", "Engineering", "Software Engineer"),
    ("Ben", "Okafor", "ben.okafor@example.com", "Engineering", "DevOps Engineer"),
    ("Carla", "Martinez", "carla.martinez@example.com", "Finance", "Financial Analyst"),
    ("Daniel", "Kim", "daniel.kim@example.com", "Finance", "AP Specialist"),
    ("Erin", "Walsh", "erin.walsh@example.com", "Human Resources", "HR Generalist"),
    ("Farid", "Haidari", "farid.haidari@example.com", "Human Resources", "Recruiter"),
    ("Grace", "Liu", "grace.liu@example.com", "Sales", "Account Executive"),
    ("Hassan", "Ali", "hassan.ali@example.com", "Sales", "Sales Development Rep"),
    ("Ivy", "Thompson", "ivy.thompson@example.com", "IT Operations", "Systems Administrator"),
    ("Jack", "Romano", "jack.romano@example.com", "IT Operations", "Help Desk Technician"),
]

TEMPLATES = [
    {
        "name": "Account Verification / Password Reset",
        "subject": "Action required: verify your account within 24 hours",
        "html_body": read_template("password_reset.html"),
        "sender_display": "Account Security",
        "technique_id": "T1566.002",
        "difficulty": "easy",
        "lure_category": "credential_harvest",
    },
    {
        "name": "IT Helpdesk Mailbox Storage",
        "subject": "Your mailbox is almost full — action needed",
        "html_body": read_template("it_support.html"),
        "sender_display": "IT Service Desk",
        "technique_id": "T1566.002",
        "difficulty": "medium",
        "lure_category": "credential_harvest",
    },
    {
        "name": "Overdue Invoice Document",
        "subject": "Overdue: Invoice #INV-88213 requires review",
        "html_body": read_template("invoice_payment.html"),
        "sender_display": "Accounts Payable",
        "technique_id": "T1566.001",
        "difficulty": "hard",
        "lure_category": "document_lure",
    },
]


def run():
    app = create_app()
    with app.app_context():
        if Department.query.count() > 0:
            print("Data already seeded — skipping. Delete data/phishaware.db to reset.")
            return

        dept_objs = {name: Department(name=name) for name in DEPARTMENTS}
        db.session.add_all(dept_objs.values())
        db.session.flush()

        for first, last, email, dept, position in TARGETS:
            db.session.add(Target(
                first_name=first, last_name=last, email=email,
                position=position, department_id=dept_objs[dept].id,
            ))

        for t in TEMPLATES:
            db.session.add(Template(**t))

        db.session.commit()
        print(f"Seeded {len(DEPARTMENTS)} departments, {len(TARGETS)} targets, {len(TEMPLATES)} templates.")


if __name__ == "__main__":
    run()