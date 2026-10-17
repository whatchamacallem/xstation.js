# HYPE questions, second round

Questions HYPE-2.md needs answered, in decreasing order of severity. Each
gives the decision, why it matters, and the answer HYPE-2.md assumes until
told otherwise. None restates a decision already given; thirty-two is the
cap for this round.

## 1 tsc needs Node

1.1 tsc is a Node program and Node is banned as a dependency. HYPE-2
assumes Node runs tsc at build time only, never at run or test time, and
that `page_build.py` may invoke it, which the rule on Python running
command line utilities requires approval for. Is build-time Node allowed,
and may Python run it? The alternative is compiling TypeScript inside
headless Chrome through the DevTools driver, which needs no Node at all.

## 2 Replicating the AI's own tables

2.1 The row log replicates the engine's tables only: `kv`, `doc`,
`doc_head`, `turn`. The typed tables the AI creates in universe and
region databases have no `seq`. HYPE-2 6.7 assumes v0 pushes such a
database whole by snapshot after any turn that changed it, and that the
second draft installs triggers on every table DDL creates, writing a
change log the row log can carry. Is the snapshot acceptable for v0, and
is the trigger log the right second draft?

## 3 The Document-Ref grammar

3.1 HYPE-2 6.4 makes a ref `<db>/<kind>/<name>/<version>`, so the
database is always the leading one or two segments and no lookup is
needed; the example `forest/trees03/scene/53` becomes
`forest/trees03/scene/clearing/53`. Is the fixed depth acceptable?

## 4 The generic provider protocol

4.1 HYPE-2 5.2 takes the chat completion protocol with function tools,
and the image generation endpoint, as xAI serves both at one base URL.
The model names in API/settings.json are placeholders. Is xAI the first
provider, and which chat and image models?

## 5 The provider key and browser-origin calls

5.1 The AI worker calls the provider directly, so the key must reach the
browser: HYPE-2 reads it from `secrets.json` in the root and sends it in
`hello`, to live only in the AI worker's memory. That works only if the
provider answers requests from a browser origin. If it does not, the
server must proxy the calls, which moves the HTTP client to Python. Is
the key in `hello` acceptable, and has the provider's CORS behaviour been
checked?

## 6 What runs on the WASM thread

6.1 HYPE-2 2.2 puts the whole substrate, KV, documents, turns, sync and
the cache, on the WASM thread, with the AI thread holding a proxy whose
every method is one task. The alternative keeps that logic on the AI
thread and makes WASM a bare SQL executor, at the cost of many more
round trips per operation. Which?

## 7 Promises in AI thread handlers

7.1 A handler on the AI thread, `ai.say` for one, spans many awaits.
HYPE-2 4.3 lets an AI thread handler return a promise, since every
database access inside it is a task of its own, and keeps WASM handlers
synchronous. Does that satisfy the rule that task bodies are synchronous,
or must the agent be written as a chain of separate tasks?

## 8 MCP revision and the stdio transport

8.1 HYPE-2 5.4 emulates revision `2025-06-18` with the `tools`
capability only, and builds the stdio transport in stage 4 so an external
agent can drive a server. Is that revision right, and is stdio in scope
for stage 4 or later?

## 9 Flow control, the research result

9.1 ttyd bounds the pty-to-client direction by itself and nothing bounds
the client-to-pty direction but libuv's write queue. HYPE-2 3.10 runs
ttyd with `--srv-buf-size 1048576`, uses 1 MiB chunks, waits on
`bufferedAmount`, and streams big blobs to the cache file so the server
is never the bottleneck, then measures ttyd's resident size in stage 2.
Is that the configuration, with a credit line added only if the
measurement demands it?

## 10 How a document declares its refs

10.1 HYPE-2 6.4 requires a top-level `refs` array in every document so
the engine prefetches without knowing the schema. The alternative resolves
refs only on demand, which gives no crossfade prefetch. Is `refs`
required, and must the engine refuse a document without it?

## 11 Two tabs on one world

11.1 The OPFS SAH pool allows one opener per file and the server runs one
process per connection on the same files in WAL. HYPE-2 6.7 refuses the
second tab with a message. Is a read-only second tab wanted instead?

## 12 Recovering from a worker fault

12.1 A fault in the AI or WASM worker leaves it in an unknown state.
HYPE-2 4.4 has Reconnect reopen the WebSocket only. Should Reconnect also
terminate and recreate both workers, or is a page reload by the user the
right recovery after a worker fault?

## 13 tappy's consumer and TAP 14 subtests

13.1 tappy parses TAP 13; indented subtest lines may come back as
unknown lines rather than results. HYPE-2 8.1 has the consumer check
every stream. Should the copy be extended to subtests, or should the
check count only the parent level lines?

