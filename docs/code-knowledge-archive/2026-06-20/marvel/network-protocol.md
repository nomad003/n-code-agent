---
type: Code Module
title: 网络与协议
description: network 连接层、protocol 分组、发包入口和协议问题排查路径。
repo: marvel
module: gameserver/network + gameserver/protocol
resource: gameserver/network
tags: network, protocol, kcp, clientlink, sendonly, ptc, 协议, 网络
symbols: ClientLink, KcpLink, LinkListener
logs: protocol, client, kcp
asserts: CHECK_COND
question_types: crash_stack, outage_log, feature_impl
part_of: gameserver-overview.md
supplements: role-framework.md, scene-framework.md
updated_at: 2026-06-18
---

# 网络与协议

这张卡用于回答“协议处理入口在哪”“服务器怎么给客户端发包”“网络连接问题怎么排查”。

## 入口文件

- `gameserver/network/clientlink.cpp` / `.h`：客户端连接。
- `gameserver/network/kcplink.cpp` / `.h`：KCP 连接。
- `gameserver/network/linklistener.cpp` / `.h`：监听入口。
- `gameserver/protocol/sendonly.cpp`：只发协议/发包辅助。
- `gameserver/ptcregister.cpp` / `.h`：协议注册。
- `gameserver/protocol/*/`：按业务域拆分的协议目录，例如 `scene`、`unit`、`skill`、`role`、`team`、`gm`。

## 核心职责

- 管理客户端连接和底层传输。
- 注册协议并按业务目录组织协议处理。
- 将玩家输入/请求转发到 `role`、`scene`、`level`、`unit` 等业务模块。
- 将服务器状态变化同步给客户端。

## 常见链路

- 客户端请求：连接层收到包，协议处理分发到业务模块。
- 服务器推送：业务模块调用协议发送接口，经 `sendonly` 或具体 protocol 发送给客户端。
- 场景同步：`scene` / `unit/sync` 与 protocol 目录联动。

## 常见提问

- “某个协议在哪里处理？”
- “服务端哪个地方发这个包？”
- “客户端操作如何进入场景/角色/技能逻辑？”
- “连接断开或 KCP 问题怎么查？”

## 排查顺序

1. 用协议名或消息名在 `gameserver/protocol` 和 `ptcregister` 搜。
2. 找到处理函数后跳到对应业务模块。
3. 发包问题查 `sendonly.cpp` 和具体 protocol 文件。
4. 连接层问题查 `clientlink`、`kcplink`、`linklistener`。

## 相关卡片

- [角色框架](role-framework.md)
- [场景框架](scene-framework.md)
- [单位、属性与技能](unit-skill-attr.md)
