# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the audit's reader on documents the real audit module writes in scratch
# roots in `build/`, whose suite has passed: a run with no failure read back,
# each line whole though written thin, each lane's bytes fewer as written than
# as sent, two scenes in turn across a reload with no failure, each kind of
# unexpected failure found at its line, and the form of a document refused.
# A chain fails by a chained call resending the prompt or history or naming a
# response the record lacks, a chain's first call holding the prompt twice, the
# lanes writing it twice, and an output item written twice. The audit digest
# of a tiny guide's walk and of every other kind of line is the gold's, and the
# guide check passes that walk and fails each fault put in it. The database
# check replays each kind of commit the server's handlers applied in a forked
# child, puts replaced, dropped or cached among them, and fails a value, a row
# and a refused commit; the text tells each kind of cell. The repeat check
# passes a told walk on a database the real store wrote and fails each of its
# conditions. The program whole runs in a forked child by `runpy`, so that the
# count reaches its last line. The texts are the gold's.

import audit, audit_read, copy, harness, jslb, json, os, runpy, shutil, signal
import sqlite3, substrate, sys, tempfile, traceback, unittest
from typing import Any

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_audit_read"

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The reader's file, which the forked child runs as a program.
_READER_PATH = os.path.join(_ROOT_PATH, "python", "audit_read.py")

# The audit's file in a root.
_AUDIT_NAME = "_audit.txt"

# The largest document of a scratch root, as the settings give it.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The first entry's time, milliseconds since the epoch.
_FIRST_AT = 1_700_000_000_000

# The indent of a line's JSON text in the document.
_JSON_INDENT = 2

# The indent of a digest record's lines after its first.
_RECORD_INDENT = "        "


# A value of this module's gold.
def gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# In the forked child: runs the reader, its output and ending to files, killed.
def child_run(arguments: list[str], output: str, ending: str) -> None:
    try:
        try:
            with open(output, "xb") as file:
                os.dup2(file.fileno(), 1)
                os.dup2(file.fileno(), 2)
            sys.argv = [_READER_PATH, *arguments]
            try:
                runpy.run_path(_READER_PATH, run_name="__main__")
                text = "returned"
            except SystemExit as error:
                text = str(error.code)
        except BaseException:
            text = traceback.format_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        with open(ending, "w", encoding="utf-8") as file:
            file.write(text)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Forked child: the server's handlers record and apply each line, then it dies.
def commits_serve(
    root: str, limits: list[int], rows: list[dict[str, Any]], ending: str
) -> None:
    try:
        try:
            # Imported here, so their import's lines count in their own suites.
            import dispatch, engine_db, engine_doc, engine_kv, engine_sql
            import engine_turn

            store = substrate.Store(root, *limits)
            for name in os.listdir(root):
                if name.endswith(".sqlite"):
                    store.db_open(name.removesuffix(".sqlite"))
            handlers = (engine_kv, engine_doc, engine_db, engine_turn)
            for module in (*handlers, engine_sql):
                module.handlers_register(store)
            for row in rows:
                line = jslb.json_decode(json.dumps(row["line"]))
                if "data" in row:
                    line[1]["d"] = str(row["data"]).encode("utf-8")
                audit.line_received(line)
                dispatch.line_dispatch(line)
            for name in store.db_list():
                store.db_close(name)
            text = "served"
        except BaseException:
            text = traceback.format_exc()
        with open(ending, "w", encoding="utf-8") as file:
            file.write(text)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Gives each test a scratch root and writes a document in it by the real audit.
