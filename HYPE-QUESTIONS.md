# HYPE questions

Questions HYPE.md needs answered, in decreasing order of severity. Each
gives the decision, why it matters, and the answer HYPE.md assumes until
told otherwise. Thirty is the cap for this round.

## 1 The shape of a JSLB line and how a handler receives it

1.1 Is a line a JSON object whose keys `"0"`, `"1"` and so on are the
headers and whose other keys are the payload, as the draft's example and
HYPE.md 3.1 read it? The alternative is a JSON array with the payload at
a position that depends on the blob count.

1.2 With the object form, `handler(**line)` works in CPython, which does
accept `"0"` as a keyword key, but no parameter can be named `0`. HYPE.md
assumes the dispatcher calls `handler(line, **payload)`, payload being
the non-integer keys, so a handler reads `line["1"]["d"]` for its first
blob and names its payload fields as parameters. Is that the convention,
or should the headers be moved under one named key such as `_` so that
`handler(**line)` alone suffices?

## 2 Where the model runs and who holds its key

2.1 Does the model loop run in the browser's "ai" worker, calling the
model's HTTP API from the page with a key held in the browser, or on the
Python server, which then needs an HTTP client in its select loop and a
key in its state directory? HYPE.md 6.3.10 assumes the browser, behind a
single door `model.turn_run`, because the draft wants the AI at full
speed in the page and the server trivial.

2.2 Which provider and model? If Anthropic, the current default would be
`claude-opus-5-5`.

2.3 Is MCP meant literally, JSON-RPC `tools/list` and `tools/call` over
a transport, or is a tool table in MCP's shape enough until an external
client needs to connect? HYPE.md assumes the table.

## 3 SQLite in the browser cannot live on the main thread

3.1 sqlite3.wasm persists through OPFS, which exists only in workers, and
`localStorage` holds about 5 MiB of strings. HYPE.md 2.3 therefore gives
every browser database to a worker and the main thread none. Does
"browser's local storage" in the draft mean OPFS, or was `localStorage`
intended for settings and preferences only?

3.2 Media then lives in the "db" worker and the main thread paints from
transferred buffers. Is that acceptable in place of the draft's files
database on the UI thread?

## 4 One static file, and where third-party code comes from

4.1 ttyd serves one file. HYPE.md 2.5 proposes `page_build.py` inlining
every script and sqlite3.wasm for the first draft, and scripts fetched
from the files database over JSLB later. The third option is a Python
static server, which the draft seems to exclude. Which?

4.2 sqlite3.wasm, xterm.js headless and tappy would be fetched by a
standard library script with pinned versions and SHA-256 into
`third_party/` and committed. Is committing them acceptable, and is
xterm.js headless the "minimal adaptation" meant?

## 5 Consequences of tappy as the test API

5.1 tappy's `TAPTestRunner` is `unittest.TextTestRunner`, so tests become
`unittest.TestCase` classes and the draft's rules "no existing test
facility" and "a falsy return fails" lapse. HYPE.md 7.1 records that as
the decision of 2026-10-17. Confirm.

5.2 unittest runs methods in name order. Is that fine, or must the JS
clone also sort by name so both read the same?

5.3 In a page `set_outdir` has no directory. HYPE.md keeps the `.tap`
texts in a map listed by class name and streams to a `pre`. Agreed?

5.4 The copy keeps tappy's style and `from` imports: `python/*.py` does
not descend into `python/tap/` and pyright would exclude it. Is a
subdirectory outside the formatting rules acceptable, or should the copy
be restyled to the project's rules?

## 6 One tty or two

6.1 HYPE.md 2.1 runs the console as a second ttyd connection with the
role in `?arg=console` through ttyd's `--url-arg`, which lets any client
name a role, so bootstrap.py whitelists three. The alternative is one
connection, dash under a pty that Python forks and relays in JSLB blobs,
which puts the console inside the same permission and logging path.
Which first, and is the single-tty form the target?

## 7 What the server does after a handler fails

7.1 HYPE.md 4.4 proposes: write one `error` line with the stack, exit 1,
let the connection end. One process per connection makes that cheap, and
it is first failure only. The alternative is to answer the error and
keep serving. Which?

7.2 The same for a worker in the page: the first failure disables the
controls and shows the detail, as bootstrap.html does. Agreed?

## 8 Raw mode and the CR terminator

8.1 The engine role puts the pty in raw mode so blobs pass. That removes
`^C`, `^D`, the 4095 byte line and the echo on that connection; a
runaway is ended by closing the socket. Agreed?

8.2 CR alone ends a line. In raw mode CR and LF are both plain bytes, so
the choice is convention. Keep CR, as Enter in a terminal sends CR?

## 9 Header fields and their defaults

9.1 Replies need an id to match: HYPE.md adds `i`/`id` on requests and
`r`/`reply` on answers. Agreed, and are those the names?

9.2 The draft gives the line header's type the default `utf-8`, which is
a content type, while dispatch keys on type. HYPE.md makes the line type
required with no default and keeps `utf-8` as the blob type default.
Agreed? Versions become integers on both headers, default 0.

9.3 The blob type registry proposed: `utf-8`, `json`, `png`, `jpeg`,
`webp`, `sqlite`, `js`, `wasm`, `html`, `css`. Short names, not MIME.
Where is the registry kept now that the format registry document is not
to be read in this round?

