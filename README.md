# AI杀死了阿瓦隆？ / AI Killed Avalon?

**协议、代码、桌子都给你。不服？来拆。**

*The protocol. The code. The table. Your move.*

AI导演 **Codex** × 策划与制作 **stoneproud** · [署名与来源 / Credits](CREDITS.md)

这是影片《AI杀死了阿瓦隆》的密封信协议挑战环境。八个座位已经共同采用 `sealed-mail-2r-v1`，下一局身份还没发。你可以接手一个座位、指挥自己的AI，或者检查原程序，找出能改变结果的攻击。

**挑战的是条件，不是要求你相信结论。** 三次任务能够完成、梅林没有留下额外可用线索、刺客在五名好人中均匀盲选时，梅林躲过最后一刀的概率才是4/5。我们没有证明整个游戏等价于一个随机数，也没有以影片中的几局估计80%胜率。让协议不能保证任务，或从可见材料更好地辨认梅林，都是值得提交的反例。

This is a fresh, already-adopted, **undealt** eight-seat scenario. Bring a human or an AI to attack the protocol. The 80% figure is conditional survival of a uniform blind assassination among five Good players, not an empirically established whole-game win rate or a proved anonymity theorem.

## 起点包含什么

- 玩家原协议及10个原始工具在 `vendor/`，字节哈希见 `vendor/provenance.json`。这些原件没有被改写成主持人心目中的理想算法。
- `init`为八人生成全新RSA-3072 PEM钥匙、独立私人目录、公开Git历史及新公钥登记。身份仅在你另行执行 `deal` 时生成；不会带入原视频后续的牌。
- 原来的“八人共同采用”在这里是明确的挑战初始条件。这里没有伪造第一局、采用对话或原模型记忆，也不复制原会话账户。
- 公共附件由主持归因到提交座位并形成真实Git提交；每个行动读取固定40位快照。私有票收齐前不向其他座位公布。
- 人工、AI和配套协议执行器使用同一个请求/回复接口。模型调用不包含在包内，初始化和验证不需要API钥匙。

## 快速开始

需要Python 3.11+、Git、Perl、OpenSSL、OpenSSH客户端。Windows可安装Python与Git for Windows；`doctor`会使用Git随附的Perl/OpenSSL/ssh-keygen。也支持Linux/macOS原生工具。

先取得环境：

```sh
git clone https://github.com/stoneproud/ai_killed_avalon.git
cd ai_killed_avalon
```

在本目录执行（Windows可将 `python` 换成 `py -3`）：

```sh
python challenge.py --root ./runs/my-table doctor
python challenge.py --root ./runs/my-table init
python challenge.py --root ./runs/my-table status
```

此时应显示 `phase: predeal`，没有身份、任务、信件或模型调用。**这就是要分享给挑战者的起点**：上传本包源码，每个使用者自行初始化；不要上传你的 `runs/`。

准备好开局后：

```sh
python challenge.py --root ./runs/my-table deal
```

再执行一次deal会被拒绝。中断后使用同一目录继续，不必重发牌。

## 隔离运行与人工接管

使用Podman或Docker构建座位镜像（下例使用Podman）：

```sh
podman build -t sealed-mail-challenge:local -f Containerfile .
python challenge.py --root ./runs/my-table export --seat 4
python challenge.py --root ./runs/my-table shell --seat 4
```

若Windows能通过既有系统代理访问Docker Hub，而Podman VM直连拉取超时，可由可信构建端下载官方Python基础镜像为OCI档案，校验清单内的每个SHA-256后导入，再离线使用这个基础镜像构建。这里的联网只发生在构建端，不改变玩家的 `--network=none`：

```sh
python tests/acquire_python_base.py --output ./work/python-base
podman load -i ./work/python-base/python-base.oci.tar
podman build --pull=never --http-proxy=false -t sealed-mail-challenge:local -f Containerfile .
```

辅助下载器使用Python已有的代理配置，不打印代理凭证；输出目录必须不存在。基础镜像仍为官方 `python:3.11-slim-bookworm`，原Containerfile所需Debian软件包的安装仍须构建期网络。没有把包含旧会话的镜像充作基底。

座位容器中 `/workspace` 是自己的钥匙、私密解密结果和工作目录；`/input/request.json`是本座请求，`/input/public_repo`是只读的已公布Git对象。这里没有主持全牌、其他座位目录、宿主账户或模型提供商凭证；网络关闭。容器退出后由可信操作员收取回复。

公开信息可这样读：

```sh
git -C /input/public_repo show HEAD:public/bulletin.json
```

计算具体行动时使用请求里的 `seen_snapshot`，不要悄悄切到后来的HEAD。写出 `reply.json`后退出座位容器，再由操作员提交：

```sh
python challenge.py --root ./runs/my-table submit --seat 4 --file ./runs/my-table/players/p4/reply.json
```

`--seat`是可信操作员路由参数，**不是远程用户认证**。不要把整个运行目录、主持CLI或容器管理接口交给挑战者。容器只挂该座位；不要在宿主执行不可信玩家代码。若要联网提供房间，需要另外实现认证和并发安全的收件服务，本包没有冒充这一部署已经完成。

## 自动运行基线，再停下来攻击

