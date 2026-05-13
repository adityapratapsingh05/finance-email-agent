"""
email_sender/smtp_sender.py
---------------------------
Sends real emails via Gmail SMTP with TLS/SSL.

Security:
    - Uses Gmail App Password (not your real Gmail password)
    - TLS/SSL enforced on port 465
    - Sender address loaded from environment variable only
    - Never hardcoded credentials

Setup:
    1. Enable 2-Step Verification on your Google account
    2. Go to Google Account > Security > App Passwords
    3. Generate a password for "Mail"
    4. Add to .env as GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logger import get_logger

log = get_logger(__name__)


def send_email(invoice, email_data):
    """
    Send a real email via Gmail SMTP.
    Raises exception on failure.
    """
    sender = os.getenv("GMAIL_USER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")
    recipient = str(invoice.get("contact_email", ""))
    subject = str(email_data.get("subject", ""))
    body = str(email_data.get("body", ""))

    if not sender or not password:
        raise ValueError("GMAIL_USER and GMAIL_APP_PASSWORD must be set in .env")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    # TLS/SSL enforced - email spoofing prevention
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    log.info("Email sent to " + recipient[:1] + "***@" + recipient.split("@")[1])
