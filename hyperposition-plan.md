# hyperposition-engine

A cloud stack for "vibe coding" an experience and interacting with it.
The experience is presented as large still images in a web browser made using generative AI from a database of facts describing an experience.

The experiences are in-browser using bare bones .html, .css and .js
content. The back end is ttyd+py+dash server-based stack for "vibe coding" an experience and interacting with it. administration scripts
are expected to support serving it from an ubuntu container on any platform.

The ttyd project is being used as a stepping stone. First ttyd is made
to serve the hyperposition-engine.html page. Then the normal ttyd+dash 
protocol ttyd serves to xterm.js is recycled as the "console" module
in hyperposition-engine.js. The console module allows dash commands to be run with binary I/O captured via the ttyd protocol in binary mode.

xterm.js is minimally adapted so hyperposition-engine.html can run it offscreen with the page showing the console I/O. with stdin hidden, stdout shown. the dash process providing the console must be
reasonably sandboxed. All further ttys allocated would communicate with back end pure PY using a new wire format called JSLB defined below.

Once logged in, the hyperposition-engine.html uses the JSLB format everywhere. (Except the console.) A collection of sqlite databases are used for substrate. The "web-worker-ai" web worker allows an AI to use MCP to control the experience. 

The experience starts with a blank black web page and a single subtitled remark "How can I help you?" The user's responses are then used fed to an AI (talking to an MCP server in the browser on a worker thread) to guide the user as requested through different experiences. This starting point is called the hyperposition and is controlled by a very bored British female AI psychoanalyst.

## Console

The AI has MCP access to the Dash shell. This allows it to do management work on the back end. e.g. checking the logs of the python server after a crash. The user should be able to interact with
the admin console as well as the AI in debug mode. the AI may be
sandboxed in a web worker and have to ask permission to talk to
the admin console.

## Wire Format JS-Line-Blobs, JSLB

The standard wire communication protocol is binary mode json lines ending in CR alone, with interleaved blobs. Integer indices into a line contain headers. Either the first char of a name or the full name are acceptable. Full names are used in debug mode.

Index 0 is the Line-Header.
    "t"/"type"    - Type used for breaking changes (="utf-8")
    "v"/"version" - Version used for breaking changes (=0)
    "k"/"key"     - * Optional. Key in a KV store
    "b"/"blobs"   - Number of blobs (=0)


Indices 1+ are Blob-Headers. They add "s"/"size" to the Line-Header.
    "v"/"version" - Version used for breaking changes (="0")
    "t"/"type"    - Type used for breaking changes (="utf-8")
    "k"/"key"     - Key in a KV store (="")
    "s"/"size"    - Data size in bytes (*required)
    "d"/"data"    - * Never serialized. An owned data array.

```txt
{ // ...
  "0":{"v":"1","t":"tile","k":"quest/forest03.json"}
  "1":{"t":"png","k":"quest/backpack.png","8732763"}
  "2":{"t":"png","k":"quest/companion.png","8732764" } // ...
  }<blob-1><blob-2><blob-3>
```

After reading the json line the recipient is responsible for reading the blobs as described by the blob headers, putting them into byte array storage, and fixing up the "d"/"data" reference in the blob headers to point to the allocated array.

This format requires a single door encode/decode function for each
language. The encode functions take a json object to be written as
a single line. They remove the "d"/"data" field from the blob headers
and append them as blobs after the line with no other control bytes
interleaved. Then, the decoding functions are required to restore
identical json with binary identical blobs from the data which was
stored as described above. this requires a json representation to
load into that supports binary arrays. e.g. JS.

this format is designed for 2-way non-blocking communication, unlike
the console and its use of dash. messages are sent to the network
as they are composed. large files may be transferred simply by sending
them with a header instructing the other side to store them in
a given DB. responses must be matched by id.

the "syscall" dispatch mechanism PY uses in its main loop requires
looking up a "line handler" by "t"/"type". then the line handler
is invoked with the json object's keys passed as `**kwargs`. the
`**kwargs` can be passed around and used as a collection, and the tool to convert a JS object to `**kwargs` could be used on sub-parts
of the JSLB object to pass that part to another subroutine. In this
manner a suite of testable functions that take `**kwargs` can
be assembled into a test suite without going via json and having
to debug all that. if there was a python version of json that could
just be passed as `**kwargs` at any point in the object hierarchy
and looked like python when you used it, that would be ideal.

