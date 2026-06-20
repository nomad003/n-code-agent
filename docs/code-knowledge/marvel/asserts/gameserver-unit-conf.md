---
type: Code Playbook
title: Assert 排障 - gameserver-unit-conf
description: gameserver-unit-conf 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-conf
resource: gameserver/unit/conf/unitconf.cpp
tags: assert, check, outage_log, crash, gameserver, unit, conf
symbols: UnitConf::InitFromTemplate, UnitConf::InitFromPresent
logs: can't find monster template id [%u]
asserts: CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-conf

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-conf` |
| 条目数 | 2 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/conf/unitconf.cpp:21` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-conf-unitconf-cpp-21-check_cond_noreturn-5e07ae03` |
| 函数 | `UnitConf::InitFromTemplate` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `can't find monster template id [%u]` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/conf/unitconf.cpp`，关键条件 `can't find monster template id [%u]`。 |
| 上下文 | 文件 `gameserver/unit/conf/unitconf.cpp`，函数 `UnitConf::InitFromTemplate`，附近日志 `can't find monster template id [%u]`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`can't find monster template id [%u]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/conf/unitconf.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
16: {
17: auto conf = const_cast<XEntityStatistics::RowData*>(XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(template_id));
18: if (conf == nullptr)
19: {
20: LogError("can't find monster template id [%u]", template_id);
21: CHECK_COND_NORETURN(false);
22: return;
23: }
24: template_conf_ = conf;
26: GetPhysConf().InitFromTemplate(conf);
```

### `gameserver/unit/conf/unitconf.cpp:34` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-conf-unitconf-cpp-34-check_cond_noreturn-5e07ae03` |
| 函数 | `UnitConf::InitFromPresent` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/conf/unitconf.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/unit/conf/unitconf.cpp`，函数 `UnitConf::InitFromPresent`，附近代码 `34: CHECK_COND_NORETURN(false);`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/conf/unitconf.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
29: void UnitConf::InitFromPresent(UINT32 present_id)
30: {
31: const XEntityPresentation::RowData* data = XEntityInfoLibrary::Instance()->GetXEntityPresentationRow(present_id);
32: if (NULL == data)
33: {
34: CHECK_COND_NORETURN(false);
35: }
36: else
37: {
38: present_conf_ = const_cast<XEntityPresentation::RowData*>(data);
```
