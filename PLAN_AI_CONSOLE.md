# PLAN_AI_CONSOLE

The AI's console: the AI worker of the ttyd page owns tty 0, the debug
console on which dash runs in its sandbox, and the AI and the person at the
page share it. Planned on 2026-11-01 by the session of
`tmp/tasks_30_2127.md`, task 3, as the maintainer's answer to Question T12
of `TEST_PLAN_TS.md` requires: a product task planned before any code.

The maintainer's words, the source of every requirement below:

> Question T12: should the AI worker build the console's port? No product
> code builds a wire.ConsolePort or calls console_register, though the stub
> says the worker pushes console.exit.
>
> [x] A. Yes, as a product task planned before any code. Recommended: the
> stub then states what the product does.
>
> The AI APIs use of dash should come with a pre-built TS MCP API. it should
> use the ttyd protocol over the wire so xterm.js can be integrated directly
> without seams. and then the AI should be able to write to/read from the
> console at the same time as the user of the html app. so they can watch
> while it is running, and type commands when it is not.
>
> This is all a part of ttyd that is expected to be leveraged without a lot
> of boilerplate and testing. It should "just work" after a bit of testing.

## 1 What will be accomplished, in order of importance

1.1 The AI worker builds the console's port: the bring up of the ttyd
page's worker makes a `wire.ConsolePort` at the page's address, relays the
UI's `console.open` and `console.close` to it, and pushes `console.exit` to
the UI when tty 0 ends. The stub of `ConsolePort.close_receive` then states
what the product does.

1.2 The AI's use of dash comes with a pre-built MCP API in TypeScript: the
browser's MCP tools of `API/mcp/tools.json`, registered by
`tools_browser.tools_register`, of which `console_run` writes a command line
to tty 0 and reads its output to the next prompt.

1.3 ttyd's protocol over the wire, so that xterm.js is integrated directly,
without seams: each message of tty 0 is relayed unchanged, as one
`console.input` or `console.output` line, between ttyd and the console view.

1.4 One console, two users at once: the AI writes to and reads from tty 0
while the person at the page sees the same screen. The person watches while
the AI's command runs, and types commands when none runs.

1.5 Little code and little testing: ttyd already gives the pty, the shell's
process and the protocol; the page relays and the AI reads, and a few cases
through the real ttyd show it working.

## 2 The console on 2026-11-01

Present, each with its own tests:

1. `wire.ConsolePort` (`ts/wire.ts`): fetches ttyd's token, opens
   `/ws?arg=console`, relays each message of ttyd as a `console.output` line
   and feeds it to its `ConsoleReader`, which answers `console.read` once
   `until` shows in the output or its timer expires; `console.input` lines go
   to ttyd as they are.
2. `console_view.ConsoleView` (`ts/console_view.ts`): xterm.js on the UI
   thread, ctrl 0 to toggle; its first message carries `AuthToken`,
   `columns` and `rows`; typed bytes go out as `console.input`; xterm's
   `disableStdin` is false only while tty 0 is open.
3. `worker_ai.console_register` (`ts/worker_ai.ts`): the relays of the UI's
   `console.open` and `console.close` to the `console` owner.
4. `tools_browser`'s `console_run`: in debug mode, the person's permit, then
   `console.show` to the UI, which opens tty 0, then the command typed as one
   `console.input` and a `console.read` until the prompt `$ `.
5. The lines of `API/ts/lines.d.ts`: `console.show`, `console.open`,
   `console.input`, `console.output`, `console.close`, `console.exit` on the
   ui-ai lane; `console.input`, `console.open`, `console.read` on the console
   lane.
6. bootstrap's console role (`python/bootstrap.py`): dash in its bubblewrap
   sandbox on tty 0, in debug mode only, its root under `/home/`.

Missing:

1. No bring up builds a `ConsolePort`, adds the `console` owner's port or
   calls `console_register`; only the blocks of group C build that path,
   each for itself (`TEST_PLAN_TS.md` 7.8.2 item 4).
2. Nothing pushes `console.exit`, though the UI handles it.
3. The person's typing is not held while the AI's command runs: once tty 0
   is open, the view takes typed bytes whenever they come, so a key pressed
   during the AI's command goes into that command's input.
4. No bring up registers the browser's MCP tools; they run only in the
   blocks that register them (`test_tools_browser`, `test_agent`,
   `test_tools_browser_console`). No program but the test suites runs
   (`API/ts/boot.d.ts`), so the product's MCP server is the tests' until the
   product's start chain exists.

## 3 The design

3.1 The worker owns tty 0 (1.1). `boot.test_worker`, the ttyd page's
worker, builds `new wire.ConsolePort(base_url)` at the page's address once
the wire is up, and hands it to `worker_ai.tap_start` in `TapParts` as
`console`. `tap_start`, given a console port, adds it as the `console`
owner's port, calls `console_register` with the port's `console_close` as
the close function, and registers the port's close function, which pushes
`console.exit` to the UI. `boot.headless_worker` hands no console port:
the headless page has no ttyd, and a `console` line there fails loud as a
line to an owner with no port. The blocks of group C keep their own
topologies, as Question T12 A said.

3.2 One stream, two readers (1.3, 1.4). Every message ttyd sends on tty 0
reaches both the console view, as `console.output`, and the AI's waiting
read, through `ConsoleReader`, as `ConsolePort.message_take` does now. The
bytes are relayed unchanged both ways: no line of the console lane
re-encodes, filters or splits a message of ttyd.

