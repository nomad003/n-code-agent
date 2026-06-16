"""FastAPI service exposing the code-comprehension agent.

POST /ask    answer a natural-language question about the target codebase
GET  /health liveness check

A small in-memory cache short-circuits repeated identical questions. The cache
lives behind this layer so it can later be swapped for the offline index (方案 2)
without changing the agent.
"""
import uvicorn
from fastapi import FastAPI, HTTPException
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


class DiagnoseRequest(BaseModel):
    backtrace: str
    log: str = ""  # optional related log snippet


class DiagnoseResponse(BaseModel):
    answer: str
    frames: list[str]      # parsed frame summaries
    resolved: int          # frames mapped to code via the index
    total_frames: int


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

    try:
        result = agent.answer(question)
    except Exception as exc:
        # Surface a clean error (e.g. upstream budget/auth/timeout) instead of a
        # 500 with a stack trace. Failures are never cached.
        raise HTTPException(status_code=502, detail=f"上游模型调用失败: {exc}")

    if req.use_cache:
        _CACHE[question] = result
    return AskResponse(answer=result, cached=False)


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose_endpoint(req: DiagnoseRequest) -> DiagnoseResponse:
    """Analyze a coredump backtrace (+ optional log) against the codebase."""
    if not req.backtrace.strip():
        raise HTTPException(status_code=400, detail="backtrace 不能为空")
    import diagnose as diag

    try:
        result = diag.diagnose(req.backtrace, extra_log=req.log)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"诊断失败: {exc}")
    return DiagnoseResponse(**result)


if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
