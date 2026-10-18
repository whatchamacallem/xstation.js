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

== Make the use of Node for tsc an exception. Sorry.

## 2 Replicating the AI's own tables

2.1 The row log replicates the engine's tables only: `kv`, `doc`,
`doc_head`, `turn`. The typed tables the AI creates in universe and
region databases have no `seq`. HYPE-2 6.7 assumes v0 pushes such a
database whole by snapshot after any turn that changed it, and that the
second draft installs triggers on every table DDL creates, writing a
change log the row log can carry. Is the snapshot acceptable for v0, and
is the trigger log the right second draft?

== No. Replication is always over JSLB. For now forward all modifications
  as they happen from the modifier to the server via other threads as needed.
  the first unit tests just need to replicate a string->string DB table
  from the AI worker and the UI. This is required to be part of the
  substrate module and not handled ad hoc. update docs.

## 3 The Document-Ref grammar

3.1 HYPE-2 6.4 makes a ref `<db>/<kind>/<name>/<version>`, so the
database is always the leading one or two segments and no lookup is
needed; the example `forest/trees03/scene/53` becomes
`forest/trees03/scene/clearing/53`. Is the fixed depth acceptable?

== Update docs, the plan over fits an example,  The document schema is:

    `/$db/$id/$version` - external DB reference.
    `$id/$version` - internal DB reference.

  $db - a valid C identifier
  $id - any non-null utf-8 sequence
  $version - an integer literal

  The default setup is described below.

## 4 The generic provider protocol

4.1 HYPE-2 5.2 takes the chat completion protocol with function tools,
and the image generation endpoint, as xAI serves both at one base URL.
The model names in API/settings.json are placeholders. Is xAI the first
provider, and which chat and image models?

== The first test is all xAI nobody else. Using the same APIs as OpenAI would
  be cool but is not required.

## 5 The provider key and browser-origin calls

5.1 The AI worker calls the provider directly, so the key must reach the
browser: HYPE-2 reads it from `secrets.json` in the root and sends it in
`hello`, to live only in the AI worker's memory. That works only if the
provider answers requests from a browser origin. If it does not, the
server must proxy the calls, which moves the HTTP client to Python. Is
the key in `hello` acceptable, and has the provider's CORS behaviour been
checked?

== No, that is a public GitHub repo. Just get it from the ENV like normal
  for testing.

## 6 What runs on the WASM thread

6.1 HYPE-2 2.2 puts the whole substrate, KV, documents, turns, sync and
the cache, on the WASM thread, with the AI thread holding a proxy whose
every method is one task. The alternative keeps that logic on the AI
thread and makes WASM a bare SQL executor, at the cost of many more
round trips per operation. Which?

== if the AI thread and the wasm thread can be merged than just do that.
  otherwise, add all the TS to WASM that helps.

## 7 Promises in AI thread handlers

7.1 A handler on the AI thread, `ai.say` for one, spans many awaits.
HYPE-2 4.3 lets an AI thread handler return a promise, since every
database access inside it is a task of its own, and keeps WASM handlers
synchronous. Does that satisfy the rule that task bodies are synchronous,
or must the agent be written as a chain of separate tasks?

== All AI MCP and WASM should be written in TS and running on the WASM thread
   instead. Only dispatch one
   JSLB in a thread at a time. The task manager provides the DB locking scheme.
   A second JSLB can be enqueued by the handler for a first JSLB. this
   second handler needs to be able to sleep on some number of resource requests.
   in this manner tasks/JSLB lines can re-enqueue in different forms and at
   different destinations.

I should be able to form a transaction diagram of the movement of data in the
thread by logging tasks/JSLB lines submitted to the task queue and events
initiated by the task queue. No other
information should be required to understand the timeline of events in the
thread.

The queue handles having sleeping tasks and being empty as needed. all of
this is required in the plan.

## 8 MCP revision and the stdio transport

8.1 HYPE-2 5.4 emulates revision `2025-06-18` with the `tools`
capability only, and builds the stdio transport in stage 4 so an external
agent can drive a server. Is that revision right, and is stdio in scope
for stage 4 or later?

== Yes, pin it and emulate any part of it.

## 9 Flow control, the research result

