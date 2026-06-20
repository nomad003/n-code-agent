# Assert 知识库

Assert 知识库用于把用户贴的 `ASSERT`、`CHECK_COND`、`Check cond failed`、
`Error Exit`、`file:line` 日志，快速映射到结构化排障答案。

## 目标

每个 Assert 条目都沉淀以下信息：

| 字段 | 含义 |
|------|------|
| 对应问题 | 这个断言代表哪类用户问题或业务问题。 |
| 上下文 | 文件、函数、条件、附近日志和附近代码。 |
| 为什么出问题 | 配置缺失、对象为空、越界、ECS 状态不一致、非法坐标等原因分类。 |
| 怎么解决 | 优先排查顺序和修复动作。 |
| 匹配词 | 日志短语、宏名、函数名、文件名、条件表达式。 |

## 生成物

当前生成物位于：

```text
docs/code-knowledge/marvel/asserts/
```

核心文件：

| 文件 | 作用 |
|------|------|
| `assert-catalog.json` | 运行时匹配源，包含所有结构化 Assert 条目。 |
| `index.md` | 前端知识库入口和分组目录。 |
| `gameserver-*.md` | gameserver 各模块 Assert 排障卡。 |
| `xecslib-*.md` | XEcsLib 各模块 Assert 排障卡。 |

当前覆盖 gameserver 与 XEcsLib 核心代码，默认排除测试、协议生成目录、第三方
`swigwin` 目录和注释中的断言。

## 生成命令

```bash
./.venv/bin/python -m code_agent.assert_knowledge \
  --repo marvel \
  --source gameserver=/home/dev/marvel/gameserver \
  --source XEcsLib=/home/dev/marvel/XEcsLib
```

新增排除规则：

```bash
./.venv/bin/python -m code_agent.assert_knowledge \
  --repo marvel \
  --source gameserver=/home/dev/marvel/gameserver \
  --source XEcsLib=/home/dev/marvel/XEcsLib \
  --exclude '**/generated/**'
```

## 运行时匹配

`/ask` 的完整 Agent loop 中会调用 `assert_knowledge.format_for_prompt()`。

匹配依据：

- 日志中的 `file:line`，但只作为弱线索。
- 固定日志短语，例如 `not find in conf`。
- 宏名，例如 `CHECK_COND`、`ASSERT_FALSE`。
- 函数名和文件名，例如 `InitEnemySkill`、`skillcore.cpp`。
- 条件表达式和附近日志，例如 `nullptr != core`、`scene id invalid`。

命中后会把结构化排障线索注入 system prompt。模型仍需要结合工具读取当前代码，
不能只凭知识卡下结论。

## 工具增强

`find_assert_context(message, context)` 仍然先查离线 assert 索引，返回断言行和附近
代码。现在它还会附带 Assert 知识库命中的结构化说明：

- 对应问题。
- 上下文。
- 为什么出问题。
- 排查/解决步骤。

这保证用户贴宕机日志时，即使行号有漂移，系统也能优先用日志短语、函数和附近代码
定位，而不是只按单个行号判断。

## 示例

用户日志：

```text
InitEnemySkill(skillcore.cpp:81) Check cond: <false> failed
skill:[921948522 monster_livinglaser_lightstream] not find in conf
```

匹配条目：

```text
gameserver/unit/skill/skillcore.cpp:81 CHECK_COND
函数: SkillCore::InitEnemySkill
日志: caster:%u skill:[%u %s] not find in conf
```

系统应回答：

- 对应问题：Enemy 技能配置缺失或技能名/skill hash 与 SkillList 不一致。
- 上下文：`InitEnemySkill` 调 `SkillConfig::GetEnemySkillConfigX` 查不到配置后打印
  `not find in conf`，随后 `CHECK_COND(false)`。
- 为什么出问题：运行时 enemy 引用了配置表没有覆盖的技能。
- 怎么解决：核对 enemy statistics ID、技能 hash、技能名、`SkillListForEnemy`、
  fallback 行和服务器配置版本；修配置后重载/发布并用同一怪物复现验证。
