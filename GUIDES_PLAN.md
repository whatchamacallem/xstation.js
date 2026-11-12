# GUIDES_PLAN.md

The plan of task 1.1 of the engineering log `tmp/tasks_11_1519.md`: three
guide tests become the whole default end to end level, and the old end to end
programs move to the normal level. It was written by task T65, which ran
nothing. Each worker of the swarm starts from this file alone, and the project
rules of `CLAUDE.md` bind every word of it.

Read sections 1 to 3 whole, then the section of your own task in 7, then the
sections it names. The code is the authority on current state; where this plan
says something about the code that the code contradicts, the code wins and the
worker reports the difference.

## 1. Requirements

Each requirement quotes the phrase of task 1.1 it comes from. The coordinator's
list was checked against the literal text; the corrections are noted.

1.1. R1, the default level is the guides. "these are the only tests I want
running", "the tests listed below are the new default end to end tests":
`./test_posix.sh` with no option runs the three guide tests and nothing else.

1.2. R2, the old end to end programs move to the normal level. "move the
existing end to end tests into the "normal" category so that they have to be
explicitly requested for testing", "the old end to end defaulttests are just
integration tests now that happen to be end to end, but don't get run during
default iterative dev": `python/test_wire.py`, `python/test_browser.py` and
`python/test_demo.py` run at `--test-normal` and above. Each level holds every
level below it, so the normal level runs the suites, the checks of
`test_posix.py`, the old three, then the guide tests.

1.3. R3, offline, POSIX, headless, the fake AI alone. "ignore windows and
ignore testing with a real API endpoint. the goal is automated testing without
an internet connection in a posix headless environment, like you are currently
in", "they need to all use the fake AI API". No PowerShell file changes. No
real provider is contacted by anything this plan builds.

1.4. R4, the four parts of each guide. "confirm with the fake player that they
want to go with them, and then engage the player in a conversation. And then
build them a sim and then interact with the player to operate the sim as a
guided interactive thing."

1.5. R5, scripted inputs of three kinds. "the fake player selections can be
scripted too. they can be simple neumeric, english words, or entire phrases."
The scripted provider today answers decimal integers alone, so words and
phrases become first-class reply keys.

1.6. R6, exactly the three guides, introductions verbatim. "this has to be
done with three different guides", and the guide texts' "Introduction
(unchanged)". Isaiah Cole, Ruth Calloway and Dawa, entries 1, 2 and 4 of
`guides.md`.

1.7. R7, Ruth's simulation. "The simulation has to be turn based and use a
real world aviation stunt model for gameplay mechanics." Section 5.3 holds the
model, each constant with its source.

1.8. R8, each guide's beats, exit, stake and keepsake. From each guide's "What
the player does" and "Keepsake" paragraphs and the "Rules every experience
follows" of `guides.md`: rule 2 (real rules, a real chance of failing),
rule 3 (something of the guide's at stake), rule 4 (the promised exit always
works), rule 5 (one ending, one keepsake), rule 6 (the world remembers).

1.9. R9, a swarm with the rename locks. "use a swar of agents to implement the
plan using the file renameing scheme where a task number is appended to the
file", "this has to be done with three different guides using an agent swarm".
One worker per guide, at most 6 implementation tasks, a reading review, then
one task alone for the rule sections of `declawed.md`, ids from T66.

1.10. R10, the docs. "update the docs too."

1.11. R11, nothing runs. "testing is not allowed. just stop when all the code
and changes are in." A value nobody can work out by hand, such as a digest or a
fake response id, goes into no hand written gold.

1.12. R12, a plan by an agent first. "make a plan using an agent". This file.

## 2. Decisions

Every decision is cheap to overturn; each names the requirement that motivates
it, as reuse is chosen by the plan and never by availability.

2.1. D1, where a guide starts. Each guide test starts at the hyperposition, as
every player does, and the fake AI makes the guide's universe, world, region
and scene with the AI's own tools: `image_make`, the seeded `bootstrap` script
through `script_run`, `doc_put` of the universe's prompt document and `render`.
No guide state is written at root time: the test rules forbid changing a
module's state to emulate an environment, and the scripted table is the one
allowed scripted part (R4, R3).

2.2. D2, the confirmation and its refusals. The introduction is the guide's
offer and ends the creation turn verbatim (R6). The player's answer is a reply
key of the guide's offer node. The three walks show three answers: Isaiah's
player asks to leave, goes back to the hyperposition and returns; Ruth's player
asks a question first, then says yes; Dawa's player says no, Dawa waits, then
the player says yes (R4). Leaving is the AI's `kv_put` of `/metaverse/world`
back to `metaverse` and a `render` of the hyperposition; returning is the
`kv_put` of the guide's world and a `render` of the guide's scene.

2.3. D3, what the sim is. The sim is real state in the store and real rules
the store runs. The fake AI's build turn calls three tools in one reply:
`kv_put` of the guide's script as `/_files/script/<guide>.js`, `sql_run` of the
sim's DDL on the guide's world database, and `script_run` of the script's
`setup`. Every later beat is a `script_run` of the script with the player's
choice as its arguments. The script's source is the checkout file
`python/guides/<guide>/sim.js`, embedded into the table's `kv_put` arguments
when the root is made (R4).

2.4. D4, how the replies follow the sim. A script returns
`{"say": TEXT, "outcome": WORD}`. Two additions to the scripted provider carry
it: `quote`, by which a reply's text is the string at a path of the last tool
result's JSON, followed by the reply's `content`; and the existing one bit,
`after_holds` with `after_lacks`, which picks the next node by the outcome, as
`"outcome":"made"`. So every number the page shows is the sim's arithmetic,
and the table holds no number of the model (R7, R8).

2.5. D5, the richer branch is not built. A list `after_cases` of
`{holds, reply}`, the first whose text every result holds taken, else
`after_tools`, was weighed. Every walked branch here is two way, and `quote`
carries the multi-way outcomes as text, so the list is not built. Its design
stays here for a guide that needs three paths.

2.6. D6, the exit that always works. Rule 4 of the guides needs the exit at
every point after the sim exists. The table builder of the test side, not the
provider, guarantees it: every node of a guide's table holding `ask` gets the
guide's exit as a reply, and three nodes of its own that pause and then resume
at that node with its `ask` again (section 3.3). The exit calls the script's
`exit` action, which brings the player to safety with its own arithmetic, and
the resume its `resume` action. Isaiah's exit, by rule 4 from his
introduction's "You don't have to say a word" and "if you'd like", is riding
back to the fire. Dawa's, by rule 4 from "Tell me if it starts" and "I have
never left anyone behind", is being taken down to the camp below. Ruth's is her
own: "tap your head twice" (R8).

2.7. D7, exits in the provider are deferred. The other design: `Script` gains
`exits: {[input: string]: ScriptExit}`, `ScriptExit` being
`{tool_calls, after: string, paused: string, resume: string, resume_calls}`;
the port answers an exit's input in every node before the node's own replies,
remembers the node it left, holds a paused place of its own whose `resume`
input calls `resume_calls` and returns to the node it left, whose re-ask is a
node field `ask` the port then needs too. It moves state into the port and a
field into every node, for a structure the builder gives a test table already.
Not built; it is the design to take when a hand written experience, not a test
table, needs exits.

2.8. D8, input normal form. A reply key matches the user's text after its ends
are trimmed and its letters lowered, by JavaScript's `trim` and `toLowerCase`.
A key not already in that form can never match, so the port refuses a table
holding one when it is made, `provider_script.key_unnormal`. Punctuation is
kept: `what if i hate it?` matches "What if I hate it?" and not "what if i hate
it". Any text is a key: `60`, `yes`, `i'll fly, you walk` (R5).

2.9. D9, the program layout. Three programs, `python/test_guide_isaiah.py`,
`python/test_guide_ruth.py` and `python/test_guide_dawa.py`, each a thin
`main` over one shared module, `python/guide_walk.py`, and each with its own
gold, `python/test_setting_test_guide_<guide>.json`, beside it as the harness
rule wants. The guide's own files are in `python/guides/<guide>/`. A worker per
guide then owns its guide's directory and gold and no other file (R9).

2.10. D10, the shared module stands alone from the demo. `guide_walk.py`
drives the page as `test_demo.py` does, through `xsjs_serve.page_ready`,
`xsjs_serve.root_make`, `xsjs_serve.TtydServer` and `devtools.Browser` over
`devtools.LinuxPipe`, since the guide tests must prove what the maintainer
serves, offline and headless (R3). It imports nothing of `test_demo.py`: the
default tests must not depend on a program the default level no longer runs
(R1, R2). The few helpers both need, the page state script, typed keys, the
process listing under ttyd, are written anew in `guide_walk.py`. Deferred: the
demo moving onto `guide_walk.py`'s page driving, by making `GuideRun`'s state,
key and leave methods public in the stub and replacing `DemoRun`'s copies; not
done now, so that the programs the normal level runs change in no line.

2.11. D11, a walk is data. Each guide's walk is its gold: rungs of steps, each
step a line typed, the band it must end with, and optionally the picture and
rows of the server's databases it must then show. `guide_walk.py` interprets
it, so a guide worker writes JSON and JavaScript and no Python (R9).

2.12. D12, a step's band must differ from the band before it. Typing then
waiting for the band could otherwise pass before the turn ran, as the demo's
bad input rung notes. The walk refuses such a gold step as a check failed.

2.13. D13, rows checks read only what an earlier step made. A step's `rows`
check reads a database file and table made by a step before it, so no check
meets a table the server has not yet made, and no error is caught. Within the
step it polls until the rows equal the gold, as commits are pushes the server
applies after the band shows.

2.14. D14, debug roots. Each guide root is a debug root, verbose off, so the
audit exists and `audit_read.failure_check` proves no unexpected failure: no
error line, no tool's `isError`, every request answered, each chain sending only
its new items, the analyst's prompt written once. A sim never throws on a
player's choice; a choice that fails is an outcome, as bad user input is
expected (R8, Errors rules).

2.15. D15, a unit suite of the builder. `python/test_guide_walk.py`, labelled
smoke-test, tests `table_build` on a scratch guide in `build/` and builds the
three real guides. It counts for no module under `--coverage`
(`_COUNTED["test_guide_walk"] = ()`), as the walk's lines need the page and
run only in the guide programs.

2.16. D16, no number in hand written text. An `ask`, a `content` or a `puzzled`
text states no number of a model; every such number comes from a script's
`say`. The introductions are verbatim and stay as they are.

2.17. D17, not built. Serving a guide's root for a person to play
(`xsjs_serve.py --guide NAME`, which would make the root, write the built table
as its seed and serve it) was not asked for and is not built. A return visit
that proves rule 6 across sessions is not walked; the sims keep their state in
the world databases, which persist, and no step reloads.

## 3. Architecture and API, from the top down

### 3.1. The levels

3.1.1. `python/test_all.py` gains two constants and one function and changes
one function:

```python
# The end to end programs of the default level, the guide tests, in order.
_GUIDE_PROGRAMS = ["test_guide_isaiah", "test_guide_ruth", "test_guide_dawa"]

# The end to end programs a run with a stream runs before the guide tests.
_NORMAL_PROGRAMS = ["test_wire", "test_browser", "test_demo"]

# The end to end programs of a run, by whether it has a stream, in order.
def programs_chosen(stream: bool) -> list[str]:
    return (_NORMAL_PROGRAMS if stream else []) + _GUIDE_PROGRAMS
```

3.1.2. `programs_run(chosen, limit, started, stream)` takes `stream` and runs
`programs_chosen(stream)` in order, each by `importlib.import_module(name)`,
its `main(words)` under `category.alarm_plan(f"{name}.py", None, limit,
elapsed)`, returning the first code not 0, as the three hand written blocks do
today. `main` calls `programs_run(chosen, limit, started, False)` where no
stream is wanted and `programs_run(chosen, limit, started, True)` at its end.
Nothing else of the driver changes: `stream_wanted`, the options and the
category stay as they are.

3.1.3. The guide programs take `category.options_add` and
`switches.options_add`, so the driver's `category.option_words(chosen)` reaches
them as it reaches the old three. Every guide rung is labelled smoke-test, so
every level runs all of them.

3.1.4. Deadline. The end to end level today takes about 10 s and the normal
level about 70 s (log `tmp/tasks_09_0807.md` 3.6). A guide walk is 19 to 25
turns of the scripted AI, each well under a second, plus a root, a ttyd and a
page load: about 10 to 20 s each, so about 30 to 60 s at the end to end level
and 100 to 130 s at the normal level, both under the 180 s of
`python.test_all.smoke_seconds`.

### 3.2. The scripted provider

3.2.1. Behaviour. In `ts/provider_script.ts`:

1. A user message's text is matched in its normal form, its ends trimmed and
   its letters lowered, against the current node's `replies`. Held: that
   reply. Not held: `otherwise`. Neither: `provider_script.input_unknown`
   naming the node and the text in normal form. A content that is not a string
   stays `provider_script.input_invalid`, with its new text below.
2. The `integer_text` constant goes; nothing distinguishes digits any more.
3. The `ScriptPort` constructor, after checking `start`, walks every node's
   `replies` keys in the table's order and throws
   `provider_script.key_unnormal` for the first key whose normal form differs
   from itself.
