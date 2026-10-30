# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The local HTTP server of the test run, infrastructure for testing that the
# driver starts on 127.0.0.1 before the first block that needs it and stops
# when the run's stream ends: a `ThreadingHTTPServer` of the standard
# library on a thread of its own, one handler thread per request. It is the
# scripted far end of a connection. The script is an object of the gold:
# `host`, `port`, `closed_port`, and `paths`, each path's `status`,
# `headers`, `body` and `delay`. Each path of the script answers GET and
# POST alike: the request's body is read by its Content-Length and dropped,
# the delay is slept, the status line is written by `send_response_only` as
# HTTP/1.0, then exactly the script's headers and the body as UTF-8, all of
# it sent by one write, so that a client that closed its end during the
# delay takes the answer as TCP allows. Any other path that starts with
# `/NAME/` is the file at the rest of the path in the directory served,
# `NAME` the directory's own name, such as `/build/headless.html`, the page
# of group B, answered with its type, by the standard library's own table
# and no file of the system, and its length. The script's `closed_port` is
# bound and never listens, so that a fetch to it is refused. Any failure of a
# handler, an unknown path or a request the standard library would refuse
# among them, is a hard failure: `handle_error` keeps the first and sends
# the main thread `SIGUSR2`, which the server holds while it serves, whose
# handler raises it there at once, wherever the main thread is, the
# handler's traceback as its cause, as the driver's own timers raise. A
# failure after the first ends its request with no answer and is not
# raised, since the run stops at the first. Standard library only, and
# plain English texts.

import functools, http.server, mimetypes, os, signal, socket, socketserver
import sys, threading, time, types
from collections.abc import Mapping
from typing import Any, NamedTuple, NoReturn, cast

# The codec of a scripted body.
_BODY_CODEC = "utf-8"

# The signal that carries a handler's first failure to the main thread.
_FAILURE_SIGNAL = signal.SIGUSR2

# The delay of a file's answer: none.
_FILE_DELAY = 0

# The status of a file's answer.
_FILE_STATUS = 200

# The types of files by their suffixes, the standard library's own table.
_FILE_TYPES = mimetypes.MimeTypes()

# The header that frames a request's body, and gives a file's length.
_LENGTH_HEADER = "content-length"

# The seconds the serving loop waits between its checks for a stop.
_POLL_SECONDS = 0.05

# The version of HTTP of every answer.
_PROTOCOL_VERSION = "HTTP/1.0"

# The header that gives a file's type.
_TYPE_HEADER = "content-type"

# A buffered writer, so that the flush after a method sends its answer whole.
_WRITE_BUFFER = -1


# What a path answers: its status, its headers, its body and its delay.
class _PathAnswer(NamedTuple):
    status: int
    headers: dict[str, str]
    body: bytes
    delay: float


# The script's answers by path, the files' prefix and their directory.
class _ServedPaths(NamedTuple):
    answers: dict[str, _PathAnswer]
    prefix: str
    files: str


# Answers each request from the paths served, and raises for any other.
class _AnswerHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = _PROTOCOL_VERSION
    wbufsize = _WRITE_BUFFER

    # Keeps the paths served, then handles the request, as the base does.
    def __init__(
        self,
        request: socket.socket,
        client_address: Any,
        server: socketserver.BaseServer,
        served: _ServedPaths,
    ) -> None:
        self.served = served
        super().__init__(request, client_address, server)

    # Answers a GET.
    def do_GET(self) -> None:
        self.request_answer()

    # Answers a POST as a GET.
    def do_POST(self) -> None:
        self.request_answer()

    # Raises for a request the standard library would refuse with `code`.
    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> NoReturn:
        raise RuntimeError(
            f"the local HTTP server refused {self.requestline!r} with"
            f" {code}: {message}"
        )

    # Drops the request's body, then sends the path's answer after its delay.
    def request_answer(self) -> None:
        length = self.headers[_LENGTH_HEADER]
        if length is not None:
            self.rfile.read(int(length))
        answer = self.served.answers.get(self.path)
        if answer is None:
            answer = self.file_answer()
        time.sleep(answer.delay)
        self.send_response_only(answer.status)
        for name, value in answer.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(answer.body)

    # The answer of the file the path names, raising unless it names one.
    def file_answer(self) -> _PathAnswer:
        served = self.served
        if not self.path.startswith(served.prefix):
            raise RuntimeError(
                f"the local HTTP server has no path {self.path!r}"
            )
        rest = self.path.removeprefix(served.prefix)
        path = os.path.realpath(os.path.join(served.files, rest))
        inside = os.path.commonpath((path, served.files)) == served.files
        if not (inside and os.path.isfile(path)):
            raise RuntimeError(
                f"the local HTTP server has no file {self.path!r}"
            )
        kind = _FILE_TYPES.guess_file_type(path)[0]
        if kind is None:
            raise RuntimeError(
                f"the local HTTP server has no type for the file {self.path!r}"
            )
        with open(path, "rb") as file:
            body = file.read()
        headers = {_TYPE_HEADER: kind, _LENGTH_HEADER: str(len(body))}
        return _PathAnswer(_FILE_STATUS, headers, body, _FILE_DELAY)


# The server, started by its constructor and stopped by `server_stop`.
class LocalServer(http.server.ThreadingHTTPServer):
    # Binds both ports of the script, then serves it and the files on a thread.
    def __init__(self, script: Mapping[str, Any], files: str) -> None:
        answers = {
            path: _PathAnswer(
                answer["status"],
                answer["headers"],
                answer["body"].encode(_BODY_CODEC),
                answer["delay"],
            )
            for path, answer in script["paths"].items()
        }
        name = os.path.basename(os.path.normpath(files))
        served = _ServedPaths(answers, f"/{name}/", os.path.realpath(files))
        handler = functools.partial(_AnswerHandler, served=served)
        super().__init__((script["host"], script["port"]), handler)
        self._closed = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._closed.bind((script["host"], script["closed_port"]))
        self._lock = threading.Lock()
        self._failure: BaseException | None = None
        self._main = cast(int, threading.main_thread().ident)
        self._kept = signal.signal(_FAILURE_SIGNAL, self._failure_raise)
        self._serving = threading.Thread(
            target=self.serve_forever, args=(_POLL_SECONDS,), daemon=True
        )
        self._serving.start()

    # Keeps the first failure of a handler and raises it in the main thread.
    def handle_error(self, request: object, client_address: object) -> None:
        failure = cast(BaseException, sys.exception())
        with self._lock:
            first = self._failure is None
            if first:
                self._failure = failure
        if first:
            signal.pthread_kill(self._main, _FAILURE_SIGNAL)

    # Stops serving, waits for every answer under way, frees both ports.
    def server_stop(self) -> None:
        self.shutdown()
        self._serving.join()
        self.server_close()
        self._closed.close()
        signal.signal(_FAILURE_SIGNAL, self._kept)

    # Raises the first failure of a handler, in the main thread the signal hit.
    def _failure_raise(
        self, number: int, frame: types.FrameType | None
    ) -> NoReturn:
        failure = self._failure
        raise RuntimeError(f"the local HTTP server failed: {failure}") from (
            failure
        )
