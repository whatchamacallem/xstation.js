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
again once the prompt is back. A line the person left half typed before
the AI's command is kept, unsubmitted, by the answer to Question C2 (3.7).

3.4 The MCP API (1.2). `console_run` stays as `API/mcp/tools.json` has it:
one command line in, its output to the next prompt and whether the read
timed out out, behind the person's permit, in debug mode only. Beside it,
by the answer to Question C1, `console_write` and `console_read` (3.6).

3.5 What it does not do. No second connection to tty 0 for the AI, no
resize, no second shell; outside debug mode the console role exits 1 and
`console_run` throws `tools_browser.debug_off`, as now.

3.6 The tools that write and read apart, by the answer to Question C1:
"[x] B. Add console_write and console_read, for programs that prompt for
input." Each is a browser tool of `API/mcp/tools.json`, in debug mode only,
behind the person's permit and opening tty 0 by `console.show`, as
`console_run` is:

1. `console_write`, the text to type: submits the text to tty 0 and returns
   at once, waiting for no output. It sends `console.busy` before it
   writes, unless the console is already busy from an earlier
   `console_write`. By 3.7 the text is submitted up to its last newline,
   and what follows it is held by the worker until a later `console_write`
   brings a newline.
2. `console_read`, a text to read to and a timeout: reads tty 0's output
   from where the last read ended to the first match of the text, or to
   the timeout, and returns the output and whether the read timed out, as
   `console_run`'s read does.
3. The turn, in the option's own words: "the console stays busy from a
   `console_write` until a `console_read` sees the prompt". A read sees
   the prompt when its output ends with `$ `; it then sends
   `console.idle`. A `console_run` inside such a turn types its line into
   the running program and ends the turn at its prompt, as a
   `console_read` would.

3.7 Lines, by the answer to Question C2, in the maintainer's words: "lines
are only submitted to the console when the AI or the user submits a
newline character. input interleaves at line boundaries using thread
sync." The design:

1. The person's line. The view holds what the person types since the last
   submission and submits it to tty 0 as one `console.input`, its carriage
   return included, when the person types Enter. Until then the view
   echoes the held line itself at the cursor; before it submits, it erases
   that echo, so that tty 0's own echo of the line replaces it. Backspace
   removes the held line's last character. A paste is cut at its newlines:
   each whole line is submitted in order, and the rest is held.
2. Output around the held line. Before the view writes output of tty 0,
   it erases its echo of the held line, and after, it echoes it again, so
   that output never splits the line on screen. From `console.busy` to
   `console.idle` the echo stays erased and the line held; at
   `console.idle` the line is echoed again after the prompt, and the
   person goes on typing it. The view finds its echo by xterm's buffer:
   when it draws the echo it records the echo's start, its row in the
   whole buffer, the viewport's base plus the cursor's row, held by an
   xterm marker, which follows the rows a full scrollback drops, and the
   cursor's column; it erases the echo by moving the cursor to that row
   of the screen, the start's row less the base now, and that column,
   then erasing below. So an echo that scrolls the screen is erased from
   its own start, and no saved cursor of a program is overwritten, as
   the saved cursor first built (ESC 7 and ESC 8) did. Correction of
   2026-11-01, measured by the build: xterm.js 5.5.0 saves that cursor
   as a row of the whole buffer, so the first erase followed a scroll
   and went wrong only once the scrollback was full; it did overwrite a
   program's saved cursor. An echo whose
   start has scrolled above the screen, a held line longer than the
   screen, is erased from the screen's top, and its part above stays in
   the scrollback, which no escape reaches.
3. The AI's lines. `console_run`'s command line ends in its newline, as
   now; `console_write`'s text is submitted up to its last newline, and its
   rest is held by the worker (3.6 item 1).
4. Thread sync. The AI worker, the owner of tty 0's port, is its one
   writer: the view's lines, which reach it as the UI's `console.input`
   lines, and the AI's go to ttyd whole, one message each, in the order
   they become whole. A line of the view that reaches the worker between
   its `console.busy` and its `console.idle`, sent before the view held its
   keys, waits in the worker until `console.idle`, then goes. So a half
   typed line is never joined to the AI's, and never lost.
