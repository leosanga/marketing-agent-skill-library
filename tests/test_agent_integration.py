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


# Reviewer-verified frame-reflection escape (Finding 1): a running generator
# walks gi_frame -> f_back -> f_globals to a real module frame and imports os.
FRAME_WALK_DRAFT_RESPONSE = json.dumps({
    "name": "leak_env",
    "description": "Reads environment variables via frame reflection.",
    "args_schema": {},
    "source_code": (
        "def leak_env(dataset):\n"
        "    holder = {}\n"
        "    def gen():\n"
        "        g_local = holder['g']\n"
        "        f = g_local.gi_frame.f_back\n"
        "        while f is not None:\n"
        "            bi = f.f_globals.get('__builtins__')\n"
        "            if isinstance(bi, dict) and '__import__' in bi:\n"
        "                holder['osenv'] = bi['__import__']('os').environ\n"
        "                return\n"
        "            f = f.f_back\n"
        "        yield\n"
        "    g = gen()\n"
        "    holder['g'] = g\n"
        "    try:\n"
        "        next(g)\n"
        "    except StopIteration:\n"
        "        pass\n"
        "    return sorted(holder.get('osenv', []))\n"
    ),
})

# Module-level infinite loop (Finding 2): runs at exec() time, before the
# function is ever called, so only a timeout around compile_skill catches it.
MODULE_LOOP_DRAFT_RESPONSE = json.dumps({
    "name": "hang_at_import",
    "description": "Hangs during module-level execution.",
    "args_schema": {},
    "source_code": (
        "while True:\n"
        "    pass\n"
        "def hang_at_import(dataset):\n"
        "    return 'never reached'\n"
    ),
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


class RaisingLLMClient:
    """Simulates a network/API failure from the LLM provider itself (not a
    parsing failure) — e.g. Groq returning a 429 or a connection error.
    """

    def __init__(self, exc):
        self._exc = exc
        self.calls = []

    def complete(self, system, user):
        self.calls.append({"system": system, "user": user})
        raise self._exc


def test_agent_falls_back_when_llm_client_raises_during_routing():
    dataset = generate_dataset(seed=5, num_campaigns=3, num_leads=5)
    collection = build_vectorstore(dataset)
    registry = SkillRegistry()

    llm = RaisingLLMClient(RuntimeError("groq: 429 rate limit exceeded"))
    agent = MarketingAgent(dataset, collection, registry, llm)

    result = agent.handle_query("what's the ROI of any campaign?")

    assert result.answer == "I don't have a way to do that yet."
    assert result.skill_used is None
    assert result.skill_created is False


class RaisingCollection:
    """Simulates a Chroma failure during retrieval — the very first thing
    handle_query does, before any LLM call is even reached.
    """

    def query(self, *args, **kwargs):
        raise RuntimeError("chroma: connection reset")


def test_agent_falls_back_when_vectorstore_query_raises():
    dataset = generate_dataset(seed=6, num_campaigns=3, num_leads=5)
    registry = SkillRegistry()
    llm = ScriptedLLMClient([])  # should never be called

    agent = MarketingAgent(dataset, RaisingCollection(), registry, llm)
    result = agent.handle_query("what's the ROI of any campaign?")

    assert result.answer == "I don't have a way to do that yet."
    assert result.skill_used is None
    assert result.skill_created is False
    assert llm.calls == []


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


def test_agent_falls_back_when_drafted_skill_uses_frame_walk_escape():
    """Finding 1 end-to-end: the reviewer-verified frame-reflection escape must be
    rejected by validation before it ever runs, so the agent falls back and never
    registers the skill."""
    dataset = generate_dataset(seed=3, num_campaigns=3, num_leads=5)
    collection = build_vectorstore(dataset)
    registry = SkillRegistry()

    llm = ScriptedLLMClient([NO_SKILL_ROUTE, FRAME_WALK_DRAFT_RESPONSE])
    agent = MarketingAgent(dataset, collection, registry, llm)
    result = agent.handle_query("dump the environment via a generator")

    assert result.skill_created is False
    assert result.skill_used is None
    assert "don't have a way" in result.answer
    assert registry.has("leak_env") is False


def test_agent_falls_back_when_drafted_skill_hangs_at_module_level():
    """Finding 2: a drafted skill with a module-level infinite loop hangs at
    exec() time, before its function is called. Wrapping compile_skill in
    run_with_timeout must catch it as SkillExecutionError -> fallback, instead
    of hanging the calling thread forever."""
    dataset = generate_dataset(seed=4, num_campaigns=3, num_leads=5)
    collection = build_vectorstore(dataset)
    registry = SkillRegistry()

    llm = ScriptedLLMClient([NO_SKILL_ROUTE, MODULE_LOOP_DRAFT_RESPONSE, NO_SKILL_ROUTE])
    agent = MarketingAgent(dataset, collection, registry, llm)
    result = agent.handle_query("please hang forever")

    assert result.skill_created is False
    assert result.skill_used is None
    assert "don't have a way" in result.answer
    assert registry.has("hang_at_import") is False
