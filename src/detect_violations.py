import pandas as pd
import duckdb
import yaml
import os

def load_rules(path="config/sla_rules.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)["rules"]

def load_events(path="data/event_log.csv"):
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df

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
                    t.ticket_id,
                    t.team,
                    t.category,
                    t.agent,
                    t.trigger_time,
                    r.response_time,
                    CASE WHEN r.response_time IS NULL THEN 1 ELSE 0 END AS missing_entirely,
                    CASE
                        WHEN r.response_time IS NULL THEN NULL
                        ELSE (EPOCH(r.response_time) - EPOCH(t.trigger_time)) / 3600.0
                    END AS actual_hours
                FROM triggers t
                LEFT JOIN responses r ON t.ticket_id = r.ticket_id
            )
            SELECT
                ticket_id,
                team,
                category,
                agent,
                trigger_time,
                response_time,
                actual_hours,
                missing_entirely,
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

if __name__ == "__main__":
    rules = load_rules()
    events = load_events()
    violations_df = detect_violations(events, rules)

    os.makedirs("data", exist_ok=True)
    violations_df.to_csv("data/violations.csv", index=False)

    total = len(violations_df)
    violated = violations_df["is_violation"].sum()
    print(f"Total SLA checks: {total}")
    print(f"Violations found: {int(violated)} ({100*violated/total:.1f}%)")
    print()
    print("Violation rate by rule:")
    summary = (
        violations_df.groupby(["rule_id", "rule_name"])
        .agg(checks=("is_violation", "count"), violations=("is_violation", "sum"))
        .assign(violation_rate=lambda x: (100 * x.violations / x.checks).round(1))
        .reset_index()
    )
    print(summary.to_string(index=False))
    print()
    print("Violation rate by team:")
    team_summary = (
        violations_df[violations_df["is_violation"] == 1]
        .groupby("team")
        .agg(violations=("is_violation", "sum"))
        .reset_index()
        .sort_values("violations", ascending=False)
    )
    print(team_summary.to_string(index=False))
