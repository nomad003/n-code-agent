# 架构

## 这是什么

一个**代码理解服务**：对外提供 HTTP 接口，回答关于某个游戏代码库（游戏服务器 / 战斗 / 客户端 / 引擎）的自然语言问题——解释代码结构、字段含义、功能流程。

核心思路：**LLM 看不到代码**，只能通过若干受沙箱限制的搜索工具去检索目标代码库，多轮"调工具 → 读结果 → 再调"，凑够证据后用中文作答。

## 请求流程

```
客户端
  │  HTTP POST /ask   或   CLI
  ▼
code_agent.server.app / code_agent.interfaces.cli
                            入口（HTTP 服务 / 命令行），HTTP 入口带问答缓存
  ▼
agent.answer(question, repo=...)  按 repo 选择目标仓库，按 AGENT_BACKEND 分发
  │
  ├─ custom（默认）──► code_agent.core.agent 内 litellm 循环 ──► mushigen /v1 ──► LLM_MODEL
  │                                                （openai/ 前缀路由）
  └─ sdk ────────────► core/agent_sdk.py（Claude Agent SDK + CLI）──► Bedrock ──► SDK_MODEL
        │
        ▼
   code_agent.retrieval.tools（沙箱工具）   在当前 repo 根目录内 grep / read / list / 查索引
        ▲
        └── 工具结果回喂给 LLM，进入下一轮
```

多仓库通过 `CODE_REPOS='gameserver=/path/a,ecs=/path/b'` 注册，请求里用 `repo`
选择。未配置 `CODE_REPOS` 时保留旧的单仓库兼容模式：使用 `TARGET_CODE_PATH`。
索引、知识库和项目概览缓存按 repo 隔离在 `index/repos/<repo>/` 下。

## 双后端

`agent.answer()` 根据 `AGENT_BACKEND` 环境变量选择后端，**两者共用同一套 `code_agent.retrieval.tools` 工具和 `config.system_prompt_for_mode()`**，对外接口完全一致。`code_agent.tools` 保留为旧路径兼容 shim。

| | `custom`（默认） | `sdk` |
|---|---|---|
| 实现 | `code_agent.core.agent` 的 `_answer_custom()` | `code_agent.core.agent_sdk`（延迟导入） |
| LLM 客户端 | litellm | claude-agent-sdk + Claude Code CLI |
| 路由 | mushigen 代理 `/v1`（OpenAI 兼容） | Bedrock（env vars） |
| 模型 | `LLM_MODEL` | `SDK_MODEL`（默认取 `ANTHROPIC_MODEL`） |
| 循环上限 | `MAX_ITERATIONS` 轮 | `max_turns = MAX_ITERATIONS` |

### custom 后端（`CodeAgent`）

litellm 的 tool-calling 循环（最多 `MAX_ITERATIONS` 轮）。设计借鉴 OpenHands
`CodeActAgent`，但为只读问答场景做了精简：

1. **事件历史**：每次工具调用建模成一对 `Action`/`Observation`（`events.py`），
   历史就是一个 `list[Event]`。无事件总线、无持久化、无订阅者——单进程一个列表即可。
2. **集中渲染消息**：`CodeAgent._build_messages()` 是「事件 → LLM messages」的唯一入口，
   负责把 assistant 的 tool_call 请求与对应的 `tool` 结果按 `tool_call_id` 正确配对
   （对应 OpenHands 的 `ConversationMemory.process_events`）。
3. **循环**：调 `litellm.completion(...)`（带当前启用的工具 schema、`tool_choice="auto"`）；
   有 `tool_calls` → `tools.dispatch()` 执行成 `Observation` 回喂；无 → 直接作答返回。
4. **stuck 检测**：连续 `STUCK_REPEAT_THRESHOLD`（默认 3）次相同工具+相同参数 → 提前收尾
   （防只读 agent 反复 grep 同一 pattern / 反复撞同一错误烧 token）。
5. **LLM 重试**：`litellm.completion(num_retries=LLM_NUM_RETRIES)` 对限流/超时/服务端错误做
   指数退避。
6. **观测遮蔽**：重建消息时只保留最近 `OBS_KEEP_FULL` 次工具输出的完整内容，
   更早的用稳定的一行摘要替代——确定性、不烧 LLM，防长会话 context 膨胀
   （对应 OpenHands 的 `ObservationMaskingCondenser`）。模型仍知道调用发生过，必要时可重跑。
7. **收尾**：超过 `MAX_ITERATIONS` 或检测到 stuck → 不带工具再调一次，要求基于现有信息作答。

custom 的 system prompt 分三层：基础工具策略、`plain/technical/edit` 受众模式、
`question_intent` 问题类型策略。`question_intent` 会把用户问题归到 crash 堆栈、
宕机/错误日志、功能实现、配置实现或通用问答，并注入对应的检索顺序和答案结构，
避免所有问题都按同一套提示词泛答。

在模型调工具前，custom 后端还会注入稳定的代码知识库地图：
`docs/code-knowledge/<repo>/` 下的 OKF-style Markdown 卡片会被解析为概念、标签、
符号、日志、断言、问题类型和资源路径摘要。它只作为导航，提示模型先定位模块和
排查手册；最终结论仍必须通过 `grep_code`、`read_file`、`find_assert_context` 等
工具核实当前代码。

**代理路由要点**：litellm 按模型名前缀选客户端。直接用 `vertex_ai/...` 会触发它的原生 Google Cloud 认证（失败且不走代理）。所以 `_routed_model()` 给模型名加 `openai/` 前缀，强制走 OpenAI 兼容路径；代理收到的仍是真实模型名。

### sdk 后端

