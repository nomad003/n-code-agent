"""FastAPI service exposing the code-comprehension agent.

POST /ask    answer a natural-language question about the target codebase
GET  /health liveness check

A small in-memory cache short-circuits repeated identical questions. The cache
lives behind this layer so it can later be swapped for the offline index (方案 2)
without changing the agent.
"""
import asyncio

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import agent
import config

app = FastAPI(title="游戏服务器/战斗/客户端/引擎 代码理解服务")

# Question -> answer. Trivial process-local cache; reset on restart.
_CACHE: dict[str, str] = {}

# --- Concurrency governance ------------------------------------------------
# Each /ask or /diagnose runs a long blocking LLM loop. We cap how many run at
# once (semaphore), how many may queue (so we shed load with 503 instead of
# piling up unboundedly), and how long any one may take (504).
_sema = asyncio.Semaphore(config.MAX_CONCURRENCY)
_waiting = 0  # requests currently queued (not yet holding a slot)


async def _run_governed(fn, *args):
    """Run a blocking callable under the concurrency gate, in a worker thread.

    Raises HTTPException(503) when the wait queue is full, (504) on timeout.
    """
    global _waiting
    if _waiting >= config.MAX_QUEUE:
        raise HTTPException(status_code=503, detail="服务繁忙，请稍后重试")
    _waiting += 1
    try:
        await _sema.acquire()
    finally:
        _waiting -= 1  # left the queue (acquired a slot, or cancelled)
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(fn, *args), timeout=config.REQUEST_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail=f"请求超时（>{config.REQUEST_TIMEOUT:.0f}s）"
        )
    finally:
        _sema.release()


class AskRequest(BaseModel):
    question: str
    use_cache: bool = True


class AskResponse(BaseModel):
    answer: str
    cached: bool


class DiagnoseRequest(BaseModel):
    backtrace: str
    log: str = ""           # optional related log snippet
    plain: bool = False     # also return a one-sentence non-technical summary


class DiagnoseResponse(BaseModel):
    answer: str
    frames: list[str]      # parsed frame summaries
    resolved: int          # frames mapped to code via the index
    total_frames: int
    plain: str = ""        # non-technical summary (only when requested)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        return AskResponse(answer="问题不能为空。", cached=False)

    # Cache hit returns immediately, without consuming a concurrency slot.
    if req.use_cache and question in _CACHE:
        return AskResponse(answer=_CACHE[question], cached=True)

    try:
        result = await _run_governed(agent.answer, question)
    except HTTPException:
        raise  # 503/504 from the gate pass through unchanged
    except Exception as exc:
        # Surface a clean error (e.g. upstream budget/auth) instead of a 500
        # with a stack trace. Failures are never cached.
        raise HTTPException(status_code=502, detail=f"上游模型调用失败: {exc}")

    if req.use_cache:
        _CACHE[question] = result
    return AskResponse(answer=result, cached=False)


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose_endpoint(req: DiagnoseRequest) -> DiagnoseResponse:
    """Analyze a coredump backtrace (+ optional log) against the codebase."""
    if not req.backtrace.strip():
        raise HTTPException(status_code=400, detail="backtrace 不能为空")
    import diagnose as diag

    try:
        result = await _run_governed(
            lambda: diag.diagnose(req.backtrace, extra_log=req.log, with_plain=req.plain)
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"诊断失败: {exc}")
    return DiagnoseResponse(**result)


if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
