---
type: Reference
title: marvel 代码知识库索引
description: 重新整理后的 marvel 代码知识入口，优先沉淀核心战斗域。
repo: marvel
module: index
resource: .
tags: marvel, index, combat, gameserver, ecs
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-20
---

# marvel 代码知识库索引

这是一份重新整理后的知识入口。当前优先覆盖 `gameserver` 核心战斗域，暂不整理网络、登录、协议连接、服务部署等服务器外围模块。具体结论仍需用工具读取当前代码核实。

## 已整理

- [gameserver 核心战斗总体框架](gameserver-combat-core-overview.md)

## 后续拆分

- 场景与 SceneBattle
- 关卡 Level / LevelSpawner / 刷怪
- CombatUnit / CombatEnemy / CombatRole
- SkillMgr / SkillCore / SkillConfig
- XBuffContainer / BuffConfig / Buff effect
- AIAgent / AIUnitAgent / AI 节点
- XEcs / XFacility / XSirius
