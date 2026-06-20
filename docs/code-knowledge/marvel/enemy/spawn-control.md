---
type: Code Module
title: SpawnControl 召唤控制
description: SpawnControl 记录召唤物限制组、数量上限和超限死亡技能。
repo: marvel
module: gameserver/unit/SpawnControl
resource: gameserver/unit
tags: enemy, spawn, spawncontrol, limit, follow
symbols: SpawnControl, SpawnControl::OnAdd, SpawnControl::OnDel, SpawnFollow, SpawnLimit
logs: not find final host, overflow last uid
asserts: ASSERT_FALSE
question_types: outage_log, feature_impl, config_impl
part_of: ../enemy-framework.md
depends_on: scene-unit-handler.md, combat-enemy.md
updated_at: 2026-06-20
---

# SpawnControl 召唤控制

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `SpawnControl` 和召唤配置。 |
| 职责 | 管理 final host 召唤数量限制、跟随绑定和超限处理。 |
| 配置 | `SpawnFollow.txt`, `SpawnLimit.txt`。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `unit2group` | 召唤物 UID 到限制组。 |
| `group2units` | 限制组到召唤物列表和上限。 |
| `m_caller_uid` | 调试 caller。 |

## 召唤控制流程

```mermaid
flowchart TD
    A["CreateUnitByCaller"] --> B["设置 host / finalhost"]
    B --> C{"SpawnFollow 存在"}
    C -->|是| D["caller 相对坐标"]
    D --> E["xecs::bindTo"]
    C -->|否| F["世界坐标"]
    E --> G["SetAttrByCaller"]
    F --> G
    G --> H["EnterScene"]
    H --> I["finalhost SpawnControl::OnAdd"]
    I --> J{"超过 SpawnLimit"}
    J -->|否| K["记录 UID"]
    J -->|是| L["最早召唤物 force2idle"]
    L --> M["drive2skill(dead_skill)"]
    M --> K
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 召唤数量不对 | `SpawnLimit.CountLimit`, `PassiveSkill`。 |
| 召唤不跟随 | `SpawnFollow.ID`, `xecs::bindTo`。 |
| 残留召唤物 | `OnDel`, final host 是否存在。 |

