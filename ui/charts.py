"""
charts.py
---------
Plotly figure builders used across the dashboard: the 12-24hr risk
timeline, the explainable risk-factor breakdown bar chart, and the
risk-history trend chart.
"""

import plotly.graph_objects as go
import pandas as pd

from calculations.thermal_risk import RISK_BANDS

LEVEL_COLOR = {label: color for label, _, _, color in RISK_BANDS}


def hourly_risk_timeline_chart(timeline_df: pd.DataFrame, peak_start=None, peak_end=None, low_start=None, low_end=None, now_time=None):
    fig = go.Figure()
    
    # 1. Personalized Thermal Exposure Score
    fig.add_trace(go.Scatter(
        x=timeline_df["time"], y=timeline_df["score"],
        mode="lines+markers",
        line=dict(width=3.5, color="#D84315"),
        marker=dict(
            size=7,
            color=[LEVEL_COLOR.get(lv, "#888") for lv in timeline_df["level"]],
            line=dict(width=1.5, color="#ffffff"),
        ),
        text=timeline_df["level"],
        hovertemplate="<b>%{x|%a %I:%M %p}</b><br>Thermal Risk Score: <b>%{y:.1f}/100</b><br>Category: <b>%{text}</b><br>Temp: %{customdata[0]:.1f}°C | RH: %{customdata[1]:.0f}%<extra></extra>",
        customdata=timeline_df[["temp_c", "rh_percent"]].values,
        name="Thermal Exposure Score",
    ))

    # Current Time vertical marker
    if now_time is not None:
        fig.add_vline(
            x=now_time,
            line_width=2, line_dash="dash", line_color="#0288D1",
            annotation_text="📍 Current Time", annotation_position="top left",
            annotation_font=dict(size=11, color="#0288D1", weight="bold"),
        )

    # Highlight Peak Risk Window (Red/Orange)
    if peak_start is not None and peak_end is not None:
        fig.add_vrect(
            x0=peak_start, x1=peak_end,
            fillcolor="#D84315", opacity=0.18, line_width=1.5, line_color="#D84315",
            annotation_text="⚠ Peak Risk Window", annotation_position="top right",
            annotation_font=dict(size=11, color="#D84315", weight="bold"),
        )

    # Highlight Recommended Lower-Exposure Window (Green)
    if low_start is not None and low_end is not None:
        fig.add_vrect(
            x0=low_start, x1=low_end,
            fillcolor="#2E7D32", opacity=0.15, line_width=1.5, line_color="#2E7D32",
            annotation_text="✓ Recommended Operational Window", annotation_position="bottom left",
            annotation_font=dict(size=11, color="#2E7D32", weight="bold"),
        )

    # Risk background bands
    for label, lo, hi, color in RISK_BANDS:
        fig.add_hrect(
            y0=lo, y1=hi, fillcolor=color, opacity=0.05, line_width=0,
            annotation_text=label, annotation_position="right",
            annotation_font=dict(size=9, color=color),
        )

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=45, t=30, b=10),
        yaxis=dict(title="Personalized Thermal Exposure Score (0-100)", range=[0, 105], gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(title="Forecast Hour", gridcolor="rgba(128,128,128,0.15)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def risk_breakdown_chart(breakdown: dict):
    """Horizontal bar chart for 'WHY THIS RISK?' with distinct categorical colors."""
    labels = list(breakdown.keys())
    values = list(breakdown.values())

    palette = {
        "Temperature": "#E65100",
        "Humidity": "#0288D1",
        "Activity": "#D84315",
        "Duration": "#8E24AA",
        "Occupation": "#3949AB",
        "Time of Day": "#FB8C00",
    }
    colors = [palette.get(k, "#EF6C00") for k in labels]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(width=1, color="rgba(255,255,255,0.4)")),
        text=[f"{v:.1f} pts" for v in values],
        textposition="outside",
        hovertemplate="<b>%{y}</b>: %{x:.1f} points<extra></extra>",
    ))
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(title="Factor Risk Contribution (pts)", range=[0, max(values + [20]) * 1.3], gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def comparison_bar_chart(res_a, res_b, name_a="Person A", name_b="Person B"):
    """Hero demonstration chart comparing Person A vs Person B under identical weather."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=name_a,
        x=["Thermal Score"],
        y=[res_a.score],
        marker_color=res_a.color,
        text=[f"{res_a.level} ({res_a.score:.1f}/100)"],
        textposition="outside",
        width=[0.35],
    ))
    fig.add_trace(go.Bar(
        name=name_b,
        x=["Thermal Score"],
        y=[res_b.score],
        marker_color=res_b.color,
        text=[f"{res_b.level} ({res_b.score:.1f}/100)"],
        textposition="outside",
        width=[0.35],
    ))
    fig.update_layout(
        barmode="group",
        height=300,
        yaxis=dict(title="Personalized Thermal Score (0-100)", range=[0, 110], gridcolor="rgba(128,128,128,0.15)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=25, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


def risk_history_chart(history_df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_df["Time"], y=history_df["Score"],
        mode="lines+markers",
        line=dict(width=2, color="#455A64"),
        marker=dict(color=[LEVEL_COLOR.get(lv, "#888") for lv in history_df["Risk"]], size=9),
        hovertext=history_df["Risk"],
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title="Score", range=[0, 100], gridcolor="rgba(128,128,128,0.15)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def multiday_heatwave_chart(multiday_df: pd.DataFrame):
    mean_max = multiday_df["max_temp_c"].mean()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=multiday_df["date"].astype(str), y=multiday_df["max_temp_c"],
        marker_color=["#B71C1C" if t - mean_max >= 4 else "#EF6C00" if t - mean_max >= 2 else "#F9A825" if t - mean_max >= 1 else "#2E7D32"
                      for t in multiday_df["max_temp_c"]],
        text=[f"{t:.1f}°C" for t in multiday_df["max_temp_c"]],
        textposition="outside",
        name="Max Temp (°C)",
        hovertemplate="<b>%{x}</b><br>Max Temp: <b>%{y:.1f}°C</b><extra></extra>",
    ))
    fig.add_hline(y=mean_max, line_dash="dash", line_color="#546E7A",
                   annotation_text=f"Baseline mean {mean_max:.1f}°C",
                   annotation_position="bottom right")
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Max Temperature (°C)", range=[0, max(multiday_df["max_temp_c"]) + 5], gridcolor="rgba(128,128,128,0.15)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
