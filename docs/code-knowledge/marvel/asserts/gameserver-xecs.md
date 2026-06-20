---
type: Code Playbook
title: Assert 排障 - gameserver-xecs
description: gameserver-xecs 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/gameserver-xecs
resource: gameserver/xecs/XFacility.cpp, gameserver/xecs/utility2math.h, gameserver/xecs/utility2quaternion.hpp, gameserver/xecs/xvector3.h
tags: assert, check, outage_log, crash, gameserver, xecs
symbols: XFacility::fetch_hit_header_hash, XFacility::fetch_hit_header_addr, XFacility::fetch_hit_load_addr, _CheckConsistency, XFacility::report_error, Vector3
logs: unit:%llu fetch hit:%d present conf not exist, unit:%llu fetch state:%d present conf not exist, %s
asserts: CHECK_COND_RETURN, CHECK_COND, CHECK_COND_WITH_LOG, assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - gameserver-xecs

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `gameserver-xecs` |
| 条目数 | 11 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `gameserver/xecs/XFacility.cpp:438` `CHECK_COND_RETURN`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-438-check_cond_return-cbca28a2` |
| 函数 | `XFacility::fetch_hit_header_hash` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `unit:%llu fetch hit:%d present conf not exist` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `unit:%llu fetch hit:%d present conf not exist`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `XFacility::fetch_hit_header_hash`，附近日志 `unit:%llu fetch hit:%d present conf not exist`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`unit:%llu fetch hit:%d present conf not exist`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
433: }
434: auto* conf = u->GetConf().GetPresentConf();
435: if (nullptr == conf)
436: {
437: LogError("unit:%llu fetch hit:%d present conf not exist", u->GetID(), hash);
438: CHECK_COND_RETURN(false, 0);
439: }
441: return xecs::hash((conf->Prefab + "_hit_header").c_str());
442: }
```

### `gameserver/xecs/XFacility.cpp:455` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-455-check_cond-ffc67c8a` |
| 函数 | `XFacility::fetch_hit_header_addr` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `unit:%llu fetch state:%d present conf not exist` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `unit:%llu fetch state:%d present conf not exist`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `XFacility::fetch_hit_header_addr`，附近日志 `unit:%llu fetch state:%d present conf not exist`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`unit:%llu fetch state:%d present conf not exist`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
450: }
451: auto* conf = u->GetConf().GetPresentConf();
452: if (nullptr == conf)
453: {
454: LogError("unit:%llu fetch state:%d present conf not exist", u->GetID(), hash);
455: CHECK_COND(false);
456: return;
457: }
458: addr.assign(CGsDir::HitDir() + conf->BehitLocation + conf->Prefab + "_hit_header.bytes");
460: LogDebug("unit ecs:%llu load hit header:%s", ecs, addr.c_str());
```

### `gameserver/xecs/XFacility.cpp:474` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-474-check_cond-ffc67c8a` |
| 函数 | `XFacility::fetch_hit_load_addr` |
| 类型 | `config_or_table_missing` |
| 条件 | `false` |
| 日志/提示 | `unit:%llu fetch hit:%d present conf not exist` |
| 对应问题 | 配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `unit:%llu fetch hit:%d present conf not exist`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `XFacility::fetch_hit_load_addr`，附近日志 `unit:%llu fetch hit:%d present conf not exist`。 |
| 为什么出问题 | 运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。 直接线索：`unit:%llu fetch hit:%d present conf not exist`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。
- 检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。
- 修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。

附近代码：

```text
469: }
470: auto* conf = u->GetConf().GetPresentConf();
471: if (nullptr == conf)
472: {
473: LogError("unit:%llu fetch hit:%d present conf not exist", u->GetID(), hash);
474: CHECK_COND(false);
475: return;
476: }
478: const std::string& hit = XEntityInfoLibrary::Instance()->GetHit(hash);
479: addr.assign(CGsDir::HitDir() + conf->BehitLocation + hit + ".bytes");
```

### `gameserver/xecs/XFacility.cpp:1591` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-1591-check_cond-fda1a6c5` |
| 函数 | `_CheckConsistency` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `data.caster() == caster` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `data.caster() == caster`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `_CheckConsistency`，附近代码 `1592: CHECK_COND(data.skillid() == skillID);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`data.caster() == caster`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `data.caster() == caster` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1586: }
1588: PtcG2C_ProjectDamageNtf oPDPtc;
1589: void _CheckConsistency(KKSG::ProjectDamageData& data, uint64_t caster, uint32_t skillID, uint32_t hitPoint)
1590: {
1591: CHECK_COND(data.caster() == caster);
1592: CHECK_COND(data.skillid() == skillID);
1593: CHECK_COND(data.hitpoint() == hitPoint);
1594: }
1596: int XFacility::project_damage(uint64_t ecs_caster, uint64_t ecs_target, uint32_t skillID, uint32_t hitPoint, uint32_t token, int hurtpart, bool is_parry)
```

### `gameserver/xecs/XFacility.cpp:1592` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-1592-check_cond-b4198ccc` |
| 函数 | `_CheckConsistency` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `data.skillid() == skillID` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `data.skillid() == skillID`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `_CheckConsistency`，附近代码 `1593: CHECK_COND(data.hitpoint() == hitPoint);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`data.skillid() == skillID`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `data.skillid() == skillID` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1588: PtcG2C_ProjectDamageNtf oPDPtc;
1589: void _CheckConsistency(KKSG::ProjectDamageData& data, uint64_t caster, uint32_t skillID, uint32_t hitPoint)
1590: {
1591: CHECK_COND(data.caster() == caster);
1592: CHECK_COND(data.skillid() == skillID);
1593: CHECK_COND(data.hitpoint() == hitPoint);
1594: }
1596: int XFacility::project_damage(uint64_t ecs_caster, uint64_t ecs_target, uint32_t skillID, uint32_t hitPoint, uint32_t token, int hurtpart, bool is_parry)
1597: {
```