5. Keys outside a line, Question C3's option A, built: the person's line
   takes printable text and Tab, Backspace edits it and Enter submits it;
   every other control key and escape sequence, the arrows included, is
   dropped by the view, since dash, built without line editing, takes none
   of them. The AI's text goes within its lines as it is. A command that
   does not return is ended by closing tty 0, ctrl 0, as now.

3.8 One command line at a time, by the maintainer's answer of 2026-11-02 to
Question C4, in their words: "Only act on literal newlines sent by the user
or AI and do not inject newlines at console edges. Only submit the command
to the console when the user or AI have submitted the final newline. That
will prevent interleaving of partial commands. do not start the next
command line until the last one is fully concluded." The design:

1. Only literal newlines. A line is submitted by a newline that the person
   types, Enter, or that a paste holds, or that the AI's text holds, and by
   nothing else; the view and the worker never add one. Nothing the view
   does moves the program's cursor to a new row: the erase of an echo that
   started at a pending wrap leaves the wrap pending, as the program left
   it, by writing the filled row's last cell again from xterm's buffer,
   its character and attributes, then the program's attributes, which the
   echo's first cell was drawn with (Question C4's option C).
2. The final newline. A command goes to tty 0 only when its final newline
   is submitted, as 3.7 built: the person's line held in the view, the
   AI's rest held in the worker.
3. The last command concluded. The worker, tty 0's one writer, knows tty 0
   concluded when its output ends with the prompt `$ `, and running from a
   line's submission until then. A turn of the other party starts only on
   a concluded tty 0: the AI's turn, its first line of `console_write` or
   `console_run`, waits in the worker until the person's command has
   concluded, the person keeping their keys meanwhile, and then sends
   `console.busy` and its line; the person's lines wait through the AI's
   turn until `console.idle`, as built. Within a party's own command its
   further lines go at once, as input to that command, so that a program
   that prompts, as `read`, takes its answer.
4. The AI's wait counts against its tool's time: a `console_run` whose
   wait passes its timeout returns `timed_out` with no output and nothing
   sent; a `console_read` within a waiting turn reads from the turn's
   start, once it starts.

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
7. `API/mcp/tools.json`: `console_write` and `console_read`, 3.6.
8. `API/ts/tools_browser.d.ts`: the two tools and the turn of a
   `console_write`, 3.6.
9. `API/ts/console_view.d.ts`: the held line, its echo and its
   submission, 3.7 items 1, 2 and 5.
10. `API/ts/worker_ai.d.ts`: the one writer of tty 0, the view's line held
    through the AI's turn and the AI's rest held to its newline, 3.7 items
    3 and 4.

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

5.4 Group C, `test_tools_browser_console`, through the real ttyd and dash:
a `console_write` of a command that prompts, `read answer && echo got
$answer`, then a `console_read` that times out on the waiting `read`, a
`console_write` of `yes` and its newline, and a `console_read` to the
prompt whose output holds `got yes` and which ends the turn; and a
`console_write` with no newline, held until the next `console_write`'s
newline submits the two as one line. Each expects `console.busy` at the
turn's first write and `console.idle` at the read that sees the prompt.

5.5 Group B, `test_console_view`: the held line echoed and not sent; Enter
submitting it whole with its carriage return, the echo erased first;
Backspace; a paste of two lines and a rest; output while a line is held
leaving the line after it; `console.busy` erasing the echo and
`console.idle` echoing it again; other control keys and escape sequences
dropped.

5.6 The worker's one writer, in the block of the worker's console through
the real ttyd: a line of the view that reaches the worker inside the AI's
turn waits until `console.idle`; the AI's rest held until its newline.

