---
type: Code Module
title: AIEntity AI 容器
description: AIEntity 管理 Unit 的 AI agent 生命周期，包括加载、进场、每帧更新和离场。
repo: marvel
module: gameserver/unit/AIEntity
resource: gameserver/ai
tags: unit, ai, aientity, agent, update
symbols: AIEntity, AIEnemyAgent, AIUnitAgent, AIEntity::Update, AIEntity::SetAgent
logs: Dead, Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md, xnavigation.md, skill-mgr.md
updated_at: 2026-06-20
---

# AIEntity AI 容器

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `AIEntity`。 |
| 职责 | 持有 AI agent，并接入 Unit 进场、更新、离场。 |
| 下游 | `SkillMgr`、`XNavigation`、目标选择。 |

## 生命周期

| 阶段 | 行为 |
| --- | --- |
| 构造 | `m_oAIEntity(this)`。 |
| Enemy 初始化 | `SetAgent(new AIEnemyAgent(...))`。 |
| 进场前 | `StartLoad(scene)`。 |
| 场景就绪 | agent `EnterScene`。 |
| 每帧 | `AIEntity::Update`。 |
| 离场 | agent `LeaveScene`。 |

## 每帧时序

```mermaid
sequenceDiagram
    participant Unit as CombatUnit
    participant AI as AIEntity
    participant Agent as AIUnitAgent
    participant Skill as SkillMgr
    participant Navi as XNavigation

    Unit->>AI: Update(delta)
    AI->>Agent: Tick / Behavior
    Agent->>Skill: 选择技能
    Agent->>Navi: 下发导航目标
    Navi-->>Unit: 移动意图
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| AI 不运行 | agent 是否创建、`StartLoad` 是否执行。 |
| 不索敌 | 视野、战斗组、目标管理。 |
| 不放技能 | `SkillMgr::RegisterAIMgr` 和 AI 技能配置。 |

