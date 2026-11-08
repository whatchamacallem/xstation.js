# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the note of console, which goes into the root's audit, and the three
# levels of the shell's runner, whose start and end of a program are such notes
# at levels 1 and 2. The notes are read back from a real audit in a scratch
# directory under `build/`. The only program a test starts is the interpreter
# that runs it. The texts expected are the gold's.

import audit, harness, os, shlex, subprocess, sys, tempfile, unittest, verbose
from collections.abc import Callable

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_verbose"

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# Where the bytecode of a started program that imports the module goes.
_PYCACHE_PATH = os.path.join(_BUILD_PATH, "pycache")

# The directory that holds the module, which a started program imports from.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The `blob_max` of the settings, the largest audit.
_BLOB_MAX: int = harness.setting_get("blob_max")

# The role the audit is opened for.
_CONSOLE_ROLE = "console"

# The label of an audit entry of a note of console.
_NOTE_LABEL: str = harness.gold_get(f"{_GOLD_ID}.note_label")

# The indent of each line of a note's body.
_NOTE_INDENT: str = harness.gold_get(f"{_GOLD_ID}.note_indent")

# A program that writes a line to each stream in turn and exits with code 3.
_OUTPUT_PROGRAM = (
    "import sys\n"
    "print('alpha', flush=True)\n"
    "print('beta', file=sys.stderr, flush=True)\n"
    "sys.exit(3)\n"
)

# A program that exits with the code in its first argument.
_EXIT_PROGRAM = "import sys; sys.exit(int(sys.argv[1]))"

# A program that writes its arguments as a list.
_ARGS_PROGRAM = "import sys; print(sys.argv[1:], flush=True)"

# A program that writes what it reads from its input, quoted.
_INPUT_PROGRAM = "import sys; print(repr(sys.stdin.read()), flush=True)"

# A program that makes the file that its first argument names.
_MARKER_PROGRAM = "import sys; open(sys.argv[1], 'w').close()"

# A program that notes two lines and ends at once, without cleaning up.
_HARD_PROGRAM = (
    "import os, sys\n"
    "sys.pycache_prefix = sys.argv[3]\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import audit, verbose\n"
    "audit.audit_open(sys.argv[2], "
    + str(_BLOB_MAX)
    + ", "
    + repr(_CONSOLE_ROLE)
    + ")\n"
    "verbose.console_note('first')\n"
    "verbose.console_note('second')\n"
    "os._exit(7)\n"
)

# A program: text unflushed in both streams, then its last args run at a level.
_HELD_PROGRAM = (
    "import sys\n"
    "sys.pycache_prefix = sys.argv[3]\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import audit, verbose\n"
    "audit.audit_open(sys.argv[2], "
    + str(_BLOB_MAX)
    + ", "
    + repr(_CONSOLE_ROLE)
    + ")\n"
    "for stream in (sys.stdout, sys.stderr):\n"
    "    stream.reconfigure(line_buffering=False, write_through=False)\n"
    "    stream.write('before ')\n"
    "argv = sys.argv[5:]\n"
    "sys.exit(verbose.exec(int(sys.argv[4]), argv, argv))\n"
)


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Makes a scratch directory in `build/` that goes when the test ends.
def _scratch_make(case: unittest.TestCase) -> str:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
    case.addCleanup(scratch.cleanup)
    return scratch.name


# Opens the audit in a scratch directory and returns the directory.
def _audit_ready(case: unittest.TestCase) -> str:
    path = _scratch_make(case)
    audit.audit_open(path, _BLOB_MAX, _CONSOLE_ROLE)
    case.addCleanup(audit.audit_close)
    return path


# Calls `fn` and checks the type and the text of what it raises.
def _raise_check(
    case: unittest.TestCase,
    kind: type[Exception],
    message: str,
    fn: Callable[[], object],
) -> None:
    with case.assertRaises(kind) as caught:
        fn()
    case.assertEqual(str(caught.exception), message)


# The label and body of each entry of the directory's audit, in order.
def _notes_read(path: str) -> list[tuple[str, str]]:
    return [(entry.label, entry.body) for entry in audit.entries_read(path)]


