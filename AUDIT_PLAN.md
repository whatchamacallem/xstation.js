# Audit Plan

The audit is of the demo of FIRST_DEMO.md, served with `--debug`, on this
machine, and nowhere else. Everything in this plan exists in debug mode only.
Outside it no line is recorded, no database is dumped, 0 is the analyst's
plain answer as today, and the server's own log of its failures stays in
`_verbose.sqlite`. No real AI provider is contacted, by the rule.

The audit is one text document per serve, written by the server: every JSLB
line of the demo, each exchange once, in the order the server learned of it,
laid out over many lines for a person, each line's blobs replaced by their
count, with a note of each task that sleeps on replies and of each text the
console's process logs. Typing 0 adds the databases of both sides to it, as an
AI poking around would see them. In debug mode the audit replaces the log:
every log that would only repeat the audit, or be noisy, is off; the browser
keeps no history of lines and no log, and sends what it records to the
server, which keeps it so that the maintainer and the agent can inspect it.

## 1. The audit as the maintainer will see it

1.1. In WSL, from the checkout: `python3 python/xsjs_serve.py --debug`, then
`http://localhost:5769/` in a browser on Windows, as 1.1 and 1.2 of
FIRST_DEMO.md say. No `--fresh` is needed: each serve copies the server's
modules and the page into the root anew, and the audit needs no new seed.

1.2. The document is `~/.cache/xsjs/root/_audit.txt`, written as the demo
runs: `less` reads it and `tail -f` follows it. Each start of the serve
program begins a new one. Each page load within one serve adds to it under a
heading of its own. With `--debug` the server writes no `_verbose.sqlite`; a
serve without it writes there only what the server logs as it fails, which
`python3 python/xsjs_log.py ~/.cache/xsjs/root` prints.

1.3. Each entry is a heading with the time and a label, then a body:

1. A line entry, labelled with its sender and receiver: the line's JSON text,
   laid out with an indent of two spaces, then, when the line has blobs, a
   marker of how many were left out.
2. A note, labelled with its thread: a task of the thread's queue that sleeps
   until the replies it names arrive, or a text the console's process logs as
   it starts and ends dash. Nothing else is noted, as every other step and
   text is a line the audit already holds.
3. A dump, labelled with its side, at the input 0.

The form, its values left as names:

```text
==== engine started, YYYY-MM-DD HH:MM:SS.mmm, process PID ====

---- HH:MM:SS.mmm, ui to ai
{
  "0": {
    "type": "ai.say",
    "id": ID
  },
  "text": "1"
}

---- HH:MM:SS.mmm, note of ai
  sleeps on ID until ai.model_reply

---- HH:MM:SS.mmm, console to ai
{
  "0": {
    "type": "console.output",
    "blobs": 1
  },
  "1": {
    "size": SIZE
  }
}
[blobs omitted: 1]
```

1.4. Type 0 and Enter. The analyst answers as before. Before the turn starts,
the page has both sides dump their databases into the document: the entries of
the `db.dump` line from the UI thread to the worker and from the worker to the
server, then `databases of the browser` and `databases of the server`. Each
database shows as an AI poking around would see it: its rows and their text,
the current version of each document, its tables and their rows, and the
schema its scripts made. Older document versions and the conversation's turns
are counted and not shown. A value that is not text shows the marker of its
size. When the two sides agree, the two dumps are the same text.

1.5. ctrl 1 shows the end of the audit, fetched from the server at each show,
as many of the newest entries as fit one line; ctrl 1 again hides it and the
page forgets it. ctrl 0 shows the console as before.

1.6. Before 1.1, `python3 python/test_demo.py` proves it: among its rungs it
types 0, checks that both dumps arrived and are equal, checks the document's
entries lane by lane, and leaves the whole document in
`build/test_demo/audit.txt` beside its pictures, whether the run passes or
fails.

## 2. Requirements

The maintainer's words of 2026-11-07, numbered R1 to R16 for reference in this
plan. A requirement of FIRST_DEMO.md is named with that file.

- R1. A plan to audit all communication in the entire demo.
- R2. Leave `--debug` on, because this is `--debug` only.
- R3. See all the JSLB I/O exchanged between the server and the browser as one
  long text document.
- R4. Reformatted for humans across multiple lines.
- R5. Blobs replaced with a simple text marker indicating how many were
  omitted in the log.
- R6. The JSLB exchanged elsewhere in the web app forwarded to the back end as
  log messages: nest the original in a log message wrapper and serialize the
  wrapped original, so that no fragile code cares what message was logged.
- R7. All the JSLB goes to the server one way or the other, if it did not come
  from there.
- R8. The server produces a single long log, formatted for humans, of all the
  JSLB used in testing the demo.
- R9. A dump of the databases on the web side and on the server whenever the
  user types 0 into the AI chat.
- R10. The demo's test types 0, so that all the databases are logged to the
  server.
- R11. The logging is done in text, skips history and old document versions,
  and shows just what an AI would see if it started poking around.
- R12. Written as AUDIT_PLAN.md.

The maintainer's answers to the questions of the first version of this plan,
numbered on.

- R13. Credentials: hide the provider's key and ttyd's token in the audit by
  the existing table, so the file never holds a key or a password.
- R14. Disable the logging when `--debug` is on, because the audit runs and
  any logging would be extremely redundant. Any information that would be lost
  by disabling the logging still moves through the audit instead. The logging
  is expected to give a small subset of the audit's coverage and is off by
  default anyway.
- R15. History in the dumps: show neither older document versions nor turns;
  count them.
- R16. Rip the timeline out; it just crashes the browser. The audit and the log
  go to the server and are forgotten in the browser. Recycle some of the
  design for the formatting and display of the JSLB, but keep no JSLB history
  in the browser: that is what the server is for, so that the maintainer and
  the agent can inspect it.

