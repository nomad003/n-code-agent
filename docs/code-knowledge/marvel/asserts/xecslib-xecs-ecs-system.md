---
type: Code Playbook
title: Assert 排障 - xecslib-xecs-ecs-system
description: xecslib-xecs-ecs-system 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/xecslib-xecs-ecs-system
resource: XEcsLib/XEcs/ecs/system/XActionSys.hpp, XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp, XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp, XEcsLib/XEcs/ecs/system/XLocationSys.hpp, XEcsLib/XEcs/ecs/system/XSkillWarningSys.hpp, XEcsLib/XEcs/ecs/system/XStateSys.hpp, XEcsLib/XEcs/ecs/system/XStatusSys.hpp, XEcsLib/XEcs/ecs/system/XSwitchNodeSys.hpp
tags: assert, check, outage_log, crash, xecslib, xecs, ecs, system
symbols: getCoolDownLeft, OnRatioChanged, Run, LiteRun, create, destroy, get_final_pos, CalcWarningPosition, transfer, switch_move_type, start
logs: cd can not go to zero!, ratio could not be zero., pos could not less than zero.
asserts: assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - xecslib-xecs-ecs-system

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `xecslib-xecs-ecs-system` |
| 条目数 | 19 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `XEcsLib/XEcs/ecs/system/XActionSys.hpp:65` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xactionsys-hpp-65-assert-124da082` |
| 函数 | `getCoolDownLeft` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `left > 0 && "cd can not go to zero!"` |
| 日志/提示 | `cd can not go to zero!` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XActionSys.hpp`，关键条件 `cd can not go to zero!`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XActionSys.hpp`，函数 `getCoolDownLeft`，附近日志 `cd can not go to zero!`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`cd can not go to zero!`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XActionSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `left > 0 && "cd can not go to zero!"` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
60: if(fabs(multiple - 1) > FLT_EPSILON)
61: getFacility(fw)->report_message(re_convertId(e, fw), skill, "CD multiple by: " + std::to_string(multiple));
62: #endif
63: left *= multiple;
65: assert(left > 0 && "cd can not go to zero!");
67: ins.used_up = usedupCheck(ins.cd, ins.phase_count, left);
68: ins.cd_relative_end = time + left;
69: }
70: else
```

### `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp:47` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xbpupdatesys-hpp-47-assert-fac51b80` |
| 函数 | `OnRatioChanged` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `older > FLT_EPSILON && newer > FLT_EPSILON && "ratio could not be zero."` |
| 日志/提示 | `ratio could not be zero.` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，关键条件 `ratio could not be zero.`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，函数 `OnRatioChanged`，附近日志 `ratio could not be zero.`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`ratio could not be zero.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `older > FLT_EPSILON && newer > FLT_EPSILON && "ratio could not be zero."` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
42: if (bp.valid)
43: {
44: XTimeLine& tline = getTimeLine(fw);
45: float newer = getActionRatio(fw, e);
47: assert(older > FLT_EPSILON && newer > FLT_EPSILON && "ratio could not be zero.");
49: if (!isGamePlayFixed(fw, e))
50: {
51: for (Entity t : bp.timers)
52: {
```

