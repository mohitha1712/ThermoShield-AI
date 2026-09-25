"""
exposure_model.py
------------------
"Thermal Exposure Risk Engine"

Combines environmental heat load with HUMAN exposure context
(occupation, activity intensity, exposure duration, time of day) into a
single transparent 0-100 "Personalized Thermal Exposure Score".

This is explicitly a DETERMINISTIC, DOCUMENTED SCORING MODEL -- not a
clinically validated medical instrument. All weights are declared below
so they can be inspected, defended in front of judges, and tuned later
by domain experts.

Composite formula
------------------
Score = clamp( Environmental Heat Component
             + Activity Load Component
             + Exposure Duration Component
             + Occupation Exposure Component
             + Time-of-Day Adjustment , 0, 100 )

Each component is capped so no single factor can alone push the score
into EXTREME -- risk should emerge from the COMBINATION of factors,
which is the project's central "same weather, different risk" thesis.
"""

from dataclasses import dataclass
from calculations.heat_index import calculate_heat_index
from calculations.wbgt import calculate_wbgt_estimate

# ---------------------------------------------------------------------
# 1. Environmental Heat Component (0-45 points)
#    Derived from Heat Index (deg C), scaled linearly between 27C (0 pts)
#    and 48C (45 pts). 27C is the lower bound where the Heat Index
#    regression becomes meaningful; 48C is an extreme heat-index value.
# ---------------------------------------------------------------------
ENV_MIN_C, ENV_MAX_C, ENV_MAX_POINTS = 27.0, 48.0, 45.0

# ---------------------------------------------------------------------
# 2. Activity Load Component (0-20 points)
#    Based on metabolic heat production categories used in occupational
#    heat-stress guidance (ACGIH-style qualitative bands).
# ---------------------------------------------------------------------
ACTIVITY_WEIGHTS = {
    "Resting": 0,
    "Light": 6,
    "Moderate": 13,
    "Heavy": 20,
}

# ---------------------------------------------------------------------
# 3. Exposure Duration Component (0-15 points)
#    Longer continuous exposure raises cumulative thermal strain.
# ---------------------------------------------------------------------
DURATION_WEIGHTS = {
    "30 minutes": 3,
    "1 hour": 6,
    "2 hours": 10,
    "3 hours": 13,
    "4+ hours": 15,
}

# ---------------------------------------------------------------------
# 4. Occupation Exposure Component (0-15 points)
#    Reflects typical outdoor/sun exposure and workload pattern of each
#    profile. General Public / Custom default to a mid value.
# ---------------------------------------------------------------------
OCCUPATION_WEIGHTS = {
    "Construction Worker": 15,
    "Agricultural Worker": 14,
    "Outdoor Worker": 14,
    "Delivery Worker": 12,
    "Traffic Police": 13,
    "Student": 8,
    "Elderly Person": 11,   # lower workload but higher physiological vulnerability (see note)
    "Office Worker": 3,
    "General Public": 7,
    "Custom Profile": 9,
}

# Vulnerability multiplier: some groups face elevated heat-illness risk
# at the SAME exposure score due to physiological factors (documented in
# public-health heat guidance), independent of workload. Applied as a
# small additive bump, capped at 5 points, never used alone to justify
# a risk level.
VULNERABILITY_BUMP = {
    "Elderly Person": 5,
    "Student": 2,
}

# ---------------------------------------------------------------------
# 5. Time-of-Day Adjustment (-5 to +5 points)
#    Peak solar loading (11:00-16:00) adds load; early morning/late
#    evening subtracts.
# ---------------------------------------------------------------------
def time_of_day_adjustment(hour: int) -> int:
    if 11 <= hour <= 16:
        return 5
    if 9 <= hour < 11 or 16 < hour <= 18:
        return 2
    if 5 <= hour < 9 or 18 < hour <= 20:
        return -2
    return -5  # night


@dataclass
class ExposureBreakdown:
    environmental_points: float
    temp_points: float
    humidity_points: float
    activity_points: float
    duration_points: float
    occupation_points: float
    vulnerability_points: float
    time_points: float
    total_score: float
    heat_index_c: float
    wbgt_estimate_c: float


def _environmental_points(heat_index_c: float) -> float:
    if heat_index_c <= ENV_MIN_C:
        return 0.0
    if heat_index_c >= ENV_MAX_C:
        return ENV_MAX_POINTS
    frac = (heat_index_c - ENV_MIN_C) / (ENV_MAX_C - ENV_MIN_C)
    return round(frac * ENV_MAX_POINTS, 1)