The maintainer's answer to the question of the second version, and the words
with it, numbered on.

- R17. The audit's own lines stay out of the document.
- R18. Disable the logging that would be a problem, or just noisy, when
  `--debug` is on, because it is redundant.

## 3. What exists, what is missing and what goes

The record today, measured on the maintainer's last serve,
`~/.cache/xsjs/root/_verbose.sqlite` of 2026-11-07 15:06: 666 entries, 297 of
the server, 258 of the worker and 111 of the UI thread. 281 of them are the
server's note of a `verbose.put` batch, the record noting its own carriage. The
reply to the browser's `tools/list` is held whole in 5 entries. The longest
entry is one line of 15452 characters.

| Requirement | In the tree | Missing, or going |
|---|---|---|
| R3 the wire's lines | The server's trace (`python/main_loop.py`) and the worker's wire tap (`ts/worker_ai.ts`, `WireTap`) each note every wire line on one line of `_verbose.sqlite` by the line renderer; the engine role (`python/bootstrap.py`) notes `tap.start`. The tap's notes feed the overlay of ctrl 1 through `overlay.line` | One document; the reply to `tap.start`, which the engine role reads and nothing notes. The trace, the tap and `overlay.line` go, by R14 and R16 |
| R4 for humans | The log tool (`python/xsjs_log.py`) prints the timeline one entry a line, a newline printed as `\n` | Lines laid out over many lines |
| R5 the blob marker | The line renderer writes `<blob "n"=K>` per blob and `<bytes "size"=N>` for a byte array in a payload | One marker of the count |
| R6, R7 the other lanes | In debug mode each queue (`ts/queue.ts`) notes a line at each step it takes, a submit, dispatch, notify, forward, reply, receive, sleep and wake, rendered in the thread, with masks of two credentials, a sized form past `line_max` and a form of its own for a wake. The notes sit in each thread's ring (`ts/verbose.ts`) and go to the server as text in `verbose.put` batches | Each exchange recorded once, as the original line, with no rendering and no history in the browser. The timeline, the ring and `verbose.put` go, by R16 |
| R8 the server's one log | The table `line` of `_verbose.sqlite`, its batches put by `engine_verbose`; the AI's `verbose_tail` tool reads a thread's lines of it through `verbose.tail` | The document; its end for the overlay and the AI. `engine_verbose` and `verbose.tail` go |
| R9, R11 the dumps | Both stores' `kv_list`, `kv_get`, `doc_get`, `doc_head`, `sql_run` and `db_snapshot`; the browser's tools give the AI a value as its text (`ts/tools_browser.ts`) | A view of a whole database; the trigger; the lines that carry the views |
| R10 the demo test | The rungs served to left; the log rung reads `_verbose.sqlite` through `xsjs_log.lines_read`; the overlay rung reads the wire's lines in the overlay; the root goes when the run passes | A rung that types 0; the checks of the document; the document kept |
| R14, R18 the log in debug mode | The server's log texts go to `_verbose.sqlite` in every mode: each line's trace, each failure's message, a browser failure's message, stack and causes, and the console's process starting and ending dash. The browser's ring has no reader but its tests, and its one other caller, a script's log line (`ts/script.ts`), is kept in the script's run result, which the script tools return as an `mcp` reply | In debug mode, the console's two texts as notes of the audit; every other text off, as a line of the audit holds it. The browser's log module goes |

Every line a page thread sends through its queue passes one function of the
queue, `line_send`, and every line it receives passes one other,
`line_arrive`, each of which knows the owner at the far end. The few lines a
thread posts past its queue, the Empty reply to `tap.start` and the `error`
line of a failure, all go to the server. Every wire line passes the server's
main loop or the engine role. These are the capture points of section 4.

The plan does not look for why the timeline crashes the browser, by R16: the
code goes.

## 4. Design, top down

The order of this section is the order of the record: the document, what the
server records itself, what the browser records and sends it, the credentials,
what goes, the end of the audit, the dumps, the two programs around them and
the tests.

### 4.1. The document

4.1.1. One text file per root, `_audit.txt`, beside `_verbose.sqlite`, UTF-8,
written by the server's processes alone: the engine role and, in debug mode,
the console role. Each opens it for appending in debug mode, in place of the
log, and writes each entry with one write under an exclusive lock of the file,
taken for the check of its size and the write, so that two processes never
interleave or pass the limit, and a hard exit loses no entry a process took.
The file is held to `blob_max`: an entry that would carry it past the limit
fails its process loud with `audit.full`, having written nothing, and the cure
is a new serve, as for the log. The main loop scans the root for `.sqlite`
files only, so the file is never taken for a database.

4.1.2. Its order is the order the server learned of each entry: what the
server writes, as it writes it; what it reads, as it reads it; what a page
thread records or notes, as that arrives. A page thread posts each record at
once, before the line it records, on the lanes the line's own effects take, so
this order is the order each sender saw, and a line's record comes before any
line it caused. Nothing is sorted by time, as the browser and the server keep
two clocks.

4.1.3. Its parts: a heading at each start of a process that opens it, `engine
started` or `console started`, with the date, the time and the process id;
then entries, each a heading `---- HH:MM:SS.mmm, LABEL` and a body. Entries are
not numbered, as two processes write them. A heading starts at the left margin
with `====` or `----`, and no line of a body does: a JSON text escapes its
newlines, and every other body is indented.

4.1.4. A line entry is labelled `SENDER to RECEIVER`, named by the queue's
owners, `ui`, `ai`, `server`, `http`, `media`, `console` and `dom`. Its body is
the line's JSON text without its blob bytes, parsed by `jslb.json_decode` and
written by `json.dumps` with an indent of 2 and non-ASCII kept; then
`[blobs omitted: N]` when the line's header counts blobs. One function lays out
every line of every lane and reads no field of any line but the header's count
of blobs. The time is the recorder's: the browser's clock for a page thread's
record, the server's for its own.

