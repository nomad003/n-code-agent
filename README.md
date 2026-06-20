# Code Agent

游戏服务器 / 战斗 / 客户端 / 引擎 代码理解服务 — 对外提供 HTTP 接口，解释代码结构、字段含义和功能流程。

> 详细文档见 [`docs/`](docs/)：[架构](docs/architecture.md) · [配置](docs/configuration.md) · [接口](docs/api.md) · [MCP](docs/mcp.md) · [测试](docs/testing.md) · [部署与迁移](docs/deployment.md)

## 架构

```
客户端 (HTTP POST /ask)
    │
    ▼
FastAPI 服务 (server.app)
    │
    ▼
LLM Agent (code_agent.core.agent) ── litellm ──► mushigen proxy ──► gemini-3.5-flash
    │
    ├── grep_code(pattern, path)      搜索代码符号/关键字
    ├── read_file(path, start, end)   读取文件内容
    ├── list_dir(path)                列出目录结构
    └── find_symbol(name)             查找类/函数定义位置
```

## 快速开始（脚本）

`scripts/` 下封装了常用操作，可在任意目录调用，首次运行会自动建好 venv：

```bash
cp .env.example .env                      # 填入 LLM_API_KEY（脚本会自动加载 .env）
scripts/setup.sh                          # 创建 venv 并安装依赖
scripts/serve.sh                          # 启动 HTTP 服务（端口 8900）
scripts/cli.sh                            # 命令行交互
scripts/cli.sh "SceneMgr 是做什么的？"      # 单次提问
scripts/ask.sh "玩家生命值字段叫什么？"      # 向运行中的服务发请求（curl 封装）

# 指定要分析的代码库
TARGET_CODE_PATH=/path/to/game-code scripts/serve.sh

# 多仓库：按 repo 分别选择 gameserver / ecs
CODE_REPOS='gameserver=/path/to/gameserver,ecs=/path/to/ecs' \
CODE_REPO_DEFAULT=gameserver scripts/serve.sh
scripts/cli.sh --repo ecs "MoveSystem 是做什么的？"
```

## 依赖安装（手动）

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 两种 Agent 后端

通过 `AGENT_BACKEND` 切换（两者共用同一套沙箱工具和 system prompt）：

| 后端 | 说明 |
|------|------|
| `custom`（默认） | litellm tool-calling 循环，经 mushigen `/v1` 代理，模型由 `LLM_MODEL` 指定 |
| `sdk` | Claude Agent SDK + Claude Code CLI，经 Bedrock，模型由 `SDK_MODEL`（默认取 `ANTHROPIC_MODEL`）指定 |

`sdk` 后端会优先使用项目内置的 CLI（`vendor/claude-cli/`，经 Git LFS 存储，仅 linux-x64），找不到则回退系统 PATH 上的 `claude`。

```bash
AGENT_BACKEND=sdk scripts/cli.sh "SceneMgr 是做什么的？"
```

## 配置

环境变量（或直接改 config.py）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` | litellm 模型标识 |
| `LLM_API_BASE` | `http://10.253.17.63:8090/v1` | 代理地址（OpenAI 兼容） |
| `TARGET_CODE_PATH` | `./target_code` | 被分析的目标代码库路径 |
| `CODE_REPOS` | （空） | 多仓库配置，如 `gameserver=/path/a,ecs=/path/b`；不设时使用 `TARGET_CODE_PATH` 单仓库模式 |
| `CODE_REPO_DEFAULT` | `default` 或首个仓库 | 默认仓库名 |
| `AGENT_ALLOWED_MODES` | `plain,technical` | 允许的回答/操作模式；`edit` 需显式追加 |
| `LLM_API_KEY` | （必填，无默认） | 认证 token，从环境变量 / `.env` 读取，不写进代码 |

## 仓库概览 / 导航缓存

为避免宽泛问题每次从零遍历目录，可为每个仓库预生成概览：

```bash
CODE_REPOS='gameserver=/path/to/gameserver,ecs=/path/to/ecs' python -m code_agent.retrieval.repo_profile --repo gameserver
CODE_REPOS='gameserver=/path/to/gameserver,ecs=/path/to/ecs' python -m code_agent.retrieval.repo_profile --repo ecs
```

概览会写到 `index/repos/<repo>/profile.json`，agent 会自动把它作为检索起点注入 prompt，也可通过工具 `repo_overview` 或 HTTP `GET /repos/{repo}/overview` 查看。

## 运行

```bash
# HTTP 服务（端口 8900）
.venv/bin/python -m server.app

# 命令行交互测试
.venv/bin/python -m code_agent.interfaces.cli
.venv/bin/python -m code_agent.interfaces.cli "SceneMgr 是做什么的？"   # 单次提问模式
```

## API

### POST /ask

```bash
curl -X POST http://localhost:8900/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "SceneMgr 是做什么的？"}'
```

请求体：
```json
{
  "question": "要问的问题",
  "use_cache": true
}
```

响应：
```json
{
  "answer": "SceneMgr 是场景管理器...",
  "cached": false
}
```

### GET /health

健康检查，返回 `{"status": "ok"}`。

## 目录说明

| 路径 | 职责 |
|------|------|
| `code_agent/core/` | Agent loop、SDK 后端、问题类型、回答模式、输出策略 |
| `code_agent/retrieval/` | 沙箱工具、离线索引、索引查询、repo profile |
| `code_agent/kb/` | 知识库、知识图谱、模块卡、Assert 知识 |
| `code_agent/diagnostics/` | backtrace/log 诊断 |
| `server/` | FastAPI 服务、HTTP API、缓存和并发闸门 |
| `frontend/` | Vue 前端资产和页面 shell |
| `code_agent/interfaces/` | CLI、MCP 入口 |
| `docs/` | 项目文档 |
| `scripts/` | 启动、测试、索引、评测脚本 |
| `tests/` | 离线测试 |
| `target_code/` | 示例/组合目标代码目录 |
| `index/` | repo 索引、知识库和 profile 缓存 |

更细的后端目录说明见 [docs/code-organization.md](docs/code-organization.md)。

## 评测

```bash
scripts/knowledge-eval.sh                         # 离线评测代码知识库召回/图谱关系
scripts/eval.sh eval/dataset.real_user.jsonl       # 需要 LLM key，评测 /ask 回答质量
```

知识库评测不调用模型；`/ask` 回答质量评测会真实调用 agent。

## 演进计划

1. **当前（方案 1）**：LLM + 实时代码搜索，每次查询走 tool call
2. **下一步（方案 2）**：离线建索引（tree-sitter AST 解析 → SQLite 符号表 + 向量数据库），精确查询直接返回不走 LLM
