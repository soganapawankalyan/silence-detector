import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

os.makedirs("outputs", exist_ok=True)

# Load all aggregations
by_rule = pd.read_csv("data/agg_by_rule.csv")
by_team_rule = pd.read_csv("data/agg_by_team_rule.csv")
by_dow = pd.read_csv("data/agg_by_dow.csv")
by_hour = pd.read_csv("data/agg_by_hour.csv")
by_category = pd.read_csv("data/agg_by_category.csv")
by_month = pd.read_csv("data/agg_by_month.csv")

COLORS = {
    "Team A": "#4C9BE8",
    "Team B": "#E8694C",
    "Team C": "#4CE8A0",
    "Team D": "#E8C44C",
}

# ── Chart 1: Violation rate by rule ──────────────────────────────────────────
fig1 = go.Figure()
by_rule_filtered = by_rule[by_rule["rule_id"] != "R05"]
fig1.add_trace(go.Bar(
    x=by_rule_filtered["rule_name"],
    y=by_rule_filtered["violation_rate_pct"],
    marker_color=["#E8694C" if v > 30 else "#4C9BE8" for v in by_rule_filtered["violation_rate_pct"]],
    text=[f"{v}%" for v in by_rule_filtered["violation_rate_pct"]],
    textposition="outside",
))
fig1.update_layout(
    title="SLA Violation Rate by Rule",
    xaxis_title="SLA Rule",
    yaxis_title="Violation Rate (%)",
    yaxis_range=[0, 65],
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=450,
)
fig1.update_xaxes(showgrid=False)
fig1.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
fig1.write_html("outputs/chart1_by_rule.html")
fig1.write_image("outputs/chart1_by_rule.png", scale=2)
print("Chart 1 saved")

# ── Chart 2: Team x Rule heatmap ─────────────────────────────────────────────
pivot = by_team_rule[by_team_rule["rule_id"] != "R05"].pivot(
    index="team", columns="rule_name", values="violation_rate_pct"
)
fig2 = go.Figure(data=go.Heatmap(
    z=pivot.values,
    x=[c.replace(" SLA", "") for c in pivot.columns],
    y=pivot.index.tolist(),
    colorscale="RdYlGn_r",
    text=[[f"{v:.0f}%" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    textfont={"size": 13},
    zmin=0, zmax=65,
))
fig2.update_layout(
    title="Violation Rate (%) by Team and Rule",
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=350,
)
fig2.write_html("outputs/chart2_team_rule_heatmap.html")
fig2.write_image("outputs/chart2_team_rule_heatmap.png", scale=2)
print("Chart 2 saved")

# ── Chart 3: Violations by hour of day ───────────────────────────────────────
fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x=by_hour["hour"],
    y=by_hour["violation_rate_pct"],
    marker_color=["#E8694C" if v >= 35 else "#4C9BE8" for v in by_hour["violation_rate_pct"]],
))
fig3.update_layout(
    title="SLA Violation Rate by Hour of Day",
    xaxis_title="Hour (24h)",
    yaxis_title="Violation Rate (%)",
    xaxis=dict(tickmode="linear", tick0=0, dtick=1),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=400,
)
fig3.update_xaxes(showgrid=False)
fig3.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
fig3.write_html("outputs/chart3_by_hour.html")
fig3.write_image("outputs/chart3_by_hour.png", scale=2)
print("Chart 3 saved")

# ── Chart 4: Monthly trend ────────────────────────────────────────────────────
by_month_filtered = by_month[by_month["month"] != "2024-07"]
fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=by_month_filtered["month"],
    y=by_month_filtered["violation_rate_pct"],
    mode="lines+markers+text",
    line=dict(color="#4C9BE8", width=2),
    marker=dict(size=8),
    text=[f"{v}%" for v in by_month_filtered["violation_rate_pct"]],
    textposition="top center",
))
fig4.update_layout(
    title="Monthly SLA Violation Rate Trend",
    xaxis_title="Month",
    yaxis_title="Violation Rate (%)",
    yaxis_range=[0, 50],
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=400,
)
fig4.update_xaxes(showgrid=False)
fig4.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
fig4.write_html("outputs/chart4_monthly_trend.html")
fig4.write_image("outputs/chart4_monthly_trend.png", scale=2)
print("Chart 4 saved")

# ── Chart 5: Violation rate by category ──────────────────────────────────────
fig5 = go.Figure()
fig5.add_trace(go.Bar(
    x=by_category["violation_rate_pct"],
    y=by_category["category"],
    orientation="h",
    marker_color=["#E8694C" if v > 32 else "#4C9BE8" for v in by_category["violation_rate_pct"]],
    text=[f"{v}%" for v in by_category["violation_rate_pct"]],
    textposition="outside",
))
fig5.update_layout(
    title="SLA Violation Rate by Ticket Category",
    xaxis_title="Violation Rate (%)",
    xaxis_range=[0, 50],
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(size=13),
    height=350,
)
fig5.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
fig5.update_yaxes(showgrid=False)
fig5.write_html("outputs/chart5_by_category.html")
fig5.write_image("outputs/chart5_by_category.png", scale=2)
print("Chart 5 saved")

print()
print("All charts saved to outputs/")
