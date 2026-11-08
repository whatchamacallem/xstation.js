# First Demo

The demo runs on this machine, Ubuntu under WSL2, and nowhere else. No
other environment is planned or asked about, by the rule added today.

The demo is the beach head: the first program a person can run. The page
starts, shows the hyperposition, takes a few numbered choices, and the scripted
AI, playing the analyst, answers through the MCP tools over the whole protocol.
No real AI provider is contacted, by the rule added today.

## 1. The demo as the maintainer will see it

1.1. In WSL, from the checkout: `python3 python/xsjs_serve.py --debug`. It
builds the engine page, makes a root in `~/.cache/xsjs/root` as the Windows
start script makes one, serves it through the ttyd the project built on
127.0.0.1 port 5769, and prints the address. It keeps serving until ctrl C. A
root seeded before the image of 1.3 and the answers of 1.4 keeps its old seed,
so `--fresh` is needed once to see them.

1.2. In a browser on Windows: `http://localhost:5769/`. WSL2 forwards localhost
to WSL's own ports, so no Windows script runs.

1.3. The page is black. At the bottom is the subtitle band with the analyst's
remark from the seed, "How can I help you?", and a text box. The picture area
above it shows the hyperposition's image, 4 px by 4 px and black, scaled up as
a black square. The `render` tool calls of the choices below name no image, so
the first of them hides the picture, and the page stays black until the next
load.

1.4. Type a number and Enter. The analyst, played by the scripted AI, answers.
Each answer goes through the MCP tools and ends in the band:

| Choice | What the analyst does | What crosses the protocol |
|---|---|---|
| 1 | Shows a subtitle through the `render` tool, then answers in text | The MCP request and result, the render on the UI lane, the turn's rows to the server |
| 2 | Writes a note under the metaverse with `kv_put`, reads it back with `kv_get`, then answers | The same, plus the `kv.put` commit over the wire, which the server's database then holds |
| 3 | Asks to run `echo hyperposition` in the console with `console_run`, then shows the output | The permit request with its Accept, Deny and Always Allow buttons, the console shown, dash in its sandbox, the output read back |
| 0 | Answers in text, calling no tool; in debug mode both sides' databases go into the audit first, by AUDIT_PLAN.md | The provider request and reply, and in debug mode `db.dump` |

The choices are the same at every step, so they can be taken in any order and
as often as wanted. Any input the table does not hold, another number, a word,
an empty line or a click on the picture, is a person's error and not a fault:
the analyst answers it in the band, the choices stay as they were, and the box
opens again.

Choice 3 ends the same way when its command does not run. On a root served
without `--debug` the console tools work in debug mode only, so no permit is
asked and no console shows. After a Deny no console shows. In both the analyst
says so honestly in the band, and the turn ends normally.

1.5. ctrl 0 shows the console, dash in the bubblewrap sandbox, where the
maintainer types too; ctrl 0 again hides it. ctrl 1 shows the end of the
audit, by AUDIT_PLAN.md.

1.6. In debug mode everything that crossed any lane is in the root's audit,
by AUDIT_PLAN.md: `less ~/.cache/xsjs/root/_audit.txt` reads every JSLB line
once, laid out for a person, from both threads of the page and from the server,
with each task's sleep and the console's start and end. The record belongs to
one serve: each start of the serve program begins a new audit, and the last
serve's stays readable until then.

1.7. Before 1.1, `python3 python/test_demo.py` proves the page is ready: it
serves a fresh root the same way, drives chrome-headless-shell through DevTools
over the steps of 1.3 to 1.6, saves a picture of each, checks the log, leaves
the page and checks the server ended. It is also a check of `./test_posix.sh`.

## 2. Requirements

The maintainer's words of 2026-11-06, numbered for reference below.

- R1. Load the hyperposition page myself.
- R2. See a black square subtitled with the therapist's response.
- R3. Make a few numeric multiple choice selections.
- R4. Over the end to end protocol.
- R5. Talk to the fake AI that is using the MCP to talk to me.
- R6. Log all the JSLB in all of the comms involved.
- R7. Scrutinize it.
- R8. The consoles working in that smoke test too.
- R9. Debug this progress using a headless Chrome DevTools connection.
- R10. The best debug stories for bringing up the whole system for a smoke test
  of the app showing the user a dummy AI API.
- R11. Use the Chrome DevTools to prove the smoke test webapp is ready for me
  to view, even if it doesn't change the picture and just has a few simple
  subtitle responses.
- R12. A real AI provider is never tried as part of a testing run, and the
  rules say so, so the question is not asked again.
- R13. A plan to see the service pass non-trivial integration tests before an
  AI endpoint is asked to debug it.
- R14. The current environment is the only one of interest, and the rules say
  so, so no question about another platform is asked. The demo runs on WSL
  only.
- R15. The line count is a real gate: fix the driver bug, work through the 15
  gaps, then add it to `--test-all`.

R12 and R14 are done: both rules are in the Testing rules of the project as of
this session. The rest is this plan.

The maintainer's words of 2026-11-07, answering the questions of the run
before, numbered on from R15.

- R16. Test time limits: the test that ttyd dies with its parent moves to a
  suite of its own in the full run. The default run stays fast, but the
  guarantee is proved only in the full run.
- R17. API type check: add a config listing every API file and a build step
  that compiles it. This meets the plan, costs one more compile, and may show
  many mismatches at first.
- R18. Reload against the engine's lock: wait a few seconds for the lock. This
  closes the race, but a real second tab takes that long to show its fault.
- R19. A full debug log: start a new log at each serve. It needs no option, but
  the old record goes at each start.
- R20. Choice 3 without `--debug`: have the tool answer the AI with an error
  and let the turn go on. This changes the rule that a failing tool fails the
  server, for this one refusal.
- R21. Update the docs to say that bad user input is an exception to the fail
  early and fail entirely design. User error interacting with the web page is
  not an exception class error, instead it is expected and designed for.
