import json
import random
from datetime import date, timedelta
from pathlib import Path

CHANNELS = ["email", "paid_search", "content", "webinar", "outbound"]
TITLES = ["VP Marketing", "RevOps Manager", "Head of Growth", "Marketing Ops Analyst", "CMO"]
STATUSES = ["new", "qualified", "nurturing", "disqualified"]


def _rand_date(rng: random.Random, start: date, days_span: int) -> date:
    return start + timedelta(days=rng.randint(0, days_span))


def generate_dataset(seed: int = 42, num_campaigns: int = 12, num_leads: int = 60) -> dict:
    rng = random.Random(seed)
    base = date(2026, 1, 1)

    campaigns = []
    for i in range(num_campaigns):
        start = _rand_date(rng, base, 180)
        campaigns.append({
            "id": f"camp_{i + 1:03d}",
            "name": f"{rng.choice(['Spring', 'Q1', 'Q2', 'Growth', 'Relaunch'])} "
                    f"{rng.choice(CHANNELS).replace('_', ' ').title()} Push",
            "channel": rng.choice(CHANNELS),
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=rng.randint(7, 45))).isoformat(),
            "budget": rng.randint(500, 20000),
            "impressions": rng.randint(1000, 200000),
            "clicks": rng.randint(50, 8000),
            "conversions": rng.randint(1, 400),
        })

    leads = []
    for i in range(num_leads):
        campaign = rng.choice(campaigns)
        leads.append({
            "id": f"lead_{i + 1:03d}",
            "name": f"Lead {i + 1}",
            "company": f"Company {rng.randint(1, 200)}",
            "title": rng.choice(TITLES),
            "company_size": rng.choice(["1-10", "11-50", "51-200", "201-1000", "1000+"]),
            "source_campaign_id": campaign["id"],
            "created_at": _rand_date(rng, base, 200).isoformat(),
            "score": rng.randint(0, 100),
            "status": rng.choice(STATUSES),
        })

    email_metrics = []
    for i, campaign in enumerate(campaigns):
        sent = rng.randint(500, 10000)
        opened = int(sent * rng.uniform(0.15, 0.55))
        clicked = int(opened * rng.uniform(0.05, 0.35))
        email_metrics.append({
            "id": f"email_{i + 1:03d}",
            "campaign_id": campaign["id"],
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "unsubscribed": rng.randint(0, int(sent * 0.02)),
            "date": campaign["start_date"],
        })

    return {"campaigns": campaigns, "leads": leads, "email_metrics": email_metrics}


def write_dataset(path: str = "data/dataset.json", seed: int = 42) -> None:
    dataset = generate_dataset(seed=seed)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dataset, indent=2))


if __name__ == "__main__":
    write_dataset()
