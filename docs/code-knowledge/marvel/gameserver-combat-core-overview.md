---
type: Code Module
title: gameserver 核心战斗总体框架
description: 战斗域模块地图。覆盖 Scene/Level/Unit/Skill/Buff/AI/XEcs。
repo: marvel
module: gameserver/combat-core
resource: gameserver
tags: gameserver, combat, battle, scene, level, unit, enemy, role, buff, ai, skill, ecs, xecs
symbols: SceneBattle, SceneHandler, LevelSpawner, Level, CombatUnit, CombatEnemy, CombatRole, XCombat, SkillMgr, SkillCore, XBuffContainer, AIEntity, AIAgent, AIUnitAgent, AIEnemyAgent, AIRoleAgent, XFacility, XSirius
logs: UnitLogErr, LogError, Check cond, skill not find, buff
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# gameserver 核心战斗总体框架

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 用途 | 说明 gameserver 核心战斗模块地图。 |
| 适用问题 | 架构、crash、宕机日志、功能实现、配置实现。 |
| 覆盖范围 | Scene、Level、Unit、Skill、Buff、AI、Combat、XEcs。 |
| 不覆盖 | 网络连接、登录、协议分发、进程部署。 |
| 使用要求 | 具体行号和结论需读取当前代码核实。 |

## 范围

覆盖：

- `gameserver/scene`：战斗场景、SceneBattle、场景 handler、场景事件、AOI/碰撞/队伍/结算等战斗容器能力。
- `gameserver/level`：Level、LevelSpawner、Lua 关卡、刷怪、地图/剧情/事件、关卡结算。
- `gameserver/unit`：CombatUnit 基类、CombatEnemy、CombatRole、属性、移动、状态、技能、同步、物理控制。
- `gameserver/combat`：伤害投射、目标/攻击者、战斗组、导航/巡逻、战斗工具。
- `gameserver/buff`：Buff 容器、Buff 生命周期、触发器、效果和战斗事件回调。
- `gameserver/ai`：YBehavior agent、Unit/Enemy/Role/Scene/Squad AI、AI 节点、目标/技能/巡逻。
- `gameserver/tableload`：Skill/Buff/AI/XEntity/Level/Scene 等配置加载与查询。
- `gameserver/xecs` + `ecs/XEcs`：服务端接入 XEcs 的 facility、动作/技能/命中/状态 ECS 系统。

不覆盖：

- `gameserver/network`、登录、连接管理、KCP、协议注册本身。
- GM、DB、邮件、账号、进程部署等非战斗核心模块。

## 总体结构

核心运行时分四层：

| 层 | 角色 | 关键入口 |
| --- | --- | --- |
| SceneBattle | 战斗场景容器。维护状态、胜负、暂停、死亡队列。 | `gameserver/scene/scenebattle.h` |
| LevelSpawner / Level | 关卡与刷怪执行层。驱动 Lua、触发器、地图、结算。 | `gameserver/level/levelspawner.h`, `gameserver/level/level.h` |
| CombatUnit | 战斗对象中心。组合 Skill、Buff、AI、属性、移动、导航。 | `gameserver/unit/unit.h` |
| XEcs | 动作、技能、命中、状态机执行层。 | `ecs/XEcs/XSirius.h`, `gameserver/xecs/XFacility.h` |

## 场景层

主要入口：

- `gameserver/scene/scenebattle.h` / `.cpp`：战斗场景基类，负责场景状态、进入/离开、更新、胜负、死亡队列、暂停、地图/场景切换、全局 AI、场景 Buff。
- `gameserver/scene/handler/scenehandler.h` / `.cpp`：聚合战斗场景 handler。
- `gameserver/scene/event/sceneeventdefine.h` / `sceneeventlistener.h`：场景事件参数和监听器。
- `gameserver/scene/fightgroup/`：场景战斗阵营/分组。
- `gameserver/scene/handler/sceneai.h`、`scenecollisions.h`、`scenedoodad.h`、`sceneactionrate.h`、`sceneend.h`：场景级 AI、碰撞、机关/交互、行动倍率、结算等。

`SceneHandler` 初始化的核心 handler 包括：

- `SceneAI`
- `LevelSpawner`
- `SceneFightGroup`
- `BattleGroupMgr`
- `SceneDropItem`
- `SceneActionRate`
- `SceneDoodad`
- `SceneCollisions`
- `SceneRobot`
- `SceneTeam`
- `SceneNotice`
- `SceneBusinessLog`
- 条件创建的 `CProveGroundProc`、`CSceneAdaptive`、`SceneEnd`

