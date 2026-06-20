---
type: Code Playbook
title: Assert 排障 - xecslib-xecs-ecs-utility
description: xecslib-xecs-ecs-utility 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/xecslib-xecs-ecs-utility
resource: XEcsLib/XEcs/ecs/utility/json.hpp, XEcsLib/XEcs/ecs/utility/utility2convert.hpp, XEcsLib/XEcs/ecs/utility/utility2interface.cpp, XEcsLib/XEcs/ecs/utility/utility2math.h, XEcsLib/XEcs/ecs/utility/utility2node.hpp, XEcsLib/XEcs/ecs/utility/utility2present.hpp, XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp, XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp, XEcsLib/XEcs/ecs/utility/utility2timer.hpp, XEcsLib/XEcs/ecs/utility/xvector3.h
tags: assert, check, outage_log, crash, xecslib, xecs, ecs, utility
symbols: convertId, re_convertId, beginSirius, update_switch, update_condition, update_while, Position, XAppendEndingNode, LoadCommonStateHeader, unmount_timer, Vector3
logs: Entity NOT found., Entity NOT found in reverse mapping, 勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字), Double Init!, pos could not less than zero.
asserts: assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - xecslib-xecs-ecs-utility

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `xecslib-xecs-ecs-utility` |
| 条目数 | 18 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `XEcsLib/XEcs/ecs/utility/json.hpp:2409` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-json-hpp-2409-assert-254a69ea` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `x` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/json.hpp`，关键条件 `x`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/json.hpp`，附近代码 `2410: #endif`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`x`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/json.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `x` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
2404: #endif
2406: // allow overriding assert
2407: #if !defined(JSON_ASSERT)
2408: #include <cassert> // assert
2409: #define JSON_ASSERT(x) assert(x)
2410: #endif
2412: // allow to access some private functions (needed by the test suite)
2413: #if defined(JSON_TESTS_PRIVATE)
2414: #define JSON_PRIVATE_UNLESS_TESTED public
```

### `XEcsLib/XEcs/ecs/utility/utility2convert.hpp:48` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2convert-hpp-48-assert-6b4f8ad9` |
| 函数 | `convertId` |
| 类型 | `config_or_table_missing` |
| 条件 | `false && "Entity NOT found."` |
| 日志/提示 | `Entity NOT found.` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，关键条件 `Entity NOT found.`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，函数 `convertId`，附近日志 `Entity NOT found.`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`Entity NOT found.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "Entity NOT found."` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
44: if (it == m.mapping.cend())
45: {
46: #if (defined _Server_Ecs_) && (!defined _Editor_Ecs_)
47: getFacility(fw)->report_id_not_found_error(id);
48: assert(false && "Entity NOT found.");
49: #endif
50: #ifdef _Client_Ecs_
51: if(id != 0) getFacility(fw)->report_id_not_found_error(id);
52: #endif
53: return null_entity;
```

### `XEcsLib/XEcs/ecs/utility/utility2convert.hpp:82` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2convert-hpp-82-assert-5670b4b8` |
| 函数 | `re_convertId` |
| 类型 | `config_or_table_missing` |
| 条件 | `false && "Entity NOT found in reverse mapping"` |
| 日志/提示 | `Entity NOT found in reverse mapping` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，关键条件 `Entity NOT found in reverse mapping`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，函数 `re_convertId`，附近日志 `Entity NOT found in reverse mapping`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`Entity NOT found in reverse mapping`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2convert.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "Entity NOT found in reverse mapping"` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
77: #ifdef _WIN32
78: const string& id = (e == null_entity) ? "null_entity" : ((XEntity::LoanType(e) == 0) ? std::to_string(e) : "loan_entity");
79: const std::string& msg = id + " NOT found in reverse mapping.";
80: win_assert(false, msg);
81: #else
82: assert(false && "Entity NOT found in reverse mapping");
83: #endif
84: return 0;
85: }
86: #else
87: return e;
```

### `XEcsLib/XEcs/ecs/utility/utility2interface.cpp:26` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2interface-cpp-26-assert-c64b6c55` |
| 函数 | `beginSirius` |
| 类型 | `null_or_missing_object` |
| 条件 | `pg_sirius == nullptr && "勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)"` |
| 日志/提示 | `勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，关键条件 `勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，函数 `beginSirius`，附近日志 `勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `pg_sirius == nullptr && "勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)"` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
22: void beginSirius(IFacility* fcy)
23: {
24: #ifdef _Client_Ecs_
25: #ifdef _WIN32
26: assert(pg_sirius == nullptr && "勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)");
27: #endif
28: #else
29: assert(pg_sirius == nullptr && "Double Init!");
30: #endif
31: if(!pg_sirius) pg_sirius = new XSirius(fcy);
```

### `XEcsLib/XEcs/ecs/utility/utility2interface.cpp:29` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2interface-cpp-29-assert-c7da4f75` |
| 函数 | `beginSirius` |
| 类型 | `null_or_missing_object` |
| 条件 | `pg_sirius == nullptr && "Double Init!"` |
| 日志/提示 | `Double Init!` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，关键条件 `Double Init!`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，函数 `beginSirius`，附近日志 `Double Init!`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`Double Init!`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2interface.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `pg_sirius == nullptr && "Double Init!"` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
24: #ifdef _Client_Ecs_
25: #ifdef _WIN32
26: assert(pg_sirius == nullptr && "勿在游戏运行中更新DLL，或上一次停止游戏时报错(截取停止时红字)");
27: #endif
28: #else
29: assert(pg_sirius == nullptr && "Double Init!");
30: #endif
31: if(!pg_sirius) pg_sirius = new XSirius(fcy);
32: }
34: void endSirius()
```

### `XEcsLib/XEcs/ecs/utility/utility2math.h:28` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2math-h-28-assert-1a4f9291` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `!_isnan(x)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/utility2math.h`，关键条件 `!_isnan(x)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2math.h`，附近代码 `28: #define XIsNaN(x) (assert(!_isnan(x)))`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`!_isnan(x)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2math.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!_isnan(x)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
23: #define XNotAngle FLT_MAX
24: #define XNRound (XRound * XTrigonometricPrecision)
25: #define XDeg2Rad(x) ((x) * 0.0174533f)
26: #define XRad2Deg(x) ((x) * 57.295780f)
27: #define XRoundToCircle(x) (float(((int)(x) % (int)XRound) + (float)((x) - (int)(x))))
28: #define XIsNaN(x) (assert(!_isnan(x)))
29: #define XClamp(x, minValue, maxValue) (std::max(std::min((x), (maxValue)), (minValue)))
30: #define XIsInteger(x) ((std::fabs(x - (int)x) < FLT_EPSILON) || (std::fabs(x - (int)x) > (1 - FLT_EPSILON)))
32: inline float XSin[int(XNRound + 1)];
33: inline float XCos[int(XNRound + 1)];
```

