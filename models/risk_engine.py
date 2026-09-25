"""
risk_engine.py
--------------
Orchestrates the full pipeline described in the project brief:

Weather Data -> Environmental Heat Analysis -> Thermal Stress Calculation
-> Human Exposure Context -> Personalized Risk Level -> Early Warning
-> Actionable Recommendation

This module has no UI code and no network code -- it is pure logic, so
it is easy to test, reason about, and defend to judges.
"""

from dataclasses import dataclass, field
import pandas as pd

from calculations.exposure_model import calculate_exposure_score, explain_factors
from calculations.thermal_risk import categorize_risk


@dataclass
class PersonalizedRiskResult:
    score: float
    level: str
    color: str
    explanation: str
    action: str
    strategy: str
    heat_index_c: float
    wbgt_estimate_c: float
    reasons: list
    breakdown: dict


def compute_personalized_risk(temp_c, rh_percent, occupation, activity, duration, hour) -> PersonalizedRiskResult:
    breakdown = calculate_exposure_score(temp_c, rh_percent, occupation, activity, duration, hour)
    category = categorize_risk(breakdown.total_score)
    reasons = explain_factors(breakdown, temp_c, rh_percent, activity, duration, hour)

    return PersonalizedRiskResult(
        score=breakdown.total_score,
        level=category.level,
        color=category.color,
        explanation=category.explanation,
        action=category.action,
        strategy=category.strategy,
        heat_index_c=breakdown.heat_index_c,
        wbgt_estimate_c=breakdown.wbgt_estimate_c,
        reasons=reasons,
        breakdown={
            "Temperature": breakdown.temp_points,
            "Humidity": breakdown.humidity_points,
            "Activity": float(breakdown.activity_points),
            "Duration": float(breakdown.duration_points),
            "Occupation": float(breakdown.occupation_points),
            "Time of Day": float(max(0, breakdown.time_points + 5)),  # Normalized 0-10 for visualization
        },
    )


def compute_hourly_risk_timeline(hourly_df: pd.DataFrame, occupation, activity, duration) -> pd.DataFrame:
    """Given an hourly weather dataframe (time, temp_c, rh_percent), compute
    the personalized risk score/level for each hour -- powers the 12-24hr
    early warning chart."""
    records = []
    for _, row in hourly_df.iterrows():
        hour = pd.Timestamp(row["time"]).hour
        result = compute_personalized_risk(
            row["temp_c"], row["rh_percent"], occupation, activity, duration, hour
        )
        records.append({
            "time": row["time"],
            "temp_c": row["temp_c"],
            "rh_percent": row["rh_percent"],
            "score": result.score,
            "level": result.level,
            "color": result.color,
            "heat_index_c": result.heat_index_c,
            "wbgt_estimate_c": result.wbgt_estimate_c,
        })
    return pd.DataFrame(records)


def find_peak_risk_window(timeline_df: pd.DataFrame, band: float = 12.0, min_notable_score: float = 45.0):
    """Identify the contiguous block of hours immediately around the
    day's highest-risk hour -- the 'PEAK RISK WINDOW'.

    Walks outward from the single highest-scoring hour while neighboring
    hours stay within `band` points of that peak. Centered on the true daily maximum.

    Returns (None, None) if the day never reaches a notable risk score.
    """
    if timeline_df.empty:
        return None, None

    df = timeline_df.reset_index(drop=True)
    max_score = df["score"].max()
    if max_score < min_notable_score:
        return None, None

    idx_max = int(df["score"].idxmax())
    threshold = max_score - band

    start = idx_max
    while start - 1 >= 0 and df["score"].iloc[start - 1] >= threshold:
        start -= 1
    end = idx_max
    while end + 1 < len(df) and df["score"].iloc[end + 1] >= threshold:
        end += 1

    return df["time"].iloc[start], df["time"].iloc[end]


