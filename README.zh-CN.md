# Agent Factory 下载中心

这是 Agent Factory 的公共下载与验证仓库。仓库仅包含可审查的安装脚本、隐私与安全说明、
校验和，以及 Releases 中的已编译二进制文件；不公开专有引擎或 control-plane 的源代码。

Agent Factory 不会向自身服务器发送模型提供商 API 密钥、源代码、提示词、diff、仓库路径、
终端输出或模型回复。Provider key 只保存在用户设备上，并由本地 runtime 直接发送至用户选择的
OpenAI-compatible endpoint。

远程技术遥测默认关闭，不包含执行内容，并且必须同时取得本地与服务器端的明确同意。完整且具有
约束力的数据范围请查看 [PRIVACY.md](PRIVACY.md)。

## Linux 与 macOS

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh
less install.sh
sh install.sh
```

## Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1
Get-Content .\install.ps1
.\install.ps1
```

安装程序会识别操作系统与架构，从公共 GitHub Release 下载对应压缩包，验证 `SHA256SUMS` 的
Ed25519 签名与压缩包 SHA-256，随后运行内置的 `self-test`。Beta 版本有意不依赖付费的 Apple
公证或 Windows Authenticode。Windows 需要 OpenSSL 完成同样的 Ed25519 验证；安装程序会显示
Authenticode 状态，但不会阻止明确标记的未签名 Beta 版本。

验证完成后，安装程序会自动打开本地设置向导。若要稍后设置，请使用
`AGENT_FACTORY_SKIP_SETUP=1`（Windows 可使用 `-SkipSetup`），然后运行：

```bash
agent-factory setup
```

向导可管理多个 OpenRouter、DeepSeek、Ollama 或 OpenAI-compatible provider profile，并为每个
角色选择“provider + model”。新增或轮换的密钥会先经过验证；profile 可以停用或删除。每个密钥
版本都作为独立记录保存在操作系统凭据存储中，不会写入 JSON；密钥轮换后，已运行任务仍保留其
原始的无密钥路由快照。Codex 和 Claude 可自动注册，其他 host 会获得可直接粘贴的配置。个人
设置、有限缓存和无内容同步队列共用一个私有 `agent-factory.json`，不使用持久化 SQLite 数据库。
MCP 会按需启动本地 runtime；使用 `agent-factory open` 可重新打开 dashboard。

普通设置仅需四步：选择 provider、粘贴密钥、选择“节省 / 平衡 / 最高质量”模式，并连接自动检测到的
coding agent。Agent Factory 会自动分配角色模型。精确模型复选框、自定义 endpoint 和手动角色路由
位于 Advanced settings。同一本地页面也可更换密钥、查看试用状态、激活 Agent Factory 和管理
MCP 连接。

Agent Factory 账户密钥与 provider key 完全分开。使用 `agent-factory activate` 输入账户密钥；
两个密钥会作为不同记录保存在操作系统凭据存储中，重启后仍可使用。前 24 小时无需 Agent
Factory 账户密钥。
