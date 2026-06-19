---
type: Code Module
title: XEcs 框架
description: XEcs component/system/utility 三层、技能/状态/移动系统和 gameserver 集成点。
repo: marvel
module: ecs/XEcs/ecs
resource: ecs/XEcs/ecs
tags: xecs, ecs, component, system, utility, skill, state, movement, sync
symbols: XInstance, XSkillSys, XStateSys, XMovement
logs: XEcs
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
depends_on: unit-skill-attr.md, combat-framework.md
supplements: gameserver-overview.md, unit-skill-attr.md
updated_at: 2026-06-18
---

# XEcs 框架

这张卡用于回答“XEcs 是什么”“gameserver 如何引用 ECS 库”“技能/状态/移动在 ECS 里怎么分层”。

## 入口文件

- `ecs/XEcs/ecs/XInstance.hpp`：ECS 实例入口。
- `ecs/XEcs/ecs/component/`：组件定义，例如 `XSkill`、`XLocation`、`XMovement`、`XStateAbilityData`、`XBuff...`、`XNet`。
- `ecs/XEcs/ecs/system/`：系统逻辑，例如 `XSkillSys`、`XStateSys`、`XRunSys`、`XHitSys`、`XSyncSys`。
- `ecs/XEcs/ecs/utility/`：数学、解析、脚本、技能、事件、曲线、文件等工具。
- `gameserver/xecs/`：gameserver 侧 XEcs 适配和同步工具。

## 核心职责

- 用 component/system 组织客户端/服务器共享的战斗表现、技能、移动、状态等逻辑。
- component 主要承载数据，system 处理行为，utility 提供解析和数学/脚本支持。
- gameserver 通过 `gameserver/xecs` 和 `unit` 初始化链路接入。

## 组件线索

- 技能：`XSkill`、`XSkillData`、`XSkillCharge`、`XSkillResult`、`XSkillTargetAim`
- 移动/位置：`XLocation`、`XMovement`、`XRotation`
- 状态/行为：`XStateAbilityData`、`XIdle`、`XNode*`
- 同步/网络：`XSync`、`XLiteSync`、`XNet`
- 蓝图/节点：`XBluePrint`、`XNodeAction`、`XNodeCondition`、`XNodeSwitch`

## 系统线索

- 技能系统：`XSkillSys`、`XSkillChargeSys`、`XSkillBulletSys`、`XSkillResultSys`
- 状态系统：`XStateSys`、`XStatusSys`、`XDeathSys`
- 移动系统：`XRunSys`、`XJumpSys`、`XFlySys`、`XLocationSys`
- 同步系统：`XSyncSys`、`XNetSys`
- 节点系统：`XActionNodeSys`、`XConditionNodeSys`、`XSwitchNodeSys`

## 常见提问

- “gameserver 和 XEcs 怎么连接？”
- “某个技能行为在 ECS 里哪个 system 处理？”
- “移动/状态/同步问题应该看 component 还是 system？”
- “ECS 配置/蓝图如何解析？”

## 排查顺序

1. 先确认问题是 gameserver 业务逻辑还是 XEcs 行为。
2. 根据名词查 component 数据，再查同名或近似 system。
3. 如果从 gameserver 进入，先看 `gameserver/xecs` 和 `unit` 初始化/同步代码。
4. 配置/蓝图解析问题查 `ecs/XEcs/ecs/utility/utility2*.hpp`。

## 相关卡片

- [单位、属性与技能](unit-skill-attr.md)
- [战斗框架](combat-framework.md)
- [怪物配置与敌人技能配置链路](monster-config.md)