## 14 When the browser sends its TAP

14.1 HYPE-2 sends the whole stream as one `tap.report` at the end. A test
that hangs then leaves nothing on the server. The alternative streams
each line as `tap.line`. Which?

## 15 ESC and xterm.js

15.1 ESC is a key the shell uses, so ESC cannot both hide the console
and reach dash while the terminal has focus. HYPE-2 assumes ESC hides the
view only when the terminal does not have focus, and a second key or a
button hides it when it does. Which key, or is the conflict acceptable?

## 16 The scope of Always Allow

16.1 HYPE-2 4.6 records Always Allow in the preferences document, which
replicates and so outlives the tab. Is that right, or should it last the
tab only?

## 17 How image bytes reach the UI

17.1 HYPE-2 5.5 has the UI fetch the provider's image URL. Provider image
URLs are temporary and the image host may not allow a browser origin.
The alternative asks for `b64_json`, which puts the bytes in the AI
worker's response and transfers them to the UI. Which is the first form?

## 18 Media budgets

18.1 HYPE-2 6.6 proposes 256 MiB for `media_db`, the current scene's refs
only for the browser's `files`, and everything for the server. Are those
the numbers, or is this too soon?

## 19 Compaction of turns

19.1 Turns live in `metaverse` by scene ref. Who decides to compact: the
agent by a token estimate against a setting, or the model through a
`turns_compact` tool? HYPE-2 assumes the agent, by estimate.

## 20 Seeding the metaverse

20.1 HYPE-2 6.2 seeds the hyperposition's documents, the analyst prompt
and the world, from the Python package when the server creates a new
`metaverse`, and keeps the universe catalogue as documents under
`metaverse/universe/<name>`. Is the server the seeder, and are the seed
texts repository files?

## 21 Attaching the region

21.1 HYPE-2 attaches the current region to the universe connection as
`region`, one region at a time. ATTACH on the SAH pool VFS is to be
verified at stage 6. Is one region enough, or must several be attached
as the draft's eight scenes were?

## 22 Protecting the engine's tables

22.1 The AI runs DDL in universe and region databases that also hold the
engine's `meta`, `kv`, `doc` and `doc_head`. HYPE-2 6.2 has `sql_run`
refuse a statement that names those tables, by parsing the statement's
table names with SQLite's own `EXPLAIN`, not by text matching. Is that
guard wanted, or is the AI trusted?

## 23 Simulation steps

23.1 The draft had a server-side TypeScript compiler for the AI's
scripts. HYPE-2 5.6 stores the AI's simulation steps as JavaScript in
`files` and runs them in the AI worker with `new Function`, so nothing
compiles at run time. Is JavaScript from the AI acceptable?

## 24 When settings take effect

24.1 Settings travel in `hello`, so a `settings.put` in debug mode takes
effect at the next connection, not at once. Acceptable?

## 25 Secrets in hello

25.1 The key rides the same connection as everything else: plain HTTP on
localhost, or HTTPS with Basic authentication on the LAN. HYPE-2 adds no
other gate. Confirm.

## 26 The debug flag on Windows

26.1 HYPE-2 passes `--debug` through `xsjs_start.ps1 --debug` into the
ttyd command. Is that the argument, and should the status script report
it?

## 27 One tty

27.1 HYPE-2 reads the answer `2` to the first round's question 6 as its
second alternative: one connection, dash under a pty the server forks,
relayed as JSLB blobs. The draft's sentence about two ttys at first is
retired. Confirm.

## 28 The whitelist rule

28.1 The first round's answer 5.4 asks for a change to the project rules
about the reformat whitelist. The rules section is the maintainer's, so
it was not edited. What is the wording?

## 29 One strings file

29.1 HYPE-2 7.1 keeps every Python and TypeScript string in
`i18n/en-US.json`, read by both, and leaves PowerShell's `i18n.psd1` as
it is. Confirm.

## 30 Log forwarding

30.1 HYPE-2 forwards the page's console output to the server as
`log.put` only in debug mode, into the server's `log` database, with a
ring of `log_ring` lines in each thread. Confirm the policy.

## 31 Version floors

31.1 With no container, the only runtime today is WSL's Python 3.14 and
SQLite 3.46. HYPE-2 keeps the floors 3.12 and 3.38 as documentation only.
Keep them, or drop them until the other OS flavours arrive?

## 32 restart and source.put

32.1 `system.restart` execs Python itself and `source.put` writes the
package it execs, both debug mode only. HYPE-2 keeps them as the one way
the AI can rewrite the server from the page. Does "rip out" cover them?