# The label and body the audit holds for a note of the text.
def _note_entry(text: str) -> tuple[str, str]:
    lines = text.split("\n")
    indented = [_NOTE_INDENT + line if line else line for line in lines]
    return (_NOTE_LABEL, "\n".join(indented))


# Returns the notes of a run: its start, then its end with the code.
def _progress_notes(argv: list[str], code: int) -> list[tuple[str, str]]:
    command = shlex.join(argv)
    return [
        _note_entry(_text_get("verbose_exec_run").replace("{0}", command)),
        _note_entry(
            _text_get(f"verbose_exec_exit_{code}").replace("{0}", command)
        ),
    ]


# Runs `fn` with the output descriptors of this process set to files.
def _output_captured(path: str, fn: Callable[[], int]) -> tuple[int, str, str]:
    out_path = os.path.join(path, "out.txt")
    err_path = os.path.join(path, "err.txt")
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out = os.dup(1)
    saved_err = os.dup(2)
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            os.dup2(out.fileno(), 1)
            os.dup2(err.fileno(), 2)
            try:
                code = fn()
            finally:
                os.dup2(saved_out, 1)
                os.dup2(saved_err, 2)
    finally:
        os.close(saved_out)
        os.close(saved_err)
    with open(out_path, encoding="utf-8") as file:
        out_text = file.read()
    with open(err_path, encoding="utf-8") as file:
        err_text = file.read()
    return code, out_text, err_text


# Runs `fn` with descriptor 0 of this process reading the bytes from a pipe.
def _input_given(data: bytes, fn: Callable[[], int]) -> int:
    read_fd, write_fd = os.pipe()
    os.write(write_fd, data)
    os.close(write_fd)
    saved = os.dup(0)
    try:
        os.dup2(read_fd, 0)
        return fn()
    finally:
        os.dup2(saved, 0)
        os.close(saved)
        os.close(read_fd)


# Tests the note of console.
class TestNote(unittest.TestCase):
    # Each text is a note of console in the audit, each line of it indented.
    def test_note_written(self) -> None:
        path = _audit_ready(self)
        for text in ["zero", "one\ntwo"]:
            verbose.console_note(text)
        two_lines = _NOTE_INDENT + "one\n" + _NOTE_INDENT + "two"
        self.assertEqual(
            _notes_read(path),
            [_note_entry("zero"), (_NOTE_LABEL, two_lines)],
        )

    # A note before the audit is opened raises the audit's refusal.
    def test_audit_unopened(self) -> None:
        _raise_check(
            self,
            RuntimeError,
            _text_get("audit_not_open"),
            lambda: verbose.console_note("early"),
        )

    # The notes of a program that ends at once are in the audit.
    def test_hard_exit(self) -> None:
        path = _scratch_make(self)
        argv = [
            sys.executable,
            "-c",
            _HARD_PROGRAM,
            _PYTHON_PATH,
            path,
            _PYCACHE_PATH,
        ]
        self.assertEqual(verbose.exec(0, argv, argv), 7)
        self.assertEqual(
            _notes_read(path), [_note_entry("first"), _note_entry("second")]
        )


