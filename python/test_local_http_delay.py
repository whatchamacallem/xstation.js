# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the delayed answers of the local HTTP server, on the server and the
# script of test_local_http, the tests that wait out a delay of that script, so
# that this suite runs in a test-all run only: each delayed path answered with
# its status line as HTTP/1.0, exactly its headers and its body, to GET and to
# POST, and the delay slept while another request is answered.

import harness, http.client, select, socket, test_local_http, time
from typing import Any, cast

# The script the server of `test_local_http` answers, from that suite's gold.
_SCRIPT: dict[str, Any] = harness.gold_get("python.test_local_http.server")

# The host and the port of the script.
_HOST: str = _SCRIPT["host"]
_PORT: int = _SCRIPT["port"]

# The path of the script whose answer is delayed.
_SLOW_PATH = "/slow"

# The path of the script answered while the delayed one waits.
_FAST_PATH = "/json"


# Tests the answers of the script's delayed paths.
class TestDelay(test_local_http.ServerCase):
    # Each delayed path answers GET and POST with its status and body.
    def test_paths_answered(self) -> None:
        test_local_http.answers_check(self, True)

    # A delayed answer is due after its delay, another answered meanwhile.
    def test_delay_threaded(self) -> None:
        delay: float = _SCRIPT["paths"][_SLOW_PATH]["delay"]
        slow = http.client.HTTPConnection(_HOST, _PORT)
        self.addCleanup(slow.close)
        begun = time.monotonic()
        slow.request("GET", _SLOW_PATH)
        fast = _SCRIPT["paths"][_FAST_PATH]
        response, read = test_local_http.request_send("GET", _FAST_PATH, None)
        self.assertEqual(response.status, fast["status"])
        self.assertEqual(read, fast["body"].encode())
        waiting = cast(socket.socket, slow.sock)
        self.assertEqual(select.select([waiting], [], [], 0)[0], [])
        answer = slow.getresponse()
        late = _SCRIPT["paths"][_SLOW_PATH]["body"]
        self.assertEqual(answer.read(), late.encode())
        self.assertGreaterEqual(time.monotonic() - begun, delay)
