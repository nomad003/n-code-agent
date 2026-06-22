# custom 后端工作原理

`custom` 是默认后端：它不用 Claude Agent SDK，而是在 `code_agent.core.agent` 里直接实现一个
litellm tool-calling 循环。它的目标很明确：只读地理解代码库，所有文件访问都必须
经过 `code_agent.retrieval.tools` 的沙箱工具。

## 总览

请求路径：

```text
HTTP /ask、MCP ask_codebase、CLI
  -> agent.answer(question, mode=..., repo=...)
  -> config.use_repo(repo) 选择当前代码库
  -> CodeAgent.run(question)
  -> litellm.completion(..., tools=tools.active_schemas())
  -> tools.dispatch(...) 读取/搜索代码
  -> 把工具结果回喂给 LLM
  -> 最终中文回答
```

`custom` 后端由 `AGENT_BACKEND=custom` 选择，也是默认值。它和 `sdk` 后端共用：

- `config.system_prompt_for_mode(mode)`
- `code_agent.retrieval.tools` 的沙箱工具
- `response_policy.enforce(...)`
- repo 上下文、索引、知识库、trace 机制

差异在于：`custom` 自己控制消息历史、tool_call 执行、stuck 检测、重试和收尾。

## 入口分发

外部入口不会直接构造 `CodeAgent`，而是调用：

```python
agent.answer(question, mode=mode, repo=repo)
```

这一层先做三件事：

1. `config.use_repo(repo)`：把当前请求绑定到指定 repo。后续 `code_agent.retrieval.tools`、`code_agent.retrieval.index_query`、`code_agent.kb.knowledge` 都通过 `config.current_*()` 读取当前 repo 的路径和 DB。
2. 解析 `mode`：`plain` / `technical` / `edit` 必须在 `AGENT_ALLOWED_MODES` 中。
3. 创建 `LLMTrace`：记录请求、每轮 LLM 输入输出、工具结果、最终答案或错误。

之后如果 `USE_SHORTCUT=1`，会先尝试 `shortcut.try_answer(question)`。精确的“X 定义在哪”类问题可以直接查符号索引返回，不进入 LLM 循环。

## 模型路由

`custom` 使用 `litellm.completion(...)` 调模型，但强制走 OpenAI 兼容代理：

```python
model = f"openai/{LLM_MODEL}"
api_base = LLM_API_BASE
api_key = LLM_API_KEY
```

原因是 litellm 会根据模型名前缀选择 provider。若直接传 `vertex_ai/...`，litellm 会尝试走原生 Google Cloud 认证，而不是项目里的 mushigen `/v1` 代理。加 `openai/` 后，litellm 使用 OpenAI-compatible client；代理收到的真实模型名仍是去掉 `openai/` 后的值。

## 提示词结构

`custom` 的提示词不是一整块硬编码文本，而是每轮在 `CodeAgent._build_messages()` 里动态拼出来：

```text
system =
  config.SYSTEM_PROMPT_BASE
  + operation_modes.response_rules(mode)
  + question_intent.prompt(question)
  + repo_profile.format_for_prompt()
  + module_knowledge.format_for_prompt(question)
  + knowledge recall（可选）

messages =
  system
  + user question
  + 历史 Action/Observation
```

### Base Prompt

基础提示词在 `code_agent.config.SYSTEM_PROMPT_BASE`。它规定 agent 的身份和工具使用策略：

- 它是代码理解助手，回答游戏服务器、战斗、客户端、引擎等代码问题。
- 它不能直接看到代码，必须通过工具检索。
- 工具优先级要省 token：
  - 只看文件名能解决：优先 `glob`。
  - 枚举型问题：优先 `grep_code(..., output_mode="files")`，不够再用 `count`。
  - 理解型问题：优先 `grep_code(..., output_mode="content", context=3)`。
  - `read_file` 只在需要完整函数体或 grep 上下文不够时用，必须显式传 `start/end`。
  - 同一轮可以并行发多个独立 `tool_calls`，减少总轮数。
- 所有路径必须相对当前 repo 根目录，不能用绝对路径或 `..` 越界。
- 信息不足要如实说明，不能编造。

