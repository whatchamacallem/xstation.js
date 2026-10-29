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

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where a download waits, checked, until it is moved into place.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# A sha256 digest: 64 lowercase hex characters.
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")

# The pinned files: name in `third_party/`, URL and `sha256sum` of the bytes.
_PINS: tuple[tuple[str, str, str], ...] = (
    (
        "ttyd-1.7.7.tar.gz",
        "https://github.com/tsl0922/ttyd/archive/refs/tags/1.7.7.tar.gz",
        "039dd995229377caee919898b7bd54484accec3bba49c118e2d5cd6ec51e3650",
    ),
    (
        "sqlite-wasm-3460100.zip",
        "https://sqlite.org/2024/sqlite-wasm-3460100.zip",
        "79b5fbfd1c5ca35f492624bb6b9323e6c74e483e2a55ff18ce5904a8cdb1b38c",
    ),
    (
        "xterm-5.5.0.tgz",
        "https://registry.npmjs.org/@xterm/xterm/-/xterm-5.5.0.tgz",
        "bd954fa721872170188cc5d7e83e88db3c83c9a18a4e8d24c2783d26491f59d2",
    ),
)

# Seconds a connect or a read may stall, a default chosen by its writer.
_SOCKET_SECONDS = 60.0

# Where the fetched files go.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")


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
    with urllib.request.urlopen(url, timeout=_SOCKET_SECONDS) as response:
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
    for name, url, sha256 in _PINS:
        file_fetch(url, sha256, name)


if __name__ == "__main__":
    main()
