---
type: Code Playbook
title: Assert 排障 - gameserver-unit-state
description: gameserver-unit-state 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-state
resource: gameserver/unit/state/StateManager.cpp, gameserver/unit/state/StateResist.cpp, gameserver/unit/state/StateStage.cpp
tags: assert, check, outage_log, crash, gameserver, unit, state
symbols: StateManager::ProjectDamage, StateManager::GetEnemyCurrentSkillRowData, BossResistState::setUnit, BossResistState::ProjectDamage, BossStage::SetHpODIndex, BossStage::GetHpODIndex
logs:
asserts: CHECK_COND, CHECK_COND_RETURN, ASSERT
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-state

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-state` |
| 条目数 | 7 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/state/StateManager.cpp:124` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-statemanager-cpp-124-check_cond-79e06ffd` |
| 函数 | `StateManager::ProjectDamage` |
| 类型 | `null_or_missing_object` |
| 条件 | `NULL != mpUnit` |
| 日志/提示 | `-` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `gameserver/unit/state/StateManager.cpp`，关键条件 `NULL != mpUnit`。 |
| 上下文 | 文件 `gameserver/unit/state/StateManager.cpp`，函数 `StateManager::ProjectDamage`，附近代码 `126: if (NULL == pHurtInfo) return;`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`NULL != mpUnit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateManager.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `NULL != mpUnit` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
119: }
120: }
122: void StateManager::ProjectDamage(const HurtInfo* pHurtInfo, ProjectDamageResult* pResult, const SkillEffect* pSklEff)
123: {
124: CHECK_COND(NULL != mpUnit);
126: if (NULL == pHurtInfo) return;
127: if (NULL == pHurtInfo->m_caster) return;
128: if (IsSceneStop()) return;
```

### `gameserver/unit/state/StateManager.cpp:470` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-statemanager-cpp-470-check_cond_return-4e7a0cac` |
| 函数 | `StateManager::GetEnemyCurrentSkillRowData` |
| 类型 | `config_or_table_missing` |
| 条件 | `NULL != pCurrentSkillRowData` |
| 日志/提示 | `-` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/state/StateManager.cpp`，关键条件 `NULL != pCurrentSkillRowData`。 |
| 上下文 | 文件 `gameserver/unit/state/StateManager.cpp`，函数 `StateManager::GetEnemyCurrentSkillRowData`，附近代码 `470: CHECK_COND_RETURN(NULL != pCurrentSkillRowData, NULL);`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`NULL != pCurrentSkillRowData`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateManager.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `NULL != pCurrentSkillRowData` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
465: {
466: if (!mpUnit->IsEnemy()) return NULL;
467: UINT32 currentskillid = xecs::getCurSkill(mpUnit->GetID());
468: if (0 == currentskillid) return NULL;
469: SkillListForEnemy::RowData* pCurrentSkillRowData = mpUnit->GetSkillMgr().GetEnemySkillConf(currentskillid);
470: CHECK_COND_RETURN(NULL != pCurrentSkillRowData, NULL);
472: return pCurrentSkillRowData;
473: }
475: void StateManager::OnStartSkill(UINT32 skillid)
```

### `gameserver/unit/state/StateResist.cpp:49` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-stateresist-cpp-49-check_cond-beceb208` |
| 函数 | `BossResistState::setUnit` |
| 类型 | `null_or_missing_object` |
| 条件 | `NULL != pUnit` |
| 日志/提示 | `-` |
| 对应问题 | 关键对象为空或未创建，后续逻辑无法继续。 触发点 `gameserver/unit/state/StateResist.cpp`，关键条件 `NULL != pUnit`。 |
| 上下文 | 文件 `gameserver/unit/state/StateResist.cpp`，函数 `BossResistState::setUnit`，附近代码 `51: if (pUnit->IsRole())`。 |
| 为什么出问题 | 调用链传入了空指针，或对象生命周期/创建流程没有完成。 直接线索：`NULL != pUnit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateResist.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `NULL != pUnit` 由谁赋值或返回。
- 沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。
- 补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。

附近代码：

```text
44: m_dwCurrBuffID = 0;
45: }
47: void BossResistState::setUnit(CombatUnit* pUnit)
48: {
49: CHECK_COND(NULL != pUnit);
51: if (pUnit->IsRole())
52: {
53: CombatRole* pCombatRole = static_cast<CombatRole*>(pUnit);
54: const PartnerBattleTable::RowData* pPartnerRowData = PartnerConfig::Instance()->GetPartnerBattleTableRow(pCombatRole->GetPartnerId());
```

### `gameserver/unit/state/StateResist.cpp:120` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-stateresist-cpp-120-check_cond-ffc67c8a` |
| 函数 | `BossResistState::ProjectDamage` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/unit/state/StateResist.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/unit/state/StateResist.cpp`，函数 `BossResistState::ProjectDamage`，附近代码 `120: CHECK_COND(false);`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateResist.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
115: case ESkillCasterType::Pet:
116: {
117: const SkillListForRole::RowData* pSkillRowData = pSklEff->m_poRoleSkillRow;
118: if (NULL == pSkillRowData)
119: {
120: CHECK_COND(false);
121: return;
122: }
124: dwBuffID = pSkillRowData->ResistBuff[0];
125: dwBuffLevel = pSkillRowData->ResistBuff[1];
```

### `gameserver/unit/state/StateResist.cpp:144` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-stateresist-cpp-144-check_cond-ffc67c8a` |
| 函数 | `BossResistState::ProjectDamage` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/unit/state/StateResist.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/unit/state/StateResist.cpp`，函数 `BossResistState::ProjectDamage`，附近代码 `144: CHECK_COND(false);`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateResist.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
139: case ESkillCasterType::Enemy:
140: {
141: const SkillListForEnemy::RowData* pSkillRowData = pSklEff->m_poEnemySkillRow;
142: if (NULL == pSkillRowData)
143: {
144: CHECK_COND(false);
145: return;
146: }
148: dwBuffID = pSkillRowData->ResistBuff[0];
149: dwBuffLevel = pSkillRowData->ResistBuff[1];
```

### `gameserver/unit/state/StateStage.cpp:240` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-statestage-cpp-240-assert-580fdade` |
| 函数 | `BossStage::SetHpODIndex` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `index < 64` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/state/StateStage.cpp`，关键条件 `index < 64`。 |
| 上下文 | 文件 `gameserver/unit/state/StateStage.cpp`，函数 `BossStage::SetHpODIndex`，附近代码 `241: m_qwStageBits |= ((UINT64)1 << index);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`index < 64`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateStage.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `index < 64` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
235: return m_oDelayData.m_bDelayed;
236: }
238: void BossStage::SetHpODIndex(UINT32 index)
239: {
240: ASSERT(index < 64);
241: m_qwStageBits |= ((UINT64)1 << index);
242: }
244: bool BossStage::GetHpODIndex(INT32 index) const
245: {
```

### `gameserver/unit/state/StateStage.cpp:246` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-state-statestage-cpp-246-assert-580fdade` |
| 函数 | `BossStage::GetHpODIndex` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `index < 64` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/state/StateStage.cpp`，关键条件 `index < 64`。 |
| 上下文 | 文件 `gameserver/unit/state/StateStage.cpp`，函数 `BossStage::GetHpODIndex`，附近代码 `247: return 0 != (m_qwStageBits & ((UINT64)1 << index));`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`index < 64`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/state/StateStage.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `index < 64` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
241: m_qwStageBits |= ((UINT64)1 << index);
242: }
244: bool BossStage::GetHpODIndex(INT32 index) const
245: {
246: ASSERT(index < 64);
247: return 0 != (m_qwStageBits & ((UINT64)1 << index));
248: }
250: UINT32 BossStage::CheckHpODIndex(const vector<uint>& HpEnterOD, double hppercent)
251: {
```
