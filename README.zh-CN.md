# Agent Factory 下载中心

这是 Agent Factory 的公共下载与验证仓库。仓库仅包含可审查的安装脚本、隐私与安全说明、
校验和，以及 Releases 中的已编译二进制文件；不公开专有引擎或 control-plane 的源代码。

Agent Factory 不会向自身服务器发送模型提供商 API 密钥、源代码、提示词、diff、仓库路径、
终端输出或模型回复。Provider key 只保存在用户设备上，并由本地 runtime 直接发送至用户选择的
OpenAI-compatible endpoint。

24 小时试用期结束后，注册使用要求每天同步一次不含执行内容的统计批次。批次仅包含受限的模型、
任务类型、结果、耗时、token 数量以及来源明确的费用字段；不会发送代码、提示词、模型回复、路径或
provider key。完整且具有约束力的数据范围请查看 [PRIVACY.md](PRIVACY.md)。

## Linux 与 macOS

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh && sh install.sh
```

## Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

安装程序会识别操作系统与架构，从公共 GitHub Release 下载对应压缩包，先验证
`SHA256SUMS` 的 RSA-SHA256 签名，再验证压缩包 SHA-256，随后运行内置 `self-test`。
验证完成后，安装程序会自动打开本地设置页面。重复运行会安全地刷新命令链接；无界面环境可设置
`AGENT_FACTORY_NO_SETUP=1`。请使用普通用户安装，不要使用 `sudo`。

普通设置只需四个选择：provider、provider key、节省/平衡/质量模式，以及检测到的 coding
agent。Agent Factory 会自动分配角色模型。Advanced settings 提供精确模型复选框、自定义
OpenAI-compatible endpoint、每个角色的有序 fallback 路由和密钥轮换。新密钥会先验证再启用；
正在运行的任务继续使用原来的无密钥路由快照。使用 `agent-factory open` 可返回本地
dashboard；无需持久化本地数据库。

## 更新与卸载

更新时重新运行安装程序即可；它会验证新的 `latest` Release 签名，并把命令切换到新版本。
卸载二进制文件时默认保留本地设置和运行记录：

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/uninstall.sh && sh uninstall.sh
```

只有显式执行 `sh uninstall.sh --purge-state` 才会删除本地状态。Windows 用户可下载并运行
本仓库的 `./uninstall.ps1`；完整清除状态需使用 `./uninstall.ps1 -PurgeState`。
