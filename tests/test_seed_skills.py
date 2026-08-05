from app.data_gen import generate_dataset
from app.seed_skills import build_seed_registry


def test_segment_leads_skill_filters_by_score():
    dataset = generate_dataset(seed=3, num_campaigns=4, num_leads=20)
    registry = build_seed_registry(dataset)
    skill = registry.get("segment_leads")
    result = skill.func(min_score=0)
    assert "leads with score >= 0" in result


def test_summarize_campaign_performance_skill_runs():
    dataset = generate_dataset(seed=3, num_campaigns=4, num_leads=5)
    registry = build_seed_registry(dataset)
    skill = registry.get("summarize_campaign_performance")
    result = skill.func()
    assert "CTR" in result


def test_draft_email_sequence_skill_runs():
    dataset = generate_dataset(seed=3, num_campaigns=4, num_leads=5)
    registry = build_seed_registry(dataset)
    skill = registry.get("draft_email_sequence")
    result = skill.func(audience_title="VP Marketing")
    assert "VP Marketing" in result