3.3 Turn taking (1.4). While the AI's command runs, the view takes no typed
input; when none runs, it does. Two new pushes on the ui-ai lane, AI to UI:
`console.busy`, which `console_run` sends before it types its command, and
`console.idle`, which it sends when the command's read ends, at the prompt,
at its timeout or at tty 0's close. At `console.busy` the view sets
xterm's `disableStdin` true; at `console.idle`, false while tty 0 is open.
Keys pressed while the AI's command runs are refused by xterm, not queued:
the screen shows the AI's command and its output, and the person types
again once the prompt is back. A partial line the person left typed before
the AI's command is Question C2 (7).

3.4 The MCP API (1.2). `console_run` stays as `API/mcp/tools.json` has it:
one command line in, its output to the next prompt and whether the read
timed out out, behind the person's permit, in debug mode only. Whether the
AI also gets tools that write and read apart, for programs that prompt or
run on, is Question C1 (7).

3.5 What it does not do. No second connection to tty 0 for the AI, no
resize, no second shell; outside debug mode the console role exits 1 and
`console_run` throws `tools_browser.debug_off`, as now.

## 4 Stubs, in the order they change, before any code

1. `API/ts/lines.d.ts`: `console.busy` and `console.idle`, ui-ai, AI to UI,
   no blob, push.
2. `API/ts/worker_ai.d.ts`: `TapParts.console`, a `wire.ConsolePort` or
   `undefined`; `tap_start`'s header, 3.1.
3. `API/ts/boot.d.ts`: `test_worker` builds the port, 3.1.
4. `API/ts/wire.d.ts`: `ConsolePort.close_receive`'s comment, true once 3.1
   is built.
5. `API/ts/console_view.d.ts` and `API/ts/page.d.ts`: the view's input held
   and freed, and the two handlers, 3.3.
6. `API/ts/tools_browser.d.ts`: `console_run` sends `console.busy` before it
   types and `console.idle` when its read ends, 3.3.

## 5 Tests

5.1 Through the real ttyd, in group C, smoke-test: `test_wire.py`'s stock
root already runs its `console` rung on the ttyd page. The rung keeps its
own `wire.ConsolePort`, since the worker's owner table routes
`console.output` to the UI thread, which runs nothing in a wire run; the
page's own port, built by 3.1, stays unopened beside it.

5.2 `test_tools_browser_console` attaches its port by `console_attach`, as
the ttyd page does, and each case of `console_run` expects `console.busy`
and `console.idle` on the `ui` lane between the show and the tool's reply.
The keys a held view refuses are tested in the view's own block (5.3),
since this block's UI is scripted.

5.3 Group B, the unit blocks of `worker_ai`, `console_view` and `page`:
the owner tables route `console.busy` and `console.idle` to the UI; the
view, held, sends no key, freed sends them again, freed while idle still
sends none, and held before tty 0 opens sends none once it is open.

## 6 Status, 2026-11-01

Built by the session of `tmp/tasks_30_2127.md`, task 3, stubs first, as 4
lists them: 3.1, `worker_ai.console_attach`, called by `tap_start` for the
port `boot.test_worker` builds, `TapParts.console` undefined on the
headless page; 3.3, `console.busy` and `console.idle` from `console_run`,
`ConsoleView.input_hold` and `input_free`, and the page's two handlers; and
5.1 to 5.3. Not built: anything Questions C1 and C2 decide; 3.4 stays as it
was. The blocks of 5 passed in the container with `--anthropic`.

## 7 Questions

Question C1: does the AI get tools that write to and read from the console
apart, beside `console_run`?

[ ] A. No: `console_run` alone, one command line to the next prompt, the
read's timeout ending a command that does not return. (Recommended: it
meets "write to/read from the console" for the shell's commands, and 3.3's
turns stay those of whole commands.)

[ ] B. Yes: `console_write`, which types text with no wait, and
`console_read`, which reads to a pattern or a timeout, for programs that
prompt; the console stays busy from a `console_write` until a
`console_read` sees the prompt.

[ ] C. Yes, as B, and `console_run` goes.

Question C2: what happens to a partial line the person left typed when the
AI's command starts?

[ ] A. `console_run` first sends the pty's line kill, `ctrl-U`, so that
dash, reading its line in the tty's canonical mode, gets the AI's command
alone; the person's partial line is lost. (Recommended: the command the AI
meant is the one that runs.)

[ ] B. `console_run` waits until the view reports an empty line, which the
view tracks from what it sent since the last prompt.

[ ] C. Nothing: the partial line and the AI's command run as one line.

## 8 Requirements analysis

The requests are those of the maintainer's answer to Question T12 quoted
above.

8.1 Class A, unsatisfied or modified without cause: none.

8.2 Class B, unsatisfied or modified with cause but without confirmation:

1. "pre-built TS MCP API": read as the browser's MCP tools that exist, with
   `console_run` the console's, and not a new library (3.4, Question C1).
2. "write to/read from the console at the same time as the user": read as
   one shared tty 0 whose output both see, the AI's writes whole command
   lines (3.2, 3.3, Question C1).
3. "type commands when it is not": the view refuses keys while the AI's
   command runs, rather than queueing them (3.3, Question C2).
4. The blocks of group C keep their own topologies, the wire test's
   console rung its own port (5.1), and `test_tools_browser_console`
   attaches its port by the product's `console_attach` (5.2).
5. Keys typed while the AI's command runs are refused by xterm with no
   notice to the person (3.3).

8.3 Class C: none yet.

8.4 Class D, satisfied by the design once built: 1.1 by 3.1; 1.3 by 3.2,
which keeps the relay of today; 1.5 by building on ttyd's own pty and
protocol, with three test places in 5.