排查场景问题时，先确认问题属于 SceneBattle 生命周期、某个 handler、还是 Unit 进出场事件。

## 关卡与刷怪层

主要入口：

- `gameserver/level/levelspawner.h` / `.cpp`：场景内关卡管理器，负责主关卡、组关卡、触发器、时间限制、地图显示/加载、cutscene/plot、结算、重连数据、Level notice。
- `gameserver/level/level.h` / `.cpp`：单个 Level，给 Lua/关卡逻辑暴露 `SpawnEnemy`、`Victory`、`Fail`、`BindUnitWithEvent`、`SendAiCmd`、`Transfer`、`ChangeMap` 等接口。
- `gameserver/level/LevelEventHandler.h`：Level 事件，包括怪物进出、加/失 Buff、死亡、敌人数量变化、玩家全死等。
- `gameserver/level/LevelSpawnerStateInfo.h`：关卡/刷怪状态信息。
- `gameserver/level/info/LevelInfo.h`、`LevelWall.h`：关卡信息和墙/阻挡相关。

关卡层常见职责：

- 从配置和 Lua 状态驱动关卡进度。
- 调 `Level::SpawnEnemy` 创建怪物并绑定 wave/group/AI/patrol/customAI。
- 监听 Unit/Enemy/Level 事件，更新任务、刷怪状态和胜负。
- 与 SceneBattle 的暂停、地图切换、死亡队列、结算协作。

## Unit 层

主要入口：

- `gameserver/unit/unit.h` / `.cpp`：`CombatUnit` 基类。
- `gameserver/unit/enemy.h` / `.cpp`：`CombatEnemy`，怪物/召唤物/可破坏物等敌方战斗单位。
- `gameserver/unit/combatrole.h` / `.cpp`：`CombatRole`，玩家/伙伴/机器人战斗单位。
- `gameserver/unit/component_def.h`：Unit 组件 typelist。

`CombatUnit` 是战斗对象中心，内部组合：

- `UnitMove`：移动。
- `AIEntity`：Unit AI 实体。
- `XNavigation`：导航/寻路接口。
- `XBuffContainer`：Buff 容器。
- `SkillMgr`：技能管理。
- `UnitCombatAttribute`：战斗属性。
- `UnitBattleGroup`：战斗组。
- `StateManager`：状态管理。
- `UnitController`：物理/控制。
- `DoodadInfo`、`BindInfo`、`UnitEffect` 等扩展能力。

`component_def.h` 用 typelist 区分不同 Unit 形态：

- `TEnemyComponents`：Enemy 使用移动、AI、导航、Buff、技能、属性、控制等完整组合。
- `TRoleComponents`：Role 使用移动、导航、技能、AI、属性、Buff、绑定、控制。
- `TDoodadComponents`、`TDestructibleComponents`：从 Enemy 组件集合裁剪。

`CombatEnemy` 在 `CombatUnit` 基础上补充：

- 模板/表现/等级/Tag。
- wave/group/host level/keep count/wave index。
- AI ID、patrol、custom AI。
- death cleanup、trigger check、spawn follow、host/final host。
- `InitSkills`、`InitBufflist`、`LevelInit` 等刷怪初始化链路。

`CombatRole` 在 `CombatUnit` 基础上补充：

- `PartnerBuilderData`、伙伴/角色信息。
- `CombatGroupNew`，负责发送、会话打包、当前角色/队伍关系。
- 角色切换 `CombatRoleSwitch`。
- `RoleSkill`、`RoleBuff`、`BattleStateCtrl`、`CombatStatistics`。
- 角色/伙伴技能初始化、战斗状态、移动提前、机器人/过渡状态。

## Skill 层

主要入口：

- `gameserver/unit/skill/skillmgr.h` / `.cpp`：Unit 上的技能管理器。
- `gameserver/unit/skill/skillcore.h` / `.cpp`：单个技能运行时配置核心。
- `gameserver/unit/skill/skillaimgr.h`：AI 可用技能分组和选择辅助。
- `gameserver/tableload/skillconfig.h` / `.cpp`：技能配置表查询和索引。

职责：

