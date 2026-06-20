---
type: Code Playbook
title: Assert 排障 - gameserver-combat
description: gameserver-combat 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-combat
resource: gameserver/combat/XCombat.cpp
tags: assert, check, outage_log, crash, gameserver, combat
symbols: XCombat::ChangeBeHitProtectValue, XCombat::ProjectDamage
logs: SkillListForRole.txt hasnot %u, %s, SkillListForPet.txt hasnot %u, %s
asserts: CHECK_COND_RETURN, CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-combat

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-combat` |
| 条目数 | 4 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/combat/XCombat.cpp:158` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-combat-xcombat-cpp-158-check_cond_return-bd177f7a` |
| 函数 | `XCombat::ChangeBeHitProtectValue` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `false` |
| 日志/提示 | `SkillListForRole.txt hasnot %u, %s` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/combat/XCombat.cpp`，关键条件 `SkillListForRole.txt hasnot %u, %s`。 |
| 上下文 | 文件 `gameserver/combat/XCombat.cpp`，函数 `XCombat::ChangeBeHitProtectValue`，附近日志 `SkillListForRole.txt hasnot %u, %s`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`SkillListForRole.txt hasnot %u, %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/combat/XCombat.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
153: {
154: SkillListForRole::RowData* pSkillRowData = SkillListConfig::Instance()->GetRoleSkillConfig((CombatRole*)pCaster, hurtInfo.m_skillId);
155: if (NULL == pSkillRowData)
156: {
157: LogError("SkillListForRole.txt hasnot %u, %s", hurtInfo.m_skillId, SkillListConfig::Instance()->GetSkillName(hurtInfo.m_skillId).c_str());
158: CHECK_COND_RETURN(false, false);
159: }
160: oppoprotectvalue = pSkillRowData->OpponentProtectValue;
161: }
162: else
163: {
```

### `gameserver/combat/XCombat.cpp:172` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-combat-xcombat-cpp-172-check_cond_return-bd177f7a` |
| 函数 | `XCombat::ChangeBeHitProtectValue` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `false` |
| 日志/提示 | `SkillListForPet.txt hasnot %u, %s` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/combat/XCombat.cpp`，关键条件 `SkillListForPet.txt hasnot %u, %s`。 |
| 上下文 | 文件 `gameserver/combat/XCombat.cpp`，函数 `XCombat::ChangeBeHitProtectValue`，附近日志 `SkillListForPet.txt hasnot %u, %s`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`SkillListForPet.txt hasnot %u, %s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/combat/XCombat.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
168: SkillListForPet::RowData* pSkillRowData = SkillListConfig::Instance()->GetPetSkillConfig((CombatEnemy*)pCaster, hurtInfo.m_skillId);
169: if (NULL == pSkillRowData)
170: {
171: LogError("SkillListForPet.txt hasnot %u, %s", hurtInfo.m_skillId, SkillListConfig::Instance()->GetSkillName(hurtInfo.m_skillId).c_str());
172: CHECK_COND_RETURN(false, false);
173: }
174: oppoprotectvalue = pSkillRowData->OpponentProtectValue;
175: }
177: AttributeWatcher oWatcher(pTarget);
```

### `gameserver/combat/XCombat.cpp:430` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-combat-xcombat-cpp-430-check_cond-d2628446` |
| 函数 | `XCombat::ProjectDamage` |
| 类型 | `null_or_missing_object` |
| 条件 | `NULL != pCaster` |
| 日志/提示 | `-` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `gameserver/combat/XCombat.cpp`，关键条件 `NULL != pCaster`。 |
| 上下文 | 文件 `gameserver/combat/XCombat.cpp`，函数 `XCombat::ProjectDamage`，附近代码 `431: CHECK_COND(NULL != pTarget);`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`NULL != pCaster`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/combat/XCombat.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `NULL != pCaster` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
425: void XCombat::ProjectDamage(const HurtInfo &hurtInfo, ProjectDamageResult& result)
426: {
427: CombatUnit *pCaster = hurtInfo.m_caster;
428: CombatUnit* pTarget = hurtInfo.m_target;
430: CHECK_COND(NULL != pCaster);
431: CHECK_COND(NULL != pTarget);
433: //反弹技能特殊处理，替换技能
434: UINT32 dwSkillID_Ori = hurtInfo.m_skillId;
435: UINT32 dwHitPoint_Ori = hurtInfo.m_hitpoint;
```

### `gameserver/combat/XCombat.cpp:431` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-combat-xcombat-cpp-431-check_cond-3b27b248` |
| 函数 | `XCombat::ProjectDamage` |
| 类型 | `null_or_missing_object` |
| 条件 | `NULL != pTarget` |
| 日志/提示 | `-` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `gameserver/combat/XCombat.cpp`，关键条件 `NULL != pTarget`。 |
| 上下文 | 文件 `gameserver/combat/XCombat.cpp`，函数 `XCombat::ProjectDamage`，附近代码 `433: //反弹技能特殊处理，替换技能`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`NULL != pTarget`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/combat/XCombat.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `NULL != pTarget` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
426: {
427: CombatUnit *pCaster = hurtInfo.m_caster;
428: CombatUnit* pTarget = hurtInfo.m_target;
430: CHECK_COND(NULL != pCaster);
431: CHECK_COND(NULL != pTarget);
433: //反弹技能特殊处理，替换技能
434: UINT32 dwSkillID_Ori = hurtInfo.m_skillId;
435: UINT32 dwHitPoint_Ori = hurtInfo.m_hitpoint;
436: if (hurtInfo.m_isParry)
```
