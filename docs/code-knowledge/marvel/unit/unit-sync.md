---
type: Code Module
title: Unit 同步模块
description: EcsSnapshot、XActionSender 和 XActionReceiver 负责 Unit 输入接收和状态广播。
repo: marvel
module: gameserver/unit/sync
resource: gameserver/unit
tags: unit, sync, ecs, action, snapshot
symbols: EcsSnapshot, XActionSender, XActionReceiver, XActionSender::PackageSyncData, XActionReceiver::OnMoveReceived
logs: SyncStep, Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl
part_of: unit/index.md
depends_on: combatunit.md, bind-info.md
updated_at: 2026-06-20
---

# Unit 同步模块

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `EcsSnapshot` / `XActionSender` / `XActionReceiver`。 |
| 职责 | 接收客户端输入，读取 ECS 状态并广播同步数据。 |
| 关键风险 | 平台绑定、本地坐标、技能状态和移动状态不一致。 |

## Snapshot 字段

| 字段 | 来源 |
| --- | --- |
| `uid` / `ecs_id` | Unit。 |
| `pos` / `face` | Unit/ECS。 |
| `binded` / `local_pos` | 平台绑定。 |
| `move_type` / `state_type` | ECS。 |
| `scrpit` | 当前技能 hash。 |

## 同步时序

```mermaid
sequenceDiagram
    participant Client as Client
    participant Receiver as XActionReceiver
    participant Unit as CombatUnit
    participant XEcs as XEcs
    participant Sender as XActionSender
    participant AOI as AOI

    Client->>Receiver: Move / Face / Cast / Slot
    Receiver->>Unit: IsValid 校验
    Receiver->>XEcs: 写输入
    XEcs-->>Unit: 运行后状态
    Unit->>Sender: Package()
    Sender->>XEcs: 读取 pos / face / move / skill
    Sender->>AOI: Broadcast StepSyncData
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 位置同步错 | `binded`, `local_pos`, ECS pos。 |
| 技能状态错 | `scrpit` 和 `state_type`。 |
| 输入无效 | `XActionReceiver::IsValid`。 |