- `SkillMgr` 挂在 `CombatUnit` 上，按 Unit 类型初始化角色、怪物、召唤物技能。
- `SkillCore` 保存技能名、ID、等级、攻击范围，以及 `SkillListForEnemy` / `SkillListForRole` / Spawn 的配置行指针。
- `SkillConfig` 加载 `SkillListForRole`、`SkillListForEnemy`、`SkillDamage`、`SkillSlotTable`、`QteEvent`、`DamageSwitch` 等表，并提供 `GetEnemySkillConfigX`、`GetRoleSkillConfigX`、`GetSpawnSkillConfigX` 等查询。
- AI 通过 `SkillAIMgr` 和 `AIUnitAgent::GetValidSkills` 参与技能选择。
- XEcs 通过 `XFacility` 查询技能等级、CD、技能脚本路径、技能条件，并回调 `on_skill_begin`、`on_skill_end`。

常见故障：

- 技能配置找不到：先看 `SkillConfig::GetEnemySkillConfigX` / `SkillCore::InitEnemySkill`。
- 技能等级/槽位不对：先看 `SkillMgr::InitPartner`、`SkillConfig::GetRoleSlotSkill`、`SkillSlotTable`。
- 技能无法释放：先看 `SkillMgr::CheckSkillCondition`、XEcs `skillPreCheck`、AI 可用技能集合。

## Buff 层

主要入口：

- `gameserver/buff/XBuffContainer.h` / `.cpp`：Unit 上的 Buff 容器。
- `gameserver/buff/XBuff.h`、`XBuffEffect.h`、`XBuffTrigger*.h`、`XBuff*.h`：Buff 本体、效果和触发器。
- `gameserver/tableload/buffconfig.h` / `.cpp`：Buff 配置加载和运行时数据生成。
- `gameserver/scene/handler/scenebuff.h`：场景 Buff 处理。

职责：

- `XBuffContainer` 维护 Unit 当前 Buff、延迟队列、操作队列、通知队列、状态和 active effect 索引。
- Buff 对技能开始/结束、连击、伤害、受击、护盾、属性变化、模式打断等事件做回调。
- `BuffConfig` 从 `BuffTable`、`BuffIDTable` 生成 `XBuffCreateData`，并处理 Buff 绑定技能、PVP 数据、依赖关系。
- XEcs 通过 `XFacility::add_buff`、`clear_buff_by_type`、`has_buff`、`has_buff_state` 等接口操作 Buff。

常见故障：

- Buff 没加上：查 `XBuffContainer::AddBuff`、`BuffConfig::FetchBuffData`。
- Buff 触发不生效：查对应 `XBuffTrigger*`、`XBuffContainer::RegisterEvent`、事件回调。
- 属性/伤害异常：查 `XBuffContainer::OnCastDamage`、`OnHurt`、`OnAttrChange` 和 `UnitCombatAttribute`。

## AI 层

主要入口：

- `gameserver/ai/aientity.h` / `.cpp`：`AIEntity` 与 `AIAgent` 基类。
- `gameserver/ai/aiunitagent.h` / `.cpp`：Unit AI、Enemy AI、Role AI。
- `gameserver/ai/aisceneagent.h`、`aisquadagent.h`：场景/小队 AI。
- `gameserver/ai/ainodes.h`、`aitargetnodes.h`、`aiskillnodes.h`、`ailevelnodes.h`、`aispacenodes.h`：行为树节点。
- `gameserver/tableload/aiconfig.h` / `.cpp`：AI 配置加载。

职责：

- `AIEntity` 是挂在 `CombatUnit` 上的组件，持有 `AIAgent`。
- `AIAgent` 继承 `YB::Agent`，负责加载行为树、tick、timer、启停、事件接收、AI reload。
- `AIUnitAgent` 连接 `TargetMgr`、`AttackerMgr`、`XPatrol`、`SkillMgr`，处理自动发现敌人、进入/离开战斗、技能组合和被击记录。
- `AIEnemyAgent` 从 `CombatEnemy` 和配置取 AI ID，处理巡逻与怪物可用技能。
- `AIRoleAgent` 用于角色/机器人 AI。
- `AIConfig` 读取 `UnitAITable`、`SceneAITable`、`PatrolTable`、`SightTable`、`SkillCombo`、`SquadAITable`、`SquadMemberAITable`。

排查 AI 时先确认：

