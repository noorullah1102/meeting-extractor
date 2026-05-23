"""
Notifier
Sends meeting action item emails via Resend API.
"""

import os

import resend


def send_email(to: list[str], subject: str, html_body: str) -> str:
    """Send an HTML email via Resend. Returns the email ID."""
    resend.api_key = os.environ.get("RESEND_API_KEY")
    email_from = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")

    email = resend.Emails.send({
        "from": email_from,
        "to": to,
        "subject": subject,
        "html": html_body,
    })
    return email["id"]
