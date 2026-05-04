# 🔇 Silence Detector — SLA Violation Detection Engine

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://silence-detector-cyqfaxdald6bqwwoqg2wbl.streamlit.app/)

> *Most dashboards show you what happened. This one shows you what should have happened — but didn't.*

---

## The Problem

In customer support operations, the most costly failures are invisible ones.

A ticket is opened. No one responds. The clock runs out. Nobody notices — because there's no event in the log to trigger an alert. The absence itself is the signal.

Standard monitoring tools catch errors that *occur*. They can't catch events that *never occurred*. This project was built to solve exactly that problem.

---

## What It Does

**Silence Detector** is a rule-driven SLA violation engine that:

1. Reads business SLA rules from a config file (no code changes needed to update rules)
2. Scans a customer support event log for expected follow-up events
3. Flags every case where the expected event didn't happen within the allowed time window
4. Aggregates violations by team, rule, hour, day, category, and month
5. Surfaces findings in an interactive dashboard
**Interactive features (v2):**
- Upload your own event log CSV and map columns to run detection on real data
- Ask natural language questions about violations — answered by Llama 3.2 running locally
- Simulate what-if scenarios by adjusting SLA thresholds with sliders and seeing violation rates update live
 built for operational decision-making

---

## Key Findings (Jan–Jun 2024 Dataset)

**Overall: 543 SLA violations detected across 1,742 checks — a 31.2% violation rate**

| Finding | Detail | Business Implication |
|---|---|---|
| Survey SLA is broken | 48.4% violation rate — worst of all rules | Customers are not being surveyed after resolution. CSAT data is unreliable. |
| Overnight gap | Hours 0 and 20 have 41.5% and 38.2% violation rates | Staffing drops after business hours. SLAs require coverage that doesn't exist. |
| Team B and D are systemic | Team B: 37–61% violation rate across rules | Not individual failures — team-level process or capacity problems. |
| Wednesday is worst day | 34.5% vs Friday at 29.6% | Counterintuitive. Mid-week volume spike likely exceeds capacity. |
| Account tickets lead violations | 36.6% violation rate vs Returns at 24.5% | Account tickets are more complex — may need longer SLA windows or dedicated handling. |

---

## Three Specific Recommendations

**1. Fix the survey pipeline immediately**
The Customer Survey SLA has a 48.4% violation rate — nearly half of resolved tickets never trigger a survey on time. This is almost certainly an automation failure, not a people failure. Audit the survey trigger logic and automate it on ticket resolution.

**2. Address the overnight staffing gap**
Violations spike at midnight (41.5%) and 8pm (38.2%). This is not random — it's a structural coverage gap. Either adjust SLA windows for overnight tickets or add on-call coverage during high-violation hours.

**3. Investigate Team B and Team D as process failures, not performance failures**
Team B violates the Escalation Review SLA at 52.9% — more than double Team A's 11.1%. Before attributing this to agent performance, check ticket volume distribution. Teams with higher violation rates may simply be receiving disproportionate ticket load.

---

## Architecture
config/
sla_rules.yaml          # Business rules — edit here, no code changes needed
src/
generate_data.py        # Synthetic event log generator (500 tickets, 6 event types)
detect_violations.py    # Core detection engine — DuckDB SQL absence detection
aggregate.py            # Aggregation layer — 6 analytical cuts
visualize.py            # Static chart exports (PNG + HTML)
data/
event_log.csv           # Raw event log
violations.csv          # Detection output — one row per SLA check
agg_by_rule.csv         # Violation rate by rule
agg_by_team_rule.csv    # Violation rate by team × rule
agg_by_dow.csv          # Violation rate by day of week
agg_by_hour.csv         # Violation rate by hour of day
agg_by_category.csv     # Violation rate by ticket category
agg_by_month.csv        # Monthly trend
app.py                    # Streamlit dashboard — interactive filters + 5 charts
outputs/                  # Exported chart PNGs

---

## How To Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic event log
python src/generate_data.py

# 3. Run violation detection
python src/detect_violations.py

# 4. Build aggregations
python src/aggregate.py

# 5. Launch dashboard
streamlit run app.py
```

---

## How To Use With Real Data

Replace `data/event_log.csv` with your own event log. Required schema:

| Column | Type | Description |
|---|---|---|
| ticket_id | string | Unique ticket identifier |
| event_type | string | Type of event (must match trigger/expected in rules) |
| timestamp | datetime | When the event occurred |
| team | string | Team responsible |
| category | string | Ticket category |
| agent | string | Agent name or ID |

Then update `config/sla_rules.yaml` to match your business rules and re-run steps 3–5.

---

## SLA Rules (Configurable)

Rules live in `config/sla_rules.yaml`. No code changes needed to add, remove, or modify rules.

```yaml
- rule_id: R01
  name: First Response SLA
  trigger_event: ticket_opened
  expected_event: first_response
  max_hours: 4
  description: Every opened ticket must receive a first response within 4 hours
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Detection engine | DuckDB (SQL absence detection) |
| Data processing | Python, Pandas |
| Visualization | Plotly |
| Dashboard | Streamlit |
| Config | YAML |
| Data generation | Faker |

---

## Why This Project Exists

Predictive models and KPI dashboards are everywhere in data portfolios.

This project tackles a different and harder problem: **detecting what didn't happen**.

Absence detection requires thinking about expected event sequences, time windows, and the gap between business rules and operational reality — not just summarizing data that already exists.

That gap — between what *should* happen and what *did* happen — is where operational failures live.
