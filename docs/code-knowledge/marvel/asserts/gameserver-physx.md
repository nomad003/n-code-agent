---
type: Code Playbook
title: Assert 排障 - gameserver-physx
description: gameserver-physx 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-physx
resource: gameserver/physx/PhysicsScene.cpp, gameserver/physx/PhysicsWorld.cpp, gameserver/physx/UnitController.cpp
tags: assert, check, outage_log, crash, gameserver, physx
symbols: PhysicsScene::Init_, PhysicsScene::LoadStaticColliders, PhysicsScene::GetLocatedPlatform, PhysicsScene::GetLevelWallFilterData, PhysicsScene::SetLevelWallFilterData, PhysicsScene::EnableLevelWall, PhysicsScene::AddLevelWall, reportError, UnitControllerHitCallback::onControllerHit, UnitController::CreatePxController_, UnitController::Move
logs: [PHYSX]%s (%d) : %s : %s
asserts: CHECK_COND_RETURN, CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-physx

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-physx` |
| 条目数 | 21 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/physx/PhysicsScene.cpp:43` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-43-check_cond_return-e3a0d014` |
| 函数 | `PhysicsScene::Init_` |
| 类型 | `precondition_failed` |
| 条件 | `physicsWorld && physicsWorld->GetPxPhysics()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `physicsWorld && physicsWorld->GetPxPhysics()`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::Init_`，附近代码 `44: physx::PxPhysics* physics = physicsWorld->GetPxPhysics();`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`physicsWorld && physicsWorld->GetPxPhysics()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `physicsWorld && physicsWorld->GetPxPhysics()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
38: }
40: bool PhysicsScene::Init_()
41: {
42: PhysicsWorld* physicsWorld = PhysicsWorld::Instance();
43: CHECK_COND_RETURN(physicsWorld && physicsWorld->GetPxPhysics(), false);
44: physx::PxPhysics* physics = physicsWorld->GetPxPhysics();
46: physx::PxSceneDesc desc(physics->getTolerancesScale());
47: desc.gravity = { 0.f, -9.81f, 0.f };
48: desc.cpuDispatcher = physx::PxDefaultCpuDispatcherCreate(0);
```

### `gameserver/physx/PhysicsScene.cpp:51` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-51-check_cond_return-72acdcf0` |
| 函数 | `PhysicsScene::Init_` |
| 类型 | `precondition_failed` |
| 条件 | `m_pxScene` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `m_pxScene`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::Init_`，附近代码 `51: CHECK_COND_RETURN(m_pxScene, false);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`m_pxScene`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_pxScene` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
46: physx::PxSceneDesc desc(physics->getTolerancesScale());
47: desc.gravity = { 0.f, -9.81f, 0.f };
48: desc.cpuDispatcher = physx::PxDefaultCpuDispatcherCreate(0);
49: desc.filterShader = physx::PxDefaultSimulationFilterShader;
50: m_pxScene = physics->createScene(desc);
51: CHECK_COND_RETURN(m_pxScene, false);
52: m_pxScene->userData = (void*)this;
54: m_controllerManager = PxCreateControllerManager(*m_pxScene);
55: CHECK_COND_RETURN(m_controllerManager, false);
56: m_controllerManager->setOverlapRecoveryModule(true);
```

### `gameserver/physx/PhysicsScene.cpp:55` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-55-check_cond_return-263b6340` |
| 函数 | `PhysicsScene::Init_` |
| 类型 | `precondition_failed` |
| 条件 | `m_controllerManager` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `m_controllerManager`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::Init_`，附近代码 `56: m_controllerManager->setOverlapRecoveryModule(true);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`m_controllerManager`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_controllerManager` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
50: m_pxScene = physics->createScene(desc);
51: CHECK_COND_RETURN(m_pxScene, false);
52: m_pxScene->userData = (void*)this;
54: m_controllerManager = PxCreateControllerManager(*m_pxScene);
55: CHECK_COND_RETURN(m_controllerManager, false);
56: m_controllerManager->setOverlapRecoveryModule(true);
58: return true;
59: }
```