- R22. The engine outside debug mode: leave it. The demo runs in debug mode.
- R23. Images from end to end: add a scene with an image to the integration
  block. It proves the whole path, and adds a seeded image and run time. A 4px
  x 4px black image for the hyperposition scene is fine.

## 3. What exists and what is missing

The status report found that every piece is written and tested, and that only
the test suites start them. Reading the pieces against the requirements gives
the gaps below. Each row names the modules by their English role, with the
file in brackets for reference only.

| Requirement | In the tree | Missing |
|---|---|---|
| R1 serve the page | The Windows start script serves the test page; the screenshot tool serves a debug root under `build/` through ttyd and leaves | A POSIX program that serves a root and stays; an engine page: the only page templates are the test page and the headless page, and neither holds the picture, the band, the box or the permit area |
| R2 first render | The UI handler of `render` paints the image or black, shows the subtitle and opens the box (`ts/page.ts`); the server seeds the hyperposition scene, the analyst's prompt and the bootstrap script into a new root (`python/main_loop.py`) | A start chain: after the first line, `tap.start`, and its reply, nothing follows. The server has the lines of a whole database (`python/engine_db.py`, `restore_lines`) and the browser's store applies them (`db.restore`, `db.file`), but nothing sends them, so the browser's store is empty and no scene can render. No program builds the store, the tools, the clients or the agent on the worker, and nothing builds the page's parts on the UI thread |
| R3 numbered choices | The scripted provider takes the decimal text of one integer as the player's message and walks a table of nodes (`ts/provider_script.ts`); the DOM port turns the box's text into `ui.input` and the UI handler into `ai.say` | The seed script is empty: one node with no replies (`python/seed/provider_script.json`). Nothing adds the scripted port to the worker's queue |
| R4 end to end | Every lane is built and tested: DOM, UI thread, AI worker, provider port, MCP client and server, store, wire, ttyd, server store; the agent integration test runs a whole turn on real parts behind a test's own far ends | The same parts joined on the real page, with the real server at the far end |
| R5 MCP talk | The `render` tool shows a subtitle; the agent runs every tool call of a reply and stores the reply with its results | A script that calls `render` and the other tools |
| R6 log every line | In debug mode the wire's tap logs each wire line in full; each queue logs every submit, dispatch, notify, forward, reply, receive, sleep and wake; the server logs each dispatch and reply; the page's lines reach the server's `_verbose.sqlite` as `verbose.put` batches | The queues and the server log only the header of a line, so the ui-ai, provider, MCP, console, DOM and media lanes are recorded as types and ids, not as JSLB. The maintainer's R14 and R16 of AUDIT_PLAN.md replace it with the audit |
| R7 scrutinize | The browser test reads `_verbose.sqlite` for its own checks; the `verbose_tail` tool reads a thread's ring | A program that prints the timeline for a person, with filters and a follow mode. The maintainer's R14 and R16 of AUDIT_PLAN.md replace it with the audit |
| R8 consoles | The console view, tty 0, the console role's sandboxed dash, the writer, the console tools behind permits and the ctrl 0 and ctrl 1 keys, all tested in group C | The console on the real page, in the demo and its test |
| R9, R11 DevTools | The DevTools client and the pipe to chrome-headless-shell (`python/devtools.py`), used by the driver, the browser test and the screenshot suite | A driver of the demo |
| R10 debug stories | The fault screen with cascades, the overlays, the console, the verbose rings, the trace of synchronous loads, the pause of a worker in the debugger | Section 4.8 names each story and what it is for |
| R13 integration before an endpoint | The agent's integration tests on the headless page | The engine's integration test in group C and the demo test |
| R15 line count | The counter and the driver's `--coverage` mode | The driver's mapping of one suite, the 15 gaps, the mode in the full run |

## 4. Design, top down

The order of this section is the order a line takes at a page load: the wire
first, then the worker, the page, the script, the record of it all, and the two
programs around it.

### 4.1. The start chain on the wire

4.1.1. Today the engine role writes `tap.start`, the settings and the switches,
reads the Empty reply and runs the main loop, which waits for lines. The
browser answers and waits too. The store protocol moves a whole database only
as blobs: a `db.restore` line with the database file as blob 1 and `files`
set, then one `db.file` line per cache file. The server can build these lines
and the browser's store applies them. Nothing sends them.

4.1.2. One new request, `db.sync`, on the wire from the AI worker to the
server, with no blobs and no payload. The server answers it with the whole of
every database it holds but its own `_verbose`: for each database in name
order, its `db.restore` line and its `db.file` lines, then the reply,
`DbSyncReply`, whose one field `databases` names them in that order. The
browser's queue runs the pushes in the order they come, before the reply, so
the task that wakes on the reply finds every database restored and checks the
list against its own. No count and no end marker is needed: the reply is the
end.

4.1.3. The browser pulls, the server does not push, so that every suite and
rung that exists sees no new line: none of them sends `db.sync`.

4.1.4. On the server a handler may now return a `dispatch.Stream`: the pushes
the main loop writes in order, then the reply. It is the twin of
`dispatch.Failure`, which is a reply then a raise. The handler of `db.sync` in
the database handlers (`python/engine_db.py`) returns one, built from the
store's snapshots. The TAP run's stream (`python/tap_loop.py`) stays as it is.

4.1.5. The sync stays lossy by design, as the Databases rules require. The
browser's store is rebuilt from the server at every page load, and nothing is
reconciled. The server is the record.

4.1.6. The whole order at a page load: `tap.start`, its Empty reply; the
worker's program then handshakes with the browser's MCP server and, over the
wire, with the server's MCP server, `initialize`, `initialized`, `tools/list`
each; then `db.sync`; then the first render.

### 4.2. The worker's program

4.2.1. A new TypeScript module, `engine`, with three functions: the worker's
program, the UI thread's program, and the entry of the engine page, which runs
on both threads and picks by the thread's name as the test page's entry does.

