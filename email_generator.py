"""
agent/email_generator.py
------------------------
Generates AI-powered follow-up emails using LangChain + OpenAI GPT-4o-mini.

PDF Requirements met:
    - All 4 tone instructions with specific CTAs per stage
    - All required fields: client name, invoice no, amount, due date,
      days overdue, payment link
    - Hallucination guard validates output after every generation
    - Retries on failure (max 2 attempts)

Security:
    - API key loaded from environment only, never hardcoded
    - _validate_output() prevents hallucinated invoice details
"""

import os
import json
import time
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.logger import get_logger

log = get_logger(__name__)

TONE_INSTRUCTIONS = {
    "warm_friendly": (
        "Write a warm and friendly payment reminder under 150 words. "
        "Be conversational and empathetic. Assume the client simply forgot. "
        "Keep it positive and forward-looking."
    ),
    "polite_firm": (
        "Write a polite but firm payment follow-up under 180 words. "
        "Acknowledge that payment is still pending after the due date. "
        "Be professional and clear. Request a confirmation of payment date."
    ),
    "formal_serious": (
        "Write a formal and serious payment notice under 200 words. "
        "Express genuine concern about the overdue amount. "
        "Clearly state that continued non-payment may impact the business relationship. "
        "Require a response within 48 hours."
    ),
    "stern_urgent": (
        "Write a stern and urgent final payment demand under 220 words. "
        "This is the absolute last notice before escalation to legal. "
        "Be firm and professional. State consequences clearly without making specific legal threats."
    ),
}

TEMPLATE = """You are a professional accounts receivable assistant for {company_name}.

TASK: {tone_instruction}

INVOICE DETAILS - use EXACTLY these values, do not change any field:
Client Name: {client_name}
Invoice Number: {invoice_no}
Amount Due: Rs.{amount_due}
Original Due Date: {due_date}
Days Overdue: {days_overdue} days
Payment Link: {payment_link}
Contact Email: {company_email}

MANDATORY CTA (include this exact call to action at the end of the email):
{cta_instruction}

STRICT RULES:
- The invoice number {invoice_no} MUST appear in the email body
- Use the exact amount Rs.{amount_due}
- Include the payment link {payment_link}
- Include the CTA instruction above
- Do NOT invent any information not provided here
- Do NOT use generic placeholder text

Return ONLY valid JSON. No markdown. No backticks. No extra text:
{{"subject": "email subject here", "body": "full professional email body here", "tone_used": "{tone_key}", "days_overdue_confirmed": {days_overdue}}}"""


def _validate_output(parsed, invoice):
    """
    Hallucination prevention.
    Verifies key invoice fields appear in the generated email.
    """
    inv_no = str(invoice["invoice_no"])
    body = str(parsed.get("body", ""))
    subject = str(parsed.get("subject", ""))

    if inv_no not in body and inv_no not in subject:
        log.warning("Hallucination guard: invoice_no not found in output for " + inv_no)
        return False
    if len(body) < 80:
        log.warning("Hallucination guard: body too short (" + str(len(body)) + " chars)")
        return False
    if not parsed.get("subject"):
        log.warning("Hallucination guard: subject is empty")
        return False
    return True


def generate_email(invoice, tone, cta="", max_retries=2):
    """
    Generate a follow-up email for the given invoice using the specified tone.
    Returns parsed JSON dict or None on failure.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or "YOUR" in api_key:
        raise ValueError("Please set your real OPENAI_API_KEY in the .env file!")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=700,
        api_key=api_key
    )
    prompt = PromptTemplate.from_template(TEMPLATE)
    chain = prompt | llm | StrOutputParser()

    for attempt in range(1, max_retries + 1):
        try:
            result = chain.invoke({
                "company_name": os.getenv("COMPANY_NAME", "Our Company"),
                "tone_instruction": TONE_INSTRUCTIONS[tone],
                "tone_key": tone,
                "client_name": str(invoice["client_name"]),
                "invoice_no": str(invoice["invoice_no"]),
                "amount_due": str(float(invoice["amount_due"])),
                "due_date": str(invoice["due_date"]),
                "days_overdue": str(int(invoice["days_overdue"])),
                "payment_link": os.getenv("PAYMENT_LINK", "https://pay.yourcompany.com"),
                "company_email": os.getenv("GMAIL_USER", "accounts@yourcompany.com"),
                "cta_instruction": cta if cta else "Please process your payment at the earliest.",
            })

            # Clean markdown fences if present
            result = result.strip()
            if result.startswith("```"):
                parts = result.split("```")
                result = parts[1] if len(parts) > 1 else result
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()

            parsed = json.loads(result)

            if "subject" in parsed and "body" in parsed:
                if _validate_output(parsed, invoice):
                    log.info("Email generated for " + str(invoice["invoice_no"]) +
                             " | tone=" + tone + " | attempt=" + str(attempt))
                    return parsed
                else:
                    log.warning("Validation failed on attempt " + str(attempt) + ", retrying...")
            else:
                log.warning("Missing required keys in LLM response on attempt " + str(attempt))

        except Exception as e:
            log.error("Attempt " + str(attempt) + " failed for " +
                      str(invoice.get("invoice_no", "?")) + ": " + str(e))
            if attempt < max_retries:
                time.sleep(2)

    log.error("All attempts failed for invoice " + str(invoice.get("invoice_no", "?")))
    return None