5.7 The reader's keep mode, in `test_wire`'s unit block: `keep_start`
and `keep_stop`; a read ending at its first match, leaving the rest kept
for the next read; a read answered at once from kept text that already
matches; and the refusals `wire.keep_none`, `wire.keep_twice` and
`wire.kept_invalid`, each by the case that throws it.

5.8 The echo's erase, in `test_integrate_console_view`: an echo that
wraps on the screen's bottom row, erased whole from its start after the
screen scrolls; and a program's saved cursor, ESC 7 written before the
person types, restored by the program's ESC 8 after the echo is drawn
and erased, at the program's place.

5.9 The tests of 3.8. `test_integrate_console_view`: an echo that started
at a pending wrap, erased, leaves the wrap pending, so that the program's
next carriage return goes back to the start of the row it filled, and
that row's last cell keeps its character and attributes; each failing
against the erase of 3.7. `test_worker_ai`'s `TestWriter`: the AI's first
line held while tty 0 runs the person's command, then sent after
`console.busy` once the output ends with `$ `; the person's line inside
their own command sent at once. `test_tools_browser_console`, through the
real ttyd and dash: the person's `sleep` running while a `console_run`
waits, which runs once the prompt is back; a `console_run` whose wait
passes its timeout returning `timed_out` with nothing sent.

## 6 Status, 2026-11-01

Built by the session of `tmp/tasks_30_2127.md`, task 3, stubs first, as 4
lists them: 3.1, `worker_ai.console_attach`, called by `tap_start` for the
port `boot.test_worker` builds, `TapParts.console` undefined on the
headless page; 3.3, `console.busy` and `console.idle` from `console_run`,
`ConsoleView.input_hold` and `input_free`, and the page's two handlers; and
5.1 to 5.3. Not built: anything Questions C1 and C2 decide; 3.4 stays as it
was. The blocks of 5 passed in the container with `--anthropic`.

Questions C1 and C2 were answered on 2026-11-01 (`tmp/tasks_30_2127.md`
task 5), and 3.6 and 3.7 planned the same day, to be built by
`TEST_PLAN_TS.md` 7.11 item 5.

Built on 2026-11-01 by the session of `tmp/tasks_30_2127.md`, task 5,
stubs first: 3.6, `console_write` and `console_read` in `API/mcp/tools.json`
and `ts/tools_browser.ts`, 18 tools in all; 3.7, the view's held line and
its echo in `ts/console_view.ts`, erased by xterm's buffer, and
`worker_ai.ConsoleWriter`, tty 0's one writer; the reader's keep mode of
`ts/wire.ts`, `keep_start` and `keep_stop`, which `API/ts/wire.d.ts` now
states, outside the list of 4; the lines `console.write`, `console.busy`
and `console.idle` of `API/ts/lines.d.ts`; and the tests of 5.4 to 5.8:
11 cases in `test_tools_browser_console`, the class `TestWriter` of
`test_worker_ai` with 6, the cases of `test_console_view` and
`test_integrate_console_view`, 11 of them for 5.8, and the class
`TestConsoleKeep` of `test_wire` with 6. Each case of 5.8 failed against
the first erase, ESC 7 and ESC 8, and passes against the buffer's. All the
console and wire blocks passed in the container as `xsjs` with
`--anthropic`, and so did the smoke and normal targets
(`TEST_PLAN_TS.md` 7.11 item 7).

Built on 2026-11-02 by the session of `tmp/tasks_30_2127.md`, task 7,
stubs first: 3.8 and the tests of 5.9. The erase of an echo that started
at a pending wrap writes the filled row's last cell again, a wide
character from its first column, with its attributes as SGR, then the
program's attributes from the echo's first cell; `worker_ai.ConsoleWriter`
knows tty 0 concluded by the prompt `$ `, across split messages, and
holds the AI's turn, its lines and its read, until then. The cases of
5.9: `pending_*` and `wide_*` of `test_integrate_console_view`, six of
`TestWriter`, and `sleep_wait` and `wait_expired` of
`test_tools_browser_console`, each failing against the code before it.
The smoke target passed in 125.899 s of its 180 s.

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