```text
declare namespace engine {
  // The worker's program, run by the bring up once tap.start is answered.
  function worker_run(tasks: queue.TaskQueue, start: boot.WorkerStart): void;
  // The UI thread's program, run by the bring up at settings.set.
  function page_run(tasks: queue.TaskQueue): void;
  // The last script of the engine page, on both threads, by self.name.
  function engine_start(): void;
}
```

4.2.2. The worker's program is a chain of tasks, each piece a function of its
own for the unit suite:

1. The store: the browser's store on the engine's pool, cleared at start, its
   sizes from the settings, `overflow_bytes`, `blob_max` and
   `turn_compact_turns`, under the root `/engine`, with its handlers
   registered: the UI thread's store requests and the server's restore lines.
2. The tools: the browser's MCP server with the browser tools registered on
   it, the handler of the `mcp` line, a client of it under the prefix
   `browser`, and a second client, of the server's MCP server over the wire,
   under the prefix `server`, so that the agent lists the two server tools the
   prompt names. Both clients in one client set; the agent registered with the
   provider owner `http`.
3. The provider port: the demo runs in scripted mode, the setting
   `provider.scripted` true, the only mode this plan builds. The script is the
   row `/_files/provider/script.json` of the restored store, so the port is
   built in the task that wakes on the sync's reply: a scripted port from that
   script, added as the `http` owner. The scripted port reads no key, and the
   provider door throws without one, so the program sets the key to the fixed
   text `scripted`. The real provider's path is kept whole in 4.10.1 and not
   built.
4. The chain: a push of the worker to itself, `engine.start`, whose handler
   starts the browser client's handshake; a wake per step, `engine.initialized`
   and `engine.listed` for each client; then `db.sync` with the wake
   `engine.synced`; then the first render with the wake `engine.rendered`. The
   render reads the current world from `/metaverse/world`, the current scene
   from the world's `scene` row, the scene document's `subtitle` and, when it
   has one, its `image`. A scene with an image first stores the image with the
   UI thread, `media.store` of its bytes with the wake `engine.stored`, as the
   UI's cache is empty at a load, then submits `render`; a scene with none
   submits `render` at once. The UI thread paints the hyperposition's image,
   shows the subtitle and opens the box.

4.2.3. Two changes to the bring up. The worker's `tap_start` runs its `run`
function in every mode, at once after the Empty reply, instead of only in
debug mode through the `worker.tests` notice: the program must run outside
debug mode too. The two test pages keep their suites in a task of their own:
their entries notify `worker.tests` to themselves in debug mode, as the bring
up did for them. The boot gains the engine worker's bring up, the same as the
test worker's on the pool `xsjs-engine-pool`, its directory
`.xsjs-engine-pool`, the cache `xsjs-engine-cache`, a capacity of 64 files and
cleared at start; and `TestStart`, what the worker's run gets beside its queue,
becomes `WorkerStart`, as it is no longer the tests' alone. The sentence of the
boot's contract that no program but the test suites runs goes.

4.2.4. The seed's hyperposition scene names an image, 4 px by 4 px and black,
the file `python/seed/hyperposition.bmp`. The server's seeding
(`python/main_loop.py`) reads the file and writes the row
`/metaverse/image/hyperposition` before the documents, and the scene document
(`python/seed/hyperposition.json`) gains the header key 1 holding that ref, and
`image` holds `{"$ref": 1}`, as the seed is written in the encoded form, since
`doc_put` stores a body as given. The canvas then shows a black square, which
is R2 taken literally. A root seeded before this keeps its old scene and its
old table, as the seed goes into a new root only: `--fresh` is needed to see
the image or the answers of 4.4.2, and until then an input the old table does
not hold still ends on the fault screen.

### 4.3. The UI thread's program and the engine page

4.3.1. A new template, `html/engine.html`, built as
`build/hyperposition-engine.html` by `python3 python/page_build.py engine
hyperposition-engine`, the name the Windows start script already serves. Its
body, in the layout the engine's style sheet already describes: the debug
views at the top in `div#debug`, holding the console view's container and the
overlays' container; the picture, `canvas#image`, hidden until a render names
an image; the band at the bottom with the subtitle, `p#subtitle`, and a form
holding the text box, `input#input`, disabled until the first render; and the
permit area, `div#permit`, where the Accept, Deny and Always Allow buttons
appear. The scripts are the test page's, with `engine.engine_start()` last and
no `pre` for a TAP stream. The style sheet gains the one rule that keeps the
box visible in the band, since unintentional invisibility is a bug, and
nothing else.

4.3.2. The UI thread's program builds the page's parts from the document: the
DOM port as the `dom` owner, which turns the box's text, clicks on the picture
and ctrl digits into lines and shows the permit buttons; the media port as the
`media` owner, with the budget `media_db_bytes` and the provider's
`timeout_seconds` as its timer; the console view on its container; the
overlays on theirs with the ring `verbose_ring`; then the UI handlers
registered with those parts. The page's bring up gains `engine_page`, which
runs its function at `settings.set`, where the test page's waits for
`ui.tests`.

4.3.3. A typed number and Enter becomes `ui.input` on the DOM lane, `ai.say`
on the ui-ai lane, the provider request on the provider lane, the reply's tool
calls as `mcp` lines, each tool's own lines, the turn's rows as commits over
the wire, and the end of the turn back to the UI thread, which shows the
subtitle and opens the box again. These handlers all exist.

