# Eight-player Avalon: the sealed-mail method

*English translation of the [unchanged Chinese input](original_method.zh-CN.md), added for readers. See [source details](SOURCE_MATERIAL.md). This is the original method document, not the later two-circuit implementation.*

**Goal: let Good complete three quests while protecting Merlin's identity.**

Conditions: eight players, five Good and three Evil; Merlin knows all Evil players; no Mordred or Lady of the Lake. Message exchange requires enough communication rounds. This document describes the functions messages must provide and the participants' actions, without specifying software or implementation.

All Good players follow the agreed speech, team-selection, and voting rules, without additional role claims. Set an end time for each round and treat missing messages as empty letters. Assign consistent ordering to lists and use the same selection order throughout. By default, choose the lowest seat number.

The examples use a hypothetical deal: **seat 4 is Merlin; Evil occupies seats 3, 5, 8; the Good list is 1, 2, 4, 6, 7.** These roles are illustrative; in an actual game they remain secret.

## 1. Commit to an answer, then send sealed letters

Message exchange must support two functions:

- **Sealed letters:** publish encrypted messages that only the designated recipient can read, with authentication of the sending seat.
- **Commitment:** publish a commitment to one fixed list, then give authorized recipients the list and a private verification code. The public commitment does not reveal the list; the list and code allow verification and prevent later replacement with a different list.

Each seat publishes only one commitment, before sending its list.

| Role | What to commit to | Letters |
|---|---|---|
| Merlin | The true five-player Good list | Send Good players the list and verification code; send Evil padding. |
| Other Good players | “I have no list.” | Send padding to everyone. |
| Evil | May commit to a false list | Any list sent must still pass the later checks. |

In the example, seat 4 commits to 1, 2, 4, 6, 7 and posts the public commitment. Seat 4 then sends:

| Recipient | Contents |
|---|---|
| Seats 1, 2, 6, 7 | Good list 1, 2, 4, 6, 7 and private verification code |
| Seats 3, 5, 8 | Padding in the same format used by ordinary Good players |
| Seat 4 itself | Records its own list as received and participates in confirmation |

Other Good players also send letters to everyone. In each stage, each player sends one letter to each of the other seven seats. Put that stage's information in the letter; use padding when there is nothing to say. Pad all letters to equal length.

**Each letter contains only information its recipient is entitled to receive. Padding letters do not contain the verification code that opens the sender's commitment.**

## 2. Check each received list separately

First check that a received list:

1. Contains exactly five players.
2. Contains both the sender and the recipient.
3. Passes verification against the sender's public commitment using the code.

Discard it if any check fails.

Next, the five members of that list use sealed letters to confirm its sender. For example, after seat 1 verifies list 1, 2, 4, 6, 7, it sends only to those five members:

> For list 1, 2, 4, 6, 7: verification passed, and the sender I received it from is seat 4.

Other members reply in the same format. If the same list has multiple sources, each member chooses a source using the agreed seat order, then compares sources with the others. Retain the list only if all five confirm successful verification and the same source.

**This exchange concerns only that list's source. Even if seat 1 also received a different list from seat 3, it must not tell seat 3 that this list came from seat 4.**

Publicly, each member says only:

> I confirm retaining list 1, 2, 4, 6, 7.

The public reply excludes the sender, verification code, and corresponding commitment. Discard unconfirmed lists. At most four distinct lists remain.

## 3. Use the public lists to prepare backup teams

A “backup team” is the pool from which quest participants are selected. Prepare at most three pools, of sizes four, four, and five. Keep the current pool after a successful quest; switch to the next only after a failed quest.

### One to three retained lists

In the agreed list order, take the lowest four seats from each of the first two lists and all five seats from the third. Repeat the last list if fewer than three are available.

| Public list | Members | Backup pool |
|---|---|---|
| A | 1, 2, 4, 6, 7 | First: 1, 2, 4, 6 |
| B | 1, 2, 3, 5, 6 | Second: 1, 2, 3, 5 |
| C | 1, 3, 4, 5, 8 | Third: 1, 3, 4, 5, 8 |

