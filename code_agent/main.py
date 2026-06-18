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
    return HTMLResponse(_ASK_UI_HTML)


@app.get("/ui", response_class=HTMLResponse)
def ask_ui() -> HTMLResponse:
    return HTMLResponse(_ASK_UI_HTML)


@app.get("/knowledge", response_class=HTMLResponse)
def knowledge_page() -> HTMLResponse:
    return HTMLResponse(_KNOWLEDGE_HTML)


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
    return HTMLResponse(_LLM_TRACES_HTML)


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


_ASK_UI_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Code Agent 提问测试</title>
  <style>
    :root { --bg:#f6f7f4; --panel:#fff; --line:#d7dad2; --text:#1f2420; --muted:#687066; --accent:#0f6b5d; --accent2:#174f8a; --error:#a5332f; --soft:#eef4f1; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:14px/1.48 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    header { height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 18px; border-bottom:1px solid var(--line); background:#fbfbf8; }
    h1 { margin:0; font-size:18px; font-weight:700; }
    a { color:var(--accent2); text-decoration:none; }
    nav { display:flex; gap:8px; align-items:center; }
    nav a { border:1px solid var(--line); border-radius:6px; padding:5px 9px; background:#fff; color:var(--muted); font-size:13px; }
    nav a.active { color:#fff; background:var(--accent); border-color:var(--accent); }
    .layout { display:grid; grid-template-columns:360px minmax(0,1fr); min-height:calc(100vh - 56px); }
    aside { border-right:1px solid var(--line); background:#fbfbf8; padding:16px; overflow:auto; }
    main { padding:18px; overflow:auto; }
    label { display:block; margin:12px 0 6px; color:var(--muted); font-size:12px; font-weight:650; }
    select, textarea, input[type=text] { width:100%; border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--text); font:inherit; }
    select, input[type=text] { height:36px; padding:0 9px; }
    textarea { min-height:260px; resize:vertical; padding:10px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; }
    .row { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
    .checks { display:flex; gap:14px; margin:12px 0; color:var(--muted); }
    .checks label { display:flex; align-items:center; gap:6px; margin:0; font-size:13px; font-weight:400; }
    button { height:36px; border:1px solid var(--line); border-radius:6px; padding:0 12px; background:#fff; cursor:pointer; font-weight:650; }
    button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
    .templates { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; }
    .templates button { text-align:left; height:auto; min-height:40px; padding:8px; font-size:12px; font-weight:500; }
    .status { color:var(--muted); margin:0 0 12px; }
    .answer { background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    .answer-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 12px; background:#fbfbf8; border-bottom:1px solid var(--line); }
    .answer-head b { font-size:15px; }
    .badges { display:flex; gap:6px; flex-wrap:wrap; }
    .badge { border:1px solid var(--line); border-radius:999px; padding:2px 8px; background:#fff; color:var(--muted); font-size:12px; }
    .badge.err { color:var(--error); border-color:#e2b8b5; }
    pre { margin:0; padding:14px; white-space:pre-wrap; overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; max-height:70vh; overflow:auto; }
    .hint { color:var(--muted); font-size:12px; margin-top:8px; }
    .split { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; }
    .panel h2 { margin:0 0 8px; font-size:14px; }
    @media (max-width:900px) { .layout { grid-template-columns:1fr; } aside { border-right:0; border-bottom:1px solid var(--line); } .row,.split { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>Code Agent 提问测试</h1>
    <nav>
      <a class="active" href="/ui">提问</a>
      <a href="/admin/llm-traces">Trace</a>
      <a href="/knowledge">知识库</a>
    </nav>
  </header>
  <div class="layout">
    <aside>
      <div class="row">
        <div>
          <label for="repo">仓库</label>
          <select id="repo"></select>
        </div>
        <div>
          <label for="mode">回答模式</label>
          <select id="mode">
            <option value="plain">plain</option>
            <option value="technical" selected>technical</option>
            <option value="edit">edit</option>
          </select>
        </div>
      </div>
      <label for="qtype">问题类型</label>
      <select id="qtype">
        <option value="">自动识别</option>
        <option value="crash_stack">程序 crash 堆栈</option>
        <option value="outage_log">宕机/错误日志</option>
        <option value="feature_impl">功能实现</option>
        <option value="config_impl">配置实现</option>
        <option value="general">通用代码问答</option>
      </select>
      <div class="checks">
        <label><input id="cache" type="checkbox" checked> 使用缓存</label>
        <label><input id="plain" type="checkbox"> 诊断白话摘要</label>
      </div>
      <label>快速模板</label>
      <div class="templates">
        <button data-template="outage">宕机日志：配置缺失 + CHECK_COND</button>
        <button data-template="crash">Crash 堆栈：贴 backtrace</button>
        <button data-template="feature">功能实现：入口/调用链/数据流</button>
        <button data-template="config">配置实现：加载/字段/生效</button>
      </div>
      <div class="hint">问题类型会覆盖自动分类，用于测试不同提示词策略。`/ask` 适合普通提问；日志/堆栈可用 `/diagnose`。</div>
    </aside>
    <main>
      <label for="question">问题 / 日志 / 堆栈</label>
      <textarea id="question" spellcheck="false"></textarea>
      <div class="actions">
        <button class="primary" id="ask">提交 /ask</button>
        <button id="diagnose">提交 /diagnose</button>
        <button id="clear">清空结果</button>
      </div>
      <p class="status" id="status">就绪</p>
      <section class="answer">
        <div class="answer-head">
          <b>回答</b>
          <div class="badges" id="badges"></div>
        </div>
        <pre id="answer">还没有请求。</pre>
      </section>
      <div class="split">
        <section class="panel">
          <h2>请求体</h2>
          <pre id="requestPreview">{}</pre>
        </section>
        <section class="panel">
          <h2>原始响应</h2>
          <pre id="raw">{}</pre>
        </section>
      </div>
    </main>
  </div>
<script>
const repoEl = document.getElementById('repo');
const modeEl = document.getElementById('mode');
const qtypeEl = document.getElementById('qtype');
const cacheEl = document.getElementById('cache');
const plainEl = document.getElementById('plain');
const questionEl = document.getElementById('question');
const statusEl = document.getElementById('status');
const answerEl = document.getElementById('answer');
const rawEl = document.getElementById('raw');
const reqEl = document.getElementById('requestPreview');
const badgesEl = document.getElementById('badges');
const askBtn = document.getElementById('ask');
const diagBtn = document.getElementById('diagnose');

const templates = {
  outage: {
    type: 'outage_log',
    text: `下面是一次宕机日志，请定位根因、错误上下文和排查细节：\n15:04:47:429[61285][0000006133] [Error] GetEnemySkillConfigX(skillconfig.cpp:489) enemy conf skill:[0 921948522 monster_livinglaser_lightstream] not find\n15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:80) [COMBAT] unit: [type=enemy uid=1153743939307804815 tid=302250101 role=0 user= name= sid=0 scene=0-0 map=0], caster:302250101 skill:[921948522 monster_livinglaser_lightstream] not find in conf\n15:04:47:429[61285][0000006133] [Error] InitEnemySkill(skillcore.cpp:81) Check cond: <false> failed\n15:04:47:429[61285][0000006133] [Error] Log_FlushOnExit(LogInit.cpp:347) *************** Error Exit ***************`
  },
  crash: { type:'crash_stack', text:'请分析这个 crash 堆栈的根因、崩溃点和排查方向：\n#0  SceneMgr::Update(float) at scene/scenemgr.cpp:142\n#1  GameLoop::tick() at game/loop.cpp:88' },
  feature: { type:'feature_impl', text:'请分析这个功能是怎么实现的：入口在哪里、核心调用链是什么、关键数据结构有哪些、如何扩展？\n功能/符号：' },
  config: { type:'config_impl', text:'请分析这个配置项如何加载和生效：配置来源、字段含义、加载链路、使用位置、默认/非法值行为、如何验证。\n配置/字段：' }
};

function setBusy(busy) {
  askBtn.disabled = busy;
  diagBtn.disabled = busy;
  statusEl.textContent = busy ? '请求中...' : '就绪';
}
function badge(text, err=false) {
  const b = document.createElement('span');
  b.className = 'badge' + (err ? ' err' : '');
  b.textContent = text;
  badgesEl.appendChild(b);
}
function showResult(payload, ms, endpoint) {
  badgesEl.innerHTML = '';
  badge(endpoint);
  badge(ms + ' ms');
  if (payload.cached !== undefined) badge(payload.cached ? 'cached' : 'fresh');
  answerEl.textContent = payload.answer || payload.detail || JSON.stringify(payload, null, 2);
  rawEl.textContent = JSON.stringify(payload, null, 2);
}
function askBody() {
  return {
    question: questionEl.value,
    repo: repoEl.value || null,
    mode: modeEl.value || null,
    question_type: qtypeEl.value || null,
    use_cache: cacheEl.checked
  };
}
function diagnoseBody() {
  const text = questionEl.value;
  const looksStack = /^\s*#\d+\s+/m.test(text);
  return {
    backtrace: looksStack ? text : '',
    log: looksStack ? '' : text,
    repo: repoEl.value || null,
    plain: plainEl.checked
  };
}
async function post(endpoint, body) {
  reqEl.textContent = JSON.stringify(body, null, 2);
  setBusy(true);
  const started = performance.now();
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    const payload = await res.json();
    showResult(payload, Math.round(performance.now() - started), endpoint);
    if (!res.ok) badge('HTTP ' + res.status, true);
  } catch (e) {
    badgesEl.innerHTML = '';
    badge(endpoint);
    badge('network error', true);
    answerEl.textContent = String(e);
    rawEl.textContent = '{}';
  } finally {
    setBusy(false);
  }
}
async function loadRepos() {
  const res = await fetch('/repos');
  const data = await res.json();
  repoEl.innerHTML = '';
  for (const r of data.repos || []) {
    const o = document.createElement('option');
    o.value = r.name;
    o.textContent = r.name + (r.name === data.default ? ' (default)' : '');
    repoEl.appendChild(o);
  }
  repoEl.value = data.default || (data.repos && data.repos[0] && data.repos[0].name) || '';
}
document.querySelectorAll('[data-template]').forEach(btn => {
  btn.onclick = () => {
    const t = templates[btn.dataset.template];
    qtypeEl.value = t.type;
    questionEl.value = t.text;
  };
});
askBtn.onclick = () => post('/ask', askBody());
diagBtn.onclick = () => post('/diagnose', diagnoseBody());
document.getElementById('clear').onclick = () => {
  answerEl.textContent = '还没有请求。';
  rawEl.textContent = '{}';
  badgesEl.innerHTML = '';
  statusEl.textContent = '就绪';
};
loadRepos();
questionEl.value = templates.outage.text;
qtypeEl.value = templates.outage.type;
</script>
</body>
</html>
"""


_KNOWLEDGE_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Code Agent 知识库</title>
  <style>
    :root { --bg:#f6f7f4; --panel:#fff; --line:#d7dad2; --text:#1f2420; --muted:#687066; --accent:#0f6b5d; --accent2:#174f8a; --error:#a5332f; --soft:#eef4f1; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:14px/1.48 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    header { height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 18px; border-bottom:1px solid var(--line); background:#fbfbf8; }
    h1 { margin:0; font-size:18px; font-weight:700; }
    nav { display:flex; gap:8px; align-items:center; }
    nav a { border:1px solid var(--line); border-radius:6px; padding:5px 9px; background:#fff; color:var(--muted); font-size:13px; text-decoration:none; }
    nav a.active { color:#fff; background:var(--accent); border-color:var(--accent); }
    .layout { display:grid; grid-template-columns:320px minmax(0,1fr); height:calc(100vh - 56px); }
    aside { border-right:1px solid var(--line); background:#fbfbf8; overflow:auto; padding:14px; }
    main { overflow:auto; padding:16px; }
    label { display:block; margin:10px 0 6px; color:var(--muted); font-size:12px; font-weight:650; }
    select, input, textarea { width:100%; border:1px solid var(--line); border-radius:6px; background:#fff; color:var(--text); font:inherit; }
    select, input { height:36px; padding:0 9px; }
    textarea { min-height:calc(100vh - 250px); resize:vertical; padding:12px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:13px; line-height:1.5; }
    button { height:36px; border:1px solid var(--line); border-radius:6px; padding:0 12px; background:#fff; cursor:pointer; font-weight:650; }
    button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
    .actions { display:flex; gap:8px; flex-wrap:wrap; margin:12px 0; }
    .card { padding:10px; border:1px solid var(--line); border-radius:7px; background:#fff; margin:8px 0; cursor:pointer; }
    .card.active, .card:hover { background:var(--soft); border-color:#a8c9bf; }
    .card-title { font-weight:700; }
    .meta { color:var(--muted); font-size:12px; margin-top:4px; display:flex; gap:6px; flex-wrap:wrap; }
    .pill { border:1px solid var(--line); border-radius:999px; padding:1px 7px; background:#fff; }
    .status { color:var(--muted); margin:0 0 10px; }
    .editor-head { display:grid; grid-template-columns:220px minmax(0,1fr); gap:10px; }
    .hint { color:var(--muted); font-size:12px; margin-top:8px; }
    @media (max-width:900px) { .layout { grid-template-columns:1fr; height:auto; } aside { border-right:0; border-bottom:1px solid var(--line); } .editor-head { grid-template-columns:1fr; } textarea { min-height:420px; } }
  </style>
</head>
<body>
  <header>
    <h1>Code Agent 知识库</h1>
    <nav>
      <a href="/ui">提问</a>
      <a href="/admin/llm-traces">Trace</a>
      <a class="active" href="/knowledge">知识库</a>
    </nav>
  </header>
  <div class="layout">
    <aside>
      <label for="repo">仓库</label>
      <select id="repo"></select>
      <div class="actions">
        <button id="newCard">新建卡片</button>
        <button id="reload">刷新</button>
      </div>
      <div id="cards"></div>
      <div class="hint">知识卡保存在 <code>docs/code-knowledge/&lt;repo&gt;/*.md</code>。保存后下一次提问会按关键词自动召回。</div>
    </aside>
    <main>
      <p class="status" id="status">选择或新建一张知识卡。</p>
      <div class="editor-head">
        <div>
          <label for="name">文件名</label>
          <input id="name" placeholder="monster-config.md">
        </div>
        <div>
          <label for="title">标题预览</label>
          <input id="title" disabled>
        </div>
      </div>
      <label for="content">Markdown 内容</label>
      <textarea id="content" spellcheck="false"></textarea>
      <div class="actions">
        <button class="primary" id="save">保存</button>
      </div>
    </main>
  </div>
<script>
const repoEl = document.getElementById('repo');
const cardsEl = document.getElementById('cards');
const nameEl = document.getElementById('name');
const titleEl = document.getElementById('title');
const contentEl = document.getElementById('content');
const statusEl = document.getElementById('status');
let currentName = '';
let cards = [];

function setStatus(s) { statusEl.textContent = s; }
function cardTitle(content, fallback) {
  const m = content.match(/^#\s+(.+)$/m);
  return m ? m[1].trim() : fallback.replace(/\.md$/, '');
}
async function loadRepos() {
  const res = await fetch('/repos');
  const data = await res.json();
  repoEl.innerHTML = '';
  for (const r of data.repos || []) {
    const o = document.createElement('option');
    o.value = r.name;
    o.textContent = r.name + (r.name === data.default ? ' (default)' : '');
    repoEl.appendChild(o);
  }
  repoEl.value = data.default || (data.repos && data.repos[0] && data.repos[0].name) || '';
}
function renderCards() {
  cardsEl.innerHTML = '';
  if (!cards.length) {
    cardsEl.innerHTML = '<div class="hint">暂无知识卡。</div>';
    return;
  }
  for (const c of cards) {
    const div = document.createElement('div');
    div.className = 'card' + (c.name === currentName ? ' active' : '');
    div.onclick = () => openCard(c.name);
    const tags = (c.tags || []).slice(0, 6).map(t => `<span class="pill">${t}</span>`).join('');
    div.innerHTML = `<div class="card-title">${c.title || c.name}</div><div class="meta"><span>${c.name}</span>${tags}</div>`;
    cardsEl.appendChild(div);
  }
}
async function loadCards() {
  setStatus('加载知识卡...');
  const res = await fetch('/knowledge/api?repo=' + encodeURIComponent(repoEl.value));
  const data = await res.json();
  cards = data.cards || [];
  renderCards();
  setStatus(`已加载 ${cards.length} 张知识卡。`);
}
async function openCard(name) {
  currentName = name;
  renderCards();
  setStatus('读取 ' + name + ' ...');
  const res = await fetch(`/knowledge/api/${encodeURIComponent(repoEl.value)}/${encodeURIComponent(name)}`);
  const data = await res.json();
  nameEl.value = data.name || name;
  titleEl.value = data.title || '';
  contentEl.value = data.content || '';
  setStatus('正在编辑 ' + nameEl.value);
}
function newCard() {
  currentName = '';
  renderCards();
  nameEl.value = 'new-module.md';
  titleEl.value = '';
  contentEl.value = `---\ntitle: 新模块知识卡\ntags: 模块, 配置, 排查\n---\n\n# 新模块知识卡\n\n## 核心概念\n\n## 主链路\n\n## 常见问题\n\n## 推荐排查顺序\n`;
  setStatus('新建知识卡，填写后保存。');
}
async function saveCard() {
  const body = {repo: repoEl.value, name: nameEl.value, content: contentEl.value};
  setStatus('保存中...');
  const res = await fetch('/knowledge/api', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)
  });
  const data = await res.json();
  if (!res.ok) {
    setStatus('保存失败：' + (data.detail || res.status));
    return;
  }
  currentName = data.name;
  titleEl.value = cardTitle(contentEl.value, data.name);
  await loadCards();
  setStatus('已保存 ' + data.name);
}
repoEl.onchange = loadCards;
document.getElementById('reload').onclick = loadCards;
document.getElementById('newCard').onclick = newCard;
document.getElementById('save').onclick = saveCard;
contentEl.addEventListener('input', () => { titleEl.value = cardTitle(contentEl.value, nameEl.value || ''); });
loadRepos().then(loadCards);
</script>
</body>
</html>
"""


_LLM_TRACES_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LLM Trace Viewer</title>
  <style>
    :root { color-scheme: light; --bg:#f7f7f4; --panel:#fff; --line:#d8d8d2; --text:#20211f; --muted:#6b6d66; --accent:#17695c; --warn:#9d5a00; --error:#a42525; --tool:#514899; --asst:#2f6fab; }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    header { height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 18px; border-bottom:1px solid var(--line); background:#fbfbf8; }
    h1 { margin:0; font-size:18px; font-weight:650; }
    nav { display:flex; gap:8px; align-items:center; }
    nav a { border:1px solid var(--line); border-radius:6px; padding:5px 9px; background:#fff; color:var(--muted); font-size:13px; text-decoration:none; }
    nav a.active { color:#fff; background:var(--accent); border-color:var(--accent); }
    .top-actions { display:flex; gap:10px; align-items:center; }
    button { border:1px solid var(--line); background:#fff; height:32px; padding:0 10px; border-radius:6px; cursor:pointer; }
    button:hover { border-color:#a8aaa2; }
    .layout { display:grid; grid-template-columns:300px 280px minmax(0,1fr); height:calc(100vh - 56px); }
    aside { border-right:1px solid var(--line); overflow:auto; background:#fbfbf8; }
    aside.rounds { background:#fafaf6; }
    main { overflow:auto; padding:18px; }
    .file { padding:12px 14px; border-bottom:1px solid var(--line); cursor:pointer; }
    .file:hover, .file.active { background:#eef4f1; }
    .file-title { display:flex; gap:8px; align-items:center; justify-content:space-between; font-weight:650; }
    .question { margin-top:6px; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .meta { margin-top:5px; color:var(--muted); font-size:12px; display:flex; gap:8px; flex-wrap:wrap; }
    .badge { border:1px solid var(--line); background:#fff; border-radius:999px; padding:1px 7px; color:var(--muted); }
    .empty { color:var(--muted); padding:24px; }
    .pane-title { padding:10px 14px; font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; border-bottom:1px solid var(--line); background:#fbfbf8; position:sticky; top:0; z-index:1; }
    .round-item { padding:10px 14px; border-bottom:1px solid var(--line); cursor:pointer; display:flex; flex-direction:column; gap:4px; }
    .round-item:hover, .round-item.active { background:#eef4f1; }
    .round-item .row { display:flex; align-items:baseline; justify-content:space-between; gap:8px; }
    .round-item .num { font-weight:650; }
    .round-item .preview { color:var(--muted); font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .round-item .tools { color:var(--muted); font-size:12px; display:flex; gap:6px; flex-wrap:wrap; }
    .round-item .tag { border:1px solid var(--line); background:#fff; border-radius:4px; padding:0 5px; font-size:11px; }
    .round-item .tag.err { border-color:var(--error); color:var(--error); }
    .round-item.summary-row { background:#fbfbf8; }
    .round-item.summary-row.active { background:#eef4f1; }
    .summary { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; margin-bottom:14px; }
    .summary h2 { margin:0 0 12px; font-size:17px; word-break:break-all; }
    .stats { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0 12px; }
    .stat { border:1px solid var(--line); border-radius:6px; padding:6px 10px; background:#fbfbf8; font-size:12px; }
    .stat b { font-size:15px; color:var(--text); margin-right:6px; }
    .answer { border-top:1px solid var(--line); margin-top:10px; padding-top:10px; }
    .answer-label { color:var(--muted); font-size:12px; margin-bottom:4px; }
    .answer-body { white-space:pre-wrap; overflow-wrap:anywhere; max-height:240px; overflow:auto; background:#fbfbf8; border:1px solid var(--line); border-radius:6px; padding:9px; }
    .cache-table { margin-top:12px; border:1px solid var(--line); border-radius:6px; overflow:hidden; font-size:12px; }
    .cache-table .row { display:grid; grid-template-columns:60px 1fr 1fr 1fr 80px; align-items:center; padding:5px 10px; border-bottom:1px solid var(--line); }
    .cache-table .row:last-child { border-bottom:0; }
    .cache-table .row.head { background:#fbfbf8; color:var(--muted); font-weight:650; }
    .cache-table .row.warm { background:#eef4f1; }
    .cache-table .row.cold { background:#fbf3e9; }
    .cache-table .bar { height:6px; background:var(--line); border-radius:3px; overflow:hidden; max-width:120px; }
    .cache-table .bar > div { height:100%; background:var(--accent); }
    .cache-table .pct { color:var(--muted); }
    .audit { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:12px 0; }
    .audit-card { border:1px solid var(--line); border-radius:8px; background:#fbfbf8; padding:12px; }
    .audit-card h3 { margin:0 0 8px; font-size:14px; }
    .audit-list { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0 0; }
    .pill { border:1px solid var(--line); border-radius:999px; background:#fff; padding:2px 8px; font-size:12px; color:var(--muted); }
    .pill.ok { border-color:#a8d0c4; color:#17695c; background:#eef7f3; }
    .pill.warn { border-color:#e2c590; color:#8a570c; background:#fbf3e4; }
    .pill.err { border-color:#e3aaa7; color:var(--error); background:#fff1f0; }
    .tool-seq { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
    .tool-step { border:1px solid var(--line); border-radius:6px; background:#fff; padding:4px 7px; font-size:12px; }
    .tool-step .idx { color:var(--muted); margin-right:4px; }
    .tool-step.err { border-color:#e3aaa7; color:var(--error); }
    .recommend { margin:8px 0 0; padding-left:18px; color:var(--text); }
    .recommend li { margin:3px 0; }
    .timeline { display:flex; flex-direction:column; gap:12px; }
    .round { background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:8px; overflow:hidden; }
    .round-head { padding:10px 14px; display:flex; align-items:center; justify-content:space-between; gap:12px; background:#fbfbf8; border-bottom:1px solid var(--line); font-weight:650; }
    .round-time { color:var(--muted); font-size:12px; font-weight:400; white-space:nowrap; }
    .round-body { padding:12px 14px; display:flex; flex-direction:column; gap:10px; }
    .bubble { border:1px solid var(--line); border-radius:7px; overflow:hidden; }
    .bubble.assistant { border-left:3px solid var(--asst); }
    .bubble.tool { border-left:3px solid var(--tool); }
    .bubble.error { border-left:3px solid var(--error); }
    .bubble-head { padding:6px 10px; background:#f2f2ee; font-size:12px; color:var(--muted); display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }
    .bubble-head .role { font-weight:650; color:var(--text); }
    .bubble-head code { background:#fff; border:1px solid var(--line); padding:1px 5px; border-radius:4px; font-size:11px; }
    .bubble-body { padding:9px 10px; white-space:pre-wrap; overflow-wrap:anywhere; max-height:380px; overflow:auto; }
    .bubble-body.tool-result { background:#fafaf6; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; }
    .args-line { padding:6px 10px; color:var(--muted); font-size:12px; font-family:ui-monospace,monospace; background:#f7f7f3; border-top:1px solid var(--line); word-break:break-all; }
    .event { background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--muted); border-radius:8px; padding:10px 14px; }
    .event.cache_hit, .event.shortcut { border-left-color:var(--warn); }
    .event.request_end { border-left-color:var(--asst); }
    .event.request_error, .event.llm_error, .event.parse_error { border-left-color:var(--error); }
    .event-name { font-weight:650; }
    .event-time { color:var(--muted); font-size:12px; }
    details.dump { margin-top:6px; }
    details.dump summary { cursor:pointer; color:var(--muted); font-size:12px; padding:4px 0; }
    pre { margin:6px 0 0; padding:10px; background:#f5f5f1; border-radius:6px; white-space:pre-wrap; overflow-wrap:anywhere; max-height:420px; overflow:auto; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px; }
    .kv { display:grid; grid-template-columns:120px minmax(0,1fr); gap:6px 10px; }
    .key { color:var(--muted); }
    @media (max-width: 900px) { .layout { grid-template-columns:1fr; height:auto; } aside { max-height:30vh; border-right:0; border-bottom:1px solid var(--line); } main { min-height:40vh; } }
  </style>
</head>
<body>
  <header>
    <h1>LLM Trace Viewer</h1>
    <div class="top-actions">
      <nav>
        <a href="/ui">提问</a>
        <a class="active" href="/admin/llm-traces">Trace</a>
        <a href="/knowledge">知识库</a>
      </nav>
      <button id="refresh">刷新</button>
    </div>
  </header>
  <div class="layout">
    <aside id="files"><div class="empty">加载中...</div></aside>
    <aside class="rounds" id="rounds"><div class="empty">选择一个会话。</div></aside>
    <main id="detail"><div class="empty">选择一个轮次查看详情。</div></main>
  </div>
<script>
const filesEl = document.getElementById('files');
const roundsEl = document.getElementById('rounds');
const detailEl = document.getElementById('detail');
const refreshBtn = document.getElementById('refresh');
let selected = '';            // selected trace file
let selectedKey = 'summary';  // selected entry in the rounds pane
let currentTrace = null;      // last loaded trace JSON
let currentAgg = null;        // aggregated rounds + flat events
let currentStats = null;      // summary stats

function fmtSize(n) {
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1024 / 1024).toFixed(1) + ' MB';
}
function fmtTokens(n) {
  if (!n) return '0';
  if (n < 1000) return String(n);
  if (n < 1000000) return (n / 1000).toFixed(n < 10000 ? 1 : 0) + 'k';
  return (n / 1000000).toFixed(2) + 'M';
}
function fmtDuration(ms) {
  if (ms < 1000) return ms + ' ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + ' s';
  const m = Math.floor(ms / 60000);
  const s = Math.round((ms % 60000) / 1000);
  return m + 'm ' + s + 's';
}
function text(v) {
  if (v === undefined || v === null) return '';
  if (typeof v === 'string') return v;
  return JSON.stringify(v, null, 2);
}
function compact(v) {
  if (v === undefined || v === null) return '';
  if (typeof v === 'string') return v;
  try { return JSON.stringify(v); } catch (_) { return String(v); }
}
function short(s, n=80) {
  s = text(s).replace(/\s+/g, ' ').trim();
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}
function el(tag, cls='', content='') {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (content !== '') node.textContent = content;
  return node;
}
function parseTs(s) {
  if (!s) return null;
  const t = Date.parse(s);
  return Number.isNaN(t) ? null : t;
}

async function loadFiles() {
  const res = await fetch('/admin/llm-traces/api');
  const data = await res.json();
  filesEl.innerHTML = '';
  filesEl.appendChild(el('div', 'pane-title', '会话'));
  if (!data.files.length) {
    filesEl.appendChild(el('div', 'empty', `没有 trace 文件：${data.trace_dir}`));
    return;
  }
  data.files.forEach(f => {
    const item = el('div', 'file' + (f.file === selected ? ' active' : ''));
    const title = el('div', 'file-title');
    title.appendChild(el('span', '', f.file));
    title.appendChild(el('span', 'badge', f.last_event || 'unknown'));
    item.appendChild(title);
    item.appendChild(el('div', 'question', f.question || '(无问题文本)'));
    const meta = el('div', 'meta');
    [f.mtime, f.mode, f.backend, fmtSize(f.size)].forEach(x => meta.appendChild(el('span', '', x || '-')));
    item.appendChild(meta);
    item.onclick = () => loadTrace(f.file);
    filesEl.appendChild(item);
  });
}

async function loadTrace(file) {
  selected = file;
  selectedKey = 'summary';
  currentTrace = null; currentAgg = null; currentStats = null;
  await loadFiles();
  roundsEl.innerHTML = '<div class="empty">加载中...</div>';
  detailEl.innerHTML = '<div class="empty">加载中...</div>';
  const res = await fetch('/admin/llm-traces/api/' + encodeURIComponent(file));
  if (!res.ok) {
    roundsEl.innerHTML = '';
    detailEl.innerHTML = '';
    detailEl.appendChild(el('div', 'empty', '读取失败：' + res.status));
    return;
  }
  currentTrace = await res.json();
  currentAgg = aggregate(currentTrace.rows || []);
  currentStats = summarize(currentTrace, currentAgg);
  renderRoundsList();
  selectEntry('summary');
}

function selectEntry(key) {
  selectedKey = key;
  // Re-style left items without rebuilding (so scroll position holds).
  roundsEl.querySelectorAll('.round-item').forEach(n => {
    n.classList.toggle('active', n.dataset.key === key);
  });
  renderDetail();
}

function renderRoundsList() {
  roundsEl.innerHTML = '';
  roundsEl.appendChild(el('div', 'pane-title', '轮次'));

  const summaryItem = el('div', 'round-item summary-row');
  summaryItem.dataset.key = 'summary';
  const sRow = el('div', 'row');
  sRow.appendChild(el('span', 'num', '会话概览'));
  sRow.appendChild(el('span', 'preview', `${currentStats.rounds} 轮`));
  summaryItem.appendChild(sRow);
  summaryItem.appendChild(el('div', 'preview', currentTrace.question || '(无问题文本)'));
  const sMeta = el('div', 'tools');
  if (currentStats.toolTotal) sMeta.appendChild(el('span', 'tag', `工具 ${currentStats.toolTotal}`));
  if (currentStats.duration !== null) sMeta.appendChild(el('span', 'tag', fmtDuration(currentStats.duration)));
  if (currentStats.hadUsage) {
    const cacheLabel = currentStats.cachedTokens
      ? `${fmtTokens(currentStats.totalTokens)} tok · cached ${fmtTokens(currentStats.cachedTokens)}`
      : `${fmtTokens(currentStats.totalTokens)} tok`;
    sMeta.appendChild(el('span', 'tag', cacheLabel));
  }
  if (currentStats.errors) sMeta.appendChild(el('span', 'tag err', `错误 ${currentStats.errors}`));
  summaryItem.appendChild(sMeta);
  summaryItem.onclick = () => selectEntry('summary');
  roundsEl.appendChild(summaryItem);

  // Flat events that ran before any round.
  const earlyFlat = currentStats.rounds === 0
    ? currentAgg.flat
    : currentAgg.flat.filter(r => r.event === 'cache_hit' || r.event === 'shortcut');
  earlyFlat.forEach((r, idx) => roundsEl.appendChild(flatItem(r, `fe${idx}`)));

  currentAgg.rounds.forEach(g => roundsEl.appendChild(roundItem(g)));

  const lateFlat = currentStats.rounds === 0
    ? []
    : currentAgg.flat.filter(r => !(r.event === 'cache_hit' || r.event === 'shortcut'));
  lateFlat.forEach((r, idx) => roundsEl.appendChild(flatItem(r, `fl${idx}`)));
}

function roundItem(g) {
  const key = 'r' + g.round;
  const item = el('div', 'round-item');
  item.dataset.key = key;
  const row = el('div', 'row');
  row.appendChild(el('span', 'num', '轮 #' + g.round));
  const ts = (g.response && g.response.ts) || (g.request && g.request.ts) || '';
  if (ts) row.appendChild(el('span', 'preview', ts.slice(11)));  // HH:MM:SS.mmm
  item.appendChild(row);

  const msg = (g.response && g.response.message) || {};
  const preview = (msg.content && String(msg.content).trim())
    || (g.request && g.request.messages && g.request.messages.length
        ? `(${g.request.messages.length} 条上下文)` : '');
  if (preview) item.appendChild(el('div', 'preview', short(preview, 90)));

  const tools = el('div', 'tools');
  const calls = msg.tool_calls || [];
  const counts = {};
  calls.forEach(c => {
    const name = (c.function && c.function.name) || c.name || 'tool';
    counts[name] = (counts[name] || 0) + 1;
  });
  Object.entries(counts).forEach(([name, n]) => {
    tools.appendChild(el('span', 'tag', n > 1 ? `${name} ×${n}` : name));
  });
  const errs = g.tools.filter(t => t.is_error).length;
  if (errs) tools.appendChild(el('span', 'tag err', `${errs} 错误`));
  const usage = g.response && g.response.usage;
  if (usage) {
    const inTok = usage.prompt_tokens || usage.input_tokens || 0;
    const outTok = usage.completion_tokens || usage.output_tokens || 0;
    const cached = (usage.cache_read_input_tokens || 0)
      + ((usage.prompt_tokens_details && usage.prompt_tokens_details.cached_tokens) || 0);
    if (inTok || outTok) {
      const label = cached
        ? `in ${fmtTokens(inTok)} (${fmtTokens(cached)} cached) · out ${fmtTokens(outTok)}`
        : `in ${fmtTokens(inTok)} · out ${fmtTokens(outTok)}`;
      tools.appendChild(el('span', 'tag', label));
    }
  }
  if (tools.children.length) item.appendChild(tools);

  item.onclick = () => selectEntry(key);
  return item;
}

function flatItem(row, key) {
  const item = el('div', 'round-item');
  item.dataset.key = key;
  const r = el('div', 'row');
  r.appendChild(el('span', 'num', row.event || 'event'));
  if (row.ts) r.appendChild(el('span', 'preview', row.ts.slice(11)));
  item.appendChild(r);
  const tip = row.answer || row.text || row.error || '';
  if (tip) item.appendChild(el('div', 'preview', short(tip, 90)));
  item.onclick = () => selectEntry(key);
  return item;
}

function renderDetail() {
  detailEl.innerHTML = '';
  if (!currentTrace) return;
  if (selectedKey === 'summary') { detailEl.appendChild(renderSummary()); return; }
  if (selectedKey.startsWith('r')) {
    const n = Number(selectedKey.slice(1));
    const g = currentAgg.rounds.find(x => x.round === n);
    if (g) detailEl.appendChild(renderRound(g));
    return;
  }
  if (selectedKey.startsWith('fe') || selectedKey.startsWith('fl')) {
    const isEarly = selectedKey.startsWith('fe');
    const idx = Number(selectedKey.slice(2));
    const pool = isEarly
      ? (currentStats.rounds === 0 ? currentAgg.flat : currentAgg.flat.filter(r => r.event === 'cache_hit' || r.event === 'shortcut'))
      : currentAgg.flat.filter(r => !(r.event === 'cache_hit' || r.event === 'shortcut'));
    const row = pool[idx];
    if (row) detailEl.appendChild(renderFlatEvent(row));
  }
}

function renderSummary() {
  const trace = currentTrace, stats = currentStats;
  const summary = el('section', 'summary');
  summary.appendChild(el('h2', '', trace.question || trace.file));
  const kv = el('div', 'kv');
  [['模式', trace.mode], ['后端', trace.backend], ['模型', trace.model], ['文件', trace.file]].forEach(([k, v]) => {
    kv.appendChild(el('div', 'key', k));
    kv.appendChild(el('div', '', text(v)));
  });
  summary.appendChild(kv);

  const statsRow = el('div', 'stats');
  const statChip = (label, value) => {
    const s = el('div', 'stat');
    s.appendChild(el('b', '', String(value)));
    s.appendChild(document.createTextNode(label));
    return s;
  };
  statsRow.appendChild(statChip('轮', stats.rounds));
  statsRow.appendChild(statChip('工具调用', stats.toolTotal));
  if (stats.duration !== null) statsRow.appendChild(statChip('耗时', fmtDuration(stats.duration)));
  if (stats.hadUsage) {
    statsRow.appendChild(statChip('总 token', fmtTokens(stats.totalTokens)));
    statsRow.appendChild(statChip(`cached (输入 ${fmtTokens(stats.promptTokens)})`, fmtTokens(stats.cachedTokens)));
    statsRow.appendChild(statChip('输出 token', fmtTokens(stats.completionTokens)));
    if (stats.promptTokens) {
      const rate = (stats.cachedTokens / stats.promptTokens * 100).toFixed(0);
      statsRow.appendChild(statChip('缓存命中率', `${rate}%`));
    }
  }
  if (stats.errors) statsRow.appendChild(statChip('错误', stats.errors));
  Object.entries(stats.toolCounts).forEach(([name, n]) => {
    const s = el('div', 'stat');
    s.appendChild(el('b', '', String(n)));
    s.appendChild(document.createTextNode(' ' + name));
    statsRow.appendChild(s);
  });
  summary.appendChild(statsRow);

  if (stats.audit) {
    summary.appendChild(renderAudit(stats.audit));
  }

  // Per-round cache breakdown — exposes whether prompt caching is actually
  // being honored by the proxy. First round should be ~0% (cache is being
  // written); rounds 2+ should approach 100% of the static prefix.
  const rounds = currentAgg.rounds.filter(g => g.response && g.response.usage);
  if (rounds.length >= 2) {
    const table = el('div', 'cache-table');
    const head = el('div', 'row head');
    ['轮', '输入', 'cached', '输出', '命中率'].forEach(h =>
      head.appendChild(el('div', '', h))
    );
    table.appendChild(head);
    rounds.forEach(g => {
      const u = g.response.usage;
      const inTok = u.prompt_tokens || u.input_tokens || 0;
      const outTok = u.completion_tokens || u.output_tokens || 0;
      const cached = (u.cache_read_input_tokens || 0)
        + ((u.prompt_tokens_details && u.prompt_tokens_details.cached_tokens) || 0);
      const pct = inTok ? Math.round(cached / inTok * 100) : 0;
      const row = el('div', 'row ' + (pct >= 50 ? 'warm' : (cached ? '' : 'cold')));
      row.appendChild(el('div', '', '#' + g.round));
      row.appendChild(el('div', '', fmtTokens(inTok)));
      const cachedCell = el('div', '');
      cachedCell.appendChild(document.createTextNode(fmtTokens(cached) + ' '));
      const bar = el('div', 'bar');
      const fill = document.createElement('div');
      fill.style.width = pct + '%';
      bar.appendChild(fill);
      cachedCell.appendChild(bar);
      row.appendChild(cachedCell);
      row.appendChild(el('div', '', fmtTokens(outTok)));
      row.appendChild(el('div', 'pct', pct + '%'));
      table.appendChild(row);
    });
    summary.appendChild(table);
  }

  if (stats.finalAnswer) {
    const ans = el('div', 'answer');
    ans.appendChild(el('div', 'answer-label', '最终答案'));
    ans.appendChild(el('div', 'answer-body', stats.finalAnswer));
    summary.appendChild(ans);
  }
  return summary;
}

function renderAudit(audit) {
  const wrap = el('div', 'audit');
  const left = el('div', 'audit-card');
  left.appendChild(el('h3', '', '最佳实践审计'));
  const meta = el('div', 'audit-list');
  meta.appendChild(el('span', 'pill ok', audit.intentLabel));
  meta.appendChild(el('span', audit.statusClass, audit.status));
  if (audit.missing.length) meta.appendChild(el('span', 'pill warn', `缺 ${audit.missing.length} 个推荐工具`));
  if (audit.repeated.length) meta.appendChild(el('span', 'pill warn', `重复 ${audit.repeated.length} 类工具`));
  if (audit.errors) meta.appendChild(el('span', 'pill err', `工具错误 ${audit.errors}`));
  left.appendChild(meta);
  if (audit.recommendations.length) {
    const ul = el('ul', 'recommend');
    audit.recommendations.forEach(r => ul.appendChild(el('li', '', r)));
    left.appendChild(ul);
  }

  const right = el('div', 'audit-card');
  right.appendChild(el('h3', '', '工具调用顺序'));
  if (audit.toolSequence.length) {
    const seq = el('div', 'tool-seq');
    audit.toolSequence.forEach((t, i) => {
      const s = el('span', 'tool-step' + (t.error ? ' err' : ''));
      s.appendChild(el('span', 'idx', String(i + 1)));
      s.appendChild(document.createTextNode(t.name));
      seq.appendChild(s);
    });
    right.appendChild(seq);
  } else {
    right.appendChild(el('div', 'empty', '没有工具调用，可能是 cache/shortcut 或模型直接回答。'));
  }
  if (audit.expected.length) {
    const expected = el('div', 'audit-list');
    audit.expected.forEach(name => {
      expected.appendChild(el('span', audit.used.has(name) ? 'pill ok' : 'pill', name));
    });
    right.appendChild(expected);
  }
  wrap.appendChild(left);
  wrap.appendChild(right);
  return wrap;
}

// --- aggregation ----------------------------------------------------------
// Group rows by their `round` field; tool_results are keyed by tool_call_id so
// they sit next to the assistant message that asked for them. Anything without
// a round (cache_hit, shortcut, request_end, sdk_*, errors) goes to a flat list.

function aggregate(rows) {
  const rounds = new Map();   // round -> { request, response, tools: Map<id, row> }
  const loose = [];           // events not tied to a round
  for (const r of rows) {
    if (r.event === 'tool_result') {
      // Tool results carry tool_call_id but not always a round; match later.
      loose.push(r);
      continue;
    }
    if (!r.round) { loose.push(r); continue; }
    let g = rounds.get(r.round);
    if (!g) { g = { round: r.round, request: null, response: null, tools: [], events: [] }; rounds.set(r.round, g); }
    if (r.event === 'llm_request') g.request = r;
    else if (r.event === 'llm_response') g.response = r;
    else g.events.push(r);
  }
  // Distribute tool_results: a tool_result follows the round whose assistant
  // message emitted its tool_call_id; fall back to a separate event card.
  const orphanTools = [];
  for (const tr of loose.filter(r => r.event === 'tool_result')) {
    let placed = false;
    for (const g of rounds.values()) {
      const calls = g.response && g.response.message && g.response.message.tool_calls;
      if (calls && calls.some(c => c && c.id === tr.tool_call_id)) {
        g.tools.push(tr); placed = true; break;
      }
    }
    if (!placed) orphanTools.push(tr);
  }
  const flat = loose.filter(r => r.event !== 'tool_result').concat(orphanTools);
  return { rounds: [...rounds.values()].sort((a, b) => a.round - b.round), flat };
}

function summarize(trace, agg) {
  const rows = trace.rows || [];
  const first = rows[0] || {};
  const last = rows[rows.length - 1] || {};
  const t0 = parseTs(first.ts);
  const t1 = parseTs(last.ts);
  const duration = (t0 !== null && t1 !== null) ? Math.max(0, t1 - t0) : null;

  const toolCounts = {};
  let toolTotal = 0;
  for (const r of rows) {
    if (r.event === 'tool_result' || r.event === 'sdk_tool_use') {
      const name = r.name || '(unknown)';
      toolCounts[name] = (toolCounts[name] || 0) + 1;
      toolTotal++;
    }
  }
  let errors = 0;
  for (const r of rows) {
    if (r.event === 'llm_error' || r.event === 'request_error' || r.event === 'parse_error') errors++;
    else if (r.event === 'tool_result' && r.is_error) errors++;
  }
  // Token accounting across all llm_response usages. Different providers expose
  // the cached-prompt count under different keys; sum whichever exists.
  let promptTokens = 0, completionTokens = 0, totalTokens = 0, cachedTokens = 0;
  let hadUsage = false;
  for (const r of rows) {
    if (r.event !== 'llm_response' || !r.usage) continue;
    hadUsage = true;
    const u = r.usage;
    promptTokens += (u.prompt_tokens || u.input_tokens || 0);
    completionTokens += (u.completion_tokens || u.output_tokens || 0);
    totalTokens += (u.total_tokens || 0);
    const cached = (u.cache_read_input_tokens || 0)
      + ((u.prompt_tokens_details && u.prompt_tokens_details.cached_tokens) || 0);
    cachedTokens += cached;
  }
  if (hadUsage && !totalTokens) totalTokens = promptTokens + completionTokens;

  let finalAnswer = '';
  for (let i = rows.length - 1; i >= 0; i--) {
    if (rows[i].event === 'request_end' && rows[i].answer) { finalAnswer = rows[i].answer; break; }
    if (rows[i].event === 'cache_hit' && rows[i].answer) { finalAnswer = rows[i].answer; break; }
    if (rows[i].event === 'shortcut' && rows[i].answer) { finalAnswer = rows[i].answer; break; }
  }
  if (!finalAnswer && agg.rounds.length) {
    const lastResp = agg.rounds[agg.rounds.length - 1].response;
    if (lastResp && lastResp.message && lastResp.message.content) finalAnswer = lastResp.message.content;
  }
  return {
    duration, toolCounts, toolTotal, errors, finalAnswer,
    rounds: agg.rounds.length,
    hadUsage, promptTokens, completionTokens, totalTokens, cachedTokens,
    audit: buildAudit(trace, agg, toolCounts, errors),
  };
}

const INTENT_RULES = {
  '程序 crash 堆栈分析': {
    expected: ['resolve_frame', 'read_file'],
    optional: ['find_assert_context', 'find_log_source', 'grep_code'],
    advice: 'crash 堆栈应先定位业务栈帧，再读崩溃点上下文，并结合上下游帧判断调用关系。'
  },
  '宕机/错误日志分析': {
    expected: ['find_assert_context', 'find_log_source', 'read_file'],
    optional: ['grep_code'],
    advice: '宕机日志应先反查断言/打印点，再读错误分支上下文，最后给出触发条件和排查顺序。'
  },
  '功能实现分析': {
    expected: ['repo_overview', 'grep_code', 'find_symbol', 'read_file'],
    optional: ['glob', 'list_dir'],
    advice: '功能实现应先缩小模块范围，再按入口、核心分支、下游调用和数据流追踪。'
  },
  '配置实现分析': {
    expected: ['glob', 'grep_code', 'read_file'],
    optional: ['repo_overview', 'find_symbol'],
    advice: '配置实现应覆盖配置来源、加载/校验/缓存链路、业务读取点和非法值行为。'
  },
  '通用代码问答': {
    expected: ['grep_code', 'read_file'],
    optional: ['repo_overview', 'find_symbol', 'glob'],
    advice: '通用问题应先低成本缩小范围，再读取关键上下文，并区分事实和推断。'
  }
};

function buildAudit(trace, agg, toolCounts, errors) {
  const intentLabel = detectIntent(trace, agg);
  const rule = INTENT_RULES[intentLabel] || INTENT_RULES['通用代码问答'];
  const toolSequence = [];
  for (const g of agg.rounds) {
    for (const t of g.tools) {
      toolSequence.push({name: t.name || '(unknown)', error: !!t.is_error});
    }
  }
  const used = new Set(toolSequence.map(t => t.name));
  const missing = rule.expected.filter(name => !used.has(name));
  const repeated = Object.entries(toolCounts)
    .filter(([name, n]) => n >= 3 && !['read_file'].includes(name))
    .map(([name]) => name);
  const recommendations = [];
  if (missing.length) recommendations.push(`建议补充推荐工具：${missing.join('、')}。`);
  if (repeated.length) recommendations.push(`存在重复检索：${repeated.join('、')}，可先改用 files/count 或收窄 path。`);
  if (errors) recommendations.push('存在工具错误，需要检查参数、路径或索引是否可用。');
  if (!toolSequence.length) recommendations.push('没有工具调用；若不是 cache/shortcut，需确认模型是否过早直接回答。');
  if (!recommendations.length) recommendations.push(rule.advice);
  const status = errors ? '需要复核' : (missing.length || repeated.length ? '可优化' : '执行良好');
  const statusClass = errors ? 'pill err' : (missing.length || repeated.length ? 'pill warn' : 'pill ok');
  return {
    intentLabel,
    expected: rule.expected,
    optional: rule.optional,
    used,
    missing,
    repeated,
    errors,
    status,
    statusClass,
    recommendations,
    toolSequence,
  };
}

function detectIntent(trace, agg) {
  for (const g of agg.rounds) {
    const messages = (g.request && g.request.messages) || [];
    const sys = messages.find(m => m.role === 'system');
    const content = messageContentText(sys && sys.content);
    const m = content.match(/当前问题类型：([^\n]+)/);
    if (m) return m[1].trim();
  }
  const q = (trace.question || '').toLowerCase();
  if (/^\s*#\d+\s+/m.test(trace.question || '') || q.includes('backtrace') || q.includes('sigsegv') || q.includes('堆栈')) return '程序 crash 堆栈分析';
  if (q.includes('assert') || q.includes('error') || q.includes('fatal') || q.includes('日志') || q.includes('宕机')) return '宕机/错误日志分析';
  if (q.includes('配置') || q.includes('config') || q.includes('字段')) return '配置实现分析';
  if (q.includes('实现') || q.includes('流程') || q.includes('调用链')) return '功能实现分析';
  return '通用代码问答';
}

function messageContentText(content) {
  if (!content) return '';
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.map(part => typeof part === 'string' ? part : (part && part.text) || '').join('\n');
  }
  return text(content);
}

function renderRound(g) {
  const card = el('section', 'round');
  const head = el('div', 'round-head');
  const tools = g.tools.length;
  const label = `轮 #${g.round}` + (tools ? `  ·  ${tools} 个工具调用` : '');
  head.appendChild(el('span', '', label));
  const ts = (g.request && g.request.ts) || (g.response && g.response.ts) || '';
  if (ts) head.appendChild(el('span', 'round-time', ts));
  card.appendChild(head);

  const body = el('div', 'round-body');
  const msg = (g.response && g.response.message) || {};
  const toolCalls = msg.tool_calls || [];

  // Assistant text (if any).
  if (msg.content && String(msg.content).trim()) {
    const b = el('div', 'bubble assistant');
    const bh = el('div', 'bubble-head');
    bh.appendChild(el('span', 'role', 'assistant'));
    if (toolCalls.length) bh.appendChild(el('span', '', `+ ${toolCalls.length} 个 tool_calls`));
    b.appendChild(bh);
    b.appendChild(el('div', 'bubble-body', String(msg.content)));
    body.appendChild(b);
  }

  // Each tool_call paired with its matching tool_result.
  const resultsByCallId = new Map();
  g.tools.forEach(t => resultsByCallId.set(t.tool_call_id, t));
  toolCalls.forEach(tc => {
    const fn = tc.function || {};
    const result = resultsByCallId.get(tc.id);
    const isErr = result && result.is_error;
    const b = el('div', 'bubble tool' + (isErr ? ' error' : ''));
    const bh = el('div', 'bubble-head');
    bh.appendChild(el('span', 'role', fn.name || tc.name || 'tool'));
    if (result) bh.appendChild(el('span', '', isErr ? 'error' : 'ok'));
    if (tc.id) {
      const code = document.createElement('code');
      code.textContent = String(tc.id).slice(0, 16);
      bh.appendChild(code);
    }
    b.appendChild(bh);

    let argsObj = null;
    if (result && result.arguments) argsObj = result.arguments;
    else if (fn.arguments) {
      try { argsObj = JSON.parse(fn.arguments); }
      catch (_) { argsObj = fn.arguments; }
    }
    if (argsObj !== null && argsObj !== undefined && argsObj !== '') {
      b.appendChild(el('div', 'args-line', compact(argsObj)));
    }
    const resBody = el('div', 'bubble-body tool-result');
    resBody.textContent = result ? text(result.result) : '(没有匹配的 tool_result)';
    b.appendChild(resBody);
    body.appendChild(b);
  });

  // Tool results without a matching tool_call entry (defensive fallback).
  g.tools.forEach(t => {
    if (toolCalls.some(c => c && c.id === t.tool_call_id)) return;
    const b = el('div', 'bubble tool' + (t.is_error ? ' error' : ''));
    const bh = el('div', 'bubble-head');
    bh.appendChild(el('span', 'role', t.name || 'tool'));
    bh.appendChild(el('span', '', t.is_error ? 'error' : 'ok'));
    b.appendChild(bh);
    if (t.arguments) b.appendChild(el('div', 'args-line', compact(t.arguments)));
    const resBody = el('div', 'bubble-body tool-result');
    resBody.textContent = text(t.result);
    b.appendChild(resBody);
    body.appendChild(b);
  });

  // Round-level errors and other extras.
  g.events.forEach(e => body.appendChild(renderFlatEvent(e)));

  // Full request dump folded away — only opened when needed.
  if (g.request) {
    const d = document.createElement('details');
    d.className = 'dump';
    const messages = g.request.messages || [];
    d.appendChild(el('summary', '', `完整请求消息 (${messages.length} 条) / tools / 参数`));
    d.appendChild(el('pre', '', text({
      messages,
      tools: g.request.tools,
      tool_choice: g.request.tool_choice,
      temperature: g.request.temperature,
      timeout: g.request.timeout,
    })));
    body.appendChild(d);
  }
  card.appendChild(body);
  return card;
}

function renderFlatEvent(row) {
  const card = el('section', 'event ' + (row.event || 'unknown'));
  const head = el('div', 'bubble-head');
  head.appendChild(el('span', 'event-name', row.event || 'event'));
  if (row.ts) head.appendChild(el('span', 'event-time', row.ts));
  card.appendChild(head);
  if (row.event === 'cache_hit' || row.event === 'shortcut' || row.event === 'request_end') {
    if (row.answer) card.appendChild(el('div', 'bubble-body', String(row.answer)));
  } else if (row.event === 'sdk_text' && row.text) {
    card.appendChild(el('div', 'bubble-body', String(row.text)));
  } else if (row.event === 'sdk_tool_use') {
    const k = el('div', 'kv');
    k.appendChild(el('div', 'key', '工具'));
    k.appendChild(el('div', '', text(row.name)));
    k.appendChild(el('div', 'key', '参数'));
    k.appendChild(el('div', '', compact(row.input)));
    card.appendChild(k);
  } else {
    const copy = {...row};
    delete copy.ts; delete copy.request_id; delete copy.event;
    if (Object.keys(copy).length) card.appendChild(el('pre', '', text(copy)));
  }
  return card;
}

refreshBtn.onclick = loadFiles;
loadFiles();
</script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
