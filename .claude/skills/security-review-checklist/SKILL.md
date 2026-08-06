---
name: security-review-checklist
description: Review changes to app/sandbox.py, app/validator.py, or app/security_gate.py against known exec-sandbox bypass classes before they merge. Use whenever a diff touches the skill-execution sandbox, the AST validator, or the request security gate.
user-invocable: false
---

# Security review checklist: skill-execution sandbox

This project executes LLM-generated Python (`app/sandbox.py`) after AST-gating
it (`app/validator.py`) and fronts the API with origin/rate-limit checks
(`app/security_gate.py`). Two real bypasses have already been found and
fixed here: an `eval` alias assignment (`g = eval; g(x)`) and dunder-attribute
walks. Treat this surface as adversarial — the input is LLM output, which is
attacker-influenced.

When a diff touches any of the three files above, work through this list
before approving:

## `app/validator.py` (AST gate)

- **Aliasing**: does the check key off the *name* of a builtin (`eval`,
  `exec`, `open`, ...) or the *AST call site*? Assigning a forbidden builtin
  to a new name and calling that (`g = eval; g(x)`) must still be caught —
  verify `ast.Name` references to forbidden names are blocked, not just
  `ast.Call` nodes.
- **Dunder/attribute walks**: can the diff be defeated by chaining
  attribute access to reach `__globals__`, `__class__.__bases__`,
  `__subclasses__()`, or similar to climb back to unrestricted builtins?
- **Forbidden name coverage**: does `FORBIDDEN_CALL_NAMES` /
  `FORBIDDEN_NAME_PREFIXES` still cover the new code paths, or did the
  change add a new way to reach `os`, `sys`, `subprocess`, `socket`,
  `shutil`, `importlib`, or filesystem/network access?
- **String/bytecode tricks**: does validation happen on the parsed AST
  (safe) or on the raw source string (bypassable via string
  concatenation, `chr()` sequences, etc.)?

## `app/sandbox.py` (execution)

- **Builtins isolation**: is `SAFE_BUILTINS` copied fresh per skill
  (`dict(SAFE_BUILTINS)`) or shared/mutable across calls? A skill that
  mutates its own builtins dict must not affect other skills' executions.
- **Timeout enforcement**: does every execution path go through
  `run_with_timeout`, or is there a new call site that can hang the
  process? Confirm the timeout thread is daemonized so it can't block
  shutdown.
- **Resource limits**: does the change introduce a path to unbounded
  memory/CPU/recursion that isn't caught by the timeout (e.g. a
  recursive function with no loop)?

## `app/security_gate.py` (request boundary)

- **Origin check**: is the comparison parsing both URLs and comparing
  `(scheme, netloc)`, or a substring/`in` check that a crafted
  Origin/Referer header could satisfy (e.g. `evil.com/https://real.com`)?
- **Rate limiting**: is the client-identity key (currently IP) still
  correctly derived, and does the window/limit logic still reset
  correctly rather than growing unbounded in `_request_log`?
- **Fail-closed**: if `ALLOWED_ORIGIN` or `GROQ_API_KEY` were unset, does
  startup still fail fast (`check_config`), or did the change add a path
  that silently falls back to permissive behavior?

## Before approving

- Does a test exist that encodes the specific bypass being fixed (see
  `tests/test_validator.py` / `tests/test_sandbox.py` for the existing
  aliasing and dunder-escape regression tests as the pattern to follow)?
- Would this diff have caught the two bypasses already fixed in this
  codebase, if applied retroactively?
