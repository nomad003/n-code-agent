---
type: Code Module
title: Enemy 配置、AI、技能、召唤
description: Enemy 关键配置字段、AI 加载、技能查表、属性和召唤控制细节。
repo: marvel
module: gameserver/unit/enemy-config-ai-skill-spawn
resource: gameserver/unit/enemy.cpp
tags: enemy, config, ai, skill, spawn, attr, destructible, boss, tableload, field
symbols: XEntityStatistics, XEntityPresentation, SkillListForEnemy, UnitAITable, SquadMemberAITable, SpawnFollow, SpawnLimitTable, CombatAttrCalc, SpawnControl, DestructibleUnit
logs: enemy conf skill, skill not find in conf, not find final host, caller create not find template id, overflow last uid
asserts: CHECK_COND, CHECK_COND_NORETURN, ASSERT_FALSE
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: enemy-framework.md
depends_on: enemy-runtime-lifecycle.md, enemy-framework.md, unit-config-attr-move.md
supplements: enemy-framework.md
updated_at: 2026-06-20
---

# Enemy 配置、AI、技能、召唤

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 用途 | 细化 Enemy 的配置实现。 |
| 覆盖 | 模板/表现、AI、技能、属性、召唤、可破坏物。 |
| 适用 | 怪物怎么配、技能缺失、AI 不动、召唤物异常。 |

## 配置依赖图

| 主配置 | 关联配置 | 运行模块 |
| --- | --- | --- |
| `XEntityStatistics.ID` | `XEntityPresentation.PresentID` | `CombatEnemy::InitConf`。 |
| `XEntityStatistics.AIID` | `UnitAITable` / `SquadMemberAITable` | `AIEnemyAgent`。 |
| `XEntityStatistics.OtherSkills` / AI 技能名 | `SkillListForEnemy` 或 `SkillListForRole` | `SkillMgr` / `SkillCore`。 |
| `XEntityStatistics.InBornBuff` | `BuffTable` / `BuffIDTable` | `InitBufflist`。 |
| `XEntityStatistics.ApplyScale` | Scene conf | `CombatAttrCalc::SceneScaleAttr`。 |
| `XEntityStatistics.AttrCopy` | 另一个 `XEntityStatistics` | `InitEnemyAttr_OfTable`。 |
| `SpawnFollow.ID` | caller ECS bind | `CreateUnitByCaller`。 |
| `SpawnLimit.ID` | `SpawnControl` | 召唤数量限制。 |
| `DestructibleObject.TemplateID` | `DestructibleUnit::STATISTICS_ID` | 可破坏物覆盖配置。 |

## XEntityStatistics 字段

核心字段：

| 字段 | 用途 | 主要使用点 |
| --- | --- | --- |
| `ID` | 模板 ID | `CreateUnit`, `InitFromTemplate`, 技能查表。 |
| `EUID` | 生成 Unit UID 的模板段 | `CombatUnit::NewId(type, EUID)`。 |
| `Name` | 名字 | 日志/调试。 |
| `PresentID` | 表现 ID | `UnitConf::InitFromPresent`。 |
| `Type` | species | 选择 Enemy/Plat/Destructible 和 typelist。 |
| `Fightgroup` | 阵营 | `InitFightGroup`。 |
| `MoveType` | 初始移动类型 | `xecs::create` 初始状态。 |
| `DefaultLevel` | 默认等级 | `CombatEnemy::InitLevel`。 |
| `DeadDisappearTime` | 死亡消失时间 | `InitFromTemplate`。 |
| `Feature` | Unit feature | `SetFeature`。 |
| `NoTargetBuff` | 目标限制 Buff | `SetNoTargetBuff`。 |

物理/移动字段：

| 字段 | 用途 |
| --- | --- |
| `Block` | 是否阻挡。 |
| `BlockFlag` | 总阻挡、死亡不阻挡等 flag。 |
| `CastRangeY` | 技能/AI 纵向范围。 |
| `MinimalMoveGap` | 最小移动间隔。 |
| `RunSpeed` / `FlySpeed` / `RotateSpeed` | 基础移动属性。 |

