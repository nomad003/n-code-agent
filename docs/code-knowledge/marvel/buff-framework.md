---
type: Code Module
title: Buff 框架
description: XBuff、XBuffContainer、Buff 效果、触发器和 BuffConfig 的模块地图。
repo: marvel
module: gameserver/buff
resource: gameserver/buff
tags: buff, xbuff, trigger, effect, dot, shield, attr, stack, 增益
symbols: XBuff, XBuffContainer, XBuffEffect, XBuffTrigger, BuffConfig
logs: Buff
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: gameserver-overview.md
depends_on: tableload-config.md, unit-skill-attr.md, combat-framework.md
supplements: unit-skill-attr.md, combat-framework.md
updated_at: 2026-06-18
---

# Buff 框架

这张卡用于回答“Buff 如何创建/生效/结束”“Buff 配置字段在哪里使用”“Buff 触发器问题怎么排查”。

## 入口文件

- `gameserver/buff/XBuff.cpp` / `.h`：Buff 对象基础。
- `gameserver/buff/XBuffContainer.cpp` / `.h`：单位上的 Buff 容器。
- `gameserver/buff/XBuffConfigData.cpp` / `.h`：Buff 配置数据封装。
- `gameserver/buff/XBuffEffect.cpp` / `.h`：效果基类。
- `gameserver/buff/XBuffTrigger.cpp` / `.h`：触发器基类。
- `gameserver/buff/XBuffUtility.cpp` / `.h`：Buff 工具函数。
- `gameserver/tableload/buffconfig.cpp` / `.h`：Buff 配置查询。

## 子类型线索

- 属性变化：`XBuffChangeAttr`
- 护盾：`XBuffShield`
- Dot：`XBuffDot`
- 减 CD：`XBuffReduceCD`
- 变身/状态：`XBuffTransform`、`XBuffSpecialState`
- 技能伤害：`XBuffSkillDamage`
- 触发器：`XBuffTriggerBySkill`、`ByHit`、`ByBeHit`、`ByBuff`、`ByStackCount`、`AtEnd`

## 核心职责

- 从配置创建 Buff、效果和触发器。
- 挂载到 `CombatUnit` 的 Buff 容器。
- 根据时间、命中、受击、技能、层数、属性等条件触发效果。
- 影响属性、伤害、技能、状态、阵营或其它战斗行为。

## 常见提问

- “某个 Buff 为什么没生效？”
- “Buff 层数/持续时间如何计算？”
- “Buff 触发器由什么事件驱动？”
- “Buff 配置字段在哪里解析？”

## 排查顺序

1. 从 Buff ID 或名字查 `BuffConfig` 和 `XBuffConfigData`。
2. 查 Buff 创建入口和挂载的 `XBuffContainer`。
3. 根据配置类型定位具体 `XBuffEffect` / `XBuffTrigger` 子类。
4. 如果影响技能/伤害，继续查 `unit/skill` 和 `combat`。

## 相关卡片

- [配置加载与 tableload](tableload-config.md)
- [单位、属性与技能](unit-skill-attr.md)
- [战斗框架](combat-framework.md)