def calculate_exposure_score(
    temp_c: float,
    rh_percent: float,
    occupation: str,
    activity: str,
    duration: str,
    hour: int,
) -> ExposureBreakdown:
    hi = calculate_heat_index(temp_c, rh_percent)
    wbgt = calculate_wbgt_estimate(temp_c, rh_percent)

    env_pts = _environmental_points(hi.heat_index_c)
    # Decompose environmental heat into intuitive Temperature and Humidity load components
    temp_factor = max(0.0, min(25.0, (temp_c - 25.0) / 20.0 * 25.0))
    humidity_factor = max(0.0, min(20.0, (rh_percent - 30.0) / 55.0 * 20.0))
    
    act_pts = ACTIVITY_WEIGHTS.get(activity, 6)
    dur_pts = DURATION_WEIGHTS.get(duration, 6)
    occ_pts = OCCUPATION_WEIGHTS.get(occupation, 9)
    vuln_pts = VULNERABILITY_BUMP.get(occupation, 0)
    time_pts = time_of_day_adjustment(hour)

    total = env_pts + act_pts + dur_pts + occ_pts + vuln_pts + time_pts
    total = max(0.0, min(100.0, total))

    return ExposureBreakdown(
        environmental_points=env_pts,
        temp_points=round(temp_factor, 1),
        humidity_points=round(humidity_factor, 1),
        activity_points=act_pts,
        duration_points=dur_pts,
        occupation_points=occ_pts,
        vulnerability_points=vuln_pts,
        time_points=time_pts,
        total_score=round(total, 1),
        heat_index_c=hi.heat_index_c,
        wbgt_estimate_c=wbgt.wbgt_estimate_c,
    )


def explain_factors(breakdown: ExposureBreakdown, temp_c, rh_percent, activity, duration, hour) -> list:
    """Return deterministic, plain-language bullet points driving the risk,
    traceable directly to input conditions and occupational parameters."""
    reasons = []
    
    # 1. Temperature explanation
    if temp_c >= 40:
        reasons.append(f"Temperature is severely elevated ({temp_c:.1f}°C), causing critical ambient thermal load.")
    elif temp_c >= 35:
        reasons.append(f"Temperature is elevated ({temp_c:.1f}°C), increasing direct thermal burden.")
    elif temp_c >= 30:
        reasons.append(f"Temperature ({temp_c:.1f}°C) is moderately warm.")
    else:
        reasons.append(f"Ambient temperature ({temp_c:.1f}°C) is within mild range.")

    # 2. Humidity explanation
    if rh_percent >= 65:
        reasons.append(f"Relative humidity is high ({rh_percent:.0f}%), significantly reducing evaporative cooling via sweat.")
    elif rh_percent >= 45:
        reasons.append(f"Relative humidity ({rh_percent:.0f}%) moderately restricts sweat evaporation efficiency.")
    else:
        reasons.append(f"Relative humidity ({rh_percent:.0f}%) allows effective evaporative sweat cooling.")

    # 3. Activity explanation
    if activity == "Heavy":
        reasons.append("Heavy physical activity generates substantial internal metabolic heat.")
    elif activity == "Moderate":
        reasons.append("Moderate physical activity increases internal metabolic heat production.")
    elif activity == "Light":
        reasons.append("Light activity generates low internal metabolic heat.")
    else:
        reasons.append("Resting posture keeps metabolic heat production minimal.")

    # 4. Duration explanation
    if duration in ("3 hours", "4+ hours"):
        reasons.append(f"Prolonged continuous exposure ({duration}) creates cumulative thermal strain without adequate recovery.")
    elif duration == "2 hours":
        reasons.append(f"Exposure duration ({duration}) allows continuous heat accumulation.")
    else:
        reasons.append(f"Shorter duration ({duration}) limits cumulative thermal strain.")

    # 5. Time of day explanation
    if 11 <= hour <= 16:
        reasons.append(f"The selected time ({hour:02d}:00) falls directly near the daily peak-risk solar period.")
    elif 9 <= hour < 11 or 16 < hour <= 18:
        reasons.append(f"The selected time ({hour:02d}:00) falls in the moderate solar transition window.")
    else:
        reasons.append(f"The selected time ({hour:02d}:00) is outside peak daytime solar radiation.")

    # 6. Occupation context
    if breakdown.occupation_points >= 12:
        reasons.append("Occupation context involves extensive outdoor and sun exposure.")

    return reasons

