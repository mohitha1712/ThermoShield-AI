# ThermoShield AI
### Human-Centric Heatwave Early Warning & Thermal Stress Intelligence
**Smart India Hackathon — Problem Statement SIH26083: Heatwave Early Warning & Human Thermal Stress Index**

> **Important Notice:** ThermoShield AI is a prototype decision-support and early-warning system, not a medical diagnostic system or official government warning service.

---

## 1. Project Title
**ThermoShield AI: Human-Centric Heatwave Early Warning & Thermal Stress Intelligence**

## 2. SIH Problem Statement
- **ID:** SIH26083
- **Title:** Heatwave Early Warning & Human Thermal Stress Index
- **Domain:** Disaster Management / Climate Health Intelligence

## 3. Problem
Conventional heat advisories report environmental weather alone:
```
Weather → Temperature / Humidity
```
However, standard ambient metrics fail to reflect individual human risk. A temperature of 38°C with 70% relative humidity affects a construction worker performing heavy physical labor for 3 hours very differently than an office worker exposed for 30 minutes in a ventilated setting. Conventional apps provide identical warnings regardless of human exposure vulnerability.

## 4. Proposed Solution
ThermoShield AI bridges meteorology and occupational physiology by translating raw environmental forecasts into **Personalized Thermal Stress Intelligence**:
```
Weather Data 
  → Thermal Analysis (Heat Index & Estimated WBGT)
  → Human Exposure Context (Occupation, Activity Intensity, Exposure Duration)
  → Thermal Exposure Risk Calculation (0–100 Score)
  → Peak-Risk Detection & Hourly Early Warning
  → Actionable, Traceable Safety Directives
```

## 5. Core Innovation: “SAME WEATHER, DIFFERENT RISK”
The defining demonstration of ThermoShield AI is:
> *“Nothing changed in the weather. We changed the human exposure.”*

- **Identical Environmental Conditions:** Chennai, 38°C, 70% RH
- **Person A (Construction Worker, Heavy Activity, 3 Hours):** Thermal Score **98/100 (EXTREME)** → Urgent escalation, mandatory cooling intervals.
- **Person B (Office Worker, Light Activity, 30 Minutes):** Thermal Score **62/100 (HIGH/MODERATE)** → Standard routine hydration.

## 6. Features
1. **Executive Overview Banner:** Immediate first-screen communication of Current Thermal Risk, Peak-Risk Window, Thermal Index, and Top Recommended Action.
2. **Current Risk Engine:** Deep evaluation of composite thermal strain, NOAA Heat Index, and BoM estimated WBGT.
3. **“Why Am I At Risk?” Explainability:** Deterministic, traceable breakdown attributing points to Temperature, Humidity, Activity, Duration, Occupation, and Diurnal Sun Exposure.
4. **12–24 Hour Early Warning Timeline:** Plotly timeline identifying the dynamic Peak-Risk Window and Recommended Lower-Exposure Window.
5. **“Best Time to Work” Scheduler:** Automatically scans forecast windows to find continuous lower-risk periods for demanding outdoor activities.
6. **Hero Live Comparison:** Interactive side-by-side comparison of two individuals under identical microclimate conditions.
7. **Prototype Thermal Risk Map:** Multi-city interactive Folium geospatial visualization across Tamil Nadu and major Indian metropolitan regions.
8. **Heatwave Watch (5-Day Outlook):** Prototype synoptic assessment classifying trends into NORMAL, WATCH, WARNING, and SEVERE.
9. **Organization Safety Mode:** Workplace site-safety dashboard with worker headcount, peak exposure periods, and supervisor protocols.
10. **Dual Mode Reliability (Live + Offline):** Seamless operation via Open-Meteo live API, with automated graceful fallback to synthetic offline data during network interruptions.

## 7. Architecture
```
┌────────────────────────────────────────────────────────┐
│                      Streamlit UI                      │
│   (Overview, Why Risk?, Scheduler, Hero Demo, Map)     │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                    models/risk_engine.py               │
│     (Pipeline Orchestrator, Timeline & Schedulers)     │
└─────────────▲────────────────────────────▲─────────────┘
              │                            │
┌─────────────┴──────────────┐ ┌───────────┴─────────────┐
│    calculations/           │ │     services/           │
│  • exposure_model.py       │ │  • weather_api.py       │
│  • heat_index.py           │ │    (Live Open-Meteo)    │
│  • wbgt.py                 │ │  • fallback_weather.py  │
│  • thermal_risk.py         │ │    (100% Offline Demo)  │
└────────────────────────────┘ └─────────────────────────┘
```

