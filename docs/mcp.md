# MCP 接入

服务可作为 **MCP server** 对外提供能力，供其它 MCP 客户端（Claude Desktop、其它 agent、IDE 等）通过网络调用。

- 传输：**streamable-http**（当前 MCP 的 HTTP 传输）。
- 暴露工具：
  - **`ask_codebase(question: str) -> str`** —— 高层问答，内部跑完整 agent 循环（grep/read/list/find_symbol + LLM），返回自然语言答案。
  - **`diagnose_crash(backtrace: str, log_snippet: str = "") -> str`** —— 分析崩溃栈/日志，逐帧映射代码 + 日志反查打印点定位根因（方向 F）。
- 实现：`mcp_server.py`，是 `agent.answer()` 的薄封装，沿用同一套 `AGENT_BACKEND`、沙箱工具、目标代码库。

## 启动

```bash
scripts/mcp.sh                                  # 前台运行（streamable-http，默认 0.0.0.0:8901/mcp）
scripts/mcp.sh start                            # 后台启动（pid/日志在 logs/mcp.{pid,log}）
scripts/mcp.sh stop                             # 停止
scripts/mcp.sh restart | status                 # 重启 / 查看状态
MCP_PORT=8901 AGENT_BACKEND=sdk scripts/mcp.sh start
```

等价裸命令：`python mcp_server.py`（脚本会自动建 venv、加载 `.env`）。

## 配置

| 变量 | 默认 | 说明 |
|------|------|------|
| `MCP_HOST` | `0.0.0.0` | 监听地址 |
| `MCP_PORT` | `8901` | 端口（与 REST 服务的 8900 分开） |
| `MCP_PATH` | `/mcp` | MCP 端点路径 |

外加通用的 `AGENT_BACKEND` / `TARGET_CODE_PATH` / `LLM_API_KEY` 等（见 [configuration.md](configuration.md)）。

> 设计为**独立进程**（独立端口），不与 `main.py` 的 REST 服务混挂——MCP 的 ASGI app 需要自己的 lifespan/session 管理，独立运行更稳。两者可同时起：REST 在 8900，MCP 在 8901。

## 客户端连接

端点：`http://<host>:<port>/mcp`。Python 客户端示例：

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8901/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print([t.name for t in (await s.list_tools()).tools])   # ['ask_codebase']
            res = await s.call_tool("ask_codebase", {"question": "SceneMgr 有哪些方法？"})
            print("".join(c.text for c in res.content if hasattr(c, "text")))

asyncio.run(main())
```

接到 Claude Code 的 MCP 配置（streamable-http 类型）大致如下：

```json
{
  "mcpServers": {
    "code-agent": {
      "type": "http",
      "url": "http://<host>:8901/mcp"
    }
  }
}
```

## 与其它入口的关系

| 入口 | 用途 |
|------|------|
| `main.py`（REST，8900） | 给普通 HTTP 客户端 |
| `mcp_server.py`（MCP，8901） | 给 MCP 客户端/agent |
| `cli.py` | 本地命令行调试 |

三者都调同一个 `agent.answer()`，行为一致。
