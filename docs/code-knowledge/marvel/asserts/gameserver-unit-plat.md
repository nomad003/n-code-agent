---
type: Code Playbook
title: Assert 排障 - gameserver-unit-plat
description: gameserver-unit-plat 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-plat
resource: gameserver/unit/plat/platentity.cpp, gameserver/unit/plat/platentity.h
tags: assert, check, outage_log, crash, gameserver, unit, plat
symbols: PlatEntity::OnPostEnterScene, GetBindeeUnit, GetBindeePlat, BindToPlat
logs:
asserts: CHECK_COND, CHECK_COND_RETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-plat

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-plat` |
| 条目数 | 5 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/plat/platentity.cpp:112` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-plat-platentity-cpp-112-check_cond-21506a06` |
| 函数 | `PlatEntity::OnPostEnterScene` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `collidersData` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/unit/plat/platentity.cpp`，关键条件 `collidersData`。 |
| 上下文 | 文件 `gameserver/unit/plat/platentity.cpp`，函数 `PlatEntity::OnPostEnterScene`，附近代码 `112: CHECK_COND(collidersData);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`collidersData`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/plat/platentity.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `collidersData` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
107: {
108: physx::PxPhysics* physics = PhysicsWorld::Instance()->GetPxPhysics();
109: physx::PxMaterial* material = PhysicsWorld::Instance()->GetMaterial();
110: gridPath = FrameWork::GetConfig().GetFilePath(gridPath.c_str(), SERVER_DIR_ROOT);
111: const SharedCollidersData* collidersData = PhysicsWorld::Instance()->GetCollidersFromFile(gridPath);
112: CHECK_COND(collidersData);
113: const physx::PxTransform globalPose = PosFaceToPxTransform(GetPosition(), GetFaceDegree());
114: physx::PxRigidDynamic* actor = CreateKinematicActorFromColliders(
115: collidersData,
116: &globalPose,
117: GetConf().GetPresentConf()->Scale,
```

### `gameserver/unit/plat/platentity.cpp:135` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-plat-platentity-cpp-135-check_cond-9994e92d` |
| 函数 | `PlatEntity::OnPostEnterScene` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `m_grid` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/unit/plat/platentity.cpp`，关键条件 `m_grid`。 |
| 上下文 | 文件 `gameserver/unit/plat/platentity.cpp`，函数 `PlatEntity::OnPostEnterScene`，附近代码 `135: CHECK_COND(m_grid);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`m_grid`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/plat/platentity.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `m_grid` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
130: UpdateHugeColliderData();
131: }
132: else
133: {
134: m_grid = Grid::GetGrid(gridPath);
135: CHECK_COND(m_grid);
137: if (IsEnabled())
138: {
139: AddSelfGridToScene_(scene);
140: }
```

### `gameserver/unit/plat/platentity.h:202` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-plat-platentity-h-202-check_cond_return-f59784ba` |
| 函数 | `GetBindeeUnit` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/unit/plat/platentity.h`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/unit/plat/platentity.h`，函数 `GetBindeeUnit`，附近代码 `203: const uint64_t bindee = xecs::getBindee_ecs(unit->GetEcsID());`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/plat/platentity.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
197: extern CombatUnit* FindUnitByEcsFeed(uint64_t ecsid);
198: }
200: inline CombatUnit* GetBindeeUnit(CombatUnit* unit)
201: {
202: CHECK_COND_RETURN(unit, NULL);
203: const uint64_t bindee = xecs::getBindee_ecs(unit->GetEcsID());
204: if (!bindee) return NULL;
205: return xecs::FindUnitByEcsFeed(bindee);
206: }
```

### `gameserver/unit/plat/platentity.h:210` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-plat-platentity-h-210-check_cond_return-f59784ba` |
| 函数 | `GetBindeePlat` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `unit` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/unit/plat/platentity.h`，关键条件 `unit`。 |
| 上下文 | 文件 `gameserver/unit/plat/platentity.h`，函数 `GetBindeePlat`，附近代码 `211: CombatUnit* bindee = GetBindeeUnit(unit);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`unit`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/plat/platentity.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
205: return xecs::FindUnitByEcsFeed(bindee);
206: }
208: inline PlatEntity* GetBindeePlat(CombatUnit* unit)
209: {
210: CHECK_COND_RETURN(unit, NULL);
211: CombatUnit* bindee = GetBindeeUnit(unit);
212: return bindee ? PlatEntity::CastFromUnit(bindee) : NULL;
213: }
215: inline UINT64 GetBindeePlatLevelUID(CombatUnit* unit)
```

### `gameserver/unit/plat/platentity.h:223` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-plat-platentity-h-223-check_cond_return-da63f67c` |
| 函数 | `BindToPlat` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `unit && plat` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/unit/plat/platentity.h`，关键条件 `unit && plat`。 |
| 上下文 | 文件 `gameserver/unit/plat/platentity.h`，函数 `BindToPlat`，附近代码 `224: return plat->BindUnit(unit, disableAutobind);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`unit && plat`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/plat/platentity.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `unit && plat` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
218: return bindee ? bindee->GetBindLevel() : 0;
219: }
221: inline bool BindToPlat(CombatUnit* unit, PlatEntity* plat, bool disableAutobind = true)
222: {
223: CHECK_COND_RETURN(unit && plat, false);
224: return plat->BindUnit(unit, disableAutobind);
225: }
```