def find_lowest_exposure_window(timeline_df: pd.DataFrame, window_hours: int = 3):
    """Find the best (lowest average risk) contiguous window of the
    requested length -- considers ALL hours including overnight.
    Powers the 'Thermally Lowest-Risk Window' display."""
    if timeline_df.empty or len(timeline_df) < window_hours:
        return None, None, None

    best_avg = None
    best_start_idx = 0
    for i in range(len(timeline_df) - window_hours + 1):
        window = timeline_df.iloc[i:i + window_hours]
        avg_score = window["score"].mean()
        if best_avg is None or avg_score < best_avg:
            best_avg = avg_score
            best_start_idx = i

    start_time = timeline_df.iloc[best_start_idx]["time"]
    end_time = timeline_df.iloc[best_start_idx + window_hours - 1]["time"]
    return start_time, end_time, round(best_avg, 1)


# Occupations that operate in a defined daytime window (not overnight).
# The scheduler will constrain recommendations to OPERATIONAL_DAYTIME_WINDOW
# for these profiles, preventing unrealistic 2 AM recommendations.
OUTDOOR_OCCUPATIONS = {
    "Construction Worker",
    "Agricultural Worker",
    "Outdoor Worker",
    "Delivery Worker",
    "Traffic Police",
}

# Configurable operational daytime window (inclusive, 24-hour clock)
OPERATIONAL_DAYTIME_START = 6   # 06:00
OPERATIONAL_DAYTIME_END   = 20  # 20:00


def find_recommended_operational_window(
    timeline_df: pd.DataFrame,
    window_hours: int = 3,
    occupation: str = "General Public",
    start_hour: int = OPERATIONAL_DAYTIME_START,
    end_hour: int = OPERATIONAL_DAYTIME_END,
):
    """Find the lowest-risk contiguous window WITHIN a practical daytime
    operating range for outdoor/field occupations.

    For occupations in OUTDOOR_OCCUPATIONS the search is restricted to
    [start_hour, end_hour] (default 06:00-20:00) so we never recommend
    02:00 AM as a construction window, even if that is the thermal minimum.

    For indoor / general profiles the function falls back to the global
    find_lowest_exposure_window which scans all hours.

    Returns (start_time, end_time, avg_score) or (None, None, None).
    """
    if timeline_df.empty or len(timeline_df) < window_hours:
        return None, None, None

    if occupation not in OUTDOOR_OCCUPATIONS:
        # Non-outdoor profiles: full-day scan is fine
        return find_lowest_exposure_window(timeline_df, window_hours)

    # Filter to rows whose hour falls within the operational window
    df = timeline_df.copy().reset_index(drop=True)
    df["_hour"] = pd.to_datetime(df["time"]).dt.hour
    daytime_mask = (df["_hour"] >= start_hour) & (df["_hour"] <= end_hour)
    daytime_df = df[daytime_mask].reset_index(drop=True)

    if len(daytime_df) < window_hours:
        # Not enough daytime rows — fall back to full scan
        return find_lowest_exposure_window(timeline_df, window_hours)

    best_avg = None
    best_start_idx = 0
    for i in range(len(daytime_df) - window_hours + 1):
        window = daytime_df.iloc[i:i + window_hours]
        avg_score = window["score"].mean()
        if best_avg is None or avg_score < best_avg:
            best_avg = avg_score
            best_start_idx = i

    start_time = daytime_df.iloc[best_start_idx]["time"]
    end_time = daytime_df.iloc[best_start_idx + window_hours - 1]["time"]
    return start_time, end_time, round(best_avg, 1)


def format_datetime_window(start_dt, end_dt) -> str:
    """Formats start and end timestamps into unambiguous strings with date awareness.
    If same day:
        Sat, Sep 26 · 09:00 AM – 05:00 PM
    If crosses midnight:
        Fri, Sep 25 · 10:00 PM – Sat, Sep 26 · 12:00 AM
    """
    if start_dt is None or end_dt is None:
        return "N/A"

    t_start = pd.Timestamp(start_dt)
    t_end = pd.Timestamp(end_dt)

    start_str = t_start.strftime("%a, %b %d · %I:%M %p")
    if t_start.date() == t_end.date():
        return f"{start_str} – {t_end.strftime('%I:%M %p')}"
    else:
        return f"{start_str} – {t_end.strftime('%a, %b %d · %I:%M %p')}"


