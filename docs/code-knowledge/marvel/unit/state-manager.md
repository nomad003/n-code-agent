---
type: Code Module
title: StateManager 状态管理
description: StateManager 管理 Boss/Player 状态、阶段、机制条、技能窗口和受击状态。
repo: marvel
module: gameserver/unit/StateManager
resource: gameserver/unit/state/StateManager.h
tags: unit, state, boss, stage, mode, hit
symbols: StateManager, BossStage, BossModeState, BossResistState, StateManager::Update, StateManager::OnStartSkill
logs: Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md, skill-mgr.md
updated_at: 2026-06-20
---

# StateManager 状态管理

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `StateManager`。 |
| 职责 | 驱动阶段、Mode、韧性/异常、机制条和技能/hit 窗口状态。 |
| 配置 | `EnemyStage`, `EnemyModeState`, `EnemyResist`, `EnemyJZ`, `PlayerJZ`。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `mBossModeState` | Boss Mode 状态。 |
| `mBossStage` | 阶段。 |
| `mAllSkillType` | 技能 hash 到状态技能类型。 |
| `m_isSkillCasting` / `m_isHiting` | 技能和 hit 窗口。 |

## 状态事件流程

```mermaid
flowchart TD
    A["OnPreEnterScene"] --> B["读取状态配置"]
    B --> C["InitSkill 建立状态技能映射"]
    D["ProjectDamage / OnAttrChange"] --> E["HP / 韧性 / 机制条变化"]
    E --> F{"达到阶段或 Mode 条件"}
    F -->|否| G["保留当前状态"]
    F -->|是| H["切换 BossStage / Mode"]
    H --> I["触发阶段 Buff / 技能 / cutscene"]
    J["OnStartSkill / OnStartHit"] --> K["标记窗口"]
    L["OnEndSkill / OnEndHit"] --> M["清理窗口"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 阶段不切 | 当前 HP、`EnemyStage.StaticsID`、BossStage 条件。 |
| 状态技能不放 | `mAllSkillType`、`SkillListForEnemy.ModeUse`。 |
| 状态延迟 | `HandleDelay` 和技能/hit 窗口。 |

