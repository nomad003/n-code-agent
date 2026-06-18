---
type: Code Module
title: 场景框架
description: Scene、SceneMgr、场景生命周期和 scene handler 的模块地图。
repo: marvel
module: gameserver/scene
resource: gameserver/scene
tags: scene, scenemgr, 场景, aoi, handler, pve, sceneunit
symbols: Scene, SceneMgr, SceneBattle, SceneHall, SceneUnitHandler
logs: Scene, SceneMgr
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# 场景框架

这张卡用于回答“场景如何创建/销毁”“SceneMgr 是什么”“单位如何进出场景”“场景内功能从哪里查”。

## 入口文件

- `gameserver/scene/scenemgr.cpp` / `scenemgr.h`：场景管理器，通常是创建、查找、销毁场景的入口。
- `gameserver/scene/scene.cpp` / `scene.h`：场景实例基础逻辑。
- `gameserver/scene/scenebattle.cpp`、`scenehall.cpp`、`sceneloading.cpp`：不同类型场景实现。
- `gameserver/scene/sceneunithandler.cpp` / `sceneunithandler.h`：场景内单位处理。
- `gameserver/scene/handler/`：场景功能 handler。
- `gameserver/scene/aoi/`、`grid/`、`team/`、`pve/`、`event/`：场景子系统。

## 核心职责

- 管理场景实例生命周期。
- 承载场景内单位、队伍、事件、AOI、网格和 PVE 逻辑。
- 连接角色进入/离开、关卡加载、战斗单位创建和网络同步。
- 为 `level` 提供场景宿主，为 `unit` 和 `combat` 提供运行环境。

## 常见链路

- 角色进入场景：通常从 `role` 或协议处理进入 `SceneMgr` / `Scene`。
- 关卡场景：`Scene` 挂载 `Level` / `LevelSpawner` 相关逻辑。
- 单位创建/销毁：`SceneUnitHandler` 与 `unit` 模块交互。
- 地图/场景配置：查 `SceneConfig` 和关卡模块的地图加载逻辑。

## 常见提问

- “SceneMgr 是做什么的？”
- “玩家/怪物怎么进入场景？”
- “场景销毁或切场景 crash 怎么排查？”
- “场景里的 handler 在哪里注册/调用？”

## 排查顺序

1. 栈帧命中 `scene/` 时先确认是 `SceneMgr`、`Scene` 还是某个 handler。
2. 查 `Scene` 生命周期和对象所有权，确认指针是否可能已经离场/销毁。
3. 如果关联关卡，继续看 [关卡框架](level-framework.md)。
4. 如果关联单位，继续看 [单位、属性与技能](unit-skill-attr.md)。

## 相关卡片

- [关卡框架](level-framework.md)
- [单位、属性与技能](unit-skill-attr.md)
- [网络与协议](network-protocol.md)
