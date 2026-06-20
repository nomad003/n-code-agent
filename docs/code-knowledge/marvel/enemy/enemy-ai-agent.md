---
type: Code Module
title: AIEnemyAgent 怪物 AI
description: AIEnemyAgent 从模板 AIID 选择 AI 表，加载行为树、状态机、视野、巡逻和自定义变量。
repo: marvel
module: gameserver/ai/AIEnemyAgent
resource: gameserver/ai
tags: enemy, ai, agent, behavior, patrol
symbols: AIEnemyAgent, AIUnitAgent, AIEnemyAgent::_GetAIIDFromConfig, AIUnitAgent::LoadConfig, AIEnemyAgent::SetPatrol
logs: Dead, Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: ../enemy-framework.md
depends_on: combat-enemy.md, ../unit/ai-entity.md
updated_at: 2026-06-20
---

# AIEnemyAgent 怪物 AI

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `AIEnemyAgent` / `AIUnitAgent`。 |
| 职责 | 加载怪物 AI 配置，处理巡逻、索敌、进战和自定义变量。 |
| 配置 | `UnitAITable` 或 `SquadMemberAITable`。 |

## AI ID 选择

| 条件 | 行为 |
| --- | --- |
| `AIID[1] == 0` | 从 `UnitAITable` 读取 `AIID[0]`。 |
| `AIID[1] == 1` | 从 `SquadMemberAITable` 读取 `AIID[0]`。 |
| `LevelInit(aiID != 0)` | 覆盖 origin AI ID。 |

## 加载流程

```mermaid
flowchart TD
    A["CombatEnemy::Init"] --> B["new AIEnemyAgent"]
    B --> C["_GetAIIDFromConfig"]
    C --> D{"AIID[1]"}
    D -->|0| E["UnitAITable"]
    D -->|1| F["SquadMemberAITable"]
    E --> G["AIUnitAgent::LoadConfig"]
    F --> G
    G --> H["加载 Tree / StateMachine / CustomVariables"]
    H --> I["OnPreEnterScene StartLoad"]
    I --> J["OnEnterScene 巡逻/索敌"]
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 怪物不索敌 | `Sight`, `FightTogetherDis`, 战斗组。 |
| 行为树没跑 | `Tree`, `StateMachine`, `StartLoad`。 |
| 巡逻不对 | `PatrolID` 和 `LevelInit` 覆盖。 |

