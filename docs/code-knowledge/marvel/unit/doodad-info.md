---
type: Code Module
title: DoodadInfo 掉落物信息
description: DoodadInfo 保存掉落物配置、创建者、生命周期和拾取角色。
repo: marvel
module: gameserver/unit/DoodadInfo
resource: gameserver/unit/doodadinfo/doodad.h
tags: unit, doodad, drop, lifetime
symbols: DoodadInfo, DropObject, DoodadConfig
logs: Check cond
asserts: CHECK_COND
question_types: feature_impl, config_impl, outage_log
part_of: unit/index.md
depends_on: unit-components.md
updated_at: 2026-06-20
---

# DoodadInfo 掉落物信息

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `DoodadInfo`。 |
| 职责 | 管理 Doodad/drop 的配置行、生命周期和拾取状态。 |
| 配置 | `DropObject.txt` 和 `DoodadConfig`。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `m_row` | `DropObject` 配置行。 |
| `m_creatorUid` | 创建者 UID。 |
| `m_livetime` | 生命周期。 |
| `m_buffIndex` | Buff 组索引。 |
| `m_pickRoleID` | 拾取角色。 |

## 生命周期流程

```mermaid
flowchart TD
    A["Species_Doodad"] --> B["typelist 绑定 DoodadInfo"]
    B --> C["读取 DropObject / DoodadConfig"]
    C --> D["进入场景"]
    D --> E["Update 扣 livetime"]
    E --> F{"被拾取或超时"}
    F -->|否| E
    F -->|是| G["清理 Doodad"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 掉落物不出现 | species、typelist、DropObject。 |
| 拾取异常 | `m_pickRoleID` 和生命周期。 |
| 清理异常 | Doodad 清理事件和场景删除。 |

