---
type: Code Module
title: gameserver 总览
description: gameserver 进程入口、主要业务模块和跨模块排查路线。
repo: marvel
module: gameserver
resource: gameserver
tags: gameserver, overview, main, process, module, crash, log
symbols: main, Process, Config
logs: Error Exit, Log_FlushOnExit
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl, config_impl
updated_at: 2026-06-18
---

# gameserver 总览

这张卡用于回答“gameserver 整体结构是什么”“某个 crash/log 应该先看哪个模块”“功能实现从哪里开始查”这类问题。它是导航卡，具体行号和逻辑仍需用工具核实。

## 入口文件

- `gameserver/main.cpp`：进程启动入口。
- `gameserver/process.cpp` / `process.h`：进程生命周期和主流程承载点。
- `gameserver/config.cpp` / `config.h`：服务配置入口。
- `gameserver/sighandle.cpp` / `minidump.h`：信号、dump、崩溃相关入口。
- `gameserver/ptcregister.cpp` / `protocol/`：协议注册和协议处理分组。

## 大模块

- `scene/`：场景实例、场景管理、scene handler、AOI、队伍、PVE、网格、事件。
- `level/`：关卡对象、刷怪/触发器、关卡脚本桥、地图加载、剧情/任务事件。
- `unit/`：战斗单位基类、玩家战斗单位、敌人、属性、移动、技能、状态、同步。
- `combat/`：战斗工具、目标管理、攻击者管理、伤害效果、战斗组、导航/巡逻。
- `buff/`：Buff 容器、效果、触发器、生命周期、属性变化和技能联动。
- `ai/`：AI agent、节点、目标选择、技能节点、关卡/空间节点。
- `tableload/`：配置表加载和查询，技能、Buff、场景、关卡、怪物、AI 等配置入口。
- `role/`：玩家角色、角色管理、战斗角色、角色技能、队伍/切换/伙伴。
- `network/` + `protocol/`：连接、KCP、监听、协议分组和发包。
- `xecs/`：gameserver 侧集成 XEcs 的适配/工具。

## 常见排查入口

- crash 栈：先用 `resolve_frame` 定位栈帧，再按路径命中具体模块卡。
- 宕机日志：先用 `find_log_source` 定位打印点；如果含 `Check cond`、`ASSERT`、`failed`，再用 `find_assert_context`。
- 配置问题：通常先看 `tableload/` 对应 config，再看使用点所在业务模块。
- 功能实现：先确认入口是协议、场景事件、关卡脚本、AI 节点还是定时器，再沿调用链查。

## 推荐排查顺序

1. 从问题提取模块词、符号、日志关键字、配置表名和 ID。
2. 用知识卡确定候选模块和入口文件。
3. 用工具核实当前代码：`find_symbol`、`grep_code`、`read_file`。
4. 如果是日志/断言，优先从打印点和断言上下文反推业务链路。
5. 回答时区分“已由代码确认”和“需要配置数据确认”。

## 相关卡片

- [配置加载](tableload-config.md)
- [场景框架](scene-framework.md)
- [关卡框架](level-framework.md)
- [单位、属性与技能](unit-skill-attr.md)
- [XEcs 框架](xecs-framework.md)
