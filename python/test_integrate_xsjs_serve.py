# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests xsjs_serve.py as a program, as a person starts it, on a root in a
# scratch directory under build/: it builds the engine page with the real tsc,
# makes the root and serves it on port 0 through the ttyd the driver's bring up
# built. Its stdout holds ttyd's log and the address once ttyd names its port,
# and ttyd answers that address's token request as it answers the page. SIGTERM
# then ends ttyd and the program, whose exit code is ttyd's, with nothing on
# its stderr. No page is opened, so no bootstrap.py runs.

import harness, http.client, json, os, re, signal, socket, subprocess, sys
import tempfile, unittest
from typing import Any, IO, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The program under test.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "xsjs_serve.py")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_integrate_xsjs_serve"


# A value of this suite's gold.
def gold_value(name: str) -> Any:
    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Returns the status and the JSON body of ttyd's answer to the token request.
def token_fetch(port: int) -> tuple[int, object]:
    connection = http.client.HTTPConnection("localhost", port)
    try:
        connection.request("GET", gold_value("token_path"))
        reply = connection.getresponse()
        return reply.status, json.loads(reply.read())
    finally:
        connection.close()


# Reads the program's stdout to its address. Returns what it read and the port.
def address_read(process: subprocess.Popen[str]) -> tuple[str, int]:
    printed = ""
    while line := cast(IO[str], process.stdout).readline():
        printed += line
        found = re.fullmatch(gold_value("address_pattern"), line)
        if found is not None:
            return printed, int(found.group(1))
    raise AssertionError(f"{printed!r}: {process.communicate()[1]}")


# The program on a scratch root, serving port 0.
class TestProgram(unittest.TestCase):
    # Makes the scratch directory and names the root in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.root = os.path.join(scratch, "root")

    # The program serves, ttyd gives its token, and SIGTERM stops them both.
    def test_token_fetched(self) -> None:
        with subprocess.Popen(
            [
                sys.executable,
                _PROGRAM_PATH,
                "--port",
                "0",
                "--root",
                self.root,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as process:
            try:
                printed, port = address_read(process)
                status, body = token_fetch(port)
                process.send_signal(signal.SIGTERM)
                rest, errors = process.communicate()
            except BaseException:
                process.terminate()
                raise
        self.assertEqual(status, gold_value("token_status"))
        self.assertEqual(body, gold_value("token_reply"))
        self.assertEqual(
            process.returncode, gold_value("stopped_code"), errors
        )
        self.assertEqual(errors, "")
        self.assertIn(gold_value("log_port").format(port), printed)
        self.assertIn(gold_value("log_stop"), rest)
        host: str = harness.setting_get("powershell.bind_address")
        with self.assertRaises(ConnectionRefusedError):
            socket.create_connection((host, port))