9.1 ttyd bounds the pty-to-client direction by itself and nothing bounds
the client-to-pty direction but libuv's write queue. HYPE-2 3.10 runs
ttyd with `--srv-buf-size 1048576`, uses 1 MiB chunks, waits on
`bufferedAmount`, and streams big blobs to the cache file so the server
is never the bottleneck, then measures ttyd's resident size in stage 2.
Is that the configuration, with a credit line added only if the
measurement demands it?

== ok

## 10 How a document declares its refs

10.1 HYPE-2 6.4 requires a top-level `refs` array in every document so
the engine prefetches without knowing the schema. The alternative resolves
refs only on demand, which gives no cross fade prefetch. Is `refs`
required, and must the engine refuse a document without it?

== use the integer indices for the reference table. this means e.g.
{
  { 0:"/blah/.x../2",
  { 1:"/blah/.fs../1"},
  { "absn":"/blah/.ssx../2"},
  { "$ref":0}
}

This can be resolved into:
{
  { "absn":"/blah/.ssx../2"},
  { "$ref":"/blah/.x../2"}
}

with the referenced strings moved into the references to them. they
may or may not be shared. this should provide a clean round trip from
"normal" to "encoded" and back.

## 11 Two tabs on one world

11.1 The OPFS SAH pool allows one opener per file and the server runs one
process per connection on the same files in WAL. HYPE-2 6.7 refuses the
second tab with a message. Is a read-only second tab wanted instead?

== no single tab only please.

## 12 Recovering from a worker fault

12.1 A fault in the AI or WASM worker leaves it in an unknown state.
HYPE-2 4.4 has Reconnect reopen the WebSocket only. Should Reconnect also
terminate and recreate both workers, or is a page reload by the user the
right recovery after a worker fault?

== Full reload after failure is the tested path.

## 13 tappy's consumer and TAP 14 subtests

13.1 tappy parses TAP 13; indented subtest lines may come back as
unknown lines rather than results. HYPE-2 8.1 has the consumer check
every stream. Should the copy be extended to subtests, or should the
check count only the parent level lines?

== write custom PY `tap.consumer` and `tap.producer` modules. write
  `tap.producer` for JS and TY. keep the consumer a simple thing that
  takes a document and returns some stats.

## 14 When the browser sends its TAP

14.1 HYPE-2 sends the whole stream as one `tap.report` at the end. A test
that hangs then leaves nothing on the server. The alternative streams
each line as `tap.line`. Which?

== individual test case results as JSLB messages from the webb app to the
   server. further JSLB debug messages may be added ad hoc.

## 15 ESC and xterm.js

15.1 ESC is a key the shell uses, so ESC cannot both hide the console
and reach dash while the terminal has focus. HYPE-2 assumes ESC hides the
view only when the terminal does not have focus, and a second key or a
button hides it when it does. Which key, or is the conflict acceptable?

== use ctrl-0 to toggle the debug console. use ctrl-1..ctrl-n to show debug tty
   io for other tty. the non-0 tty do not need to be interactive or have any
   console features. add that to the console plan.

## 16 The scope of Always Allow

16.1 HYPE-2 4.6 records Always Allow in the preferences document, which
replicates and so outlives the tab. Is that right, or should it last the
tab only?

== Tab only.

## 17 How image bytes reach the UI

17.1 HYPE-2 5.5 has the UI fetch the provider's image URL. Provider image
URLs are temporary and the image host may not allow a browser origin.
The alternative asks for `b64_json`, which puts the bytes in the AI
worker's response and transfers them to the UI. Which is the first form?

== The integration tests should use inline `b64_json` of low resolution
   `.png` test patterns drawn with hard pixel edges.
   Do not design server side fetching, but have it as a required open door.

## 18 Media budgets

18.1 HYPE-2 6.6 proposes 256 MiB for `media_db`, the current scene's refs
only for the browser's `files`, and everything for the server. Are those
the numbers, or is this too soon?

== Putting constants, with sane defaults, in settings.js for normal
   configuration of the services
   required is expected for all this, make that a general request.

## 19 Compaction of turns

19.1 Turns live in `metaverse` by scene ref. Who decides to compact: the
agent by a token estimate against a setting, or the model through a
`turns_compact` tool? HYPE-2 assumes the agent, by estimate.

== The players current universe DB lives in the metaverse DB.
    - "metaverse" is like a bookshelf of experiences
    - multiple players can be tracked in multiple universes at the same time
    - the user may switch players. by default there is only one.
  Then the players current world DB to use is stored in the current universe DB
    - "world" is global state for an experience. these are standard games terms
  This is all required, update the plan.
   The default guidance and set up for the AI API shouldn't go past this. the
   AI API is expected to design scripts using the sqlite wrapper as a single
   door. DB admin, like
   this should be baked into the TS/PY sqlite wrapper and not left exposed to
   some AI slop script. Using heuristics is fine.

## 20 Seeding the metaverse

20.1 HYPE-2 6.2 seeds the hyperposition's documents, the analyst prompt
and the world, from the Python package when the server creates a new
`metaverse`, and keeps the universe catalogue as documents under
`metaverse/universe/<name>`. Is the server the seeder, and are the seed
texts repository files?

== yes.
  The AI API is given a bootstrap.js file to start with that knows
  how to replicate DB modification to and from the server. In an ideal world
  the server DB could simply be replicated deterministically using the existing
  DB wrapper replication code.
  it is OK if there is DSYNC. communication is only one way. on startup the
  page replicates from the server, and browser DB cache files should actually
  be invalidated if they are different than the server version and re-uploaded.
  that way the server is the ultimate source of truth. if the web app wrecks
  itself (and it may) in theory the server should be able to repair the
  saved DBs, and restore the web app to a stable state when it restarted.
  Make the reload on DB DSYNC a requirement of the prototype. That needs to be
  unit tested early. It needs to work for iteration time.

## 21 Attaching the region

21.1 HYPE-2 attaches the current region to the universe connection as
`region`, one region at a time. ATTACH on the SAH pool VFS is to be
verified at stage 6. Is one region enough, or must several be attached
as the draft's eight scenes were?

== This layer of code is tutorial code for an AI API and it is expected
  to be edited by it. Have a table of universes in the metaverse. this
  is the only fixed schema. have a table of worlds (with a mutable schema) in
  any universe. have a table of regions (with a mutable schema) in any world.
  don't break down the DBs further in the seed config. allow the AI API to
  design new DB schema and add/remove DB using it as required to implement the
  experience. use a C identifier for all of the above so they are legal
  DB names. metaverse is "metaverse". the default universe might be
  "current_universe" for simulations based on scientific data and happening
  in the present day. Otherwise the name would correspond to the kind of
  fantasy requested, or simply designate a requested partition of realities.
  The world can be called "world" by default. Further details would have to
  be filled in by the AI API when the analyst has chosen a destination.

  the integration tests have to perform these operations using an integer
  based communication protocol that stubs out the AI API. that is how testing
  has to go. in deployment, this could just be part of an AI prompt it is too
  soon to write. the requirement to add to the docs from this response is
  that the AI needs MVC to implement the above and the tests need stubs
  that use the MVC to smoke test the baseline expected usage that will be
  asked of the AI API as well.

## 22 Protecting the engine's tables

22.1 The AI runs DDL in universe and region databases that also hold the
engine's `meta`, `kv`, `doc` and `doc_head`. HYPE-2 6.2 has `sql_run`
refuse a statement that names those tables, by parsing the statement's
table names with SQLite's own `EXPLAIN`, not by text matching. Is that
guard wanted, or is the AI trusted?

== engine tables:
  add one leading underscore to "engine" DB names:
    - the "_settings" DB is immutable
    - the "_files" and "_preferences" DB have immutable schema

## 23 Simulation steps

23.1 The draft had a server-side TypeScript compiler for the AI's
scripts. HYPE-2 5.6 stores the AI's simulation steps as JavaScript in
`files` and runs them in the AI worker with `new Function`, so nothing
compiles at run time. Is JavaScript from the AI acceptable?

== No, this is wrong and has to be clearly updated. The AI API's scripts
  are not sent to the server for recompilation. Instead the AI uses its
  MCP interface to edit the JS live in the browser. And once done, it
  gets cached and backed up. TS is used to precompile the modules that
  the AI is not expected to edit. The AI is expected to have MCP controls
  to run and debug the .js it is editing using MCP so that it can diagnose
  stepping problems in a simulation. it is not required to write a simulator
  but it needs to be tested using the TAP test protocol using the integer
  based stub AI conversations.

## 24 When settings take effect

24.1 Settings travel in `hello`, so a `settings.put` in debug mode takes
effect at the next connection, not at once. Acceptable?

== settings should be served via the settings.js module which will have an
   id based lookup mechanism. and be deep frozen when not loaded in debug
   mode (as is normal in development.) it should load after "error_handler.js"
   which has no other job than to catch exceptions, resource load failures and
   other errors and replace the screen using document.write to present
   any error with a callstack in a big `<pre>` block and top the app.

## 25 Secrets in hello

25.1 The key rides the same connection as everything else: plain HTTP on
localhost, or HTTPS with Basic authentication on the LAN. HYPE-2 adds no
other gate. Confirm.

== confirm. audit to follow.

## 26 The debug flag on Windows

26.1 HYPE-2 passes `--debug` through `xsjs_start.ps1 --debug` into the
ttyd command. Is that the argument, and should the status script report
it?

== no, debug is a settings.js thing. it gets disabled for releases.

## 27 One tty

27.1 HYPE-2 reads the answer `2` to the first round's question 6 as its
second alternative: one connection, dash under a pty the server forks,
relayed as JSLB blobs. The draft's sentence about two ttys at first is
retired. Confirm.

== no, i have always explicitly asked for the opposite of this, and require
   explanations before plans change. in recent responses i have indicated that
   the dash tty should be entirely optional. (and it should for any sane
   security architecture going forward). Being able to launch PY directly
   is important because one day that process may become a C/C++/Rust webserver
   component with a hardened and optimized implementation. Dash is just for
   development in debug mode by me and the AI API.

## 28 The whitelist rule

28.1 The first round's answer 5.4 asks for a change to the project rules
about the reformat whitelist. The rules section is the maintainer's, so
it was not edited. What is the wording?

== Add "Do not suggest additions to the whitelist." please.

## 29 One strings file

29.1 HYPE-2 7.1 keeps every Python and TypeScript string in
`i18n/en-US.json`, read by both, and leaves PowerShell's `i18n.psd1` as
it is. Confirm.

== yes.

## 30 Log forwarding

30.1 HYPE-2 forwards the page's console output to the server as
`log.put` only in debug mode, into the server's `log` database, with a
ring of `log_ring` lines in each thread. Confirm the policy.

== There is no log_* DB/namespace, there is only the verbose_* DB/namespace.
   `verbose.log()` would be a good name, and then the log operation
   would be gated by the verbosity level. i explained the verbose module
   in detail, that is what i want for logging, telemetry, dumps. put that
   in the docs.

## 31 Version floors

31.1 With no container, the only runtime today is WSL's Python 3.14 and
SQLite 3.46. HYPE-2 keeps the floors 3.12 and 3.38 as documentation only.
Keep them, or drop them until the other OS flavours arrive?

== drop them until the other OS flavours arrive. remove version checks they
   would be too brittle at this stage od dev.

## 32 restart and source.put

32.1 `system.restart` execs Python itself and `source.put` writes the
package it execs, both debug mode only. HYPE-2 keeps them as the one way
the AI can rewrite the server from the page. Does "rip out" cover them?

At this point the request to "rip out" out something could have been any
of 10 i might have made so far. a request to "rip out" is a request to avoid
ossification of example code.

as i type this, i want bootstrap.py to be able to download a new main loop
PY file from the web app and serve it after a restart. in this manner, the AI
API can try to recover the server when only the bootstrap.py file is intact.
It can send over multiple main loop files and examine the outputs as needed.
the main loop is responsible for handling JSLB and there is a stock JSLB
dispatcher provided as described in the plan. bootstrap.py should be immutable
when not in debug. That means the player may have to reload a few times, but
the AI should be able to recover/clean up/admin the box without needing someone
to log in over Dash and clean up for it. This should all be fairly bare bones,
and the AI API should normally have no business mucking with the PY files served 
from the back end. this is dev MCP only. the main goal is having only one
AI in a single conversation in the browser able to debug and work globally
without asking the user to copy and paste or auth.