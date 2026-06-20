---
type: Code Playbook
title: Assert 排障 - gameserver-scene
description: gameserver-scene 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-scene
resource: gameserver/scene/aoi/sceneaoi.cpp, gameserver/scene/event/sceneeventlistener.cpp, gameserver/scene/grid/grid.cpp, gameserver/scene/grid/grid.h, gameserver/scene/grid/gridinfo.cpp, gameserver/scene/handler/scenecollisions.cpp, gameserver/scene/scene.cpp, gameserver/scene/scenebattle.cpp, gameserver/scene/sceneunithandler.cpp, gameserver/scene/waypoint/waypointmgr.cpp
tags: assert, check, outage_log, crash, gameserver, scene
symbols: UnitList::AddUnit, ASSERT_NO_DUPLICATE_DELEGATE, FindRawGridsWithCache, Grid, StaticGrid::_LoadFileSlop, StaticGrid::_GetMaxIndex, SceneCollisions::SolveCollisionForUnitNonPhysX_, SceneCollisions::SolveOverlapsWithBosses, Scene::UnInit, Scene::AddRole, SceneBattle::LoadedNextScene, SceneUnitHandler::CreateRoleNew, SceneUnitHandler::CreateDestructible, WayPointMgr::_GetWayPointGraph
logs: unit:%llu has been added, invalid y [%f] of xz [%f %f] in grid file [%s], can't find monster template id [%u], caller:[%llu] create not find template id:[%u], can't find destructible template id [%u] | create template destructible unit failed, create template destructible unit failed | can't find destructible template id [%u], load wayPointGraph fail, filepath: %s
asserts: CHECK_COND, ASSERT_NO_DUPLICATE_DELEGATE, ASSERT, CHECK_COND_RETURN, CHECK_COND_NORETURN, CHECK_COND_WITH_LOG_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-scene

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-scene` |
| 条目数 | 24 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/scene/aoi/sceneaoi.cpp:17` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-aoi-sceneaoi-cpp-17-check_cond-ffc67c8a` |
| 函数 | `UnitList::AddUnit` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `unit:%llu has been added` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/scene/aoi/sceneaoi.cpp`，关键条件 `unit:%llu has been added`。 |
| 上下文 | 文件 `gameserver/scene/aoi/sceneaoi.cpp`，函数 `UnitList::AddUnit`，附近日志 `unit:%llu has been added`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`unit:%llu has been added`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/aoi/sceneaoi.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
12: {
13: auto i = id2unit.find(unit->GetID());
14: if (i != id2unit.end())
15: {
16: LogError("unit:%llu has been added", unit->GetID());
17: CHECK_COND(false);
18: return;
19: }
20: unitlist.push_back(unit);
21: id2unit.insert(std::make_pair(unit->GetID(), --unitlist.end()));
22: }
```

### `gameserver/scene/event/sceneeventlistener.cpp:5` `ASSERT_NO_DUPLICATE_DELEGATE`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-event-sceneeventlistener-cpp-5-assert_no_duplicate_delegate-f715275b` |
| 函数 | `-` |
| 类型 | `invariant_failed` |
| 条件 | `d` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/scene/event/sceneeventlistener.cpp`，关键条件 `d`。 |
| 上下文 | 文件 `gameserver/scene/event/sceneeventlistener.cpp`，附近代码 `7: if (handler == d)\`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`d`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/event/sceneeventlistener.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `d` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
1: #include "sceneeventlistener.h"
2: #include "commondef.h"
3: #include "scene/event/sceneeventdefine.h"
5: #define ASSERT_NO_DUPLICATE_DELEGATE(d) for (auto& handler : handlers)\
6: {\
7: if (handler == d)\
8: {\
9: ASSERT(false);\
10: }\
```

### `gameserver/scene/event/sceneeventlistener.cpp:9` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-event-sceneeventlistener-cpp-9-assert-35481c09` |
| 函数 | `-` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/scene/event/sceneeventlistener.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/scene/event/sceneeventlistener.cpp`，附近代码 `10: }\`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/event/sceneeventlistener.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
5: #define ASSERT_NO_DUPLICATE_DELEGATE(d) for (auto& handler : handlers)\
6: {\
7: if (handler == d)\
8: {\
9: ASSERT(false);\
10: }\
11: }
13: SceneEventHandler::SceneEventHandler(Scene* pScene)
14: {
```

