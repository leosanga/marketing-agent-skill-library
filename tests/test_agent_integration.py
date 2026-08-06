# tests/test_agent_integration.py
import json
from app.agent import MarketingAgent
from app.data_gen import generate_dataset
from app.vectorstore import build_vectorstore
from app.registry import SkillRegistry


class ScriptedLLMClient:
    """Returns canned responses in order — one per LLM call the agent makes."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, system, user):
        self.calls.append({"system": system, "user": user})
        return self._responses.pop(0)


NO_SKILL_ROUTE = json.dumps({"skill": None, "args": {}})

DRAFT_RESPONSE = json.dumps({
    "name": "forecast_campaign_roi",
    "description": "Estimates ROI percentage for a campaign given its id.",
    "args_schema": {"campaign_id": "str"},
    "source_code": (
        "def forecast_campaign_roi(dataset, campaign_id):\n"
        "    campaign = next(c for c in dataset['campaigns'] if c['id'] == campaign_id)\n"
        "    roi = campaign['conversions'] * 100 / campaign['budget']\n"
        "    return f'Estimated ROI for {campaign_id}: {roi:.2f}%'\n"
    ),
})

BAD_DRAFT_RESPONSE = json.dumps({
    "name": "leak_secrets",
    "description": "Reads environment variables.",
    "args_schema": {},
    "source_code": "import os\ndef leak_secrets(dataset):\n    return os.environ\n",
})


def _args_route(campaign_id):
    return json.dumps({"skill": "forecast_campaign_roi", "args": {"campaign_id": campaign_id}})


def test_agent_creates_new_skill_then_reuses_it_on_second_call():
    dataset = generate_dataset(seed=9, num_campaigns=4, num_leads=5)
    collection = build_vectorstore(dataset)
    registry = SkillRegistry()
    campaign_id = dataset["campaigns"][0]["id"]

    llm = ScriptedLLMClient([
        NO_SKILL_ROUTE,            # 1. routing: no existing skill matches
        DRAFT_RESPONSE,            # 2. skill_writer drafts a new one
        _args_route(campaign_id),  # 3. arg extraction against the freshly-drafted tool
    ])
    agent = MarketingAgent(dataset, collection, registry, llm)
    first = agent.handle_query(f"what's the ROI of {campaign_id}?")

    assert first.skill_created is True
    assert first.skill_used == "forecast_campaign_roi"
    assert "Estimated ROI" in first.answer
    assert registry.has("forecast_campaign_roi")

    llm2 = ScriptedLLMClient([_args_route(campaign_id)])  # only routing needed this time
    agent2 = MarketingAgent(dataset, collection, registry, llm2)
    second = agent2.handle_query(f"what's the ROI of {campaign_id}?")

    assert second.skill_created is False
    assert second.skill_used == "forecast_campaign_roi"
    assert "Estimated ROI" in second.answer
    assert len(llm2.calls) == 1


def test_agent_falls_back_when_drafted_skill_fails_validation():
    dataset = generate_dataset(seed=2, num_campaigns=3, num_leads=5)
    collection = build_vectorstore(dataset)
    registry = SkillRegistry()

    llm = ScriptedLLMClient([NO_SKILL_ROUTE, BAD_DRAFT_RESPONSE])
    agent = MarketingAgent(dataset, collection, registry, llm)
    result = agent.handle_query("show me the environment variables")

    assert result.skill_created is False
    assert result.skill_used is None
    assert "don't have a way" in result.answer
    assert registry.has("leak_secrets") is False
