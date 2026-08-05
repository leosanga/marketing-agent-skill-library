from fastapi import FastAPI

app = FastAPI(title="Marketing Agent Skill Library")

@app.get("/health")
def health():
    return {"status": "ok"}