### `gameserver/scene/event/sceneeventlistener.cpp:26` `ASSERT_NO_DUPLICATE_DELEGATE`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-event-sceneeventlistener-cpp-26-assert_no_duplicate_delegate-58f4003d` |
| 函数 | `ASSERT_NO_DUPLICATE_DELEGATE` |
| 类型 | `invariant_failed` |
| 条件 | `d` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/scene/event/sceneeventlistener.cpp`，关键条件 `d`。 |
| 上下文 | 文件 `gameserver/scene/event/sceneeventlistener.cpp`，函数 `ASSERT_NO_DUPLICATE_DELEGATE`，附近代码 `28: handlers.push_back(d);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`d`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/event/sceneeventlistener.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `d` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
21: }
23: void SceneEventHandler::RegisterEventHandler(SceneEventDefine eventType, const EventHandler& d)
24: {
25: auto& handlers = m_event_handlers[eventType].m_handlers;
26: ASSERT_NO_DUPLICATE_DELEGATE(d)
28: handlers.push_back(d);
29: }
31: void SceneEventHandler::ClearHandlers(SceneEventDefine eventType)
```

### `gameserver/scene/grid/grid.cpp:30` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-grid-cpp-30-check_cond_return-fd8e5f15` |
| 函数 | `FindRawGridsWithCache` |
| 类型 | `precondition_failed` |
| 条件 | `!fileName.empty()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/grid/grid.cpp`，关键条件 `!fileName.empty()`。 |
| 上下文 | 文件 `gameserver/scene/grid/grid.cpp`，函数 `FindRawGridsWithCache`，附近代码 `32: auto cacheIter = s_GridCache.find(filePath);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`!fileName.empty()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/grid.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!fileName.empty()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
26: static std::unordered_map<std::string, std::unique_ptr<grid::Grids, GridDeleter>> s_GridCache;
28: static const grid::Grids* FindRawGridsWithCache(const std::string &fileName)
29: {
30: CHECK_COND_RETURN(!fileName.empty(), NULL);
31: std::string filePath = FrameWork::GetConfig().GetFilePath(fileName.c_str(), SERVER_DIR_ROOT);
32: auto cacheIter = s_GridCache.find(filePath);
33: if (cacheIter != s_GridCache.end())
34: {
35: return cacheIter->second.get();
```

### `gameserver/scene/grid/grid.h:25` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-grid-h-25-check_cond-a80f7706` |
| 函数 | `Grid` |
| 类型 | `invariant_failed` |
| 条件 | `m_pGrids && m_pGrids->chf` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/scene/grid/grid.h`，关键条件 `m_pGrids && m_pGrids->chf`。 |
| 上下文 | 文件 `gameserver/scene/grid/grid.h`，函数 `Grid`，附近代码 `25: CHECK_COND(m_pGrids && m_pGrids->chf);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`m_pGrids && m_pGrids->chf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/grid.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_pGrids && m_pGrids->chf` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
20: class Grid : public SceneQueryInterface
21: {
22: private:
23: Grid(const grid::Grids* grids) : m_pGrids(grids), m_fMaxDownheight(0.f)
24: {
25: CHECK_COND(m_pGrids && m_pGrids->chf);
26: const auto* chf = m_pGrids->chf;
27: m_aoi_len_x = int((chf->width * chf->cs) / AOI_GRID_LEN);
28: m_aoi_len_z = int((chf->height * chf->cs) / AOI_GRID_LEN);
29: }
```

### `gameserver/scene/grid/gridinfo.cpp:629` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-629-check_cond_return-ab41f19c` |
| 函数 | `StaticGrid::_LoadFileSlop` |
| 类型 | `precondition_failed` |
| 条件 | `num > 0` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `num > 0`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，函数 `StaticGrid::_LoadFileSlop`，附近代码 `632: m_poGridData[index].m_index = hdataIndex;`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`num > 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `num > 0` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
625: memcpy(&num, dataPtr, sizeof(short));
626: i += sizeof(short);
627: dataPtr += sizeof(short);
629: CHECK_COND_RETURN(num > 0, false);
630: CHECK_COND_RETURN(num < 256, false);
632: m_poGridData[index].m_index = hdataIndex;
633: m_poGridData[index].m_len = num;
634: for (short j = 0; j < num; ++j)
```

### `gameserver/scene/grid/gridinfo.cpp:630` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-630-check_cond_return-ede1dfb5` |
| 函数 | `StaticGrid::_LoadFileSlop` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `num < 256` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `num < 256`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，函数 `StaticGrid::_LoadFileSlop`，附近代码 `632: m_poGridData[index].m_index = hdataIndex;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`num < 256`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `num < 256` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
625: memcpy(&num, dataPtr, sizeof(short));
626: i += sizeof(short);
627: dataPtr += sizeof(short);
629: CHECK_COND_RETURN(num > 0, false);
630: CHECK_COND_RETURN(num < 256, false);
632: m_poGridData[index].m_index = hdataIndex;
633: m_poGridData[index].m_len = num;
634: for (short j = 0; j < num; ++j)
635: {
```

### `gameserver/scene/grid/gridinfo.cpp:676` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-676-check_cond_return-adc636a9` |
| 函数 | `-` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `i == data.size()` |
| 日志/提示 | `invalid y [%f] of xz [%f %f] in grid file [%s]` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `invalid y [%f] of xz [%f %f] in grid file [%s]`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，附近日志 `invalid y [%f] of xz [%f %f] in grid file [%s]`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`invalid y [%f] of xz [%f %f] in grid file [%s]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `i == data.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
671: GetSceneXY(x, z, grid_x, grid_z);
672: //LogError("invalid y [%f] of xz [%f %f] in grid file [%s]", heightData.y, x, z, fileName.c_str());
673: }
674: }
675: }
676: CHECK_COND_RETURN(i == data.size(), false);
677: CHECK_COND_RETURN(hdataIndex == totalHeight, false);
679: int memorycost = m_MaxOffset * sizeof(GridData) + totalHeight * sizeof(HeightData);
680: LogInfo("file:[%s] loaded, memory used:[%.2fMB], y_range:[%.2f-%.2f], side: %.2f, max_offset: %d, grid_cnt: %d, height_cnt: %d",
681: fileName.c_str(), memorycost/1024.0f/1024.0f, yMin, yMax, m_header.side, m_MaxOffset, totalGrid, totalHeight);
```

### `gameserver/scene/grid/gridinfo.cpp:677` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-677-check_cond_return-4b6517fe` |
| 函数 | `-` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `hdataIndex == totalHeight` |
| 日志/提示 | `invalid y [%f] of xz [%f %f] in grid file [%s]` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `invalid y [%f] of xz [%f %f] in grid file [%s]`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，附近日志 `invalid y [%f] of xz [%f %f] in grid file [%s]`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`invalid y [%f] of xz [%f %f] in grid file [%s]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `hdataIndex == totalHeight` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
672: //LogError("invalid y [%f] of xz [%f %f] in grid file [%s]", heightData.y, x, z, fileName.c_str());
673: }
674: }
675: }
676: CHECK_COND_RETURN(i == data.size(), false);
677: CHECK_COND_RETURN(hdataIndex == totalHeight, false);
679: int memorycost = m_MaxOffset * sizeof(GridData) + totalHeight * sizeof(HeightData);
680: LogInfo("file:[%s] loaded, memory used:[%.2fMB], y_range:[%.2f-%.2f], side: %.2f, max_offset: %d, grid_cnt: %d, height_cnt: %d",
681: fileName.c_str(), memorycost/1024.0f/1024.0f, yMin, yMax, m_header.side, m_MaxOffset, totalGrid, totalHeight);
```

