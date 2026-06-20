---
type: Code Module
title: SceneUnitHandler 创建入口
description: SceneUnitHandler 负责根据模板 ID 创建 Enemy、召唤物和可破坏物。
repo: marvel
module: gameserver/unit/SceneUnitHandler
resource: gameserver/unit/sceneunithandler
tags: enemy, creation, sceneunithandler, spawn, destructible
symbols: SceneUnitHandler, SceneUnitHandler::CreateUnit, SceneUnitHandler::CreateUnitByCaller, CreateTemplateUnit
logs: can't find monster template id, caller create not find template id, Spawn Enemy failed
asserts: CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: enemy/index.md
depends_on: combat-enemy.md
updated_at: 2026-06-20
---

# SceneUnitHandler 创建入口

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | `SceneUnitHandler` 创建接口。 |
| 职责 | 查模板、选择派生类、调用初始化、登记创建列表。 |
| 边界 | 关卡参数补充见 [Level::SpawnEnemy 刷怪入口](level-spawn-enemy.md)。 |

## 创建流程

```mermaid
flowchart TD
    A{"创建来源"}
    A -->|关卡刷怪| B["CreateUnit"]
    A -->|技能召唤| C["CreateUnitByCaller"]
    A -->|可破坏物| D["CreateTemplateUnit"]
    B --> E["查 XEntityStatistics"]
    C --> E
    D --> E
    E -->|缺失| X["日志 + CHECK_COND_NORETURN"]
    E -->|存在| F{"Type"}
    F -->|MovablePlat| G["PlatEntity"]
    F -->|Destructible| H["DestructibleUnit"]
    F -->|其他| I["CombatEnemy"]
    G --> J["Init"]
    H --> J
    I --> J
    J --> K["写 m_CreatedUnitList"]
```

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 模板找不到 | 传入 monster/template ID 和 `XEntityStatistics.ID`。 |
| 派生类不对 | `XEntityStatistics.Type`。 |
| 召唤失败 | caller 和 caller scene 是否有效。 |