4.3.4. A person's actions on the page end on no fault screen, by R21, in four
more places. The box closes in its own submit and click listeners, as well as
when its turn starts, as the queue's next step comes too late: a second Enter
or click on a busy UI thread would start a second turn, which the scripted
provider refuses. The UI thread's program sets the box's `maxLength` to
`line_max` over 8, so that a paste past it is cut and the turn it says fits one
line, at JSON's worst of 6 bytes a character and the line's own overhead. In a
window too short for one row the console leaves one row, as a short window is a
person's choice, where ctrl 0 or a resize used to throw. `console.show` on a
view that is not idle, as when ctrl 0 has just asked for tty 0, is answered at
once, as tty 0's writer holds the AI's lines until dash's prompt, and only an
idle view sleeps until tty 0 opens. So the refusal `page.console_busy`, which
ended that case on the fault screen, and the view's `open_is`, which then had
no caller, are gone.

### 4.4. The scripted analyst

4.4.1. The scripted provider walks a table of nodes: each node answers each
input it holds with a reply, which may call tools and names the node to be in
once their results are back, and a node reached by tools holds the reply that
follows them, `after_tools`. A node may also hold `otherwise`, the reply to any
input it does not hold. A node reached by tools may hold `after_holds`, a text
every tool result of the reply must hold for `after_tools` to follow, with
`after_lacks`, the reply when one does not. The seed of the table, which the
server writes into `_files` of a new root, is the file
`python/seed/provider_script.json`, which today holds one empty node.

4.4.2. The demo's table has two nodes, `start` and `menu`, with the same four
inputs and the same `otherwise` in each, so that the choices are the same at
every step:

| Input | Reply | Tool calls, in order | After the tools | Next node |
|---|---|---|---|---|
| 1 | no text | `browser.render` with a subtitle | text | `menu` |
| 2 | no text | `browser.kv_put` on `/metaverse/demo/note`, `browser.kv_get` of it | text | `menu` |
| 3 | no text | `browser.console_run` of `echo hyperposition` with a timeout | `browser.render` with the output's subtitle, then text, when the tool's result holds `hyperposition`, by `after_holds`; else text alone, by `after_lacks` | `menu` |
| 0 | text | none | | `menu` |
| any other, `otherwise` | text naming the choices | none | | `menu` |

The texts are the analyst's, bored and British as the prompt describes her,
and they are the maintainer's to edit in the seed. The first screen shows the
seed scene's remark alone; the choices are this table's. An input the table
does not hold is a person's error, which the Errors rules expect and design
for, so the analyst answers it. `otherwise` takes a number outside the table, a
word, an empty line or a click on the picture, whose message is the text
`agent.click_text`. The scripted provider's refusal stays only for a table
holding no `otherwise`, a test's own script, where an input it lacks is a bug
of the test: it fails the worker loud and shows the fault screen with the
cascade, as the Errors rules require. A content that is not a string stays a
refusal in every table, as no person can send one.

4.4.3. The texts of the demo test's gold pin the subtitles, so a change of the
seed changes the gold. A test of the seed's coherence runs beside the server's
seeding tests: every `next` names a node, every tool call names a browser tool
of the tool list with its prefix, every argument is a JSON object, every node
with replies holds `otherwise`, `after_lacks` is wherever `after_holds` is, and
the demo's inputs lead where this table says.

4.4.4. The console tools (`ts/tools_browser.ts`) work in debug mode only. On a
root served without `--debug` all three answer the AI with an error result
holding the refusal's text, in the form of a permit denial, in place of
throwing, so that the turn goes on. The rule that a tool that throws fails the
server stays for every other throw. The error mark of a result does not reach a
chat message, and a real provider's format has no such field, so the scripted
provider sees only the tool's text and the analyst reads it as a real AI would:
`after_holds` of the node reached after the console is `hyperposition`, and its
`after_lacks` answers a refusal, a Deny and a command whose output lacks the
text alike. A read that timed out after dash printed the word holds the text,
so it follows `after_tools`.

### 4.5. Every line on every lane, recorded

AUDIT_PLAN.md replaces this section: the timeline, the wire tap, the overlay of
tty 1 and `_verbose.sqlite` in debug mode are gone, and the audit,
`_audit.txt`, records each line once.

4.5.1. The lanes a turn crosses: ui-dom, ui-media, ui-ai, the worker's own
lines to itself, the `mcp` lines between the agent and the browser's MCP
server, ai-http to the scripted provider, ai-console to tty 0, ai-server over
the wire, and the server's own dispatches. In debug mode every one of them is
already noted in the timeline of the thread that sent or received it, by the
queue on the page and by the main loop on the server, and every page line
reaches the server's `_verbose.sqlite`. What is noted is the header alone, so
the record is of types and ids, not of JSLB. Only the wire's tap renders the
whole line.

4.5.2. The change: in debug mode the queue's timeline lines, submit, dispatch,
notify, forward, reply, receive, sleep and wake, carry the line's full
rendering, the JSON text with one tag per blob whose header carries the blob's
size and key, by the one line renderer; the server's dispatch and reply lines
likewise. A line whose entry would not fit one `verbose.put` below `line_max`
is noted as its header and the sizes of its payload and blobs, as the wire's
tap does today. Blob bytes are never logged: a console message's bytes are in
the console view and a value's bytes are in the store. The wire's tap stays,
as it feeds the overlay of tty 1.

4.5.3. The record is the root's `_verbose.sqlite`, the table `line` with
`seq`, `at`, `thread` and `text`, written by the server for its own lines and
for each `verbose.put` batch of the page's two threads. Nothing new is written;
what is written becomes complete.

4.5.4. The tool: `python3 python/xsjs_log.py ROOT [--thread ui|ai|server]
[--type TYPE] [--grep TEXT] [--follow]`, standard library only, reads the file
read only and prints one line per entry, `seq at thread text`, in `seq`
order, the order the server wrote them. `--follow` keeps reading as the file
grows, as the wire test reads a TAP file. Its module function, `lines_read`,
serves the demo test's check of the log. The root is `~/.cache/xsjs/root` for
the serve program and `build/test_demo-*/root` for a failed demo test, which
keeps its root.

### 4.6. The serve program

