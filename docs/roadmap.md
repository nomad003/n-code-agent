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
| Memory / microagents / RecallAction | 触发词注入 prompt | 需要时一次预检索即可（注：若做方案 3 知识沉淀飞轮，会有条件翻回此项，见三-A+） |
| LLM 式压缩（`LLMSummarizingCondenser`） | 用额外 LLM 调用压历史 | 短问答收益不抵成本；已用确定性遮蔽替代 |
| 12 态状态机 + 确认模式 | 危险写/执行的人类把关 | 只读无副作用，三态足够 |

> 原则：保持工具层（`tools.py`）是唯一接触文件系统的层，复杂度只在真正需要时引入。

## 三、后续可选方向

按"价值 / 成本"粗排，未承诺、未排期，取用时再评估。

### A. 方案 2：离线索引（部分落地）

当前每次查询都走 LLM tool-call。离线索引让符号/全文检索从"全库扫描"变成"一次 SQLite 查询"。

**已落地（第一步：符号索引 + 工具加速）**
- `indexer.py`：tree-sitter 解析 C++ → 抽取 class/struct/enum/union/function/method → SQLite `symbols` 表 + FTS5 全文索引（`files_fts`）。每条符号记 `file + line + 文件哈希`（为方案 3 的失效检查预留）。
- `index_query.py`：只读查询层，无索引时返回 `None` 让调用方回退。
- `tools.py`：`find_symbol` 优先查索引（精确、一步命中）；`grep_code` 对「整库 + 纯文本」走 FTS 快路，正则/限定路径回退 live scan。
- 构建：`scripts/index.sh`（真实 gameserver：553 文件 / 9256 符号 / 3.5s / 8M）。`USE_INDEX=0` 可强制回退。

**未做（后续）**
- 向量库 / 语义检索（刻意推迟到方案 3，符号索引不需要它）。
- 增量更新（当前是全量重建）；多语言（当前仅 C++）。
- 在 `/ask` 入口做查询分类、精确问题完全不走 LLM（见下方「入口短路」思路）。
- 价值：高（延迟、成本降）；剩余成本：中（增量更新 + 入口短路）。

### A+. 方案 3：代码知识沉淀闭环（自增强知识飞轮）

把 agent 每次实时解读的结果**沉淀成结构化知识**，下次同类问题检索增强 —— 越用越快、越省 token。是方案 2 的"动态升级版"。

```
用户问题 → agent.answer()（实时解读 / 搜索 / 分析）→ 结果
   ↓ ① Knowledge Extractor（可异步，不阻塞响应）
   从这轮的 问题 + 答案 + 走过的 Action/Observation 抽取知识条目
   ↓ 入库（SQLite + 向量，与方案 2 共用检索层）
   ↓ ② 下次起手先检索相关知识，作为线索注入 / 作为第 5 个工具 recall_knowledge
```

**与方案 2 的关系（互补，非替代）：**

| | 方案 2（静态索引） | 方案 3（动态沉淀） |
|---|---|---|
| 知识来源 | 预建 tree-sitter AST → 符号表 | LLM 每次解读的结果 |
| 内容 | 事实型（X 定义在哪、调用关系） | 解读型（X 模块干嘛、字段含义、功能流程） |
| 何时建 | 离线一次性 | 随查询增量积累 |

两者共用同一检索层：方案 2 答"在哪/是什么"，方案 3 答"为什么/怎么运作"。本闭环套在 `agent.answer()` 外层，**与后端无关**（custom / sdk 都受益）。

**硬前提 —— 知识失效机制（成败关键，非细节）：** 代码会变、LLM 解读可能错。没有失效机制，飞轮会越转越脏，错误知识反复召回污染累积。必须有：

1. **绑定代码版本**：每条知识记录依据的 `file + 内容哈希/commit`；检索时若源文件已变，降级为"此结论基于旧版本，需重新核实"，而非直接采信。
2. **溯源与可信度**：知识带上引用的 `file:line`，可溯源、可校验。
3. **检索增强 ≠ 直接相信**：召回的知识作为"参考线索"喂给 agent，让它用工具二次验证关键点，再输出。

**渐进路径：**
- ~~**MVP**：问答后存 `{问题, 答案, 引用文件+哈希}` 到 SQLite；下次召回注入。~~ ✅ 已落地
- ~~**V2**：加失效（源文件变 → 标 stale）、`recall_knowledge` 工具。~~ ✅ 已落地（失效提前到 MVP 一起做）
- **V3（未做）**：向量/语义召回（当前是 FTS 关键词 OR 匹配）；与方案 2 符号表合并成统一检索；知识去重/合并、可信度打分。

**已落地（MVP + 失效）**
- `knowledge.py`：SQLite + FTS5 知识库。`store(q, a, refs)` 记录问题/答案/引用文件+内容哈希；`recall(query)` 按关键词 OR 匹配召回，并对每条重算引用文件哈希、变了标 `stale`。独立 DB（`KNOWLEDGE_DB_PATH`），与只读 code_index 分开。
- `agent.CodeAgent`：问答后**自动沉淀**（`_precipitate`，从 `read_file` 的 Action 提取引用文件）；起手**自动召回**注入 system 提示（`_recalled_context`，stale 条目降级为"需重新核实"）。`recall_knowledge` 作为第 7 个工具，仅在飞轮开启时 advertise。
- 开关 `USE_KNOWLEDGE`（默认 **关**，验证命中率后再开）。失效是核心：实测改源文件 → stale=True、还原 → False。
- 实测飞轮：同一问题问两次，第二次成功召回第一次结论作为线索（带来源文件 + 核实提示）。

