# Adapter end-to-end test evidence

Exact commands and timings from completed tool stdout in this chat; assertions from test source. Original raw stdout was not written to disk. No invented wall-clock timestamps.

## Executed checks

1. `LOCAL_PYTHON/python.exe -m unittest discover -s tests -p test_bot.py -v`

   Result: 2 tests, 312.352s, exit 0 / OK.

   Revision scope: Historical baseline before x_source/fail_quests extensions and the final own-report hardening. Executed file hashes were not captured.

   - Fresh initialize: eight new RSA-3072 keypairs; random Host.deal; seat-local Bot via published-only export for every action.
   - Completed three successes, zero failures, three Evil public discussion speeches and one assassination action.
   - All task cards success; all first-offer-circle votes reject; public speech matches fixed broadcast.
   - Original p3/p2 branch unit assertions cover A_in_four, A_in_three, consensus and fallback.

2. `LOCAL_PYTHON/python.exe -m unittest tests.test_bot_attacks.AttackAdapterTests.test_bad_three_report_four_A_choice_recovery -v`

   Result: 1 tests, 472.740s, exit 0 / OK.

   Revision scope: Attack adapter before final own-report helper hardening. Executed file hash was not captured.

   - New fixture truth [1,2,3,6,7]; Evil 4/5/8 offer [4,5,6,7,8], [1,2,3,4,5], [1,2,4,6,8].
   - Initial p3 branch A_in_three; X [4,5,6,7,8]; first quest team [4,5,6] has exactly one Fail from seat 4.
   - Eight quest-2 proposal-1 source reports: outsiders null, Good 6/7 source 4, Evil 4/5/8 source 4; eight votes reject.
   - Only A=1 publishes quest-2 proposal-2 x_choice [1,2,3,6,7]; choice has exactly seven formal fields.
   - p2 four_source_agreement team equals actual proposed team. Final three successes, one failure, exactly two rejected teams total.

3. `LOCAL_PYTHON/python.exe -m unittest tests.test_bot_attacks.AttackAdapterTests.test_bad_three_report_five_unsplit_recovery -v`

   Result: 1 tests, 553.962s, exit 0 / OK.

   Revision scope: Attack adapter before final own-report helper hardening. Executed file hash was not captured.

   - Same newly generated fixture roles and four actual cryptographic offers as consensus test.
   - Good X members 6/7 report source 4; Evil 4/5/8 report source 5. p2 chooses unsplit_partition and no x_choice is published.
   - Only seat 4 plays Fail in quests 1 and 2; first teams are [4,5,6] then [1,2,3,4].
   - After the recovery-range failure, quest 3 team becomes [1,2,3,6]; subsequent quests pass on the recovered true range.
   - Final three successes, two failures; all eight source-preparation votes reject; exactly two rejected teams total.

4. `LOCAL_PYTHON/python.exe -m unittest tests.test_bot_attacks.AttackAdapterTests.test_invalid_first_offer_cannot_be_replaced_in_receipt_circle tests.test_bot_attacks.AttackAdapterTests.test_real_mail_A_in_four_complete_game -v`

   Result: 2 tests, 354.702s, exit 0 / OK.

   Revision scope: Before final own-report hardening. This process imported the invalid test before missing-seat-8 coverage was added; that later version was independently tested below.

   - Invalid-first test: Evil 4 first offer includes a forbidden extra field, then republishes its valid original packet during receipt circle.
   - p5 fixed-first plus hash/schema chain ignores seat 4 at S_offer and at later snapshot; private verified inputs never include source 4; true first quest team [1,2,3] still passes.
   - A_in_four test uses new RSA mail: truth [1,2,3,4,5], Evil 6/7/8 false lists [1,2,3,6,7], [1,4,5,6,7], [1,2,4,6,8].
   - Every completed receipt vote computes A_in_four and sole range [1,2,3,4,5]; final three successes, zero failures; no recovery files appear.

5. `LOCAL_PYTHON/python.exe -m unittest tests.test_bot_attacks.AttackAdapterTests.test_invalid_first_offer_cannot_be_replaced_in_receipt_circle -v`

   Result: 1 tests, 131.045s, exit 0 / OK.

   Revision scope: Latest invalid/missing test before final own-report helper hardening.

   - Latest invalid-first test simultaneously removes Evil 8 first offer attachment.
   - Invalid seat-4 first packet cannot be rescued by later valid packet; missing seat-8 first packet is omitted from fixed S_offer reports.
   - All receipt packets have exactly v/game/phase/seat/lists/four_choice; private verified records exclude invalid source 4.
   - Host reaches approved task team [1,2,3].

6. `LOCAL_PYTHON/python.exe -m unittest tests.test_bot.BotTests.test_own_report_only_fills_unoccupied_current_leader_slot tests.test_bot.BotTests.test_attack_and_eligibility_boundaries tests.test_bot.BotTests.test_original_selection_and_both_recovery_branches -v`

   Result: 3 tests, 1.219s, exit 0 / OK.

   Revision scope: Final source hashes recorded in this report. No full E2E rerun after helper hardening, per parent instruction.

   - Final helper hardening: legitimate current leader receipt and x_choice accepted with real p5/p6 tools.
   - Nonleader, stale snapshot, wrong receipt quest/window, and occupied invalid first event reject own-report fill.
   - Good cannot enable Evil attack config; Good task remains success; already-submitted action rejects.
   - Original tools still calculate both initial A branches and both recovery branches.

## Final files and vendor

- `bot.py`: `ba537f8dc79823590b2cf48c162d260d4bf37cc4b55bf1dd5fb22082c9a82131`
- `tests/test_bot.py`: `05342511e43c37a9f4fb1ff8237fbb02449025e8fc86b59431810c6f193cf243`
- `tests/test_bot_attacks.py`: `069a437d0a04b3f288fab075111ac0e9518dc81e27dfd60b7ae791e670b3f893`
- `.gitignore`: `5486cb816b8c7afe6dd16408012753243cc6e188da83bfb7c0f048097f6a1c60`

Vendor verification: PASS; 13 original files checked with `challenge.verify_vendor()`. Manifest SHA-256: `6b518da82feb0d8311dc42c93ad2b6601655ef612c67e5bd43be345af24e5b3a`.

## Scope limits

- Full E2E runs preceded final own-report helper hardening; focused final-code tests cover legitimate receipt/choice calls and rejection boundaries. Historical executed source hashes were not captured.
- Rejection-budget E2E evidence is exactly two forced preparation rejections. No worst-case malicious-leader wrong-team schedule was tested; this report does not claim to prove that budget bound.
- All role overrides occur only inside tests and only on new temporary hosts. No original experiment, old keypair, model call, or production role override is used.
- Fixture tests retain failed new-room state and action transcripts under work/challenge21_test_failures; work/ is ignored by Git. Successful fixtures were temporary and removed.
- Assassination target remains uniformly selected among known Good seats. Tests assert completion rather than forcing an Assassin miss or claiming a sampled 80% win rate.