### `gameserver/physx/PhysicsScene.cpp:116` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-116-check_cond_return-f66396e8` |
| 函数 | `PhysicsScene::LoadStaticColliders` |
| 类型 | `precondition_failed` |
| 条件 | `sharedCollidersData` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `sharedCollidersData`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::LoadStaticColliders`，附近代码 `116: CHECK_COND_RETURN(sharedCollidersData, false);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`sharedCollidersData`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `sharedCollidersData` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
111: bool PhysicsScene::LoadStaticColliders(const std::string& filepath)
112: {
113: std::string blockPath = SceneConfig::GetBlockDir() + filepath + ".json";
114: blockPath = FrameWork::GetConfig().GetFilePath(blockPath.c_str(), SERVER_DIR_ROOT);
115: const SharedCollidersData* sharedCollidersData = PhysicsWorld::Instance()->GetCollidersFromFile(blockPath);
116: CHECK_COND_RETURN(sharedCollidersData, false);
117: m_filepath = blockPath;
119: m_collidersData = AddColliderToPxScene(sharedCollidersData, m_pxScene);
120: if (!m_collidersData)
121: return false;
```

### `gameserver/physx/PhysicsScene.cpp:433` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-433-check_cond_return-f59784ba` |
| 函数 | `PhysicsScene::GetLocatedPlatform` |
| 类型 | `precondition_failed` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::GetLocatedPlatform`，附近代码 `434: const xecs::Vector3& pos = unit->GetPosition();`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
428: }
429: }
431: PlatEntity* PhysicsScene::GetLocatedPlatform(CombatUnit* unit, float* distFromGround) const
432: {
433: CHECK_COND_RETURN(unit, NULL);
434: const xecs::Vector3& pos = unit->GetPosition();
435: physx::PxRaycastBuffer hit;
436: physx::PxQueryFilterData queryFilterData;
437: queryFilterData.data = unit->Get<UnitController>()->GetFilterData();
438: queryFilterData.flags = physx::PxQueryFlag::eSTATIC | physx::PxQueryFlag::eDYNAMIC | physx::PxQueryFlag::ePREFILTER;
```

### `gameserver/physx/PhysicsScene.cpp:1005` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1005-check_cond_return-b9c9b84f` |
| 函数 | `PhysicsScene::GetLevelWallFilterData` |
| 类型 | `precondition_failed` |
| 条件 | `iter != m_levelWalls.end()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter != m_levelWalls.end()`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::GetLevelWallFilterData`，附近代码 `1006: CHECK_COND_RETURN(iter->second, physx::PxFilterData());`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`iter != m_levelWalls.end()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter != m_levelWalls.end()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
1000: }
1002: physx::PxFilterData PhysicsScene::GetLevelWallFilterData(const std::string& wallName)
1003: {
1004: auto iter = m_levelWalls.find(wallName);
1005: CHECK_COND_RETURN(iter != m_levelWalls.end(), physx::PxFilterData());
1006: CHECK_COND_RETURN(iter->second, physx::PxFilterData());
1008: physx::PxShape* shape = NULL;
1009: auto shapeNum = iter->second->getShapes(&shape, 1);
1010: CHECK_COND_RETURN(shapeNum == 1 && shape, physx::PxFilterData());
```

### `gameserver/physx/PhysicsScene.cpp:1006` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1006-check_cond_return-9db901e5` |
| 函数 | `PhysicsScene::GetLevelWallFilterData` |
| 类型 | `precondition_failed` |
| 条件 | `iter->second` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter->second`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::GetLevelWallFilterData`，附近代码 `1008: physx::PxShape* shape = NULL;`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`iter->second`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter->second` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
1002: physx::PxFilterData PhysicsScene::GetLevelWallFilterData(const std::string& wallName)
1003: {
1004: auto iter = m_levelWalls.find(wallName);
1005: CHECK_COND_RETURN(iter != m_levelWalls.end(), physx::PxFilterData());
1006: CHECK_COND_RETURN(iter->second, physx::PxFilterData());
1008: physx::PxShape* shape = NULL;
1009: auto shapeNum = iter->second->getShapes(&shape, 1);
1010: CHECK_COND_RETURN(shapeNum == 1 && shape, physx::PxFilterData());
```

### `gameserver/physx/PhysicsScene.cpp:1010` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1010-check_cond_return-c9c8c686` |
| 函数 | `PhysicsScene::GetLevelWallFilterData` |
| 类型 | `precondition_failed` |
| 条件 | `shapeNum == 1 && shape` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `shapeNum == 1 && shape`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::GetLevelWallFilterData`，附近代码 `1012: return shape->getQueryFilterData();`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`shapeNum == 1 && shape`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `shapeNum == 1 && shape` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
1005: CHECK_COND_RETURN(iter != m_levelWalls.end(), physx::PxFilterData());
1006: CHECK_COND_RETURN(iter->second, physx::PxFilterData());
1008: physx::PxShape* shape = NULL;
1009: auto shapeNum = iter->second->getShapes(&shape, 1);
1010: CHECK_COND_RETURN(shapeNum == 1 && shape, physx::PxFilterData());
1012: return shape->getQueryFilterData();
1013: }
1015: void PhysicsScene::SetLevelWallFilterData(const std::string& wallName, const physx::PxFilterData& filterData)
```

### `gameserver/physx/PhysicsScene.cpp:1018` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1018-check_cond-bcc86cfa` |
| 函数 | `PhysicsScene::SetLevelWallFilterData` |
| 类型 | `invariant_failed` |
| 条件 | `iter != m_levelWalls.end()` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter != m_levelWalls.end()`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::SetLevelWallFilterData`，附近代码 `1019: CHECK_COND(iter->second);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`iter != m_levelWalls.end()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter != m_levelWalls.end()` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1013: }
1015: void PhysicsScene::SetLevelWallFilterData(const std::string& wallName, const physx::PxFilterData& filterData)
1016: {
1017: auto iter = m_levelWalls.find(wallName);
1018: CHECK_COND(iter != m_levelWalls.end());
1019: CHECK_COND(iter->second);
1021: physx::PxShape* shape = NULL;
1022: auto shapeNum = iter->second->getShapes(&shape, 1);
1023: CHECK_COND(shapeNum == 1 && shape);
```

### `gameserver/physx/PhysicsScene.cpp:1019` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1019-check_cond-eb3620ce` |
| 函数 | `PhysicsScene::SetLevelWallFilterData` |
| 类型 | `invariant_failed` |
| 条件 | `iter->second` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter->second`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::SetLevelWallFilterData`，附近代码 `1021: physx::PxShape* shape = NULL;`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`iter->second`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter->second` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1015: void PhysicsScene::SetLevelWallFilterData(const std::string& wallName, const physx::PxFilterData& filterData)
1016: {
1017: auto iter = m_levelWalls.find(wallName);
1018: CHECK_COND(iter != m_levelWalls.end());
1019: CHECK_COND(iter->second);
1021: physx::PxShape* shape = NULL;
1022: auto shapeNum = iter->second->getShapes(&shape, 1);
1023: CHECK_COND(shapeNum == 1 && shape);
```

### `gameserver/physx/PhysicsScene.cpp:1023` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1023-check_cond-6c3580bf` |
| 函数 | `PhysicsScene::SetLevelWallFilterData` |
| 类型 | `invariant_failed` |
| 条件 | `shapeNum == 1 && shape` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `shapeNum == 1 && shape`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::SetLevelWallFilterData`，附近代码 `1025: shape->setQueryFilterData(filterData);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`shapeNum == 1 && shape`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `shapeNum == 1 && shape` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1018: CHECK_COND(iter != m_levelWalls.end());
1019: CHECK_COND(iter->second);
1021: physx::PxShape* shape = NULL;
1022: auto shapeNum = iter->second->getShapes(&shape, 1);
1023: CHECK_COND(shapeNum == 1 && shape);
1025: shape->setQueryFilterData(filterData);
1026: }
1028: void PhysicsScene::EnableLevelWall(const std::string& wallName, bool enable)
```

### `gameserver/physx/PhysicsScene.cpp:1031` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1031-check_cond-bcc86cfa` |
| 函数 | `PhysicsScene::EnableLevelWall` |
| 类型 | `invariant_failed` |
| 条件 | `iter != m_levelWalls.end()` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter != m_levelWalls.end()`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::EnableLevelWall`，附近代码 `1032: CHECK_COND(iter->second);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`iter != m_levelWalls.end()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter != m_levelWalls.end()` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1026: }
1028: void PhysicsScene::EnableLevelWall(const std::string& wallName, bool enable)
1029: {
1030: auto iter = m_levelWalls.find(wallName);
1031: CHECK_COND(iter != m_levelWalls.end());
1032: CHECK_COND(iter->second);
1034: physx::PxShape* shape = NULL;
1035: auto shapeNum = iter->second->getShapes(&shape, 1);
1036: CHECK_COND(shapeNum == 1 && shape);
```

