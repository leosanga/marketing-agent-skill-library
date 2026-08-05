import json
import pytest
from app.skill_writer import draft_skill, SkillDraftError


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response
        self.last_call = None

    def complete(self, system: str, user: str) -> str:
        self.last_call = {"system": system, "user": user}
        return self.response


GOOD_RESPONSE = json.dumps({
    "name": "forecast_campaign_roi",
    "description": "Estimates ROI for a campaign given its id.",
    "args_schema": {"campaign_id": "str"},
    "source_code": (
        "def forecast_campaign_roi(dataset, campaign_id):\n"
        "    campaign = next(c for c in dataset['campaigns'] if c['id'] == campaign_id)\n"
        "    return campaign['conversions'] * 100 / campaign['budget']\n"
    ),
})


def test_draft_skill_parses_well_formed_response():
    client = FakeLLMClient(GOOD_RESPONSE)
    drafted = draft_skill("what's the ROI of campaign camp_001?", client)
    assert drafted.name == "forecast_campaign_roi"
    assert "campaign_id" in drafted.args_schema
    assert "def forecast_campaign_roi" in drafted.source_code

def test_draft_skill_passes_query_into_prompt():
    client = FakeLLMClient(GOOD_RESPONSE)
    draft_skill("what's the ROI of campaign camp_001?", client)
    assert "camp_001" in client.last_call["user"]

def test_draft_skill_raises_on_malformed_json():
    client = FakeLLMClient("not json at all")
    with pytest.raises(SkillDraftError):
        draft_skill("anything", client)
