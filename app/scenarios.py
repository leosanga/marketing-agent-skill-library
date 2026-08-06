SCENARIOS = [
    {
        "id": "top_leads",
        "label": "Which leads should we prioritize this week?",
        "query": "Which leads have the highest score and should be prioritized this week?",
    },
    {
        "id": "best_campaign",
        "label": "Which campaign is performing best?",
        "query": "Which campaign has the best conversion rate?",
    },
    {
        "id": "email_sequence_vp",
        "label": "Draft outreach for VP Marketing leads",
        "query": "Draft an email sequence for leads with the title VP Marketing",
    },
    {
        "id": "campaign_roi",
        "label": "What's the estimated ROI of our top campaign?",
        "query": "What is the estimated ROI of our top-performing campaign?",
    },
]


def get_scenario(scenario_id: str) -> dict | None:
    return next((s for s in SCENARIOS if s["id"] == scenario_id), None)
