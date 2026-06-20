---
type: Code Playbook
title: Assert 排障 - xecslib-xecs-xsirius-cpp
description: xecslib-xecs-xsirius-cpp 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。
repo: marvel
module: asserts/xecslib-xecs-xsirius-cpp
resource: XEcsLib/XEcs/XSirius.cpp
tags: assert, check, outage_log, crash, xecslib, xecs, xsirius, cpp
symbols: XSirius::setActionRatio
logs: ratio could not be zero.
asserts: assert
question_types: crash_stack, outage_log, feature_impl, config_impl
part_of: index.md
updated_at: 2026-06-20
---

# Assert 排障 - xecslib-xecs-xsirius-cpp

## 卡片说明

| 项 | 内容 |
| --- | --- |
| 分组 | `xecslib-xecs-xsirius-cpp` |
| 条目数 | 1 |
| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |

## Assert 条目

### `XEcsLib/XEcs/XSirius.cpp:1473` `assert`

| 字段 | 内容 |
| --- | --- |
| ID | `xecslib-xecs-xsirius-cpp-1473-assert-78de3a52` |
| 函数 | `XSirius::setActionRatio` |
| 类型 | `ecs_entity_or_component_invalid` |
| 条件 | `ratio > FLT_EPSILON && "ratio could not be zero."` |
| 日志/提示 | `ratio could not be zero.` |
| 对应问题 | ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。 触发点 `XEcsLib/XEcs/XSirius.cpp`，关键条件 `ratio could not be zero.`。 |
| 上下文 | 文件 `XEcsLib/XEcs/XSirius.cpp`，函数 `XSirius::setActionRatio`，附近日志 `ratio could not be zero.`。 |
| 为什么出问题 | Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。 直接线索：`ratio could not be zero.`。 |

排查/解决：

- 先用日志中的文件/函数定位到 `XEcsLib/XEcs/XSirius.cpp`，不要只相信运行时行号；行号可能因版本漂移不准。
- 读取断言前后 30-80 行，确认 `ratio > FLT_EPSILON && "ratio could not be zero."` 由谁赋值或返回。
- 确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。
- 检查 remove/destroy 和 view 遍历是否并发修改同一容器。

附近代码：

```text
1468: attr.parried = false;
1469: }
1470: #endif
1471: void XSirius::setActionRatio(uint64_t id, float ratio)
1472: {
1473: assert(ratio > FLT_EPSILON && "ratio could not be zero.");
1475: Entity e = convertId(id, _fw);
1476: XAttributes& a = _fw.get<XAttributes>(e);
1478: XSystemManager::getInstance().get<XActionSys>()->setActionRatio(_fw, e, a, ratio);
```
