---
type: Code Module
title: CombatEnemy 生命周期
description: CombatEnemy 保存怪物字段，接入初始化、进离场、LevelInit、死亡和清理。
repo: marvel
module: gameserver/unit/CombatEnemy
resource: gameserver/unit/enemy.h
tags: enemy, combatenemy, lifecycle, level, death
symbols: CombatEnemy, CombatEnemy::Init, CombatEnemy::LevelInit, CombatEnemy::OnPreEnterScene, CombatEnemy::OnDied, CombatEnemy::CleanUpInScene
logs: create enemy uid, pre enter scene, post enter scene, dead disappear, clear up scene, leave scene
asserts: CHECK_COND, CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl
part_of: ../enemy-framework.md
depends_on: ../unit/combatunit.md
updated_at: 2026-06-20
---

# CombatEnemy 生命周期

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `CombatEnemy`。 |
| 职责 | 怪物派生层字段、初始化、进离场、关卡参数、死亡清理。 |
| 边界 | 创建入口见 [SceneUnitHandler 创建入口](scene-unit-handler.md)。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `m_WaveID` / `m_GroupID` / `m_WaveIndex` | 关卡 wave/group 信息。 |
| `m_hostlevel` / `m_KeepCount` | 关卡宿主和 keep count。 |
| `m_deadtime` / `m_dead_disappeartime` | 死亡消失倒计时。 |
| `m_host` / `m_finalhost` | 召唤关系。 |
| `m_spawn_follow.followid_` | 跟随召唤绑定。 |

## 初始化时序

```mermaid
sequenceDiagram
    participant Handler as SceneUnitHandler
    participant Enemy as CombatEnemy
    participant Unit as CombatUnit
    participant Attr as CombatAttrCalc
    participant Skill as SkillMgr
    participant XEcs as XEcs

    Handler->>Enemy: Init(conf, scene)
    Enemy->>Unit: InitComponents()
    Enemy->>Enemy: InitConf / InitTimers
    Enemy->>Enemy: 创建 AIEnemyAgent
    Enemy->>Skill: InitSkills(scene)
    Enemy->>Attr: InitEnemyAttr()
    Enemy->>Enemy: StateManager.Init / InitFightGroup
    Enemy->>XEcs: xecs::create()
    Enemy->>Skill: PostInit / BindEcs()
```

## 死亡清理流程

```mermaid
flowchart TD
    A["OnDied"] --> B["设置 m_deadtime"]
    B --> C["SceneEventEnemyDieArgs"]
    C --> D["LevelEventEnemyArgs_Die"]
    D --> E["AI Dead 消息"]
    E --> F["CombatUnit::OnDied"]
    G["Update"] --> H{"m_deadtime > 0"}
    H -->|是| I["扣倒计时"]
    I --> J{"到期"}
    J -->|是| K["DoDeadDisappear"]
    K --> L["CleanUpInScene"]
    L --> M["LeaveScene"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 进场后 AI 不加载 | `OnPreEnterScene`、`StartLoad`。 |
| wave/group 不对 | `LevelInit` 参数。 |
| 死亡后不消失 | `m_dead_disappeartime`、`SceneActionRate`。 |

