#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Fetches the pinned third party files into the checkout's third_party
# directory with urllib, each to its library's directory, made when missing.
# The SHA-256 of each download is checked before the file is moved into
# place, and a file already there with the right digest is left alone. The
# test driver calls pins_fetch before each run:
#
#     python3 python/third_party_fetch.py [--anthropic] [--debug] [--verbose]
#
# With the switch anthropic, in Anthropic's cloud container, ttyd's pin is
# replaced by the archive Ubuntu's package manager places, the upstream
# archive of the source package ttyd 1.7.7-4build1, whose tree is the pin's:
# it is checked by its own digest and never fetched, and a missing one fails
# naming the command that places it. Python runs no package manager.

import argparse, hashlib, os, re, sys, tempfile, urllib.request

# The checkout's top directory.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where a download waits, checked, until it is moved into place.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# A sha256 digest: 64 lowercase hex characters.
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")

# The pinned files: path in `third_party/`, URL and `sha256sum` of the bytes.
_PINS: tuple[tuple[str, str, str], ...] = (
    (
        "ttyd/ttyd-1.7.7.tar.gz",
        "https://github.com/tsl0922/ttyd/archive/refs/tags/1.7.7.tar.gz",
        "039dd995229377caee919898b7bd54484accec3bba49c118e2d5cd6ec51e3650",
    ),
    (
        "sqlite/sqlite-wasm-3460100.zip",
        "https://sqlite.org/2024/sqlite-wasm-3460100.zip",
        "79b5fbfd1c5ca35f492624bb6b9323e6c74e483e2a55ff18ce5904a8cdb1b38c",
    ),
    (
        "xterm/xterm-5.5.0.tgz",
        "https://registry.npmjs.org/@xterm/xterm/-/xterm-5.5.0.tgz",
        "bd954fa721872170188cc5d7e83e88db3c83c9a18a4e8d24c2783d26491f59d2",
    ),
)

# The package manager's file for ttyd's pin: path, command and digest.
_PACKAGE_PIN = (
    "ttyd/ttyd_1.7.7.orig.tar.xz",
    "apt-get source --download-only ttyd=1.7.7-4build1",
    "48eba3f76af237f4c09cceb5ddbe0f845832557819f7e5c60c88285f8822af88",
)

# The path in `third_party/` of the pin that `_PACKAGE_PIN` replaces.
_PACKAGE_REPLACED = "ttyd/ttyd-1.7.7.tar.gz"

# Where the package manager's sources hold ttyd `1.7.7-4build1`.
_PACKAGE_SOURCE = "a deb-src entry of Ubuntu resolute's universe"

# Seconds a connect or a read may stall, a default chosen by its writer.
_SOCKET_SECONDS = 60.0

# Where the fetched files go.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# Bytecode of the modules the functions below import goes in `build/pycache`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# Returns the path of the name, fetching it unless it has the sha256 now.
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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.makedirs(_BUILD_PATH, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
        scratch_path = os.path.join(scratch, os.path.basename(path))
        with open(scratch_path, "wb") as file:
            file.write(data)
        os.replace(scratch_path, path)
    return path


# Returns the path of the package manager's file, checked by its digest.
def package_check(name: str, command: str, sha256: str) -> str:
    path = os.path.join(_THIRD_PARTY_PATH, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name}: absent; the package manager places it in"
            f" {os.path.dirname(path)} by `{command}`, with {_PACKAGE_SOURCE}"
        )
    with open(path, "rb") as file:
        actual = hashlib.file_digest(file, "sha256").hexdigest()
    if actual != sha256:
        raise ValueError(f"{name}: sha256 {actual}, expected {sha256}")
    return path


# Returns the path of ttyd's archive from the package manager.
def package_path() -> str:
    return os.path.join(_THIRD_PARTY_PATH, _PACKAGE_PIN[0])


# Returns the paths of the pinned files, fetched to the first failure.
def pins_fetch() -> list[str]:
    import switches

    paths: list[str] = []
    for name, url, sha256 in _PINS:
        packaged = switches.anthropic and name == _PACKAGE_REPLACED
        if packaged:
            paths.append(package_check(*_PACKAGE_PIN))
        else:
            paths.append(file_fetch(url, sha256, name))
    return paths


# Fetches every pinned file from the command line, printing nothing.
def main() -> None:
    import switches

    parser = argparse.ArgumentParser(
        description="Fetch the pinned third party files into third_party/."
    )
    switches.options_add(parser)
    switches.switches_set(parser.parse_args())
    pins_fetch()


if __name__ == "__main__":
    main()