4.6.1. `python3 python/xsjs_serve.py [--debug] [--verbose] [--port N] [--root
PATH] [--fresh]`, standard library only, the POSIX start that stands alone
from the Windows scripts, as the Testing rules require. It builds the engine
page, makes the root, which begins a new log, and serves it through ttyd,
prints the address, and keeps serving until SIGINT or SIGTERM, when it stops
ttyd's process group and exits with ttyd's code. ttyd's log goes to stderr as
it comes.

4.6.2. The root, `~/.cache/xsjs/root` unless `--root` says otherwise, is made
as the Windows start script makes one: the server's runtime modules and the
seed from `python/`, `i18n/en-US.json`, `settings.json`, `provider.json`, the
page, and `parameters.json` from the switches. It is kept between runs, so the
maintainer's databases persist; `--fresh` removes it first. The log alone does
not persist: each run removes `_verbose.sqlite` and its `-wal` and `-shm` files
when they exist and keeps every other file, so each serve begins a new record,
and the last serve's stays readable by the log tool until the next start. Only
a serve does this: a page load within one serve adds to the same log. A log
that reaches `blob_max` still fails the server, and the cure is a new serve,
which costs the old record and no database. The engine's lock in the root means
one page per root. The engine role (`python/bootstrap.py`) waits up to 5 s for
the lock, so a reload that reaches the server before the old one has exited
takes it once the old one is gone. A second connection, as a second tab, waits
those 5 s, then fails loud on the server's side and shows the fault screen.

4.6.3. ttyd is the one the project built, `build/ttyd/ttyd`, with the start
script's options: the port from the settings, 5769, on the bind address
127.0.0.1, writable, origin checked, the terminal type, the page as the index,
the URL argument, the receive chunk, running the root's `bootstrap.py` on the
root. The programs it starts, ttyd and through it Python, are those the tests
and the screenshot tool already start.

4.6.4. The demo test makes its roots and starts its ttyd through this
module's functions, so what the test proves is what the maintainer runs.

### 4.7. The demo test over DevTools

4.7.1. `python3 python/test_demo.py [--test-all]
[--anthropic] [--debug] [--verbose]`, a check after the stream of the driver,
after the browser test, with its timers, window size, texts and log table in
its own gold, `python.test_demo`. It drives chrome-headless-shell by the
project's DevTools client, rung by rung, each under a timer and labelled, a
picture of each state saved to `build/test_demo/`. The roots go when the run
passes and stay when it fails.

4.7.2. The rungs, with their labels:

| Rung | Label | What it proves |
|---|---|---|
| served | smoke-test | The page builds, the root is made, ttyd answers, the page loads, and the first render shows: the band holds the seed's remark, the box is enabled, the picture is shown, 4 by 4, its pixels black. Picture saved |
| choice 1 | smoke-test | Typing 1 and Enter ends with the analyst's first text in the band, the box enabled again and the picture hidden. Picture saved |
| choice 3 | smoke-test | Typing 3 shows the permit text and its three buttons; Accept shows the console view; dash's rows hold the prompt and `hyperposition`; the band holds the analyst's text. Picture saved |
| bad input | smoke-test | Typing a number outside the table, then a word, then an empty line, each ends with the analyst's `otherwise` text in the band and the box enabled and holding the focus; a choice then still answers |
| choice 2 | test-all | Typing 2 ends with its text; the server's metaverse database holds the note's row, read directly from the file as the browser test reads values |
| console | test-all | ctrl 0 hides the view and shows it again; `echo hello` typed into the terminal's input shows `hello` in a row. Picture saved |
| overlay | test-all | ctrl 1 shows the wire overlay holding a sent and a received line; ctrl 1 hides it. Picture saved |
| log | smoke-test | The root's `_verbose.sqlite` holds each fragment of the gold's table, one per lane and direction a turn crosses, the media lane that the first render's image crosses, and the bad input rung's inputs and answer, with its JSLB; the log tool's function reads them |
| left | smoke-test | about:blank ends the page; the server's `bootstrap.py` under ttyd ends; ttyd stops; the root goes |

4.7.3. The core rungs are smoke-test so that the default run proves the demo;
the three test-all rungs keep the default run within its three minutes. The
smoke run is about 100 s today, so the budget is measured when the test exists.
The bad input rung comes after choice 3, so that the rungs before it keep their
line ids. For the same budget the suite that proves ttyd dies with its parent,
which makes two real page builds, is a suite of its own in the full run only,
so that guarantee is proved only there.

4.7.4. `--hold`: after a failed rung the test leaves the page, keeps ttyd
serving the root, prints the address and waits for ctrl C, so that a person
opens the failed state in a browser: the root's databases hold the state and a
fresh page load restores it from the server.

4.7.5. The engine's integration block in group C, in 5.3 below, proves the
same turn on the headless page, a scripted UI in place of the person, and the
demo test proves it on the engine page. The block's scene holds the seed's
image: its scripted UI uses the real page handlers of `render`, `media.store`
and its wake, and a real media port on real elements, so that the block proves
the whole path of an image, from the server's database to the canvas. Together
with the wire rung of the sync they are the non-trivial integration tests of
R13.

4.7.6. No test serves the engine outside debug mode, so that mode stays
unproven, by the maintainer's choice in R22: the demo runs in debug mode. The
answer to choice 3 on a root served without `--debug`, in 1.4, is therefore
proved only below the engine, by the suites of the console tools and the
scripted provider.

### 4.8. The debug stories

Each story says when to use it and what it gives. An AI debugging the system
from inside the AI endpoint is not among them.

1. Prove it: `python3 python/test_demo.py`. Exit 0 with a picture of each
   state in `build/test_demo/`, or the first failed rung by name, its picture,
   the kept root and, with `--hold`, the page served for a look.
2. Serve it: `python3 python/xsjs_serve.py --debug`, the address, ttyd's log on
   stderr, ctrl C to stop. Each start begins a new audit, which is also the
   cure for an audit that has filled.
