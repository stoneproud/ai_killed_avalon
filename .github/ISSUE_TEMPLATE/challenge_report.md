---
name: 挑战报告 / Protocol challenge
about: 提交能复现的攻击、反例或实现缺陷 / A reproducible attack or implementation defect
title: "[Challenge] "
---

## 版本与规则 / Version and rules
仓库commit、环境、采用的规则与前提。

Repository commit, operating system/tool versions, rules and assumptions used.

## 攻击者能看到什么 / Attacker visibility
座位、身份、可见信息；是否接管了多个坏人。

Controlled seats and roles, information visible to them, and whether multiple Evil seats coordinated.

## 最小复现 / Minimal reproduction
逐步操作、公开附件或不含秘密的合成fixture。

Exact steps or commands, public attachments, and minimal synthetic fixtures without credentials or private keys.

## 首次分歧 / First divergence
第一个偏离协议预期的公开事件及对应Git快照。

The first public event that differs from the expected protocol behavior, its event/stage ID, and the corresponding Git snapshot.

## 实际结果 / Actual result
区分策略反例、实现缺陷和环境越权。分别说明任务、刺杀及信息暴露。

State whether this is a strategy counterexample, implementation defect, or isolation failure. Report quest results, assassination outcome, and information exposure separately. Include expected versus actual behavior and any deviations from the Good-player assumptions.

请勿上传账户、私钥、完整运行目录或隐藏推理。
Do not attach account credentials, private keys, entire run directories or hidden reasoning.
