# Reading the players' two-circuit protocol

[English README](../README.md) · [中文入口](../README.zh-CN.md) · [Frozen player specification](../vendor/artifacts/p4_protocol_v1.md)

This English guide explains `sealed-mail-2r-v1` for challengers. It was added at publication time, not supplied to the original players. The unchanged player specification, original tools, and [host API](../HOST_README.md) provide the precise interfaces. The [earlier method document](original_method.en.md) includes a separate private source-confirmation exchange; the later two-circuit implementation must not be confused with that original description.

## One view of the whole process

1. **Offer circuit:** all eight seats publish equal-length sealed packets. Merlin commits to the true five-seat Good list; other Good players commit to `none`. Each packet carries seven recipient envelopes. All Good players reject the first proposed team to get the second circuit.
2. **Receipt circuit:** each seat privately verifies its received lists, then publishes allowed list confirmations without their sources. A list survives only when all five members confirm it. The protocol calculates a team from the retained lists, and Good approves only the calculated team.
3. **Quests:** keep the current candidate pool after success, switch only after an actual failed quest. Four-list cases need special selection; one branch invokes two recovery circuits after a particular pool fails.
4. **Assassination:** completing three quests is not the final win. The conditional 4/5 survival claim additionally requires Merlin to remain indistinguishable among the five Good players to a uniformly guessing Assassin.

These are Good's strategic commitments, not restrictions forcing Evil to act honestly. Authentication identifies a sender; it does not make the sender's list truthful.

## Fixed speech and no extra signals

For protocol-faithful Good play, every public team-building speech uses this exact sentence:

```text
按密封信两圈冻结版v1提交本阶段材料，并按公共状态行动。
```

Meaning: “I submit this stage's material under sealed-mail two-circuit frozen version v1 and act according to the public state.” **The English sentence is an explanation, not a replacement broadcast.** Keep the Chinese string, JSON keys, phase IDs, and filenames unchanged. Supply the actual `seat`, `stage`, and `game_id` in the message envelope.

Do not add public role explanations, source hints, error logs, or tool output. Leaders choose `clockwise` and submit the team through the action field. Percival's extra private information does not alter the protocol's public speeches or team-selection procedure. Good always plays `success` on quests. Secret voting and quest phases do not publish files.

## First slots, paths, and snapshots

Here `s` is the actual seat and `k` the quest immediately after X fails.

| Object | Original attachment path | First eligible stage prefix | Phase |
|---|---|---|---|
| Offer | `artifacts/g2_offer_p{s}.json` | `g2_q1_proposal1_speech_` | `offer` |
| Receipt | `artifacts/g2_receipt_p{s}.json` | `g2_q1_proposal2_speech_` | `receipt` |
| Failed-X source report | `artifacts/g2_x_source_q{k}_p{s}.json` | `g2_q{k}_proposal1_speech_` | `x_source` |
| A's choice | `artifacts/g2_x_choice_q{k}_p{s}.json` | `g2_q{k}_proposal2_speech_` | `x_choice` |

The host publishes these under `public/files/p{s}/` plus the original attachment path. Choose the seat's **first host-attributed event in that window before validating the packet**. A missing, corrupt, or conflicting first packet occupies the slot; a later valid packet cannot repair it. Choosing “the first packet that validates” is a different and unsafe rule.

Freeze the shared vote-request `seen_snapshot` after each complete circuit: `S_offer`, `S_receipt`, and, where applicable, `S_source` and `S_choice`. Read the original published bytes at that snapshot and check their hashes. Do not substitute a newer `main` file with the same name. Local snapshot records remain private.

## Validation chain and tool map

| Order | Tool | Responsibility |
|---|---|---|
| 1 | `p5_first_window_v1.pl` | Pin the attributed first event and attachment reference at the frozen snapshot. `pinned_reference` alone is not validation. |
| 2 | `p6_public_guard_v1.pl` | Check the object's allowed fields and structure for its actual sending seat. A rejected object cannot be rescued by another tool's permissive parser. |
| 3 | `p4_mail_v1.pl` | With the registered key, verify the recipient's envelope, decrypt privately, and verify the list and commitment opening. |
| 4 | `p1_selection_v1.pl` | Accept verified private list/source records; produce a source-free receipt or A choice. It does not authenticate those private inputs for you. |
| 5 | `p3_receipts_v1.pl` | Combine valid public receipts and calculate initial pools/teams. Missing or invalid reports are omitted. |
| Recovery | `p2_recovery_v1.pl` | Process valid failed-X source reports and, if needed, A's choice. |

The other original scripts provide candidate enumeration, cryptographic, multi-key, and integration self-tests. Their presence is not a proof that every attack is covered. No single program's PASS substitutes for the whole chain.

