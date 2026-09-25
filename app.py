"""
ThermoShield AI
Human-Centric Heatwave Early Warning & Thermal Stress Intelligence

SIH26083 - Heatwave Early Warning & Human Thermal Stress Index
Dual Demonstration Engine:
  1. Controlled Demo: "SAME WEATHER, DIFFERENT RISK" (Chennai 38°C, 70% RH)
  2. Live Demo: Real-Time Open-Meteo API Feed -> Dynamic Human Thermal Stress
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from services.fallback_weather import (
    get_demo_current, get_demo_hourly, get_demo_multiday, list_cities, CITY_PROFILES
)
from services.weather_api import (
    get_current_weather, get_hourly_forecast, get_daily_forecast,
    get_multi_city_weather, WeatherAPIError
)
from models.risk_engine import (
    compute_personalized_risk, compute_hourly_risk_timeline,
    find_peak_risk_window, find_lowest_exposure_window, recommend_work_schedule,
    detect_heatwave_status, format_datetime_window,
    find_recommended_operational_window, OUTDOOR_OCCUPATIONS,
    OPERATIONAL_DAYTIME_START, OPERATIONAL_DAYTIME_END, compute_risk_trend,
)
from calculations.wbgt import WBGT_REFERENCE_BANDS
from calculations.thermal_risk import RISK_BANDS, RISK_GUIDANCE
from ui.components import (
    inject_global_css, render_risk_badge, source_tag, metric_card, alert_card,
    executive_summary_bar, data_freshness_status, current_exposure_advisory_card
)
from ui.charts import (
    hourly_risk_timeline_chart, risk_breakdown_chart, comparison_bar_chart,
    risk_history_chart, multiday_heatwave_chart
)
from ui.advisory import get_advisory, translate, action_center_items

# ----------------------------------------------------------------------
# PAGE CONFIG & CSS
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="ThermoShield AI | Thermal Stress Intelligence",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

OCCUPATIONS = [
    "Construction Worker",
    "Agricultural Worker",
    "Delivery Worker",
    "Traffic Police",
    "Outdoor Worker",
    "Student",
    "Office Worker",
    "Elderly Person",
    "General Public",
]
ACTIVITIES = ["Resting", "Light", "Moderate", "Heavy"]
DURATIONS = ["30 minutes", "1 hour", "2 hours", "3 hours", "4+ hours"]

if "risk_history" not in st.session_state:
    st.session_state.risk_history = []

if "hero_scenario" not in st.session_state:
    st.session_state.hero_scenario = False

# ----------------------------------------------------------------------
# CACHED LIVE WEATHER HELPERS (TTL: 5 Minutes)
# ----------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def cached_live_current(city_name: str) -> dict:
    return get_current_weather(city_name)


@st.cache_data(ttl=300, show_spinner=False)
def cached_live_hourly(city_name: str, hours: int = 24) -> pd.DataFrame:
    return get_hourly_forecast(city_name, hours)


@st.cache_data(ttl=300, show_spinner=False)
def cached_live_daily(city_name: str, days: int = 5) -> pd.DataFrame:
    return get_daily_forecast(city_name, days)


@st.cache_data(ttl=300, show_spinner=False)
def cached_multi_city_weather(cities_tuple: tuple) -> list:
    return get_multi_city_weather(list(cities_tuple))


# ----------------------------------------------------------------------
# SIDEBAR CONTROLS
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🛡️ ThermoShield AI")
    st.markdown("**Human-Centric Heatwave Intelligence**")
    st.caption("SIH Prototype · Decision Support")

    st.markdown("---")
    mode = st.radio(
        "Data Mode",
        ["LIVE MODE", "DEMO MODE"],
        index=0,
        horizontal=True,
        help="LIVE MODE uses Open-Meteo real-time live forecast. DEMO MODE operates 100% offline."
    )

    st.markdown("### 📍 Location")
    city = st.selectbox("City / Region", list_cities(), index=0)

    st.markdown("### 👤 Human Exposure Profile")
    occupation = st.selectbox("Occupation", OCCUPATIONS, index=0)
    activity = st.select_slider("Activity Intensity", ACTIVITIES, value="Heavy")
    duration = st.select_slider("Exposure Duration", DURATIONS, value="3 hours")

    st.markdown("### 🌐 Language")
    lang = st.radio("Advisory Language", ["English", "Tamil"], horizontal=True)

    st.markdown("---")
    st.caption(
        "⚠️ **Decision-Support Notice:** ThermoShield AI provides operational thermal exposure guidance, "
        "not clinical diagnostic advice or official government disaster declarations."
    )

# ----------------------------------------------------------------------
# WEATHER DATA FETCHING & ROBUST OFFLINE FALLBACK
# ----------------------------------------------------------------------
is_fallback = False
fallback_msg = ""

def fetch_current(selected_city, selected_mode):
    global is_fallback, fallback_msg
    if selected_mode == "LIVE MODE":
        try:
            return cached_live_current(selected_city), True, False
        except Exception as e:
            is_fallback = True
            fallback_msg = f"Live weather API unavailable ({e}) — switched to Demo Fallback."
            return get_demo_current(selected_city), False, True
    return get_demo_current(selected_city), False, False


def fetch_hourly(selected_city, selected_mode, hours=24):
    global is_fallback, fallback_msg
    if selected_mode == "LIVE MODE":
        try:
            df = cached_live_hourly(selected_city, hours)
            if df is not None and not df.empty:
                return df, True
        except Exception:
            is_fallback = True
    return get_demo_hourly(selected_city, hours), False


def fetch_multiday(selected_city, selected_mode, days=5):
    global is_fallback, fallback_msg
    if selected_mode == "LIVE MODE":
        try:
            df = cached_live_daily(selected_city, days)
            if df is not None and not df.empty:
                return df, True
        except Exception:
            is_fallback = True
    return get_demo_multiday(selected_city, days), False


current, is_live_current, triggered_fallback = fetch_current(city, mode)
hourly_df, is_live_hourly = fetch_hourly(city, mode, 24)
multiday_df, is_live_multiday = fetch_multiday(city, mode, 5)

# Derive local hour from current data or system time
try:
    now_hour = pd.to_datetime(current.get("timestamp", datetime.now())).hour
except Exception:
    now_hour = datetime.now().hour

# Compute personalized risk for the current profile using the LIVE/DEMO weather
result = compute_personalized_risk(
    current["temp_c"], current["rh_percent"], occupation, activity, duration, now_hour
)

# Compute 24h timeline and dynamic peak risk window using the actual forecast
timeline_df = compute_hourly_risk_timeline(hourly_df, occupation, activity, duration)
peak_start, peak_end = find_peak_risk_window(timeline_df)
low_start, low_end, low_avg = find_lowest_exposure_window(timeline_df, window_hours=2)

# Dynamic risk trend derived from forecast
risk_trend = compute_risk_trend(timeline_df, now_hour)

# Unambiguous exact date/time strings
peak_window_str = format_datetime_window(peak_start, peak_end)
low_window_str = format_datetime_window(low_start, low_end)

# Forecast range string
if hourly_df is not None and not hourly_df.empty:
    t_first = pd.Timestamp(hourly_df["time"].iloc[0])
    t_last = pd.Timestamp(hourly_df["time"].iloc[-1])
    forecast_range_str = f"{t_first.strftime('%a, %b %d · %I:%M %p')} – {t_last.strftime('%a, %b %d · %I:%M %p')}"
else:
    forecast_range_str = "Next 24 Hours"

# Session history update
new_history_entry = {
    "Time": datetime.now().strftime("%H:%M:%S"),
    "Location": city,
    "Occupation": occupation,
    "Activity": activity,
    "Duration": duration,
    "Score": result.score,
    "Risk": result.level,
    "Mode": "LIVE" if is_live_current else "DEMO",
}
last_entry = st.session_state.risk_history[-1] if st.session_state.risk_history else None
if last_entry is None or {k: v for k, v in new_history_entry.items() if k != "Time"} != {k: v for k, v in last_entry.items() if k != "Time"}:
    st.session_state.risk_history.append(new_history_entry)
    st.session_state.risk_history = st.session_state.risk_history[-200:]

# ----------------------------------------------------------------------
# HEADER & DATA FRESHNESS BAR
# ----------------------------------------------------------------------
st.title("🌡️ ThermoShield AI")
st.markdown("**Human-Centric Heatwave Early Warning & Thermal Stress Intelligence**")

# Data Freshness / Source Provenance
data_freshness_status(
    is_live=is_live_current,
    source=current.get("source", "Open-Meteo Live API" if is_live_current else "Demo Simulation"),
    updated=current.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M")),
    forecast_range=forecast_range_str,
    is_fallback=triggered_fallback or (mode == "LIVE MODE" and not is_live_current),
)

# ----------------------------------------------------------------------
# NAVIGATION TABS
# ----------------------------------------------------------------------
tabs = st.tabs([
    "1. Overview",
    "2. Current Risk",
    "3. Why This Risk?",
    "4. Hourly Early Warning",
    "5. Best Time to Work",
    "6. Same Weather / Different Risk",
    "7. Thermal Risk Map",
    "8. Heatwave Watch",
    "9. Organization Safety Mode",
    "10. Methodology",
])

# ======================================================================
# TAB 1: OVERVIEW (Vertical Decision-Support Dashboard)
# ======================================================================
with tabs[0]:
    st.markdown("## Human-Centric Thermal Risk Overview")
    st.caption(
        f"Decision support for {occupation} · {activity} activity · {duration} exposure · {city}"
    )

    # 1. ONE DOMINANT CURRENT THERMAL EXPOSURE SECTION
    st.markdown(
        f"""
        <div class="ts-risk-hero" style="border-left-color:{result.color};">
            <div class="ts-section-label">CURRENT THERMAL EXPOSURE</div>
            <div class="ts-risk-hero-main">
                <div>
                    <div class="ts-risk-score" style="color:{result.color};">{result.score:.1f}<span>/100</span></div>
                    <div style="margin-top:0.35rem;">
                        <span class="ts-badge" style="background:{result.color};">{result.level}</span>
                    </div>
                </div>
                <div class="ts-risk-context">
                    <div><b>Profile</b> · {occupation}</div>
                    <div><b>Activity</b> · {activity} &nbsp; <b>Duration</b> · {duration}</div>
                    <div class="ts-trend-text">{risk_trend['text']}</div>
                </div>
            </div>
            <div class="ts-hero-action">
                <b>Primary operational guidance:</b> {result.action}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. COMPACT WEATHER / THERMAL INDICATORS
    st.markdown("#### Current Conditions")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Air Temperature", f"{current['temp_c']:.1f}°C", "Ambient shade temperature")
    with m2:
        metric_card("Relative Humidity", f"{current['rh_percent']:.0f}%", "Evaporative cooling")
    with m3:
        metric_card(
            "Thermal Index",
            f"{result.heat_index_c:.1f}°C",
            f"Est. WBGT {result.wbgt_estimate_c:.1f}°C",
        )
    with m4:
        metric_card(
            "Wind Speed",
            f"{current.get('wind_kmh', 12):.0f} km/h",
            "Convective cooling",
        )

    st.markdown("---")

    # 3. WHY THIS RISK — primarily vertical
    st.markdown("#### WHY THIS RISK?")
    st.caption(
        "The score is traceable to the actual environmental conditions and selected exposure profile."
    )
    st.plotly_chart(
        risk_breakdown_chart(result.breakdown),
        width="stretch",
        key="overview_risk_breakdown",
    )

    st.markdown("**Key contributing factors**")
    for r in result.reasons:
        st.markdown(f"- {r}")

    st.info(f"**Risk trend:** {risk_trend['detail']}")

    st.markdown("---")

    # 4. NEXT 24 HOURS — focal visual
    st.markdown("#### NEXT 24 HOURS")
    st.caption(
        "Forecast-derived personalized thermal exposure. The chart marks current time, "
        "peak-risk conditions, and the preferred lower-risk operational window."
    )

    now_time_val = (
        timeline_df["time"].iloc[0]
        if timeline_df is not None and not timeline_df.empty
        else None
    )

    st.plotly_chart(
        hourly_risk_timeline_chart(
            timeline_df,
            peak_start,
            peak_end,
            low_start,
            low_end,
            now_time=now_time_val,
        ),
        width="stretch",
        key="overview_hourly_risk_timeline",
    )

    # 5. TREND + ACTION, vertically stacked
    st.markdown("#### RISK TREND")
    st.markdown(
        f"""
        <div class="ts-action-strip">
            <div class="ts-section-label">{risk_trend['label'] if 'label' in risk_trend else 'FORECAST TREND'}</div>
            <div class="ts-trend-text">{risk_trend['text']}</div>
            <div class="ts-small">{risk_trend['detail']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### ACTION")
    st.markdown(
        f"""
        <div class="ts-action-strip" style="border-left-color:{result.color};">
            <div class="ts-section-label">RECOMMENDED ACTION</div>
            <div style="font-size:1.05rem; font-weight:700; line-height:1.5;">{result.action}</div>
            <div class="ts-small" style="margin-top:0.55rem;">{result.strategy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if peak_start is not None and peak_end is not None:
        st.markdown("#### PEAK-RISK PERIOD")
        st.warning(
            f"**{peak_window_str}**\n\n"
            "Higher forecast thermal stress during this period. "
            "Plan strenuous outdoor activity with appropriate recovery breaks."
        )

    # 6. SUPPORTING DETAILS
    with st.expander("View Operational Action Checklist & Shift Guidelines"):
        st.markdown(f"**Recommended Shift Strategy:** {result.strategy}")
        st.markdown("**Field Action Checklist:**")
        for item in action_center_items(result.level, occupation):
            st.markdown(f"- {item}")


# ======================================================================
# TAB 2: CURRENT RISK
# ======================================================================
with tabs[1]:
    st.markdown("### ⚠️ Current Thermal Risk Assessment")
    st.caption("Deep physiological and environmental breakdown for the selected individual.")

    cr_col1, cr_col2 = st.columns([1, 2])
    with cr_col1:
        st.markdown(
            f"""
            <div class="ts-card" style="border-top: 5px solid {result.color}; text-align:center;">
                <div class="ts-metric-label">Personalized Thermal Exposure Score</div>
                <div style="margin: 0.8rem 0;">
                    <span class="ts-badge" style="background:{result.color}; font-size:1.35rem; padding:0.5rem 1.4rem;">
                        {result.level}
                    </span>
                </div>
                <div style="font-size:2.6rem; font-weight:800; color:{result.color};">
                    {result.score} <span style="font-size:1rem; opacity:0.7; font-weight:500;">/ 100</span>
                </div>
                <div class="ts-small" style="margin-top:0.5rem;">Composite Thermal Strain Index</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Scientific Indicators")
        st.write(f"- **Heat-Index-Based Thermal Risk:** `{result.heat_index_c:.1f}°C` (NOAA Rothfusz)")
        st.write(f"- **Estimated WBGT:** `{result.wbgt_estimate_c:.1f}°C` (BoM approximation)")
        st.caption("Estimated WBGT is derived from temperature and humidity only (shade/no globe sensor).")

    with cr_col2:
        st.markdown("#### Exposure Analysis")
        st.info(result.explanation)

        st.markdown("#### Direct Recommended Action")
        st.warning(result.action)

        st.markdown("#### Work-Rest Cycle Strategy")
        st.success(result.strategy)

        st.markdown("#### Action Checklist")
        for item in action_center_items(result.level, occupation):
            st.markdown(f"- {item}")

# ======================================================================
# TAB 3: WHY THIS RISK? (Phase 5 Explainability)
# ======================================================================
with tabs[2]:
    st.markdown("### 🔍 Why Am I At Risk?")
    st.caption(
        "Deterministic, traceable factor attribution. No simulated or black-box ML explanations — "
        "every point is mapped directly to actual forecast and occupational inputs."
    )

    why_col1, why_col2 = st.columns([1.1, 1])
    with why_col1:
        st.markdown("#### Factor Risk Contribution Breakdown")
        st.plotly_chart(
            risk_breakdown_chart(result.breakdown),
            width="stretch",
            key="why_risk_breakdown",
        )

    with why_col2:
        st.markdown("#### Traceable Plain-Language Drivers")
        for r in result.reasons:
            st.markdown(f"- **{r}**")

        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:10px; border:1px solid rgba(255,255,255,0.08); font-size:0.88rem;">
                <b>Traceability Formula:</b><br>
                Personalized Risk Score (<b>{result.score}/100</b>) is computed additively from:
                <ul>
                    <li>Environmental Heat: Heat Index {result.heat_index_c:.1f}°C (Air Temp: {current['temp_c']:.1f}°C, RH: {current['rh_percent']:.0f}%)</li>
                    <li>Metabolic Workload: {activity}</li>
                    <li>Cumulative Exposure Duration: {duration}</li>
                    <li>Occupational Context: {occupation}</li>
                    <li>Diurnal Sun Exposure: Hour {now_hour:02d}:00</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ======================================================================
# TAB 4: HOURLY EARLY WARNING (Phase 6 Timeline)
# ======================================================================
with tabs[3]:
    st.markdown("### ⏱️ 12–24 Hour Early Warning Timeline")
    st.caption("Forecast of personal thermal exposure across upcoming hours, derived from real-time meteorological forecast data.")

    st.plotly_chart(
        hourly_risk_timeline_chart(
            timeline_df,
            peak_start,
            peak_end,
            low_start,
            low_end,
        ),
        width="stretch",
        key="hourly_early_warning_timeline",
    )

    ew_col1, ew_col2 = st.columns(2)
    with ew_col1:
        if peak_start is not None and peak_end is not None:
            st.error(
                f"**⚠ DYNAMIC PEAK THERMAL-RISK WINDOW:**\n\n"
                f"### {peak_window_str}\n\n"
                f"Avoid continuous strenuous activity during this period. Enforce shaded recovery breaks."
            )
        else:
            st.info("No extreme peak risk period detected in current forecast window.")
    with ew_col2:
        if low_start is not None and low_end is not None:
            st.success(
                f"**✓ RECOMMENDED LOWER-EXPOSURE WINDOW:**\n\n"
                f"### {low_window_str}\n\n"
                f"Average exposure score {low_avg:.1f} (benefiting from lower diurnal ambient temperatures)."
            )

    with st.expander("View Complete Hourly Forecast & Personal Risk Table"):
        display_hourly = timeline_df.copy()
        display_hourly["Formatted Time"] = display_hourly["time"].dt.strftime("%a, %b %d · %I:%M %p")
        display_hourly = display_hourly.rename(columns={
            "temp_c": "Temp (°C)",
            "rh_percent": "RH (%)",
            "score": "Thermal Score",
            "level": "Risk Category",
            "heat_index_c": "Heat Index (°C)",
            "wbgt_estimate_c": "Est. WBGT (°C)",
        })
        st.dataframe(
            display_hourly[["Formatted Time", "Temp (°C)", "RH (%)", "Heat Index (°C)", "Est. WBGT (°C)", "Thermal Score", "Risk Category"]],
            width='stretch'
        )

# ======================================================================
# TAB 5: BEST TIME TO WORK (Phase 7 Scheduler)
# ======================================================================
with tabs[4]:
    st.markdown("### 🕒 Best Time to Work")
    st.caption(
        "Scans the actual upcoming hourly forecast and separates the lowest thermal "
        "stress from the operationally practical work window."
    )

    bsc1, bsc2, bsc3 = st.columns([2, 2, 1])
    with bsc1:
        sched_activity = st.selectbox(
            "Planned Task Activity",
            ACTIVITIES,
            index=3,
            key="bw_activity",
        )
    with bsc2:
        sched_dur_hours = st.slider(
            "Required Task Duration (Hours)",
            min_value=1,
            max_value=6,
            value=2,
            key="bw_hours",
        )
    with bsc3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.button("Scan Live Forecast", width="stretch", key="scan_live_forecast")

    sched_plan = recommend_work_schedule(
        hourly_df,
        occupation,
        sched_activity,
        sched_dur_hours,
    )

    if sched_plan["status"] == "success":
        is_outdoor = sched_plan.get("is_outdoor_occupation", False)

        st.markdown("#### RECOMMENDED OPERATIONAL WINDOW")
        st.markdown(
            f"""
            <div class="ts-schedule-hero">
                <div class="ts-section-label">PREFERRED WORK PERIOD</div>
                <div class="ts-schedule-time">{sched_plan['formatted_recommended']}</div>
                <div class="ts-schedule-meta">
                    Average thermal score:
                    <b>{sched_plan['recommended_score']:.1f}/100</b>
                    · {sched_plan['recommended_level']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("**Why:** Lower forecast thermal stress during the selected work period.")

        if is_outdoor:
            st.caption(
                "For outdoor occupations, the operational search is constrained to "
                "06:00 AM–08:00 PM rather than selecting overnight thermal minima."
            )

        st.markdown("#### PEAK-RISK PERIOD")
        if sched_plan["peak_start"] is not None and sched_plan["peak_end"] is not None:
            st.markdown(
                f"""
                <div class="ts-schedule-risk">
                    <div class="ts-section-label">HIGHER-THERMAL-STRESS PERIOD</div>
                    <div class="ts-schedule-time">{sched_plan['formatted_peak']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write(
                "**Why:** Higher temperature + humidity + daytime thermal loading."
            )
        else:
            st.info("No distinct peak-risk period was identified in the selected forecast.")

        st.markdown("#### SELECTION LOGIC")
        st.write(sched_plan["explanation"])

        # Thermal minimum is deliberately secondary: it may occur outside
        # realistic operational hours for outdoor occupations.
        with st.expander("Thermal Minimum Reference"):
            th_fmt = sched_plan.get("formatted_thermal_min", "N/A")
            th_score = sched_plan.get("thermal_min_score", "N/A")
            th_level = sched_plan.get("thermal_min_level", "")
            st.write(
                f"Lowest absolute thermal stress in the scanned forecast: "
                f"**{th_fmt}** (average score: **{th_score}** · {th_level})."
            )
            if is_outdoor:
                st.caption(
                    "This is a thermal reference only. Overnight hours are excluded "
                    "from outdoor operational recommendations."
                )

    else:
        st.warning(
            "No suitable lower-risk operational window found in the selected working hours."
        )
        if sched_plan.get("formatted_thermal_min"):
            st.caption(
                f"Least-risk available period: {sched_plan['formatted_thermal_min']} "
                f"(score: {sched_plan.get('thermal_min_score', 'N/A')})."
            )


# ======================================================================
# TAB 6: SAME WEATHER, DIFFERENT RISK (Phase 8 HERO DEMONSTRATION)
# ======================================================================
with tabs[5]:
    st.markdown("## ⚖️ Same Weather. Different Risk.")
    st.markdown(
        "> ### *“Nothing changed in the weather. We changed the human exposure.”*"
    )
    st.caption("The central innovation: standard weather apps treat both persons identically; ThermoShield AI provides personalized, occupation-aware life-saving intelligence.")

    # 1-Click Expo Demo Preset Button
    preset_col1, preset_col2 = st.columns([1.5, 2.5])
    with preset_col1:
        if st.button("🎯 Load SIH Expo Preset: Chennai (38°C, 70% RH)", width='stretch'):
            st.session_state.hero_scenario = True
            st.session_state.hero_temp = 38.0
            st.session_state.hero_rh = 70.0
            st.session_state.hero_city = "Chennai"
    with preset_col2:
        if st.session_state.hero_scenario:
            st.success("✓ SIH Expo Preset Active: Chennai (38°C, 70% RH) · Construction vs Office Worker")

    # Shared Weather Conditions
    st.markdown("#### 1. Identical Environmental Weather")
    h_temp = st.session_state.get("hero_temp", current["temp_c"])
    h_rh = st.session_state.get("hero_rh", current["rh_percent"])
    h_city = st.session_state.get("hero_city", city)

    hw_col1, hw_col2, hw_col3, hw_col4 = st.columns(4)
    with hw_col1:
        metric_card("Ambient Temperature", f"{h_temp:.1f}°C")
    with hw_col2:
        metric_card("Relative Humidity", f"{h_rh:.0f}%")
    with hw_col3:
        hi_hero = compute_personalized_risk(h_temp, h_rh, "Office Worker", "Light", "30 minutes", 13).heat_index_c
        metric_card("Heat Index (Both)", f"{hi_hero:.1f}°C")
    with hw_col4:
        metric_card("Location (Both)", h_city)

    st.markdown("---")

    # Side-by-side human exposure setup
    st.markdown("#### 2. Distinct Human Exposure Contexts")
    h_left, h_right = st.columns(2)

    with h_left:
        st.markdown(
            """
            <div style="background:rgba(216, 67, 21, 0.1); border-left:5px solid #D84315; padding:0.8rem 1.2rem; border-radius:8px;">
                <h4 style="margin:0; color:#ffab91;">PERSON A</h4>
                <div style="font-size:0.85rem; opacity:0.8;">High Occupational Heat Strain</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pa_occ = st.selectbox("Occupation A", OCCUPATIONS, index=0, key="pa_occ")  # Construction Worker
        pa_act = st.select_slider("Activity A", ACTIVITIES, value="Heavy", key="pa_act")
        pa_dur = st.select_slider("Duration A", DURATIONS, value="3 hours", key="pa_dur")

    with h_right:
        st.markdown(
            """
            <div style="background:rgba(46, 125, 50, 0.1); border-left:5px solid #2E7D32; padding:0.8rem 1.2rem; border-radius:8px;">
                <h4 style="margin:0; color:#a5d6a7;">PERSON B</h4>
                <div style="font-size:0.85rem; opacity:0.8;">Low Occupational Heat Strain</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pb_occ = st.selectbox("Occupation B", OCCUPATIONS, index=6, key="pb_occ")  # Office Worker
        pb_act = st.select_slider("Activity B", ACTIVITIES, value="Light", key="pb_act")
        pb_dur = st.select_slider("Duration B", DURATIONS, value="30 minutes", key="pb_dur")

    # Compute outcomes for both under EXACT SAME weather
    res_a = compute_personalized_risk(h_temp, h_rh, pa_occ, pa_act, pa_dur, 13)
    res_b = compute_personalized_risk(h_temp, h_rh, pb_occ, pb_act, pb_dur, 13)

    st.markdown("---")

    # Side-by-side results
    st.markdown("#### 3. Radically Different Thermal Safety Outcomes")
    r_col1, r_col2 = st.columns(2)

    with r_col1:
        st.markdown(
            f"""
            <div class="ts-card" style="border: 2px solid {res_a.color};">
                <div style="font-size: 1.1rem; font-weight:700; color:{res_a.color};">{pa_occ}</div>
                <div style="margin: 0.6rem 0;">
                    <span class="ts-badge" style="background:{res_a.color}; font-size:1.15rem; padding:0.4rem 1.2rem;">
                        {res_a.level} ({res_a.score}/100)
                    </span>
                </div>
                <div style="font-size:0.9rem; margin-bottom:0.6rem;"><b>Primary Action:</b> {res_a.action}</div>
                <div class="ts-small"><b>Strategy:</b> {res_a.strategy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r_col2:
        st.markdown(
            f"""
            <div class="ts-card" style="border: 2px solid {res_b.color};">
                <div style="font-size: 1.1rem; font-weight:700; color:{res_b.color};">{pb_occ}</div>
                <div style="margin: 0.6rem 0;">
                    <span class="ts-badge" style="background:{res_b.color}; font-size:1.15rem; padding:0.4rem 1.2rem;">
                        {res_b.level} ({res_b.score}/100)
                    </span>
                </div>
                <div style="font-size:0.9rem; margin-bottom:0.6rem;"><b>Primary Action:</b> {res_b.action}</div>
                <div class="ts-small"><b>Strategy:</b> {res_b.strategy}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Comparison chart
    st.plotly_chart(
        comparison_bar_chart(
            res_a,
            res_b,
            name_a=f"Person A ({pa_occ})",
            name_b=f"Person B ({pb_occ})",
        ),
        width="stretch",
        key="same_weather_different_risk_comparison",
    )

    st.markdown(
        f"""
        <div style="text-align:center; padding:1.2rem; background:rgba(255,255,255,0.02); border-radius:12px; border:1px solid rgba(255,255,255,0.08); margin-top:1rem;">
            <div style="font-size:1.3rem; font-weight:800; color:#ffab91;">
                “Nothing changed in the weather. We changed the human exposure.”
            </div>
            <div style="font-size:0.95rem; opacity:0.85; margin-top:0.4rem;">
                Ambient meteorological conditions remain 100% identical. The risk diverges entirely because human physical exposure and metabolic load changed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ======================================================================
# TAB 7: THERMAL RISK MAP (Phase 9 - Live Multi-City Map)
# ======================================================================
with tabs[6]:
    map_title = "LIVE THERMAL RISK MAP" if (mode == "LIVE MODE" and is_live_current) else "PROTOTYPE THERMAL RISK MAP (DEMO / FALLBACK)"
    st.markdown(f"### 🗺️ {map_title}")
    st.caption("Multi-city spatial thermal intelligence. Markers reflect live conditions and the active exposure profile.")

    try:
        from ui.map import render_city_map
        all_cities = list_cities()
        if mode == "LIVE MODE":
            try:
                city_weather_list = cached_multi_city_weather(tuple(all_cities))
            except Exception:
                city_weather_list = [get_demo_current(c) for c in all_cities]
        else:
            city_weather_list = [get_demo_current(c) for c in all_cities]

        city_conditions = []
        for c_curr in city_weather_list:
            c_name = c_curr["city"]
            c_timeline = compute_hourly_risk_timeline(get_demo_hourly(c_name, 24), occupation, activity, duration)
            c_pstart, c_pend = find_peak_risk_window(c_timeline)
            c_pstr = format_datetime_window(c_pstart, c_pend)

            city_conditions.append({
                "city": c_name,
                "temp_c": c_curr["temp_c"],
                "rh_percent": c_curr["rh_percent"],
                "lat": c_curr["lat"],
                "lon": c_curr["lon"],
                "peak_window": c_pstr,
                "source": c_curr.get("source", "Open-Meteo Live API" if c_curr.get("is_live", False) else "Demo Simulation"),
                "timestamp": c_curr.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M")),
                "is_live": c_curr.get("is_live", False),
            })

        render_city_map(city_conditions, {"occupation": occupation, "activity": activity, "duration": duration, "hour": now_hour})
    except Exception as e:
        st.warning(f"Map rendering in fallback mode: {e}")

    st.markdown("#### Hyperlocal Urban Micro-Zone Concept")
    st.caption("How micro-environments within the same city modify ambient thermal load.")
    mz1, mz2, mz3, mz4 = st.columns(4)
    zone_offsets = [
        ("City Center", 0.0, "Urban core / traffic"),
        ("Industrial Zone", 2.0, "Machinery & asphalt"),
        ("Residential Green", -1.0, "Tree canopy cover"),
        ("Open Construction", 2.5, "Direct sun / unshaded"),
    ]
    for col, (z_name, offset, z_desc) in zip([mz1, mz2, mz3, mz4], zone_offsets):
        with col:
            zt = current["temp_c"] + offset
            zr = compute_personalized_risk(zt, current["rh_percent"], occupation, activity, duration, now_hour)
            metric_card(z_name, f"{zt:.1f}°C", f"Risk: {zr.level} · {z_desc}")

# ======================================================================
# TAB 8: HEATWAVE WATCH (Phase 10 - Live Multi-Day Watch)
# ======================================================================
with tabs[7]:
    st.markdown("### 🌡️ Heatwave Watch (5-Day Outlook)")
    st.caption("Multi-day meteorological trend analysis. PROTOTYPE RISK ASSESSMENT — not an official government alert.")

    hw_status, hw_note = detect_heatwave_status(multiday_df)
    status_colors = {
        "NORMAL": "#2E7D32",
        "WATCH": "#F9A825",
        "WARNING": "#EF6C00",
        "SEVERE": "#B71C1C",
    }

    hw_top1, hw_top2 = st.columns([1, 2])
    with hw_top1:
        st.markdown(
            f"""
            <div class="ts-card" style="border-top: 5px solid {status_colors.get(hw_status, '#888')}; text-align:center;">
                <div class="ts-metric-label">Heatwave Watch Status</div>
                <div style="margin: 0.6rem 0;">
                    <span class="ts-badge" style="background:{status_colors.get(hw_status, '#888')}; font-size:1.2rem; padding:0.4rem 1.2rem;">
                        {hw_status}
                    </span>
                </div>
                <div class="ts-small">PROTOTYPE RISK ASSESSMENT</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hw_top2:
        st.info(f"**Synoptic Assessment:** {hw_note}")
        mean_t = multiday_df["max_temp_c"].mean()
        max_t = multiday_df["max_temp_c"].max()
        highest_day = multiday_df.loc[multiday_df["max_temp_c"].idxmax(), "date"]
        elevated_days = (multiday_df["max_temp_c"] - mean_t >= 2.0).sum()
        st.write(f"- **Highest-Risk Day:** `{highest_day}` ({max_t:.1f}°C)")
        st.write(f"- **Elevated-Risk Days in Forecast:** `{elevated_days}` of {len(multiday_df)} days")
        st.write(f"- **Period Baseline Average Max:** `{mean_t:.1f}°C`")

    st.markdown("#### 5-Day Thermal Exposure Progression")
    day_cols = st.columns(min(len(multiday_df), 5))
    day_labels = ["Today", "Tomorrow", "Day 3", "Day 4", "Day 5"]

    for idx, (col, (_, row)) in enumerate(zip(day_cols, multiday_df.iterrows())):
        with col:
            d_date = row["date"]
            d_max = row["max_temp_c"]
            d_min = row["min_temp_c"]
            d_rh = row["avg_rh"]
            d_label = day_labels[idx] if idx < len(day_labels) else f"Day {idx+1}"
            date_display = d_date.strftime("%a, %b %d") if hasattr(d_date, "strftime") else str(d_date)

            d_risk = compute_personalized_risk(d_max, d_rh, occupation, activity, duration, 14)

            st.markdown(
                f"""
                <div class="ts-card" style="border-top: 3px solid {d_risk.color}; text-align:center; padding:0.8rem 0.5rem;">
                    <div style="font-weight:700; font-size:0.9rem;">{d_label}</div>
                    <div style="font-size:0.75rem; opacity:0.75; margin-bottom:0.4rem;">{date_display}</div>
                    <div style="font-size:1.25rem; font-weight:800; color:{d_risk.color};">{d_max:.1f}°C</div>
                    <div style="font-size:0.75rem; opacity:0.7;">Low: {d_min:.0f}°C | RH: {d_rh:.0f}%</div>
                    <div style="margin-top:0.4rem;">
                        <span class="ts-badge" style="background:{d_risk.color}; font-size:0.75rem; padding:2px 8px;">
                            {d_risk.level}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.plotly_chart(
        multiday_heatwave_chart(multiday_df),
        width="stretch",
        key="heatwave_multiday_chart",
    )

# ======================================================================
# TAB 9: ORGANIZATION SAFETY MODE (Phase 11)
# ======================================================================
with tabs[8]:
    st.markdown("### 🏢 Organization Safety Mode")
    st.caption("Institutional decision support for construction sites, logistics teams, agricultural co-ops, and universities.")

    org_c1, org_c2, org_c3, org_c4 = st.columns(4)
    with org_c1:
        org_workers = st.number_input("Workers / Individuals Exposed", min_value=1, max_value=5000, value=35)
    with org_c2:
        org_occ = st.selectbox("Site Occupation Profile", OCCUPATIONS, index=0, key="org_occ_tab")
    with org_c3:
        org_act = st.select_slider("Predominant Activity", ACTIVITIES, value="Heavy", key="org_act_tab")
    with org_c4:
        org_dur = st.select_slider("Continuous Shift Duration", DURATIONS, value="3 hours", key="org_dur_tab")

    org_res = compute_personalized_risk(current["temp_c"], current["rh_percent"], org_occ, org_act, org_dur, now_hour)
    org_timeline = compute_hourly_risk_timeline(hourly_df, org_occ, org_act, org_dur)
    org_pk_start, org_pk_end = find_peak_risk_window(org_timeline)
    org_pk_str = format_datetime_window(org_pk_start, org_pk_end)

    st.markdown("---")
    st.markdown(f"#### 🏭 SITE HEAT STATUS — {city.upper()} INDUSTRIAL/OUTDOOR SECTOR")

    osc1, osc2, osc3, osc4 = st.columns(4)
    with osc1:
        metric_card("Exposed Personnel", f"{org_workers} workers")
    with osc2:
        st.markdown(
            f"""
            <div class="ts-card">
                <div class="ts-metric-label">Site Thermal Risk</div>
                <div style="margin-top:0.3rem;"><span class="ts-badge" style="background:{org_res.color};">{org_res.level}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with osc3:
        metric_card("Critical Peak Period", org_pk_str)
    with osc4:
        metric_card("Apparent Temp", f"{org_res.heat_index_c:.1f}°C")

    alert_card(
        f"Site Supervisor Advisory: {org_occ}",
        org_res.color,
        [
            f"<b>Primary Operational Directive:</b> {org_res.action}",
            f"<b>Shift Optimization:</b> {org_res.strategy}",
            f"<b>Hydration Requirement:</b> Mandatory 250ml water intake every 20 minutes under active heat stress.",
        ],
    )

    if org_res.level in ("VERY HIGH", "EXTREME"):
        st.error(
            "🚨 **ESCALATION RECOMMENDED:** Activate heat-stress safety protocols. "
            "Implement mandatory buddy-system monitoring for heat exhaustion signs, "
            "provide shaded electrolyte recovery stations, and shift strenuous heavy tasks away from the peak window."
        )

# ======================================================================
# TAB 10: METHODOLOGY & TRANSPARENCY (Scientific Grounding)
# ======================================================================
with tabs[9]:
    st.markdown("### 📚 Scientific Methodology & Honest AI Positioning")

    st.info(
        "**Honest Positioning:** ThermoShield AI is a human-centric thermal-risk decision-support platform "
        "that combines real-time weather data with transparent thermal calculations and exposure-aware risk analysis. "
        "The prototype does not fabricate machine learning accuracy scores; machine learning can be incorporated "
        "where genuine historical sensor data adds validated predictive power."
    )

    st.markdown("#### 1. Heat Index Calculation (NOAA / Rothfusz Equation)")
    st.write(
        "Air temperature and relative humidity are converted to the standard NOAA Heat Index "
        "using the complete Rothfusz multi-variate regression with low-humidity and high-humidity adjustments. "
        "Valid primarily above 27°C (80°F)."
    )

    st.markdown("#### 2. Wet Bulb Globe Temperature (WBGT) Estimation")
    st.write(
        "Formal WBGT requires dry-bulb, natural wet-bulb, and black-globe radiant thermometers: "
        "`WBGT = 0.7*Tw + 0.2*Tg + 0.1*Td`. Where radiant sensors are unavailable, "
        "this prototype applies the published Australian Bureau of Meteorology / Liljegren simplified estimate: "
        "`WBGT = 0.567*T + 0.393*e + 3.94`. "
        "It is explicitly labelled as **Estimated WBGT (no solar/wind sensor)** to maintain scientific integrity."
    )

    st.markdown("#### 3. Human Exposure Scoring Weights")
    st.write(
        "A composite score (0-100) is deterministically computed from: "
        "- Environmental Heat Component (0–45 points)\n"
        "- Activity Load Component (0–20 points)\n"
        "- Exposure Duration Component (0–15 points)\n"
        "- Occupation Setting Component (0–15 points)\n"
        "- Diurnal Time-of-Day Adjustment (-5 to +5 points)"
    )

    st.markdown("#### 4. Scope & Limitations")
    st.warning(
        "- **Decision-Support Prototype:** Not a clinical diagnostic tool or legal safety sign-off.\n"
        "- **No Sensor Input:** Real radiant solar load and individual acclimatization vary.\n"
        "- **Weather Uncertainty:** Live and demo forecasts carry natural meteorological margin of error."
    )