class AuditCase(unittest.TestCase):
    # Makes the scratch root and opens its document.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.path = os.path.join(self.root, _AUDIT_NAME)
        self.at = _FIRST_AT
        audit.audit_open(self.root, _BLOB_MAX, "engine")
        self.addCleanup(self.document_close)
        self.closed = False

    # Closes the document, once.
    def document_close(self) -> None:
        if not self.closed:
            audit.audit_close()
            self.closed = True

    # Writes the rows of the gold's list as entries, a millisecond apart.
    def rows_write(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.at += 1
            if "note" in row:
                audit.note_put(row["note"], self.at, row["text"])
            elif "start" in row:
                audit.audit_close()
                audit.audit_open(self.root, _BLOB_MAX, row["start"])
            else:
                audit.record_put(
                    row["sender"],
                    row["receiver"],
                    self.at,
                    json.dumps(row["line"]),
                )

    # The entries of the rows named, read back from the document.
    def entries_of(self, *names: str) -> list[audit_read.ReadEntry]:
        for name in names:
            self.rows_write(gold_value(name))
        return audit_read.entries_parse(audit_read.document_read(self.path))

    # Asserts the check of the rows named raises, naming a line of the entry.
    def failed_assert(self, name: str) -> None:
        entries = self.entries_of(name)
        with self.assertRaises(audit_read.AuditFailed) as caught:
            audit_read.failure_check(entries)
        self.assertRegex(str(caught.exception), gold_value("failures")[name])

    # Each lane's bytes as the gold's rows were sent and as the document holds.
    def lanes_measured(
        self, rows: list[dict[str, Any]]
    ) -> list[tuple[str, int, int]]:
        written = audit.entries_read(self.root)
        measured: list[tuple[str, int, int]] = []
        for lane in gold_value("summary_lanes"):
            sent = sum(
                len(
                    json.dumps(
                        row["line"], ensure_ascii=False, indent=_JSON_INDENT
                    ).encode("utf-8")
                )
                for row in rows
                if "line" in row
                and f"{row['sender']} to {row['receiver']}" == lane
            )
            held = sum(
                len(entry.body.encode("utf-8"))
                for entry in written
                if entry.label == lane
            )
            measured.append((lane, sent, held))
        return measured


# A document of a run that went as it should.
class TestRead(AuditCase):
    # The entries in order, with their lines, starts, labels, types and counts.
    def test_entries_read(self) -> None:
        entries = self.entries_of("run")
        rows: list[list[Any]] = gold_value("run_entries")
        found = [
            [
                entry.number,
                entry.start,
                entry.label,
                audit_read.type_of(entry),
                entry.kept,
            ]
            for entry in entries
        ]
        self.assertEqual(found, rows)

    # Each line is read whole, as it was sent, though the document is thin.
    def test_lines_whole(self) -> None:
        entries = self.entries_of("run")
        rows: list[dict[str, Any]] = gold_value("run")
        lines = [entry.line for entry in entries if entry.line is not None]
        self.assertEqual(lines, [row["line"] for row in rows if "line" in row])

    # A blob's mark after the JSON leaves the JSON read.
    def test_blobs_read(self) -> None:
        entries = self.entries_of("blobs")
        self.assertEqual(entries[0].line["size"], 3)

    # Each lane of the conversation writes fewer bytes than it sent.
    def test_lanes_thinner(self) -> None:
        self.entries_of("run")
        for lane, sent, held in self.lanes_measured(gold_value("run")):
            with self.subTest(lane=lane):
                self.assertLess(held, sent)

    # The run has no failure, and every request its reply.
    def test_run_passed(self) -> None:
        entries = self.entries_of("run")
        audit_read.failure_check(entries)
        self.assertEqual(audit_read.requests_open(entries), [])

    # Scenes in turn across a reload write the prompt once and no item twice.
    def test_scenes_passed(self) -> None:
        entries = self.entries_of("scenes")
        rows: list[dict[str, Any]] = gold_value("scenes")
        lines = [entry.line for entry in entries if entry.line is not None]
        self.assertEqual(lines, [row["line"] for row in rows if "line" in row])
        self.assertEqual(audit_read.prompt_recorded(entries), 1)
        audit_read.failure_check(entries)

    # Two dumps of each side pass the check, as a person asked for them.
    def test_dumps_passed(self) -> None:
        views: list[dict[str, Any]] = gold_value("views")
        audit.dump_put("databases of the browser", views)
        audit.dump_put("databases of the server", views)
        audit_read.failure_check(self.entries_of())


# Each unexpected failure, found at its line.
class TestFailures(AuditCase):
    # Each row of the gold's failures raises its text.
    def test_each_failure(self) -> None:
        for name in gold_value("failures"):
            with self.subTest(name=name):
                self.document_close()
                os.remove(self.path)
                audit.audit_open(self.root, _BLOB_MAX, "engine")
                self.closed = False
                self.failed_assert(name)

    # A request with no reply is open, and a later reply closes it.
    def test_request_opened(self) -> None:
        entries = self.entries_of("request")
        self.assertEqual(
            audit_read.requests_open(entries), gold_value("request_open")
        )
        entries = self.entries_of("reply")
        self.assertEqual(audit_read.requests_open(entries), [])

    # A reply in a later start of the engine answers nothing of an earlier.
    def test_start_apart(self) -> None:
        entries = self.entries_of("request", "second_start", "reply")
        self.assertEqual(
            audit_read.requests_open(entries), gold_value("request_open")
        )


# The audit digest, the run told for a person to read.
class TestDigest(AuditCase):
    # The digest of the rows named, its summary last, is the gold's.
    def digest_assert(self, name: str) -> None:
        lines = audit_read.digest_lines(self.entries_of(name))
        self.assertEqual(lines, gold_value(f"{name}_digest"))

    # A walk tells the player, the model, the tools, the bands and commits.
    def test_walk_told(self) -> None:
        self.digest_assert("walk")

    # Every other kind of line is told, a long string named again, restarts.
    def test_lines_told(self) -> None:
        self.digest_assert("told")

    # A dump is shown whole, and a second of the same text names the first.
    def test_dump_told(self) -> None:
        views: list[dict[str, Any]] = gold_value("views")
        audit.dump_put("databases of the browser", views)
        audit.dump_put("databases of the server", views)
        entries = self.entries_of()
        lines = audit_read.digest_lines(entries)
        heads = [
            index for index, line in enumerate(lines) if line.startswith("L")
        ]
        self.assertEqual(len(heads), 2)
        first, second = (lines[index] for index in heads)
        self.assertRegex(first, gold_value("dump_told"))
        self.assertRegex(second, gold_value("dump_told"))
        body = entries[0].body.split("\n")
        shown = lines[heads[0] + 1 : heads[1]]
        self.assertEqual(shown[0], _RECORD_INDENT + body[0])
        self.assertEqual(len(shown), len(body))
        named = f"{_RECORD_INDENT}same as L{entries[0].number}"
        self.assertEqual(lines[heads[1] + 1], named)

    # A document with no entry tells nothing, then a summary of nothing.
    def test_empty_told(self) -> None:
        lines = audit_read.digest_lines(self.entries_of())
        self.assertEqual(lines, gold_value("empty_digest"))


# The guide check of a tiny guide's walk, by its table and gold.
class TestGuide(AuditCase):
    # Checks the entries by the gold's table and walk.
    def guide_check(self, entries: list[audit_read.ReadEntry]) -> None:
        audit_read.guide_check(
            entries, gold_value("walk_table"), gold_value("walk_gold")
        )

    # A walk its table and gold expect passes both checks.
    def test_walk_passed(self) -> None:
        entries = self.entries_of("walk")
        audit_read.failure_check(entries)
        self.guide_check(entries)

    # A dump, the answer to an input of 0 in debug mode, is no fault.
    def test_dump_passed(self) -> None:
        self.rows_write(gold_value("walk"))
        audit.dump_put("databases of the browser", gold_value("views"))
        self.guide_check(self.entries_of())

    # A table with no reply to the player's text fails at the model's reply.
    def test_reply_missing(self) -> None:
        entries = self.entries_of("walk")
        table = copy.deepcopy(gold_value("walk_table"))
        del table["nodes"]["again"]["otherwise"]
        with self.assertRaisesRegex(
            audit_read.AuditFailed, gold_value("reply_missing")
        ):
            audit_read.guide_check(entries, table, gold_value("walk_gold"))

    # Each fault of the gold, put in the walk, fails at its first message.
    def test_each_fault(self) -> None:
        walk: list[dict[str, Any]] = gold_value("walk")
        faults: dict[str, dict[str, Any]] = gold_value("guide_failures")
        for name, fault in faults.items():
            with self.subTest(name=name):
                self.document_close()
                os.remove(self.path)
                audit.audit_open(self.root, _BLOB_MAX, "engine")
                self.closed = False
                at: int = fault["at"]
                self.rows_write([*walk[:at], *fault["rows"], *walk[at + 1 :]])
                with self.assertRaisesRegex(
                    audit_read.AuditFailed, fault["failure"]
                ):
                    self.guide_check(self.entries_of())


# The database check of commits the server's handlers applied, and the text.
class TestDatabases(AuditCase):
    # Makes the start's databases, copies them as the server's, serves there.
    def setUp(self) -> None:
        super().setUp()
        self.start = os.path.join(self.root, "start")
        self.end = os.path.join(self.root, "end")
        self.replay = os.path.join(self.root, "replay")
        self.limits: list[int] = gold_value("databases_limits")
        store = substrate.Store(self.start, *self.limits)
        for name in gold_value("databases_start"):
            store.db_create(name)
            store.db_close(name)
        shutil.copytree(self.start, self.end)
        self.rows_write(gold_value("databases_settings"))
        self.commits_serve()

    # Applies the gold's commits to `end` by the server's handlers in a child.
    def commits_serve(self) -> None:
        ending = os.path.join(self.root, "ending.txt")
        rows: list[dict[str, Any]] = gold_value("databases_commits")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            commits_serve(self.end, self.limits, rows, ending)
        os.waitpid(pid, 0)
        with open(ending, encoding="utf-8") as file:
            self.assertEqual(file.read(), "served")

    # The end's store, open on each database, closed when the test ends.
    def end_store(self) -> substrate.Store:
        store = substrate.Store(self.end, *self.limits)
        for name in gold_value("databases_start"):
            store.db_open(name)
            self.addCleanup(store.db_close, name)
        return store

    # Asserts the check of the record raises the gold's failure of `name`.
    def check_failed(self, name: str, start: str) -> None:
        entries = self.entries_of()
        with self.assertRaisesRegex(
            audit_read.AuditFailed, gold_value("databases_failures")[name]
        ):
            audit_read.databases_check(entries, start, self.end, self.replay)

    # The replay of each kind of commit makes the server's databases.
    def test_replay_passed(self) -> None:
        entries = self.entries_of()
        audit_read.databases_check(entries, self.start, self.end, self.replay)
        self.assertEqual(
            audit_read.database_lines(self.replay),
            audit_read.database_lines(self.end),
        )

    # A value the server holds that the record did not put fails at its put.
    def test_value_differs(self) -> None:
        self.end_store().kv_put(gold_value("databases_put_ref"), b"other")
        self.check_failed("value", self.start)

    # A row the server holds that no commit made fails at its table.
    def test_row_differs(self) -> None:
        statement = substrate.SqlStatement(gold_value("databases_extra"), [])
        self.end_store().sql_run(gold_value("databases_start")[0], [statement])
        self.check_failed("row", self.start)

    # A commit the store refuses, a database the start holds, fails at it.
    def test_commit_refused(self) -> None:
        self.check_failed("refused", self.end)

    # Each kind of cell is told, a long string whole, the store's tables once.
    def test_lines_told(self) -> None:
        lines = audit_read.database_lines(self.end)
        for line in gold_value("databases_lines"):
            with self.subTest(line=line):
                self.assertIn(line, lines)


# The repeat check of a told walk, on a database the real store wrote.
class TestRepeated(AuditCase):
    # Writes the end's database by the real store, as the server left it.
    def setUp(self) -> None:
        super().setUp()
        self.end = os.path.join(self.root, "end")
        made: dict[str, Any] = gold_value("repeat_database")
        store = substrate.Store(self.end, *gold_value("databases_limits"))
        store.db_create(made["db"])
        statements = [
            substrate.SqlStatement(row["sql"], row["params"])
            for row in made["statements"]
        ]
        store.sql_run(made["db"], statements)
        store.db_close(made["db"])

    # Starts the document again with no entry.
    def document_renew(self) -> None:
        self.document_close()
        os.remove(self.path)
        audit.audit_open(self.root, _BLOB_MAX, "engine")
        self.closed = False

    # The message of the check's refusal of the entries by a table and query.
    def refusal_of(
        self,
        entries: list[audit_read.ReadEntry],
        table: dict[str, Any],
        repeated: dict[str, Any],
    ) -> str:
        with self.assertRaises(audit_read.AuditFailed) as caught:
            audit_read.repeat_check(entries, table, self.end, repeated)
        return str(caught.exception)

    # A told walk passes, its evidence naming the line that shows each part.
    def test_repeat_passed(self) -> None:
        entries = self.entries_of("repeat_walk")
        audit_read.failure_check(entries)
        evidence = audit_read.repeat_check(
            entries,
            gold_value("repeat_table"),
            self.end,
            gold_value("repeat_query"),
        )
        lines: list[int] = gold_value("repeat_lines")
        numbers = [entries[index].number for index in lines]
        due = gold_value("repeat_evidence").format(*numbers)
        self.assertEqual(evidence, due)

    # A query of no row, two rows, a number, an empty text or two texts fails.
    def test_query_refused(self) -> None:
        entries = self.entries_of("repeat_walk")
        for case in gold_value("repeat_queries"):
            with self.subTest(sql=case["sql"]):
                repeated = {
                    **gold_value("repeat_query"),
                    "sql": case["sql"],
                    "params": case["params"],
                }
                message = self.refusal_of(
                    entries, gold_value("repeat_table"), repeated
                )
                self.assertEqual(message, case["failure"])

    # Read only: a query that writes raises, and the database keeps its rows.
    def test_read_only(self) -> None:
        entries = self.entries_of("repeat_walk")
        table = gold_value("repeat_table")
        repeated: dict[str, Any] = gold_value("repeat_query")
        writing = {**repeated, "sql": gold_value("repeat_write")}
        with self.assertRaises(sqlite3.OperationalError):
            audit_read.repeat_check(entries, table, self.end, writing)
        audit_read.repeat_check(entries, table, self.end, repeated)

    # A record with no band yet fails before it reads a turn.
    def test_band_missing(self) -> None:
        cut: dict[str, Any] = gold_value("repeat_cut")
        walk: list[dict[str, Any]] = gold_value("repeat_walk")
        self.rows_write(walk[: cut["at"]])
        message = self.refusal_of(
            self.entries_of(),
            gold_value("repeat_table"),
            gold_value("repeat_query"),
        )
        self.assertEqual(message, cut["failure"])

    # Each fault of the gold, put in the walk, fails naming the line it says.
    def test_each_refusal(self) -> None:
        walk: list[dict[str, Any]] = gold_value("repeat_walk")
        faults: dict[str, dict[str, Any]] = gold_value("repeat_failures")
        for name, fault in faults.items():
            with self.subTest(name=name):
                self.document_renew()
                at: int = fault["at"]
                self.rows_write([*walk[:at], *fault["rows"], *walk[at + 1 :]])
                entries = self.entries_of()
                message = self.refusal_of(
                    entries,
                    gold_value("repeat_table"),
                    gold_value("repeat_query"),
                )
                number = entries[fault["line"]].number
                self.assertEqual(message, fault["failure"].format(number))

    # A content of the table that holds the output fails, named by its place.
    def test_own_text(self) -> None:
        own: dict[str, Any] = gold_value("repeat_own")
        table = copy.deepcopy(gold_value("repeat_table"))
        table["nodes"]["end"]["otherwise"]["content"] = own["content"]
        message = self.refusal_of(
            self.entries_of("repeat_walk"), table, gold_value("repeat_query")
        )
        self.assertEqual(message, own["failure"])


# A text that is no audit document.
class TestForm(unittest.TestCase):
    # Each of the gold's texts raises naming the line that does not fit.
    def test_form_refused(self) -> None:
        for text, message in gold_value("refused"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError) as caught:
                    audit_read.entries_parse(text)
                self.assertEqual(str(caught.exception), message)


# The program whole, in a forked child.
class TestProgram(AuditCase):
    # Runs the program in a forked child, returns how it ended and its output.
    def program_run(self, *arguments: str) -> tuple[str, str]:
        output = os.path.join(self.root, "output.txt")
        ending = os.path.join(self.root, "ending.txt")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            child_run(list(arguments), output, ending)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(ending, encoding="utf-8") as file:
            ended = file.read()
        with open(output, encoding="utf-8") as file:
            printed = file.read()
        os.remove(ending)
        os.remove(output)
        return ended, printed

    # Without `--check` the digest prints under its title, with no verdict.
    def test_digest_only(self) -> None:
        self.rows_write(gold_value("error"))
        ended, printed = self.program_run(self.path)
        self.assertEqual(ended, "0")
        entries = audit_read.entries_parse(audit_read.document_read(self.path))
        due = [
            gold_value("digest_title").format(self.path),
            *audit_read.digest_lines(entries),
        ]
        self.assertEqual(printed, "\n".join(due) + "\n")

    # `--check` on a run with no failure exits 0, the verdict after the digest.
    def test_check_passed(self) -> None:
        self.rows_write(gold_value("run"))
        ended, printed = self.program_run(self.path, "--check")
        self.assertEqual(ended, "0")
        verdict = gold_value("check_passed")
        self.assertTrue(printed.endswith(f"\n\n{verdict}\n"))

    # `--check` on a run with a failure exits 1, naming its line.
    def test_check_failed(self) -> None:
        self.rows_write(gold_value("error"))
        ended, printed = self.program_run(self.path, "--check")
        self.assertEqual(ended, "1")
        self.assertIn("failure: line 3: a line of type error", printed)

    # `--guide` reads a real guide's table and gold, and fails a walk not its.
    def test_guide_refused(self) -> None:
        self.rows_write(gold_value("walk"))
        ended, printed = self.program_run(
            self.path, "--guide", gold_value("guide_name")
        )
        self.assertEqual(ended, "1")
        self.assertRegex(printed, gold_value("guide_refused"))