4.1.5. A note is labelled `note of THREAD`, `ui`, `ai` or `console`, the last
the console role. Its body is its text, each line indented by two spaces.

4.1.6. A dump is labelled `databases of the browser` or `databases of the
server`. Its body is each database of 4.7.4 in name order, laid out by one
function from its view: its name; its rows, each key with its size and its
text indented below it, or the marker `[bytes omitted: N]` for a value that is
not text, or the text of `substrate.file_lost` for a lost value, which is what
`kv_get` answers; its documents, each current ref with its body laid out as a
line is; its tables, each name with its columns and one JSON array a row; its
schema, one statement a line; then the count of what is not shown. The demo
test's gold pins the exact text.

4.1.7. The server's module `audit` writes the document, reads its end for
4.6, and reads it back whole for the tests. No other code lays out a line, a
note or a view, and the test driver lays out the records a block sends through
the same functions.

```python
# python/audit.pyi: the audit document of a root, `_audit.txt`, debug mode.
from typing import Any, NamedTuple

import jslb

# One entry read back: the start it follows from 1, its time as printed, its
# label, as `ui to ai`, `note of ai` or `databases of the browser`, its body.
class AuditEntry(NamedTuple):
    start: int
    time: str
    label: str
    body: str

# Opens the root's document for appending, held to `blob_max`, and writes the
# start heading of this process's role, `engine` or `console`.
def audit_open(root: str, blob_max: int, role: str) -> None: ...

# Closes the document and returns the module to its state before the open.
def audit_close() -> None: ...

# A line entry of a wire line the server read, `ai to server`, but the
# audit's own lines.
def line_received(line: jslb.Object) -> None: ...

# A line entry of a wire line the server writes, `server to ai`, written
# before the line.
def line_sent(line: jslb.Object) -> None: ...

# A line entry of a page thread's record: its sender, receiver, time and the
# JSON text of the line it records.
def record_put(sender: str, receiver: str, at: int, text: str) -> None: ...

# A note of a thread: its time and text.
def note_put(thread: str, at: int, text: str) -> None: ...

# A dump entry of one side's views, in name order, under its title.
def dump_put(title: str, views: list[dict[str, Any]]) -> None: ...

# The laid out text of a record or a note, as the document holds it, for a
# test driver's block log.
def record_text(sender: str, receiver: str, at: int, text: str) -> str: ...
def note_text(thread: str, at: int, text: str) -> str: ...

# The newest whole entries, at most `count`, whose text fits below `limit`
# bytes, oldest first, as the document holds them.
def tail_read(count: int, limit: int) -> str: ...

# The entries of a root's document in order, the demo test's check.
def entries_read(root: str) -> list[AuditEntry]: ...
```

### 4.2. What the server records itself

4.2.1. Every wire line passes the server, so the server records the wire whole,
both ways, and the browser records nothing of it, by R7. The main loop records
each line it reads before it dispatches it, and each push, reply and `error` it
writes before it writes it, at the points of its trace, which goes. The engine
role records `tap.start` before it writes it, the reply it reads, and its own
`error` line, for every main loop. The test main loops, `echo_loop`,
`tap_loop` and `stall_loop`, record no other line of their own.

4.2.2. The audit's own lines are not recorded as lines, by R17: every type
under `audit.`, as `audit.line` and `audit.note` carry a record or a note and
become the entry they hold, and `audit.tail` and its reply carry the
document's end, which recorded would copy the document into itself and leave
the next tail stopped at that copy.

4.2.3. The server's log in debug mode, by R14 and R18: neither role opens
`_verbose.sqlite`, and each text it logs today is either off or a note:

1. Off, as a line of the audit holds it whole: the traces of each line,
   `main_loop.line_dispatch`, `line_push`, `line_reply`, `line_error` and
   their sized forms, `bootstrap.start_submit` and `bootstrap.line_error`; a
   failure's message, `main_loop.serve_failed` and `bootstrap.run_failed`, as
   the `error` line the process then writes is recorded before it is written,
   its message, stack and causes in it; a browser failure's message, stack and
   causes, `engine_tap.browser_failed` and `engine_tap.browser_cause`, as the
   browser's `error` line is recorded as it is read.
2. A note, `note of console`, as no line holds it: the console role's start
   and end of dash, `verbose.exec_run` and `verbose.exec_exit`, which
   `verbose.log` writes into the audit in debug mode.

Outside debug mode the log is as today: each failure's texts in
`_verbose.sqlite`, the server's last words, which `xsjs_log.py` prints.

4.2.4. The line's JSON text without its blob bytes is a function of `jslb` in
both languages, `line_json`: Python's is today's private `_line_text` made
public, and the server lays out its own lines through it as it lays out a
record's text.

```python
# python/jslb.pyi
# The JSON text `line_encode` writes before the blob bytes, the CR left off.
def line_json(line: Object) -> str: ...
```

### 4.3. What the browser records and sends

4.3.1. The rule for lines, which reads the owner at the far end and never the
line: a queue records each line it sends, but to the server, and each line it
receives from a port that is no queue, `http`, `media`, `console` and `dom`. A
line between the two threads is thus recorded once, by its sender. A line to
the thread itself, as an `mcp` line between the agent and the browser's MCP
server or the worker's `engine.start`, is recorded once, at its send. A line
the worker forwards crosses two lanes and has two entries, as `console.output`
from tty 0 has `console to ai` and `ai to ui`. The lanes this covers are those
of 4.5.1 of FIRST_DEMO.md: ui-dom, ui-media, ui-ai, the worker's own lines,
the `mcp` lines, ai-http, ai-console, and ai-server through the server.

