# Marketing Agent Skill Library

An AI agent that answers marketing-ops questions over synthetic CRM data
using RAG + a real vector database, and drafts, validates, and registers
new tools for itself at runtime when no existing tool covers a request.

Design spec: `vault/docs/superpowers/specs/2026-08-06-marketing-agent-skill-library-design.md`
(in the `claude` vault repo).

## Stack

Python, FastAPI, Groq (LLM), Chroma (embedded vector DB), Docker, Render (free tier).

## Configuration

The service requires two environment variables. Both are checked at
startup — the app refuses to start (and `/health` never gets a chance to
report green) if either is missing, empty, or left as its placeholder
value:

| Variable | Required for | Checked at startup? |
| --- | --- | --- |
| `GROQ_API_KEY` | Answering any `/chat` request | Yes — the app refuses to start if unset or empty |
| `ALLOWED_ORIGIN` | Passing the `/chat` origin check | Yes — the app refuses to start if unset, empty, or left as the placeholder domain |

`ALLOWED_ORIGIN` must be set to the exact scheme+host that will call this
API (e.g. `https://your-portfolio-domain.com`) — the security gate rejects
any request whose Origin/Referer doesn't match it exactly. Startup fails
fast with `ALLOWED_ORIGIN environment variable is required` if it's left
unset or equal to the literal placeholder `https://REPLACE_WITH_YOUR_DOMAIN.com`,
so a forgotten or copy-pasted-unedited value is caught before the service
ever comes up, rather than surfacing later as a silent `403` on every
`/chat` request.

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env     # fill in GROQ_API_KEY and ALLOWED_ORIGIN
pytest -v
uvicorn app.main:app --reload
```

`app/main.py` loads `.env` automatically at import time (via
`python-dotenv`), so values in `.env` reach `os.environ` without needing to
export them in your shell manually.

## Deploying (Render)

`render.yaml` defines a single Docker web service. Both `GROQ_API_KEY` and
`ALLOWED_ORIGIN` are declared with `sync: false`, which means Render will
prompt you to set their values in the dashboard rather than committing
secrets to the repo — set both before the first deploy. Both are enforced
at startup (see Configuration above), so a deploy with either missing will
fail to come up rather than serving traffic in a broken state.

## Known limitations (accepted, not bugs)

- **Skill registry is ephemeral.** It lives in-process only and resets on
  every redeploy/restart (Render's free tier has ephemeral disk). The
  recorded demo walkthrough captures a full create-then-reuse cycle
  independent of what a live visitor's session happens to trigger.
- **Sandbox timeout cannot force-kill a CPU-bound infinite loop.** The
  timeout runs drafted skills in a worker thread; Python has no safe way
  to kill a running thread. This is mitigated by the AST validator
  blocking dangerous primitives before execution, and by a bounded public
  input surface (fixed preset scenarios, not free text) — not solved
  outright, at this budget.
- **First run in a fresh environment needs network access** to download
  Chroma's default embedding model (cached afterward).
