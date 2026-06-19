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

## 关系维护规则

知识卡片 frontmatter 支持五类语义关系：

* `part_of`：模块/链路属于更上层框架，例如 `scene-framework.md` 属于 `gameserver-overview.md`。
* `depends_on`：理解本卡前建议先读的基础卡，例如怪物配置链路依赖 tableload 与单位技能卡。
* `supplements`：本卡补充另一张卡的细节、示例或排查路径。
* `contradicts`：两张卡存在结论冲突时再填写，用于人工治理。
* `supersedes`：本卡取代旧版卡时再填写，用于淘汰过期知识。

当前 marvel 卡片已经使用 `part_of`、`depends_on`、`supplements` 建立模块关系。
暂未发现真实冲突或旧版替换卡，因此没有写入 `contradicts` / `supersedes` 边。
