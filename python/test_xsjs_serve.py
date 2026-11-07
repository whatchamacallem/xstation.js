# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of xsjs_serve on roots in scratch directories under build/, with the
# ttyd the driver's bring up built. First the root as the start script makes
# one: its files, what a second making keeps and replaces, and fresh. Then
# ttyd's command line against the gold. Then the server on port 0: the port its
# log names, its session of its own, its log copied to stderr, which each test
# points at a scratch file, each way it ends, by either signal, by itself and
# by SIGKILL past the wait, and its refusals. A test that blocks the signals
# gives them back at its end. Last the program whole, in a forked child by
# runpy, which builds the page with the real tsc, so that a count reaches every
# line of the module: its stop at a signal and its refusal. The program ended
# with no chance to stop ttyd is the suite of test_xsjs_serve_death.py, which
# takes ProgramCase from here.

import contextlib, filecmp, harness, os, re, runpy, signal, socket, switches
import sys, tempfile, traceback, unittest, xsjs_serve
from typing import Any, NoReturn, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The checkout's `python` directory, whose modules a root holds.
_PYTHON_PATH = os.path.join(_ROOT_PATH, "python")

# The program under test.
_PROGRAM_PATH = os.path.join(_PYTHON_PATH, "xsjs_serve.py")

# The strings a root holds, by their path in the root and the checkout.
_STRINGS_PATH = os.path.join("i18n", "en-US.json")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_xsjs_serve"

# The directory of a root that holds its modules.
_ROOT_PYTHON = "python"

# The folder of `python` that holds the seed.
_SEED_NAME = "seed"

# The program a build directory holds, as the stub of its build names it.
_TTYD_NAME = "ttyd"

# The name of the page a test writes, in its scratch directory.
_PAGE_NAME = "page.html"

# The name of the file a test points stderr at.
_LOG_NAME = "stderr.log"

# The permissions of that file: read and write by its owner.
_LOG_MODE = 0o600

# The descriptors a forked program prints to and ttyd's log is copied to.
_STDOUT_FD = 1
_STDERR_FD = 2

# The exit code of a forked child whose program raised.
_CHILD_FAILED = 1

# The signals that stop the program.
_STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


# A value of this suite's gold.
def gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Kills ttyd's group, which a test that passed has stopped already.
def group_kill(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


# Stops the forked child of a failed test, which a passing test waited for.
def child_stop(pid: int) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGTERM)
        os.waitpid(pid, 0)


# In the forked child: runs the program whole, its stdout the pipe, and exits.
def program_child(output: int, arguments: list[str]) -> NoReturn:
    code = _CHILD_FAILED
    try:
        os.dup2(output, _STDOUT_FD)
        sys.argv = [_PROGRAM_PATH, *arguments]
        runpy.run_path(_PROGRAM_PATH, run_name="__main__")
    except SystemExit as ended:
        code = cast(int, ended.code)
    except BaseException:
        traceback.print_exc()
    os._exit(code)


# The default root and ttyd's command line, which need no root on disk.
class TestPaths(unittest.TestCase):
    # The default root is `root` under the start script's folder in home.
    def test_root_default(self) -> None:
        self.assertEqual(
            xsjs_serve.root_default(harness.settings_copy()),
            os.path.join(os.path.expanduser("~"), gold_value("root_default")),
        )

    # The command line is the built ttyd, then the gold's on the port given.
    def test_arguments_given(self) -> None:
        values = harness.settings_copy()
        root: str = gold_value("root_sample")
        ttyd = os.path.join(
            _ROOT_PATH,
            harness.setting_get("powershell.ttyd_build"),
            _TTYD_NAME,
        )
        for port in (0, harness.setting_get("powershell.linux_port")):
            with self.subTest(port=port):
                due = [
                    text.replace("{port}", str(port)).replace("{root}", root)
                    for text in gold_value("arguments")
                ]
                self.assertEqual(
                    xsjs_serve.ttyd_arguments(values, root, port),
                    [ttyd, *due],
                )


# A scratch directory with a page in it, and stderr pointed at a file there.
class ScratchCase(unittest.TestCase):
    # Makes the directory, writes the page and points stderr at its file.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.root = os.path.join(self.scratch, "root")
        self.values = harness.settings_copy()
        self.page = os.path.join(self.scratch, _PAGE_NAME)
        with open(self.page, "w", encoding="utf-8") as file:
            file.write(gold_value("page_text"))
        self.log_path = os.path.join(self.scratch, _LOG_NAME)
        saved = os.dup(_STDERR_FD)
        self.addCleanup(os.close, saved)
        self.addCleanup(os.dup2, saved, _STDERR_FD)
        log = os.open(self.log_path, os.O_WRONLY | os.O_CREAT, _LOG_MODE)
        os.dup2(log, _STDERR_FD)
        os.close(log)

    # What stderr has been given so far.
    def log_read(self) -> str:
        with open(self.log_path, encoding="utf-8") as file:
            return file.read()

    # Fails unless the two files hold the same bytes.
    def files_same(self, first: str, second: str) -> None:
        self.assertTrue(filecmp.cmp(first, second, shallow=False), second)

    # Makes the root from the test's page with the gold's parameters.
    def root_ready(self, fresh: bool) -> None:
        xsjs_serve.root_make(
            self.values,
            self.page,
            self.root,
            gold_value("parameters"),
            fresh,
        )


