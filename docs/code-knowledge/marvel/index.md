# Marvel 代码知识库索引

本目录是 `marvel` 聚合仓库的代码知识库，覆盖 `gameserver` 与 `ecs/XEcs`。
卡片用于给 code-agent 提供稳定模块地图；具体结论仍需通过工具读取当前代码核实。

## Gameserver

* [gameserver 总览](gameserver-overview.md) - 进程入口、模块分层和排查路径。
* [配置加载](tableload-config.md) - `tableload` 配置类、表查询和配置问题排查。
* [场景框架](scene-framework.md) - `Scene` / `SceneMgr` / scene handler。
* [关卡框架](level-framework.md) - `Level`、`LevelSpawner`、Lua/tolua 桥、刷怪和事件。
* [战斗框架](combat-framework.md) - 战斗管理、目标、伤害效果、战斗工具。
* [单位、属性与技能](unit-skill-attr.md) - `CombatUnit`、`CombatRole`、`CombatEnemy`、属性和技能。
* [怪物配置与敌人技能配置链路](monster-config.md) - 怪物配置和 enemy skill not find 排查。
* [Buff 框架](buff-framework.md) - Buff 容器、效果、触发器和配置。
* [AI 框架](ai-framework.md) - AI agent、节点和技能/目标/关卡相关 AI。
* [角色框架](role-framework.md) - `Role`、`RoleMgr`、战斗角色、技能和队伍切换。
* [网络与协议](network-protocol.md) - client link、KCP、listener、protocol 分组和发包入口。

## ECS

* [XEcs 框架](xecs-framework.md) - component/system/utility 三层和 gameserver 集成点。