### `XEcsLib/XEcs/ecs/utility/utility2node.hpp:32` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2node-hpp-32-assert-da4a18d5` |
| 函数 | `update_switch` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `bp.cur_switch < SWITCH_MAX` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，关键条件 `bp.cur_switch < SWITCH_MAX`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，函数 `update_switch`，附近代码 `34: size_t shift = SWITCH_MAX * 4;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`bp.cur_switch < SWITCH_MAX`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `bp.cur_switch < SWITCH_MAX` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
27: if (bp.sync)
28: {
29: bp.seq_switch |= (res << (bp.cur_switch * 4));
31: bp.cur_switch++;
32: assert(bp.cur_switch < SWITCH_MAX);
34: size_t shift = SWITCH_MAX * 4;
36: bp.seq_switch ^= ((bp.seq_switch >> shift) << shift);
37: bp.seq_switch |= (bp.cur_switch << shift);
```

### `XEcsLib/XEcs/ecs/utility/utility2node.hpp:52` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2node-hpp-52-assert-b92ddfb9` |
| 函数 | `update_condition` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `bp.cur_condition < COND_MAX` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，关键条件 `bp.cur_condition < COND_MAX`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，函数 `update_condition`，附近代码 `54: bp.seq_condition ^= ((bp.seq_condition >> COND_MAX) << COND_MAX);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`bp.cur_condition < COND_MAX`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `bp.cur_condition < COND_MAX` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
47: if (bp.sync)
48: {
49: if (res) bp.seq_condition |= (1 << bp.cur_condition);
51: bp.cur_condition++;
52: assert(bp.cur_condition < COND_MAX);
54: bp.seq_condition ^= ((bp.seq_condition >> COND_MAX) << COND_MAX);
55: bp.seq_condition |= (bp.cur_condition << COND_MAX);
57: getEvents(fw).on_branch_dec.broadcast(std::forward<Entity>(e), fw);
```

