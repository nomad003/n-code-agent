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
