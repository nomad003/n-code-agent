---
type: Reference
title: Unit 层索引
description: CombatUnit 通用组件地图。排除 Enemy/Role 派生细节。
repo: marvel
module: gameserver/unit
resource: gameserver/unit
tags: unit, combatunit, layer, index, 战斗单位
part_of: ../gameserver/combat-core-overview.md
depends_on: ../gameserver/combat-core-overview.md
updated_at: 2026-06-20
---

# Unit 层索引

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 用途 | 作为 Unit 层目录，指向每个独立模块知识卡。 |
| 覆盖 | Unit 生命周期、组件组合、通用配置来源。 |
| 不展开 | `CombatEnemy`、`CombatRole` 的派生初始化和业务细节。 |
| 适用问题 | crash 栈、宕机日志、功能实现、配置实现。 |
| 使用要求 | 具体行号需读取当前代码核实。 |

## 范围

覆盖代码：

- `gameserver/unit/unit.h` / `.cpp`
- `gameserver/unit/component_base.h`
- `gameserver/unit/component_def.h`
- `gameserver/unit/conf/`
- `gameserver/unit/attr/`
- `gameserver/unit/move/`
- `gameserver/unit/state/`
- `gameserver/unit/skill/`
- `gameserver/unit/sync/`
- `gameserver/unit/affixeffect/`
- `gameserver/unit/doodadinfo/`
- `gameserver/unit/plat/bindinfo.*`

只作为依赖提到：

- `gameserver/buff/`
- `gameserver/ai/`
- `gameserver/combat/`
- `gameserver/physx/`
- `gameserver/xecs/`
- `gameserver/tableload/`

明确不展开：

- `CombatEnemy` 怪物、召唤物、可破坏物的派生逻辑。
- `CombatRole` 玩家、伙伴、机器人、切人和会话逻辑。
- 网络协议注册、连接、登录、服务部署。

## Unit 基础职责

`CombatUnit` 是战斗对象的通用中心。

它负责：

- 保存 Unit ID、ECS ID、模板 ID、表现 ID。
- 保存位置、朝向、移动类型、状态标签。
- 组合属性、移动、状态、技能、Buff、AI、导航。
- 进入场景、离开场景、每帧更新、每秒更新。
- 对接 ECS、场景、关卡、伤害、Buff、AI。

## 细分卡片

| 子卡 | 重点 | 适用问题 |
| --- | --- | --- |
| [CombatUnit 运行骨架](combatunit.md) | Unit 身份、场景生命周期、更新、死亡入口。 | crash 栈、离场后引用、死亡没触发。 |
| [Unit 组件系统](unit-components.md) | 组件 typelist、`InitComponents`、`PartialCall`。 | 组件为空、组件未调用。 |
| [UnitConf 配置封装](unit-conf.md) | 模板/表现/物理参数聚合。 | 配置缺失、体型/碰撞异常。 |
| [UnitCombatAttribute 属性容器](unit-combat-attribute.md) | 属性数组、当前值约束、属性变化事件。 | 属性读写和同步异常。 |
| [CombatAttrCalc 属性初始化](combat-attr-calc.md) | 属性加载、复制、缩放、最终当前值。 | 属性过高/过低、召唤继承。 |
| [UnitMove 移动与碰撞修正](unit-move.md) | 移动入口、阻挡、动态墙、可行走区。 | 穿墙、拉回、高度异常。 |
| [XNavigation 导航模块](xnavigation.md) | 目标修正、路径、直线可达、传送判定。 | AI 导航失败。 |
| [UnitController 物理控制器](unit-controller.md) | PhysX CCT、碰撞过滤、控制器释放。 | 物理碰撞和 CCT crash。 |
| [StateManager 状态管理](state-manager.md) | 阶段、Mode、机制条、技能/hit 窗口。 | 状态切换、状态技能。 |
| [SkillMgr 技能管理](skill-mgr.md) | 技能创建、AI 注册、条件技能、ECS 绑定。 | 技能对象和 AI 技能。 |
| [技能编辑器节点枚举](skill-editor-nodes.md) | 技能 JSON 节点、XNodeData、XBPNodeSys 映射。 | 技能编辑器节点、节点不执行。 |
| [XBuffContainer Buff 容器接入](xbuff-container.md) | Buff 生命周期和 Unit 事件接入。 | 出生 Buff、技能 Buff。 |
| [AIEntity AI 容器](ai-entity.md) | AI agent 生命周期和每帧驱动。 | AI 不运行。 |
| [UnitEffect Affix Effect](unit-effect.md) | Affix effect 事件触发。 | Effect/Buff/属性修正。 |
| [DoodadInfo 掉落物信息](doodad-info.md) | Doodad/drop 生命周期。 | 掉落物清理和拾取。 |
| [BindInfo 平台绑定](bind-info.md) | 平台自动绑定、脚本绑定和解绑。 | 平台绑定错位。 |
| [Unit 同步模块](unit-sync.md) | 输入接收、ECS snapshot、状态广播。 | 位置/技能同步错误。 |

