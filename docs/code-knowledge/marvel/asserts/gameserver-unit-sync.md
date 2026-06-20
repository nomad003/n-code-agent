---
type: Code Playbook
title: Assert 排障 - gameserver-unit-sync
description: gameserver-unit-sync 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-unit-sync
resource: gameserver/unit/sync/XActionSender.cpp
tags: assert, check, outage_log, crash, gameserver, unit, sync
symbols: XActionSender::PackageSyncData
logs:
asserts: CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-unit-sync

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-unit-sync` |
| 条目数 | 1 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/unit/sync/XActionSender.cpp:47` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-unit-sync-xactionsender-cpp-47-check_cond_noreturn-724c87f8` |
| 函数 | `XActionSender::PackageSyncData` |
| 类型 | `numeric_or_position_invalid` |
| 条件 | `(net->pos->x) > -FLT_EPSILON && (net->pos->y) > -FLT_EPSILON && (net->pos->z) > -FLT_EPSILON` |
| 日志/提示 | `-` |
| 对应问题 | 坐标、比例或数值非法，可能是负坐标、NaN、0 比例或物理数据异常。 触发点 `gameserver/unit/sync/XActionSender.cpp`，关键条件 `(net->pos->x) > -FLT_EPSILON && (net->pos->y) > -FLT_EPSILON && (net->pos->z) > -FLT_EPSILON`。 |
| 上下文 | 文件 `gameserver/unit/sync/XActionSender.cpp`，函数 `XActionSender::PackageSyncData`，附近代码 `48: //set face`。 |
| 为什么出问题 | 上游传入非法数值，常见是坐标未初始化、比例为 0、NaN 或负值。 直接线索：`(net->pos->x) > -FLT_EPSILON && (net->pos->y) > -FLT_EPSILON && (net->pos->z) > -FLT_EPSILON`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/unit/sync/XActionSender.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `(net->pos->x) > -FLT_EPSILON && (net->pos->y) > -FLT_EPSILON && (net->pos->z) > -FLT_EPSILON` 由谁赋值或返回。
- 打印上游坐标/比例/向量来源，检查初始化、单位转换和物理碰撞数据。
- 修正非法数据源；对外部输入增加范围校验。

附近代码：

```text
42: //set id
43: pdata->set_entityid(p->GetID());
44: //common info
45: int common = 0;
47: CHECK_COND_NORETURN((net->pos->x) > -FLT_EPSILON && (net->pos->y) > -FLT_EPSILON && (net->pos->z) > -FLT_EPSILON);
48: //set face
49: pdata->set_face(net->dir);
50: pdata->set_posx((UINT32)(floor(net->pos->x * 10000)));
51: pdata->set_posy((UINT32)(floor(net->pos->y * 10000)));
52: pdata->set_posz((UINT32)(floor(net->pos->z * 10000)));
```