3. Read the audit, by AUDIT_PLAN.md: `less ~/.cache/xsjs/root/_audit.txt`, or
   `build/test_demo/audit.txt` after a demo test, every line of every lane
   once, each task's sleep and the console's start and end, laid out for a
   person, in the order the server learned of it; `tail -f` follows it; typing
   0 adds both sides' databases at that moment. This is the one record of a
   serve, readable until the next start of the serve program removes it: what
   the UI thread sent the worker, what the worker asked the provider, what the
   provider answered, each tool call and result, each commit, each reply.
4. On the page: ctrl 1 shows the end of the audit; ctrl 0 shows the console,
   where the maintainer or the AI runs commands in the sandboxed dash; a fault
   replaces the screen with its message, its stack and each cause's, with a
   Reload, and the same cascade is in the audit's `error` line.
5. From the AI's side: the `audit_tail` tool reads the end of the audit, the
   `script_debug` tool traces every store call of a script, and `console_run`
   runs a command behind the permit.
6. From DevTools by hand: a scratch driver through the DevTools client opens
   the page, reads the band, the box and the permit area by evaluating script
   on the page, follows the console, saves pictures, traces synchronous loads
   on the UI thread and pauses the AI worker in the debugger.
7. The suites: `--module NAME` runs one suite or block; `--debug` runs the
   smoke run with every line logged; the TAP streams name the first failure.
8. The server alone: `python3 python/test_wire.py` proves the wire, the sync
   among its rungs, with no browser program at all.

### 4.9. The line count gate

4.9.1. The driver's mapping lacks the suite of the store's limit, so a full
count looks for a module that does not exist. The fix is one row: that suite
counts for the store module.

4.9.2. Fifteen modules have a line never counted, the first of each known from
the status report:

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

Each gap is one of three kinds, decided by reading it: untested code, which
gets a test; code that runs only in a forked child or a started program, which
the counter cannot see and which gets the counter's exemption mark on its
statement with the reason beside it; or dead code, which goes. The full run
with the count is repeated until it passes, one gap at a time, since the count
stops at the first.

4.9.3. Then `./test_posix.sh --test-all` passes `--coverage` to the driver.
The default run does not, and the tty run stays separate, as the count refuses
it. The full run's time is measured before and after, since the counter's
events cost.

### 4.10. Deferred designs, kept whole

Nothing here is built by this plan. Each is written out so that it is not
lost.

4.10.1. The real provider. The engine role reads neither the provider file nor
the key's variable today. The design: the engine role reads `provider.json`
of the root and the variable the settings name, `XSJS_PROVIDER_KEY`, from its
environment, which the serve program and ttyd pass on; when `provider.scripted`
is false it pushes `provider.set`, on the wire from the server to the AI
worker, no blobs, with `base_url`, `chat_model`, `image_model` and `key`, at
once after the Empty reply to `tap.start`, before the program sends anything.
Both the wire's tap and the server's log write that one line as its header
only. The worker's handler sets the key in the provider door, keeps the three
names for the agent and the image tool, and the `http` owner becomes the HTTP
port with the provider's `timeout_seconds`. The request format against xAI is
then checked by the maintainer, by hand, with their key, outside every run, by
the rule.

4.10.2. The browser's store across page loads. It is cleared at each load and
rebuilt by the sync. Keeping it would need no new line: the sync is lossy by
design. It would need a choice of which side's copy wins for a database both
hold, which is a question for when the server is not the only record.

4.10.3. The Windows start script serves `build/hyperposition-engine.html`,
which `page_build.py engine hyperposition-engine` builds once the template
exists, in place of the `test` template its document names today. The script
does not change; its document's build command does. Windows is not proven
here, by the rule.

4.10.4. The media port's timer is the provider's `timeout_seconds`, since the
images it fetches are the provider's. A setting of its own comes when images
come from elsewhere.

4.10.5. Pictures: the seed holds one, the hyperposition's black image of 4.2.4,
which the first render shows. `image_make` with the scripted provider's test
pattern works end to end, as the agent's integration test proves. The demo's
script does not call it, and its `render` calls name no image, as the
maintainer accepts no picture change; one more reply in the table would show
the pattern.

## 5. Stages, in order

Each stage writes its API text first, then its unit tests, then its code, then
its integration tests, and ends with `./test_posix.sh` passing and nothing
staged or committed. The order is bottom up: the record first, so that every
later stage can be read in the timeline; the server before the browser; the
browser's worker before its page; the two programs last; the line count after
the beach head, since it adds no feature and the maintainer's order put the
beach head first.

### 5.0. The APIs

The line types `db.sync` and its reply, with `provider.set` written as
deferred; `dispatch.Stream` on the server; the sync handler of the database
handlers; the main loop writing a stream; the worker's `tap_start` running its
function in every mode; the boot's engine worker and `WorkerStart`; the
`engine` module; the page's `engine_page`; the queue's full renderings; the
serve and log programs' public functions; the scripted provider's `otherwise`,
`after_holds` and `after_lacks`; the page builder's `api_check` and `tsc_run`;
the new strings. Proof: the source checks of the whitelisted files pass on the
API files, and the type check of the TypeScript API passes: the config
`ts/tsconfig.api.json` lists every file of `API/ts` by name,
`page_build.api_check()` compiles it through `page_build.tsc_run` as a source
check (`python/test_posix.py`), and a unit test checks that the config lists
exactly those files. That compile proves the API text against itself. Beside
it, `api_match.text_match` proves the text against the code, by decision 25. A
mismatch leaves the code's own blocks running first in the default run only, by
decision 23. No code.

### 5.1. The record

The queue's timeline lines in full, with the golds of the queue's unit and
integration blocks updated; the main loop's dispatch and reply lines in full,
with its unit suite; the log program with a unit suite that writes a
`_verbose.sqlite` through the server's own log functions and reads it back,
follow mode included, and an integration suite that runs the program on such a
file. Proof: the default run.

### 5.2. The start chain on the server

