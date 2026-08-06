---
name: gen-test
description: Scaffold a new pytest test file for a module in app/, following this project's existing test conventions (no mocking library, ScriptedLLMClient-style fakes, FastAPI TestClient, direct AST/behavior assertions). Invoke with the target module name, e.g. "/gen-test app/skill_writer.py".
disable-model-invocation: true
---

# gen-test

Scaffold `tests/test_<module>.py` for a module in `app/`, matching the
conventions already used in this repo rather than generic pytest boilerplate.

## Conventions to follow (from existing tests)

- **No mocking library.** LLM calls are faked with a small hand-written
  class that returns canned responses in call order, e.g.
  `ScriptedLLMClient` in `tests/test_agent_integration.py`:

  ```python
  class ScriptedLLMClient:
      def __init__(self, responses):
          self._responses = list(responses)
          self.calls = []

      def complete(self, system, user):
          self.calls.append({"system": system, "user": user})
          return self._responses.pop(0)
  ```

  Reuse this pattern (or import it) for any module that depends on
  `GroqLLMClient` rather than mocking `groq.Groq` directly.

- **FastAPI endpoints** use `fastapi.testclient.TestClient` against the
  real `app.main.app`, not a mocked ASGI app — see `tests/test_main.py`.

- **Security/validator modules** assert on behavior, not implementation:
  write one test per bypass class being guarded against (see
  `tests/test_validator.py`, `tests/test_sandbox.py`) — name tests after
  the specific attack/regression, e.g.
  `test_aliased_eval_call_is_rejected`, not `test_validate_1`.

- **Fixtures/data** use `app.data_gen.generate_dataset(seed=..., ...)`
  for deterministic synthetic CRM data rather than hardcoded dicts, when
  the module under test needs a dataset.

- Flat functions (`def test_...():`), not test classes. No `unittest.TestCase`.

## Steps

1. Read the target module (`app/<module>.py`) to identify its public
   functions/classes and any external dependencies (Groq client, Chroma
   collection, FastAPI routes).
2. Check for an existing partial test file at `tests/test_<module>.py` —
   extend rather than overwrite if one exists.
3. For each public function/class, write one happy-path test and one
   test per edge case that's evident from the implementation (error
   branches, empty input, boundary values) — match the specificity level
   of existing tests in `tests/`, not exhaustive parametrization.
4. If the module touches the sandbox/validator/security-gate surface,
   defer to the `security-review-checklist` skill for the bypass classes
   to cover.
5. Run `pytest tests/test_<module>.py -v` and report pass/fail counts,
   matching this project's existing habit of reporting "N/N passing".
