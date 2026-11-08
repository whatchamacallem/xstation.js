# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the audit document on scratch roots in `build/`: a line with and
# without blobs laid out, a page thread's record laid out as the server's own
# line is, a note, a dump of views in name order, the audit's own lines left
# out, the start headings of both roles, two opens appending to one file, two
# processes writing at once with no entry interleaved, a hard exit keeping
# every entry written, a write past `blob_max` refused whole, the tail's fit
# and order, and `entries_read` reading back what was written. The texts,
# lines and views are the gold's.

import audit, harness, jslb, json, os, re, signal, sys, tempfile, time
import unittest
from typing import Any, cast

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_audit"

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The `blob_max` of the settings, the largest document.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The file in the root that holds the document.
_FILE_NAME = "_audit.txt"

# How many milliseconds a second counts.
_MILLISECONDS = 1000


# A value of this module's gold.
def _gold(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# A text of the gold's `texts`.
def _text_get(name: str) -> str:
    return cast(str, _gold(f"texts.{name}"))


# Lines of the gold joined as one text.
def _joined(name: str) -> str:
    return "\n".join(cast(list[str], _gold(name)))


# A line of the gold read as the decoders read one.
def _line_of(name: str) -> jslb.Object:
    return cast(jslb.Object, jslb.json_decode(json.dumps(_gold(name))))


# The gold's local time in milliseconds since the epoch.
def _at_gold() -> int:
    year, month, day, hour, minute, second = _gold("at_local")
    local = (year, month, day, hour, minute, second, 0, 0, -1)
    return int(time.mktime(local)) * _MILLISECONDS + _gold("at_milliseconds")


# Gives each test a scratch root, the document closed at its end.
class ScratchCase(unittest.TestCase):
    # Makes the scratch root.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.root = scratch.name
        self.path = os.path.join(self.root, _FILE_NAME)

    # Opens the root's document, closed when the test ends.
    def audit_ready(
        self, blob_max: int = _BLOB_MAX, role: str = "engine"
    ) -> None:
        audit.audit_open(self.root, blob_max, role)
        self.addCleanup(audit.audit_close)

    # The document's text.
    def text_read(self) -> str:
        with open(self.path, encoding="utf-8") as file:
            return file.read()


# Tests the layout of each kind of entry.
class TestLayout(ScratchCase):
    # A line with a blob is its JSON text over many lines, then the marker.
    def test_line_blobs(self) -> None:
        text = jslb.line_json(_line_of("blob_line"))
        expected = (
            f"---- {_gold('time_text')}, {_gold('record_label')}\n"
            + _joined("blob_body")
            + "\n\n"
        )
        self.assertEqual(
            audit.record_text("ui", "ai", _at_gold(), text), expected
        )

    # A line with no blob has no marker, and keeps its text beyond ASCII.
    def test_line_plain(self) -> None:
        text = jslb.line_json(_line_of("plain_line"))
        body = audit.record_text("ui", "ai", _at_gold(), text).split("\n", 1)
        self.assertEqual(body[1], _joined("plain_body") + "\n\n")

    # The server's own lines are laid out as a page thread's record is.
    def test_record_alike(self) -> None:
        self.audit_ready()
        line = _line_of("blob_line")
        audit.line_received(line)
        audit.line_sent(line)
        audit.record_put("ui", "ai", _at_gold(), jslb.line_json(line))
        entries = audit.entries_read(self.root)
        labels = [entry.label for entry in entries]
        self.assertEqual(
            labels,
            [
                _gold("received_label"),
                _gold("sent_label"),
                _gold("record_label"),
            ],
        )
        for entry in entries:
            self.assertEqual(entry.body, _joined("blob_body"))
            self.assertEqual(entry.start, 1)
        self.assertEqual(entries[2].time, _gold("time_text"))

    # A note's every line is indented under its label.
    def test_note(self) -> None:
        self.audit_ready()
        audit.note_put("ai", _at_gold(), _gold("note_text"))
        (entry,) = audit.entries_read(self.root)
        self.assertEqual(entry.label, _gold("note_label"))
        self.assertEqual(entry.body, _joined("note_body"))
        self.assertEqual(
            audit.note_text("ai", _at_gold(), _gold("note_text")),
            f"---- {_gold('time_text')}, {_gold('note_label')}\n"
            + _joined("note_body")
            + "\n\n",
        )

    # A dump lays out each database in name order, history counted.
    def test_dump(self) -> None:
        self.audit_ready()
        audit.dump_put(_gold("dump_title"), _gold("views"))
        (entry,) = audit.entries_read(self.root)
        self.assertEqual(entry.label, _gold("dump_title"))
        self.assertEqual(entry.body, _joined("dump_body"))

    # The audit's own lines are never recorded, either way.
    def test_own_skipped(self) -> None:
        self.audit_ready()
        before = self.text_read()
        audit.line_received(_line_of("own_line"))
        audit.line_sent(_line_of("own_line"))
        self.assertEqual(self.text_read(), before)


# Tests the file: its headings, its appends, its limit and its writers.
class TestFile(ScratchCase):
    # Each role's open writes its start heading with the process id.
    def test_starts(self) -> None:
        for role in ("engine", "console"):
            audit.audit_open(self.root, _BLOB_MAX, role)
            audit.audit_close()
        headings = self.text_read().split("\n\n")[:2]
        pattern = re.compile(_gold("start_pattern"))
        for role, heading in zip(("engine", "console"), headings, strict=True):
            match = pattern.fullmatch(heading)
            self.assertIsNotNone(match, heading)
            match = cast(re.Match[str], match)
            self.assertEqual(match[1], role)
            self.assertEqual(int(match[2]), os.getpid())

    # Two opens append to one file, each entry under its own start.
    def test_appended(self) -> None:
        for number in range(2):
            audit.audit_open(self.root, _BLOB_MAX, "engine")
            audit.note_put("ui", _at_gold(), str(number))
            audit.audit_close()
        entries = audit.entries_read(self.root)
        self.assertEqual([entry.start for entry in entries], [1, 2])
        self.assertEqual([entry.body for entry in entries], ["  0", "  1"])

    # An entry past `blob_max` raises and writes nothing.
    def test_full(self) -> None:
        self.audit_ready(_gold("full_blob_max"))
        size = os.path.getsize(self.path)
        text = "x" * _gold("full_blob_max")
        entry = audit.note_text("ui", _at_gold(), text)
        with self.assertRaises(OSError) as raised:
            audit.note_put("ui", _at_gold(), text)
        self.assertEqual(
            str(raised.exception),
            _text_get("audit_full").format(
                self.path,
                size,
                len(entry.encode("utf-8")),
                _gold("full_blob_max"),
            ),
        )
        self.assertEqual(os.path.getsize(self.path), size)

    # Before the open each call raises, and a second open raises too.
    def test_not_open(self) -> None:
        for call in (
            audit.audit_close,
            lambda: audit.note_put("ui", 0, "x"),
            lambda: audit.tail_read(1, _BLOB_MAX),
        ):
            with self.assertRaises(RuntimeError) as raised:
                call()
            self.assertEqual(
                str(raised.exception), _text_get("audit_not_open")
            )
        self.audit_ready()
        with self.assertRaises(RuntimeError) as raised:
            audit.audit_open(self.root, _BLOB_MAX, "engine")
        self.assertEqual(str(raised.exception), _text_get("audit_open_twice"))

    # Two processes writing at once leave every entry whole.
    def test_processes(self) -> None:
        count: int = _gold("process_entries")
        children: list[int] = []
        sys.stdout.flush()
        sys.stderr.flush()
        for thread in ("ui", "ai"):
            pid = os.fork()
            if pid == 0:
                audit.audit_open(self.root, _BLOB_MAX, "engine")
                for number in range(count):
                    audit.note_put(thread, _at_gold(), f"{thread} {number}")
                os._exit(0)
            children.append(pid)
        for pid in children:
            status = os.waitpid(pid, 0)[1]
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        entries = audit.entries_read(self.root)
        self.assertEqual(len(entries), 2 * count)
        for thread in ("ui", "ai"):
            bodies = [
                entry.body
                for entry in entries
                if entry.label == f"note of {thread}"
            ]
            self.assertEqual(
                bodies, [f"  {thread} {number}" for number in range(count)]
            )

    # A process ended by SIGKILL leaves every entry it wrote.
    def test_hard_exit(self) -> None:
        count: int = _gold("hard_entries")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            audit.audit_open(self.root, _BLOB_MAX, "engine")
            for number in range(count):
                audit.note_put("ai", _at_gold(), str(number))
            os.kill(os.getpid(), signal.SIGKILL)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        bodies = [entry.body for entry in audit.entries_read(self.root)]
        self.assertEqual(bodies, [f"  {number}" for number in range(count)])


# Tests the end of the document a tail reads.
class TestTail(ScratchCase):
    # Writes five notes and returns each entry's text as the document has it.
    def notes_write(self) -> list[str]:
        self.audit_ready()
        texts: list[str] = []
        for number in range(5):
            audit.note_put("ui", _at_gold(), f"note {number}")
            texts.append(audit.note_text("ui", _at_gold(), f"note {number}"))
        return texts

    # The newest entries, at most the count, oldest first.
    def test_order(self) -> None:
        texts = self.notes_write()
        self.assertEqual(audit.tail_read(3, _BLOB_MAX), "".join(texts[2:]))
        self.assertEqual(audit.tail_read(9, _BLOB_MAX), "".join(texts))
        self.assertEqual(audit.tail_read(0, _BLOB_MAX), "")

    # An entry that does not fit the limit ends the tail, older ones too.
    def test_fit(self) -> None:
        texts = self.notes_write()
        sizes = [
            len(json.dumps(text, ensure_ascii=False).encode("utf-8")) - 2
            for text in texts
        ]
        limit = sizes[3] + sizes[4] + 1
        self.assertEqual(audit.tail_read(5, limit), "".join(texts[3:]))
        self.assertEqual(audit.tail_read(5, limit - 1), texts[4])
        self.assertEqual(audit.tail_read(5, sizes[4]), "")
