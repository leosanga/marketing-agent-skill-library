# app/main.py
import os
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from app.agent import MarketingAgent
from app.data_gen import generate_dataset
from app.llm_client import GroqLLMClient
from app.scenarios import get_scenario
from app.security_gate import security_gate
from app.seed_skills import build_seed_registry
from app.vectorstore import build_vectorstore


def check_config() -> None:
    """Refuse to serve if required configuration is missing.

    Called at startup (via the lifespan handler below) so a misconfigured
    deployment fails loudly before /health can ever report green, instead of
    deferring the failure into first-request agent construction.
    """
    if "GROQ_API_KEY" not in os.environ:
        raise RuntimeError("GROQ_API_KEY environment variable is required")


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