属性字段：

| 字段 | 用途 |
| --- | --- |
| `BaseAtk` / `BaseDef` / `BaseHp` | 基础攻防血。 |
| `BaseAttr` | 额外基础属性。 |
| `AttrCopy` | 从另一个模板复制基础属性。 |
| `ApplyScale` | 是否使用场景缩放。 |
| `CallerAttrList` | 召唤物按比例继承 caller 属性。 |
| `MaxSuperArmor` | 初始霸体。 |

AI/技能字段：

| 字段 | 用途 |
| --- | --- |
| `AIID[0]` | AI 配置 ID。 |
| `AIID[1]` | AI 配置类型：0 读 `UnitAITable`，1 读 `SquadMemberAITable`。 |
| `PatrolID` | 默认巡逻 ID。 |
| `AppearSkill` | 登场技能。 |
| `OtherSkills` | 模板额外技能。 |
| `SkillListTable` | 非 0 时走 `SKILL_SPAWN`。 |
| `SkillStatisticsID` | 复用另一个 statistics ID 的 `SkillListForEnemy`。 |

## XEntityPresentation 字段

| 字段 | 用途 |
| --- | --- |
| `Prefab` | 客户端表现资源。 |
| `AnimLocation` | 动画位置。 |
| `SkillLocation` | 技能资源位置。 |
| `CurveLocation` | 曲线资源位置。 |
| `Scale` | 体型缩放。 |
| `BoundRadius` / `BoundHeight` | 基础碰撞体。 |
| `Huge` | 是否大体型。 |
| `HugeMonsterColliders` | 大体型分状态碰撞体。 |
| `CollisionStatus` | 技能碰撞状态。 |
| `BuffListTag` | Buff 目标 tag。 |
| `StateAbilityLocation` | 状态能力资源。 |
| `LevelConfigFile` | 平台/关卡配置文件。 |
| `ActionScript` | 动作脚本。 |

## AI 配置链路

AI ID 选择：

| 条件 | 行为 |
| --- | --- |
| 模板 `AIID[1] == 0` | `AIUnitAgent` 从 `UnitAITable` 取 `AIID[0]`。 |
| 模板 `AIID[1] == 1` | 从 `SquadMemberAITable` 取 `AIID[0]`。 |
| `LevelInit(aiID != 0)` | 覆盖 origin AI ID。 |

`UnitAITable` 关键字段：

| 字段 | 用途 |
| --- | --- |
| `Tree` | 行为树入口。 |
| `StateMachine` | FSM。 |
| `Sight` | 视野半径和 Y 轴范围。 |
| `FightTogetherDis` | 联动进战距离。 |
| `LeaveFighting` | 离战距离。 |
| `MainSkillName`, `LeftSkillName`, `RightSkillName`, `BackSkillName` | AI 技能分组。 |
| `CheckingSkillName`, `CheckingSkillAndStopName` | 检查类技能。 |
| `DashSkillName`, `FarSkillName`, `SelectSkillName`, `UnusedSkillName` | 特殊技能分组。 |
| `MoveSkillName`, `TurnSkillName` | 移动/转向技能。 |
| `HPSkills` | HP 阈值技能。 |
| `SkillComboID` | 技能组合。 |
| `Navi` | 导航配置。 |
| `CustomVariables`, `CustomSubTrees`, `CustomMarkers` | AI 自定义。 |

实现：

| 函数 | 行为 |
| --- | --- |
| `AIEnemyAgent::_GetAIIDFromConfig` | 从模板 `AIID` 取配置 ID 和类型。 |
| `AIUnitAgent::LoadConfig` | 加载行为树、状态机、变量、辅助 manager。 |
| `AIEnemyAgent::OnEnterScene` | 初始化巡逻路径。 |
| `AIEnemyAgent::SetPatrol` | 关卡覆盖巡逻 ID。 |
| `AIUnitAgent::DetectEnemyInSight` | 视野找敌并合并战斗组。 |

