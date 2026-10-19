#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Fetches the pinned third party files into the checkout's third_party
# directory with urllib. The SHA-256 of each download is checked before the
# file is moved into place, and a file already there with the right digest is
# left alone:
#
#     python3 python/third_party_fetch.py

import argparse, hashlib, os, re, tempfile, urllib.request
from typing import NamedTuple

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where a download waits, checked, until it is moved into place.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# A sha256 digest: 64 lowercase hex characters.
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")

# Where the fetched files go.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")


# A pinned file: its name in `third_party/`, its URL and its sha256.
class _PinEntry(NamedTuple):
    name: str
    url: str
    sha256: str


# The pinned files: name in `third_party/`, URL and `sha256sum` of the bytes.
_PINS: tuple[_PinEntry, ...] = (
    _PinEntry(
        name="ttyd-1.7.7.tar.gz",
        url="https://github.com/tsl0922/ttyd/archive/refs/tags/1.7.7.tar.gz",
        sha256="",
    ),
    _PinEntry(
        name="sqlite-wasm-3460100.zip",
        url="https://sqlite.org/2024/sqlite-wasm-3460100.zip",
        sha256="",
    ),
    _PinEntry(
        name="xterm-5.5.0.tgz",
        url="https://registry.npmjs.org/@xterm/xterm/-/xterm-5.5.0.tgz",
        sha256="",
    ),
)


# Returns the path of the file, fetching it unless it has the sha256 now.
def file_fetch(url: str, sha256: str, name: str) -> str:
    if not _DIGEST_PATTERN.fullmatch(sha256):
        raise ValueError(
            f"{name}: sha256 {sha256!r} is not 64 lowercase hex characters"
        )
    path = os.path.join(_THIRD_PARTY_PATH, name)
    if os.path.exists(path):
        with open(path, "rb") as file:
            if hashlib.file_digest(file, "sha256").hexdigest() == sha256:
                return path
    with urllib.request.urlopen(url) as response:
        data: bytes = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise ValueError(
            f"{name}: {url} has sha256 {actual}, expected {sha256}"
        )
    os.makedirs(_THIRD_PARTY_PATH, exist_ok=True)
    os.makedirs(_BUILD_PATH, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
        scratch_path = os.path.join(scratch, name)
        with open(scratch_path, "wb") as file:
            file.write(data)
        os.replace(scratch_path, path)
    return path


# Fetches every pinned file, stopping at the first failure.
def main() -> None:
    argparse.ArgumentParser(
        description="Fetch the pinned third party files into third_party/."
    ).parse_args()
    for pin in _PINS:
        file_fetch(pin.url, pin.sha256, pin.name)


if __name__ == "__main__":
    main()
