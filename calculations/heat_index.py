"""
heat_index.py
--------------
Computes the NOAA / Rothfusz Heat Index (apparent temperature) from
air temperature and relative humidity.

Reference:
Rothfusz, L.P. (1990). "The Heat Index Equation". NWS Southern Region
Technical Attachment SR 90-23, National Weather Service.

This is the SAME formula used by the U.S. National Weather Service to
produce the "feels like" temperature on heat advisories. It is valid
primarily for temperatures >= 27 deg C (80 deg F) and RH >= 40%. Outside
that range, the module returns a simple heat-index approximation
(the raw air temperature adjusted only slightly) and flags the result
as "extrapolated" so the UI can be transparent about it.

IMPORTANT (per project scope): Heat Index is NOT the same as WBGT.
Heat Index assumes shade and light wind; it does not account for solar
radiation load. See wbgt.py for the outdoor estimate and its caveats.
"""

from dataclasses import dataclass


@dataclass
class HeatIndexResult:
    temp_c: float
    rh_percent: float
    heat_index_c: float
    heat_index_f: float
    method: str  # "rothfusz_full" or "simple_approximation"
    note: str


def c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def calculate_heat_index(temp_c: float, rh_percent: float) -> HeatIndexResult:
    """
    Calculate the NOAA Heat Index.

    Args:
        temp_c: Dry-bulb air temperature in Celsius.
        rh_percent: Relative humidity in percent (0-100).

    Returns:
        HeatIndexResult with heat index in C and F, and the method used.
    """
    rh_percent = max(0.0, min(100.0, rh_percent))
    T = c_to_f(temp_c)  # Rothfusz regression is defined in Fahrenheit
    R = rh_percent

    # Simple approximation (Steadman-style average), used as a first pass
    # and as the fallback for conditions outside the full regression's
    # valid range.
    hi_simple = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (R * 0.094))

    if (hi_simple + T) / 2.0 < 80.0:
        # Full regression not appropriate; conditions are not hot enough
        # for meaningful heat-stress amplification.
        return HeatIndexResult(
            temp_c=temp_c,
            rh_percent=rh_percent,
            heat_index_c=round(f_to_c(hi_simple), 1),
            heat_index_f=round(hi_simple, 1),
            method="simple_approximation",
            note="Conditions below the Heat Index regression's valid range "
                 "(approx. < 27C). Simple approximation used.",
        )

    # Full Rothfusz regression (valid roughly T>=80F, RH>=40%)
    HI = (
        -42.379
        + 2.04901523 * T
        + 10.14333127 * R
        - 0.22475541 * T * R
        - 0.00683783 * T * T
        - 0.05481717 * R * R
        + 0.00122874 * T * T * R
        + 0.00085282 * T * R * R
        - 0.00000199 * T * T * R * R
    )

    # Adjustments per NWS guidance
    if R < 13 and 80 <= T <= 112:
        adjustment = ((13 - R) / 4.0) * ((17 - abs(T - 95.0)) / 17.0) ** 0.5
        HI -= adjustment
    elif R > 85 and 80 <= T <= 87:
        adjustment = ((R - 85) / 10.0) * ((87 - T) / 5.0)
        HI += adjustment

    return HeatIndexResult(
        temp_c=temp_c,
        rh_percent=rh_percent,
        heat_index_c=round(f_to_c(HI), 1),
        heat_index_f=round(HI, 1),
        method="rothfusz_full",
        note="Full NOAA/Rothfusz regression applied (shade, light-wind "
             "assumption; does not include direct solar load).",
    )
