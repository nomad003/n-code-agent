# 优化路线图

记录已落地的优化、明确舍弃的设计、以及后续可选方向。给后续维护者一个"做了什么、为什么、接下来可做什么"的全景。

## 一、已落地

### custom 后端：借鉴 OpenHands 的精简实现

参考 OpenHands `CodeActAgent` 架构，只取对「只读代码问答」最高回报的四项（详见 [architecture.md](architecture.md) 的 custom 后端章节）：

| 优化 | 对应 OpenHands | 价值 |
|------|---------------|------|
| Action/Observation 事件模型 + 集中消息渲染（`events.py` / `CodeAgent._build_messages`） | `ConversationMemory.process_events` | 可维护性：tool_call ↔ tool-result 配对集中一处 |
| stuck 检测：连续相同工具调用提前收尾（`STUCK_REPEAT_THRESHOLD`） | `StuckDetector` | 防反复 grep 同一 pattern / 撞同一错误烧 token |
| LLM 重试：限流/超时/服务端错误指数退避（`LLM_NUM_RETRIES`） | `RetryMixin` | 健壮性：代理抽风不再直接 500 |
| 确定性观测遮蔽：仅保留最近 N 次完整工具输出（`OBS_KEEP_FULL`） | `ObservationMaskingCondenser` | 长会话 context 不膨胀，且不烧 LLM |

### 服务化与运维

- 三个对等入口（REST `main.py` / MCP `mcp_server.py` / CLI `cli.py`），都走同一个 `agent.answer()`。
- `/ask` 失败返回干净 502（非 500 栈），失败不入缓存。
- MCP 调用日志 → `logs/mcp.log`（轮转）；`serve.sh`/`mcp.sh` 支持 `start/stop/restart/status`。
- 全量环境变量配置（`.env` / `.env.example`）、离线单元测试套件（见 [testing.md](testing.md)）。

## 二、明确舍弃（对只读问答属过度设计）

这些是 OpenHands 为「可写、可执行任意代码、多 agent 协作」场景所做，本服务只读、单进程、无副作用，**不引入**：

| 舍弃项 | OpenHands 中的作用 | 为何不需要 |
|--------|-------------------|-----------|
| Runtime 沙箱 / Docker / ActionExecutionClient-Server | 隔离执行任意代码 | 只读、不执行，本地函数调用即可 |
| EventStream 事件总线 + 订阅者 + 持久化 | 解耦 controller/runtime/memory/UI 并发协作 | 单进程一个 `list[Event]` 足够 |
| 多 agent 委派（`AgentDelegateAction`） | 复杂任务拆分 | 单一只读 agent 用不到 |
| Memory / microagents / RecallAction | 触发词注入 prompt | 需要时一次预检索即可 |
| LLM 式压缩（`LLMSummarizingCondenser`） | 用额外 LLM 调用压历史 | 短问答收益不抵成本；已用确定性遮蔽替代 |
| 12 态状态机 + 确认模式 | 危险写/执行的人类把关 | 只读无副作用，三态足够 |

> 原则：保持工具层（`tools.py`）是唯一接触文件系统的层，复杂度只在真正需要时引入。

## 三、后续可选方向

按"价值 / 成本"粗排，未承诺、未排期，取用时再评估。

### A. 方案 2：离线索引（最大功能跃迁）

当前每次查询都走 LLM tool-call。下一阶段做离线索引：tree-sitter AST → SQLite 符号表 + 向量库，**精确查询（如"X 类定义在哪"）直接返回，不走 LLM**。
- 关键：`tools.py` 已刻意做成唯一接触文件的层 —— 索引可顶替这些实现而 `agent.py` 不动。
- 价值：高（延迟、成本大降）；成本：高（新建索引管线 + 增量更新）。

### B. 服务治理

- `/ask` 并发上限 / 排队 / 单请求超时（当前无限制，agent 循环可能长时间占用）。
- MCP / REST 的鉴权（当前无 token 校验，仅可信内网）。
- 常驻：systemd unit（开机自启 + 崩溃重启），替代当前 `nohup`/前台。
- 价值：中（生产化必需）；成本：低-中。

### C. SDK 后端能力对齐

custom 后端的 stuck / 遮蔽 / 重试，SDK 后端目前依赖框架自身机制，未对齐。若 SDK 后端要正式使用，评估是否需要补齐可观测性（调用日志）与一致的限额行为。
- 价值：中（取决于是否真用 SDK 后端）；成本：中。

### D. 缓存增强

当前 `/ask` 是进程内字典缓存、重启即失。可选：持久化缓存（SQLite/Redis）、按 `TARGET_CODE_PATH` 版本失效（代码变了缓存作废）。
- 价值：中；成本：低-中。

### E. 质量评测

建一个小型问答评测集（问题 → 期望涉及的文件/符号），回归时跑，量化"换模型 / 改 prompt / 调限额"对回答质量的影响。
- 价值：中（防回归、支撑调参）；成本：中。

## 四、参考

- OpenHands 架构调研要点见本仓库提交历史与 [architecture.md](architecture.md)。
- 出处：`docs.openhands.dev`、`github.com/OpenHands/OpenHands`（经典 V0 tag 0.19–1.5；当前 main 已重构为 Software Agent SDK）。