def recommend_work_schedule(hourly_df: pd.DataFrame, occupation: str, activity: str, duration_hours: int = 2):
    """Provides a complete decision-support analysis for the Best Time to Work feature.

    Returns TWO distinct windows:
    - thermal_min_*  : Absolute thermally lowest-risk window (any hour, including overnight).
    - operational_*  : Recommended operational window constrained to 06:00–20:00 daytime
                       for outdoor occupations -- prevents absurd 02:00 AM recommendations
                       for field workers.

    Also returns the peak-risk window to avoid and a plain-language explanation.
    """
    dur_label = f"{duration_hours} hour" if duration_hours == 1 else f"{duration_hours} hours"
    if duration_hours >= 4:
        dur_label = "4+ hours"

    timeline_df = compute_hourly_risk_timeline(hourly_df, occupation, activity, dur_label)
    if timeline_df.empty:
        return {
            "status": "unavailable",
            "message": "Hourly forecast data unavailable to compute work window.",
            "recommended_window": None,
            "peak_window": None,
            "explanation": "No hourly data available."
        }

    # --- 1. Absolute thermal minimum (all hours) ---
    th_start, th_end, th_score = find_lowest_exposure_window(timeline_df, window_hours=duration_hours)
    th_cat = categorize_risk(th_score) if th_score is not None else None

    # --- 2. Operational window (daytime-constrained for outdoor occupations) ---
    op_start, op_end, op_score = find_recommended_operational_window(
        timeline_df, window_hours=duration_hours, occupation=occupation
    )
    op_cat = categorize_risk(op_score) if op_score is not None else None

    # --- 3. Peak-risk window (always all-hours) ---
    peak_start, peak_end = find_peak_risk_window(timeline_df)

    # --- 4. Build explanation ---
    is_outdoor = occupation in OUTDOOR_OCCUPATIONS
    primary_cat = op_cat  # The operationally meaningful window
    primary_score = op_score
    primary_start = op_start

    if primary_cat and primary_cat.level in ("VERY HIGH", "EXTREME"):
        explanation = (
            f"Persistent elevated thermal stress across the entire forecast window. "
            f"Even the best available {'daytime ' if is_outdoor else ''}window scores {primary_score}/100 ({primary_cat.level}). "
            f"No genuinely low-risk window exists within operational hours. "
            f"Postponing strenuous tasks or enforcing mandatory shaded rest-work cycles is strongly recommended."
        )
    elif primary_cat:
        t_start_str = pd.Timestamp(primary_start).strftime("%I:%M %p") if primary_start is not None else "N/A"
        day_note = (
            f" The search was constrained to {OPERATIONAL_DAYTIME_START:02d}:00–{OPERATIONAL_DAYTIME_END:02d}:00 "
            f"(practical operational hours for {occupation})."
            if is_outdoor else ""
        )
        explanation = (
            f"A continuous lower-risk window was identified starting at {t_start_str}, "
            f"with an average exposure score of {primary_score}/100 ({primary_cat.level}), "
            f"benefiting from cooler diurnal temperatures and reduced solar radiation."
            f"{day_note}"
        )
    else:
        explanation = "Insufficient forecast data to evaluate a continuous work window."

    # Backwards-compatible keys (recommended_* = operational window for app.py)
    return {
        "status": "success",
        "timeline_df": timeline_df,
        "is_outdoor_occupation": is_outdoor,
        # --- Operational (daytime-constrained for outdoor; full-scan for others) ---
        "recommended_start": op_start,
        "recommended_end": op_end,
        "recommended_score": op_score,
        "recommended_level": op_cat.level if op_cat else "LOW",
        "recommended_color": op_cat.color if op_cat else "#2E7D32",
        "formatted_recommended": format_datetime_window(op_start, op_end),
        # --- Absolute thermal minimum (any hour) ---
        "thermal_min_start": th_start,
        "thermal_min_end": th_end,
        "thermal_min_score": th_score,
        "thermal_min_level": th_cat.level if th_cat else "LOW",
        "thermal_min_color": th_cat.color if th_cat else "#2E7D32",
        "formatted_thermal_min": format_datetime_window(th_start, th_end),
        # --- Peak risk window ---
        "peak_start": peak_start,
        "peak_end": peak_end,
        "formatted_peak": format_datetime_window(peak_start, peak_end),
        "explanation": explanation,
    }


