---
type: Code Playbook
title: Assert 排障 - gameserver-role
description: gameserver-role 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-role
resource: gameserver/role/role.cpp
tags: assert, check, outage_log, crash, gameserver, role
symbols: Role::EnterScene
logs:
asserts: CHECK_COND_NORETURN
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-role

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-role` |
| 条目数 | 1 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/role/role.cpp:458` `CHECK_COND_NORETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-role-role-cpp-458-check_cond_noreturn-5e07ae03` |
| 函数 | `Role::EnterScene` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/role/role.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/role/role.cpp`，函数 `Role::EnterScene`，附近代码 `459: }`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/role/role.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
453: RoleLogErr(this, "enter scene:[%llu %u] [current scene:%llu %u is not NULL]"
454: , scene->GetSceneUID(), scene->GetSceneID(), m_current_scene->GetSceneUID(), m_current_scene->GetSceneID());
455: LeaveScene();
456: m_combat_group.UnInit();
458: CHECK_COND_NORETURN(false);
459: }
461: // current scene
462: SetSceneFlag(ROLE_FLAG_IN_SCENE);
```