**现有项目的有利条件：** `events.py` 的 Action/Observation 历史是 Extractor 的现成输入；`tools.py` 是唯一文件入口，检索层可作为"第 5 个工具"接入，`agent.py` 几乎不动。

**风险：**
- 正反馈不一定成立 —— 若用户问题分散、命中率低，沉淀收益跟不上维护成本。MVP 阶段先测命中率再投入。
- 错误传播 —— 一条错知识被反复召回会放大；失效 + 溯源是底线。

**权衡说明（诚实记录）：** 本闭环用到 Memory/RAG，而上面「二、明确舍弃」曾以"只读问答用不到"为由舍弃它。结论不矛盾：当时是**无知识沉淀**场景下的正确取舍；一旦要做"越用越强"的飞轮，RAG 正是其核心机制 —— 这是**有条件地翻回**该决策，触发条件就是方案 3 立项。

- 价值：高（飞轮成立时延迟/成本/质量持续改善）；MVP 成本：低（复用 FTS）；剩余成本：中（向量召回 + 命中率验证 + 去重）。
- 状态：MVP + 失效已落地，默认关闭待验证命中率；语义召回与统一检索留待 V3。

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

### F. 运行时诊断：日志 / coredump backtrace 分析（MVP 已落地）

把服务从「读代码」扩展到「诊断运行时问题」：给一段 **崩溃栈（backtrace）** 或 **日志片段**，结合代码库定位根因、解释每一帧、给出排查方向。这是 gameserver 场景的高价值诉求（崩溃/卡死/异常日志的根因定位）。

**已落地（backtrace 诊断 + 日志反查）**
- `diagnose.py`：
  - 解析 gdb 风格 backtrace → 逐帧提取函数 → 复用符号索引（`index_query`）映射到 `file:line`；带类名（`SceneMgr::Update`）时自动收窄同名候选（实测 50 个 → 1 个），含 `c++filt` demangle。
  - **日志反查**（`find_log_source`）：运行时日志是「填好值的格式串」，剥掉时间戳/级别前缀、按数字/地址切分、取最长固定文本片段去 FTS 搜格式串 → 定位打印点。实测带变量/带时间戳的真实日志均精准命中。
- agent 工具：`resolve_frame`（帧→定义，类名收窄）、`find_log_source`（日志→打印点）。
- 入口：`POST /diagnose`（`{backtrace, log}`，两者可单独或组合）+ MCP 工具 `diagnose_crash`。诊断时会预先反查日志打印点写进 prompt，agent 再读代码综合分析。
- 实测：(a) 真实崩溃栈 2/3 帧定位，agent 识别 `this=0x0` 空指针给根因；(b) 纯日志诊断，反查到打印点后 agent 追到 `ASSERT_FALSE` 断言根因。

**未做（后续）**
- 按 build 版本绑定行号（栈对应的代码版本）；release 缺符号/inline 的处理。
- 崩溃模式知识沉淀（与方案 3 结合，相似栈/日志直接命中历史诊断）。

**典型输入与产出**
- coredump backtrace（`gdb bt` / 信号栈）→ 逐帧映射到 `file:line` + 函数解释 + 最可能的崩溃原因（空指针/越界/竞态…）+ 涉及的相关代码。
- 日志片段（报错/断言/异常）→ 关联到打印该日志的代码位置、上下游调用、可能触发条件。

**架构落点（复用现有能力）**
- 新增工具，与现有四个并列：
  - `resolve_frame(symbol_or_addr)`：把 backtrace 里的函数名/符号映射到定义位置 —— **直接复用方案 2 的符号索引**（`index_query.find_symbol`），这是它和方案 2 的强依赖点。
  - `find_log_source(message)`：按日志文本（去掉变量部分）在代码里反查 `LOG/printf/断言` 调用点 —— 复用 FTS 全文索引。
- 入口：`/ask` 已能传任意文本，可直接贴栈/日志提问；或加一个专门的 `POST /diagnose`（结构化输入 backtrace + 可选日志），以及对应 MCP 工具 `diagnose_crash`。
- agent 循环不变：把栈/日志当作问题上下文，agent 用上述工具逐帧检索代码再综合。

**关键难点**
- **符号 ↔ 源码映射**：release 版栈常缺符号/被 inline/名字 mangled。需要 demangle（`c++filt`），且最好有 build 时的符号信息；纯靠源码名匹配会有歧义（重载/同名）。
- **日志反查的噪音**：日志含运行时变量，需先归一化（剥掉数字/路径/地址）再检索，否则匹配不到格式串。
- **行号漂移**：栈里的行号对应的是当时的代码版本；与方案 3 同样需要 **版本绑定**（backtrace 来自哪个 commit/build）。

**渐进路径**
- MVP：`/ask` 贴 backtrace，新增 `resolve_frame` 工具走符号索引，让 agent 逐帧解读。先验证"栈帧→代码"映射准确率。
- V2：`POST /diagnose` 结构化入口 + 日志反查工具 + demangle；按 build 版本绑定。
- V3：沉淀「崩溃模式 → 根因」知识（与方案 3 飞轮结合），相似栈直接命中历史诊断。

- 价值：高（gameserver 运维刚需，超出纯代码问答）；MVP 成本：低（复用方案 2 索引）；剩余成本：中（日志反查 + 版本绑定）。
- 依赖：符号映射依赖方案 2 符号索引（已用）；版本绑定与方案 3 共用机制。

## 四、参考

- OpenHands 架构调研要点见本仓库提交历史与 [architecture.md](architecture.md)。
- 出处：`docs.openhands.dev`、`github.com/OpenHands/OpenHands`（经典 V0 tag 0.19–1.5；当前 main 已重构为 Software Agent SDK）。
