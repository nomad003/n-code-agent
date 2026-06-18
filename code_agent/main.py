"""FastAPI service exposing the code-comprehension agent.

POST /ask    answer a natural-language question about the target codebase
GET  /health liveness check

A small in-memory cache short-circuits repeated identical questions. The cache
lives behind this layer so it can later be swapped for the offline index (方案 2)
without changing the agent.
"""
import asyncio
import concurrent.futures
import os
import re
from collections import OrderedDict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agent
from . import config
from . import llm_trace
from . import module_knowledge
from . import operation_modes
from . import question_intent
from . import response_policy
from . import trace_viewer

app = FastAPI(title="游戏服务器/战斗/客户端/引擎 代码理解服务")
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# (repo, mode, question_type, question) -> answer. Bounded LRU (move-to-end on hit, evict oldest past the
# cap) so a long-running process can't grow the cache without limit. Reset on
# restart. CACHE_MAX_ENTRIES=0 disables caching.
_CACHE: "OrderedDict[tuple[str, str, str, str], str]" = OrderedDict()


def _cache_get(question: str, mode: str, repo: str, question_type: str) -> str | None:
    key = (repo, mode, question_type, question)
    val = _CACHE.get(key)
    if val is not None:
        _CACHE.move_to_end(key)  # mark most-recently-used
    return val


def _cache_put(
    question: str, mode: str, repo: str, question_type: str, answer: str
) -> None:
    if config.CACHE_MAX_ENTRIES <= 0:
        return
    key = (repo, mode, question_type, question)
    _CACHE[key] = answer
    _CACHE.move_to_end(key)
    while len(_CACHE) > config.CACHE_MAX_ENTRIES:
        _CACHE.popitem(last=False)  # evict least-recently-used


def _resolve_request_mode(mode: str | None) -> str:
    try:
        return operation_modes.resolve(
            mode, default=config.AGENT_DEFAULT_MODE, allowed=config.AGENT_ALLOWED_MODES
        )
    except operation_modes.ModeError as exc:
        status = 400 if "unknown operation mode" in str(exc) else 403
        raise HTTPException(status_code=status, detail=str(exc))


