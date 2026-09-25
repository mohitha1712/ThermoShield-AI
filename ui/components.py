"""
components.py
--------------
Small reusable Streamlit UI helpers: CSS injection, risk badges, metric
cards, alert cards. Keeping these in one place gives the whole app a
consistent "climate-health dashboard" look instead of default Streamlit
styling.
"""

import streamlit as st


def inject_global_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .block-container { 
            padding-top: 1.2rem; 
            padding-bottom: 2rem;
            max-width: 1250px; 
        }
        
        /* Modern Cards */
        .ts-card {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(140, 140, 140, 0.16);
            border-radius: 12px;
            padding: 1.1rem 1.3rem;
            margin-bottom: 0.8rem;
            backdrop-filter: blur(8px);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .ts-card:hover {
            border-color: rgba(230, 81, 0, 0.4);
        }
        
        /* Executive Header Banner */
        .ts-exec-banner {
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: linear-gradient(135deg, rgba(30, 34, 45, 0.85) 0%, rgba(20, 24, 33, 0.95) 100%);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }
        
        .ts-badge {
            display: inline-block;
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.95rem;
            color: white !important;
            letter-spacing: 0.03em;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }
        
        .ts-source-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            background: rgba(120, 120, 120, 0.15);
            border: 1px solid rgba(120, 120, 120, 0.25);
        }
        
        .ts-metric-label { 
            font-size: 0.82rem; 
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.75; 
            margin-bottom: 0.2rem;
        }
        
        .ts-metric-value { 
            font-size: 1.7rem; 
            font-weight: 700; 
            letter-spacing: -0.02em;
        }
        
        .ts-alert {
            border-radius: 12px;
            padding: 1.1rem 1.4rem;
            border-left: 6px solid;
            margin-top: 0.6rem;
            margin-bottom: 0.9rem;
        }
        
        .ts-notice-box {
            background: rgba(245, 124, 0, 0.1);
            border: 1px solid rgba(245, 124, 0, 0.3);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            font-size: 0.85rem;
            color: #f57c00;
            margin-bottom: 0.8rem;
        }

        .ts-comparison-box {
            border-radius: 12px;
            padding: 1.2rem;
            border: 2px solid;
            background: rgba(255, 255, 255, 0.03);
            margin-top: 0.5rem;
        }

        .ts-small { font-size: 0.82rem; opacity: 0.75; margin-top: 0.2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(level: str, color: str) -> str:
    return f'<span class="ts-badge" style="background:{color}">{level}</span>'


def render_risk_badge(level: str, color: str):
    st.markdown(risk_badge(level, color), unsafe_allow_html=True)


def source_tag(source_label: str, is_live: bool):
    icon = "🟢" if is_live else "🟡"
    st.markdown(
        f'<span class="ts-source-tag">{icon} {source_label}</span>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, help_text: str = ""):
    st.markdown(
        f"""
        <div class="ts-card">
            <div class="ts-metric-label">{label}</div>
            <div class="ts-metric-value">{value}</div>
            {f'<div class="ts-small">{help_text}</div>' if help_text else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def executive_summary_bar(risk_level: str, risk_color: str, peak_window: str, heat_index_c: float, wbgt_c: float, top_action: str):
    """Communicates the 4 essential thermal safety parameters immediately on the first screen:
    1. CURRENT THERMAL RISK
    2. PEAK-RISK WINDOW
    3. THERMAL INDEX
    4. TOP RECOMMENDED ACTION
    """
    st.markdown(
        f"""
        <div class="ts-exec-banner" style="border-left: 6px solid {risk_color};">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.2rem; align-items: start;">
                <div>
                    <div class="ts-metric-label">1. Current Thermal Risk</div>
                    <div style="margin-top: 0.35rem;">
                        <span class="ts-badge" style="background:{risk_color}; font-size: 1.1rem; padding: 0.4rem 1.1rem;">
                            {risk_level}
                        </span>
                    </div>
                </div>
                <div>
                    <div class="ts-metric-label">2. Peak-Risk Window</div>
                    <div style="font-size: 1.35rem; font-weight: 700; color: #ffab91; margin-top: 0.3rem;">
                        {peak_window}
                    </div>
                </div>
                <div>
                    <div class="ts-metric-label">3. Thermal Indices</div>
                    <div style="font-size: 1.35rem; font-weight: 700; margin-top: 0.3rem;">
                        {heat_index_c:.1f}°C <span style="font-size:0.85rem; opacity:0.75; font-weight:500;">(Heat Index)</span>
                    </div>
                    <div class="ts-small">Est. WBGT: {wbgt_c:.1f}°C</div>
                </div>
                <div>
                    <div class="ts-metric-label">4. Top Recommended Action</div>
                    <div style="font-size: 0.95rem; font-weight: 600; line-height: 1.35; margin-top: 0.3rem;">
                        {top_action}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert_card(title: str, color: str, lines: list):
    body = "".join(f"<div style='margin-bottom:0.25rem;'>{line}</div>" for line in lines)
    st.markdown(
        f"""
        <div class="ts-alert" style="border-color:{color}; background:{color}18;">
            <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.4rem; color:{color};">{title}</div>
            <div style="font-size:0.92rem; line-height:1.45;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_freshness_status(is_live: bool, source: str, updated: str, forecast_range: str, is_fallback: bool = False):
    """Clear data freshness and source provenance display."""
    if is_live and not is_fallback:
        badge_html = '<span style="background:#2E7D32; color:white; padding:4px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; letter-spacing:0.04em;">🟢 LIVE DATA</span>'
        border_color = "rgba(46, 125, 50, 0.4)"
        bg = "rgba(46, 125, 50, 0.08)"
    else:
        status_text = "⚠️ LIVE DATA UNAVAILABLE · Using DEMO FALLBACK" if is_fallback else "🟡 DEMO DATA (Offline Simulation)"
        badge_html = f'<span style="background:#F57C00; color:white; padding:4px 12px; border-radius:12px; font-weight:700; font-size:0.8rem; letter-spacing:0.04em;">{status_text}</span>'
        border_color = "rgba(245, 124, 0, 0.4)"
        bg = "rgba(245, 124, 0, 0.08)"

    st.markdown(
        f"""
        <div style="background:{bg}; border:1px solid {border_color}; border-radius:10px; padding:0.75rem 1.2rem; margin-bottom:1rem; display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:0.8rem;">
            <div>{badge_html}</div>
            <div style="font-size:0.85rem;"><b>Source:</b> {source}</div>
            <div style="font-size:0.85rem;"><b>Updated:</b> {updated}</div>
            <div style="font-size:0.85rem;"><b>Forecast Range:</b> {forecast_range}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def current_exposure_advisory_card(level: str, color: str, why_summary: str, peak_period_str: str, recommended_action: str):
    """Concise decision-support card using live conditions."""
    st.markdown(
        f"""
        <div class="ts-card" style="border-left: 6px solid {color}; background: rgba(255,255,255,0.03); margin-top: 0.6rem; margin-bottom: 1rem;">
            <div style="font-size:0.82rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:700; color:{color}; margin-bottom:0.6rem;">
                CURRENT EXPOSURE ADVISORY (REAL-TIME DECISION SUPPORT)
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.2rem; align-items:start;">
                <div>
                    <div class="ts-metric-label">Current Thermal Risk:</div>
                    <div style="margin-top:0.3rem;">
                        <span class="ts-badge" style="background:{color}; font-size:1.05rem; padding:0.35rem 1rem;">{level}</span>
                    </div>
                </div>
                <div>
                    <div class="ts-metric-label">Why:</div>
                    <div style="font-size:0.95rem; font-weight:600; margin-top:0.3rem; line-height:1.4;">{why_summary}</div>
                </div>
                <div>
                    <div class="ts-metric-label">Next Peak-Risk Period:</div>
                    <div style="font-size:1.1rem; font-weight:700; color:#ffab91; margin-top:0.3rem;">{peak_period_str}</div>
                </div>
                <div>
                    <div class="ts-metric-label">Recommended Action:</div>
                    <div style="font-size:0.92rem; font-weight:600; margin-top:0.3rem; line-height:1.4;">{recommended_action}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