## 10 The fate of put, ls, restart and forked modules

10.1 HYPE.md 6.2.7 turns `put` and `ls` into `files.put` and `kv.list`,
keeps `restart` as `system.restart`, and keeps the fork of modules in
bootstrap.py without a caller. Do forked modules survive as a way to run
a long job off the select loop, or do they go?

## 11 What "reasonably sandboxed" means for dash

11.1 Without root, Python can scrub the environment, change directory,
set resource limits and, on this kernel, call `os.unshare` for user and
network namespaces. Which of these are required, and is a failure to
apply one a hard error or a reason not to serve the console?

11.2 Is the AI's console access meant to be gated by the page confirming
each command, as HYPE.md 4.7 assumes?

## 12 The overflow threshold

12.1 The draft says 128 KiB twice and 128 MiB once. HYPE.md 5.4 takes
128 KiB, near SQLite's measured crossover. Which?

## 13 Replication and conflicts

13.1 HYPE.md 5.9 starts with whole-database snapshots, then a row log by
`seq`. The browser writes its player's world and scenes, the server backs
them up, the server masters scripts and seeds. What happens with two tabs
on one world, and what cadence is "as reasonable"?

## 14 The JSON Pointers section

14.1 The draft's section ends mid-sentence at "When the play". HYPE.md
5.5 assumes every KV key is a JSON Pointer into one logical document and
that `world` holds `/scene`. What was the rest of the sentence, and what
is the document's root?

## 15 Identity

15.1 "Once logged in" today means ttyd's Basic authentication. Is there
a player identity beyond that, and how does a connection map to a
`worlds/<player>/` directory? HYPE.md 5.7 leaves `<player>` undefined.

## 16 Debug mode

16.1 HYPE.md 2.4 sets debug mode with a flag in the ttyd command written
by the start script, reports it in the hello, and gates the console,
settings writes, module puts and restart on it. Is that the definition?

## 17 Scenes as files and the region

17.1 One SQLite file per scene, attached to the world connection as the
region, at most eight attached. Compaction replaces a prefix of turns with
one summary turn. Crossfade means fetching the next scene's files before
`scene.enter`. Does that match the terminology section?

## 18 The ECS schema and the AI's rights

18.1 HYPE.md 5.6 gives entities, JSON components by kind, media by role
and a turn log, so the AI invents kinds without DDL. May the AI run DDL
at all through `sql.run`, or only statements against these tables?

## 19 The thread model of the first draft

19.1 The draft says "the first draft does have to have a web worker",
which may be missing a "not". OPFS forces at least one worker. HYPE.md
uses two, "db" and "ai", plus the main thread. Is two right, or one?

## 20 Synchronous task bodies

20.1 HYPE.md 4.6 makes a task body synchronous and splits anything that
must await into a second task, which is what makes "one task per
database" true without locks. Agreed?

## 21 Images

21.1 Who makes the pictures, the same model or an image provider, and
from which thread? HYPE.md names a tool `image.make` that stores into
files and returns the key, and leaves the provider open. Formats PNG and
WebP; a size budget per image?

## 22 The JavaScript test runner

22.1 HYPE.md runs the JS suites in headless Chrome through the existing
DevTools driver, because sqlite3.wasm and OPFS need a browser. Node is
installed but unused by the project. One runner in the browser only?

## 23 Flow control for big uploads

23.1 ttyd queues pty writes in memory with no window. HYPE.md measures
ttyd's resident size during a 128 MiB echo in stage 2 and adds a credit
window only if that measurement demands it. Agreed?

## 24 Docker

24.1 `docker` is installed in this WSL. May the lifecycle test use it,
and is `ubuntu:24.04` the base? The container runs as a user, not root.

## 25 Start at boot on Linux

25.1 The Windows side uses a sign-in task. On Linux and in a container
there is no sign-in. HYPE.md 6.4 leaves `xsjs_start.sh` starting ttyd
with `setsid` and a pid file. Is a systemd user unit wanted, or nothing?

## 26 Shell dialect and logs

26.1 `archive.sh` is POSIX sh and `clean.sh` is bash. HYPE.md makes the
four admin scripts POSIX sh for dash, with logs `<script>.sh.md` beside
them like the PowerShell logs. Agreed?

## 27 Settings

27.1 The hello carries the settings. Are they seeded from a top-level
`settings.json` read by the server at start, as earlier planning named,
and may only debug mode write them back?

## 28 Version floors

28.1 WSL has Python 3.14 and SQLite 3.46; `ubuntu:24.04` has Python 3.12
and SQLite 3.45. HYPE.md needs `Connection.serialize` (3.11) and, for
the sandbox, `os.unshare` (3.12); `STRICT` needs SQLite 3.37. Floors of
Python 3.12 and SQLite 3.38?

## 29 The i18n call

29.1 The draft writes `i18n("internal_error", code)`. A Python module is
not callable and `from` imports are banned, so HYPE.md names the function
`text_format` in both languages, with `{0}` placeholders shared with the
PowerShell strings. Is the name acceptable?

## 30 Measuring the 200 Hz goal

30.1 HYPE.md measures the main thread with a long task observer during
a 16 MiB transfer and requires no task over 5 ms. Is that the acceptance
measurement for the UI thread, and 5 ms the budget?
