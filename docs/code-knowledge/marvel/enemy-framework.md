---
type: Code Module
title: Enemy 层
description: CombatEnemy 初始化、刷怪、AI/技能/死亡和配置链路。
repo: marvel
module: gameserver/unit/enemy
resource: gameserver/unit/enemy
tags: enemy, combatenemy, monster, boss, elite, spawn, doodad, destructible, ai, skill, buff, death, config, 怪物
symbols: CombatEnemy, EnemyCleanUpReason, SceneUnitHandler, Level::SpawnEnemy, SceneUnitHandler::CreateUnit, SceneUnitHandler::CreateUnitByCaller, AIEnemyAgent, SkillMgr, SkillCore, CombatAttrCalc, SpawnConfig, SpawnControl, DestructibleUnit, CEnemyOutLook
logs: can't find monster template id, enemy conf skill, skill not find in conf, Spawn Enemy failed, create enemy uid, pre enter scene, post enter scene, dead disappear, not find final host, clear up scene, Check cond
asserts: CHECK_COND, CHECK_COND_NORETURN, CHECK_COND_WITH_LOG_RETURN, ASSERT_FALSE
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: gameserver-combat-core-overview.md
depends_on: unit-framework.md, gameserver-combat-core-overview.md
supplements: unit-framework.md
updated_at: 2026-06-20
---

# Enemy 层

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 用途 | 说明 `CombatEnemy` 派生层。 |
| 覆盖 | 创建、初始化、Level 接入、AI、技能、Buff、属性、死亡清理。 |
| 特殊路径 | 召唤物、跟随召唤物、Doodad、Destructible、MovablePlat。 |
| 不展开 | Role 侧创建、网络协议、客户端表现细节。 |
| 使用要求 | 行号可能变化。排查时以函数名、日志文本、配置 ID 为主。 |

## 范围

覆盖代码：

- `gameserver/unit/enemy.h`
- `gameserver/unit/enemy.cpp`
- `gameserver/scene/sceneunithandler.cpp`
- `gameserver/level/level.cpp`
- `gameserver/unit/mobcontrol.*`
- `gameserver/unit/outlook/enemyoutlook.*`
- `gameserver/unit/destructible/destructibleunit.*`

关联代码：

- `gameserver/unit/skill/skillmgr.*`
- `gameserver/unit/skill/skillcore.*`
- `gameserver/unit/attr/combatattrcalc.*`
- `gameserver/ai/aiunitagent.*`
- `gameserver/tableload/xentityinfolibrary.*`
- `gameserver/tableload/skillconfig.*`
- `gameserver/tableload/aiconfig.*`
- `gameserver/tableload/spawnconfig.*`

## Enemy 类型

`CombatEnemy` 继承 `CombatUnit`。

## 细分卡片

| 子卡 | 重点 | 适用问题 |
| --- | --- | --- |
| [Enemy 创建与生命周期](enemy-runtime-lifecycle.md) | `CombatEnemy` 字段、创建入口、初始化、`LevelInit`、死亡清理。 | 刷怪失败、进离场、死亡不清理、wave/group。 |
| [Enemy 配置、AI、技能、召唤](enemy-config-ai-skill-spawn.md) | 模板/表现配置、AI、技能查表、属性、召唤、可破坏物。 | 怪物怎么配、技能缺失、AI 不动、召唤物异常。 |

类型来自 `XEntityStatistics.Type`：

| 类型判断 | 含义 | 主要影响 |
| --- | --- | --- |
| `IsBoss()` | Boss | 进入场景时注册到 `AISceneMsgChannel`，状态和集火逻辑更复杂。 |
| `IsElite()` | 精英 | 使用 Enemy 通用初始化。 |
| `IsDoodad()` | 掉落物或交互物 | 自动加 `NoTarget`、`NoHit`，清理时触发 doodad clean 事件。 |
| `IsDestructible()` | 可破坏物 | 由 `DestructibleUnit` 扩展，配置覆盖来自 `DestructibleObjectTable`。 |
| `IsSpawnType()` | 召唤类模板 | 使用 Enemy 基类能力，属性可能继承 caller。 |
| `Species_MovablePlat` | 可移动平台 | `SceneUnitHandler::CreateTemplateUnit` 创建 `PlatEntity`。 |

