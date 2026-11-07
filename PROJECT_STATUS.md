# Project Status

Measured on 2026-11-06 at commit 591c1da, on Ubuntu 26.04 under WSL2, with Python 3.14, Node 22, ttyd 1.7.7 and Chrome for Testing 156. This covers the POSIX side only. The Windows side was not looked at.

## Summary

1. Every POSIX test that runs passes. `./test_posix.sh` passes all 119 suites in about 100 s, and `./test_posix.sh --test-all` passes all 122 suites and its three final checks in 618 s.
2. No test failure is blocking work. The blockers are what the tests cannot show: no program runs yet except the tests, a real AI has not been used, and only this one machine has been proven.
3. One mode fails, and neither official target uses it: `--coverage`, the Python line count, stops at its second suite. 15 of 35 Python modules have at least one line it never counted.

## Test Runs

| Run | What it covers | Result | Time |
|---|---|---|---|
| `./test_posix.sh`, 3 runs | The smoke-test suites and the final checks at smoke level | Passed, 119 of 119 suites each time | 98, 103 and 99 s of the 180 s limit |
| `./test_posix.sh --test-all`, 1 clean run | All suites and the final checks at normal level | Passed, 122 of 122 suites, 1901 tests | 618 s, no limit |
| `./test_posix.sh --debug` | The smoke run with debug mode on | Passed, 119 of 119 suites | 110 s |
| `python3 python/test_all.py --tty` | The smoke suites relayed through the engine's own terminal | Passed, 119 of 119 suites | 99 s |
| `--module failing_suite`, `--module failing_block.ts` | Suites that fail on purpose, proving that failures are counted | Passed: Python counted 4 failures, or 1 with failfast; TypeScript counted 3 | Under 4 s |
| `--coverage` | Python line coverage | **Failed**, see blocker 4 | Under 1 s |
| `./test_posix.sh --anthropic` | The cloud container run | **Cannot run here**, see blocker 3 | Under 1 s |
| `--verbose` | Any run with the console's shell at verbose level 2 | Not run. `test_tools_browser_console` fails under it, and you chose on 2026-11-05 to leave that as it is | None |

No run skipped a test, and the formatters changed no file.

Two earlier `--test-all` runs failed in `test_bootstrap` and do not count. They were started through `nohup`, which makes every child ignore the hangup signal that two of its tests expect, so the launch caused the failure and not the project. Repeating it confirmed this: the suite fails with `nohup` and passes without it. Blocker 6 records what this means for future test runners.

## Suite Status

| Group | Where it runs | Suites | Tests | Seconds | Status |
|---|---|---|---|---|---|
| Python | Python unit, integration and server-start suites | 65 | 891 | 33.8 | All pass |
| A unit | TypeScript in Node | 23 | 487 | 3.4 | All pass |
| A integration | TypeScript in Node, and one Python pair test | 5 | 39 | 4.7 | All pass |
| B unit | TypeScript in headless Chrome | 14 | 324 | 15.6 | All pass |
| B integration | TypeScript in headless Chrome | 9 | 119 | 14.5 | All pass |
| C integration | TypeScript in headless Chrome, served by a real ttyd and server | 5 | 39 | 12.3 | All pass |
| Whole page | The screenshot tool opening the whole page | 1 | 2 | 3.4 | All pass |
| **Total** | | **122** | **1901** | **87.7** | **All pass** |

Three of the 122 suites run only in `--test-all`: `test_reformat_formatters`, `test_test_posix_formatters` and `test_integrate_xsjs_screenshot`. The appendix lists every suite.

These checks run after the suites and passed at both levels:

| Check | What it proves |
|---|---|
| `python/test_posix.py` | Source files keep the encoding and comment rules, the synchronization audit passes, and at normal level the formatters and linters are clean |
| `python/test_wire.py` | The page and server talk over a real ttyd, on three server setups named echo, stock and restart |
| `python/test_browser.py` | The page's bring up, faults, tools and console, in about 45 steps driven through Chrome, most of them at normal level only |

