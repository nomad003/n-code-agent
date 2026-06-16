"""FastAPI service exposing the code-comprehension agent.

POST /ask    answer a natural-language question about the target codebase
GET  /health liveness check

A small in-memory cache short-circuits repeated identical questions. The cache
lives behind this layer so it can later be swapped for the offline index (方案 2)
without changing the agent.
"""
import asyncio
import concurrent.futures
from collections import OrderedDict

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import agent
import config

app = FastAPI(title="游戏服务器/战斗/客户端/引擎 代码理解服务")

# Question -> answer. Bounded LRU (move-to-end on hit, evict oldest past the
# cap) so a long-running process can't grow the cache without limit. Reset on
# restart. CACHE_MAX_ENTRIES=0 disables caching.
_CACHE: "OrderedDict[str, str]" = OrderedDict()


def _cache_get(question: str) -> str | None:
    val = _CACHE.get(question)
    if val is not None:
        _CACHE.move_to_end(question)  # mark most-recently-used
    return val


def _cache_put(question: str, answer: str) -> None:
    if config.CACHE_MAX_ENTRIES <= 0:
        return
    _CACHE[question] = answer
    _CACHE.move_to_end(question)
    while len(_CACHE) > config.CACHE_MAX_ENTRIES:
        _CACHE.popitem(last=False)  # evict least-recently-used

# --- Concurrency governance ------------------------------------------------
# Each /ask or /diagnose runs a long blocking LLM loop. We cap how many run at
# once (semaphore), how many may queue (so we shed load with 503 instead of
# piling up unboundedly), and how long any one may take (504).
# A bounded thread pool is the ACTUAL concurrency gate: at most MAX_CONCURRENCY
# blocking agent runs execute at once (the pool itself queues the rest). This is
# robust to the 504 case — a timed-out request's thread can't be killed (Python
# limitation), but it keeps occupying a pool worker, so no NEW work starts beyond
# the cap. `_inflight` (submitted-but-not-finished) drives admission and is only
# ever mutated on the event-loop thread (decrement marshalled via
# call_soon_threadsafe), so it can't drift / race.
_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=config.MAX_CONCURRENCY, thread_name_prefix="agent"
)
_inflight = 0


def _dec_inflight() -> None:
    global _inflight
    _inflight -= 1


async def _run_governed(fn, *args):
    """Run a blocking callable under the concurrency gate, in the thread pool.

    Raises HTTPException(503) when running+queued would exceed the cap, (504) on
    per-request timeout. The slot is freed only when the worker thread actually
    finishes (not when the timeout fires), so the cap reflects real load.
    """
    global _inflight
    if _inflight >= config.MAX_CONCURRENCY + config.MAX_QUEUE:
        raise HTTPException(status_code=503, detail="服务繁忙，请稍后重试")
    _inflight += 1
    loop = asyncio.get_running_loop()
    cfut = _executor.submit(fn, *args)

    # Fires on the worker thread when fn truly returns/raises; marshal the
    # decrement back to the loop thread so all _inflight writes are serialized.
    # If the loop is already closed (e.g. short-lived test loops), fall back to
    # a direct decrement — the GIL makes the single subtraction safe enough.
    def _release(_f):
        try:
            loop.call_soon_threadsafe(_dec_inflight)
        except RuntimeError:
            _dec_inflight()

    cfut.add_done_callback(_release)
    try:
        return await asyncio.wait_for(
            asyncio.wrap_future(cfut), timeout=config.REQUEST_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504, detail=f"请求超时（>{config.REQUEST_TIMEOUT:.0f}s）"
        )


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
    if req.use_cache:
        cached = _cache_get(question)
        if cached is not None:
            return AskResponse(answer=cached, cached=True)

    try:
        result = await _run_governed(agent.answer, question)
    except HTTPException:
        raise  # 503/504 from the gate pass through unchanged
    except Exception as exc:
        # Surface a clean error (e.g. upstream budget/auth) instead of a 500
        # with a stack trace. Failures are never cached.
        raise HTTPException(status_code=502, detail=f"上游模型调用失败: {exc}")

    if req.use_cache:
        _cache_put(question, result)
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
