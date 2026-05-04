import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="Silence Detector",
    page_icon="🔇",
    layout="wide"
)

@st.cache_data
def load_data():
    violations = pd.read_csv("data/violations.csv", parse_dates=["trigger_time", "response_time"])
    by_rule = pd.read_csv("data/agg_by_rule.csv")
    by_team_rule = pd.read_csv("data/agg_by_team_rule.csv")
    by_dow = pd.read_csv("data/agg_by_dow.csv")
    by_hour = pd.read_csv("data/agg_by_hour.csv")
    by_category = pd.read_csv("data/agg_by_category.csv")
    by_month = pd.read_csv("data/agg_by_month.csv")
    return violations, by_rule, by_team_rule, by_dow, by_hour, by_category, by_month

violations, by_rule, by_team_rule, by_dow, by_hour, by_category, by_month = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.title("Filters")
selected_teams = st.sidebar.multiselect(
    "Teams", options=sorted(violations["team"].unique()), default=sorted(violations["team"].unique())
)
selected_categories = st.sidebar.multiselect(
    "Categories", options=sorted(violations["category"].unique()), default=sorted(violations["category"].unique())
)
selected_rules = st.sidebar.multiselect(
    "SLA Rules", options=sorted(violations["rule_id"].unique()), default=["R01","R02","R03","R04"]
)

filtered = violations[
    violations["team"].isin(selected_teams) &
    violations["category"].isin(selected_categories) &
    violations["rule_id"].isin(selected_rules)
]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔇 Silence Detector")
st.markdown("**Finds SLA violations — events that should have happened, but didn't — across 500 support tickets.**")
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
total = len(filtered)
violated = int(filtered["is_violation"].sum())
violation_rate = round(100 * violated / total, 1) if total > 0 else 0
avg_overdue = round(filtered[filtered["hours_overdue"] > 0]["hours_overdue"].mean(), 1)
worst_rule = (
    filtered[filtered["rule_id"] != "R05"]
    .groupby("rule_name")["is_violation"].mean()
    .idxmax() if total > 0 else "N/A"
)
worst_team = (
    filtered.groupby("team")["is_violation"].mean().idxmax() if total > 0 else "N/A"
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total SLA Checks", f"{total:,}")
k2.metric("Violations Found", f"{violated:,}")
k3.metric("Overall Violation Rate", f"{violation_rate}%")
k4.metric("Avg Hours Overdue", f"{avg_overdue}h")
k5.metric("Worst Rule", worst_rule.replace(" SLA","").replace("Customer Survey","Survey").replace("Resolution Acknowledgment","Resolution") if worst_rule != "N/A" else "N/A")

st.divider()

# ── Row 1: By rule + heatmap ──────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Violation Rate by SLA Rule")
    rule_data = (
        filtered[filtered["rule_id"] != "R05"]
        .groupby(["rule_id", "rule_name"])
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )
    fig1 = go.Figure(go.Bar(
        x=rule_data["rule_name"],
        y=rule_data["rate"],
        marker_color=["#E8694C" if v > 30 else "#4C9BE8" for v in rule_data["rate"]],
        text=[f"{v}%" for v in rule_data["rate"]],
        textposition="outside",
    ))
    fig1.update_layout(
        yaxis_range=[0, 70], yaxis_title="Violation Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20, b=80), height=350,
        xaxis=dict(tickangle=-20, tickfont=dict(size=11))
    )
    fig1.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Team × Rule Heatmap")
    pivot_data = (
        filtered[filtered["rule_id"] != "R05"]
        .groupby(["team", "rule_name"])
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .pivot(index="team", columns="rule_name", values="rate")
    )
    fig2 = go.Figure(go.Heatmap(
        z=pivot_data.values,
        x=[c.replace(" SLA","") for c in pivot_data.columns],
        y=pivot_data.index.tolist(),
        colorscale="RdYlGn_r",
        text=[[f"{v:.0f}%" for v in row] for row in pivot_data.values],
        texttemplate="%{text}",
        textfont={"size": 13},
        zmin=0, zmax=65,
    ))
    fig2.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Hour of day + monthly trend ───────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader("Violation Rate by Hour of Day")
    filtered["hour"] = filtered["trigger_time"].dt.hour
    hour_data = (
        filtered.groupby("hour")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )
    fig3 = go.Figure(go.Bar(
        x=hour_data["hour"],
        y=hour_data["rate"],
        marker_color=["#E8694C" if v >= 35 else "#4C9BE8" for v in hour_data["rate"]],
    ))
    fig3.update_layout(
        yaxis_title="Violation Rate (%)",
        xaxis=dict(tickmode="linear", tick0=0, dtick=2),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350,
    )
    fig3.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Monthly Violation Rate Trend")
    filtered["month"] = filtered["trigger_time"].dt.to_period("M").astype(str)
    month_data = (
        filtered[filtered["month"] != "2024-07"]
        .groupby("month")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )
    fig4 = go.Figure(go.Scatter(
        x=month_data["month"],
        y=month_data["rate"],
        mode="lines+markers+text",
        line=dict(color="#4C9BE8", width=2),
        marker=dict(size=8),
        text=[f"{v}%" for v in month_data["rate"]],
        textposition="top center",
    ))
    fig4.update_layout(
        yaxis_range=[0, 50], yaxis_title="Violation Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350,
    )
    fig4.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    st.plotly_chart(fig4, use_container_width=True)

# ── Row 3: Category + raw violations table ────────────────────────────────────
col5, col6 = st.columns([1, 2])

with col5:
    st.subheader("Violation Rate by Category")
    cat_data = (
        filtered.groupby("category")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("rate", ascending=True)
    )
    fig5 = go.Figure(go.Bar(
        x=cat_data["rate"],
        y=cat_data["category"],
        orientation="h",
        marker_color=["#E8694C" if v > cat_data["rate"].median() else "#4C9BE8" for v in cat_data["rate"]],
        text=[f"{v}%" for v in cat_data["rate"]],
        textposition="outside",
    ))
    fig5.update_layout(
        xaxis_range=[0, 50], xaxis_title="Violation Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350,
    )
    fig5.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
    st.plotly_chart(fig5, use_container_width=True)

with col6:
    st.subheader("Violation Details")
    display_cols = ["ticket_id", "rule_name", "team", "category", "trigger_time", "actual_hours", "hours_overdue", "is_violation"]
    table_data = filtered[filtered["is_violation"] == 1][display_cols].copy()
    table_data["actual_hours"] = table_data["actual_hours"].round(1)
    table_data["hours_overdue"] = table_data["hours_overdue"].round(1)
    table_data = table_data.rename(columns={
        "ticket_id": "Ticket",
        "rule_name": "Rule",
        "team": "Team",
        "category": "Category",
        "trigger_time": "Triggered At",
        "actual_hours": "Actual Hrs",
        "hours_overdue": "Hrs Overdue",
        "is_violation": "Violation",
    })
    st.dataframe(table_data.head(100), use_container_width=True, height=320)

st.divider()
st.caption("Data: Synthetic customer support event log · 500 tickets · Jan–Jun 2024 · Built with Python, DuckDB, and Streamlit")