| 生命周期 | 入口 | 主要动作 |
| --- | --- | --- |
| 构造 | `CombatUnit::CombatUnit` | 初始化导航、AI、Buff、战斗组、移动、绑定、物理控制器。 |
| 组件绑定 | `CombatUnit::InitComponents` | 把实际成员对象写入 `m_oComponents`。 |
| 进场前 | `CombatUnit::OnPreEnterScene` | 战斗场景中初始化 `StateManager` 进场前状态。 |
| 进场 | `CombatUnit::EnterScene` | 设置当前场景，调用 `Scene::AddUnit`，再触发进场后逻辑。 |
| 进场后 | `CombatUnit::OnPostEnterScene` | 可释放登场技能，调用移动和控制器进场回调。 |
| 场景就绪 | `CombatUnit::OnSceneReady` | 关闭技能初始 CD、启动 AI agent、触发 `AttrEffect`。 |
| 每帧 | `CombatUnit::Update` | 状态、体力恢复、组件 Update、秒级更新、死亡检测。 |
| 离场 | `CombatUnit::LeaveScene` | AI 离场、战斗组离开、组件离场、`Scene::DelUnit`。 |
| 死亡 | `CombatUnit::UpdateDeath` | `CheckDeath` 成立后进入真实死亡处理。 |

## 组件组合

组件基类：

| 类型 | 职责 |
| --- | --- |
| `IUnitComponent` | 提供 `Update`、`OnPostEnterScene`、`OnLeaveScene` 和 `CombatUnit*` 绑定。 |
| `m_oComponents` | 按 typelist 下标保存组件指针。 |
| `PartialCall` | 按当前 Unit 物种筛选组件后批量调用。 |

组件集合：

| 集合 | 组成 | 说明 |
| --- | --- | --- |
| `TEnemyComponents` | `UnitMove`、`AIEntity`、`XNavigation`、`XBuffContainer`、`SkillMgr`、`UnitCombatAttribute`、`BindInfo`、`UnitController` 等 | 完整组件集合。这里只看通用组合，不展开 Enemy 行为。 |
| `TRoleComponents` | `UnitMove`、`XNavigation`、`SkillMgr`、`AIEntity`、`UnitCombatAttribute`、`XBuffContainer`、`BindInfo`、`UnitController` | Role 组件集合。这里只看组件选择，不展开 Role 行为。 |
| `TDoodadComponents` | 从 Enemy 集合裁剪后追加 `DoodadInfo` | 掉落物或交互物形态。 |
| `TDestructibleComponents` | 从 Enemy 集合裁剪 AI、导航、平台、绑定、控制器等 | 可破坏物形态。 |
| `TComponentsWithUpdatorPerFrame` | `XBuffContainer`、`AIEntity`、`XNavigation`、`DoodadInfo`、`BindInfo`、`UnitMove` | `CombatUnit::Update` 每帧调用。 |
| `TComponentsWithUpdatorPerSec` | `UnitCombatAttribute` | 秒级组件集合。当前基类主要由状态和属性逻辑驱动。 |
| `TComponentsWithEnterSceneFunctor` | `UnitMove`、`UnitController` | 进出场回调组件。 |

## 模块职责

