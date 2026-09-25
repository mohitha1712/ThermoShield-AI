"""
map.py
------
Renders the "Prototype Thermal Risk Map" across multiple cities using
Folium. Each marker is colored by that city's current personalized risk
(computed with a fixed reference profile so cities are comparable), and
a popup shows the peak-risk window for that city.
"""

import folium
from streamlit_folium import st_folium

from calculations.thermal_risk import RISK_BANDS
from models.risk_engine import compute_personalized_risk

LEVEL_COLOR = {label: color for label, _, _, color in RISK_BANDS}


def build_city_map(city_conditions: list, reference_profile: dict):
    """
    city_conditions: list of dicts with keys city, temp_c, rh_percent, lat, lon, peak_window (str)
    reference_profile: dict with occupation/activity/duration used so all
        cities are compared on an identical human-exposure basis.
    """
    if not city_conditions:
        center = [13.0, 78.5]
    else:
        valid_lats = [c["lat"] for c in city_conditions if c.get("lat") is not None]
        valid_lons = [c["lon"] for c in city_conditions if c.get("lon") is not None]
        center = [
            sum(valid_lats) / len(valid_lats) if valid_lats else 13.0,
            sum(valid_lons) / len(valid_lons) if valid_lons else 78.5,
        ]

    fmap = folium.Map(location=center, zoom_start=6, tiles="OpenStreetMap")

    for c in city_conditions:
        temp_c = c.get("temp_c", 35.0)
        rh = c.get("rh_percent", 50.0)
        lat = c.get("lat", 13.08)
        lon = c.get("lon", 80.27)
        
        result = compute_personalized_risk(
            temp_c, rh,
            reference_profile.get("occupation", "Construction Worker"),
            reference_profile.get("activity", "Heavy"),
            reference_profile.get("duration", "3 hours"),
            reference_profile.get("hour", 13),
        )
        color = LEVEL_COLOR.get(result.level, "#888")
        
        source_label = c.get("source", "Live Weather API" if c.get("is_live", True) else "Demo Simulation")
        time_label = c.get("timestamp", "Current")

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:200px; padding:4px;">
            <div style="font-size:14px; font-weight:700; margin-bottom:4px;">📍 {c.get('city', 'Location')}</div>
            <div style="margin-bottom:6px;">
                <span style="background:{color}; color:white; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:700;">
                    {result.level} ({result.score:.1f}/100)
                </span>
            </div>
            <div style="font-size:12px; line-height:1.45; color:#333;">
                <b>Temp:</b> {temp_c:.1f}°C &nbsp;|&nbsp; <b>RH:</b> {rh:.0f}%<br>
                <b>Heat Index:</b> {result.heat_index_c:.1f}°C<br>
                <b>Est. WBGT:</b> {result.wbgt_estimate_c:.1f}°C<br>
                <b>Peak Window:</b> {c.get('peak_window', 'N/A')}<br>
                <span style="font-size:10px; opacity:0.8; color:#666;">
                    <b>Source:</b> {source_label}<br>
                    <b>Time:</b> {time_label}
                </span>
            </div>
        </div>
        """
        folium.CircleMarker(
            location=[lat, lon],
            radius=12,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{c.get('city', '')}: {result.level} ({result.score:.1f})",
        ).add_to(fmap)

    return fmap


def render_city_map(city_conditions: list, reference_profile: dict):
    fmap = build_city_map(city_conditions, reference_profile)
    st_folium(fmap, use_container_width=True, height=440, returned_objects=[])
