# Engineering log 22_0710

## Tasks

1 exectute the plan in @REVIEW_EXECUTION.md  using agents

1.1 Census, read only (REVIEW_EXECUTION.md 12.1).
1.2 Rules sweep, read only (12.2).
1.3 Line contract, read only (12.3).
1.4 Twins, read only (12.4).
1.5 Rungs of `python/test_browser.py`, stages 0, 4, 6, 7, read only (12.5).
1.6 Rungs of `python/test_browser.py`, stage 5, read only (12.5).
1.7 Rungs of `python/test_browser.py`, stage 8, read only (12.5).
1.8 `ts/test_substrate.ts`, read only (12.6).
1.9 Python test infrastructure (11.1).
1.10 Rules tooling (11.2).
1.11 Windows administration scripts and third party code (11.3).
1.12 JSLB in both languages (11.4).
1.13 Python server core (11.5).
1.14 Python substrate (11.6).
1.15 Python engine handlers (11.7).
1.16 Python platform and the seeds (11.8).
1.17 Wire test (11.9).
1.18 Page build and DevTools (11.10).
1.19 Browser test's harness (11.11).
1.20 TypeScript test harness (11.12).
1.21 First TypeScript modules (11.13).
1.22 TypeScript dispatcher and task manager (11.14).
1.23 TypeScript wire and http lanes (11.15).
1.24 TypeScript substrate (11.16).
1.25 MCP and the providers in TypeScript (11.17).
1.26 Agent loop and scripts (11.18).
1.27 Browser tools (11.19).
1.28 AI worker and boot (11.20).
1.29 The page (11.21).
1.30 Media and the console view (11.22).
1.31 Verifier of tasks 1.9, 1.10, 1.11 (13.2.1).
1.32 Verifier of tasks 1.12, 1.13 (13.2.2).
1.33 Verifier of tasks 1.14, 1.15 (13.2.3).
1.34 Verifier of tasks 1.16, 1.17, 1.18 (13.2.4).
1.35 Verifier of task 1.19 (13.2.5).
1.36 Verifier of tasks 1.20 to 1.23 (13.2.6).
1.37 Verifier of tasks 1.24, 1.27 (13.2.7).
1.38 Verifier of tasks 1.25, 1.26 (13.2.8).
1.39 Verifier of tasks 1.28, 1.29, 1.30 (13.2.9).
1.40 Closing agent (14.1).
1.41 Formatter (14.2).

## Order of operations

1 Phase 0 (9.1): open this log with task number k = 1, since no task 1 existed before; record `git rev-parse --short HEAD` and `git status --short` as the baseline; make `tmp/review/` with `report/`, `i18n/`, and `inbox/<id>/`, `done/<id>/` per task and for `coordinator`; run the lock check of 15.2.
2 Phase 1 (9.2): launch tasks 1.1 to 1.30 as general purpose agents with the prompt of 15.3.1, in a rolling pool of at most eight, in the order 1.19, 1.24, 1.15, 1.12, 1.1 to 1.8, then 1.9, 1.10, 1.11, 1.13, 1.14, 1.16, 1.17, 1.18, 1.20 to 1.23, 1.25 to 1.30.
3 After every agent ends (15.2): lock check, listing of `tmp/review/inbox/*/`, `git status --short`, and a record here with the time and the reply in short.
4 Slot priority when the pool has room: the next Phase 1 task, then a Phase 2 drain (9.3) of an ended task whose inbox holds requests, then a verifier (8.8.1) whose first area has ended with an empty inbox; a verifier is resumed by SendMessage as each later area of its group ends with an empty inbox.
5 Phase 2 (9.3): resume ended agents by SendMessage with the text of 15.3.2, or a fresh agent under the same task id; at most three resumptions per task; repeat until every Phase 1 agent has ended and every inbox is empty.
6 Phase 3 (9.4): verifiers 1.31 to 1.39; a REJECTED fix goes to its owner as a request and is worked once as in 9.3.
7 Phase 4 (9.5): closing agent 1.40 after every writer and verifier has ended; one more round of 9.3 and 1.40 again if 14.1.6 calls for it.
8 Phase 5 (9.6): formatter 1.41 after 1.40.
9 Phase 6 (9.7, 15.4): the postmortem, here and in the conversation, with this log's link.

## Record

22_0711 Phase 0. Baseline `85b7075`. `git status --short` printed nothing: the tree is clean. Expected by 9.1.2 were `?? REVIEW_EXECUTION.md` and ` D` lines for removed top level `.md` files; neither shows because `REVIEW_EXECUTION.md` is tracked (`git ls-files` lists it) and HEAD `85b7075`, later than the `1545189` named in 1.7, is the commit "final review doc" from the session's start snapshot, so the file and the removals stand committed. Tracked top level `.md` files: `CLAUDE.md`, `LICENSE.md`, `README.md`, `REVIEW_EXECUTION.md`, `declawed.md`. Also present, ignored by `.gitignore` and never tracked: `xsjs_install.ps1.md`, `xsjs_start.ps1.md`, `xsjs_stop.ps1.md`; `build/` ignored. No other change. `tmp/` existed, empty, at the start.

22_0711 Phase 0. Made `tmp/review/report/`, `tmp/review/i18n/`, and `inbox/` and `done/` directories for tasks 1.1 to 1.41 and `coordinator` (42 each). Lock check printed nothing.

22_0712 Phase 1. Launched as general purpose agents with the prompt of 15.3.1, k = 1, baseline `85b7075`: tasks 1.19, 1.24, 1.15, 1.12, 1.1, 1.2, 1.3, 1.4. Pool full at eight. Queue: 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11, 1.13, 1.14, 1.16, 1.17, 1.18, 1.20, 1.21, 1.22, 1.23, 1.25, 1.26, 1.27, 1.28, 1.29, 1.30.

22_0722 Task 1.4 ended. Reply: 3 findings, M 2 `ts/substrate.ts` `json_canonical` writes numbers in (0, 1e-4) unlike Python's `repr` so forwarded `_files` hashes differ and `cache_fill` throws `substrate.fill_desync` (request 1.4_1 to 1.24); S 2 `version_find` rounds Document-Ref versions past 2^53, a public interface, proposed edit in report item 9.1; S 4 `ts/test_mcp.ts` has no test of the `_meta` permit mark surviving `tools/list` (request 1.4_2 to 1.25). Candidates 12.4.5.1 to 4 accepted, 12.4.5.7 holds but for stack lines; open 12.4.4.1 to 4 stand. Inbox empty, locks none. Departures from 7.2, read only: `sed -n`, `cat`, `head`, `sort`, one `git rev-parse --short HEAD`. Checks: locks shown are running agents' only (`ts/test_substrate.ts.T1.24`, `python/engine_system.py.T1.15`, reports of 1.1, 1.2, 1.12, 1.15, 1.24); inboxes 1.14: 1.24_1, 1.24: 1.4_1, 1.25: 1.4_2, 1.28: 1.24_2; `git status --short` shows unstaged changes only (` M`, ` D` from locks, `??` lock names), nothing staged. Launched task 1.5.

22_0724 Task 1.12 ended. Reply: 6 findings, all fixed: M 3 `_blob_named` in `python/jslb.py` narrowed a type by `isinstance` branch, now `cast`; M 3 test size constants' comments did not say their writer chose them and one test used a bare 5000; U 4 no vector for a non-object blob header or a non-integer `b`, added with both tests' `errors_expected` entries; U 4 no test of Python's refusal of a leading byte order mark, added; S 4 TypeScript test for a 5000 digit number (11.4.6.4) and Python test for the `RecursionError` path (11.4.6.5) added. Files changed: `python/jslb.py`, `python/test_jslb.py`, `python/vectors_make.py`, `ts/test_jslb.ts`; report and an empty fragment created. Requests none sent, none received; locks none. Open: 11.4.6.6's other half holds, a `sink_close` throwing in `ts/jslb.ts`'s decoder cleanup replaces the first error, a decided item (11.4.4.3) against the first failure rule, open by 5.3.5. Proposed edits to this plan in 11.4.4.26 and 11.4.6.4. Departures, read only: `sed -n`, `cat`, `awk`, `head`, `cut`, `tr`, `echo`, `git rev-parse`. Owed to testing: every suite of the area; whether 1,000,000 nested brackets raise `RecursionError` on Python 3.14.4. Checks: locks shown are running agents' only (1.24 `ts/substrate.ts`, 1.15 `python/test_engine_verbose.py`, 1.19 `python/test_browser.py`, reports of 1.1, 1.2, 1.15, 1.19, 1.24); inboxes unchanged (1.14: 1.24_1, 1.24: 1.4_1, 1.25: 1.4_2, 1.28: 1.24_2); nothing staged. Verifier 1.32 is ready (first area 1.12 ended, inbox empty) and waits for a slot behind the Phase 1 queue. Launched task 1.6.

22_0727 Task 1.3 ended. Reply: 14 findings, 12 U and 2 M, all severity 3; 18 items accepted. Header name form, 5 findings: `ts/tools_browser.ts` builds all 9 of its line types in short names (12.3.5.3); `ts/provider.ts` `post_make` builds `http.request` short; `ts/error_overlay.ts` builds `fault` short; `ConsolePort.names_full` in `ts/wire.ts` reads the debug setting itself (12.3.5.4); `ts/page.ts` has its own `names_full` and `DomPort` builds `ui.input` and `ui.control_key` short. Server: `python/bootstrap.py` writes its `error` line on an argument error before raw mode (12.3.5.5); `python/echo_loop.py` passes a line with `r` to the dispatcher instead of refusing it as an unknown reply. `worker.snapshot_reply` not named in 12.3.2.16 (12.3.5.8), record stale. 12.3.5.6 no longer holds. Nine proposed edits in report item 9: `API/ts/lines.d.ts` rows and comments, `queue.d.ts` `OwnerTable` comment, `dispatch.d.ts` handler comment (12.3.5.7), signature changes `tools_register(..., full)` and `chat_request` / `image_request(..., full?)`, plan edits 12.3.3.7 and 12.3.2.16. Files changed none. Requests pending: 1.3_1 to 1.23 (`ts/wire.ts`), 1.3_2 to 1.29 (`ts/page.ts`), 1.3_3 and 1.3_4 to 1.16 (`python/bootstrap.py`, `python/echo_loop.py`). Inbox empty, locks none. Departures, read only: `git rev-parse`, `sed -n`, `awk`, `cat`, `head`. Checks: locks shown are running agents' only (1.19 `python/test_browser.py`, reports of 1.1, 1.2, 1.6, 1.15, 1.19, 1.24, and 1.2's requests 1.2_1 to 1.2_13 under `.T1.2` in the inboxes of 1.10, 1.11, 1.13, 1.14, 1.15, 1.16, 1.18, 1.19); published requests: 1.14: 1.24_1, 1.16: 1.15_1, 1.3_3, 1.3_4, 1.23: 1.3_1, 1.25: 1.4_2, 1.28: 1.24_2, 1.29: 1.3_2; 1.4_1 has left 1.24's inbox; nothing staged. Launched task 1.7.

22_0727 Task 1.15 ended. Reply: 8 findings, all fixed: M 2 `system.restart` `_argv_make` removed only `--main-loop x`, so `--main-loop=x` or a short form made the restart fail on a repeated option, now every form; M 2 `tap.line` appended through a buffered file against the stub, now unbuffered and raising on a short write with new string `engine_tap.write_short`; M 3 removed the unreachable `option_unfinished` branch; renamed three word `_main_loop_path`, `_main_loop_write` and `test_unregistered` in nine test modules (now `test_called_early`); MCP error tests compare `i18n` text; test sizes carry the writer-chose comment; S 4 three SHA-256 hex literals in `python/test_engine_kv.py` now computed by `hashlib`. Not filed: nine `not_registered` checks kept (agent's judgement), fixed temp file name in `source.put` (11.7.6.7) breaks no rule. Files changed: `python/engine_system.py`, `python/engine_tap.py`, nine `python/test_engine_*.py`. Fragment `tmp/review/i18n/1.15.json` adds `engine_tap.write_short`, removes `engine_system.option_unfinished`; `test_write_short` cannot pass until 1.40 merges. Request 1.15_1 to 1.16 pending. Request 1.2_6 in its inbox still under 1.2's lock, not claimed; owed to Phase 2. Owed to testing: whether `bootstrap.py` accepts a start line ending in `--`. Locks none. Departures: read only `cat`, `sed -n`, `head`, `sort`, `uniq`, `awk`, `git rev-parse`; one `python3 -c` that parsed `API/mcp/tools.json` only, outside 7.2. Checks: locks shown are running agents' only (1.19 `python/test_browser.py`, reports of 1.1, 1.2, 1.6, 1.19, 1.24, 1.2's requests 1.2_1 to 1.2_18 under `.T1.2`); published requests unchanged; nothing staged. Launched task 1.8.

22_0728 Task 1.24 ended. Reply: 9 findings: M 2 4.1, 4.8, 4.9; M 3 4.2, 4.3, 4.4; S 2 4.7; S 3 4.5; U 4 4.6; twenty items accepted; candidates 11.16.6.7 and 11.16.6.8 do not hold. Fixed in `ts/substrate.ts`: 4.1 `forward_pending` refusal in `db_unload` and `db_load` removed, lines in flight finish afterwards; 4.3 constants moved into `constants` but `round_table` and `hash_start`; 4.4 type `Forward` renamed `ForwardedLine`; 4.7 `doc_put` counts the next version exactly past 2^53; 4.8 (request 1.4_1, applied) numbers below 1e-4 stored as Python's `repr` writes them. Fixed in `ts/test_substrate.ts`: 4.2 desync message compared as `i18n` text; `Recorded` renamed `RecordedOperation`; 4.6 ported `test_create_failed`, `test_ref_database`, `test_snapshots_apart`, `test_value_held`, stale `since` test split in three, document tests in `TestDocuments`; new `test_load_pending`, `test_version_wide`, `test_numbers_small`. Not fixed: 4.5 copied SHA-256 needs a public `HashStream` in `API/ts/utility.d.ts` (proposed edit 9.1); 4.9 `db_compact`'s `VACUUM` can renumber rowids in the browser's copy only, open question; 4.7 remainder `ref_split` past 2^53 needs a public type change (proposed edit 9.2, open 10.2). Requests pending: 1.24_1 to 1.14 (remove `substrate.forward_pending`), 1.24_2 to 1.28 Seam: pending (send `db_load`'s snapshot behind the database's waiting lines; until then a load overtaking waiting lines ends in a desync fault at the next write). Fragment `tmp/review/i18n/1.24.json` empty. Late request 1.2_23 owed to Phase 2. Locks none. Departures: read only `sed -n`, `awk`, `cat`, `git rev-parse`; wrote its fragment with `printf >` and appended the 1.4_1 resolution with `echo >>`, both under `tmp/review/`. Checks: locks shown are running agents' only (1.19 `python/test_browser.py`, reports of 1.1, 1.2, 1.6, 1.19); 1.2's requests 1.2_1 to 1.2_32 now published to 1.10, 1.11, 1.13, 1.14, 1.15, 1.16, 1.18, 1.19, 1.21 to 1.30; `done/1.24/1.4_1.md` resolved; nothing staged. Drains owed: 1.15 (1.2_6), 1.24 (1.2_23). Launched task 1.9.

22_0732 Task 1.2 ended. Reply: 35 findings. M 1 (5): comment check failures that stop `test_posix.py` once the banner question is answered: `API/python/tap_consumer.pyi` and 24 of the 25 `API/ts/*.d.ts` (86 multi line comments and `;` outside code spans), checked first in file order; one comment in `python/stall_loop.py`, five in `python/test_browser.py` (three `;`, two two line), one `;` in `ts/test_agent.ts`. U 1 (1): plan 4.9.6.4 leaves out these stops but the four `;` comments. M 2 (3): PowerShell errors swallowed or defaulted (12 hits); `python/test_browser.py` stub server swallowing handler errors and `rung_long` reporting a default 0.0 ms as a measurement; `ts/wire.ts` `close_take` skipping a missing close receiver. M 3 (26): names not two words, literal timers and sizes, constants outside `constants`, `typing` names out of order in `python/devtools.py`, non literal `i18n` names in `ts/test_i18n.ts`, unreachable `queue.step_empty` and `http.stack_missing` branches. Files changed none; 32 requests sent to 1.10, 1.11, 1.13 to 1.16, 1.18, 1.19, 1.21 to 1.30, pending. Proposed edits: stub comments under `API/`, plan 4.9.6.4. Open: whether `Test` counts as a word in test class names (Python and TypeScript differ); three names the plan states that break the two word rule; 12.2.4.1 to 12.2.4.7; the `xsjs_install.ps1` banner. Inbox empty, locks none. Departures, read only: `sed`, `head`, `awk`, `cut`, `sort`, `uniq`, `tr`, `paste`, `printf`, `git rev-parse`, and a helper script in its scratchpad. Checks: locks shown are running agents' only (1.19 `python/test_browser.py`, its report, its claimed requests 1.2_11 to 1.2_13 and 1.1_3; 1.6's report); inbox counts 1.10: 1, 1.11: 3, 1.13: 1, 1.14: 2, 1.15: 1, 1.16: 5, 1.17: 1, 1.18: 2, 1.19: 4, 1.20: 1, 1.21: 3, 1.22: 2, 1.23: 5, 1.24: 1, 1.25: 2, 1.26: 2, 1.27: 3, 1.28: 2, 1.29: 2, 1.30: 2; nothing staged. Launched task 1.10.

22_0732 Task 1.1 ended. Reply: 10 findings: U 3 4.1 to 4.3; S 3 4.4, 4.7; M 2 4.5, 4.6; M 3 4.8 to 4.10. The eight inventories otherwise hold: 1199 literal `i18n` calls with no missing entry or placeholder mismatch, 130 PowerShell names, the settings keys, the whitelist, both tsconfig lists, both test tables, every other stub difference on record, the 16 + 2 tools. Requests sent: 1.1_1 to 1.20 (`TAPTestRunner.failfast` and `null` diagnostics in `Tracker` differ from the stub); 1.1_2 to 1.11 (`srv_buf_size` a hard coded literal in `xsjs_util.ps1`); 1.1_3 to 1.19 (browser test roots inherit `verbose_level` from the checkout), claimed by 1.19; 1.1_4 to 1.17 (wire test roots inherit `provider.scripted` and `verbose_level`); 1.1_5 to 1.27 (withdrawn `sql_run` refusal sentence still in a test). Proposed edits: `API/README.md`, comments in `API/ts/dispatch.d.ts` and `API/ts/queue.d.ts`, `reply_make` in `API/python/dispatch.pyi`, `main` in `API/python/third_party_fetch.pyi`, plan 12.1.2.15 to exclude the test harness from the production tsconfig. Open: 12.1.4.1 and 12.1.4.2; `source_put {name}` against `{name, text}` (12.1.5.2); `pyproject.toml`, where 12.1.2.13 and 11.2.6.4 disagree on whether it is a source file. Files changed none, locks none, inbox empty. Departures, read only: `sed -n`, `awk`, `cat`, `head`, `xargs`, `basename`, `cut`, one `git rev-parse`; read `jslb.py.T1.12`, `substrate.ts.T1.24`, `test_browser.py.T1.19` under lock names as 8.4 allows. Checks: locks shown are running agents' only (1.19 `python/test_browser.py`, report and four claimed requests; 1.6's report); inbox counts as at 22_0732 above; nothing staged. Launched task 1.11.

22_0736 Task 1.19 ended. Reply: 11 findings fixed in `python/test_browser.py`: M 1 two two line comments that would stop `test_posix.py`; M 2 TAP line splits, stub errors swallowed, rung not named on non `CheckFailed` errors, closed port released early; U 2 roots took `debug`, `verbose_level` and `provider.scripted` from the checkout; S 2 stub server started in a smoke run, now on first need; M 3 `tap_check` counted failures, mutable Protocol attribute, constants after their classes, probe names not two words. Fragment `tmp/review/i18n/1.19.json` empty. Requests received 1.1_3, 1.2_11, 1.2_12, 1.2_13, all applied and in `done/1.19/`. Requests sent none; locks none, no stray locks. Unmet: a rung timer cannot fire inside a DevTools call, so a rung can overrun by one DevTools wait (60 s); fix needs a new public name in `devtools`, proposed edit 9.3; proposals 9.1 and 9.2 update plan 11.11.3.4 and 11.11.3.6. Risk for testing: the stub now ends the run on any handler error, so an unserved request such as `/favicon.ico` when "stage 5: stub reachable" opens `/text` would fail the run. Departures: read only `sed`, `awk`, `cat`, `head`, `tail`, `tr`, `cut`, `sort`, `uniq`, `echo`, `git rev-parse`, `for` loops; one redirection writing two scratch lists in its session scratchpad; command counts approximate. Checks: one lock, 1.6's report, a running agent's; inboxes: 1.10: 1.2_1; 1.11: 1.1_2, 1.2_2, 1.2_3; 1.13: 1.2_4; 1.14: 1.24_1, 1.2_5; 1.15: 1.2_6; 1.16: 1.15_1, 1.2_7, 1.2_8, 1.3_3, 1.3_4; 1.17: 1.1_4; 1.18: 1.2_9, 1.2_10; 1.20: 1.1_1; 1.21: 1.2_14 to 1.2_16; 1.22: 1.2_17, 1.2_18; 1.23: 1.2_19 to 1.2_22, 1.3_1; 1.24: 1.2_23; 1.25: 1.2_24, 1.4_2; 1.26: 1.2_25, 1.2_26; 1.27: 1.1_5, 1.2_27, 1.2_28; 1.28: 1.24_2, 1.2_29; 1.29: 1.2_30, 1.3_2; 1.30: 1.2_31, 1.2_32; nothing staged. Verifier 1.35 ready (1.19 ended, inbox empty), waits behind the Phase 1 queue. Launched task 1.13.

22_0740 Task 1.7 ended. Reply: 25 "stage 8:" rungs reviewed, 4 findings in `python/test_browser.py`: 4.1 M 2 `rung_still` "time without input" reads its before state as soon as the server has the last turn while debug log lines may still be in flight, so a correct page can fail (12.5.5.7.3 holds; request 1.7_1: take the before state once two reads a poll apart agree); 4.2 M 3 `rung_click` picks its point with a bare `// 3` (request 1.7_2: `_CLICK_DIVISOR = 3` with a writer-chose comment); 4.3 M 3 `rung_terminal` and `rung_overlay` print "and it stays shown" and "below the console" without checking them (request 1.7_3: drop the words); 4.4 U 3 root "compact": `rung_compact_auto` sets `provider.scripted` false and writes its own `provider.json`, a second rung using that file against the maintainer's "not used during testing" and the one approved rung (4.8.7.4), while 12.5.2.7.3.5 asks it to check the second chat request; not fixed, options and proposed plan edits (2.10.1, 12.5.2.7.3.3, 11.5.3.26) in its report. `rung_long` 0.0 ms already fixed by 1.19 (1.2_13); the click candidate holds up; rung name word counts open under 12.2.4.5. Requests 1.7_1 to 1.7_3 to 1.19, pending. Inbox empty, locks none. Departures: read only `sed -n`, `head`, `git rev-parse`, `cut`, `sort`, `tr`, `comm`; `sort` and `comm` wrote two lists to its scratchpad; requests sent before the report's definition of done.

22_0740 Task 1.6 ended. Reply: 5 findings in the "stage 5:" rungs, each a request to 1.19, pending: M 2 `rung_order` requires three replies in the stub's write order, which the browser does not guarantee (1.6_1); M 4 `rung_single` cannot catch its bug, as the stub never answers the timed out request while the rung watches (1.6_2); M 2 `rung_drain_poll` posts one 8 MiB echo while ttyd is stopped, which socket buffers may absorb, and its comment overstates the echoes posted (1.6_3); S 4 `rung_large` runs the 128 MiB echo's port on the page's main thread, not the AI worker (1.6_4); S 4 `rung_token` and `rung_opening` point the port at the stub server, not ttyd, the open timer fix needing a change in 1.18's `python/devtools.py` (1.6_5). All 51 stage 5 rungs present; every probe and `i18n` name exists; 12.5.5.4.9 and 12.5.5.1.2 no longer hold for stage 5; name word counts and the private read in the drain poll probe left open. Inbox empty, locks none. Departures: read only `git rev-parse`, `sed -n`, `head`, `tail`, `cat`, `tr`, `sort`, `comm`; two scratch files written and removed by redirection in its scratchpad.

22_0740 Checks after 1.7 and 1.6: locks shown are running agents' only (1.10 `python/test_posix.py`, reports of 1.9 and 1.10); inbox 1.19 now holds 1.5_1 to 1.5_7, 1.6_1 to 1.6_5, 1.7_1 to 1.7_3, so 1.19 owes a drain and verifier 1.35 is no longer ready; other inboxes as at 22_0736; nothing staged. Launched tasks 1.14 and 1.16.

22_0741 Task 1.5 ended. Reply: stage 0, 4, 6, 7 rungs of `python/test_browser.py` reviewed, 8 findings: M 2 `rung_pool` checks the server once though each database's drop travels its own queue; M 2 `rung_early` checks the console at the first prompt, so late text slips past; M 3 `rung_pool` never compares its error message; M 3 seven count and size constants lack the writer-chose comment; severity 4: no rung covers `<object data>` or an SVG `xlink:href` failing to load; no rung throws on the test page itself; `rung_desync` claims "Reload replaced metaverse" unchecked; `rung_bulk_reload` claims the refetch after unload and load unchecked. Not fixable without a run: `rung_pool`'s error text comes from sqlite3.wasm. Requests 1.5_1 to 1.5_7 to 1.19, pending. Inbox empty, locks none, files changed none. Departures: read only `sed -n`, `awk`, `cat`, `head`, `tail`, `cut`, `tr`, one `git rev-parse`; definition of done written after the requests (10.2.2). Checks: locks shown are running agents' only (reports of 1.9, 1.10); inbox counts 1.11: 3, 1.13: 1, 1.14: 2, 1.15: 1, 1.16: 5, 1.17: 1, 1.18: 2, 1.19: 15, 1.20: 1, 1.21: 3, 1.22: 2, 1.23: 5, 1.24: 3, 1.25: 2, 1.26: 2, 1.27: 3, 1.28: 2, 1.29: 2, 1.30: 2; 1.10's inbox now empty; nothing staged. Launched task 1.17.

