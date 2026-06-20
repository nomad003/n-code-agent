---
type: Code Playbook
title: Assert 排障 - gameserver-unit-attr
description: gameserver-unit-attr 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-attr
resource: gameserver/unit/attr/combatattrdef.cpp, gameserver/unit/attr/combatattribute.cpp
tags: assert, check, outage_log, crash, gameserver, unit, attr
symbols: InitAttrIndexArray, AttrData::Set, AttrData::HandleMaxList
logs: unit: %u-%llu, attr: %d is invalid, unit: %u-%llu, attr: %d value: %f < 0
asserts: ASSERT, CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-attr

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-attr` |
| 条目数 | 4 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/attr/combatattrdef.cpp:29` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-attr-combatattrdef-cpp-29-assert-b45d1fe1` |
| 函数 | `InitAttrIndexArray` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `attrID < CA_MAX_COUNT` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/attr/combatattrdef.cpp`，关键条件 `attrID < CA_MAX_COUNT`。 |
| 上下文 | 文件 `gameserver/unit/attr/combatattrdef.cpp`，函数 `InitAttrIndexArray`，附近代码 `30: g_AttrOffsetArray[attrID] = i;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`attrID < CA_MAX_COUNT`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/attr/combatattrdef.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `attrID < CA_MAX_COUNT` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
25: memset(g_AttrOffsetArray, 0, sizeof g_AttrOffsetArray);
26: for (UINT32 i = 0; i < CA_NAME_COUNT; ++i)
27: {
28: UINT32 attrID = g_AttrNameList[i].AttrID;
29: ASSERT(attrID < CA_MAX_COUNT);
30: g_AttrOffsetArray[attrID] = i;
31: }
32: }
```

### `gameserver/unit/attr/combatattribute.cpp:38` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-attr-combatattribute-cpp-38-check_cond-ffc67c8a` |
| 函数 | `AttrData::Set` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `unit: %u-%llu, attr: %d is invalid` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/unit/attr/combatattribute.cpp`，关键条件 `unit: %u-%llu, attr: %d is invalid`。 |
| 上下文 | 文件 `gameserver/unit/attr/combatattribute.cpp`，函数 `AttrData::Set`，附近日志 `unit: %u-%llu, attr: %d is invalid`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`unit: %u-%llu, attr: %d is invalid`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/attr/combatattribute.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
33: {
34: UINT32 offset = AttributeDefInfo::GetAttributeOffset(attrID);
35: if (offset >= CA_NAME_COUNT)
36: {
37: LogError("unit: %u-%llu, attr: %d is invalid", mUnitId, mUId, attrID);
38: CHECK_COND(false);
39: }
41: if (value < -1e-9)
42: {
43: AttrDefine::RowData* rowData = RoleAttrConfig::Instance()->GetAttrDefine(attrID);
```

### `gameserver/unit/attr/combatattribute.cpp:50` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-attr-combatattribute-cpp-50-check_cond-ffc67c8a` |
| 函数 | `AttrData::Set` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `false` |
| 日志/提示 | `unit: %u-%llu, attr: %d value: %f < 0` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/attr/combatattribute.cpp`，关键条件 `unit: %u-%llu, attr: %d value: %f < 0`。 |
| 上下文 | 文件 `gameserver/unit/attr/combatattribute.cpp`，函数 `AttrData::Set`，附近日志 `unit: %u-%llu, attr: %d value: %f < 0`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`unit: %u-%llu, attr: %d value: %f < 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/attr/combatattribute.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
45: {
46: value = 0;
47: if (rowData->MinusAble == 1)
48: {
49: LogError("unit: %u-%llu, attr: %d value: %f < 0", mUnitId, mUId, attrID, value);
50: CHECK_COND(false);
51: }
52: }
53: }
55: mAttrData[offset] = value;
```

### `gameserver/unit/attr/combatattribute.cpp:60` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-attr-combatattribute-cpp-60-check_cond-869d550f` |
| 函数 | `AttrData::HandleMaxList` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `index < CA_MAXTYPE_ATTR_SIZE` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/attr/combatattribute.cpp`，关键条件 `index < CA_MAXTYPE_ATTR_SIZE`。 |
| 上下文 | 文件 `gameserver/unit/attr/combatattribute.cpp`，函数 `AttrData::HandleMaxList`，附近代码 `62: if (ATTR_None == attrID) return;`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`index < CA_MAXTYPE_ATTR_SIZE`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/attr/combatattribute.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `index < CA_MAXTYPE_ATTR_SIZE` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
55: mAttrData[offset] = value;
56: }
58: void AttrData::HandleMaxList(CombatAttrDef attrID, double value, UINT32 index)
59: {
60: CHECK_COND(index < CA_MAXTYPE_ATTR_SIZE);
62: if (ATTR_None == attrID) return;
63: double absValue = std::abs(value);
64: UINT32 uintValue = (UINT32)absValue;
65: if (uintValue == 0) return;
```
