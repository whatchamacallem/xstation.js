#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Formats the files reformat_whitelist.txt's shell globs match, from the
# project's top directory: Python with ruff, at the 79 columns
# pyproject.toml sets, and shell with shfmt. Markdown is checked with
# mdformat, not rewritten.

from __future__ import annotations

import argparse
import glob
import os
import subprocess

_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

_ROOT_PATH = os.path.dirname(_PYTHON_PATH)

_RUFF_CACHE_PATH = os.path.join(_ROOT_PATH, "build", "ruff_cache")

# The formatter command for each extension. Other files have none.
_FORMATTERS: dict[str, list[str]] = {
    ".md": ["mdformat", "--check"],
    ".py": ["ruff", "format", "--cache-dir", _RUFF_CACHE_PATH],
    ".sh": ["shfmt", "--list", "--write"],
}

_WHITELIST_PATH = os.path.join(_PYTHON_PATH, "reformat_whitelist.txt")


# Runs each formatter once over its files.
def reformat(paths: list[str]) -> None:
    for extension, command in _FORMATTERS.items():
        matched = [path for path in paths if path.endswith(extension)]
        # With no files, ruff formats the directory and shfmt reads stdin.
        if matched:
            subprocess.run(command + matched, check=True, cwd=_ROOT_PATH)


# Returns the files the whitelist's globs match from the top, sorted.
def whitelist_paths() -> list[str]:
    with open(_WHITELIST_PATH, encoding="utf-8") as whitelist_file:
        patterns = whitelist_file.read().splitlines()
    paths: set[str] = set()
    for pattern in patterns:
        matched = glob.glob(pattern, root_dir=_ROOT_PATH)
        if not matched:
            raise RuntimeError(
                f"{_WHITELIST_PATH}: {pattern!r} matches nothing"
            )
        paths.update(os.path.join(_ROOT_PATH, path) for path in matched)
    return sorted(paths)


# Formats the whitelisted files.
def main() -> None:
    argparse.ArgumentParser(
        description="Format the files reformat_whitelist.txt lists."
    ).parse_args()
    reformat(whitelist_paths())


if __name__ == "__main__":
    main()
