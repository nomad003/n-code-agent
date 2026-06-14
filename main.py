"""FastAPI service exposing the code-comprehension agent.

POST /ask    answer a natural-language question about the target codebase
GET  /health liveness check

A small in-memory cache short-circuits repeated identical questions. The cache
lives behind this layer so it can later be swapped for the offline index (方案 2)
without changing the agent.
"""
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

import agent
import config

app = FastAPI(title="游戏服务器/战斗/客户端/引擎 代码理解服务")

# Question -> answer. Trivial process-local cache; reset on restart.
_CACHE: dict[str, str] = {}


class AskRequest(BaseModel):
    question: str
    use_cache: bool = True


class AskResponse(BaseModel):
    answer: str
    cached: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        return AskResponse(answer="问题不能为空。", cached=False)

    if req.use_cache and question in _CACHE:
        return AskResponse(answer=_CACHE[question], cached=True)

    result = agent.answer(question)

    if req.use_cache:
        _CACHE[question] = result
    return AskResponse(answer=result, cached=False)


if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