4.3.2. The wrapper of a line is a new line, `audit.line`: a push with one blob
and the payload `sender`, `receiver` and `at`, milliseconds since the epoch.
Its blob is the original line serialized: `jslb.line_json(line)`, UTF-8, the
JSON text `jslb.line_encode` writes before the blob bytes. No blob byte is ever
sent. A byte array in a payload, as a BLOB column of a `sql.run` reply,
becomes the JSON string `[bytes omitted: N]`, as JSON has no bytes and the
encoder would refuse it. As a blob the original is whole up to `blob_max`, the
system's one limit, where a payload would stop at `line_max`, so no sized form
exists.

4.3.3. The notes carry what the timeline held that no line entry does, by R14,
and nothing the audit already holds, by R18: a new line, `audit.note`, a push
with the payload `thread`, `ui` or `ai`, `at` and `text`. The timeline's steps
are sorted thus:

1. A submit, notify, forward, reply and receive are the line entries
   themselves, and are not noted.
2. A run of a line is not noted: each queue runs its lines in the order its
   inputs gave them, which is the order of their entries.
3. A wake is not noted: it follows the last reply its sleep named, which is an
   entry.
4. A sleep is noted, as no entry says which task waits on which replies, the
   first fact a hang needs: `sleeps on IDS until WAKE`, naming the replies'
   ids and the wake's type alone, never a line rendered.

A thread's log text is not noted either: the browser's one, a script's log
line, is in the script's run result, which the script tools return in an
`mcp` reply the audit records.

4.3.4. Routes: the worker posts its records and notes to the server. The UI
thread posts its own to the worker, which forwards them to the server
unchanged: `audit.` is owned by `ai` in the UI thread's owner table and by
`server` in the worker's.

4.3.5. The server's handlers, `engine_audit`, write each record and note
through `audit.record_put` and `audit.note_put`. A record's blob is read whole,
from memory or from the file the main loop's sink finished, as the handlers of
other blobs do.

4.3.6. A record is posted before the line it records, so that the server sees
it before anything the line causes. The worker's records and notes made before
it answers `tap.start` are held and posted in order once the Empty reply is
out, as the engine role reads that reply first and alone: today that is the
record of `settings.set`.

4.3.7. The audit's own lines, every type under `audit.`, are not recorded and
take no note, by 4.2.2. This one prefix, and the masks of 4.4, are the only
places the audit reads a line's type.

4.3.8. Where the audit runs: wherever the timeline's sink is attached today,
in debug mode, so that no thread's record is lost, by R14: each worker's bring
up, `worker_ai.tap_start`, for the engine worker, the test page's worker and
the headless page's worker; and each page's bring up, `page.page_open`, for the
engine page and the test page. A queue a test block builds for itself has no
audit, as it has no sink today, so no line case's gold changes. The headless
page's relay hands each line of the audit to the test driver, as it hands
`verbose.put` today, never to the test's end, and the driver writes it into the
block's log by `audit.record_text` and `audit.note_text`.

4.3.9. Lines outside the queues: a fault line from one page thread to the
other goes past the queues by the error overlay, by design, as the queue may
be what failed; the `error` line the worker sends the server holds the same
cascade and is recorded there. ttyd's own JSON, its token answer and its first
messages, and the frames of tty 0 and tty 1 are not JSLB; the lines those
frames carry are recorded.

4.3.10. In no mode does a page thread keep a line or a log text, by R16:
outside debug mode it records and notes nothing, and in either mode a
script's log lines stay in its run's result alone. The browser's log module,
`verbose`, then has no caller and goes, by 4.5.

```text
declare namespace lines {
  // `audit.line`: one page thread's record of a line, its JSON text blob 1.
  interface AuditLine {
    sender: queue.ThreadName;
    receiver: queue.ThreadName;
    at: number;
  }
  // `audit.note`: one page thread's step or log text.
  interface AuditNote {
    thread: "ui" | "ai";
    at: number;
    text: string;
  }
}

declare namespace jslb {
  // The JSON text `line_encode` writes before the blob bytes, the CR left off,
  // a byte array in a payload as the string `[bytes omitted: N]`.
  function line_json(line: Line): string;
}

declare namespace queue {
  class TaskQueue {
    // In debug mode: records each line sent, but to the server, and each
    // received from a port that is no queue, as an `audit.line` before the
    // line; notes each sleep as an `audit.note`; holds both until
    // `audit_open`.
    audit_attach(): void;
    // Posts the held records and notes in order, and each later one at once.
    audit_open(): void;
  }
}
```

```python
# python/engine_audit.pyi: the handlers of the audit, debug mode only.
import jslb, substrate

# `audit.line`: a page thread's record into the document.
def audit_line(
    line: jslb.Object, *, sender: str, receiver: str, at: int
) -> None: ...

# `audit.note`: a page thread's step or log text into the document.
def audit_note(
    line: jslb.Object, *, thread: str, at: int, text: str
) -> None: ...

# `audit.tail`: reply with the document's newest entries, by 4.6.
def audit_tail(line: jslb.Object, *, count: int) -> jslb.Object: ...

# `db.dump`: the browser's views from blob 1, then the server's own.
def db_dump(line: jslb.Object) -> None: ...

# Registers the four when `debug` is true; `line_max` bounds the tail.
def handlers_register(
    debug: bool, line_max: int, store: substrate.Store
) -> None: ...
```

### 4.4. Credentials

4.4.1. Two fields of two lines hold a credential when one exists: the
`Authorization` header of `http.request`, which holds the provider's key, and
the `token` of a `console.open` reply, which ttyd makes from the username and
password when it is given them, as the Windows start script can with
`--debug`. In the demo neither is secret: the scripted key is the text
`scripted`, and ttyd's token is empty with no credential.