### `gameserver/physx/PhysicsScene.cpp:1032` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1032-check_cond-eb3620ce` |
| 函数 | `PhysicsScene::EnableLevelWall` |
| 类型 | `invariant_failed` |
| 条件 | `iter->second` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `iter->second`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::EnableLevelWall`，附近代码 `1034: physx::PxShape* shape = NULL;`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`iter->second`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `iter->second` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1028: void PhysicsScene::EnableLevelWall(const std::string& wallName, bool enable)
1029: {
1030: auto iter = m_levelWalls.find(wallName);
1031: CHECK_COND(iter != m_levelWalls.end());
1032: CHECK_COND(iter->second);
1034: physx::PxShape* shape = NULL;
1035: auto shapeNum = iter->second->getShapes(&shape, 1);
1036: CHECK_COND(shapeNum == 1 && shape);
```

### `gameserver/physx/PhysicsScene.cpp:1036` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1036-check_cond-6c3580bf` |
| 函数 | `PhysicsScene::EnableLevelWall` |
| 类型 | `invariant_failed` |
| 条件 | `shapeNum == 1 && shape` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `shapeNum == 1 && shape`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::EnableLevelWall`，附近代码 `1038: physx::PxFilterData filterData = shape->getQueryFilterData();`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`shapeNum == 1 && shape`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `shapeNum == 1 && shape` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1031: CHECK_COND(iter != m_levelWalls.end());
1032: CHECK_COND(iter->second);
1034: physx::PxShape* shape = NULL;
1035: auto shapeNum = iter->second->getShapes(&shape, 1);
1036: CHECK_COND(shapeNum == 1 && shape);
1038: physx::PxFilterData filterData = shape->getQueryFilterData();
1040: if (enable)
1041: AddPhysicsBlockFlag(filterData, PhysicsQueryGroup::eUNITS);
```

