# GitHub首次发布复核 / Publication check

- 日期：2026-10-11（Asia/Shanghai）。
- 源代码提交：`7596b2c281b702b6e4e1948671277dc5504ee934`。
- 在独立公开仓库副本运行：`python -m unittest discover -s tests -v`。
- 实际结果：**24 tests / OK / exit 0**，测试工具报告用时4185.187秒。
- 环境：Windows、Python 3.11，使用本机Git与加密工具。此次是原生测试；没有重新运行容器整局，也没有模型调用。既有容器证据仍见VALIDATION.md及原报告。
- 覆盖：新密钥与未发牌起点、完整原生基线对局、假名单和来源恢复分支、无效首包、主持规则、快照与私密信息隔离。
- 45份原包文件逐字节比较：发布前仅README和.gitattributes有编辑；根目录清单另行更新。原执行代码、测试和vendor原件未改。原包清单保留于provenance。
- 首次提交49份文件均核对暂存区与工作区原始字节；根目录manifest和校验和通过。新增本报告后更新公开清单。
- 发布候选中未发现私钥块、常见GitHub/OpenAI token模式或账户凭据文件；没有上传运行房间、模型会话或影片工程历史。

This record reports the actual fresh native test run for the first GitHub publication. The 24 tests passed; this is neither an exhaustive security proof nor a statistical estimate of the protocol's win rate. Historical validation files remain unchanged.

## English entry point / 英文入口更新 · 2026-10-12

The default README is now a complete English challenge workflow. `README.zh-CN.md` preserves the Chinese workflow, with reciprocal language links. The issue template now explains every field in both languages. The English host API was already present.

The unchanged 8,284-byte input originally given to player 4 is included as `docs/original_method.zh-CN.md`, verified against SHA256 `bc71a7bb2bd629be44bd98a9a48c13cb68cd8de48935d1620d6618dc411609ac`. A full English translation and a separate English guide to the later two-circuit implementation are added as publication reading aids. Neither is attributed to the original players or substituted for their frozen artifacts.

Verification for this documentation update: local Markdown link targets, README command parity, original input hash, unchanged tracked executable/test/vendor bytes, and regenerated publication inventory/hash files. No model calls, new game, container rebuild, or repeat of the earlier 24-test run is claimed. Machine identifiers and the original fixed Chinese broadcast remain unchanged.

本次为分语言入口、原始材料及英文导读更新；执行代码、测试、玩家原件不变。原文全文保留原字节，译文与两圈实现导读分别标注，不混成原玩家文档。当前清单核验记录见 `docs/documentation_check.json`。