### Mode 规则

`operation_modes.response_rules(mode)` 会追加回答风格规则：

| mode | 作用 |
|------|------|
| `plain` | 面向非程序员/策划/QA，采用渐进披露；优先用表格、短清单和 Mermaid 图表达。配置问题给“配置面/表/字段/用途”明细，功能问题给流程图和结构化步骤；不输出代码、命令、JSON、配置样例，也不默认暴露知识卡/文件/符号等内部线索 |
| `technical` | 面向程序员，同样先用表格、短清单和 Mermaid 图表达；配置问题先给表/字段/用途，再补加载链路和使用位置；功能问题先给流程图和结构化步骤，再补类、函数、调用链、文件路径和行号 |
| `edit` | 面向直接改码，要求先定位影响范围，再说明变更和验证；没有写工具时只能给方案 |

最终答案还会经过 `response_policy.enforce(...)`。尤其是 `plain` 模式，即使模型输出了代码形态内容，也会被服务边界再过滤一次。

### 问题类型策略

`question_intent.prompt(question)` 会根据用户问题追加“最佳实践”策略。它和 `mode`
不是一回事：

- `mode` 决定面向谁回答：非程序员、程序员、还是改码。
- `question_intent` 决定怎么查、怎么组织答案。

当前内置四类高频问题：

| 类型 | 识别线索 | 优先工具 | 答案重点 |
|------|----------|----------|----------|
| 程序 crash 堆栈 | `#0/#1` 栈帧、backtrace、core、SIGSEGV、堆栈 | `resolve_frame`、`read_file` | 崩溃点、触发条件、调用关系、根因证据、排查/修复 |
| 宕机/错误日志 | ERROR/WARN/FATAL、ASSERT/CHECK、断言、宕机日志 | `find_assert_context`、`find_log_source` | 日志语义、打印点/断言点、错误分支、影响范围、排查顺序 |
| 功能实现 | “怎么实现/流程/调用链/做什么/机制” | `repo_overview`、`grep_code(files/content)`、`find_symbol` | 入口、核心类/函数、主流程、数据结构、扩展点 |
| 配置实现 | 配置/配置表/字段/开关/热更/config/yaml/json | `glob`、`grep_code(files/count)`、`read_file` | 配置来源、加载链路、字段含义、使用位置、默认/非法值、验证方式 |

如果没有命中这四类，会注入通用策略：先归类、低成本缩小范围、区分事实和推断。

### Repo Profile 和知识线索

基础提示词之后会追加当前 repo 的项目概览：

```text
repo_profile.format_for_prompt()
```

这部分来自 `index/repos/<repo>/profile.json`，用于告诉模型常用目录、模块、符号样例和导航入口，避免每次从根目录盲搜。

随后会按问题关键词召回版本化模块知识卡：

```text
docs/code-knowledge/<repo>/*.md
```

这类卡片用于维护大模块的稳定框架、关键链路、配置关系和排查手册，例如
`docs/code-knowledge/marvel/monster-config.md` 记录了怪物配置、`CombatEnemy` 初始化、
`SkillListForEnemy`、`GetEnemySkillConfigX`、`InitEnemySkill` 和常见 enemy skill 缺配置宕机链路。
知识卡会作为“框架导览”注入 prompt，但答案仍要求用工具读当前代码核实。

如果开启 `USE_KNOWLEDGE=1`，还会追加历史问答召回结果。召回内容被明确标成“线索”，模型必须再用工具核实。

## 消息构造

`CodeAgent._build_messages()` 是唯一的“历史事件 -> LLM messages”入口。

每轮消息包含：

1. system prompt：由 `config.system_prompt_for_mode(mode)` 生成。
2. repo profile：如果存在 `index/repos/<repo>/profile.json`，会通过 `repo_profile.format_for_prompt()` 注入，作为代码导航起点。
3. knowledge recall：如果 `USE_KNOWLEDGE=1`，会召回历史问答线索并提示模型必须二次核实。
4. user question。
5. 历史 Action / Observation。

历史事件有两类：

