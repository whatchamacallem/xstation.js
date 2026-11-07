# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of third_party_fetch: `file_fetch` against file URLs of a scratch
# directory under build/, into the real third_party/ in a library directory
# no pin uses, which git ignores as it ignores the pins. Each file a test
# puts there is removed when the test ends, and the directory with it. Then
# `pins_fetch` on the pins already in place, the gold's paths and digests.
# Then the file as the program `xsjs_install.ps1` starts, run in a forked
# child, whose lines of the file the line counter counts.

import contextlib, harness, hashlib, io, os, pathlib, runpy, signal, switches
import sys, tempfile, third_party_fetch, traceback, unittest

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The directory the fetched files go to.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The library directory of every name a test fetches, which no pin uses.
_LIBRARY_NAME = "test_third_party_fetch"

# The gold's pins, each its path in `third_party/` and its sha256, in order.
_PINS_ID = "python.test_third_party_fetch.pins"

# A command that places a file, which `package_check` names when it is absent.
_PACKAGE_COMMAND = "apt-get source --download-only test-package=1.0-1"

# The gold id of the pins with ttyd's from the package manager, by switch.
_PINS_ANTHROPIC_ID = "python.test_third_party_fetch.pins_anthropic"

# The gold id of the command that places ttyd's file from the package manager.
_PACKAGE_COMMAND_ID = "python.test_third_party_fetch.package_command"

# The file `xsjs_install.ps1` starts as a program.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "third_party_fetch.py")

# What a forked child sends when the program returned, before what it printed.
_ENDING_RETURNED = "returned"


# Returns the name in the scratch library of the file name.
def name_make(file_name: str) -> str:
    return _LIBRARY_NAME + "/" + file_name


# In the forked child: the program run, its ending sent, then a kill.
def _child_main(argv: list[str], write_fd: int) -> None:
    try:
        try:
            sys.argv = [_PROGRAM_PATH, *argv]
            shown = io.StringIO()
            with contextlib.redirect_stdout(shown):
                runpy.run_path(_PROGRAM_PATH, run_name="__main__")
            ending = _ENDING_RETURNED + shown.getvalue()
        except BaseException:
            ending = traceback.format_exc()
        with open(write_fd, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# A test with a scratch source file and the scratch library of the target.
class LibraryCase(unittest.TestCase):
    # Makes the scratch directory that holds the source file.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.source_path = os.path.join(scratch, "source")
        self.library_path = os.path.join(_THIRD_PARTY_PATH, _LIBRARY_NAME)
        self.assertFalse(os.path.exists(self.library_path), self.library_path)

    # Writes the bytes to the source file and returns its file URL.
    def source_write(self, data: bytes) -> str:
        with open(self.source_path, "wb") as file:
            file.write(data)
        return pathlib.Path(self.source_path).as_uri()

    # Removes the file and the scratch library when the test ends.
    def removal_add(self, path: str) -> None:
        self.addCleanup(os.rmdir, self.library_path)
        self.addCleanup(os.remove, path)

    # Writes the bytes to a new file of the scratch library, removed after.
    def target_write(self, name: str, data: bytes) -> str:
        path = os.path.join(_THIRD_PARTY_PATH, name)
        os.mkdir(self.library_path)
        with open(path, "wb") as file:
            file.write(data)
        self.removal_add(path)
        return path


# Tests of `file_fetch` with a source file in scratch and the real target.
class TestFetch(LibraryCase):
    # An existing file with another digest is replaced by the fetched bytes.
    def test_existing_replaced(self) -> None:
        data = b"new bytes"
        name = name_make("old.bin")
        path = self.target_write(name, b"old bytes")
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, name)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # An existing file with the right digest is returned without a fetch.
    def test_existing_reused(self) -> None:
        data = b"kept bytes"
        name = name_make("kept.bin")
        path = self.target_write(name, data)
        missing = pathlib.Path(self.source_path).as_uri()
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(missing, digest, name)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A good digest makes the library, writes the bytes and returns the path.
    def test_good_digest(self) -> None:
        data = b"good bytes"
        name = name_make("good.bin")
        path = os.path.join(_THIRD_PARTY_PATH, name)
        url = self.source_write(data)
        digest = hashlib.sha256(data).hexdigest()
        fetched = third_party_fetch.file_fetch(url, digest, name)
        self.removal_add(path)
        self.assertEqual(fetched, path)
        with open(path, "rb") as file:
            self.assertEqual(file.read(), data)

    # A digest that is not 64 lowercase hex characters raises naming the pin.
    def test_malformed_digest(self) -> None:
        data = b"bytes"
        name = name_make("bad.bin")
        url = self.source_write(data)
        good = hashlib.sha256(data).hexdigest()
        malformed = (
            "",
            good[:63],
            good + "0",
            good + "\n",
            "A" * 64,
            "g" * 64,
        )
        for digest in malformed:
            with self.assertRaises(ValueError, msg=repr(digest)) as context:
                third_party_fetch.file_fetch(url, digest, name)
            self.assertIn(name, str(context.exception))
        self.assertFalse(os.path.exists(self.library_path))

    # A wrong digest raises naming both digests and leaves no file.
    def test_wrong_digest(self) -> None:
        name = name_make("wrong.bin")
        actual = hashlib.sha256(b"actual bytes").hexdigest()
        wanted = hashlib.sha256(b"wanted bytes").hexdigest()
        url = self.source_write(b"actual bytes")
        with self.assertRaises(ValueError) as context:
            third_party_fetch.file_fetch(url, wanted, name)
        self.assertIn(actual, str(context.exception))
        self.assertIn(wanted, str(context.exception))
        self.assertFalse(os.path.exists(self.library_path))