These print nothing when they pass, so their pass is known from the exit code of the run and there is no count of their steps.

Not run, by design:

1. `test_devtools_powershell`, the Windows browser link, has been offline since 2026-10-30 and belongs to the Windows side.
2. `powershell/test_powershell.ps1`, the Windows test target, is out of scope for this report.

## Blockers by Priority

### 1. Nothing but the tests runs, and no plan says what comes next

The AI turn loop, the provider, the browser tools, the page's handlers and the console view are all written and tested, but only test suites start them. `agent.ts` is called from its three test files alone, and nothing outside the tests sets the provider key. The page that `xsjs_start.ps1` serves is the test page, and its own test list is empty on purpose, so opening it proves the bring up and nothing else. `API/ts/boot.d.ts` states this as the current design: there is no hello, no start chain and no first render.

The tree holds no plan for the next stage. `PLAN_B.md`, `PLAN_OF_RECIORD.md` and `PLAN_AI_CONSOLE.md` were deleted earlier, and I did not read them, since a deletion may be deliberate. The project rules put the design before the code, so the next stage cannot start from the code alone.

Question 1.1: how should the next stage be defined? This unblocks all new feature work, and the answer also sets when blockers 2 and 3 matter.

[ ] A. Write a new plan from your requirements, top down, for the first program a person can run: the page starts a real turn against the scripted AI, the stand-in used for testing. It costs a planning session before any code, and it carries over no old decisions by accident.

[ ] B. Restore the three deleted plans from git and update them. This is quicker, but it may bring back decisions you removed on purpose.

[ ] C. Finish the test work in blockers 3 and 4 first, and define the program afterwards. The base gets firmer, but the product waits.

### 2. No real AI has been used

`settings.json` sets `provider.scripted` to true and `provider.json` is blank, so every run uses the scripted AI, as the rules require of the suites. `API/ts/provider.d.ts` says xAI is the only provider tested, but no suite contacts it, so nothing here shows that the request format, the key handling or image generation work against the real service.

Question 2.1: when should a real provider first be tried? It needs your key and a live service.

[ ] A. Once the first program runs, by hand, with your key, and never in the suites. Nothing is spent until a turn can actually be played. Format errors surface late, but they should be cheap to fix.

[ ] B. Now, with a small one-off script that sends one request. Format errors surface early, at the cost of a throwaway script and of your key being used before the program exists.

### 3. Only this one machine is proven

All the results above come from this WSL2 machine. The other planned environments have not run:

1. The cloud run stops at once here. It needs the ttyd source archive placed by `apt-get source --download-only ttyd=1.7.7-4build1`, and the browser in `/opt/pw-browsers`, which is absent. It has never run end to end.
2. `test_posix.sh` is meant to run in Docker later. Docker is installed here, but the tree holds no Dockerfile.
3. No run has been made on Linux outside WSL. The screenshot tool's POSIX path has also only run here.

Question 3.1: which environment should be proven next? A second environment would also expose anything that depends on this machine, such as blocker 6's hangup signal.

[ ] A. The cloud container, in the next cloud session, where its browser and archive are in place. Nothing is installed here, and it also gives a Linux outside WSL.

[ ] B. Docker, by writing a Dockerfile now. It gives a repeatable run on any machine, at the cost of a new file to maintain and a choice of base image.

[ ] C. Install the cloud's parts here, with your approval, as this needs a package source added. It proves the switch only, as the machine stays the same.

### 4. The Python line count fails, and TypeScript has none

`--coverage` is outside both official targets, so nothing notices this failure. It stops at `python/tap_producer.py` line 266, in its second suite, because it ends at the first gap. I ran it once per module to see the extent: 20 of 35 Python modules pass and 15 have a gap.