- `Action`：模型发出的 tool_call 请求，保存原始 assistant message、tool_call_id、工具名和参数。
- `Observation`：工具执行结果，保存 tool_call_id、工具名、结果文本和是否错误。

构造 messages 时，Action 会还原成 assistant tool_call message；Observation 会还原成对应的 `role="tool"` message。这样能保证 OpenAI tool-call 协议要求的 `tool_call_id` 配对正确。

消息大致长这样：

```python
[
    {"role": "system", "content": "...提示词 + repo profile..."},
    {"role": "user", "content": "SceneMgr 是做什么的？"},
    {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "find_symbol",
                    "arguments": "{\"name\":\"SceneMgr\"}",
                },
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "find_symbol",
        "content": "scene/SceneMgr.h:12: class SceneMgr ...",
    },
]
```

下一轮 LLM 看到上一轮工具结果后，再决定继续查调用点、读文件片段，或直接回答。

## 观测遮蔽

长会话里工具输出会很大。`custom` 不额外调用 LLM 做总结，而是确定性遮蔽旧 Observation：

- 最近 `OBS_KEEP_FULL` 条工具输出保留完整内容。
- 更早的工具输出替换为一行稳定摘要：

```text
[省略较早的 <tool> 输出，如需可重新调用]
```

这样模型知道之前调用过工具；如果确实需要细节，可以重新调用。稳定摘要也有利于代理侧 prompt cache。

## 单轮 LLM 调用

每轮 `_llm_call(with_tools=True)` 会调用：

```python
litellm.completion(
    model=_routed_model(),
    api_base=LLM_API_BASE,
    api_key=require_api_key(),
    messages=messages,
    tools=tools.active_schemas(),
    tool_choice="auto",
    temperature=LLM_TEMPERATURE,
    timeout=LLM_TIMEOUT,
    num_retries=LLM_NUM_RETRIES,
)
```

`num_retries` 让 litellm 对限流、超时、服务端错误做重试。每次请求和响应都会写入 trace。

## 工具如何暴露给模型

工具由两层组成：

1. `TOOL_SCHEMAS`：给 LLM 看的 JSON schema，描述工具名、参数和说明。
2. `TOOL_REGISTRY`：服务端实际执行函数的注册表。

每轮带工具调用时，`custom` 传入：

```python
tools=tools.active_schemas()
tool_choice="auto"
```

`active_schemas()` 默认返回代码检索工具；只有 `USE_KNOWLEDGE=1` 时，才额外暴露 `recall_knowledge`，避免模型看到一个默认无效的工具。

当前主要工具：

| 工具 | 典型用途 |
|------|----------|
| `repo_overview()` | 先看当前 repo 的项目概览和模块导航 |
| `glob(pattern, path, head_limit)` | 只按文件名/路径找候选文件，最便宜 |
| `list_dir(path)` | 看某个目录下一层结构 |
| `grep_code(pattern, path, output_mode, context, head_limit)` | 搜关键字/调用点；`files` 枚举文件，`count` 看分布，`content` 看命中上下文 |
| `find_symbol(name)` | 定位类、函数、结构体、枚举、方法定义 |
| `read_file(path, start, end)` | 读取关键代码片段 |
| `resolve_frame(frame)` | 把崩溃栈帧映射到代码 |
| `find_log_source(message)` | 根据日志文本反查打印点 |
| `find_assert_context(message)` | 根据断言失败/错误日志查询离线 assert 索引，返回断言行和上下文 |
| `recall_knowledge(query)` | 开启知识库时召回历史问答线索 |

模型返回工具调用后，服务端不会直接信任参数执行任意代码，只会走：

```python
tools.dispatch(name, args)
```

`dispatch()` 从 `TOOL_REGISTRY` 找同名函数。未知工具、参数错误、路径错误或内部异常都会转成 `error: ...` 字符串，作为 tool result 回喂给模型，让模型自己修正下一步，而不是让整个请求崩掉。

## Tool Calling 循环

主循环在 `CodeAgent._loop()`：

