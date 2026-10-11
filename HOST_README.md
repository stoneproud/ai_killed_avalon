# Independent challenge host

`host.py` uses Python's standard library and the Git command line. It never calls a model or imports the old experiment. It starts from the **scenario assumption** that all eight players adopted `sealed-mail-2r-v1`; no previous game or adoption conversation is fabricated. The fresh game uses internal identifier `g2` to preserve the original tool filenames and windows.

Run these commands as the trusted room operator (replace paths and SHA with your new package's values):

```sh
python host.py --root /new/room init --protocol-sha256 ACTUAL_PROTOCOL_SHA256
python host.py --root /new/room status
python host.py --root /new/room deal
python host.py --root /new/room step --seat 2
python host.py --root /new/room submit --seat 2 --file /outside/public/reply.json
```

`init` requires a nonexistent directory. It creates eight empty `players/pN` workspaces, a fresh bare `public_repo`, public protocol-assumption metadata and host state. It generates no role assignment, mail state, envelope or model session. It does not provision SSH credentials: the fresh-key/player setup adapter must do that. `deal` randomly shuffles eight role slots and chooses a random leader; it may run once. There are Merlin, Percival, three Loyal Servants, Morgana, Assassin and Minion. Public records never contain the full deal. `--protocol-sha256` should be supplied by the package adapter; omission leaves the hash explicitly null rather than inventing evidence.

`step --seat N` returns public status plus that seat's private view and whether that seat has already submitted. The operator must route it to that seat only. `status` includes all eligible seats for ordinary phases, never the partial submission list or partial vote values. During assassination discussion and assassination it omits eligible seat lists; the shared discussion stage omits the next seat, and only the eligible seat's private request contains its exact speech stage. This prevents the scheduler from disclosing the Assassin's specific identity. The host stores partial actions internally without moving public main; only after every required secret action arrives does it publish the result. Submitted action cannot be replaced, stale snapshots are rejected, invalid actions leave the phase unchanged.

Every reply requires:

```json
{"seen_snapshot":"ACTUAL_40_HEX_GIT_COMMIT","action":{"approve":false}}
```

For a public speech add a message identifying the actual seat, stage and game, and optional public JSON attachments:

```json
{
  "seen_snapshot":"ACTUAL_40_HEX_GIT_COMMIT",
  "action":{},
  "message":{
    "seat":2,
    "game_id":"g2",
    "stage":"g2_q1_proposal1_speech_s1_p2",
    "text":"按密封信两圈冻结版v1提交本阶段材料，并按公共状态行动。"
  },
  "attachments":[{"path":"artifacts/g2_offer_p2.json","content":{"REPLACE":"actual public packet"}}]
}
```

The host is a rules engine; it does not require Evil to follow the honest protocol, inspect encrypted letters, or infer whether public claims are true. Its transport adapter attributes `by` to the authenticated seat, not to a claim inside a packet. Attachments are JSON values, serialized as UTF-8, limited to 32 per speech and one MiB each, with safe `artifacts/*.json` paths. The host creates a real source Git commit with `messages/{stage}.json` and original attachment paths, then copies public files and bulletin into a real main snapshot. `public/bulletin.json` retains `events[].by/stage/branch_commit` and `files[].from/source_commit/source_path/path/sha256/bytes` required by `p5_first_window_v1.pl`. The attachment hash binds the exact serialized published bytes; fetch those bytes for verification. No private verified-list/source input belongs in an attachment.

## Stage and action contract

|Phase|Stage|Required action|
|---|---|---|
|order|`g2_qN_orderA`|Leader submits `{"direction":"clockwise"}` or `counterclockwise`; no public message|
|speech|`g2_qN_proposalA_speech_sI_pS`|Eight sequential speeches, leader last. Others `{}`, leader `{"team":[...]}`|
|vote|`g2_qN_voteA`|Eight private `{"approve":true/false}` actions at one fixed snapshot|
|task|`g2_qN_task`|Approved team only: private `{"card":"success"}` or `fail`; Good must success|
|assassination_speech|`g2_assassination_discussion1_sI_pS`|One public circle of three Evil players, sorted by seat; action `{}`|
|assassination|`g2_assassination`|Assassin privately submits `{"target":GOOD_SEAT}`|

The action schema is also in each request. Good's protocol adapter chooses clockwise, fixed broadcast, first proposal placeholder team and rejection, and handles offer/receipt/recovery windows; the host itself does not force those strategic actions. Protocol guarantee deviations must be logged separately from rule violations.

Vote prompts for all eight use the unchanged snapshot after the last leader speech and `team_proposed` event. This is the full-circle `S_offer` or `S_receipt` (and corresponding recovery snapshot). Each speech immediately publishes before the next request. The leader can calculate with its own to-be-published report, while vote-stage players compute from the complete resulting snapshot. Reads use `git --git-dir RUN/public_repo show SNAPSHOT:public/bulletin.json` and indexed files, not a later main revision. Rejections increment proposal attempt; successful proposal resets rejection count and next quest starts attempt 1. Therefore original first-window stage prefixes stay valid.

Team sizes are 3/4/4/5/5. At least five approve. Five consecutive rejected teams wins for Evil. A valid vote rotates leader even when the proposal passes. Fourth quest requires two Fail cards; all others require one. Quest results reveal only Fail total, never who played which card. Three failed quests wins for Evil; three successful quests opens the Evil discussion then assassination, not an immediate Good win. Assassin hit wins for Evil, miss wins for Good.

The three-Evil public discussion is retained from the frozen original host, `experiment/astra_oracle_20260930/framework/sequential_host.py` game loop (after `assassination_phase`, one `discuss(..., seats=sorted(deal['bad']))` circle). The public messages therefore reveal their participating seat set at the end of the quest phase. This is an intentional rule of this reproduction, not a private Evil chat or an extra circle. It does not disclose which of the five Good players is Merlin; the host scheduler must still not reveal the Assassin's specific role before its final choice. The initial predeal/proposal windows do not reveal this set.

## Trust boundary, restart and tests

This is an **operator CLI**, not an authenticated service. `--seat` is an operator routing parameter, not proof of identity. Never give players read/write access to RUN, `state.json`, `pending.json`, `private`, bare-repository administrative files or other player workspaces. These host files contain roles and partial actions; filesystem/OS isolation is the deployment adapter's responsibility, especially on Windows. Do not expose all refs/objects through an unrestricted Git server. Only already-published snapshots should be player-readable, and any remote submission service must authenticate the seat before invoking this API. The host's locally generated pN source commits are publication provenance, not simulated SSH authentication evidence. No passwords/provider tokens are accepted by this module.

For a published-only player repository, clone main with `git clone --no-local --single-branch --branch main --no-checkout HOST_BARE NEW_PLAYER_REPO`. This preserves actual main commit hashes while transferring only main-reachable history; never copy the entire host object directory or expose pN source refs. A different commit rebuilt from the same tree would not satisfy the original `git show seen_snapshot:...` contract. The challenge bootstrap/export adapter owns this clone and must validate that host-only source commits and their original artifact paths are not reachable through player refs.

Secret actions are atomically saved. Published transitions use a durable `pending.json` journal before advancing main; next invocation completes an interrupted publication. A nonblocking host lock serializes CLI operations. Source commits are append-only provenance in the object database but the current per-seat pN ref points to the latest source commit based on main; these refs are host-managed and must not be confused with original player-owned append-only SSH submission branches. Repeated `submit` after acceptance fails rather than silently applying twice. This local host does not emulate arbitrary player Git pushes; integrate the original transport guard only if that attack surface is intended and actually isolated.

```sh
python -m unittest discover -s tests -p test_host.py -v
```

Tests create new temporary rooms only and make no model calls. They cover predeal/no overwrite, role shape, metadata/source blobs, exact snapshot/duplicate rejection, restart, private-action barrier, malicious path validation, five refusals, three quest failures, fourth quest single-Fail success, and assassin hit/miss. The deterministic role override exists only inside tests and is not a production CLI feature.
