"""
wbgt.py
-------
Estimated Wet Bulb Globe Temperature (WBGT) for OUTDOOR, sun-exposed
conditions, used by occupational-health bodies (ACGIH, OSHA, NIOSH,
Indian Institute of Tropical Meteorology heatwave advisories) as the
basis for work/rest and hydration guidance.

True WBGT requires three measured instruments:
    Tw  - natural wet-bulb temperature
    Tg  - black-globe temperature (solar radiant load)
    Td  - dry-bulb air temperature
    WBGT = 0.7*Tw + 0.2*Tg + 0.1*Td   (outdoor, sun)

This prototype does NOT have a wet-bulb or globe thermometer feed.
Instead it uses the widely published Australian Bureau of Meteorology /
Liljegren-style SIMPLIFIED WBGT ESTIMATE derived from dry-bulb
temperature and humidity (vapour pressure) alone:

    WBGT_estimate = 0.567*T + 0.393*e + 3.94

    where T = dry-bulb temp (C), e = water vapour pressure (hPa),
    e = (RH/100) * 6.105 * exp(17.27*T / (237.7+T))

This is a genuine, published approximation (Australian BoM apparent
temperature family) commonly used when globe-temperature data is
unavailable. It systematically UNDERSTATES true outdoor WBGT on
strongly sunny, low-wind days because it has no direct solar/wind term.

Per project requirements, every result from this module is labelled
"Estimated WBGT (no solar/wind sensor)" rather than claimed as an
official outdoor WBGT reading.
"""

import math
from dataclasses import dataclass


@dataclass
class WBGTResult:
    temp_c: float
    rh_percent: float
    vapour_pressure_hpa: float
    wbgt_estimate_c: float
    method: str
    note: str


def calculate_wbgt_estimate(temp_c: float, rh_percent: float) -> WBGTResult:
    rh_percent = max(0.0, min(100.0, rh_percent))
    e = (rh_percent / 100.0) * 6.105 * math.exp(
        (17.27 * temp_c) / (237.7 + temp_c)
    )
    wbgt = 0.567 * temp_c + 0.393 * e + 3.94

    return WBGTResult(
        temp_c=temp_c,
        rh_percent=rh_percent,
        vapour_pressure_hpa=round(e, 2),
        wbgt_estimate_c=round(wbgt, 1),
        method="simplified_humidity_based_estimate",
        note="Estimated WBGT derived from temperature and humidity only "
             "(no black-globe/solar or wind sensor available). Likely "
             "understates true outdoor WBGT on strong-sun, low-wind days. "
             "Labelled as 'Estimated WBGT', not an official reading.",
    )


# Published occupational WBGT action limits (deg C), unacclimatized worker,
# moderate work, commonly cited by ACGIH / IMD heat advisories -- used only
# as a reference band for the methodology page, NOT as the primary risk
# categorization (see thermal_risk.py for the engine's own thresholds).
WBGT_REFERENCE_BANDS = [
    ("Caution", 27.0, 29.0),
    ("Extreme Caution", 29.0, 31.0),
    ("Danger", 31.0, 33.0),
    ("Extreme Danger", 33.0, 99.0),
]