用 Claude Agent SDK 跑 agent 循环，但**把 `code_agent.retrieval.tools` 的沙箱工具包装成 SDK 工具**（`@tool` + `create_sdk_mcp_server`），内部仍调 `tools.dispatch()`——所以路径沙箱、输出限长与 custom 完全相同。同时通过 `disallowed_tools` 禁用 SDK 自带的 Read/Grep/Glob/Bash/Write/Edit，**让模型只能用我们的沙箱工具**。

- 工具在 SDK 内命名为 `mcp__code__<tool>`，由 `allowed_tools` 白名单放行。
- CLI 经 Bedrock 路由（`_bedrock_env()` 把相关 env vars 显式传入 `options.env`）。
- CLI 二进制优先用项目内置的 `vendor/claude-cli/`（见 [deployment.md](deployment.md)），找不到回退系统 PATH。

## 工具层（`code_agent.retrieval.tools`）

模型唯一能接触文件系统的途径，是设计的安全边界，也是将来换索引（方案 2）的接缝。

| 工具 | 作用 |
|------|------|
| `grep_code(pattern, path, output_mode, context, head_limit)` | 正则搜符号/关键字；支持内容、文件列表、计数三种输出 |
| `read_file(path, start, end)` | 按行读文件片段（1-based，含端点） |
| `list_dir(path)` | 列目录（单层），目录以 `/` 结尾 |
| `glob(pattern, path, head_limit)` | 按路径模式列文件，适合只看文件名的枚举问题 |
| `find_symbol(name)` | 找类/函数/类型定义（多语言定义正则，找不到退化为普通搜索） |
| `repo_overview()` | 查看当前 repo 的项目概览 / 导航缓存 |
| `resolve_frame(frame)` | 把崩溃栈函数定位到代码定义 |
| `find_log_source(message)` | 根据运行时日志反查打印点 |
| `find_assert_context(message)` | 根据断言失败/错误日志定位 assert/check 语句并返回上下文 |
| `recall_knowledge(query)` | 启用 `USE_KNOWLEDGE=1` 时召回历史问答线索 |

三道护栏：

1. **路径沙箱**（`_resolve()`）：所有路径限制在当前请求的 repo 根目录内，`..` 越界报错。
2. **输出限长**：grep ≤ `MAX_GREP_MATCHES`、读文件 ≤ `MAX_READ_BYTES`、列目录 ≤ `MAX_LIST_ENTRIES`，防止撑爆上下文。
3. **错误不抛出**：`dispatch()` 把工具错误转成字符串回喂给模型，让它自行纠正，而非让循环崩溃。

> 已知边界：`_resolve()` 不对软链接做 `realpath` 解析，符号链接逃逸不在防护范围内。

**索引加速（方案 2）**：存在索引时，`find_symbol` 直接查 SQLite 符号表（精确、一步命中），`grep_code` 对「整库 + 纯文本」走 FTS5 全文索引，`find_assert_context` 查离线抽取的 assert/check 索引；正则或限定子目录的搜索仍走 live scan。索引缺失或 `USE_INDEX=0` 时全部回退 live scan，行为不变。

## 模块职责

| 目录/文件 | 职责 |
|------|------|
| `code_agent/config.py` | 全局配置、repo 解析/上下文、system prompt、`require_api_key()` |
| `code_agent/core/` | Agent loop、SDK 后端、事件模型、回答模式、问题类型和输出策略 |
| `code_agent/retrieval/` | 沙箱工具、离线索引、索引查询、shortcut、repo profile |
| `code_agent/kb/` | 知识飞轮、知识图谱、模块知识卡、Assert catalog、知识评测 |
| `code_agent/diagnostics/` | backtrace/log 诊断与预解析 |
| `code_agent/server/` | FastAPI 服务、HTTP API、缓存、并发闸门、页面路由 |
| `code_agent/frontend/` | Vue 前端静态资源和页面 shell helper |
| `code_agent/interfaces/` | MCP server、CLI，以及旧 HTTP shim |
| `code_agent/observability/` | LLM trace 写入和 trace viewer API |
| `code_agent/evals/` | `/ask` 回答质量评测 |
| `code_agent/static` | 指向 `code_agent/frontend/static` 的兼容路径 |
| `code_agent/*.py` | 旧路径兼容 shim，不放业务逻辑 |
| `vendor/claude-cli/` | 内置 Claude Code CLI（linux-x64，二进制经 Git LFS） |

更细的放置规则见 [code-organization.md](code-organization.md)。

## 演进计划

1. **当前（方案 1）**：LLM + 实时代码搜索，每次查询走 tool call。
2. **方案 2（符号索引已落地）**：`code_agent.retrieval.indexer` 用 tree-sitter 解析 C++ → SQLite 符号表 + FTS5 全文索引；`tools.find_symbol`/`grep_code` 优先走索引（快、精确），无索引则回退 live scan。支持**增量更新**（`indexer.update()` / `scripts/index.sh --update`，按文件哈希只重建变更项）和**入口短路**（`code_agent.retrieval.shortcut`：精确"X 定义在哪"直接查索引、跳过 LLM）。`code_agent.retrieval.tools` 作为唯一接触文件的层，索引顶替其实现而 `code_agent.core.agent` 不动。向量库/语义检索推迟到方案 3。
3. **方案 3（知识飞轮已落地，默认关）**：`knowledge.py` 把每次问答沉淀进 SQLite/FTS，下次相似问题召回作线索注入（`USE_KNOWLEDGE=1` 开启）。**失效机制**是核心：召回时重算引用文件哈希，变了标 stale 并降级为"需重新核实"，agent 用工具二次核实而非直接采信。语义召回留待 V3。

> 已落地优化、明确舍弃的设计、以及更细的后续方向（服务治理、缓存、评测等）见 [roadmap.md](roadmap.md)。