1. 调一次 LLM。
2. 如果 LLM 没有返回 `tool_calls`，说明它已经给出最终答案，直接返回。
3. 如果有 `tool_calls`：
   - 为每个 tool_call 创建 `Action`。
   - 解析 JSON 参数。
   - 调 `tools.dispatch(name, args)`。
   - 把结果包装成 `Observation`。
   - Action 和 Observation 都追加到 `self.history`。
4. 检查是否 stuck。
5. 进入下一轮。

模型可以在同一轮发多个 tool_call。`custom` 会按顺序执行并全部回填到下一轮 messages。

更具体地说，一次 loop 是：

```text
for round in 1..MAX_ITERATIONS:
  1. messages = _build_messages(with_tools=True)
  2. response = litellm.completion(messages, tools=active_schemas(), tool_choice="auto")
  3. 如果 response 没有 tool_calls：
       返回 response.content
  4. 如果有 tool_calls：
       对每个 tool_call：
         Action(tool_call_id, name, raw_arguments, assistant_message)
         args = json.loads(raw_arguments)
         result = tools.dispatch(name, args)
         Observation(tool_call_id, name, result, is_error)
       append 到 history
  5. 如果 _is_stuck()：
       break

如果达到轮数上限或 stuck：
  - 最近 assistant 文本像完整答案：直接复用
  - 否则 _llm_call(with_tools=False)，追加“基于已有信息给最终回答”
```

关键点：

- `Action` 保存模型原始 assistant tool_call message。
- `Observation` 保存工具执行结果。
- 下一轮通过 `_build_messages()` 把它们还原成 OpenAI tool-call 协议消息。
- `tool_call_id` 必须配对；否则模型无法知道哪个工具结果对应哪个调用。
- `with_tools=False` 的最终收尾轮不会再暴露工具，强制模型基于已有证据回答。

## 如何分析代码并解决提问

`custom` 不会把整个仓库塞给模型，也不会预先遍历所有文件。它采用“先定位、再读证据、最后归纳”的按需检索流程：

```text
问题
  -> 注入 repo profile / 历史知识线索
  -> 判断问题意图
  -> 选择工具定位候选文件和符号
  -> 读取关键代码片段
  -> 沿调用、继承、字段、日志、配置继续追踪
  -> 基于已读证据组织答案
```

### 1. 先给模型代码导航

每轮 `_build_messages()` 会把当前 repo 的 profile 注入 system prompt。profile 来自
`python -m code_agent.retrieval.repo_profile --repo <name>` 生成的缓存，通常包含：

- 仓库根目录和主要目录
- 语言和文件分布
- 常见入口文件、核心模块、符号样例
- README / 配置 / 构建文件等导航信息

这一步的作用是给模型一个“地图”，让它优先去可能相关的目录，而不是每次从根目录盲扫。

如果开启 `USE_KNOWLEDGE=1`，还会注入历史相似问答，但只作为线索；模型仍被要求用工具重新核实当前代码。

### 2. 判断问题类型

模型根据问题选择不同检索路径：

| 问题类型 | 常见处理方式 |
|----------|--------------|
| “X 在哪定义？” | 先走 `shortcut.try_answer()`；未命中再用 `find_symbol("X")` |
| “X 是做什么的？” | `find_symbol` 定位定义，`read_file` 读类/函数上下文，再 `grep_code` 查调用点 |
| “某功能流程是什么？” | 从关键词 `grep_code` / `glob` 找入口，沿调用链读关键文件 |
| “字段/配置含义？” | 搜字段定义、赋值、读取、序列化/配置加载位置 |
| “崩溃/日志怎么定位？” | `resolve_frame` 映射栈帧；断言日志先用 `find_assert_context`，普通日志用 `find_log_source`，再读附近逻辑 |
| “有哪些模块/目录？” | `repo_overview`、`list_dir`、`glob` 先做结构扫描，再按需展开 |

精确“定义在哪”类问题会尽量短路，直接返回索引结果，避免不必要的 LLM 多轮检索。

### 3. 定位候选代码

定位阶段优先使用低成本、范围窄的工具：

