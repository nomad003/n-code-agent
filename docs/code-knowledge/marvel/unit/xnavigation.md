---
type: Code Module
title: XNavigation 导航模块
description: XNavigation 负责导航目标修正、Waypoint 路径、直线可达和传送判定。
repo: marvel
module: gameserver/combat/XNavigation
resource: gameserver/combat/XNavigation.h
tags: unit, navigation, navi, waypoint, ai, move
symbols: XNavigation, XNavigation::Enable, XNavigation::Update, XNavigation::AdjustNaviDestPos
logs: Navi, NaviEnableResult
asserts: CHECK_COND
question_types: outage_log, feature_impl, config_impl
part_of: ../unit-framework.md
depends_on: unit-move.md, unit-conf.md
updated_at: 2026-06-20
---

# XNavigation 导航模块

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `XNavigation`。 |
| 职责 | 给 AI 和移动提供目的点导航、路径推进和失败原因。 |
| 下游 | `UnitMove` 执行实际移动。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `m_originDestPos` / `m_adjustedDestPos` | 原始和修正目标点。 |
| `m_path` / `m_curPathIdx` | 当前路径点。 |
| `m_naviMode` | WaypointGraph 导航模式。 |
| `m_nResult` | 导航结果。 |

## 导航流程

```mermaid
flowchart TD
    A["Enable(dest, radius)"] --> B["AdjustNaviDestPos"]
    B --> C{"_CheckCanStraightReach"}
    C -->|可直达| D["设置直线目标"]
    C -->|不可直达| E{"_CheckCanFindPathByWayPoint"}
    E -->|成功| F["写 path / curPathIdx"]
    E -->|失败| G["NaviEnableResult 失败"]
    D --> H["Update 推进"]
    F --> H
    H --> I{"_IsNeedTeleport"}
    I -->|是| J["传送或强制修正"]
    I -->|否| K["UnitMove 移动到下一点"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| AI 不追人 | `Enable` 是否成功、目标点和半径。 |
| 导航失败 | `[Navi]` 日志和 `NaviEnableResult`。 |
| 频繁传送 | `teleLimit`、路径点、可达检查。 |