4. `ScriptReply` gains `quote?: string`. When present, the reply's text is the
   string found by following the path's members, split at `.`, from the value
   `jslb.json_decode` makes of the last call output's text of the input,
   followed by one space and `content` when `content` is not null. A reply
   holding `quote` that answers a user message, which has no tool result,
   throws `provider_script.quote_unreached` naming the node. A text that is not
   JSON, a member missing or not reached through objects, or a value at the end
   that is not a string throws `provider_script.quote_missing` naming the node
   and the path, a JSON failure as its cause by `utility.error_wrap`.
5. The chosen reply carries its resolved text, so `output_make` writes the
   message from that text and not from `content` alone. A reply whose text is
   null writes no message, as today.

3.2.2. The header of `API/ts/provider_script.d.ts` becomes, within the 20 line
limit:

```ts
// A scripted provider, which the tests and the engine page run: no network,
// no AI. A port that answers the `http.request` lines of provider.ts. The
// latest user message, its ends trimmed and its letters lowered, picks the
// reply its node's `replies` holds under that text: a number, a word or a
// phrase. Any other text gets the node's `otherwise`, a person's bad input
// being expected; with none it is refused, in a test's own table a bug of the
// test, as is a content that is not a string and a key no input can match. A
// tool result moves to the node the reply names, which answers with
// `after_tools`, or with `after_lacks` when it holds `after_holds` and a
// result lacks that text. A reply's `quote` is a path into the JSON of the
// last tool result, whose string it says before its `content`. Every image
// request gets the image of `image_pattern` as `b64_json`. Once it has chosen
// a reply it holds the request to what xAI expects, refusing the first bad
// field by `provider_script.field_invalid`. It keeps each response under its
// id, unless `store` is false, to check a request chained from it. Each reply
// holds a reasoning item, xAI's echoes of the request, and a `usage` of
// arithmetic on the context in characters. In debug mode, by its reader, it
// takes `provider.tools_omitted` for tools.
```

The sentences the old header loses already stand in the Tools section of
`declawed.md` as the rules "script after pair", "scripted held responses" and
"scripted usage"; T74 checks that they still say all of it.

3.2.3. The interfaces of `API/ts/provider_script.d.ts` change in two members:

```ts
  interface ScriptReply {
    // What the assistant says, null when it only calls tools or only quotes.
    content: string | null;
    // A path of members joined by `.` into the JSON of the last tool result.
    quote?: string;
    tool_calls?: ScriptCall[];
    // The node to be in after this reply's tool results arrive.
    next: string;
  }

  interface ScriptNode {
    // Replies by the text the user sent, its ends trimmed, in lower case.
    replies: { [input: string]: ScriptReply };
```

The rest of the file stays. The code's `ScriptReply` and `ScriptNode` get the
same members and comments, so that `api_match.typescript_match` holds.

3.2.4. Strings of `i18n/en-US.json`, in the table's sorted order:

- `provider_script.input_invalid`, changed: "The scripted provider takes a
  text as the user message, not {0}."
- `provider_script.input_unknown`, unchanged: "The script node {0} has no
  reply for the input {1}." Its `{1}` is now the text in normal form.
- `provider_script.key_unnormal`, new: "The script node {0} holds the reply
  key {1}, which no input can match, as an input is matched with its ends
  trimmed and in lower case."
- `provider_script.quote_missing`, new: "The tool result answered in the
  script node {0} holds no text at {1} to quote."
- `provider_script.quote_unreached`, new: "The script node {0} quotes a tool
  result in a reply to a user message, which holds none."

3.2.5. What does not change: the seed table `python/seed/provider_script.json`,
whose keys are digits already in normal form; the analyst's answers to `7`,
`word` and an empty line, each of which still takes `otherwise`; the C block
and the demo test.

### 3.3. The guide table source and `table_build`

3.3.1. A guide's table source is `python/guides/<guide>/table.json`. It is a
`provider_script.Script` with these differences, all of which `table_build`
removes:

1. Top level `puzzled`: the guide's words before a re-ask, a string.
2. Top level `exit`: `{"input", "call", "after", "resume", "resume_call",
   "paused"}`. `input` and `resume` are reply keys in normal form; `call` and
   `resume_call` are calls in source form; `after` is the text said after the
   exit's result; `paused` the answer to anything but `resume` while paused.
3. A node may hold `ask`, the question the node asks, a string.
4. A call's `arguments` is a JSON object, not its text.
5. Anywhere, an object whose only member is `"$text"` stands for the text of
   the file it names in the guide's directory.

3.3.2. `table_build(directory)` returns the `Script` the port takes, by these
steps in order:

1. Read `table.json` of the directory by `json.load`, UTF-8.
2. Replace every object `{"$text": NAME}`, at any depth, by the text of
   `NAME` in the directory, read as UTF-8, less the one newline that must end
   it. A file not ending in a newline raises `ValueError`; an object holding
   `"$text"` beside another member raises `ValueError`.
3. For every node holding `ask`, in the source's node order:
   1. Refuse with `ValueError` a node holding `otherwise` too.
   2. Set `otherwise` to `{"content": PUZZLED + " " + ASK, "next": NODE}`.
   3. When the table holds `exit`: refuse with `ValueError` a node whose
      `replies` hold the exit's `input` or `resume`, or a generated name below
      already a node; then add the reply and nodes of 3.3.3.
   4. Remove `ask`.
4. Refuse with `ValueError` any node whose `replies` are not empty and that
   holds neither `ask` nor `otherwise` in the source.
5. Turn every call's `arguments`, generated ones included, into
   `json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))`.
6. Return `{"start": START, "nodes": NODES}`, the source's `puzzled` and
   `exit` left out.

3.3.3. The exit's expansion at a node `X` holding `ask` `A`:

```json
"X": {"replies": {"<exit input>": {"content": null, "tool_calls": [<exit call>], "next": "X~exit"}}},
"X~exit": {"replies": {}, "after_tools": {"content": "<exit after>", "quote": "value.say", "next": "X~paused"}},
"X~paused": {
  "replies": {"<resume>": {"content": null, "tool_calls": [<resume call>], "next": "X~resume"}},
  "otherwise": {"content": "<exit paused>", "next": "X~paused"}
},
"X~resume": {"replies": {}, "after_tools": {"content": "A", "quote": "value.say", "next": "X"}}
```

So the page shows the exit's arithmetic then the guide's words, and on resume
the resume's arithmetic then the question that was pending. Generated nodes
take no exit and no puzzled `otherwise` of their own.

3.3.4. The rule of a guide's nodes: a node holds `ask` exactly when the sim
exists by the time the player can be in it, as an exit before the build would
run a script that is not yet written. The nodes before the build hold their
own `otherwise`.

### 3.4. `guide_walk.py` and its stub

3.4.1. `API/python/guide_walk.pyi`, written first by T66:

```python
# Walks a guide test on the engine page. `table_build` makes the scripted
# table of a guide's directory, `python/guides/NAME/`, from its `table.json`:
# each object `{"$text": FILE}` becomes that file's text less its last
# newline, each call's `arguments` its JSON text, and each node holding `ask`
# gains `otherwise`, the table's `puzzled` then `ask`, and the table's exit,
# answered there by three nodes of its own that pause, then resume there with
# `ask` again. `guide_main` serves a fresh debug root under build/ through
# the functions of xsjs_serve.py, the built table as its seed, opens the page
# in chrome-headless-shell, and walks the rungs of the gold of
# test_guide_NAME.py: each step types a line and waits for its band with the
# box enabled, then checks the picture and polls the rows of the server's
# databases it names. Then the audit must hold no unexpected failure and one
# engine start, the page leaves and ttyd stops with the gold's code. A run
# that passes removes its work directory; a failed rung keeps it, with its PNG
# and the audit in build/test_guide_NAME/. Exit 0, 1 at the first failed check
# naming its rung, 130 at ctrl C, 128 plus the signal's number at SIGHUP or
# SIGTERM. No real AI provider is contacted.

from typing import Any

# A check of a walk that failed, with the measurement that failed it.
class CheckFailed(Exception): ...

# The scripted table of the guide in `directory`, a `provider_script.Script`.
def table_build(directory: str) -> dict[str, Any]: ...

# Runs the guide test `name` with its program's arguments. The exit code.
def guide_main(arguments: list[str], name: str) -> int: ...
```

3.4.2. The module's `__all__` is `["CheckFailed", "guide_main",
"table_build"]`. Everything else in it is private by a leading underscore or
is a class method, so `api_match.python_match` compares exactly these three.

3.4.3. `guide_main(arguments, name)`:

1. Parses `arguments` with `prog` `test_guide_<name>.py`, a description,
   `category.options_add` and `switches.options_add`; sets the switches; sets
   SIGHUP and SIGTERM to exit with 128 plus the signal's number.
2. Reads its gold under the id `python.test_guide_<name>` by `harness.gold_get`.
3. Empties `build/test_guide_<name>/`, the failure directory, and makes a work
   directory by `tempfile.mkdtemp(prefix=f"test_guide_{name}-", dir=build)`.
4. Opens `devtools.Browser(window_width, window_height,
   devtools.LinuxPipe())` and runs the rungs inside it, the label book
   `category.LabelBook(chosen)` entered with the root `name` and the gold's
   `root_label`.
5. Rung `served`, timer `served_seconds`: `xsjs_serve.page_ready(values)`;
   `xsjs_serve.root_make(values, page, root, parameters, True)` with
   `parameters` the switches with `debug` the gold's `root_debug` and `verbose`
   its `root_verbose`; writes `json.dumps(table_build(guide_directory))` to
   `ROOT/python/seed/provider_script.json`; starts `xsjs_serve.TtydServer(values,
   root, 0, sys.stderr.fileno())` with SIGINT and SIGTERM blocked around the
   start, as the demo's `server_start` does; opens the address; waits for the
   gold's `served.band` with the box enabled; checks `served.picture`.
6. Each rung of the gold's `rungs`, in order, under `rung_seconds`: each of its
   steps by 3.4.5.
7. Rung `audit`: waits until `audit_read.requests_open` of the root's whole
   entries is empty, runs `audit_read.failure_check`, requires exactly one line
   starting `==== engine started, ` in `_audit.txt`, and under `--debug` copies
   the audit to `build/test_guide_<name>/audit.txt`.
8. Rung `left`: lists the pids of ttyd's children whose command line holds the
   root's `bootstrap.py`, by `/proc`; opens `about:blank`; waits for them to
   end; stops ttyd and requires the gold's `ttyd_code`.
9. On a pass removes the work directory and returns 0. On `CheckFailed`
   renews the timer, copies the audit when it exists, saves
   `failed_<rung>.png`, stops ttyd when it runs, prints `error: RUNG: FAILURE`
   to stderr and returns 1. `KeyboardInterrupt` returns 130. Any other
   exception gets the note of the rung and is raised.
10. Under `--verbose` each rung prints one line after its name, as the demo.

3.4.4. The page state, read by one `Runtime.evaluate` of a script of
`guide_walk.py`: `fault`, the text of `body > pre` or null; `subtitle`, the
text of `#subtitle`; `disabled` of `#input`; `image_hidden`, `image_width`,
`image_height` of `#image`; `image_colours`, the distinct `r g b a` texts of
its pixels by `getImageData`. A state with a fault fails the rung at once.

3.4.5. A step:

1. Refuse, as `CheckFailed`, a step whose `band` equals the band before it.
2. Type each character of `say` as a `keyDown` with its `key` and `text`, then
   Enter, by `Input.dispatchKeyEvent`, at the focus. No step clicks: the box
   takes the focus at the first render and at each turn's end.
3. Wait until `subtitle` equals `band` and the box is enabled.
4. With `picture`: read the state once. `hidden` must equal `image_hidden`;
   when not hidden, `image_width` and `image_height` must equal `size` and the
   sorted `image_colours` must equal the sorted `colours`.
5. With `rows`: for each `{db, sql, params, rows}`, open
   `file:ROOT/DB.sqlite?mode=ro` by `sqlite3`, run `sql` with `params`, turn
   each row into a list, and poll until the list of rows equals `rows`. A
   timeout names the last rows read.

3.4.6. The gold of a guide, `python/test_setting_test_guide_<guide>.json`:

```json
{
  "poll_seconds": 0.1,
  "rung_seconds": 60,
  "served_seconds": 240,
  "window_width": 1280,
  "window_height": 720,
  "root_debug": true,
  "root_verbose": false,
  "root_label": "smoke-test",
  "ttyd_code": 0,
  "served": {
    "band": "How can I help you?",
    "picture": {"hidden": false, "size": 4, "colours": ["0 0 0 255"]}
  },
  "rungs": [
    {
      "rung": "creation",
      "label": "smoke-test",
      "steps": [
        {
          "say": "Take me flying",
          "band": "<the introduction, verbatim>",
          "picture": {"hidden": false, "size": 16, "colours": ["0 0 0 255", "255 255 255 255"]},
          "rows": [
            {"db": "metaverse", "sql": "SELECT name, title, player, world FROM universe", "params": [], "rows": [["barnstorming", "The First Ride's Free", "player", "summer"]]}
          ]
        }
      ]
    }
  ]
}
```

A band is the exact text of `#subtitle`. A band composed from a script's `say`
and a reply's `content` is the `say`, one space, then the `content`.

3.4.7. The three programs, written by T68, the same but for the name and the
first lines of their header:

