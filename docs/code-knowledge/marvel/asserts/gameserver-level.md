---
type: Code Playbook
title: Assert 排障 - gameserver-level
description: gameserver-level 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-level
resource: gameserver/level/LevelMgr.cpp, gameserver/level/info/LevelWall.cpp
tags: assert, check, outage_log, crash, gameserver, level
symbols: LevelMgr::Init, LevelMgr::Update, GetPinType, ParseLuaStack, LoadTrigger, LevelWall::InitNew, LevelWall::AddLevelWall, LevelWall::ExpireTempWall
logs: Current luastate is set to end., array is designed for vec3 only now
asserts: ASSERT, assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-level

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-level` |
| 条目数 | 10 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/level/LevelMgr.cpp:45` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-45-assert-7f7af461` |
| 函数 | `LevelMgr::Init` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，函数 `LevelMgr::Init`，附近代码 `46: return false;`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
40: m_oNewLuaStateS.emplace_back(pLuaLevelState);
41: m_pLuaState = pLuaLevelState->GetLuaS();
43: if (!m_pLuaState->Init())
44: {
45: ASSERT(false);
46: return false;
47: }
48: //m_oLuaState.Init();
49: AddBasicGameRules();
50: //LoadAllScript();
```

### `gameserver/level/LevelMgr.cpp:96` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-96-assert-7f7af461` |
| 函数 | `LevelMgr::Update` |
| 类型 | `state_or_skill_invalid` |
| 条件 | `false` |
| 日志/提示 | `Current luastate is set to end.` |
| 对应问题 | 状态机或技能数据不符合当前流程要求。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `Current luastate is set to end.`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，函数 `LevelMgr::Update`，附近日志 `Current luastate is set to end.`。 |
| 为什么出问题 | 当前状态、技能类型或配置不允许进入该分支。 直接线索：`Current luastate is set to end.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。
- 确认状态切换时序和技能类型是否符合代码分支要求。

附近代码：

```text
91: if (pLevelstate->IsEnd())
92: {
93: if (m_pLuaState == pLevelstate->GetLuaS())
94: {
95: LogError("Current luastate is set to end.");
96: ASSERT(false);
97: }
98: LogInfo("A out-of-date level lua state is empty. try delete it.");
99: delete pLevelstate;
100: it = m_oNewLuaStateS.erase(it);
101: }
```

### `gameserver/level/LevelMgr.cpp:350` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-350-assert-2b205569` |
| 函数 | `GetPinType` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，函数 `GetPinType`，附近代码 `350: assert(false);`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
345: }
346: else if (strcmp(pinType, "str") == 0)
347: {
348: return KKSG::PinType::PinType_Str;
349: }
350: assert(false);
351: return KKSG::PinType::PinType_Float;
352: }
354: static void ParseLuaStack(lua_State* L, KKSG::LevelNotice& notice, int nArgsRead, int nArgs, int version = 1)
355: {
```

### `gameserver/level/LevelMgr.cpp:423` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-423-assert-2b205569` |
| 函数 | `ParseLuaStack` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，函数 `ParseLuaStack`，附近代码 `423: assert(false);`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
418: pVec3->set_y((*ptr_to_vec)->y);
419: pVec3->set_z((*ptr_to_vec)->z);
420: }
421: else
422: {
423: assert(false);
424: }
425: }
426: }
427: else if (strcmp(pinType, "int") == 0)
428: {
```

### `gameserver/level/LevelMgr.cpp:494` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-494-assert-7f7af461` |
| 函数 | `-` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `array is designed for vec3 only now` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `array is designed for vec3 only now`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，附近日志 `array is designed for vec3 only now`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`array is designed for vec3 only now`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
489: //break;
490: //case KKSG::PinType::PinType_Str:
491: //break;
492: default:
493: LogError("array is designed for vec3 only now");
494: ASSERT(false);
495: break;
496: }
497: }
498: }
499: }
```

### `gameserver/level/LevelMgr.cpp:737` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-737-assert-2b205569` |
| 函数 | `-` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，附近代码 `737: assert(false);`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
732: pVec3->set_y((*ptr_to_vec)->y);
733: pVec3->set_z((*ptr_to_vec)->z);
734: }
735: else
736: {
737: assert(false);
738: }
739: }
740: else if (strcmp(pinType, "int") == 0)
741: {
742: pData->set_type(KKSG::PinType::PinType_Int);
```

### `gameserver/level/LevelMgr.cpp:1349` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-levelmgr-cpp-1349-assert-30d28ab9` |
| 函数 | `LoadTrigger` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `event.id <= EVENTID_MAX` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `gameserver/level/LevelMgr.cpp`，关键条件 `event.id <= EVENTID_MAX`。 |
| 上下文 | 文件 `gameserver/level/LevelMgr.cpp`，函数 `LoadTrigger`，附近代码 `1349: ASSERT(event.id <= EVENTID_MAX);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`event.id <= EVENTID_MAX`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/LevelMgr.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `event.id <= EVENTID_MAX` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
1344: for (int jj = 0; jj < earray.Size(); ++jj)
1345: {
1346: TriggerEvent event;
1347: JsonUtil::GetValue(earray, jj, v);
1348: JsonUtil::GetValue(*v, "id", event.id);
1349: ASSERT(event.id <= EVENTID_MAX);
1350: int eventType = 0;
1351: //JsonUtil::GetValue(*v, "eventType", eventType);
1352: //event.eventType = (TriggerEventType)eventType;
1353: //JsonUtil::GetValue(*v, "eventArgs", event.args);
1354: //JsonUtil::GetValue(*v, "buffArgs", event.buffArgs);
```

### `gameserver/level/info/LevelWall.cpp:47` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-info-levelwall-cpp-47-assert-7f7af461` |
| 函数 | `LevelWall::InitNew` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/info/LevelWall.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/info/LevelWall.cpp`，函数 `LevelWall::InitNew`，附近代码 `48: return;`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/info/LevelWall.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
42: {
43: m_pSpawner = pSpawner;
45: if (!levelFullData || !m_pSpawner)
46: {
47: ASSERT(false);
48: return;
49: }
51: m_levelWallInfo.m_defaultWall.uID = (pSpawner->GetMainLevel() ? pSpawner->GetMainLevel()->GetUID() : 0);
52: InitWallCluster(m_levelWallInfo.m_defaultWall, levelFullData);
```

### `gameserver/level/info/LevelWall.cpp:59` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-info-levelwall-cpp-59-assert-7f7af461` |
| 函数 | `LevelWall::AddLevelWall` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/info/LevelWall.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/info/LevelWall.cpp`，函数 `LevelWall::AddLevelWall`，附近代码 `60: return;`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/info/LevelWall.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
55: void LevelWall::AddLevelWall(Level* pLevel, const std::shared_ptr<LevelEditorData>& levelFullData)
56: {
57: if (!levelFullData || !m_pSpawner)
58: {
59: ASSERT(false);
60: return;
61: }
63: auto& wall = levelFullData->LevelWallList;
64: bool isPlatLevel = pLevel->IsPlat();
```

### `gameserver/level/info/LevelWall.cpp:377` `ASSERT`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-level-info-levelwall-cpp-377-assert-7f7af461` |
| 函数 | `LevelWall::ExpireTempWall` |
| 类型 | `unexpected_branch` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | 执行到了代码认为不应该到达的分支。 触发点 `gameserver/level/info/LevelWall.cpp`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/level/info/LevelWall.cpp`，函数 `LevelWall::ExpireTempWall`，附近代码 `378: return;`。 |
| 为什么出问题 | 枚举值、类型分支或配置组合没有被当前代码支持。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/level/info/LevelWall.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认枚举、类型或配置值是否新增但代码没有处理。
- 补齐对应分支，或修正配置不要落到未支持类型。

附近代码：

```text
372: return;
373: wallCluster& cluster = platUID ? m_levelWallInfo.m_platUID2WallCluster[platUID] : m_levelWallInfo.m_defaultWall;
375: if (!CheckWallState(cluster, index, true))
376: {
377: ASSERT(false);
378: return;
379: }
381: XLevelWallInfo& info = cluster.m_levelWallInfos[index];
382: info.enable = false;
```
