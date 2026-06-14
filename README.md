# Code Agent

游戏服务器 / 战斗 / 客户端 / 引擎 代码理解服务 — 对外提供 HTTP 接口，解释代码结构、字段含义和功能流程。

## 架构

```
客户端 (HTTP POST /ask)
    │
    ▼
FastAPI 服务 (main.py)
    │
    ▼
LLM Agent (agent.py) ── litellm ──► mushigen proxy ──► gemini-3.5-flash
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
```

## 依赖安装（手动）

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 配置

环境变量（或直接改 config.py）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` | litellm 模型标识 |
| `LLM_API_BASE` | `https://mushigen.comet.scopelyai.com/v1` | 代理地址（OpenAI 兼容） |
| `TARGET_CODE_PATH` | `./target_code` | 被分析的目标代码库路径 |
| `LLM_API_KEY` | （必填，无默认） | 认证 token，从环境变量 / `.env` 读取，不写进代码 |

## 运行

```bash
# HTTP 服务（端口 8900）
.venv/bin/python main.py

# 命令行交互测试
.venv/bin/python cli.py
.venv/bin/python cli.py "SceneMgr 是做什么的？"   # 单次提问模式
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

## 文件说明

| 文件 | 职责 |
|------|------|
| `config.py` | 全局配置：模型、路径、system prompt |
| `tools.py` | 代码搜索工具实现 + 工具定义 |
| `agent.py` | LLM 交互循环（tool calling） |
| `main.py` | FastAPI HTTP 服务 |
| `cli.py` | 命令行交互模式 |

## 演进计划

1. **当前（方案 1）**：LLM + 实时代码搜索，每次查询走 tool call
2. **下一步（方案 2）**：离线建索引（tree-sitter AST 解析 → SQLite 符号表 + 向量数据库），精确查询直接返回不走 LLM

