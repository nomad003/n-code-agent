---
type: Code Module
title: 单位、属性与技能
description: CombatUnit、CombatRole、CombatEnemy、属性、技能、状态和同步的模块地图。
repo: marvel
module: gameserver/unit
resource: gameserver/unit
tags: unit, combatunit, combatrole, combatenemy, skill, attr, state, sync, 单位, 技能, 属性
symbols: CombatUnit, CombatRole, CombatEnemy, SkillMgr, SkillCore, CombatAttrCalc
logs: UnitLogErr, skill not find
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# 单位、属性与技能

这张卡用于回答“战斗单位如何初始化”“玩家/怪物单位区别”“技能系统入口在哪”“属性如何计算”。

## 入口文件

- `gameserver/unit/unit.cpp` / `unit.h`：战斗单位基础。
- `gameserver/unit/combatrole.cpp` / `.h`：玩家战斗角色。
- `gameserver/unit/enemy.cpp` / `.h`：敌人/怪物战斗单位。
- `gameserver/unit/attr/`：属性计算，常见入口包括 `CombatAttrCalc`。
- `gameserver/unit/skill/`：技能管理和技能核心，常见入口是 `SkillMgr`、`SkillCore`。
- `gameserver/unit/state/`：状态机和状态相关逻辑。
- `gameserver/unit/sync/`：单位同步。
- `gameserver/unit/conf/`：单位配置封装。

## 核心职责

- 抽象战斗单位生命周期、位置、属性、技能、状态和同步。
- 区分玩家战斗角色 `CombatRole` 和敌人 `CombatEnemy` 的初始化链路。
- 将配置表中的实体/技能/属性数据转成运行时对象。
- 连接 `scene`、`level`、`combat`、`buff`、`ai` 和 `xecs`。

## 常见链路

- 怪物初始化：`Level` / `LevelSpawner` 创建 enemy，进入 `CombatEnemy::Init`，再初始化配置、AI、技能、属性和 ECS。
- 技能创建：`SkillMgr` 创建技能对象，`SkillCore` 初始化具体技能配置。
- 属性初始化：角色/怪物根据各自配置和场景上下文初始化属性。
- 状态/同步：单位状态变化后需要同步给客户端或驱动 ECS 状态。

## 常见问题

- “某个技能为什么初始化失败？”
- “怪物/玩家属性从哪里来？”
- “单位已经销毁但还被引用导致 crash？”
- “状态切换、移动、同步问题怎么查？”

## 排查顺序

1. 根据栈帧判断是 `unit` 基类、`combatrole`、`enemy`、`skill`、`attr` 还是 `state/sync`。
2. 如果是配置缺失，优先查 `tableload` 对应 config。
3. 如果是怪物技能，直接使用 [怪物配置与敌人技能配置链路](monster-config.md)。
4. 如果涉及 ECS 行为，继续看 [XEcs 框架](xecs-framework.md)。

## 相关卡片

- [怪物配置与敌人技能配置链路](monster-config.md)
- [战斗框架](combat-framework.md)
- [Buff 框架](buff-framework.md)
- [XEcs 框架](xecs-framework.md)
