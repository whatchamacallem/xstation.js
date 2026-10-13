#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Checks the whitelisted files are UTF-8 with no non-ASCII outside
# _NON_ASCII_ALLOWED, formats them with reformat.py, then lints the Python
# ones with ruff check.

from __future__ import annotations

import argparse
import subprocess

import reformat

# The non-ASCII characters the whitelisted files may hold.
_NON_ASCII_ALLOWED = {
    "\N{COPYRIGHT SIGN}",
    "\N{LATIN SMALL LETTER E WITH ACUTE}",
}


# Fails on the first non-ASCII character not in _NON_ASCII_ALLOWED.
def non_ascii_check(path: str) -> None:
    with open(path, "rb") as file:
        data = file.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"{path}: not UTF-8: {error}") from error
    for line_number, line in enumerate(text.split("\n"), 1):
        for column, character in enumerate(line, 1):
            if character.isascii() or character in _NON_ASCII_ALLOWED:
                continue
            raise RuntimeError(
                f"{path}:{line_number}:{column}: U+{ord(character):04X}"
                f" {character!r} isn't in _NON_ASCII_ALLOWED"
            )


def main() -> None:
    argparse.ArgumentParser(
        description="Check, format and lint the files"
        " reformat_whitelist.txt lists."
    ).parse_args()
    paths = reformat.whitelist_paths()
    for path in paths:
        non_ascii_check(path)
    reformat.reformat(paths)
    python_paths = [path for path in paths if path.endswith(".py")]
    # With no files, ruff checks the directory.
    if python_paths:
        subprocess.run(["ruff", "check", *python_paths], check=True)


if __name__ == "__main__":
    main()
