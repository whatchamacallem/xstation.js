#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Formats the files that reformat_whitelist.txt's lines match, from the
# project's top directory, each with the formatter that reformat_table.json
# gives its extension: Python with ruff, at the 79 columns pyproject.toml
# sets, shell with shfmt, and TypeScript, JavaScript and HTML with prettier,
# at 79 columns given on its command line and no configuration file. A check
# runs each row's checker in place of its formatter, ruff format --check,
# shfmt --diff and prettier --check, and rewrites nothing. It formats the
# table's linux rows; powershell/test_lint.ps1 formats its windows rows, the
# PowerShell files, on Windows. A whitelist line is a path from the top with
# * or ? in its last part only, and matches at least one file and no
# directory.

import argparse, fnmatch, json, os, re, subprocess
from typing import Any, NamedTuple

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

_ROOT_PATH = os.path.dirname(_PYTHON_PATH)

# The system whose rows this script formats, `test_lint.ps1` the others.
_SYSTEM = "linux"

# What handles each extension of the whitelisted files.
_TABLE_PATH = os.path.join(_PYTHON_PATH, "reformat_table.json")

# A whitelist line: a path from the top, with `*` or `?` in its last part only.
_WHITELIST_LINE = re.compile(r"(?:[^*?\[\]`/]+/)*[^\[\]`/]+")

_WHITELIST_PATH = os.path.join(_PYTHON_PATH, "reformat_whitelist.txt")


# What handles the whitelisted files of one extension, a row of the table.
class FileType(NamedTuple):
    checker: list[str]
    comments: str
    encoding: str
    formatter: list[str]
    linter: list[str]
    system: str


# Runs each checker of this system once over its files, rewriting nothing.
def format_check(paths: list[str]) -> None:
    _commands_run(paths, True)


# Returns the files the whitelist lines match under the root, sorted.
def paths_match(root_path: str, patterns: list[str]) -> list[str]:
    paths: set[str] = set()
    for pattern in patterns:
        if not _WHITELIST_LINE.fullmatch(pattern):
            raise RuntimeError(
                f"whitelist line {pattern!r} is not a path with * or ? in"
                " its last part only"
            )
        directory, _, leaf = pattern.rpartition("/")
        directory_path = os.path.join(root_path, directory)
        names: list[str] = []
        if os.path.isdir(directory_path):
            names = os.listdir(directory_path)
        matched = [
            name
            for name in sorted(names)
            if fnmatch.fnmatchcase(name, leaf)
            and (leaf.startswith(".") or not name.startswith("."))
        ]
        if not matched:
            raise RuntimeError(
                f"whitelist line {pattern!r} matches nothing under {root_path}"
            )
        for name in matched:
            relative = os.path.join(directory, name)
            path = os.path.join(root_path, relative)
            if not os.path.isfile(path):
                raise RuntimeError(
                    f"whitelist line {pattern!r} matches {relative!r}, which"
                    " is not a file"
                )
            paths.add(path)
    return sorted(paths)


# Runs each formatter of this system once over its files.
def reformat(paths: list[str]) -> None:
    _commands_run(paths, False)


# Returns the table's rows by extension, each with exactly the six keys.
def table_read() -> dict[str, FileType]:
    with open(_TABLE_PATH, encoding="utf-8") as table_file:
        table: dict[str, dict[str, Any]] = json.load(table_file)
    return {extension: FileType(**row) for extension, row in table.items()}


# Returns the row of the file's extension, failing when it has none.
def type_find(table: dict[str, FileType], path: str) -> FileType:
    extension = os.path.splitext(path)[1]
    if extension not in table:
        raise RuntimeError(
            f"{path}: no row for {extension!r} in {_TABLE_PATH}"
        )
    return table[extension]


# Returns the files the whitelist's lines match from the top, sorted.
def whitelist_paths() -> list[str]:
    with open(_WHITELIST_PATH, encoding="utf-8") as whitelist_file:
        patterns = whitelist_file.read().splitlines()
    return paths_match(_ROOT_PATH, patterns)


# Runs the checker or the formatter of each row of this system on its files.
def _commands_run(paths: list[str], check: bool) -> None:
    table = table_read()
    # A file whose extension has no row fails before any command runs.
    for path in paths:
        type_find(table, path)
    for extension, row in table.items():
        matched = [
            path for path in paths if os.path.splitext(path)[1] == extension
        ]
        command = row.checker if check else row.formatter
        # With no files, ruff formats the directory and shfmt reads stdin.
        if matched and row.system == _SYSTEM:
            subprocess.run([*command, *matched], check=True, cwd=_ROOT_PATH)


# Formats the whitelisted files.
def main() -> None:
    argparse.ArgumentParser(
        description="Format the whitelisted files of the linux rows of"
        " reformat_table.json."
    ).parse_args()
    reformat(whitelist_paths())


if __name__ == "__main__":
    main()
