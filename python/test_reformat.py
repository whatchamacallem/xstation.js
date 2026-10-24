# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests of reformat's table, of the commands its check and its formatting
# start, with subprocess.run replaced so that none starts, and of its
# matching of whitelist lines, the matching on a scratch tree under build/,
# each refusal compared with its message.

import os, reformat, tempfile, unittest.mock

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The checkout's top directory, from which the whitelist's lines are paths.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The table that `reformat` reads, in its own directory.
_TABLE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(reformat.__file__)), "reformat_table.json"
)

# The files of each matching test's scratch tree, from its root.
_TREE_NAMES = ["x/a.py", "x/b.py", "x/.c.py", "x/d.txt", "top.sh"]

# The options of each ruff command of the table, its configuration and cache.
_RUFF_OPTIONS = [
    "--config",
    "python/pyproject.toml",
    "--cache-dir",
    "build/ruff_cache",
]

# A file of each extension the command tests give, PowerShell's run by none.
_COMMAND_PATHS = ["/a/b.py", "/a/b.sh", "/a/b.ts", "/a/b.ps1"]

# The commands a check starts on them, in the table's order, rewriting none.
_CHECK_COMMANDS = [
    ["ruff", "format", "--check", *_RUFF_OPTIONS, "/a/b.py"],
    ["shfmt", "--diff", "/a/b.sh"],
    ["prettier", "--check", "--no-config", "--print-width", "79", "/a/b.ts"],
]

# The commands a formatting starts on them, in the table's order.
_FORMAT_COMMANDS = [
    ["ruff", "format", *_RUFF_OPTIONS, "/a/b.py"],
    ["shfmt", "--list", "--write", "/a/b.sh"],
    ["prettier", "--write", "--no-config", "--print-width", "79", "/a/b.ts"],
]


# Writes an empty file at each path from the root, making its directories.
def tree_make(root: str, names: list[str]) -> None:
    for name in names:
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb"):
            pass


# The table's rows, and the row that a path's extension finds.
class TestTable(unittest.TestCase):
    # The table holds a row of the six fields for each whitelisted extension.
    def test_rows_read(self) -> None:
        table = reformat.table_read()
        self.assertEqual(
            sorted(table),
            [
                ".html",
                ".js",
                ".md",
                ".ps1",
                ".psd1",
                ".py",
                ".pyi",
                ".sh",
                ".ts",
            ],
        )
        for extension, row in table.items():
            self.assertIsInstance(row, reformat.FileType, extension)

    # The PowerShell rows are read as `utf-8-sig` and formatted on Windows.
    def test_windows_rows(self) -> None:
        table = reformat.table_read()
        expected = reformat.FileType(
            [], "powershell", "utf-8-sig", [], [], "windows"
        )
        for extension in (".ps1", ".psd1"):
            self.assertEqual(table[extension], expected, extension)

    # Every other row is read as `utf-8` and checked and formatted on Linux.
    def test_linux_rows(self) -> None:
        for extension, row in reformat.table_read().items():
            if extension not in (".ps1", ".psd1"):
                self.assertEqual(row.system, "linux", extension)
                self.assertEqual(row.encoding, "utf-8", extension)
                self.assertTrue(row.checker, extension)
                self.assertTrue(row.formatter, extension)

    # A path finds the row of its last extension.
    def test_row_found(self) -> None:
        table = reformat.table_read()
        self.assertIs(reformat.type_find(table, "/a/b.d.ts"), table[".ts"])

    # A path whose extension has no row, or that has none, is refused.
    def test_row_missing(self) -> None:
        table = reformat.table_read()
        for path, expected in (
            ("/a/b.txt", f"/a/b.txt: no row for '.txt' in {_TABLE_PATH}"),
            ("/a/Makefile", f"/a/Makefile: no row for '' in {_TABLE_PATH}"),
        ):
            with self.assertRaises(RuntimeError) as caught:
                reformat.type_find(table, path)
            self.assertEqual(caught.exception.args, (expected,), path)


