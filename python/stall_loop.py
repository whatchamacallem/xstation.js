# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# A main loop file whose loop_prepare never returns, so bootstrap.py never
# writes hello: a server that stays silent once its socket is open.
# bootstrap.py runs it from the root's main_loop directory when --main-loop
# names it in debug mode. Nothing here catches a signal, so the hangup ttyd
# sends when the socket closes ends the program.

import signal


# Sleeps until a signal, forever, so it never returns.
def loop_prepare(root: str) -> dict[str, int]:
    while True:
        signal.pause()


# Never runs, as loop_prepare never returns; bootstrap.py requires it.
def loop_run(read_fd: int, write_fd: int, root: str) -> None:
    raise RuntimeError(
        f"loop_run ran in {root}, though loop_prepare never returns"
    )