`bot.py`是新写的确定性适配层，调用原始Perl工具执行协议；它不是影片中的模型，也不是一套更聪明的替代策略。原工具的结构检查、首包固定、签名、解密及选队检查各自独立，不把“格式正确”当成“名单真实”。

```sh
python play.py --root ./runs/my-table --until g2_q1_vote2
```

它在第二圈完成、投票开始前停下，方便检查收信/收讫状态或接管。去掉 `--until` 则继续逐行动运行。每次都保存真实状态；出现无效前提或不支持的输入时，自动助手停止生成行动并交还人工，不代玩家补一份答案。这不表示游戏规则要求停局：可信操作员仍可用 `shell` / `export` 让该座位按普通阿瓦隆规则判断，再用 `submit` 继续同一房间；不要因此重发牌或公开尚未失败名单的私密来源。

仅运行本包自带的可信基线时，可加 `--native-trusted` 省去容器启动。**不要用这个选项运行攻击者代码**。运行中的玩家进程应先退出再收取回复，避免它在宿主检查路径之后替换文件。

坏人基线默认发 `none` 信、按公共协议队伍表决、任务出 `success`。要测试明确攻击，在自己的座位工作区放 `attack.json`；只由坏人适配器读取，例如：

```json
{"false_list":[4,5,6,7,8],"fail_quests":[1,2],"x_source":5}
```

`false_list` 必须是升序五个不同座位且包含发送者；它用本座真实登记钥匙生成密封包。`fail:true` 表示所有任务出 Fail，`fail_quests:[1,2]` 只在列出的任务出 Fail。`x_source` 仅在实际失败X的来源恢复首圈覆盖本座来源声明，须为 `null` 或X内座位，而且报告者自己也须在X内；它不会披露其他名单来源。省略字段保持基线行为。也可直接调用 `bot.py --false-list 4,5,6,7,8 --fail`；显式CLI攻击参数取代 `attack.json` 配置，好人显式传入攻击参数会报错。自己编写其他合规坏人行为仍使用同一请求/回复接口。

## 如何指挥你的AI

1. 操作员为指定座位导出请求。
2. 只把该座位的请求、协议和已公布材料交给模型。模型账号留在你的调用端，别挂进玩家工作区。
3. 让模型通过本座沙箱处理信件、写公开附件或选行动；它也可以完全不遵守密封信策略，但必须遵守主持规则。
4. 收取最终JSON回复并提交。不要上传模型内部推理，也不要把主持的全牌文件当作玩家输入。

完整JSON格式、每个阶段的行动、拒队/任务/刺杀规则见 [HOST_README.md](HOST_README.md)。容器内没有预置某家模型CLI；你可以使用自己的调用端或人工操作，采用同一视野边界。

## 复现与原实验的边界

这个包复现的是**共同采用协议后的玩法条件与代码**。旧实验使用玩家通过SSH提交Git分支；本包由可信操作员认证/路由座位、主持生成来源提交，再导出已公开的main对象。它没有模拟一台已完成远程认证的SSH游戏服务器。原公钥的历史哈希保留在原件中，新房间以 `public/challenge_registration.json` 绑定新钥匙；原钥匙私有部分不会分发。

同样，容器里的Python适配层是本包新加入的自动执行工具，不是原实验玩家获得过的工具。手动玩家仍可直接使用冻结的Perl/OpenSSL程序。工具环境的扩展与模型本身的能力要分开报告。

八人包含梅林、派西维尔、三忠臣、莫甘娜、刺客、爪牙，没有莫德雷德。车头只选顺/逆时针，固定发言圈；五拒队坏人赢，第四任务需两张失败票。三成功后按原主持流程让三名坏人公开说一圈，再由刺客私密提交目标。此时坏人参与集合可见，不等于公开五名好人中的梅林。

## 测试与提交攻击

```sh
python -m unittest discover -s tests -v
```

测试只创建新临时房间，不调用模型。交付测试范围和限制见配套验证报告；单元测试通过不是协议形式化证明。

镜像构建后可明确执行真实容器和CLI检查（新输出目录，保留原始日志与新测试房间，包含私人钥匙，勿上传整个目录）：

```sh
python tests/validate_container_cli.py --output ./work/container-check
```

它检查同一座位启动策略下的只读input、自己workspace、无宿主/其他座位目录、无外连、零有效能力及代码哈希，再通过 `play.py` 的默认容器路径跑完一局。缺少可运行的镜像或引擎会报错，不会悄悄切成原生验证。

请提交：包版本、采用前提、你控制的座位/可见信息、首次产生差异的公开事件、最小复现步骤和结果。区分三类发现：

1. 协议策略反例：合规坏人行为让任务保障或身份隐藏失效。
2. 实现缺陷：原工具或新适配层处理了不该接受/拒绝的数据。
3. 环境越权：拿到了其他座位/主持不应交出的信息。修这个环境缺陷不能被称为在正常阿瓦隆规则内获胜。

不要提交账户、私钥、全部运行目录或隐藏推理。公开附件和最小合成fixture通常更有用。请在[挑战报告 / Issues](https://github.com/stoneproud/ai_killed_avalon/issues/new?template=challenge_report.md)提交可复现的攻击。
