---
type: Code Module
title: BindInfo 平台绑定
description: BindInfo 每帧检查 Unit 与平台的自动绑定、脚本绑定和解绑。
repo: marvel
module: gameserver/unit/BindInfo
resource: gameserver/unit/plat/bindinfo.h
tags: unit, bind, platform, ecs
symbols: BindInfo, BindInfo::Update, xecs::bindTo
logs: Check cond
asserts: CHECK_COND
question_types: crash_stack, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md
updated_at: 2026-06-20
---

# BindInfo 平台绑定

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `BindInfo`。 |
| 职责 | 检查 Unit 与平台的绑定/解绑状态。 |
| 边界 | Enemy 默认不是自动绑定，通常由技能或关卡脚本绑定。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `is_dirty_` | 标记绑定状态需要检查。 |

## 绑定流程

```mermaid
flowchart TD
    A["BindInfo::Update"] --> B{"is_dirty_ 或 auto-bind"}
    B -->|否| C["不处理"]
    B -->|是| D["检查平台关系"]
    D --> E{"需要 bind/unbind"}
    E -->|bind| F["xecs::bindTo"]
    E -->|unbind| G["脚本或平台解绑"]
    E -->|无变化| C
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 平台绑定错位 | ECS bind、local_pos、平台 transform。 |
| 解绑失败 | 脚本解绑和 `is_dirty_`。 |
| Enemy 意外绑定 | auto-bind 标记来源。 |