4.4.2. By R13 the copy that `line_json` serializes is masked by the table the
timeline uses today, which stays in the queue when the timeline goes, so the
document never holds a credential, and a masked field shows `<masked>`. The
deferred `provider.set` of 4.13 is written as its header alone.

### 4.5. What goes, by R14, R16 and R18

1. The queue's timeline: its notes of each step with the line rendered, the
   masks' use there, the sized form `queue.line_sized`, `queue.entry_fits`,
   the wake's form and `VerboseBatch`, and the sink's attachment
   `sink_attach`, which `audit_attach` replaces.
2. The browser's log module `verbose` whole: its ring `LineRing`, `log`,
   `history_get` and `sink_set`, with the `verbose_ring` setting's use in the
   browser; `ts/script.ts` keeps a script's log lines in the run's result
   alone.
3. The wire tap `worker_ai.WireTap`, `worker_ai.note_make`, `TapParts.overlay`
   and the line `overlay.line`; the overlay of ctrl 1 shows the end of the
   audit instead, by 4.6.
4. The lines `verbose.put` and `verbose.tail`, the module `engine_verbose`
   with its suites, and the server's `verbose.lines_put`, `verbose.tail_get`,
   `verbose.history_get` and its ring.
5. In debug mode, the server's texts that 4.2.3 turns off; the engine role
   and the main loop log a failure outside debug mode alone.
6. The AI's tool `verbose_tail`, which `audit_tail` replaces, by 4.6.
7. The demo test's log rung, whose table moves to the audit rung.

What stays: `_verbose.sqlite` and `xsjs_log.py`, for a serve without
`--debug`; `jslb.line_render`, which error messages and the vectors use; the
`verbose_ring` setting, as the overlay's count of entries.

### 4.6. The end of the audit, recycled from the tail and the overlay

4.6.1. `audit.tail`: a request of the worker to the server, debug mode, with
`count`, answered by `AuditTailReply` with `text`: the newest whole entries of
the document, at most `count`, whose text fits the reply below `line_max`,
oldest first, as `verbose.tail` fits its lines today. An entry that does not
fit ends the reply, older ones dropped too.

4.6.2. The AI's tool `audit_tail`, with `count`, in place of `verbose_tail`:
its result is the text. Outside debug mode it answers the error result of the
console tools, `tools_browser.debug_off`, as the audit does not exist there,
and the log of a serve without `--debug` holds only what the server logs as it
fails, which ends the session.

4.6.3. The overlay of ctrl 1: at each show the UI thread submits
`audit.tail` with the `verbose_ring` setting as its count, the worker relays it
to the server and the reply back, as it relays `settings.put`, and the overlay
shows the reply's text, scrolled to its end. At each hide it empties, so the
page holds the text only while it is shown. A dump larger than one reply ends
the tail at it.

```text
declare namespace lines {
  // `audit.tail`: the document's newest entries, at most `count`.
  interface AuditTail {
    count: number;
  }
  interface AuditTailReply {
    text: string;
  }
}
```

### 4.7. The dumps

4.7.1. The trigger: the UI thread's handler of the person's text, in debug
mode, when the text is exactly `0`, notifies `db.dump` to the worker before it
submits the turn's `ai.say`. Nothing else triggers a dump. The analyst's table
does not change, and the analyst's answer to 0 follows the dumps.

4.7.2. The worker's handler of `db.dump`, a handler of the browser's store:
builds the view of each database the store holds, in name order, by
`Store.db_view`, and notifies `db.dump` to the server, as the sync's request
names its owner, with the JSON text of that list as blob 1. Both lines are
pushes, and nothing waits for them.

4.7.3. The server's handler of `db.dump`: writes the dump `databases of the
browser` from blob 1, parsed by `jslb.json_decode`, then builds its own views
of `store.db_list()` in name order and writes `databases of the server`. Every
commit the browser made before the input reached the server before the
`db.dump` line, on the same wire in order, so both dumps are of the same
moment, the state before the turn of 0.

4.7.4. The view of one database is what an AI poking around with the browser's
tools would see, the same in both languages:

1. Rows: every row of the store's key-value table that is not a version of a
   document, by key, with its size and its text as the `kv_get` tool reads it,
   the bytes as UTF-8; `binary` when the bytes are not UTF-8 or hold a control
   character other than tab, newline and carriage return; `lost` when its
   cache file is missing, as `kv_get` then answers `substrate.file_lost`. The
   seed's image is `binary` by its control characters alone: its 102 bytes
   are all below 0x80 and decode as UTF-8, NULs among them, which `kv_get`
   would hand an AI as text and no person reads as text.
2. Documents: the current version of each document, by id, its ref and its
   body as `doc_get` returns it, in its encoded form.
3. Tables: every table but the store's own `_kv`, `_head` and `_turn` and
   SQLite's own `sqlite_` tables, by name, with its columns and its rows as
   `sql_run` returns them, in rowid order or, for a table without rowid, in
   primary key order; a BLOB cell as the object `{"bytes": N}`, which no other
   cell can be.
4. Schema: the SQL text of every table, index, view and trigger that is not the
   store's own, by name.
5. Not shown, by R15: the count of older document versions, of turns, and of
   the scenes those turns belong to.

4.7.5. The browser sends its views and the server lays out both, so one
function lays out every dump, and the two dumps of one moment are the same
text exactly when the two stores agree. A view is compared between the
languages as a JSON value, so the languages' number texts never differ.

4.7.6. Size: the blob of the browser's views is held to `blob_max` as every
blob is, and a larger one fails loud, as anything past the system's one limit
does.

4.7.7. The view is a method of the store in both languages, as it reads the
store's own tables and its cache's holding of each file.

```text
declare namespace substrate {
  // A row of a view: its key and size, and its text unless it has none.
  interface ViewRow {
    key: string;
    size: number;
    kind: "text" | "binary" | "lost";
    text?: string;
  }
  // The current version of a document: its ref and its encoded body.
  interface ViewDocument {
    ref: lines.DocRef;
    body: lines.Document;
  }
  // A table of the scripts: its columns and its rows in order.
  interface ViewTable {
    name: string;
    columns: string[];
    rows: unknown[][];
  }
  // A database as the AI's tools show it, its history counted.
  interface DbView {
    db: string;
    rows: ViewRow[];
    documents: ViewDocument[];
    tables: ViewTable[];
    schema: string[];
    versions_hidden: number;
    turns_hidden: number;
    scenes_hidden: number;
  }
  class Store {
    // The view of one database, from its rows, heads, tables and cache.
    db_view(db: string): DbView;
  }
}

