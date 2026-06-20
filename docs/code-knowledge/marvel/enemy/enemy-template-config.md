---
type: Code Module
title: XEntityStatistics 怪物模板配置
description: XEntityStatistics 是 Enemy 模板主配置，驱动类型、阵营、属性、AI、技能和死亡时间。
repo: marvel
module: tableload/XEntityStatistics
resource: tableload/XEntityStatistics
tags: enemy, config, template, statistics, tableload
symbols: XEntityStatistics, UnitConf::InitFromTemplate, CombatEnemy::InitFromTemplate
logs: can't find monster template id
asserts: CHECK_COND_NORETURN
question_types: outage_log, feature_impl, config_impl
part_of: enemy/index.md
depends_on: combat-enemy.md
updated_at: 2026-06-20
---

# XEntityStatistics 怪物模板配置

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `XEntityStatistics` 表。 |
| 职责 | Enemy 模板主配置，决定类型、表现、阵营、属性、AI、技能和死亡行为。 |
| 下游 | `CombatEnemy::Init`、`UnitConf`、`CombatAttrCalc`、`SkillMgr`、`AIEnemyAgent`。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `ID` | 模板 ID。 |
| `PresentID` | 表现 ID。 |
| `Type` | species 和派生类选择。 |
| `Fightgroup` | 阵营。 |
| `DefaultLevel` | 默认等级。 |
| `DeadDisappearTime` | 死亡消失时间。 |
| `AIID` | AI 配置 ID 和表类型。 |
| `AppearSkill` / `OtherSkills` | 技能配置入口。 |
| `AttrCopy` / `ApplyScale` / `BaseAttr` | 属性初始化入口。 |

## 字段到运行时流程

```mermaid
flowchart TD
    A["XEntityStatistics.ID"] --> B["SceneUnitHandler::CreateUnit"]
    B --> C["CombatEnemy::Init"]
    C --> D["PresentID -> UnitConf::InitFromPresent"]
    C --> E["Type -> 派生类 / typelist"]
    C --> F["Fightgroup -> InitFightGroup"]
    C --> G["AIID -> AIEnemyAgent"]
    C --> H["AppearSkill / OtherSkills -> SkillMgr"]
    C --> I["BaseAttr / AttrCopy / ApplyScale -> CombatAttrCalc"]
    C --> J["DeadDisappearTime / Feature / NoTargetBuff"]
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 模板不存在 | `ID` 和调用方传入 ID。 |
| 类型不对 | `Type`。 |
| 技能/AI/属性异常 | `AIID`, `OtherSkills`, `AttrCopy`, `ApplyScale`。 |