## 创建入口

| 场景 | 入口 | 链路 |
| --- | --- | --- |
| 关卡刷怪 | `Level::SpawnEnemy` | 坐标修正后调用 `SceneUnitHandler::CreateUnit`，再 `LevelInit`，最后 `EnterScene`。 |
| 通用创建 | `SceneUnitHandler::CreateUnit` | 查 `XEntityStatistics`，按类型创建 `CombatEnemy` / `PlatEntity` / `DestructibleUnit`。 |
| 召唤创建 | `SceneUnitHandler::CreateUnitByCaller` | 设置 host/final_host，继承部分数据，必要时绑定到 caller，再 `EnterScene`。 |
| 可破坏物 | `SceneUnitHandler::CreateDestructible` | 使用固定 `DestructibleUnit::STATISTICS_ID`，再由 `DestructibleObjectTable` 覆盖配置。 |

创建失败优先看：

- `XEntityStatistics.txt` 是否有 template ID。
- `XEntityStatistics.Type` 是否选择了预期派生类。
- `Level::SpawnEnemy` 是否传入正确坐标和 `isAir`。
- `CreateUnitByCaller` 是否能找到 caller 和 caller 所在 scene。

## 初始化链路

`CombatEnemy::Init`：

| 步骤 | 动作 | 关键数据 |
| --- | --- | --- |
| 1 | 写入 `m_uTemplateID`、`m_uPresentID`、`m_uEntitySpecies`。 | `XEntityStatistics.ID`、`PresentID`、`Type`。 |
| 2 | `InitComponents`。 | 继承 Unit 组件集合。 |
| 3 | `InitConf`。 | 先 `XEntityPresentation`，再 `XEntityStatistics`。 |
| 4 | `InitTimers`。 | Unit 秒级 timer。 |
| 5 | 创建 `AIEnemyAgent`。 | scene、Enemy 指针。 |
| 6 | `InitSkills(scene)`。 | AI 技能、模板技能、条件技能。 |
| 7 | 初始化属性。 | `CombatAttrCalc::InitEnemyAttr`。 |
| 8 | 初始化状态。 | `StateManager::Init`、`InitSkill`。 |
| 9 | 初始化阵营。 | `XEntityStatistics.Fightgroup`。 |
| 10 | 创建 ECS 实体。 | move type、face、pos、idle state。 |
| 11 | `PostInit`。 | `_AttachBeHit`、`SkillMgr::BindEcs`。 |

`CombatEnemy::OnPreEnterScene`：

| 步骤 | 动作 | 说明 |
| --- | --- | --- |
| 1 | `InitLevel(scene)` | 设置 Enemy 等级。优先场景缩放等级，否则模板默认等级，兜底 1。 |
| 2 | `InitBufflist(scene)` | 非 Destructible 加载 `XEntityStatistics.InBornBuff`。 |
| 3 | `SceneBattle::InitEnemyAdaptiveAttr` | 非 Destructible 执行场景自适应属性。 |
| 4 | Boss 注册 | Boss 调 `MsgChannel().AddSceneBoss(this)`。 |
| 5 | `AIEntity::StartLoad(scene)` | 加载 AI 配置和行为树。 |
| 6 | `CombatUnit::OnPreEnterScene` | 进入 Unit 通用进场前逻辑。 |

`CombatEnemy::Update`：

- 先执行 `CombatUnit::Update`。
- 死亡消失倒计时存在时，按场景行动倍率扣时间。
- 倒计时结束调用 `DoDeadDisappear`。
- 未死亡时执行 `CheckTrigger`。

`CombatEnemy::OnDied`：

