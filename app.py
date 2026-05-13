"""
app.py
------
Streamlit web dashboard for the Finance Credit Follow-Up Email Agent.

Run with:
    streamlit run app.py
Then open: http://localhost:8501
"""

import streamlit as st
import pandas as pd
import sys
import os
import uuid
from datetime import date

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.csv_reader import load_invoices
from agent.tone_classifier import classify_tone
from agent.email_generator import generate_email
from agent.escalation import generate_escalation_report
from email_sender.dry_run_sender import save_dry_run
from database.db_manager import log_action, log_escalation, get_audit_log, initialize_db

initialize_db()

st.set_page_config(
    page_title="Finance Email Agent",
    page_icon="📧",
    layout="wide"
)

st.title("📧 Finance Credit Follow-Up Email Agent")
st.markdown("AI-powered invoice recovery system using LangChain + OpenAI GPT-4o-mini")

# Sidebar
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password",
                             value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    dry_run = st.checkbox("Dry-Run Mode (no real emails)", value=True)
    st.markdown("---")
    st.markdown("**Escalation Tiers**")
    st.markdown("🟢 1-7 days: Warm & Friendly")
    st.markdown("🔵 8-14 days: Polite but Firm")
    st.markdown("🟡 15-21 days: Formal & Serious")
    st.markdown("🔴 22-30 days: Stern & Urgent")
    st.markdown("⬛ 30+ days: Escalated")

# File upload
st.header("Step 1 — Upload Invoice File")
uploaded = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded:
    tmp_path = "/tmp/" + uploaded.name
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    try:
        invoices = load_invoices(tmp_path)
        df = pd.DataFrame(invoices)

        st.header("Step 2 — Invoice Preview")
        st.metric("Total Invoices", len(invoices))

        col1, col2, col3, col4 = st.columns(4)
        overdue = [i for i in invoices if i["days_overdue"] > 0]
        escalate = [i for i in invoices if i["days_overdue"] > 30]
        col1.metric("Overdue", len(overdue))
        col2.metric("To Email", len([i for i in invoices if 0 < i["days_overdue"] <= 30]))
        col3.metric("To Escalate", len(escalate))
        col4.metric("Not Due", len([i for i in invoices if i["days_overdue"] <= 0]))

        def color_row(row):
            d = row.get("days_overdue", 0)
            if d <= 0:
                return ["background-color: #f0f0f0"] * len(row)
            elif d <= 7:
                return ["background-color: #d1fae5"] * len(row)
            elif d <= 14:
                return ["background-color: #dbeafe"] * len(row)
            elif d <= 21:
                return ["background-color: #fef9c3"] * len(row)
            elif d <= 30:
                return ["background-color: #fee2e2"] * len(row)
            else:
                return ["background-color: #1f2937; color: white"] * len(row)

        display_cols = ["invoice_no", "client_name", "amount_due", "due_date",
                        "days_overdue", "contact_email", "followup_count"]
        st.dataframe(df[display_cols].style.apply(color_row, axis=1), use_container_width=True)

        st.header("Step 3 — Run Agent")
        if st.button("Run Agent", type="primary"):
            if not os.getenv("OPENAI_API_KEY"):
                st.error("Please enter your OpenAI API key in the sidebar!")
            else:
                run_id = str(uuid.uuid4())[:8].upper()
                st.info("Run ID: " + run_id)
                progress = st.progress(0)
                results = []
                escalated_list = []

                for i, inv in enumerate(invoices):
                    days = int(inv.get("days_overdue", 0))
                    cl = classify_tone(days)
                    action = cl["action"]
                    tone = cl["tone"]
                    label = cl["label"]

                    if action == "skip":
                        results.append({
                            "invoice_no": inv["invoice_no"],
                            "client_name": inv["client_name"],
                            "action": "Skipped",
                            "tone": "-",
                            "status": "Not overdue",
                            "subject": "-"
                        })
                        log_action(run_id, inv, "skipped", "skipped")

                    elif action == "escalate":
                        results.append({
                            "invoice_no": inv["invoice_no"],
                            "client_name": inv["client_name"],
                            "action": "Escalated",
                            "tone": "Finance/Legal",
                            "status": "Routed to team",
                            "subject": "-"
                        })
                        escalated_list.append(inv)
                        log_escalation(run_id, inv)

                    else:
                        try:
                            data = generate_email(inv, tone)
                            if data:
                                path = save_dry_run(inv, data)
                                subj = str(data.get("subject", ""))
                                log_action(run_id, inv, "dry_run", "success",
                                           tone_used=tone, email_subject=subj)
                                results.append({
                                    "invoice_no": inv["invoice_no"],
                                    "client_name": inv["client_name"],
                                    "action": "Email Generated",
                                    "tone": label,
                                    "status": "Success",
                                    "subject": subj
                                })
                            else:
                                results.append({
                                    "invoice_no": inv["invoice_no"],
                                    "client_name": inv["client_name"],
                                    "action": "Failed",
                                    "tone": label,
                                    "status": "API Error",
                                    "subject": "-"
                                })
                        except Exception as e:
                            results.append({
                                "invoice_no": inv["invoice_no"],
                                "client_name": inv["client_name"],
                                "action": "Error",
                                "tone": label,
                                "status": str(e)[:50],
                                "subject": "-"
                            })

                    progress.progress((i + 1) / len(invoices))

                if escalated_list:
                    generate_escalation_report(escalated_list, run_id)

                st.success("Agent run complete!")
                st.header("Results")
                st.dataframe(pd.DataFrame(results), use_container_width=True)

                # Show generated emails
                dry_dir = os.path.join(os.path.dirname(__file__), "outputs/dry_run")
                if os.path.exists(dry_dir):
                    email_files = sorted(os.listdir(dry_dir))
                    if email_files:
                        st.header("Generated Email Previews")
                        for fname in email_files[-len(invoices):]:
                            with st.expander(fname):
                                with open(os.path.join(dry_dir, fname)) as ef:
                                    st.text(ef.read())

    except Exception as e:
        st.error("Error loading file: " + str(e))

# Audit log
st.header("Audit Log")
logs = get_audit_log(50)
if logs:
    st.dataframe(pd.DataFrame(logs), use_container_width=True)
else:
    st.info("No audit log entries yet. Run the agent to see logs here.")
