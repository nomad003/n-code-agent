---
type: Code Playbook
title: Assert 排障 - gameserver-ai
description: gameserver-ai 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-ai
resource: gameserver/ai/aiutility.cpp
tags: assert, check, outage_log, crash, gameserver, ai
symbols: GET_REAL_INDEX
logs: Index out of range: | , AIID %u, RawIndex %d, RealIndex %d
asserts: CHECK_COND_WITH_LOG
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-ai

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-ai` |
| 条目数 | 1 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/ai/aiutility.cpp:182` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-ai-aiutility-cpp-182-check_cond_with_log-d2d8f1f3` |
| 函数 | `GET_REAL_INDEX` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `false` |
| 日志/提示 | `Index out of range: \| , AIID %u, RawIndex %d, RealIndex %d` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/ai/aiutility.cpp`，关键条件 `Index out of range: | , AIID %u, RawIndex %d, RealIndex %d`。 |
| 上下文 | 文件 `gameserver/ai/aiutility.cpp`，函数 `GET_REAL_INDEX`，附近日志 `Index out of range: | , AIID %u, RawIndex %d, RealIndex %d`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`Index out of range: | , AIID %u, RawIndex %d, RealIndex %d`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/ai/aiutility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
177: GET_REAL_INDEX(configname)\
179: #define GET_REAL_INDEX(configname)\
180: if (realIndex < 0)\
181: {\
182: CHECK_COND_WITH_LOG(false, LogError("Index out of range: "#configname", AIID %u, RawIndex %d, RealIndex %d", pAgent->GetRowData().ID(), index, realIndex));\
183: }
185: #define TRYSET_VALUE_FROM_ROWDATA(key, configname, sequenceidx)\
186: pAgent->GetMemory()->GetMainData()->TrySet(key, rowData.configname()[realIndex][sequenceidx])
```