## 8. Thermal Methodology
- **NOAA / Rothfusz Heat Index:** Computes apparent temperature in shade and light wind from dry-bulb temperature and relative humidity:
  $$\text{HI} = -42.379 + 2.04901523 T + 10.14333127 R - 0.22475541 T R - \dots$$
- **Estimated Wet Bulb Globe Temperature (WBGT):** True outdoor WBGT requires natural wet-bulb ($T_w$) and black-globe radiant ($T_g$) sensors: $\text{WBGT} = 0.7 T_w + 0.2 T_g + 0.1 T_d$. Where direct radiant instruments are unavailable, the system uses the published Australian BoM / Liljegren simplified estimate:
  $$\text{WBGT}_{\text{est}} = 0.567 T + 0.393 e + 3.94$$
  where $e$ is water vapor pressure (hPa). This is explicitly labeled as **Estimated WBGT (no solar/wind sensor)** to maintain scientific integrity.

## 9. Human Exposure Model
Personalized Thermal Exposure Score ($0 \le S \le 100$) is computed additively:
$$\text{Score} = \text{clamp}\Big(\text{EnvHeat}(0\text{--}45) + \text{Activity}(0\text{--}20) + \text{Duration}(0\text{--}15) + \text{Occupation}(0\text{--}15) + \text{TimeOfDay}(-5\text{ to }+5), 0, 100\Big)$$

- **Risk Categories:**
  - **LOW (0–29):** Normal precautions, routine hydration.
  - **MODERATE (30–49):** Discomfort onset, increase fluid intake.
  - **HIGH (50–67):** Significant strain, frequent shaded rest intervals.
  - **VERY HIGH (68–84):** Substantial physiological burden, curtail continuous exposure.
  - **EXTREME (85–100):** Urgent thermal risk, cancel or reschedule non-essential outdoor work.

## 10. Early Warning Mechanism
Rather than relying on fixed arbitrary hours, the engine scans the 24-hour diurnal profile dynamically. It centers the **Peak-Risk Window** around the diurnal maximum and determines contiguous hours where risk is elevated. Conversely, it calculates the **Recommended Lower-Exposure Window** by identifying the minimum average stress period capable of accommodating the planned duration.

## 11. Technology Stack
- **Core Language:** Python 3.11+
- **Frontend / Dashboard:** Streamlit 1.36+
- **Data Manipulation:** Pandas 2.2+, NumPy 1.26+
- **Visualization:** Plotly 5.22+
- **Geospatial Mapping:** Folium 0.16+, Streamlit-Folium 0.22+
- **Networking:** Requests 2.31+ (Open-Meteo Live API)

## 12. Installation
### Windows (PowerShell)
```powershell
cd d:\Projects\SIH26083_Heatwave_Early_Warning
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux
```bash
cd SIH26083_Heatwave_Early_Warning
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 13. Running the Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

## 14. Demo Mode & Live Fallback
- **DEMO MODE:** Uses offline diurnal simulation curves (`services/fallback_weather.py`) tailored to major Indian cities. Requires **zero internet connection** and zero API keys.
- **LIVE MODE:** Connects dynamically to Open-Meteo free endpoints. If network requests time out, fail, or drop offline, ThermoShield AI automatically falls back to demo simulation and displays:
  > *“Live weather unavailable — showing demo data.”*

## 15. Limitations
1. **Decision Support Only:** Not a medical diagnostic instrument or legal safety clearance.
2. **Individual Variability:** Pre-existing health conditions, hydration baseline, and acclimatization vary across individuals.
3. **No Direct Globe Sensor:** WBGT is a simplified mathematical estimate derived from humidity and temperature, not an official black-globe radiant measurement.
4. **Forecast Uncertainty:** Numerical weather forecasts contain standard meteorological deviations.

## 16. Future Scope
- Hardware integration with IoT micro-weather stations (ESP32 + BME280 + Black Globe sensor).
- Satellite Land Surface Temperature (LST) and Urban Heat Island (UHI) micro-zone downscaling.
- Integration with wearable biometric monitors (heart rate and skin temperature telemetry).
- Automated SMS/WhatsApp safety alerts in regional languages (Tamil, Hindi, Telugu).
