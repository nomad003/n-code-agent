# 配置

所有配置集中在 `config.py`，**每一项都有默认值，且都可被同名环境变量覆盖**。无需改代码，临时改用 `VAR=值 scripts/serve.sh` 即可。

## `.env`

把密钥/路径放到 `.env`（已被 `.gitignore` 排除，不会提交）。`scripts/` 下的脚本会自动加载 `.env`，且**已有环境变量优先**（不会覆盖你显式 `export` 的值）。

```bash
cp .env.example .env     # 填入 LLM_API_KEY，按需改 TARGET_CODE_PATH / CODE_REPOS / AGENT_BACKEND
```

> 裸跑 `python -m code_agent.main`（不经脚本）不会自动加载 `.env`，需自己 `export`，或先 `set -a; source .env; set +a`。

## 通用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_BACKEND` | `custom` | 后端：`custom`（litellm）或 `sdk`（Claude Agent SDK） |
| `AGENT_DEFAULT_MODE` | `plain` | 默认回答/操作等级：`plain`、`technical`、`edit` |
| `AGENT_ALLOWED_MODES` | `plain` | agent 开启的模式白名单，逗号分隔；接口只能选择这里已开启的模式 |
| `TARGET_CODE_PATH` | `./target_code` | **被分析的目标代码库路径** |
| `CODE_REPOS` | （空） | 多仓库配置，格式 `gameserver=/path/to/gameserver,ecs=/path/to/ecs`；不设时走 `TARGET_CODE_PATH` 单仓库兼容模式 |
| `CODE_REPO_DEFAULT` | `default` 或 `CODE_REPOS` 首项 | 默认仓库名；`/ask`、CLI、MCP 不传 `repo` 时使用 |
| `AGENT_MAX_ITERATIONS` | `12` | Agent 最多调几轮工具 |
| `LLM_NUM_RETRIES` | `3` | LLM 调用失败重试次数（限流/超时/服务端错误），0=关闭 |
| `STUCK_REPEAT_THRESHOLD` | `3` | 连续相同工具调用判定卡住、提前收尾，0=关闭（仅 custom） |
| `OBS_KEEP_FULL` | `6` | 只保留最近 N 次工具输出完整内容，更早的遮蔽成摘要，0=不遮蔽（仅 custom） |
| `MAX_READ_BYTES` | `20000` | 单次读文件上限（字节） |
| `MAX_GREP_MATCHES` | `100` | grep 最多返回条数 |
| `MAX_LIST_ENTRIES` | `300` | 列目录最多条数 |
| `INDEX_DB_PATH` | `./index/code_index.db` | 单仓库模式的离线索引 SQLite 路径（`scripts/index.sh` 构建）；多仓库模式下默认使用 `./index/repos/<repo>/code_index.db` |
| `USE_INDEX` | `1` | 是否用索引加速 `find_symbol`/`grep_code`，0=强制 live scan |
| `USE_SHORTCUT` | `1` | 精确"X 定义在哪"问题直接查索引返回、不走 LLM，0=关 |
| `KNOWLEDGE_DB_PATH` | `./index/knowledge.db` | 单仓库模式的知识飞轮 SQLite 路径；多仓库模式下默认使用 `./index/repos/<repo>/knowledge.db` |
| `USE_KNOWLEDGE` | `0` | 是否启用知识沉淀飞轮（沉淀+召回），默认关 |
| `SERVICE_HOST` | `0.0.0.0` | HTTP 监听地址 |
| `SERVICE_PORT` | `8900` | HTTP 端口 |
| `MAX_CONCURRENCY` | `4` | `/ask`+`/diagnose` 最大并发数（线程池 worker 数） |
| `MAX_QUEUE` | `8` | 超出并发时最多排队数，再多返回 503 |
| `REQUEST_TIMEOUT` | `180` | 单请求超时秒数，超时返回 504 |
| `CACHE_MAX_ENTRIES` | `512` | `/ask` 答案缓存上限（LRU 淘汰），0=禁用缓存 |
| `LLM_TRACE_ENABLED` | `1` | 是否为每次 agent 请求记录 LLM 交互 trace，0=关闭 |
| `LLM_TRACE_DIR` | `./logs/llm` | 每个请求一个 JSONL trace 文件，记录每轮 LLM 输入/输出、工具结果、最终答案 |
| `LLM_TRACE_VIEW_MAX_FILES` | `200` | 后台 trace 可视化页面最多列出的文件数 |

### 多仓库配置

推荐用 `CODE_REPOS` 同时注册 gameserver 和 ecs：