| 步骤 | 动作 |
| --- | --- |
| 1 | 根据 `DeadDisappearTime` 设置 `m_deadtime`。 |
| 2 | 触发 `SceneEventEnemyDieArgs`。 |
| 3 | 触发 `LevelEventEnemyArgs_Die`。 |
| 4 | 给全局 AI 发送 `"Dead"` 消息。 |
| 5 | 调用 `CombatUnit::OnDied`。 |

## Level 接入

`Level::SpawnEnemy` 传入：

- `monsterID`
- 坐标和朝向
- `waveID`
- `isAir`
- `waveIndex`
- `aiID`
- `interactExstring`
- `waveRange`
- `keepMapNum`
- `groupID`
- `patrolID`
- `customAI`

`CombatEnemy::LevelInit` 写入：

| 字段 | 作用 |
| --- | --- |
| `waveID` | 关卡 wave 标识。 |
| `waveIndex` | wave 内索引。 |
| `level` | host level UID。 |
| `keepMapNum` | keep count。 |
| `interactExstring` | 交互或关卡扩展字符串。 |
| `aiID` | 覆盖 AI 原始 ID。 |
| `waveRange` | 覆盖 AI 视野。 |
| `groupID` | 关卡组。 |
| `patrolID` | 覆盖巡逻 ID。 |
| `customAI` | 按 `key=value|key=value` 写入 AI 自定义变量。 |

## 配置映射

| 运行模块 | tableload 入口 | 配置文件 | 关键字段 |
| --- | --- | --- | --- |
| 模板 | `XEntityInfoLibrary` | `table/XEntityStatistics.txt` | `ID`、`EUID`、`PresentID`、`Type`、`Fightgroup`、`MoveType`、`DefaultLevel`。 |
| 表现 | `XEntityInfoLibrary` | `table/XEntityPresentation.txt` | `Prefab`、`Scale`、`BoundRadius`、`BoundHeight`、`HugeMonsterColliders`、`CollisionStatus`、`BuffListTag`、`ActionScript`。 |
| 出生 Buff | `BuffConfig` + 模板字段 | `table/BuffTable.txt`、`table/BuffIDTable.txt`、`XEntityStatistics.InBornBuff` | Buff ID、等级、触发器、效果。 |
| Enemy 技能 | `SkillConfig` | `table/SkillListForEnemy.txt` | `SkillScript`、`XEntityStatisticsID`、`DamageRatio`、`InitCD`、`CDRatio`、`ModeUse`、`HpMaxLimit`、`AttackRange`、`DamageSwitchID`、`DamageSource`、`DestructLevel`。 |
| Spawn 技能 | `SkillConfig` | `table/SkillListForRole.txt` | `XEntityStatistics.SkillListTable != 0` 时走 `SKILL_SPAWN`，通过 `GetSpawnSkillConfigX` 查技能。 |
| 模板技能入口 | `XEntityInfoLibrary` | `table/XEntityStatistics.txt` | `AppearSkill`、`OtherSkills`、`SkillListTable`、`SkillStatisticsID`。 |
| AI | `AIConfig` | `table/UnitAITable.txt`、`table/SquadMemberAITable.txt` | `Tree`、`StateMachine`、`Sight`、`FightTogetherDis`、技能名集合、`SkillComboID`、`HPSkills`、`Navi`、`CustomVariables`。 |
| AI 选择 | 模板字段 | `XEntityStatistics.AIID` | `AIID[0]` 是配置 ID，`AIID[1]` 决定 Unit/SquadMember 配置类型。 |
| 属性 | `CombatAttrCalc` | `table/XEntityStatistics.txt` | `RunSpeed`、`FlySpeed`、`RotateSpeed`、`BaseAtk`、`BaseDef`、`BaseHp`、`BaseAttr`、`AttrCopy`、`ApplyScale`。 |
| 场景缩放 | `SceneConfig` / scene conf | `table/SceneList.txt` 等 | `SceneMonsterLevel`、`AttackBaseRate`、`DefenceRate`、`MaxHpRate`。 |
| Boss 状态 | `BossStateConfig` | `table/EnemyStage.txt`、`table/EnemyModeState.txt`、`table/EnemyResist.txt`、`table/EnemyJZ.txt` | 阶段、Mode、韧性、机制条、阶段技能和 Buff。 |
| 召唤跟随 | `SpawnConfig` | `table/SpawnFollow.txt` | `ID`、`DamageShare`。 |
| 召唤限制 | `SpawnConfig` | `table/SpawnLimit.txt` | `CountLimit`、`DeadSkill`、`PassiveSkill`、`PassiveSkillRate`。 |
| 可破坏物 | `LevelConfig` | `table/DestructibleObject.txt` | `TemplateID`、`BaseHp`、`PresentationStages`、`RoleSkillTypes`、`MonsterMinSkillDestructLevel`、`InBornBuff`、`Fightgroup`、`DropSourceID`。 |
| 全局兜底 | `GlobalConfig` | 全局配置 | `DeadCleanTime`、集火慢动作参数、自动发现半径等。 |

