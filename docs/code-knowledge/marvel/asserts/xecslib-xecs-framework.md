---
type: Code Playbook
title: Assert 排障 - xecslib-xecs-framework
description: xecslib-xecs-framework 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/xecslib-xecs-framework
resource: XEcsLib/XEcs/framework/XDelegate.hpp, XEcsLib/XEcs/framework/XEntity.h, XEcsLib/XEcs/framework/XFramework.hpp, XEcsLib/XEcs/framework/XSparseContainer.hpp, XEcsLib/XEcs/framework/XSystem.hpp, XEcsLib/XEcs/framework/XView.hpp, XEcsLib/XEcs/framework/tupleplus.hpp
tags: assert, check, outage_log, crash, xecslib, xecs, framework
symbols: operator, Loan, destroy, assign, remove, current, decltype, get_or_assign, get_actor, generator, on_view_begin, Extract_Complex_Index, get_real, swap, constexpr, get, visit
logs: try to get components failed!, try to get component failed!
asserts: assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - xecslib-xecs-framework

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `xecslib-xecs-framework` |
| 条目数 | 24 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `XEcsLib/XEcs/framework/XDelegate.hpp:70` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xdelegate-hpp-70-assert-d121e735` |
| 函数 | `operator` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `_caller` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XDelegate.hpp`，关键条件 `_caller`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XDelegate.hpp`，函数 `operator`，附近代码 `71: return _caller(_this, std::forward<Args>(args)...);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`_caller`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XDelegate.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `_caller` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
65: _caller = nullptr;
66: }
68: Ret operator()(Args&&... args)
69: {
70: assert(_caller);
71: return _caller(_this, std::forward<Args>(args)...);
72: }
74: template<auto method>
75: void connect() noexcept
```

### `XEcsLib/XEcs/framework/XEntity.h:73` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xentity-h-73-assert-a9ebd85b` |
| 函数 | `Loan` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `LoanType(e) == 0` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XEntity.h`，关键条件 `LoanType(e) == 0`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XEntity.h`，函数 `Loan`，附近代码 `74: return e | ((Entity_Type)loan << 48);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`LoanType(e) == 0`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XEntity.h`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `LoanType(e) == 0` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
68: return (uint32_t)((e & 0x0FFF000000000000) >> 48);
69: }
71: inline static Entity_Type Loan(const Entity_Type e, const uint32_t loan) noexcept
72: {
73: assert(LoanType(e) == 0);
74: return e | ((Entity_Type)loan << 48);
75: }
77: inline static constexpr Entity_Type Identifier(
78: const Entity_Traits::IdentifierSpec id,
```

### `XEcsLib/XEcs/framework/XFramework.hpp:215` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-215-assert-2d62a626` |
| 函数 | `destroy` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `valid(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `valid(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `destroy`，附近代码 `215: assert(valid(e));`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`valid(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `valid(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
210: * the `valid` member function can be used to know if they are still valid
211: * or the entity has been destroyed and potentially recycled.
212: */
213: void destroy(Entity_Type e)
214: {
215: assert(valid(e));
217: family_id type = XEntity::LoanType(e);
219: if (type == 0)
220: {
```

### `XEcsLib/XEcs/framework/XFramework.hpp:253` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-253-assert-8b608b10` |
| 函数 | `assign` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `valid(e)/* && XEntity::LoanType(e) == 0*/` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `valid(e)/* && XEntity::LoanType(e) == 0*/`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `assign`，附近代码 `253: assert(valid(e)/* && XEntity::LoanType(e) == 0*/);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`valid(e)/* && XEntity::LoanType(e) == 0*/`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `valid(e)/* && XEntity::LoanType(e) == 0*/` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
248: * arguments provided.
249: */
250: template<typename Component, typename... Args>
251: inline Component& assign(const Entity_Type e, Args&& ... args)
252: {
253: assert(valid(e)/* && XEntity::LoanType(e) == 0*/);
255: #ifdef _Client_Ecs_
256: #ifdef _WIN32
257: const string& id = (e == null_entity) ? "null_entity" : std::to_string(e);
258: const std::string& msg = "Entity " + id + " assign " + std::string(type_name_traits<Component>::name);
```

### `XEcsLib/XEcs/framework/XFramework.hpp:275` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-275-assert-2d62a626` |
| 函数 | `remove` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `valid(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `valid(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `remove`，附近代码 `277: #ifdef _Client_Ecs_`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`valid(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `valid(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
270: }
272: template<typename Component>
273: void remove(const Entity_Type e)
274: {
275: assert(valid(e));
277: #ifdef _Client_Ecs_
278: #ifdef _WIN32
279: const string& id = (e == null_entity) ? "null_entity" : std::to_string(e);
280: const std::string& msg = "Entity " + id + " remove " + std::string(type_name_traits<Component>::name);
```

### `XEcsLib/XEcs/framework/XFramework.hpp:335` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-335-assert-68820d78` |
| 函数 | `current` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `idx < _entities.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `idx < _entities.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `current`，附近代码 `335: assert(idx < _entities.size());`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`idx < _entities.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `idx < _entities.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
330: * potentially recycled
331: */
332: Version_Type current(const Entity_Type e) const noexcept
333: {
334: const auto idx = size_t(XEntity::Value(e));
335: assert(idx < _entities.size());
337: return XEntity::Version(_entities[idx]);
338: }
340: /**
```

### `XEcsLib/XEcs/framework/XFramework.hpp:359` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-359-assert-2b261871` |
| 函数 | `decltype` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false && "try to get components failed!"` |
| 日志/提示 | `try to get components failed!` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `try to get components failed!`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `decltype`，附近日志 `try to get components failed!`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`try to get components failed!`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "try to get components failed!"` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
354: #ifdef _WIN32
355: const string& id = (e == null_entity) ? "null_entity" : std::to_string(e);
356: const std::string& msg = id + " get " + ((std::string(type_name_traits<Component>::name) + ", ") + ...);
357: win_assert(false, msg);
358: #else
359: assert(false && "try to get components failed!");
360: #endif
361: }
363: if constexpr (sizeof...(Component) == 1)
364: {
```

### `XEcsLib/XEcs/framework/XFramework.hpp:382` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-382-assert-be251171` |
| 函数 | `decltype` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false && "try to get component failed!"` |
| 日志/提示 | `try to get component failed!` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `try to get component failed!`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `decltype`，附近日志 `try to get component failed!`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`try to get component failed!`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false && "try to get component failed!"` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
377: {
378: #ifdef _WIN32
379: const string& id = (e == null_entity) ? "null_entity" : std::to_string(e);
380: win_assert(false, id + " get " + std::string(type_name_traits<Component>::name));
381: #else
382: assert(false && "try to get component failed!");
383: #endif
384: }
385: return static_cast<Pool_Wrapper<Component>*>(_pools[type]._pool)->get(e);
386: }
```

### `XEcsLib/XEcs/framework/XFramework.hpp:391` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-391-assert-2d62a626` |
| 函数 | `get_or_assign` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `valid(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `valid(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `get_or_assign`，附近代码 `393: auto* pool = assure<Component>();`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`valid(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `valid(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
386: }
388: template<typename Component, typename... Args>
389: Component& get_or_assign(const Entity_Type e, Args&&... args) noexcept
390: {
391: assert(valid(e));
393: auto* pool = assure<Component>();
394: auto* c = pool->try_get(e);
395: return c ? *c : assign<Component>(e, std::forward<Args>(args)...);
396: }
```

### `XEcsLib/XEcs/framework/XFramework.hpp:472` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-472-assert-b4c96b15` |
| 函数 | `get_actor` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `has(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `has(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `get_actor`，附近代码 `473: return { *this, e };`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`has(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `has(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
467: }
468: }
470: inline XActor<Entity> get_actor(Entity_Type e)
471: {
472: assert(has(e));
473: return { *this, e };
474: //return std::move(a);
475: }
477: /**
```

### `XEcsLib/XEcs/framework/XFramework.hpp:577` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xframework-hpp-577-assert-085f2989` |
| 函数 | `generator` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `e < Entity_Traits::entity_id_mask` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XFramework.hpp`，关键条件 `e < Entity_Traits::entity_id_mask`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XFramework.hpp`，函数 `generator`，附近代码 `577: assert(e < Entity_Traits::entity_id_mask);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`e < Entity_Traits::entity_id_mask`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XFramework.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `e < Entity_Traits::entity_id_mask` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
572: _entities[idx] = e;
573: }
574: else
575: {
576: e = _entities.emplace_back(Entity_Type(size()));
577: assert(e < Entity_Traits::entity_id_mask);
578: }
580: return e;
581: }
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:271` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-271-assert-16969977` |
| 函数 | `on_view_begin` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `!viewing()` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `!viewing()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `on_view_begin`，附近代码 `274: _cursor = begin();`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`!viewing()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!viewing()` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
267: inline bool viewing() const noexcept { return _viewing; }
269: inline void on_view_begin()
270: {
271: assert(!viewing());
272: _viewing = true;
274: _cursor = begin();
275: }
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:311` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-311-assert-44b23a99` |
| 函数 | `Extract_Complex_Index` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `has(e, page, offset)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `has(e, page, offset)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `Extract_Complex_Index`，附近代码 `311: assert(has(e, page, offset));`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`has(e, page, offset)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `has(e, page, offset)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
306: */
307: inline Index_Type get(const Entity_Type e)const noexcept
308: {
309: Complex_Type cx_id = Index(e);
310: Extract_Complex_Index(cx_id)
311: assert(has(e, page, offset));
313: return (Index_Type)_sparse[page][offset];
314: }
316: inline Entity_Type get_real(size_t idx) const noexcept
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:318` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-318-assert-5a350c07` |
| 函数 | `get_real` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `idx < size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `idx < size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `get_real`，附近代码 `319: return _dense[idx];`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`idx < size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `idx < size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
313: return (Index_Type)_sparse[page][offset];
314: }
316: inline Entity_Type get_real(size_t idx) const noexcept
317: {
318: assert(idx < size());
319: return _dense[idx];
320: }
321: /**
322: * @Assigns an entity to a sparse set.
323: *
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:333` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-333-assert-d5385e69` |
| 函数 | `Extract_Complex_Index` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `!has(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `!has(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `Extract_Complex_Index`，附近代码 `334: accommodate(page);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`!has(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `!has(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
328: void create(const Entity_Type e)
329: {
330: Complex_Type cx_id = Index(e);
331: Extract_Complex_Index(cx_id)
333: assert(!has(e));
334: accommodate(page);
336: _sparse[page][offset] = Entity_Type(_dense.size());
337: _dense.emplace_back(e);
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:351` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-351-assert-b4c96b15` |
| 函数 | `destroy` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `has(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `has(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `destroy`，附近代码 `351: assert(has(e));`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`has(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `has(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
346: * An assertion will abort the execution at runtime if the
347: * sparse set doesn't contain the given entity.
348: */
349: virtual void destroy(const Entity_Type e)
350: {
351: assert(has(e));
353: //uint32_t at = get(e);
355: Index_Type from_page, from_offset;
356: Complex_Type cx_id = Index(e);
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:405` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-405-assert-a2547ae3` |
| 函数 | `swap` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `lhs < _dense.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `lhs < _dense.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `swap`，附近代码 `408: auto &&[srcp, srco] = Index(_dense[lhs]);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`lhs < _dense.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `lhs < _dense.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
401: void swap(const size_t lhs, const size_t rhs)
402: {
403: if (lhs == rhs) return;
405: assert(lhs < _dense.size());
406: assert(rhs < _dense.size());
408: auto &&[srcp, srco] = Index(_dense[lhs]);
409: auto &&[dstp, dsto] = Index(_dense[rhs]);
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:406` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-406-assert-945c85a8` |
| 函数 | `swap` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `rhs < _dense.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `rhs < _dense.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `swap`，附近代码 `408: auto &&[srcp, srco] = Index(_dense[lhs]);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`rhs < _dense.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `rhs < _dense.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
401: void swap(const size_t lhs, const size_t rhs)
402: {
403: if (lhs == rhs) return;
405: assert(lhs < _dense.size());
406: assert(rhs < _dense.size());
408: auto &&[srcp, srco] = Index(_dense[lhs]);
409: auto &&[dstp, dsto] = Index(_dense[rhs]);
411: std::swap(_sparse[srcp][srco], _sparse[dstp][dsto]);
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:652` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-652-assert-5ed98502` |
| 函数 | `constexpr` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `Underlying_Type::has(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `Underlying_Type::has(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `constexpr`，附近代码 `652: assert(Underlying_Type::has(e));`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`Underlying_Type::has(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `Underlying_Type::has(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
647: */
648: const Component& get(const Entity_Type e) const noexcept
649: {
650: if constexpr (is_empty_v<Component>)
651: {
652: assert(Underlying_Type::has(e));
653: return _instance;
654: }
655: else
656: return _instance[Underlying_Type::get(e)];
657: }
```

### `XEcsLib/XEcs/framework/XSparseContainer.hpp:796` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsparsecontainer-hpp-796-assert-1daebed1` |
| 函数 | `constexpr` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `index < size` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，关键条件 `index < size`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，函数 `constexpr`，附近代码 `796: assert(index < size);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`index < size`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSparseContainer.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `index < size` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
791: void release_memory_at(const size_t index)
792: {
793: if constexpr (!is_empty_v<Component>)
794: {
795: size_t size = _instance.size();
796: assert(index < size);
798: if (index != size - 1) //some STL container (etc. unordered_map for gcc) not support to move to itself.
799: //Component must implement 'move-assignment' properly in case memory leak
800: _instance[index] = std::move(_instance.back());
801: _instance.pop_back();
```

### `XEcsLib/XEcs/framework/XSystem.hpp:109` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsystem-hpp-109-assert-1cba0076` |
| 函数 | `get` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `f < _system.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSystem.hpp`，关键条件 `f < _system.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSystem.hpp`，函数 `get`，附近代码 `111: return static_cast<S*>(_system[f]);`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`f < _system.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSystem.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `f < _system.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
105: template<typename S>
106: S* get()
107: {
108: auto f = S::family();
109: assert(f < _system.size());
111: return static_cast<S*>(_system[f]);
112: }
114: XSystemBase* get(family_id family)
```

### `XEcsLib/XEcs/framework/XSystem.hpp:116` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xsystem-hpp-116-assert-abbf2157` |
| 函数 | `get` |
| 类型 | `bounds_or_count_invalid` |
| 条件 | `family < _system.size()` |
| 日志/提示 | `-` |
| 对应问题 | 索引、数量或范围不满足代码约束，可能越界或数据结构不完整。 触发点 `XEcsLib/XEcs/framework/XSystem.hpp`，关键条件 `family < _system.size()`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XSystem.hpp`，函数 `get`，附近代码 `118: return _system[family];`。 |
| 为什么出问题 | 数据数量和代码期望不一致，或索引计算越过有效范围。 直接线索：`family < _system.size()`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XSystem.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `family < _system.size()` 由谁赋值或返回。
- 打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。
- 修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。

附近代码：

```text
111: return static_cast<S*>(_system[f]);
112: }
114: XSystemBase* get(family_id family)
115: {
116: assert(family < _system.size());
118: return _system[family];
119: }
121: template<typename S>
```

### `XEcsLib/XEcs/framework/XView.hpp:389` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-xview-hpp-389-assert-b4c96b15` |
| 函数 | `get` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `has(e)` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/XView.hpp`，关键条件 `has(e)`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/XView.hpp`，函数 `get`，附近代码 `390: return _pool->get(e);`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`has(e)`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/XView.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `has(e)` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
384: return find(e) != end();
385: }
387: raw_type& get(const Entity_Type e) const noexcept
388: {
389: assert(has(e));
390: return _pool->get(e);
391: }
393: /**
394: * @Iterates entities and components and applies the given function
```

### `XEcsLib/XEcs/framework/tupleplus.hpp:49` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-framework-tupleplus-hpp-49-assert-b7f02e6b` |
| 函数 | `visit` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `false` |
| 日志/提示 | `-` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/framework/tupleplus.hpp`，关键条件 `false`。 |
| 上下文 | 文件 `XEcsLib/XEcs/framework/tupleplus.hpp`，函数 `visit`，附近代码 `50: };`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`false`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/framework/tupleplus.hpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `false` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
45: template <>
46: struct runtime_impl<0>
47: {
48: template <typename Tuple, typename F>
49: static void visit(Tuple& tup, size_t idx, F& func) { assert(false); }
50: };
52: template <typename... Types, typename F>
53: void tuple_runtime_at(std::tuple<Types...> const& tup, size_t idx, F& func)
54: {
```
