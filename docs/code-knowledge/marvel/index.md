---
type: Reference
title: marvel 代码知识库索引
description: marvel 知识入口。核心战斗域优先。
repo: marvel
module: index
resource: .
tags: marvel, index, combat, gameserver, ecs
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-22
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

- [gameserver 核心战斗总体框架](gameserver/combat-core-overview.md)
- [Unit 层索引](unit/index.md)
- [Skill 层索引](skill/index.md)
- [AI 层索引](ai/index.md)
- [Level 层索引](level/index.md)
- [CombatUnit 运行骨架](unit/combatunit.md)
- [Unit 组件系统](unit/unit-components.md)
- [UnitConf 配置封装](unit/unit-conf.md)
- [UnitCombatAttribute 属性容器](unit/unit-combat-attribute.md)
- [CombatAttrCalc 属性初始化](unit/combat-attr-calc.md)
- [UnitMove 移动与碰撞修正](unit/unit-move.md)
- [XNavigation 导航模块](unit/xnavigation.md)
- [UnitController 物理控制器](unit/unit-controller.md)
- [StateManager 状态管理](unit/state-manager.md)
- [SkillMgr 技能管理](unit/skill-mgr.md)
- [技能编辑器节点枚举](skill/skill-editor-nodes.md)
- [XBuffContainer Buff 容器接入](unit/xbuff-container.md)
- [AIEntity AI 容器](unit/ai-entity.md)
- [AI 编辑器节点枚举](ai/ai-editor-nodes.md)
- [关卡编辑器节点枚举](level/level-editor-nodes.md)
- [UnitEffect Affix Effect](unit/unit-effect.md)
- [DoodadInfo 掉落物信息](unit/doodad-info.md)
- [BindInfo 平台绑定](unit/bind-info.md)
- [Unit 同步模块](unit/unit-sync.md)
- [Enemy 层索引](enemy/index.md)
- [CombatEnemy 生命周期](enemy/combat-enemy.md)
- [SceneUnitHandler 创建入口](enemy/scene-unit-handler.md)
- [Level::SpawnEnemy 刷怪入口](enemy/level-spawn-enemy.md)
- [XEntityStatistics 怪物模板配置](enemy/enemy-template-config.md)
- [XEntityPresentation 表现配置](enemy/enemy-presentation-config.md)
- [AIEnemyAgent 怪物 AI](enemy/enemy-ai-agent.md)
- [Enemy 技能配置查表](enemy/enemy-skill-config.md)
- [Enemy 属性初始化](enemy/enemy-attr-init.md)
- [SpawnControl 召唤控制](enemy/spawn-control.md)
- [DestructibleUnit 可破坏物](enemy/destructible-unit.md)

## 后续拆分

- 场景与 SceneBattle
- CombatRole 派生层
- BuffConfig / Buff effect 内部
- XEcs / XFacility / XSirius
