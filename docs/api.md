# 接口与用法

## HTTP API

服务默认监听 `0.0.0.0:8900`（`SERVICE_HOST` / `SERVICE_PORT` 可改）。

### `GET /ui`

Vue 统一控制台的提问页。可选择 repo、回答模式、问题类型，支持提交 `/ask` 和
`/diagnose`，并展示回答和原始响应。

同一个 Vue 前端也承载：

| 页面 | 说明 |
|------|------|
| `GET /ui` | 提问 / 诊断测试 |
| `GET /admin/llm-traces` | 模型调用分析 |
| `GET /knowledge` | 模块知识库维护、图谱浏览、问答沉淀 |

### `GET /health`

健康检查。

```bash
curl http://localhost:8900/health
# {"status":"ok"}
```

### `POST /ask`

提问。

内部处理链路见 [ask-diagnose-flow.md](ask-diagnose-flow.md)。简要规则：
`/ask` 进入完整 Agent loop 时会先注入知识图谱和模块知识卡，再由模型按问题决定
是否调用代码检索/读取工具；缓存和 shortcut 命中时会跳过完整 loop。

**请求体**

```json
{
  "question": "要问的问题",
  "use_cache": true,
  "mode": "plain",
  "repo": "gameserver",
  "question_type": "outage_log"
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `question` | string | （必填） | 自然语言问题 |
| `use_cache` | bool | `true` | 是否使用缓存 |
| `mode` | string | `AGENT_DEFAULT_MODE` | 回答/操作等级：`plain`、`technical`、`edit`；必须已在 `AGENT_ALLOWED_MODES` 开启 |
| `repo` | string | `CODE_REPO_DEFAULT` | 目标代码库名称；来自 `CODE_REPOS` |
| `question_type` | string | 自动识别 | 覆盖问题类型策略：`crash_stack`、`outage_log`、`feature_impl`、`config_impl`、`general`；不传或为空时自动识别，若输入缺少对象或目标会直接返回澄清问题 |

**响应**

```json
{
  "answer": "SceneMgr 是场景管理器……",
  "cached": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 回答 |
| `cached` | bool | 本次是否命中缓存 |

**示例**

```bash
curl -X POST http://localhost:8900/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "SceneMgr 是做什么的？"}'
```

多仓库示例：

```bash
curl -X POST http://localhost:8900/ask \
  -H "Content-Type: application/json" \
  -d '{"repo": "ecs", "question": "MoveSystem 是做什么的？"}'
```

### `GET /repos`

列出当前可选代码库：

```json
{
  "default": "gameserver",
  "modes": {
    "default": "plain",
    "allowed": ["plain", "technical"],
    "labels": {
      "plain": "level 1 / non-programmer",
      "technical": "level 2 / programmer"
    }
  },
  "repos": [
    {"name": "gameserver", "path": "/path/to/gameserver"},
    {"name": "ecs", "path": "/path/to/ecs"}
  ]
}
```

### `GET /repos/{repo}/overview`

读取某个仓库的概览/导航缓存。未构建时返回 `available:false`。

构建命令：

```bash
python -m code_agent.retrieval.repo_profile --repo gameserver
python -m code_agent.retrieval.repo_profile --repo ecs
```

### 缓存说明

缓存是 `server.app` 里的**有界 LRU**（问题 → 答案，上限 `CACHE_MAX_ENTRIES`，超出淘汰最久未用）：

- `use_cache=true` 且问题问过 → 直接返回缓存，`cached:true`，**不调 LLM**（省时省 token），且不占并发槽。
- 缓存 key 包含 `repo + mode + question`，不同仓库不会串答案。
- 命中即提到最新位置（LRU）；超过上限淘汰最旧；`CACHE_MAX_ENTRIES=0` 禁用缓存。
- 重启服务即清空；失败的请求不入缓存。
- 空问题返回 `{"answer":"问题不能为空。","cached":false}`。

### 模型调用分析

默认每次有效 `/ask` 请求都会在 `logs/llm/` 下生成一个独立 `.jsonl` 文件，记录请求信息、每轮 LLM 输入 messages、LLM 输出、工具调用结果和最终答案。用 `LLM_TRACE_ENABLED=0` 可关闭，用 `LLM_TRACE_DIR` 可改目录。缓存命中也会生成 trace，但只记录 `cache_hit`，不会有 LLM round。

后台可视化页面：

```text
GET /admin/llm-traces
```

配套 JSON 接口：

| 接口 | 说明 |
|------|------|
| `GET /admin/llm-traces/api` | 列出最近的 trace 文件 |
| `GET /admin/llm-traces/api/{file}` | 读取某个 `.jsonl` trace 文件，按事件返回 |

页面展示 `logs/llm/` 下的请求记录，并按对话轮次整理每次 LLM request/response、tool result、cache hit 和最终答案。

### 代码知识库管理

知识库文件位于 `docs/code-knowledge/<repo>/`。页面入口：

```text
GET /knowledge
```

配套 JSON 接口：

| 接口 | 说明 |
|------|------|
| `GET /knowledge/api?repo=<repo>` | 列出知识卡片 |
| `GET /knowledge/api/{repo}/{file}` | 读取知识卡片，返回 `content`、`body`、`meta` |
| `POST /knowledge/api` | 保存知识卡片 |
| `GET /knowledge/api/graph?repo=<repo>` | 返回知识图谱节点、边和 `relations` 元数据，包含概念、标签、符号、日志、断言、问题类型、资源路径和语义关系 |
| `GET /knowledge/api/common-qa?repo=<repo>` | 列出人工维护的常用问答卡片，可在知识工作台展示，并可被 `/ask` 高置信命中后直接返回 |
| `GET /knowledge/api/qa?repo=<repo>` | 列出后台知识飞轮沉淀的历史问答 |
| `POST /knowledge/api/qa/ask` | 在知识库后台追问模型，返回待人工审核的答案 |
| `POST /knowledge/api/precipitate` | 将人工认可的问答落地为 `Code Playbook` 知识卡 |

推荐沉淀流程：

1. 在知识库页面进入“问答沉淀”。
2. 后台追问模型，得到一版答案。
3. 人工编辑标题、标签和沉淀结论。
4. 确认答案质量后调用 `precipitate` 落地成 Markdown 知识卡。
5. 后续类似问题会通过模块知识卡召回这份 `Code Playbook`，但仍要求 agent 用工具核实当前代码。

常用问答集使用 `docs/code-knowledge/<repo>/common-qa/*.md`。这类卡片需要在
frontmatter 声明 `type: Common QA`、`questions` 和 `aliases`。当用户问题与这些
问法高置信匹配时，`/ask` 会直接返回编辑好的 Markdown 答案，不进入 LLM loop。

图谱 relation 当前定义：

| relation | 含义 | 来源 |
|----------|------|------|
| `links_to` | 一个知识卡片正文通过 Markdown 链接引用另一个知识卡片 | Markdown 内部链接 |
| `tagged_with` | 一个知识卡片在 frontmatter `tags` 中声明了该标签 | 卡片 frontmatter |
| `owns_symbol` | 一个知识卡片在 frontmatter `symbols` 中声明关键类、函数或类型 | 卡片 frontmatter |
| `emits_log` | 一个知识卡片在 frontmatter `logs` 中声明常见日志关键字或错误文本 | 卡片 frontmatter |
| `checks_assert` | 一个知识卡片在 frontmatter `asserts` 中声明常见断言、CHECK 或错误条件 | 卡片 frontmatter |
| `answers_question_type` | 一个知识卡片在 frontmatter `question_types` 中声明适用问题类型 | 卡片 frontmatter |
| `documents_resource` | 一个知识卡片在 frontmatter `resource` 中声明描述的模块路径或代码资源 | 卡片 frontmatter |
| `part_of` | A 是 B 的组成部分 | 卡片 frontmatter |
| `supplements` | A 补充 B 的细节、示例或背景 | 卡片 frontmatter |
| `contradicts` | A 与 B 存在冲突，需要人工复核 | 卡片 frontmatter |
| `supersedes` | A 取代 B，B 不再是最新有效信息 | 卡片 frontmatter |
| `depends_on` | 理解 A 需要先了解 B | 卡片 frontmatter |

### `POST /diagnose`

分析崩溃栈（coredump backtrace），结合代码库定位根因（方向 F）。

内部处理链路见 [ask-diagnose-flow.md](ask-diagnose-flow.md)。`/diagnose` 会先解析
栈帧、日志打印点和断言上下文，再把这些线索交给 Agent 继续分析。

**请求体**

```json
{
  "backtrace": "#0 0x... in SceneMgr::Update (this=0x0) at scene/scenemgr.cpp:142\n#1 ...",
  "log": "可选：相关日志片段",
  "plain": false,
  "repo": "gameserver"
}
```

`backtrace` 和 `log` 可单独或组合提供，但不能同时为空。`plain=true` 时额外返回一句面向非技术同学的白话摘要（多一次 LLM 调用）。coredump-monitor 的 `code-agent` provider 就用它同时拿技术分析 + 白话。

**响应**

| 字段 | 说明 |
|------|------|
| `answer` | 诊断结论（根因 + 排查方向） |
| `frames` | 解析出的栈帧摘要列表 |
| `resolved` | 成功映射到代码的帧数 |
| `total_frames` | 解析出的总帧数 |
| `plain` | 白话摘要（仅 `plain=true` 时非空） |

**示例**

```bash
curl -X POST http://localhost:8900/diagnose \
  -H "Content-Type: application/json" \
  -d '{"backtrace": "#0 0x55ab in SceneMgr::Update (this=0x0) at scene/scenemgr.cpp:142\n#1 0x55cd in Process::Update () at process.cpp:211"}'
```

逐帧用符号索引（方案 2）映射到 `file:line`；带类名的帧（`SceneMgr::Update`）自动收窄同名候选。`log` 字段会被反查到打印它的代码位置（剥时间戳 + 变量归一化 → FTS）；如果日志像断言失败或 ASSERT/CHECK 报错，还会查询离线 assert 索引，把断言语句和上下文作为诊断线索。`backtrace` 与 `log` 可单独或组合提供；两者同时为空返回 400。

### 并发治理

`/ask` 和 `/diagnose` 是异步接口，阻塞的 agent 循环走并发闸门：

| 情况 | 状态码 |
|------|--------|
| 正常 | 200 |
| 上游模型调用失败（预算/鉴权等） | 502 |
| 请求了未知或未开启的 `mode` | 400 / 403 |
| 服务繁忙（并发 + 排队已满，`MAX_CONCURRENCY`/`MAX_QUEUE`） | 503 |
| 单请求超时（`REQUEST_TIMEOUT`，默认 180s） | 504 |

闸门是一个有界线程池（`MAX_CONCURRENCY` 个 worker）：504 超时无法杀死线程，但该线程仍占用 worker，所以真实并发不会被架空（槽位在线程真正结束时才释放）。缓存命中不占并发槽，直接返回。阈值见 [configuration.md](configuration.md)。

## 命令行（`code_agent.interfaces.cli`）

```bash
# 交互模式（会打印工具调用过程）
scripts/cli.sh

# 单次提问
scripts/cli.sh "SceneMgr 是做什么的？"

# 程序员解读模式（需 agent 已开启 technical）
scripts/cli.sh --mode technical "SceneMgr 初始化流程怎么走？"

# 切后端
AGENT_BACKEND=sdk scripts/cli.sh "暴击伤害怎么算？"
```

交互模式下输入 `quit` / `exit` / `q` 或 Ctrl-D 退出。

## 脚本（`scripts/`）

脚本从自身位置解析项目根，可在任意目录调用，首次运行自动建好 venv 并加载 `.env`。

| 脚本 | 作用 |
|------|------|
| `setup.sh` | 创建 venv 并安装依赖 |
| `serve.sh [start\|stop\|restart\|status]` | HTTP 服务（端口 8900）；无参数=前台运行 |
| `mcp.sh [start\|stop\|restart\|status]` | MCP 服务（端口 8901）；无参数=前台运行 |
| `cli.sh ["问题"]` | 命令行交互；带参数则单次提问 |
| `ask.sh [--no-cache] [--mode plain\|technical\|edit] "问题"` | 用 curl 向**运行中**的服务发 `/ask` |

`scripts/common.sh` 是被 source 的公共库（`PROJECT_ROOT`、`VENV_PY`、`ensure_venv`、`run_py`、加载 `.env`、`daemon_*` 守护进程助手），不直接运行。

### 后台运行 / 停止

`serve.sh` 和 `mcp.sh` 支持子命令：

```bash
scripts/serve.sh start      # 后台启动，pid/日志写 logs/serve.{pid,log}
scripts/serve.sh status     # 查看状态
scripts/serve.sh stop       # 停止（先 SIGTERM，10s 后 SIGKILL）
scripts/serve.sh restart    # 重启
scripts/serve.sh            # 不带参数 = 前台运行（Ctrl-C 停）

scripts/mcp.sh start        # 同理，logs/mcp.{pid,log}
scripts/mcp.sh stop
```

pid 文件与日志都在 `logs/` 下（已 gitignore）。`stop`/`start` 幂等：重复 stop 提示未运行，重复 start 提示已运行。

```bash
# 典型流程
scripts/serve.sh start                    # 后台起服务
scripts/ask.sh "玩家生命值字段叫什么？"      # 提问
scripts/ask.sh --mode technical "玩家生命值在哪里扣减？"  # 请求程序员解读模式
scripts/ask.sh --no-cache "同一个问题"      # 绕过缓存
scripts/serve.sh stop                     # 用完停掉
```