| 模块 | 主要代码 | 功能 | 配置来源 |
| --- | --- | --- | --- |
| Unit 基类 | `unit/unit.h`, `unit/unit.cpp` | 生命周期、组件挂载、场景进出、通用事件、死亡检测。 | 间接依赖所有组件配置。 |
| 组件基类 | `unit/component_base.h` | 统一组件接口和 Unit 指针绑定。 | 无直接配置。 |
| 组件 typelist | `unit/component_def.h` | 按 Unit 物种选择组件集合。 | `EntitySpecies`。 |
| Unit 配置封装 | `unit/conf/unitconf.*` | 模板、表现、碰撞体、体型、Buff 标签。 | `XEntityStatistics`、`XEntityPresentation`、`PartnerBattleTable`。 |
| 属性容器 | `unit/attr/combatattribute.*` | 保存和修改 `CombatAttrDef` 数值。 | `AttrDefine` 定义属性元信息。 |
| 属性计算 | `unit/attr/combatattrcalc.*` | 初始化和缩放属性，处理 HP、护盾、体力、CD、Buff 时长等。 | Unit 模板、场景、队伍、Buff、技能等运行时数据。 |
| 移动 | `unit/move/unitmove.*` | 移动校正、碰撞、动态阻挡、墙触发、可行走区域检查。 | Unit 物理配置、场景地图、动态墙。 |
| 导航 | `combat/XNavigation.*` | 目的点导航、路径检测、直线可达、不可达和传送判定。 | 场景 WaypointGraph、Unit 半径、目标点参数。 |
| 物理控制器 | `physx/UnitController.*` | PhysX CCT 创建、移动、过滤、碰撞行为、位置纠正。 | Unit 物理配置、PhysicsScene。 |
| 状态管理 | `unit/state/StateManager.*` | 阶段、Mode、韧性、机制条、状态技能和受击状态。 | `EnemyStage`、`EnemyModeState`、`EnemyResist`、`EnemyJZ`、`PlayerJZ`。 |
| 技能管理 | `unit/skill/skillmgr.*`, `unit/skill/skillcore.*` | 技能初始化、CD、条件、ECS 绑定、AI 技能集合。 | `SkillListForRole`、`SkillListForEnemy`、`SkillListForPartner`、`SkillDamage` 等。 |
| 技能编辑器节点 | `XEcsLib/XEcs/ecs/component/*`, `XEcsLib/XEcs/ecs/system/*`, `utility2reader_json.hpp` | 技能 JSON 节点加载、节点数据结构、节点执行系统映射。 | 技能编辑器导出的 Skill / Hit / Display / State JSON。 |
| Buff 容器 | `buff/XBuffContainer.*` | Buff 生命周期、触发器、延迟队列、属性和伤害事件。 | `BuffTable`、`BuffIDTable`、Unit Buff 标签。 |
| AI 实体 | `ai/aientity.*`, `ai/aiunitagent.*` | 挂接 YBehavior agent、tick、启停、目标和技能选择。 | `UnitAITable`、`PatrolTable`、`SightTable`、`SkillCombo`、`Squad*`。 |
| 附加效果 | `unit/affixeffect/uniteffect.*`, `affixeffect/attreffect.*` | 管理 affix effect 数据，响应技能、伤害、状态、属性变化。 | `AffixEffect`。 |
| 掉落物信息 | `unit/doodadinfo/doodad.*` | 保存掉落物配置、创建者、Buff 索引、拾取对象、生命周期。 | `DropObject`。 |
| 绑定信息 | `unit/plat/bindinfo.*` | 自动绑定、解绑、平台站立检查。 | 间接依赖平台、场景和 Unit 绑定状态。 |
| 战斗组 | `combat/battlegroup.*` | Unit 分组、角色集合、组切换、离组。 | 场景运行时数据。 |
| 击杀记录 | `combat/killerwatcher.*` | 记录击杀者、执行者、技能、Buff。 | 伤害和属性变化上下文。 |
| Unit 同步 | `unit/sync/unitecs.*`, `unit/sync/xactionsender.*`, `unit/sync/xactionreceiver.*` | ECS 快照、服务端同步包、客户端动作输入校验。 | `SkillConfig` 用于技能名，ECS 状态用于快照。 |

## 配置映射

