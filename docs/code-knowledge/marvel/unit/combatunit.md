---
type: Code Module
title: CombatUnit 运行骨架
description: CombatUnit 身份字段、场景生命周期、每帧更新和死亡入口。
repo: marvel
module: gameserver/unit/CombatUnit
resource: gameserver/unit/unit.h
tags: unit, combatunit, lifecycle, death, scene, field
symbols: CombatUnit, CombatUnit::EnterScene, CombatUnit::LeaveScene, CombatUnit::Update, CombatUnit::UpdateDeath
logs: enter scene, leave scene, Check cond
asserts: CHECK_COND, CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl
part_of: unit/index.md
depends_on: unit/index.md
updated_at: 2026-06-20
---

# CombatUnit 运行骨架

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `CombatUnit` 基类。 |
| 职责 | 保存 Unit 身份、场景指针、生命周期状态和通用事件入口。 |
| 边界 | 不展开具体组件内部逻辑；组件见 [Unit 组件系统](unit-components.md)。 |

## 核心字段

| 字段 | 来源 | 用途 |
| --- | --- | --- |
| `m_uID` | `CombatUnit::NewId` 或外部传入 | Unit 逻辑 UID。 |
| `m_uEcsID` | `xecs::create` | ECS 实体 ID。 |
| `m_currScene` | `EnterScene` / `LeaveScene` | 当前场景。 |
| `m_uTemplateID` | 模板初始化 | 配置模板 ID。 |
| `m_uPresentID` | 模板初始化 | 表现 ID。 |
| `m_uEntitySpecies` | `XEntityStatistics.Type` | 决定组件 typelist。 |
| `m_bDeathFlag` / `m_IsDead` | 死亡流程 | 防重复死亡和清理。 |
| `m_bDestroying` | 销毁流程 | 防重复释放。 |

## 模块关系图

```mermaid
flowchart TD
    Unit["CombatUnit"]
    Scene["Scene / SceneBattle"]
    Components["Unit Components"]
    Ecs["XEcs"]
    Attr["UnitCombatAttribute"]
    Death["UpdateDeath / OnDied"]

    Unit --> Scene
    Unit --> Components
    Unit --> Ecs
    Unit --> Attr
    Unit --> Death
```

## 生命周期时序图

```mermaid
sequenceDiagram
    participant Caller as 创建方
    participant Unit as CombatUnit
    participant Scene as Scene
    participant Components as 组件集合

    Caller->>Unit: InitComponents / InitTimers
    Caller->>Unit: EnterScene(scene)
    Unit->>Unit: OnPreEnterScene()
    Unit->>Scene: AddUnit(this)
    Unit->>Unit: OnPostEnterScene()
    Unit->>Components: OnPostEnterScene()
    loop 每帧
        Scene->>Unit: Update(delta)
        Unit->>Components: Update(delta)
        Unit->>Unit: UpdateDeath()
    end
    Caller->>Unit: LeaveScene()
    Unit->>Components: OnLeaveScene()
    Unit->>Scene: DelUnit(this)
```

## 更新流程

```mermaid
flowchart TD
    A["CombatUnit::Update"] --> B{"m_currScene 有效"}
    B -->|否| Z["返回"]
    B -->|是| C{"SceneBattle::IsStop"}
    C -->|是| Z
    C -->|否| D{"Puppet 状态"}
    D -->|是| E["delta = 0"]
    D -->|否| F["保留 delta"]
    E --> G["StateManager::Update"]
    F --> G
    G --> H["RecoverVigorPerSec"]
    H --> I["组件 PartialCall(Update)"]
    I --> J["UpdatePerSceneSecond"]
    J --> K["UpdateDeath"]
```

## 排查入口

| 现象 | 优先检查 |
| --- | --- |
| 离场后访问 crash | `m_currScene`、`LeaveScene` 顺序、组件是否仍持有 UID。 |
| 不更新 | 场景暂停、puppet 状态、是否进场。 |
| 死亡没触发 | `m_bDeathFlag`、`ATTR_CurrentHp`、`UpdateDeath`。 |

