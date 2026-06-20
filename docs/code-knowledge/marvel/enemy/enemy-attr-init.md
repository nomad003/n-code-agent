---
type: Code Module
title: Enemy 属性初始化
description: Enemy 属性初始化读取 XEntityStatistics，处理 AttrCopy、ApplyScale、CallerAttrList 和召唤继承。
repo: marvel
module: gameserver/unit/enemy-attr-init
resource: gameserver/unit/attr/combatattrcalc.cpp
tags: enemy, attr, config, scale, spawn
symbols: CombatAttrCalc::InitEnemyAttr, CombatAttrCalc::InitSpawnAttr, CombatAttrCalc::InitEnemyAttr_OfTable
logs: Check cond
asserts: CHECK_COND
question_types: outage_log, feature_impl, config_impl
part_of: ../enemy-framework.md
depends_on: ../unit/combat-attr-calc.md, enemy-template-config.md
updated_at: 2026-06-20
---

# Enemy 属性初始化

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | Enemy 属性初始化链路。 |
| 职责 | 从模板和 caller 加载属性，应用场景/队伍缩放。 |
| 边界 | 通用属性容器见 [UnitCombatAttribute 属性容器](../unit/unit-combat-attribute.md)。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `BaseAtk` / `BaseDef` / `BaseHp` | 基础攻防血。 |
| `BaseAttr` | 额外属性。 |
| `AttrCopy` | 从另一个模板复制基础属性。 |
| `ApplyScale` | 是否走场景缩放。 |
| `CallerAttrList` | 召唤物按比例继承 caller 属性。 |

## 属性流程

```mermaid
flowchart TD
    A{"初始化类型"} -->|普通 Enemy| B["InitEnemyAttr"]
    A -->|召唤物| C["InitSpawnAttr"]
    B --> D["InitEnemyAttr_OfTable"]
    C --> D
    D --> E{"AttrCopy"}
    E -->|是| F["读取复制模板"]
    E -->|否| G["读取自身模板"]
    F --> H["写基础属性"]
    G --> H
    H --> I{"ApplyScale"}
    I -->|是| J["SceneScaleAttr / TeamScaleAttr"]
    I -->|否| K["跳过缩放"]
    C --> L["复制 caller 未初始化属性"]
    L --> M["CallerAttrList 覆盖"]
    J --> N["InitAttr_AtLast"]
    K --> N
    M --> N
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 属性过高/过低 | `AttrCopy`, `ApplyScale`, `BaseAttr`, 场景缩放。 |
| 召唤物属性异常 | caller 属性、`CallerAttrList`、caller 等级。 |
| HP 初始化异常 | `InitAttr_AtLast` 顺序。 |

