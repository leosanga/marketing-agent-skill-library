from app.validator import validate_skill_source

GOOD_SOURCE = '''
def forecast_campaign_roi(dataset, campaign_id):
    campaign = next(c for c in dataset["campaigns"] if c["id"] == campaign_id)
    roi = campaign["conversions"] * 100 / campaign["budget"]
    return f"Estimated ROI for {campaign_id}: {roi:.2f}"
'''

BAD_SOURCE_IMPORT = '''
import os

def forecast_campaign_roi(dataset, campaign_id):
    return os.listdir(".")
'''

BAD_SOURCE_EVAL = '''
def forecast_campaign_roi(dataset, campaign_id):
    return eval(campaign_id)
'''

BAD_SOURCE_SYNTAX = '''
def forecast_campaign_roi(dataset, campaign_id)
    return "broken"
'''

BAD_SOURCE_ALIASED_EVAL = '''
def forecast_campaign_roi(dataset, campaign_id):
    g = eval
    return g(campaign_id)
'''

def test_valid_source_passes():
    ok, _ = validate_skill_source(GOOD_SOURCE, "forecast_campaign_roi")
    assert ok is True

def test_import_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_IMPORT, "forecast_campaign_roi")
    assert ok is False
    assert "import" in reason

def test_eval_call_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_EVAL, "forecast_campaign_roi")
    assert ok is False
    assert "eval" in reason

def test_syntax_error_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_SYNTAX, "forecast_campaign_roi")
    assert ok is False
    assert "syntax error" in reason

def test_missing_function_name_is_rejected():
    ok, _ = validate_skill_source(GOOD_SOURCE, "wrong_name")
    assert ok is False

def test_aliased_eval_call_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_ALIASED_EVAL, "forecast_campaign_roi")
    assert ok is False
    assert "eval" in reason
