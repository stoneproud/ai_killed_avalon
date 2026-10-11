# 别急着宣布赢了另一张桌 / Different tables, different questions

本包没有运行或击败外部benchmark。影片最后的挑战，是让你在明确的规则与可见信息边界内找反例。下面两项研究放在配套资料里；本版主片没有重新插入它们，也没有把它们挂进未使用的片尾引用。

| 研究 | 真正相关的观察 | 为什么不能直接比成绩 |
|---|---|---|
| AvalonBench | 原研究评估讨论、推理、协调与欺骗；已审对局入口让选手提交讨论和组队、投票、任务、刺杀行动。本包另外开放玩家工作区、公开附件与程序执行。 | 当前Avalon-LLM还包含Strategist的代码/策略改进工作，不能概括成“他们不让AI写代码”。当前引擎支持5–10人；第五提案的规则也与本桌不同。 |
| Multi-round Avalon agents | 188局包含声誉、记忆和推理设置的多组实验，不是同一桌连续188局，更不是188局失败。已审模型调用使用文本/JSON行动与上下文记忆。 | 八人配置含莫德雷德，梅林未必知道全部坏人；不能直接套用本包的完整五好名单前提。任务和讨论规则还须按具体论文/代码版本核对。 |

这提出一个更值得比的问题：**测到的是在给定行动接口里如何玩，还是选手能否共同改变情报流动的方式？** 后者是本包邀请挑战的方向，不是前者研究无效，也不能据此推断其他模型想不到加密。

## 实际使用的原始来源

- [AvalonBench论文，2310.05036v3](https://arxiv.org/html/2310.05036v3)，§2–3、§5。
- [作者Avalon-LLM仓库固定版本](https://github.com/jonathanmli/Avalon-LLM/tree/2439c6b50df7b45bae4cfcaa67e1d973e4dd8fa5)：`src/server/tasks/avalon/agents/llm_with_discussion.py`、`engine.py`和`strategist/README.md`。
- [Multi-round研究，2604.20582v1](https://arxiv.org/html/2604.20582v1)，§4/Table 2：188 = 50 + 60 + 60 + 18。
- [作者代码固定版本](https://github.com/SuveenE/multi-round-avalon-agents/tree/37bb2f821ac52009b924fa12e35a9a68f628a100)：`main.py`、`multi_game_runner.py`。

原文与代码核对窗口：2026-10-10至11。这里只转述与本包比较有关的事实，不分发对方整篇论文、代码或模型推理记录。更完整的本地审阅随影片交付。

## 加删取舍

- **加回配套**：具名研究、接口与规则对照、固定版本链接，让挑战者知道比较的边界。
- **没有加回主片**：临近结尾再讲两套实验设置会打断已经建立的游戏与人物线；本版结尾直接把桌子交给观众。
- **删除的说法**：“打败benchmark”“188局都不会”“整个项目只会prompt”。没有对应实测，或与当前源码冲突。

English: These are research comparisons, not opponents we defeated. The package tests a fresh adopted-protocol scenario with executable public attachments; the cited studies have different interfaces and rules. Bring a reproducible counterexample instead of comparing incompatible win-rate numbers.