22_0741 Task 1.9 ended. Reply: 5 findings, all fixed: M 3 `python/test_i18n.py` `TestLookup` error tests checked only the exception class, now the exact message; M 3 `python/i18n.py` `_STRINGS` stood after a function, now with the constants and filled at import by the module's last line; M 4 the loader's two `ValueError` paths had no test, `TestLoading` added; U 2 `python/test_all.py` smoke run's closing line added " of its 120 s", now `the <category> run took <s> s` (11.1.3.18); U 4 `main` read `sys.argv` itself, now takes its argument list (11.1.3.14). Files changed: `python/test_all.py`, `python/test_i18n.py`, `python/i18n.py`; empty fragment `tmp/review/i18n/1.9.json`. Requests none sent, none received; inbox empty, locks none. Accepted: 11.1.6.6 holds but matches 11.1.3.17 on an accepted assumption; `tap_consumer` stub departures covered by 11.1.4.3 and 4.8.1.2. Proposed plan edits to 11.1.4.3 and 11.1.3.24. Departures: read only `sed -n`, `head`, `awk`, `cat`, `sort`, `tr`, `git rev-parse`, a shell `for` loop. Checks: locks shown are running agents' only (1.11 `powershell/xsjs_util.ps1` and report, 1.10's report); inbox counts as at 22_0741 above; nothing staged. Verifier 1.31 ready (1.9 ended, inbox empty), waits behind the Phase 1 queue. Launched task 1.18.

22_0742 Task 1.8 ended. Reply: `ts/test_substrate.ts` read against `ts/substrate.ts` as 1.24 left it; no test that cannot pass. 3 findings: 4.1 U 4 two Python assertions without port or record (`test_turns_append`'s `json_valid(content)` CHECK refusal; `test_kill_between`'s `seq` 0 after the kill); 4.2 M 3 `constants.slot_count`, `piece_bytes`, `map_bytes` comments lack the writer-chose wording (3.5, 6.7); 4.3 U 4 `test_create_twice` expects `substrate.db_exists` / `substrate.db_absent` where Python expects `FileExistsError` and SQLite's error, code right, plan 12.6.3.2 silent, proposed plan edit (report 9.1). 12.6.5.1, .2, .4 no longer hold; 12.6.5.3 (digests) owed to testing; 12.6.5.5 survives as 4.2; all 51 `substrate.` names compared by `i18n` text. Requests 1.8_1 (4.1) and 1.8_2 (4.2) to 1.24, pending, Phase 2 work. Open: the rule that a test module imports only its module and the harness against this file's use of `jslb`, `utility`, `i18n`; 11.16.4.24 (forwarded `turn.append` never compacting) built, unconfirmed. Files changed none; inbox empty, locks none. Departures: read only `sed -n`, `awk`, `cut`, `paste`, `head`, a `while read` loop, `git rev-parse`. Checks: locks shown are running agents' only (1.11 `powershell/xsjs_util.ps1` and report, 1.10's report); inbox counts as at 22_0741; nothing staged. Launched task 1.20.

22_0743 Task 1.10 ended. Reply: 4 findings: 4.1 M 2 `synchronization_check` message said "the four modules" while five are exempt, now ends "outside _SYNCHRONIZATION_MODULES", test first `TestAuditMessage.test_token_refused`; 4.2 S 2 audit pattern passed `new  Promise` (two spaces) and refused member `x.await`, now `new\s+Promise` and passes `x.await` while refusing `...await`, three probes added; 4.3 M 3 four three word names renamed `regex_scan`, `string_scan`, `template_scan`, `shell_quoted` (request 1.2_1 applied, in done); 4.4 M 2 not fixed (6.12): the audit can misread a division after a generic's `>` as a regular expression, needing TypeScript's parser, not installed; no current `ts/*.ts` file has the form. Files changed: `python/test_posix.py`, `python/test_test_posix.py`. Requests sent none. Proposed plan edits: probe counts in 11.2.3.7 to eleven and seven; 11.2.3.19 gains the new test. Other candidates checked, none filed; every whitelist miss is a recorded exclusion. Open: 11.2.5.1 to 11.2.5.14, the banner question first as it stops every run; 4.7.1 missing byte order mark of three PowerShell files; 4.7.14 whitelist misses and `.md` lines; names `non_ascii_check` and `Comment` the plan names against the two word rule; unrecorded: `test_lint.ps1` installs PSScriptAnalyzer with `Install-Module`. Inbox empty, locks none. Departures: read only `cat`, `sed -n`, `awk`, `head`, `sort`, `uniq`, `cut`, `git rev-parse`. Checks: locks shown are running agents' only (1.11 `xsjs_install.ps1` and report); inbox counts unchanged; nothing staged. Launched task 1.21.

22_0747 Task 1.11 ended. Reply: 13 findings, 9 M (6 sev 2, 2 sev 3, 1 sev 4), 3 S sev 4, 1 U sev 4; 12 fixed. 4.13 not fixed: `xsjs_util_get_distribution` ignores `wsl --list` exit codes; telling a failure from "no distribution" or "none running" needs WSL's real exit codes, a measurement. Fixes: every `-ErrorAction SilentlyContinue` replaced by a loud form; the `Import-LocalizedData` retry, the log `catch`, the `UBR` default and the `wsl --update` warn-and-continue removed; `apt-get` exit codes checked; poll counts, wait and output width named constants; `xsjs_util_invoke_native` logs the expanded command before its exit line (11.3.3.7); start clears old copies in the root before copying; `test_powershell.ps1` header names `provider.json`; `test_pin_names` and `test_install_pinned` added. Files changed: `powershell/xsjs_util.ps1`, `xsjs_start.ps1`, `xsjs_install.ps1`, `xsjs_stop.ps1` and `xsjs_status.ps1` (outside held parts), `powershell/test_powershell.ps1`, `powershell/en-US/i18n.psd1`, `python/test_third_party_fetch.py`. Fragment `tmp/review/i18n/1.11.json` empty. Requests sent none. Received: 1.2_2 and 1.2_3 applied, but the part of 1.2_2 removing `if ($log_path_)` declined (`xsjs_status.ps1` writes no log by design); 1.1_2 (`srv_buf_size`) declined under 11.3.3.15, listed open. Proposed plan edits: the patch has 7 hunks not 8 (11.3.3.4); all eight PowerShell files start with a byte order mark at the baseline, so 3.15, 11.3.3.12 and 4.7.1 are wrong; `provider.json` added to 11.3.3.10. Inbox empty, locks none. Departures: `sed`, `cat`, `awk`, `sort`, `tr`, `cut`, `head`, `od`, `git rev-parse`; redirected output into the session scratchpad, two scratch files `used.txt` and `defined.txt` at its top level, possibly overwriting another agent's files of those names. Checks: locks shown are running agents' only (1.20 `ts/test_unittest.ts` and report, 1.13's report); inbox 1.16 now 6, 1.11 and 1.13 empty, others unchanged; nothing staged. Verifier 1.31's group (1.9, 1.10, 1.11) has all ended with empty inboxes; 1.31 waits behind the Phase 1 queue. Launched task 1.22.

22_0748 Task 1.13 ended. Reply: 4 findings: 4.1 M 2 `python/mcp_stdio.py` used the locale's encoding for stdin and stdout, so non ASCII input raised and output was not UTF-8 under a non UTF-8 locale (11.5.3.15), fixed: `stdio_serve` switches both streams to UTF-8, process tests start the child with ASCII forced, new `test_process_wide`; 4.2 M 3 four error tests in `python/test_mcp.py` checked only the code or a fragment, now the full `i18n` text; 4.4 M 3 four three word test names renamed `test_list_shape`, `test_list_permit`, `test_error_kept`, `test_data_absent` (request 1.2_4 applied, in done); 4.3 U 3 `python/bootstrap.py` gives `hello` a fixed id 1 instead of `dispatch.id_next` (seam 11.5.7.1), request 1.13_1 to 1.16, pending. Files changed: `python/mcp_stdio.py`, `python/test_mcp_stdio.py`, `python/test_mcp.py`; fragment empty, every name of its five prefixes defined, used and called with the right count in both languages. Open: test modules import more than their own module (`jslb`, `mcp`) as the stubs and 4.5.11 put those types in the API, three options in its report; wording fixes for 11.5.3.11 and 11.5.3.15 proposed. Inbox empty, locks none. Departures: read only `cat`, `sed -n`, `awk`, `head`, `sort`, `comm`, `git rev-parse`; two lists of `i18n` names written to the session scratchpad. Checks: locks shown are running agents' only (1.16 `python/bootstrap.py` and report, reports of 1.14 and 1.20); inbox 1.20 now empty, 1.28 now 3, others unchanged; nothing staged. Verifier 1.32's group (1.12, 1.13) has all ended with empty inboxes. Launched task 1.23.

22_0750 Task 1.20 ended. Reply: 3 findings, all fixed: 4.3 M 2 `ts/test_all.ts` took a thread as the UI when `self.name === ""` while `boot.boot_run` and `test_hook.engine_run` take it as the worker when `"ai"`, all three now test `"ai"`; 4.1 M 3 thirteen error checks in `ts/test_unittest.ts` checked only the class (3.5), now compare name and message through new helper `thrown_text`; 4.2 U 3 request 1.1_1: `ts/tap_producer.ts` `failfast` now private and `diagnostics` optional as the stub declares, `undefined` for `null`; two tests in `ts/test_tap_producer.ts` updated first, the request's "no test change" being wrong; TAP text unchanged. Files changed: `ts/test_all.ts`, `ts/test_unittest.ts`, `ts/test_tap_producer.ts`, `ts/tap_producer.ts`; empty fragment `tmp/review/i18n/1.20.json`. Requests: 1.1_1 applied, in done; 1.20_1 to 1.28, pending, asks `boot_run` keep its `"ai"` test, no change to `ts/boot.ts`. Proposed plan edit 11.12.3.13 to the `"ai"` test. Locks none, no stray locks, inbox empty. Departures: read only `sed -n`, `cat`, `head`, `tail`, `od`, `tr`, `echo`, `git rev-parse`. Checks: locks shown are running agents' only (1.21 `ts/test_verbose.ts`, report and claimed 1.2_14 to 1.2_16; reports of 1.14, 1.16, 1.18); inboxes 1.14 now empty, 1.21: 4, 1.24: 4, 1.28: 4, others unchanged; nothing staged. Launched task 1.25.

22_0751 Task 1.14 ended. Reply: 5 findings: M 3 `python/substrate.py` unreachable `substrate.transaction_none` branch, now a `cast`, fixed; M 3 `python/test_substrate.py` hard coded desync message now built with `i18n`, fixed; M 3 `_MAP_BYTES` comment now says its writer chose it, fixed; S 3 the replay test no longer sets `seq` to 1 and 5 directly but reaches them by six counted writes, fixed; S 4 not fixed: `db_restore` brings no cache files with an image, a maintainer's choice with three designs in its item 10. Inbox: 1.24_1 and 1.2_5 applied, in `done/1.14`. Files changed: `python/substrate.py`, `python/test_substrate.py`; fragment `tmp/review/i18n/1.14.json` removes `substrate.forward_pending` and `substrate.transaction_none`. Request 1.14_1 to 1.24, pending (TypeScript replay test to build its start state the same way). Open: `_cache_prune` skip (11.6.5.1); `python/test_substrate.py` importing `jslb` against the one-module import rule; the restore cache file design; 4.7.5 and 4.7.6. Locks none, no stray locks. Departures: read only `sed -n`, `cat`, `head`, `awk`, `tr`, `sort`, `cut`, one `git rev-parse`; one `git show` of the baseline file, forbidden by 7.3, output to `/dev/null` and not read; one redirect wrote a scratch file in the scratchpad. Checks: locks shown are running agents' only (1.21 `ts/test_overlay.ts`, report and claimed requests; 1.16 `python/test_stall_loop.py` and `python/test_echo_loop.py` at once, two source locks against 8.2's one at a time, and report; 1.18 `python/test_devtools.py` and report); inboxes 1.14 empty, others unchanged; nothing staged. Verifier 1.33's group: 1.14 ended with empty inbox, 1.15 owes a drain. Launched task 1.26.

22_0754 Task 1.16 ended. Reply: 9 findings: M 1 one, M 2 one, M 3 four, M 4 two, U 3 one (proposed edit, no code change); 8 fixed. 4.1 the `;` comment in `python/stall_loop.py` would stop `test_posix.py`; request 1.2_7's suggested text would also be refused for a bare `_`, so the names went in backticks. 4.2 `seed/prompt.json` no longer tells the AI that `engine.store` matches the database tools for `db_stats` and `db_load`. 4.3 `python/bootstrap.py` sets raw mode before writing a refused command line's error line; a parsed console run stays cooked. 4.4 `python/echo_loop.py` refuses a line carrying `r` before dispatch. Files changed: `python/bootstrap.py`, `python/test_bootstrap.py`, `python/main_loop.py`, `python/echo_loop.py`, `python/stall_loop.py`, `seed/prompt.json`; created `python/test_echo_loop.py`, `python/test_stall_loop.py`; fragment `tmp/review/i18n/1.16.json` adds `echo_loop.reply_unknown`, `stall_loop.run_reached`. Request 1.16_1 to 1.9 (add the two new modules to `_MODULES` as smoke suites), pending; 1.9 has ended, so 1.9 owes a drain. Received six: five applied, 1.13_1 declined (`dispatch.id_next` for `hello` breaks bootstrap's decided import set 11.8.3.14 and fixed id 1, 11.8.3.10), left open. Locks none, no stray locks. Departures: `sed`, `cat`, `awk` to read, one `git rev-parse`, one `python3 -I -c` reading `API/mcp/tools.json` for tool names, outside 7.2. Checks: locks shown are running agents' only (reports of 1.18, 1.21, 1.22; 1.22's claimed 1.2_17, 1.2_18); inboxes: 1.9: 1.16_1; 1.15: 1.2_6; 1.17: 1.1_4; 1.19: 1.5_1 to 1.5_7, 1.6_1 to 1.6_5, 1.7_1 to 1.7_3; 1.23: 1.2_19 to 1.2_22, 1.3_1; 1.24: 1.14_1, 1.2_23, 1.8_1, 1.8_2; 1.25: 1.2_24, 1.4_2; 1.26: 1.2_25, 1.2_26; 1.27: 1.1_5, 1.2_27, 1.2_28; 1.28: 1.20_1, 1.21_1, 1.22_1, 1.24_2, 1.2_29; 1.29: 1.2_30, 1.3_2; 1.30: 1.2_31, 1.2_32; nothing staged. Drains owed: 1.9, 1.15, 1.19, 1.24. Verifier 1.31's group no longer ready (1.9's inbox not empty). Launched task 1.27.

22_0755 Task 1.21 ended. Reply: 8 findings: 4.1 M 2 fixed: in the worker, `ts/error_overlay.ts`'s `error` handler now cancels the event, so the page's `onerror` cannot win the race and show file, line, column with no stack; 4.2 M 2 fixed (request 1.18_1): `overlay_install()` runs at module load, so a throw later in the bundle or while xterm.js loads shows the fault screen, not a blank page; the calls in `ts/boot.ts` and `ts/page.ts` stay and do nothing; 4.3 U 2 a debug `settings_put` on the UI changes only the UI's copy, the AI worker keeps the old value, request 1.21_1 to 1.28 (`ts/worker_ai.ts`), pending; 4.4 to 4.8 M 3 fixed: error tests compare messages; `Leaf`, `Entry` renamed `SettingLeaf`, `OverlayEntry` (1.2_14); three constants into `constants` in `ts/utility.ts` (1.2_15); `ts/test_i18n.ts` calls `i18n` with literal names (1.2_16); test ring sizes and put values named constants. Files changed: `ts/error_overlay.ts`, `ts/utility.ts`, `ts/settings.ts`, `ts/overlay.ts`, `ts/test_i18n.ts`, `ts/test_verbose.ts`, `ts/test_overlay.ts`, `ts/test_settings.ts`; fragment `tmp/review/i18n/1.21.json` empty. Received 1.2_14, 1.2_15, 1.2_16, 1.18_1, all applied, in done. Open: the two of 11.13.5; what a test compares for a platform `TypeError` with no `i18n` text; counting words in test class names. Locks none. Departures: `sed -n`, `awk`, `cat`, `tail` to read; `cp` of one file to the scratchpad; appended resolution lines to claimed requests with `echo >>`. Checks: locks shown are running agents' only (1.22 `ts/test_queue.ts`, report and claimed 1.2_17, 1.2_18; 1.18's report); inbox 1.21 empty, 1.28: 5, others unchanged; nothing staged. Launched task 1.28.

22_0756 Task 1.18 ended. Reply: 10 findings: M 2 x3, M 3 x5, S 4 x1 fixed; U 3 x1 proposed. M 2: the error overlay's handlers were installed only by the page's last script, so a UI throw while the bundle or xterm.js loaded left a blank page, request 1.18_1 to 1.21 applied (`overlay_install()` at load); `python/devtools.py` browser stop script swallowed every `Stop-Process` error, now loud but for a helper already exited with the browser (that error category recalled from memory, owed to testing); `python/page_build.py` ran tsc with no limit, now `_TSC_SECONDS = 120.0`. M 3: `from typing` name order (1.2_9) and the relay's 64 KiB buffer as a named constant (1.2_10) applied; C# `Run`, `Copy` renamed `RelayRun`, `StreamCopy`; twenty one error tests in both test files now compare the message. S 4: `page_open` timeout message repeats `net::ERR_CONNECTION_REFUSED`. U 3: proposed correction to 11.10.3.14, two subprocess waits use the subprocess timeout, not a `WaitTimer`. Files changed: `python/devtools.py`, `python/test_devtools.py`, `python/page_build.py`, `python/test_page_build.py`; fragment empty. Received 1.2_9, 1.2_10 applied, in done. Locks none, no stray locks. Open: `test_template_hooked` still fails, the maintainer's choice a) to c) under 11.10.5.1. Departures: `cat`, `sed -n`, `head`, `cut`, `tr`, `tail` to read, one `git rev-parse`; a scratch listing in the session scratchpad; one `git show 85b7075:python/test_devtools.py`, forbidden by 7.3, output only the lines of its own edit. Checks: locks shown are running agents' only (1.17 `python/test_wire.py`, report and claimed 1.1_4; 1.22's report); inbox counts 1.9: 1, 1.15: 1, 1.17: 1, 1.19: 15, 1.23: 5, 1.24: 4, 1.25: 2, 1.26: 2, 1.27: 3, 1.28: 5, 1.29: 2, 1.30: 2; nothing staged. Launched task 1.29.

22_0757 Task 1.22 ended. Reply: 5 findings: M 3 x3 fixed, U 2 x1 requested, U 4 x1 fixed. `ts/queue.ts`: `step_take`'s unreachable `queue.step_empty` branch replaced by a cast (1.2_18); `Owed` renamed `OwedRequest` (1.2_17). `ts/test_queue.ts`: `Bench` renamed `QueueBench` (1.2_17); `test_header_kinds` added for `queue.type_invalid` and `queue.field_invalid`. Request 1.22_1 to 1.28, pending: `queue_synchronous` is meant for debug mode only but nothing checks it; asks a throw in `thread_open` in `ts/worker_ai.ts`, naming `settings_check` in `python/settings.py` (1.13) as the alternative place. Received 1.2_17, 1.2_18 applied, in done. Fragment `tmp/review/i18n/1.22.json` removes `queue.step_empty`. Proposed stub text for `API/ts/queue.d.ts`: the optional owner on `task_submit` / `line_notify`, `sink_attach`, `VerboseBatch`. 11.14.6.1 decided by 11.14.4.4 and 12.4.3.7; 11.14.6.4 and 11.14.6.5 do not hold. Locks none. Departures: read only `sed -n`, `awk`, `cat`, `head`, `sort`, `git rev-parse`, `git ls-files`; one `printf` to `/dev/null`; one redirect into its scratchpad. Checks: locks shown are running agents' only (1.17 `python/test_wire.py`, report and claimed 1.1_4); inbox 1.22 empty, others unchanged; nothing staged. Launched task 1.30, the last of Phase 1's queue.

22_1212 Lost agents (8.9). After 22_0757 every running agent, tasks 1.17, 1.23, 1.25, 1.26, 1.27, 1.28, 1.29, 1.30, stopped with HTTP 429, "You've hit your session limit · resets 12pm (America/Los_Angeles)"; each stop is confirmed by its notification. Locks held, which stay their tasks': 1.17 report `tmp/review/report/1.17.md.T1.17` and claimed `1.1_4`, no source lock (its `python/test_wire.py` lock of 22_0757 was released before the stop); 1.23 `ts/test_http.ts` (shown ` D ts/test_http.ts`, `?? ts/test_http.ts.T1.23`), report, claimed 1.2_19 to 1.2_22 and 1.3_1; 1.25 `ts/test_mcp.ts` (shown ` D ts/test_mcp.ts`, `?? ts/test_mcp.ts.T1.25`), report, claimed 1.2_24 and 1.4_2; 1.26 to 1.30 none. Inboxes unclaimed: 1.26: 1.2_25, 1.2_26; 1.27: 1.1_5, 1.2_27, 1.2_28; 1.28: 1.20_1, 1.21_1, 1.22_1, 1.24_2, 1.2_29; 1.29: 1.2_30, 1.3_2; 1.30: 1.2_31, 1.2_32; drains owed unchanged (1.9: 1.16_1; 1.15: 1.2_6; 1.19: 15; 1.24: 4). Nothing staged; untracked beside the locks: `python/test_echo_loop.py`, `python/test_stall_loop.py` (1.16). The limit is a session total, not a rate, so a smaller pool would not lower the work; the pool stays at eight (9.2). The limit has reset; the eight are resumed by SendMessage, each told its locks and to check each half made change against `git diff 85b7075 -- F` and its report before going on. Pool full at eight with the resumed agents; drains of 1.19, 1.24, 1.15, 1.9 and verifier 1.32 wait for slots.

22_1214 Task 1.17 ended, after its resumption. Reply: 3 findings in `python/test_wire.py`, all fixed: S 2 candidate 11.9.6.1, the "echo blob_max" rung held 2 GiB several times over in the client (request, joined copy, every frame built up front, echo); frames are now built as sent, nothing joined, and any blob over 128 MiB is streamed to a file and checked by its sha256; M 2 request 1.1_4, wire roots inherited `provider.scripted` and `verbose_level` from the checkout's settings, now set to true and 1 as 1.19 set the browser roots; M 3 `_PUT_COUNT`, `_TAIL_COUNT`, `_COLUMNS`, `_ROWS` gain the writer-chose comment. 21 accepted items; 4 open questions already listed (11.9.5.1, 11.9.5.2, the word count after `rung_`, the `from i18n import i18n` gap in the project rules). Requests: 1.1_4 applied, in done; 1.17_1 sent to 1.19 (same comment for `_PROBE_COLUMNS`, `_PROBE_ROWS`), pending. Fragment `tmp/review/i18n/1.17.json` empty. Proposed plan edits to 11.9.3.4 and 11.9.3.5. Resume check: its edits stood complete and unlocked and matched `git diff 85b7075`. Locks none, inbox empty. Departures: `cat`, `sed -n`, `awk`, `cut`, a `python3 -c` reading `tools.json`, `git rev-parse`; one `git show 85b7075:python/test_wire.py`, forbidden by 7.3, output discarded unread. Owed to testing: whether "echo blob_max" fits its 120 s timer now that it also hashes 2 GiB, and 2 GiB more disk under `build/` while it runs. Checks: locks shown are running agents' only (reports of 1.23, 1.25, 1.27; 1.23 and 1.25 have released their source locks and claimed requests); inboxes 1.23, 1.25 now empty, 1.19 now 16 with 1.17_1, others as at 22_1212; nothing staged. Verifier 1.34's group (1.16, 1.17, 1.18) has all ended with empty inboxes, ready. Slot freed: Phase 2 drain of 1.19 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3).

22_1215 Task 1.23 ended, after its resumption. Reply: resume check found its `ts/test_http.ts` edits complete, kept. 13 findings (M 1 x1, M 2 x4, M 3 x6, U 3 x2, S 2 x1), 12 fixed: `test_json_refused` could never pass as `json_text` accepts 2^54; thirteen `ts/test_http.ts` tests checked only `Error`, now the exact `i18n` text; `console.read` refuses a timeout longer than a timer holds instead of answering "timed out" at once; a second `wire_open` throws `wire.open_twice`; a cache file longer than its blob's size is caught; in `ts/http.ts` only a failed fetch or body read becomes a `fetch_failed` error line; tty 1's first message carries only the token, the 80 by 24 size copied from the old page gone (that ttyd 1.7.7 accepts this is from memory, owed to testing). Not fixed: 4.5 `ConsolePort` reads `debug` itself instead of being given the worker's `names_full()`, needing a public constructor change, proposed in item 9.1, maintainer's item 10.1. Files changed: `ts/wire.ts`, `ts/test_wire.ts`, `ts/http.ts`, `ts/test_http.ts`; fragment `tmp/review/i18n/1.23.json` rewords `wire.read_seconds`, removes `http.stack_missing`. Requests sent none. Received five: 1.2_20, 1.2_22 applied; 1.2_19 applied to the console port only, declined for the wire port (no close receiver is set there, so it would replace the `wire.close_silent` fault); 1.2_21 declined, the size constants removed; 1.3_1 declined, it needs a default name form the rules ban. Locks none, inbox empty. Departures: `cat`, `sed -n`, `awk`, `tail` to read; one `python3 -I -c` reading `tools.json`, failed, `grep` used instead; one `git show 85b7075:ts/test_http.ts`, forbidden by 7.3. Checks: locks shown are running agents' only (1.19 claimed its 16 requests; 1.26 `ts/test_agent.ts`, report, claimed 1.2_25, 1.2_26; 1.27 `ts/test_tools_browser.ts`, report, claimed 1.1_5, 1.2_27, 1.2_28; 1.25's report); inbox 1.27 gains 1.26_1 from 1.26, others as at 22_1214; nothing staged. Verifier 1.36's group (1.20, 1.21, 1.22, 1.23) has all ended with empty inboxes, ready. Slot freed: Phase 2 drain of 1.24 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3).

22_1215 Task 1.25 ended, after its resumption. Reply: resume check found the held `ts/test_mcp.ts` identical to the baseline, no half made change. 6 findings (U 2 x1, M 3 x2, S 4 x3), 5 fixed: U 2 the scripted provider lacked the fourth fault of 11.17.3.17, tool results whose `tool_call_id`s do not match the last reply's calls, fixed test first (`test_results_unmatched`); M 3 one word types `Fields`, `Bench` now `FieldTable`, `ScriptBench` in all six files (1.2_24); M 3 `crc_table` and `adler_modulus` stood outside `constants`, each now a local of the function that reads it; S 4 `test_list_permit` added to `ts/test_mcp.ts`, `_meta` survives `tools/list` (1.4_2); S 4 `test_dotted_names` now proves `tools_convert` drops `_meta`; not fixed: S 4 nothing tests `key_get` with no key set, the test needing a new export `key_clear`, an API change (6.2), proposed edit 9.1. Files changed: `ts/mcp.ts`, `ts/provider.ts`, `ts/provider_script.ts`, `ts/test_mcp.ts`, `ts/test_provider.ts`, `ts/test_provider_script.ts`; fragment `tmp/review/i18n/1.25.json` adds `provider_script.results_unmatched`. Requests sent none; 1.2_24, 1.4_2 applied, in done. Open 10.1: whether every class field needs its own one line comment. Locks none, inbox empty. Departures: `cat`, `sed -n`, `awk`, `head`, `git rev-parse`, two read only `python3 -I -c` (tools.json keys, line widths); one `git show 85b7075:ts/test_mcp.ts` on resume, forbidden by 7.3. Checks: locks shown are running agents' only (1.19 claimed 16; 1.26, 1.27 as at 22_1215 above); inboxes unchanged; nothing staged. Verifier 1.38's group: 1.25 ended with an empty inbox, so 1.38 may launch (8.8.1). Launchable verifiers by 8.8.1, a first area ended with an empty inbox: 1.31 (1.10, 1.11), 1.32, 1.33 (1.14), 1.34, 1.36, 1.38 (1.25). Slot freed: Phase 2 drain of 1.15 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3).

22_1216 Task 1.15 ended its Phase 2. Reply: request 1.2_6 (rename three word names `_main_loop_path`, `_main_loop_write` and nine `test_unregistered` methods) resolved applied, Phase 1 having already renamed them `_loop_path`, `_loop_write`, `test_called_early`, `grep` showing no old name left; in `done/1.15`. Its request 1.15_1 to 1.16 was resolved applied by 1.16 with no change to `python/bootstrap.py`; owed to testing, in both reports: argparse takes a start line ending in `--`, and a restart from such a line would still fail. No source file changed; items 5 to 7 and 12 updated, report published. Counts unchanged: M 2: 2, M 3: 5, S 4: 1. Locks none, inbox empty. Departures none new (`ls`, `grep`, `find`, `mv`, `test`, Edit). Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and 16 claimed; 1.24 `ts/test_substrate.ts` and 4 claimed; 1.29 `ts/test_page.ts`, report, claimed 1.2_30, 1.3_2; reports of 1.26, 1.27); inboxes 1.15, 1.26, 1.27 now empty, others unchanged; nothing staged. Verifier 1.33's group (1.14, 1.15) has all ended with empty inboxes. Slot freed: Phase 2 drain of 1.9 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3).