## 技能链路

技能来源：

1. `AIEnemyAgent` 加载 AI 配置。
2. `SkillMgr::InitSkill(UnitAITable)` 创建 AI 技能名集合。
3. `SkillMgr::InitSkill(SquadMemberAITable)` 创建小队 AI 技能名集合。
4. `SkillMgr::InitSkill(XEntityStatistics)` 创建 `AppearSkill` 和 `OtherSkills`。
5. `SkillMgr::InitConditionSkills` 建立 HP 阈值和阶段技能索引。
6. `SkillMgr::RegisterAIMgr` 按技能类型注册给 AI。
7. 普通 Enemy 用 `SkillCore::InitEnemySkill` 查 `SkillListForEnemy`。
8. Spawn 技能用 `SkillCore::InitSpawnSkill` 查 `SkillListForRole`。

技能类型选择：

- `XEntityStatistics.SkillListTable == 0`：`SkillMgr` 类型是 `SKILL_ENEMY`。
- `XEntityStatistics.SkillListTable != 0`：`SkillMgr` 类型是 `SKILL_SPAWN`。

`SkillListForEnemy` 查找规则：

1. 传入 `skillHash` 和 caster template ID。
2. 如果 `XEntityStatistics.SkillStatisticsID` 非 0，则改用该 ID 查表。
3. 先查 `(statisticsID, skillHash)`。
4. 查不到且 `statisticsID != 0`，回退查 `(0, skillHash)`。
5. 仍查不到会打印 `enemy conf skill` 或 `skill not find in conf`。

排查技能缺失时必须同时核对：

- AI 配置中的技能名是否拼对。
- `XEntityStatistics.OtherSkills` / `AppearSkill` 是否拼对。
- `SkillListForEnemy.SkillScript` 是否对应技能名。
- `SkillListForEnemy.XEntityStatisticsID` 是否等于模板 ID、`SkillStatisticsID` 或 0。
- `SkillConfig::InitSkillEnemy` 是否把该行加载进 `mSkillListForEnemy`。

Spawn 技能缺失时还要核对：

- `XEntityStatistics.SkillListTable` 是否非 0。
- `SkillConfig::GetSpawnSkillConfigX` 是否能在 `SkillListForRole` 查到技能。
- 日志可能是 `skill not find in conf`，不一定出现 `enemy conf skill`。

## 属性链路

普通 Enemy：

1. `UnitCombatAttribute::Init(templateID, uid)`。
2. `CombatAttrCalc::InitEnemyAttr`。
3. `InitEnemyAttr_OfTable` 写入速度、霸体、基础攻防血、`BaseAttr`。
4. `AttrCopy` 非 0 时从另一个 `XEntityStatistics` 复制基础属性。
5. `ApplyScale` 非 0 时走场景缩放。
6. 走队伍人数缩放。
7. 设置 `ATTR_DamageType = Damage_None`。
8. `InitAttr_AtLast` 设置当前 HP、体力、能量、机制条。

