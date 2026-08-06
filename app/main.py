# app/main.py
import os
from contextlib import asynccontextmanager
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

# Must run before importing app.security_gate, which reads ALLOWED_ORIGIN
# from the environment at import time. Loads .env into os.environ for local
# dev; no-op if .env is absent (e.g. in Docker/Render, where env vars are
# set directly).
load_dotenv()

from app.agent import MarketingAgent
from app.data_gen import generate_dataset
from app.llm_client import GroqLLMClient
from app.scenarios import get_scenario
from app.security_gate import security_gate
from app import security_gate as security_gate_module
from app.seed_skills import build_seed_registry
from app.vectorstore import build_vectorstore


def check_config() -> None:
    """Refuse to serve if required configuration is missing.

    Called at startup (via the lifespan handler below) so a misconfigured
    deployment fails loudly before /health can ever report green, instead of
    deferring the failure into first-request agent construction.

    Both GROQ_API_KEY and ALLOWED_ORIGIN are required for the service to
    actually work: a missing/placeholder ALLOWED_ORIGIN doesn't raise a
    KeyError (app.security_gate falls back to a placeholder domain), it
    just makes every /chat request 403. That failure mode wouldn't show up
    in /health, so it's checked here explicitly rather than left to be
    discovered at request time.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY environment variable is required")

    allowed_origin = os.environ.get("ALLOWED_ORIGIN", "")
    if not allowed_origin or allowed_origin == security_gate_module.PLACEHOLDER_ORIGIN:
        raise RuntimeError(
            "ALLOWED_ORIGIN environment variable is required "
            "(and must not be left as the placeholder domain)"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_config()
    yield


app = FastAPI(title="Marketing Agent Skill Library", lifespan=lifespan)


@lru_cache
def get_agent() -> MarketingAgent:
    dataset = generate_dataset()
    collection = build_vectorstore(dataset)
    registry = build_seed_registry(dataset)
    llm_client = GroqLLMClient()
    return MarketingAgent(dataset, collection, registry, llm_client)


class ChatRequest(BaseModel):
    scenario_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", dependencies=[Depends(security_gate)])
def chat(payload: ChatRequest, agent: MarketingAgent = Depends(get_agent)):
    scenario = get_scenario(payload.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=400, detail="unknown scenario_id")
    result = agent.handle_query(scenario["query"])
    return {
        "answer": result.answer,
        "skill_used": result.skill_used,
        "skill_created": result.skill_created,
    }