- AI 是否启用或被 `AIDisableFlag` 停止。
- Unit 是否已进场并 `AIEntity::StartLoad`。
- `UnitAITable` / `SquadMemberAITable` 是否能按 AI ID 取到配置。
- `TargetMgr` 是否能选到目标，`SkillMgr` 是否有可释放技能。

## Combat 工具层

主要入口：

- `gameserver/combat/XCombat.h` / `.cpp`：伤害投射和伤害阶段处理。
- `gameserver/combat/targetmgr.h` / `.cpp`：目标管理。
- `gameserver/combat/attackermgr.h` / `.cpp`：攻击者记录。
- `gameserver/combat/battlegroup.h` / `.cpp`：战斗组。
- `gameserver/combat/combateffect.h`、`combatutility.h`、`damagedebug.h`、`killerwatcher.h`。
- `gameserver/combat/XNavigation.h`、`XPatrol.h`。

职责：

- `XCombat` 提供 `ProjectDamage`、`ProjectStart`、`ProjectEnd`、`BeforeDamageHandler`、`DamageHandler`、`AfterDamageHandle` 等伤害阶段。
- `TargetMgr` 持有当前目标并可查找最近敌人。
- `AttackerMgr` 记录攻击者队列，给 AI/仇恨/受击逻辑使用。
- `BattleGroupMgr` / `UnitBattleGroup` 维护战斗阵营/分组。
- `XNavigation` / `XPatrol` 给 Unit 和 AI 提供移动/巡逻辅助。

## XEcs 层

主要入口：

- `ecs/XEcs/XSirius.h` / `.cpp`：ECS 实例和服务端接口。
- `ecs/XEcs/ecs/XInstance.hpp`：系统更新入口。
- `ecs/XEcs/ecs/component/`：ECS 组件，例如 `XSkill`、`XHitData`、`XMovement`、`XStateAbilityData`、`XBuffTargetType` 相关数据。
- `ecs/XEcs/ecs/system/`：ECS 系统，例如 `XSkillSys`、`XHitSys`、`XStateSys`、`XActionSys`、`XBuffNodeSys`、`XSkillTargetSelectSys`、`XSkillResultSys`、`XSkillQteSys`、`XSkillMobSys`。
- `gameserver/xecs/XFacility.h` / `.cpp`：gameserver 接入 XEcs 的 facility。

职责：

- `XSirius` 对外暴露 `drive2skill`、`drive2hit`、`slot2skill`、`drive2move`、`drive2death`、`reload`、`sync` 等接口。
- `XInstance::update` 调 `XSystemManager::update_all`，驱动 ECS 系统。
- 服务端 `XSirius` 注册输入、状态、动作、技能、命中、目标选择、QTE、Buff node、脚本消息、移动/跳跃/飞行/绑定等系统。
- `XFacility` 是 ECS 与 gameserver 之间的桥，负责：
  - 查询 Unit 是否角色/Boss/当前玩家、位置/高度/半径/速度/CD/技能等级/Buff 等。
  - 查询目标集合、盟友集合、仇恨目标。
  - 回调伤害投射、加 Buff、清 Buff、技能开始/结束、状态变化、移动纠正、QTE、掉落、绑定等事件。
  - 把 ECS ID 映射回 `CombatUnit`。

## 核心协作链路

### 角色进入战斗

1. `CombatRole::Init` 设置角色类型、伙伴数据、战斗状态。
2. 调 `InitComponents` 绑定 Unit 组件。
3. 初始化属性：`UnitCombatAttribute` + `CombatAttrCalc::InitRoleAttr`。
4. 初始化技能：`SkillMgr::Init` + `SkillMgr::InitPartner` + `RoleSkill`。
5. 初始化 Buff：`RoleBuff` / `XBuffContainer`。
6. 初始化状态和 ECS：`InitEcs`、进场、SceneBattle/SceneHandler 参与后续 Update。

### 怪物刷出

1. `Level` / `LevelSpawner` 根据关卡配置或 Lua 调 `SpawnEnemy`。
2. `CombatEnemy::Init` 绑定模板、位置、朝向、飞行等基础信息。
3. `CombatEnemy::LevelInit` 写入 wave/group/level/AI/patrol/customAI 等关卡上下文。
4. 初始化配置、属性、技能、Buff、AI。
5. 进场后由 SceneBattle、LevelSpawner、AI、ECS 共同驱动战斗。

### 技能释放与伤害

