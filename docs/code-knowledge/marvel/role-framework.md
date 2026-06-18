---
type: Code Module
title: 角色框架
description: Role、RoleMgr、CombatRole、角色技能、伙伴和队伍切换。
repo: marvel
module: gameserver/role
resource: gameserver/role
tags: role, player, combatrole, roleskill, partner, team, switch, 角色
symbols: Role, RoleMgr, CombatRole, RoleSkill
logs: Role
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# 角色框架

这张卡用于回答“玩家角色如何管理”“Role 和 CombatRole 区别”“角色技能/队伍切换/伙伴相关功能从哪里查”。

## 入口文件

- `gameserver/role/role.cpp` / `.h`：玩家角色对象。
- `gameserver/role/rolemgr.cpp` / `.h`：角色管理。
- `gameserver/unit/combatrole.cpp` / `.h`：进入战斗场景后的角色战斗单位。
- `gameserver/role/roleskill.cpp` / `.h`：角色技能。
- `gameserver/role/rolebuff.cpp` / `.h`：角色 Buff 相关。
- `gameserver/role/roleswitch.cpp`、`formationswitch.cpp`、`rolecombatgroup.cpp`：切换、编队和战斗组。
- `gameserver/role/partnerbuilder.cpp`：伙伴构建。

## 核心职责

- 管理玩家角色的在线状态、场景切换和战斗单位。
- 维护角色技能、Buff、队伍切换、伙伴和战斗组数据。
- 连接网络协议、场景、关卡、单位、技能和配置。

## 常见链路

- 登录/进入场景：协议处理进入 `Role` / `RoleMgr`，再进入 `Scene`。
- 战斗角色：`Role` 在场景中对应 `CombatRole`。
- 技能：角色技能配置和运行时技能系统最终进入 `unit/skill`。
- 切换/编队：`roleswitch`、`formationswitch`、`rolecombatgroup`。

## 常见提问

- “Role 和 CombatRole 分别负责什么？”
- “玩家技能如何初始化？”
- “切人/编队/伙伴功能在哪？”
- “玩家进入场景 crash 怎么查？”

## 排查顺序

1. 看问题来自协议、场景切换、技能、Buff、切人还是伙伴。
2. 角色生命周期问题先看 `role` / `rolemgr`。
3. 战斗内问题跳到 `unit/combatrole`、`unit/skill`、`combat`。
4. 配置问题查 `partnerconfig`、`roleattrconfig`、技能配置等 `tableload` 类。

## 相关卡片

- [场景框架](scene-framework.md)
- [单位、属性与技能](unit-skill-attr.md)
- [网络与协议](network-protocol.md)
