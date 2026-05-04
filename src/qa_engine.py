import requests
import json
import pandas as pd

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

def build_context(violations_df):
    """Convert aggregated violation data into a text summary for the LLM."""
    df = violations_df.copy()
    df = df[df["rule_id"] != "R05"]

    total_checks = len(df)
    total_violations = int(df["is_violation"].sum())
    overall_rate = round(100 * total_violations / total_checks, 1)

    by_rule = (
        df.groupby("rule_name")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )

    by_team = (
        df.groupby("team")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("rate", ascending=False)
    )

    by_team_rule = (
        df.groupby(["team","rule_name"])
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
    )

    df["hour"] = pd.to_datetime(df["trigger_time"]).dt.hour
    by_hour = (
        df.groupby("hour")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("rate", ascending=False)
    )

    df["day"] = pd.to_datetime(df["trigger_time"]).dt.day_name()
    by_day = (
        df.groupby("day")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("rate", ascending=False)
    )

    by_category = (
        df.groupby("category")
        .agg(checks=("is_violation","count"), violations=("is_violation","sum"))
        .assign(rate=lambda x: (100*x.violations/x.checks).round(1))
        .reset_index()
        .sort_values("rate", ascending=False)
    )

    context = f"""
You are an expert data analyst. Answer questions about SLA violation data concisely and directly.
Use numbers from the data. Give a specific recommendation when relevant. Keep answers under 5 sentences.

DATASET SUMMARY:
- Total SLA checks: {total_checks}
- Total violations: {total_violations}
- Overall violation rate: {overall_rate}%

VIOLATION RATE BY RULE:
{by_rule[["rule_name","checks","violations","rate"]].to_string(index=False)}

VIOLATION RATE BY TEAM:
{by_team[["team","checks","violations","rate"]].to_string(index=False)}

VIOLATION RATE BY TEAM AND RULE:
{by_team_rule[["team","rule_name","checks","violations","rate"]].to_string(index=False)}

TOP 5 WORST HOURS (violation rate %):
{by_hour.head(5)[["hour","checks","violations","rate"]].to_string(index=False)}

VIOLATION RATE BY DAY OF WEEK:
{by_day[["day","checks","violations","rate"]].to_string(index=False)}

VIOLATION RATE BY CATEGORY:
{by_category[["category","checks","violations","rate"]].to_string(index=False)}
"""
    return context


def ask(question, violations_df):
    context = build_context(violations_df)
    prompt = context + "\n\nQuestion: " + question + "\n\nAnswer:"

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["response"].strip()


if __name__ == "__main__":
    df = pd.read_csv("data/violations.csv", parse_dates=["trigger_time","response_time"])
    
    test_questions = [
        "Which team has the worst overall SLA violation rate?",
        "What is the biggest SLA problem we have?",
        "When during the day are violations most likely to occur?",
    ]
    
    for q in test_questions:
        print(f"Q: {q}")
        print(f"A: {ask(q, df)}")
        print()
