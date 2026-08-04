"""
Maps simulation event types (and template lure categories) to MITRE
ATT&CK (Enterprise) techniques/tactics so the platform's analytics speak
the same language a SOC or purple team would use, instead of just raw
"click rate" numbers.

Reference techniques used (Enterprise matrix, Initial Access / Execution /
Credential Access tactics):
  T1566      Phishing (parent)
  T1566.001  Phishing: Spearphishing Attachment
  T1566.002  Phishing: Spearphishing Link
  T1598      Phishing for Information (recon-oriented)
  T1598.002  Phishing for Information: Spearphishing Attachment
  T1598.003  Phishing for Information: Spearphishing Link
  T1204.001  User Execution: Malicious Link
  T1204.002  User Execution: Malicious File
  M1017      Mitigation: User Training (used for "reported" — the desired
             defensive outcome, not an attacker technique)
"""

TECHNIQUE_LIBRARY = {
    "T1566": {"name": "Phishing", "tactic": "Initial Access"},
    "T1566.001": {"name": "Spearphishing Attachment", "tactic": "Initial Access"},
    "T1566.002": {"name": "Spearphishing Link", "tactic": "Initial Access"},
    "T1598": {"name": "Phishing for Information", "tactic": "Reconnaissance"},
    "T1598.002": {"name": "Spearphishing Attachment (Recon)", "tactic": "Reconnaissance"},
    "T1598.003": {"name": "Spearphishing Link (Recon)", "tactic": "Reconnaissance"},
    "T1204.001": {"name": "User Execution: Malicious Link", "tactic": "Execution"},
    "T1204.002": {"name": "User Execution: Malicious File", "tactic": "Execution"},
    "T1078": {"name": "Valid Accounts (credential exposure risk)", "tactic": "Defense Evasion / Persistence"},
    "M1017": {"name": "User Training (positive control)", "tactic": "Mitigation"},
}

# Which technique an *event* represents, keyed by event_type. The template's
# own technique_id (its lure style) is used for "sent"/"opened" since those
# stages represent the attacker's initial-access attempt; later stages map
# to the more specific execution/credential-access technique.
EVENT_TECHNIQUE_MAP = {
    "sent": None,  # inherits template.technique_id
    "opened": "T1598.003",
    "clicked": "T1204.001",
    "submitted": "T1078",
    "reported": "M1017",
}


def resolve_event_technique(event_type: str, template_technique_id: str) -> dict:
    """Return {technique_id, name, tactic} for a given event."""
    mapped = EVENT_TECHNIQUE_MAP.get(event_type)
    technique_id = mapped or template_technique_id or "T1566"
    meta = TECHNIQUE_LIBRARY.get(technique_id, {"name": technique_id, "tactic": "Unknown"})
    return {"technique_id": technique_id, "name": meta["name"], "tactic": meta["tactic"]}


def severity_for_event(event_type: str) -> str:
    return {
        "sent": "info",
        "opened": "low",
        "clicked": "medium",
        "submitted": "high",
        "reported": "info",
    }.get(event_type, "info")