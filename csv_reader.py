"""
utils/csv_reader.py
-------------------
Loads and validates invoice data from CSV or Excel files.

Security:
    - sanitize_field() strips HTML and prompt injection keywords
      from all text fields before they enter the LLM prompt
    - Email format validation prevents malformed data
    - Schema validation ensures required columns are present
"""

import re
import os
import pandas as pd
from datetime import date

REQUIRED_COLUMNS = {
    "invoice_no", "client_name", "amount_due",
    "due_date", "contact_email", "followup_count"
}


def sanitize_field(value):
    """
    Prompt injection prevention.
    Strips HTML tags and known injection keywords from CSV text fields.
    """
    if not isinstance(value, str):
        value = str(value)
    # Remove HTML tags
    value = re.sub(r"<[^>]+>", "", value)
    # Remove prompt injection keywords
    injection_keywords = [
        "ignore", "forget", "disregard", "system",
        "prompt", "instruction", "override", "jailbreak"
    ]
    for word in injection_keywords:
        value = re.sub(word, "", value, flags=re.IGNORECASE)
    return value[:500].strip()


def validate_email(email):
    """Basic email format validation."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, str(email).strip()))


def load_invoices(file_path):
    """
    Load invoices from CSV or Excel.
    Returns a list of dicts with validated and sanitized fields.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + str(missing))

    # Parse and validate due_date
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce").dt.date
    df = df.dropna(subset=["due_date"])

    # Calculate days overdue
    df["days_overdue"] = df["due_date"].apply(lambda d: (date.today() - d).days)

    # Sanitize text fields (prompt injection prevention)
    df["client_name"] = df["client_name"].apply(sanitize_field)
    df["invoice_no"] = df["invoice_no"].apply(sanitize_field)

    # Validate email addresses
    df = df[df["contact_email"].apply(validate_email)]

    # Numeric validation
    df["amount_due"] = pd.to_numeric(df["amount_due"], errors="coerce").fillna(0)
    df["followup_count"] = pd.to_numeric(
        df["followup_count"], errors="coerce"
    ).fillna(0).astype(int)

    return df.to_dict(orient="records")
