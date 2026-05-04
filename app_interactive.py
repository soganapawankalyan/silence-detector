import streamlit as st
import pandas as pd
import duckdb
import yaml
import io
from datetime import timedelta
import plotly.graph_objects as go

st.set_page_config(
    page_title="Silence Detector",
    page_icon="🔇",
    layout="wide"
)

def load_rules(path="config/sla_rules.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)["rules"]

def detect_violations(events_df, rules):
    results = []
    con = duckdb.connect()
    con.register("events", events_df)
    for rule in rules:
        trigger = rule["trigger_event"]
        expected = rule["expected_event"]
        max_hours = rule["max_hours"]
        rule_id = rule["rule_id"]
        rule_name = rule["name"]
        query = f"""
            WITH triggers AS (
                SELECT ticket_id, team, category, agent,
                       timestamp AS trigger_time
                FROM events
                WHERE event_type = '{trigger}'
            ),
            responses AS (
                SELECT ticket_id,
                       MIN(timestamp) AS response_time
                FROM events
                WHERE event_type = '{expected}'
                GROUP BY ticket_id
            ),
            joined AS (
                SELECT
                    t.ticket_id, t.team, t.category, t.agent,
                    t.trigger_time, r.response_time,
                    CASE WHEN r.response_time IS NULL THEN 1 ELSE 0 END AS missing_entirely,
                    CASE
                        WHEN r.response_time IS NULL THEN NULL
                        ELSE (EPOCH(r.response_time) - EPOCH(t.trigger_time)) / 3600.0
                    END AS actual_hours
                FROM triggers t
                LEFT JOIN responses r ON t.ticket_id = r.ticket_id
            )
            SELECT
                ticket_id, team, category, agent,
                trigger_time, response_time, actual_hours, missing_entirely,
                CASE
                    WHEN missing_entirely = 1 THEN 1
                    WHEN actual_hours > {max_hours} THEN 1
                    ELSE 0
                END AS is_violation,
                CASE
                    WHEN missing_entirely = 1 THEN NULL
                    WHEN actual_hours > {max_hours} THEN actual_hours - {max_hours}
                    ELSE 0
                END AS hours_overdue
            FROM joined
        """
        df_result = con.execute(query).df()
        df_result["rule_id"] = rule_id
        df_result["rule_name"] = rule_name
        df_result["max_hours"] = max_hours
        df_result["trigger_event"] = trigger
        df_result["expected_event"] = expected
        results.append(df_result)
    con.close()
    return pd.concat(results, ignore_index=True)

def build_charts(filtered):
    charts = {}

    # Chart 1: By rule
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
    fig1.update_layout(yaxis_range=[0,70], yaxis_title="Violation Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=20,b=80),
        height=350, xaxis=dict(tickangle=-20, tickfont=dict(size=11)))
    fig1.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    charts["by_rule"] = fig1

    # Chart 2: Heatmap
    try:
        pivot_data = (
            filtered[filtered["rule_id"] != "R05"]
            .groupby(["team","rule_name"])
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
            texttemplate="%{text}", textfont={"size":13},
            zmin=0, zmax=65,
        ))
        fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=20), height=350)
        charts["heatmap"] = fig2
    except Exception:
        charts["heatmap"] = None

    # Chart 3: By hour
    filtered = filtered.copy()
    filtered["hour"] = pd.to_datetime(filtered["trigger_time"]).dt.hour
    hour_data = (
        filtered.groupby("hour")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )
    fig3 = go.Figure(go.Bar(
        x=hour_data["hour"], y=hour_data["rate"],
        marker_color=["#E8694C" if v >= 35 else "#4C9BE8" for v in hour_data["rate"]],
    ))
    fig3.update_layout(yaxis_title="Violation Rate (%)",
        xaxis=dict(tickmode="linear", tick0=0, dtick=2),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350)
    fig3.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    charts["by_hour"] = fig3

    # Chart 4: Monthly trend
    filtered["month"] = pd.to_datetime(filtered["trigger_time"]).dt.to_period("M").astype(str)
    month_data = (
        filtered.groupby("month")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("month")
    )
    fig4 = go.Figure(go.Scatter(
        x=month_data["month"], y=month_data["rate"],
        mode="lines+markers+text",
        line=dict(color="#4C9BE8", width=2), marker=dict(size=8),
        text=[f"{v}%" for v in month_data["rate"]], textposition="top center",
    ))
    fig4.update_layout(yaxis_range=[0,50], yaxis_title="Violation Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20), height=350)
    fig4.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    charts["monthly"] = fig4

    return charts

# ── Session state ─────────────────────────────────────────────────────────────
if "violations" not in st.session_state:
    st.session_state.violations = None
if "mode" not in st.session_state:
    st.session_state.mode = "demo"

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🔇 Silence Detector")
st.markdown("**Finds SLA violations — events that should have happened, but didn't.**")

# ── Mode selector ─────────────────────────────────────────────────────────────
mode = st.radio(
    "Data source",
    ["Use demo dataset", "Upload my own data"],
    horizontal=True
)

# ── Demo mode ─────────────────────────────────────────────────────────────────
if mode == "Use demo dataset":
    try:
        violations = pd.read_csv("data/violations.csv", parse_dates=["trigger_time","response_time"])
        st.session_state.violations = violations
        st.session_state.mode = "demo"
        st.success(f"Demo dataset loaded — {violations['ticket_id'].nunique()} tickets, {len(violations)} SLA checks")
    except FileNotFoundError:
        st.error("Demo data not found. Run: python src/generate_data.py && python src/detect_violations.py")
        st.stop()

# ── Upload mode ───────────────────────────────────────────────────────────────
else:
    st.markdown("### Upload your event log")
    st.markdown("Your CSV must contain these columns: `ticket_id`, `event_type`, `timestamp`, `team`, `category`, `agent`")

    uploaded = st.file_uploader("Upload event log CSV", type=["csv"])

    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.markdown("#### Column mapping")
            st.markdown("Map your CSV columns to the required schema:")

            cols = ["(none)"] + list(df.columns)
            c1, c2, c3 = st.columns(3)
            with c1:
                col_ticket = st.selectbox("ticket_id column", cols, index=cols.index("ticket_id") if "ticket_id" in cols else 0)
                col_event = st.selectbox("event_type column", cols, index=cols.index("event_type") if "event_type" in cols else 0)
            with c2:
                col_time = st.selectbox("timestamp column", cols, index=cols.index("timestamp") if "timestamp" in cols else 0)
                col_team = st.selectbox("team column", cols, index=cols.index("team") if "team" in cols else 0)
            with c3:
                col_category = st.selectbox("category column", cols, index=cols.index("category") if "category" in cols else 0)
                col_agent = st.selectbox("agent column", cols, index=cols.index("agent") if "agent" in cols else 0)

            if st.button("Run detection on my data"):
                mapping = {
                    col_ticket: "ticket_id", col_event: "event_type",
                    col_time: "timestamp", col_team: "team",
                    col_category: "category", col_agent: "agent"
                }
                if "(none)" in mapping:
                    st.error("Please map all columns before running.")
                else:
                    mapped_df = df.rename(columns=mapping)[["ticket_id","event_type","timestamp","team","category","agent"]]
                    mapped_df["timestamp"] = pd.to_datetime(mapped_df["timestamp"])

                    with st.spinner("Running violation detection..."):
                        rules = load_rules()
                        violations = detect_violations(mapped_df, rules)
                        st.session_state.violations = violations
                        st.session_state.mode = "upload"

                    st.success(f"Detection complete — {violations['ticket_id'].nunique()} tickets, {len(violations)} SLA checks, {int(violations['is_violation'].sum())} violations found")

        except Exception as e:
            st.error(f"Error reading file: {e}")

    if st.session_state.violations is None:
        st.info("Upload a CSV and run detection to see results.")
        st.stop()

# ── Analysis ──────────────────────────────────────────────────────────────────
violations = st.session_state.violations
st.divider()

# Sidebar filters
st.sidebar.title("Filters")
selected_teams = st.sidebar.multiselect("Teams", sorted(violations["team"].unique()), default=sorted(violations["team"].unique()))
selected_categories = st.sidebar.multiselect("Categories", sorted(violations["category"].unique()), default=sorted(violations["category"].unique()))
selected_rules = st.sidebar.multiselect("SLA Rules", sorted(violations["rule_id"].unique()), default=[r for r in sorted(violations["rule_id"].unique()) if r != "R05"])

filtered = violations[
    violations["team"].isin(selected_teams) &
    violations["category"].isin(selected_categories) &
    violations["rule_id"].isin(selected_rules)
]

# KPIs
total = len(filtered)
violated = int(filtered["is_violation"].sum())
violation_rate = round(100 * violated / total, 1) if total > 0 else 0
avg_overdue = round(filtered[filtered["hours_overdue"] > 0]["hours_overdue"].mean(), 1)
worst_team = filtered.groupby("team")["is_violation"].mean().idxmax() if total > 0 else "N/A"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total SLA Checks", f"{total:,}")
k2.metric("Violations Found", f"{violated:,}")
k3.metric("Overall Violation Rate", f"{violation_rate}%")
k4.metric("Avg Hours Overdue", f"{avg_overdue}h")
k5.metric("Worst Team", worst_team)
st.divider()

# Charts
charts = build_charts(filtered)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Violation Rate by SLA Rule")
    st.plotly_chart(charts["by_rule"], use_container_width=True)
with col2:
    st.subheader("Team × Rule Heatmap")
    if charts["heatmap"]:
        st.plotly_chart(charts["heatmap"], use_container_width=True)
    else:
        st.info("Not enough data for heatmap.")

col3, col4 = st.columns(2)
with col3:
    st.subheader("Violation Rate by Hour of Day")
    st.plotly_chart(charts["by_hour"], use_container_width=True)
with col4:
    st.subheader("Monthly Violation Rate Trend")
    st.plotly_chart(charts["monthly"], use_container_width=True)

st.subheader("Violation Details")
display_cols = ["ticket_id","rule_name","team","category","trigger_time","actual_hours","hours_overdue","is_violation"]
available_cols = [c for c in display_cols if c in filtered.columns]
table_data = filtered[filtered["is_violation"]==1][available_cols].copy()
if "actual_hours" in table_data.columns:
    table_data["actual_hours"] = table_data["actual_hours"].round(1)
if "hours_overdue" in table_data.columns:
    table_data["hours_overdue"] = table_data["hours_overdue"].round(1)
st.dataframe(table_data.head(100), use_container_width=True, height=320)

st.divider()
st.caption("Silence Detector · Built with Python, DuckDB, Streamlit · github.com/soganapawankalyan/silence-detector")

# ── Q&A Section ───────────────────────────────────────────────────────────────
st.divider()
st.subheader("Ask a question about your data")
st.markdown("Powered by Llama 3.2 running locally via Ollama.")

sample_questions = [
    "Which team has the worst overall SLA violation rate?",
    "What is the biggest SLA problem we have?",
    "When during the day are violations most likely to occur?",
    "Which ticket category needs attention?",
    "What day of the week has the most violations?",
]

selected_sample = st.selectbox(
    "Try a sample question or type your own below:",
    ["(type your own)"] + sample_questions
)

user_question = st.text_input(
    "Your question:",
    value="" if selected_sample == "(type your own)" else selected_sample
)

if st.button("Get Answer") and user_question.strip():
    import requests
    import pandas as pd

    def ask_ollama(question, df):
        vdf = df[df["rule_id"] != "R05"].copy()
        total_checks = len(vdf)
        total_violations = int(vdf["is_violation"].sum())
        overall_rate = round(100 * total_violations / total_checks, 1)
        by_rule = (vdf.groupby("rule_name").agg(checks=("is_violation","count"), violations=("is_violation","sum")).assign(rate=lambda x: (100*x.violations/x.checks).round(1)).reset_index())
        by_team = (vdf.groupby("team").agg(checks=("is_violation","count"), violations=("is_violation","sum")).assign(rate=lambda x: (100*x.violations/x.checks).round(1)).reset_index().sort_values("rate", ascending=False))
        by_category = (vdf.groupby("category").agg(checks=("is_violation","count"), violations=("is_violation","sum")).assign(rate=lambda x: (100*x.violations/x.checks).round(1)).reset_index().sort_values("rate", ascending=False))
        vdf["hour"] = pd.to_datetime(vdf["trigger_time"]).dt.hour
        by_hour = (vdf.groupby("hour").agg(checks=("is_violation","count"), violations=("is_violation","sum")).assign(rate=lambda x: (100*x.violations/x.checks).round(1)).reset_index().sort_values("rate", ascending=False))
        vdf["day"] = pd.to_datetime(vdf["trigger_time"]).dt.day_name()
        by_day = (vdf.groupby("day").agg(checks=("is_violation","count"), violations=("is_violation","sum")).assign(rate=lambda x: (100*x.violations/x.checks).round(1)).reset_index().sort_values("rate", ascending=False))

        context = (
            "You are an expert data analyst. Answer questions about SLA violation data concisely and directly. "
            "Use numbers from the data. Give a specific recommendation when relevant. Keep answers under 5 sentences.\n\n"
            "DATASET SUMMARY:\n"
            f"- Total SLA checks: {total_checks}\n"
            f"- Total violations: {total_violations}\n"
            f"- Overall violation rate: {overall_rate}%\n\n"
            f"VIOLATION RATE BY RULE:\n{by_rule[['rule_name','checks','violations','rate']].to_string(index=False)}\n\n"
            f"VIOLATION RATE BY TEAM:\n{by_team[['team','checks','violations','rate']].to_string(index=False)}\n\n"
            f"TOP 5 WORST HOURS:\n{by_hour.head(5)[['hour','checks','violations','rate']].to_string(index=False)}\n\n"
            f"VIOLATION RATE BY DAY:\n{by_day[['day','checks','violations','rate']].to_string(index=False)}\n\n"
            f"VIOLATION RATE BY CATEGORY:\n{by_category[['category','checks','violations','rate']].to_string(index=False)}"
        )
        prompt = context + "\n\nQuestion: " + question + "\n\nAnswer:"
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2", "prompt": prompt, "stream": False},
                timeout=120
            )
            return response.json()["response"].strip()
        except Exception as e:
            return f"Ollama not reachable. Run: ollama serve. Error: {e}"

    with st.spinner("Thinking... (10-30 seconds)"):
        answer = ask_ollama(user_question, violations)
    st.success(answer)
