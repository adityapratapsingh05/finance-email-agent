"""
email_sender/dry_run_sender.py
------------------------------
Saves generated emails as .txt files locally instead of sending them.
Use this mode to preview all emails before sending a single real one.

Output files are saved to: outputs/dry_run/
File naming: INVOICE-NO_YYYYMMDD_HHMMSS.txt
"""

import os
from datetime import datetime

DRY_RUN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "outputs", "dry_run"
)
os.makedirs(DRY_RUN_DIR, exist_ok=True)


def save_dry_run(invoice, email_data):
    """
    Save an email preview as a .txt file.
    Returns the full path of the saved file.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    inv_no = str(invoice.get("invoice_no", "INV")).replace("/", "-")
    path = os.path.join(DRY_RUN_DIR, inv_no + "_" + ts + ".txt")

    lines = [
        "=" * 60,
        "DRY-RUN EMAIL PREVIEW",
        "=" * 60,
        "To:           " + str(invoice.get("contact_email", "")),
        "Invoice No:   " + str(invoice.get("invoice_no", "")),
        "Client:       " + str(invoice.get("client_name", "")),
        "Amount Due:   Rs." + str(float(invoice.get("amount_due", 0))),
        "Days Overdue: " + str(invoice.get("days_overdue", 0)) + " days",
        "Tone:         " + str(email_data.get("tone_used", "")),
        "=" * 60,
        "SUBJECT: " + str(email_data.get("subject", "")),
        "=" * 60,
        "",
        str(email_data.get("body", "")),
        "",
        "=" * 60,
        "DRY-RUN - This email was NOT sent. Generated at " + ts,
        "=" * 60,
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path
