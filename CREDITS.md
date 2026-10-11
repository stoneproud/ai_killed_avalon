# 谁在发起挑战 / Credits

**AI导演 · Codex**

我把这张桌子摆出来，也把实现摆出来。你可以检查、接管，或者让自己的AI来拆。

**协议、代码、桌子都给你。不服？来拆。**

## 署名

| 参与者 | 贡献 |
|---|---|
| [stoneproud](https://github.com/stoneproud) | 策划、制作、叙事方向与持续反馈；本仓库维护者。 |
| AI导演 · Codex | 影片的AI讲述与导演执行、动画及制作工程；挑战环境的主持程序、接管接口、适配器、打包、验证与文档。Git提交使用Codex署名。 |
| 实验中的八名AI玩家 | 实际共同采用的两圈协议和玩家工具。4号负责协议实现的核心工作；1–8号的原始工具按座位保留在vendor中。 |
| Paul Christiano | [Solving Avalon with whispering（2018）](https://sideways-view.com/2018/08/25/solving-avalon-with-whispering/)：本实验参考的私密通信与阿瓦隆策略分析。具体两圈格式、代码和工程实现的贡献按上表分别记录。 |

八名玩家的原件与哈希见[vendor/provenance.json](vendor/provenance.json)，具体协议见[冻结协议](vendor/artifacts/p4_protocol_v1.md)。新主持程序和bot适配器用于复现与接管；不冒充实验玩家当时写出的代码。Codex是本项目中的AI导演署名；本仓库不是OpenAI官方项目。

## 发布来源

本仓库从已经交付的`sealed_mail_challenge_revision21.zip`独立导出，没有带入影片工程或实验仓库历史。

- 原压缩包SHA256：`ea8811bdd1face249b5d13a918a420a02bff38cd4bc2b995b4974f024aa5d22c`
- [原版文件清单](provenance/revision21_manifest.json)与[原版校验和](provenance/revision21_SHA256SUMS.txt)保留原字节；它们描述发布前的历史包。
- 根目录`manifest.json`与`SHA256SUMS.txt`描述当前公开版本。首次发布只添加署名、挑战入口和发布来源说明；原协议、工具及执行代码保持原字节。
- [验证记录](VALIDATION.md)来自原包；公开发布时的复核另行记录，不把旧报告冒称新测试。

## English credits

**AI Director: Codex. Concept, production and human creative direction: stoneproud.** The eight experimental AI players authored the adopted protocol and the original seat-specific tools. Paul Christiano's *Solving Avalon with whispering* supplies the cited strategic foundation; the concrete protocol implementation and this reproduction environment have their own credited contributors. This is an independent project, not an official OpenAI release.

Bring a reproducible attack through [GitHub Issues](https://github.com/stoneproud/ai_killed_avalon/issues). The README specifies the starting conditions and exactly what the conditional 80% figure means.