# The root, as the start script makes one.
class TestRoot(ScratchCase):
    # Writes a file that no making holds, under the path given.
    def file_write(self, path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

    # Writes a database of an earlier run, and stale files where copies go.
    def run_earlier(self) -> tuple[str, list[str]]:
        database = os.path.join(self.root, gold_value("database_name"))
        self.file_write(database, gold_value("database_text"))
        stale: str = gold_value("stale_name")
        folders = (_ROOT_PYTHON, os.path.dirname(_STRINGS_PATH))
        paths = [os.path.join(self.root, name, stale) for name in folders]
        for path in paths:
            self.file_write(path, stale)
        return database, paths

    # The root holds the modules, the seed, the strings, the files, the page.
    def test_files_made(self) -> None:
        self.root_ready(False)
        powershell = self.values["powershell"]
        python_path = os.path.join(self.root, _ROOT_PYTHON)
        names = [f"{name}.py" for name in powershell["runtime_modules"]]
        for name in names:
            self.files_same(
                os.path.join(_PYTHON_PATH, name),
                os.path.join(python_path, name),
            )
        self.assertEqual(
            sorted(os.listdir(python_path)), sorted([*names, _SEED_NAME])
        )
        seed_path = os.path.join(_PYTHON_PATH, _SEED_NAME)
        seeds = os.listdir(seed_path)
        self.assertEqual(
            sorted(os.listdir(os.path.join(python_path, _SEED_NAME))),
            sorted(seeds),
        )
        for name in seeds:
            self.files_same(
                os.path.join(seed_path, name),
                os.path.join(python_path, _SEED_NAME, name),
            )
        self.files_same(
            os.path.join(_ROOT_PATH, _STRINGS_PATH),
            os.path.join(self.root, _STRINGS_PATH),
        )
        for name in powershell["root_files"]:
            self.files_same(
                os.path.join(_ROOT_PATH, name), os.path.join(self.root, name)
            )
        self.files_same(
            self.page, os.path.join(self.root, powershell["engine_page"])
        )
        self.assertEqual(
            switches.parameters_load(self.root), gold_value("parameters")
        )

    # A second making replaces what it makes and keeps the rest of the root.
    def test_rest_kept(self) -> None:
        self.root_ready(False)
        database, stale = self.run_earlier()
        parameters = gold_value("parameters_other")
        xsjs_serve.root_make(
            self.values, self.page, self.root, parameters, False
        )
        with open(database, encoding="utf-8") as file:
            self.assertEqual(file.read(), gold_value("database_text"))
        for path in stale:
            self.assertFalse(os.path.exists(path), path)
        self.assertEqual(switches.parameters_load(self.root), parameters)

    # A second making removes an earlier run's log and keeps the databases.
    def test_log_removed(self) -> None:
        self.root_ready(False)
        database, _ = self.run_earlier()
        names: list[str] = gold_value("verbose_names")
        logs = [os.path.join(self.root, name) for name in names]
        for path in logs:
            self.file_write(path, gold_value("verbose_text"))
        self.root_ready(False)
        for path in logs:
            self.assertFalse(os.path.exists(path), path)
        with open(database, encoding="utf-8") as file:
            self.assertEqual(file.read(), gold_value("database_text"))

    # Fresh removes the whole root first, what the making keeps included.
    def test_fresh_removed(self) -> None:
        self.root_ready(False)
        database, _ = self.run_earlier()
        self.root_ready(True)
        self.assertFalse(os.path.exists(database), database)
        self.assertEqual(
            switches.parameters_load(self.root), gold_value("parameters")
        )

    # Fresh on a root that is not there yet makes it all the same.
    def test_fresh_absent(self) -> None:
        self.root_ready(True)
        self.assertEqual(
            switches.parameters_load(self.root), gold_value("parameters")
        )


# The built ttyd on a root of the test's page, serving port 0.
class TestServer(ScratchCase):
    # Makes the root and names the address ttyd binds.
    def setUp(self) -> None:
        super().setUp()
        self.root_ready(False)
        self.host: str = self.values["powershell"]["bind_address"]

    # Starts ttyd, killed at the test's end if the test left it running.
    def server_start(self) -> xsjs_serve.TtydServer:
        server = xsjs_serve.TtydServer(self.values, self.root, 0)
        self.addCleanup(group_kill, server.pid)
        return server

    # Blocks the signals as the program does, for this test alone.
    def signals_block(self) -> None:
        saved = signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
        self.addCleanup(signal.pthread_sigmask, signal.SIG_SETMASK, saved)

    # ttyd serves the port its log names, alone in a session, until its stop.
    def test_port_served(self) -> None:
        server = self.server_start()
        self.assertGreater(server.port, 0)
        self.assertEqual(os.getsid(server.pid), server.pid)
        self.assertEqual(
            server.address_get(),
            gold_value("address_text").format(server.port),
        )
        with socket.create_connection((self.host, server.port)):
            pass
        self.assertEqual(server.server_stop(), gold_value("stopped_code"))
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection((self.host, server.port))
        with self.assertRaises(ProcessLookupError):
            os.killpg(server.pid, 0)

    # ttyd's log reaches stderr, up to its port's line and after it.
    def test_log_copied(self) -> None:
        server = self.server_start()
        port = server.port
        self.assertIn(gold_value("log_port").format(port), self.log_read())
        server.server_stop()
        self.assertIn(gold_value("log_stop"), self.log_read())

    # A ttyd not built is refused, naming where it should be.
    def test_ttyd_missing(self) -> None:
        self.values["powershell"]["ttyd_build"] = self.scratch
        with self.assertRaises(FileNotFoundError) as caught:
            xsjs_serve.TtydServer(self.values, self.root, 0)
        path = os.path.join(self.scratch, _TTYD_NAME)
        self.assertEqual(
            str(caught.exception), gold_value("text_missing").format(path)
        )

    # A ttyd that ends before it listens raises with its code, its log shown.
    def test_start_ended(self) -> None:
        os.remove(
            os.path.join(self.root, self.values["powershell"]["engine_page"])
        )
        with self.assertRaises(RuntimeError) as caught:
            xsjs_serve.TtydServer(self.values, self.root, 0)
        self.assertEqual(
            str(caught.exception),
            gold_value("text_ended").format(
                gold_value("ended_code"), self.root
            ),
        )
        self.assertIn(gold_value("log_refused"), self.log_read())

    # Either signal ends the wait, and ttyd, which never saw it blocked, stops.
    def test_wait_signal(self) -> None:
        for number in _STOP_SIGNALS:
            with self.subTest(number=number):
                self.signals_block()
                server = self.server_start()
                os.kill(os.getpid(), number)
                server.signal_wait()
                self.assertEqual(
                    server.server_stop(), gold_value("stopped_code")
                )

    # The wait ends at ttyd's end, and the stop then raises with its code.
    def test_wait_ended(self) -> None:
        self.signals_block()
        server = self.server_start()
        os.kill(server.pid, signal.SIGKILL)
        server.signal_wait()
        with self.assertRaises(RuntimeError) as caught:
            server.server_stop()
        self.assertEqual(
            str(caught.exception),
            gold_value("text_ended").format(
                gold_value("killed_ended_code"), self.root
            ),
        )

    # A ttyd deaf to SIGTERM is killed past the wait, with a shell's code.
    def test_stop_killed(self) -> None:
        server = self.server_start()
        os.kill(server.pid, signal.SIGSTOP)
        os.waitid(os.P_PID, server.pid, os.WSTOPPED | os.WNOWAIT)
        self.assertEqual(server.server_stop(), gold_value("killed_code"))


# The program whole, in a forked child, as its own line runs it.
class ProgramCase(ScratchCase):
    # Names the address ttyd binds.
    def setUp(self) -> None:
        super().setUp()
        self.host: str = self.values["powershell"]["bind_address"]

    # Forks the program, returning its pid and the read end of its stdout.
    def program_start(self, arguments: list[str]) -> tuple[int, int]:
        reader, writer = os.pipe()
        pid = os.fork()
        if pid == 0:
            program_child(writer, arguments)
        os.close(writer)
        self.addCleanup(child_stop, pid)
        return pid, reader

    # Returns the port of the address it printed, which takes a connection.
    def port_read(self, reader: int) -> int:
        with os.fdopen(reader, encoding="utf-8") as output:
            address = output.readline()
        found = re.fullmatch(gold_value("address_pattern"), address)
        if found is None:
            self.fail(f"{address!r}: {self.log_read()}")
        port = int(found.group(1))
        with socket.create_connection((self.host, port)):
            pass
        return port


# The program's own ends: its stop at a signal and its refusal.
class TestProgram(ProgramCase):
    # It builds the page, makes the root, prints the address, stops at SIGINT.
    def test_program_served(self) -> None:
        pid, reader = self.program_start(
            ["--debug", "--verbose", "--port", "0", "--root", self.root]
        )
        port = self.port_read(reader)
        os.kill(pid, signal.SIGINT)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(
            os.waitstatus_to_exitcode(status),
            gold_value("stopped_code"),
            self.log_read(),
        )
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection((self.host, port))
        page: str = self.values["powershell"]["engine_page"]
        self.files_same(
            os.path.join(_BUILD_PATH, page), os.path.join(self.root, page)
        )
        self.assertEqual(
            switches.parameters_load(self.root),
            {**switches.switches_get(), "debug": True, "verbose": True},
        )

    # An option the program does not hold ends it before anything is built.
    def test_option_refused(self) -> None:
        pid, reader = self.program_start(["--refused"])
        os.close(reader)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(
            os.waitstatus_to_exitcode(status), gold_value("usage_code")
        )
