# 架构

## 这是什么

一个**代码理解服务**：对外提供 HTTP 接口，回答关于某个游戏代码库（游戏服务器 / 战斗 / 客户端 / 引擎）的自然语言问题——解释代码结构、字段含义、功能流程。

核心思路：**LLM 看不到代码**，只能通过若干受沙箱限制的搜索工具去检索目标代码库，多轮"调工具 → 读结果 → 再调"，凑够证据后用中文作答。

## 请求流程

```
客户端
  │  HTTP POST /ask   或   CLI
  ▼
main.py / cli.py            入口（HTTP 服务 / 命令行），main.py 带问答缓存
  ▼
agent.answer(question)      按 AGENT_BACKEND 分发
  │
  ├─ custom（默认）──► agent.py 内 litellm 循环 ──► mushigen /v1 ──► LLM_MODEL
  │                                                （openai/ 前缀路由）
  └─ sdk ────────────► agent_sdk.py（Claude Agent SDK + CLI）──► Bedrock ──► SDK_MODEL
        │
        ▼
   tools.py（4 个沙箱工具）   在 TARGET_CODE_PATH 内 grep / read / list
        ▲
        └── 工具结果回喂给 LLM，进入下一轮
```

## 双后端

`agent.answer()` 根据 `AGENT_BACKEND` 环境变量选择后端，**两者共用同一套 `tools.py` 工具和 `config.SYSTEM_PROMPT`**，对外接口完全一致。

| | `custom`（默认） | `sdk` |
|---|---|---|
| 实现 | `agent.py` 的 `_answer_custom()` | `agent_sdk.py`（延迟导入） |
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
3. **循环**：调 `litellm.completion(...)`（带 4 个工具 schema、`tool_choice="auto"`）；
   有 `tool_calls` → `tools.dispatch()` 执行成 `Observation` 回喂；无 → 直接作答返回。
4. **stuck 检测**：连续 `STUCK_REPEAT_THRESHOLD`（默认 3）次相同工具+相同参数 → 提前收尾
   （防只读 agent 反复 grep 同一 pattern / 反复撞同一错误烧 token）。
5. **LLM 重试**：`litellm.completion(num_retries=LLM_NUM_RETRIES)` 对限流/超时/服务端错误做
   指数退避。
6. **收尾**：超过 `MAX_ITERATIONS` 或检测到 stuck → 不带工具再调一次，要求基于现有信息作答。

**代理路由要点**：litellm 按模型名前缀选客户端。直接用 `vertex_ai/...` 会触发它的原生 Google Cloud 认证（失败且不走代理）。所以 `_routed_model()` 给模型名加 `openai/` 前缀，强制走 OpenAI 兼容路径；代理收到的仍是真实模型名。

### sdk 后端

用 Claude Agent SDK 跑 agent 循环，但**把 `tools.py` 的沙箱工具包装成 SDK 工具**（`@tool` + `create_sdk_mcp_server`），内部仍调 `tools.dispatch()`——所以路径沙箱、输出限长与 custom 完全相同。同时通过 `disallowed_tools` 禁用 SDK 自带的 Read/Grep/Glob/Bash/Write/Edit，**让模型只能用我们的 4 个工具**。

- 工具在 SDK 内命名为 `mcp__code__<tool>`，由 `allowed_tools` 白名单放行。
- CLI 经 Bedrock 路由（`_bedrock_env()` 把相关 env vars 显式传入 `options.env`）。
- CLI 二进制优先用项目内置的 `vendor/claude-cli/`（见 [deployment.md](deployment.md)），找不到回退系统 PATH。

## 工具层（`tools.py`）

模型唯一能接触文件系统的途径，是设计的安全边界，也是将来换索引（方案 2）的接缝。

| 工具 | 作用 |
|------|------|
| `grep_code(pattern, path)` | 正则搜符号/关键字，返回 `文件:行号: 内容` |
| `read_file(path, start, end)` | 按行读文件片段（1-based，含端点） |
| `list_dir(path)` | 列目录（单层），目录以 `/` 结尾 |
| `find_symbol(name)` | 找类/函数/类型定义（多语言定义正则，找不到退化为普通搜索） |

三道护栏：

1. **路径沙箱**（`_resolve()`）：所有路径限制在 `TARGET_CODE_PATH` 内，`..` 越界报错。
2. **输出限长**：grep ≤ `MAX_GREP_MATCHES`、读文件 ≤ `MAX_READ_BYTES`、列目录 ≤ `MAX_LIST_ENTRIES`，防止撑爆上下文。
3. **错误不抛出**：`dispatch()` 把工具错误转成字符串回喂给模型，让它自行纠正，而非让循环崩溃。

> 已知边界：`_resolve()` 不对软链接做 `realpath` 解析，符号链接逃逸不在防护范围内。

## 模块职责

| 文件 | 职责 |
|------|------|
| `config.py` | 全局配置（环境变量驱动）、system prompt、`require_api_key()` |
| `tools.py` | 4 个沙箱工具 + 工具 schema + `dispatch()` 注册表 |
| `agent.py` | 后端分发 + custom 循环（`CodeAgent`：事件历史/stuck/重试） |
| `events.py` | custom 循环的 `Action`/`Observation` 事件模型 |
| `agent_sdk.py` | sdk（Claude Agent SDK）后端 |
| `main.py` | FastAPI 服务（`/ask`、`/health`）+ 问答缓存（端口 8900） |
| `mcp_server.py` | MCP server，暴露 `ask_codebase`（streamable-http，端口 8901，见 [mcp.md](mcp.md)） |
| `cli.py` | 命令行交互 / 单次提问 |
| `vendor/claude-cli/` | 内置 Claude Code CLI（linux-x64，二进制经 Git LFS） |

## 演进计划

1. **当前（方案 1）**：LLM + 实时代码搜索，每次查询走 tool call。
2. **下一步（方案 2）**：离线建索引（tree-sitter AST → SQLite 符号表 + 向量库），精确查询不走 LLM 直接返回。`tools.py` 被刻意做成唯一接触文件的层，就是为了让索引顶替这些实现而上层不动。