def detect_heatwave_status(multiday_df: pd.DataFrame):
    """Simple, documented heatwave-watch heuristic for the demo:
    - WATCH: any single day's max temp exceeds the 5-day mean by >= 2C
    - WARNING: 2+ consecutive days exceed the mean by >= 2C
    - SEVERE: 2+ consecutive days exceed the mean by >= 4C, or any day >= 45C
    - NORMAL: none of the above

    This is explicitly a PROTOTYPE heuristic, not an official IMD
    heatwave declaration (which uses departure-from-normal criteria
    against long-term climatological baselines)."""
    if multiday_df.empty:
        return "NORMAL", "Insufficient data."

    mean_max = multiday_df["max_temp_c"].mean()
    deviations = multiday_df["max_temp_c"] - mean_max

    severe_days = (deviations >= 4) | (multiday_df["max_temp_c"] >= 45)
    warning_days = deviations >= 2

    def has_consecutive(mask, n=2):
        run = 0
        for v in mask:
            run = run + 1 if v else 0
            if run >= n:
                return True
        return False

    if has_consecutive(severe_days, 2) or (severe_days.sum() >= 1 and multiday_df["max_temp_c"].max() >= 45):
        return "SEVERE", "Multiple days of significantly above-average, dangerous heat detected."
    if has_consecutive(warning_days, 2):
        return "WARNING", "Consecutive days of well-above-average heat detected."
    if warning_days.any():
        return "WATCH", "At least one day shows a notable heat spike above the period average."
    return "NORMAL", "No unusual heat pattern detected in the forecast window."


def compute_risk_trend(timeline_df: pd.DataFrame, now_hour: int) -> dict:
    """Computes a dynamic risk trend insight from actual forecast timeline values.
    
    Returns a dict with:
        - symbol : str ("↑", "▶", "↓", "→")
        - label  : str ("RISING", "PEAKING", "DECLINING", "STABLE")
        - text   : str (e.g., "↑ Rising toward afternoon peak")
        - detail : str (e.g., "Rising toward peak at ~02:00 PM")
    """
    if timeline_df is None or timeline_df.empty or "score" not in timeline_df.columns:
        return {
            "symbol": "→",
            "label": "STABLE",
            "text": "→ Stable thermal exposure",
            "detail": "Forecast data unavailable for trend calculation.",
        }

    scores = timeline_df["score"].tolist()
    times = timeline_df["time"].tolist()
    
    if len(scores) < 3:
        return {
            "symbol": "→",
            "label": "STABLE",
            "text": "→ Stable thermal exposure",
            "detail": "Insufficient forecast points to calculate trend.",
        }

    # Find row corresponding to current hour or default to first
    curr_idx = 0
    for idx, t in enumerate(times):
        try:
            if pd.to_datetime(t).hour == now_hour:
                curr_idx = idx
                break
        except Exception:
            pass

    current_score = scores[curr_idx]
    max_score = max(scores)
    max_idx = scores.index(max_score)
    
    next_idx = min(curr_idx + 3, len(scores) - 1)
    future_score = scores[next_idx]
    delta = future_score - current_score

    if current_score >= max_score - 2.5:
        return {
            "symbol": "▶",
            "label": "PEAKING",
            "text": "▶ Peaking at maximum daily heat",
            "detail": f"Currently near maximum daily exposure ({max_score:.1f}/100).",
        }
    elif delta >= 3.0:
        try:
            peak_time_str = pd.to_datetime(times[max_idx]).strftime("%I:%M %p")
        except Exception:
            peak_time_str = "afternoon"
        return {
            "symbol": "↑",
            "label": "RISING",
            "text": f"↑ Rising toward afternoon peak",
            "detail": f"Rising by +{delta:.1f} pts toward peak at ~{peak_time_str}.",
        }
    elif delta <= -3.0:
        return {
            "symbol": "↓",
            "label": "DECLINING",
            "text": "↓ Declining thermal stress",
            "detail": f"Easing by {abs(delta):.1f} pts as diurnal heat subsides.",
        }
    else:
        return {
            "symbol": "→",
            "label": "STABLE",
            "text": "→ Stable thermal conditions",
            "detail": "Thermal exposure remaining relatively constant across next hours.",
        }

