import json
import re
from dataclasses import dataclass

SKILL_WRITER_SYSTEM_PROMPT = """You write small, safe Python functions for a marketing-analytics agent.

Rules:
- Output ONLY a single JSON object, no prose, no markdown fences.
- JSON keys: name, description, args_schema, source_code.
- name: a snake_case function name.
- description: one sentence describing what it does and its arguments.
- args_schema: an object mapping argument name -> python type name (e.g. {"min_score": "int"}). Do not include "dataset".
- source_code: a single Python function definition. The function's FIRST parameter must be named "dataset" (a dict with keys "campaigns", "leads", "email_metrics" - lists of dicts). Additional parameters must match args_schema, in order. The function must NOT contain any import statements, and must not call eval, exec, open, or __import__. Return a string.
"""


@dataclass
class DraftedSkill:
    name: str
    description: str
    args_schema: dict
    source_code: str


class SkillDraftError(Exception):
    pass


def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise SkillDraftError(f"no JSON object found in LLM output: {raw!r}")
    return json.loads(match.group(0))


def draft_skill(query: str, llm_client, context: list[str] | None = None) -> DraftedSkill:
    context = context or []
    context_block = "\n".join(context) if context else "(no relevant context found)"
    user_prompt = (
        f"Relevant context:\n{context_block}\n\n"
        f"A user asked: {query!r}\nNo existing tool covers this. Draft one."
    )
    raw = llm_client.complete(system=SKILL_WRITER_SYSTEM_PROMPT, user=user_prompt)
    try:
        parsed = _extract_json(raw)
        return DraftedSkill(
            name=parsed["name"],
            description=parsed["description"],
            args_schema=parsed.get("args_schema", {}),
            source_code=parsed["source_code"],
        )
    except (KeyError, json.JSONDecodeError) as e:
        raise SkillDraftError(f"malformed skill draft: {e}")
