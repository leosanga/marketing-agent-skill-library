from app.scenarios import SCENARIOS, get_scenario

def test_all_scenario_ids_are_unique():
    ids = [s["id"] for s in SCENARIOS]
    assert len(ids) == len(set(ids))

def test_get_scenario_returns_matching_entry():
    scenario = get_scenario(SCENARIOS[0]["id"])
    assert scenario == SCENARIOS[0]

def test_get_scenario_returns_none_for_unknown_id():
    assert get_scenario("not-a-real-id") is None