### `gameserver/physx/PhysicsScene.cpp:1061` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsscene-cpp-1061-check_cond_return-f67d65b1` |
| 函数 | `PhysicsScene::AddLevelWall` |
| 类型 | `precondition_failed` |
| 条件 | `shape && actor` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/PhysicsScene.cpp`，关键条件 `shape && actor`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsScene.cpp`，函数 `PhysicsScene::AddLevelWall`，附近代码 `1063: actor->attachShape(*shape);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`shape && actor`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsScene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `shape && actor` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
1056: return "";
1057: }
1059: physx::PxShape* shape = physics->createShape(geometry, *PhysicsWorld::Instance()->GetMaterial(), true);
1060: physx::PxRigidStatic* actor = physics->createRigidStatic(pose);
1061: CHECK_COND_RETURN(shape && actor, "");
1063: actor->attachShape(*shape);
1064: shape->release();
1065: m_pxScene->addActor(*actor);
1066: m_levelWalls.emplace_hint(m_levelWalls.end(), wallName, actor);
```

### `gameserver/physx/PhysicsWorld.cpp:96` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-physicsworld-cpp-96-check_cond-b564bc0b` |
| 函数 | `reportError` |
| 类型 | `invariant_failed` |
| 条件 | `code != physx::PxErrorCode::eABORT` |
| 日志/提示 | `[PHYSX]%s (%d) : %s : %s` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/PhysicsWorld.cpp`，关键条件 `[PHYSX]%s (%d) : %s : %s`。 |
| 上下文 | 文件 `gameserver/physx/PhysicsWorld.cpp`，函数 `reportError`，附近日志 `[PHYSX]%s (%d) : %s : %s`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`[PHYSX]%s (%d) : %s : %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/PhysicsWorld.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `code != physx::PxErrorCode::eABORT` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
91: if (isDebug)
92: LogDebug("[PHYSX]%s (%d) : %s : %s", file, line, errorCode, message);
93: else
94: LogError("[PHYSX]%s (%d) : %s : %s", file, line, errorCode, message);
96: CHECK_COND(code != physx::PxErrorCode::eABORT);
97: }
98: };
101: bool PhysicsWorld::Init(UINT32 pvdPort, const std::string& omniPvdFile)
```

### `gameserver/physx/UnitController.cpp:39` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-unitcontroller-cpp-39-check_cond-dad33a4c` |
| 函数 | `UnitControllerHitCallback::onControllerHit` |
| 类型 | `invariant_failed` |
| 条件 | `thisController && otherController` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/UnitController.cpp`，关键条件 `thisController && otherController`。 |
| 上下文 | 文件 `gameserver/physx/UnitController.cpp`，函数 `UnitControllerHitCallback::onControllerHit`，附近代码 `40: CombatUnit* thisUnit = thisController->GetUnit();`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`thisController && otherController`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/UnitController.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `thisController && otherController` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
35: void UnitControllerHitCallback::onControllerHit(const physx::PxControllersHit& hit)
36: {
37: UnitController* thisController = (UnitController*)hit.controller->getUserData();
38: UnitController* otherController = (UnitController*)hit.other->getUserData();
39: CHECK_COND(thisController && otherController);
40: CombatUnit* thisUnit = thisController->GetUnit();
41: CombatUnit* otherUnit = otherController->GetUnit();
42: CHECK_COND(thisUnit && otherUnit);
44: physx::PxVec3 pushVec{ 0.f, 0.f, 0.f };
```