### `gameserver/xecs/XFacility.cpp:1593` `CHECK_COND`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-1593-check_cond-22e132db` |
| 函数 | `_CheckConsistency` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `data.hitpoint() == hitPoint` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `data.hitpoint() == hitPoint`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `_CheckConsistency`，附近代码 `1593: CHECK_COND(data.hitpoint() == hitPoint);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`data.hitpoint() == hitPoint`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `data.hitpoint() == hitPoint` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1588: PtcG2C_ProjectDamageNtf oPDPtc;
1589: void _CheckConsistency(KKSG::ProjectDamageData& data, uint64_t caster, uint32_t skillID, uint32_t hitPoint)
1590: {
1591: CHECK_COND(data.caster() == caster);
1592: CHECK_COND(data.skillid() == skillID);
1593: CHECK_COND(data.hitpoint() == hitPoint);
1594: }
1596: int XFacility::project_damage(uint64_t ecs_caster, uint64_t ecs_target, uint32_t skillID, uint32_t hitPoint, uint32_t token, int hurtpart, bool is_parry)
1597: {
1598: HurtInfo hurtInfo;
```

### `gameserver/xecs/XFacility.cpp:1819` `CHECK_COND_WITH_LOG`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xfacility-cpp-1819-check_cond_with_log-7a50ca09` |
| 函数 | `XFacility::report_error` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `%s` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/XFacility.cpp`，关键条件 `%s`。 |
| 上下文 | 文件 `gameserver/xecs/XFacility.cpp`，函数 `XFacility::report_error`，附近日志 `%s`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`%s`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/XFacility.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1814: LogError("%s", error.c_str());
1815: }
1817: void XFacility::report_error(const std::string& error)
1818: {
1819: CHECK_COND_WITH_LOG(false, LogError("%s", error.c_str()));
1820: }
1822: void XFacility::report_warning(const std::string& warning)
1823: {
1824: LogWarn("%s", warning.c_str());
```

### `gameserver/xecs/utility2math.h:28` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-utility2math-h-28-assert-1a4f9291` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `!_isnan(x)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/utility2math.h`，关键条件 `!_isnan(x)`。 |
| 上下文 | 文件 `gameserver/xecs/utility2math.h`，附近代码 `28: #define XIsNaN(x) (assert(!_isnan(x)))`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`!_isnan(x)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/utility2math.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!_isnan(x)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
23: #define XNotAngle FLT_MAX
24: #define XNRound (XRound * XTrigonometricPrecision)
25: #define XDeg2Rad(x) ((x) * 0.0174533f)
26: #define XRad2Deg(x) ((x) * 57.295780f)
27: #define XRoundToCircle(x) (float(((int)(x) % (int)XRound) + (float)((x) - (int)(x))))
28: #define XIsNaN(x) (assert(!_isnan(x)))
29: #define XClamp(x, minValue, maxValue) (std::max(std::min((x), (maxValue)), (minValue)))
30: #define XIsInteger(x) ((std::fabs(x - (int)x) < FLT_EPSILON) || (std::fabs(x - (int)x) > (1 - FLT_EPSILON)))
32: inline float XSin[int(XNRound + 1)];
33: inline float XCos[int(XNRound + 1)];
```

### `gameserver/xecs/utility2quaternion.hpp:67` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-utility2quaternion-hpp-67-assert-b8883498` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `s != 0` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/utility2quaternion.hpp`，关键条件 `s != 0`。 |
| 上下文 | 文件 `gameserver/xecs/utility2quaternion.hpp`，附近代码 `68: return q * (1.0f / s);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`s != 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/utility2quaternion.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `s != 0` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
62: q.w *= s;
63: }
65: inline Quaternion operator /(const Quaternion& q, float s)
66: {
67: assert(s != 0);
68: return q * (1.0f / s);
69: }
71: inline void operator /=(Quaternion& q, float s)
72: {
```

### `gameserver/xecs/utility2quaternion.hpp:73` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-utility2quaternion-hpp-73-assert-b8883498` |
| 函数 | `-` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `s != 0` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/utility2quaternion.hpp`，关键条件 `s != 0`。 |
| 上下文 | 文件 `gameserver/xecs/utility2quaternion.hpp`，附近代码 `74: q *= (1.0f / s);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`s != 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/utility2quaternion.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `s != 0` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
68: return q * (1.0f / s);
69: }
71: inline void operator /=(Quaternion& q, float s)
72: {
73: assert(s != 0);
74: q *= (1.0f / s);
75: }
77: inline void operator *=(Quaternion& q1, const Quaternion& q2) { q1 = q1 * q2; }
```

### `gameserver/xecs/xvector3.h:43` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `gameserver-xecs-xvector3-h-43-assert-bc110b4d` |
| 函数 | `Vector3` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `gameserver/xecs/xvector3.h`，关键条件 `false`。 |
| 上下文 | 文件 `gameserver/xecs/xvector3.h`，函数 `Vector3`，附近代码 `43: default: assert(false); break;`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `gameserver/xecs/xvector3.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
38: {
39: case 0: return x;
40: case 1: return y;
41: case 2: return z;
42: #ifdef _Server_Ecs_
43: default: assert(false); break;
44: #endif
45: #ifdef _Client_Ecs_
46: default: return 0;
47: #endif
48: }
```
