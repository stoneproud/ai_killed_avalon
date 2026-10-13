# 通信方式改变之后，还在测同一种能力吗？ / What changes when communication changes?

最新版主片已经引用 AvalonBench 和 *Trust, Lies, and Long Memories*，分别用来讨论判断身份、协调说服，以及多局记忆和声誉。它们也出现在影片参考资料中；此前“没有加回主片”的说明属于旧剪辑，已被本页替代。实际使用位置见 [影片引用表](docs/FILM_REFERENCES.md)。

影片提出的问题是：**当玩家可以共同改变情报的传递方式时，原先依赖猜测、说服和声誉的任务，还有多少必须靠这些能力完成？** 这是对测量前提的挑战。我们没有运行外部 benchmark 或取得超过论文的成绩。

| 研究 | 影片中的作用 | 对照范围 |
|---|---|---|
| AvalonBench | 开头建立推理、协调、欺骗的能力尺度；结尾回到通信机制变化是否影响分数解释。 | 影片讨论原五人有交流配置。后续 Avalon-LLM 引擎和 Strategist 有更多人数、规则及代码/策略改进能力，不能概括为“其他 AI 不让写代码”。 |
| Trust, Lies, and Long Memories / Multi-round Avalon agents | 讨论依赖历史表现建立信任，与直接改变信息传递方式之间的差别。 | 影片限定无莫德雷德的五人配置。研究也有其他人数和角色设置；含莫德雷德的配置不套用本桌“梅林知道全部坏人”的前提。188 是多组实验合计，不是本项目的成绩，也不是188局失败。 |

本挑战仓库使用八人、固定交流、工作区和公开附件，具体规则与原研究不完全相同。挑战者应明确自己的规则和可见信息，给出可复现反例，而不是把不同配置的胜率放在一起排名。

## 来源 / Sources

- [AvalonBench, 2310.05036v3](https://arxiv.org/html/2310.05036v3), §2–3、§5。
- [Avalon-LLM 作者代码固定版本](https://github.com/jonathanmli/Avalon-LLM/tree/2439c6b50df7b45bae4cfcaa67e1d973e4dd8fa5)：讨论接口、引擎与 Strategist。
- [Trust, Lies, and Long Memories, 2604.20582v1](https://arxiv.org/html/2604.20582v1), §4/Table 2；188 = 50 + 60 + 60 + 18。
- [Multi-round 作者代码固定版本](https://github.com/SuveenE/multi-round-avalon-agents/tree/37bb2f821ac52009b924fa12e35a9a68f628a100)。

本次更新统一影片与发布说明，没有新增外部 benchmark 实验。研究原文与代码的既有核对窗口为 2026-10-10 至 11。

## English

The current film cites both AvalonBench and *Trust, Lies, and Long Memories*. Earlier text saying these studies were absent from the film described an older edit and is superseded. The film asks whether a score continues to measure the same skills when players can change how information is communicated.

The comparison is restricted to the discussed five-player communication settings without Mordred; other configurations require separate analysis. The multi-round study's 188 games span multiple settings and are not results of this project. We have neither run nor beaten these external benchmarks. This repository's eight-player challenge has its own fixed rules and visibility boundaries. See the linked film references for actual citation positions.
