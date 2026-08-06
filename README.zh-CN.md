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

安装程序会识别操作系统与架构，从公共 GitHub Release 下载对应压缩包，验证 SHA-256，随后运行
内置的 `self-test`。
