# 配置

所有配置集中在 `config.py`，**每一项都有默认值，且都可被同名环境变量覆盖**。无需改代码，临时改用 `VAR=值 scripts/serve.sh` 即可。

## `.env`

把密钥/路径放到 `.env`（已被 `.gitignore` 排除，不会提交）。`scripts/` 下的脚本会自动加载 `.env`，且**已有环境变量优先**（不会覆盖你显式 `export` 的值）。

```bash
cp .env.example .env     # 填入 LLM_API_KEY，按需改 TARGET_CODE_PATH / AGENT_BACKEND
```

> 裸跑 `python main.py`（不经脚本）不会自动加载 `.env`，需自己 `export`，或先 `set -a; source .env; set +a`。

## 通用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_BACKEND` | `custom` | 后端：`custom`（litellm）或 `sdk`（Claude Agent SDK） |
| `TARGET_CODE_PATH` | `./target_code` | **被分析的目标代码库路径** |
| `AGENT_MAX_ITERATIONS` | `12` | Agent 最多调几轮工具 |
| `MAX_READ_BYTES` | `20000` | 单次读文件上限（字节） |
| `MAX_GREP_MATCHES` | `100` | grep 最多返回条数 |
| `MAX_LIST_ENTRIES` | `300` | 列目录最多条数 |
| `SERVICE_HOST` | `0.0.0.0` | HTTP 监听地址 |
| `SERVICE_PORT` | `8900` | HTTP 端口 |

> `SYSTEM_PROMPT` 只在 `config.py` 里改（无对应环境变量）。

## custom 后端配置

经 mushigen 代理（OpenAI 兼容网关）。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` | 模型（实际会被加 `openai/` 前缀走代理） |
| `LLM_API_BASE` | `https://mushigen.comet.scopelyai.com/v1` | 代理地址（OpenAI 兼容，注意是 `/v1`） |
| `LLM_API_KEY` | （必填，无默认） | 认证 token，缺失时首次调用即报清晰错误 |
| `LLM_TEMPERATURE` | `0` | 采样温度 |
| `LLM_TIMEOUT` | `120` | 单次 LLM 超时（秒） |

也可把 `LLM_MODEL` 改成代理上的 Claude（如 `us.anthropic.claude-sonnet-4-6`），无需切换 SDK，litellm 这层抽象本就支持。代理可用模型用 `GET /v1/models` 查询。

## sdk 后端配置

经 Bedrock，依赖 Claude Code CLI。CLI 会读取这些环境变量：

| 变量 | 示例 | 说明 |
|------|------|------|
| `SDK_MODEL` | `us.anthropic.claude-opus-4-8` | 模型；不设则取 `ANTHROPIC_MODEL` |
| `CLAUDE_CODE_USE_BEDROCK` | `1` | 启用 Bedrock |
| `ANTHROPIC_BEDROCK_BASE_URL` | `https://mushigen.comet.scopelyai.com/bedrock` | Bedrock 代理地址（注意是 `/bedrock`） |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH` | `1` | 跳过原生 AWS 鉴权（走代理 token） |
| `AWS_REGION` | `us-east-1` | 区域 |
| `ANTHROPIC_AUTH_TOKEN` | `sk-...` | 代理认证 token |

> 注意两套后端走的是代理的不同路径：custom → `/v1`，sdk → `/bedrock`。

## 切换示例

```bash
# 用默认 custom 后端
scripts/cli.sh "SceneMgr 是做什么的？"

# 临时切到 sdk 后端
AGENT_BACKEND=sdk scripts/cli.sh "SceneMgr 是做什么的？"

# 指定要分析的代码库
TARGET_CODE_PATH=/path/to/game-code scripts/serve.sh
```
