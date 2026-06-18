---
type: Code Module
title: 战斗框架
description: gameserver/combat 下战斗管理、目标、伤害效果、战斗组和工具函数。
repo: marvel
module: gameserver/combat
resource: gameserver/combat
tags: combat, battle, 战斗, damage, target, attacker, navigation, patrol
symbols: XCombat, TargetMgr, AttackerMgr, CombatEffect, BattleGroup
logs: Combat
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl
updated_at: 2026-06-18
---

# 战斗框架

这张卡用于回答“战斗核心在哪”“伤害/目标/攻击者怎么管理”“战斗相关 crash 怎么查”。

## 入口文件

- `gameserver/combat/XCombat.cpp` / `XCombat.h`：战斗核心入口。
- `gameserver/combat/targetmgr.cpp` / `.h`：目标管理。
- `gameserver/combat/attackermgr.cpp` / `.h`：攻击者管理。
- `gameserver/combat/combateffect.cpp` / `.h`：战斗效果。
- `gameserver/combat/combatutility.cpp` / `.h`：战斗工具函数。
- `gameserver/combat/battlegroup.cpp` / `.h`：战斗组。
- `gameserver/combat/XNavigation.cpp`、`XPatrol.cpp`：导航和巡逻。
- `gameserver/combat/damagedebug.cpp`：伤害调试信息。

## 核心职责

- 维护战斗上下文和战斗单位之间的关系。
- 提供目标选择、攻击者记录、伤害/效果处理的公共逻辑。
- 与 `unit` 的属性、技能、Buff、状态共同构成战斗运行时。
- 为 AI、关卡和技能系统提供战斗查询和执行能力。

## 常见链路

- 技能命中/伤害：`unit/skill` 触发后进入 combat effect、target/attacker 管理和属性计算。
- AI 选目标：`ai` 节点可能调用 combat 查询目标。
- Buff 影响战斗：`buff` 修改属性、伤害、状态或触发额外效果。
- 关卡刷怪后：enemy 进入 combat/unit 初始化，随后参与战斗。

## 常见提问

- “某个伤害是怎么算的？”
- “目标选择为什么选错？”
- “攻击者/仇恨/战斗组在哪里维护？”
- “战斗单位死亡或命中 crash 怎么排查？”

## 排查顺序

1. 先确认入口来自技能、Buff、AI、关卡还是协议。
2. 定位 `unit/skill` 或 `buff` 调用到 combat 的位置。
3. 查 `TargetMgr`、`AttackerMgr`、`CombatEffect` 是否持有已销毁单位或错误状态。
4. 若涉及配置，回到 `tableload` 对应 config。

## 相关卡片

- [单位、属性与技能](unit-skill-attr.md)
- [Buff 框架](buff-framework.md)
- [AI 框架](ai-framework.md)