On the JS side, the same type based plugin line-dispatch syscall
mechanism is required. As an example, this allows logging to be
registered for and sent from the server to a diagnostic page.

## sqlite

Chosen as a dynamic AI command language for scene data, typically
using Entity Component System or ECS structured records.

- utf-8 line driven
- has KV wrapper with 128KiB blowout to fs cache

https://sqlite.org/wasm/doc/trunk/demo-123.md

## JSLB task queue module

Each JS thread needs a JSLB queue. JSLB tasks arrive in the unencoded JSLB JS format. They may or may not have been encoded and decoded by transmission between threads.

Access to a DB is only allowed by executing a task. Specifically, when the task queue has already dispatched the task to the thread owning that DB (and perhaps others used at the same time). Large amounts of processing, touching more than one DB, may be requested in a single task (the UI thread still needs to be 200Hz when possible) without requiring subtasks to redispatch to other databases. The task dispatch mechanism is intended to be large grained, for things like
"""the user clicked at X, Y""" instead of """set /forest1/sdf/4/"""

When multiple threads are required to perform a task, JSLB can be sent to the first thread with embedded forwarding instructions to have that JSLB marked up and sent along to additional threads. For example, the JSLB may have an optional diagnostics request embedded in a certain message type.

- DBs are assigned to threads, by default "worker-ai".
  - Thread I/O is JSLB ending in CR with interleaved blobs.
- The files DB is a KY store on the main thread.
- Scripts may be kept in any DB.
for now, the AI thread will have 
- max 1 task per DB at a time.
 
the API for a tasks should abstract whether it is performed in the same thread or in another worker. as long as the thread is the correct owner for the DB is should be allowed. the first draft does have to have a web worker.

## Algorithm

1. The player initiates interaction. Time always stops.
2. A JS handler optionally updates the page or notifies the AI.

  User ---> JS ---> html
  User ---> JS ---> AI

3. The AI interacts with the database directly or via JS.

  AI <--> MCP <----------> SQL # { utf-8 sql, .ts, .bin }
  AI <--> MCP <--> JS <--> SQL # experience step
  AI ---> MCP ---> TS compiler # server-side TypeScript

4. Then it updates the html, possibly with a new picture or scene.

  AI ---> MCP ---> JS ---> html # render step

5. The player is presented with an updated page.

## Terminology

- each scene is a new "conversation" with a new establishing shot.
- each scene has a database which references the files.
- compaction is possible. crossfades stream in.

- an experience is made out of a series of scenes.
- it has media files and a collection of entity databases.

- the experience terminology is as follows.
  - multiverse: a catalog of separate experiences.
  - universe: a specific experience design.
  - world: the current experience state.
  - region: everything in your area.
  - scene: a location.

## Experience Design

- by default, time stops when the player stops
- by default gameplay is 2.5D
- service provides self designed generative AI experiences
- players are guided into experiences within their multiverse

When the hyperposition-engine loads with no scene selected, then
it loads a scene known as the "hyperposition." It contains nothing
but wisps of fog and a few inexplicable bright lights. The engine
bears this scene's namesake. It is the one scene that the player
is unable to modify. In this scene the player meets the AI analyst
who tries to determine the right universe to send the player to.
The analyst has admin control over the metaverse and expected to
perform requests as non-judgementally and efficiently as possible.

The design of the Myst Game, with basic rpg elements added is
a good template for slow moving 2.5D. Multiplayer, turn-based
strategy games need to work too. Multiplayer may require a
rewrite of the backend in C++ and for now it is more important
to design and prove the back end's algorithms and operation
than it is to slow down and think about multiplayer and C++ just
yet.

## System architecture

The front end is JS and the back end is PY. That division
is permanent.

And SH should not be used outside of admin
scripts for installing/uninstalling/starting/stopping the
service. There should be a POSIX parallel to the powershell
at the top level in xsjs and I should be able to test the
lifecycle using scripts with the same names as the top level
.ps but with .sh endings. The test for this needs to be
automated to run in a docker container inside WSL. keep the xsjs
name for now on the back end. Because the hyperposition-engine
is just one application of the xsjs back end administration
ttyd based tool suite. 


The new html app being written to serve on the front end is
called the hyperposition-engine because it is designed to do
this one job, instead of being designed to serve custom webpages
in general.

