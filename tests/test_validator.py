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

BAD_SOURCE_DUNDER_ESCAPE = '''
def forecast_campaign_roi(dataset, campaign_id):
    return ().__class__.__bases__[0].__subclasses__()
'''

# Reviewer-verified escape: a running generator walks its own gi_frame -> f_back
# -> f_globals to a real module frame, reads that frame's real __builtins__ dict
# and imports os. Uses only NON-dunder attributes (gi_frame, f_back, f_globals),
# so the dunder check does not catch it — the frame-attr blocklist must.
BAD_SOURCE_FRAME_WALK = '''
def forecast_campaign_roi(dataset, campaign_id="x"):
    holder = {}
    def gen():
        g_local = holder["g"]
        f = g_local.gi_frame.f_back
        while f is not None:
            bi = f.f_globals.get("__builtins__")
            if isinstance(bi, dict) and "__import__" in bi:
                holder["osenv"] = bi["__import__"]("os").environ
                return
            f = f.f_back
        yield
    g = gen()
    holder["g"] = g
    try:
        next(g)
    except StopIteration:
        pass
    return sorted(holder.get("osenv", []))[:3]
'''

# Attribute-aliasing gap sibling to BAD_SOURCE_ALIASED_EVAL: the forbidden call
# name is reached as an *attribute* (b.eval) then aliased, which the ast.Call
# branch alone would miss once it's called via the bare alias.
BAD_SOURCE_ALIASED_ATTR_EVAL = '''
def forecast_campaign_roi(dataset, campaign_id):
    b = dataset
    ev = b.eval
    return ev(campaign_id)
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

def test_dunder_attribute_escape_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_DUNDER_ESCAPE, "forecast_campaign_roi")
    assert ok is False
    assert "dunder" in reason.lower() or "__" in reason

def test_frame_walk_escape_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_FRAME_WALK, "forecast_campaign_roi")
    assert ok is False
    assert "gi_frame" in reason or "frame" in reason.lower()

def test_aliased_attribute_eval_call_is_rejected():
    ok, reason = validate_skill_source(BAD_SOURCE_ALIASED_ATTR_EVAL, "forecast_campaign_roi")
    assert ok is False
    assert "eval" in reason
