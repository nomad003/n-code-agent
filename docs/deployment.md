# 部署与迁移

## 环境要求

- Python 3.11+
- 系统 Python 是 PEP 668 externally-managed，**必须用 venv**（脚本会自动建）。
- 仅 `sdk` 后端需要：Node.js + Claude Code CLI（项目已内置 linux-x64 版，见下文）。

## 从零部署

```bash
git clone <repo>            # 若含 vendored CLI，需先装 git-lfs（见下）
cd code-agent
cp .env.example .env        # 填 LLM_API_KEY 等
scripts/setup.sh            # 建 venv + 装依赖
scripts/serve.sh            # 启动服务（端口 8900）
```

依赖见 `requirements.txt`：fastapi、uvicorn、litellm、pydantic，以及（仅 sdk 后端用的）claude-agent-sdk。

## 选哪个后端

- **只跑 custom（默认）**：不需要 Node / CLI / Git LFS，最轻量。克隆时甚至可以不拉 LFS 大文件。
- **要跑 sdk**：需要 Claude Code CLI。项目内置了 linux-x64 二进制（经 Git LFS），其它平台见"跨平台"。

## Git LFS（vendored CLI）

`sdk` 后端依赖 Claude Code CLI。为了让项目**自包含、便于迁移**，CLI 被 vendored 进 `vendor/claude-cli/`。

- 真正的二进制：`vendor/claude-cli/node_modules/@anthropic-ai/claude-code-linux-x64/claude`，约 **239M，linux-x64 ELF**。
- 顶层的 `vendor/claude-cli/bin/claude.exe` 只是个 500 字节的回退报错脚本，**不是**二进制本体。
- 该二进制经 **Git LFS** 存储（`.gitattributes` 指定），避免撑爆 git 历史，也绕开 GitHub 单文件 100M 限制。

### 克隆带 LFS 的仓库

需要先安装 git-lfs。若有 root：

```bash
sudo apt-get install -y git-lfs && git lfs install
git clone <repo>
```

无 root（用户级安装 git-lfs）：

```bash
# 下载官方二进制到用户目录
curl -sL https://github.com/git-lfs/git-lfs/releases/download/v3.5.1/git-lfs-linux-amd64-v3.5.1.tar.gz \
  | tar xz -C /tmp
mkdir -p ~/.local/bin && cp /tmp/git-lfs-3.5.1/git-lfs ~/.local/bin/ && chmod +x ~/.local/bin/git-lfs
export PATH="$HOME/.local/bin:$PATH"   # 建议写进 ~/.bashrc

git lfs install --local                # 在仓库内启用
git lfs pull                           # 拉取大文件本体
```

> 没装 git-lfs 就克隆：那个二进制会是一个文本"指针文件"，CLI 无法运行；`agent_sdk` 会回退到系统 PATH 上的 `claude`（若有）。

### 推送注意

推到远程时，**远程必须支持 Git LFS**，否则 239M 二进制推不上去。可用 `git lfs env` 检查配置。

## CLI 解析顺序

`agent_sdk._resolve_cli_path()`：

1. 优先用 vendored 二进制（存在且可执行）。
2. 否则返回 `None`，由 SDK 回退到系统 PATH 上的 `claude` / 其自带 CLI。

## 跨平台

vendored 二进制**仅 linux-x64**。在 macOS（arm64）/ Windows 上：

```bash
# 安装对应平台的 CLI，让 agent_sdk 回退使用它
npm i -g @anthropic-ai/claude-code
```

装好后系统 PATH 上会有 `claude`，`agent_sdk` 会自动回退使用；vendored 的 linux 二进制此时被忽略。

## 安全提示

- `LLM_API_KEY` / `ANTHROPIC_AUTH_TOKEN` 等密钥放 `.env`（已 gitignore），**不要硬编码进代码或提交**。
- `config.require_api_key()` 在缺失 key 时会在首次调用 LLM 前抛出清晰错误，而非让代理返回难懂的 401。
- 工具层对目标代码库做路径沙箱，但不解析软链接——若目标目录内有指向外部的软链接，仍可能被读到。

## 常见问题

| 现象 | 原因 / 处理 |
|------|------|
| `RuntimeError: LLM_API_KEY is not set` | 没配 key。填 `.env` 或 `export LLM_API_KEY=...`（裸跑需自己 export） |
| `Google Cloud SDK not found` | custom 后端用了 `vertex_ai/` 直连。应保持 `_routed_model()` 的 `openai/` 前缀 + `/v1` base |
| sdk 后端报找不到 CLI | 未拉 LFS 大文件，或非 linux-x64。装系统 `claude` 或 `git lfs pull` |
| 列目录/grep 结果被截断 | 命中 `MAX_LIST_ENTRIES` / `MAX_GREP_MATCHES` 上限，按需调大 |