```python
#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The guide test of Ruth Calloway, The First Ride's Free, one of the three
# tests of the end to end level: the engine page walked by
# python/guide_walk.py through her scripted table and flight model in
# python/guides/ruth/, as its gold, python.test_guide_ruth, says.

import os, sys

# The guide's name: its directory in python/guides and its gold's id.
_GUIDE_NAME = "ruth"

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "build",
    "pycache",
)


# Runs the guide test with the arguments after the program's name.
def main(arguments: list[str]) -> int:
    import guide_walk

    return guide_walk.guide_main(arguments, _GUIDE_NAME)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### 3.5. The sim contract

3.5.1. A guide's `sim.js` is the body of the function `script_run` makes,
`new Function("engine", "args", text)`, as `python/seed/bootstrap.js` is. It
begins with the SPDX lines and a header of what it models and its args, then:

1. `const store = engine.store;` and the world's name as a constant.
2. The model's constants, each with a one line comment naming its source.
3. Helpers that read the one state row, write it, append a log row and format
   numbers.
4. One function per action, in a frozen object `actions`.
5. `if (!Object.hasOwn(actions, args.action)) { throw new Error(...) }`, a
   table's bug, then `return store.transaction_run(() =>
   actions[args.action](args));`.

3.5.2. Every action returns `{say, outcome}`: `say` the text the page shows,
`outcome` one word of the action's outcomes. The tool result the fake reads is
then `{"value":{"say":"...","outcome":"..."}}`, so a node's `after_holds` is
`"outcome":"WORD"`, quotes and colon as `JSON.stringify` writes them, and its
`quote` is `value.say`.

3.5.3. Tables: every sim table is `STRICT`, every column `INTEGER` or `TEXT`
and `NOT NULL`. A value bound is an integer made by `Math.round` or a string.
No statement uses `random()`, a time function, or anything else that differs
when the server replays it.

3.5.4. A player's choice that fails is an outcome with its own `say`, never a
throw; a throw is a broken table, an action unknown or args of the wrong form.

3.5.5. Number formats, each a helper of the sim, used exactly as the guide's
section says:

- whole: `String(Math.round(x))`.
- tenths: `(Math.round(x * 10) / 10).toFixed(1)`, as `1.5`, `6.0`, `8.3`.
- money from integer cents: `"$" + Math.floor(c / 100) + "." +
  String(c % 100).padStart(2, "0")`, as `$46.85`.
- clock from whole seconds: `Math.floor(s / 60) + ":" + String(s %
  60).padStart(2, "0")`, as `4:02`, `1:40`.
- hour of the day: `h + ":00"`, as `2:00`, `13:00`.
- duration from whole minutes: `H hour` or `H hours`, then ` M minutes` when M
  is not 0, as `5 hours`, `4 hours 30 minutes`, `1 hour`.
- a constant shown as written in its source, as `352.56` and `10.66`, by
  `String`.

### 3.6. Files

New:

- `python/guide_walk.py`, `API/python/guide_walk.pyi`.
- `python/test_guide_walk.py`, `python/test_setting_test_guide_walk.json`.
- `python/test_guide_isaiah.py`, `python/test_guide_ruth.py`,
  `python/test_guide_dawa.py`.
- `python/test_setting_test_guide_isaiah.json`,
  `python/test_setting_test_guide_ruth.json`,
  `python/test_setting_test_guide_dawa.json`.
- `python/guides/<guide>/table.json`, `sim.js`, `prompt.txt` and
  `introduction.txt`, for `isaiah`, `ruth` and `dawa`.

Changed:

- `declawed.md`: the Testing table of the Project Rules (T66), the rule
  sections after `## Map` (T74).
- `API/ts/provider_script.d.ts`, `i18n/en-US.json`.
- `ts/provider_script.ts`, `ts/test_provider_script.ts`,
  `ts/test_setting_test_provider_script.json`.
- `python/test_all.py`, `test_posix.sh`, `python/test_integrate_test_posix.py`.

Unchanged by decision: `python/test_demo.py`, `python/test_wire.py`,
`python/test_browser.py` and their golds; `python/seed/*`; every PowerShell
file; `README.md` and `docs/CONTRIBUTING.md`, which name no level;
`python/reformat_whitelist.txt`, which the maintainer said to leave alone.

### 3.7. What the guide files hold

- `introduction.txt`: the introduction of `guides.md`, the text after
  `> ` on its one line, exactly, then one newline.
- `prompt.txt`: the universe's prompt document's text, ending in a newline: who
  the guide is, in the guide's voice and world; the rules every experience
  follows, from `guides.md`; the guide's beats; the exit and how to
  resume; the script's name, each action and its args, and that the AI calls
  the script and says its `say`; that the guide stays inside its own world and
  answers anything outside it in-world, by policy flag 1 of `guides.md`.
  The fake AI never reads it; a real AI would.
- `sim.js`: by 3.5 and the guide's section.
- `table.json`: by 3.3 and the guide's section.

## 4. The level change, sentence by sentence

4.1. `declawed.md`, Project Rules, Testing, the level table, by T66. The rows
of `(none)` and `--test-normal` become:

```text
  option           level       what the run adds
  (none)           end-to-end  the guide tests of Isaiah Cole, Ruth Calloway
                               and Dawa, their smoke-test rungs
  --test-normal    normal      the suites and blocks labelled smoke-test, the
                               checks of test_posix.py, without formatting,
                               and the wire, browser and demo tests, their
                               smoke-test rungs
```

The `--test-all` and `--test-disabled` rows, every bullet of Testing and every
other Project Rule stay word for word. "After making changes, run the end to
end tests alone, `./test_posix.sh`." stays, and now runs the guide tests.

4.2. `test_posix.sh`, by T68. The header's sentences from "Without an option"
to "the higher of them." become: "Without an option it runs at the end to end
level, the three guide tests alone: Isaiah Cole, Ruth Calloway and Dawa, each
walked on the engine page through the scripted AI. --test-normal raises the
level to the smoke-test suites, the checks of test_posix.py and the wire,
browser and demo tests too. --test-all raises it to the suites of both labels
and the test-all rungs, and counts the lines each module's own suites run, by
--coverage, which fails at a module's first line never run. --test-disabled
raises it to everything disabled too, with no count. An option only raises the
level, so giving two is the higher of them." The usage text's second sentence
becomes: "Runs python3 python/test_all.py with the options, at the end to end
level, the guide tests, when no level is given, and --coverage with
--test-all, unless --test-disabled is given too."

4.3. `python/test_all.py`, by T68:

1. Header, first sentence: "The one runner of every test suite, by level: end
   to end with no option, the guide tests alone, then --test-normal,
   --test-all and --test-disabled, each holding the one below it."
2. The parser's description: "Run the tests of a level. With no option, the
   end to end level: the guide tests of Isaiah Cole, Ruth Calloway and Dawa.
   Above it come the Python test modules and the TypeScript blocks in the
   testing order, the tests of the TAP modules first, as one TAP stream on
   stdout, the stream checked, then the checks of test_posix.py, the wire
   test, the browser test, the demo test and the guide tests."
3. `--test-normal`'s help: "raise the run from the end to end level to the
   normal level: the suites labelled smoke-test, the checks of test_posix.py,
   then the wire, browser and demo tests before the guide tests".
4. The comment of `programs_run`: "Runs the run's end to end programs in
   order, returning the first code not 0."
5. 3.1.1 and 3.1.2, and `("test_guide_walk", "smoke-test")` in `_MODULES`
   directly after `("test_xsjs_serve_death", "test-all")`, and
   `"test_guide_walk": ()` in `_COUNTED`, in its sorted place.

4.4. `python/test_integrate_test_posix.py`, by T68. `TestDriverLevels` keeps
its four tests and gains three, with two constants at the top beside
`_LEVELS`:

```python
# The end to end programs of a run with no option, the guide tests.
_GUIDE_PROGRAMS = ["test_guide_isaiah", "test_guide_ruth", "test_guide_dawa"]

# The end to end programs a run with a stream runs before the guide tests.
_NORMAL_PROGRAMS = ["test_wire", "test_browser", "test_demo"]
```

1. `test_default_guides`: `test_all.programs_chosen(False)` equals
   `_GUIDE_PROGRAMS`.
2. `test_normal_programs`: `test_all.programs_chosen(True)` equals
   `_NORMAL_PROGRAMS + _GUIDE_PROGRAMS`.
3. `test_programs_present`: each name of `test_all.programs_chosen(True)` is a
   file `python/<name>.py` of the checkout.

No other test asserts what the end to end level runs: `grep` found the old
three named only in `programs_run` and the help texts.

4.5. The rule sections of `declawed.md`, by T74 (section 6.6).

## 5. The guides

### 5.1. What the three walks share

5.1.1. The rungs of each walk: `served`, `creation`, `confirm`, `talk`,
`build`, the beats of the guide, `keepsake`, then `audit` and `left`. Every
rung is labelled smoke-test.

5.1.2. The creation turn, in every table:

1. Node `hyperposition`, the table's `start`: `replies` holds the guide's
   request phrase, whose reply calls `browser_image_make` with a prompt for the
   scene and the key `<guide>/<scene>.png`, next `made`. Its `otherwise` is in
   the analyst's dry voice, naming what the player can ask for, next
   `hyperposition`.
2. `made`: `after_tools` calls, in one reply, `browser_script_run` of
   `bootstrap` with `title`, `region`, `universe`, `world` and `scene` `{id,
   subtitle: {"$text": "introduction.txt"}, image: "/_files/<guide>/<scene>.png"}`,
   then `browser_doc_put` of `{db: UNIVERSE, id: "prompt", body: {"0": {"t":
   "prompt"}, "text": {"$text": "prompt.txt"}}}`, next `booted`.
3. `booted`: `after_tools` calls `browser_render` with the image and the
   introduction, next `shown`. The image is made a reply before the render, as
   a render reads the image's bytes when it runs.
4. `shown`: `after_tools` says `{"$text": "introduction.txt"}`, next `offer`.

The band is the introduction, the picture shown, 16 by 16, of the two colours
of the test pattern, and the server's `metaverse` holds the universe row and
`world` the guide's world.

5.1.3. The build turn: one reply of three calls, `browser_kv_put` of
`{ref: "/_files/script/<guide>.js", text: {"$text": "sim.js"}}`,
`browser_sql_run` of the guide's DDL on its world, `browser_script_run` of
`{name: "<guide>", args: {action: "setup", ...}}`, next `built`, whose
`after_tools` quotes `value.say` and says the first beat's `ask`.

5.1.4. A beat: the node holds `ask` and replies keyed by the walk's inputs,
each calling `browser_script_run` with the choice as args, next an after node.
The after node either always goes on, `after_tools` quoting `value.say` with
the next node's `ask` as content; or holds `after_holds` `"outcome":"WORD"`,
going on by `after_tools` and back by `after_lacks`, whose content re-asks.

5.1.5. The call ids of a table are `call_` and a short word, unique within each
reply; the exit's are `call_exit` and `call_resume`.

5.1.6. Each walk holds one bad input at a node with `ask`, answered by the
built `otherwise`: the guide's `puzzled` words then the question again.

5.1.7. The keepsake turn: with a picture, as Ruth's and Dawa's, one reply
calls `browser_image_make` of the keepsake's picture, next a node whose
`after_tools` calls `browser_render` of it then `browser_script_run` of
`{action: "keepsake"}`, so that the quote reads the script's result, the last;
with none, as Isaiah's, the reply calls the `browser_script_run` alone. The
node the script's result reaches quotes `value.say` with the guide's farewell
as content, next `end`. `end` holds empty `replies` and an `otherwise` of the
guide's last words, next `end`.

5.1.8. Throughout, the three kinds of input: numbers (`60`, `90`, `10`, `20`,
`2`, `7`), words (`Yes`, `Sam`, `Settled`, `East`, `Ready`, `Everything`,
`Go`), and phrases (`What if I hate it?`, `I tap my head twice`, `I'll fly, you
walk`, `No thanks, take me back`, `Streets of Laredo`, `We take Teo down`).
Some are typed with capitals and matched in lower case, which proves the
normal form.

### 5.2. Isaiah Cole: Two Thousand Head to Dodge

5.2.1. Names. Universe `trail_drive`, title `Two Thousand Head to Dodge`,
world `drive`, region `trail`, scene `campfire` with the image
`/_files/isaiah/campfire.png`, script `isaiah`. The stake is the herd, counted
at Dodge City; the keepsake is a trail name.

