---
type: Code Module
title: XBuffContainer Buff 容器接入
description: XBuffContainer 在 Unit 生命周期、技能/伤害事件和出生 Buff 中的接入点。
repo: marvel
module: gameserver/unit/XBuffContainer
resource: gameserver/buff
tags: unit, buff, xbuffcontainer, event
symbols: XBuffContainer, CombatEnemy::InitBufflist, CombatUnit::OnStartSkill, CombatUnit::OnEndSkill
logs: buff, Check cond
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: ../unit-framework.md
depends_on: combatunit.md
updated_at: 2026-06-20
---

# XBuffContainer Buff 容器接入

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `XBuffContainer` 在 Unit 层的接入。 |
| 职责 | 承接 Buff 生命周期、技能事件、伤害事件和属性变化。 |
| 边界 | Buff 内部公式和具体 Buff 配置后续可独立拆卡。 |

## 接入点

| 接入点 | Unit 行为 |
| --- | --- |
| `CombatUnit::InitComponents` | 绑定到组件集合。 |
| `CombatUnit::Update` | 每帧更新。 |
| `CombatEnemy::InitBufflist` | 加出生 Buff。 |
| 技能事件 | `OnStartSkill`, `OnEndSkill`。 |
| 伤害/属性事件 | 影响属性、状态和技能。 |

## 事件流程

```mermaid
flowchart TD
    A["CombatUnit 事件"] --> B{"事件类型"}
    B -->|出生| C["InitBufflist"]
    B -->|技能开始/结束| D["OnStartSkill / OnEndSkill"]
    B -->|受伤/属性变化| E["OnHurt / OnAttrChange"]
    C --> F["XBuffContainer"]
    D --> F
    E --> F
    F --> G["属性修正"]
    F --> H["状态修正"]
    F --> I["技能生命周期响应"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 出生 Buff 没有 | `InBornBuff`、`InitBufflist` 是否执行。 |
| 技能 Buff 不触发 | 技能事件是否传到 Buff 容器。 |
| 属性被异常修改 | Buff 事件和 `UnitEffect`。 |

