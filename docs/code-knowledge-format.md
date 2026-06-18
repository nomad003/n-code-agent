# 代码知识库规范与落地计划

## 目标

代码知识库用于沉淀稳定的模块框架、配置链路、日志/断言排查手册和跨仓库关系，避免
code-agent 每次回答都从零遍历代码。它服务四类高频问题：

- 程序 crash 堆栈：快速定位栈帧所属模块、生命周期、常见空指针/状态错误。
- 宕机/错误日志：用日志关键字、assert/check 文案命中模块卡，再反查打印点和上下文。
- 功能实现：先给模块地图和入口，再用工具核实调用链。
- 配置实现：先给配置表、加载类、运行时使用点，再核实字段和数据流。

## 与 OKF 的关系

采用 **OKF-compatible 子集 + 代码扩展字段**。

保留 OKF 的核心优点：

- 每个概念是一份 UTF-8 Markdown 文件。
- 文件顶部使用 YAML frontmatter，正文使用结构化 Markdown。
- 文件可进入 git，支持 diff、review、blame。
- 通过 Markdown 链接表达模块之间的关系。
- `index.md` 用于渐进导航，避免一次性加载全量知识。

不原样照搬 OKF 的原因：

- OKF 面向通用知识/数据资产目录，代码问答需要额外字段来匹配符号、日志、断言和问题类型。
- 当前实现的模块知识卡读取器还是轻量解析器，不依赖完整 YAML 库；frontmatter 要保持简单。
- 代码知识卡必须持续提示“具体结论仍需用工具核实”，不能把卡片当作最终事实。

## 文件布局

当前落地使用平铺目录：

```text
docs/code-knowledge/
  common/
  marvel/
    index.md
    gameserver-overview.md
    combat-framework.md
    ...
```

后续如果需要更强 OKF 兼容，可演进为分层目录：

```text
docs/code-knowledge/marvel/
  index.md
  gameserver/
    index.md
    combat.md
    scene.md
  ecs/
    index.md
    xecs-runtime.md
```

## Frontmatter

推荐字段：

```yaml
---
type: Code Module
title: 战斗框架
description: 战斗管理、目标选择、伤害效果和战斗单位的模块地图
repo: marvel
module: gameserver/combat
resource: gameserver/combat
tags: combat, battle, unit, skill
symbols: XCombat, CombatUnit, SkillMgr
logs: Combat, UnitLogErr
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---
```

字段约定：

| 字段 | 用途 |
|------|------|
| `type` | 卡片类型，如 `Code Module`、`Code Playbook`、`Config Chain` |
| `title` | UI 展示名和 prompt 注入标题 |
| `description` | 一句话摘要，用于索引、列表和召回片段 |
| `repo` | 对应 `CODE_REPOS` 里的 repo 名 |
| `module` | 模块路径或逻辑模块名 |
| `resource` | 主要代码路径 |
| `tags` | 召回关键词；当前解析器支持逗号分隔和 `[a, b]` |
| `symbols` | 关键类/函数/类型名，供人工维护和后续索引增强 |
| `logs` | 常见日志关键词 |
| `asserts` | 常见断言/check 关键词 |
| `question_types` | 适用问题类型 |
| `updated_at` | 人工更新日期 |

## 正文模板

```md
# 模块名

这张卡用于回答哪些问题。说明本卡是稳定框架，具体行号和结论仍需工具核实。

## 入口文件

## 核心职责

## 关键流程

## 配置与数据来源

## 常见日志/断言

## 常见提问

## 排查顺序

## 相关卡片
```

## 召回策略

当前实现位于 `code_agent/module_knowledge.py`：

1. 按当前 repo 加载 `docs/code-knowledge/common/` 和 `docs/code-knowledge/<repo>/`。
2. 从用户问题抽取中英文词、符号名和中文短语。
3. 按 title、tags、body 简单打分，取最多 3 张卡片注入 prompt。
4. Agent 必须把知识卡当作导航和排查手册，最终仍通过工具读取代码核实。

后续增强：

- 递归读取子目录，支持完整 OKF bundle。
- 给 frontmatter 建 SQLite/FTS 索引，提升日志、符号、assert 命中率。
- UI 增加图谱视图，展示模块链接和 cited-by。
- CI 校验 frontmatter 必填字段、内部链接、重复 tags。

## 第一阶段落地范围

先覆盖 `marvel` 聚合仓库的大模块：

- `gameserver` 总览
- `gameserver/tableload` 配置加载
- `gameserver/scene` 场景
- `gameserver/level` 关卡/刷怪/脚本桥
- `gameserver/combat` 战斗核心
- `gameserver/unit` 单位/属性/技能
- `gameserver/buff` Buff
- `gameserver/ai` AI
- `gameserver/role` 玩家角色
- `gameserver/network` / `gameserver/protocol` 网络协议
- `ecs/XEcs/ecs` ECS 组件/系统/工具库

第一版只做模块地图和常见排查入口；第二版再按真实问题补充具体配置链路和日志手册。
