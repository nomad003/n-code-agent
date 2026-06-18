---
type: Code Module
title: AI 框架
description: AI agent、AI 节点、目标/技能/关卡/空间节点和 AI 配置入口。
repo: marvel
module: gameserver/ai
resource: gameserver/ai
tags: ai, agent, node, target, skill, squad, enemy, behavior
symbols: AIUnitAgent, AISceneAgent, AISquadAgent, AILaunchCore
logs: AI
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# AI 框架

这张卡用于回答“怪物 AI 如何执行”“AI 节点在哪里”“AI 技能/目标选择怎么查”。

## 入口文件

- `gameserver/ai/aiunitagent.cpp` / `.h`：单位级 AI agent。
- `gameserver/ai/aisceneagent.cpp` / `.h`：场景级 AI agent。
- `gameserver/ai/aisquadagent.cpp` / `.h`：小队/组 AI agent。
- `gameserver/ai/ainodes.cpp` / `.h`：基础 AI 节点。
- `gameserver/ai/aitargetnodes.cpp`：目标相关节点。
- `gameserver/ai/aiskillnodes.cpp`：技能相关节点。
- `gameserver/ai/ailevelnodes.cpp`：关卡相关节点。
- `gameserver/ai/aispacenodes.cpp`：空间/位置相关节点。
- `gameserver/tableload/aiconfig.cpp` / `.h`：AI 配置查询。

## 核心职责

- 给怪物、场景或小队挂载 AI agent。
- 根据 AI 配置驱动节点执行。
- 通过节点选择目标、释放技能、移动、响应关卡和场景状态。
- 与 `unit/enemy`、`combat`、`level`、`tableload/aiconfig` 强相关。

## 常见链路

- 怪物初始化时创建 AI agent。
- AI 节点读配置并在 tick/事件中执行。
- 技能节点最终会进入 `SkillMgr` / `SkillCore`。
- 目标节点会查询 combat/scene/unit 状态。

## 常见提问

- “怪物 AI 为什么不放技能？”
- “AI 目标选择规则在哪里？”
- “某个 AI 节点配置字段怎么生效？”
- “AI 相关 crash 怎么排查？”

## 排查顺序

1. 先确认是 unit、scene 还是 squad AI。
2. 从配置 ID 查 `AIConfig`，再定位具体节点类。
3. 如果技能释放失败，跳到 `unit/skill` 和 `SkillConfig`。
4. 如果目标选择异常，查 `aitargetnodes` 和 `combat/targetmgr`。

## 相关卡片

- [单位、属性与技能](unit-skill-attr.md)
- [战斗框架](combat-framework.md)
- [配置加载与 tableload](tableload-config.md)