召唤 Enemy：

1. `SceneUnitHandler::CreateUnitByCaller` 设置 host 和 final_host。
2. `CombatEnemy::SetAttrByCaller` 调 `CombatAttrCalc::InitSpawnAttr`。
3. 先加载模板属性。
4. 再从 caller 复制未被表初始化、可设置、非状态类属性。
5. `CallerAttrList` 可按比例复制指定属性。
6. `DefaultLevel == 0` 时继承 caller 等级。
7. 没有复制基础攻防血时，才继续场景或队伍缩放。

可破坏物：

1. 使用通用 `DestructibleUnit::STATISTICS_ID`。
2. 表现 ID 来自 `DestructibleObjectTable.PresentationStages`。
3. `OverrideDestructibleAttr` 用 `DestructibleObjectTable.BaseHp` 覆盖基础 HP。
4. 可按 `ApplyScale` 做场景缩放。

## AI 链路

AI ID 来源：

- 默认来自 `XEntityStatistics.AIID[0]`。
- `XEntityStatistics.AIID[1]` 决定读 `UnitAITable` 还是 `SquadMemberAITable`。
- `LevelInit(aiID)` 可以覆盖原始 AI ID。

进场加载：

1. `CombatEnemy::OnPreEnterScene` 调 `AIEntity::StartLoad(scene)`。
2. `AIUnitAgent::LoadConfig` 调 `LoadFromConfig`。
3. 加载行为树、状态机、子树、变量。
4. 创建 `TargetMgr`、`AttackerMgr`、`XPatrol` 等按行为树节点需要延迟创建。
5. `AIEnemyAgent::OnEnterScene` 初始化巡逻路径。

AI 技能：

- `UnitAITable.MainSkillName` 等字段会创建并注册技能。
- `HPSkills` 会形成 HP 阈值技能。
- `SkillComboID` 绑定技能组合。
- `CheckingSkillName`、`MoveSkillName`、`TurnSkillName` 等决定 AI 行为节点能用的技能。

## 召唤关系

`CreateUnitByCaller` 设置：

| 字段 | 说明 |
| --- | --- |
| `host` | 直接召唤者。 |
| `final_host` | 最终归属者。caller 是 Enemy 时继承 caller 的 final_host。 |
| `hostlevel` | caller 是 Enemy 且有 host level 时继承。 |
| `keep` | caller 是 Enemy 时继承 keep count。 |
| `fightgroup` | 模板 `Fightgroup == -1` 时继承 caller 阵营。 |
| `SpawnFollow` | 有配置时坐标相对 caller，并通过 ECS rigid bind 到 caller。 |
| `SpawnLimit` | 通过 `SpawnControl::OnAdd/OnDel` 维护数量限制。 |

`HostDel`：

- 离场时检查 final_host。
- 如果 `SpawnLimit.CountLimit` 有限制，通知 final host 的 `SpawnControl::OnDel`。

## 死亡和清理

清理入口：

| 入口 | 说明 |
| --- | --- |
| `OnDied` | 正常死亡事件入口。 |
| `DoDeadDisappear` | 死亡消失倒计时结束后离场。 |
| `CleanUpInScene` | 场景清理、关卡 kill、doodad 超时、AI kill 等强制清理。 |
| `ForceKill` | 当前直接走 `CleanUpInScene(reason_kill_level)`。 |
| `OnLeaveScene` | Boss 反注册、spawn host 删除关系。 |

`EnemyCleanUpReason` 常见原因：

- scene cleanup
- kill all
- kill level
- doodad timeout
- doodad pick
- mob release
- AI kill
- node end kill
- revive clean
- kill entity
- kill group end

## 重点排查入口

