---
type: Code Module
title: 关卡框架
description: Level、LevelSpawner、关卡事件、Lua/tolua 桥和刷怪流程。
repo: marvel
module: gameserver/level
resource: gameserver/level
tags: level, spawner, 关卡, 刷怪, lua, tolua, trigger, wave, map
symbols: Level, LevelSpawner, LevelMgr, CLuaLevelState, LevelEventHandler
logs: LevelLogErr, Load script file failed
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# 关卡框架

这张卡用于回答“关卡如何初始化”“刷怪从哪里走”“Lua 关卡脚本如何调用 C++”“地图加载/触发器问题怎么排查”。

## 入口文件

- `gameserver/level/level.cpp` / `level.h`：关卡对象，包含初始化、定时、刷怪、地图、剧情、任务等入口。
- `gameserver/level/levelspawner.cpp` / `levelspawner.h`：刷怪、触发器、地图加载和关卡状态处理。
- `gameserver/level/LevelMgr.cpp` / `LevelMgr.h`：关卡管理。
- `gameserver/level/LevelEventHandler.cpp` / `.h`：关卡事件绑定和分发。
- `gameserver/level/LuaLevelState.cpp` / `.h`：Lua 关卡状态。
- `gameserver/level/function/Level/tolua_level.cpp`：Lua 暴露给脚本的 C++ 方法，例如 `SpawnEnemy`、`LoadMap`、`Bind...Event`。

## 核心职责

- 初始化关卡数据和脚本状态。
- 管理关卡事件、触发器、刷怪 wave、地图加载、剧情和任务。
- 通过 tolua 让 Lua 脚本调用 C++ 的关卡接口。
- 与 `scene`、`unit/enemy`、`ai`、`tableload` 交互完成运行时玩法。

## 关键流程

1. `Level::Init(...)` 读取 `LevelEditorData` 并初始化关卡运行时数据。
2. `LevelSpawner::Init()` 和相关 Load/Reload 方法处理刷怪、地图、触发器。
3. Lua/tolua 入口调用 `Level` 方法，例如 `SpawnEnemy` 创建怪物。
4. 怪物创建后进入 `CombatEnemy` 初始化链路，见 [怪物配置与敌人技能配置链路](monster-config.md)。

## 常见日志/问题

- `Load script file failed`：先看 `Level::Init` 附近脚本加载逻辑和脚本名来源。
- 刷怪失败：查 `LevelSpawner`、`SpawnConfig`、`LevelEditorData`、怪物模板配置。
- 地图加载异常：查 `Level::LoadMap`、`LevelSpawner::LoadMap`、`SceneConfig`。
- 脚本调用 crash：先定位 tolua 包装函数，再看对应 C++ `Level` 方法。

## 排查顺序

1. 确认问题来自脚本、刷怪、事件、地图还是关卡生命周期。
2. 用日志/栈帧定位到 `level.cpp`、`levelspawner.cpp` 或 tolua 文件。
3. 继续追到配置类：`LevelConfig`、`SpawnConfig`、`SceneConfig`。
4. 如果涉及怪物/技能，跳到 `unit` 和 `tableload/skillconfig`。

## 相关卡片

- [场景框架](scene-framework.md)
- [怪物配置与敌人技能配置链路](monster-config.md)
- [配置加载与 tableload](tableload-config.md)
