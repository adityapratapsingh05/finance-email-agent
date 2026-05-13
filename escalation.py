"""
agent/escalation.py
-------------------
Handles invoices overdue more than 30 days.
No email is sent to the client.
Instead a CSV report is generated and saved to outputs/escalations/.
"""

import os
import csv
from datetime import datetime
from utils.logger import get_logger

log = get_logger(__name__)

ESCALATION_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "escalations")


def generate_escalation_report(escalated_invoices, run_id):
    """
    Saves a CSV report of all escalated invoices.
    This report is intended for the finance/legal team.
    """
    os.makedirs(ESCALATION_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = "escalation_report_" + run_id + "_" + ts + ".csv"
    path = os.path.join(ESCALATION_DIR, filename)

    fields = ["invoice_no", "client_name", "amount_due", "due_date",
              "days_overdue", "contact_email", "followup_count"]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for inv in escalated_invoices:
            writer.writerow({k: inv.get(k, "") for k in fields})

    log.warning("ESCALATION REPORT saved: " + filename)
    log.warning(str(len(escalated_invoices)) + " invoice(s) escalated to finance/legal team")
    print("")
    print("ESCALATION REPORT saved: " + path)
    print("Send this file to your finance/legal team for follow-up action.")
    return path