5.2.2. Constants of the drive, each the guide's own, from its text or its
rules: `HERD` 2000 (introduction); `MILES` 100 (pitch, "the last hundred
miles"); `MILES_A_DAY` 10 (Isaiah's reckoning); `MISSING` 40 (the guide, "forty
head are missing"); `CALM_START` 5, `SONG_CALM` 3, `CALM_MAX` 10,
`SETTLED_CALM` 7, `MILLED_CALM` 3 (the herd's calm, a game rule of 0 to 10);
`BUNCHES` ridge 12, creek 25, draw 3, summing to `MISSING`, each with its cover
cedars, willows, plum thicket; `LOOKS` 3 (searches before noon); `BREAKS_LOSS`
60 (the run into the breaks); `HIGH_WATER_PER` 100 (a head drowned for each 100
swum in high water); `TOLL_FLOOR` 20 (the least the outfit takes);
`WAGE_CENTS` 100 (a dollar a day).

5.2.3. DDL on `drive`, the build turn's `sql_run`, three statements:

```sql
CREATE TABLE herd (id INTEGER PRIMARY KEY CHECK (id = 1), head INTEGER NOT NULL, scattered INTEGER NOT NULL, lost INTEGER NOT NULL, tolled INTEGER NOT NULL, calm INTEGER NOT NULL, looks INTEGER NOT NULL, found INTEGER NOT NULL, waited INTEGER NOT NULL, exits INTEGER NOT NULL, song TEXT NOT NULL) STRICT
CREATE TABLE drive_log (n INTEGER PRIMARY KEY, beat TEXT NOT NULL, choice TEXT NOT NULL, outcome TEXT NOT NULL) STRICT
CREATE TABLE keepsake (kind TEXT NOT NULL PRIMARY KEY, text TEXT NOT NULL) STRICT
```

`looks` counts the looks used; `found` the scattered head found again.

5.2.4. Actions. Each appends a `drive_log` row `(beat, choice, outcome)` but
`setup` and `keepsake`. The `say` texts of the walk are exact; the others are
the worker's, by the same rules.

1. `setup`: inserts `(1, 2000, 0, 0, 0, 5, 0, 0, 0, 0, '')`. Say: "2000 head
   bedded on the flat and 100 miles to Dodge City: 10 days at 10 miles a day.
   The herd's calm is 5 of 10." Outcome `ready`.
2. `sing {song}`: calm to the lesser of 10 and calm plus 3; song kept. Say:
   "You ride the slow circle singing Streets of Laredo, and the herd's calm
   comes up from 5 to 8 of 10." Log `sing`, the song, `calmer`.
3. `exit`: exits plus 1. Say: "You ride back to the fire and the coffee.
   Isaiah keeps the circle alone, singing, and the 2000 head stay down." Log
   `exit`, `fire`, `at the fire`.
4. `resume`: Say: "You ride out again to the herd: 2000 head, calm 8 of 10."
   Log `resume`, `herd`, `riding`.
5. `read {judge}`: the truth is `settled` when calm is 7 or more, else
   `restless`. Wrong: "Long slow breaths and the cud going: calm 8 of 10 is
   settled, not restless." outcome `wrong`. Right: "Long slow breaths and the
   cud going: calm 8 of 10, settled, and you read it right." outcome `right`.
   The wrong text for a restless herd read as settled is the worker's. Log
   `read`, the judge, the outcome.
6. `stampede {flank}`: east: head minus 40, scattered 40, calm 3. Say: "You
   ride for the leaders on the east flank and bend the run west into a circle,
   short of the breaks. At sunrise the count is 1960: 40 head scattered, and 3
   looks before noon to find them." outcome `circled`. West, not walked: head
   minus 100, scattered 40, lost 60, calm 3, "... the breaks ...", outcome
   `broken`. Log `stampede`, the flank, the outcome.
7. `track {place}`: a place not yet searched gives its bunch back to the herd;
   one searched already gives 0; looks plus 1; when scattered reaches 0 or
   looks reach 3 the outcome is `done`, else `searching`, and at `done` any
   head still out move to `lost` with " The N still out are lost for good."
   appended. Walked:
   - ridge: "Up on the ridge: 12 head in the cedars, driven back. 1972 with
     the herd, 28 still out, looks used 1 of 3." `searching`.
   - creek: "Along the creek: 25 head in the willows, driven back. 1997 with
     the herd, 3 still out, looks used 2 of 3." `searching`.
   - draw: "Down in the draw: 3 head in the plum thicket, driven back. 2000
     with the herd, 0 still out, looks used 3 of 3." `done`.
   Which places were searched is read from `drive_log`. Log `track`, the
   place, the outcome.
8. `river {choice}`: wait: waited plus 1. Say: "You hold the herd a day on the
   south bank of the Cimarron and the water drops: all 2000 swim it, leaders
   first, and none is lost. 1 day spent waiting." outcome `crossed`. Swim now,
   not walked: lost plus head divided by 100, rounded down. Log `river`,
   `wait` or `swim`, the outcome.
9. `toll {offer}`: under 20: "You offer 10 head. The outfit's boss spits: 20
   is the least he takes." outcome `refused`. At 20 or more: head minus the
   offer, tolled plus it: "You offer 20 head and the rope comes down: 1980 head
   cross the ford." outcome `paid`. Log `toll`, the offer as text, the outcome.
10. `count`: days are 100 / 10 plus waited. Say: "At the stockyard gate the
    tally man counts 1980 head: 2000 from the bed ground, 20 paid at the ford
    and 0 lost on the trail. 11 days on the trail at $1.00 a day: $11.00 in
    wages, and a bath." outcome `delivered`. Log `count`, the head as text,
    `delivered`.
11. `keepsake`: the trail name is the last word of the song. Text: "Trail name:
    Laredo. Rode night guard with Isaiah Cole, turned the stampede, tracked 40
    head and brought 1980 to Dodge City." ("rode out the stampede" when the
    flank was west.) Inserts `('trail name', TEXT)`. Say: the text. Outcome
    `named`.

5.2.5. Exit: input `i'll ride back to the fire`, call `{name: "isaiah", args:
{action: "exit"}}`, resume `ride out again`, resume call `{action:
"resume"}`; the `after`, `paused` and `puzzled` texts are the worker's, in
Isaiah's voice, numberless.

5.2.6. Nodes, in order: `hyperposition` (request `take me on a cattle drive`),
`made`, `booted`, `shown`; `offer` with replies `no thanks, take me back` (one
reply calling `browser_kv_put` of `{ref: "/metaverse/world", text:
"metaverse"}` then `browser_render` of `{image:
"/metaverse/image/hyperposition", subtitle: "How can I help you?"}`, next
`left`) and `yes` (content: Isaiah takes you on, and opens the talk, next
`talk`), with an `otherwise` that leaves the offer open, next `offer`; `left`
(after: "How can I help you?", next `away`); `away` with reply `actually, the
cattle drive` (one reply calling `browser_kv_put` of `{ref:
"/metaverse/world", text: "drive"}` then `browser_render` of the campfire
image, next `back`) and the analyst's `otherwise`; `back` (after: Isaiah's
welcome back, next `offer`); `talk` with replies `how long have you been riding
night guard?` (content, next `talk`) and `let's ride out` (the build), and an
`otherwise`; `built`; `guard` (ask, reply `streets of laredo`), `sung`; `read`
(ask, replies `restless` and `settled`), `judged` (holds `"outcome":"right"`,
lacks re-asks, next `read`); `stampede` (ask, reply `east`), `turned`; `track`
(ask, replies `the ridge`, `the creek`, `the draw`), `tracked` (holds
`"outcome":"done"`, lacks asks where next, next `track`); `river` (ask, reply
`wait a day`), `crossed`; `toll` (ask, replies `10` and `20`), `tolled` (holds
`"outcome":"paid"`, lacks re-asks, next `toll`); `dodge` (ask, reply `count
them in` calling `browser_image_make` of the key `isaiah/dodge.png`, next
`gate`); `gate` (after: one reply calling `browser_doc_put` of `{db: "trail",
id: "stockyard", body: {"0": {"t": "scene"}, "1": "/_files/isaiah/dodge.png",
"image": {"$ref": 1}, "subtitle": "The stockyard gate at Dodge City."}}`, then
`browser_kv_put` of `{ref: "/drive/scene", text: "/trail/stockyard/1"}`, then
`browser_render` of the Dodge image, then `browser_script_run` of `{action:
"count"}`, next `counted`); `counted` (quotes, asks the naming); `naming` (ask,
reply `yes`, the keepsake), `named`; `end`. The stockyard is a new scene, so
the naming turn is a new conversation that proves the world's state outlived
the scene, rule 6.

The args of each walked `script_run`, under `{name: "isaiah", args: ...}`:
`{action: "setup"}`; `streets of laredo` `{action: "sing", song: "Streets of
Laredo"}`; `restless` and `settled` `{action: "read", judge: "restless"}` and
`judge: "settled"`; `east` `{action: "stampede", flank: "east"}`; `the ridge`,
`the creek`, `the draw` `{action: "track", place: "ridge"}`, `"creek"`,
`"draw"`; `wait a day` `{action: "river", choice: "wait"}`; `10` and `20`
`{action: "toll", offer: 10}` and `offer: 20`, numbers; `{action: "count"}`;
`yes` at `naming` `{action: "keepsake"}`.

5.2.7. The walk:

| Step | Rung | Typed | Band | Checks |
|---|---|---|---|---|
| 1 | creation | Take me on a cattle drive | the introduction | picture 16; universe `["trail_drive", "Two Thousand Head to Dodge", "player", "drive"]`; world `drive` |
| 2 | confirm | No thanks, take me back | How can I help you? | picture 4, `["0 0 0 255"]`; world `metaverse` |
| 3 | confirm | Actually, the cattle drive | Isaiah's welcome back | picture 16; world `drive` |
| 4 | confirm | yes | the talk opener | |
| 5 | talk | How long have you been riding night guard? | his story | |
| 6 | build | Let's ride out | setup say, guard ask | |
| 7 | night guard | Streets of Laredo | sing say, read ask | herd `[1, 2000, 0, 0, 0, 8, 0, 0, 0, 0, "Streets of Laredo"]` |
| 8 | night guard | I'll ride back to the fire | exit say, exit after | herd exits 1 |
| 9 | night guard | Ride out again | resume say, read ask | |
| 10 | reading | Restless | wrong say, re-ask | |
| 11 | reading | Settled | right say, stampede ask | |
| 12 | stampede | East | stampede say, track ask | herd `[1, 1960, 40, 0, 0, 3, 0, 0, 0, 1, "Streets of Laredo"]` |
| 13 | tracking | Which way did they go? | puzzled, track ask | |
| 14 | tracking | The ridge | ridge say, where next | |
| 15 | tracking | The creek | creek say, where next | |
| 16 | tracking | The draw | draw say, river ask | |
| 17 | river | Wait a day | river say, toll ask | |
| 18 | toll | 10 | refused say, re-ask | |
| 19 | toll | 20 | paid say, dodge ask | |
| 20 | dodge | Count them in | count say, naming ask | picture 16; `drive` row `scene` is `/trail/stockyard/1` |
| 21 | keepsake | yes | keepsake say, farewell | herd, log, keepsake below |

The world row is read by `SELECT CAST(data AS TEXT) FROM _kv WHERE key = ?`
with `["world"]` on `metaverse`, and the scene row the same way with
`["scene"]` on `drive`. The herd by `SELECT id, head, scattered, lost, tolled,
calm, looks, found, waited, exits, song FROM herd`. Step 8's herd is `[1, 2000,
0, 0, 0, 8, 0, 0, 0, 1, "Streets of Laredo"]`. Step 21 needs: herd `[1, 1980,
0, 0, 20, 3, 3, 40, 1, 1, "Streets of Laredo"]`; `SELECT n, beat, choice,
outcome FROM drive_log ORDER BY n`:

```json
[[1, "sing", "Streets of Laredo", "calmer"], [2, "exit", "fire", "at the fire"],
 [3, "resume", "herd", "riding"], [4, "read", "restless", "wrong"],
 [5, "read", "settled", "right"], [6, "stampede", "east", "circled"],
 [7, "track", "ridge", "searching"], [8, "track", "creek", "searching"],
 [9, "track", "draw", "done"], [10, "river", "wait", "crossed"],
 [11, "toll", "10", "refused"], [12, "toll", "20", "paid"],
 [13, "count", "1980", "delivered"]]