declare namespace lines {
  // `db.dump`: no payload. On ui-ai no blob; on the wire blob 1, the JSON
  // text of the browser's views in name order.
  interface DbDump {}
}
```

```python
# python/substrate.pyi
class Store:
    # The JSON value of `substrate.DbView` of API/ts for one database.
    def db_view(self, db: str) -> dict[str, object]: ...
```

### 4.8. The lines, in the form of the Line types table

```text
type lane from->to blobs reply
audit.line ui-ai UI->AI 1 push (debug), then forwarded
audit.line wire AI->SERVER 1 push (debug)
audit.note ui-ai UI->AI 0 push (debug), then forwarded
audit.note wire AI->SERVER 0 push (debug)
audit.tail ui-ai UI->AI 0 AuditTailReply (debug), relayed to SERVER
audit.tail wire AI->SERVER 0 AuditTailReply (debug)
db.dump ui-ai UI->AI 0 push (debug), at the input 0
db.dump wire AI->SERVER 1 push (debug), the browser's views
```

Gone: `verbose.put` on both lanes, `verbose.tail`, `overlay.line`.

### 4.9. The serve program

The serve program removes `_audit.txt` with `_verbose.sqlite` and its `-wal`
and `-shm` files at each start, so each serve begins a new document and the
last serve's stays readable until the next start. A page load within one serve
adds to the same document.

### 4.10. The tests that read the old record

1. The test driver's group B relay takes `audit.line` and `audit.note` where it
   takes `verbose.put` today and writes them into the block's log; the
   headless page's relay hands them to the driver alone.
2. The engine's group C block, `test_integrate_engine`, pins the wire's lines
   today through `overlay.line`. It pins them through `audit.tail` instead: its
   scripted UI submits it after a case, through the worker's relay, and the
   case checks the text holds the gold's fragments, so the block proves the
   audit end to end from the browser on the real server.
3. The wire test's verbose rung becomes an audit rung on the stock root:
   `audit.line` and `audit.note` of its own, then `audit.tail`, whose text
   holds them laid out.
4. The browser test's ring and sink rungs go with the ring. Its read of the
   server's log for a browser failure on a debug root, in `bail_check`, reads
   the audit's `ai to server` entry of the browser's `error` line holding the
   message instead, as 4.2.3 turns that log text off.
5. The queue's integration block, which reads a traced case's timeline back
   through `verbose.put`, reads the case's records and notes through the audit
   instead.
6. The overlay's block, the verbose blocks and suites, and every suite of a
   removed piece change or go with it.

### 4.11. The demo test

4.11.1. Two new rungs, two changed and one gone, each with its gold in
`python.test_demo`:

| Rung | Label | What it proves |
|---|---|---|
| overlay | test-all | ctrl 1 shows the end of the audit, holding the gold's fragments of the last turn; ctrl 1 hides it and the overlay holds no text |
| dump | smoke-test | Typing 0 with no click ends with the analyst's answer to 0 in the band and the box enabled and focused. The document then holds, read by `audit.entries_read` under the rung's timer, the entries of that input in this order: `ui to ai` of `db.dump`, `ai to server` of `db.dump` with `[blobs omitted: 1]`, `databases of the browser`, `databases of the server`, `ui to ai` of `ai.say` holding `"text": "0"`. The two dumps are the same text, each holds the gold's fragments of the seed, among them the seed's image as `[bytes omitted: 102]` and the hyperposition's document, and none holds a row of an older document version |
| audit | smoke-test | The gold's table `audit`, which takes over the log rung's, each row a label, a line type or a note's words, and a fragment of the laid out text, one per lane and direction the demo crosses, each in some entry: `ui to dom` and `dom to ui`, `ui to media` and `media to ui`, `ui to ai` and `ai to ui`, `ai to ai` of `mcp`, `ai to http` and `http to ai`, `ai to console` and `console to ai`, `ai to server` and `server to ai`, `db.restore` with its blob marker, a sleep of `ai` on the provider's reply, the bad input rung's inputs and answer, and the masked token of a `console.open` reply. No entry is of a type under `audit.`, and no note is of a run or a wake. Every line entry's body parses as JSON. One `engine started` heading in a smoke run and two after the reload of a full run |
| log | gone | Its table moves to the audit rung, as `_verbose.sqlite` is not written in debug mode |
| left | smoke-test | As before, and first it copies `_audit.txt` to `build/test_demo/audit.txt`; a failed run copies it too and keeps the root |

4.11.2. The order of the rungs: served, reload, choice 1, choice 3, bad input,
choice 2, console, overlay, dump, audit, left. The dump rung comes late so that
a full run's dump holds the note of choice 2, and the audit rung after it so
that its table holds the lines of 0.

4.11.3. No fragment of the audit table holds an id or a time, as the reload of
a full run makes two page loads.

### 4.12. The debug stories

The stories of 4.8 of FIRST_DEMO.md change in three places. Read the timeline
becomes read the audit: `less ~/.cache/xsjs/root/_audit.txt`, or
`build/test_demo/audit.txt` after a demo test, every line of every lane once,
each task's sleep and the console's start and end, laid out for a person, in
the order
the server learned of it; `tail -f` follows it; typing 0 adds both sides'
databases at that moment. On the page, ctrl 1 shows the end of the audit. From
the AI's side, `audit_tail` reads it in place of `verbose_tail`.

### 4.13. Deferred designs, kept whole

4.13.1. The real provider's line, `provider.set` of FIRST_DEMO.md 4.10.1, not
built. Its key crosses the wire from the server, so the server's audit records
it, by R13 as its header alone, as the masks keep every credential out of the
document.

## 5. Stages, in order

Each stage writes its API text first, then its unit tests, then its code, then
its integration tests, and ends with `./test_posix.sh` passing and nothing
staged or committed. Section 4 holds every API text of every stage, top down,
so that none waits on a stage to be designed. The order is bottom up: the
document first, so that every later stage can be read in it; the server before
the browser; the new record whole before the old one goes; the dumps after the
records; the test last.

### 5.1. The document on the server

The module `audit` with its stub and its unit suite: a line with and without
blobs laid out, a record's text laid out alike, a note, a dump of views, the
start headings of both roles, two opens appending to one file, two processes
writing at once with no entry interleaved, a write that would pass `blob_max`
raising `audit.full` and writing nothing, one write per entry, the tail's fit
and order, and `entries_read` reading back what was written. Python's
`jslb.line_json`, with the vectors' sidecars gaining each message's JSON form
beside its rendered form, which Python's suite checks here and TypeScript's in
5.2. The main loop's records, with its unit suite: a read line, a push, a
reply, a stream's pushes in order, an `error`, and no entry of a type under
`audit.`. The engine role's records, with its unit suite: `tap.start`, its
reply and its own `error` line, and no document outside debug mode. The serve
program's removal, with its unit suite. The main loop's integration suite on a
real pty. Proof: the default run; then the largest document the wire, browser
and demo tests write is measured once, before their roots go, against
`blob_max`.

### 5.2. The browser's records and notes

`audit.line` and `audit.note` in the wire API and the Line types table;
TypeScript's `jslb.line_json` with its
suite on the vectors and a nested byte array; the queue's `audit_attach` and
`audit_open`, with its unit block on a synchronous queue whose local ports
stand for each kind of owner: a send to its own thread, to the other thread, to
a port and to the server; an arrival from a port and from a queue; each record
before its line; a sleep noted by ids and wake type alone, and no run or wake
noted; records and notes held until the open; none of a type under `audit.`;
the masks. `audit_attach` beside
`sink_attach` in `worker_ai.tap_start` and `page.page_open`, the worker's
records posted after the Empty reply, with their suites. `engine_audit`'s
`audit_line` and `audit_note` with their unit and integration suites, a blob
in memory and one in a cache file of the sink; the test main loops that serve
`verbose.put` today serve these too. The group B relay of 4.10. Proof: groups
A, B and C.

### 5.3. The end of the audit

`audit.tail` and `engine_audit.audit_tail`, with their suites. The AI's tool
`audit_tail` in API/mcp/tools.json, with its suite and its refusal outside
debug mode. The worker's relay of the UI's `audit.tail`. The overlay of ctrl 1
showing the tail and emptied at hide, with its block. The C block pinning the
wire's lines through the tail, by 4.10. Proof: groups A, B and C.

### 5.4. The old record goes

Everything of 4.5, with its suites and blocks: the timeline, the browser's
`verbose` module, the wire tap, `overlay.line`, `verbose.put`, `verbose.tail`,
`engine_verbose`, the server's traces and ring, the tool `verbose_tail`. In
debug mode neither role opens `_verbose.sqlite`, the failure texts of 4.2.3
are off, with a test of each that the audit holds the `error` line instead,
and the server's `verbose.log` writes the console role's two texts as notes of
the audit. The wire test's audit rung, the
browser test's changes and the queue's integration block of 4.10. Proof: the
default run with the wire and browser tests; a search of `ts/` and `python/`
finds no name of 4.5 but in this plan's history.

### 5.5. The dumps

`Store.db_view` in both languages. `vectors_make.py` writes `dump.json`: a list
of store operations, a text value, a binary value, a value over
`overflow_bytes`, two versions of one document, a script's table with a BLOB
and a NULL, a trigger, two turns, and the expected view, written by hand in
that module, so that neither store's code makes its own expectation. Each
store's suite applies the operations through the store's public methods and
compares its view with the vector's as a JSON value, and each makes a lost
value through its own restore without the file. `db.dump` in the wire API and
the Line types table; the browser store's handler of `db.dump`, with its block;
`engine_audit.db_dump`, with its suites; the UI thread's trigger, with the
engine page's unit block gaining two cases: 0 in debug mode sends `db.dump`,
then `ai.say`; another number sends `ai.say` alone. The C block gains a case:
its scripted UI notifies `db.dump`, and the tail then holds both dumps. Proof:
groups A, B and C.

### 5.6. The demo test

The rungs of 4.11 and their gold. FIRST_DEMO.md's text of the timeline, the
overlay and the log, in 1.4's row 0, 1.5, 1.6, 4.5 and 4.8, points to this
plan, and its R6 and R7 rows of section 7 name R14 and R16 as the maintainer's
change; the project's rules gain the audit's rules and lose the old record's.
Three default runs measure the budget of three minutes. Proof:
`./test_posix.sh` passes, and `build/test_demo/audit.txt` holds the run's
document.

### 5.7. The full run

`./test_posix.sh --test-all` passes, with the line count reaching every line of
`audit.py`, `engine_audit.py` and the lines this plan adds to the engine role,
the main loop, `verbose.py`, the store, the serve program and
`vectors_make.py`. Formatting last.

### 5.8. The viewing

The agent runs the demo test, then the serve program with `--debug`, types 0
on the page and presses ctrl 1 by DevTools, reads the document, and reports its
path, its size, and an excerpt of each lane, of the notes and of both dumps.
The session's log records what was seen.

## 6. Decisions made, each cheap to overturn

1. The document is a text file in the root, `_audit.txt`, and not a table of
   `_verbose.sqlite`: R3 asks for one long text document, which a person reads
   with no program, and it is held to `blob_max` apart from the log.
2. The document is in the order the server learned of each entry, not sorted
   by time: the browser posts each record at once and before its line, and two
   clocks cannot be merged faithfully.
3. One entry per exchange: by the sending queue, or by the receiving queue
   when the sender is a port, and by the server for the wire, by R7.
4. A record carries the original's JSON text as a blob, so that it is whole up
   to `blob_max`; R6's "nest" is met by the record holding the whole line and
   "serialize" by its blob.
5. JSON is laid out by Python's `json.dumps` with an indent of 2 and non-ASCII
   kept; strings stay escaped, so a stack or a tool's JSON text stays on one
   line of the entry.
6. The markers: `[blobs omitted: N]` after a line, the string `[bytes omitted:
   N]` for a byte array in a payload, and `[bytes omitted: N]` for a value or
   cell of a dump that is not text. Text is UTF-8 with no control character
   but tab, newline and carriage return, measured on the seed's image, which
   is valid UTF-8 and full of NULs.
7. The heading's time is the recorder's clock. Entries are not numbered, as
   the engine role and the console role both write the document; each takes
   an exclusive lock of the file for its check and its write.
8. Of the timeline's steps only a sleep is noted, by its replies' ids and its
   wake's type: a run follows the order of the entries and a wake follows its
   last reply, so noting either would repeat the audit, by R18, while no entry
   says what a task waits on, by R14. No line is rendered in the browser, by
   R16.
9. The audit runs where the timeline's sink runs today, every worker's and
   every page's bring up in debug mode, so that the test pages' records are
   not lost either, by R14; a block's own queues have no audit.
10. The overlay of ctrl 1 and the AI's tool read the end of the audit from the
    server, recycling the tail's fit and the overlay's display, by R16; the
    tool is renamed `audit_tail`, keeps `count` and drops `thread`, and works
    in debug mode only, as the audit does.
11. The `verbose_ring` setting keeps its name as the overlay's count of
    entries, its one remaining use.
12. The trigger of a dump is the text `0` exactly, read in the UI thread's
    handler of the person's text, so a person's 0 dumps with any AI.
13. Both `db.dump` lines are pushes; the demo test waits for the dumps by
    reading the document under its timer.
14. The browser sends its views and the server lays out both dumps, so one
    function lays out every dump.
15. The demo test requires the two dumps equal, an audit of the sync. The
    browser compacts its turns at `turn_compact_turns`, 64 user turns, which
    the demo does not reach; past it the counts of turns would differ.
16. The server's handlers of the audit are a module of their own,
    `engine_audit`, registered in debug mode, as `engine_verbose` registers
    `verbose.put` today.
17. The view is a store method, `db_view`, in both languages, proven equal by
    a vector of `vectors_make.py` written by hand, compared as JSON values.
18. No new program: the document is read with `less` and followed with
    `tail -f`; `audit.entries_read` serves the tests.
19. In debug mode a log text is off when a line of the audit holds what it
    says, as a failure's message and stack are in the `error` line, and a note
    otherwise, which leaves the console role's start and end of dash, by R18.
    Outside debug mode every log text is as today.

## 7. Requirements by class

- `A`: request unsatisfied or modified without cause.
- `B`: request unsatisfied or modified with cause but without confirmation.
- `C`: request confirmed withdrawn or modified.
- `D`: request satisfied without modification or withdrawal.

| Requirement | Class | Where |
|---|---|---|
| R1 audit all communication | D | the whole plan |
| R2 debug mode only | D | the introduction, 4.3.10, 4.7.1 |
| R3 the wire as one document | D | 4.1, 4.2 |
| R4 laid out for humans | D | 4.1.4 to 4.1.6; decision 5 |
| R5 a marker of the count of blobs | D | 4.1.4, 4.3.2; decision 6 |
| R6 the original wrapped and serialized | C | 4.3.2, 4.4: the masks of two credentials read two fields, confirmed by R13 |
| R7 every line reaches the server | D | 4.2, 4.3: every line reaches it as itself or as a record; a fault line's cascade reaches it in the `error` line, 4.3.9 |
| R8 one log of all the JSLB | C | 4.2.2, 4.3.7: the audit's own lines are not in the document, confirmed by R17 |
| R9 the dumps at 0 | D | 4.7; decision 12 |
| R10 the demo test types 0 | D | 4.11 |
| R11 text, no history, the AI's view | D | 4.7.4, confirmed by R15 |
| R12 AUDIT_PLAN.md | D | this file |
| R13 hide the credentials | D | 4.4 |
| R14 no logging in debug mode, nothing lost | D | 4.2.3, 4.3.3, 4.3.8, 4.5; decisions 8 and 9 |
| R15 history counted, not shown | D | 4.7.4 |
| R16 the timeline out, no history in the browser | D | 4.5, 4.6, 4.3.10; decision 10 |
| R17 the audit's own lines left out | D | 4.2.2, 4.3.7 |
| R18 no redundant or noisy log in debug mode | D | 4.2.3, 4.3.3, 4.5; decisions 8 and 19 |

R6 and R7 of FIRST_DEMO.md, to log all the JSLB of the comms and scrutinize
it, were met by the timeline; R14 and R16 change them to the audit, class C,
which stage 5.6 writes into that file.

No requirement is class A or B. Every question of the plan's earlier versions
is answered, R13 to R18, and none is open.
