# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the local HTTP server with the standard library's own client against
# the real server, on the script of this suite's gold: each path answered
# with its status line as HTTP/1.0, exactly its headers and its body, to GET
# and to POST, whose body the server reads and drops; the delay slept while
# another request is answered; the closed port bound and refusing; the files
# of a scratch directory under build/ served by path; and each failure of a
# handler raised in this, the main thread, at once, the first only. Each
# test starts a server of its own and stops it.

import errno, harness, http.client, local_http, os, select, signal, socket
import tempfile, time, unittest
from collections.abc import Callable
from typing import Any, cast

# The gold of this suite.
_GOLD_ID = "python.test_local_http"

# The script the server answers.
_SCRIPT: dict[str, Any] = harness.gold_get(f"{_GOLD_ID}.server")

# The host and the two ports of the script.
_HOST: str = _SCRIPT["host"]
_PORT: int = _SCRIPT["port"]
_CLOSED_PORT: int = _SCRIPT["closed_port"]

# The build directory of the checkout, where the scratch directories go.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The bytes of the body each POST sends, which the server reads and drops.
_POST_BYTES = 65536

# The HTTP version `http.client` reports for an answer of HTTP/1.0.
_VERSION_10 = 10

# The path of the script whose answer is delayed.
_SLOW_PATH = "/slow"

# The path of the script answered while the delayed one waits.
_FAST_PATH = "/json"

# The page written in the scratch directory, its text and its type.
_PAGE_NAME = "page.html"
_PAGE_TEXT = "<!doctype html><title>page</title>\n"
_PAGE_TYPE = "text/html"

# A file of a suffix the type table does not know.
_UNTYPED_NAME = "page.tap"

# The signal the server holds while it serves, by its stub.
_FAILURE_SIGNAL = signal.SIGUSR2

# The start of each failure the main thread is sent.
_FAILED_TEXT = "the local HTTP server failed: "


# Sends one request on a connection of its own, returns the answer and body.
def request_send(
    method: str, path: str, body: bytes | None
) -> tuple[http.client.HTTPResponse, bytes]:
    connection = http.client.HTTPConnection(_HOST, _PORT)
    try:
        connection.request(method, path, body)
        response = connection.getresponse()
        return response, response.read()
    finally:
        connection.close()


# Sends the bytes on a connection of its own and reads until the server ends.
def bytes_send(data: bytes) -> bytes:
    with socket.create_connection((_HOST, _PORT)) as connection:
        connection.sendall(data)
        return connection.recv(1)


# Starts a server on the script, serving a scratch directory under build/.
class ServerCase(unittest.TestCase):
    # Makes the scratch directory with a page, then starts the server on it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        self.addCleanup(scratch.cleanup)
        self.files = scratch.name
        self.prefix = f"/{os.path.basename(self.files)}/"
        for name in (_PAGE_NAME, _UNTYPED_NAME):
            page = os.path.join(self.files, name)
            with open(page, "w", encoding="utf-8") as file:
                file.write(_PAGE_TEXT)
        self.handler = signal.getsignal(_FAILURE_SIGNAL)
        self.server_start()

    # Starts a server on the script and the scratch directory, stopped after.
    def server_start(self) -> None:
        self.server = local_http.LocalServer(_SCRIPT, self.files)
        self.addCleanup(self.server.server_stop)

    # Stops the server, then starts another, for a failure after the first.
    def server_restart(self) -> None:
        self.server.server_stop()
        self.server_start()

    # Fails unless the send raises the handler's failure with this text.
    def failure_expect(self, send: Callable[[], object], text: str) -> None:
        with self.assertRaises(RuntimeError) as caught:
            send()
        self.assertEqual(str(caught.exception), _FAILED_TEXT + text)
        cause = caught.exception.__cause__
        self.assertIsInstance(cause, RuntimeError)
        self.assertEqual(str(cause), text)


