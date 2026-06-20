# 代码目录组织

`code_agent/` 只保留代码理解核心包和配置，不再保留根目录同名 shim。
HTTP 服务和前端资产位于仓库顶层 `server/`、`frontend/`。

## 目录分层

| 目录 | 职责 | 主要模块 |
|------|------|----------|
| `code_agent/core/` | Agent 运行核心 | `agent.py`、`agent_sdk.py`、`events.py`、`operation_modes.py`、`question_intent.py`、`response_policy.py` |
| `code_agent/retrieval/` | 代码检索与索引 | `tools.py`、`indexer.py`、`index_query.py`、`repo_profile.py`、`shortcut.py` |
| `code_agent/kb/` | 知识库与知识评测 | `knowledge.py`、`knowledge_graph.py`、`module_knowledge.py`、`assert_knowledge.py`、`knowledge_eval.py` |
| `code_agent/diagnostics/` | 运行时诊断 | `diagnose.py` |
| `server/` | HTTP 服务 | `app.py` |
| `frontend/` | 前端资产与 shell | `assets.py`、`static/` |
| `code_agent/interfaces/` | 非 HTTP 入口 | `mcp_server.py`、`cli.py` |
| `code_agent/observability/` | 调用观测 | `llm_trace.py`、`trace_viewer.py` |
| `code_agent/evals/` | 回答质量评测 | `evaluate.py` |
| `frontend/static/` | Vue 前端静态资源 | `app.html`、`app.css`、`app.js` |

## 常用命令

```bash
python -m code_agent.retrieval.indexer --repo marvel
python -m code_agent.kb.knowledge_eval eval/knowledge.marvel.jsonl
python -m code_agent.evals.evaluate eval/dataset.sample.jsonl
python -m server.app
python -m code_agent.interfaces.mcp_server
```

## 依赖方向

推荐依赖方向：

```text
server -> code_agent.core -> code_agent.retrieval
                 \-> kb
                 \-> diagnostics
code_agent.interfaces -> code_agent.core
code_agent.observability <- code_agent.core/server
code_agent.evals -> code_agent.core
```

约束：

- `config.py` 留在根目录，作为全局配置和 repo 上下文。
- 文件系统访问集中在 `retrieval/tools.py` 和索引相关模块。
- LLM loop 只放在 `core/agent.py` 或 `core/agent_sdk.py`。
- 知识卡、图谱、Assert catalog 的解析放在 `kb/`。
- HTTP 服务只放在顶层 `server/`；MCP/CLI 放在 `code_agent/interfaces/`。
- 前端页面资产只放在 `frontend/static/`，服务端只通过 `frontend.assets` 读取页面 shell。
- `code_agent/` 根目录不放业务 shim；新增模块必须进入对应子包。

## 新代码放置规则

| 新功能 | 放置位置 |
|--------|----------|
| 新工具、新索引、新代码搜索策略 | `code_agent/retrieval/` |
| 新问题类型、新回答模式、Agent loop 改造 | `code_agent/core/` |
| 新知识卡格式、知识召回、图谱关系、Assert catalog | `code_agent/kb/` |
| 新 HTTP API、服务缓存、并发治理 | `server/` |
| 新前端页面、样式、交互脚本 | `frontend/static/` |
| 新 MCP tool、CLI 参数 | `code_agent/interfaces/` |
| 新 trace 解析、可视化后端 | `code_agent/observability/` |
| 新评测集执行器 | `code_agent/evals/` |