# Tests the shell's runner at its three levels.
class TestCommand(unittest.TestCase):
    # A level outside 0 to 2 raises, runs nothing and notes nothing.
    def test_level_unknown(self) -> None:
        path = _audit_ready(self)
        program = [sys.executable, "-c", _MARKER_PROGRAM]
        argv = [*program, os.path.join(path, "ran")]
        for level, case in ((3, "above"), (-1, "below")):
            _raise_check(
                self,
                ValueError,
                _text_get(f"verbose_level_invalid_{case}"),
                lambda: verbose.exec(level, argv, argv),
            )
        self.assertFalse(os.path.exists(argv[-1]))
        self.assertEqual(_notes_read(path), [])

    # Level 0 returns the exit code of the program.
    def test_command_code(self) -> None:
        argv = [sys.executable, "-c", _EXIT_PROGRAM]
        self.assertEqual(verbose.exec(0, argv + ["0"], argv + ["0"]), 0)
        self.assertEqual(verbose.exec(0, argv + ["5"], argv + ["5"]), 5)

    # Level 0 passes the output through and notes nothing.
    def test_command_pass(self) -> None:
        path = _audit_ready(self)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        code, out, err = _output_captured(
            path, lambda: verbose.exec(0, argv, argv)
        )
        self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
        self.assertEqual(_notes_read(path), [])

    # Every level writes what Python holds for both streams before it runs.
    def test_command_flushed(self) -> None:
        path = _scratch_make(self)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        for level in range(3):
            child = [
                sys.executable,
                "-c",
                _HELD_PROGRAM,
                _PYTHON_PATH,
                path,
                _PYCACHE_PATH,
                str(level),
                *argv,
            ]
            ended = subprocess.run(
                child, capture_output=True, encoding="utf-8"
            )
            self.assertEqual(
                (ended.returncode, ended.stdout, ended.stderr),
                (3, "before alpha\n", "before beta\n"),
            )

    # Levels 1 and 2 pass the output through and note its start and its exit.
    def test_command_noted(self) -> None:
        path = _audit_ready(self)
        argv = [sys.executable, "-c", _OUTPUT_PROGRAM]
        expected: list[tuple[str, str]] = []
        for level in (1, 2):
            code, out, err = _output_captured(
                path, lambda: verbose.exec(level, argv, argv)
            )
            self.assertEqual((code, out, err), (3, "alpha\n", "beta\n"))
            expected += _progress_notes(argv, 3)
            self.assertEqual(_notes_read(path), expected)

    # Level 2 runs the verbose command line, levels 0 and 1 the plain one.
    def test_command_chosen(self) -> None:
        path = _audit_ready(self)
        program = [sys.executable, "-c", _ARGS_PROGRAM]
        argv = [*program, "plain"]
        argv_verbose = [*program, "--verbose", "x y"]
        listed = str(["plain"]) + "\n"
        listed_verbose = str(["--verbose", "x y"]) + "\n"
        printed = {0: listed, 1: listed, 2: listed_verbose}
        for level, expected in printed.items():
            code, out, _ = _output_captured(
                path, lambda: verbose.exec(level, argv, argv_verbose)
            )
            self.assertEqual((code, out), (0, expected))
        self.assertEqual(
            _notes_read(path),
            [*_progress_notes(argv, 0), *_progress_notes(argv_verbose, 0)],
        )

    # Every level passes the input through, so a console reads its terminal.
    def test_command_input(self) -> None:
        path = _audit_ready(self)
        argv = [sys.executable, "-c", _INPUT_PROGRAM]
        for level in range(3):
            code, out, _ = _output_captured(
                path,
                lambda: _input_given(
                    b"typed", lambda: verbose.exec(level, argv, argv)
                ),
            )
            self.assertEqual((code, out), (0, repr("typed") + "\n"))

    # A program that cannot start raises at every level, noted at 1 and 2.
    def test_command_start(self) -> None:
        path = _audit_ready(self)
        absent = [os.path.join(path, "absent")]
        for level in range(3):
            with self.assertRaises(FileNotFoundError) as caught:
                verbose.exec(level, absent, absent)
            self.assertEqual(caught.exception.filename, absent[0])
        started = _note_entry(
            _text_get("verbose_exec_run").replace("{0}", shlex.join(absent))
        )
        self.assertEqual(_notes_read(path), [started, started])

    # Level 0 needs no audit, and levels 1 and 2 refuse before they run.
    def test_command_unopened(self) -> None:
        path = _scratch_make(self)
        program = [sys.executable, "-c", _MARKER_PROGRAM]
        first = [*program, os.path.join(path, "first")]
        second = [*program, os.path.join(path, "second")]
        self.assertEqual(verbose.exec(0, first, first), 0)
        self.assertTrue(os.path.exists(first[-1]))
        for level in (1, 2):
            _raise_check(
                self,
                RuntimeError,
                _text_get("audit_not_open"),
                lambda: verbose.exec(level, second, second),
            )
        self.assertFalse(os.path.exists(second[-1]))