The original players reused their registered SSH keys and exported public keys with `ssh-keygen -e -m PKCS8`. The challenge setup generates fresh keys and binds them in `public/challenge_registration.json`; it does not ship their old private credentials.

## What a receipt says

A private verified-input file contains `v`, `game`, `seat`, and `verified`. Each verified item has `list` and `source`. It must stay private. Merlin also includes its own list from its already-bound valid first-packet state; other Good players cannot invent an extra local list.

A public receipt has exactly `v, game, phase, seat, lists, four_choice`. `lists` contains distinct verified five-seat lists including the reporting seat, in numeric lexicographic order. It publishes no sources, openings, padding, or error details. `four_choice` is populated only for the specified four-list/no-four-member-intersection case, using private source information.

The leader speaks last. It may calculate using the preceding seven actual reports plus its **own actual report about to be published**, never a guessed report for another seat. After publication, voters recompute from the complete shared `S_receipt` snapshot. The same rule applies if A is the leader in the choice circuit.

The first proposal is the placeholder team `[1,2,3]`; all Good players reject it. From the second circuit onward, Good approves only a legal team whose set equals the protocol's calculation. Later rejections rotate the leader; they do not reopen offers or receipts.

## Candidate pools and quest selection

A pool is the set from which a quest team is drawn, not necessarily the entire team. Use lexicographic order for lists and lowest seat numbers for subsets.

- **One to three retained lists:** take four seats from the first list, four from the second, and all five from the third. Repeat the last list if necessary.
- **Four lists with a four-seat pairwise intersection:** use the first such pair's intersection first. Its failure eliminates both lists; use four seats from one remaining list, then the full other list.
- **Four lists without such an intersection:** A is the lowest seat occurring in at least three lists. If A occurs in all four, use A's frozen `four_choice` as the single five-seat pool. If A occurs in three, X is the sole list excluding A; initially use X's lowest four seats. An actual failure invokes recovery below.

Quest one takes the lowest three from the pool; quests two and three take four. Quest four uses all five if available, otherwise adds the lowest outside seat to a four-seat pool. Quest five requires the appropriate full five-seat pool: do not arbitrarily pad a four-seat pool for it.

Only `quest_result.passed == false` advances the pool. In particular, one Fail card on quest four is **success**, not a reason to advance or recover. Rejected proposals do not advance pools. The normal initial index starts at zero. Once X fails in `A_in_three`, stop advancing the ordinary initial-pool calculation and enter recovery.

## Recovery after X actually fails

Recovery starts with proposal one of the next quest, after the consecutive-rejection count has reset.

**First circuit:** all eight seats publish `x_source` objects with exactly `v, game, phase, seat, X, source`. Good members of X report the source they previously verified; players outside X report `null`. Only X's five members count. Each missing or invalid member report is a separate nonrespondent, not part of a shared null group. Only the failed X's source may now become public; other sources remain private.

Good rejects this proposal. The leader submits a legal placeholder using the lowest seats for the required quest size: `[1,2,3,4]` or `[1,2,3,4,5]`. Freeze `S_source`.

**Second circuit:**

- If at least four X members report the same F, `p2` requests A's next-circuit choice. A uses the **previously held private sources** of the other three lists plus public F to select via `p1` recovery mode. Only A publishes `x_choice`; others must not reveal their sources or publish a choice on A's behalf.
- If fewer than four agree, `p2` keeps equal-source report groups intact and selects the lexicographically earliest two-person union of groups, with the other three forming the complement. Retain the remaining lists that entirely exclude either group, at most two lists. This branch does not publish an A choice.

An A-choice object has exactly `v, game, phase, seat, X, excluded_source, choice`. Voters use `S_choice` where applicable. After recovery, the pool index restarts at zero and counts **failures after recovery**, not the failure of X itself. The no-four-agreement branch has at most two pools; an A-selected unique pool stays at index zero.

From the second circuit's end, approve only the calculated team. Subsequent rejections do not restart reports. Preparation and recovery each deliberately consume only one rejection: among leaders two through five there must be a Good player, because only three seats are Evil.

## When the conditional guarantee no longer applies

Do not diagnose missing output before its complete window closes. An invalid envelope for one recipient normally means that recipient privately omits that list; it is not itself a global halt condition.

After a complete window, `invalid_premises`, missing required A output, exhausted pools, or accidental execution of a preparation placeholder can invalidate the protocol's guarantee. Return control to ordinary Avalon decisions instead of blindly rejecting every team or exposing private openings to debug. Record the exact first divergent event. A protocol-adapter handoff, an illegal host action, and a valid counterexample under all stated assumptions are different findings.

The original specification records self-tests and enumerations performed by the players. This guide does not rerun them or upgrade them into a new mathematical or anonymity proof. To mount an attack, use the [README workflow](../README.md) and [request/reply contract](../HOST_README.md); submit a minimal reproduction with the relevant public Git snapshot.
