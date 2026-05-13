"""
main.py
-------
CLI entry point for the Finance Credit Follow-Up Email Agent.

Usage:
    python main.py --file data/sample_invoices.csv --dry-run
    python main.py --file data/sample_invoices.csv --live
"""

import argparse
import sys
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.csv_reader import load_invoices
from utils.logger import get_logger
from agent.tone_classifier import classify_tone
from agent.email_generator import generate_email
from agent.escalation import generate_escalation_report
from email_sender.dry_run_sender import save_dry_run
from email_sender.smtp_sender import send_email
from database.db_manager import log_action, log_escalation, initialize_db

log = get_logger("main")


def run_agent(file_path, dry_run=True):
    initialize_db()
    run_id = str(uuid.uuid4())[:8].upper()

    log.info("=" * 60)
    log.info("Agent started | run_id=" + run_id)
    log.info("Mode: " + ("DRY-RUN" if dry_run else "LIVE SEND"))
    log.info("=" * 60)

    invoices = load_invoices(file_path)
    log.info("Loaded " + str(len(invoices)) + " invoices from " + file_path)

    emails_done = 0
    escalated = 0
    skipped = 0
    errors = 0
    escalated_list = []

    for i, inv in enumerate(invoices, 1):
        days = int(inv.get("days_overdue", 0))
        followup_count = int(inv.get("followup_count", 0))

        # PDF requirement: use both days_overdue AND followup_count
        cl = classify_tone(days, followup_count)
        action = cl["action"]
        tone = cl["tone"]
        label = cl["label"]
        cta = cl["cta"]

        inv_no = str(inv["invoice_no"])
        name = str(inv["client_name"])
        amt = str(float(inv["amount_due"]))

        print("")
        print(str(i) + "/" + str(len(invoices)) + " | " + inv_no + " | " + name)
        print("   Days overdue   : " + str(days))
        print("   Follow-up count: " + str(followup_count))
        print("   Amount         : Rs." + amt)
        print("   Tone           : " + label)

        if action == "skip":
            print("   Result         : SKIPPED - not overdue")
            skipped += 1
            log_action(run_id, inv, "skipped", "skipped")

        elif action == "escalate":
            print("   Result         : ESCALATED to finance/legal team")
            escalated += 1
            escalated_list.append(inv)
            log_escalation(run_id, inv)

        else:
            print("   Result         : Generating email via OpenAI...")
            try:
                data = generate_email(inv, tone, cta=cta)
                if data is not None:
                    if dry_run:
                        path = save_dry_run(inv, data)
                        print("   Result         : SUCCESS (dry-run)")
                        print("   Subject        : " + str(data.get("subject", "")))
                        print("   Saved to       : " + os.path.basename(path))
                    else:
                        send_email(inv, data)
                        print("   Result         : EMAIL SENT LIVE")
                        print("   Subject        : " + str(data.get("subject", "")))
                    log_action(run_id, inv, "dry_run" if dry_run else "sent",
                               "success", tone_used=tone,
                               email_subject=str(data.get("subject", "")))
                    emails_done += 1
                else:
                    print("   Result         : FAILED - check API key in .env")
                    errors += 1
            except Exception as e:
                print("   Result         : ERROR - " + str(e))
                log.error("Error on " + inv_no + ": " + str(e))
                errors += 1

    if escalated_list:
        generate_escalation_report(escalated_list, run_id)

    print("")
    print("=" * 55)
    print("RUN COMPLETE | run_id=" + run_id)
    print("Emails done  : " + str(emails_done))
    print("Escalated    : " + str(escalated))
    print("Skipped      : " + str(skipped))
    print("Errors       : " + str(errors))
    print("=" * 55)

    if escalated_list:
        print("")
        print("ESCALATION LIST - Needs finance/legal action:")
        for inv in escalated_list:
            print("  * " + str(inv["invoice_no"]) + " | " +
                  str(inv["client_name"]) + " | Rs." +
                  str(float(inv["amount_due"])) + " | " +
                  str(inv["days_overdue"]) + " days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finance Credit Follow-Up Email Agent")
    parser.add_argument("--file", required=True, help="Path to CSV or Excel invoice file")
    parser.add_argument("--dry-run", action="store_true", help="Preview emails without sending")
    parser.add_argument("--live", action="store_true", help="Send real emails via SMTP")
    args = parser.parse_args()

    if not args.dry_run and not args.live:
        print("Please specify --dry-run or --live")
        sys.exit(1)

    run_agent(args.file, dry_run=not args.live)