### `XEcsLib/XEcs/ecs/utility/utility2node.hpp:67` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2node-hpp-67-assert-e2e5d0c2` |
| 函数 | `update_while` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `idx < UNTIL_MAX` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，关键条件 `idx < UNTIL_MAX`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，函数 `update_while`，附近代码 `68: bp.seq_while |= (1 << idx);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`idx < UNTIL_MAX`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2node.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `idx < UNTIL_MAX` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
62: {
63: XBluePrint& bp = fw.get<XBluePrint>(e);
65: if (bp.sync)
66: {
67: assert(idx < UNTIL_MAX);
68: bp.seq_while |= (1 << idx);
70: getEvents(fw).on_branch_dec.broadcast(std::forward<Entity>(e), fw);
71: }
72: }
```

### `XEcsLib/XEcs/ecs/utility/utility2present.hpp:83` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2present-hpp-83-assert-9134e411` |
| 函数 | `Position` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false && "pos could not less than zero."` |
| 日志/提示 | `pos could not less than zero.` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/utility2present.hpp`，关键条件 `pos could not less than zero.`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2present.hpp`，函数 `Position`，附近日志 `pos could not less than zero.`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`pos could not less than zero.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2present.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "pos could not less than zero."` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
79: #if (defined _Server_Ecs_) && (!defined _Editor_Ecs_)
80: if (pos.x < -FLT_EPSILON ||
81: pos.y < -FLT_EPSILON ||
82: pos.z < -FLT_EPSILON)
83: assert(false && "pos could not less than zero.");
84: #endif
85: #ifdef _Server_Ecs_
86: if (!isMinimalGap(fw, re_convertId(e, fw), pos - p.position, getActionRatio(fw, e)))
87: #else
88: if (!isMinimalGap(pos - p.position, getActionRatio(fw, e)))
```

### `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp:67` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2quaternion-hpp-67-assert-b8883498` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `s != 0` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，关键条件 `s != 0`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，附近代码 `68: return q * (1.0f / s);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`s != 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `s != 0` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
62: q.w *= s;
63: }
65: inline Quaternion operator /(const Quaternion& q, float s)
66: {
67: assert(s != 0);
68: return q * (1.0f / s);
69: }
71: inline void operator /=(Quaternion& q, float s)
72: {
```

### `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp:73` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2quaternion-hpp-73-assert-b8883498` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `s != 0` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，关键条件 `s != 0`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，附近代码 `74: q *= (1.0f / s);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`s != 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2quaternion.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `s != 0` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
68: return q * (1.0f / s);
69: }
71: inline void operator /=(Quaternion& q, float s)
72: {
73: assert(s != 0);
74: q *= (1.0f / s);
75: }
77: inline void operator *=(Quaternion& q1, const Quaternion& q2) { q1 = q1 * q2; }
```

### `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp:54` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2reader-json-hpp-54-assert-ed18f60f` |
| 函数 | `-` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)pNode->index < pBase->nodeCount` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，关键条件 `(uint32_t)pNode->index < pBase->nodeCount`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，附近代码 `54: assert((uint32_t)pNode->index < pBase->nodeCount); \`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)pNode->index < pBase->nodeCount`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)pNode->index < pBase->nodeCount` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
49: pNode->timeBased = J.at("timeBased"); \
50: \
51: pNode->family = get_node_type<Type>(); \
52: pNode->instance = pBase; \
53: pNode->hash = pBase->hash; \
54: assert((uint32_t)pNode->index < pBase->nodeCount); \
55: pBase->node[pNode->index] = pNode; \
56: \
57: if(pNode->timeBased) \
58: { \
59: pBase->headIndex = pNode->index; \
```

