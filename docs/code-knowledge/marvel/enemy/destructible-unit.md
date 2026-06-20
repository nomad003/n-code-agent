---
type: Code Module
title: DestructibleUnit 可破坏物
description: DestructibleUnit 使用公共模板并由 DestructibleObject 覆盖血量、表现阶段、技能破坏规则和掉落。
repo: marvel
module: gameserver/unit/DestructibleUnit
resource: gameserver/unit/destructible
tags: enemy, destructible, config, hp, collider, drop
symbols: DestructibleUnit, DestructibleObject, CombatAttrCalc::OverrideDestructibleAttr
logs: Check cond
asserts: CHECK_COND
question_types: outage_log, feature_impl, config_impl
part_of: ../enemy-framework.md
depends_on: enemy-template-config.md, enemy-presentation-config.md
updated_at: 2026-06-20
---

# DestructibleUnit 可破坏物

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `DestructibleUnit`。 |
| 职责 | 处理可破坏物模板覆盖、阶段表现、破坏规则和掉落。 |
| 配置 | `DestructibleObject.txt` 或 JSON override。 |

## 配置字段

| 字段 | 用途 |
| --- | --- |
| `TemplateID` | 可破坏物业务模板。 |
| `BaseHp` | 覆盖 HP。 |
| `PresentationStages` | 阶段表现和血量阶段。 |
| `RoleSkillTypes` | 可被哪些角色技能破坏。 |
| `MonsterMinSkillDestructLevel` | 怪物技能破坏等级门槛。 |
| `DropDoodadId` / `DropSourceID` | 掉落。 |

## 配置流程

```mermaid
flowchart TD
    A["创建 DestructibleUnit"] --> B["公共 XEntityStatistics 38000"]
    B --> C["读取 DestructibleObject.TemplateID"]
    C --> D["覆盖 BaseHp / ApplyScale / Fightgroup"]
    D --> E["PresentationStages 阶段表现"]
    E --> F["InitConf / InitBodySize"]
    F --> G["OverrideDestructibleAttr"]
    G --> H{"受到技能伤害"}
    H --> I["检查 SkillTypes / DestructLevel"]
    I -->|可破坏| J["扣血 / 切阶段 / 掉落"]
    I -->|不可破坏| K["忽略或只表现受击"]
```

## 排查入口

| 现象 | 检查字段 |
| --- | --- |
| 打不掉 | `RoleSkillTypes`, `MonsterMinSkillDestructLevel`, `DestructLevel`。 |
| HP 不对 | `BaseHp`, `ApplyScale`, 阶段配置。 |
| 掉落不对 | `DropDoodadId`, `DropSourceID`。 |

