# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of ttyd_build with the real archive, patches, patch, cmake and the
# compiler. First the run's build, which the driver's bring up made where
# settings.json says: checkout_build returns its ttyd and a second call
# changes no file there, ttyd --version writes the gold's line, and the
# patch's --srv-buf-size is taken with the settings' srv_buf_size and
# refused below 0. Then inputs_build into scratch directories under build/:
# a patch that does not apply raises naming patch and the log, its lines in
# the cause, leaving no record and no ttyd; and a build from no patches,
# whose ttyd names the option unrecognized, is built again from the
# project's patches, then left alone, then built again once its ttyd is
# removed. The option takes its value after =, since an unpatched ttyd
# takes a separate value as its start command and starts serving.

import harness, os, subprocess, tempfile, ttyd_build, unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# This suite's gold, the outputs of the programs it runs.
_GOLD_ID = "python.test_ttyd_build"

# The option of the project's patch, given with its value after `=`.
_SIZE_OPTION = "--srv-buf-size"

# The option that has ttyd write its version and exit.
_VERSION_OPTION = "--version"

# The program a build directory holds, as the stub names it.
_BINARY_NAME = "ttyd"

# The log of a build directory, as the stub names it.
_LOG_NAME = "build.log"

# The folder of a build directory that holds the source, as the stub names it.
_SOURCE_NAME = "source"

# A patch whose one hunk the source does not hold, a real fault.
_REFUSED_PATCH = (
    "--- a/CMakeLists.txt\n"
    "+++ b/CMakeLists.txt\n"
    "@@ -1 +1 @@\n"
    "-a line the source does not hold\n"
    "+a line in its place\n"
)

# The name of that patch in its scratch directory.
_REFUSED_NAME = "01_refused.patch"


# A value of this suite's gold.
def gold_value(name: str) -> object:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# The path from the checkout's top that the setting names.
def setting_path(name: str) -> str:
    return os.path.join(_ROOT_PATH, harness.setting_get(name))


# The argument that gives the patch's option the size.
def size_argument(size: object) -> str:
    return f"{_SIZE_OPTION}={size}"


# Runs the program with the arguments, returning its exit code and output.
def binary_run(path: str, *arguments: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        [path, *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


# The inode and modification time of each file and folder under the path.
def tree_stamps(path: str) -> dict[str, tuple[int, int]]:
    stamps: dict[str, tuple[int, int]] = {}
    for folder, names, files in os.walk(path):
        for name in names + files:
            stat = os.lstat(os.path.join(folder, name))
            stamps[os.path.join(folder, name)] = (
                stat.st_ino,
                stat.st_mtime_ns,
            )
    return stamps


# Tests of the run's build, made by the bring up where the settings say.
class TestCheckout(unittest.TestCase):
    # The path is the settings' build directory's, and a second call keeps it.
    def test_build_kept(self) -> None:
        build = setting_path("powershell.ttyd_build")
        path = ttyd_build.checkout_build()
        self.assertEqual(path, os.path.join(build, _BINARY_NAME))
        stamps = tree_stamps(build)
        self.assertEqual(ttyd_build.checkout_build(), path)
        self.assertEqual(tree_stamps(build), stamps)

    # The version option writes the gold's line and exits 0.
    def test_version_written(self) -> None:
        path = ttyd_build.checkout_build()
        result = binary_run(path, _VERSION_OPTION)
        self.assertEqual(result, (0, gold_value("version_text"), ""))

    # The patch's option takes the settings' size.
    def test_size_taken(self) -> None:
        path = ttyd_build.checkout_build()
        size = harness.setting_get("srv_buf_size")
        result = binary_run(path, size_argument(size), _VERSION_OPTION)
        self.assertEqual(result, (0, gold_value("version_text"), ""))

    # The patch's option refuses a size below 0 with its line.
    def test_size_refused(self) -> None:
        path = ttyd_build.checkout_build()
        size = gold_value("refused_size")
        result = binary_run(path, size_argument(size), _VERSION_OPTION)
        wanted = (gold_value("refused_code"), "", gold_value("refused_text"))
        self.assertEqual(result, wanted)


# Tests of builds from the inputs given, into a scratch directory each.
class TestInputs(unittest.TestCase):
    # Makes the scratch directory, and finds the archive and the patches.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.archive = setting_path("powershell.ttyd_archive")
        self.patches = setting_path("powershell.ttyd_patches")
        self.build = os.path.join(self.scratch, "build")

    # Makes a folder of the scratch directory holding the patches given.
    def patches_write(self, name: str, patches: dict[str, str]) -> str:
        path = os.path.join(self.scratch, name)
        os.mkdir(path)
        for patch, text in patches.items():
            with open(
                os.path.join(path, patch), "w", encoding="utf-8"
            ) as file:
                file.write(text)
        return path

    # A patch that does not apply raises naming it, the log's lines in cause.
    def test_patch_refused(self) -> None:
        refused = self.patches_write(
            "refused", {_REFUSED_NAME: _REFUSED_PATCH}
        )
        with self.assertRaises(RuntimeError) as context:
            ttyd_build.inputs_build(self.archive, refused, self.build)
        message = str(context.exception)
        log_path = os.path.join(self.build, _LOG_NAME)
        self.assertEqual(message.split()[0], "patch")
        self.assertIn(os.path.join(refused, _REFUSED_NAME), message)
        self.assertIn(f" {gold_value('patch_code')} ", message)
        self.assertIn(log_path, message)
        lines: list[str] = harness.gold_get(f"{_GOLD_ID}.patch_lines")
        cause = context.exception.__cause__
        self.assertIsInstance(cause, RuntimeError)
        self.assertEqual(str(cause), "\n".join(lines))
        with open(log_path, encoding="utf-8") as file:
            self.assertEqual(
                file.read(), "".join(f"{line}\n" for line in lines)
            )
        self.assertEqual(
            sorted(os.listdir(self.build)), [_LOG_NAME, _SOURCE_NAME]
        )

    # Other patches build again, the same are kept, a removed ttyd is built.
    def test_inputs_changed(self) -> None:
        empty = self.patches_write("empty", {})
        size = harness.setting_get("srv_buf_size")
        argument = size_argument(size)
        version = gold_value("version_text")
        path = ttyd_build.inputs_build(self.archive, empty, self.build)
        self.assertEqual(path, os.path.join(self.build, _BINARY_NAME))
        refused = str(gold_value("unrecognized_text")).format(path, argument)
        self.assertEqual(
            binary_run(path, argument, _VERSION_OPTION), (0, version, refused)
        )
        built = ttyd_build.inputs_build(self.archive, self.patches, self.build)
        self.assertEqual(built, path)
        self.assertEqual(
            binary_run(path, argument, _VERSION_OPTION), (0, version, "")
        )
        stamps = tree_stamps(self.build)
        kept = ttyd_build.inputs_build(self.archive, self.patches, self.build)
        self.assertEqual(kept, path)
        self.assertEqual(tree_stamps(self.build), stamps)
        os.remove(path)
        again = ttyd_build.inputs_build(self.archive, self.patches, self.build)
        self.assertEqual(again, path)
        self.assertEqual(
            binary_run(path, argument, _VERSION_OPTION), (0, version, "")
        )
