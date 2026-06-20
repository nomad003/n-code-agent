---
type: Code Module
title: UnitCombatAttribute 属性容器
description: AttrData 和 UnitCombatAttribute 的属性读写、当前值约束和属性变化事件。
repo: marvel
module: gameserver/unit/UnitCombatAttribute
resource: gameserver/unit/attr/combatattribute.h
tags: unit, attr, combatattribute, field
symbols: UnitCombatAttribute, AttrData, UnitCombatAttribute::GetAttr, UnitCombatAttribute::SetAttr, UnitCombatAttribute::AddCurrentAttr
logs: Check cond
asserts: CHECK_COND
question_types: crash_stack, feature_impl, config_impl
part_of: unit/index.md
depends_on: combatunit.md
updated_at: 2026-06-20
---

# UnitCombatAttribute 属性容器

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `UnitCombatAttribute` / `AttrData`。 |
| 职责 | 保存所有战斗属性，提供读写和当前值约束。 |
| 配置 | `AttrDefine.txt` 决定属性类型和同步标记。 |

## 字段

| 字段 | 用途 |
| --- | --- |
| `AttrData::mAttrData` | 所有属性值。 |
| `AttrData::mAttrDataMax` | 多来源最大值类属性。 |
| `AttrData::mUId` | Unit UID。 |
| `AttrData::mUnitId` | 模板或伙伴 ID。 |

## 属性读写流程

```mermaid
flowchart TD
    A["业务模块请求属性变更"] --> B{"CanSetAttr"}
    B -->|否| C["返回失败或忽略"]
    B -->|是| D{"写入方式"}
    D -->|SetAttr| E["直接写属性"]
    D -->|AddAttr| F["旧值累加"]
    D -->|SetCurrentAttr| G["按最大值约束当前值"]
    D -->|AddCurrentAttr| G
    E --> H["OnAttrChanged"]
    F --> H
    G --> H
    H --> I["Buff / State / Skill / Sync 响应"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 当前 HP 异常 | 当前值是否被最大值约束；初始化顺序是否正确。 |
| 属性不同步 | `AttrDefine` 同步标记和 `RoleAttrConfig`。 |
| 属性递归变化 | `m_oWatcherStack` 和 `OnAttrChanged` 调用链。 |