Questions C1 and C2 were answered by the maintainer on 2026-11-01
(`tmp/tasks_30_2127.md` task 5): C1 B, "Add console_write and
console_read, for programs that prompt for input" (3.6); and C2 in the
maintainer's own words, "lines are only submitted to the console when the
AI or the user submits a newline character. input interleaves at line
boundaries using thread sync." (3.7). The same day the maintainer
confirmed this plan's design choices, "[x] A. Confirm all six" of
`TEST_PLAN_TS.md` 11.3 item 20.

Question C3, asked on 2026-11-01 by the session of `tmp/tasks_30_2127.md`,
task 5: which keys may go to tty 0 outside a line? By the answer to C2,
lines go only when a newline submits them, so a key that is not part of a
line has no turn of its own. Dash in its sandbox has no line editing, and
bubblewrap's `--new-session` gives it no controlling terminal, so what the
interrupt `ctrl-C` reaches there is not yet measured.

[ ] A. None, as built (3.7 item 5): the view drops the person's other
control keys and escape sequences, the AI's text goes within its lines as
it is, and a command that does not return is ended by closing tty 0.
(Recommended: nothing goes outside a line, as the answer to C2 says.)

[ ] B. As A, and the interrupt `ctrl-C` goes at once from the person or
from `console_write`, dropping the view's held line as the tty drops its
own, once a measurement shows what it reaches in the sandbox.

[ ] C. The person's control keys and escape sequences join the held line
as typed, and the tty takes them as it would.

Question C4, asked on 2026-11-01 by the session of `tmp/tasks_30_2127.md`,
task 5: where does the cursor go when the echo started at a pending wrap?
A program that writes the last column of a row leaves the cursor there
with its wrap pending; the echo's first character takes the wrap, so the
echo starts at the next row's first column. The erase then leaves the
cursor at that first column, with the wrap taken, so a carriage return,
newline or backspace that the program writes next acts on the next row,
not on the row it filled.

[ ] A. As built: the cursor stays at the next row's first column.
(Recommended: printable text the program writes next lands where it would
have, and only a carriage return, newline or backspace right after a full
row moves.)

[ ] B. The view saves the cursor by ESC 7 and restores it by ESC 8 for an
echo that starts at a pending wrap only, which brings back the overwrite
of a program's saved cursor in that one case.

[ ] C. The erase moves the cursor to the filled row's last column and
writes that cell again from the buffer, its character and attributes, so
that the wrap is pending again as the program left it.

Questions C3 and C4 were answered on 2026-11-02 by the maintainer's
message, "you are asking me about default choices that i made by not explicitly
selecting them. if you keep asking then they are not choices, they are
simply remaining unresolved. please accept my default choices in the
past and consider them actionable." Each takes its option A, the default and the
code as built: C3 A, no key outside a line; C4 A, the cursor left at the
next row's first column.

Corrected on 2026-11-02, the same day: the maintainer marked C3 A, and
answered C4 in their own words, built by 3.8, which leaves no cursor at
the next row (option C) and starts no command line before the last one
concluded.

## 8 Requirements analysis

The requests are those of the maintainer's answer to Question T12 quoted
above, and the maintainer's answers to Questions C1 and C2 and the
confirmation of 2026-11-01 (7).

8.1 Class A, unsatisfied or modified without cause: none.

8.2 Class B, unsatisfied or modified with cause but without confirmation.
Every item here was confirmed on 2026-11-02 (8.3 item 7); the text stays
for the record:

1. Question C1's tools in debug mode, behind the person's permit, opening
   tty 0 by `console.show`, as `console_run` (3.6).
2. "sees the prompt" read as a read whose output ends with `$ ` (3.6 item
   3).
3. A `console_run` inside a turn of `console_write` allowed, ending the turn
   at its prompt (3.6 item 3).
4. "lines are only submitted to the console when the AI or the user
   submits a newline character" read as lines held above the tty, in the
   view for the person and in the worker for the AI, the view echoing the
   held line itself (3.7 items 1 to 3).