`dispatch.Stream` with its unit suite; the sync handler with the database
handlers' unit and integration suites; the main loop writing a stream, unit
and integration; the wire rung `sync` on the stock root, which submits
`db.sync` and expects the restore and file lines of `_files`, `_preferences`,
`_settings` and `metaverse` in name order, then the reply naming them. Proof:
the default run, the wire test included.

### 5.3. The worker's program, with the analyst

The bring up's two changes with the worker's and the boot's unit suites and the
two test pages' entries adjusted; the seed table of 4.4 with its coherence
test; the scripted provider's `otherwise`, `after_holds` and `after_lacks` and
the console tools' refusal, each with its suites; the seed's image of 4.2.4
with the server's seeding tests; the `engine` module's worker pieces. Its group
B unit block runs the pieces in a fresh worker of the headless page: the store
built, the handshake against the real browser tools, the sync's wake applying
restore lines that the block's own lane builds from a store it fills with the
seed, the first render reaching the UI lane, then a turn on the block's own
script. Its group C integration block runs against the real ttyd and server:
the first render's line on the UI lane holds the seed's remark and the scene's
image, which the block's scripted UI stores and paints through the real page
handlers and a real media port on real elements; `ai.say` of 1 ends with the
seed table's text; the `mcp` lines and the turn's commits are seen on the wire;
the console tool's permit request on the UI lane, answered accept, shows the
console and reaches dash; bad inputs and a click end with `otherwise`; choice 3
answered Deny ends with `after_lacks`, no console and no render; a later choice
still works. Proof: groups B and C pass.

### 5.4. The UI thread's program and the engine page

The page's `engine_page` and the `engine` module's page pieces, with a group B
unit block on the UI side that builds the page's elements as the page's
integration block does: a render line paints black, shows the subtitle and
opens the box; a typed number becomes `ai.say` on the AI lane; a permit request
shows the buttons and a click answers it. The `engine` template and its build,
with the page builder's unit suite extended: the template builds, holds the
engine's entry last and no TAP element. The style sheet's one rule. Proof:
group B passes and `python3 python/page_build.py engine hyperposition-engine`
builds.

### 5.5. The serve program

The serve program with a unit suite of its root making, the log's removal
among it, and options and an integration suite that serves on port 0, fetches
ttyd's token and stops it. The engine role's wait for its lock, with a unit
test that a lock freed within the wait is taken. The test that ttyd dies with
its parent is a suite of its own, `python/test_xsjs_serve_death.py`, labelled
test-all. Proof: the default run, the full run for that suite, and the program
serves by hand.

### 5.6. The demo test

The demo test with its gold, in the driver's checks after the stream as a
smoke-test check. Three default runs measure the budget. Proof:
`./test_posix.sh` passes with it, and the pictures are in `build/test_demo/`.

### 5.7. The viewing

The agent runs the demo test, then the serve program with `--debug`, and
reports the address and the table of 1.4. The maintainer views the page. The
session's log records what was seen and what was not.

### 5.8. The line count gate

As 4.9: the mapping row, the fifteen gaps one at a time, the full run with the
count, the times measured. On 2026-11-07 the mapping row was in place and a
count of every module found the fifteen gaps closed by the sessions before;
only the new `api_match.py` had two lines, which a test then reached, and
`./test_posix.sh --test-all` now passes `--coverage`.

## 6. Decisions made, each cheap to overturn

1. The black square is the hyperposition's image, 4 px by 4 px and black, which
   the canvas scales up over the picture area. The canvas stays hidden when a
   render names no image, as the render handler does today, and the picture
   area is then the black page.
2. The page is served from WSL on 127.0.0.1 port 5769 and reached from a
   Windows browser at `http://localhost:5769/` by WSL2's localhost forwarding.
   If that is off on the machine, the Windows start script's port proxy is the
   way, and it is outside this plan.
3. The serve program's root is `~/.cache/xsjs/root`, the Windows start
   script's folder, kept between runs but for its log, which each run removes;
   `--fresh` removes the whole root. The tests' roots are under `build/`.
4. The number is typed in the box. A click on the picture sends its
   coordinates as a turn, which exists and is no choice of the demo: the
   analyst answers it with `otherwise`, while the picture shows.
5. The browser pulls the databases with `db.sync`; the server does not push
   them, so no existing suite sees a new line.
6. The sync's reply follows its pushes, so no count or end marker exists.
7. The queues' timelines log full renderings; there is no overlay per lane,
   and the wire overlay on ctrl 1 stays.
8. The scripted provider's key is the fixed text `scripted`.
9. The engine's pool is cleared at every page load.
10. The media port's timer is the provider's `timeout_seconds`.
11. The analyst's choices are 1, 2 and 3 at every node and 0 for a plain
    answer; the texts are the seed's and the maintainer's to edit; any other
    input is answered by `otherwise`, and the choices stay.
12. The screenshot tool and its suite keep opening the test page; the demo's
    pictures come from the demo test.
13. The demo test's core rungs are smoke-test and three are test-all, so
    the default run stays within its three minutes; measured in 5.6.
14. The line count gate is the last stage; it depends on nothing here and can
    move first.
15. The worker lists the server's two tools under `server.`, as the prompt
    says, though the demo's script calls neither.
16. The engine template keeps the test page's build markers; whether the test
    vectors and gold ride along is settled by the page builder's one-build rule
    in 5.4.
17. The agent's integration bench and the demo's C block each keep their own
    script: the bench's castle turn is a test of the agent, the C block's is
    the seed.
18. The wait for the engine's lock is 5 s, tried every 0.01 s, the same as the
    page's own wait for the engine's files at a reload, `engine_wait_seconds`.
    The wait and the try are both constants of the engine role
    (`python/bootstrap.py`) and not settings, as the lock is taken before the
    settings are read. The text of the refusal does not change.