| Module | First line never counted |
|---|---|
| `bootstrap` | 308 |
| `devtools` | 359 |
| `engine_system` | 139 |
| `internationalization` | 27 |
| `main_loop` | 190 |
| `mcp` | 195 |
| `mcp_stdio` | 93 |
| `page_build` | 116 |
| `reformat` | 135 |
| `substrate` | 207 |
| `tap_loop` | 150 |
| `tap_producer` | 266 |
| `test_posix` | 157 |
| `third_party_fetch` | 132 |
| `vectors_make` | 166 |

These gaps are not checked one by one, so some may be lines that run before the count starts, not untested code. The count shows only the first gap in each module. `test_all.py` also has a fault of its own: it looks for a file `substrate_limit.py` that does not exist, because `test_substrate_limit` is not mapped to `substrate`, so a full run would crash there even with the gaps closed. The TypeScript code has no coverage measure at all.

Question 4.1: what should the line count be?

[ ] A. Make it a real gate: fix the driver's mapping, work through the 15 gaps, then add it to `--test-all`. This gives a true measure of the Python, at the cost of test work that adds no features.

[ ] B. Keep it as an occasional tool. Fix only the driver's mapping and leave the gaps. This is cheap, and the mode keeps failing.

[ ] C. Remove `--coverage`. There is less code to keep, and no measure of untested Python.

### 5. The long run gives little feedback

Of the 618 s of `--test-all`, the 122 suites take 88 s and the final checks take about 530 s. Those checks print nothing as they pass, so a slow or stuck step is hard to see and their time cannot be split. The smoke run is comfortable at about 100 s of 180 s, though an earlier log recorded 154 s with the machine under other load, so a busy machine could reach the limit.

I recommend no action until the checks start to slow down work. Printing each step's name and time would be the fix, and I have not made it.

### 6. Small discrepancies

None of these stops work, and each has a one-step fix.

1. `API/ts/lines.d.ts` still points to `API/README.md`, which commit 591c1da deleted. The fix is to delete the pointer, since the rules forbid naming `declawed.md` there.
2. `docs/CONTRIBUTING.md` is another project's document, titled libhatchet, and it says `CLAUDE.md` links to it, which is false here. The fix is to delete or replace it.
3. `python/test_wire.py` says in its header that ttyd 1.7.7 accepting a first message with no size is from memory and still owed a test. The fix is to add that test.
4. `test_bootstrap` fails when the run ignores the hangup signal, as under `nohup`. The fix is to note this for whoever sets up a Docker or cloud runner, or to have the suite restore the signal for its children.
5. `build/` holds six leftover `test_browser-*` directories, five from 2026-10-30 and one from 2026-11-06, from runs that failed or were stopped. They are ignored by git and harmless. `clean.sh` removes them, along with everything else git ignores except `tmp/`, so the next run rebuilds `build/`.

## Appendix: Every Suite

Results are from the clean `./test_posix.sh --test-all` run. All of these passed. Tests is the number of passing test points inside the suite.

