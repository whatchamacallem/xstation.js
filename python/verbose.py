# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The shell's runner, the one place the engine starts an external program. Its
# levels are the only verbose levels the server has, and its input and output
# pass through at every level. At levels 1 and 2 the start and the end of the
# program are notes of console in the root's audit, as the console role, the
# one role that runs a shell, runs in debug mode alone, and at level 2 the
# verbose command line runs. `console_note` writes such a note, for the console
# role's own failure too, as its `error` line goes to tty 0 and no line of the
# audit holds it. It depends on no other engine module but the audit and the
# strings.

import audit, shlex, subprocess, sys, time
from internationalization import i18n

# The highest level of the runner, the one that runs the verbose command line.
_LEVEL_MAX = 2

# The thread of the audit's notes of the console role.
_CONSOLE_THREAD = "console"

# How many nanoseconds the clock counts in a millisecond.
_NANOSECONDS_PER_MILLISECOND = 1_000_000


# Raises unless the runner's level is 0, 1 or 2.
def _level_check(level: int) -> None:
    if not 0 <= level <= _LEVEL_MAX:
        raise ValueError(i18n("verbose.level_invalid", level, _LEVEL_MAX))


# Writes a note of console in the audit.
def console_note(text: str) -> None:
    at = time.time_ns() // _NANOSECONDS_PER_MILLISECOND
    audit.note_put(_CONSOLE_THREAD, at, text)


# Runs the program on this process's input and output, after a flush of both.
def _run_through(argv: list[str]) -> int:
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(argv).returncode


# Runs the program passed through, its start and its exit noted.
def _run_noted(argv: list[str]) -> int:
    command = shlex.join(argv)
    console_note(i18n("verbose.exec_run", command))
    code = _run_through(argv)
    console_note(i18n("verbose.exec_exit", command, code))
    return code


# Runs `argv`, or `argv_verbose` at level 2, the one place a program starts.
def exec(level: int, argv: list[str], argv_verbose: list[str]) -> int:
    _level_check(level)
    if level == 0:
        return _run_through(argv)
    if level == 1:
        return _run_noted(argv)
    return _run_noted(argv_verbose)