19. The seeded image is a BMP, `python/seed/hyperposition.bmp`, 102 bytes: this
    work runs nothing, so no PNG's checksums can be computed, and a BMP has
    none. Chrome's `createImageBitmap` decodes it from a Blob with no type.
20. The table's new names are `otherwise`, `after_holds` and `after_lacks`.
    `after_holds` reads the tool's text, as the error mark of a result does not
    reach a chat message.
21. The table's `browser.render` calls stay imageless, so a `render` tool call
    hides the canvas and the page stays black, as the render tool's contract
    says. Naming the seed's image in them would keep the square shown.
22. The suite that proves ttyd dies with its parent is
    `python/test_xsjs_serve_death.py`, labelled test-all, in the Python unit
    list after the serve program's unit suite, with its gold
    `python/test_setting_test_xsjs_serve_death.json`. It counts for the serve
    program by a row of the driver's `_COUNTED`, and imports `ProgramCase` from
    `python/test_xsjs_serve.py`, as `test_jslb_vectors` imports `test_jslb`.
23. The API check's place is the source checks: `python/test_posix.py` calls
    `page_build.api_check()`, and no page build does; it compiles through
    `page_build.tsc_run`, as the page builds do. The cloud rule then holds with
    no new branch. In the default run API mismatches do not stop the code's own
    blocks from running first, as the source checks come after the stream. In a
    full run they do, as `test_test_posix_formatters` runs the checks whole in
    the Python unit phase, before the TypeScript blocks.
24. A root seeded before the image and `otherwise` is not migrated: it keeps
    its old scene and table, and `--fresh` takes the new seed.
25. The API text is proved against the code, by the maintainer's request of
    2026-11-07 that `API/` be checked against as much code as reasonably
    possible, which answers question 1 of session 07 11:21: `python/api_match.py`
    has tsc emit the code's declarations and compile them against `API/ts`
    both ways, compares each stub of `API/python` with its module, each handler
    with its payload in `API/ts/lines.d.ts`, and the browser suites' gold with
    `API/mcp/tools.json` and `API/sql/substrate.sql`; the suites of the store,
    the log, the seed and the settings hold the real databases and files to
    `API/sql` and `API/settings.json`. It runs in `python/test_posix.py` after
    the compile of 5.0. What it cannot see, parameter names of TypeScript among
    them, is the section api_match of the rules.

## 7. Requirements by class

- `A`: request unsatisfied or modified without cause.
- `B`: request unsatisfied or modified with cause but without confirmation.
- `C`: request confirmed withdrawn or modified.
- `D`: request satisfied without modification or withdrawal.

| Requirement | Class | Where |
|---|---|---|
| R1 load the page myself | D | 4.6, 5.5, 5.7 |
| R2 black square with the response | D | 4.1, 4.2, 4.3; decision 1 |
| R3 numbered choices | D | 4.4; decision 4 |
| R4 end to end | D | 4.1 to 4.4, 5.3 |
| R5 the fake AI talks through MCP | D | 4.4 |
| R6 log all the JSLB | B | 4.5.2: a line whose entry would not fit one `verbose.put` below `line_max` is recorded as its header and sizes, as the wire's tap does today, since the page's lines leave the browser only as `verbose.put` lines under `line_max` |
| R7 scrutinize | D | 4.5.4, 4.8. The maintainer's R14 and R16 of AUDIT_PLAN.md replace it with the audit |
| R8 consoles in the smoke test | D | 4.4 choice 3, 4.7 |
| R9 debug through DevTools | D | 4.7, 4.8 |
| R10 best debug stories | D | 4.8 |
| R11 prove ready to view | D | 4.7, 5.7 |
| R12 no real provider in a run, in the rules | D | done this session |
| R13 integration tests before an endpoint | D | 4.7.5, 5.2, 5.3, 5.6 |
| R14 current environment only, in the rules | D | done this session |
| R15 the line count gate | D | 4.9, 5.8 |
| R16 a suite of its own for ttyd's death | D | 4.7.3, 5.5; decision 22 |
| R17 a config and a build step for the API text | D | 5.0; decisions 23 and 25 |
| R18 wait for the engine's lock | D | 4.6.2, 5.5; decision 18 |
| R19 a new log at each serve | D | 1.6, 4.6.1, 4.6.2, 4.8, 5.5; decision 3 |
| R20 the console tools' refusal | D | 1.4, 4.4.2, 4.4.4, 5.3; decision 20 |
| R21 bad user input is no exception class error | B | 1.4, 4.3.4, 4.4.1 to 4.4.3, 4.7.2, 7.2: the words ask for the docs alone, and the plan goes beyond them by changing the seed and the scripted provider, so that the code agrees with the rule |
| R22 the engine outside debug mode left alone | D | 4.7.6 |
| R23 a seeded image in the integration block's scene | D | 1.3, 4.2.2, 4.2.4, 4.7.2, 4.7.5, 5.3; decisions 1, 19, 21 |

### 7.1. Unfinished Logging

The record of a line over the entry limit. `line_max` is 1 MiB and a line of
the demo is under 4 KiB, so the demo's record is complete either way. The
question is what the record holds for a line that is not.

[x] A. The sized form: a line whose rendering does not fit one `verbose.put`
below `line_max` is recorded as its header and the sizes of its payload and
blobs, as the wire's tap does today. Nothing new is written, and every lane is
recorded the same way.

### 7.2. Bad User Input

R21 asks that the docs say bad user input is no exception class error. The docs
alone would leave the seed and the scripted provider ending such an input on
the fault screen, so the rule would be false of the program it describes. The
plan therefore goes beyond the words "update the docs": the rule is in the
Errors and Data rules, the seed and the scripted provider change by 4.4.1 and
4.4.2, and the page changes by 4.3.4, so that the code agrees with it. That
change is the cause of class B, as the maintainer has not confirmed it. The
requirement is satisfied in this plan but for the rare ways a person's action
still reaches a throw, which session 07 11:21's postmortem lists as questions.

