# app/agent.py
import json
import re
from dataclasses import dataclass

from app.registry import Skill, SkillRegistry
from app.sandbox import compile_skill, run_with_timeout, SkillExecutionError
from app.skill_writer import draft_skill, SkillDraftError
from app.validator import validate_skill_source
from app.vectorstore import query_vectorstore

ROUTING_SYSTEM_PROMPT = """You route marketing-analytics questions to the right tool.

Available tools:
{tool_list}

Given the user's question and some retrieved context, output ONLY a JSON object:
{{"skill": "<tool_name_or_null>", "args": {{...}}}}

Use "skill": null if none of the available tools can answer the question.
"args" must only contain keys that tool declares.
"""

FALLBACK_ANSWER = "I don't have a way to do that yet."


@dataclass
class AgentResponse:
    answer: str
    skill_used: str | None
    skill_created: bool


class RoutingError(Exception):
    pass


def _format_tool_list(registry: SkillRegistry) -> str:
    tools = registry.list_skills()
    if not tools:
        return "(none registered yet)"
    return "\n".join(f"- {s.name}: {s.description}" for s in tools)


def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise RoutingError(f"no JSON object found in routing output: {raw!r}")
    return json.loads(match.group(0))


def route_query(query: str, registry: SkillRegistry, llm_client, context: list[str]) -> tuple[str | None, dict]:
    system = ROUTING_SYSTEM_PROMPT.format(tool_list=_format_tool_list(registry))
    user = "Context:\n" + "\n".join(context) + f"\n\nQuestion: {query}"
    raw = llm_client.complete(system=system, user=user)
    try:
        parsed = _extract_json(raw)
    except json.JSONDecodeError as e:
        raise RoutingError(f"malformed routing output: {e}")
    return parsed.get("skill"), parsed.get("args", {})


class MarketingAgent:
    def __init__(self, dataset: dict, vectorstore_collection, registry: SkillRegistry, llm_client):
        self.dataset = dataset
        self.collection = vectorstore_collection
        self.registry = registry
        self.llm_client = llm_client

    def _bind_drafted_skill(self, compiled_func):
        return lambda **kwargs: compiled_func(self.dataset, **kwargs)

    def _extract_args_for_drafted_skill(self, query: str, drafted, context: list[str]) -> dict:
        temp_registry = SkillRegistry()
        temp_registry.register(Skill(
            name=drafted.name,
            description=drafted.description,
            args_schema=drafted.args_schema,
            source_code=drafted.source_code,
            func=lambda **kwargs: None,
        ))
        try:
            _, args = route_query(query, temp_registry, self.llm_client, context)
        except RoutingError:
            args = {}
        return args

    def handle_query(self, query: str) -> AgentResponse:
        # Outermost safety net: anything not already handled by the narrower
        # try/excepts below (e.g. a raw exception from query_vectorstore, or
        # from llm_client.complete() itself rather than its parsed output)
        # must still fail closed with the plain fallback, never a stack trace.
        try:
            context = query_vectorstore(self.collection, query, n_results=3)

            try:
                skill_name, args = route_query(query, self.registry, self.llm_client, context)
            except RoutingError:
                skill_name, args = None, {}

            if skill_name and self.registry.has(skill_name):
                skill = self.registry.get(skill_name)
                try:
                    answer = run_with_timeout(skill.func, kwargs=args)
                except SkillExecutionError:
                    return AgentResponse(
                        answer="I hit an error running that. Try a different question.",
                        skill_used=skill_name,
                        skill_created=False,
                    )
                return AgentResponse(answer=answer, skill_used=skill_name, skill_created=False)

            try:
                drafted = draft_skill(query, self.llm_client, context=context)
            except SkillDraftError:
                return AgentResponse(answer=FALLBACK_ANSWER, skill_used=None, skill_created=False)

            is_valid, _reason = validate_skill_source(drafted.source_code, drafted.name)
            if not is_valid:
                return AgentResponse(answer=FALLBACK_ANSWER, skill_used=None, skill_created=False)

            draft_args = self._extract_args_for_drafted_skill(query, drafted, context)

            try:
                compiled_func = compile_skill(drafted.source_code, drafted.name)
                bound_func = self._bind_drafted_skill(compiled_func)
                answer = run_with_timeout(bound_func, kwargs=draft_args)
            except SkillExecutionError:
                return AgentResponse(answer=FALLBACK_ANSWER, skill_used=None, skill_created=False)

            # Only register after a successful real execution — never save a skill
            # that was merely validated but not proven to actually run.
            self.registry.register(Skill(
                name=drafted.name,
                description=drafted.description,
                args_schema=drafted.args_schema,
                source_code=drafted.source_code,
                func=bound_func,
            ))

            return AgentResponse(answer=answer, skill_used=drafted.name, skill_created=True)
        except Exception:
            return AgentResponse(answer=FALLBACK_ANSWER, skill_used=None, skill_created=False)