Meanwhile, all the JS is editable by AI over MCP and will be
backed up immediately to a front end and backend DB. The
SH and PY should be effectively immutable to the web app. The
web app does have admin console access via ttyd+dash but that
is only intended for debugging and may be disabled. in debug mode
the AI can do things like rewrite the bootstrap.py and reboot
the server while running within the web page. It has to be centralized so the debugging AI has access to all data in one conversation.

Further ttys requested should be served by python and not dash.
There should be no dependency on the Unix command line. Instead
the PY scripts need to use the PY system modules to do everything
in PY. Add these modules:
  - verbose : wraps subprocess with a verbose level and different
    flags and handling depending on the verbose level. level 0 calls
    commands with no good news wanted and allows the output to go
    to stderr/stdout as is. level 1 adds basic .md formatting
    to the logs generated by these called. level 2 is just everything
    raw again with verbose flags passed to subcommands. also keep all
    the logging routines here and an internal log history of
    N lines generated at level 1 so the front end could ask for it.
  - substrate : this module is a single door to sqlite module/dbs.
    adds a file cache layer for blobs over 128MiB. Add a KV accessor
    so the DB can be accessed as such.
  - bootstrap.py is just the platform specific services required to
    run the main_loop.py. They implement the prescribed json lines
    protocol above, the client and server waiting on each end of the
    pipe.

At first only 2 tty should be required by the web app. The html client
may even drop down to using only 1 tty. Multiplayer would require
multiple tty from ttyd, 1 per additional player.

## JSON Pointers

When the play

## Individually testable modules.

A critical part of this planning process is identifying the modules required in each language before starting. No two modules should call into each other cyclically as this violates the principles of starting with "unit testing" and incremental "integration testing" and I want both. 

I want JS and PY test suite for everything possible, building up from the smallest modules to the largest. Both languages must implement the
output expected of the Test Anything Protocol when testing. Do not use existing test facilities for any language. Make a bespoke solution
that registers one function call per test and calls each one in
the order they were registered. Each module should have a test sub
module with a standardized entry point that returns the test suite for that module as an array of function calls. Only the name of the function, as queried from the interpreter, is used to document a test.
If a test throws an exception or returns "falsy" then the test failed.
Provide a wrapper that formats error messages for humans.

For now don't bother parsing the Test Anything Protocol, and instead
return (num_fail, num_pass) along with it for now. It is intended for
AI and human reading form now. Add color to any HTML output so readers
can see failed lines. highlight the entire line.

# Code quality

this is test driven development. first we design a module, then we
write tests for it, and then we fix all the bugs. after that we
move on to the next module. and we build our way up by stacking
modules with one way call patterns going down.

that way when we have all out modules assembled, testing as we go, we know the final assembly will work. this process has to be made clear in all action plans to write code.

all function call and class identifiers should contain two english names. modules (and their test sub modules) are the only exception.

both PY and JS require i18n support. when reading normal code i should see `i18n("internal_error", code)` or whatever and the i18n should
just be a dictionary of strings. If the UI string happens to be undefined then throw a message about the missing string and don't worry about the rest, that can be debugged in a subsequent step.

The remaining parameters should be formatted into the string if it
has formatting specifiers. Again, just throwing over improper usage
is fine as long as the callstack is correct it can all be unravelled
from there.

## HTML App

The JS app stores sqlite dbs in the browsers local storage
and then syncs them to the webserver. This design is intended to
allow the AI to run at full speed within the browser and then have
continuous backups to the server (as reasonable.)

This means the JS side has to implement an identical "substrate"
module to the PY side. It has the same API except it has more
work to do. In addition to managing a list of DBs, KV store
abstraction, and having a 128KiB filesystem overflow like the
server it has to do replication. the current players state
(the world) should contain a JSON Pointer to the players
current scene. More on that later.

The players current scene description is going to be in a DB on the AI 
worker thread's side. The AI worker provides immediate access to 
the DBs
required to implement the experience. this is moved off the UI
thread so the the UI doesn't stall in the DB and the AI doesn't
have to talk across 2 threads for normal DB access. (just 1.)
(media remains in the UI threads "files" DB and is referenced by BV
path from the AI thread.)

Media is expected to be loaded by the UI thread and written into
its "files" DB. The AI worker loads media by sending URLs.

Meanwhile, on the web app side, the main JS thread owns 3 databases.
The settings and preferences DBs map strings to json strings.
For example, per RFC 8259 """null""" is a valid way to say null that
way.

This means the 3 DB are:
  - settings : App wide constants, mutable when debug mode is enabled.
  - preferences : User configurable settings.
  - files KV: media cache, system scripts, blobs
