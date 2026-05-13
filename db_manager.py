"""
database/db_manager.py
----------------------
SQLite audit trail for all agent actions.

Security:
    - Email addresses are masked in logs (r***@domain.com) for data privacy
    - Parameterized queries prevent SQL injection
    - Database stored locally only

Schema:
    audit_log table stores every agent action with run_id, invoice details,
    tone used, action taken, status, and masked email.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create audit_log table if it does not exist."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id        TEXT,
            invoice_no    TEXT,
            client_name   TEXT,
            amount_due    REAL,
            days_overdue  INTEGER,
            tone_used     TEXT,
            action        TEXT,
            status        TEXT,
            email_sent_to TEXT,
            error_msg     TEXT,
            email_subject TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_action(run_id, invoice, action, status,
               tone_used=None, email_subject=None, error_msg=None):
    """Log any agent action to the audit trail."""
    try:
        email = str(invoice.get("contact_email", ""))
        # Data privacy: mask email in logs
        if "@" in email:
            masked = email[0] + "***@" + email.split("@")[1]
        else:
            masked = email

        conn = get_conn()
        conn.execute(
            """INSERT INTO audit_log
               (run_id, invoice_no, client_name, amount_due, days_overdue,
                tone_used, action, status, email_sent_to, error_msg, email_subject)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(run_id),
                str(invoice.get("invoice_no", "")),
                str(invoice.get("client_name", "")),
                float(invoice.get("amount_due", 0)),
                int(invoice.get("days_overdue", 0)),
                str(tone_used) if tone_used else None,
                str(action),
                str(status),
                masked,
                str(error_msg) if error_msg else None,
                str(email_subject) if email_subject else None
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB log error: " + str(e))


def log_escalation(run_id, invoice):
    """Shortcut to log an escalation action."""
    log_action(run_id, invoice, "escalated", "success")


def get_audit_log(limit=100):
    """Retrieve recent audit log entries."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