## 技能配置链路

普通 Enemy：

| 步骤 | 实现 |
| --- | --- |
| 1 | `SkillMgr::Init` 判断 `SkillListTable == 0`，设置 `SKILL_ENEMY`。 |
| 2 | AI 配置技能名通过 `CreateSkills` 创建。 |
| 3 | 模板 `AppearSkill` 和 `OtherSkills` 创建。 |
| 4 | `SkillCore::InitEnemySkill` 查 `SkillConfig::GetEnemySkillConfigX`。 |
| 5 | `SkillConfig` 按 `(XEntityStatisticsID, hash(SkillScript))` 查 `SkillListForEnemy`。 |
| 6 | 查不到时如果 statistics ID 非 0，会回退查 `(0, hash)`。 |

Spawn 技能：

| 步骤 | 实现 |
| --- | --- |
| 1 | `SkillListTable != 0`，`SkillMgr` 类型是 `SKILL_SPAWN`。 |
| 2 | `CreateSkill` 调 `GetSpawnSkillLevel`。 |
| 3 | `SkillCore::InitSpawnSkill` 查 `SkillConfig::GetSpawnSkillConfigX`。 |
| 4 | 表是 `SkillListForRole`，不是 `SkillListForEnemy`。 |

`SkillListForEnemy` 关键字段：

| 字段 | 用途 |
| --- | --- |
| `SkillScript` | 技能脚本名，参与 hash。 |
| `XEntityStatisticsID` | 绑定模板或复用模板 ID。 |
| `DamageRatio` | 伤害倍率。 |
| `InitCD` / `CDRatio` / `CDRange` | 初始 CD 和 CD 比例。 |
| `BuffID`, `BeginBuff`, `EndBuff` | 技能相关 Buff。 |
| `ModeUse` | 阶段/Mode 可用性。 |
| `HpMinLimit`, `HpMaxLimit` | HP 条件。 |
| `AttackRange` | 攻击范围。 |
| `CheckObstacle` | 是否检查阻挡。 |
| `DisableCollision` | 技能期间是否禁碰撞。 |
| `Importance` | AI 选择权重。 |
| `DamageSwitchID`, `DamageSource` | 伤害开关和来源。 |
| `DestructLevel` | 对可破坏物伤害等级。 |

技能缺失排查：

| 日志 | 常见原因 |
| --- | --- |
| `enemy conf skill:[...] not find` | `SkillListForEnemy` 没有 `(statisticsID, skillHash)`，且 fallback 也没有。 |
| `caster:%u skill:[%u %s] not find in conf` | `SkillCore::InitEnemySkill` 未拿到配置。 |
| `skill:[%u-%u %s] not find in conf` | Spawn 技能走 `SkillListForRole` 查不到。 |

## 属性配置链路

普通 Enemy：

| 字段 | 实现 |
| --- | --- |
| `RunSpeed`, `FlySpeed`, `RotateSpeed` | 写入移动属性。 |
| `MaxSuperArmor` | 写入 `ATTR_SuperArmor`。 |
| `BaseAtk`, `BaseDef`, `BaseHp` | 写入基础攻防血。 |
| `BaseAttr` | 写入额外属性。 |
| `AttrCopy` | 先切换到复制模板再读基础属性。 |
| `ApplyScale` | 调 `SceneScaleAttr`。 |

召唤属性：

| 来源 | 行为 |
| --- | --- |
| 自身模板 | 先执行 `InitEnemyAttr_OfTable`。 |
| caller 属性 | 复制未被表初始化、可设置、非状态属性。 |
| `CallerAttrList` | 按比例覆盖指定属性。 |
| `DefaultLevel == 0` | 继承 caller 等级。 |
| caller 是 Enemy | 可走队伍缩放。 |

## 召唤配置

`SpawnFollow.txt`：

