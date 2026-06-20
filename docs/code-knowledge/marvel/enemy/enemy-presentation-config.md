---
type: Code Module
title: XEntityPresentation 表现配置
description: XEntityPresentation 提供 Enemy 资源路径、缩放、碰撞体、Buff tag 和状态资源。
repo: marvel
module: tableload/XEntityPresentation
resource: tableload/XEntityPresentation
tags: enemy, config, presentation, collider, bufftag
symbols: XEntityPresentation, UnitConf::InitFromPresent, UnitConf::InitBodySize
logs: Check cond
asserts: CHECK_COND_NORETURN
question_types: feature_impl, config_impl, outage_log
part_of: enemy/index.md
depends_on: enemy-template-config.md, ../unit/unit-conf.md
updated_at: 2026-06-20
---

# XEntityPresentation 表现配置

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `XEntityPresentation` 表。 |
| 职责 | 提供模型资源、动作资源、体型缩放、碰撞体和 Buff tag。 |
| 下游 | `UnitConf::InitFromPresent`。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `Prefab` / `AnimLocation` / `SkillLocation` | 客户端表现资源。 |
| `Scale` | 体型缩放。 |
| `BoundRadius` / `BoundHeight` | 碰撞体基础尺寸。 |
| `Huge` / `HugeMonsterColliders` | 大体型多碰撞体。 |
| `CollisionStatus` | 技能碰撞状态。 |
| `BuffListTag` | Buff 目标 tag。 |

## 加载流程

```mermaid
flowchart TD
    A["InitFromPresent(PresentID)"] --> B["读取资源路径"]
    B --> C["读取 Scale"]
    C --> D["计算 BoundRadius / BoundHeight"]
    D --> E{"Huge"}
    E -->|是| F["解析 HugeMonsterColliders"]
    E -->|否| G["普通碰撞体"]
    F --> H["写 UnitPhysicsConf"]
    G --> H
    H --> I["写 BuffListTag / CollisionStatus"]
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| Boss 碰撞体偏差 | `Scale`, `Huge`, `HugeMonsterColliders`。 |
| Buff 目标判断异常 | `BuffListTag`。 |
| 技能碰撞异常 | `CollisionStatus`。 |