5. "input interleaves at line boundaries using thread sync" read as the
   worker the one writer of tty 0, whole lines in the order they become
   whole, and a line of the view that reaches it inside the AI's turn held
   to the turn's end (3.7 item 4).
6. The keys outside a line, Question C3's option A built (3.7 item 5).
7. Output kept only within a turn, from `console.busy` to `console.idle`;
   a `console_read` outside a turn reads from its own start (3.6 item 2).
8. `console_read` returns its output with CR LF made LF and nothing cut,
   the prompt kept; `console_write` returns `{}` (3.6).
9. A read that sees the prompt sends `console.idle` only inside a turn; a
   `console_run` outside one makes its own turn and ends it (3.6 item 3).
10. Each tool asks the person's permit under its own name, and "always"
    allows that tool alone (3.6).
11. `worker_ai.ConsoleWriter` wraps the port inside `console_attach`; the
    AI's text goes as the new line `console.write`, the view's as
    `console.input`, which tells them apart (3.7 item 4).
12. DEL alone is Backspace; ctrl-H, LF and the C1 controls are dropped,
    and an escape sequence is dropped whole (3.7 item 5).
13. The view's held lines are kept across a close of tty 0 until the next
    `console.idle` (3.7 item 4).
14. The cases of 5.6 sit in `test_tools_browser_console` and
    `TestWriter`, not in `test_worker_ai_console`, whose ttyd starts no
    shell.
15. A read that times out waits 0.5 s and a draw 0.2 s, for the smoke
    target's time.
16. The echo's start held by an xterm marker, the view's writes made one
    at a time, each after xterm has parsed the one before, and a start at
    a pending wrap taken as the next row's start (Question C4) (3.7 item
    2).
17. The reader's keep mode added to `API/ts/wire.d.ts`, a stub outside the
    list of 4, with its refusals `wire.keep_none`, `wire.keep_twice` and
    `wire.kept_invalid` (5.7).
18. The decisions of task 7's build of 3.8: `console.busy` and
    `console.idle` reach the UI through a `notify_ui` that
    `console_attach` gives the writer, ahead of the tool's reply; a
    waiting read that times out lapses its turn, which starts again only
    at the AI's next write or read, so that nothing goes after a
    `console_run` that reported nothing typed; a `console.idle` on a turn
    that never started drops the AI's waiting lines; a tty 0 that has
    shown no prompt, at its start or after `console.open`, is running;
    an erased last cell is written again as a blank; a filled row above
    the screen is not restored; the underline's style and colour are not
    restored, since xterm's public cell API gives neither.

8.3 Class C, confirmed on 2026-11-01, "[x] A. Confirm all six" of
`TEST_PLAN_TS.md` 11.3 item 20, once class B:

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
6. Question C1 B and Question C2, answered in the maintainer's words
   (7), with item 3 above kept: the view still refuses keys while the AI's
   command runs, and a line half typed before it is now held (3.7); and
   item 2 widened, the AI writing text by `console_write` too (3.6).
7. 8.2 items 1 to 17, and Questions C3 and C4 at their option A,
   confirmed by the maintainer's message of 2026-11-02, an unmarked
   default being the maintainer's choice:
   "you are asking me about default choices that i made by not explicitly
   selecting them. if you keep asking then they are not choices, they are
   simply remaining unresolved. please accept my default choices in the
   past and consider them actionable."
8. Question C3 A, marked by the maintainer, and Question C4, answered in
   the maintainer's words (3.8), on 2026-11-02.
9. 8.2 item 18, by Question C5, "[A] A. Confirm all three.", and
   Question C6, "[A] A. Accept it, since one cell's underline style
   and colour are the only loss.", the maintainer's message of
   2026-11-03: the edge erase does not restore the underline's style
   and colour.

8.4 Class D, satisfied by the design once built: 1.1 by 3.1; 1.3 by 3.2,
which keeps the relay of today; 1.5 by building on ttyd's own pty and
protocol, with three test places in 5.