1. AI、玩家输入或脚本触发技能。
2. `SkillMgr` / `SkillCore` 确认技能配置、等级、CD、条件。
3. `XSirius` / ECS 驱动技能动作、目标选择、命中、子弹、QTE 等。
4. `XFacility` 回调 gameserver 查询目标、技能数据、Buff/属性，并投射伤害。
5. `XCombat` 处理伤害阶段，`XBuffContainer` 参与伤害前后、护盾、触发器和属性变化。
6. Unit/Scene/Level 收到死亡、受击、事件并更新关卡状态。

### Buff 触发

1. Skill、ECS 或业务逻辑调用 `XFacility::add_buff` / `XBuffContainer::AddBuff`。
2. `BuffConfig::FetchBuffData` 解析 Buff 配置为运行时数据。
3. `XBuffContainer` 创建 Buff，注册 effect/trigger，维护通知。
4. 后续技能、伤害、属性、连击、Buff stack 等事件触发对应 `XBuffTrigger*` / `XBuffEffect`。

## 常见问题入口

| 问题类型 | 优先入口 |
| --- | --- |
| 怪物技能找不到 | `gameserver/unit/skill/skillcore.cpp`、`gameserver/tableload/skillconfig.cpp`、`SkillListForEnemy` |
| 角色技能槽位/等级错误 | `SkillMgr`、`RoleSkill`、`SkillConfig`、`SkillSlotTable` |
| 怪物不放技能/不进战斗 | `AIUnitAgent`、`AIEnemyAgent`、`TargetMgr`、`SkillAIMgr`、`UnitAITable` |
| 伤害异常 | `XCombat`、`XFacility::project_damage`、`UnitCombatAttribute`、`XBuffContainer` |
| Buff 不生效 | `BuffConfig::FetchBuffData`、`XBuffContainer`、对应 `XBuffTrigger*` / `XBuffEffect` |
| 刷怪/关卡卡住 | `LevelSpawner`、`Level`、`LevelEventHandler`、`LevelSpawnerStateInfo` |
| ECS 状态/技能动作异常 | `XSirius`、`XSkillSys`、`XStateSys`、`XHitSys`、`XFacility` |
| Unit 进出场/死亡异常 | `SceneBattle::OnEnterScene/OnLeaveScene`、`CombatUnit`、`CombatEnemy::OnDied`、`SceneDeath` |

## 推荐排查顺序

1. 先判断问题属于场景容器、关卡刷怪、Unit 生命周期、技能、Buff、AI、伤害，还是 XEcs 动作状态机。
2. 如果有日志，先用 `find_log_source` 定位打印点；如果有 `Check cond` / `CHECK_COND` / `failed`，再用 `find_assert_context`。
3. 如果有 Unit UID/ECS ID，沿 `CombatUnit`、`SceneBattle`、`XFacility::FindUnitByEcsFeed` 方向确认对象是否仍有效。
4. 如果是配置问题，先看 `tableload` 对应 config，再看 Unit 初始化或运行时使用点。
5. 如果是 AI/技能问题，先确认 AI 配置、可用技能集合、目标选择，再看 SkillMgr/SkillCore 和 XEcs skill precheck。
6. 如果是伤害/Buff 问题，先看 `XCombat` 阶段，再看 Buff 事件、属性变化和 ECS 回调。

## 后续应拆分的卡片

- `scene-battle-framework.md`：SceneBattle、SceneHandler、场景事件。
- `level-spawner-framework.md`：LevelSpawner、Level、刷怪和 Lua 关卡。
- [Unit 通用层](unit-framework.md)：CombatUnit、组件 typelist、通用 Unit 配置映射。已建立。
- [Enemy 层](enemy-framework.md)：CombatEnemy、怪物、召唤物、可破坏物。已建立。
- `role-framework.md`：CombatRole、玩家、伙伴、机器人、切人。
- `skill-framework.md`：SkillMgr、SkillCore、SkillConfig、技能配置链路。
- `buff-framework.md`：XBuffContainer、BuffConfig、Buff effect/trigger。
- `ai-framework.md`：AIAgent、AIUnitAgent、AI 节点、AI 配置。
- `xecs-runtime-framework.md`：XSirius、XFacility、ECS component/system。

## 相关卡片

- [marvel 代码知识库索引](index.md)
- [Unit 通用层](unit-framework.md)
- [Enemy 层](enemy-framework.md)
