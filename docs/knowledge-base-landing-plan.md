# 代码知识库落地计划

## 背景

`/home/dev/llm/knowledge-base` 是完整的公司知识代理平台，包含 raw/wiki/schema 分层、知识图谱、A2A/MCP skill 注册、问答沉淀、治理和评测。`code-agent` 不需要整套搬迁，当前目标是把其中对代码问答最有价值的机制裁剪落地。

## 目标

让 code-agent 面对四类真实问题时，先获得稳定的代码知识地图，再用工具核实当前代码：

- crash 堆栈：先定位栈帧所属模块、生命周期和常见错误模式。
- 宕机/错误日志：先用日志关键字、assert/check 和模块卡片缩小范围。
- 功能实现：先给模块入口和相关卡片，再查调用链。
- 配置实现：先定位配置链路、表名、加载类和运行时使用点。

## 借鉴机制与裁剪

| knowledge-base 机制 | code-agent 落地方式 |
| --- | --- |
| raw/wiki/schema 三层 | 保留为 `docs/code-knowledge/<repo>/` 的 OKF-style bundle；暂不引入 raw 投喂层 |
| KnowledgeRelation 图谱 | 从 Markdown 链接和 frontmatter 派生轻量图谱，并支持五类语义关系字段 |
| GraphCache prompt 注入 | 在 `CodeAgent._build_messages()` 注入“代码知识库地图” |
| Skill Registry | 后续把 MCP/API 工具定义统一到一个 registry；本阶段不重构协议层 |
| 问答沉淀 | 复用现有后台问答沉淀，增强落地卡片后可进入图谱 |
| Capsule 协议 | 后续用于标准化四类问题的答案结构；本阶段先在 prompt 中使用问题类型策略 |

## knowledge-base 参考记录

`/home/dev/llm/knowledge-base` 的核心判断：

- 核心范式是 `raw/ + wiki/ + schema/`：
  - `raw/`：不可变原始资料。
  - `wiki/`：LLM 生成和维护的知识沉淀产物。
  - `schema/`：给 Agent 的操作规范、关系定义、治理规则。
- 后端是 FastAPI + SQLAlchemy + Alembic，面向 PostgreSQL/pgvector、Redis/RQ。
- 前端是 Vue 3/Vite/TS。
- 对外支持 HTTP API、A2A、MCP。

最值得 code-agent 借鉴的部分：

- 知识图谱不只是前端展示：`server/app/services/graph_cache.py` 会把页面清单和关系摘要注入 agent system prompt，避免每次盲搜。
- 统一工具/Skill 注册：`server/app/skills/registry.py` 是 A2A、MCP、REST 的共同能力源，避免多套协议定义分叉。
- 问答沉淀机制：`server/app/services/sedimentation_service.py` 会判断一次问答是否值得沉淀为新页面或 patch 旧页面。
- Agent Loop：`server/app/intelligence/engine.py` 实现 tool-use loop，带工具调用去重、长输出压缩、trace 记录。
- 知识会话协议：`docs/a2a/knowledge-session-protocol.md` 的 Capsule 设计适合 code-agent，字段包括事实、约束、风险、引用、open questions。

knowledge-base 实际代码允许五类关系，以 `schema/relations.md` 和 `RELATION_TYPES` 为准：

| relation | 含义 | code-agent 可借鉴场景 |
| --- | --- | --- |
| `part_of` | 组成/从属 | 模块属于子系统、配置链路属于框架 |
| `supplements` | 补充 | 排查手册补充模块卡、问答沉淀补充已有卡 |
| `contradicts` | 冲突 | 旧结论与新代码/新日志排查结果冲突 |
| `supersedes` | 取代 | 新沉淀替代旧排查手册或旧配置规则 |
| `depends_on` | 依赖 | 理解 A 需要先读 B，例如配置链依赖表加载框架 |

注意：knowledge-base 的 `schema/AGENTS.md` 里仍有 `implies/derived_from` 残留描述，但代码实际不允许这两类关系；后续借鉴时不采用。
在 code-agent 中，这五类关系通过同名 frontmatter 字段维护，例如
`depends_on: tableload-config.md, unit-skill-attr.md`。

## 分阶段执行

### Phase 1：知识地图可用

- 递归读取 `docs/code-knowledge/<repo>/`，支持后续模块化子目录。
- 统一解析 frontmatter，提取 `tags/symbols/logs/asserts/question_types/resource` 和五类语义关系。
- 图谱增加实体节点和关系：`owns_symbol`、`emits_log`、`checks_assert`、`answers_question_type`、`documents_resource`。
- 图谱增加知识卡片语义边：`part_of`、`supplements`、`contradicts`、`supersedes`、`depends_on`。
- 将图谱摘要注入 agent system prompt，要求模型先按地图导航，再用工具核实。

### Phase 2：沉淀治理增强

- 后台问答沉淀生成 `Code Playbook` 时，自动补充 `logs/asserts/symbols/question_types`。
- 增加卡片 lint：frontmatter 必填、内部链接有效、重复实体提示。
- 为“用户认可的问答”增加人工状态字段，避免未审核答案污染知识库。

### Phase 3：代码问答 Capsule

- 为 crash_stack、outage_log、feature_impl、config_impl 输出统一结构。
- 每次回答包含结论、证据、排查步骤、风险/不确定点、后续验证命令。
- 评测集按四类问题分别统计命中率。

## 本次执行范围

本次先完成 Phase 1：

1. 新增后端知识图谱解析模块。
2. 卡片召回改为递归 OKF bundle。
3. `/knowledge/api/graph` 返回更完整的实体图谱和关系说明。
4. agent prompt 注入知识库地图。
5. 补充测试和文档。

## 非目标

- 不引入独立数据库存储知识卡片。
- 不把 knowledge-base 的 ACL、A2A 队列、ReviewQueue 整套搬进来。
- 不默认相信知识卡片，所有结论仍需工具核实当前代码。