| 现象 | 优先看 | 配置或上下文 |
| --- | --- | --- |
| `can't find monster template id` | `SceneUnitHandler::CreateUnit`、`CreateUnitByCaller`、`UnitConf::InitFromTemplate` | `XEntityStatistics.ID` 是否存在。 |
| 怪物模型或碰撞异常 | `CombatEnemy::InitConf`、`UnitConf::InitFromPresent` | `XEntityPresentation.PresentID`、体型、碰撞、Huge collider。 |
| 怪物等级异常 | `CombatEnemy::InitLevel` | `SceneMonsterLevel`、`XEntityStatistics.DefaultLevel`。 |
| 出生 Buff 缺失 | `CombatEnemy::InitBufflist` | `XEntityStatistics.InBornBuff`、`BuffTable`、`BuffIDTable`。 |
| 怪物技能找不到 | `SkillCore::InitEnemySkill`、`SkillConfig::GetEnemySkillConfigX`、`SkillCore::InitSpawnSkill` | AI 技能名、`OtherSkills`、`AppearSkill`、`SkillListForEnemy`、`SkillListForRole`、`SkillListTable`、`SkillStatisticsID`。 |
| AI 不动或不攻击 | `AIEnemyAgent`、`AIUnitAgent::LoadConfig`、`AIEntity::StartLoad` | `XEntityStatistics.AIID`、`UnitAITable`、`SquadMemberAITable`、行为树、视野。 |
| AI 技能不会释放 | `SkillMgr::RegisterAIMgr`、`SkillAIMgr`、AI 节点 | AI 技能分类字段、CD、HP 阈值、阶段限制。 |
| 属性或伤害异常 | `CombatAttrCalc::InitEnemyAttr`、`InitSpawnAttr` | `BaseAtk`、`BaseDef`、`BaseHp`、`BaseAttr`、`AttrCopy`、`ApplyScale`、队伍缩放。 |
| 召唤物属性异常 | `CreateUnitByCaller`、`InitSpawnAttr` | caller 属性、`CallerAttrList`、`DefaultLevel`、`Fightgroup`。 |
| 召唤数量异常 | `SpawnControl`、`HostDel` | `SpawnLimit.CountLimit`、final_host 是否存在。 |
| 跟随召唤异常 | `SpawnFollow` 分支、`xecs::bindTo` | `SpawnFollow.ID`、相对坐标、caller 是否有效。 |
| Boss 阶段异常 | `StateManager`、`StateStage` | `EnemyStage`、`SkillListForEnemy.ModeUse`、阶段 Buff。 |
| 死亡后关卡不推进 | `CombatEnemy::OnDied`、`LevelEventEnemyArgs_Die` | host level、wave/group、死亡事件是否触发。 |
| 死亡后对象没清理 | `m_deadtime`、`DoDeadDisappear`、`CleanUpInScene` | `DeadDisappearTime`、`GlobalConfig.Battle.DeadCleanTime`、场景 action rate。 |
| 可破坏物异常 | `DestructibleUnit::Init`、`OverrideDestructibleAttr` | `DestructibleObject.txt`、`PresentationStages`、`BaseHp`、碰撞体。 |

## 回答问题时的边界

回答 Enemy 层问题时：

- 先判断创建来源：关卡刷怪、召唤、可破坏物，还是场景清理。
- 日志里的 template ID 优先按 `XEntityStatistics.ID` 查。
- 技能日志里的 skill hash 要反查技能名，再核对 `SkillListForEnemy.SkillScript`。
- `SkillStatisticsID` 会改变技能查表 ID，不能只看原始 template ID。
- 召唤物必须同时看 host、final_host、SpawnLimit、SpawnFollow。
- 死亡问题必须同时看 Enemy 事件、Level 事件、AI 全局消息和离场清理。

## 相关卡片

- [Unit 通用层](unit-framework.md)
- [gameserver 核心战斗总体框架](gameserver-combat-core-overview.md)
- [Enemy 创建与生命周期](enemy-runtime-lifecycle.md)
- [Enemy 配置、AI、技能、召唤](enemy-config-ai-skill-spawn.md)