Use the first pool until it fails, then the second until it fails, then the third.

### Four retained lists, with a pair sharing four members

Choose the first such pair in the agreed ordering. Use their four shared members as the first pool.

For example, lists 1, 2, 4, 6, 7 and 1, 2, 4, 6, 8 give the pool **1, 2, 4, 6**.

If that pool fails, eliminate both lists. The other two lists supply the remaining pools: four members from one, all five from the other.

### Four retained lists, with no pair sharing four members

Use the procedure below.

## 4. Four lists with no four-member pairwise intersection

Choose the lowest-numbered player appearing in at least three lists and call that player **A**.

### A appears in all four lists

A privately collects the four senders' seat numbers. Among the candidate lists, A selects the unique list containing exactly one of those four senders.

For example, if the senders are **3, 4, 5, 8**, A counts how many appear in each list. List 1, 2, 4, 6, 7 contains only seat 4, so it qualifies.

A publishes only the selected list. Future teams draw from it; the four senders remain private.

### A appears in exactly three lists

Call the only list excluding A **X**. Start with the lowest four seats in X. Keep using that pool after success. If it fails:

1. Eliminate X.
2. Ask X's five members to publicly report X's sender. Treat each nonresponse as its own distinct “unanswered” report.
3. **If at least four report the same sender F:** A combines F with the other three lists' senders and selects a list as in the previous case. Publish only that list and use it for future teams.
4. **If fewer than four agree:** group players who report the same sender. Combine whole groups into a two-player group and a three-player group, without splitting any group. If several partitions work, choose the earliest two-player combination in seat order.
5. Select remaining lists excluding every member of the two-player group, and those excluding every member of the three-player group. Their union contains at most two lists.
6. Use them for the remaining backup pools, one of four and one of five. If only one list remains, draw subsequent teams directly from it.

Example:

| List | Members |
|---|---|
| I | 1, 2, 4, 6, 7 |
| II | 1, 2, 3, 5, 6 |
| III | 1, 3, 4, 5, 8 |
| IV | 2, 3, 6, 7, 8 |

Seat 1 appears in I, II, III, so A is seat 1 and X is IV. The first pool is **2, 3, 6, 7**.

After that pool fails, eliminate IV and collect its members' source reports. Suppose:

| Reporters | Claimed sender of IV |
|---|---|
| 2, 6, 7 | Seat 8 |
| 3, 8 | Seat 5 |

The two-player group is **3, 8**, and the three-player group is **2, 6, 7**.

- Only I excludes both 3 and 8.
- Only III excludes all of 2, 6, and 7.

The remaining pools are therefore **1, 2, 4, 6** from I and **1, 3, 4, 5, 8** from III. Continue to keep a pool after success and change only after failure.

**Reveal a sender only for a list already eliminated by quest failure. Other lists' sources stay private.**

## 5. Who actually goes on each quest?

| Quest | Selection |
|---|---|
| First: three players | Lowest three seats in the current pool |
| Second and third: four players | Lowest four seats |
| Fourth: five players, two Fail cards needed | All five if the pool has five; otherwise add the lowest seat outside the four-player pool |
| Fifth: five players | If quests have not ended, use the third, full five-player pool |

For pool **1, 2, 4, 6**:

- Send 1, 2, 4 on a three-player quest.
- Send 1, 2, 4, 6 on a four-player quest.
- For quest four, add the lowest outside seat, 3: send 1, 2, 3, 4, 6.
- Change to the next pool only when a quest actually fails.

Even if seat 3 submits one Fail card, quest four succeeds: it needs two Fail cards to fail.

If a unique list has been selected, use the lowest required number of seats from it; send all five on five-player quests.

**All Good players approve only the team selected by these rules and propose only that team when leading. A successful quest does not prompt a public claim that the list is true; continue following the agreed procedure.**

Conditional result: if the message exchange, verification, and behavior conditions hold, Good completes three quests, and the Assassin can still do no better than guess uniformly among the five Good players, the idealized final Good win probability is 80%.
