---
type: Config Chain
title: 配置加载与 tableload
description: gameserver/tableload 下配置类、表查询入口和配置问题排查方法。
repo: marvel
module: gameserver/tableload
resource: gameserver/tableload
tags: tableload, config, conf, 配置, 表, skillconfig, buffconfig, sceneconfig, levelconfig
symbols: TableInit, SkillConfig, BuffConfig, SceneConfig, LevelConfig
logs: not find, config, conf
asserts: CHECK_COND
question_types: outage_log, config_impl, feature_impl
updated_at: 2026-06-18
---

# 配置加载与 tableload

这张卡用于回答“某个配置如何加载/生效”“配置缺失为什么报错”“日志里的 table/config not find 应该查哪里”。

## 入口文件

- `gameserver/tableload/tableinit.cpp` / `tableinit.h`：配置初始化聚合入口。
- `gameserver/tableload/skillconfig.cpp` / `skillconfig.h`：技能配置查询，怪物技能配置问题常见入口。
- `gameserver/tableload/buffconfig.cpp` / `buffconfig.h`：Buff 配置。
- `gameserver/tableload/sceneconfig.cpp` / `sceneconfig.h`：场景/地图配置。
- `gameserver/tableload/levelconfig.cpp` / `levelconfig.h`：关卡配置。
- `gameserver/tableload/aiconfig.cpp`、`spawnconfig.cpp`、`xentityinfolibrary.cpp`：AI、刷怪、实体信息相关配置。

## 核心职责

- 把配置表加载成运行时查询结构。
- 对外提供 `Get...Row`、`Get...Config` 这类查询函数。
- 为 `scene`、`level`、`unit`、`skill`、`buff`、`ai` 等业务模块提供配置数据。
- 在配置缺失时通常会打印 `not find`、`conf`、`config` 类错误日志，部分路径会接硬断言。

## 配置问题排查

1. 从日志提取配置 ID、名字、hash、类型名。
2. 用 `find_log_source` 定位打印点，确认是哪一个 config 类报错。
3. 读对应 `tableload/*config.cpp` 查询函数，确认 key 规则和 fallback 规则。
4. 再跳到业务使用点，确认调用方传入的 ID/hash 从哪里来。
5. 回答时明确哪些需要查真实表数据，不能只靠代码推断。

## 常见配置链路

- 怪物技能：`SkillConfig` + `SkillListForEnemy` + `XEntityStatistics.SkillStatisticsID`，见 [怪物配置与敌人技能配置链路](monster-config.md)。
- Buff：`BuffConfig` 提供 Buff 基础配置，运行时由 `XBuffContainer` 和具体 `XBuffEffect` 消费。
- 场景/地图：`SceneConfig` 被 `scene` / `level` 模块使用。
- 关卡：`LevelConfig`、`SpawnConfig` 和 `LevelEditorData` 共同影响刷怪、地图和事件。

## 常见提问

- “这个配置字段在哪里生效？”
- “某个 ID not find 是哪张表缺了？”
- “为什么配置表有值但运行时查不到？”
- “技能/Buff/场景/关卡配置加载链路是什么？”

## 相关卡片

- [怪物配置与敌人技能配置链路](monster-config.md)
- [Buff 框架](buff-framework.md)
- [关卡框架](level-framework.md)
- [场景框架](scene-framework.md)