### `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp:72` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2reader-json-hpp-72-assert-3b8e27bc` |
| 函数 | `-` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)pNode->index < XNodeMax + XVirtualNodeMax` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，关键条件 `(uint32_t)pNode->index < XNodeMax + XVirtualNodeMax`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，附近代码 `73: pNode->family = get_node_type<Type>(); \`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)pNode->index < XNodeMax + XVirtualNodeMax`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)pNode->index < XNodeMax + XVirtualNodeMax` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
67: }
69: #define XLoadVirtualBaseNode(pNode, pBase, Type) \
70: { \
71: pNode->index = XVirtualNodeAt++; \
72: assert((uint32_t)pNode->index < XNodeMax + XVirtualNodeMax); \
73: pNode->family = get_node_type<Type>(); \
74: pNode->instance = pBase; \
75: pNode->hash = pBase->hash; \
76: pBase->node[pNode->index] = pNode; \
77: }
```

### `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp:462` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2reader-json-hpp-462-assert-f57e473c` |
| 函数 | `XAppendEndingNode` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)pEnd->index < XNodeMax + XVirtualNodeMax` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，关键条件 `(uint32_t)pEnd->index < XNodeMax + XVirtualNodeMax`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，函数 `XAppendEndingNode`，附近代码 `463: pBase->node[pEnd->index] = pEnd;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)pEnd->index < XNodeMax + XVirtualNodeMax`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)pEnd->index < XNodeMax + XVirtualNodeMax` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
457: pEnd->timeBased = true;
459: pEnd->family = get_node_type<XEndData>();
460: pEnd->instance = pBase;
461: pEnd->hash = pBase->hash;
462: assert((uint32_t)pEnd->index < XNodeMax + XVirtualNodeMax);
463: pBase->node[pEnd->index] = pEnd;
465: {
466: pEnd->at = pBase->length;
467: pBase->times.emplace(pEnd->at, pBase, pEnd->index, get_node_type<XTimerData>());
```

### `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp:1083` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2reader-json-hpp-1083-assert-bc110b4d` |
| 函数 | `LoadCommonStateHeader` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，函数 `LoadCommonStateHeader`，附近代码 `1083: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2reader_json.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1078: return LoadStateByJson(fw, LoadFile(fw, "./Assets/BundleRes/StatePackage/FreeFly/common_freefly_header.bytes"), 0, true);
1079: #else
1080: return LoadStateByJson(fw, LoadFile(fw, "./gsconf/StatePackage/FreeFly/common_freefly_header.bytes"), 0, true);
1081: #endif
1082: }break;
1083: default: assert(false); break;
1084: }
1085: }
1086: return nullptr;
1087: }
```

### `XEcsLib/XEcs/ecs/utility/utility2timer.hpp:158` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-utility2timer-hpp-158-assert-b13d5fd7` |
| 函数 | `unmount_timer` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(int)standard >= 0` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/utility/utility2timer.hpp`，关键条件 `(int)standard >= 0`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/utility2timer.hpp`，函数 `unmount_timer`，附近代码 `158: assert((int)standard >= 0);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(int)standard >= 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/utility2timer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(int)standard >= 0` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
153: size_t standard = (timer._generation - tline.generation) * TLineMax + (timer._idx - tline.cursor);
154: #ifdef _Client_Ecs_
155: //in case script not match with server
156: if ((int)standard < 0) standard = 0;
157: #else
158: assert((int)standard >= 0);
159: #endif
161: double time_at = (standard + timer._odds / 1000.0) * (double)ratio;
163: timer._time_at = (size_t)time_at;
```

### `XEcsLib/XEcs/ecs/utility/xvector3.h:43` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-utility-xvector3-h-43-assert-bc110b4d` |
| 函数 | `Vector3` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/utility/xvector3.h`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/utility/xvector3.h`，函数 `Vector3`，附近代码 `43: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/utility/xvector3.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
38: {
39: case 0: return x;
40: case 1: return y;
41: case 2: return z;
42: #ifdef _Server_Ecs_
43: default: assert(false); break;
44: #endif
45: #ifdef _Client_Ecs_
46: default: return 0;
47: #endif
48: }
```
