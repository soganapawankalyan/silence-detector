import pandas as pd
import numpy as np
from faker import Faker
from datetime import timedelta
import random
import os

fake = Faker()
random.seed(42)
np.random.seed(42)

TEAMS = ["Team A", "Team B", "Team C", "Team D"]
CATEGORIES = ["Billing", "Technical", "Account", "Shipping", "Returns"]
AGENTS = [fake.name() for _ in range(20)]

TEAM_VIOLATION_RATE = {
    "Team A": 0.15,
    "Team B": 0.40,
    "Team C": 0.20,
    "Team D": 0.35,
}

def generate_event_log(n_tickets=500):
    rows = []
    start_date = pd.Timestamp("2024-01-01")
    end_date = pd.Timestamp("2024-06-30")
    hour_probs = [0.02]*6 + [0.005]*2 + [0.085]*9 + [0.02]*7
    hour_probs = [p/sum(hour_probs) for p in hour_probs]

    for i in range(n_tickets):
        ticket_id = f"TKT-{1000 + i}"
        team = random.choice(TEAMS)
        category = random.choice(CATEGORIES)
        agent = random.choice(AGENTS)
        violation_rate = TEAM_VIOLATION_RATE[team]

        open_time = fake.date_time_between(start_date=start_date, end_date=end_date)
        hour_offset = int(np.random.choice(range(24), p=hour_probs))
        open_time = open_time.replace(hour=hour_offset, minute=random.randint(0, 59))

        rows.append({"ticket_id": ticket_id, "event_type": "ticket_opened", "timestamp": open_time, "team": team, "category": category, "agent": agent})

        delay_hours = random.uniform(4.5, 12) if random.random() < violation_rate else random.uniform(0.25, 3.5)
        response_time = open_time + timedelta(hours=delay_hours)
        rows.append({"ticket_id": ticket_id, "event_type": "first_response", "timestamp": response_time, "team": team, "category": category, "agent": agent})

        if random.random() < 0.30:
            escalate_time = response_time + timedelta(hours=random.uniform(0.5, 3))
            rows.append({"ticket_id": ticket_id, "event_type": "ticket_escalated", "timestamp": escalate_time, "team": team, "category": category, "agent": agent})
            review_delay = random.uniform(2.5, 8) if random.random() < violation_rate else random.uniform(0.25, 1.8)
            rows.append({"ticket_id": ticket_id, "event_type": "escalation_reviewed", "timestamp": escalate_time + timedelta(hours=review_delay), "team": team, "category": category, "agent": agent})

        if random.random() < 0.20:
            reassign_time = response_time + timedelta(hours=random.uniform(1, 5))
            new_agent = random.choice(AGENTS)
            rows.append({"ticket_id": ticket_id, "event_type": "ticket_reassigned", "timestamp": reassign_time, "team": team, "category": category, "agent": new_agent})
            reresponse_delay = random.uniform(3.5, 10) if random.random() < violation_rate else random.uniform(0.25, 2.8)
            rows.append({"ticket_id": ticket_id, "event_type": "first_response", "timestamp": reassign_time + timedelta(hours=reresponse_delay), "team": team, "category": category, "agent": new_agent})

        resolve_time = response_time + timedelta(hours=random.uniform(2, 48))
        rows.append({"ticket_id": ticket_id, "event_type": "ticket_resolved", "timestamp": resolve_time, "team": team, "category": category, "agent": agent})

        confirm_delay = random.uniform(8.5, 24) if random.random() < violation_rate else random.uniform(0.5, 7.5)
        rows.append({"ticket_id": ticket_id, "event_type": "resolution_confirmed", "timestamp": resolve_time + timedelta(hours=confirm_delay), "team": team, "category": category, "agent": agent})

        survey_violation_rate = min(violation_rate + 0.20, 0.75)
        survey_delay = random.uniform(25, 72) if random.random() < survey_violation_rate else random.uniform(1, 23)
        rows.append({"ticket_id": ticket_id, "event_type": "survey_sent", "timestamp": resolve_time + timedelta(hours=survey_delay), "team": team, "category": category, "agent": agent})

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = generate_event_log(500)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/event_log.csv", index=False)
    print(f"Generated {len(df)} events for {df['ticket_id'].nunique()} tickets")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"\nEvent type counts:")
    print(df["event_type"].value_counts())