def _resolve_request_repo(repo: str | None) -> str:
    try:
        return config.resolve_repo_name(repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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
    mode: str | None = None
    repo: str | None = None
    question_type: str | None = None


class AskResponse(BaseModel):
    answer: str
    cached: bool


class DiagnoseRequest(BaseModel):
    backtrace: str
    log: str = ""           # optional related log snippet
    plain: bool = False     # also return a one-sentence non-technical summary
    repo: str | None = None


class DiagnoseResponse(BaseModel):
    answer: str
    frames: list[str]      # parsed frame summaries
    resolved: int          # frames mapped to code via the index
    total_frames: int
    plain: str = ""        # non-technical summary (only when requested)


class KnowledgeSaveRequest(BaseModel):
    repo: str
    name: str
    content: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/repos")
def repos() -> dict:
    return {
        "default": config.CODE_REPO_DEFAULT,
        "repos": [
            {
                "name": name,
                "path": config.CODE_REPOS[name].path if config.CODE_REPOS else config.TARGET_CODE_PATH,
            }
            for name in config.repo_names()
        ],
    }


@app.get("/repos/{repo}/overview")
def repo_overview(repo: str) -> dict:
    repo_name = _resolve_request_repo(repo)
    with config.use_repo(repo_name):
        from . import repo_profile

        profile = repo_profile.load()
        if profile is None:
            return {
                "repo": repo_name,
                "available": False,
                "message": "profile not built; run `python -m code_agent.repo_profile --repo <name>`",
            }
        return {"repo": repo_name, "available": True, "profile": profile}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        return AskResponse(answer="问题不能为空。", cached=False)
    mode = _resolve_request_mode(req.mode)
    repo = _resolve_request_repo(req.repo)
    try:
        question_type = question_intent.normalize(req.question_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Cache hit returns immediately, without consuming a concurrency slot.
    if req.use_cache:
        cached = _cache_get(question, mode, repo, question_type)
        if cached is not None:
            answer = response_policy.enforce(cached, mode=mode)
            with config.use_repo(repo):
                trace = llm_trace.LLMTrace(question=question, mode=mode, backend="cache")
            trace.write("cache_hit", answer=answer)
            trace.write("request_end", answer=answer)
            return AskResponse(answer=answer, cached=True)

    try:
        result = await _run_governed(
            lambda: agent.answer(
                question,
                mode=mode,
                repo=repo,
                question_type=question_type,
            )
        )
    except HTTPException:
        raise  # 503/504 from the gate pass through unchanged
    except Exception as exc:
        # Surface a clean error (e.g. upstream budget/auth) instead of a 500
        # with a stack trace. Failures are never cached.
        raise HTTPException(status_code=502, detail=f"上游模型调用失败: {exc}")

    result = response_policy.enforce(result, mode=mode)
    if req.use_cache:
        _cache_put(question, mode, repo, question_type, result)
    return AskResponse(answer=result, cached=False)


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose_endpoint(req: DiagnoseRequest) -> DiagnoseResponse:
    """Analyze a coredump backtrace (+ optional log) against the codebase."""
    if not req.backtrace.strip() and not req.log.strip():
        raise HTTPException(status_code=400, detail="backtrace 和 log 不能同时为空")
    from . import diagnose as diag
    repo = _resolve_request_repo(req.repo)

    try:
        result = await _run_governed(
            lambda: _diagnose_in_repo(diag, repo, req.backtrace, req.log, req.plain)
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"诊断失败: {exc}")
    # Diagnosis output is inherently technical (frames, function names, file:line);
    # use the technical policy so legitimate code references aren't stripped.
    result["answer"] = response_policy.enforce(result["answer"], mode="technical")
    result["plain"] = response_policy.enforce(result.get("plain", ""))
    return DiagnoseResponse(**result)


def _diagnose_in_repo(diag, repo: str, backtrace: str, log: str, plain: bool) -> dict:
    with config.use_repo(repo):
        return diag.diagnose(backtrace, extra_log=log, with_plain=plain)


@app.get("/", response_class=HTMLResponse)
def ui_root() -> HTMLResponse:
    return _frontend_app()


@app.get("/ui", response_class=HTMLResponse)
def ask_ui() -> HTMLResponse:
    return _frontend_app()


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_page() -> HTMLResponse:
    return _frontend_app()


@app.get("/knowledge/api")
def knowledge_list(repo: str | None = None) -> dict:
    repo_name = _resolve_request_repo(repo)
    root = _knowledge_repo_dir(repo_name)
    cards = []
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            if not os.path.isfile(path):
                continue
            card = module_knowledge._read_card(path)
            cards.append(
                {
                    "name": name,
                    "title": card.title if card else name[:-3],
                    "tags": card.tags if card else [],
                    "size": os.path.getsize(path),
                    "mtime": int(os.path.getmtime(path)),
                }
            )
    return {"repo": repo_name, "cards": cards}


@app.get("/knowledge/api/{repo}/{name}")
def knowledge_read(repo: str, name: str) -> dict:
    repo_name = _resolve_request_repo(repo)
    path = _knowledge_card_path(repo_name, name)
    try:
        content = open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="knowledge card not found")
    card = module_knowledge._read_card(path)
    return {
        "repo": repo_name,
        "name": os.path.basename(path),
        "title": card.title if card else os.path.basename(path)[:-3],
        "tags": card.tags if card else [],
        "content": content,
    }


@app.post("/knowledge/api")
def knowledge_save(req: KnowledgeSaveRequest) -> dict:
    repo_name = _resolve_request_repo(req.repo)
    path = _knowledge_card_path(repo_name, req.name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(req.content.rstrip() + "\n")
    return {"repo": repo_name, "name": os.path.basename(path), "saved": True}


_CARD_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.md$")


def _knowledge_repo_dir(repo: str) -> str:
    root = os.path.join(config.PROJECT_ROOT, "docs", "code-knowledge", repo)
    return os.path.abspath(root)


def _knowledge_card_path(repo: str, name: str) -> str:
    base = os.path.basename(name or "")
    if not base.endswith(".md"):
        base += ".md"
    if base != name and name.endswith(".md"):
        raise HTTPException(status_code=400, detail="invalid card name")
    if not _CARD_NAME_RE.match(base):
        raise HTTPException(status_code=400, detail="invalid card name")
    root = _knowledge_repo_dir(repo)
    path = os.path.abspath(os.path.join(root, base))
    if path != root and not path.startswith(root + os.sep):
        raise HTTPException(status_code=400, detail="invalid card path")
    return path


@app.get("/admin/llm-traces", response_class=HTMLResponse)
def llm_traces_page() -> HTMLResponse:
    """Visualize per-request LLM trace files under logs/llm."""
    return _frontend_app()


@app.get("/admin/llm-traces/api")
def llm_traces_api() -> dict:
    return {
        "trace_dir": config.LLM_TRACE_DIR,
        "files": trace_viewer.list_traces(),
    }


@app.get("/admin/llm-traces/api/{name}")
def llm_trace_file_api(name: str) -> dict:
    try:
        return trace_viewer.read_trace(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="trace file not found")


def _frontend_app() -> HTMLResponse:
    path = os.path.join(_STATIC_DIR, "app.html")
    with open(path, "r", encoding="utf-8") as fh:
        return HTMLResponse(fh.read())



if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
