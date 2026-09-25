"""
weather_api.py
--------------
LIVE MODE weather abstraction with persistent session and automatic retries.

Uses the free Open-Meteo API (https://open-meteo.com) with proper session headers
and exponential backoff to ensure reliable real-time weather retrieval without API keys.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import pandas as pd
from services.fallback_weather import CITY_PROFILES, get_demo_current

BASE_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 7

# Shared persistent session with retry logic and standard browser headers
_session = requests.Session()
_retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})


class WeatherAPIError(Exception):
    pass


def _city_coords(city: str):
    profile = CITY_PROFILES.get(city)
    if not profile:
        raise WeatherAPIError(f"Unknown location: {city}")
    return profile["lat"], profile["lon"]


def get_current_weather(city: str) -> dict:
    lat, lon = _city_coords(city)
    try:
        resp = _session.get(
            BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,apparent_temperature",
                "timezone": "auto",
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        cur = data["current"]
        return {
            "city": city,
            "temp_c": float(cur["temperature_2m"]),
            "rh_percent": float(cur["relative_humidity_2m"]),
            "wind_kmh": float(cur.get("wind_speed_10m", 0)),
            "apparent_temp_c": cur.get("apparent_temperature"),
            "timestamp": cur["time"].replace("T", " "),
            "source": "Open-Meteo Live API",
            "lat": lat,
            "lon": lon,
            "is_live": True,
        }
    except Exception as exc:
        raise WeatherAPIError(str(exc)) from exc


def get_hourly_forecast(city: str, hours: int = 24) -> pd.DataFrame:
    lat, lon = _city_coords(city)
    try:
        resp = _session.get(
            BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                "forecast_days": 3,
                "timezone": "auto",
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        hourly = data["hourly"]
        df = pd.DataFrame({
            "time": pd.to_datetime(hourly["time"]),
            "temp_c": hourly["temperature_2m"],
            "rh_percent": hourly["relative_humidity_2m"],
            "wind_kmh": hourly["wind_speed_10m"],
        })
        
        # Match starting time with current forecast hour
        cur_time_str = data.get("current", {}).get("time")
        if cur_time_str:
            cur_time = pd.to_datetime(cur_time_str)
        else:
            cur_time = pd.Timestamp(datetime.now())
            
        future_df = df[df["time"] >= cur_time.floor("h")].head(hours).reset_index(drop=True)
        if future_df.empty:
            future_df = df.head(hours).reset_index(drop=True)
        return future_df
    except Exception as exc:
        raise WeatherAPIError(str(exc)) from exc


def get_daily_forecast(city: str, days: int = 5) -> pd.DataFrame:
    lat, lon = _city_coords(city)
    try:
        resp = _session.get(
            BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean",
                "forecast_days": days,
                "timezone": "auto",
            },
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        daily = data["daily"]
        df = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]).date,
            "max_temp_c": daily["temperature_2m_max"],
            "min_temp_c": daily["temperature_2m_min"],
            "avg_rh": daily.get("relative_humidity_2m_mean", [50] * len(daily["time"])),
        })
        return df
    except Exception as exc:
        raise WeatherAPIError(str(exc)) from exc


def get_multi_city_weather(cities: list) -> list:
    """Batch-fetches current live weather for multiple cities in a single HTTP request."""
    valid_cities = [c for c in cities if c in CITY_PROFILES]
    if not valid_cities:
        return []

    lats = [CITY_PROFILES[c]["lat"] for c in valid_cities]
    lons = [CITY_PROFILES[c]["lon"] for c in valid_cities]

    try:
        resp = _session.get(
            BASE_URL,
            params={
                "latitude": lats,
                "longitude": lons,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=TIMEOUT_SECONDS + 2,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        # When querying multiple locations, Open-Meteo returns a list of results
        items = data if isinstance(data, list) else [data]
        for c_name, item in zip(valid_cities, items):
            cur = item.get("current", {})
            results.append({
                "city": c_name,
                "temp_c": float(cur.get("temperature_2m", CITY_PROFILES[c_name]["base_temp"])),
                "rh_percent": float(cur.get("relative_humidity_2m", CITY_PROFILES[c_name]["base_rh"])),
                "wind_kmh": float(cur.get("wind_speed_10m", 12.0)),
                "lat": CITY_PROFILES[c_name]["lat"],
                "lon": CITY_PROFILES[c_name]["lon"],
                "timestamp": cur.get("time", "").replace("T", " "),
                "is_live": True,
                "source": "Open-Meteo Live API",
            })
        return results
    except Exception:
        # Fallback to local demo data for each city if batch network call fails
        fallback_results = []
        for c_name in valid_cities:
            demo_c = get_demo_current(c_name)
            demo_c["is_live"] = False
            demo_c["source"] = "Demo Simulation (Fallback)"
            fallback_results.append(demo_c)
        return fallback_results