- `repo_overview()`：先看项目概览和常用模块导航。
- `find_symbol(name)`：查类、函数、结构体、枚举、方法定义。
- `find_assert_context(message)`：用户贴断言失败、ASSERT/CHECK 或错误日志时，直接查离线 assert 索引，返回断言语句和附近代码。
- `grep_code(pattern, output_mode="files")`：先只拿命中文件列表，避免一次返回大量内容。
- `glob(pattern)` / `list_dir(path)`：按路径结构找模块、配置、脚本和同名文件。

如果当前 repo 有索引，`find_symbol` 和整库纯文本 `grep_code` 会先查 SQLite/FTS；没有索引才 live scan。

### 4. 读取证据并继续追踪

定位到候选文件后，模型用 `read_file(path, start, end)` 读取小范围代码片段。通常会继续追踪：

- 定义附近的成员变量、注释、初始化逻辑
- 函数内部调用的下一级函数
- 调用方和被调用方
- 注册表、工厂、消息分发、定时器、回调
- 配置加载、proto/IDL、数据库字段、日志打印
- ECS / gameserver 之间的引用关系

这里仍然是按需读取：工具有输出上限，模型需要根据当前证据决定下一步查什么，而不是把文件整块塞进上下文。

### 5. 多工程问题怎么处理

当前请求绑定一个 repo。对你现在的配置，默认 `marvel` repo 是组合目录：

```text
target_code/marvel/
  gameserver -> /home/dev/marvel/gameserver
  ecs        -> /home/dev/marvel/XEcsLib
```

因此默认提问时，`code_agent.retrieval.tools` 的沙箱根目录就是 `target_code/marvel`，模型能同时搜索：

- `gameserver/...`
- `ecs/...`

如果问题涉及 gameserver 调 ECS，模型通常会先在 `gameserver` 找调用点，再沿符号名、include、类型名或日志关键词到 `ecs` 下继续查定义和实现。索引、知识库、profile 也按 repo 隔离，所以 `marvel` 的索引会覆盖这两个子目录。

### 6. 归纳答案

模型最终回答时只基于已经读到的工具结果组织结论。通常会包含：

- 结论：这个类/函数/模块负责什么
- 关键代码位置：文件、行号、符号名
- 流程：入口、核心分支、调用链、数据流
- 注意事项：未找到的证据、需要继续确认的点
- 面向不同 `mode` 的表达方式：`plain` 更白话，`technical` 保留代码细节，`edit` 偏向修改方案

如果达到轮数上限或 stuck，`custom` 会停用工具，让模型基于已经收集到的证据收尾；证据不足时应说明“不确定”或给出下一步需要查的点。

## 沙箱工具边界

LLM 不能直接读文件系统，只能调用 `code_agent.retrieval.tools` 的工具。关键工具包括：

- `grep_code(...)`
- `read_file(...)`
- `list_dir(...)`
- `glob(...)`
- `find_symbol(...)`
- `repo_overview()`
- `resolve_frame(...)`
- `find_log_source(...)`
- `recall_knowledge(...)`，仅 `USE_KNOWLEDGE=1` 时暴露

工具层负责三件事：

1. 路径限制在当前 repo 根目录内。
2. 输出限长，避免撑爆上下文。
3. 错误转字符串返回给模型，而不是抛异常打断循环。

索引可用时，`find_symbol` 和部分 `grep_code` 会优先走当前 repo 的 SQLite 索引；没有索引则回退 live scan。

`find_assert_context` 也依赖当前 repo 的 SQLite 索引。索引构建时会确定性抽取
`assert(...)`、`ASSERT_*`、`CHECK_*`、`VERIFY_*`、`ENSURE_*` 这类断言/检查宏，记录宏名、文件、行号、完整语句和字符串消息。查询时会把运行时日志里的时间戳、数字、地址等变量剥掉，用固定文本片段匹配这些断言语句，因此能把类似“scene id invalid 1001”的日志定位回对应的 `ASSERT_FALSE(..., "scene id invalid %d", id)`。

运行时日志里的 `file:line` 只作为弱 hint：不同构建版本、宏展开、生成文件或旧二进制都可能导致行号不准。工具会优先使用固定文本匹配；如果没有文本命中，才用 `file:line` 在附近窗口找 assert/check 候选。返回结果必须再结合上下文和构建版本确认，不能只凭日志行号下结论。