### `gameserver/physx/UnitController.cpp:42` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-unitcontroller-cpp-42-check_cond-fc622c19` |
| 函数 | `UnitControllerHitCallback::onControllerHit` |
| 类型 | `invariant_failed` |
| 条件 | `thisUnit && otherUnit` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/physx/UnitController.cpp`，关键条件 `thisUnit && otherUnit`。 |
| 上下文 | 文件 `gameserver/physx/UnitController.cpp`，函数 `UnitControllerHitCallback::onControllerHit`，附近代码 `42: CHECK_COND(thisUnit && otherUnit);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`thisUnit && otherUnit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/UnitController.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `thisUnit && otherUnit` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
37: UnitController* thisController = (UnitController*)hit.controller->getUserData();
38: UnitController* otherController = (UnitController*)hit.other->getUserData();
39: CHECK_COND(thisController && otherController);
40: CombatUnit* thisUnit = thisController->GetUnit();
41: CombatUnit* otherUnit = otherController->GetUnit();
42: CHECK_COND(thisUnit && otherUnit);
44: physx::PxVec3 pushVec{ 0.f, 0.f, 0.f };
45: if (UnitController::CanUnitPushOtherOnHit(thisUnit, otherUnit, hit, pushVec))
46: {
47: const xecs::Vector3& otherPos = otherUnit->GetPosition();
```