### `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp:323` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xbpupdatesys-hpp-323-assert-bbcbd034` |
| 函数 | `Run` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)t.index < XNodeMax + XVirtualNodeMax` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，关键条件 `(uint32_t)t.index < XNodeMax + XVirtualNodeMax`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，函数 `Run`，附近代码 `323: assert((uint32_t)t.index < XNodeMax + XVirtualNodeMax);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)t.index < XNodeMax + XVirtualNodeMax`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)t.index < XNodeMax + XVirtualNodeMax` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
318: {
319: for (const XTransferData& t : root->transfer)
320: {
321: if (t.enable && t.index != Invalide_Trans)
322: {
323: assert((uint32_t)t.index < XNodeMax + XVirtualNodeMax);
324: stack.push_back(root->instance->node[t.index]);
325: }
326: }
327: }
```

### `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp:415` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xbpupdatesys-hpp-415-assert-bbcbd034` |
| 函数 | `LiteRun` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)t.index < XNodeMax + XVirtualNodeMax` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，关键条件 `(uint32_t)t.index < XNodeMax + XVirtualNodeMax`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，函数 `LiteRun`，附近代码 `415: assert((uint32_t)t.index < XNodeMax + XVirtualNodeMax);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)t.index < XNodeMax + XVirtualNodeMax`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XBPUpdateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)t.index < XNodeMax + XVirtualNodeMax` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
410: XNodeData* next = nullptr;
411: for (const XTransferData& t : root->transfer)
412: {
413: if (t.enable && t.index != Invalide_Trans)
414: {
415: assert((uint32_t)t.index < XNodeMax + XVirtualNodeMax);
416: next = root->instance->node[t.index];
417: }
418: }
420: if (root == next) break;
```

### `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp:37` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xenttmappingsys-hpp-37-assert-770878ee` |
| 函数 | `create` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `m.mapping.find(id) == m.mapping.end()` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，关键条件 `m.mapping.find(id) == m.mapping.end()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，函数 `create`，附近代码 `40: size_t entt = (size_t)XEntity::Value(e);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`m.mapping.find(id) == m.mapping.end()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m.mapping.find(id) == m.mapping.end()` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
33: void create(Entity e, uint64_t id, framework& fw)
34: {
35: XEnttMapping& m = getEntityMapping(fw);
37: assert(m.mapping.find(id) == m.mapping.end());
38: m.mapping[id] = e;
40: size_t entt = (size_t)XEntity::Value(e);
41: while (entt >= m.reverse_mapping.size())
42: {
```

### `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp:46` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xenttmappingsys-hpp-46-assert-c5acb1ab` |
| 函数 | `create` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `0 == m.reverse_mapping[entt]` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，关键条件 `0 == m.reverse_mapping[entt]`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，函数 `create`，附近代码 `47: m.reverse_mapping[entt] = id;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`0 == m.reverse_mapping[entt]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `0 == m.reverse_mapping[entt]` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
41: while (entt >= m.reverse_mapping.size())
42: {
43: m.reverse_mapping.push_back(0);
44: }
46: assert(0 == m.reverse_mapping[entt]);
47: m.reverse_mapping[entt] = id;
48: }
50: void destroy(Entity e, framework& fw)
51: {
```

### `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp:55` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xenttmappingsys-hpp-55-assert-e03689f0` |
| 函数 | `destroy` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `!instance->isUpdating()` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，关键条件 `!instance->isUpdating()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，函数 `destroy`，附近代码 `56: #endif`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`!instance->isUpdating()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!instance->isUpdating()` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
50: void destroy(Entity e, framework& fw)
51: {
52: XInstance* instance = getInstance(fw);
54: #ifndef _Editor_Ecs_
55: assert(!instance->isUpdating());
56: #endif
58: if (e != instance->getSingle())
59: {
60: XEnttMapping& m = getEntityMapping(fw);
```

### `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp:64` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xenttmappingsys-hpp-64-assert-b8cbf62b` |
| 函数 | `destroy` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `entt < m.reverse_mapping.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，关键条件 `entt < m.reverse_mapping.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，函数 `destroy`，附近代码 `68: #ifdef _Server_Ecs_`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`entt < m.reverse_mapping.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `entt < m.reverse_mapping.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
59: {
60: XEnttMapping& m = getEntityMapping(fw);
62: size_t entt = (size_t)XEntity::Value(e);
64: assert(entt < m.reverse_mapping.size());
66: uint64_t id = m.reverse_mapping[entt];
68: #ifdef _Server_Ecs_
69: auto it = m.mapping.find(id);
```

### `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp:70` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xenttmappingsys-hpp-70-assert-2b8c55f7` |
| 函数 | `destroy` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `it != m.mapping.end()` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，关键条件 `it != m.mapping.end()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，函数 `destroy`，附近代码 `72: m.mapping.erase(id);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`it != m.mapping.end()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XEnttMappingSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `it != m.mapping.end()` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
66: uint64_t id = m.reverse_mapping[entt];
68: #ifdef _Server_Ecs_
69: auto it = m.mapping.find(id);
70: assert(it != m.mapping.end());
71: #endif
72: m.mapping.erase(id);
73: m.reverse_mapping[entt] = 0;
74: #ifdef _Client_Ecs_
75: //keep group id of e in mapping
```

### `XEcsLib/XEcs/ecs/system/XLocationSys.hpp:332` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xlocationsys-hpp-332-assert-9134e411` |
| 函数 | `get_final_pos` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false && "pos could not less than zero."` |
| 日志/提示 | `pos could not less than zero.` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XLocationSys.hpp`，关键条件 `pos could not less than zero.`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XLocationSys.hpp`，函数 `get_final_pos`，附近日志 `pos could not less than zero.`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`pos could not less than zero.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XLocationSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "pos could not less than zero."` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
327: }
328: #ifdef _Server_Ecs_
329: if (pos.position.x < -FLT_EPSILON ||
330: pos.position.y < -FLT_EPSILON ||
331: pos.position.z < -FLT_EPSILON)
332: assert(false && "pos could not less than zero.");
334: st.sticky = false;
335: #endif
336: }
337: #endif
```

### `XEcsLib/XEcs/ecs/system/XSkillWarningSys.hpp:78` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xskillwarningsys-hpp-78-assert-3cd5e1ab` |
| 函数 | `CalcWarningPosition` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `(uint32_t)w->bulletIndex < XNodeLimit(w->instance)` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/system/XSkillWarningSys.hpp`，关键条件 `(uint32_t)w->bulletIndex < XNodeLimit(w->instance)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XSkillWarningSys.hpp`，函数 `CalcWarningPosition`，附近代码 `79: XBulletData* b = static_cast<XBulletData*>(w->instance->node[w->bulletIndex]);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`(uint32_t)w->bulletIndex < XNodeLimit(w->instance)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XSkillWarningSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(uint32_t)w->bulletIndex < XNodeLimit(w->instance)` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
73: center += (forward * len);
74: }
76: if (w->needBullet)
77: {
78: assert((uint32_t)w->bulletIndex < XNodeLimit(w->instance));
79: XBulletData* b = static_cast<XBulletData*>(w->instance->node[w->bulletIndex]);
80: //calculate visual bullet
81: Vector3 begin{}, towards{}; float dis{};
82: if (w->visibleBullet)
83: {
```

### `XEcsLib/XEcs/ecs/system/XStateSys.hpp:56` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatesys-hpp-56-assert-af369401` |
| 函数 | `transfer` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `f != invalid_family_id` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，关键条件 `f != invalid_family_id`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，函数 `transfer`，附近代码 `60: int tmp = present ? 1 : 0;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`f != invalid_family_id`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `f != invalid_family_id` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
51: }
53: s.transferring = true;
55: f = get_sys_from_status(fw, get_sys_map_key(fw, e, s.current, s.mt_current));
56: assert(f != invalid_family_id);
58: s.next = to;
60: int tmp = present ? 1 : 0;
```

### `XEcsLib/XEcs/ecs/system/XStateSys.hpp:92` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatesys-hpp-92-assert-af369401` |
| 函数 | `transfer` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `f != invalid_family_id` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，关键条件 `f != invalid_family_id`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，函数 `transfer`，附近代码 `95: }`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`f != invalid_family_id`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `f != invalid_family_id` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
88: s.last = s.current;
89: s.current = s.next;
91: f = get_sys_from_status(fw, get_sys_map_key(fw, e, s.current, s.mt_current));
92: assert(f != invalid_family_id);
94: res = true;
95: }
97: s.transferring = false;
```

### `XEcsLib/XEcs/ecs/system/XStateSys.hpp:108` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatesys-hpp-108-assert-dd96d632` |
| 函数 | `switch_move_type` |
| 类型 | `null_or_missing_object` |
| 条件 | `mt != XMoveType::None` |
| 日志/提示 | `-` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，关键条件 `mt != XMoveType::None`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，函数 `switch_move_type`，附近代码 `110: XStatement& s = fw.get<XStatement>(e);`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`mt != XMoveType::None`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `mt != XMoveType::None` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
103: return res ? s.current : XStateType::Max;
104: }
106: bool switch_move_type(framework& fw, Entity e, XMoveType mt)
107: {
108: assert(mt != XMoveType::None);
110: XStatement& s = fw.get<XStatement>(e);
112: if (s.mt_current != mt)
113: {
```

### `XEcsLib/XEcs/ecs/system/XStateSys.hpp:121` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatesys-hpp-121-assert-bc110b4d` |
| 函数 | `switch_move_type` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，函数 `switch_move_type`，附近代码 `121: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
116: case XMoveType::None: break;
117: case XMoveType::Run: fw.remove<XGroundable>(e); break;
118: case XMoveType::Fly: fw.remove<XFlyable>(e); break;
119: case XMoveType::Jump: fw.remove<XJumpable>(e); break;
120: case XMoveType::FreeFly:fw.remove<XFreeFlyable>(e); break;
121: default: assert(false); break;
122: }
124: #ifdef _Server_Ecs_
125: if(XMoveType::None != s.mt_current)
126: #endif
```

### `XEcsLib/XEcs/ecs/system/XStateSys.hpp:138` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatesys-hpp-138-assert-bc110b4d` |
| 函数 | `switch_move_type` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，函数 `switch_move_type`，附近代码 `138: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStateSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
133: {
134: case XMoveType::Run: fw.assign<XGroundable>(e); break;
135: case XMoveType::Fly: fw.assign<XFlyable>(e); break;
136: case XMoveType::Jump: fw.assign<XJumpable>(e); break;
137: case XMoveType::FreeFly:fw.assign<XFreeFlyable>(e); break;
138: default: assert(false); break;
139: }
140: }
141: return true;
142: }
143: };
```

### `XEcsLib/XEcs/ecs/system/XStatusSys.hpp:63` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatussys-hpp-63-assert-bc110b4d` |
| 函数 | `transfer` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，函数 `transfer`，附近代码 `63: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
58: case XStateType::Idle: fw.remove<XIdleable>(e); break;
59: case XStateType::Move: fw.remove<XMoveable>(e); break;
60: case XStateType::Hit: fw.remove<XBehitable>(e); break;
61: case XStateType::Skill: fw.remove<XSkillable>(e); break;
62: case XStateType::Death: fw.remove<XDeathable>(e); break;
63: default: assert(false); break;
64: }
65: ps->finish = true;
66: switch (ps->next)
67: {
68: case XStateType::Idle: fw.assign<XIdleable>(e); break;
```

### `XEcsLib/XEcs/ecs/system/XStatusSys.hpp:73` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xstatussys-hpp-73-assert-bc110b4d` |
| 函数 | `transfer` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，函数 `transfer`，附近代码 `73: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XStatusSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
68: case XStateType::Idle: fw.assign<XIdleable>(e); break;
69: case XStateType::Move: fw.assign<XMoveable>(e); break;
70: case XStateType::Hit: fw.assign<XBehitable>(e); break;
71: case XStateType::Skill: fw.assign<XSkillable>(e); break;
72: case XStateType::Death: fw.assign<XDeathable>(e); break;
73: default: assert(false); break;
74: }
76: XStatusSys* pStatus = static_cast<XStatusSys*>(
77: XSystemManager::getInstance().get(get_sys_from_status(fw, get_sys_map_key(fw, e, ps->next, ps->mt_current))));
78: pStatus->begin(e, fw);
```

### `XEcsLib/XEcs/ecs/system/XSwitchNodeSys.hpp:69` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-ecs-system-xswitchnodesys-hpp-69-assert-65df5165` |
| 函数 | `start` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `vs->rhs.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/ecs/system/XSwitchNodeSys.hpp`，关键条件 `vs->rhs.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/ecs/system/XSwitchNodeSys.hpp`，函数 `start`，附近代码 `71: {`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`vs->rhs.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/ecs/system/XSwitchNodeSys.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `vs->rhs.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
65: script_proto_type* callback = script_get(fw, get_sys_type<XSwitchNodeSys>(), s->functionHash);
67: if (callback)
68: {
69: assert(vs->rhs.size());
70: switch (vs->rhs.size())
71: {
72: case 2: return_type = switch_call_back(callback, fw, e, vs->specifier, vs->rhs[1]); break;
73: case 3: return_type = switch_call_back(callback, fw, e, vs->specifier, vs->rhs[1], vs->rhs[2]); break;
74: case 4: return_type = switch_call_back(callback, fw, e, vs->specifier, vs->rhs[1], vs->rhs[2], vs->rhs[3]); break;
```