# Tests the answers of the script's paths, and of the files served.
class TestAnswers(ServerCase):
    # Each path answers GET and POST with its status, headers and body alone.
    def test_paths_answered(self) -> None:
        paths: dict[str, dict[str, Any]] = _SCRIPT["paths"]
        for path, answer in paths.items():
            for method, body in (("GET", None), ("POST", b"x" * _POST_BYTES)):
                with self.subTest(path=path, method=method):
                    response, read = request_send(method, path, body)
                    self.assertEqual(response.version, _VERSION_10)
                    self.assertEqual(response.status, answer["status"])
                    headers = list(answer["headers"].items())
                    self.assertEqual(response.getheaders(), headers)
                    self.assertEqual(read, answer["body"].encode())

    # A delayed answer is due after its delay, another answered meanwhile.
    def test_delay_threaded(self) -> None:
        delay: float = _SCRIPT["paths"][_SLOW_PATH]["delay"]
        slow = http.client.HTTPConnection(_HOST, _PORT)
        self.addCleanup(slow.close)
        begun = time.monotonic()
        slow.request("GET", _SLOW_PATH)
        fast = _SCRIPT["paths"][_FAST_PATH]
        response, read = request_send("GET", _FAST_PATH, None)
        self.assertEqual(response.status, fast["status"])
        self.assertEqual(read, fast["body"].encode())
        waiting = cast(socket.socket, slow.sock)
        self.assertEqual(select.select([waiting], [], [], 0)[0], [])
        answer = slow.getresponse()
        late = _SCRIPT["paths"][_SLOW_PATH]["body"]
        self.assertEqual(answer.read(), late.encode())
        self.assertGreaterEqual(time.monotonic() - begun, delay)

    # A file of the directory is served at its path, with its type and length.
    def test_file_served(self) -> None:
        response, read = request_send("GET", self.prefix + _PAGE_NAME, None)
        self.assertEqual(response.version, _VERSION_10)
        self.assertEqual(response.status, http.HTTPStatus.OK)
        headers = [
            ("content-type", _PAGE_TYPE),
            ("content-length", str(len(_PAGE_TEXT))),
        ]
        self.assertEqual(response.getheaders(), headers)
        self.assertEqual(read, _PAGE_TEXT.encode())

    # The closed port is held bound, and a connection to it is refused.
    def test_closed_refused(self) -> None:
        connection = http.client.HTTPConnection(_HOST, _CLOSED_PORT)
        self.addCleanup(connection.close)
        with self.assertRaises(ConnectionRefusedError):
            connection.request("GET", "/")
        with socket.socket() as probe:
            with self.assertRaises(OSError) as caught:
                probe.bind((_HOST, _CLOSED_PORT))
        self.assertEqual(caught.exception.errno, errno.EADDRINUSE)

    # The server holds its signal while it serves, and gives it back at stop.
    def test_stop_frees(self) -> None:
        self.assertNotEqual(signal.getsignal(_FAILURE_SIGNAL), self.handler)
        self.server.server_stop()
        self.assertEqual(signal.getsignal(_FAILURE_SIGNAL), self.handler)
        with self.assertRaises(ConnectionRefusedError):
            request_send("GET", _FAST_PATH, None)
        with socket.socket() as probe:
            probe.bind((_HOST, _CLOSED_PORT))


# Tests that each failure of a handler is raised in the main thread at once.
class TestFailures(ServerCase):
    # A path neither the script nor the files hold fails the run.
    def test_path_unknown(self) -> None:
        text = "the local HTTP server has no path '/absent'"
        self.failure_expect(lambda: request_send("GET", "/absent", None), text)

    # Only the first failure is raised: a later one ends its request alone.
    def test_failure_first(self) -> None:
        text = "the local HTTP server has no path '/absent'"
        self.failure_expect(lambda: request_send("GET", "/absent", None), text)
        with self.assertRaises(http.client.RemoteDisconnected):
            request_send("GET", "/absent", None)
        response, _ = request_send("GET", _FAST_PATH, None)
        self.assertEqual(response.status, 200)

    # A path under the files' prefix that names no file in them fails.
    def test_file_unknown(self) -> None:
        for rest in ("absent.html", "", "../test_local_http.py"):
            with self.subTest(rest=rest):
                path = self.prefix + rest
                text = f"the local HTTP server has no file {path!r}"
                self.failure_expect(
                    lambda: request_send("GET", path, None), text
                )
                self.server_restart()

    # A file whose type the table does not know fails.
    def test_file_untyped(self) -> None:
        path = self.prefix + _UNTYPED_NAME
        text = f"the local HTTP server has no type for the file {path!r}"
        self.failure_expect(lambda: request_send("GET", path, None), text)

    # A request the standard library would refuse fails, as HEAD and bad text.
    def test_request_refused(self) -> None:
        cases = (
            (
                lambda: request_send("HEAD", _FAST_PATH, None),
                "the local HTTP server refused 'HEAD /json HTTP/1.1' with 501:"
                " Unsupported method ('HEAD')",
            ),
            (
                lambda: bytes_send(b"GET /json HTTP/9\r\n\r\n"),
                "the local HTTP server refused 'GET /json HTTP/9' with 400:"
                " Bad request version ('HTTP/9')",
            ),
        )
        for send, text in cases:
            with self.subTest(text=text):
                self.failure_expect(send, text)
                self.server_restart()
