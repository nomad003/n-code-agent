---
type: Code Module
title: UnitConf 配置封装
description: UnitConf 和 UnitPhysicsConf 读取模板/表现配置并生成物理体型参数。
repo: marvel
module: gameserver/unit/UnitConf
resource: gameserver/unit/conf/unitconf.h
tags: unit, config, unitconf, physics, presentation, statistics
symbols: UnitConf, UnitPhysicsConf, UnitConf::InitFromPresent, UnitConf::InitFromTemplate, UnitConf::InitBodySize
logs: can't find monster template id
asserts: CHECK_COND_NORETURN
question_types: outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md
updated_at: 2026-06-20
---

# UnitConf 配置封装

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `UnitConf` / `UnitPhysicsConf`。 |
| 职责 | 聚合模板、表现、体型、碰撞和 Buff tag 配置。 |
| 下游 | `UnitMove`、`UnitController`、`XNavigation`、Buff 目标判断。 |

## 字段

| 字段 | 来源 | 用途 |
| --- | --- | --- |
| `present_conf_` | `XEntityPresentation` | 表现、体型、碰撞、Buff tag。 |
| `template_conf_` | `XEntityStatistics` | 模板、属性、AI、技能、阵营。 |
| `phys_conf_` | 模板/表现组合 | 运行时物理参数。 |
| `bound_aabb_conf_` | `InitBodySize` | Unit AABB。 |
| `m_BuffListTags` | `BuffListTag` | Buff 目标匹配。 |

## 配置加载流程

```mermaid
flowchart TD
    A["InitConf"] --> B["InitFromPresent(present_id)"]
    B --> C{"XEntityPresentation 存在"}
    C -->|否| X["CHECK_COND_NORETURN"]
    C -->|是| D["读取 Scale / BoundRadius / BoundHeight / Huge"]
    D --> E["InitBodySize 计算半径/高度/AABB"]
    E --> F{"Huge"}
    F -->|是| G["解析 HugeMonsterColliders"]
    F -->|否| H["普通碰撞体"]
    G --> I["InitFromTemplate(template_id)"]
    H --> I
    I --> J{"XEntityStatistics 存在"}
    J -->|否| K["日志: can't find monster template id"]
    K --> X
    J -->|是| L["读取 Block / BlockFlag / CastRangeY"]
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 怪物体型异常 | `Scale`, `BoundRadius`, `BoundHeight`, `HugeMonsterColliders`。 |
| 碰撞状态异常 | `Block`, `BlockFlag`, `CollisionStatus`。 |
| 模板缺失 crash | `XEntityStatistics.ID` 和调用方传入模板 ID。 |

