---
type: Code Module
title: CombatAttrCalc 属性初始化
description: CombatAttrCalc 负责 Enemy/Spawn 属性加载、复制、缩放和最终当前值初始化。
repo: marvel
module: gameserver/unit/CombatAttrCalc
resource: gameserver/unit/attr/combatattrcalc.h
tags: unit, attr, combatattrcalc, scale, spawn
symbols: CombatAttrCalc, CombatAttrCalc::InitEnemyAttr, CombatAttrCalc::InitSpawnAttr, CombatAttrCalc::SceneScaleAttr, CombatAttrCalc::InitAttr_AtLast
logs: Check cond
asserts: CHECK_COND
question_types: outage_log, feature_impl, config_impl
part_of: unit/index.md
depends_on: unit-combat-attribute.md, unit-conf.md
updated_at: 2026-06-20
---

# CombatAttrCalc 属性初始化

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `CombatAttrCalc`。 |
| 职责 | 从表和场景读取基础属性，处理复制、缩放和当前值初始化。 |
| 下游 | 伤害、移动速度、Buff、技能 CD、同步。 |

## 功能

| 功能 | 函数 |
| --- | --- |
| Enemy 属性初始化 | `InitEnemyAttr` |
| 召唤物属性初始化 | `InitSpawnAttr` |
| 表属性加载 | `InitEnemyAttr_OfTable` |
| 场景缩放 | `SceneScaleAttr` |
| 队伍缩放 | `TeamScaleAttr` |
| 最终当前值 | `InitAttr_AtLast` |
| 运行时派生速度 | `GetRunSpeed`, `GetFlySpeed`, `GetAttackSpeed` |

## 初始化时序

```mermaid
sequenceDiagram
    participant Enemy as CombatEnemy
    participant Calc as CombatAttrCalc
    participant Conf as XEntityStatistics
    participant Attr as UnitCombatAttribute
    participant Scene as Scene

    Enemy->>Attr: Init(templateID, uid)
    Enemy->>Calc: InitEnemyAttr(enemy, conf, scene)
    Calc->>Conf: 读取基础攻防血和 BaseAttr
    alt AttrCopy 非 0
        Calc->>Conf: 切换复制模板
    end
    Calc->>Attr: 写入基础属性
    alt ApplyScale 非 0
        Calc->>Scene: 读取场景缩放
        Calc->>Attr: SceneScaleAttr
    end
    Calc->>Attr: InitAttr_AtLast
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 属性过高/过低 | `AttrCopy`, `ApplyScale`, `BaseAttr`, 场景/队伍缩放。 |
| 召唤物属性异常 | caller 复制、`CallerAttrList`、caller 等级。 |
| 速度异常 | `RunSpeed`, `FlySpeed`, speed percent, scale。 |

