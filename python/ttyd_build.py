# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Builds ttyd from the pinned source archive and the project's patches by the
# steps of xsjs_install.ps1's ttyd build, for the test driver's bring up.
# checkout_build reads powershell.ttyd_archive, powershell.ttyd_patches and
# powershell.ttyd_build of settings.json, paths from the checkout's top, and
# hands them to inputs_build. A build directory holds the record inputs.json,
# the SHA-256 of the archive, then the name and SHA-256 of each patch in the
# order they apply; one whose ttyd is present and whose record's bytes equal
# those the inputs give now is left alone, with no program started. Every
# other call builds from the archive, as a patch applies only once: the build
# directory is removed, the archive unpacked by tarfile into its source/ with
# the first component of each path stripped, each *.patch applied in name
# order with patch -p1, then cmake -S, with git's package disabled so that
# cmake starts no git, and cmake --build run and the built ttyd --version,
# and the record written last, so that a failed build leaves none. Python
# starts patch, cmake and the built ttyd, and nothing else. Each program's
# stdin is /dev/null and its stdout and stderr go to build.log in
# the build directory, which the program writes itself, so nothing reaches
# stdout, the driver's TAP stream, and a hard exit loses no line of the log.
# A program that exits other than 0 raises naming its command line, its exit
# code and the log, the log's last lines in the cause. No program has a time
# limit, since the build is outside every limit of the run.

import hashlib, json, os, settings, shlex, shutil, subprocess, tarfile
from typing import IO

# The public names of this module, as its stub declares them.
__all__ = ["checkout_build", "inputs_build"]

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The settings, which name the archive, the patches and the build directory.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# The folder of a build directory that the archive is unpacked into.
_SOURCE_NAME = "source"

# The program cmake builds, in the build directory.
_BINARY_NAME = "ttyd"

# The record of the inputs of the build, in a build directory.
_RECORD_NAME = "inputs.json"

# The log of the programs' output, in a build directory.
_LOG_NAME = "build.log"

# The end of the name of each patch applied.
_PATCH_SUFFIX = ".patch"

# Keeps cmake from starting git, whose `git describe` reads the enclosing tree.
_GIT_OPTION = "-DCMAKE_DISABLE_FIND_PACKAGE_Git=TRUE"

# The lines of the log an error carries, a default chosen by its writer.
_TAIL_LINES = 20


# Unpacks the gzipped tar into the folder, cutting each path's first part.
def archive_unpack(archive_path: str, source_path: str) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        members: list[tarfile.TarInfo] = []
        for member in archive.getmembers():
            _, _, rest = member.name.partition("/")
            # The top folder itself has no path left, as with `tar`.
            if rest:
                members.append(member.replace(name=rest, deep=False))
        archive.extractall(source_path, members=members, filter="data")


# Builds ttyd where `settings.json` says, returning the path of its `ttyd`.
def checkout_build() -> str:
    loaded = settings.settings_load(_SETTINGS_PATH)["powershell"]
    return inputs_build(
        os.path.join(_ROOT_PATH, loaded["ttyd_archive"]),
        os.path.join(_ROOT_PATH, loaded["ttyd_patches"]),
        os.path.join(_ROOT_PATH, loaded["ttyd_build"]),
    )


# Returns the `SHA-256` hex of the file's bytes.
def file_digest(path: str) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


# Builds ttyd from the inputs unless built from them, returning its path.
def inputs_build(archive_path: str, patches_path: str, build_path: str) -> str:
    # Absolute, since `patch -d` enters the source before it opens the patch.
    build_path = os.path.abspath(build_path)
    patches = [
        os.path.join(os.path.abspath(patches_path), name)
        for name in sorted(os.listdir(patches_path))
        if name.endswith(_PATCH_SUFFIX)
    ]
    record = record_text(archive_path, patches)
    binary_path = os.path.join(build_path, _BINARY_NAME)
    record_path = os.path.join(build_path, _RECORD_NAME)
    if os.path.exists(binary_path) and os.path.exists(record_path):
        with open(record_path, "rb") as file:
            if file.read() == record:
                return binary_path
    # A patch applies only once, so every build starts from the archive.
    if os.path.exists(build_path):
        shutil.rmtree(build_path)
    source_path = os.path.join(build_path, _SOURCE_NAME)
    os.makedirs(source_path)
    log_path = os.path.join(build_path, _LOG_NAME)
    with open(log_path, "xb", buffering=0) as log:
        archive_unpack(archive_path, source_path)
        for patch in patches:
            program_run(
                ["patch", "-p1", "-d", source_path, "-i", patch], log, log_path
            )
        program_run(
            ["cmake", "-S", source_path, "-B", build_path, _GIT_OPTION],
            log,
            log_path,
        )
        program_run(["cmake", "--build", build_path], log, log_path)
        program_run([binary_path, "--version"], log, log_path)
    with open(record_path, "xb") as file:
        file.write(record)
    return binary_path


# Runs the command, its output to the log, raising unless it exits 0.
def program_run(command: list[str], log: IO[bytes], log_path: str) -> None:
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        with open(log_path, "rb") as file:
            lines = file.read().decode("utf-8", "replace").splitlines()
        raise RuntimeError(
            f"{shlex.join(command)} exited with {completed.returncode}"
            f" building ttyd, its output in {log_path}"
        ) from RuntimeError("\n".join(lines[-_TAIL_LINES:]))


# The record's bytes: the archive's `SHA-256`, then each patch's name and hex.
def record_text(archive_path: str, patches: list[str]) -> bytes:
    record = {
        "archive": file_digest(archive_path),
        "patches": [
            [os.path.basename(patch), file_digest(patch)] for patch in patches
        ],
    }
    return (json.dumps(record, indent=2) + "\n").encode("utf-8")