### Python

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_tap_consumer` | smoke-test | 43 | 0.0 |
| `test_tap_producer` | smoke-test | 44 | 0.0 |
| `test_internationalization` | smoke-test | 7 | 0.0 |
| `test_reformat` | smoke-test | 17 | 0.0 |
| `test_reformat_formatters` | test-all | 3 | 0.4 |
| `test_test` | smoke-test | 47 | 0.1 |
| `test_jslb` | smoke-test | 77 | 0.1 |
| `test_switches` | smoke-test | 15 | 0.1 |
| `test_third_party_fetch` | smoke-test | 10 | 0.0 |
| `test_devtools` | smoke-test | 62 | 0.4 |
| `test_local_http` | smoke-test | 10 | 2.2 |
| `test_stall_loop` | smoke-test | 2 | 0.2 |
| `test_substrate` | smoke-test | 37 | 0.4 |
| `test_substrate_limit` | smoke-test | 2 | 0.1 |
| `test_test_posix` | smoke-test | 24 | 0.0 |
| `test_test_posix_formatters` | test-all | 1 | 0.0 |
| `test_verbose` | smoke-test | 33 | 0.6 |
| `test_devtools_chrome` | smoke-test | 20 | 6.1 |
| `test_dispatch` | smoke-test | 29 | 0.1 |
| `test_settings` | smoke-test | 18 | 0.0 |
| `test_vectors_make` | smoke-test | 7 | 0.2 |
| `test_engine_db` | smoke-test | 11 | 0.2 |
| `test_engine_doc` | smoke-test | 5 | 0.0 |
| `test_engine_kv` | smoke-test | 13 | 0.2 |
| `test_engine_sql` | smoke-test | 7 | 0.1 |
| `test_engine_tap` | smoke-test | 15 | 0.2 |
| `test_engine_turn` | smoke-test | 7 | 0.1 |
| `test_engine_verbose` | smoke-test | 9 | 0.1 |
| `test_jslb_vectors` | smoke-test | 2 | 3.7 |
| `test_mcp` | smoke-test | 28 | 0.0 |
| `test_page_build` | smoke-test | 38 | 0.1 |
| `test_page_build_node` | smoke-test | 8 | 3.0 |
| `test_page_build_tsc` | smoke-test | 5 | 5.0 |
| `test_tap_loop` | smoke-test | 8 | 0.5 |
| `test_ttyd_build` | smoke-test | 7 | 3.6 |
| `test_echo_loop` | smoke-test | 9 | 0.1 |
| `test_engine_mcp` | smoke-test | 10 | 0.0 |
| `test_engine_system` | smoke-test | 25 | 0.3 |
| `test_main_loop` | smoke-test | 25 | 1.2 |
| `test_mcp_stdio` | smoke-test | 11 | 0.0 |
| `test_bootstrap` | smoke-test | 28 | 1.0 |
| `test_bootstrap_dash` | smoke-test | 5 | 0.2 |
| `test_tap_pair` | smoke-test | 12 | 0.0 |
| `test_integrate_test_posix` | smoke-test | 7 | 0.0 |
| `test_integrate_dispatch` | smoke-test | 6 | 0.0 |
| `test_integrate_settings` | smoke-test | 5 | 0.0 |
| `test_integrate_vectors_make` | smoke-test | 2 | 0.1 |
| `test_integrate_engine_db` | smoke-test | 4 | 0.1 |
| `test_integrate_engine_doc` | smoke-test | 2 | 0.0 |
| `test_integrate_engine_kv` | smoke-test | 5 | 0.1 |
| `test_integrate_engine_sql` | smoke-test | 3 | 0.0 |
| `test_integrate_engine_tap` | smoke-test | 5 | 0.0 |
| `test_integrate_engine_turn` | smoke-test | 4 | 0.1 |
| `test_integrate_engine_verbose` | smoke-test | 5 | 0.1 |
| `test_integrate_mcp` | smoke-test | 3 | 0.0 |
| `test_integrate_page_build` | smoke-test | 1 | 0.0 |
| `test_integrate_tap_loop` | smoke-test | 1 | 0.2 |
| `test_integrate_echo_loop` | smoke-test | 2 | 0.0 |
| `test_integrate_engine_mcp` | smoke-test | 4 | 0.0 |
| `test_integrate_engine_system` | smoke-test | 5 | 0.0 |
| `test_integrate_main_loop` | smoke-test | 6 | 0.3 |
| `test_integrate_mcp_stdio` | smoke-test | 3 | 0.0 |
| `test_integrate_bootstrap` | smoke-test | 3 | 0.1 |
| `test_mcp_stdio_process` | smoke-test | 3 | 0.2 |
| `test_tap_tty` | smoke-test | 16 | 1.7 |

### A unit

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_tap_producer.ts` | smoke-test | 33 | 0.1 |
| `test_unittest.ts` | smoke-test | 16 | 0.1 |
| `test_harness.ts` | smoke-test | 6 | 0.1 |
| `test_ui_strings.ts` | smoke-test | 2 | 0.1 |
| `test_i18n.ts` | smoke-test | 13 | 0.1 |
| `test_switches.ts` | smoke-test | 5 | 0.1 |
| `test_utility.ts` | smoke-test | 45 | 0.1 |
| `test_jslb.ts` | smoke-test | 35 | 0.1 |
| `test_settings.ts` | smoke-test | 13 | 0.1 |
| `test_dispatch.ts` | smoke-test | 41 | 0.1 |
| `test_http.ts` | smoke-test | 35 | 0.1 |
| `test_media.ts` | smoke-test | 25 | 0.2 |
| `test_provider.ts` | smoke-test | 14 | 0.1 |
| `test_provider_key.ts` | smoke-test | 2 | 0.1 |
| `test_provider_key_unset.ts` | smoke-test | 1 | 0.1 |
| `test_provider_script.ts` | smoke-test | 28 | 0.1 |
| `test_verbose.ts` | smoke-test | 16 | 0.1 |
| `test_wire.ts` | smoke-test | 39 | 0.1 |
| `test_queue.ts` | smoke-test | 51 | 0.1 |
| `test_substrate.ts` | smoke-test | 6 | 0.1 |
| `test_line_case.ts` | smoke-test | 3 | 0.8 |
| `test_mcp.ts` | smoke-test | 31 | 0.1 |
| `test_wire_port.ts` | smoke-test | 27 | 0.1 |