| 字段 | 用途 |
| --- | --- |
| `ID` | 召唤物模板 ID。 |
| `DamageShare` | 伤害共享配置。 |

实现：

- `CreateUnitByCaller` 发现 `SpawnFollow` 行时，把召唤位置当 caller 相对偏移。
- 调 `xecs::bindTo(spawn, caller, XBindType::Rigid)`。
- `CombatEnemy::IsSpawnFollow` 由 `m_spawn_follow.followid_` 判断。

`SpawnLimit.txt`：

| 字段 | 用途 |
| --- | --- |
| `ID` | 召唤物模板 ID。 |
| `CountLimit[0]` | 限制组。 |
| `CountLimit[1]` | 默认数量上限。 |
| `DeadSkill` | 超限时旧召唤物释放的死亡技能。 |
| `PassiveSkill` | 用 caller 被动技能调整数量上限。 |
| `PassiveSkillRate` | 被动等级到上限映射。 |

`SpawnControl` 字段：

| 字段 | 用途 |
| --- | --- |
| `unit2group` | 召唤物 UID 到限制组。 |
| `group2units` | 限制组到召唤物列表和上限。 |
| `m_caller_uid` | 调试日志中的 caller。 |

实现：

- `OnAdd` 达到上限时取最早召唤物。
- 旧召唤物先 `force2idle`，再 `drive2skill(dead_skill)`。
- `OnDel` 从 `unit2group` 和 `group2units` 删除 UID。

## 可破坏物配置

主链路：

| 项 | 内容 |
| --- | --- |
| 公共模板 | `DestructibleUnit::STATISTICS_ID = 38000`。 |
| 覆盖配置 | `DestructibleObject.txt` 或 JSON override。 |
| 表现阶段 | `PresentationStages` 决定表现 ID 和血量阶段。 |
| 属性覆盖 | `BaseHp` 覆盖公共模板 HP。 |
| 掉落 | `DropDoodadId`, `DropSourceID`。 |

关键字段：

| 字段 | 用途 |
| --- | --- |
| `TemplateID` | 可破坏物业务模板。 |
| `BaseHp` | 覆盖 HP。 |
| `ApplyScale` | 是否场景缩放。 |
| `InitialActivity` | 初始激活状态。 |
| `PresentationStages` | 阶段表现。 |
| `RoleSkillTypes` | 可被哪些角色技能类型破坏。 |
| `MonsterMinSkillDestructLevel` | 怪物技能破坏等级门槛。 |
| `DestructByBehitSkill` | 是否可由受击技能破坏。 |
| `CloseCollisionDelayOnDeath` | 死亡后关闭碰撞延迟。 |
| `InBornBuff` | 可破坏物出生 Buff。 |
| `Fightgroup` | 阵营覆盖。 |
| `TriggerObject` | 触发形状。 |

## 常见排查

| 现象 | 排查字段 |
| --- | --- |
| 怪物不会索敌 | `AIID`, `UnitAITable.Tree`, `Sight`, `FightTogetherDis`。 |
| 怪物技能不存在 | `AI 技能名`, `OtherSkills`, `SkillListForEnemy.SkillScript`, `SkillStatisticsID`。 |
| 召唤物技能不存在 | `SkillListTable`, `SkillListForRole`, spawn skill level。 |
| 召唤数量不对 | `SpawnLimit.CountLimit`, `PassiveSkill`, caller 技能等级。 |
| 召唤物没跟随 | `SpawnFollow.ID`, `xecs::bindTo`, caller 是否在场景。 |
| 属性过高/过低 | `AttrCopy`, `ApplyScale`, `BaseAttr`, 队伍缩放。 |
| 可破坏物打不掉 | `RoleSkillTypes`, `MonsterMinSkillDestructLevel`, `DestructLevel`。 |

## 相关卡片

- [Enemy 创建与生命周期](enemy-runtime-lifecycle.md)
- [Enemy 层](enemy-framework.md)
