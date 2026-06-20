---
type: Code Playbook
title: Assert 排障 - gameserver-tableload
description: gameserver-tableload 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-tableload
resource: gameserver/tableload/aiconfig.cpp, gameserver/tableload/buffconfig.cpp, gameserver/tableload/roleattrconfig.cpp, gameserver/tableload/scenedropconfig.cpp
tags: assert, check, outage_log, crash, gameserver, tableload
symbols: AIConfig::CheckLoad, BuffConfig::GetBuffInfo, RoleAttrConfig::GetSynAttrID, SceneDropConfig::CheckLoad
logs: UnitAITable is empty, buff ID too large: %u, cant larger than 16777215 | buff Level too large: %u, cant larger than 255, GetSynAttrID attrID %d
asserts: ASSERT, CHECK_COND_WITH_LOG_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-tableload

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-tableload` |
| 条目数 | 5 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/tableload/aiconfig.cpp:143` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-tableload-aiconfig-cpp-143-assert-7f7af461` |
| 函数 | `AIConfig::CheckLoad` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `UnitAITable is empty` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/tableload/aiconfig.cpp`，关键条件 `UnitAITable is empty`。 |
| 上下文 | 文件 `gameserver/tableload/aiconfig.cpp`，函数 `AIConfig::CheckLoad`，附近日志 `UnitAITable is empty`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`UnitAITable is empty`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/tableload/aiconfig.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
138: //TOOL_AUTO_GEN_CPP_END
140: if (m_oUnitAITable.Table.empty())
141: {
142: LogError("UnitAITable is empty");
143: ASSERT(false);
144: }
146: return true;
147: }
```

### `gameserver/tableload/buffconfig.cpp:251` `CHECK_COND_WITH_LOG_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-tableload-buffconfig-cpp-251-check_cond_with_log_return-98663fe6` |
| 函数 | `BuffConfig::GetBuffInfo` |
| 类型 | `config_or_table_missing` |
| 条件 | `buffID <= 0x00FFFFFF` |
| 日志/提示 | `buff ID too large: %u, cant larger than 16777215 \| buff Level too large: %u, cant larger than 255` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/tableload/buffconfig.cpp`，关键条件 `buff ID too large: %u, cant larger than 16777215 | buff Level too large: %u, cant larger than 255`。 |
| 上下文 | 文件 `gameserver/tableload/buffconfig.cpp`，函数 `BuffConfig::GetBuffInfo`，附近日志 `buff ID too large: %u, cant larger than 16777215 | buff Level too large: %u, cant larger than 255`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`buff ID too large: %u, cant larger than 16777215 | buff Level too large: %u, cant larger than 255`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/tableload/buffconfig.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `buffID <= 0x00FFFFFF` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
247: const XBuffCreateData* BuffConfig::GetBuffInfo(UINT32 buffID, UINT32 BuffLevel, bool isPVP)
248: {
249: XBuffCreateData *pBuffInfo = NULL;
251: CHECK_COND_WITH_LOG_RETURN(buffID <= 0x00FFFFFF, LogError("buff ID too large: %u, cant larger than 16777215", buffID), nullptr);
252: //CHECK_COND_WITH_LOG_RETURN(BuffLevel <= 0x000000FF, LogError("buff Level too large: %u, cant larger than 255", BuffLevel), nullptr);
254: BuffIDLevel key;
255: key._.ID = buffID;
256: key._.Level = BuffLevel;
```

### `gameserver/tableload/roleattrconfig.cpp:60` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-tableload-roleattrconfig-cpp-60-assert-7f7af461` |
| 函数 | `RoleAttrConfig::GetSynAttrID` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `GetSynAttrID attrID %d` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/tableload/roleattrconfig.cpp`，关键条件 `GetSynAttrID attrID %d`。 |
| 上下文 | 文件 `gameserver/tableload/roleattrconfig.cpp`，函数 `RoleAttrConfig::GetSynAttrID`，附近日志 `GetSynAttrID attrID %d`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`GetSynAttrID attrID %d`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/tableload/roleattrconfig.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
55: CombatAttrDef RoleAttrConfig::GetSynAttrID(CombatAttrDef attrID, UINT32 count)
56: {
57: if (count > 1)
58: {
59: LogError("GetSynAttrID attrID %d", attrID);
60: ASSERT(false);
61: }
62: AttrDefine::RowData* pRowData = GetAttrDefine(attrID);
63: if (NULL == pRowData) return ATTR_None;
64: if (0 == pRowData->SynClient) return ATTR_None;
65: if (1 == pRowData->SynClient) return attrID;
```

### `gameserver/tableload/scenedropconfig.cpp:60` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-tableload-scenedropconfig-cpp-60-assert-d3694cf5` |
| 函数 | `SceneDropConfig::CheckLoad` |
| 类型 | `config_or_table_missing` |
| 条件 | `it->Drop.size() == it->Combine.size()` |
| 日志/提示 | `-` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/tableload/scenedropconfig.cpp`，关键条件 `it->Drop.size() == it->Combine.size()`。 |
| 上下文 | 文件 `gameserver/tableload/scenedropconfig.cpp`，函数 `SceneDropConfig::CheckLoad`，附近代码 `62: }`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`it->Drop.size() == it->Combine.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/tableload/scenedropconfig.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `it->Drop.size() == it->Combine.size()` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
56: m_dropitem.SetDropList(m_oDropList);
58: for (auto& it : m_oDropList.Table)
59: {
60: ASSERT(it->Drop.size() == it->Combine.size());
61: ASSERT(it->Drop.size() == it->Rates.size());
62: }
64: //m_enemydrop.clear();
65: //m_scenetypedrop.clear();
```

### `gameserver/tableload/scenedropconfig.cpp:61` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-tableload-scenedropconfig-cpp-61-assert-74ca6273` |
| 函数 | `SceneDropConfig::CheckLoad` |
| 类型 | `config_or_table_missing` |
| 条件 | `it->Drop.size() == it->Rates.size()` |
| 日志/提示 | `-` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/tableload/scenedropconfig.cpp`，关键条件 `it->Drop.size() == it->Rates.size()`。 |
| 上下文 | 文件 `gameserver/tableload/scenedropconfig.cpp`，函数 `SceneDropConfig::CheckLoad`，附近代码 `62: }`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`it->Drop.size() == it->Rates.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/tableload/scenedropconfig.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `it->Drop.size() == it->Rates.size()` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
56: m_dropitem.SetDropList(m_oDropList);
58: for (auto& it : m_oDropList.Table)
59: {
60: ASSERT(it->Drop.size() == it->Combine.size());
61: ASSERT(it->Drop.size() == it->Rates.size());
62: }
64: //m_enemydrop.clear();
65: //m_scenetypedrop.clear();
66: m_dropitem.SetDropList(m_oDropList);
```