### `gameserver/scene/grid/gridinfo.cpp:718` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-718-check_cond_return-a4af2c27` |
| 函数 | `StaticGrid::_GetMaxIndex` |
| 类型 | `precondition_failed` |
| 条件 | `num > 0` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `num > 0`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，函数 `StaticGrid::_GetMaxIndex`，附近代码 `720: int heightDataSize = sizeof(short) + sizeof(UINT8) * 4;`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`num > 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `num > 0` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
713: memcpy(&num, dataPtr, sizeof(short));
714: i += sizeof(short);
715: dataPtr += sizeof(short);
717: totalHeight += num;
718: CHECK_COND_RETURN(num > 0, maxIndex);
720: int heightDataSize = sizeof(short) + sizeof(UINT8) * 4;
721: i += heightDataSize * num;
722: dataPtr += heightDataSize * num;
723: }
```

### `gameserver/scene/grid/gridinfo.cpp:724` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-724-check_cond_return-5bd261be` |
| 函数 | `StaticGrid::_GetMaxIndex` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `i == data.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `i == data.size()`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，函数 `StaticGrid::_GetMaxIndex`，附近代码 `726: CHECK_COND_RETURN(maxIndex >= 0, maxIndex);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`i == data.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `i == data.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
720: int heightDataSize = sizeof(short) + sizeof(UINT8) * 4;
721: i += heightDataSize * num;
722: dataPtr += heightDataSize * num;
723: }
724: CHECK_COND_RETURN(i == data.size(), maxIndex);
726: CHECK_COND_RETURN(maxIndex >= 0, maxIndex);
728: return maxIndex;
729: }
```

### `gameserver/scene/grid/gridinfo.cpp:726` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-grid-gridinfo-cpp-726-check_cond_return-ceda7810` |
| 函数 | `StaticGrid::_GetMaxIndex` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `maxIndex >= 0` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/scene/grid/gridinfo.cpp`，关键条件 `maxIndex >= 0`。 |
| 上下文 | 文件 `gameserver/scene/grid/gridinfo.cpp`，函数 `StaticGrid::_GetMaxIndex`，附近代码 `728: return maxIndex;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`maxIndex >= 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/grid/gridinfo.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `maxIndex >= 0` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
721: i += heightDataSize * num;
722: dataPtr += heightDataSize * num;
723: }
724: CHECK_COND_RETURN(i == data.size(), maxIndex);
726: CHECK_COND_RETURN(maxIndex >= 0, maxIndex);
728: return maxIndex;
729: }
```

