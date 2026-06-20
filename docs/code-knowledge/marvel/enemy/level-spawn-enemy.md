---
type: Code Module
title: Level::SpawnEnemy 刷怪入口
description: Level::SpawnEnemy 接收 Lua/关卡参数，修正坐标并创建 Enemy。
repo: marvel
module: gameserver/level/SpawnEnemy
resource: gameserver/level
tags: enemy, level, spawn, wave, group
symbols: Level::SpawnEnemy, CombatEnemy::LevelInit
logs: Spawn Enemy, Spawn Enemy failed
asserts: CHECK_COND
question_types: outage_log, feature_impl, config_impl
part_of: enemy/index.md
depends_on: scene-unit-handler.md
updated_at: 2026-06-20
---

# Level::SpawnEnemy 刷怪入口

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 模块 | 关卡刷怪入口。 |
| 职责 | 接收 Lua/Level 参数，做平台坐标和地面高度修正，然后创建并进场。 |
| 下游 | `SceneUnitHandler::CreateUnit`、`CombatEnemy::LevelInit`。 |

## 刷怪时序

```mermaid
sequenceDiagram
    participant Lua as Lua/Level
    participant Level as Level
    participant Handler as SceneUnitHandler
    participant Enemy as CombatEnemy
    participant Scene as SceneBattle

    Lua->>Level: SpawnEnemy(monsterID, pos, wave, group)
    Level->>Level: 平台坐标转换 / 地面修正
    Level->>Handler: CreateUnit(monsterID, pos)
    Handler-->>Level: enemy*
    Level->>Enemy: LevelInit(wave, group, ai, patrol)
    Level->>Scene: AddToGroup / timeline bind
    Level->>Enemy: EnterScene(scene)
```

## LevelInit 字段

| 参数 | 写入位置 |
| --- | --- |
| `waveID` / `waveIndex` | `m_WaveID` / `m_WaveIndex` |
| `groupID` | `m_GroupID` |
| `level` | `m_hostlevel` |
| `keepMapNum` | `m_KeepCount` |
| `aiID` | `AIAgent::SetOriginAIID` |
| `patrolID` | `AIEnemyAgent::SetPatrol` |

## 排查入口

| 现象 | 检查点 |
| --- | --- |
| 刷怪失败 | monster ID、坐标修正、CreateUnit 返回值。 |
| group 不对 | `LevelInit` 参数和 `Level::AddToGroup`。 |
| 巡逻不对 | `patrolID` 覆盖逻辑。 |