# Tests of `package_check` on files of the scratch library, and its path.
class TestPackage(LibraryCase):
    # A file there with its digest is returned, with no fetch.
    def test_package_placed(self) -> None:
        data = b"packaged bytes"
        name = name_make("packaged.tar.xz")
        path = self.target_write(name, data)
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(
            third_party_fetch.package_check(name, _PACKAGE_COMMAND, digest),
            path,
        )

    # An absent file is refused, naming the command that places it.
    def test_package_absent(self) -> None:
        name = name_make("absent.tar.xz")
        digest = hashlib.sha256(b"").hexdigest()
        with self.assertRaises(FileNotFoundError) as context:
            third_party_fetch.package_check(name, _PACKAGE_COMMAND, digest)
        self.assertIn(_PACKAGE_COMMAND, str(context.exception))

    # A file with another digest is refused, showing both digests.
    def test_package_wrong(self) -> None:
        name = name_make("wrong.tar.xz")
        self.target_write(name, b"other bytes")
        wanted = hashlib.sha256(b"packaged bytes").hexdigest()
        actual = hashlib.sha256(b"other bytes").hexdigest()
        with self.assertRaises(ValueError) as context:
            third_party_fetch.package_check(name, _PACKAGE_COMMAND, wanted)
        self.assertIn(actual, str(context.exception))
        self.assertIn(wanted, str(context.exception))

    # ttyd's archive from the package manager is the first of the gold's.
    def test_package_path(self) -> None:
        pins: list[list[str]] = harness.gold_get(_PINS_ANTHROPIC_ID)
        self.assertEqual(
            third_party_fetch.package_path(),
            os.path.join(_THIRD_PARTY_PATH, pins[0][0]),
        )


# Tests of `pins_fetch` on the pins, which the run fetched before its blocks.
class TestPins(unittest.TestCase):
    # Each pin is at its path with its digest, and a second fetch keeps it.
    def test_pins_placed(self) -> None:
        chosen = _PINS_ANTHROPIC_ID if switches.anthropic else _PINS_ID
        pins: list[list[str]] = harness.gold_get(chosen)
        paths = [os.path.join(_THIRD_PARTY_PATH, name) for name, _ in pins]
        self.assertEqual(third_party_fetch.pins_fetch(), paths)
        for path, (_, digest) in zip(paths, pins):
            with open(path, "rb") as file:
                actual = hashlib.file_digest(file, "sha256").hexdigest()
            self.assertEqual(actual, digest, path)
        stats = [os.stat(path) for path in paths]
        self.assertEqual(third_party_fetch.pins_fetch(), paths)
        for path, stat in zip(paths, stats):
            again = os.stat(path)
            self.assertEqual(
                (again.st_ino, again.st_mtime_ns),
                (stat.st_ino, stat.st_mtime_ns),
                path,
            )


# Tests of the file as a program, each run in a forked child.
class TestProgram(unittest.TestCase):
    # Runs the program with the options in a forked child, returns its ending.
    def program_run(self, argv: list[str]) -> str:
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            _child_main(argv, write_fd)
        os.close(write_fd)
        with open(read_fd, encoding="utf-8") as file:
            ending = file.read()
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
        return ending

    # With the pins in place the program returns and prints nothing.
    def test_program_placed(self) -> None:
        self.assertEqual(self.program_run([]), _ENDING_RETURNED)

    # With `--anthropic` ttyd's pin is the package manager's file, checked.
    def test_program_packaged(self) -> None:
        ending = self.program_run(["--anthropic"])
        if os.path.exists(third_party_fetch.package_path()):
            self.assertEqual(ending, _ENDING_RETURNED)
        else:
            command: str = harness.gold_get(_PACKAGE_COMMAND_ID)
            self.assertIn(command, ending)
