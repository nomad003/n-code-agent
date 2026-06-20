---
type: Reference
title: marvel 代码知识库索引
description: marvel 知识入口。核心战斗域优先。
repo: marvel
module: index
resource: .
tags: marvel, index, combat, gameserver, ecs
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-20
---

# marvel 代码知识库索引

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 用途 | 作为 marvel 知识库入口。 |
| 当前重点 | `gameserver` 核心战斗域。 |
| 暂不覆盖 | 网络、登录、协议连接、服务部署。 |
| 使用要求 | 具体结论需读取当前代码核实。 |

## 已整理

- [gameserver 核心战斗总体框架](gameserver-combat-core-overview.md)
- [Unit 通用层](unit-framework.md)
- [Unit 运行骨架与组件系统](unit-runtime-components.md)
- [Unit 配置、属性、移动](unit-config-attr-move.md)
- [Unit 状态、技能、AI、同步](unit-state-skill-ai-sync.md)
- [Enemy 层](enemy-framework.md)
- [Enemy 创建与生命周期](enemy-runtime-lifecycle.md)
- [Enemy 配置、AI、技能、召唤](enemy-config-ai-skill-spawn.md)

## 后续拆分

- 场景与 SceneBattle
- 关卡 Level / LevelSpawner / 刷怪
- CombatRole 派生层
- SkillMgr / SkillCore / SkillConfig
- XBuffContainer / BuffConfig / Buff effect
- AIAgent / AIUnitAgent / AI 节点
- XEcs / XFacility / XSirius
