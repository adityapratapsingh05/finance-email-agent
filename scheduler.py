"""
scheduler.py
------------
Runs the Finance Credit Follow-Up Email Agent automatically on a daily schedule.

Usage:
    python scheduler.py

The agent runs every day at 09:00 in dry-run mode by default.
Edit SCHEDULE_HOUR, SCHEDULE_MINUTE, and INVOICE_FILE below to configure.

Dependencies:
    pip install apscheduler==3.10.4
"""

import logging
import os
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_agent

# --- Configuration ---
INVOICE_FILE = "data/sample_invoices.csv"
SCHEDULE_HOUR = 9       # Run at 09:00
SCHEDULE_MINUTE = 0
DRY_RUN = True          # Set to False to send real emails

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
log = logging.getLogger("scheduler")

scheduler = BlockingScheduler()


@scheduler.scheduled_job(CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE))
def daily_run():
    """Triggered automatically every day at the configured time."""
    log.info("=" * 55)
    log.info("Scheduled daily run triggered")
    log.info("=" * 55)
    try:
        run_agent(INVOICE_FILE, dry_run=DRY_RUN)
        log.info("Scheduled run completed successfully")
    except Exception as e:
        log.error("Scheduled run failed: " + str(e))


if __name__ == "__main__":
    mode = "DRY-RUN" if DRY_RUN else "LIVE SEND"
    log.info(f"Scheduler started — agent runs daily at "
             f"{SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} in {mode} mode")
    log.info(f"Invoice file: {INVOICE_FILE}")
    log.info("Press Ctrl+C to stop the scheduler")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped")
