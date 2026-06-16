# 接口与用法

## HTTP API

服务默认监听 `0.0.0.0:8900`（`SERVICE_HOST` / `SERVICE_PORT` 可改）。

### `GET /health`

健康检查。

```bash
curl http://localhost:8900/health
# {"status":"ok"}
```

### `POST /ask`

提问。

**请求体**

```json
{
  "question": "要问的问题",
  "use_cache": true
}
```

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `question` | string | （必填） | 自然语言问题 |
| `use_cache` | bool | `true` | 是否使用缓存 |

**响应**

```json
{
  "answer": "SceneMgr 是场景管理器……",
  "cached": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `answer` | string | 回答 |
| `cached` | bool | 本次是否命中缓存 |

**示例**

```bash
curl -X POST http://localhost:8900/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "SceneMgr 是做什么的？"}'
```

### 缓存说明

缓存是 `main.py` 里的进程内字典（问题 → 答案）：

- `use_cache=true` 且问题问过 → 直接返回缓存，`cached:true`，**不调 LLM**（省时省 token）。
- 重启服务即清空。
- 缓存层位于 agent 之上，将来（方案 2）可替换为离线索引而不动 agent。
- 空问题返回 `{"answer":"问题不能为空。","cached":false}`。

### `POST /diagnose`

分析崩溃栈（coredump backtrace），结合代码库定位根因（方向 F）。

**请求体**

```json
{
  "backtrace": "#0 0x... in SceneMgr::Update (this=0x0) at scene/scenemgr.cpp:142\n#1 ...",
  "log": "可选：相关日志片段"
}
```

**响应**

| 字段 | 说明 |
|------|------|
| `answer` | 诊断结论（根因 + 排查方向） |
| `frames` | 解析出的栈帧摘要列表 |
| `resolved` | 成功映射到代码的帧数 |
| `total_frames` | 解析出的总帧数 |

**示例**

```bash
curl -X POST http://localhost:8900/diagnose \
  -H "Content-Type: application/json" \
  -d '{"backtrace": "#0 0x55ab in SceneMgr::Update (this=0x0) at scene/scenemgr.cpp:142\n#1 0x55cd in Process::Update () at process.cpp:211"}'
```

逐帧用符号索引（方案 2）映射到 `file:line`；带类名的帧（`SceneMgr::Update`）自动收窄同名候选。空 backtrace 返回 400。

## 命令行（`cli.py`）

```bash
# 交互模式（会打印工具调用过程）
scripts/cli.sh

# 单次提问
scripts/cli.sh "SceneMgr 是做什么的？"

# 切后端
AGENT_BACKEND=sdk scripts/cli.sh "暴击伤害怎么算？"
```

交互模式下输入 `quit` / `exit` / `q` 或 Ctrl-D 退出。

## 脚本（`scripts/`）

脚本从自身位置解析项目根，可在任意目录调用，首次运行自动建好 venv 并加载 `.env`。

| 脚本 | 作用 |
|------|------|
| `setup.sh` | 创建 venv 并安装依赖 |
| `serve.sh [start\|stop\|restart\|status]` | HTTP 服务（端口 8900）；无参数=前台运行 |
| `mcp.sh [start\|stop\|restart\|status]` | MCP 服务（端口 8901）；无参数=前台运行 |
| `cli.sh ["问题"]` | 命令行交互；带参数则单次提问 |
| `ask.sh [--no-cache] "问题"` | 用 curl 向**运行中**的服务发 `/ask` |

`scripts/common.sh` 是被 source 的公共库（`PROJECT_ROOT`、`VENV_PY`、`ensure_venv`、`run_py`、加载 `.env`、`daemon_*` 守护进程助手），不直接运行。

### 后台运行 / 停止

`serve.sh` 和 `mcp.sh` 支持子命令：

```bash
scripts/serve.sh start      # 后台启动，pid/日志写 logs/serve.{pid,log}
scripts/serve.sh status     # 查看状态
scripts/serve.sh stop       # 停止（先 SIGTERM，10s 后 SIGKILL）
scripts/serve.sh restart    # 重启
scripts/serve.sh            # 不带参数 = 前台运行（Ctrl-C 停）

scripts/mcp.sh start        # 同理，logs/mcp.{pid,log}
scripts/mcp.sh stop
```

pid 文件与日志都在 `logs/` 下（已 gitignore）。`stop`/`start` 幂等：重复 stop 提示未运行，重复 start 提示已运行。

```bash
# 典型流程
scripts/serve.sh start                    # 后台起服务
scripts/ask.sh "玩家生命值字段叫什么？"      # 提问
scripts/ask.sh --no-cache "同一个问题"      # 绕过缓存
scripts/serve.sh stop                     # 用完停掉
```
