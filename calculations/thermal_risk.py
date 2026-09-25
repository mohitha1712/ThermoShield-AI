"""
thermal_risk.py
----------------
Converts a numeric "Personalized Thermal Exposure Score" (0-100, produced
by exposure_model.py) into one of five documented risk categories, each
with a plain-language explanation and a recommended action.

The category boundaries are deliberately transparent and documented here
(NOT hidden "magic numbers"), so they can be reviewed/tuned by domain
experts before any real deployment. They are informed by the general
shape of NOAA Heat Index categories and ACGIH/IMD WBGT action-limit
bands, rescaled onto our 0-100 composite exposure score.
"""

from dataclasses import dataclass

RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "VERY HIGH", "EXTREME"]

# (label, min_score_inclusive, max_score_exclusive, color)
RISK_BANDS = [
    ("LOW", 0, 30, "#2E7D32"),
    ("MODERATE", 30, 50, "#F9A825"),
    ("HIGH", 50, 68, "#EF6C00"),
    ("VERY HIGH", 68, 85, "#D84315"),
    ("EXTREME", 85, 101, "#B71C1C"),
]

RISK_GUIDANCE = {
    "LOW": {
        "explanation": "Thermal exposure conditions are within normal, "
                        "manageable limits for most people.",
        "action": "Normal precautions. Maintain routine hydration.",
        "strategy": "No special scheduling changes are needed.",
    },
    "MODERATE": {
        "explanation": "Heat and exposure factors are starting to add up. "
                        "Sensitive individuals may begin to feel discomfort.",
        "action": "Increase hydration frequency and avoid unnecessarily "
                   "prolonging outdoor exposure.",
        "strategy": "Prefer cooler parts of the day for longer tasks where possible.",
    },
    "HIGH": {
        "explanation": "Combined environmental heat, activity load, and "
                        "exposure duration create a meaningful thermal "
                        "stress burden.",
        "action": "Take frequent cooling/rest breaks and avoid unnecessary "
                   "exposure during the peak-risk window.",
        "strategy": "Split long tasks with shaded/cooled rest breaks every 30-45 min.",
    },
    "VERY HIGH": {
        "explanation": "Conditions plus personal exposure context indicate "
                        "a substantial thermal stress load, especially for "
                        "higher-exertion or longer-duration activity.",
        "action": "Strongly reduce prolonged outdoor exposure and "
                   "prioritize cooling/rest periods.",
        "strategy": "Reschedule strenuous portions of work to the recommended "
                     "lower-exposure window; increase rest:work ratio.",
    },
    "EXTREME": {
        "explanation": "The combination of heat, humidity, activity "
                        "intensity, and exposure duration represents a "
                        "high thermal-stress scenario for this profile.",
        "action": "Treat as an urgent heat-risk situation. Avoid "
                   "unnecessary exposure during peak-risk periods; "
                   "consider escalation for occupational settings.",
        "strategy": "Postpone non-essential outdoor activity; if exposure is "
                     "unavoidable, minimize duration and maximize rest/cooling.",
    },
}


@dataclass
class RiskCategoryResult:
    score: float
    level: str
    color: str
    explanation: str
    action: str
    strategy: str


def categorize_risk(score: float) -> RiskCategoryResult:
    score = max(0.0, min(100.0, score))
    for label, lo, hi, color in RISK_BANDS:
        if lo <= score < hi:
            g = RISK_GUIDANCE[label]
            return RiskCategoryResult(
                score=round(score, 1),
                level=label,
                color=color,
                explanation=g["explanation"],
                action=g["action"],
                strategy=g["strategy"],
            )
    # Fallback (score == 100 edge case)
    g = RISK_GUIDANCE["EXTREME"]
    return RiskCategoryResult(
        score=round(score, 1), level="EXTREME", color="#B71C1C",
        explanation=g["explanation"], action=g["action"], strategy=g["strategy"],
    )