```bash
CODE_REPOS='gameserver=/data/code/gameserver,ecs=/data/code/ecs'
CODE_REPO_DEFAULT=gameserver
```

请求时用 `repo` 选择仓库：

```bash
curl -X POST http://localhost:8900/ask \
  -H 'Content-Type: application/json' \
  -d '{"repo":"ecs","question":"MoveSystem 是做什么的？"}'
```

CLI / MCP 也支持同名参数：

```bash
scripts/cli.sh --repo gameserver "SceneMgr 是做什么的？"
scripts/cli.sh --repo ecs "MoveSystem 是做什么的？"
```

离线索引和知识库按仓库隔离，默认写到：

```text
index/repos/gameserver/code_index.db
index/repos/gameserver/knowledge.db
index/repos/ecs/code_index.db
index/repos/ecs/knowledge.db
```

仓库导航/项目概览缓存也按仓库隔离：

```bash
python -m code_agent.repo_profile --repo gameserver
python -m code_agent.repo_profile --repo ecs
```

### 操作等级

`/ask`、MCP `ask_codebase` 和 CLI 都可选择 `mode`，但请求的模式必须包含在 `AGENT_ALLOWED_MODES` 中：

| 模式 | 等级 | 面向对象 | 行为 |
|------|------|----------|------|
| `plain` | 1 | 策划 / QA / 非程序员 | 精确、简洁、结构化自然语言；强制过滤代码、命令、配置样例 |
| `technical` | 2 | 程序员 | 允许代码级解读、调用链、风险点、文件和行号；不直接改代码 |
| `edit` | 3 | 程序员 / agent 自动改码 | 允许直接代码修改类任务；必须显式开启，且仍受后端工具能力和沙箱限制 |

默认只开启 `plain`。例如要开放程序员解读：

```bash
AGENT_ALLOWED_MODES=plain,technical scripts/serve.sh
```

要开放直接改码入口：

```bash
AGENT_ALLOWED_MODES=plain,technical,edit scripts/serve.sh
```

> `SYSTEM_PROMPT_BASE` 和各模式提示词只在代码中维护；运行时用 `system_prompt_for_mode(mode)` 组合。

## custom 后端配置

经 mushigen 代理（OpenAI 兼容网关）。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` | 模型（实际会被加 `openai/` 前缀走代理） |
| `LLM_API_BASE` | `http://10.253.17.63:8090/v1` | 代理地址（OpenAI 兼容，注意是 `/v1`） |
| `LLM_API_KEY` | （必填，无默认） | 认证 token，缺失时首次调用即报清晰错误 |
| `LLM_TEMPERATURE` | `0` | 采样温度 |
| `LLM_TIMEOUT` | `120` | 单次 LLM 超时（秒） |

也可把 `LLM_MODEL` 改成代理上的 Claude（如 `us.anthropic.claude-sonnet-4-6`），无需切换 SDK，litellm 这层抽象本就支持。代理可用模型用 `GET /v1/models` 查询。

## sdk 后端配置

经 Bedrock，依赖 Claude Code CLI。CLI 会读取这些环境变量：

| 变量 | 示例 | 说明 |
|------|------|------|
| `SDK_MODEL` | `us.anthropic.claude-opus-4-8` | 模型；不设则取 `ANTHROPIC_MODEL` |
| `CLAUDE_CODE_USE_BEDROCK` | `1` | 启用 Bedrock |
| `ANTHROPIC_BEDROCK_BASE_URL` | `http://10.253.17.63:8090/bedrock` | Bedrock 代理地址（注意是 `/bedrock`） |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH` | `1` | 跳过原生 AWS 鉴权（走代理 token） |
| `AWS_REGION` | `us-east-1` | 区域 |
| `ANTHROPIC_AUTH_TOKEN` | `sk-...` | 代理认证 token |

> 注意两套后端走的是代理的不同路径：custom → `/v1`，sdk → `/bedrock`。

## 切换示例

```bash
# 用默认 custom 后端
scripts/cli.sh "SceneMgr 是做什么的？"

# 临时切到 sdk 后端
AGENT_BACKEND=sdk scripts/cli.sh "SceneMgr 是做什么的？"

# 单仓库兼容模式
TARGET_CODE_PATH=/path/to/game-code scripts/serve.sh

# 多仓库模式
CODE_REPOS='gameserver=/data/code/gameserver,ecs=/data/code/ecs' \
CODE_REPO_DEFAULT=gameserver scripts/serve.sh
```
