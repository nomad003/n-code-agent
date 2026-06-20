---
type: Reference
title: Assert 排障索引
description: gameserver 与 XEcsLib 核心代码 Assert/CHECK 结构化排障目录。
repo: marvel
module: asserts
resource: XEcsLib/XEcs/XSirius.cpp, XEcsLib/XEcs/ecs/system, XEcsLib/XEcs/ecs/utility, XEcsLib/XEcs/framework, gameserver/ai, gameserver/buff, gameserver/combat, gameserver/level, gameserver/physx, gameserver/role, gameserver/scene, gameserver/tableload, gameserver/unit/attr, gameserver/unit/conf, gameserver/unit/destructible, gameserver/unit/plat
tags: assert, check, outage_log, crash, diagnostic
symbols: XSirius::setActionRatio, getCoolDownLeft, OnRatioChanged, Run, LiteRun, create, destroy, get_final_pos, CalcWarningPosition, transfer, switch_move_type, start, convertId, re_convertId, beginSirius, update_switch, update_condition, update_while, Position, XAppendEndingNode, LoadCommonStateHeader, unmount_timer, Vector3, operator
logs: Check cond, ASSERT, failed, Error Exit
asserts: assert, CHECK_COND_WITH_LOG, CHECK_COND, CHECK_COND_RETURN, ASSERT, CHECK_COND_NORETURN, ASSERT_NO_DUPLICATE_DELEGATE, CHECK_COND_WITH_LOG_RETURN
question_types: crash_stack, outage_log
updated_at: 2026-06-20
---

# Assert 排障索引

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 覆盖范围 | gameserver 与 XEcsLib 核心代码，共 188 个 Assert/CHECK 条目。 |
| 用途 | 用户贴 `Check cond`、`ASSERT`、`failed`、`Error Exit` 或 `file:line` 日志时，先匹配本索引，再读代码上下文确认。 |
| 生成物 | `assert-catalog.json` 是运行时匹配源；本目录 Markdown 是可视化维护卡。 |

## 分组

| 分组 | 数量 | 卡片 |
| --- | ---: | --- |
| `gameserver-ai` | 1 | [gameserver-ai.md](gameserver-ai.md) |
| `gameserver-buff` | 10 | [gameserver-buff.md](gameserver-buff.md) |
| `gameserver-combat` | 4 | [gameserver-combat.md](gameserver-combat.md) |
| `gameserver-level` | 10 | [gameserver-level.md](gameserver-level.md) |
| `gameserver-physx` | 21 | [gameserver-physx.md](gameserver-physx.md) |
| `gameserver-role` | 1 | [gameserver-role.md](gameserver-role.md) |
| `gameserver-scene` | 24 | [gameserver-scene.md](gameserver-scene.md) |
| `gameserver-tableload` | 5 | [gameserver-tableload.md](gameserver-tableload.md) |
| `gameserver-unit-attr` | 4 | [gameserver-unit-attr.md](gameserver-unit-attr.md) |
| `gameserver-unit-conf` | 2 | [gameserver-unit-conf.md](gameserver-unit-conf.md) |
| `gameserver-unit-destructible` | 11 | [gameserver-unit-destructible.md](gameserver-unit-destructible.md) |
| `gameserver-unit-plat` | 5 | [gameserver-unit-plat.md](gameserver-unit-plat.md) |
| `gameserver-unit-skill` | 4 | [gameserver-unit-skill.md](gameserver-unit-skill.md) |
| `gameserver-unit-state` | 7 | [gameserver-unit-state.md](gameserver-unit-state.md) |
| `gameserver-unit-sync` | 1 | [gameserver-unit-sync.md](gameserver-unit-sync.md) |
| `gameserver-unit-unit-cpp` | 5 | [gameserver-unit-unit-cpp.md](gameserver-unit-unit-cpp.md) |
| `gameserver-xecs` | 11 | [gameserver-xecs.md](gameserver-xecs.md) |
| `xecslib-xecs-ecs-system` | 19 | [xecslib-xecs-ecs-system.md](xecslib-xecs-ecs-system.md) |
| `xecslib-xecs-ecs-utility` | 18 | [xecslib-xecs-ecs-utility.md](xecslib-xecs-ecs-utility.md) |
| `xecslib-xecs-framework` | 24 | [xecslib-xecs-framework.md](xecslib-xecs-framework.md) |
| `xecslib-xecs-xsirius-cpp` | 1 | [xecslib-xecs-xsirius-cpp.md](xecslib-xecs-xsirius-cpp.md) |

## 回答要求

当用户日志命中某个 Assert 条目时，答案必须包含：

- 对应问题：这个断言代表哪类业务/数据问题。
- 上下文：文件、函数、附近日志、触发条件。
- 为什么出问题：配置缺失、对象为空、ECS 状态不一致、越界、非法坐标等。
- 怎么解决：按排查顺序给出配置、数据、调用链或代码修复动作。
- 行号说明：运行时行号可能漂移，必须结合函数、日志短语和代码上下文确认。