### `gameserver/scene/handler/scenecollisions.cpp:192` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-handler-scenecollisions-cpp-192-check_cond_return-33876b86` |
| 函数 | `SceneCollisions::SolveCollisionForUnitNonPhysX_` |
| 类型 | `precondition_failed` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/handler/scenecollisions.cpp`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/scene/handler/scenecollisions.cpp`，函数 `SceneCollisions::SolveCollisionForUnitNonPhysX_`，附近代码 `193: xecs::Vector3 passiveMoveVec{}; // Collect push vectors together and apply to the target unit at last.`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/handler/scenecollisions.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
187: }
188: }
190: xecs::Vector3 SceneCollisions::SolveCollisionForUnitNonPhysX_(CombatUnit* unit, const NonPhysXPusherList& pusherList)
191: {
192: CHECK_COND_RETURN(unit, xecs::Vector3());
193: xecs::Vector3 passiveMoveVec{}; // Collect push vectors together and apply to the target unit at last.
194: const xecs::Vector3& curPos = unit->GetPosition();
195: NonPhysXPushInfo bePushed {
196: curPos,
197: unit->GetConf().GetBoundRaidus(),
```

### `gameserver/scene/handler/scenecollisions.cpp:392` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-handler-scenecollisions-cpp-392-check_cond_return-20305886` |
| 函数 | `SceneCollisions::SolveOverlapsWithBosses` |
| 类型 | `precondition_failed` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/handler/scenecollisions.cpp`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/scene/handler/scenecollisions.cpp`，函数 `SceneCollisions::SolveOverlapsWithBosses`，附近代码 `393: CollectPushersForPhysX_(m_scene, m_physxPusherList, BOSS_PUSHER);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/handler/scenecollisions.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
387: }
389: xecs::Vector3 SceneCollisions::SolveOverlapsWithBosses(CombatUnit* unit, const xecs::Vector3& pos)
390: {
391: // Only for Physics use.
392: CHECK_COND_RETURN(unit, pos);
393: CollectPushersForPhysX_(m_scene, m_physxPusherList, BOSS_PUSHER);
394: xecs::Vector3 finalPos = pos;
396: //const UINT32 blockSensFlag = xecs::getBlockSens_ecs(unit->GetEcsID());
397: physx::PxRigidDynamic* actor = unit->Get<UnitController>()->GetPxActor();
```

### `gameserver/scene/scene.cpp:152` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-scene-cpp-152-check_cond_noreturn-c763d899` |
| 函数 | `Scene::UnInit` |
| 类型 | `precondition_failed` |
| 条件 | `m_id2role.empty()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/scene.cpp`，关键条件 `m_id2role.empty()`。 |
| 上下文 | 文件 `gameserver/scene/scene.cpp`，函数 `Scene::UnInit`，附近代码 `155: if (m_aoi)`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`m_id2role.empty()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/scene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_id2role.empty()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
148: void Scene::UnInit()
149: {
150: //CleanUp();
152: CHECK_COND_NORETURN(m_id2role.empty());
153: CHECK_COND_NORETURN(m_id2loadingrole.empty());
155: if (m_aoi)
156: {
157: delete m_aoi;
```

### `gameserver/scene/scene.cpp:153` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-scene-cpp-153-check_cond_noreturn-3e329cf3` |
| 函数 | `Scene::UnInit` |
| 类型 | `precondition_failed` |
| 条件 | `m_id2loadingrole.empty()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/scene/scene.cpp`，关键条件 `m_id2loadingrole.empty()`。 |
| 上下文 | 文件 `gameserver/scene/scene.cpp`，函数 `Scene::UnInit`，附近代码 `155: if (m_aoi)`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`m_id2loadingrole.empty()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/scene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_id2loadingrole.empty()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
148: void Scene::UnInit()
149: {
150: //CleanUp();
152: CHECK_COND_NORETURN(m_id2role.empty());
153: CHECK_COND_NORETURN(m_id2loadingrole.empty());
155: if (m_aoi)
156: {
157: delete m_aoi;
158: m_aoi = NULL;
```

### `gameserver/scene/scene.cpp:325` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-scene-cpp-325-check_cond_noreturn-5e07ae03` |
| 函数 | `Scene::AddRole` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/scene/scene.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/scene/scene.cpp`，函数 `Scene::AddRole`，附近代码 `325: CHECK_COND_NORETURN(false);`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/scene.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
320: {
321: m_id2role[role->GetId()] = role;
322: }
323: else
324: {
325: CHECK_COND_NORETURN(false);
326: }
327: }
329: void Scene::DelRole(Role* role)
330: {
```

### `gameserver/scene/scenebattle.cpp:816` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-scenebattle-cpp-816-assert-7f7af461` |
| 函数 | `SceneBattle::LoadedNextScene` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/scene/scenebattle.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/scene/scenebattle.cpp`，函数 `SceneBattle::LoadedNextScene`，附近代码 `817: return false;`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/scenebattle.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
812: if (auto pSpawner = Get<LevelSpawner>())
813: {
814: if (!pSpawner->ChangeMap(m_conf->MapID, true))
815: {
816: ASSERT(false);
817: return false;
818: }
819: }
821: OnMapChange(m_conf->MapID);
```

### `gameserver/scene/sceneunithandler.cpp:189` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-sceneunithandler-cpp-189-check_cond_noreturn-5e07ae03` |
| 函数 | `SceneUnitHandler::CreateRoleNew` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `can't find monster template id [%u]` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/scene/sceneunithandler.cpp`，关键条件 `can't find monster template id [%u]`。 |
| 上下文 | 文件 `gameserver/scene/sceneunithandler.cpp`，函数 `SceneUnitHandler::CreateRoleNew`，附近日志 `can't find monster template id [%u]`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`can't find monster template id [%u]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/sceneunithandler.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
184: {
185: auto i = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(uTemplateID);
186: if (i == NULL)
187: {
188: LogError("can't find monster template id [%u]", uTemplateID);
189: CHECK_COND_NORETURN(false);
190: return NULL;
191: }
192: unit = CreateTemplateUnit(i, pos, face, type);
193: if (nullptr != unit)
194: {
```

### `gameserver/scene/sceneunithandler.cpp:264` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-sceneunithandler-cpp-264-check_cond_noreturn-5e07ae03` |
| 函数 | `-` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `caller:[%llu] create not find template id:[%u]` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/scene/sceneunithandler.cpp`，关键条件 `caller:[%llu] create not find template id:[%u]`。 |
| 上下文 | 文件 `gameserver/scene/sceneunithandler.cpp`，附近日志 `caller:[%llu] create not find template id:[%u]`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`caller:[%llu] create not find template id:[%u]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/sceneunithandler.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
259: }
260: auto conf = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(uTemplateID);
261: if (conf == NULL)
262: {
263: LogError("caller:[%llu] create not find template id:[%u]", caller->GetID(), uTemplateID);
264: CHECK_COND_NORETURN(false);
265: return NULL;
266: }
268: //CombatEnemy *pEnemy = new CombatEnemy();
269: //pEnemy->SetID(CombatUnit::NewId(KKSG::Category_Enemy, conf->EUID));
```

### `gameserver/scene/sceneunithandler.cpp:348` `CHECK_COND_WITH_LOG_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-sceneunithandler-cpp-348-check_cond_with_log_return-102bf043` |
| 函数 | `SceneUnitHandler::CreateDestructible` |
| 类型 | `config_or_table_missing` |
| 条件 | `i` |
| 日志/提示 | `can't find destructible template id [%u] \| create template destructible unit failed` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/scene/sceneunithandler.cpp`，关键条件 `can't find destructible template id [%u] | create template destructible unit failed`。 |
| 上下文 | 文件 `gameserver/scene/sceneunithandler.cpp`，函数 `SceneUnitHandler::CreateDestructible`，附近日志 `can't find destructible template id [%u] | create template destructible unit failed`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`can't find destructible template id [%u] | create template destructible unit failed`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/sceneunithandler.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `i` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
343: }
345: CombatUnit* SceneUnitHandler::CreateDestructible(const DestructibleSettings* settings, Scene* scene, const xecs::Vector3& pos, float face)
346: {
347: auto i = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(DestructibleUnit::STATISTICS_ID);
348: CHECK_COND_WITH_LOG_RETURN(i, LogError("can't find destructible template id [%u]", DestructibleUnit::STATISTICS_ID), NULL);
350: CombatUnit* unit = CreateTemplateUnit(i, pos, face, KKSG::Category_Enemy);
351: CHECK_COND_WITH_LOG_RETURN(unit, LogError("create template destructible unit failed"), NULL);
353: ((DestructibleUnit*)unit)->Init(settings, scene, pos, face);
```

### `gameserver/scene/sceneunithandler.cpp:351` `CHECK_COND_WITH_LOG_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-sceneunithandler-cpp-351-check_cond_with_log_return-1634d3e3` |
| 函数 | `SceneUnitHandler::CreateDestructible` |
| 类型 | `config_or_table_missing` |
| 条件 | `unit` |
| 日志/提示 | `create template destructible unit failed \| can't find destructible template id [%u]` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/scene/sceneunithandler.cpp`，关键条件 `create template destructible unit failed | can't find destructible template id [%u]`。 |
| 上下文 | 文件 `gameserver/scene/sceneunithandler.cpp`，函数 `SceneUnitHandler::CreateDestructible`，附近日志 `create template destructible unit failed | can't find destructible template id [%u]`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`create template destructible unit failed | can't find destructible template id [%u]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/sceneunithandler.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
346: {
347: auto i = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(DestructibleUnit::STATISTICS_ID);
348: CHECK_COND_WITH_LOG_RETURN(i, LogError("can't find destructible template id [%u]", DestructibleUnit::STATISTICS_ID), NULL);
350: CombatUnit* unit = CreateTemplateUnit(i, pos, face, KKSG::Category_Enemy);
351: CHECK_COND_WITH_LOG_RETURN(unit, LogError("create template destructible unit failed"), NULL);
353: ((DestructibleUnit*)unit)->Init(settings, scene, pos, face);
355: m_CreatedUnitList[unit->GetID()] = unit;
```

### `gameserver/scene/waypoint/waypointmgr.cpp:108` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-scene-waypoint-waypointmgr-cpp-108-assert-7f7af461` |
| 函数 | `WayPointMgr::_GetWayPointGraph` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `load wayPointGraph fail, filepath: %s` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/scene/waypoint/waypointmgr.cpp`，关键条件 `load wayPointGraph fail, filepath: %s`。 |
| 上下文 | 文件 `gameserver/scene/waypoint/waypointmgr.cpp`，函数 `WayPointMgr::_GetWayPointGraph`，附近日志 `load wayPointGraph fail, filepath: %s`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`load wayPointGraph fail, filepath: %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/scene/waypoint/waypointmgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
103: grid::NavToolPayload payload[64];
104: int payloadSize = 64;
105: grid::WaypointGraph* graph = grid::LoadWayPointGraph(fullpath.c_str(), payload, &payloadSize);
106: if (!graph) {
107: LogError(" load wayPointGraph fail, filepath: %s", filepath.c_str());
108: ASSERT(false);
109: }
111: LogInfo("load way point graph success, filepath: %s", filepath.c_str());
113: m_wayPointGraphCache[filepath] = graph;
```
