---
type: Code Playbook
title: Assert 排障 - gameserver-unit-unit-cpp
description: gameserver-unit-unit-cpp 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-unit-cpp
resource: gameserver/unit/unit.cpp
tags: assert, check, outage_log, crash, gameserver, unit, unit, cpp
symbols: CombatUnit::EnterScene, CombatUnit::SetPosition, CombatUnit::GetAttr, CombatUnit::SetAttr, CombatUnit::AddAttr
logs: unit:%llu enter scene NULL | unit: %llu-%u has in scene: [%llu %d]
asserts: CHECK_COND_NORETURN, CHECK_COND, CHECK_COND_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-unit-cpp

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-unit-cpp` |
| 条目数 | 5 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/unit.cpp:241` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-unit-cpp-241-check_cond_noreturn-5e07ae03` |
| 函数 | `CombatUnit::EnterScene` |
| 类型 | `null_or_missing_object` |
| 条件 | `false` |
| 日志/提示 | `unit:%llu enter scene NULL \| unit: %llu-%u has in scene: [%llu %d]` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `gameserver/unit/unit.cpp`，关键条件 `unit:%llu enter scene NULL | unit: %llu-%u has in scene: [%llu %d]`。 |
| 上下文 | 文件 `gameserver/unit/unit.cpp`，函数 `CombatUnit::EnterScene`，附近日志 `unit:%llu enter scene NULL | unit: %llu-%u has in scene: [%llu %d]`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`unit:%llu enter scene NULL | unit: %llu-%u has in scene: [%llu %d]`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/unit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
237: //1. check
238: if (NULL == scene)
239: {
240: LogError("unit:%llu enter scene NULL", GetID());
241: CHECK_COND_NORETURN(false);
242: return false;
243: }
244: if (GetCurrScene() == scene)
245: {
246: LogError("unit: %llu-%u has in scene: [%llu %d]", GetID(), GetTemplateID(), scene->GetSceneUID(), scene->GetSceneID());
```

### `gameserver/unit/unit.cpp:603` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-unit-cpp-603-check_cond-dc8f9532` |
| 函数 | `CombatUnit::SetPosition` |
| 类型 | `numeric_or_position_invalid` |
| 条件 | `x > -FLT_EPSILON && y > -FLT_EPSILON && z > -FLT_EPSILON` |
| 日志/提示 | `-` |
| 对应问题 | 坐标、比例或数值非法，可能是负坐标、NaN、0 比例或物理数据异常。 触发点 `gameserver/unit/unit.cpp`，关键条件 `x > -FLT_EPSILON && y > -FLT_EPSILON && z > -FLT_EPSILON`。 |
| 上下文 | 文件 `gameserver/unit/unit.cpp`，函数 `CombatUnit::SetPosition`，附近代码 `604: if(IsPlat())`。 |
| 为什么出问题 | 上游传入非法数值，常见是坐标未初始化、比例为 0、NaN 或负值。 直接线索：`x > -FLT_EPSILON && y > -FLT_EPSILON && z > -FLT_EPSILON`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/unit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `x > -FLT_EPSILON && y > -FLT_EPSILON && z > -FLT_EPSILON` 由谁赋值或返回。
- 打印上游坐标/比例/向量来源，检查初始化、单位转换和物理碰撞数据。
- 修正非法数据源；对外部输入增加范围校验。

附近代码：

```text
598: return xecs::getPosition_ecs(this->m_uEcsID);
599: }
601: void CombatUnit::SetPosition(float x, float y, float z)
602: {
603: CHECK_COND(x > -FLT_EPSILON && y > -FLT_EPSILON && z > -FLT_EPSILON);
604: if(IsPlat())
605: {
606: ((PlatEntity*)this)->RecordPosInLastFrame();
607: }
608: xecs::setPosition(this->m_uID, x, y, z);
```

### `gameserver/unit/unit.cpp:700` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-unit-cpp-700-check_cond_return-6e5b0268` |
| 函数 | `CombatUnit::GetAttr` |
| 类型 | `precondition_failed` |
| 条件 | `AttributeDefInfo::IsAttrIDValid(attrID)` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/unit/unit.cpp`，关键条件 `AttributeDefInfo::IsAttrIDValid(attrID)`。 |
| 上下文 | 文件 `gameserver/unit/unit.cpp`，函数 `CombatUnit::GetAttr`，附近代码 `702: double value = 0;`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`AttributeDefInfo::IsAttrIDValid(attrID)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/unit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `AttributeDefInfo::IsAttrIDValid(attrID)` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
695: return mUnitCombatAttribute.GetAttr(attrID);
696: }
698: double CombatUnit::GetAttr(CombatAttrDef attrID)
699: {
700: CHECK_COND_RETURN(AttributeDefInfo::IsAttrIDValid(attrID), 0);
702: double value = 0;
703: if (0 != AttributeDefInfo::GetIndexAttrByRoleMax(attrID))
704: {
705: value = GetMaxAttrInMultiUnit(attrID);
```

### `gameserver/unit/unit.cpp:716` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-unit-cpp-716-check_cond-c54f69d4` |
| 函数 | `CombatUnit::SetAttr` |
| 类型 | `invariant_failed` |
| 条件 | `AttributeDefInfo::IsAttrIDValid(attrID)` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/unit.cpp`，关键条件 `AttributeDefInfo::IsAttrIDValid(attrID)`。 |
| 上下文 | 文件 `gameserver/unit/unit.cpp`，函数 `CombatUnit::SetAttr`，附近代码 `718: if (IsStateAttr(attrID))`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`AttributeDefInfo::IsAttrIDValid(attrID)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/unit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `AttributeDefInfo::IsAttrIDValid(attrID)` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
711: return value;
712: }
714: void CombatUnit::SetAttr(CombatAttrDef attrID, double value, bool bSuppressLog)
715: {
716: CHECK_COND(AttributeDefInfo::IsAttrIDValid(attrID));
718: if (IsStateAttr(attrID))
719: {
720: GetStateManager().AddStateAttrValue(attrID, value - GetAttr(attrID));
721: }
```

### `gameserver/unit/unit.cpp:741` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-unit-cpp-741-check_cond-c54f69d4` |
| 函数 | `CombatUnit::AddAttr` |
| 类型 | `invariant_failed` |
| 条件 | `AttributeDefInfo::IsAttrIDValid(attrID)` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/unit.cpp`，关键条件 `AttributeDefInfo::IsAttrIDValid(attrID)`。 |
| 上下文 | 文件 `gameserver/unit/unit.cpp`，函数 `CombatUnit::AddAttr`，附近代码 `743: if (IsStateAttr(attrID))`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`AttributeDefInfo::IsAttrIDValid(attrID)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/unit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `AttributeDefInfo::IsAttrIDValid(attrID)` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
736: }
737: }
739: void CombatUnit::AddAttr(CombatAttrDef attrID, double value, bool bSuppressLog)
740: {
741: CHECK_COND(AttributeDefInfo::IsAttrIDValid(attrID));
743: if (IsStateAttr(attrID))
744: {
745: GetStateManager().AddStateAttrValue(attrID, value);
746: }
```
