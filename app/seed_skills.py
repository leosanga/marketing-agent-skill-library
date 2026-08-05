from app.registry import Skill, SkillRegistry


def segment_leads(dataset: dict, min_score: int = 70) -> str:
    matches = [lead for lead in dataset["leads"] if lead["score"] >= min_score]
    if not matches:
        return f"No leads found with score >= {min_score}."
    lines = [
        f"- {lead['name']} ({lead['company']}, score {lead['score']}, status {lead['status']})"
        for lead in matches
    ]
    return f"{len(matches)} leads with score >= {min_score}:\n" + "\n".join(lines)


def summarize_campaign_performance(dataset: dict, campaign_id: str | None = None) -> str:
    campaigns = dataset["campaigns"]
    if campaign_id:
        campaigns = [c for c in campaigns if c["id"] == campaign_id]
        if not campaigns:
            return f"No campaign found with id {campaign_id}."
    lines = []
    for c in campaigns:
        ctr = (c["clicks"] / c["impressions"] * 100) if c["impressions"] else 0
        conv_rate = (c["conversions"] / c["clicks"] * 100) if c["clicks"] else 0
        lines.append(
            f"- {c['name']} ({c['id']}): CTR {ctr:.1f}%, conversion rate {conv_rate:.1f}%, "
            f"{c['conversions']} conversions on ${c['budget']} budget"
        )
    return "\n".join(lines)


def draft_email_sequence(dataset: dict, audience_title: str) -> str:
    matching_leads = [lead for lead in dataset["leads"] if lead["title"] == audience_title]
    count = len(matching_leads)
    return (
        f"3-email sequence draft for {audience_title} ({count} matching leads):\n"
        f"1. Intro: pain point framing for {audience_title}s dealing with fragmented GTM data.\n"
        f"2. Proof: a short case study relevant to {audience_title}s.\n"
        f"3. CTA: book a 15-minute walkthrough."
    )


def build_seed_registry(dataset: dict) -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(Skill(
        name="segment_leads",
        description="Segment leads by minimum lead score. Args: min_score (int, default 70).",
        args_schema={"min_score": "int"},
        source_code="<seed skill: see app/seed_skills.py:segment_leads>",
        func=lambda **kwargs: segment_leads(dataset, **kwargs),
    ))
    registry.register(Skill(
        name="summarize_campaign_performance",
        description=(
            "Summarize CTR and conversion rate for one campaign or all campaigns. "
            "Args: campaign_id (str, optional)."
        ),
        args_schema={"campaign_id": "str"},
        source_code="<seed skill: see app/seed_skills.py:summarize_campaign_performance>",
        func=lambda **kwargs: summarize_campaign_performance(dataset, **kwargs),
    ))
    registry.register(Skill(
        name="draft_email_sequence",
        description=(
            "Draft a 3-email outreach sequence for a given audience job title. "
            "Args: audience_title (str)."
        ),
        args_schema={"audience_title": "str"},
        source_code="<seed skill: see app/seed_skills.py:draft_email_sequence>",
        func=lambda **kwargs: draft_email_sequence(dataset, **kwargs),
    ))
    return registry