22_1217 Task 1.9 ended its Phase 2. Reply: request 1.16_1 applied: `("test_echo_loop", "smoke-test")` and `("test_stall_loop", "smoke-test")` added to `_MODULES` in `python/test_all.py` after `test_bootstrap`; checked by reading that both files exist, that their modules depend only on `dispatch`, `jslb`, `settings`, `i18n`, `signal`, all earlier in the table, that neither sets `SIGALRM`, and that the whitelist's `python/*.py` covers both; in `done/1.9`. Files changed in Phase 2: `python/test_all.py`. Totals unchanged: 5 findings, all fixed. Report items 5, 7, 12 updated, published. Locks none, inbox empty, no new departures. Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and 16 claimed; 1.30 report and claimed 1.2_31, 1.2_32; reports of 1.26, 1.27, 1.29); inboxes 1.9, 1.24, 1.29 now empty; 1.24's locks released, it still runs; nothing staged. Every Phase 2 drain owed at 22_1212 has been sent. Verifier 1.31's group (1.9, 1.10, 1.11) has all ended with empty inboxes. Phase 3: launched task 1.31 with the prompt of 15.3.1, entry "13.1 and 13.2.1", Phase 3.

22_1217 Task 1.24 ended its Phase 2. Reply: four requests applied, only `ts/test_substrate.ts` changed: 1.14_1 the replay test's start state (`hello_make`) built by ordinary writes as the Python twin's, asserting `_files` at seq 1 and `metaverse` at seq 5, unused `root` parameter gone; 1.2_23 five local functions renamed `cache_present`, `statement_run`, `values_held`, `schema_stop`, `kill_stop` (`Recorded` renamed and `stale` gone in Phase 1); 1.8_1 two Python assertions ported, `test_turns_append` checks `sql_run` refusing non-JSON `_turn` content leaves seq at 2, `test_kill_between` checks seq 0 after the kill (whether sqlite3.wasm's message holds SQLite's exact "CHECK constraint failed" owed to testing); 1.8_2 `slot_count`, `piece_bytes`, `map_bytes` comments gain the writer-chose wording. Report items 5 to 7 and 12 updated, republished: 1.24_1 applied by 1.14 (`substrate.forward_pending` removed); 1.24_2 still in 1.28's inbox; until it lands a `db_load` whose snapshot overtakes the database's waiting lines opens a copy behind the server, and the next write fails loud with a desync and a reload, the server keeping every line. Locks none, inbox empty. Departure: resolution lines appended with `echo >>` under `tmp/review/`. Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and 16 claimed; 1.28 report and claimed 1.20_1, 1.21_1, 1.22_1, 1.24_2, 1.2_29; reports of 1.27, 1.29, 1.30; 1.26's report released, 1.26 still runs); inboxes 1.24, 1.30 now empty; nothing staged. Verifier 1.37's group: 1.24 ended with an empty inbox, so 1.37 may launch (8.8.1). Launched task 1.32 with the prompt of 15.3.1, entry "13.1 and 13.2.2", Phase 3.

22_1217 Task 1.26 ended, after its resumption. Reply: resume check found its four files without diff against 85b7075 and no `*.T1.26` lock, nothing to complete or revert. 6 findings (M 1 x1, M 2 x2, M 3 x3), all fixed: M 1 a comment in `ts/test_agent.ts` held a `;` the comment check refuses (1.2_25); M 2 a script returning NaN, an infinity or a BigInt made the tool throw and the turn fault where the run should return the exception, the value now checked inside the run; M 2 `prompt_text` refused a universe prompt document of any type but `prompt`, so every later turn threw, a refusal no requirement asked for, removed, a non string `text` still throws; M 3 one word `Fields`, `Bench` and three local `tools` renamed (1.2_26), the bare soft limit `0` and `slot_count` now constants with the writer-chose comment. Files changed: `ts/agent.ts`, `ts/test_agent.ts`, `ts/script.ts`, `ts/test_script.ts`; new tests `test_value_uncarried`, `test_prompt_typed`; fragment `tmp/review/i18n/1.26.json` rewords `agent.prompt_invalid`. Requests: 1.26_1 to 1.27 (the notice 11.18.7.2 asks for), applied by 1.27; 1.2_25, 1.2_26 applied. Open, maintainer's: `agent.universe_ambiguous` (two `universe` rows can share the current world); whether test modules may use the real modules below them rather than doubles; whether `Test` counts as a word in test class names. Locks none, inbox empty. Departures from 7.2: read with `sed -n`, `cat`, `head`, `tail`, `awk`, `cut`, `tr`, `echo`; resolution lines appended with `printf >>` under `tmp/review/`. Checks: locks shown are running agents' only (as at the entry above); inboxes unchanged; nothing staged. Verifier 1.38's group (1.25, 1.26) has all ended with empty inboxes. Launched task 1.33 with the prompt of 15.3.1, entry "13.1 and 13.2.3", Phase 3.

22_1218 Task 1.27 ended, after its resumption. Reply: no edit begun before the stop, nothing to finish or revert. 6 findings, 4 fixed, 2 not fixable without changing `API/` (6.2): M 2 fixed, `console_run` ran outside debug mode, now throws `tools_browser.debug_off` before asking permission, as the server gates its debug tools, test `test_debug_off` first; M 2 proposed (9.1), with tty 0 not open `console_run` faults with `wire.socket_missing` where the plan says the AI opens the console with permission, the fix needing a new `console.show` line and edits to `API/ts/lines.d.ts` and `API/ts/console_view.d.ts`, design in 9.1 with a maintainer's choice (show the console view or open tty 0 hidden); U 3 proposed (9.2), the module's lines use short names even in debug mode (D27), the fix a `full` parameter to `tools_register`, the same edit 1.3 proposed in its 9.6; S 3 and two M 3 fixed: the withdrawn `sql_run` refusal sentence gone from the test, `held`/`show` renamed `images_held`/`scene_show`, `recorded_tools` inside `constants`. Files changed: `ts/tools_browser.ts`, `ts/test_tools_browser.ts`; fragment `tmp/review/i18n/1.27.json` adds `tools_browser.debug_off`. Requests sent none; 1.1_5, 1.2_27, 1.2_28, 1.26_1 (a notice, no change) applied. Pending seam: 1.24_2 (order of `db_load`'s snapshot behind a database's forwarded lines), now claimed by 1.28; 1.27's side changes when 1.28 sends its request. Open, maintainer's: whether every field carries its own comment line (11.19.6.5 second half), read otherwise by 1.24, none added; one baseline 80 column test comment the formatter cannot wrap. Locks none, inbox empty. Departures from 7.2: `sed -n`, `cat`, `head`, one `git rev-parse`. Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and 16 claimed; 1.28 report and 5 claimed; reports of 1.29, 1.30); inboxes unchanged; nothing staged. Verifier 1.37's group (1.24, 1.27) has all ended with empty inboxes. Launched task 1.34 with the prompt of 15.3.1, entry "13.1 and 13.2.4", Phase 3.

22_1218 Task 1.29 ended, after its resumption. Reply: no change begun before the stop, `git diff 85b7075` empty for its three files, no lock. 4 findings, 3 fixed: 4.1 S 3 the page used `provider.timeout_seconds` as the image download timer, now `download_seconds: 120` with the writer-chose comment; 4.2 U 3 `ts/page.ts` had its own `names_full()` reading `debug`, a second reader against D27, the page now takes the name form from the worker's first line (`settings.set`), the private function gone; 4.4 M 3 one word names in `ts/test_page.ts` renamed `FieldTable`, `FixtureElements`, `HandlerBench`. Not fixed: 4.3 U 3 `DomPort` builds `ui.input` and `ui.control_key` in short names even in debug mode, the fix needing a constructor argument `API/ts/boot.d.ts` would declare, stub edit and code proposed in item 9.1 (6.2). Files changed: `ts/page.ts`, `ts/test_page.ts`; `html/engine.css` unchanged; no fragment needed. Requests sent none; 1.2_30 applied, 1.3_2 part (a) applied, part (b) declined under 6.2, both in done. Locks none, inbox empty. Departures: `sed`, `cat`, `head`, `tail`, `awk`, `cut`, `tr`, `od` to read, one `git rev-parse`; one `git show 85b7075:ts/page.ts` piped into `head -0`, printing nothing, forbidden by 7.3. Checks: locks shown are running agents' only (1.19, 1.28 as before; 1.30's report); nothing staged. Verifier 1.39's group: 1.29 ended with an empty inbox, so 1.39 may launch (8.8.1).

22_1218 Task 1.30 ended, after its resumption. Reply: no lock or edit found against 85b7075 on resume. 3 findings, all M 3, all fixed: 4.1 the `columns: 120` / `rows: 40` comment in `ts/console_view.ts` gains the writer-chose wording (1.2_31); 4.2 one word names now `ViewPhase` in `ts/console_view.ts` and `ViewRig` in `ts/test_console_view.ts` (1.2_32); 4.3 `budget` in `ts/test_media.ts` and the frame, band, cell sizes in `ts/test_console_view.ts` gain the writer-chose comment. Candidates checked, not filed: 11.22.6.1, 11.22.6.3, 11.22.6.5 (allowed by 11.14.4.6), 11.22.6.4 (belongs to `ts/page.ts`). Files changed: `ts/console_view.ts`, `ts/test_console_view.ts`, `ts/test_media.ts`; empty fragment `tmp/review/i18n/1.30.json`. Requests sent none; 1.2_31, 1.2_32 applied, in done. Proposed plan edit: 11.22.3.9 to say `exit_done` throws unless the view is "open or closing", as the code and 4.5.30. Open, maintainer's: 11.22.5.1 and 4.7.8, the xterm `Terminal` constructor options written from memory and the resize path. Locks none, inbox empty. Departures: read only `sed -n`, `awk`, `cat`, `head`, `sort`, `uniq`, `printf`, `git rev-parse`; read `ts/wire.ts` under 1.23's lock name `ts/wire.ts.T1.23`. Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and 16 claimed; 1.28 report and 5 claimed); inboxes 1.19: 16 claimed, 1.28: 5 claimed, all others empty; nothing staged. Phase 1 now has only 1.28 running. Two slots freed: launched tasks 1.36 and 1.37 with the prompt of 15.3.1, entries "13.1 and 13.2.6" and "13.1 and 13.2.7", Phase 3.

22_1222 Task 1.32 ended (verifier of 1.12, 1.13). Reply: all 9 fixes CONFIRMED, none REJECTED. 1.12: two new error vectors (boolean `b`, blob header not an object); TypeScript test that a 5000 digit number reads as `Infinity`; Python test that deep nesting gives `RecursionError`; Python test refusing a leading byte order mark; a `cast` for the `isinstance` branch in `_blob_named`; writer-chose comments on size constants. 1.13: `python/mcp_stdio.py` UTF-8 stdin and stdout with a child process test under ASCII; four MCP error tests compare the exact `i18n` text; 1.2_4 renames applied correctly. Neither task declined a request; both fragments empty; no seam changed; added lines ASCII and within 79 columns; six sampled "met" items hold. Report 1.13 still lists 1.13_1 (`id_next` for the `hello` id) pending though 1.16 declined it; the point is open for the maintainer, the decline 1.34's to check. Owed to testing: whether 1,000,000 nested brackets give `RecursionError` on Python 3.14.4 rather than a crash; whether pyright strict accepts `cast(io.TextIOWrapper, …)`. Requests none, files changed none outside its report, locks none. Departures: one `git show` of the baseline commit to count a test pattern, forbidden by 7.3; `sed`, `awk`, `cat`, `head`, `sort` to read; one temporary list in the scratchpad. Checks: locks shown are running agents' only (1.19 report, `python/test_browser.py` and its inbox released; 1.28 report and 5 claimed; 1.36's report); inbox 1.19 now empty; inbox 1.18 now holds 1.19_1 from 1.19, so 1.18 owes a drain and verifier 1.34's group (running) no longer has every inbox empty; nothing staged. Slot freed: Phase 2 drain of 1.18 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3).

22_1223 Task 1.19 ended its Phase 2. Reply: all 16 requests worked and in `done/1.19` (20 in all), one lock cycle on `python/test_browser.py`. Applied in full 15: 1.5_1 to 1.5_7, 1.6_1 to 1.6_4, 1.7_1 to 1.7_3, 1.17_1. Partly applied 1.6_5: the token timer rung stops ttyd with `SIGSTOP` instead of the stub, the stub's unused held token path removed; `rung_opening` stays on the stub until 1.18 lets `python/devtools.py` keep `Fetch.requestPaused` events, sent as 1.19_1 to 1.18 with `Seam: pending`, no change on 1.19's side. Addition beyond the requests: for 1.6_1 the order rung's port waits `_ORDER_SECONDS` = 30, its own choice, since releasing each answer one step at a time takes several DevTools round trips past the old 2 s HTTP timeout. Departures from 1.6_2 and 1.6_4: the late answer rung records a `BrokenPipeError` or `ConnectionResetError` on its write as a measured outcome, any other handler error still failing the run; the 128 MiB echo runs in a worker of the bundle built from the probe kit's `echo_body` source, the two drain rungs staying on the page's port as 1.6_4 allows. Owed to testing: whether Chrome fires `error` for a failing `<object>` and SVG `<image>`; whether a stopped ttyd still accepts the connection so the token timer runs; what the late write meets. Report items 5 to 7 and 12 updated; item 12 met except the open timer through ttyd, held by 1.19_1. Files changed: `python/test_browser.py`. Locks none, inbox empty. Departures: shell `for` loops, `cut`, `tr`, `sort`, a redirection of scratch lists to the session scratchpad. Verifier 1.35's group: 1.19 ended with an empty inbox, so 1.35 may launch.

22_1223 Task 1.33 ended (verifier of 1.14, 1.15). Reply: all 15 fixes and applied requests CONFIRMED, none REJECTED. 1.14: 6 (findings 4.1 to 4.4, requests 1.2_5, 1.24_1); the rebuilt replay start in `python/test_substrate.py` gives the same seq values (`_files` 1 to 3, `metaverse` 5 to 12); the TypeScript twin changed through 1.14_1. 1.15: 9 (findings 4.1 to 4.8, request 1.2_6); the restart fix removes every form of `--main-loop` that `python/bootstrap.py`'s parser accepts and leaves look-alike words; the TAP file is written unbuffered and a short write raises, its test passing only once 1.40 merges `engine_tap.write_short`. No declined requests; sampled "met" items hold. Observations, not findings: `python/test_engine_kv.py` still compares the English literal `_DESYNC_MESSAGE` beside the `i18n` text while 1.14 removed the same literal from `python/test_substrate.py`, both meeting 3.5; 1.14's recorded `git show` breaks 7.3. Files changed none, requests none, locks none. Departures: read only `sed -n`, `cat`, `head`, `tail`, `sort`, `tr`, `git rev-parse`; one redirect of a name list into the session scratchpad. Checks: locks shown are running agents' only (1.18 `python/test_devtools.py` and claimed 1.19_1; 1.28 report and claimed requests; 1.36's report); inbox 1.27 now holds 1.28_1 from 1.28, `Seam: 1.24_2 applied`, so 1.27 owes a drain and verifier 1.37's group (running) no longer has every inbox empty; nothing staged. Two slots freed: Phase 2 drain of 1.27 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3); launched task 1.35 with the prompt of 15.3.1, entry "13.1 and 13.2.5", Phase 3.

22_1224 Task 1.18 ended its Phase 2. Reply: request 1.19_1 applied (the "wire open timer" rung to move from the stub server to ttyd, using DevTools `Fetch.enable` with ttyd stopped, needs `python/devtools.py` to keep the `Fetch.requestPaused` events it drops): `PageEvents` gains a `requests_paused` list, appending each such event's `params` in order, kept out of `API/python/devtools.pyi` as the other extra `PageEvents` fields under 4.5.26; test first, `TestPage.test_request_paused`. Seam: 1.18_2 sent back to 1.19 with `Seam: 1.19_1 applied`; 1.19's side (`LifecycleEvents` declaring the field, the rewrite of `rung_opening`) pending. Files changed in Phase 2: `python/devtools.py`, `python/test_devtools.py`. Report items 5 to 7, 12, 13 updated, published; exit still met. Locks none, inbox empty, no departures in Phase 2. Phase 1 totals unchanged: 9 fixed, 1 proposed plan edit (11.10.3.14). Checks: locks shown are running agents' only (reports of 1.27, 1.28, 1.36); inboxes 1.27, 1.28 now empty; inbox 1.19 holds 1.18_2, so 1.19 owes a drain; nothing staged. Verifier 1.34 (running) is to be resumed for 1.18's Phase 2 change if it ends without it. Slot freed: Phase 2 drain of 1.19 sent by SendMessage with the text of 15.3.2 (resumption 2 of 3).

22_1225 Task 1.27 ended its Phase 2. Reply: request 1.28_1 (M 2, `Seam: 1.24_2 applied`) applied: `db_load` asked the server for a snapshot while this side's copy was still open, so a write made in between could be lost under the loaded image; the tool now unloads a loaded database first, then sends `db.snapshot` as before. Test first, `TestAdmin.test_load_loaded`: the call unloads the open database, a read then fails with `substrate.db_unloaded`, the wake opens the snapshot at its `seq`; the other load tests already unload first and are unchanged. Seam 1.24_2 closed: 1.28's side, the server port holding a snapshot behind the database's waiting lines, is in `ts/worker_ai.ts`; no request goes back. Report published with new finding 4.7 and items 3.9, 5, 7.5, 12.6, 12.9, 13.3 updated. Files changed this phase: `ts/tools_browser.ts`, `ts/test_tools_browser.ts`. Totals: 7 findings (M 2 x2, U 3 x1, S 3 x1, M 3 x3), 5 fixed, 2 proposed edits needing the maintainer (tty 0 opening 9.1, debug mode name form 9.2). Requests sent none; locks none, inbox empty. Departure: one read only `cat` of the request. Checks: locks shown are running agents' only (1.19 claimed 1.18_2; reports of 1.31, 1.35, 1.36; 1.28's report released, 1.28 still runs); inboxes all empty but 1.19's claimed one; nothing staged. Verifier 1.37 (running) is to be resumed for 1.27's Phase 2 change if it ends without it. Slot freed: launched task 1.38 with the prompt of 15.3.1, entry "13.1 and 13.2.8", Phase 3.

22_1225 Task 1.28 ended, after its resumption. Reply: no change begun before the stop. 11 findings (M 2 x2, M 3 x2, U 2 x4, S 2 x2, S 3 x1), 10 fixed with tests: the start fetches the scene image and the scripted provider's Script from the server only when the browser lacks the file; debug mode's tty 1 overlay shows the hello and its reply, and the wire rendering reaches the server as `verbose.put`; `provider.scripted` read once. Not fixed: 4.11 a byte measure copied from `ts/queue.ts` needs a public `queue.line_bytes` in `API/ts/queue.d.ts`, proposed edit 9.1. Inbox all applied: 1.20_1 no change needed; 1.21_1 a settings put from the UI also changes the AI's live settings; 1.22_1 synchronous mode outside debug mode throws `worker_ai.synchronous_release`; 1.2_29 one word names now `FieldTable`, `WorkerBench`; 1.24_2 applied by another mechanism, as the proposed `replicate.fetch` line would fault in `ts/queue.ts` (`queue.reply_missing` / `queue.reply_unowed`): a new port `ServerHold` around the server port holds a `db.snapshot` behind its database's waiting lines in `ForwardQueue`. Files changed: `ts/worker_ai.ts`, `ts/test_worker_ai.ts`; `ts/boot.ts`, `ts/test_boot.ts` unchanged; fragment `tmp/review/i18n/1.28.json`. Request 1.28_1 to 1.27 (unload a loaded database before `db_load` asks its snapshot), applied by 1.27. Proposed edits: 9.1 above; 9.2 updates 11.20.3.6, 11.20.3.12, 11.20.4.9 for `ServerHold` and the new wake `worker.script_fetched`. Locks none, inbox empty. Departures from 7.2: `sed -n`, `cat`, `awk`, `head`, `cut`, one `git rev-parse` to read; one `printf >>` appending resolution lines to five request files. Checks: locks shown are running agents' only (1.19 claimed 1.18_2; reports of 1.35, 1.36; 1.31's report released, 1.31 still runs); nothing staged. Phase 1 complete: every task 1.1 to 1.30 has ended. Verifier 1.39's group (1.28, 1.29, 1.30) has all ended with empty inboxes. Slot freed: launched task 1.39 with the prompt of 15.3.1, entry "13.1 and 13.2.9", Phase 3; every verifier is now launched.

22_1225 Task 1.31 ended (verifier of 1.9, 1.10, 1.11). Reply: all 21 fixes CONFIRMED, none REJECTED: 1.9 six (4.1 to 4.5, applied 1.16_1); 1.10 three (4.1 to 4.3, 4.3 the same fix as 1.2_1); 1.11 twelve (4.1 to 4.12, including 1.2_2, 1.2_3). Declined requests CONFIRMED: 1.1_2 (`--srv-buf-size` stays a literal in the start script, by 11.3.3.5, 11.3.3.15, 2.11.3) and item 9 of 1.2_2 (`if ($log_path_)` stays, `xsjs_status.ps1` writes no log by design). Unfixed findings' reasons hold under 6.12 and 7.1: 1.10 4.4 (division after a type argument in the audit's scanner), 1.11 4.13 (`wsl --list` exit codes never read). Report 1.10 wrong on one point: its open question 10.2 says `powershell/test_lint.ps1` has no byte order mark, but it starts with one at the baseline; 1.11's proposed edit 9.2 has it right. Proposed edits: 1.11's 9.2 misses 11.2.4.12 and 11.2.4.19, which still say the mark is absent. No `tmp/review/i18n/1.10.json` exists; nothing lost, 1.10 adds no strings. Latent risk, not a rejection: the new `xsjs_util_get_command_text` would log the wrong value if a future command used one of its own local names (`$command_`, `$value_` and four others); no current call does. Requests none, inbox empty, locks none, files changed only its report. Departures from 7.2, read only: `cat`, `sed -n`, `od`, `head`, `file`, `sort`, `tr`, `git rev-parse`, a `for` loop; two name lists in its scratch directory; none against 7.3. Checks: locks shown are running agents' only (1.19 `python/test_browser.py` and claimed 1.18_2; reports of 1.35, 1.36); nothing staged. Running: 1.19 (Phase 2), verifiers 1.34 to 1.39; seven of eight, nothing queued. Owed: resume 1.34 for 1.18's Phase 2 change, 1.37 for 1.27's, 1.35 for 1.19's second Phase 2, each if it ends without having checked it.

22_1226 Task 1.19 ended its second Phase 2. Reply: request 1.18_2 applied, in done (21 resolved in all): 1.18 applied 1.19_1, so `devtools.PageEvents` keeps paused fetch requests in `requests_paused`, closing the seam. `rung_opening` now goes through ttyd, not the stub, completing 1.6_5: it reads ttyd's token, stops ttyd, has DevTools pause the port's token fetch and answers it with ttyd's own token, so the port asks a stopped ttyd for the WebSocket and its open timer runs out; `Fetch.disable` and ttyd's resume sit in a `finally`. Removed as unused: the stub's `_OPENING_BASE`, its two branches, `release_wait`; `LifecycleEvents` declares `requests_paused`. Report items 5, 6.1, 7.17, new 7.21, 12 updated, published; nothing held open by a request. Owed to testing: that DevTools can pause the port's token fetch and answering it with ttyd's token lets the WebSocket request go on; that a stopped ttyd still accepts the connection so the open timer runs. Files changed: `python/test_browser.py`. Locks none, inbox empty. Departures: `cut`, `tr`, read only. Checks: locks shown are running agents' only (reports of 1.35, 1.36); every inbox empty; nothing staged. Phase 2 has no inbox left to drain; resumptions used: 1.19 two, 1.24, 1.15, 1.9, 1.18, 1.27 one each. Running: verifiers 1.34 to 1.39, six of eight; nothing queued.