## Stuck 检测

`custom` 有轻量 stuck 检测，避免模型反复做无意义搜索。阈值由 `STUCK_REPEAT_THRESHOLD` 控制，默认 3。

满足任一条件就提前收尾：

1. 最近 N 次 Action 完全相同。
2. 最近 N 次 Action 是同一工具 + 同一主键，例如反复 grep 同一个 pattern，只是微调 path/context/output_mode。
3. 最近 N 次 Observation 都是错误。

检测到 stuck 后，不再继续让模型调用工具，而是进入最终回答阶段。

## 收尾策略

循环结束有三种情况：

1. 模型直接回答：立即返回。
2. 达到 `MAX_ITERATIONS` 或 stuck，但最近一轮 assistant 文本已经像完整答案：直接复用该文本，省一次 LLM 调用。
3. 否则再发一次 `with_tools=False` 的 LLM 调用，并追加提示：

```text
已达到工具调用上限，请基于目前收集到的信息给出最终回答。
```

这次不带 tools，强制模型基于已有证据收尾。

## 知识飞轮

当 `USE_KNOWLEDGE=1`：

1. 请求开始时，`_recalled_context(question)` 从当前 repo 的知识库召回相似问答，注入 system prompt。
2. 回答结束后，`_precipitate(answer)` 把本轮问答和引用文件哈希写入当前 repo 的 `knowledge.db`。
3. 下次召回时会重新计算引用文件哈希；文件变了会标记 stale，提示模型必须重新核实。

默认关闭，避免未经验证的历史知识污染回答。

## 可观测性

`custom` 写两类运行信息：

- stderr 进度行：例如第几轮、调用了哪些工具、是否 stuck。
- JSONL trace：默认写到 `logs/llm/`，可在 `/admin/llm-traces` 查看。

trace 记录：

- request_start / request_end / request_error
- llm_request / llm_response / llm_error
- tool_result
- shortcut / cache_hit

这对排查“为什么模型没搜到”“为什么重复 grep”“为什么答案来自缓存或 shortcut”很有用。

## 相关配置

| 配置 | 作用 |
|------|------|
| `AGENT_BACKEND=custom` | 选择 custom 后端 |
| `LLM_MODEL` | 模型名，经 `_routed_model()` 加 `openai/` 前缀 |
| `LLM_API_BASE` | OpenAI 兼容代理地址 |
| `LLM_API_KEY` | 代理认证 token |
| `AGENT_MAX_ITERATIONS` | 最大工具调用轮数 |
| `LLM_NUM_RETRIES` | litellm 重试次数 |
| `LLM_TIMEOUT` | 单次 LLM 超时 |
| `OBS_KEEP_FULL` | 保留最近多少条完整工具输出 |
| `STUCK_REPEAT_THRESHOLD` | stuck 检测阈值 |
| `USE_INDEX` | 是否使用当前 repo 的索引 |
| `USE_SHORTCUT` | 是否启用精确定义查询短路 |
| `USE_KNOWLEDGE` | 是否启用知识召回与沉淀 |
| `LLM_TRACE_ENABLED` | 是否写 JSONL trace |

## 与 sdk 后端的区别

| 维度 | custom | sdk |
|------|--------|-----|
| 循环实现 | 项目内 `CodeAgent` 自己控制 | Claude Agent SDK 控制 |
| 模型调用 | litellm + `/v1` OpenAI 兼容代理 | Claude Code CLI + Bedrock 代理 |
| 工具执行 | `tools.dispatch()` | SDK tool 包装后仍调 `tools.dispatch()` |
| 历史管理 | Action/Observation 本地事件列表 | SDK 内部管理 |
| stuck/遮蔽/收尾 | 项目内显式实现 | 依赖 SDK 行为 |
| 可观测性 | JSONL trace + stderr 进度 | SDK 流式事件 + trace |

一句话：`custom` 是项目自己实现的、可控性更高的只读代码问答 agent 循环；`sdk` 是把同一套工具交给 Claude Agent SDK 执行。