| 运行模块 | tableload 入口 | 配置文件 | 关键字段或用途 |
| --- | --- | --- | --- |
| `UnitConf::InitFromTemplate` | `XEntityInfoLibrary` | `table/XEntityStatistics.txt` | `Block`、`BlockFlag`、`CastRangeY`、`MinimalMoveGap`、类型。 |
| `UnitConf::InitFromPresent` | `XEntityInfoLibrary` | `table/XEntityPresentation.txt` | `CollisionStatus`、`Huge`、`Scale`、`BoundRadius`、`BoundHeight`、`HugeMonsterColliders`、`BuffListTag`。 |
| `UnitConf::InitFromPartner` | `PartnerConfig` | `table/PartnerBattleTable.txt` | 伙伴形态的物理参数。这里只记录配置入口，不展开 Role。 |
| `UnitCombatAttribute` | `RoleAttrConfig` | `table/AttrDefine.txt` | 属性 ID、同步标记、属性类型、最大值类型。 |
| `CombatAttrCalc` | 多个配置入口 | `XEntityStatistics`、`PartnerBattleTable`、场景/队伍运行时数据 | 初始化属性、缩放属性、CD、体力、护盾、HP 变化。 |
| `UnitMove` | `SceneConfig` | `table/SceneList.txt`、`table/MapList.txt` | 地图、阻挡、导航路径、场景地图数据。 |
| `UnitMove` | `WallConfig` | `table/DynamicWall.txt` | 动态墙、触发墙、直线检测。 |
| `XNavigation` | `SceneConfig` / 场景网格 | 地图 nav 数据 | WaypointGraph、路径搜索、直线可达。 |
| `UnitController` | Unit 物理配置 | `XEntityStatistics`、`XEntityPresentation` | 碰撞体半径、高度、阻挡、技能碰撞。 |
| `StateManager` | `BossStateConfig` | `table/EnemyStage.txt`、`table/EnemyModeState.txt`、`table/EnemyResist.txt`、`table/EnemyJZ.txt`、`table/PlayerJZ.txt` | 阶段、Mode、韧性、机制条。 |
| `SkillMgr` / `SkillCore` | `SkillConfig` | `table/SkillListForRole.txt`、`table/SkillListForEnemy.txt`、`table/SkillListForPartner.txt` | Unit 技能列表、技能脚本、技能等级。 |
| `SkillMgr` / ECS | `SkillConfig` | `table/SkillDamage.txt`、`table/SkillChange.txt`、`table/SuperArmorTable.txt`、`table/QteEvent.txt`、`table/SkillSlot.txt`、`table/DamageSwitch.txt` | 伤害点、技能变化、霸体、QTE、槽位、伤害开关。 |
| `XBuffContainer` | `BuffConfig` | `table/BuffTable.txt`、`table/BuffIDTable.txt` | Buff 运行时数据、触发器、效果、绑定技能。 |
| `AIEntity` / `AIAgent` | `AIConfig` | `table/UnitAITable.txt`、`table/SceneAITable.txt`、`table/PatrolTable.txt`、`table/SightTable.txt`、`table/SkillCombo.txt`、`table/SquadAITable.txt`、`table/SquadMemberAITable.txt` | 行为树、巡逻、视野、技能组合、小队 AI。 |
| `UnitEffect` / `AttrEffect` | `AffixEffectConfig` | `table/AffixEffect.txt` | 技能、Buff、伤害、属性、状态相关附加效果。 |
| `DoodadInfo` | `DoodadConfig` | `table/DropObject.txt` | 掉落物行、Buff 组、生命周期、拾取信息。 |
| 表加载顺序 | `tableload/tableinit.cpp` | 多个配置 | `SceneConfig`、`XEntityInfoLibrary`、`RoleAttrConfig`、`AIConfig`、`BuffConfig`、`BossStateConfig`、`SkillConfig` 等依次初始化。 |

## 更新链路

每帧链路：

1. `CombatUnit::Update(delta)` 检查当前场景。
2. 战斗场景停止时直接返回。
3. puppet 状态下把 `delta` 置零。
4. 计算 `sceneDelta = delta * m_fSlowDownRate`。
5. `StateManager::Update(sceneDelta)`。
6. `CombatAttrCalc::RecoverVigorPerSec(this, sceneDelta)`。
7. `PartialCall<TComponentsWithUpdatorPerFrame>`。
8. 秒级时间累计后调用 `UpdatePerSceneSecond()`。
9. `UpdateDeath()` 检查死亡。

每秒链路：

1. 确认仍在场景中。
2. 确认当前场景是 `SceneBattle`。
3. 死亡 Unit 直接返回。
4. `StateManager::UpdatePerSecond()`。

进场链路：

