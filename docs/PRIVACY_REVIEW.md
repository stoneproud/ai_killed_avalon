# Public-material privacy review / 公开材料脱敏检查

Review date: **2026-10-12**. Scope: the published repository's files and reachable Git history, plus a separate review of the film's audience bundle. This page records the repository changes. The audience download contains sanitized source material; per-file production redaction logs are retained locally, outside the Release asset. See [film materials](FILM_MATERIALS.md) for the current download contents.

| Material / 材料 | Finding / 发现 | Action / 处理 |
|---|---|---|
| Four historical test reports / 四份历史测试报告 | 28 occurrences of local installation/project paths; five non-null tool-run IDs / 28处本机路径、5个工具运行标识 | Replace paths with `LOCAL_*` labels and IDs with stable `REDACTED_RUN_*` labels; preserve results and timings / 匿名化元数据，保留结果及耗时 |
| Executable code, tests, Containerfile / 执行代码与测试 | No actual private key or access-token material found in the reviewed files / 未发现实际私钥或访问令牌材料 | Preserve code bytes / 保留代码原字节 |
| Original input, player protocol and vendor tools / 原始材料、玩家协议和程序 | Public method text, public provenance hashes, and generic sandbox paths / 公开方法、来源哈希及通用沙箱路径 | Preserve original bytes and source hashes / 保留原件及来源哈希 |
| Credits, references, GitHub links / 署名、引用、挑战链接 | Intentionally public attribution / 有意公开的署名与出处 | Retain / 保留 |
| Example Git identity and network-test address / 示例Git身份与网络测试地址 | Synthetic identity and test destination, not a personal account or secret / 模拟身份与测试目标，不是个人凭证 | Retain; do not break tests by treating examples as secrets / 保留示例，不破坏测试 |
| Reachable Git history / 可达Git历史 | Older commits retain the previous non-secret machine paths and tool-run IDs / 旧提交仍保留原本机路径和工具标识 | No history rewrite; current files are sanitized / 最新文件已脱敏，不强推改写历史 |

The changed report files and their before/after SHA256 values are in [privacy_redactions.json](privacy_redactions.json). The original historical report hashes are provenance, not hashes of the sanitized text. Current downloadable bytes are covered by the root `manifest.json` and `SHA256SUMS.txt`.

`LOCAL_PROJECT`, `LOCAL_PYTHON`, and `LOCAL_SYSTEM_TOOLS` identify the type of local path without disclosing the producing machine's location. These are report placeholders, not runnable replacement commands. `REDACTED_RUN_*` preserves relationships between repeated run identifiers without distributing the original identifier. No gameplay event ID, public commit, packet, test result, or original protocol has been substituted.

检查未发现需要轮换的实际账号凭证、私钥或访问令牌；这不等同于无限范围的保密证明。历史提交仍可能显示旧的非凭证路径，未将“当前文件已脱敏”写成“历史已彻底清除”。此前的影片本地整包亦另行制作脱敏版；不覆盖原实验或冻结证据。

No new game or model call was run for this review. This is a publication-data review, not a new security audit of the host or a proof of the protocol.