22_1228 Task 1.34 ended (verifier of 1.16, 1.17, 1.18). Reply: 3 REJECTED, the rest CONFIRMED. REJECTED, each a request to its owner (9.4): 1.16 4.2 in `python/seed/prompt.json`, the sentence right but the edit dropped the space after a colon, now ``bytes:`engine.store.kv_put``, request 1.34_1 to restore it; 1.16 4.6, new `python/test_echo_loop.py`: four size constants' comments lack the writer-chose wording (6.7, 3.5), and `python/test_main_loop.py`, owned by 1.16 and marked met, has the same four lines, request 1.34_2 covering both; 1.18's Phase 2 work on 1.19_1 adds a public field `PageEvents.requests_paused` to `python/devtools.py`, used by another module and not declared in the `API/` stub, while 4.5.26 accepts only five named fields outside the stub, so under 6.2 it should have been a proposed edit, request 1.34_3 asks 1.18 to remove it, keep the design as a proposed edit, and ask 1.19 to undo its side. CONFIRMED: the other fixes of the three tasks, 1.16's declined 1.13_1, 1.18's design of the `overlay_install` request (1.21's applying it is 1.36's). Sampled "met" item failing: the `python/test_main_loop.py` constants. Open: whether 4.5.26's acceptance covers further `PageEvents` fields; if 1.18 declines 1.34_3 citing a decided item, the maintainer decides. Notes: 1.17 and 1.18 each ran one `git show` (7.3), recorded; in `python/test_echo_loop.py`, if the forked child fails to write its result file it never kills itself and runs the rest of the suite, noted for the maintainer, not filed. Files changed none, locks none. Departures: `cat`, `sed -n`, `awk`, `head` to read; `git rev-parse`, `date` once each. 1.34 saw 1.18's Phase 2 change, so no resumption is owed for it. Checks: locks shown are running agents' only (1.35's report; 1.36's report released, 1.36 still runs); inboxes: 1.16: 1.34_1, 1.34_2; 1.18: 1.34_3; 1.21: 1.36_1 from verifier 1.36; nothing staged. Three slots free: Phase 2 drains sent by SendMessage with the text of 15.3.2 to 1.16 (resumption 1 of 3), 1.18 (resumption 2 of 3), 1.21 (resumption 1 of 3).

22_1228 Task 1.36 ended (verifier of 1.20 to 1.23). Reply: 26 fixes and 12 requests checked, all CONFIRMED but one part. 1.20: 4.1 to 4.3 with 1.1_1. 1.21: 4.1, 4.2, 4.4 to 4.7 with 1.2_14 to 1.2_16 and 1.18_1; 4.8 CONFIRMED except one part REJECTED (M 3): the new comment on `settings_make` in `ts/test_settings.ts` calls the fixture's values "its writer's choice", but all but `debug` are copied from `settings.json`, as the baseline comment ("the example values") said; request 1.36_1 to 1.21 restores the baseline line. 1.22: 4.1, 4.2, 4.3, 4.5 with 1.2_17, 1.2_18; the removed `queue.step_empty` used nowhere else. 1.23: 4.1 to 4.4, 4.6 to 4.13; declines of 1.2_19 (the `WirePort` half), 1.2_21, 1.3_1 CONFIRMED by the items cited. The diff touches exactly the 18 files the four reports list; fragments, seams, line widths, comment rules hold. Pending with 1.28, for its verifier: 1.20_1, 1.21_1, 1.22_1 (all since applied by 1.28). Departure seen: 1.23's `git show 85b7075:ts/test_http.ts` (7.3). Requests 1 sent; files changed none outside `tmp/review/`; locks none. Departures: read only `sed -n`, `cat`, `awk`, `head`, `cut`, `tr`, `git rev-parse`. Checks: locks shown are running agents' only (1.35's report; drains of 1.16, 1.18, 1.21 just sent, no locks yet); inboxes as at the entry above; nothing staged. Running: 1.16, 1.18, 1.21 (Phase 2), verifiers 1.35, 1.37, 1.38, 1.39; seven of eight.

22_1229 Task 1.21 ended its Phase 2. Reply: request 1.36_1 (M 3, verifier 1.36 REJECTED one part of fix 4.8) applied: the comment on `settings_make` in `ts/test_settings.ts` restored to the baseline "the example values", the values being those of `settings.json`; the rest of 4.8 (named constants `timeout_changed`, `line_changed`) confirmed; in `done/1.21`. Its request 1.21_1 to 1.28 (4.3) applied by 1.28: a debug settings change on the page updates the AI worker's copy before it goes to the server, test `TestRelays.test_settings_sent`; nothing calls the change from the worker's side, so nothing went on to 1.29. Report items 5 to 7, 12 updated, a note under 4.8; definition of done met; open for the maintainer: tests of a write to a frozen object check only the error type, the browser's error having no `i18n` text. Phase 2 changed `ts/test_settings.ts` only; requests sent none; locks none; inbox empty. Departure: `echo >>` of the resolution line. 1.36 is not resumed: 9.4 gives a REJECTED fix's result to the closing agent (14.1.4).

22_1229 Task 1.37 ended (verifier of 1.24, 1.27). Reply: none REJECTED. 1.24: 7 fixes and 4 requests (1.14_1, 1.2_23, 1.8_1, 1.8_2) CONFIRMED; 1.27: 5 fixes and 5 requests (1.1_5, 1.2_27, 1.2_28, 1.26_1, 1.28_1) CONFIRMED, so 1.27's Phase 2 change was checked and no resumption is owed. Neither declined a request. The `forward_pending` change: 1.24 removed a block that stopped a database being unloaded or reloaded with unanswered writes to the server; the pieces keeping the reloaded copy in step are in place in `ts/substrate.ts` (1.24), the server port in `ts/worker_ai.ts` (1.28), the `db_load` tool in `ts/tools_browser.ts` (1.27). Not fixed, reasons hold: 1.24 4.5, 1.27 4.2, 1.27 4.3 need `API/` stub changes, proposed edits; 1.24 4.9 (`VACUUM` renumbering rows in the browser's copy) open. Remarks for the closing agent: `doc_head` in `ts/substrate.ts` reads a document's version as a JavaScript number, so past 2^53 it can return the wrong reference if sqlite3.wasm returns numbers not BigInts (owed to testing), the new test using an even value that cannot catch it; 1.24's report still lists 1.24_2 pending though 1.28 applied it; matching findings handled differently, 1.24 turned `arrival_text` into a function and judged field comments unneeded, 1.27 left `arrival_text` outside `constants` and listed field comments open. Files changed none outside `tmp/review/`; requests none; locks none. Departures: read only `sed -n`, `awk`, `cat`, `comm`; one `git diff` saved to the session scratchpad.

22_1229 Checks: locks shown are running agents' only (reports of 1.18, 1.35; 1.16's claimed requests released); inbox 1.16 now empty; inbox 1.19 holds 1.18_3 from 1.18, `Seam: 1.34_3 applied`: 1.18 has withdrawn `requests_paused` from `python/devtools.py` under 1.34_3, so until 1.19 undoes its side (`LifecycleEvents` field, `rung_opening` back to its baseline form on the stub) the seam stands half applied; nothing staged. Phase 2 drain of 1.19 sent by SendMessage with the text of 15.3.2 (resumption 3 of 3, its last; any later request to 1.19 goes to the postmortem). Verifier 1.35 (running) is to be resumed for this change if it ends without it. Running: 1.16, 1.18, 1.19 (Phase 2), verifiers 1.35, 1.38, 1.39.

22_1230 Task 1.16 ended its Phase 2. Reply: both REJECTED fixes reworked: 1.34_1 (M 3) the space after "bytes:" in `python/seed/prompt.json` restored, the word diff against `85b7075` showing only 4.2's added clause; 1.34_2 (M 3) the comments on `_OVERFLOW_BYTES`, `_CHUNK_BYTES`, `_STREAMED_BYTES`, `_READ_BYTES` in `python/test_echo_loop.py` and `python/test_main_loop.py` now say their writer chose them, in the request's wording, values unchanged. Unrequested, by the same rule after checking the area's other test modules: `_LOOP_SEQ` in `python/test_bootstrap.py` now reads "Counts chosen by their writer: the `seq` map the test main loop returns."; the rest are recorded results, not choices. 1.16_1 to 1.9 applied. Report items 5 to 7, 12 updated, item 12 noting Phase 1's size comment check missed these; published. Locks none, inbox empty. Commands: `ls`, `cat`, `grep`, `git diff`, `awk` read only, `test`, `mv`; `cat`, `awk` outside 7.2; no shell writes.

22_1230 Task 1.18 ended its second Phase 2. Reply: request 1.34_3 applied, not declined, nothing deciding the field being found: `requests_paused` on `PageEvents` is a public name another module uses, with no stub text and no acceptance (6.2), 4.5.26 accepting five named fields only, and candidate 12.5.5.4.10 names two fixes for the open timer rung (`--max-clients 1`, or `Fetch.enable` with ttyd stopped) that no record chooses. Removed: the field and its `Fetch.requestPaused` branch from `python/devtools.py`, `test_request_paused` from `python/test_devtools.py`, both back to their Phase 1 state. Design kept: report item 9.2, a proposed edit of `API/python/devtools.pyi` with the stub line, code, test and 1.19's steps for `rung_opening`; item 10.7 lists 12.5.5.4.10 not fixed under 6.12. Seam: 1.18_3 to 1.19 with `Seam: 1.34_3 applied`, pending with 1.19. Report items 5, 6, 7, 9, 10, 12, 13 updated, published; exit met. Locks none, inbox empty, 1.34_3 in `done/1.18`. Departure: one `tail` to read a resolution line. 1.34 is not resumed for 1.16's and 1.18's rework: 9.4 gives a REJECTED fix's result to the closing agent (14.1.4). Checks: locks shown are running agents' only (1.19 claimed 1.18_3; 1.35's report); inboxes all empty but 1.19's claimed one; nothing staged. Running: 1.19 (Phase 2, last resumption), verifiers 1.35, 1.38, 1.39.

22_1230 Task 1.38 ended (verifier of 1.25, 1.26). Reply: 13 verdicts, all CONFIRMED. 1.25: five fixes (the scripted provider's fourth fault, `tool_call_id`s not matching the calls, with `provider_script.results_unmatched` and a test; `FieldTable`, `ScriptBench`; two module level constants in `ts/provider_script.ts` moved into their functions; a test of a permit tool's `_meta` surviving `tools/list`; a test of `tools_convert` dropping `_meta`), and the untested `provider.key_missing` case rightly left unfixed, needing a new name in `API/ts/provider.d.ts`, proposed edit 9.1. 1.26: six fixes (`;` in a comment replaced; `Fields`, `Bench`, three local `tools` renamed; a script returning NaN, Infinity, a BigInt or a cyclic object comes back as the run's error instead of faulting the turn, 1.27 notified first; the prompt type check removed, a non string `text` still throwing; bare soft limit 0 named `soft_reached`; `slot_count` comment says its writer chose it). Neither declined a request; no locks; `API/` and `i18n/en-US.json` untouched; new strings in fragments; sampled "met" items hold. Owed to testing: `tsc` and the "stage 0: typescript suites" rung. Noted: 1.25's `git show 85b7075:ts/test_mcp.ts` (7.3). Files changed none but its report; requests none; locks none. Departures from 7.2, read only: `sed -n`, `cat`, `awk`, `git rev-parse`, two `python3 -I -c`. Checks: locks shown are running agents' only (1.19 claimed 1.18_3; 1.35's report); nothing staged. Running: 1.19 (Phase 2), verifiers 1.35, 1.39.

22_1231 Task 1.19 ended its third Phase 2, its last resumption. Reply: request 1.18_3 applied, in done (22 in all): its side of the open timer change undone after 1.34 REJECTED the `python/devtools.py` side (6.2, a public name on a class the stub declares with no stub text; 5.2, no record choosing between the candidate's two alternatives). Back at the baseline: `rung_opening`, its table call `rung_opening(session, stub)`, `_OPENING_BASE`, the stub's opening branches, `release_wait`; `LifecycleEvents` no longer declares `requests_paused`; `git diff` against the baseline shows no change left in `rung_opening` or `release_wait`. Seam 1.19_1 / 1.18_2 / 1.34_3 / 1.18_3 now applied on neither side. Stays: the token timer rung still goes through a stopped ttyd (1.6_5 item 1), needing nothing new from `devtools`; 1.19 notes 1.34_3's reasoning may cover it too. Gap open: the open timer rung still points at the stub (12.5.5.4.10), the design to move it to ttyd kept in 1.18's report item 9. Report items 5, 6.1, 7.17, 7.21, new 7.22, 12 updated, 1.19_1 recorded withdrawn; published. Files changed: `python/test_browser.py`. Locks none, inbox empty, every command within 7.2. Checks: locks shown are running agents' only (1.35's report); every inbox empty; nothing staged. Phase 2 has no request left; resumptions used: 1.19 three (its limit), 1.18 two, 1.24, 1.15, 1.9, 1.27, 1.16, 1.21 one each. Running: verifiers 1.35, 1.39. Owed: resume 1.35 for 1.19's third Phase 2 change if it ends without it.

22_1233 Task 1.39 ended (verifier of 1.28, 1.29, 1.30). Reply: 17 items, 16 CONFIRMED, 1 REJECTED. REJECTED (M 2): 1.28 4.3, the tty 1 debug overlay now also showing `hello`, shows the whole `hello` including `provider_key`, the provider API key: in debug mode the key reaches the UI thread's overlay on screen and in a test's PNG, and through fix 4.4 the AI thread's log, which the AI can read through a tool, and the server's `_verbose` database; the shipped `settings.json` turns debug on and the server sends the key whenever `XSJS_PROVIDER_KEY` is set; this breaks 2.10.1, 11.17.3.12, 11.20.3.8, which keep the key in the worker's memory only. Request 1.39_1 to 1.28 with two designs, neither chosen: (a) remove the hello display and list the conflict open; (b) show the hello without `provider_key`. Declines CONFIRMED: 1.3_2 (b) / 1.29 4.3 (`DomPort` lines in short names, 6.2, stub edit proposed in 1.29's report); 1.28 4.11 (copied `line_bytes`, 6.2). Open for the maintainer: fix 4.4 CONFIRMED, but in debug mode each wire line's rendering goes into a log entry capped at `line_max` (1 MiB shipped), so a valid wire line well under that cap can stop the worker with `queue.entry_over`; the design asks for the rendering, a design gap, not the fix's fault. Files changed none outside `tmp/review/`; locks none. Departures from 7.2, read only: `sed -n`, `cat`, `head`, `awk`, one `git rev-parse`. Checks: locks shown are running agents' only (1.35's report); inbox 1.28 holds 1.39_1; nothing staged. Phase 2 drain of 1.28 sent by SendMessage with the text of 15.3.2 (resumption 1 of 3; its 22_1212 resumption was a lost agent's, 8.9). Running: 1.28 (Phase 2), verifier 1.35.

22_1235 Task 1.28 ended its Phase 2. Reply: request 1.39_1 applied with option (a): fix 4.3 reverted, since it put `provider_key` on screen, in the AI thread's verbose ring and in the server's `_verbose` in debug mode, against the design keeping the key in the worker's memory only. Removed: `tap?.received_show(hello)`, the `tap` parameter of `hello_answer`, `WireTap.received_show`, its test `test_hello_shown`; `WireTap` back to its baseline form; the reply to `hello` still goes through the tap and is shown. Fix 4.4 (wire rendering to `_verbose`) stays, as the verifier asked. New open question, report 10.6: the overlay should show every wire line both ways but the key must not leave the worker; (a) do not show `hello`, as the code now does, or (b) show `hello` rendered without `provider_key`; no record decides, so item 12.7 is marked unmet for that reason only. Files changed: `ts/worker_ai.ts`, `ts/test_worker_ai.ts`; `ts/boot.ts`, `ts/test_boot.ts` unchanged. Requests sent none; 1.39_1 in `done/1.28`. Report items 4.3.6, 5, 7.6, 10.6, 12.7, 13.3 updated, published. Locks none, inbox empty. Departures from 7.2: `cat`, `awk` to read and measure; one `printf >>` of the resolution line. Checks: locks shown are running agents' only (1.35's report); every inbox empty; nothing staged. Running: verifier 1.35 alone.

22_1237 Task 1.35 ended (verifier of 1.19). Reply: all 11 findings of report 1.19 (4.1 to 4.11) CONFIRMED; 21 of 22 resolved requests CONFIRMED, 1.18_2 undone by 1.18_3 leaving nothing to confirm; 1.18_3 CONFIRMED: the open timer rung and `release_wait` back as at the baseline, neither `python/test_browser.py` nor `python/devtools.py` declaring `requests_paused`. No declined requests, none REJECTED. Late change: while it worked 1.19 applied 1.18_2 and undid it; the final `git diff` of `python/test_browser.py` matches what it first read, byte for byte, so no resumption is owed. Six sampled "met" items hold. Remark, not a finding: the stub server's error reaches the main thread by `SIGUSR1` at any point, so after a failure it can land inside cleanup, such as the `finally` resuming a stopped ttyd or the browser's shutdown. Owed to testing: if headless Chrome asks the stub for `/favicon.ico` or resets a held socket, the run now ends where before it carried on; the read only `events` property and the `contextlib.ExitStack` annotations need a pyright strict run. Open: the open timer rung through ttyd stays on the stub (12.5.5.4.10) after 1.34 rejected the `devtools.py` field. Files changed none outside `tmp/review/`; requests none; locks none. Departures: read only `cat`, `sed -n`, `awk`, `head`, `tr`, `sort`, `cut`, scratch redirections. Checks: lock check printed nothing; every inbox empty; nothing staged; all 39 reports 1.1 to 1.39 published. Phase 3 complete: every writer and verifier has ended (8.8.2). Phase 4: launched task 1.40 with the prompt of 15.3.1, entry 14.1, Phase 4.

22_1248 Task 1.40 ended (closing). Reply: all checks passed, no requests sent. 14.1.1: all 20 fragments merged into `i18n/en-US.json`, 350 names; 6 added, 2 reworded, 5 removed; no conflicting texts, every name from the task owning its prefix, no removed name still called. 14.1.2: all 1272 literal calls name an existing entry with the right argument count, apart from the deliberate probes of the two `test_i18n` files; every entry used outside the tests. 14.1.3: the review created only `python/test_echo_loop.py` and `python/test_stall_loop.py`, both covered by the reformat whitelist and each once in `_MODULES`; no renames. 14.1.4: the five REJECTED fixes' reworks (1.34_1, 1.34_2, 1.34_3, 1.36_1, 1.39_1) hold. 14.1.5: seam 1.24_2 applied in all three files; seam 1.19_1 backed out on both sides; nothing half applied. 14.1.6: no locks, inboxes empty, nothing staged. 14.1.7: `tmp/review/summary.md`, `tmp/review/maintainer_edits.md`, `tmp/review/open.md` written. Totals: 234 findings (M 159, U 45, S 30; severity 1: 10, 2: 64, 3: 129, 4: 31); 189 fixed, 7 partly fixed, 38 not fixed, each listed with a sentence and its reason, most waiting on stub or plan edits or questions for the maintainer. Three unfixed severity 1: a stub comment check stops `python/test_posix.py` once the banner question is answered: 1.2 4.1 (`API/python/tap_consumer.pyi`), 1.2 4.3 (24 of 25 `API/ts/*.d.ts`), 1.2 4.2 (the plan's list of where a run stops); fixes proposed in report 1.2 item 9. Departures: `sed`, `awk`, `cat` to read; two read only `python3 -I` scripts in its scratchpad (call check, report sections); `maintainer_edits.md` and `open.md` written by shell redirection; one `git show 85b7075:i18n/en-US.json`, forbidden by 7.3, printing only a line count. Checks: lock check printed nothing; every inbox empty; nothing staged. 14.1.6 calls for no further round. Phase 5: launched task 1.41 with the prompt of 15.3.1, entry 14.2, Phase 5.

22_1251 Task 1.41 ended (formatter). Reply: the formatter is stable, `tmp/review/format_1.diff` and `tmp/review/format_2.diff` byte identical under `cmp`. Staged 86 files, the whitelisted files the review changed: 84 modified and the two new `python/test_echo_loop.py`, `python/test_stall_loop.py`; `i18n/en-US.json` and `python/seed/prompt.json` are not whitelisted, stay unstaged, and their review changes stand in both diff files. `python3 python/reformat.py` ran twice, exit 0 both times, the second changing nothing. Formatter changes, line wrapping only, none reverted, unstaged over the staged review change (`MM`): `python/test_browser.py`, `ts/test_http.ts`, `ts/test_mcp.ts`, `ts/test_substrate.ts`, `ts/test_verbose.ts`. 14.2.6: no protected file changed (`API/` stubs, `python/bootstrap.html`, `README.md`, `LICENSE.md`, `archive.sh`, `clean.sh`). Open questions met: the hook line of `html/test_engine.html` still split over three lines, so `test_template_hooked` still fails; six HTML lines over 79 columns, three in `python/bootstrap.html`; Node's compile cache still written outside `build/`. Owed to `powershell/test_lint.ps1` on Windows: the 7 PowerShell files the review changed (`xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_powershell.ps1`, `powershell/xsjs_util.ps1`, `powershell/en-US/i18n.psd1`). No commit, nothing unstaged, no requests, no locks. Departures: read only `awk`, `cut`, `sort`, `uniq`, `head`, `tail`, `cat`, `sed -n`, `xargs`, `date`, `command -v`; redirections into the session scratchpad. Checks: lock check printed nothing; every inbox empty; `git status --short`: 79 `M ` staged, 5 `MM`, 2 `A `, 2 ` M` unstaged (`i18n/en-US.json`, `python/seed/prompt.json`), the staging being 14.2.2's, the one the project rules allow. Every task 1.1 to 1.41 has ended. Phase 6: a read only agent outside the task list condenses `tmp/review/open.md` and `tmp/review/maintainer_edits.md` into a digest in the session scratchpad for the postmortem; it changes no file of the tree.

22_1320 The digest agent ended: 87 open questions, 90 values owed to testing, 81 proposed edits (14 needing a choice), formatter items; it found that several proposed stub comments would themselves fail `comments_check`, and that the proposed text for 11.4.6.4 contradicts its own reason. Lock check printed nothing; every inbox empty. Every agent has ended; the postmortem follows, its annex being the digest, copied below it whole.

## Postmortem

22_1320. Baseline `85b7075`. Sources: the 41 reports under `tmp/review/report/`, `tmp/review/summary.md`, `tmp/review/open.md`, `tmp/review/maintainer_edits.md`, the record above, and the annex below.

1 Unfinished tasks and lost agents

1.1 Unfinished tasks: none. Tasks 1.1 to 1.41 have ended and their 41 reports are published; no lock is left and every inbox is empty.

1.2 Lost agents: eight. After 22_0757 every running agent, tasks 1.17, 1.23, 1.25, 1.26, 1.27, 1.28, 1.29 and 1.30, stopped with HTTP 429 ("You've hit your session limit · resets 12pm (America/Los_Angeles)"). They were logged at 22_1212 with their locks and resumed by SendMessage under the same task ids after the reset; each found its edits complete or none begun, and all eight finished. No agent was replaced and none was lost after that.

1.3 Phase 2 resumptions: 1.19 three, its limit, the third working its last request; 1.18 two; 1.9, 1.15, 1.16, 1.21, 1.24, 1.27 and 1.28 one each. No request was left unworked, so none goes to this postmortem.

1.4 A read only helper agent outside the task list wrote the digest that is this postmortem's annex; it changed no file of the tree.

2 Findings not fixed, 38, ids `<task> 4.<n>`, one sentence each

2.1 Severity 1 (blocking):

2.1.1 1.2 4.1: a `;` in a comment of `API/python/tap_consumer.pyi` is refused by `comments_check`, the first stop of `python/test_posix.py` once the banner question is answered; the stub is the maintainer's and the edit is proposed.

2.1.2 1.2 4.3: 86 comments in 24 of the 25 `API/ts/*.d.ts` run over two lines or hold a `;`, which the same check refuses; proposed.

2.1.3 1.2 4.2: the plan's list of where a run stops (4.9.6.4) leaves out those stub comments; proposed.

2.2 Severity 2 (defect):

2.2.1 1.4 4.2: `version_find` in `ts/substrate.ts` rounds a Document-Ref version past 2^53 because the stub types it `number`; a public type change, proposed with two options (6.1.12).

2.2.2 1.10 4.4: the audit scanner in `python/test_posix.py` can read a division after a generic's `>` as a regular expression; telling them apart needs TypeScript's parser, which is not installed, and no current file has the form.

2.2.3 1.11 4.13: `xsjs_util_get_distribution` in `powershell/xsjs_util.ps1` does not read the exit codes of `wsl --list`; telling a failure from "none" needs WSL's real codes, a measurement.

2.2.4 1.24 4.9: the `VACUUM` of `Store.db_compact` in `ts/substrate.ts` may renumber rowids in the browser's copy only, so the copies could differ; open whether to accept, forward or refuse it.

2.2.5 1.27 4.2: `console_run` in `ts/tools_browser.ts` faults with `wire.socket_missing` when tty 0 is not open, where the design has the AI open the console with permission; it needs a new `console.show` line, proposed with a choice.

2.2.6 1.28 4.3: tty 1's debug overlay does not show the `hello`; the fix that showed it put `provider_key` on screen and in the logs, was REJECTED and reverted, and whether to show the `hello` without its key is open.

2.3 Severity 3 (rule):

2.3.1 1.1 4.1: `reply_make` in `python/dispatch.py` differs from its stub, whose `blobs` should default to `None`; stub edit proposed.

2.3.2 1.1 4.2: `main` of `python/third_party_fetch.py` is a public name its stub lacks; stub edit proposed.

2.3.3 1.1 4.4: `powershell/xsjs_util.ps1` passes `--srv-buf-size 1048576` as a literal, not from `settings.json`; declined by 1.11 under the plan's "read no setting", the decline CONFIRMED.

2.3.4 1.1 4.8: `API/README.md` names the removed planning document; edit proposed.

2.3.5 1.1 4.9 and 1.3 4.12: `API/ts/dispatch.d.ts` says a handler returns a reply without a header, where the code returns a finished reply line; edit proposed.

2.3.6 1.1 4.10: the constructor comment of `API/ts/queue.d.ts` does not say `queue_synchronous` is debug only; edit proposed.

2.3.7 1.3 4.1 and 1.27 4.3: `ts/tools_browser.ts` builds its lines in short names even in debug mode, against the rule that debug mode uses full names; it needs a `full` parameter on `tools_register`, proposed.

2.3.8 1.3 4.2: `post_make` in `ts/provider.ts` builds `http.request` in short names in debug mode; a signature change, proposed.

2.3.9 1.3 4.3 and 1.23 4.5: `ConsolePort` in `ts/wire.ts` reads `debug` itself, a second reader of the name form; a constructor change, proposed with a choice.

2.3.10 1.3 4.5: the `fault` line of `ts/error_overlay.ts` is short in debug mode, as the module depends on nothing and can run before the settings; proposed to record as an exception.

2.3.11 1.3 4.6: the wake type `worker.snapshot_reply` in `ts/worker_ai.ts` is in no record; a plan edit proposed.

2.3.12 1.3 4.9: the two `mcp` rows of `API/ts/lines.d.ts` disagree with the code, which is right; proposed.

2.3.13 1.3 4.10: `HttpResponse` in `API/ts/lines.d.ts` describes a blob the code never sends; proposed.

2.3.14 1.3 4.11: four lane rows of `API/ts/lines.d.ts` (`error`, `fault`, the `console.read` and `dom.choice` replies) describe them otherwise than the code builds them; proposed.

2.3.15 1.3 4.13: the `OwnerTable` comment of `API/ts/queue.d.ts` disagrees with the owners the code uses; proposed.

2.3.16 1.5 4.4: `rung_pool` in `python/test_browser.py` does not compare its error message, which is sqlite3.wasm's and needs a run to know.

2.3.17 1.7 4.4: `rung_compact_auto` writes a second `provider.json` against the one approved rung, while the plan asks it to check the second chat request; two plan statements conflict, open with two options (5.5.1).

2.3.18 1.13 4.3: `python/bootstrap.py` gives `hello` the fixed id 1 rather than `dispatch.id_next`; declined by 1.16 under decided items, the decline CONFIRMED, open.

2.3.19 1.16 4.9: `_document_read` in `python/main_loop.py` raises the decoder's own error, not `main_loop.seed_invalid`, for an invalid seed document; the code fails loud, and a plan edit is proposed.

2.3.20 1.18 4.10: two subprocess waits in `python/devtools.py` use the subprocess timeout rather than a named `WaitTimer`; the code meets the rule, and a plan edit is proposed.

2.3.21 1.24 4.5: `ts/substrate.ts` holds a copied SHA-256 (`HashStream`); moving it needs a public name in `API/ts/utility.d.ts`, proposed.

2.3.22 1.28 4.11: `line_bytes` in `ts/worker_ai.ts` copies a byte measure from `ts/queue.ts`; it needs a public `queue.line_bytes`, proposed.

2.3.23 1.29 4.3: `DomPort` in `ts/page.ts` builds `ui.input` and `ui.control_key` in short names in debug mode; it needs a constructor argument that `API/ts/boot.d.ts` would declare, proposed.

2.4 Severity 4 (completeness):

2.4.1 1.8 4.3: `test_create_twice` in `ts/test_substrate.ts` expects `substrate.db_exists` and `substrate.db_absent` where the Python twin expects `FileExistsError` and SQLite's error, a port difference no record states; a plan edit proposed.

2.4.2 1.14 4.5: `Store.db_restore` in `python/substrate.py` brings no cache files with a restored image; the maintainer's choice among three designs, the full one changing a public signature.

2.4.3 1.25 4.6: nothing tests `key_get` with no key set; the test needs a new export `key_clear`, proposed.

3 Findings partly fixed, 7

3.1 1.2 4.5: the PowerShell error swallowing is fixed except `if ($log_path_)` in `xsjs_util_write_log`, kept because `xsjs_status.ps1` writes no log by design; CONFIRMED.

3.2 1.2 4.22: `close_take` in `ts/wire.ts` is fixed for `ConsolePort` and declined for `WirePort`, where a check would replace the `wire.close_silent` fault; CONFIRMED.

3.3 1.3 4.4: the page's own `names_full` in `ts/page.ts` is gone; the `DomPort` half is 2.3.23.

3.4 1.6 4.5: the token timer rung of `python/test_browser.py` runs through a stopped ttyd, but the open timer rung stays on the stub server, as the `devtools` field it needed was REJECTED; its design is proposed (6.1.5).

3.5 1.19 4.4: every exception in `main` of `python/test_browser.py` names its rung, but a rung timer cannot fire inside a DevTools call, so a rung can overrun by one DevTools wait; it needs `ProtocolClient.deadline_set`, proposed.

3.6 1.24 4.3: constants of `ts/substrate.ts` moved into `constants` except the SHA-256 tables `round_table` and `hash_start`, which leave with 2.3.21.

3.7 1.24 4.7: `doc_put` counts versions exactly past 2^53, but `ref_split`'s `version` stays a `number` as the stub declares; proposed with 2.2.1.

4 Seams, rejections and remarks

4.1 Half applied seams: none (14.1.5). The snapshot chain (1.24_2, then 1.28_1: a `db.snapshot` held behind its database's waiting lines in `ts/worker_ai.ts`, and `db_load` in `ts/tools_browser.ts` unloading a loaded database first) is applied on all three sides. The open timer chain (1.19_1, 1.18_2, 1.34_3, 1.18_3: the field `PageEvents.requests_paused` and the rung through ttyd) was applied, REJECTED and backed out on both sides.

4.2 REJECTED fixes: five, each reworked by its owner and CONFIRMED by 1.40: the lost space after "bytes:" in `python/seed/prompt.json`; the writer-chose comments on four size constants of `python/test_echo_loop.py` and `python/test_main_loop.py`; `PageEvents.requests_paused` in `python/devtools.py`, removed; the comment on `settings_make` in `ts/test_settings.ts`, restored; and the `provider_key` leak through tty 1's debug overlay (1.28 4.3), whose `hello` display was removed.

4.3 Remarks of verifiers, not findings: past 2^53 `doc_head` in `ts/substrate.ts` can name a version `doc_put` did not write if sqlite3.wasm returns a Number; in debug mode a wire line's rendering can exceed `line_max` and stop the worker with `queue.entry_over`; the stub server's `SIGUSR1` in `python/test_browser.py` can land inside cleanup; `python/test_echo_loop.py`'s forked child runs the rest of the suite if it cannot open its ending file; `xsjs_util_get_command_text` would log the wrong value if a command used one of its own local names.

4.4 Stale lines in published reports: report 1.24 lists 1.24_2 as pending though it is applied; report 1.13 lists 1.13_1 as pending though 1.16 declined it; report 1.10 10.2 says `powershell/test_lint.ps1` has no byte order mark though it has one.

5 Open questions met, 87 after merging (annex section 1, the full text of each)

5.1 Naming, 5: whether `rung_` counts among a rung name's two words (137 names in `python/test_browser.py` and `python/test_wire.py`); whether `Test` counts among a test class name's two words, either reading breaking one set of classes; whether `non_ascii_check` and `Comment` in `python/test_posix.py`, which the plan expects, may break the two word rule; the name of the setting `verbose_level`; the page names of `python/test_browser.py`.

5.2 Imports, 6: whether the project rules should record the exception `from i18n import i18n`, used across the Python tree; whether `ts/test_substrate.ts` may import `jslb`, `utility` and `i18n` beside its module (admit the modules below it, or the strict rule); the same for the Python tests that import `jslb`, `mcp` and `dispatch` (as built, plain dictionaries in `python/test_dispatch.py`, or amend the rule); the same for `python/test_substrate.py` importing `jslb` (keep it, or compare a literal); the same for `ts/test_agent.ts` and `ts/test_script.ts` using real modules rather than doubles; whether the sibling imports inside the rung functions of `python/test_browser.py` may stay.

5.3 Comments, 1: whether every class field needs its own one line comment (`ts/mcp.ts`, `ts/provider_script.ts`, `ts/tools_browser.ts`), which tasks 1.24 and 1.27 read in opposite ways.

5.4 Debug name form, 2: whether the `fault` line of `ts/error_overlay.ts` may stay short; how `ConsolePort` learns the name form (reads `debug` itself as built, a constructor `full`, or the request's form).

5.5 Provider and compaction, 4:

5.5.1 Which provider the root "compact" of `python/test_browser.py` uses for `rung_compact_auto`: its own `provider.json` at the local stub, with the maintainer extending the one approved rung, or a scripted root that drops the check of the second chat request and proves it by a unit test of `prompt_build`.

5.5.2 Whether a forwarded `turn.append` may never compact, as built; where compaction runs; the compaction threshold.

5.6 Browser rungs, 12: the grain of a label and the smoke suites; the value of `blob_max` and the size of the large proofs; one root "level" shared by the debug and console rungs; two TAP documents per browser run; the fixed SAH pool and cache capacities; whether `probe.fault` should find the TAP `<pre>`; the categories of `python/test_browser.py`; whether `probe.wire_pending` may read `WirePort`'s private fields; whether the open timer rung uses `--max-clients 1` or `Fetch.enable` with a stopped ttyd (the latter needing `requests_paused`); whether the plan's acceptance of five `PageEvents` fields outside the stub extends to more; the sleep loop of `page_open` in `python/devtools.py`; and, seen and not filed, that the client of `python/test_wire.py` still sends `columns` and `rows` in its first message.

5.7 PowerShell, 7: the banner of `xsjs_install.ps1`, which stops `python/test_posix.py` before every stub comment finding; the byte order mark premise, false at the baseline as all eight PowerShell files have one; `powershell/test_lint.ps1` installing PSScriptAnalyzer with `Install-Module`, beside the project rule on package managers; `--srv-buf-size` as a literal or read from `srv_buf_size`; where `ttyd.log` lives; where the install's WSL step runs and which checkout it uses; the tests of the two official targets.

5.8 Formatter and whitelist, 12: `API/sql/*.sql` and a `.sql` lexer; whether `LICENSE.md` and `README.md` stay whitelisted; whether `python/pyproject.toml` is a source file; `html/engine.css` outside the whitelist; an 80 column comment in each of the three `html/*.html` templates; three long lines of `python/bootstrap.html`; an 80 column comment in `ts/test_tools_browser.ts`; the long string literals of `python/test_browser.py`; the hook of `html/test_engine.html`, split over three lines by the formatter, so `test_template_hooked` still fails; the formatter's changes to the templates, for the maintainer's review; Node's compile cache written outside `build/`; the other class B items of the posix tooling, each with its built option standing.

5.9 Stubs and API, 8: whether the server tool takes `source_put {name}` or `{name, text}`; accepting the built additions to `API/ts/unittest.d.ts`, `API/ts/tap_producer.d.ts` and `API/ts/queue.d.ts`; the stub rows of the console open reply, pending; `API/ts/boot.d.ts` saying `self.name` is undefined on the main thread, where the code tests `""`; `RefParts.version` a number or a `bigint` past 2^53; a throwing `sink_close` in `ts/jslb.ts` losing the first failure (wrap with `cause`, a stub addition `sink_abort`, or as built); the three designs for `db_restore`'s cache files; the other reports' proposed edits awaiting the maintainer.

5.10 Other, 30: `_cache_prune` in `python/substrate.py` skipping only `FileNotFoundError`; a tool's exception as a JSON-RPC -32603 with the server running on; `python/mcp_stdio.py` setting no `sys.pycache_prefix`; a verbose line before `settings_set`; `python/engine_turn.py` using `json.dumps` without the 2^53 check; reading `seq` before the lazy write lock; the canonicalizers' texts for small numbers, conditional, open only if declined; whether a window counts blob bytes only; testing the 55 byte SHA-256 padding boundary; both decoders reading an overflowing number as an infinity the encoders refuse; `_HELLO_ID` against `id_next`; the defaults as a whole; `-h` printing help to the pty; whether `universe.world` is UNIQUE; shell level 1 through the console; the form of the debug trace; whether only the console reads `verbose_level`; `i18n` for `python/page_build.py`; what a test compares for a platform `TypeError` with no `i18n` text; the `VACUUM` rowids (2.2.4); the `db_load` desync before the snapshot chain landed, now closed; the `overlay_install()` seam with no request from 1.18; whether tty 1's overlay shows the `hello` without its key (2.2.6); a debug rendering past `line_max`; the forked child of `python/test_echo_loop.py`; `chmod +x test_posix.sh`; the xterm `Terminal` options written from memory and the resize path (pin `@xterm/addon-fit` or delete `resize_send`); the TAP module layout and grammar; the two minute limit and the test infrastructure's options and modules; failfast for smoke and normal runs against the project rule of the first failure.

6 Proposed edits, 81 (annex section 3, the full text of each), 14 needing a maintainer's choice

6.1 Stubs under `API/`, 26 edits over 18 targets:

6.1.1 `API/python/dispatch.pyi`: `reply_make`'s `blobs` defaults to `None`.

6.1.2 `API/python/third_party_fetch.pyi`: declare `main`.

6.1.3 `API/python/tap_consumer.pyi`: reword the comment holding a `;` (severity 1).

6.1.4 `API/python/main_loop.pyi`: only the pending `loop_prepare`.

6.1.5 `API/python/devtools.pyi`: choice, `PageEvents.requests_paused` for the open timer rung through ttyd; and `ProtocolClient.deadline_set`, so a rung timer can fire inside a DevTools call.

6.1.6 `API/ts/*.d.ts`, 24 files: 86 comments to one line each and every `;` reworded (severity 1).

6.1.7 `API/ts/dispatch.d.ts`: the handler returns a finished reply line built with `reply_make`.

6.1.8 `API/ts/queue.d.ts`: the constructor comment says `queue_synchronous` is debug only; the `OwnerTable` comment follows the code; choice, accept the built `owner?` parameters, `sink_attach` and `VerboseBatch`; add `line_bytes`.

6.1.9 `API/ts/lines.d.ts`: the two `mcp` rows; the `HttpResponse` comment; four lane rows; choice, the rows `console.show` and `ui.show_reply`, showing the console view or opening tty 0 hidden.

6.1.10 `API/ts/tools_browser.d.ts`: `tools_register` gains `settings_get` and `full`.

6.1.11 `API/ts/provider.d.ts`: `full?` on `chat_request` and the image request; `key_clear`, for the tests only.

6.1.12 `API/ts/substrate.d.ts`: choice, `RefParts.version` a `bigint`, or a `number` documented as rounded past 2^53.

6.1.13 `API/ts/utility.d.ts`: export `HashStream`.

6.1.14 `API/ts/wire.d.ts`: choice, `ConsolePort(base_url, full)`.

6.1.15 `API/ts/console_view.d.ts`: choice, `open_is()`, with 6.1.9.

6.1.16 `API/ts/boot.d.ts`: `DomPort(container, full)`.

6.1.17 `API/ts/unittest.d.ts` and `API/ts/tap_producer.d.ts`: choice, accept the built additions.

6.1.18 The stub rows of the console open reply, pending.

6.1.19 Conflict: several of these proposed comment texts would themselves be refused by `comments_check` (two or more lines, a `;`, or a `^` or `_` outside a code span) and need rewording before they are applied.

6.2 `API/README.md`, 1: drop the removed planning document's name and say a file changes only by the maintainer.

6.3 `README.md`: none.

6.4 REVIEW_EXECUTION.md, 41: correct the nine statements that three PowerShell files lack a byte order mark; add the stub comments to the list of where a run stops; update test lists and counts (`TestLoading`, the audit's eleven refused and seven passed texts, `test_token_refused`); seven patch hunks, not eight; `provider.json` among the start's preconditions; the `jslb` edge cases now handled; the JSON-RPC notification wording; UTF-8 stdin and stdout; the transaction scope of `db.create` and `db.drop`; every form of `--main-loop`; `bootstrap.reply_blob` against `bootstrap.reply_unexpected`; the seed document's error; the wire test's root settings and streamed blobs; the wording of the timed waits; the browser run's state and root settings; the `self.name === "ai"` test; `ServerHold` and `worker.script_fetched`; the closing phase of `exit_done`; the two tsconfig lists; `worker.snapshot_reply`; the port difference of `test_create_twice`; and, tied to choices, the second `provider.json` of the root "compact" in three places, the `requests_paused` record, `ConsolePort` and `DomPort` signatures, and the `fault` line exception. The text proposed for the jslb number item contradicts its own reason and needs reconciling.

6.5 Code tied to stub edits, 13, made only if those stub edits are accepted: the `full` name form through `ts/tools_browser.ts`, `ts/provider.ts`, `ts/wire.ts` and `ts/page.ts`; `bigint` versions in `ts/substrate.ts`; `requests_paused` and the open timer rung through ttyd; `deadline_set`; `HashStream` moved into `ts/utility.ts`; `key_clear` and its test; the `console.show` request through `ts/tools_browser.ts`, `ts/page.ts` and `ts/console_view.ts`; `queue.line_bytes`.

7 Values owed to the testing phase, 90 (annex section 2, the full text of each)

7.1 Python, 25: a run of every changed Python suite, none of which has run, and pyright strict; `i18n` raising on none of its 1272 calls; one `python/test_posix.py` run once the banner question is answered; `RecursionError` on 1,000,000 nested arrays under Python 3.14.4; `cast(io.TextIOWrapper, …)` under pyright; argparse taking a trailing `--` in `python/bootstrap.py`; `SIGUSR1` interrupting the DevTools waits, cleanup included; `test_write_short` now that its name is merged.

7.2 TypeScript, 17: tsc over every edited file, the five the formatter rewrote included; the rung "stage 0: typescript suites" for every new test; the literal digests and sizes that reading cannot recompute; whether 120 s is enough for tsc; V8's messages.

7.3 Browser test, 25: a run of every rung, their seconds and their fit in two minutes; the debug name form on the live wire; `ServerHold` with a real `db_load`; the xterm.js layout; the media download timer and decode paths.

7.4 ttyd and Chrome, 12: Chrome's `error` on a failing `<object>`; allocating `blob_max` + 1 bytes and a 4 GiB peak; what a stopped ttyd absorbs; "echo blob_max" fitting 120 s with a 2 GiB hash, and its disk under `build/`; ttyd 1.7.7 spawning tty 1 from a first message without a size; the form of `DevToolsActivePort`; `/favicon.ico` requests or socket resets now ending the browser run; the ttyd install items (hashes, `chmod +x python/third_party_fetch.py`, a patch dry run).

7.5 PowerShell on Windows, 5: lint and a run of the seven changed files (8); WSL's exit codes for `wsl --list`; `Stop-Process` on an exited process; the C# relay compiling under `Add-Type`.

7.6 sqlite3.wasm, 6: its error texts; an INTEGER past 2^53 as a Number or a `BigInt`; two exports with no write between them being equal; `VACUUM` freeing pages and renumbering rowids; the test pool's 32 files.

8 PowerShell files owed to `powershell/test_lint.ps1` on Windows: `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_powershell.ps1`, `powershell/xsjs_util.ps1`, `powershell/en-US/i18n.psd1`.

9 Formatter: stable; `python3 python/reformat.py` ran twice, the second run changed nothing, and `tmp/review/format_1.diff` and `tmp/review/format_2.diff` are byte identical. Its changes, line wrapping only, none reverted: `python/test_browser.py`, `ts/test_http.ts`, `ts/test_mcp.ts`, `ts/test_substrate.ts`, `ts/test_verbose.ts`. Changes of 14.2.6: none; no stub under `API/`, `python/bootstrap.html`, `README.md`, `LICENSE.md`, `archive.sh` or `clean.sh` changed.

10 Screenshots: none, since nothing ran. Tasks 1.28, 1.29 and 1.30 changed what the page shows (tty 1's overlay, the image download timer, the console view's names), unseen.

11 A and B items of the requests the review served (REVIEW_EXECUTION.md 17.3, 17.4), unresolved, each with its question in 17.5 and option a) built:

11.1 A, unsatisfied without cause: none.

11.2 B, "decide what it really means to be done": each agent set its own definition of done, within the limits that it runs nothing, changes no public interface and decides no question left to the maintainer.

11.3 B, "things that are simply incorrect or mistakes that can be fixed": broken things that are open questions, such as the hooked template test, the mode of `test_posix.sh` and the lines the formatter cannot wrap, were listed and not fixed.

11.4 B, the earlier working rules departed from: more read only commands, the formatter's staging, and fragments that add, reword and remove. In the run, agents went further: most read with `cat`, `sed -n`, `awk` and `head`, several ran read only `python3 -c`, and tasks 1.14, 1.17, 1.18, 1.23, 1.25, 1.29, 1.32 and 1.40 each ran one `git show` of the baseline, which the plan forbids.

11.5 B, screenshots: none, since nothing runs.

11.6 B, the pool of eight at once: the plan writer's guard against HTTP 429; in the run the session limit still stopped all eight running agents at once (1.2), and the pool stayed at eight because the limit counts the session's total, not its rate.

11.7 B, "no external references": the plan names the tree it reviews and leaves the stubs under `API/` as the authority on public names; `API/README.md` still names a removed planning document (6.2).

11.8 B, "a self contained description": decisions carried over from the removed plans may have been missed, and a finding that revisits one shows what was searched so it can be declined.

12 The coordinator's notes

12.1 Phase 0 found the tree clean instead of the expected untracked plan and removals, because HEAD `85b7075` had committed them.

12.2 The coordinator first read 8.8.1 as launching a verifier only when every area of its group had ended; it was corrected at 22_1215 to the first area ended with an empty inbox. This delayed verifiers and changed no verdict.

12.3 The three-resumption limit was counted on Phase 2 drains only; the 8.9 resumptions after the 429 were counted apart.

12.4 Other departures recorded: 1.16 held two source locks at once, against one at a time; 1.11 wrote `used.txt` and `defined.txt` at the top of the shared scratchpad, possibly over another agent's files of those names.

12.5 A defect made during the review, the provider key on screen and in the logs in debug mode (1.28 4.3), was caught by verifier 1.39 and reverted before closing.

13 State of the tree: nothing committed. The formatter staged 86 files, the whitelisted files the review changed, as the project rules allow before a formatter run; five of them carry the formatter's unstaged changes on top (`MM`). `i18n/en-US.json` and `python/seed/prompt.json` are changed and unstaged, being outside the whitelist. The review's working files are under `tmp/review/`: 41 reports, `summary.md`, `open.md`, `maintainer_edits.md`, the two format diffs, the fragments and the resolved requests.

## Postmortem annex: digest of open questions, owed values, proposed edits and formatter

The digest below is copied whole from the helper agent's output; its numbering is its own, and its references to 1.x to 5.x are to its own items.


Baseline `85b7075`. Inputs: `tmp/review/open.md`, `tmp/review/maintainer_edits.md`,
`tmp/review/summary.md`, `tmp/review/report/1.41.md`. A source "1.7 10.2" is item
10.2 of report 1.7; "summary 3.3.18" is that item of `summary.md`; bare section
ids such as 11.3.3.15 are REVIEW_EXECUTION.md's. Reports 1.31 to 1.39 mostly
restate their owners' items and are listed as further sources. Report 1.22 10.1
records no question of its own.

1 Open questions met

1.1 Naming rules

1.1.1 Whether the prefix `rung_` counts among the two English words of a rung name (12.2.2.5, 12.2.4.5), on which 137 names in `python/test_browser.py` and `python/test_wire.py` depend (108 with one word after `rung_`, 29 with two, such as `rung_level_two`, `rung_error_first`, `rung_drain_poll`, `rung_compact_auto`, `rung_tool_failed`, `rung_refused_role` (12.5.5.6.5) and `rung_blob_max` (12.5.4.5, 11.11.4.11)), with the options of 1.7 10.1: count the prefix and rename each two-word name to one word after `rung_`, or do not count it and leave the names as they are (1.2 10.5, 1.5 10.2, 1.5 10.6, 1.6 10.1, 1.7 10.1, 1.17 10.3, 1.19 10.4, 1.35 10).

1.1.2 Whether `Test` counts among the two words of a test class name, which 12.2.2.5 settles only for `test_` methods, so that under either reading one set breaks 3.6: the Python classes of `Test` and one word (most of them), or the nine of `Test` and two (`TestByteOrder`, `TestIdNext`, `TestLabelBook`, `TestLexerName`, `TestLogAll`, `TestMainLoop`, `TestPowershellCheck`, `TestPowershellLexer`, `TestVectorsWrite`), with almost every TypeScript class being `Test` and two words (`TestValueStore`, `TestOwnerRouting`, `TestOwnerTables`, `TestOwnerTable`, `TestWorkerLines`, `TestPageHandlers`, `TestTurnRecorded`, `TestTurnNext`, `TestTurnShort`, `TestSoftLimit`) and a few `Test` and one (`TestDigest`, `TestOverlay`, `TestScroll`, `TestRun`, `TestErrors`, `TestSurface`, `TestPrompt`, `TestFailure`, `TestCompacted`), listed and not filed (1.2 10.6, 1.21 10.4, 1.22 10.2, 1.26 10.3, 1.28 10.4, 1.29 10.2, 1.38 10).

1.1.3 Whether the names `non_ascii_check` (three words, 11.2.3.3) and `Comment` (one word, 11.2.3.4, 11.2.3.6) in `python/test_posix.py`, which REVIEW_EXECUTION.md gives as expected, can stand against the two-word rule of 3.6, a decided item that breaks a rule and is therefore open under 5.3.5 (1.2 10.7, 1.10 10.6, 1.31 10.1).

1.1.4 The name of the setting `verbose_level` (4.8.4.19), listed with no options (1.13 10.3, 1.32 11.1).

1.1.5 The page names of `python/test_browser.py` (11.11.5.6), listed and not changed (1.19 10.2, 1.35 10).

1.2 Import rule

1.2.1 Whether the project rules should include the maintainer's exception `from i18n import i18n` (3.13, 12.2.4.4), which `API/python/i18n.pyi` calls "The one `from` import allowed" and which is used by all ten files of the 11.5 area, `python/jslb.py`, `python/test_jslb.py`, `python/stall_loop.py` and the two new test modules, the gap being reported and the rules left unedited (1.1 10.2, 1.2 10.4, 1.9 10.2, 1.12 10.4, 1.13 10.4, 1.16 10.5, 1.17 10.4, 1.31 10.1, 1.32 11.1).

1.2.2 Whether the test import rule (3.2.1, 2.11.2: a test module imports only its module and the harness) allows `ts/test_substrate.ts` to import `jslb` (`line_make`, `line_render`, `line_encode`, `payload_of`, `field_get`, `blob_make`), `utility` (`sha256_hex`, `json_text`, `base64_decode`, `utf8_encode`) and `i18n` beside `substrate` and `unittest` (11.16.3.21), with options a) the rule admits the modules that the tested module's API is built on, below it, or b) the strict rule, with the tests comparing raw line objects and constant digests, nothing chosen (1.8 10.1).

1.2.3 The same rule for the Python tests of candidate 11.5.6.7, where `python/test_dispatch.py` and `python/test_settings.py` import `jslb`, `python/test_mcp_stdio.py` imports `mcp`, both MCP tests read `API/mcp/tools.json` and every `python/test_engine_*.py` imports `dispatch` and `jslb`, with options a) as built, reading the rule as admitting the modules the API's types come from, b) `python/test_dispatch.py` builds its lines as plain `dict` literals and drops `jslb`, the rest unchanged, or c) amend the rule to name those modules (1.13 10.5, 1.32 11.1).

1.2.4 The same rule for `python/test_substrate.py`, which imports `jslb` for `test_nested_text` because the stored text is the wire encoder's (11.6.3.32), with options a) keep the import, or b) compare with a literal written from the encoder's key rule (11.4.3.5) and drop the import (1.14 10.2, 1.33 10.1).

1.2.5 The same rule for `ts/test_agent.ts` and `ts/test_script.ts`, which use `substrate.Store`, `queue.TaskQueue`, `provider_script.ScriptPort`, `provider.chat_request` and `chat_response`, `settings.ValueStore`, `jslb`, `dispatch`, `utility`, `verbose` and `i18n`, while 11.18.4.10 decides only the doubles (11.18.3.16), with options a) as in 1.2.2, or b) the strict rule, making every such module a double, nothing chosen (1.26 10.2, 1.38 10).

1.2.6 Whether the sibling imports placed inside the rung functions of `python/test_browser.py` (12.5.3.1.9, 11.11.5.4, 4.7.14) can stay, built option kept, listed with no options (1.5 10.4, 1.6 10.3, 1.19 10.2, 1.35 10).

1.3 Comment rules

1.3.1 Whether every class field must have its own one-line comment, for the uncommented fields of `Server`, `Client`, `ClientSet` and `ProtocolError` in `ts/mcp.ts`, `ScriptPort` in `ts/provider_script.ts` and the test double `PortDouble` (11.17.6.3), and for the `ToolContext` fields `store`, `tasks`, `provider_owner` and `settings_get` and the `constants` fields grouped under one comment in `ts/tools_browser.ts` (11.19.6.5), with options a) "one comment line per construct" (3.6, 12.2.2.7) asks for a one-line comment on every field, as task 1.24 read it, or b) the rule limits a comment to one line and asks for none per field, as `comments_check` in `python/test_posix.py` enforces and as the project rules' ban on documentation added only because some is missing implies, nothing added (1.25 10.1, 1.27 10.1, 1.37 7.1, 1.38 10).

1.4 Debug-mode name form D27

1.4.1 Whether the worker's `fault` line, built by `fault_report` in `ts/error_overlay.ts`, which by its stub depends on nothing and can run before the settings exist, may keep short names in debug mode against D27, an exception that 1.3 9.8 proposes to record in 12.3.3.7 (1.3 10.2; summary 3.3.10).

1.4.2 How `ConsolePort` in `ts/wire.ts` learns the debug name form, with D27 (one `names_full()`, whose answer `ts/wire.ts` is given) against the decided `ConsolePort(base_url, settings_get)` of 11.15.4.1, with options a) as built, the port reads `debug` itself, b) the constructor `ConsolePort(base_url, full)` of 1.23 9.1, or c) the request's form, as request 1.3_1 proposed, a) being built (1.23 10.1, 1.36 10.1; summary 3.3.9, 3.3.22).

1.5 Provider and compaction

1.5.1 Which provider the root "compact" of `python/test_browser.py` uses for `rung_compact_auto` (finding 1.7 4.4), with options 10.2.1, as built, the root's own `provider.json` at the local stub, the maintainer extending the approval of 4.8.7.4 to a second rung and the edits of 1.7 9.1 applied, or 10.2.2, a scripted root (`scripts_place`, `turn_compact_turns` 2, `_INPUT_PLAIN` twice) that checks the server's turns and the dispatched `turn.*` order and drops the check of the second chat request that 12.5.2.7.3.5 asks for, that request being proved instead by a unit test of `prompt_build` in `ts/test_agent.ts` (1.7 10.2; summary 3.3.18).

1.5.2 Whether a forwarded `turn.append` may never compact, since the TypeScript `operation_apply` in `ts/substrate.ts` applies it through `#turn_add` and `test_applied_exactly` asserts this (12.4.4.1, 11.16.4.24, 12.6.3.2.10), built but not confirmed by the maintainer (4.8.6.2) (1.4 10.1, 1.8 10.2, 1.24 10.3, 1.37 7.1).

1.5.3 Where compaction runs (11.7.5.4), built option standing, listed with no options (1.15 10.4, 1.33 10.1).

1.5.4 The compaction threshold (4.8.4.27), listed with no options (1.13 10.3, 1.32 11.1).

1.6 Browser test rungs

1.6.1 The grain of a label, the smoke-test suites and the default option (11.1.5.3, 11.1.5.4, 11.9.5.2, 12.5.3.1.5, 4.8.4.28), built as one suite per wire rung, every rung except "echo blob_max" and "echo 128 MiB" being `smoke-test`, `--smoke-test` alone being the default run, and the TypeScript modules running under the rung's `smoke-test` (1.5 10.5, 1.6 10.3, 1.9 10.1, 1.17 10.2, 1.20 10.3, 1.31 10.1).

1.6.2 The value of `blob_max` and the size of the large proofs at a window's edge (11.4.5.1, 4.8.4.8, 4.8.4.15, 11.9.5.1, 12.5.3.1.10), built option a) kept: a blob of `blob_max`, one byte more refused, and 128 MiB as one message (1.5 10.5, 1.6 10.3, 1.12 10.1, 1.17 10.1, 1.24 10.3, 1.32 11.1, 1.37 7.1).

1.6.3 Whether the debug and console rungs share one root "level", where "debug mode without feedback" runs (12.5.3.3.1, 11.11.5.2), a class B item with its built option standing (1.5 10.5, 1.6 10.3, 1.19 10.2, 1.35 10).

1.6.4 Whether a browser run writes two TAP documents (12.5.3.2.1), a class B item with its built option standing (1.5 10.5).

1.6.5 The fixed SAH pool, its slots and the cache capacities (12.5.3.5.7, 11.20.4.3), a class B item with options a platform port or larger constants (1.5 10.5, 1.28 10.2).

1.6.6 Whether `probe.fault` (`probe.fault_text`) in `python/test_browser.py` should find the TAP `<pre>` on the test page (11.11.5.5), which 1.5's design 4.2 leaves untouched (1.5 10.4, 1.19 10.2, 1.35 10).

1.6.7 The categories of `python/test_browser.py` (11.11.5.3), listed and not changed (1.19 10.2, 1.35 10).

1.6.8 Whether `probe.wire_pending` in `python/test_browser.py`, which `rung_drain_poll` relies on, may keep reading the private `socket` and `poll_id` of `WirePort` (12.5.5.4.8, 11.11.6.20), its writer's options a) to d) having been lost, the built option standing, and any other form needing a public name in `API/ts/wire.d.ts`, such as a read of the buffered amount and the poll (1.6 10.2, 1.19 10.3, 1.35 10).

1.6.9 Whether the "wire open timer" rung `rung_opening` in `python/test_browser.py` (12.5.5.4.10), which after 1.34_3 and 1.18_3 still aims at the stub server and not at ttyd, should use `--max-clients 1` or `Fetch.enable` with a stopped ttyd, the latter needing `python/devtools.py` to keep `Fetch.requestPaused` in the public `PageEvents` field `requests_paused` proposed in 1.18 9.2 (request 1.6_5) (1.18 10.6, 1.18 10.7, 1.35 10; summary 4.4).

1.6.10 Whether 4.5.26's acceptance of five `PageEvents` fields outside the stub `API/python/devtools.pyi` extends to further fields, which 1.34 reads from 4.3.7 as not, the point going to the maintainer if an owner decides otherwise (1.34 10.1).

1.6.11 The sleep loop of `page_open` in `python/devtools.py` (11.10.5.3, 4.7.14, D15), built option standing (1.18 10.3).

1.6.12 Seen and not filed: the client of `python/test_wire.py`, which drives the Python rungs, still sends `columns` and `rows` (`_COLUMNS`, `_ROWS`) in its first message, which 1.23 4.3 did not touch because it changed only the page's client (1.36 10.4).

1.7 PowerShell

1.7.1 The banner of `xsjs_install.ps1` (11.2.5.3, 11.3.5.3, 4.8.4.39), which stops `python/test_posix.py` before every comment finding in 1.2's item 4, built option kept (1.2 10.10, 1.10 10.3, 1.11 10.4, 1.31 10.1; see summary 3.1.1).

1.7.2 The UTF-8 byte order mark that `xsjs_status.ps1`, `xsjs_stop.ps1` and `powershell/test_lint.ps1` were said to lack (11.2.5.2, 11.3.5.2, 4.7.1), a premise that fails at the baseline because all eight PowerShell files start with `EF BB BF`, so the maintainer may close the point with the edits of 1.11 9.2 and 1.31 9.1, 1.10 10.2's statement that `test_lint.ps1` has no mark being stale (1.10 10.2, 1.11 10.3, 1.31 10.1; summary 5.1).

1.7.3 Met with no record: `powershell/test_lint.ps1` installs PSScriptAnalyzer with `Install-PackageProvider` and `Install-Module` when it is missing, beside the project rule on package managers, which binds what an agent runs, and the script runs only when the maintainer runs the Windows target (1.10 10.7, 1.31 10.1).

1.7.4 Whether `powershell/xsjs_util.ps1` keeps passing ttyd `--srv-buf-size 1048576` as a literal while the setting `srv_buf_size`, 1 MiB (4.8.4.10), governs only the runners' ttyd (11.3.6.5, 11.5.6.3, 12.1.5.5, request 1.1_2), with options a) as built, following 2.11.3, 11.3.3.5 and 11.3.3.15 ("read no setting"), or b) `xsjs_util_get_ttyd_options` reads `srv_buf_size` from the `settings.json` it copies, against 11.3.3.15 (1.11 10.1, 1.31 10.1; summary 3.3.3).

1.7.5 The location of `ttyd.log` under `%LOCALAPPDATA%` (11.3.5.1, 4.7.2), built option kept (1.11 10.2, 1.31 10.1).

1.7.6 Where the install's WSL step runs and which checkout it uses (11.3.5.4, 11.3.5.5), built options kept (1.11 10.4, 1.31 10.1).

1.7.7 The tests of the two official targets, `powershell/test_powershell.ps1` and `test_posix.sh` (11.3.5.6), built option kept (1.11 10.4, 1.31 10.1).

1.8 Formatter and whitelist

1.8.1 Whether `API/sql/*.sql` joins the whitelist with a `.sql` lexer (12.1.4.1, 11.2.5.12) (1.1 10.1, 1.10 10.4).

1.8.2 Whether the lines `LICENSE.md` and `README.md` stay in `python/reformat_whitelist.txt` (11.2.5.14, 4.7.14), where they are checked only by `mdformat --check`, which rewrites nothing (1.1 10.3, 1.10 10.5, 1.31 10.1; 1.41 3.3).

1.8.3 Whether `python/pyproject.toml`, the one TOML file, outside the whitelist and with no lexer, is a source file (12.1.5.4), since 12.1.2.13 counts it among the recorded exclusions "which are not misses" while 11.2.6.4 calls it a "recorded miss", with `.gitignore`, `.gitattributes` and the coordinator's `.vscode/settings.json` in the same position, listed and not requested (1.1 10.5, 1.10 10.5).

1.8.4 Whether `html/engine.css` may stay outside the whitelist, given 3.10 and 12.1.2.13, which keep `.css` out for want of a lexer (4.7.14, 4.9.4.1) (1.29 10.1).

1.8.5 Lines over 79 columns that the formatter cannot wrap (12.2.4.6, 11.10.5.2, 11.2.6.8): the comment "The AI worker runs the text of each `data-worker` script, in order." at 80 columns in each of the three `html/*.html` templates, which 1.41 places at line 21 of `html/engine.html`, 29 of `html/test.html` and 22 of `html/test_engine.html`, produced by the formatter's re-indent and not wrapped by hand (1.2 10.8, 1.18 10.2, 1.41 10.2).

1.8.6 Lines over 79 columns that the formatter cannot wrap: three lines of `python/bootstrap.html` (81, 82 and 86 columns), held by D22 (1.41 10.2).

1.8.7 Lines over 79 columns that the formatter cannot wrap: the comment "A snapshot streamed to the cache opens from its handle, sink digest kept." in `ts/test_tools_browser.ts`, 80 columns (6.11) (1.2 10.8, 1.27 10.2, 1.37 7.1).

1.8.8 Lines over 79 columns that the formatter cannot wrap: the string literals of `python/test_browser.py`, six by 1.2 and five after 1.19's rename of its 4.11 (`self.postMessage({ header: ...` in `_PROBE_KIT`, "the page faulted where", "a click on Reload, whose onclick", "values over overflow_bytes were written", "SELECT name, title, player, world FROM universe"), owned by task 1.19 and covered by request 1.2_11 (12.5.4.1, 11.11.5.1) (1.2 10.8, 1.5 10.1, 1.6 10.3, 1.7 10.3, 1.19 10.1, 1.35 10).

1.8.9 The hook of `html/test_engine.html`, which the formatter split over three lines (prettier now reports the file unchanged), so that `test_template_hooked` in `python/test_page_build.py`, which counts the one-line `<script data-worker>test_hook.engine_run();</script>` (`_HOOK_SCRIPT`), still fails, with options a) to c) recorded in 11.10.5.1 and not restated in the inputs, nothing chosen (4.7.12, 4.9.6.3, 11.12.5.1) (1.18 10.1, 1.20 10.1, 1.41 10.1).

1.8.10 The formatter's changes to the templates, which 1.18's item 3.12 lists for the maintainer's review (11.10.4.12) (1.18 10.4).

1.8.11 Node's compile cache, which prettier writes in the system's temporary directory outside `build/` (11.2.5.11), a class B item left as built (1.10 10.4, 1.41 3.2, 1.41 10.3).

1.8.12 The other class B items of the posix tooling, 11.2.5.4 to 11.2.5.13 (1.8.1 and 1.8.11 among them), each with its built option standing, not restated in the inputs (1.10 10.4, 1.31 10.1).

1.9 Stubs and API

1.9.1 Whether the server tool takes `source_put {name}`, as the plan named it, or `{name, text}` (`required: ["name", "text"]`), as `API/mcp/tools.json` and `python/engine_system.py` take it, a difference that an earlier review recorded and never scheduled (12.1.5.2) (1.1 10.4).

1.9.2 Whether the maintainer accepts the built additions to `API/ts/unittest.d.ts` and `API/ts/tap_producer.d.ts` (4.5.10, 4.5.33, 4.5.34) and to `API/ts/queue.d.ts` (4.5.5, edit 1.22 9.1), see 3.1.8.3 and 3.1.17.1 (1.20 10.4, 1.36 10.3).

1.9.3 The stub rows for D23's `ConsoleOpenReply` (4.6.9.12), proposed and not applied, awaiting the maintainer (1.30 10.2).

1.9.4 The words in `API/ts/boot.d.ts` saying that `self.name` is "undefined on the main thread" (4.6, 11.20.4.4), listed with no options (the edit 1.20 9.1 of 11.12.3.13 records the code's `self.name === ""` on the UI thread) (1.28 10.3).

1.9.5 Whether the `version` from `ref_split` (`RefParts.version` in `API/ts/substrate.d.ts`, `version_find` in `ts/substrate.ts`) stays a JavaScript number past 2^53, with options a) a number, documented as in edit 1.24 9.2, or b) a `bigint` (edit 1.4 9.1) or the literal's text, either of which changes a public type (1.24 10.2, 1.37 7.1; summary 3.2.1, 4.7).

1.9.6 Whether a `sink_close` that throws inside `#stream_shut` of `bytes_feed` in `ts/jslb.ts`, called from the `catch`, may replace the fault and so lose the first failure, decided as built (11.4.4.3) but against the project rule of the first failure (candidate 11.4.6.6, whose first half no longer holds because the pool `sink_close` of `CacheFiles` in `ts/substrate.ts` frees a short blob), with options a) wrap with `cause` in `ts/jslb.ts` under a new `jslb.` name, b) the stub addition `sink_abort` (6.2), left unbuilt by 4.5.40, or c) a sink that drops a blob closed after a failure, now built on the sink side, Python's `finally` keeping the fault as `__context__`, nothing chosen (1.12 10.3, 1.32 11.1).

1.9.7 Which of three designs, not restated in the inputs, brings a restored database image's cache files back in `Store.db_restore` of `python/substrate.py` (1.14 4.5), the full design changing a public signature (6.2) (1.14 10.3, 1.33 10.1; summary 3.4.2).

1.9.8 The proposed edits of other reports that these reports found awaiting the maintainer, all in section 3: `ProtocolClient.deadline_set` in `API/python/devtools.pyi` (1.19 9.3), the 12.1.2.15 edit on the harness modules left out of `ts/tsconfig.json` (1.1 9.6, which matches the code), and 1.27 9.1 (with its choice of showing the view) and 9.2 (1.18 10.6, 1.27 10.3, 1.37 7.1).

1.10 Other

1.10.1 Whether `_cache_prune` in `python/substrate.py` may skip only `FileNotFoundError` (12.2.4.1, 11.6.5.1), unchanged (1.2 10.1, 1.14 10.1, 1.33 10.1).

1.10.2 Whether a tool's exception becomes a -32603 JSON-RPC response with the stack in `data` while the server keeps running, in `Server.message_handle` of `python/mcp.py` and `failure_make` of `ts/mcp.ts` (12.2.4.2, 11.5.5.2, 11.7.5.3), built option standing, together with its TypeScript record 12.4.4.4, under which a TypeScript tool that submits and throws meets `queue.wait_missing` (1.2 10.2, 1.3 10.1, 1.4 10.4, 1.13 10.2, 1.15 10.3, 1.32 11.1, 1.33 10.1).

1.10.3 Whether `python/mcp_stdio.py`, which sets no `sys.pycache_prefix`, should set one (12.2.4.3, 11.5.5.1, 4.7.3) (1.2 10.3, 1.13 10.1, 1.32 11.1).

1.10.4 Whether a verbose line written before `settings_set` is ever wanted, given that `LineRing.log` in `ts/verbose.ts` reads `verbose_ring` through `settings_get` before the first line and throws `settings.not_set` (12.4.4.2, 11.13.5.1, 11.20.5.1, 4.7.13), the page writing its first verbose line after `settings_set` (1.4 10.2, 1.21 10.1, 1.28 10.1, 1.29 10.4).

1.10.5 Whether `python/engine_turn.py` may build its canonical JSON with `json.dumps` without the 2^53 check (12.4.4.3, 4.7.5, 11.7.5.1) (1.4 10.3, 1.14 10.4, 1.15 10.1, 1.33 10.1).

1.10.6 Whether `python/engine_sql.py` and `python/engine_turn.py` may read `seq` before the lazy write lock (4.7.6, 11.7.5.2), a point that also names `python/substrate.py` (1.14 10.4, 1.15 10.2, 1.33 10.1).

1.10.7 Conditional: 1.4's finding 4.1, the canonicalizers' texts for numbers such as 0.00001, 1e-7 and -1.5e-7, becomes open if task 1.24 declines it under 11.4.4.33, and section 3 of the summary lists no unfixed 1.4 4.1 (1.4 10.5).

1.10.8 Whether a window counts blob bytes only (4.8.4.7), built option kept (1.12 10.2, 1.32 11.1).

1.10.9 Whether to test the untested 55-byte SHA-256 padding boundary (4.7.15, 11.13.5.2), with options a) and b), b) adding a digest to `python/vectors_make.py`, nothing chosen (1.12 10.5, 1.21 10.2, 1.32 11.1).

1.10.10 Noted with no record: both `jslb` decoders read a number token that overflows a double, such as `1e400`, or in Python an integer token of 310 to 4300 digits, as an infinity, which the encoders then refuse to write (`jslb.number_refused`), and no statement covers this (1.12 10.6, 1.32 11.1).

1.10.11 Whether `python/bootstrap.py` keeps the constant `_HELLO_ID` (decided by 11.8.3.14 and 11.8.3.10) against seam 11.5.7.1, which says bootstrap calls `id_next` once per request it sends, given that a later server request taking `dispatch.id_next` would restart at 1 (12.3.2.3) and collide with `hello`'s id, request 1.13_1 having been declined by 1.16 (1.13 10.6, 1.16 10.4, 1.32 11.1; summary 3.3.19).

1.10.12 The defaults taken as a whole (4.7.11; D1, D13 and D21 used by 1.15), built options standing (1.15 10.5, 1.33 10.1).

1.10.13 Whether `-h` prints help to the pty and exits 0 (11.8.5.1), as the argparse parser of the 11.8 area does, built option standing (1.16 10.1).

1.10.14 Whether `universe.world` should be UNIQUE, the built hard error `agent.universe_ambiguous` in `ts/agent.ts` on two `universe` rows of the current world standing and a UNIQUE `world` being the other option (11.8.5.2, 11.18.5.1, 4.7.4) (1.16 10.2, 1.26 10.1, 1.38 10).

1.10.15 Whether the console passes shell level 1 through (4.8.4.20, 12.5.3.6.6, 11.8.5.3), listed with no options (1.5 10.5, 1.13 10.3, 1.16 10.3, 1.32 11.1).

1.10.16 The form of the debug trace and its header JSON (4.8.4.21, 12.5.3.3.2, 11.8.5.3), listed with no options (1.5 10.5, 1.13 10.3, 1.16 10.3, 1.32 11.1).

1.10.17 Whether only the console reads `verbose_level` (4.8.4.22, 11.8.5.3), listed with no options (1.16 10.3).

1.10.18 Nothing decides `i18n` for `python/page_build.py`, which writes f-strings, as 2.11 counts it a tool and 3.9 says tools do not use `i18n` (11.10.3.22) (1.18 10.5).

1.10.19 What a test compares for a platform `TypeError` that has no `i18n` text, such as a write to a frozen object, which 3.5 does not say, the tests keeping `assertRaises(TypeError, ...)` (1.21 10.3, 1.36 10.2).

1.10.20 Whether the `VACUUM` of `Store.db_compact` in `ts/substrate.ts`, which may renumber rowids in the browser's copy only (4.9, 11.16.6.9, 4.2.9), is a) accepted, b) forwarded to the server, or c) refused for such tables, against 3.14, none chosen (1.24 10.1, 1.37 7.1; summary 3.2.4).

1.10.21 Closed: until request 1.24_2 landed, a `db_load` whose snapshot overtook the database's waiting lines opened a copy behind the server, so the next write was a desync, but 1.37 4.1.1 closed this because 1.24_2 is applied on every side (1.24 10.4, 1.37 7.1; summary 1.5.1, 5.1).

1.10.22 The seam of 11.20.7.1 (`overlay_install()` running from the last script) has no request from task 1.18 yet (1.28 10.5).

1.10.23 Whether tty 1's debug overlay shows the `hello`, with 11.20.3.21 (the tap shows "each line it passes, in both directions", candidate 11.20.6.1) against 2.10.1 and 11.20.3.8 (the provider key stays in the worker's memory), with options a) the `hello` is not shown, as built and kept by 1.39_1, or b) the `hello` is shown, rendered from a copy without its `provider_key` field, with a test that the note holds no key (1.28 10.6, 1.39 10.2; summary 1.4.5, 3.2.6).

1.10.24 What a debug-mode rendering of a wire line in `ts/worker_ai.ts` becomes past `line_max`, since every rendering goes into a verbose entry bounded by `line_max`, so that a large legal wire line faults with `queue.entry_over`, while 11.20.3.21 asks for that rendering and no record says what happens past the bound (1.39 10.1; summary 5.2).

1.10.25 Observed and not filed: in `_child_end` of `python/test_echo_loop.py`, if the child's own `open` of the ending file fails, the forked child keeps running the rest of the suite, because that `open` stands outside the `try` that precedes the `SIGKILL`, while `python/test_stall_loop.py` uses `finally` for its kill (1.34 10.2; summary 5.2).

1.10.26 Whether `test_posix.sh` gets `chmod +x`, its mode still being 100644 (11.2.5.1) (1.10 10.1, 1.31 10.1).

1.10.27 The xterm `Terminal` constructor options in `ts/console_view.ts`, written from memory, and the resize path, with options pin `@xterm/addon-fit` or delete `resize_send`, now that `ConsoleView.rows_fit` reaches `resize_send` through `terminal.resize` and its `onResize` (12.5.4.6, 4.7.8, 11.22.5.1), a question that affects what the page shows (11.21.5), nothing chosen (1.5 10.3, 1.29 10.3, 1.30 10.1).

1.10.28 The TAP module layout and the TAP line grammar (11.1.5.1, 11.1.5.2, 4.8.4.1, 4.8.4.2, D12), built options standing (1.9 10.1, 1.20 10.2, 1.31 10.1).

1.10.29 The two-minute limit, the options and defaults, the place of `alarm_plan` (now `python/category.py`) and the test modules of the test infrastructure (within 11.1.5.1 to 11.1.5.9), built options kept (1.9 10.1, 1.31 10.1).

1.10.30 Whether a smoke-test run should end at its first failure while a `normal-test` run without `--failfast` records every failing test of a module, which `tap_check` in `python/test_browser.py` reports, and whether the browser runs may set failfast to false (12.2.4.7, 12.5.3.2.2, within 11.1.5.1 to 11.1.5.9), given the project rule of the first failure, built option kept (1.2 10.9, 1.5 10.5, 1.9 10.1, 1.31 10.1).

2 Values owed to the testing phase

2.1 Python (items covering both languages are placed here)

2.1.1 That `i18n` raises on none of its literal calls at run time in either language, since the argument counts were matched to the placeholder counts only by pattern (1199 calls by 1.1, 1272 by summary 1.2 against the merged `i18n/en-US.json`) (1.1 11.2).

2.1.2 One run of `python/test_posix.py` once the banner question (1.7.1) is answered, to confirm the order of its stops at 1.2's findings 4.1, 4.3, 4.10, 4.14 and 4.28 as read (1.2 11).

2.1.3 The texts of 1.4's finding 4.1, from a run of both canonicalizers, Python and TypeScript, on 0.00001, 1e-7 and -1.5e-7 (1.4 11.1).

2.1.4 The TAP identity of 3.6, from the stage 0 runs of both runners (1.4 11.2).

2.1.5 A run of `python/test_i18n.py` with its new message comparisons and `TestLoading`, a run of `python/test_all.py` with `main(arguments)`, every suite's measured seconds, tappy compatibility and a pyright strict run (11.1.4.24) (1.9 11.1, 1.31 11.1).

2.1.6 A run of `audit_probe` in `python/test_posix.py` with the three new probes and the new pattern, of `test_token_refused`, and of `python/test_test_posix.py`, none of which has run (1.10 11.1, 1.31 11.1).

2.1.7 The formatter's stability on 1.10's two edited files, which 1.41 4.3 answers for every whitelisted file in a linux row (section 4.1 here) (1.10 11.2).

2.1.8 A run of `test_posix.sh` by the maintainer (11.2.4.15, 11.2.4.19) (1.10 11.3).

2.1.9 A run of `python/test_third_party_fetch.py` with its two new tests (1.11 11.4, 1.31 11.1).

2.1.10 Every suite of the 11.4 area (`jslb` and the vectors) run in both languages, with every changed test of 1.32's group (1.12 11.1, 1.32 9.3).

2.1.11 That `_DEEP_NESTING`, the 1000000 nested arrays of `test_nesting_deep` in `python/test_jslb.py`, raises `RecursionError` from the C JSON scanner of Python 3.14.4 under the test driver's stack and does not crash (1.12 11.2, 1.32 9.1).

2.1.12 The two new error vectors through both decoders, whole, by bytes and split, and `test_number_long` in `ts/test_jslb.ts` (1.12 11.3).

2.1.13 Stage 3 under `python3 -X dev`, stage 4's rungs and a clean pyright (11.5.3.29) (1.13 11.1).

2.1.14 The changed MCP tests, none run (`test_process_wide`, the process tests under `PYTHONIOENCODING=ascii` and the four reworded assertions), and pyright strict on `cast(io.TextIOWrapper, stream).reconfigure(...)` in `python/mcp_stdio.py`, which relies on typeshed's default type argument (1.13 11.2, 1.32 9.2).

2.1.15 The substrate suites under `python3 -X dev` (11.6.3.35) with the fragments merged, including the new start of `test_recorded_replay` and the desync message, so far confirmed by reading only (1.14 11.1, 1.33 11.1).

2.1.16 The behaviours of Python's SQLite in 11.6.4.20 and the texts of 1.14's item 3.17 (1.14 11.2).

2.1.17 Every test of 1.15's nine modules, the new ones included, and a clean pyright (11.7.3.24) (1.15 11.1).

2.1.18 Whether the argparse parser of `python/bootstrap.py` accepts a trailing `--` (`--root r --`), in which case the appended `--main-loop` lands after it and `system.restart` is refused, a client's `--url-arg --` included, the fix then being to put the option before a trailing `--` in `_argv_make`, with nothing built until a run shows the problem (request 1.15_1) (1.15 11.2, 1.16 11, 1.33 11.1).

2.1.19 A run of `test_write_short` in `python/test_engine_tap.py`, which could not pass before `engine_tap.write_short` was merged and now finds its name (summary 1.2) (1.15 11.4).

2.1.20 Every test of 1.16's findings 4.3, 4.6 and 4.8, written but not run, the 0.2 s of `_RUNNING_SECONDS`, and `exit_on_error=False` on Python 3.14.4 (11.8.4.8) (1.16 11).

2.1.21 The error text of the `json` module for `{"a": ` (1.18 4.8) (1.18 11.3).

2.1.22 The Unconfirmed values of 11.10.4.10 and 11.10.4.19, and every test of the 11.10 area (`python/devtools.py`, `python/page_build.py`), none of which has run (1.18 11.5).

2.1.23 That a `SIGUSR1` sent by `pthread_kill` interrupts the main thread's DevTools and `select` waits in `python/test_browser.py`, with PEP 475 raising the handler's exception, together with 1.35's remark that the stub server's `SIGUSR1` can arrive during cleanup (1.19 11.3; summary 5.2).

2.1.24 Pyright strict on `python/test_browser.py`, including the read-only `events` property and the bare `contextlib.ExitStack` annotations (1.19 11.4, 1.35 11).

2.1.25 Every test and rung named in 1.34's verdicts, none of which has run (1.34 11).

2.2 TypeScript and tsc

2.2.1 That tsc accepts every `Settings` literal of the TypeScript tests (the excess property check), every type-only reference of 3.10 and the signatures that 1.1 compared by text (1.1 11.1).

2.2.2 Every test of `ts/test_substrate.ts` in the rung "stage 0: typescript suites", including the new `test_create_failed`, `test_ref_database`, `test_snapshots_apart`, `test_value_held`, the three stale tests, `test_load_pending`, `test_version_wide` and `test_numbers_small`, and 1.37's runs of both suites with every new test (1.8 11.1, 1.24 11.1, 1.37 8.1).

2.2.3 The literal digests and sizes in `constants` that reading cannot recompute (12.6.5.3): `world_sha256`, `scene_sha256`, `image_sha256`, `image_size` (88), the PNG of `image_base64` (the reference PNG's values) and the step script's 319 bytes (4.9.6.5), in `ts/test_tools_browser.ts`, `ts/test_substrate.ts` and the 1.25 modules (1.8 11.2, 1.24 11.3, 1.25 11.2, 1.27 11.2).

2.2.4 The SHA-256 `1e2806a1...` of `constants.enter_result` in `ts/test_agent.ts`, compared live with the double's `kv_put` digest of the text `/castle_gatehouse/scene/arrival/1`, the same constant standing in `ts/test_substrate.ts` and `ts/test_tools_browser.ts` and its `seq` 2 holding by reading (D1) (1.26 11.2).

2.2.5 The step script's digest, if a constant for it is wanted back (11.18.4.13) (1.26 11.3).

2.2.6 Whether 120 s is enough for tsc (1.18 4.3) (1.18 11.3).

2.2.7 tsc over 1.20's four edited files: `diagnostics?: string` after a defaulted parameter, the tuple `string | undefined`, and `#failfast` (1.20 11.1).

2.2.8 The rung "stage 0: typescript suites" for the new message comparisons of `test_unittest` (the JSON texts, with `Uint8Array` as `{"0":1}`) and for "diagnostics: undefined" in `test_tap_producer` (1.20 11.2).

2.2.9 V8's stack header for `SkipTest` (11.12.4.14) and the assignability of 11.12.4.25 (1.20 11.3).

2.2.10 Every test that 1.21 edited, run once under tsc and in the page (1.21 11).

2.2.11 tsc over the edits of 1.25 and 1.26 (1.38's ten files), and the rung "stage 0: typescript suites" with `test_results_unmatched`, `test_list_permit`, `test_dotted_names`, `test_value_uncarried`, `test_prompt_typed` and the changed `test_prompt_invalid` of `ts/test_agent.ts`, `ts/test_script.ts` and the three 1.25 modules (1.25 11.1, 1.26 11.1, 1.38 11).

2.2.12 That V8's BigInt message is the same with and without `number_check` as the replacer (1.38 11).

2.2.13 A run of the `ts/test_tools_browser.ts` suite with `test_debug_off`, whose name `tools_browser.debug_off` the merge of 14.1.1 has added (summary 1.1) (1.27 11.1).

2.2.14 The two test modules of 1.30's area (console view and media), which have never run (1.30 11.4).

2.2.15 tsc over 1.36's 18 changed files (`readonly #failfast`, the `as` casts, the `Map` of `test_json_refused`), and the rung "stage 0: typescript suites" for every new or changed expected text (1.36 11.1, 1.36 11.2).

2.2.16 The new TypeScript tests of 1.39's three areas, `TestQueueMode`, `test_snapshot_behind`, `test_snapshot_passed`, `test_note_logged`, `test_image_held`, `test_script_fetched` and `test_script_held`, checked by reading only with nothing compiled, `test_hello_shown` having since been removed (summary 1.4.5) (1.28 11.1, 1.39 11.1).

2.2.17 tsc and the suites over the five files the formatter rewrote (`python/test_browser.py`, `ts/test_http.ts`, `ts/test_mcp.ts`, `ts/test_substrate.ts`, `ts/test_verbose.ts`), whose changes are white space only (1.41 11.2).

2.3 Browser test (rungs of `python/test_browser.py` in Chrome)

2.3.1 The name form of every line on the live wire and lanes in debug mode, `hello`'s full form being Unconfirmed (12.3.3.7), and that the worker's `settings.set` arrives in full names in debug mode, so that `settings.put`, `ai.say`, `ai.click`, `dom.choice` and the media copies follow it (1.3 11.1, 1.29 11).

2.3.2 A server line over `line_max` reaching the page (3.16), and a second `hello` after `system.restart` ending in `wire.hello_twice` (D9) (1.3 11.2).

2.3.3 Dotted tool names at the first real provider run (D28) (1.3 11.3, 1.25 11.2).

2.3.4 In `rung_worker_hang`, the worker's suite must still be running when `worker_pause` lands, one poll of `_POLL_SECONDS` after its first TAP line, because a suite that ends first leaves the cut document well formed and fails the rung (1.5 11.2).

2.3.5 In `rung_kill_between` ("stage 6: kill between file and row"), the second worker opens the sync access handles right after `first.terminate()`, which releases the first worker's handles asynchronously (1.5 11.3, 1.8 11.1).

2.3.6 In `rung_server_trace`, the ring of `verbose_ring` (1000) lines must hold every line since `hello` on the root "level", among them the debug-mode `verbose.put` notices of the start and of two turns, since a full ring fails `trace_check`; also the close codes that `rung_cycle` prints (3.7.1) (1.5 11.4).

2.3.7 In `rung_exit`, the dropped text is typed after a turn, which does not order the console socket's close, and a `console.exit` the UI has not yet handled leaves `disableStdin` false; also the designs of 3.7.3 (1.5 11.5).

2.3.8 The fit of the labels in 2 minutes (12.5.3.1.5) and every rung's seconds (11.11.4.4) (1.5 11.6, 1.6 11.3, 1.7 11.1, 1.17 11.3, 1.19 11.5).

2.3.9 The trace event names of 12.5.3.4.12, the synchronous runs being identical, and the disk and OPFS use of 12.5.3.1.11 (1.6 11.3).

2.3.10 A run of every stage 8 rung (1.7 11.1).

2.3.11 Whether rungs one poll apart settle the tail of a turn, for request 1.7_1 (1.7 11.2).

2.3.12 Whether any UI task runs between `long_task_ms`, 5 ms, and the long task observer's 50 ms floor, a range the observer cannot see (1.7 11.3).

2.3.13 The root "main"'s turn count under 64 (12.5.3.7.8), and the 1 s provider timeout of the root "compact" against the local stub (1.7 11.4).

2.3.14 The measured `blob_max` (`rung_blob_max`, 11.4.4.8) and the shipped `blob_max` (11.9.4.20) (1.12 11.4, 1.17 11.3).

2.3.15 The browser rungs of 11.13.3.36: a throw in the xterm.js script or late in the bundle reaching the `<pre>` screen (1.21 4.2), and a worker throw after `error_overlay` loads showing only the posted stack, never the page's `onerror` text (1.21 4.1, `rung_posted`) (1.21 11, 1.36 11.3).

2.3.16 The rungs of 11.14.3.50: the scheduling outside synchronous mode, a `ThreadPort` across a real worker, `verbose.put` forwarded unchanged from the UI through the AI worker to the server, a sleep woken by two replies in either order over real ports, one run identical twice in synchronous mode, the UI stress test (`long_task_ms`, a soft target that is measured) with no synchronous network load, `sink_attach` on the live `verbose`, a handler's throw reaching `error_overlay`, and the hello relay (1.22 11.1).

2.3.17 `queue.message_invalid` and `queue.message_error`, whose messages arrive on a `ThreadPort` only in a later macrotask, and `queue.buffer_shared`, which needs shared memory (cross origin isolation) and whose token the audit refuses in a test module, each reachable only in a browser run (1.22 11.2).

2.3.18 Seen and not filed: with the live `debug` true, the trace that `test_run_twice` and `test_trace_gated` write through `verbose.log` reaches the AI worker's live ring and goes to the server's `_verbose` as `verbose.put`, which no test reads, by the design of 11.14.3.46 (1.22 11.3).

2.3.19 The http chain of 1.23's finding 4.11 and the console read bound of its 4.8 inside the page, and everything of 11.15.3.39 (1.23 11.2, 1.36 11.4).

2.3.20 The stage 7 proofs of the tool, `console_run`'s output and its timeout on `sleep 600` and on Deny, as rungs of task 1.19 (11.19.3.15) (1.27 11.3).

2.3.21 The `ServerHold` order with a real `db_load` and waiting lines, the hello in tty 1's overlay (no longer shown after 1.39_1, summary 1.4.5), the wire rendering in `_verbose`, the Script fetch after a `_files` restore, and the Unconfirmed items of 11.20.4.19 (1.28 11.1).

2.3.22 The items of 1.29's 3.12, the rungs of 11.21.3.21, `TestLayout`'s column and the console rows fitted above the band with xterm.js, and the 120 s media download timer on a real download (1.29 11).

2.3.23 Every proof of 11.22.3.16, as browser rungs of task 1.19 (1.30 11.1).

2.3.24 That xterm 5.5.0's `.xterm-screen` has its height when `open` returns, which `terminal_place` divides by the rows, that the UMD script defines the global `Terminal`, and the constructor options (11.22.5.1) (1.30 11.2).

2.3.25 The decode and download paths that no unit test starts: `createImageBitmap`, the abort of `fetch` by the timer, a status outside 200 to 299, and a real `ImageBitmap` closed on eviction (1.30 11.3).

2.4 ttyd and Chrome

2.4.1 That Chrome fires `error` at an `<object>` whose `data` answers 404 (1.5 4.1) (1.5 11.1).

2.4.2 Whether Chrome allocates the `Uint8Array` of `blob_max` + 1 bytes that `rung_over` (`probe.pattern`) and `rung_put_largest` (`probe.words_make`) build before the refusal, and the page's peak memory in `rung_round`, about 4 GiB (1.6 11.1).

2.4.3 How much the path from Chrome to a stopped ttyd absorbs, which decides whether the drain rungs hold frames back (1.6 4.3) (1.6 11.2).

2.4.4 The items of 11.3.4.14: the three `sha256` values, `chmod +x python/third_party_fetch.py` (still not executable), one `patch -p1 --dry-run`, the ttyd build packages, and stopping the old ttyd by hand once (1.11 11.1).

2.4.5 A restart through ttyd from `--main-loop=x` and from an abbreviation, proving 1.15's 4.1 end to end, and the end-to-end proofs of 11.8.3.46 that tasks 1.17 and 1.19 carry (1.15 11.3, 1.16 11).

2.4.6 The whole wire test `python/test_wire.py`, which has not run, including the changed send and receive paths (1.17 11.1).

2.4.7 Whether "echo blob_max" fits `_RUNG_SECONDS` 120.0 with a SHA-256 over 2 GiB, and its time and disk use under `build/`, with the client's streamed echo next to the server's cache file (1.17 11.2, 1.34 11).

2.4.8 ttyd's title, log lines and `--port 0` (3.21), and ttyd's resident size during the 128 MiB echo (1.17 11.3).

2.4.9 How Chrome writes `DevToolsActivePort` (all at once, or with a trailing line end), a measurement needed to fix candidate 11.10.6.6, under which a port path cut short but holding two fields is accepted and then fails at the handshake (1.18 11.4).

2.4.10 Whether headless Chrome asks the stub server for a path it does not serve, such as `/favicon.ico` when "stage 5: stub reachable" opens `/text`, or resets a held socket so that a handler raises, either of which now ends the run (1.19 4.3, 1.35 4.1.3) (1.19 11.1, 1.35 11).

2.4.11 That a socket bound in WSL and never listening makes Windows Chrome's connection to its port refused, because a Windows listener on the same number cannot be held from WSL (1.19 11.2).

2.4.12 That ttyd 1.7.7 spawns tty 1 from a first message without a size, leaving the pty of `python/bootstrap.py` unaffected (1.23 4.3), proved through the rungs of the hello relay and the token (1.23 11.1, 1.36 11.4).

2.5 PowerShell on Windows

2.5.1 Formatting and analysis by `powershell/test_lint.ps1`, and a run, of the seven PowerShell files the review changed (`xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_powershell.ps1`, `powershell/xsjs_util.ps1`, `powershell/en-US/i18n.psd1`), which only the maintainer runs (1.10 11.3, 1.11 11.1, 1.11 11.2, 1.31 11.1, 1.41 11.1).

2.5.2 A run of 1.11's PowerShell edits: the whole list read and filtered (`Get-Command -CommandType Application`, `Get-NetTCPConnection`, `Get-ScheduledTask`, `Get-NetFirewallRule`), also in `xsjs_status.ps1` as a user who is not an administrator, `Get-ItemPropertyValue ... UBR`, and `xsjs_util_get_command_text` on every native command (1.11 11.2, 1.31 11.1).

2.5.3 WSL's exit codes for `wsl --list --verbose` with no distribution and for `wsl --list --running --quiet` with none running, needed by `xsjs_util_get_distribution` in `powershell/xsjs_util.ps1` (1.11 11.3, 1.31 11.1; summary 3.2.3).

2.5.4 The `ObjectNotFound` category of `Stop-Process -Id` on a process that is already gone, recalled from memory (1.18 4.2), and that `Stop-Process` raises nothing for a process that exits while it is being stopped (1.18 11.1, 1.34 11).

2.5.5 That the C# relay compiles under `Add-Type` with `const int CopyBytes` and the names `RelayRun` and `StreamCopy` (1.18 11.2).

2.6 sqlite3.wasm

2.6.1 The texts that `sqlite_assert` matches ("no such table: absent" and the CHECK text of request 1.8_1), and the SAH pool's refusal text, which `rung_pool` does not compare (1.5 4.4) (1.5 11.6, 1.8 11.3; summary 3.3.17).

2.6.2 The coercion of bound text into a STRICT INTEGER column (`test_version_wide`), and whether an INTEGER past 2^53 comes back as a number or as a `BigInt` (1.8 11.3, 1.24 11.2).

2.6.3 Whether `doc_head` in `ts/substrate.ts`, which builds its ref from a version read through `String()`, can name a version past 2^53 that `doc_put` did not write when sqlite3.wasm returns a Number, an Unconfirmed point (1.37 6.1, 1.37 8.1; summary 5.2).

2.6.4 That two exports with no write between them are equal (`test_databases_answered`) (1.8 11.3).

2.6.5 That `VACUUM` frees pages (`test_compact_vacuum`, 11.16.4.27), and whether it renumbers rowids on this build (1.8 11.3, 1.24 11.2; summary 3.2.4).

2.6.6 Whether the test pool's 32 files cover the most the suite holds at once, about ten database files and their journals in `test_recorded_replay` (1.8 11.4).

3 Proposed edits

Reports with no proposed edit: 1.5, 1.6, 1.14, 1.21, 1.26 (its stubs agree with the fixed code), 1.32, 1.33, 1.34, 1.35, 1.36, 1.37, 1.38, 1.39 and 1.41. "Choice" marks an edit that waits on a maintainer's choice; every edit under `API/` and REVIEW_EXECUTION.md is the maintainer's to apply (6.2, 6.10).

3.1 Stubs under `API/`

3.1.1 `API/python/dispatch.pyi`.

3.1.1.1 `reply_make`'s `blobs: list[jslb.Object] = ...` becomes `blobs: list[jslb.Object] | None = ...`, because 11.5.3.6 says `blobs` defaults to `None` and `[]` would be a shared mutable default (1.1 9.4; summary 3.3.1).

3.1.2 `API/python/third_party_fetch.pyi`.

3.1.2.1 After the `file_fetch` line, add the comment "# Fetches every pinned file, stopping at the first failure." and `def main() -> None: ...`, because 11.3.4.12 names `main` and the install runs the tool by its command line (1.1 9.5; summary 3.3.2).

3.1.3 `API/python/tap_consumer.pyi`.

3.1.3.1 The comment "A line as tappy's parser returns it; `category` names its kind." becomes "A line as tappy's parser returns it, `category` naming its kind.", because `comments_check` refuses the `;` and this is the first stop of `python/test_posix.py` once the banner question is answered (1.2 9.1; summary 3.1.1).

3.1.4 `API/python/main_loop.pyi`.

3.1.4.1 No edit beyond the pending `loop_prepare` of 4.6.9.3, whose text the inputs do not restate (1.16 9.1).

3.1.5 `API/python/devtools.pyi`.

3.1.5.1 Choice: add to `class PageEvents` the comment "# The `params` of each `Fetch.requestPaused` event, in order." and the field `requests_paused: list[dict[str, Any]]`, which is the whole design of the `Fetch.enable` form of the "wire open timer" rung, to be accepted or rejected together with the choice between `Fetch.enable` and `--max-clients 1` (12.5.5.4.10), its earlier application having been REJECTED and reverted (summary 1.4.3) (1.18 9.2; summary 4.4; code in 3.5.4).

3.1.5.2 Add to `ProtocolClient` the comment "# Ends every later wait at the monotonic time given when that comes first." and `def deadline_set(self, end: float | None) -> None: ...`, so that a rung timer can fire inside a DevTools call (1.19 9.3; summary 4.5; code in 3.5.5).

3.1.6 `API/ts/*.d.ts`, 24 of the 25 files.

3.1.6.1 Each of the 86 comments of two or more lines listed in 1.2's finding 4.3 becomes one line of at most 79 columns, a comment that describes the whole namespace moving its other sentences into a header comment above `declare namespace`, where several lines are allowed, and each `;` or other character outside `.,"'?:!()/`, letters, digits and space, when it is outside a code span, is reworded or put in backticks, for example "Posts a notification; nothing answers it." in `API/ts/queue.d.ts` becoming "Posts a notification, which nothing answers.", described in words because the wording is the maintainer's API prose (1.2 9.2; summary 3.1.2).

3.1.7 `API/ts/dispatch.d.ts`.

3.1.7.1 The handler comment "A handler gets the line and returns the reply without a header, nothing for a notification, or a sleep. It is synchronous." becomes "A handler gets the line and returns a finished reply line built with `reply_make`, nothing for a notification, or a sleep. It is synchronous.", proposed twice with the same words and different line breaks, by 1.1 9.2 (finding 1.1 4.9, reasons 3.3 and 2.8.2) and by 1.3 9.5 (finding 1.3 4.12, the `Reply` type) (summary 3.3.5, 3.3.15).

3.1.8 `API/ts/queue.d.ts`.

3.1.8.1 In the constructor comment, "`synchronous` is the debug mode of 4.2" becomes "`synchronous` is `queue_synchronous`, debug only", because the plan's section 4.2 is gone and 2.8.2 states the setting (1.1 9.3; summary 3.3.6).

3.1.8.2 The `OwnerTable` comment becomes "Type prefix to owner: `"kv."` to `"ai"` on both threads, the AI thread's forwarded `kv.*` lines naming `"server"` as their explicit owner; `"verbose."` to `"server"` on the AI thread." (1.3 9.4; summary 3.3.16).

3.1.8.3 Choice (acceptance): the built additions of 4.5.5 (11.14.4.26), which the code in `ts/queue.ts` already holds: `task_submit(line, owner?: ThreadName)` and `line_notify(line, owner?: ThreadName)`, each with "A given owner takes the place of the owner table's.", `sink_attach(sink_set, settings_get)` after `depth()`, with a comment on installing the thread's `VerboseBatch` as its verbose sink, and the class `VerboseBatch` (`constructor(thread, settings_get)`, `line_add`, `batch_send`) after `TaskQueue` (1.22 9.1, 1.36 10.3).

3.1.8.4 After `type OwnerTable`, add "The bytes a held line counts toward `blob_max`: its blobs' sizes." and `function line_bytes(line: lines.Line): number;`, giving one measure for every window (1.28 9.1; summary 3.3.25; code in 3.5.10).

3.1.9 `API/ts/lines.d.ts`.

3.1.9.1 In the lane table, the `mcp` rows `wire either 0 push (JSON-RPC)` and `mcp AGENT <-> MCP 0 push (JSON-RPC)` become `wire AI -> SERVER 0 Mcp, or push (JSON-RPC)` and `mcp AGENT -> MCP 0 Mcp, or push (JSON-RPC)`, and two head-comment lines after "every reply a sleeping task waited for has arrived." define "Mcp, or push" (a JSON-RPC request travels with `i` and its response is the reply's payload, while a JSON-RPC notification is a push), following the code of both languages (1.3 9.1; summary 3.3.12).

3.1.9.2 The comment above `interface HttpResponse` becomes "The reply to http.request, its `t` the request's own type: `json` when the content type is JSON, else `text`.", which drops the blob 1 clause and keeps the alternative design on record: image downloads moved to the http port would add `binary` to `HttpRequest`, read the body with `arrayBuffer()` and reply with it as blob 1 (11.15.6.8) (1.3 9.2; summary 3.3.13).

3.1.9.3 Four lane rows change: `error` "either, r set" to "either, r if i", `fault` "either" to "AI -> UI", the `console.read` reply `ConsoleRead` to `ConsoleReadReply` and the `dom.choice` reply `DomChoice` to `DomChoiceReply`, and the `ConsoleRead` comment says the port replies with the output received after the read was posted, through the message in which `until` appears, or with what came when the timer of `timeout_seconds` expires (3.12, 12.3.3.12) (1.3 9.3; summary 3.3.14).

3.1.9.4 Choice: add the rows `console.show ui-ai AI -> UI 0 Empty` and `ui.show_reply ui UI -> UI 0 wake`, and `interface ConsoleShow {}` after `ConsoleExit`, commented that the UI shows the console view as ctrl-0 does and replies once tty 0 is open, so that the AI can open tty 0 with permission, the maintainer choosing between showing the view (as proposed, because feeding it hidden is an open research goal, 2.6.1) and opening tty 0 with the view hidden (1.27 9.1.1, 1.27 9.1.2, 1.27 9.1.7; summary 3.2.5; code in 3.5.9).

3.1.10 `API/ts/tools_browser.d.ts`.

3.1.10.1 `tools_register` gains `settings_get: (id: string) => unknown` (the code's present departure, 11.19.4.1) and `full: boolean` after `info: lines.ProviderInfo`, so that the tools' lines take the worker's name form in debug mode (D27), proposed identically by 1.3 9.6 and 1.27 9.2 (summary 3.3.7, 3.3.24; code in 3.5.1).

3.1.11 `API/ts/provider.d.ts`.

3.1.11.1 `chat_request` and the function taking `request: ImageRequest` each gain `full?: boolean` after their request parameter, with the comment "`full` gives the line full names, the worker's name form." above `chat_request`, needing no change to `API/ts/agent.d.ts` (1.3 9.7; summary 3.3.8; code in 3.5.2).

3.1.11.2 After `tools_convert`, add "Forgets the key, so that the next read throws, for the tests only." and `function key_clear(): void;`, so that `key_get` with no key set can be tested (1.25 9.1; summary 3.4.3; code in 3.5.8).

3.1.12 `API/ts/substrate.d.ts`.

3.1.12.1 Choice between two edits of `RefParts.version`: a) `version?: bigint;` (1.4 9.1), exact in both twins with every key kept and serialized by no caller, or b) keep `version?: number;` under the new comment "A JavaScript number: exact to 2^53, rounded past it." (1.24 9.2), the store reading only its presence (1.24 10.2; summary 3.2.1, 4.7; code for a) in 3.5.3).

3.1.13 `API/ts/utility.d.ts`.

3.1.13.1 After `sha256_hex`, add the class `HashStream` ("A SHA-256 fed in pieces of any size, as a streamed blob arrives.") with `bytes_add(data: Uint8Array): void` ("Feeds bytes, keeping none of the caller's view after the call.") and `digest_hex(): lines.Sha256` ("The hash of the bytes fed so far.") (1.24 9.1; summary 3.3.23, 4.6; code in 3.5.7).

3.1.14 `API/ts/wire.d.ts`.

3.1.14.1 Choice (option b) of 1.23 10.1 against the built a) and the request form c)): `ConsolePort`'s `constructor(base_url: string)` becomes `constructor(base_url: string, full: boolean)` with the comment "full is the worker's names_full(), the form of the lines the port builds.", and 4.5.29 is amended to match (3.4.5) (1.23 9.1; summary 3.3.22; code in 3.5.6).

3.1.15 `API/ts/console_view.d.ts`.

3.1.15.1 Choice (part of 3.1.9.4): in `ConsoleView`, after `view_toggle(): void;`, add `open_is(): boolean;`, true while tty 0 is open (the phase "open") (1.27 9.1.3).

3.1.16 `API/ts/boot.d.ts`.

3.1.16.1 The `DomPort` comment gains "in the name form `full` that the worker chose", and its constructor becomes `constructor(container: HTMLElement, full: boolean)`, because 2.7.2 and D27 give the debug form to every line the page builds and the port has no other way to learn the worker's answer (1.29 9.1; summary 3.3.26; code in 3.5.11).

3.1.17 `API/ts/unittest.d.ts` and `API/ts/tap_producer.d.ts`.

3.1.17.1 Choice (acceptance): the built additions of 4.5.10, 4.5.33 and 4.5.34, whose text the inputs do not restate (1.20 10.4, 1.36 10.3).

3.1.18 Stub not named in the inputs.

3.1.18.1 The stub rows for D23's `ConsoleOpenReply` (4.6.9.12), proposed and not applied, whose text the inputs do not restate (1.30 10.2).

3.1.19 Conflict among the stub edits, for the maintainer: under the one-line, restricted-character comment rule that 1.2 9.2 applies, these proposed new texts would themselves be refused by `comments_check` and need rewording before they are applied: comments of two or more lines in 3.1.7.1 (1.1 9.2, 1.3 9.5), 3.1.8.1 (1.1 9.3), 3.1.8.2 (1.3 9.4, which also has a `;` outside a code span), 3.1.8.3 (1.22 9.1, which also keeps "Posts a notification; nothing answers it."), 3.1.9.2 (1.3 9.2), the `ConsoleRead` comment of 3.1.9.3 (1.3 9.3), 3.1.9.4 (1.27 9.1.2) and 3.1.16.1 (1.29 9.1), and characters outside code spans in 3.1.12.1 b) (the `^` of "2^53", 1.24 9.2) and 3.1.14.1 (the `_` of "names_full()", 1.23 9.1).

3.2 `API/README.md`

3.2.1 The text "The external API of every module hyperposition-plan.md names, before any is written. Nothing here runs. A file changes only when hyperposition-plan.md changes with it." becomes "The external API of every module of the engine, before any is written. Nothing here runs. A file changes only by the maintainer.", because the plan file no longer exists and `API/` is the maintainer's (6.2) (1.1 9.1; summary 3.3.4).

3.3 `README.md`

3.3.1 None: no report proposes an edit to the top-level `README.md` (1.6 9.1 and 1.7 9.2 say so explicitly, and no other report's item 9 names it).

3.4 REVIEW_EXECUTION.md, in section order

3.4.1 2.10.1, choice (only for option 10.2.1 of 1.5.1): "only the HTTP timeout rung uses a `provider.json`, its own, at a local stub (approved)." becomes "only the HTTP timeout rung (approved) and the compaction rung of the root "compact" use a `provider.json`, each its own, at a local stub." (1.7 9.1.1).

3.4.2 2.11.3 ("Unconfirmed: a UTF-8 byte order mark allowed"), 4.2.25.2, 4.7.1, 4.8.4.38, 11.2.5.2 d), the last clause of 11.3.4.13, and 11.3.5.2 each say that three PowerShell files lack the byte order mark, and they are to be corrected because all eight files have one, with the wording left to the maintainer since no new text is given (1.11 9.2).

3.4.3 3.15: "Three PowerShell files ... have no UTF-8 byte order mark ... that is open (4.7.1), and D22 ... holds the first two." becomes "Every PowerShell file starts with a UTF-8 byte order mark, which the PowerShell rule of the earlier job's agent instructions requires, not the project rules." (1.11 9.2).

3.4.4 Section 4.5, choice (accept or reject 3.1.5.1): add the record "Proposed, an addition to `python/devtools.py`: the `PageEvents` field `requests_paused`, the `params` of each `Fetch.requestPaused` event, for the `Fetch.enable` form of the 'wire open timer' rung (12.5.5.4.10). Files: `python/devtools.py`, `python/test_devtools.py`, `python/test_browser.py`, `API/python/devtools.pyi`. State: awaiting acceptance." (1.18 9.2).

3.4.5 4.5.29, choice (only with 3.1.14.1): amend it to `ConsolePort(base_url, full)` (1.23 9.1).

3.4.6 4.9.6.4: the list of places where a run stops becomes the stub comments that `comments_check` refuses, first `API/python/tap_consumer.pyi` and then 86 comments of more than one line in 24 of the 25 `API/ts/*.d.ts`, followed by seven comments (one in `python/stall_loop.py` above `loop_run`, a `;`; five in `python/test_browser.py`, a `;` above each of `rung_early`, `ui_request` and `rung_ui_put_largest` and two-line comments above `_PATTERN_PIECE` and `_IMAGE_COPIES`; one `;` in `ts/test_agent.ts`), noting that 1.16 9.4 reports the `;` above `stall_loop.loop_run` as fixed, so that entry may be dropped (1.2 9.3, 1.16 9.4; summary 3.1.3).

3.4.7 11.1.3.24: "with `TestLookup` and `TestStrings`" becomes "with `TestLookup`, `TestLoading` (the two `ValueError` paths of the loader) and `TestStrings`" (1.9 9.2).

3.4.8 11.1.4.3: after "where the stub derives them from a `Line` class", add "with a `category`; no `Plan.skip`, `Result.number` an `int` where the stub has `int | None`, and `Unknown.text` added;", naming the consumer's departures from its stub (1.9 9.1).

3.4.9 11.2.3.7: `_AUDIT_REFUSED` holds eleven texts and `_AUDIT_PASSED` seven, not nine and six, and a sentence is added that `new` and `Promise` separated by any white space are a hit, `await` after a member dot (`x.await`) is not, and a spread `...await` is (1.10 9.1).

3.4.10 11.2.3.19: after "`comments_find` refusing a lexer name it does not know.", insert "; `synchronization_check` refusing a token outside the five modules with its message (`test_token_refused`)" (1.10 9.2).

3.4.11 11.2.4.12: "`test_lint.ps1` is LF with no byte order mark (11.2.5.2, 11.3.5.2)." becomes "`test_lint.ps1` is LF and starts with a byte order mark." (1.31 9.1).

3.4.12 11.2.4.19: remove the clause "PSScriptAnalyzer's `PSUseBOMForUnicodeEncodedFile` may report the files with no mark, unverified." (1.31 9.1).

3.4.13 11.3.3.4: "eight hunks" becomes "seven hunks", since the patch holds seven `@@` hunks, one in each man page and five in `src/server.c` (1.11 9.1).

3.4.14 11.3.3.10: the stated preconditions gain `provider.json` beside `settings.json`, `i18n\en-US.json` and `build\hyperposition-engine.html` (1.11 9.3).

3.4.15 11.3.3.12: "Five start with a mark (...) and three do not (...); both kinds pass." becomes "All eight start with a mark, and a file without one would pass too." (1.11 9.2).

3.4.16 11.4.4.26: the "Not handled, as recorded" list shrinks to "`bytearray` for `d`;", followed by "Handled since: stale files in a vector directory, which `vectors_write` removes before it writes, and a number or a key of over 4300 digits, whose `ValueError` the Python decoder raises as `jslb.line_not_json`." (1.12 9.1).

3.4.17 11.4.6.4: "and no test pins either behaviour" becomes "and `python/test_jslb.py` pins Python's refusal (`test_number_long`), TypeScript's being unpinned", which disagrees with the edit's own reason that 1.12's finding 4.2 adds the TypeScript `test_number_long` (also named in 2.1.12), so the maintainer has to reconcile the two (1.12 9.2).

3.4.18 11.5.3.11: "The server returns `None` for any message without an `id`, a notification;" becomes "The server returns `None` for a notification, a message with `jsonrpc` `2.0`, a string `method` and no `id`; a message without an `id` that is not valid gets -32600 with `id` null;", following JSON-RPC 2.0 section 5 (1.13 9.1).

3.4.19 11.5.3.15: "Stdio output is compact UTF-8, flushed per response." becomes "Stdin and stdout are UTF-8 whatever the locale; the output is compact and flushed per response." (1.13 9.2).

3.4.20 11.5.3.26, choice (only for option 10.2.1 of 1.5.1): "in every test but one," becomes "in every test but two,", and "The one rung of the real HTTP timeout inside a turn writes" becomes "The rung of the real HTTP timeout inside a turn, and the compaction rung of the root "compact", each write" (1.7 9.1.3).

3.4.21 11.7.3.6: "Its handler, inside one `transaction_run`, refuses" becomes "Its handler, inside one `transaction_run` (for `db.create` and `db.drop`, whose file is made or removed, outside one, by `operation_apply`), refuses" (1.15 9.2).

3.4.22 11.7.3.19: "every two token `--main-loop <x>` removed" becomes "every form of `--main-loop` that the parser of `bootstrap.py` takes (`--main-loop <x>`, `--main-loop=<x>`, and an abbreviation from `--m` in either form) removed" (1.15 9.1).

3.4.23 11.8.3.11: "a reply with a blob raises `bootstrap.reply_blob`," becomes "a reply whose blob streams, over `overflow_bytes`, raises `bootstrap.reply_blob` before its bytes, a reply with a smaller blob `bootstrap.reply_unexpected`," (1.16 9.2).

3.4.24 11.8.3.30: "A seed file that is not a valid document raises `main_loop.seed_invalid`." becomes "A seed file that is not a JSON object raises `main_loop.seed_invalid`, and one that is not a valid document the substrate's error from `doc_put`." (1.16 9.3; summary 3.3.20).

3.4.25 11.8.6.1 names the `;` above `stall_loop.loop_run`, which is now fixed, and no new text is given for it (1.16 9.4).

3.4.26 11.9.3.4: after "with `debug` written for the root", add ", `verbose_level` 1 and `provider.scripted` true, the checkout's values at the baseline" (1.17 9.1).

3.4.27 11.9.3.5: after "It reads lines with `jslb`'s decoder.", add that it queues each line's pieces without copying them and frames each message only when it is sent, and that its decoder streams a blob over 128 MiB (`_HELD_BYTES`) to a file in the run's directory, which the echo check compares by its `sha256`, resolving candidate 11.9.6.1 (1.17 9.2).

3.4.28 11.10.3.14: "Every wait has a named `WaitTimer` that raises `TimeoutError`." becomes "Every wait is bounded by a named constant and raises `TimeoutError` naming what it waited for: the polls and the protocol's waits through a `WaitTimer`, the waits of `command_run` and `process_wait` through the subprocess module's timeout." (1.18 9.1; summary 3.3.21).

3.4.29 11.11.3.4: the run's state becomes "the one browser, as a `BrowserDriver`, the `RungLog`, the work directory, the run's `contextlib.ExitStack` with the stub server it starts when a rung first needs it, the three pages, the port held bound and never listening, and the set of pages built so far." (1.19 9.1).

3.4.30 11.11.3.6: after its first sentence, add "Every root sets `debug` true, `verbose_level` 1 and `provider.scripted` true, the checkout's values at the baseline, before its own settings, as `test_wire.py` sets `debug`." (1.19 9.2).

3.4.31 11.12.3.13: the sentence becomes "In the AI worker (`self.name === "ai"`, as `boot.boot_run` and `test_hook.engine_run` test it) it calls `boot.test_worker(worker_run)`; on the UI thread, `boot.test_page(page_run)`.", replacing the test on `self.name === ""` (1.20 9.1).

3.4.32 11.20.3.6: "the server port, wrapped in a `WireTap` in debug mode;" becomes "the server port, the `ServerHold` that holds a `db.snapshot` behind its database's waiting lines, around the wire or, in debug mode, its `WireTap`;" (1.28 9.2).

3.4.33 11.20.3.12: add at the end "A `db.snapshot` posted while lines of its database wait joins that database's queue and goes out after them." (1.28 9.2).

3.4.34 11.20.4.9: add `worker.script_fetched` to the `worker.` types (1.28 9.2).

3.4.35 11.21.3.9, choice (only with 3.1.16.1): "`DomPort(container)`" becomes "`DomPort(container, full)`" (1.29 9.1).

3.4.36 11.22.3.9: "which throws `console_view.exit_phase` unless the view is open," becomes "which throws `console_view.exit_phase` unless the view is open or closing,", matching the closing phase added by 4.5.30 and the string's text "not open or closing" (1.30 9.1).

3.4.37 12.1.2.15: `ts/tsconfig.json` lists every module of `ts/` that is not test code (the test modules, `test_hook.ts` and the harness `unittest.ts` and `tap_producer.ts` being test code), and `ts/tsconfig.test.json` lists "those modules, the harness and every test module", which matches the code (1.1 9.6; 1.18 10.6).

3.4.38 12.3.2.16: after "the suffixes being names under `worker.`.", add "The code's `worker.snapshot_reply`, the start chain's one wake of a `db.snapshot` reply, restoring or loading by its state, stands where the record wrote `.restored` and `.loaded` (11.20.4.9)." (1.3 9.9; summary 3.3.11).

3.4.39 12.3.3.7, choice (1.4.1): after "`bootstrap.py`'s `error` line uses short names in debug mode too, as the coordinator ordered;", add "the worker's `fault` line, built by `error_overlay`, which depends on nothing, uses short names in every mode, a point left to the maintainer;" (1.3 9.8; summary 3.3.10).

3.4.40 12.5.2.7.3.3, choice (only for option 10.2.1 of 1.5.1): "in every other test `provider.scripted` is true and the file is never read." becomes "in every other test but "compaction at the threshold" (12.5.2.7.3.5) `provider.scripted` is true and the file is never read." (1.7 9.1.2).

3.4.41 12.6.3.2.13, a new paragraph after 12.6.3.2.12: "In `test_create_twice` a second `db_create` and a `db_open` of a missing file throw `substrate.db_exists` and `substrate.db_absent`, where Python raises `FileExistsError` from `os.open` and SQLite's own error (11.6.3.33); the SAH pool has neither." (1.8 9.1; summary 3.4.1).

3.5 Other targets: code that waits on a stub edit

3.5.1 With 3.1.10.1: in `ts/tools_browser.ts`, `ToolContext` keeps `readonly full: boolean`, the private `line_build(type, payload, blobs)` becomes `line_build(type, full, payload, blobs)` with `jslb.header_make(type, { full })` and every call passes `context.full`, and `value_fetch` builds `jslb.header_make(constants.get_type, { key: ref, full: this.full })`, while `worker_start` in `ts/worker_ai.ts` passes its `full` (task 1.28) and the expected lines of `ts/test_tools_browser.ts` move with it, `bench_make` passing `false` and a debug case checking full names (1.3 9.6, 1.27 9.2).

3.5.2 With 3.1.11.1: `post_make` in `ts/provider.ts` takes `full` and builds `jslb.header_make(constants.request_type, { full })`, `TurnLoop.request_submit` in `ts/agent.ts` passes the form of the turn's request line (`Object.hasOwn(request[0], "type")`), the `image_make` tool passes the `context.full` of 3.5.1, and `ts/test_provider.ts` moves with it (1.3 9.7).

3.5.3 With option a) of 3.1.12.1: `version_find` in `ts/substrate.ts` returns `bigint | undefined` using `BigInt(tail)` in place of `Number(tail)`, and the `ref_split` cases of `ts/test_substrate.ts` write `1n`, `12n` and `0n`, while option b) brings no code (1.4 9.1, 1.24 9.2).

3.5.4 With 3.1.5.1: `python/devtools.py` sets `self.requests_paused: list[dict[str, Any]] = []` in `PageEvents.__init__` and, after the `Debugger.paused` branch of `PageEvents.message_handle`, appends `message["params"]` on `Fetch.requestPaused`, `python/test_devtools.py` adds `test_request_paused` to `TestPage` (two events, R1 for `http://x/token` and R2 for `http://x/ws`, expected in order), and in `python/test_browser.py` `LifecycleEvents` declares `requests_paused` and `rung_opening` reads ttyd's token with `probe.token_read`, sends `Fetch.enable` with a pattern for the token URL, stops ttyd with `SIGSTOP`, opens the port with `wire_open("opening", session.url)`, pumps events until a paused request is kept and answers it with `Fetch.fulfillRequest` and ttyd's token body, waits for the open timer's fault, sends `Fetch.disable` and resumes ttyd with `SIGCONT`, after which `_OPENING_BASE` no longer points at the stub (1.18 9.2).

3.5.5 With 3.1.5.2: `python/devtools.py` keeps `self.deadline: float | None = None` and `WaitTimer` takes the deadline and ends at `min(time.monotonic() + seconds, deadline)`, naming the deadline in its message, while in `python/test_browser.py` `DriverClient` declares `deadline_set`, `RungLog` keeps the client once the browser starts and `rung_start` calls `deadline_set(self.timer.end)`, so that `main`'s note names the rung (1.19 9.3).

3.5.6 With 3.1.14.1: in `ts/wire.ts` the field `settings_get` becomes `private readonly full: boolean`, set by the constructor, the three `full: this.names_full()` become `full: this.full`, and `names_full()` and `constants.debug_setting` are deleted, while `console_make` in `ts/worker_ai.ts` makes `new wire.ConsolePort(base_url, full)` (task 1.28), `console_make` and `test_scheme_unknown` of `ts/test_wire.ts` pass `true`, and the probe `console_make(base, read)` of `python/test_browser.py` passes the probe's debug value (task 1.19), the worker receiving first (11.15.7.1) (1.23 9.1).

3.5.7 With 3.1.13.1: `ts/utility.ts` (task 1.21) exports `HashStream` as it stands in `ts/substrate.ts`, mixing blocks with its own `block_run` and tested in `ts/test_utility.ts`, and `ts/substrate.ts` deletes `primes_first`, `fraction_bits`, `round_table`, `hash_start`, `bits_rotate`, `block_mix`, `HashStream` and the constants `block_bytes` to `word_range` and `padding_marker` and uses `utility.HashStream` in `SinkOpen`, `sink_open` and `handle_hash`, with `TestHash` staying to test the sink (1.24 9.1; summary 4.6).

3.5.8 With 3.1.11.2: `ts/provider.ts` exports `key_clear(): void { key_stored = undefined; }` with its comment, and `TestProviderKey` in `ts/test_provider.ts` gains a field `#kept = ""`, a `setUp` that keeps `provider.key_get()` (the boot's key), a `tearDown` that restores it with `provider.key_set(this.#kept)`, and `test_key_missing`, which calls `provider.key_clear()` and compares the message thrown by `provider.key_get()` with `i18n("provider.key_missing")` (1.25 9.1).

3.5.9 With 3.1.9.4 and 3.1.15.1, for task 1.27, in `ts/tools_browser.ts`: `constants.show_type: "console.show"` and `show_wake: "tools.show_reply"`, `console_run` and the permit wake (Accept, Always Allow) return `context.request_sleep(line_build(constants.show_type, {}), constants.ui_owner, state, constants.show_wake)` with the `ConsoleState` where they now call `context.console_send`, and a new wake `[constants.show_wake]` returns `context.console_send(text, timeout_seconds)`, while in `ts/test_tools_browser.ts` `wake_types` gains `tools.show_reply` and `test_console_recorded`, `test_permit_always`, `test_permits_counted` and `test_console_expired` answer the `console.show` request (owner `ui`, payload `{}`) with an empty reply (1.27 9.1.4).

3.5.10 With 3.1.9.4, for task 1.29, in `ts/page.ts`: the owner row `"console.show": "ui"`, a handler `show_take(line)` that throws outside debug mode, calls `view.view_show()`, sleeps on `view.open_request()` with wake type `ui.show_reply` when `view.open_wanted()`, replies at once when `view.open_is()` and otherwise throws a new `page.console_busy` naming the phase, a wake handler `show_done(wake)` that calls `view.open_done(wake)` and replies, and `open_is()` added to `ConsoleControl`, a new string name that would need its `i18n` text (1.27 9.1.5).

3.5.11 With 3.1.15.1, for task 1.30: `open_is(): boolean { return this.phase === "open"; }` in `ts/console_view.ts` with its test in `ts/test_console_view.ts`, `ts/worker_ai.ts` being unchanged because the view's `console.open` goes through its relay as at ctrl-0 (1.27 9.1.6).

3.5.12 With 3.1.8.4: `export` on `line_bytes` in `ts/queue.ts` (task 1.22), and in `ts/worker_ai.ts` its own `line_bytes` removed and `line_add` calling `queue.line_bytes(line)` (1.28 9.1).

3.5.13 With 3.1.16.1: in `ts/page.ts`, `DomPort` gains `private readonly full: boolean`, set by the constructor `(container: HTMLElement, full: boolean)` under the comment "Finds the image, the input and the permit area, keeps the name form, and listens.", `text_take`, `click_take` and `key_take` pass `this.full` to `line_build` in place of `false`, and `engine_open` makes `new DomPort(body, full)`, while in `ts/test_page.ts` the seven `new page.DomPort(elements.container)` and the refusal `new page.DomPort(empty)` gain `false` and `TestDomPort` gains `test_names_full` (a port made with `true` posts a submitted text and a ctrl-3 whose headers hold `type`) (1.29 9.1).

3.5.14 No code is needed for 3.1.8.3 (the code of `ts/queue.ts` already holds the names, 1.22 9.1), for option b) of 3.1.12.1 (1.24 9.2), for 3.1.17.1 (built, 1.20 10.4), or for any REVIEW_EXECUTION.md edit except where 3.4 marks it as tied to a stub edit.

4 Formatter (report 1.41)

4.1 Stability: `python3 python/reformat.py` was run twice, and `cmp tmp/review/format_1.diff tmp/review/format_2.diff` found them identical (exit 0), the first run having had ruff reformat 1 of 65 `.py` files and none of 25 `.pyi`, prettier rewrite 4 `.ts` files and none of the `.html`, `.js` or `API/ts/*.d.ts`, shfmt list none and `mdformat --check` pass, and the second run having changed nothing, so the formatter is stable after one run (1.41 4.3).

4.2 Staging: 86 files were staged with `git add` before the run, the 84 whitelisted changed files and the two created ones (`python/test_echo_loop.py`, `python/test_stall_loop.py`, as `A`), while `i18n/en-US.json` and `python/seed/prompt.json`, which are not whitelisted (3.10), were left unstaged, nothing was committed or unstaged, and every run exited 0 (1.41 4.1, 4.2, 12.5).

4.3 Files the formatter changed, left unstaged over the staged review changes (`MM`), all white space or wrapping parentheses, none changing behaviour and none reverted (1.41 4.4, 5.1):

4.3.1 `python/test_browser.py`: the lambdas of `rung_order` and `rung_early` were wrapped in parentheses over several lines, and the signature of `still_settled` was joined onto one line of 79 columns or fewer.

4.3.2 `ts/test_http.ts`: one `message_thrown` call was joined onto one line.

4.3.3 `ts/test_mcp.ts`: one `assertEqual` call was split over four lines.

4.3.4 `ts/test_substrate.ts`: the `cache_present` arrow and one `raised_assert` call were each joined onto one line.

4.3.5 `ts/test_verbose.ts`: three `assertEqual(message_thrown(...), ...)` calls were each split over four lines.

4.4 Protected files of 14.2.6 (files of 6.10 or 5.6 covered by the whitelist): `API/python/*.pyi`, `API/ts/*.d.ts`, `python/bootstrap.html`, `README.md`, `LICENSE.md`, `archive.sh` and `clean.sh` were all reported unchanged, `git diff` names none of them, and so nothing was listed or reverted (1.41 4.5).

4.5 Open formatting questions:

4.5.1 The hook of `html/test_engine.html` stays split over three lines (prettier reported the file unchanged), so `test_template_hooked` in `python/test_page_build.py` still counts a one-line `_HOOK_SCRIPT` and fails (1.41 10.1; same as 1.8.9).

4.5.2 After the run, the formatter's re-indent leaves HTML lines over 79 columns: line 21 of `html/engine.html`, 29 of `html/test.html` and 22 of `html/test_engine.html` (80 each), and three lines of `python/bootstrap.html` (81, 82 and 86 columns), held by D22 (11.2.6.8, 11.10.5.2) (1.41 10.2; same as 1.8.5 and 1.8.6).

4.5.3 Node's compile cache is written outside `build/` when prettier runs (11.2.5.11), a class B item left as built (1.41 3.2, 10.3; same as 1.8.11).

4.5.4 Accepted and not changed: the formatter rewrites every whitelisted file of a linux row, not only those the review changed (14.2.3, 11.2.4.6), and the whitelist lines `LICENSE.md` and `README.md` are checked by `mdformat --check`, which rewrites nothing (11.2.4.10, 11.2.5.14) (1.41 3.1, 3.3; see 1.8.2).

4.6 The PowerShell files owed to `powershell/test_lint.ps1` on Windows (14.2.5, 15.4), not formatted here because the PowerShell rows have the system `windows` and no formatter on Linux (11.2.3.8): `xsjs_install.ps1`, `xsjs_start.ps1`, `xsjs_status.ps1`, `xsjs_stop.ps1`, `powershell/test_powershell.ps1`, `powershell/xsjs_util.ps1` and `powershell/en-US/i18n.psd1` (1.41 3.4, 11.1; same as 2.5.1).

4.7 Also owed: tsc and the suites over the five reformatted files, whose changes are white space only (1.41 11.2; same as 2.2.17).

5 Counts

5.1 Section 1, open questions after merging: 87 (1.1 naming 5, 1.2 import 6, 1.3 comments 1, 1.4 D27 2, 1.5 provider and compaction 4, 1.6 browser rungs 12, 1.7 PowerShell 7, 1.8 formatter and whitelist 12, 1.9 stubs and API 8, 1.10 other 30), one of them (1.10.21) recorded as closed and one (1.10.7) conditional.

5.2 Section 2, owed values after merging: 90 (2.1 Python 25, 2.2 TypeScript and tsc 17, 2.3 browser test 25, 2.4 ttyd and Chrome 12, 2.5 PowerShell 5, 2.6 sqlite3.wasm 6).

5.3 Section 3, proposed edits after merging: 81 (3.1 stubs: 26 edits over 18 stub targets; 3.2 `API/README.md` 1; 3.3 `README.md` 0; 3.4 REVIEW_EXECUTION.md 41; 3.5 code tied to stub edits 13), plus three items that are not edits (3.1.19 the conflict, 3.3.1 none, 3.5.14 no code), of which 14 need a maintainer's choice (3.1.5.1, 3.1.8.3, 3.1.9.4, 3.1.12.1, 3.1.14.1, 3.1.15.1, 3.1.17.1, 3.4.1, 3.4.4, 3.4.5, 3.4.20, 3.4.35, 3.4.39, 3.4.40), 3.4.2 and 3.4.17 need the maintainer's wording, and 3.1.19 needs a rewording of the stub texts it names.

5.4 Section 4, formatter: 14 items (4.1, 4.2, 4.3.1 to 4.3.5, 4.4, 4.5.1 to 4.5.4, 4.6, 4.7); formatter stable after one run, no protected file changed, seven PowerShell files owed.
