"""
agent/tone_classifier.py
------------------------
Maps days overdue AND followup_count to an escalation tone and action.

PDF Requirement:
    Stage is determined by max(days_overdue_tier, followup_count_tier)
    Whichever is higher wins.

Tiers:
    <= 0 days  : skip (not overdue)
    1-7 days   : warm_friendly     (Stage 1) CTA: Pay now link
    8-14 days  : polite_firm       (Stage 2) CTA: Confirm payment date
    15-21 days : formal_serious    (Stage 3) CTA: Respond within 48 hrs
    22-30 days : stern_urgent      (Stage 4) CTA: Pay immediately or call us
    30+ days   : escalate to finance/legal   NO email sent
"""


def _days_to_tier(days_overdue):
    if days_overdue <= 0:
        return 0
    elif days_overdue <= 7:
        return 1
    elif days_overdue <= 14:
        return 2
    elif days_overdue <= 21:
        return 3
    elif days_overdue <= 30:
        return 4
    else:
        return 5


def _followup_to_tier(followup_count):
    count = int(followup_count)
    if count <= 0:
        return 1
    elif count == 1:
        return 2
    elif count == 2:
        return 3
    elif count == 3:
        return 4
    else:
        return 5


TIER_MAP = {
    0: {"action": "skip",     "tone": None,            "label": "Not Overdue",               "cta": ""},
    1: {"action": "email",    "tone": "warm_friendly",  "label": "Warm and Friendly",         "cta": "Please use the payment link below or share your bank details to process payment now."},
    2: {"action": "email",    "tone": "polite_firm",    "label": "Polite but Firm",           "cta": "Please confirm your expected payment date by replying to this email within 24 hours."},
    3: {"action": "email",    "tone": "formal_serious", "label": "Formal and Serious",        "cta": "Please respond within 48 hours with payment confirmation or a resolution plan."},
    4: {"action": "email",    "tone": "stern_urgent",   "label": "Stern and Urgent",          "cta": "Pay immediately using the link below or call us within 24 hours to avoid escalation to our legal team."},
    5: {"action": "escalate", "tone": None,             "label": "Escalated to Finance/Legal","cta": "Assigned to finance manager for legal review. No further automated emails will be sent."},
}


def classify_tone(days_overdue, followup_count=0):
    """
    Returns dict with action, tone, label, cta, tier.
    Uses max(days_overdue_tier, followup_count_tier) as per PDF requirement.
    """
    days_tier = _days_to_tier(int(days_overdue))
    followup_tier = _followup_to_tier(int(followup_count))
    final_tier = max(days_tier, followup_tier)
    result = TIER_MAP[final_tier].copy()
    result["tier"] = final_tier
    return result