### A integration

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_tap_pair_ts` | smoke-test | 6 | 1.8 |
| `test_integrate_queue.ts` | smoke-test | 8 | 0.4 |
| `test_integrate_http.ts` | smoke-test | 11 | 2.2 |
| `test_integrate_mcp.ts` | smoke-test | 6 | 0.2 |
| `test_integrate_provider_script.ts` | smoke-test | 8 | 0.2 |

### B unit

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_error_overlay.ts` | smoke-test | 9 | 0.1 |
| `test_error_overlay_worker.ts` | smoke-test | 5 | 0.3 |
| `test_overlay.ts` | smoke-test | 24 | 0.1 |
| `test_substrate_limit.ts` | smoke-test | 2 | 1.0 |
| `test_substrate_store.ts` | smoke-test | 61 | 3.2 |
| `test_jslb_decode.ts` | smoke-test | 42 | 7.5 |
| `test_console_view.ts` | smoke-test | 63 | 0.2 |
| `test_media_cache.ts` | smoke-test | 12 | 0.1 |
| `test_script.ts` | smoke-test | 20 | 0.6 |
| `test_worker_ai.ts` | smoke-test | 23 | 0.1 |
| `test_page.ts` | smoke-test | 16 | 0.1 |
| `test_tools_browser.ts` | smoke-test | 23 | 0.7 |
| `test_agent.ts` | smoke-test | 21 | 1.7 |
| `test_boot.ts` | smoke-test | 3 | 0.1 |

### B integration

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_integrate_substrate.ts` | smoke-test | 15 | 0.3 |
| `test_integrate_media.ts` | smoke-test | 7 | 1.1 |
| `test_integrate_worker_ai.ts` | smoke-test | 3 | 0.5 |
| `test_integrate_console_view.ts` | smoke-test | 55 | 6.5 |
| `test_substrate_crash.ts` | smoke-test | 2 | 2.4 |
| `test_integrate_page.ts` | smoke-test | 19 | 0.9 |
| `test_integrate_tools_browser.ts` | smoke-test | 8 | 0.3 |
| `test_agent_faults.ts` | smoke-test | 8 | 2.0 |
| `test_integrate_agent.ts` | smoke-test | 2 | 0.4 |

### C integration

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_wire_end.ts` | smoke-test | 3 | 0.3 |
| `test_integrate_wire.ts` | smoke-test | 4 | 1.1 |
| `test_worker_ai_console.ts` | smoke-test | 2 | 0.1 |
| `test_tools_browser_console.ts` | smoke-test | 19 | 6.5 |
| `test_console_open.ts` | smoke-test | 11 | 4.3 |

### Whole page

| Suite | Label | Tests | Seconds |
|---|---|---|---|
| `test_integrate_xsjs_screenshot` | test-all | 2 | 3.4 |
