"""
fallback_weather.py
--------------------
DEMO MODE data source. Provides realistic, clearly-labelled synthetic
weather so the application is fully demoable with zero internet
connectivity and zero API keys.

Data is generated deterministically (seeded) from a simple diurnal
temperature/humidity curve per city, so results are stable across runs
within a session but still look like a real day's weather.
"""

import math
from datetime import datetime, timedelta
import pandas as pd

# Base daytime peak temp / humidity per city (approximate, plausible
# April-June values for demonstration only -- NOT official observations).
CITY_PROFILES = {
    "Chennai":        {"base_temp": 33, "peak_temp": 41, "base_rh": 55, "min_rh": 40, "lat": 13.0827, "lon": 80.2707},
    "Kanchipuram":     {"base_temp": 32, "peak_temp": 42, "base_rh": 50, "min_rh": 35, "lat": 12.8342, "lon": 79.7036},
    "Chengalpattu":    {"base_temp": 32, "peak_temp": 41, "base_rh": 52, "min_rh": 38, "lat": 12.6819, "lon": 79.9888},
    "Madurai":         {"base_temp": 33, "peak_temp": 42, "base_rh": 45, "min_rh": 30, "lat": 9.9252,  "lon": 78.1198},
    "Coimbatore":      {"base_temp": 30, "peak_temp": 37, "base_rh": 48, "min_rh": 35, "lat": 11.0168, "lon": 76.9558},
    "Tiruchirappalli": {"base_temp": 32, "peak_temp": 43, "base_rh": 42, "min_rh": 28, "lat": 10.7905, "lon": 78.7047},
    "Trichy":          {"base_temp": 32, "peak_temp": 43, "base_rh": 42, "min_rh": 28, "lat": 10.7905, "lon": 78.7047},
    "Bengaluru":       {"base_temp": 27, "peak_temp": 34, "base_rh": 50, "min_rh": 35, "lat": 12.9716, "lon": 77.5946},
    "Hyderabad":       {"base_temp": 30, "peak_temp": 40, "base_rh": 40, "min_rh": 25, "lat": 17.3850, "lon": 78.4867},
    "Delhi":           {"base_temp": 32, "peak_temp": 45, "base_rh": 35, "min_rh": 15, "lat": 28.6139, "lon": 77.2090},
}


def _diurnal_temp(hour: float, base: float, peak: float) -> float:
    """Smooth diurnal curve: minimum around 03:00-04:00, maximum around
    14:00. `base` is treated as the pre-dawn low, `peak` as the afternoon
    high (a realistic day/night swing rather than a flat overnight floor)."""
    night_min = base - 5.0
    day_max = peak
    mid = (night_min + day_max) / 2.0
    amp = (day_max - night_min) / 2.0
    return mid + amp * math.cos(2 * math.pi * (hour - 14) / 24.0)


def _diurnal_rh(hour: float, base_rh: float, min_rh: float) -> float:
    """Humidity inversely tracks temperature: highest overnight, lowest
    at the afternoon temperature peak."""
    night_max_rh = min(100.0, base_rh + 15.0)
    day_min_rh = min_rh
    mid = (night_max_rh + day_min_rh) / 2.0
    amp = (night_max_rh - day_min_rh) / 2.0
    return mid - amp * math.cos(2 * math.pi * (hour - 14) / 24.0)


def get_demo_current(city: str) -> dict:
    profile = CITY_PROFILES.get(city, CITY_PROFILES["Chennai"])
    now = datetime.now()
    hour = now.hour + now.minute / 60.0
    temp = round(_diurnal_temp(hour, profile["base_temp"], profile["peak_temp"]), 1)
    rh = round(_diurnal_rh(hour, profile["base_rh"], profile["min_rh"]), 1)
    return {
        "city": city,
        "temp_c": temp,
        "rh_percent": rh,
        "wind_kmh": 12.0,
        "timestamp": now.strftime("%Y-%m-%d %H:%M"),
        "source": "Demo Simulation",
        "lat": profile["lat"],
        "lon": profile["lon"],
    }


def get_demo_hourly(city: str, hours: int = 24) -> pd.DataFrame:
    profile = CITY_PROFILES.get(city, CITY_PROFILES["Chennai"])
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    rows = []
    for i in range(hours):
        t = now + timedelta(hours=i)
        h = t.hour
        temp = round(_diurnal_temp(h, profile["base_temp"], profile["peak_temp"]), 1)
        rh = round(_diurnal_rh(h, profile["base_rh"], profile["min_rh"]), 1)
        rows.append({"time": t, "temp_c": temp, "rh_percent": rh, "wind_kmh": 10 + (i % 5)})
    return pd.DataFrame(rows)


def get_demo_multiday(city: str, days: int = 5) -> pd.DataFrame:
    """Multi-day demo forecast used by the Heatwave Watch layer. Injects
    a mild warming trend then a brief heatwave spike so the detector has
    something real to find in the demo."""
    profile = CITY_PROFILES.get(city, CITY_PROFILES["Chennai"])
    today = datetime.now().date()
    rows = []
    for d in range(days):
        date = today + timedelta(days=d)
        # Warming trend with a heatwave bump on days 2-3
        bump = 0
        if d in (2, 3):
            bump = 3.5
        elif d == 4:
            bump = 1.5
        peak = profile["peak_temp"] + bump
        rows.append({
            "date": date,
            "max_temp_c": round(peak, 1),
            "min_temp_c": round(profile["base_temp"] - 4, 1),
            "avg_rh": profile["base_rh"],
        })
    return pd.DataFrame(rows)


def list_cities():
    return [
        "Chennai",
        "Kanchipuram",
        "Chengalpattu",
        "Madurai",
        "Coimbatore",
        "Trichy",
        "Bengaluru",
        "Hyderabad",
        "Delhi",
    ]
