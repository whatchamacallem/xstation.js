# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the TAP suite server joined to everything it calls into, in a forked
# child over pipes, with a root in `build/` whose settings are the
# checkout's in short names. One input holds two `tap.run` requests, served
# in turn by the handler the server registers in the real `dispatch`, read
# and answered by the real codec of `jslb` with the limits the real
# `settings` reads, each running the real driver, test_all.py, as a
# program: a small suite in a smoke-test run, then failing_suite, the suite
# that fails by design, in a normal-test run that expects the failures the
# gold measured for it. The lines each run pushes come before its reply,
# and the TAP consumer reads them as one stream, well formed, with those
# failures, so that each reply's exit code is the driver's pass. The child
# writes how its work ended to a file, or to stderr with the failure when
# that write fails, then kills itself whatever happened, so the handler it
# registers never reaches another test.

import functools, harness, json, os, signal, sys, tap_consumer, tap_loop
import tempfile, traceback, unittest
from collections.abc import Callable
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_tap_loop"

# A size chosen by its writer: the most the test reads from the pipe.
_READ_BYTES: int = harness.gold_get(f"{_GOLD_ID}.read_bytes")

# The failing tests of failing_suite in a normal-test run, as measured.
_FAILING_FAILURES: int = harness.gold_get(f"{_GOLD_ID}.failing_failures")

# How a child ends when the loop returns at the end of its input.
_ENDING_RETURNED = "returned"

# The exit code of the driver when the failing tests are those expected.
_DRIVER_PASSED = 0

# The small suite of the first run.
_SUITE_SMALL = "test_tap_producer"

# The suite of the second run, which fails by design.
_SUITE_FAILING = "failing_suite"


# The bytes of a `tap.run` request of one suite, with no failfast.
def _run_make(
    request_id: int, category: str, failures: int, module: str
) -> bytes:
    line = {
        "0": {"t": "tap.run", "i": request_id},
        "category": category,
        "failfast": False,
        "failures": failures,
        "modules": [module],
    }
    return json.dumps(line, separators=(",", ":")).encode("utf-8") + b"\r"


# Splits output into its lines, none of which carries a blob.
def _lines_split(output: bytes) -> list[dict[str, Any]]:
    return [json.loads(text) for text in output.split(b"\r")[:-1]]


# Reads a pipe to its end and closes it.
def _pipe_drain(fd: int) -> bytes:
    data = bytearray()
    while chunk := os.read(fd, _READ_BYTES):
        data += chunk
    os.close(fd)
    return bytes(data)


# In the forked child: runs the work, writes how it ended, kills itself.
def _child_end(
    work: Callable[[int, int], str], read_fd: int, write_fd: int, path: str
) -> None:
    try:
        try:
            ending = work(read_fd, write_fd)
        except SystemExit as error:
            ending = f"exit {error.code}"
        except BaseException:
            ending = traceback.format_exc()
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(ending)
        except BaseException:
            # The parent finds no ending, so the failure and it go to stderr.
            sys.stderr.write(
                f"{traceback.format_exc()}the ending not written: {ending}\n"
            )
            sys.stderr.flush()
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# The work of a child that prepares the root and serves the pipes to the end.
def _suites_serve(root: str, read_fd: int, write_fd: int) -> str:
    tap_loop.loop_prepare(root)
    tap_loop.loop_run(read_fd, write_fd, root)
    return _ENDING_RETURNED


# Runs of the driver served in turn by the server and its callees.
class TestRuns(unittest.TestCase):
    # Makes the scratch directory and the root with the short names.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.scratch = scratch.name
        self.root = os.path.join(scratch.name, "root")
        os.mkdir(self.root)
        values = harness.settings_copy()
        values["debug"] = False
        path = os.path.join(self.root, "settings.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(values, file)

    # Serves the data in a child, returns its ending and the lines written.
    def serve_read(self, data: bytes) -> tuple[str, list[dict[str, Any]]]:
        input_read, input_write = os.pipe()
        os.set_blocking(input_write, False)
        self.assertEqual(os.write(input_write, data), len(data))
        os.close(input_write)
        output_read, output_write = os.pipe()
        path = os.path.join(self.scratch, "ending.txt")
        work = functools.partial(_suites_serve, self.root)
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            os.close(output_read)
            _child_end(work, input_read, output_write, path)
        os.close(input_read)
        os.close(output_write)
        output = _pipe_drain(output_read)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        with open(path, encoding="utf-8") as file:
            ending = file.read()
        os.remove(path)
        return ending, _lines_split(output)

    # Splits the lines into the runs: the texts each pushed, then its reply.
    def runs_split(
        self, lines: list[dict[str, Any]]
    ) -> list[tuple[list[str], dict[str, Any]]]:
        runs: list[tuple[list[str], dict[str, Any]]] = []
        texts: list[str] = []
        for line in lines:
            if "r" in line["0"]:
                runs.append((texts, line))
                texts = []
                continue
            self.assertEqual(line["0"], {"t": "tap.line"})
            self.assertEqual(line["language"], "python")
            texts.append(line["text"])
        self.assertEqual(texts, [])
        return runs

    # Each run pushes its stream, then replies the driver's pass.
    def test_runs_served(self) -> None:
        first = _run_make(1, "smoke-test", 0, _SUITE_SMALL)
        second = _run_make(2, "normal-test", _FAILING_FAILURES, _SUITE_FAILING)
        ending, lines = self.serve_read(first + second)
        self.assertEqual(ending, _ENDING_RETURNED)
        runs = self.runs_split(lines)
        headers = [reply["0"] for _, reply in runs]
        expected = [{"t": "tap.run", "r": 1}, {"t": "tap.run", "r": 2}]
        self.assertEqual(headers, expected)
        for (texts, reply), failures in zip(
            runs, (0, _FAILING_FAILURES), strict=True
        ):
            document = "".join(text + "\n" for text in texts)
            stats = tap_consumer.document_stats(document)
            self.assertTrue(stats.well_formed, document)
            self.assertEqual(stats.failed, failures, document)
            self.assertEqual(reply["code"], _DRIVER_PASSED, reply["stderr"])
