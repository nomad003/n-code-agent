---
type: Code Module
title: UnitController 物理控制器
description: UnitController 负责 PhysX CCT 创建、碰撞过滤、移动执行和控制器释放。
repo: marvel
module: gameserver/physx/UnitController
resource: gameserver/physx/UnitController.h
tags: unit, physx, controller, collision, cct
symbols: UnitController, UnitController::OnPostEnterScene, UnitController::Move, UnitController::UpdateFilterData, UnitController::CanBlock
logs: Check cond
asserts: CHECK_COND
question_types: crash_stack, feature_impl, config_impl
part_of: ../unit-framework.md
depends_on: unit-conf.md
updated_at: 2026-06-20
---

# UnitController 物理控制器

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `UnitController`。 |
| 职责 | 将 Unit 物理参数转成 PhysX CCT，并执行碰撞移动。 |
| 上游 | `UnitConf`, fight group, physics scene。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `m_controller` | PhysX CCT 指针。 |
| `m_filterData` | 碰撞过滤数据。 |
| `m_queryCache` | PhysX 查询缓存。 |
| `m_curGroundHeight` | 当前地面高度。 |

## 控制器时序

```mermaid
sequenceDiagram
    participant Unit as CombatUnit
    participant Controller as UnitController
    participant Conf as UnitConf
    participant PhysX as PhysicsScene
    participant Move as UnitMove

    Unit->>Controller: OnPostEnterScene()
    Controller->>Conf: GetFilterDataByUnitConf()
    Controller->>PhysX: 创建 CCT
    Move->>Controller: Move(delta)
    Controller->>PhysX: CCT move
    PhysX-->>Controller: 碰撞和地面信息
    Controller-->>Move: 位置和碰撞结果
    Unit->>Controller: OnLeaveScene()
    Controller->>PhysX: 释放 CCT
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 物理碰撞异常 | fight group、always collider、skill collider。 |
| 位置纠正后偏差 | `OnCorrectPosition` 是否同步 controller。 |
| 离场 crash | `OnLeaveScene` 是否释放 CCT。 |

