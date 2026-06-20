# 代码目录组织

`code_agent/` 后端代码按职责拆成子包，根目录保留兼容 shim。旧导入方式仍可用：

```python
from code_agent import agent, tools, diagnose
```

这些旧模块会直接别名到新实现模块，保留私有调试/测试入口，例如
`code_agent.main._inflight`、`code_agent.tools._RG_PATH`。

## 目录分层

| 目录 | 职责 | 主要模块 |
|------|------|----------|
| `code_agent/core/` | Agent 运行核心 | `agent.py`、`agent_sdk.py`、`events.py`、`operation_modes.py`、`question_intent.py`、`response_policy.py` |
| `code_agent/retrieval/` | 代码检索与索引 | `tools.py`、`indexer.py`、`index_query.py`、`repo_profile.py`、`shortcut.py` |
| `code_agent/kb/` | 知识库与知识评测 | `knowledge.py`、`knowledge_graph.py`、`module_knowledge.py`、`assert_knowledge.py`、`knowledge_eval.py` |
| `code_agent/diagnostics/` | 运行时诊断 | `diagnose.py` |
| `code_agent/interfaces/` | 对外入口 | `main.py`、`mcp_server.py`、`cli.py` |
| `code_agent/observability/` | 调用观测 | `llm_trace.py`、`trace_viewer.py` |
| `code_agent/evals/` | 回答质量评测 | `evaluate.py` |
| `code_agent/static/` | Vue 前端静态资源 | `app.html`、`app.css`、`app.js` |

## 兼容入口

根目录下的同名文件是兼容层：

| 旧路径 | 新实现 |
|--------|--------|
| `code_agent/agent.py` | `code_agent/core/agent.py` |
| `code_agent/tools.py` | `code_agent/retrieval/tools.py` |
| `code_agent/indexer.py` | `code_agent/retrieval/indexer.py` |
| `code_agent/knowledge_graph.py` | `code_agent/kb/knowledge_graph.py` |
| `code_agent/assert_knowledge.py` | `code_agent/kb/assert_knowledge.py` |
| `code_agent/diagnose.py` | `code_agent/diagnostics/diagnose.py` |
| `code_agent/main.py` | `code_agent/interfaces/main.py` |
| `code_agent/evaluate.py` | `code_agent/evals/evaluate.py` |

命令也保持不变：

```bash
python -m code_agent.indexer --repo marvel
python -m code_agent.knowledge_eval eval/knowledge.marvel.jsonl
python -m code_agent.evaluate eval/dataset.sample.jsonl
python -m code_agent.main
python -m code_agent.mcp_server
```

## 依赖方向

推荐依赖方向：

```text
interfaces -> core -> retrieval
                 \-> kb
                 \-> diagnostics
observability <- core/interfaces
evals -> core
```

约束：

- `config.py` 留在根目录，作为全局配置和 repo 上下文。
- 文件系统访问集中在 `retrieval/tools.py` 和索引相关模块。
- LLM loop 只放在 `core/agent.py` 或 `core/agent_sdk.py`。
- 知识卡、图谱、Assert catalog 的解析放在 `kb/`。
- HTTP/MCP/CLI 只做参数解析、缓存、并发治理和调用编排。
- 根目录兼容 shim 不放业务逻辑。

## 新代码放置规则

| 新功能 | 放置位置 |
|--------|----------|
| 新工具、新索引、新代码搜索策略 | `code_agent/retrieval/` |
| 新问题类型、新回答模式、Agent loop 改造 | `code_agent/core/` |
| 新知识卡格式、知识召回、图谱关系、Assert catalog | `code_agent/kb/` |
| 新 HTTP API、MCP tool、CLI 参数 | `code_agent/interfaces/` |
| 新 trace 解析、可视化后端 | `code_agent/observability/` |
| 新评测集执行器 | `code_agent/evals/` |