1. `EnterScene` 校验 scene。
2. `OnPreEnterScene` 处理状态进场前逻辑。
3. 设置 `m_currScene`。
4. `Scene::AddUnit(this)`。
5. 打印 `enter scene` 日志。
6. `OnPostEnterScene` 处理登场技能。
7. `UnitMove` 和 `UnitController` 执行进场回调。

离场链路：

1. AI agent 执行 `LeaveScene`。
2. `UnitBattleGroup::Leave(false)`。
3. 派生类 `OnLeaveScene()`。
4. `UnitMove` 和 `UnitController` 执行离场回调。
5. 打印 `leave scene` 日志。
6. `Scene::DelUnit(this)`。
7. 清空 `m_currScene`。

## 重点排查入口

| 现象 | 优先看 | 配置或上下文 |
| --- | --- | --- |
| Unit 进场失败 | `CombatUnit::EnterScene`、`Scene::AddUnit` | scene 是否为空，是否重复进场。 |
| Unit 离场后被访问 | `CombatUnit::LeaveScene`、AI agent、战斗组、场景 Unit 容器 | UID 是否还在 Scene、ECS、AI、Buff 队列中。 |
| 模板配置找不到 | `UnitConf::InitFromTemplate` | `XEntityStatistics.txt` 的 template ID。日志含 `can't find monster template id`。 |
| 表现配置找不到 | `UnitConf::InitFromPresent` | `XEntityPresentation.txt` 的 present ID。失败会触发 `CHECK_COND_NORETURN`。 |
| 碰撞体异常 | `UnitConf::InitBodySize`、`UnitMove`、`UnitController` | `Scale`、`BoundRadius`、`BoundHeight`、`HugeMonsterColliders`、`BlockFlag`。 |
| 移动被挡或位置校正 | `UnitMove::TryMove`、`CheckBlock`、`CheckDynamicBlock` | 场景阻挡、动态墙、Unit 半径、高度、平台绑定。 |
| 导航失败 | `XNavigation::Enable`、`_CheckCanFindPathByWayPoint`、`_CheckCanStraightReach` | WaypointGraph、目标点、半径、teleLimit、navi mode。 |
| 属性不同步 | `UnitCombatAttribute`、`CombatUnit::FillAttr2Client`、`RoleAttrConfig::GetAttrDefineNeedSysClient` | `AttrDefine.SynClient`。 |
| HP、护盾、体力异常 | `CombatAttrCalc`、`XBuffContainer`、`XCombat` | 属性、Buff、伤害上下文。 |
| 状态不切换 | `StateManager`、`StateStage`、`StateMode`、`StateResist` | `EnemyStage`、`EnemyModeState`、`EnemyResist`、`EnemyJZ`、`PlayerJZ`。 |
| 技能找不到 | `SkillMgr`、`SkillCore`、`SkillConfig` | Unit 类型、skill hash、skill level、statistics ID。 |
| Buff 没生效 | `XBuffContainer`、`BuffConfig::FetchBuffData` | `BuffTable`、`BuffIDTable`、Unit `BuffListTag`。 |
| AI 没 tick | `AIEntity`、`AIAgent`、`AIUnitAgent` | 是否进场，AI 是否禁用，`UnitAITable` 是否存在。 |
| ECS 状态不同步 | `EcsSnapshot`、`XActionSender`、`XActionReceiver`、`XFacility` | ECS ID、当前状态、当前技能、位置和朝向。 |
| 掉落物异常 | `DoodadInfo`、`DoodadConfig` | `DropObject` 行、Buff 组、拾取角色、生命周期。 |

## 回答问题时的边界

回答 Unit 层问题时：

- 先判断问题在基类生命周期、组件、配置、还是派生类。
- 只有确认栈或日志落在派生类时，才展开 `CombatEnemy` 或 `CombatRole`。
- 行号不作为唯一依据。优先使用函数名、日志文本、assert 文本、配置 ID。
- 配置问题要同时给出 tableload 入口和表名。
- crash 栈要说明对象生命周期：是否已进场、是否离场、是否死亡、是否仍被 ECS/AI/Buff 引用。

## 相关卡片

- [gameserver 核心战斗总体框架](../gameserver/combat-core-overview.md)
- [Enemy 层索引](../enemy/index.md)
- [CombatUnit 运行骨架](combatunit.md)
- [Unit 组件系统](unit-components.md)
