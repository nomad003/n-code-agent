---
type: Code Playbook
title: Assert 排障 - gameserver-buff
description: gameserver-buff 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-buff
resource: gameserver/buff/XBuffCommand.cpp, gameserver/buff/XBuffContainer.h, gameserver/buff/XBuffSpecialState.cpp, gameserver/buff/XBuffTrigger.cpp
tags: assert, check, outage_log, crash, gameserver, buff
symbols: XBuffCommandEnterResist::Creator::Creator, XBuffCommandDecResist::Creator::Creator, XBuffContainer::ForEachBuffEffect, XBuffContainer::ForEachBuffEffectStatic, XBuffSpecialState::Creator::Creator, XBuffTrigger::Creator::Creator
logs: Buff %u resist param error: %s, Buff %u invalid resist id: %u, Buff %u addresist param error: %s, Buff %u invalid resist id: %u | Buff %u invalid resist value: %lf, Buff %u invalid resist value: %lf | Buff %u invalid resist id: %u, Buff %u StateParam count error (0 or BuffState's count expected), Buff %u DamageSource %u out of range 16, Buff [%u %u] TriggerRate and TriggerBuff MUST have same count
asserts: CHECK_COND_WITH_LOG, CHECK_COND, assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-buff

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-buff` |
| 条目数 | 10 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/buff/XBuffCommand.cpp:91` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcommand-cpp-91-check_cond_with_log-8cfb3e8c` |
| 函数 | `XBuffCommandEnterResist::Creator::Creator` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `params.size() == 3` |
| 日志/提示 | `Buff %u resist param error: %s` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffCommand.cpp`，关键条件 `Buff %u resist param error: %s`。 |
| 上下文 | 文件 `gameserver/buff/XBuffCommand.cpp`，函数 `XBuffCommandEnterResist::Creator::Creator`，附近日志 `Buff %u resist param error: %s`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`Buff %u resist param error: %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffCommand.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `params.size() == 3` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
87: XBuffCommandEnterResist::Creator::Creator(const XBuffCreateData& data, const std::string& s)
88: {
89: std::vector<UINT32> params;
90: ReadHelper.Parse(const_cast<char*>(s.c_str()), params, ' ');
91: CHECK_COND_WITH_LOG(params.size() == 3, LogError("Buff %u resist param error: %s", data.id, s.c_str()));
93: m_Data.ResistID = params[0];
94: m_Data.Buff[0] = params[1];
95: m_Data.Buff[1] = params[2];
```

### `gameserver/buff/XBuffCommand.cpp:97` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcommand-cpp-97-check_cond_with_log-d6f31ac1` |
| 函数 | `XBuffCommandEnterResist::Creator::Creator` |
| 类型 | `invariant_failed` |
| 条件 | `m_Data.ResistID != 0` |
| 日志/提示 | `Buff %u invalid resist id: %u` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/buff/XBuffCommand.cpp`，关键条件 `Buff %u invalid resist id: %u`。 |
| 上下文 | 文件 `gameserver/buff/XBuffCommand.cpp`，函数 `XBuffCommandEnterResist::Creator::Creator`，附近日志 `Buff %u invalid resist id: %u`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`Buff %u invalid resist id: %u`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffCommand.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_Data.ResistID != 0` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
93: m_Data.ResistID = params[0];
94: m_Data.Buff[0] = params[1];
95: m_Data.Buff[1] = params[2];
97: CHECK_COND_WITH_LOG(m_Data.ResistID != 0, LogError("Buff %u invalid resist id: %u", data.id, m_Data.ResistID));
98: }
100: void XBuffCommandEnterResist::Creator::CreateInstantEffect(const XBuffRealCreateData& data, XBuff* pBuff)
101: {
102: pBuff->GetUnit()->GetStateManager().GetBossResistState().EnterResistState(m_Data.ResistID, pBuff->GetMeta().CasterUID, m_Data.Buff[0], m_Data.Buff[1], pBuff->GetMeta().FromSkill);
```

### `gameserver/buff/XBuffCommand.cpp:116` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcommand-cpp-116-check_cond_with_log-f8d22a25` |
| 函数 | `XBuffCommandDecResist::Creator::Creator` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `params.size() >= 2` |
| 日志/提示 | `Buff %u addresist param error: %s` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffCommand.cpp`，关键条件 `Buff %u addresist param error: %s`。 |
| 上下文 | 文件 `gameserver/buff/XBuffCommand.cpp`，函数 `XBuffCommandDecResist::Creator::Creator`，附近日志 `Buff %u addresist param error: %s`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`Buff %u addresist param error: %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffCommand.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `params.size() >= 2` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
112: XBuffCommandDecResist::Creator::Creator(XBuffCreateData& data, const std::string& s)
113: {
114: std::vector<double> params;
115: ReadHelper.Parse(const_cast<char*>(s.c_str()), params, ' ');
116: CHECK_COND_WITH_LOG(params.size() >= 2, LogError("Buff %u addresist param error: %s", data.id, s.c_str()));
118: m_Data.ResistID = (UINT32)params[0];
119: m_Data.ResistValue = params[1];
120: if (params.size() >= 4)
121: {
```

### `gameserver/buff/XBuffCommand.cpp:126` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcommand-cpp-126-check_cond_with_log-d6f31ac1` |
| 函数 | `XBuffCommandDecResist::Creator::Creator` |
| 类型 | `invariant_failed` |
| 条件 | `m_Data.ResistID != 0` |
| 日志/提示 | `Buff %u invalid resist id: %u \| Buff %u invalid resist value: %lf` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/buff/XBuffCommand.cpp`，关键条件 `Buff %u invalid resist id: %u | Buff %u invalid resist value: %lf`。 |
| 上下文 | 文件 `gameserver/buff/XBuffCommand.cpp`，函数 `XBuffCommandDecResist::Creator::Creator`，附近日志 `Buff %u invalid resist id: %u | Buff %u invalid resist value: %lf`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`Buff %u invalid resist id: %u | Buff %u invalid resist value: %lf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffCommand.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_Data.ResistID != 0` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
121: {
122: m_Data.Buff[0] = (UINT32)params[2];
123: m_Data.Buff[1] = (UINT32)params[3];
124: }
126: CHECK_COND_WITH_LOG(m_Data.ResistID != 0, LogError("Buff %u invalid resist id: %u", data.id, m_Data.ResistID));
127: CHECK_COND_WITH_LOG(m_Data.ResistValue > 0.0, LogError("Buff %u invalid resist value: %lf", data.id, m_Data.ResistValue));
129: data.needCache.calcTypes.insert(EBuffAttrCalcType::CtrlValueDec);
130: }
```

### `gameserver/buff/XBuffCommand.cpp:127` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcommand-cpp-127-check_cond_with_log-b2711e0e` |
| 函数 | `XBuffCommandDecResist::Creator::Creator` |
| 类型 | `invariant_failed` |
| 条件 | `m_Data.ResistValue > 0.0` |
| 日志/提示 | `Buff %u invalid resist value: %lf \| Buff %u invalid resist id: %u` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/buff/XBuffCommand.cpp`，关键条件 `Buff %u invalid resist value: %lf | Buff %u invalid resist id: %u`。 |
| 上下文 | 文件 `gameserver/buff/XBuffCommand.cpp`，函数 `XBuffCommandDecResist::Creator::Creator`，附近日志 `Buff %u invalid resist value: %lf | Buff %u invalid resist id: %u`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`Buff %u invalid resist value: %lf | Buff %u invalid resist id: %u`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffCommand.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_Data.ResistValue > 0.0` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
122: m_Data.Buff[0] = (UINT32)params[2];
123: m_Data.Buff[1] = (UINT32)params[3];
124: }
126: CHECK_COND_WITH_LOG(m_Data.ResistID != 0, LogError("Buff %u invalid resist id: %u", data.id, m_Data.ResistID));
127: CHECK_COND_WITH_LOG(m_Data.ResistValue > 0.0, LogError("Buff %u invalid resist value: %lf", data.id, m_Data.ResistValue));
129: data.needCache.calcTypes.insert(EBuffAttrCalcType::CtrlValueDec);
130: }
132: void XBuffCommandDecResist::Creator::CreateInstantEffect(const XBuffRealCreateData& data, XBuff* pBuff)
```

### `gameserver/buff/XBuffContainer.h:212` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcontainer-h-212-check_cond-47afff0d` |
| 函数 | `XBuffContainer::ForEachBuffEffect` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `XBuffUtility::GetEffectIndex<Effect>() >= 0` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffContainer.h`，关键条件 `XBuffUtility::GetEffectIndex<Effect>() >= 0`。 |
| 上下文 | 文件 `gameserver/buff/XBuffContainer.h`，函数 `XBuffContainer::ForEachBuffEffect`，附近代码 `212: CHECK_COND(XBuffUtility::GetEffectIndex<Effect>() >= 0);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`XBuffUtility::GetEffectIndex<Effect>() >= 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffContainer.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `XBuffUtility::GetEffectIndex<Effect>() >= 0` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
207: template<typename Effect, typename Action, typename ...Args>
208: void XBuffContainer::ForEachBuffEffect(Action act, Args&&... args)
209: {
210: //static_assert(std::is_invocable_r_v<bool, Action, Args&&...);
211: //static_assert(XBuffUtility::Add2EffectStatus<Effect>());
212: CHECK_COND(XBuffUtility::GetEffectIndex<Effect>() >= 0);
214: auto pSet = m_Effects[XBuffUtility::GetEffectIndex<Effect>()];
215: if (!pSet || pSet->empty())
216: return;
217: m_Iterating = true;
```

### `gameserver/buff/XBuffContainer.h:234` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffcontainer-h-234-check_cond-47afff0d` |
| 函数 | `XBuffContainer::ForEachBuffEffectStatic` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `XBuffUtility::GetEffectIndex<Effect>() >= 0` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffContainer.h`，关键条件 `XBuffUtility::GetEffectIndex<Effect>() >= 0`。 |
| 上下文 | 文件 `gameserver/buff/XBuffContainer.h`，函数 `XBuffContainer::ForEachBuffEffectStatic`，附近代码 `234: CHECK_COND(XBuffUtility::GetEffectIndex<Effect>() >= 0);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`XBuffUtility::GetEffectIndex<Effect>() >= 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffContainer.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `XBuffUtility::GetEffectIndex<Effect>() >= 0` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
229: template<typename Effect, typename Action, typename...Args >
230: void XBuffContainer::ForEachBuffEffectStatic(Action act, Args&&... args)
231: {
232: //static_assert(std::is_invocable_r_v<bool, Action, Args&&...);
233: //static_assert(XBuffUtility::Add2EffectStatus<Effect>());
234: CHECK_COND(XBuffUtility::GetEffectIndex<Effect>() >= 0);
236: auto pSet = m_Effects[XBuffUtility::GetEffectIndex<Effect>()];
237: if (!pSet || pSet->empty())
238: return;
239: m_Iterating = true;
```

### `gameserver/buff/XBuffSpecialState.cpp:251` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffspecialstate-cpp-251-check_cond_with_log-373d5f13` |
| 函数 | `XBuffSpecialState::Creator::Creator` |
| 类型 | `config_or_table_missing` |
| 条件 | `pRowData->BuffState.size() == pRowData->StateParam.size() \|\| pRowData->StateParam.size() == 0` |
| 日志/提示 | `Buff %u StateParam count error (0 or BuffState's count expected)` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/buff/XBuffSpecialState.cpp`，关键条件 `Buff %u StateParam count error (0 or BuffState's count expected)`。 |
| 上下文 | 文件 `gameserver/buff/XBuffSpecialState.cpp`，函数 `XBuffSpecialState::Creator::Creator`，附近日志 `Buff %u StateParam count error (0 or BuffState's count expected)`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`Buff %u StateParam count error (0 or BuffState's count expected)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffSpecialState.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `pRowData->BuffState.size() == pRowData->StateParam.size() || pRowData->StateParam.size() == 0` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
246: }
248: XBuffSpecialState::Creator::Creator(const XBuffCreateData& data)
249: {
250: auto pRowData = data.pRowData;
251: CHECK_COND_WITH_LOG(pRowData->BuffState.size() == pRowData->StateParam.size() || pRowData->StateParam.size() == 0, LogError("Buff %u StateParam count error (0 or BuffState's count expected)", data.id));
253: for (uint32_t i = 0; i < pRowData->BuffState.size(); ++i)
254: {
255: uint p = 0;
256: XBuffUtility::GetParam(p, pRowData->StateParam, i);
```

### `gameserver/buff/XBuffSpecialState.cpp:261` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbuffspecialstate-cpp-261-check_cond_with_log-36acd907` |
| 函数 | `XBuffSpecialState::Creator::Creator` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `m_DamageSource <= 16` |
| 日志/提示 | `Buff %u DamageSource %u out of range 16` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffSpecialState.cpp`，关键条件 `Buff %u DamageSource %u out of range 16`。 |
| 上下文 | 文件 `gameserver/buff/XBuffSpecialState.cpp`，函数 `XBuffSpecialState::Creator::Creator`，附近日志 `Buff %u DamageSource %u out of range 16`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`Buff %u DamageSource %u out of range 16`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffSpecialState.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_DamageSource <= 16` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
256: XBuffUtility::GetParam(p, pRowData->StateParam, i);
257: m_States.emplace_back((XBuffState)pRowData->BuffState[i], p);
258: }
259: m_DefenceLevel = pRowData->AttackDefenceLevel[1];
260: m_DamageSource = pRowData->DamageSource;
261: CHECK_COND_WITH_LOG(m_DamageSource <= 16, LogError("Buff %u DamageSource %u out of range 16", data.id, m_DamageSource));
262: }
264: XBuffEffect* XBuffSpecialState::Creator::CreateEffect(const XBuffRealCreateData& data, XBuff* pBuff)
265: {
266: EffectType* pEffect = pBuff->AddEffect<EffectType, true, false, false>();
```

### `gameserver/buff/XBuffTrigger.cpp:150` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-buff-xbufftrigger-cpp-150-assert-2b205569` |
| 函数 | `XBuffTrigger::Creator::Creator` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `false` |
| 日志/提示 | `Buff [%u %u] TriggerRate and TriggerBuff MUST have same count` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/buff/XBuffTrigger.cpp`，关键条件 `Buff [%u %u] TriggerRate and TriggerBuff MUST have same count`。 |
| 上下文 | 文件 `gameserver/buff/XBuffTrigger.cpp`，函数 `XBuffTrigger::Creator::Creator`，附近日志 `Buff [%u %u] TriggerRate and TriggerBuff MUST have same count`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`Buff [%u %u] TriggerRate and TriggerBuff MUST have same count`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/buff/XBuffTrigger.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
145: if (m_Rate.size() > 1)
146: {
147: if (m_Rate.size() != m_TriggerBuff.size())
148: {
149: LogError("Buff [%u %u] TriggerRate and TriggerBuff MUST have same count");
150: assert(false);
151: }
152: }
153: for (const auto& it : pRowData->BuffTriggerLimit)
154: {
155: m_Limits.push_back(it[0]);
```
