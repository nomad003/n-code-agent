# 文档索引

游戏服务器 / 战斗 / 客户端 / 引擎 代码理解服务 —— 项目文档。

| 文档 | 内容 |
|------|------|
| [architecture.md](architecture.md) | 整体架构、请求流程、双后端、工具层 |
| [custom-backend.md](custom-backend.md) | custom 后端工作原理：如何按需检索代码、分析问题、组织答案，以及 tool-calling 循环、消息历史、stuck 检测 |
| [configuration.md](configuration.md) | 全部环境变量、`.env`、两套后端各自的配置 |
| [api.md](api.md) | HTTP 接口（`/ask`、`/health`）、CLI、脚本 |
| [mcp.md](mcp.md) | MCP server 接入（`ask_codebase`，streamable-http） |
| [testing.md](testing.md) | 测试运行方式、覆盖范围、端到端 verify |
| [deployment.md](deployment.md) | 部署、迁移、Git LFS、vendored CLI、常见问题 |
| [roadmap.md](roadmap.md) | 已落地优化、舍弃的设计、后续可选方向 |

快速上手见项目根目录的 [README.md](../README.md)。给 Claude Code 的工作指引见 [CLAUDE.md](../CLAUDE.md)。
