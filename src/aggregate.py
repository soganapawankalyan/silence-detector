import pandas as pd
import os

def load_violations(path="data/violations.csv"):
    df = pd.read_csv(path, parse_dates=["trigger_time", "response_time"])
    return df

def build_aggregations(df):
    os.makedirs("data", exist_ok=True)

    # 1. Violation rate by rule
    by_rule = (
        df.groupby(["rule_id", "rule_name", "max_hours"])
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
            avg_hours_overdue=("hours_overdue", "mean"),
            max_hours_overdue=("hours_overdue", "max"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
    )
    by_rule.to_csv("data/agg_by_rule.csv", index=False)
    print("=== By Rule ===")
    print(by_rule[["rule_name", "total_checks", "total_violations", "violation_rate_pct", "avg_hours_overdue"]].to_string(index=False))

    # 2. Violation rate by team x rule
    by_team_rule = (
        df.groupby(["team", "rule_id", "rule_name"])
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
    )
    by_team_rule.to_csv("data/agg_by_team_rule.csv", index=False)
    print()
    print("=== By Team x Rule ===")
    print(by_team_rule.to_string(index=False))

    # 3. Violation rate by day of week
    df["day_of_week"] = df["trigger_time"].dt.day_name()
    df["day_num"] = df["trigger_time"].dt.dayofweek
    by_dow = (
        df.groupby(["day_num", "day_of_week"])
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
        .sort_values("day_num")
    )
    by_dow.to_csv("data/agg_by_dow.csv", index=False)
    print()
    print("=== By Day of Week ===")
    print(by_dow[["day_of_week", "total_checks", "total_violations", "violation_rate_pct"]].to_string(index=False))

    # 4. Violation rate by hour of day
    df["hour"] = df["trigger_time"].dt.hour
    by_hour = (
        df.groupby("hour")
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
    )
    by_hour.to_csv("data/agg_by_hour.csv", index=False)
    print()
    print("=== By Hour of Day (top 5 worst) ===")
    print(by_hour.sort_values("violation_rate_pct", ascending=False).head(5)[["hour", "total_checks", "total_violations", "violation_rate_pct"]].to_string(index=False))

    # 5. Violation rate by category
    by_category = (
        df.groupby("category")
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
        .sort_values("violation_rate_pct", ascending=False)
    )
    by_category.to_csv("data/agg_by_category.csv", index=False)
    print()
    print("=== By Category ===")
    print(by_category.to_string(index=False))

    # 6. Monthly trend
    df["month"] = df["trigger_time"].dt.to_period("M").astype(str)
    by_month = (
        df.groupby("month")
        .agg(
            total_checks=("is_violation", "count"),
            total_violations=("is_violation", "sum"),
        )
        .assign(violation_rate_pct=lambda x: (100 * x.total_violations / x.total_checks).round(1))
        .reset_index()
    )
    by_month.to_csv("data/agg_by_month.csv", index=False)
    print()
    print("=== Monthly Trend ===")
    print(by_month.to_string(index=False))

if __name__ == "__main__":
    df = load_violations()
    build_aggregations(df)
    print()
    print("All aggregation files saved to data/")