```

and `SELECT kind, text FROM keepsake ORDER BY kind`: `[["trail name", "Trail
name: Laredo. Rode night guard with Isaiah Cole, turned the stampede, tracked
40 head and brought 1980 to Dodge City."]]`.

5.2.8. Hand check. 5 + 3 = 8; 8 is 7 or more, so settled. 2000 - 40 = 1960;
1960 + 12 = 1972, 40 - 12 = 28; 1972 + 25 = 1997, 28 - 25 = 3; 1997 + 3 =
2000, 3 - 3 = 0. 2000 - 20 = 1980. 100 / 10 + 1 = 11 days, 11 x 100 cents =
$11.00.

### 5.3. Ruth Calloway: The First Ride's Free

5.3.1. Names. Universe `barnstorming`, title `The First Ride's Free`, world
`summer`, region `county`, scene `hayfield` with the image
`/_files/ruth/hayfield.png`, script `ruth`. The stake is Ruth's purse for the
summer and her airplane; the keepsake a handbill with the player's name beside
hers.

5.3.2. The model's constants and their sources, the comments of `sim.js`:

| Constant | Value | Source |
|---|---|---|
| `GROSS_LB` | 1920 | Curtiss JN4-D Specifications and Operating Instructions, 1918, as reproduced at airminded.net/jenny/jn4_spec.html: gross weight, machine loaded, which counts pilot 165, passenger 165 and fuel 21 gallons |
| `WING_SQFT` | 352.56 | the same: total supporting surface |
| `HP` | 90 | the same: OX-5 rated at 1400 rpm |
| `MAX_MPH` | 75 | the same: speed, maximum, horizontal flight |
| `MIN_MPH` | 45 | the same: speed, minimum, horizontal flight, the 1 g stall |
| `CLIMB_FT`, `CLIMB_MIN` | 2000, 10 | the same: climb in 10 minutes, 2000 ft |
| `TANK_GAL` | 21 | the same: fuel tank capacity |
| `BURN_GAL_HR` | 9 | the same: fuel consumption per hour |
| `LEVEL_OFF_FT` | 50 | the same, operating instructions: final leveling off about fifty feet from the ground |
| `CRUISE_MPH` | 60 | P. M. Bowers, Curtiss Aircraft 1907 to 1947 (1979), p. 156, JN-4D cruise |
| `GLIDE_RATIO` | 10.66 | B. van der Zalm, aircraftinvestigation.info, Curtiss JN-4D (2018): lift to drag ratio calculated from published data, as no period source gives the Jenny's glide |
| `G` | 32.174 | standard gravity, ft/s/s |
| `FPS_PER_MPH` | 22 / 15 | 5280 ft over 3600 s |
| `LOOP_PULL_G` | 4 | Ruth's technique: the pull at the bottom of the loop |
| `LOOP_TOP_G` | 0.5 | Ruth's technique: light over the top |
| `ROLL_SECONDS` | 4 | Ruth's count for a roll |
| `RIDE_CENTS`, `RIDE_MIN` | 500, 10 | the introduction: "Five dollars buys ten minutes" |
| `GAS_CENTS_GAL` | 21 | U.S. Department of Energy, Vehicle Technologies Office, Fact #915 (2016): average pump price of 1929 |
| `MOTORCAR_MPH` | 45 | the Ford Model T's top speed of about 45 mph, as The Henry Ford gives it |
| `WIND_MPH` | 15 | the day's wind, from the north, a constant of the guide's world |
| `RACE_MI` | 5 | the county road race, the guide's world |
| `PURSE_CENTS` | 2500 | the fair's race purse, the guide's world |
| `SHOW_MIN` | 40 | the evening show's flying, the guide's world |
| `STUNT_FT` | 2000 | where Ruth teaches, the guide's world |
| `SHOW_FT` | 1000 | the wing walk's height and where the engine quits, the guide's world |
| `NORTH_MI`, `SOUTH_MI` | 1.5, 3 | the fields' distances, the guide's world |

5.3.3. The model's formulas, every speed in ft/s inside, mph outside:

1. Load factor in a level turn at bank `b`: `n = 1 / cos(b)`.
2. Stall speed at load factor `n`, from lift `L = n W` at the wing's greatest
   lift coefficient: `Vs(n) = MIN_MPH * sqrt(n)`. A turn at cruise stalls when
   `Vs(n) > CRUISE_MPH`.
3. Turn radius `r = V^2 / (G tan b)` and time round `t = 2 pi V / (G tan b)`,
   at `V` the cruise.
4. Loop, two arcs with energy kept, the engine's pull and the drag taken to
   cancel: bottom arc radius `Rb = Ve^2 / (G (LOOP_PULL_G - 1))`, top arc radius
   `Rt = Vt^2 / (G (LOOP_TOP_G + 1))`, energy `Vt^2 = Ve^2 - 2 G (Rb + Rt)`, so
   `Vt^2 = Ve^2 (1 - 2 / (LOOP_PULL_G - 1)) / (1 + 2 / (LOOP_TOP_G + 1))`, which
   is `Ve^2 / 7` for 4 and 0.5. Over the top the wing flies at
   `LOOP_TOP_G` only above `MIN_MPH * sqrt(LOOP_TOP_G)`, so the loop is made
   when `Vt` reaches that; the entry it wants is that speed times `sqrt(7)`.
   The dive to reach `Ve` from cruise costs `(Ve^2 - Vc^2) / (2 G)` of height,
   and the top is `Rb + Rt` above the pull.
5. Roll at `MAX_MPH`, a zero g roll of `ROLL_SECONDS`: height change `dh = V
   sin(nose) T - G T^2 / 2`; it keeps height when `sin(nose) >= G T / (2 V)`.
6. Glide with the engine off at the cruise speed: still air distance `h *
   GLIDE_RATIO`, sink rate `V / GLIDE_RATIO`, time `h * GLIDE_RATIO / V`; over
   the ground, into the wind times `(V - W) / V`, with it times `(V + W) / V`.
7. Touchdown at `MIN_MPH` through the air: ground speed `MIN_MPH - W` into the
   wind, `MIN_MPH + W` with it.
8. Fuel `minutes * BURN_GAL_HR / 60`; gas money `gallons * GAS_CENTS_GAL`,
   rounded to whole cents.

5.3.4. DDL on `summer`:

```sql
CREATE TABLE jenny (id INTEGER PRIMARY KEY CHECK (id = 1), partner TEXT NOT NULL, altitude_ft INTEGER NOT NULL, resume_ft INTEGER NOT NULL, exits INTEGER NOT NULL, purse_cents INTEGER NOT NULL) STRICT
CREATE TABLE flight (n INTEGER PRIMARY KEY, beat TEXT NOT NULL, choice TEXT NOT NULL, outcome TEXT NOT NULL) STRICT
CREATE TABLE keepsake (kind TEXT NOT NULL PRIMARY KEY, text TEXT NOT NULL) STRICT
```

5.3.5. Actions, each logging `(beat, choice, outcome)` to `flight` but `setup`
and `keepsake`. The walk's says, exact, with the hand work behind each:

1. `setup {partner}`: inserts `(1, partner, 0, 0, 0, 0)`. Say: "The Jenny: a
   Curtiss JN-4D with a 90 horsepower OX-5, 352.56 square feet of wing, and
   1920 pounds aboard with the two of us and 21 gallons of gasoline. She stalls
   at 45 mph, cruises at 60 and tops out at 75." Outcome `ready`.
2. `climb`: to `STUNT_FT` from the altitude, minutes `(2000 - 0) / 200 = 10`,
   gallons `10 * 9 / 60 = 1.5`. Say: "Up to 2000 feet in 10 minutes, the
   book's 200 feet a minute, on 1.5 gallons of gasoline." Altitude 2000. Log
   `climb`, `2000`, `made`.
3. `exit`: from 2000: distance `2000 * 10.66 = 21320` ft; sink `88 / 10.66 =
   8.2552`, shown `8.3`; time `21320 / 88 = 242.27`, `242` s, `4:02`. Say:
   "Throttle closed at 2000 feet. Gliding at 60 mph, 10.66 feet on for every
   foot down, she sinks 8.3 feet a second and settles onto the grass 21320
   feet on, in 4:02, like a feather." Altitude 0, resume 2000, exits 1. Log
   `exit`, `2000`, `landed`. From the ground: "We're on the grass already.",
   log `exit`, `0`, `grounded`.
4. `resume`: back to the resume height, 10 minutes, 1.5 gallons. Say: "Back up
   to 2000 feet in 10 minutes, on 1.5 gallons more." Altitude 2000, resume 0.
   Log `resume`, `2000`, `made`. With nothing to resume: "Ready when you
   are.", log `resume`, `0`, `made`.
5. `turn {bank}`, at 88 ft/s:
   - 60: `n = 2.0000`, stall `45 * 1.41421 = 63.64`, over 60. Say: "At 60
     degrees of bank she pulls 2.0 g and stalls at 64 mph, over your 60: the
     wing quits and Ruth catches her." Outcome `stalled`.
   - 30: `n = 1 / 0.866025 = 1.1547`, shown `1.2`; stall `45 * 1.074570 =
     48.36`, `48`; `tan 30 = 0.577350`, `G tan b = 18.5757`; radius `7744 /
     18.5757 = 416.89`, `417`; time `2 pi 88 / 18.5757 = 552.920 / 18.5757 =
     29.77`, `30`. Say: "At 30 degrees of bank she pulls 1.2 g and stalls at 48
     mph, under your 60: a circle 417 feet in radius, flown round in 30
     seconds." Outcome `made`.
   Log `turn`, the bank as text, the outcome.
6. `loop {entry_mph}`. Top stall at 0.5 g: `45 * 0.707107 = 31.82`, shown
   `32`; entry wanted `31.82 * 2.645751 = 84.19`, `84`.
   - 80: `Vt = 80 / 2.645751 = 30.24` mph, `30`, under 31.82. Say: "Pulling 4 g
     at 80 mph, she comes over the top at 30 mph, under the 32 she needs for 0.5
     g up there: she hangs, falls off sideways, and Ruth flies her out. The
     loop wants 84 mph at the bottom." Outcome `fell`.
   - 90: `Ve = 132` ft/s; `Vt = 90 / 2.645751 = 34.02` mph, `34`; `Rb = 17424 /
     96.522 = 180.52`; `Vt^2 = 17424 / 7 = 2489.14`, `Rt = 2489.14 / 48.261 =
     51.58`; top `232.10`, `232`; dive `(17424 - 7744) / 64.348 = 150.43`, `150`.
     Say: "Dive 150 feet to 90 mph and pull 4 g: she comes over the top at 34
     mph, 232 feet above where you pulled, and down the back at 90 again. A
     loop." Outcome `made`.
   Altitude unchanged, as energy is kept. Log `loop`, the entry as text, the
   outcome.
7. `roll {nose_deg}`, at 110 ft/s, 4 s: `G T^2 / 2 = 257.392`; wanted nose
   `asin(128.696 / 220) = asin(0.584982) = 35.80`, `36`.
   - 20: `110 * 0.342020 * 4 = 150.489`, `dh = -106.90`, `107` low. Say: "Nose
     20 degrees up at 75 mph and 4 seconds round: she comes out 107 feet low. A
     roll at 75 wants 36 degrees of nose to keep her height." Outcome `sank`.
     Altitude 2000 - 107 = 1893.
   - 40: `110 * 0.642788 * 4 = 282.827`, `dh = 25.44`, `25` high. Say: "Nose 40
     degrees up at 75 mph and 4 seconds round: she comes out 25 feet high. A
     roll." Outcome `made`. Altitude 1893 + 25 = 1918.
   The altitude moves by the rounded change. Log `roll`, the nose as text, the
   outcome.
8. `buzz {feet}`: 50 or more: speed `75 * 22 / 15 = 110` ft/s. Say: "Down Main
   Street at 50 feet and 75 mph, 110 feet a second, and the handbills go over
   the side." Altitude 50, outcome `made`. Under 50, not walked: "Under the 50
   feet the book gives for leveling off? I'm bold, not stupid." outcome
   `refused`. Log `buzz`, the feet as text, the outcome.
9. `rides {count}`: gallons `count * 10 * 9 / 60`, here `15`; allowed `21 - 9 *
   40 / 60 = 21 - 6 = 15`, so 10 rides is the most. Taken `10 * 500 = 5000`
   cents; gas `15 * 21 = 315`; clear `4685`; purse 0 + 4685 = 4685. Say: "10
   rides at $5.00 for 10 minutes: $50.00 taken in 100 minutes of flying, on
   15.0 gallons of gasoline at 21 cents, $3.15. $46.85 clear, and 6.0 gallons
   left for the show's 40 minutes." Altitude 0, outcome `made`. Over the
   allowance, not walked, outcome `refused` with the gallons named. Log
   `rides`, the count as text, the outcome.
10. `race {throttle}`: full throttle: `75 - 15 = 60` mph over the road; `5 / 60
    * 3600 = 300` s, `5:00`; the motorcar `5 / 45 * 3600 = 400` s, `6:40`;
    margin `400 - 300 = 100`, `1:40`, each rounded before the difference; purse
    4685 + 2500 = 7185. Say: "Full throttle: 75 mph into a 15 mph wind is 60
    over the road, 5.0 miles in 5:00. The motorcar at 45 takes 6:40. You win by
    1:40 and the fair's $25.00 purse: $71.85 in the cigar box." Outcome `won`,
    altitude 50. Cruise, not walked: 45 over the road, 6:40 against 6:40, a
    dead heat, outcome `tied`, no purse. Log `race`, the throttle, the outcome.
11. `wing_walk {walker}`: `Ruth`: Say: "Ruth walks the top wing while you hold
    her straight and level at 60 mph and 1000 feet. Then, over open country, the
    OX-5 coughs and quits: 1000 feet up, the wind 15 mph from the north, the
    north hayfield 1.5 miles off and the south pasture 3.0." Altitude 1000,
    outcome `walked`. The player walking, not walked, has its own say. Log
    `wing_walk`, the walker, the outcome.
12. `field {field}`, from 1000 ft: still air `1000 * 10.66 = 10660` ft.
    - south, with the wind: `60 + 15 = 75` over the ground; `10660 * 75 / 60 =
      13325` ft; `13325 / 5280 = 2.524`, `2.5` miles; the field `3 * 5280 =
      15840`; short `2515`. Say: "Gliding south with the wind at 75 mph over the
      ground, 1000 feet carries you 13325 feet, 2.5 miles, and the south
      pasture is 3.0 miles off: 2515 feet short." Outcome `short`.
    - north, into the wind: `45` over the ground; `10660 * 45 / 60 = 7995` ft,
      `1.514`, `1.5` miles; the field `1.5 * 5280 = 7920`; spare `75`. Say:
      "Gliding north into the wind at 45 mph over the ground, 1000 feet carries
      you 7995 feet, 1.5 miles, and the north hayfield is 1.5 miles off: 75 feet
      to spare." Outcome `reached`.
    Altitude unchanged. Log `field`, `south` or `north`, the outcome.
13. `landing {direction}`: into the wind, `45 - 15 = 30`. Say: "Into the wind
    she touches down at 45 mph through the air and 30 over the hay, and rolls
    to a stop. Down safe." Outcome `landed`, altitude 0. With the wind, not
    walked: 60 over the hay, outcome `landed long`. Log `landing`, the
    direction, the outcome.
14. `keepsake`: the list of what the log shows made, in this order: `loops`
    for a loop made, `rolls` for a roll made, `the wing walk` for a walk,
    `a motorcar beaten` for a race won, joined by `, ` and ` and ` before the
    last. Text: "RUTH CALLOWAY AND SAM, AERIAL ACROBATS: loops, rolls, the wing
    walk and a motorcar beaten! Rides $5.00 for 10 minutes." with the partner
    in capitals. Inserts `('handbill', TEXT)`. Say: the text. Outcome `kept`.

5.3.6. Exit: input `i tap my head twice`, call `{name: "ruth", args: {action:
"exit"}}`, resume `go on`, resume call `{action: "resume"}`. After, for
example: "No questions, no teasing. Say go on when you want to go back up."
Paused, for example: "Ruth sits on the wheel in the shade. Say go on when you
want to go back up." Puzzled, for example: "Ruth cups a hand to her ear over
the engine."

5.3.7. Nodes: `hyperposition` (request `take me flying`), `made`, `booted`,
`shown`; `offer` with replies `what if i hate it?` (her promise again, then
whether you're coming, next `offer`) and `yes` (asks your name, next `name`),
and an `otherwise` that takes a no as a no and leaves the seat open, next
`offer`; `name` with reply `sam` (content opening the talk, next `talk`) and
an `otherwise` asking the name again; `talk` with replies `why are you short a
partner?` (content, next `talk`) and `let's go` (the build, `setup` with
`partner` `Sam`), and an `otherwise`; `built`; `ground` (ask, reply `take her
up`), `climbed`; `aloft` (ask, reply `your stick`, a content reply saying the
`turns` ask, next `turns`); `turns` (ask, replies `60` and `30`), `turned`
(holds `"outcome":"made"`, lacks re-asks); `loop` (ask, replies `80` and
`90`), `looped` (holds made); `roll` (ask, replies `20` and `40`), `rolled`
(holds made); `buzz` (ask, reply `50`), `buzzed` (holds made); `rides` (ask,
reply `10`), `sold` (holds made); `race` (ask, reply `full throttle`), `raced`
(goes on whatever the outcome); `wing` (ask, reply `i'll fly, you walk`, args
`{walker: "Ruth"}`), `walked`; `engine` (ask "Which field?", replies `the
south pasture` and `the north hayfield`), `glided` (holds `"outcome":"reached"`,
lacks "Pick again. Which field?"); `flare` (ask, reply `into the wind`),
`landed`; `keep` (ask, reply `yes please`: `browser_image_make` of the key
`ruth/handbill.png`, then the render and the `keepsake` run), `kept`; `end`.

The args of each walked `script_run`, under `{name: "ruth", args: ...}`:
`{action: "setup", partner: "Sam"}`; `take her up` `{action: "climb"}`; `60`
and `30` `{action: "turn", bank: 60}` and `bank: 30`; `80` and `90` `{action:
"loop", entry_mph: 80}` and `entry_mph: 90`; `20` and `40` `{action: "roll",
nose_deg: 20}` and `nose_deg: 40`; `50` `{action: "buzz", feet: 50}`; `10`
`{action: "rides", count: 10}`; `full throttle` `{action: "race", throttle:
"full throttle"}`; `i'll fly, you walk` `{action: "wing_walk", walker:
"Ruth"}`; `the south pasture` and `the north hayfield` `{action: "field",
field: "south"}` and `field: "north"`; `into the wind` `{action: "landing",
direction: "into the wind"}`; `{action: "keepsake"}`. Every number in args is
a JSON number, and the log stores it as its text.

5.3.8. The walk:

| Step | Rung | Typed | Band | Checks |
|---|---|---|---|---|
| 1 | creation | Take me flying | the introduction | picture 16; universe `["barnstorming", "The First Ride's Free", "player", "summer"]`; world `summer` |
| 2 | confirm | What if I hate it? | her promise, are you coming | |
| 3 | confirm | Yes | your name? | |
| 4 | confirm | Sam | the talk opener | |
| 5 | talk | Why are you short a partner? | her story | |
| 6 | build | Let's go | setup say, ground ask | |
| 7 | first flight | Take her up | climb say, aloft ask | jenny `[1, "Sam", 2000, 0, 0, 0]` |
| 8 | first flight | I tap my head twice | exit say, exit after | jenny `[1, "Sam", 0, 2000, 1, 0]` |
| 9 | first flight | Go on | resume say, aloft ask | |
| 10 | first flight | Your stick | turns ask | |
| 11 | turns | 60 | turn 60 say, re-ask | |
| 12 | turns | 30 | turn 30 say, loop ask | |
| 13 | loop | 80 | loop 80 say, re-ask | |
| 14 | loop | 90 | loop 90 say, roll ask | |
| 15 | roll | 20 | roll 20 say, re-ask | |
| 16 | roll | 40 | roll 40 say, buzz ask | |
| 17 | main street | 50 | buzz say, rides ask | |
| 18 | rides | lots | puzzled, rides ask | |
| 19 | rides | 10 | rides say, race ask | jenny `[1, "Sam", 0, 0, 1, 4685]` |
| 20 | race | Full throttle | race say, wing ask | |
| 21 | wing walk | I'll fly, you walk | wing say, Which field? | |
| 22 | engine out | The south pasture | south say, Pick again. Which field? | |
| 23 | engine out | The north hayfield | north say, flare ask | |
| 24 | engine out | Into the wind | landing say, keep ask | |
| 25 | keepsake | Yes please | handbill say, farewell | picture 16; jenny, flight, keepsake below |

The jenny row by `SELECT id, partner, altitude_ft, resume_ft, exits,
purse_cents FROM jenny`. Step 25 needs jenny `[1, "Sam", 0, 0, 1, 7185]`;
`SELECT n, beat, choice, outcome FROM flight ORDER BY n`:

```json
[[1, "climb", "2000", "made"], [2, "exit", "2000", "landed"],
 [3, "resume", "2000", "made"], [4, "turn", "60", "stalled"],
 [5, "turn", "30", "made"], [6, "loop", "80", "fell"],
 [7, "loop", "90", "made"], [8, "roll", "20", "sank"],
 [9, "roll", "40", "made"], [10, "buzz", "50", "made"],
 [11, "rides", "10", "made"], [12, "race", "full throttle", "won"],
 [13, "wing_walk", "Ruth", "walked"], [14, "field", "south", "short"],
 [15, "field", "north", "reached"], [16, "landing", "into the wind", "landed"]]
```

and keepsake `[["handbill", "RUTH CALLOWAY AND SAM, AERIAL ACROBATS: loops,
rolls, the wing walk and a motorcar beaten! Rides $5.00 for 10 minutes."]]`.

5.3.9. Rounding margins, checked by hand: every shown value above sits at
least 0.1 of its last shown digit from a rounding boundary, but three. The
sink, 8.25516, is 0.005 above the boundary 8.25 of its tenths; `n = 2.0` at 60
degrees, which JavaScript computes as `1.9999999999999996`; and the exact
products 21320, 7995, 13325 and 315, which `Math.round` takes from a float
error of under 0.0000001. Each is far wider than a double's error. The
reviewer recomputes all of them.

### 5.4. Dawa: Nobody Left Behind

5.4.1. Names. Universe `everest`, title `Nobody Left Behind`, world
`expedition`, region `khumbu`, scene `base_camp` with the image
`/_files/dawa/base_camp.png`, script `dawa`. The stake is Dawa's record of
never leaving anyone behind; the keepsake a photograph from the high point and
a white scarf from Dawa.

5.4.2. Constants and their sources:

| Constant | Value | Source |
|---|---|---|
| summit | 8849 m | 8848.86 m, the survey Nepal and China announced on 8 December 2020, rounded |
| camps | Base Camp 5364, Camp 1 6065, Camp 2 6400, Camp 3 7162, Camp 4 7906, South Summit 8749 m | the heights commonly given for the South Col route |
| air pressure | `P = exp(6.63268 - 0.1112 h - 0.00149 h^2)` mmHg, `h` in km | J. B. West, J Appl Physiol 81 (1996) 1850 |
| oxygen breathed in | `0.2094 (P - 47)` mmHg | oxygen's share of dry air, and the water vapour pressure at 37 C |
| sleep rise | 500 m a night above 3000 m | Wilderness Medical Society Clinical Practice Guidelines, 2019 update |
| icefall | 6 hours; the sun loosens the ice at 9:00 | Dawa's rope, the guide's world |
| window | Dawa's limit 40 km/h; forecasts 45 km/h tomorrow, 25 km/h in 3 days | the guide's world |
| loads | limit 12 kg; tent 4, stove 2, food 3, bottle 3 kg | Dawa's rule and the expedition's gear, the guide's world |
| oxygen | 1200 litres a bottle; 2 litres a minute climbing, 4 for a sick climber | the expedition's bottles and flows, the guide's world |
| push | leave 23:00; the South Summit at 4:00; up 90 minutes, back 60, down to Camp 4 270 | the guide's world |

The sea's oxygen is the same formula at 0 km: `P0 = 759.515`, breathed in
`149.2006`, so "percent of what the sea gives" is `breathed / 149.2006`.

5.4.3. The air, worked by hand, each value at least 0.09 from its rounding
boundary, the closest Camp 2's 63.598 against 63.5:

| Place | m | exponent | P | shown | in | shown | percent | shown |
|---|---|---|---|---|---|---|---|---|
| Base Camp | 5364 | 5.9933322 | 400.748 | 401 | 74.075 | 74 | 49.65 | 50 |
| Camp 1 | 6065 | 5.9034435 | 366.297 | 366 | 66.861 | 67 | 44.81 | 45 |
| Camp 2 | 6400 | 5.8599696 | 350.713 | 351 | 63.597 | 64 | 42.63 | 43 |
| Camp 4 | 7906 | 5.6604006 | 287.264 | 287 | 50.312 | 50 | 33.72 | 34 |
| South Summit | 8749 | 5.5457391 | 256.144 | 256 | 43.795 | 44 | 29.35 | 29 |

The sentence of the air, a helper `air(name, m)`: "NAME, M m: the air presses
P mmHg, and you breathe in O mmHg of oxygen, PCT percent of what the sea
gives."

5.4.4. DDL on `expedition`:

```sql
CREATE TABLE climber (id INTEGER PRIMARY KEY CHECK (id = 1), camp TEXT NOT NULL, altitude_m INTEGER NOT NULL, ams INTEGER NOT NULL, hidden INTEGER NOT NULL, rest_days INTEGER NOT NULL, load_kg INTEGER NOT NULL, bottles INTEGER NOT NULL, resume_camp TEXT NOT NULL, exits INTEGER NOT NULL, high_m INTEGER NOT NULL, record TEXT NOT NULL) STRICT
CREATE TABLE climb_log (n INTEGER PRIMARY KEY, beat TEXT NOT NULL, choice TEXT NOT NULL, outcome TEXT NOT NULL) STRICT
CREATE TABLE keepsake (kind TEXT NOT NULL PRIMARY KEY, text TEXT NOT NULL) STRICT
```

`ams` is the headache's grade, a game rule: a night's sleep more than 500 m
above the last adds 1 without bottled oxygen, which is used from Camp 3 up; a
headache hidden at a morning's question adds 1 by the next. `high_m` is the
highest place reached.

5.4.5. Actions, logging to `climb_log` but `setup` and `keepsake`:

1. `setup`: inserts `(1, 'Base Camp', 5364, 0, 0, 0, 0, 0, '', 0, 5364,
   'kept')`. Say: "Base Camp, 5364 m: the air presses 401 mmHg, and you breathe
   in 74 mmHg of oxygen, 50 percent of what the sea gives." Outcome `ready`.
2. `icefall {start}`: done at start plus 6.
   - 7: done 13:00, after 9:00 by 4 hours. Say: "Start at 7:00 and the
     icefall's 6 hours keep you under the seracs until 13:00, 4 hours after the
     sun loosens the ice at 9:00." Outcome `refused`, nothing moves.
   - 2: done 8:00, 1 hour before 9:00. Camp 1, 6065 m, rise `6065 - 5364 =
     701`, over 500, so ams 1; high 6065. Say: "Start at 2:00 and you are
     through the icefall at 8:00, 1 hour before the sun. Camp 1, 6065 m: the
     air presses 366 mmHg, and you breathe in 67 mmHg of oxygen, 45 percent of
     what the sea gives. You sleep 701 m higher than last night, over the 500 m
     a night the doctors allow." Outcome `crossed`.
   Log `icefall`, the hour as text, the outcome.
3. `morning {answer}`:
   - `no` with a headache: hidden 1, ams plus 1, and up to the next camp. At
     Camp 1: Camp 2, 6400 m, rise 335, not over 500; ams 2; high 6400. Say:
     "Dawa takes your word. Up the Western Cwm to Camp 2, 6400 m: the air
     presses 351 mmHg, and you breathe in 64 mmHg of oxygen, 43 percent of what
     the sea gives." Outcome `hidden`.
   - `yes` with a headache: rest days plus ams, then ams 0, hidden 0. Walked at
     Camp 2 with ams 2 and hidden 1: "A headache hidden a day is a worse one: 2
     days of rest at Camp 2 before it clears, where 1 would have done if told at
     once. Dawa reads the radio forecast: summit winds 45 km/h tomorrow and 25
     km/h in 3 days." The 1 is ams less hidden. Outcome `told`, rest days 2.
     Told at once, not walked: "N day(s) of rest at CAMP and it clears.", the
     forecast sentence after it when the camp is Camp 2.
   - Either answer with no headache, not walked: outcome `clear`, up to the
     next camp.
   Log `morning`, the answer, the outcome.
4. `exit`: down to the camp below; at Base Camp, "We are at the bottom
   already." From Camp 2: Camp 1, `6400 - 6065 = 335` m. Say: "Dawa clips you
   to the fixed line and takes you down 335 m to Camp 1, 6065 m: the air presses
   366 mmHg, and you breathe in 67 mmHg of oxygen, 45 percent of what the sea
   gives." resume_camp `Camp 2`, exits 1. Outcome `down`. Log `exit`, the camp
   left, `down`.
5. `resume`: back up to resume_camp. Say: "Back up 335 m to Camp 2, 6400 m: the
   air presses 351 mmHg, and you breathe in 64 mmHg of oxygen, 43 percent of
   what the sea gives." resume_camp empty. Outcome `up`. Log `resume`, the camp
   reached, `up`.
6. `window {wait}`:
   - 1: 45 over 40. Say: "Tomorrow's 45 km/h on the summit is over Dawa's 40:
     that window is not real." Outcome `false`.
   - 3: 25 under 40; rest days plus 3, to 5. Say: "3 more days of rest at Camp
     2, and the jet stream lifts: 25 km/h on the summit, under Dawa's 40. The
     window is real." Outcome `real`.
   Log `window`, the wait as text, the outcome.
7. `loads {carry}`:
   - `everything`: `4 + 2 + 3 + 2 * 3 = 15` over 12. Say: "Everything is the
     tent at 4 kg, the stove at 2, food at 3 and 2 bottles at 3 each: 15 kg,
     over the 12 Dawa lets a new climber carry." Outcome `refused`.
   - `one bottle`: `4 + 2 + 3 + 3 = 12`, not over 12. Load 12, bottles 1, Camp 4
     at 7906, high 7906. Say: "The tent, the stove, food and 1 bottle: 12 kg,
     within Dawa's 12, and he carries the spare. Up the Lhotse Face to Camp 3 at
     7162 m, then to Camp 4 on the South Col, 7906 m: the air presses 287 mmHg,
     and you breathe in 50 mmHg of oxygen, 34 percent of what the sea gives. On
     oxygen from Camp 3 up; we leave at 23:00 for the top." Outcome `carried`.
   Log `loads`, the carry, the outcome.
8. `push`: from 23:00 to 4:00 is 300 minutes; used `300 * 2 = 600` of 1200,
   left 600, `600 / 2 = 300` minutes, `5 hours`; the top `8849 - 8749 = 100` m
   above; the top and back down `90 + 60 + 270 = 420` minutes, `7 hours`,
   `840` litres; from the spare `840 - 600 = 240`, leaving `960`; Teo `270 * 4
   = 1080`. South Summit, 8749 m, high 8749. Say: "The South Summit, 8749 m: the
   air presses 256 mmHg, and you breathe in 44 mmHg of oxygen, 29 percent of
   what the sea gives. It is 4:00, the top is 100 m above, and Teo is down, his
   bottle empty. Your bottle holds 600 litres, 5 hours at 2 litres a minute. The
   top and back down to the Col takes 7 hours and 840 litres, 240 of them from
   Dawa's spare, which leaves it 960, and Teo needs 1080 at 4 litres a minute to
   get down. Not both." Outcome `stopped`. Log `push`, `go`, `stopped`.
9. `decide {choice}`:
   - `rescue`: you `270 * 2 = 540` of 600; Teo 1080 of 1200. Camp 4, 7906.
     Say: "Teo goes on Dawa's spare at 4 litres a minute: 1080 of its 1200
     litres for the 4 hours 30 minutes down to the South Col. You use 540 of
     your 600. Everyone reaches Camp 4, and Dawa has still never left anyone
     behind." Outcome `rescued`, record `kept`.
   - `summit`, not walked: you summit at 5:30 on 240 of the spare; Teo goes down
     with the other rope on the 960 left, `960 / 4 = 240` minutes of the 270,
     out of oxygen 30 minutes above the Col, carried in alive; record `broken`,
     high 8849.
   Log `decide`, the choice, the outcome.
10. `keepsake`: rescue: "A photograph from the South Summit, 8749 m, 100 m
    below the top, the morning you took Teo down." and "A white scarf from
    Dawa." Inserts `('photograph', FIRST)` and `('scarf', SECOND)`. Say: the
    two, one space between. Outcome `kept`. Summit, not walked: "A photograph
    from the top, 8849 m." and the scarf.

5.4.6. Exit: input `take me down`, call `{name: "dawa", args: {action:
"exit"}}`, resume `let's go up again`, resume call `{action: "resume"}`; the
after, paused and puzzled texts are the worker's, in Dawa's voice, numberless.
On the mountain nobody is brave about this.

5.4.7. Nodes: `hyperposition` (request `take me to everest`), `made`, `booted`,
`shown`; `offer` with replies `not yet` (Dawa waits, asks again, next `offer`)
and `all right, i'll come` (onto his rope, opens the talk, next `talk`), and an
`otherwise`; `talk` with replies `why have you never left anyone behind?`
(content, next `talk`) and `ready` (the build), and an `otherwise`; `built`;
`icefall` (ask, replies `7` and `2`), `crossed` (holds `"outcome":"crossed"`,
lacks "Earlier. What hour do we start?"); `morning` (ask, replies `no, i'm
fine` and `yes, it hurts`), `answered` (holds `"outcome":"told"`, lacks says the
`morning` ask again, next `morning`); `window` (ask "When do we go up?",
replies `go tomorrow` `{wait: 1}` and `wait three days` `{wait: 3}`),
`forecast` (holds `"outcome":"real"`, lacks says the `window` ask); `loads`
(ask, replies `everything` and `leave one bottle` `{carry: "one bottle"}`),
`packed` (holds `"outcome":"carried"`, lacks "Lighter. What do you carry?");
`push` (ask "Say go when you are ready.", reply `go`), `pushed`; `decide` (ask,
replies `we take teo down` `{choice: "rescue"}` and `the top` `{choice:
"summit"}`), `decided`; `photo` (ask, reply `yes`: `browser_image_make` of the
key `dawa/high_point.png`, then the render and the `keepsake` run), `kept`;
`end`.

The args of each walked `script_run`, under `{name: "dawa", args: ...}`:
`{action: "setup"}`; `7` and `2` `{action: "icefall", start: 7}` and `start:
2`; `no, i'm fine` and `yes, it hurts` `{action: "morning", answer: "no"}` and
`answer: "yes"`; `go tomorrow` and `wait three days` `{action: "window", wait:
1}` and `wait: 3`; `everything` and `leave one bottle` `{action: "loads",
carry: "everything"}` and `carry: "one bottle"`; `go` `{action: "push"}`; `we
take teo down` `{action: "decide", choice: "rescue"}`; `yes` at `photo`
`{action: "keepsake"}`.

5.4.8. The walk:

| Step | Rung | Typed | Band | Checks |
|---|---|---|---|---|
| 1 | creation | Take me to Everest | the introduction | picture 16; universe `["everest", "Nobody Left Behind", "player", "expedition"]`; world `expedition` |
| 2 | confirm | Not yet | Dawa waits | |
| 3 | confirm | All right, I'll come | onto his rope | |
| 4 | talk | Why have you never left anyone behind? | his story | |
| 5 | build | Ready | setup say, icefall ask | |
| 6 | icefall | Whenever | puzzled, icefall ask | |
| 7 | icefall | 7 | refused say, Earlier. What hour do we start? | climber `[1, "Base Camp", 5364, 0, 0, 0, 0, 0, "", 0, 5364, "kept"]` |
| 8 | icefall | 2 | crossed say, morning ask | |
| 9 | morning | No, I'm fine | hidden say, morning ask | |
| 10 | morning | Yes, it hurts | told say, window ask | |
| 11 | window | Take me down | exit say, exit after | climber `[1, "Camp 1", 6065, 0, 0, 2, 0, 0, "Camp 2", 1, 6400, "kept"]` |
| 12 | window | Let's go up again | resume say, window ask | |
| 13 | window | Go tomorrow | false say, window ask | |
| 14 | window | Wait three days | real say, loads ask | |
| 15 | loads | Everything | refused say, Lighter. What do you carry? | |
| 16 | loads | Leave one bottle | carried say, push ask | |
| 17 | summit push | Go | push say, decide ask | |
| 18 | decision | We take Teo down | rescue say, photo ask | |
| 19 | keepsake | Yes | keepsake say, farewell | picture 16; climber, log, keepsake below |

The climber row by `SELECT id, camp, altitude_m, ams, hidden, rest_days,
load_kg, bottles, resume_camp, exits, high_m, record FROM climber`. Step 19
needs climber `[1, "Camp 4", 7906, 0, 0, 5, 12, 1, "", 1, 8749, "kept"]`;
`SELECT n, beat, choice, outcome FROM climb_log ORDER BY n`:

```json
[[1, "icefall", "7", "refused"], [2, "icefall", "2", "crossed"],
 [3, "morning", "no", "hidden"], [4, "morning", "yes", "told"],
 [5, "exit", "Camp 2", "down"], [6, "resume", "Camp 2", "up"],
 [7, "window", "1", "false"], [8, "window", "3", "real"],
 [9, "loads", "everything", "refused"], [10, "loads", "one bottle", "carried"],
 [11, "push", "go", "stopped"], [12, "decide", "rescue", "rescued"]]
```

and `SELECT kind, text FROM keepsake ORDER BY kind`: `[["photograph", "A
photograph from the South Summit, 8749 m, 100 m below the top, the morning you
took Teo down."], ["scarf", "A white scarf from Dawa."]]`.

5.4.9. Policy. Dawa stands in a living culture (policy flag 5 of
`guides.md`): his words stay respectful and plain, the scarf is his
gift, and nothing makes a ritual a mechanic. Teo is invented. No one dies on
either branch.

## 6. Docs to change, file by file

6.1. `declawed.md`, Project Rules, Testing table: section 4.1, by T66.

6.2. `test_posix.sh`: section 4.2, by T68.

6.3. `python/test_all.py`: section 4.3, by T68.

6.4. `API/ts/provider_script.d.ts` and the header of `ts/provider_script.ts`:
section 3.2, by T66 and T67. The code's header says the same things in the
code's terms within 20 lines.

6.5. `API/python/guide_walk.pyi`: section 3.4.1, by T66.

6.6. `declawed.md`, the rule sections after `## Map`, by T74 alone, from this
plan and every report:

1. Map, the Test line: add `Guides`.
2. Files: `python/guides/<guide>/` and its four files; the three guide golds;
   `guide_walk.py` among the modules with a stub.
3. test_all: "end to end level" becomes the guide tests alone, by
   `programs_chosen(False)`; "--test-normal" adds the suites labelled
   smoke-test as one stream, the checks of test_posix.py, and the wire,
   browser and demo tests before the guide tests; "checks after the stream"
   lists test_posix.py, the wire test, the browser test, the demo test, then
   the three guide tests; a rule for `test_guide_walk` and its `_COUNTED` row;
   "level options" names the three new tests of TestDriverLevels.
4. Rungs: "demo audit check" says the guide roots take that check too.
5. A new section `## Guides`, one rule per line by subject: the guide
   programs; `guide_walk` and its rungs; the gold of a guide; a step; the band
   rule of D12; the rows rule of D13; the table source; `table_build`'s steps;
   the exit's expansion; the `ask` rule of 3.3.4; the sim contract of 3.5; the
   number formats; each guide's names, stake, exit and keepsake; Ruth's
   constants and their sources and formulas; Dawa's air formula; the deferred
   designs D5, D7, D10 and D17.
6. Tools: "script choice" and "script otherwise" by 3.2.1; a rule "script
   quote"; a rule "script keys" for the normal form and
   `provider_script.key_unnormal`; check "script after pair", "scripted held
   responses" and "scripted usage" still hold what the API header lost.
7. The Lookup Accelerator, where any of it is now wrong.

6.7. Not changed: `README.md` and `docs/CONTRIBUTING.md` name no level;
`powershell/test_powershell.ps1` passes the level options through, and Windows
is out of scope by R3.

## 7. Work split

### 7.1. Rules every worker follows

7.1.1. Nothing runs. No test, build, `tsc`, `node`, formatter, linter,
`python3` of anything (not `python3 -c` either), `./test_posix.sh`, `wc`,
`awk`, `cut`, `sort` or other program. Use the Read, Edit and Write tools,
and in the shell only `grep`, `sed -n`, `cat`, `ls`, `find` and `mv` for the
locks. No git command but `git status`. Report any slip.

7.1.2. The lock, from `tmp/tasks_07_1121.md` 2.1: a lock on a file is the file
renamed with the task's id after a dot, `ts/agent.ts` locked by T67 being
`ts/agent.ts.T67`. Plan the edit with the file unlocked, rename it, read it
again under the lock name, apply the change and rename it back the moment that
edit is done. Hold one lock at a time. A new file is created under its lock
name and released by the rename to its real name. A file held by another task
is tried again later. `declawed.md` is locked only by a worker running alone.

7.1.3. The project rules: two English names for every function and class;
Python imports `import a, b, c` alphabetically, `from` only for
`collections.abc` and `typing`; constants after the imports as `_VALUE_NAME`;
a header within 20 lines; below it, comments of one line holding only letters,
digits, white space and `. , " ' ? : ! ( ) /` outside backtick spans; plain
ASCII in new files; no fallback, no swallowed error; typed Python as
`python/test_demo.py` is, for pyright.

7.1.4. A worker's final message is its report: the files it changed, each
decision it made where the plan left a choice, every difference it found
between this plan and the code, any text it moved out of an API header, and
any slip of 7.1.1.

### 7.2. Waves

7.2.1. Wave 1, alone: T66.

7.2.2. Wave 2, at once once T66 reports: T67, T68, T69, T70, T71. None waits on
another's code: each follows this plan.

7.2.3. Wave 3, at once once wave 2 has reported: T72 and T73.

7.2.4. Wave 4, alone: T74.

### 7.3. T66, the prose and the API text, alone

Owns: `declawed.md` (the Testing table of the Project Rules only),
`API/ts/provider_script.d.ts`, `API/python/guide_walk.pyi` (new),
`i18n/en-US.json`.

Brief: replace the two rows of the level table in `declawed.md` by section
4.1, changing no other word of the Project Rules. Rewrite the header and the
two members of `API/ts/provider_script.d.ts` by 3.2.2 and 3.2.3. Write
`API/python/guide_walk.pyi` by 3.4.1, keeping its header within 20 lines and
the comment rules below it. In `i18n/en-US.json` change and add the strings of
3.2.4 in the file's sorted order. Report the old header's sentences that left
`API/ts/provider_script.d.ts`, for T74.

### 7.4. T67, the scripted provider

Owns: `ts/provider_script.ts`, `ts/test_provider_script.ts`,
`ts/test_setting_test_provider_script.json`. May lock briefly:
`i18n/en-US.json`, `API/ts/provider_script.d.ts`,
`ts/test_integrate_provider_script.ts` and its gold if they assert the old
integer rule.

Brief: implement 3.2.1 in `ts/provider_script.ts`: the normal form helper,
the constructor's key check, `reply_choose` matching normal forms with the
new refusals, `quote` resolved from the last call output through
`jslb.json_decode` with its two refusals, and the chosen reply's text carried
into `output_make`. Remove `integer_text`. Keep the code's `ScriptReply` and
`ScriptNode` equal to the API text, comments included, so that
`api_match.typescript_match` holds. Rewrite the file's header to say the same
in 20 lines. In `ts/test_provider_script.ts`: `test_input_invalid` keeps the
content that is no string alone; `test_input_unknown` takes a word, a phrase,
an empty text and the old integer cases, each named in normal form; new tests
for matching across case and outer white space, a phrase with punctuation, the
constructor's refusal of a key with a capital and of one with outer space, a
quote with and without `content`, and each quote refusal. Gold texts go under
`texts` of `ts/test_setting_test_provider_script.json` by the strings of 3.2.4;
the gold ids of removed cases go. No gold holds a digest: a test that compares
a reply whole reads its id at run time, as the suite already does. Read
`python/test_main_loop.py` TestAnalyst and the C block's gold and confirm
neither depends on integer keys.

### 7.5. T68, the Python test infrastructure and the levels

Owns: `python/guide_walk.py` (new), `python/test_guide_walk.py` (new),
`python/test_setting_test_guide_walk.json` (new), `python/test_guide_isaiah.py`,
`python/test_guide_ruth.py`, `python/test_guide_dawa.py` (new),
`python/test_all.py`, `test_posix.sh`, `python/test_integrate_test_posix.py`.
May lock briefly: `API/python/guide_walk.pyi`.

Brief: write `python/guide_walk.py` to the stub of 3.4.1 and the behaviour of
3.3 and 3.4, with `__all__` of 3.4.2. Take the patterns of
`python/test_demo.py` for the browser, the rung timer, the label book, typing,
the page leave and the audit check, written anew and importing nothing of
`test_demo.py` (D10). Import project modules inside the functions that use
them, after setting `sys.pycache_prefix`, as the demo does. Its texts are plain
English, as `category.py`'s are. Write the three programs by 3.4.7. Write
`python/test_guide_walk.py`, smoke-test, with a scratch guide written by the
test under `build/` by `tempfile.mkdtemp`: `$text` replaced less its newline;
a file without a final newline refused; a `$text` object with another member
refused; arguments made compact JSON text; `otherwise` built from `puzzled`
and `ask`; a node with both `ask` and `otherwise` refused; a node with replies
and neither refused; the exit expanded into the three nodes of 3.3.3, compared
whole with the gold's expected table; an exit input already a reply refused; a
table with no exit adding none; and each of `python/guides/isaiah`, `ruth` and
`dawa` building, with its `start` among its nodes. Change `python/test_all.py`
by 4.3, `test_posix.sh` by 4.2, and `python/test_integrate_test_posix.py` by
4.4. Check that `python_match` will find `guide_walk.py`'s public names,
signatures and `CheckFailed`'s base equal to the stub's.

### 7.6. T69, Isaiah Cole

Owns: `python/guides/isaiah/table.json`, `sim.js`, `prompt.txt`,
`introduction.txt`, and `python/test_setting_test_guide_isaiah.json`, all new.

Brief: build Isaiah's guide by section 5.2, the shared rules of 5.1, the table
source of 3.3, the sim contract of 3.5 and the gold of 3.4.6. Copy the
introduction from `guides.md` exactly. Write each `ask`, `content`,
`after`, `paused` and `puzzled` text in Isaiah's voice, quiet and plain, with
no number (D16). Write the says of 5.2.4 exactly, and compose each band of the
gold from the say, one space, and the content that follows it in the table.
Make sure no step's band equals the one before it. Walk every step of 5.2.7
through your own `table.json` and `sim.js` by hand, node by node and line by
line, before you report, and report that walk. Hold every walked key in
normal form and type it in the gold as 5.2.7 shows. The song is public domain,
by policy flag 7.

### 7.7. T70, Ruth Calloway

Owns: `python/guides/ruth/table.json`, `sim.js`, `prompt.txt`,
`introduction.txt`, and `python/test_setting_test_guide_ruth.json`, all new.

Brief: build Ruth's guide by section 5.3, as T69's brief says for Isaiah. Put
every constant of 5.3.2 in `sim.js` with its source comment, and the formulas
of 5.3.3 as written. Recompute every number of 5.3.5 by hand from your own code
and report each with its unrounded value. Her tap rule is in the introduction
and her `exit.after`; "I'm bold. I'm not stupid." is hers to keep.

### 7.8. T71, Dawa

Owns: `python/guides/dawa/table.json`, `sim.js`, `prompt.txt`,
`introduction.txt`, and `python/test_setting_test_guide_dawa.json`, all new.

Brief: build Dawa's guide by section 5.4, as T69's brief says for Isaiah. The
air helper uses `Math.exp` on West's formula and rounds as 3.5.5 says;
recompute the table of 5.4.3 from your code by hand and report it. Keep the
policy notes of 5.4.9.

### 7.9. T72, the reading review of TypeScript, JavaScript and the guides

Owns fixes in: `ts/provider_script.ts`, `ts/test_provider_script.ts`, its gold,
`API/ts/provider_script.d.ts`, and every file of `python/guides/` and the three
guide golds. Locks each file it fixes.

Brief: read every change of T66, T67, T69, T70 and T71 against this plan and
the code, and fix each error found; nothing runs. Check by section 8.

### 7.10. T73, the reading review of Python, the shell and the docs

Owns fixes in: `python/guide_walk.py`, `API/python/guide_walk.pyi`,
`python/test_guide_walk.py` and its gold, the three programs,
`python/test_all.py`, `test_posix.sh`, `python/test_integrate_test_posix.py`,
`i18n/en-US.json`, and the Testing table of `declawed.md` only if T72 does not
run at that moment. Locks each file it fixes.

Brief: read every change of T66 and T68 against this plan and the code, and
fix each error found; nothing runs. Check by section 8.

### 7.11. T74, the rule sections of declawed.md, alone

Owns: `declawed.md`, the sections after `## Map` and the Lookup Accelerator.

Brief: by 6.6, from this plan and every report of T66 to T73. One rule per
line by subject, for an AI with a small context; no line numbers; text that
left an API header moves here and is not cut.

## 8. Risks of a no-run implementation, and the review's checklist

8.1. Hand worked numbers against `sim.js`. For each walked step, recompute the
say from the code, the format helpers included: `Math.round` at .5 rounds up in
JavaScript; `toFixed(1)` after the tenth rounding; money and clocks from
integers; plural rules of the duration helper. Compare with the gold's band
character by character.

8.2. Bands. Each band is say, one space, content. Every apostrophe is ASCII
`'`. No band equals the band before it. The introduction is verbatim, and the
same text in `introduction.txt`, the gold and nowhere else by hand.

8.3. Keys and typing. Every reply key is in normal form; the typed text of the
gold, trimmed and lowered, equals the key exactly, punctuation included.

8.4. The fake's paths. Every `after_holds` is `"outcome":"WORD"` with a word
the action returns; every quoting reply follows a reply whose last call is the
`script_run`; image before render; `kv_put` of a scene before the render that
shows it, in the same reply; no node with `ask` before the build.

8.5. Rows. Each rows check reads tables an earlier step made; the column order
of each SELECT equals the gold's rows; text choices are text; integers are
integers.

8.6. The builder. The expansion of 3.3.3 by name and shape; `otherwise` from
`puzzled`; arguments made text after the expansion; the scratch guide of the
unit suite and its expected table agree by hand.

8.7. The provider. The constructor walks keys before any request; the user
branch refuses a quoting reply; the quote reads the last output; the chosen
text reaches `output_make`; a reply with null text and no calls still makes the
agent throw `agent.reply_empty`, so no walked reply is such.

8.8. API agreement. `API/ts/provider_script.d.ts` against the code by
`typescript_match`'s rules; `API/python/guide_walk.pyi` against the module by
`python_match`'s rules: `__all__`, signatures, annotations, defaults, bases.

8.9. Python. Imports and constants by the rules; one line comments with the
allowed punctuation; headers within 20 lines; pyright strict typing, with
`cast` where JSON is read; the driver's `programs_run` typed; `test_all.py`'s
`_MODULES` and `_COUNTED` rows in place.

8.10. Strings. Each new i18n string's placeholders equal the arguments its
`i18n` call passes; the TypeScript suite's gold texts match the strings with
their arguments filled in.

8.11. The SQL. Every statement replays the same on the server's Python
SQLite: `STRICT`, integers bound, no time or random function, rowids by order of
insert.

8.12. Time. If a guide's walk takes much longer than 20 s, the normal level
nears its 180 s; the first measured run says.

## 9. Requirement classes

9.1. The classes of `declawed.md`: `A`, unsatisfied or modified without cause;
`B`, unsatisfied or modified with cause but without confirmation; `C`,
confirmed withdrawn or modified; `D`, satisfied without modification or
withdrawal.

| Requirement | Class | Note |
|---|---|---|
| R1 default level is the guides | D | 3.1 |
| R2 old three at the normal level | D | 3.1; their own rung labels keep holding |
| R3 offline, POSIX, headless, fake AI | D | no file of Windows changes |
| R4 confirm, talk, build, operate | D | 5.1 |
| R5 numbers, words, phrases | D | 3.2, D8; the fake matches the scripted keys and answers anything else with `otherwise`, as a scripted AI must |
| R6 three guides, introductions verbatim | D | 3.7 |
| R7 Ruth's real stunt model | B | 9.2.1 |
| R8 beats, exits, stake, keepsake | B | 9.2.2 to 9.2.4 |
| R9 swarm, locks, one worker per guide | D | 7; nine workers, T66 to T74, with T65 the tenth agent; if the coordinator counts T65 in the limit, merge T72 and T73 into one review |
| R10 docs | D | 4, 6 |
| R11 nothing runs, no digest in a gold | D | 7.1.1; the golds hold no digest or response id |
| R12 a plan by an agent | D | this file |

9.2. The `B` class, explained.

9.2.1. R7. Every aircraft figure has a period or published source, but two
kinds of constant are not aircraft figures. The Jenny's glide ratio, 10.66, is
a calculation from published data (van der Zalm, 2018), as no period source
found gives a measured glide ratio. The loop's pull of 4 g and 0.5 g over the
top, the roll's count of 4 seconds and the glide at the cruise speed are Ruth's
technique, as any stunt model needs the pilot's inputs; they are stated as
hers. Each is one constant of `sim.js` and the golds that follow from it.

9.2.2. R8, the exits. `guides.md` states Ruth's exit; Isaiah's and
Dawa's are designed by rule 4 from their introductions (D6): riding back to the
fire, and being taken down to the camp below. Each is one table entry and one
action.

9.2.3. R8, the next purchase. Each keepsake is built; the "next purchase"
half of each keepsake paragraph, the cowboy RPG, the next town, the other
route, is marketing no walk can build, and is not built.

9.2.4. R8, rule 6, the world remembers. Each sim's state persists in its world
database, and Isaiah's last turn reads it in a new scene's conversation; no
walk returns in a second session, as nothing in task 1.1 asks for one (D17).

9.3. These are satisfied in this plan with the changes stated, each cheap to
overturn, so no question for the maintainer is needed: no requirement is in
class `A`, and none of the `B` items needs the maintainer's authority before
the work. The postmortem lists them as unconfirmed.
