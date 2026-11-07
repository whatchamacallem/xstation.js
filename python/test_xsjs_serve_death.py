# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests that ttyd dies with xsjs_serve, on the forked program of
# test_xsjs_serve and a root in a scratch directory under build/, with the ttyd
# the driver's bring up built. Each test builds the page with the real tsc, so
# that this suite runs in a test-all run only. The program ended by SIGKILL, or
# by SIGHUP's default action, stops nothing itself, so that the port it printed
# going shows that the kernel told ttyd. The port is polled, not ttyd's pid, as
# an orphan may stay a zombie for a moment.

import harness, os, signal, socket, test_xsjs_serve, time

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_xsjs_serve_death"

# The seconds the port has to go, from the program's end.
_GONE_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.gone_seconds")

# The wait between two tries of the port.
_POLL_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.poll_seconds")


# The program ended with no chance to stop ttyd, which the kernel then ends.
class TestParentDeath(test_xsjs_serve.ProgramCase):
    # Returns once the port refuses a connection, failing past the gold's wait.
    def port_gone(self, port: int) -> None:
        end = time.monotonic() + _GONE_SECONDS
        while True:
            try:
                with socket.create_connection((self.host, port)):
                    pass
            except ConnectionRefusedError:
                return
            if time.monotonic() >= end:
                self.fail(f"port {port} still serves: {self.log_read()}")
            time.sleep(_POLL_SECONDS)

    # Ends the serving program by the signal, then waits for its port to go.
    def death_check(self, number: int) -> None:
        pid, reader = self.program_start(["--port", "0", "--root", self.root])
        port = self.port_read(reader)
        os.kill(pid, number)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -number)
        self.port_gone(port)

    # SIGKILL runs no line of the program, and ttyd ends all the same.
    def test_death_killed(self) -> None:
        self.death_check(signal.SIGKILL)

    # The program installs no hangup handler, so SIGHUP ends it as abruptly.
    def test_death_hangup(self) -> None:
        self.death_check(signal.SIGHUP)
