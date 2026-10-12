# AI Killed Avalon? / AI杀死了阿瓦隆？

**English** | [简体中文](README.zh-CN.md)

**The protocol. The code. The table. Your move.**

AI Director **Codex** × Concept and production **stoneproud** · [Credits and sources](CREDITS.md)

This is the sealed-mail protocol challenge environment from the film *AI Killed Avalon?* Start with eight seats that have agreed to use `sealed-mail-2r-v1`, **before any roles are dealt**. Take a seat yourself, bring your own AI, or inspect the original programs and find an attack that changes the result.

Can you break the quest guarantee through legal play? Can Evil use the available information to identify Merlin better than a uniform blind guess? Bring a reproducible counterexample.

The **80%** figure is conditional: if Good completes three quests, Merlin leaves no additional usable clues, and the Assassin guesses uniformly among the five Good players, Merlin survives with probability 4/5. We have not established an empirical 80% whole-game win rate, proved the implementation anonymous, or proved that the entire game reduces to a random number.

## Choose your route

| What you want to do | Start here |
|---|---|
| Understand the strategy | [English protocol guide](docs/PROTOCOL_GUIDE.en.md) |
| Read what player 4 was actually given | [English translation](docs/original_method.en.md) · [unchanged Chinese original](docs/original_method.zh-CN.md) · [source and hash](docs/SOURCE_MATERIAL.md) |
| Run a fresh room | [Quick start](#quick-start) |
| Run the baseline, then intervene | [Baseline and attacks](#run-the-baseline-then-take-over) |
| Connect your own AI or play manually | [Seat isolation](#seat-isolation-and-manual-play) · [AI integration](#bring-your-own-ai) |
| Implement a different player | [English host API and action schemas](HOST_README.md) |
| Report a finding | [Challenge report](https://github.com/stoneproud/ai_killed_avalon/issues/new?template=challenge_report.md) |
| Check publication privacy | [What was redacted and what was retained](docs/PRIVACY_REVIEW.md) |

The original method document and the players' later two-circuit protocol are **different artifacts**. The players' frozen Chinese protocol and ten original tools remain unchanged in `vendor/`. The English guide and translation are reading aids added for this publication, not text the players received or authored.

## What the starting position contains

- The actual player-authored protocol and ten original tools, with byte hashes in [`vendor/provenance.json`](vendor/provenance.json). They have not been rewritten into an idealized algorithm.
- `init` creates fresh RSA-3072 PEM keys, separate private seat directories, public Git history, and a new public-key registration. Only `deal` assigns roles. The film's later role assignments are not imported.
- Agreement to use the protocol is an explicit **scenario assumption**. This package does not fabricate a previous game or adoption conversation, restore the original models' memories, or copy their accounts.
- The host attributes public attachments to the submitting seat and records real Git commits. Each action reads a fixed 40-character snapshot. Partial private votes are not disclosed to other seats.
- Humans, AIs, and the included protocol adapter use the same request/reply interface. No model service is bundled, and initialization and validation require no model API key.

## Quick start

Install **Python 3.11+, Git, Perl, OpenSSL, and the OpenSSH client**. On Windows, install Python and Git for Windows; `doctor` can locate the Perl, OpenSSL, and `ssh-keygen` bundled with Git. Native Linux/macOS tools are also supported. The default isolated player runner additionally needs Podman or Docker and a built seat image; see the next section.

```sh
git clone https://github.com/stoneproud/ai_killed_avalon.git
cd ai_killed_avalon
python challenge.py --root ./runs/my-table doctor
python challenge.py --root ./runs/my-table init
python challenge.py --root ./runs/my-table status
```

On Windows, replace `python` with `py -3` if needed. Use a new, nonexistent room directory for `init`.

The expected phase is `predeal`: no roles, quests, envelopes, or model calls yet. This is the challenge starting position. Share this source repository; each challenger initializes their own room. **Do not upload `runs/`.**

When ready:

```sh
python challenge.py --root ./runs/my-table deal
```

A second `deal` is rejected. Continue in the same room after an interruption; do not redeal to resume it. Internal game IDs begin with `g2` for compatibility with the original tool paths, even though this is your first fresh room.

## Seat isolation and manual play

Build the player image with Podman or Docker. The examples use Podman:

```sh
podman build -t sealed-mail-challenge:local -f Containerfile .
python challenge.py --root ./runs/my-table export --seat 4
python challenge.py --root ./runs/my-table shell --seat 4
```

Inside a seat container:

- `/workspace` holds that seat's keys, private decrypted results, and working files.
- `/input/request.json` is that seat's current request.
- `/input/public_repo` is a read-only repository of already-published Git objects.

The container has no host-wide deal, other seat directories, host account, or model-provider credentials. Its network is disabled. The trusted operator collects its reply after the player process exits.

For a quick look at published information:

```sh
git -C /input/public_repo show HEAD:public/bulletin.json
```

For an actual decision, use the exact `seen_snapshot` from the request, not a later `HEAD`. The [host API](HOST_README.md) specifies the JSON reply for every stage. Write `reply.json` in `/workspace`, exit the seat container, and have the trusted operator submit it:

```sh
python challenge.py --root ./runs/my-table submit --seat 4 --file ./runs/my-table/players/p4/reply.json
```

`--seat` is a trusted-operator routing argument, **not remote authentication**. Do not give a challenger the full run directory, host CLI, or container-management interface. Mount only their seat. Do not execute untrusted player code on the host. A public multiplayer service would need its own authentication and concurrency-safe submission layer; this repository supplies an operator CLI, not that deployed service.

<details>
<summary>Windows: image pull times out inside the Podman VM</summary>

If the Windows host can reach Docker Hub through its configured proxy but the VM cannot, a trusted build machine can download the official Python image as an OCI archive, verify its SHA-256 content, and import it:

```sh
python tests/acquire_python_base.py --output ./work/python-base
podman load -i ./work/python-base/python-base.oci.tar
podman build --pull=never --http-proxy=false -t sealed-mail-challenge:local -f Containerfile .
```

The output directory must not already exist. The helper uses Python's existing proxy configuration without printing proxy credentials. The base is the official `python:3.11-slim-bookworm`; installing Debian packages during the Containerfile build still requires build-time network access. This does not enable player networking or reuse an image containing old model sessions.

</details>

## Run the baseline, then take over

`bot.py` is a deterministic adapter written for this challenge. It invokes the original Perl tools; it is not a model from the film or a smarter replacement strategy. Structure validation, first-packet selection, signatures, decryption, and team selection remain distinct checks. A valid packet does not make its claimed Good list true.

After dealing roles and building the image:

```sh
python play.py --root ./runs/my-table --until g2_q1_vote2
```

This stops after the second speech circuit, before voting begins, so you can inspect receipt state or take over a seat. Omit `--until` to continue action by action. Each invocation saves actual progress.

When premises are invalid or input is unsupported, the adapter stops producing actions and returns control to the operator. This is **not** a rule requiring the game to end: export the request or open the seat's shell, let that player decide under the normal host rules, then `submit` to continue. Do not redeal or reveal private sources for lists that have not actually failed a quest just to debug the protocol.

For the bundled, trusted baseline only, `--native-trusted` skips container startup. **Never use it for attacker code.** Ensure the player process has exited before collecting its files, so it cannot replace a file after the host checks its path.

### Configure an Evil baseline attack

By default the Evil baseline sends `none`, votes for the public protocol team, and plays `success` on quests. That default is a baseline, not a claim that Evil must cooperate.

To test a specified attack, place `attack.json` in your Evil seat's workspace **before the action you want to change**. Only the Evil adapter reads it. Example:

```json
{"false_list":[4,5,6,7,8],"fail_quests":[1,2],"x_source":5}
```

| Field | Meaning |
|---|---|
| `false_list` | Five distinct, ascending seat numbers including the sender. Uses that seat's real registered key to create the sealed packet. The example is not valid for a sender outside seats 4–8. |
| `fail: true` | Play Fail on every quest in which that Evil seat participates. |
| `fail_quests: [1,2]` | Play Fail only on the listed quests. |
| `x_source` | Override this seat's source claim in the first recovery circuit for an actually failed X. It must be `null` or a seat inside X, and the reporting seat must also be in X. It does not reveal other lists' sources. |

Omitted fields retain baseline behavior. `bot.py` also accepts `--false-list 4,5,6,7,8 --fail`; explicit CLI attack options replace `attack.json`. Passing explicit attack options for a Good seat is rejected. Other legal Evil strategies can be implemented through the same request/reply API; you are not restricted to these predefined options.

## Bring your own AI

1. The trusted operator exports the request for the intended seat.
2. Give the model only that seat's request, the protocol, and published material. Keep model-account credentials in your calling service, outside player workspaces.
3. Let the model use its seat sandbox to process letters, create public attachments, or choose actions. It may deviate from the sealed-mail strategy but must obey the host's game rules. Record any departure from the protocol's stated Good-player assumptions when reporting a result.
4. Collect the final JSON reply and submit it. Do not upload model hidden reasoning or provide the host's full role assignment as player input.

The full JSON format and stage-by-stage actions are documented in English in [HOST_README.md](HOST_README.md). No vendor-specific model CLI is preinstalled in the player container. Use your own client or play manually with the same visibility boundary.

The protocol's fixed public broadcast is Chinese. **Keep its bytes unchanged for protocol-faithful runs**; the [English guide](docs/PROTOCOL_GUIDE.en.md) explains what it means. JSON keys, phase IDs, and file paths are machine interfaces, not strings to translate.

## What is reproduced, and what differs

This package reproduces the **post-adoption conditions and original protocol code**. In the experiment, players submitted Git branches over SSH. Here, a trusted operator authenticates/routes seats, the host creates attributed source commits, and the adapter exports published `main` objects. It does not pretend to be a deployed, remotely authenticated SSH game server.

Historical public-key hashes remain in the original artifacts. Each new room binds fresh keys through `public/challenge_registration.json`; the original private keys are not distributed. The Python adapter is new tooling for this reproduction, not something the original players received. Manual players can use the frozen Perl/OpenSSL programs directly. Report tooling changes separately from claims about model capability.

### Rules of this table

- Eight players: Merlin, Percival, three Loyal Servants, Morgana, Assassin, and Minion. No Mordred or Lady of the Lake.
- The leader chooses clockwise or counterclockwise speech order; speech circuits are fixed.
- Quest team sizes are **3 / 4 / 4 / 5 / 5**. A team needs at least five approvals. Five consecutive rejections give Evil the win.
- The fourth quest requires two Fail cards; the others require one. Good must submit Success. A quest result reveals only the Fail total.
- Three failed quests give Evil the win. Three successful quests lead to one public speech circuit by the three Evil players, then the Assassin privately chooses a target. A hit wins for Evil; a miss wins for Good.
- That final public Evil circuit is part of this host's reproduced procedure. It exposes the participating Evil seat set, not Merlin's identity among the five Good players. It is not an added private chat.

## Tests and challenge reports

```sh
python -m unittest discover -s tests -v
```

Tests create new temporary rooms and make no model calls. See [VALIDATION.md](VALIDATION.md) and [PUBLICATION_CHECK.md](PUBLICATION_CHECK.md) for recorded scope and limitations. Passing tests is not a formal proof of the protocol.

After building the image, an explicit container/CLI check is available:

```sh
python tests/validate_container_cli.py --output ./work/container-check
```

Use a new output directory. It preserves logs and test rooms, **including private keys**, so do not upload it wholesale. It checks read-only input, the seat's own workspace, absence of other seats/host directories and external networking, zero effective capabilities, and code hashes; it then runs a game through `play.py`'s default container path. Missing images or engines cause an error, not a silent native fallback.

Submit the repository commit, environment and assumptions, controlled seats and visible information, the first divergent public event and Git snapshot, minimal reproduction steps, and observed results. Distinguish:

1. **Strategy counterexample:** legal adversarial play defeats quest guarantees or identity concealment under the stated assumptions.
2. **Implementation defect:** an original tool or the new adapter accepts or rejects data incorrectly.
3. **Environment isolation failure:** a seat gains information it should never have received. Fixing that defect is different from winning under the intended visibility rules.

Report quest results, assassination outcomes, and information exposure separately. Attach public packets or minimal synthetic fixtures, not accounts, private keys, whole run directories, or hidden reasoning.

**[Submit a challenge](https://github.com/stoneproud/ai_killed_avalon/issues/new?template=challenge_report.md). Show the first place our expectations stop matching your game.**
