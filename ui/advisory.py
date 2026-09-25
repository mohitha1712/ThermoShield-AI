"""
advisory.py
-----------
Generates specific, occupation-aware advisory text (Section 12) and
provides a small English/Tamil phrase table for key messages (Section 30).
"""

OCCUPATION_ADVISORY = {
    "Construction Worker": "Heavy outdoor work is associated with elevated thermal exposure during the peak-risk window. Consider scheduling strenuous tasks earlier in the day, increasing rest/cooling breaks, and maintaining hydration.",
    "Agricultural Worker": "Consider moving physically demanding field work toward cooler hours and taking regular shaded recovery periods, especially during peak sun.",
    "Delivery Worker": "Frequent sun exposure during rounds adds up over the day. Plan heavier delivery loads for cooler windows and carry water; take brief shade breaks where possible.",
    "Traffic Police": "Prolonged standing in direct sun raises cumulative heat load. Rotate duty positions where possible and use shaded posts/cooling breaks during peak hours.",
    "Outdoor Worker": "Continuous outdoor exposure elevates heat load significantly. Take mandatory rest breaks in shaded areas, rotate tasks, wear protective hats, and hydrate frequently.",
    "Student": "Outdoor sports/activity should be reduced during the peak-risk period; prefer early morning or evening for physical activity.",
    "Elderly Person": "Elevated physiological sensitivity to heat means even shorter exposures warrant caution. Stay indoors or in cooled spaces during peak hours, and hydrate regularly.",
    "Office Worker": "Indoor exposure is generally lower, but poorly ventilated or non-cooled environments may still create heat stress -- ensure adequate airflow/cooling.",
    "General Public": "Limit non-essential outdoor activity during the peak-risk window and stay hydrated throughout the day.",
    "Custom Profile": "Adjust exposure timing and intensity based on the risk breakdown above; prioritize hydration and shaded rest during higher-risk hours.",
}

TRANSLATIONS = {
    "peak_risk_message": {
        "English": "Peak thermal risk expected between {start} and {end}.",
        "Tamil": "{start} முதல் {end} வரை வெப்ப அழுத்த அபாயம் அதிகமாக இருக்கும்.",
    },
    "hydration": {
        "English": "Drink water regularly, even if you do not feel thirsty.",
        "Tamil": "தாகம் இல்லாவிட்டாலும் தொடர்ந்து தண்ணீர் குடிக்கவும்.",
    },
    "reduce_exposure": {
        "English": "Reduce prolonged outdoor exposure during peak hours.",
        "Tamil": "உச்ச நேரங்களில் வெளிப்புற வேலையைக் குறைக்கவும்.",
    },
}


def get_advisory(occupation: str) -> str:
    return OCCUPATION_ADVISORY.get(occupation, OCCUPATION_ADVISORY["General Public"])


def translate(key: str, lang: str, **kwargs) -> str:
    template = TRANSLATIONS.get(key, {}).get(lang, TRANSLATIONS.get(key, {}).get("English", ""))
    return template.format(**kwargs)


def action_center_items(level: str, occupation: str) -> list:
    items = ["Hydration: drink water regularly, don't wait until thirsty."]
    if level in ("MODERATE", "HIGH", "VERY HIGH", "EXTREME"):
        items.append("Cooling/rest: take shaded or cooled breaks at regular intervals.")
    if level in ("HIGH", "VERY HIGH", "EXTREME"):
        items.append("Exposure reduction: shorten continuous time in direct sun/heat.")
        items.append("Schedule adjustment: shift strenuous tasks to the recommended lower-exposure window.")
    if level in ("VERY HIGH", "EXTREME") and occupation in (
        "Construction Worker", "Agricultural Worker", "Delivery Worker", "Traffic Police"
    ):
        items.append("Protective clothing: light-colored, breathable clothing and head covering.")
        items.append("Supervisor/institution notification suggested for this occupational setting.")
    if level == "EXTREME":
        items.append("Escalation recommended: consider activating a heat-safety protocol for exposed groups.")
    return items
