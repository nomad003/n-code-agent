---
type: Code Module
title: UnitEffect Affix Effect
description: UnitEffect 和 AttrEffect 处理技能、Buff、伤害、属性和状态事件中的 affix effect。
repo: marvel
module: gameserver/unit/UnitEffect
resource: gameserver/unit/affixeffect/uniteffect.h
tags: unit, effect, affix, attr, buff
symbols: UnitEffect, AttrEffect, AffixEffectConfig
logs: Check cond
asserts: CHECK_COND
question_types: feature_impl, config_impl, outage_log
part_of: ../unit-framework.md
depends_on: xbuff-container.md, unit-combat-attribute.md
updated_at: 2026-06-20
---

# UnitEffect Affix Effect

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `UnitEffect` / `AttrEffect`。 |
| 职责 | 按 `AffixEffect` 配置在事件中加 Buff、改属性或修正伤害。 |
| 配置 | `AffixEffect.txt`。 |

## 主要类型

| 类型 | 含义 |
| --- | --- |
| `SKILL_ADDBUFF_TYPE` | 技能开始/结束加 Buff。 |
| `CALL_PET_ADDBUFF` | 召唤物加 Buff。 |
| `ATTACK_ADDATTR_TYPE` | 攻击时加属性。 |
| `SKILL_ADD_DAMAGE_TYPE` | 技能加伤害。 |
| `BOSS_ENTER_STATE_TYPE` | Boss 进入状态加 Buff。 |

## Effect 流程

```mermaid
flowchart TD
    A["技能 / Buff / 伤害事件"] --> B["UnitEffect 查询 effect type"]
    B --> C{"Effect 类型"}
    C -->|加 Buff| D["XBuffContainer"]
    C -->|加属性| E["UnitCombatAttribute 临时属性"]
    C -->|加伤害| F["伤害计算修正"]
    C -->|Boss 状态| D
    D --> G["事件结束清理或保留"]
    E --> G
    F --> G
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| Effect 没触发 | 事件入口和 `AffixEffectConfig`。 |
| Buff 时间异常 | Buff changetime effect。 |
| 伤害倍率异常 | `SKILL_ADD_DAMAGE_TYPE` 和 DOT scale。 |

