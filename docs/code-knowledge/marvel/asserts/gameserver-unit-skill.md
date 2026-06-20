---
type: Code Playbook
title: Assert 排障 - gameserver-unit-skill
description: gameserver-unit-skill 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-skill
resource: gameserver/unit/skill/skillcore.cpp, gameserver/unit/skill/skillmgr.cpp
tags: assert, check, outage_log, crash, gameserver, unit, skill
symbols: SkillCore::InitEnemySkill, SkillCore::InitRoleSkill, SkillCore::InitSpawnSkill, SkillMgr::GetSkillLevel
logs: caster:%u skill:[%u %s] not find in conf, skillpartner:%u skill:[%u-%u %s] not find in conf, skill:[%u-%u %s] not find in conf, not find skillid
asserts: CHECK_COND, CHECK_COND_WITH_LOG_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-skill

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-skill` |
| 条目数 | 4 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/skill/skillcore.cpp:81` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-skill-skillcore-cpp-81-check_cond-ffc67c8a` |
| 函数 | `SkillCore::InitEnemySkill` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `caster:%u skill:[%u %s] not find in conf` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/skill/skillcore.cpp`，关键条件 `caster:%u skill:[%u %s] not find in conf`。 |
| 上下文 | 文件 `gameserver/unit/skill/skillcore.cpp`，函数 `SkillCore::InitEnemySkill`，附近日志 `caster:%u skill:[%u %s] not find in conf`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`caster:%u skill:[%u %s] not find in conf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/skill/skillcore.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
76: const std::string& skill_name = SkillConfig::Instance()->GetSkillName(skillid);
77: pSkillListForEnemy = SkillConfig::Instance()->GetEnemySkillConfigX(skillid, casterTypeID);
78: if (NULL == pSkillListForEnemy)
79: {
80: UnitLogErr(pUnit, "caster:%u skill:[%u %s] not find in conf", casterTypeID, skillid, skill_name.c_str());
81: CHECK_COND(false);
82: return;
83: }
85: ID = skillid;
86: Level = 1;
```

### `gameserver/unit/skill/skillcore.cpp:100` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-skill-skillcore-cpp-100-check_cond-ffc67c8a` |
| 函数 | `SkillCore::InitRoleSkill` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `skillpartner:%u skill:[%u-%u %s] not find in conf` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/skill/skillcore.cpp`，关键条件 `skillpartner:%u skill:[%u-%u %s] not find in conf`。 |
| 上下文 | 文件 `gameserver/unit/skill/skillcore.cpp`，函数 `SkillCore::InitRoleSkill`，附近日志 `skillpartner:%u skill:[%u-%u %s] not find in conf`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`skillpartner:%u skill:[%u-%u %s] not find in conf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/skill/skillcore.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
95: UINT32 skill_partner = pUnit->GetSkillMgr().GetSkillTemplateId();
96: pSkillListForRole = SkillConfig::Instance()->GetRoleSkillConfigX(skillid, skilllevel, skill_partner);
97: if (NULL == pSkillListForRole)
98: {
99: UnitLogErr(pUnit, "skillpartner:%u skill:[%u-%u %s] not find in conf", skill_partner, skillid, skilllevel, skill_name.c_str());
100: CHECK_COND(false);
101: return;
102: }
104: ID = skillid;
105: Level = skilllevel;
```

### `gameserver/unit/skill/skillcore.cpp:118` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-skill-skillcore-cpp-118-check_cond-ffc67c8a` |
| 函数 | `SkillCore::InitSpawnSkill` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `skill:[%u-%u %s] not find in conf` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/skill/skillcore.cpp`，关键条件 `skill:[%u-%u %s] not find in conf`。 |
| 上下文 | 文件 `gameserver/unit/skill/skillcore.cpp`，函数 `SkillCore::InitSpawnSkill`，附近日志 `skill:[%u-%u %s] not find in conf`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`skill:[%u-%u %s] not find in conf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/skill/skillcore.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
113: const std::string& skill_name = SkillConfig::Instance()->GetSkillName(skillid);
114: pSkillListForSpawn = SkillConfig::Instance()->GetSpawnSkillConfigX(skillid, skilllevel);
115: if (NULL == pSkillListForSpawn)
116: {
117: UnitLogErr(pUnit, "skill:[%u-%u %s] not find in conf", skillid, skilllevel, skill_name.c_str());
118: CHECK_COND(false);
119: return;
120: }
122: ID = skillid;
123: Level = skilllevel;
```

### `gameserver/unit/skill/skillmgr.cpp:527` `CHECK_COND_WITH_LOG_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-skill-skillmgr-cpp-527-check_cond_with_log_return-f37b4200` |
| 函数 | `SkillMgr::GetSkillLevel` |
| 类型 | `config_or_table_missing` |
| 条件 | `nullptr != core` |
| 日志/提示 | `not find skillid` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/skill/skillmgr.cpp`，关键条件 `not find skillid`。 |
| 上下文 | 文件 `gameserver/unit/skill/skillmgr.cpp`，函数 `SkillMgr::GetSkillLevel`，附近日志 `not find skillid`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`not find skillid`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/skill/skillmgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `nullptr != core` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
522: {
523: SkillCore* core = FindSkillCore(skillhashid);
525: if (is_assert)
526: {
527: CHECK_COND_WITH_LOG_RETURN(nullptr != core, "not find skillid", 0);
528: }
529: return nullptr == core ? 0 : core->Level;
530: }
532: bool SkillMgr::IsValidSkill(UINT32 skillid)
```
