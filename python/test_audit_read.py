# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the audit's reader on documents the real audit module writes in scratch
# roots in `build/`, whose suite has passed: a run with no failure read back,
# each line whole though the document wrote it thin, its digest and summary,
# each lane's bytes fewer as written than as sent, two scenes in turn across a
# reload with no failure, each kind of unexpected failure found at its line,
# and the form of a document refused. The failures of a chain are a chained
# call that resends the prompt or the history or names a response the record
# lacks, a chain's first call holding the prompt twice, the lanes writing the
# prompt twice, and an item of the model's output written twice. The program
# whole runs in a forked child by `runpy`, so that the count reaches its last
# line. The texts are the gold's.

import audit, audit_read, harness, json, os, runpy, signal, sys, tempfile
import traceback, unittest
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

    # A digest has a line per entry and a line per start of the engine.
    def test_digest_lines(self) -> None:
        lines = audit_read.digest_lines(self.entries_of("run"))
        self.assertEqual(lines, gold_value("run_digest"))

    # A document with no entry has an empty digest and a summary of nothing.
    def test_empty_read(self) -> None:
        entries = self.entries_of()
        self.assertEqual(audit_read.digest_lines(entries), [])
        self.assertEqual(
            audit_read.summary_lines(entries), gold_value("empty_summary")
        )

    # The summary counts what the run did, each lane's bytes measured here.
    def test_summary_lines(self) -> None:
        entries = self.entries_of("run")
        fixed: list[str] = gold_value("run_summary")
        at: int = gold_value("summary_bytes_at")
        lanes = [
            gold_value("summary_bytes").format(*measured)
            for measured in self.lanes_measured(gold_value("run"))
        ]
        self.assertEqual(
            audit_read.summary_lines(entries),
            [*fixed[:at], *lanes, *fixed[at:]],
        )

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

    # A dump of each side, the same text and differing, is told in the summary.
    def test_dumps_told(self) -> None:
        views: list[dict[str, Any]] = gold_value("views")
        audit.dump_put("databases of the browser", views)
        audit.dump_put("databases of the server", views)
        entries = self.entries_of()
        self.assertIn(
            "database dumps: 2, the same text",
            audit_read.summary_lines(entries),
        )
        audit.dump_put("databases of the server", [])
        entries = self.entries_of()
        self.assertIn(
            "database dumps: 3, differing", audit_read.summary_lines(entries)
        )
        audit_read.failure_check(entries)

    # A long value is cut, and an MCP reply with no content shows its payload.
    def test_details_told(self) -> None:
        lines = audit_read.digest_lines(self.entries_of("details"))
        ends: list[str] = gold_value("details_ends")
        for line, end in zip(lines[1:], ends, strict=True):
            self.assertTrue(line.endswith(end), line)

    # A debug mode call's tool list is told as the text it sent in its place.
    def test_tools_omitted(self) -> None:
        entries = self.entries_of("omitted")
        detail: str = gold_value("omitted_detail")
        line = audit_read.digest_lines(entries)[1]
        self.assertTrue(line.endswith(detail), line)
        summary = audit_read.summary_lines(entries)
        for told in gold_value("omitted_summary"):
            self.assertIn(told, summary)
        audit_read.failure_check(entries)

    # A dump's digest line tells its size alone.
    def test_dump_size(self) -> None:
        audit.dump_put("databases of the server", gold_value("views"))
        lines = audit_read.digest_lines(self.entries_of())
        self.assertRegex(lines[-1], r" \d+ bytes$")

    # A chain's first call sends the prompt once, a chained call none.
    def test_prompt_copies(self) -> None:
        entries = self.entries_of("run")
        rows: list[dict[str, Any]] = gold_value("run")
        self.assertEqual(
            audit_read.prompt_copies(entries), gold_value("run_copies")
        )
        self.assertEqual(audit_read.input_of(entries[0]), [])
        self.assertEqual(
            audit_read.input_of(entries[7]), rows[7]["line"]["json"]["input"]
        )


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

    # Without `--check` a document with a failure exits 0, its digest printed.
    def test_digest_only(self) -> None:
        self.rows_write(gold_value("error"))
        ended, printed = self.program_run(self.path)
        self.assertEqual(ended, "0")
        self.assertIn("error", printed)
        self.assertNotIn("check:", printed)

    # `--check` on a run with no failure exits 0 and says so.
    def test_check_passed(self) -> None:
        self.rows_write(gold_value("run"))
        ended, printed = self.program_run(self.path, "--check")
        self.assertEqual(ended, "0")
        self.assertTrue(printed.endswith("check: no unexpected failure\n"))

    # `--check` on a run with a failure exits 1, naming its line.
    def test_check_failed(self) -> None:
        self.rows_write(gold_value("error"))
        ended, printed = self.program_run(self.path, "--check")
        self.assertEqual(ended, "1")
        self.assertIn("failure: line 3: a line of type error", printed)