# The commands each run starts, `subprocess.run` replaced so that none starts.
class TestCommands(unittest.TestCase):
    # A check starts each Linux row's checker on its files, rewriting none.
    def test_check_commands(self) -> None:
        with unittest.mock.patch("subprocess.run") as run:
            reformat.format_check(_COMMAND_PATHS)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list], _CHECK_COMMANDS
        )
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"check": True, "cwd": _ROOT_PATH})

    # A formatting starts each Linux row's formatter on its files.
    def test_format_commands(self) -> None:
        with unittest.mock.patch("subprocess.run") as run:
            reformat.reformat(_COMMAND_PATHS)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list], _FORMAT_COMMANDS
        )
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"check": True, "cwd": _ROOT_PATH})


# The matching of whitelist lines on a scratch tree, and each refusal.
class TestMatch(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch trees.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A `*` matches every name of its directory but the hidden ones.
    def test_glob_matched(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            self.assertEqual(
                reformat.paths_match(root, ["x/*.py"]),
                [os.path.join(root, "x/a.py"), os.path.join(root, "x/b.py")],
            )

    # A last part that starts with a dot matches the hidden names.
    def test_hidden_matched(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            self.assertEqual(
                reformat.paths_match(root, ["x/.*.py"]),
                [os.path.join(root, "x/.c.py")],
            )

    # A `?` matches one character.
    def test_question_matched(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            self.assertEqual(
                reformat.paths_match(root, ["x/?.py"]),
                [os.path.join(root, "x/a.py"), os.path.join(root, "x/b.py")],
            )

    # A literal line matches its file, and a file matched twice comes once.
    def test_literal_matched(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            self.assertEqual(
                reformat.paths_match(root, ["top.sh", "x/a.py", "x/*.py"]),
                [
                    os.path.join(root, "top.sh"),
                    os.path.join(root, "x/a.py"),
                    os.path.join(root, "x/b.py"),
                ],
            )

    # A line that matches no name is refused.
    def test_nothing_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            with self.assertRaises(RuntimeError) as caught:
                reformat.paths_match(root, ["x/*.sh"])
            expected = f"whitelist line 'x/*.sh' matches nothing under {root}"
            self.assertEqual(caught.exception.args, (expected,))

    # A line whose directory is missing is refused as matching nothing.
    def test_directory_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            with self.assertRaises(RuntimeError) as caught:
                reformat.paths_match(root, ["y/*.py"])
            expected = f"whitelist line 'y/*.py' matches nothing under {root}"
            self.assertEqual(caught.exception.args, (expected,))

    # A line that matches a directory is refused.
    def test_directory_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            os.makedirs(os.path.join(root, "x", "e.py"))
            with self.assertRaises(RuntimeError) as caught:
                reformat.paths_match(root, ["x/*.py"])
            expected = (
                "whitelist line 'x/*.py' matches 'x/e.py', which is not a file"
            )
            self.assertEqual(caught.exception.args, (expected,))

    # A name is matched with its case.
    def test_case_kept(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            with self.assertRaises(RuntimeError) as caught:
                reformat.paths_match(root, ["x/A.py"])
            expected = f"whitelist line 'x/A.py' matches nothing under {root}"
            self.assertEqual(caught.exception.args, (expected,))

    # A line that is not a path with wildcards in its last part is refused.
    def test_pattern_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as root:
            tree_make(root, _TREE_NAMES)
            for pattern in (
                "",
                "*/a.py",
                "x?/a.py",
                "x/[ab].py",
                "/x/a.py",
                "x//a.py",
                "x/a`.py",
            ):
                with self.assertRaises(RuntimeError) as caught:
                    reformat.paths_match(root, [pattern])
                expected = (
                    f"whitelist line {pattern!r} is not a path with * or ? in"
                    " its last part only"
                )
                self.assertEqual(caught.exception.args, (expected,), pattern)


# The checkout's whitelist and the table.
class TestWhitelist(unittest.TestCase):
    # The whitelist lists the eight PowerShell files.
    def test_powershell_listed(self) -> None:
        paths = reformat.whitelist_paths()
        for name in (
            "xsjs_install.ps1",
            "xsjs_start.ps1",
            "xsjs_status.ps1",
            "xsjs_stop.ps1",
            "powershell/test_lint.ps1",
            "powershell/test_powershell.ps1",
            "powershell/xsjs_util.ps1",
            "powershell/en-US/i18n.psd1",
        ):
            self.assertIn(os.path.join(_ROOT_PATH, name), paths)

    # Every whitelisted file has a row of the table.
    def test_rows_cover(self) -> None:
        table = reformat.table_read()
        for path in reformat.whitelist_paths():
            reformat.type_find(table, path)
