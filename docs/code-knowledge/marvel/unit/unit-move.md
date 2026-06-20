---
type: Code Module
title: UnitMove 移动与碰撞修正
description: UnitMove 负责移动入口、地面修正、动态阻挡、触发墙和可行走区检查。
repo: marvel
module: gameserver/unit/UnitMove
resource: gameserver/unit/move/unitmove.h
tags: unit, move, collision, wall, walkable
symbols: UnitMove, UnitMove::TryMove, UnitMove::ForceGround, UnitMove::CheckCollision, UnitMove::BroadcastCorrectLocation
logs: Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: unit-conf.md, unit-controller.md
updated_at: 2026-06-20
---

# UnitMove 移动与碰撞修正

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `UnitMove`。 |
| 职责 | 处理移动、地面高度、阻挡碰撞、墙触发和位置纠正。 |
| 配置 | `Block`, `BlockFlag`, `BoundRadius`, `DynamicWall.txt`, 场景地图数据。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `scene_` | 当前战斗场景缓存。 |
| `m_lastWalkablePos` | 最近可行走位置。 |
| `m_returnWalkableArea` | 是否需要返回可行走区。 |
| `m_inNoFreeFlyZone` | 是否在禁自由飞区域。 |

## 移动流程

```mermaid
flowchart TD
    A["TryMove / TransferLocation"] --> B["读取 UnitConf 体型和 Block"]
    B --> C["ForceGround 修正地面高度"]
    C --> D{"CheckBlock / CheckCollision"}
    D -->|阻挡| E["CheckDynamicBlockWithCorrectPos"]
    E --> F{"可修正位置"}
    F -->|有| G["BroadcastCorrectLocation"]
    F -->|无| H["拒绝或回滚"]
    D -->|不阻挡| I["写入位置"]
    G --> I
    I --> J["TestTrigger 动态墙"]
    J --> K["记录 LastWalkablePos / 禁飞区"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 穿墙 | `CheckBlock`、`DynamicWall`、`BlockFlag`。 |
| 被拉回 | `m_lastWalkablePos`、非可行走区检查。 |
| 高度异常 | `ForceGround`、地图 query、空中单位标记。 |

