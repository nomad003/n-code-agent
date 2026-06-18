# 测试

测试**全部离线**——不调 LLM、不访问网络。LLM 调用通过 monkeypatch 替换后端的 `answer` 函数，工具针对临时代码库运行，因此不会碰到真实目标代码库或代理。

## 运行

```bash
scripts/test.sh                  # 跑全部测试（首次会自动装 pytest/httpx）
scripts/test.sh -k grep          # 只跑名字含 grep 的用例
scripts/test.sh tests/test_api.py            # 跑单个文件
scripts/test.sh tests/test_tools.py::test_grep_finds_match   # 跑单个用例
```

底层等价命令：

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## 依赖

测试依赖在 `requirements-dev.txt`（在 `requirements.txt` 基础上加 `pytest`、`httpx`）。配置见 `pytest.ini`（`testpaths=tests`，并把项目根加入 `pythonpath`）。

## 覆盖范围

| 文件 | 覆盖内容 |
|------|---------|
| `tests/conftest.py` | `target_code` fixture：建临时代码库并把 `config.TARGET_CODE_PATH` 指过去 |
| `tests/test_tools.py` | 路径沙箱（越界拒绝、前导斜杠）、grep/read/list/find_symbol、输出限长、`dispatch()` 错误处理、schema 与注册表一致性 |
| `tests/test_config.py` | `require_api_key()`、`_routed_model()` 的 `openai/` 前缀、`AGENT_BACKEND` 后端分发（custom / sdk，sdk 用桩模块避免真导入） |
| `tests/test_api.py` | `/health`、`/ask`、空问题、缓存命中跳过 agent、`use_cache=false`、agent 异常 → 502、失败不入缓存 |

## 约定

- **不发真实请求**：测 agent 循环时 monkeypatch `agent._answer_custom` 或 `agent.answer`；测后端分发时用桩 `agent_sdk` 模块（`sys.modules` 注入），避免触发 SDK / litellm 导入。
- **沙箱隔离**：工具测试用 `target_code` fixture 的 `tmp_path`，`config.TARGET_CODE_PATH` 在每个用例内被 monkeypatch，互不影响。
- **限长用例**用 monkeypatch 临时调小 `MAX_*` 阈值，避免造大文件。

## 端到端 verify（需要可用代理 + key）

单元测试不覆盖真实 LLM 链路。要确认实际服务可用，配好 `.env` 后：

```bash
scripts/serve.sh &                            # 起服务
curl -s http://localhost:8900/health          # {"status":"ok"}
scripts/ask.sh "SceneMgr 有什么方法？"          # 经真实代理返回答案
```

若代理预算超限 / token 失效，`/ask` 会返回 **502**（`上游模型调用失败: ...`）而非 500 栈——这是预期的错误处理。

## 质量评测（方向 E，需要可用代理 + key）

单元测试验证逻辑；**评测**衡量回答质量。评测集是 `{问题 → 期望文件/符号}` 的 JSONL：

```bash
scripts/eval.sh                                  # 跑样例集 eval/dataset.sample.jsonl
scripts/eval.sh eval/dataset.real_user.jsonl     # 跑真实用户日志/问题集
scripts/eval.sh eval/my_set.jsonl                # 自定义评测集
USE_KNOWLEDGE=1 scripts/eval.sh <set> --twice     # 同时测方案 3 飞轮召回率
```

每题调 agent，按"答案是否提到全部期望符号 + 至少一个期望文件"打分，输出通过率（确定性子串匹配，无 LLM judge）。真实集还可用 `expect_all_files` 要求多个关键文件全部命中、用 `expect_phrases` 要求根因关键词出现。`--twice` 每题问两次，报告第二次召回第一次沉淀的比例——判断方案 3 是否值得默认开启的信号。换模型/改 prompt/调限额后跑一遍，用通过率量化影响。

> 扩充评测集（针对真实 gameserver 符号）是开启方案 3 默认值前要补的一步——样例集太小，召回率不具统计意义。
