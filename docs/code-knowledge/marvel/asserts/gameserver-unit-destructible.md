---
type: Code Playbook
title: Assert 排障 - gameserver-unit-destructible
description: gameserver-unit-destructible 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-destructible
resource: gameserver/unit/destructible/destructiblegroups.cpp, gameserver/unit/destructible/destructibleunit.cpp
tags: assert, check, outage_log, crash, gameserver, unit, destructible
symbols: DestructibleGroups::CreateDestructibleById, DestructibleGroups::CreateNewDestructibleImpl_, DestructibleGroups::CreateNewDestructible_, DestructibleSettings::LoadFromJson, DestructibleUnit::Init, DestructibleUnit::InitDestructibleOutlook, DestructibleUnit::AddColliderToScene, CreateShapesFromColliders
logs: [DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt, [DESTRUCTIBLE]load colliders from file:%s failed, [DESTRUCTIBLE]create actor from colliders file:%s failed
asserts: CHECK_COND_RETURN, CHECK_COND_WITH_LOG_RETURN, CHECK_COND, CHECK_COND_WITH_LOG
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-destructible

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-destructible` |
| 条目数 | 11 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/destructible/destructiblegroups.cpp:153` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructiblegroups-cpp-153-check_cond_return-aae4466c` |
| 函数 | `DestructibleGroups::CreateDestructibleById` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `state` |
| 日志/提示 | `-` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/unit/destructible/destructiblegroups.cpp`，关键条件 `state`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructiblegroups.cpp`，函数 `DestructibleGroups::CreateDestructibleById`，附近代码 `154: if (state->IsAlive())`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`state`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructiblegroups.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `state` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
148: }
150: DestructibleUnit* DestructibleGroups::CreateDestructibleById(DestructibleGroupId groupId, DestructibleId id, const xecs::Vector3* overridePos, const float* overrideFace)
151: {
152: DestructibleState* state = GetDestructibleStateById(groupId, id);
153: CHECK_COND_RETURN(state, NULL);
154: if (state->IsAlive())
155: return state->unit;
157: state->unit = CreateNewDestructible_(&state->settings, overridePos, overrideFace);
158: return state->unit;
```

### `gameserver/unit/destructible/destructiblegroups.cpp:220` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructiblegroups-cpp-220-check_cond_return-0e773915` |
| 函数 | `DestructibleGroups::CreateNewDestructibleImpl_` |
| 类型 | `precondition_failed` |
| 条件 | `unit->IsDestructible()` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/unit/destructible/destructiblegroups.cpp`，关键条件 `unit->IsDestructible()`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructiblegroups.cpp`，函数 `DestructibleGroups::CreateNewDestructibleImpl_`，附近代码 `222: unit->SetHostLevel(level ? level->GetUID() : 0);`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`unit->IsDestructible()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructiblegroups.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit->IsDestructible()` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
216: CombatEnemy* unit = (CombatEnemy*)scene->GetSceneUnitHandler().CreateDestructible(settings, scene,
217: overridePos ? *overridePos : mobPos,
218: overrideFace ? *overrideFace : mobFace
219: );
220: CHECK_COND_RETURN(unit->IsDestructible(), NULL);
222: unit->SetHostLevel(level ? level->GetUID() : 0);
224: unit->EnterScene(scene);
225: UnitLogInf(unit, "[DESTRUCTIBLE] created id[%u]", settings->id);
```

### `gameserver/unit/destructible/destructiblegroups.cpp:232` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructiblegroups-cpp-232-check_cond_return-4487d78b` |
| 函数 | `DestructibleGroups::CreateNewDestructible_` |
| 类型 | `precondition_failed` |
| 条件 | `m_level && m_level->GetSpawner() && settings` |
| 日志/提示 | `-` |
| 对应问题 | 函数前置条件失败，当前调用参数或对象状态不满足要求。 触发点 `gameserver/unit/destructible/destructiblegroups.cpp`，关键条件 `m_level && m_level->GetSpawner() && settings`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructiblegroups.cpp`，函数 `DestructibleGroups::CreateNewDestructible_`，附近代码 `233: SceneBattle* scene = m_level->GetSpawner()->GetScene();`。 |
| 为什么出问题 | 调用方没有满足函数入口约束，宏通常会提前返回。 直接线索：`m_level && m_level->GetSpawner() && settings`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructiblegroups.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_level && m_level->GetSpawner() && settings` 由谁赋值或返回。
- 检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。
- 如果是可恢复错误，补充上游日志并返回明确错误码。

附近代码：

```text
227: return (DestructibleUnit*)unit;
228: }
230: DestructibleUnit* DestructibleGroups::CreateNewDestructible_(const DestructibleSettings* settings, const xecs::Vector3* overridePos, const float* overrideFace)
231: {
232: CHECK_COND_RETURN(m_level && m_level->GetSpawner() && settings, NULL);
233: SceneBattle* scene = m_level->GetSpawner()->GetScene();
234: return CreateNewDestructibleImpl_(scene, m_level, settings, overridePos, overrideFace);
235: }
237: void DestructibleGroups::OnDestructed(DestructibleGroupId groupId, DestructibleId id, DestructibleUnit* unit, CombatUnit* killerUnit, bool triggerLevelExstring, bool drop, DestructReason reason)
```

### `gameserver/unit/destructible/destructibleunit.cpp:119` `CHECK_COND_WITH_LOG_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-119-check_cond_with_log_return-3c7e106e` |
| 函数 | `DestructibleSettings::LoadFromJson` |
| 类型 | `config_or_table_missing` |
| 条件 | `row` |
| 日志/提示 | `[DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `[DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleSettings::LoadFromJson`，附近日志 `[DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`[DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `row` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
114: {
115: id = jsonValue.FindMember("id")->value.GetUint();
116: groupId = group;
117: UINT32 templateID = jsonValue.FindMember("templateID")->value.GetUint();
118: auto* row = LevelConfig::Instance()->GetDestructibleObjectTableRow(templateID);
119: CHECK_COND_WITH_LOG_RETURN(row, LogError("[DESTRUCTIBLE] id[%u] templateID[%u] not found in DestructibleObject.txt", id, templateID), false);
121: if (jsonValue.HasMember("levelExstringOnDestructed"))
122: {
123: const auto& s = jsonValue.FindMember("levelExstringOnDestructed")->value;
124: levelExstringOnDestructed = { s.GetString(), s.GetStringLength() };
```

### `gameserver/unit/destructible/destructibleunit.cpp:214` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-214-check_cond-e85fc59d` |
| 函数 | `DestructibleUnit::Init` |
| 类型 | `invariant_failed` |
| 条件 | `settings && scene` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `settings && scene`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleUnit::Init`，附近代码 `214: CHECK_COND(settings && scene);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`settings && scene`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `settings && scene` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
209: // Compare to other units, destructibles use another table `DestructibleObject.txt` for configuration,
210: // some fields for common use may be overrided by that table,
211: // so the following initialization code may be a little different to `CombatEnemy::Init`.
212: void DestructibleUnit::Init(const DestructibleSettings* settings, Scene* scene, const xecs::Vector3& pos, float face)
213: {
214: CHECK_COND(settings && scene);
215: const auto& presentationStages = settings->overrideTable.PresentationStages;
216: CHECK_COND(presentationStages.size() > 0);
217: const XEntityStatistics::RowData* conf = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(DestructibleUnit::STATISTICS_ID);
218: CHECK_COND(conf);
```

### `gameserver/unit/destructible/destructibleunit.cpp:216` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-216-check_cond-9c7eb8e9` |
| 函数 | `DestructibleUnit::Init` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `presentationStages.size() > 0` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `presentationStages.size() > 0`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleUnit::Init`，附近代码 `216: CHECK_COND(presentationStages.size() > 0);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`presentationStages.size() > 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `presentationStages.size() > 0` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
211: // so the following initialization code may be a little different to `CombatEnemy::Init`.
212: void DestructibleUnit::Init(const DestructibleSettings* settings, Scene* scene, const xecs::Vector3& pos, float face)
213: {
214: CHECK_COND(settings && scene);
215: const auto& presentationStages = settings->overrideTable.PresentationStages;
216: CHECK_COND(presentationStages.size() > 0);
217: const XEntityStatistics::RowData* conf = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(DestructibleUnit::STATISTICS_ID);
218: CHECK_COND(conf);
220: //****** basic init begin ******
221: m_settings = settings;
```

### `gameserver/unit/destructible/destructibleunit.cpp:218` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-218-check_cond-4cf612c4` |
| 函数 | `DestructibleUnit::Init` |
| 类型 | `config_or_table_missing` |
| 条件 | `conf` |
| 日志/提示 | `-` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `conf`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleUnit::Init`，附近代码 `218: CHECK_COND(conf);`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`conf`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `conf` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
213: {
214: CHECK_COND(settings && scene);
215: const auto& presentationStages = settings->overrideTable.PresentationStages;
216: CHECK_COND(presentationStages.size() > 0);
217: const XEntityStatistics::RowData* conf = XEntityInfoLibrary::Instance()->GetXEntityStatisticsRow(DestructibleUnit::STATISTICS_ID);
218: CHECK_COND(conf);
220: //****** basic init begin ******
221: m_settings = settings;
222: m_stage = 0;
223: m_uTemplateID = STATISTICS_ID;
```

### `gameserver/unit/destructible/destructibleunit.cpp:281` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-281-check_cond-9a99b91e` |
| 函数 | `DestructibleUnit::InitDestructibleOutlook` |
| 类型 | `invariant_failed` |
| 条件 | `outlook && settings` |
| 日志/提示 | `-` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `outlook && settings`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleUnit::InitDestructibleOutlook`，附近代码 `283: outlook->set_id(settings->id);`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`outlook && settings`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `outlook && settings` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
276: UnitLogInf(this, "ecs:%llu move:%u pos:[%.03f %.03f %.03f] init [%p]", GetEcsID(), move_type, pos.x, pos.y, pos.z, this);
277: }
279: void DestructibleUnit::InitDestructibleOutlook(KKSG::DestructibleOutLook* outlook, const DestructibleSettings* settings)
280: {
281: CHECK_COND(outlook && settings);
283: outlook->set_id(settings->id);
284: outlook->set_templateid(settings->overrideTable.TemplateID);
286: auto* rotationWithoutY = outlook->mutable_rotationwithouty();
```

### `gameserver/unit/destructible/destructibleunit.cpp:535` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-535-check_cond_with_log-4e015dc6` |
| 函数 | `DestructibleUnit::AddColliderToScene` |
| 类型 | `invariant_failed` |
| 条件 | `collidersData` |
| 日志/提示 | `[DESTRUCTIBLE]load colliders from file:%s failed` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `[DESTRUCTIBLE]load colliders from file:%s failed`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `DestructibleUnit::AddColliderToScene`，附近日志 `[DESTRUCTIBLE]load colliders from file:%s failed`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`[DESTRUCTIBLE]load colliders from file:%s failed`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `collidersData` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
531: BindToPlat(this, plat);
533: const std::string& collidersPath = SceneConfig::Instance()->GetBlockPath(GetConf().GetPresentConf()->BlockFilePath, true);
534: const SharedCollidersData* collidersData = PhysicsWorld::Instance()->GetCollidersFromFile(FrameWork::GetConfig().GetFilePath(collidersPath.c_str(), SERVER_DIR_ROOT));
535: CHECK_COND_WITH_LOG(collidersData, LogError("[DESTRUCTIBLE]load colliders from file:%s failed", collidersPath.c_str()));
537: const xecs::Vector3 localPos = pos - plat->GetPosition();
538: const float localFace = face - plat->GetFaceDegree();
539: const physx::PxTransform localPose(physx::PxVec3(localPos.x, localPos.y, localPos.z), FaceToPxQuat(localFace) * m_settings->rotWithoutY);
```

### `gameserver/unit/destructible/destructibleunit.cpp:578` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-578-check_cond_with_log-4e015dc6` |
| 函数 | `CreateShapesFromColliders` |
| 类型 | `invariant_failed` |
| 条件 | `collidersData` |
| 日志/提示 | `[DESTRUCTIBLE]load colliders from file:%s failed` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `[DESTRUCTIBLE]load colliders from file:%s failed`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `CreateShapesFromColliders`，附近日志 `[DESTRUCTIBLE]load colliders from file:%s failed`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`[DESTRUCTIBLE]load colliders from file:%s failed`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `collidersData` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
573: PhysicsScene* physicsScene = static_cast<PhysicsScene*>(scene->GetSceneQuery());
574: if (!physicsScene->GetPxScene()) return;
576: const std::string& collidersPath = SceneConfig::Instance()->GetBlockPath(GetConf().GetPresentConf()->BlockFilePath, true);
577: const SharedCollidersData* collidersData = PhysicsWorld::Instance()->GetCollidersFromFile(FrameWork::GetConfig().GetFilePath(collidersPath.c_str(), SERVER_DIR_ROOT));
578: CHECK_COND_WITH_LOG(collidersData, LogError("[DESTRUCTIBLE]load colliders from file:%s failed", collidersPath.c_str()));
580: const physx::PxTransform pose(physx::PxVec3(pos.x, pos.y, pos.z), FaceToPxQuat(face) * m_settings->rotWithoutY);
581: physx::PxRigidStatic* actor = CreateStaticActorFromColliders(collidersData,
582: &pose,
583: GetConf().GetPresentConf()->Scale,
```

### `gameserver/unit/destructible/destructibleunit.cpp:589` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-destructible-destructibleunit-cpp-589-check_cond_with_log-187092f0` |
| 函数 | `CreateShapesFromColliders` |
| 类型 | `invariant_failed` |
| 条件 | `actor` |
| 日志/提示 | `[DESTRUCTIBLE]create actor from colliders file:%s failed` |
| 对应问题 | 代码内部不变量被破坏。 触发点 `gameserver/unit/destructible/destructibleunit.cpp`，关键条件 `[DESTRUCTIBLE]create actor from colliders file:%s failed`。 |
| 上下文 | 文件 `gameserver/unit/destructible/destructibleunit.cpp`，函数 `CreateShapesFromColliders`，附近日志 `[DESTRUCTIBLE]create actor from colliders file:%s failed`。 |
| 为什么出问题 | 对象内部状态被破坏，需要向上追踪最后一次写入。 直接线索：`[DESTRUCTIBLE]create actor from colliders file:%s failed`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/destructible/destructibleunit.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `actor` 由谁赋值或返回。
- 追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。
- 补充最小复现日志，记录关键 ID、状态和配置版本。

附近代码：

```text
584: [](physx::PxShape* shape, const auto* collider, void* userdata){
585: physx::PxFilterData filterData = shape->getQueryFilterData();
586: AddPhysicsSelfFlag(filterData, PhysicsQueryGroup::eIMPACTABLE);
587: shape->setQueryFilterData(filterData);
588: }, NULL);
589: CHECK_COND_WITH_LOG(actor, LogError("[DESTRUCTIBLE]create actor from colliders file:%s failed", collidersPath.c_str()));
591: actor->setName(GetConf().GetPresentConf()->BlockFilePath.c_str());
592: actor->userData = static_cast<CombatUnit*>(this);
593: physicsScene->GetPxScene()->addActor(*actor);
594: m_actor = actor;
```
