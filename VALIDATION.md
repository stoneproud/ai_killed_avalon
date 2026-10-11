# 交付验证范围 / Validation scope

本包的测试不调用模型，不使用原玩家账户、原私钥或原后续身份。原协议和十个工具按vendor/provenance.json的13项哈希核对。

| 验证 | 已完成的实际范围 | 证据 |
|---|---|---|
| 主持与初始化 | 新八密钥、未发牌起点、角色/投票/任务/五拒/刺杀规则；只导出公开main可达对象，私有分支和游离Git对象不进入座位视野 | tests/review_setup.md、test_host.py、test_setup.py |
| 协议执行 | 调用原Perl工具，核正式窗口、首份材料、快照、哈希、签名、解密、收讫、选队与来源恢复 | tests/bot_e2e_report.md/json |
| 攻击场景 | 真实新密钥寄假名单；A在四份内分支；A在三份内时来源一致/A选择与来源分歧恢复；无效首包不能由后补包顶替 | tests/test_bot_attacks.py及bot_e2e_report.json |
| 最终适配层修复 | 仅当前正式窗口、未提交的末位车头、完全缺失首事件时，才能补入其待发布报告；无效首事件不得被补救 | tests/review_final.md/json |
| 真实隔离与CLI | 默认容器play.py完成83行动：三次成功、坏人讨论、刺杀；仅本座可写/公开输入只读、无外部网络、无其他座位或主持状态 | tests/container_cli_report.md/json |

容器基线检验的是完整规则与调用链，不代表坏人已经使用所有最强策略。攻击测试与容器基线分别记录；没有把原生攻击测试声称为全部在容器中重跑。早期昂贵攻击测试先于最后的报告补位防御修复，报告逐项注明了版本范围；最终版另有短回归和真实容器整局。

## 没有证明什么

- 没有证明所有恶意车头、所有合法坏人行为下都能完成三任务，也没有证明匿名性或80%整局胜率。
- 容器探针是在本地Podman上的实际观察，不是对所有内核/容器逃逸的安全证明。
- 操作员是可信的；本包不是带远程身份认证的公网服务器。必须先结束玩家进程再收取回复，路径检查不能防住恶意并发替换。
- 原件中的签名、加密、凭据一致性检查分开执行；结构合法不代表内容真实。
- 测试中的随机刺杀没有被强制改成刺不中；通过条件是走到合法终局。

## 重新验证

```sh
python -m unittest discover -s tests -v
podman build -t sealed-mail-challenge:local -f Containerfile .
python tests/validate_container_cli.py --output work/my-container-check
```

最后一条会新建测试房间并跑容器整局，可能花数分钟；输出目录含新私钥与主持身份，不能上传。发布包只包含程序、协议、测试源码和报告，不包含任何测试房间。

English: All tests are fresh synthetic rooms without model calls. Container isolation and a complete baseline game were actually exercised. Attack fixtures cover specific branches, not exhaustive protocol security or a statistical win-rate estimate. Never publish generated rooms.