### `gameserver/physx/UnitController.cpp:253` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-unitcontroller-cpp-253-check_cond_return-7b4fdd6a` |
| 函数 | `UnitController::CreatePxController_` |
| 类型 | `precondition_failed` |
| 条件 | `unit && scene` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/UnitController.cpp`，关键条件 `unit && scene`。 |
| 上下文 | 文件 `gameserver/physx/UnitController.cpp`，函数 `UnitController::CreatePxController_`，附近代码 `255: physx::PxCapsuleControllerDesc desc;`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit && scene`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/UnitController.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit && scene` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
248: return IsPhysicsFiltersBlock(m_filterData, filterData);
249: }
251: physx::PxController* UnitController::CreatePxController_(CombatUnit* unit, PhysicsScene* scene)
252: {
253: CHECK_COND_RETURN(unit && scene, NULL);
255: physx::PxCapsuleControllerDesc desc;
256: desc.contactOffset = PhysicsScene::CONTACT_OFFSET;
257: desc.upDirection = { 0.f, 1.f, 0.f };
258: desc.stepOffset = GetGlobalConfig().Common.UnitMaxClimb;
```

### `gameserver/physx/UnitController.cpp:443` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-unitcontroller-cpp-443-check_cond_return-43338730` |
| 函数 | `UnitController::Move` |
| 类型 | `precondition_failed` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/UnitController.cpp`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/physx/UnitController.cpp`，函数 `UnitController::Move`，附近代码 `444: SceneBattle* scene = unit->GetCurrBattle();`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/UnitController.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
438: }
440: xecs::Vector3 UnitController::Move(const xecs::Vector3& from, const xecs::Vector3& dest, bool updatePosition)
441: {
442: CombatUnit* unit = GetUnit();
443: CHECK_COND_RETURN(unit, dest);
444: SceneBattle* scene = unit->GetCurrBattle();
445: CHECK_COND_RETURN(scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX, from); // Not allow to move.
446: if (unit->GetConf().GetTemplateConf() && unit->GetConf().GetTemplateConf()->IgnorePlatforms) // use `IgnorePlatforms` to ignore everything, TODO: change variable name.
447: return dest;
448: PhysicsScene* physicsScene = static_cast<PhysicsScene*>(scene->GetSceneQuery());
```

### `gameserver/physx/UnitController.cpp:445` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-physx-unitcontroller-cpp-445-check_cond_return-1f8b2e24` |
| 函数 | `UnitController::Move` |
| 类型 | `precondition_failed` |
| 条件 | `scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/physx/UnitController.cpp`，关键条件 `scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX`。 |
| 上下文 | 文件 `gameserver/physx/UnitController.cpp`，函数 `UnitController::Move`，附近代码 `445: CHECK_COND_RETURN(scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX, from); // Not...`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/physx/UnitController.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
440: xecs::Vector3 UnitController::Move(const xecs::Vector3& from, const xecs::Vector3& dest, bool updatePosition)
441: {
442: CombatUnit* unit = GetUnit();
443: CHECK_COND_RETURN(unit, dest);
444: SceneBattle* scene = unit->GetCurrBattle();
445: CHECK_COND_RETURN(scene && scene->GetSceneQuery() && scene->GetSceneQuery()->GetType() == SceneQueryInterface::PhysX, from); // Not allow to move.
446: if (unit->GetConf().GetTemplateConf() && unit->GetConf().GetTemplateConf()->IgnorePlatforms) // use `IgnorePlatforms` to ignore everything, TODO: change variable name.
447: return dest;
448: PhysicsScene* physicsScene = static_cast<PhysicsScene*>(scene->GetSceneQuery());
450: xecs::Vector3 lastUnitPos = from;
```
