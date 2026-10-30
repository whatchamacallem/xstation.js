# The local HTTP server of the test run, an `http.server` of the standard
# library on a thread of its own, which the driver starts on 127.0.0.1 before
# the first block that needs it and stops when the run's stream ends. It is
# the scripted far end of a connection. The script is an object of the gold:
# `host`, `port`, `closed_port`, and `paths`, each path's `status`,
# `headers`, `body` and `delay`. Each path of the script answers GET and
# POST alike with that status, those headers and no others, that body as
# UTF-8, after that delay in seconds, slept; the request's body is read by
# its `Content-Length` and dropped, and the status line is written by
# `send_response_only` as HTTP/1.0, one handler thread per request. Any
# other path that starts `/NAME/` is the file at the rest of the path in the
# directory served, `NAME` the directory's own name, such as
# `/build/headless.html`, the page of group B, with its type and length. The
# script's `closed_port` is bound and never listens, so that a fetch to it
# is refused. Any failure of a handler, an unknown path or a request the
# standard library would refuse among them, is a hard failure: the first is
# raised at once in the main thread, wherever it is, by `SIGUSR2`, which
# the server holds while it serves, the handler's traceback as its cause. A
# failure after the first ends its request with no answer and is not raised,
# since the run stops at the first.

import http.server
from collections.abc import Mapping
from typing import Any

# The server, started by its constructor and stopped by `server_stop`.
class LocalServer(http.server.ThreadingHTTPServer):
    # Binds both ports of the script, then serves it and the files on a thread.
    def __init__(self, script: Mapping[str, Any], files: str) -> None: ...
    # Keeps the first failure of a handler and raises it in the main thread.
    def handle_error(
        self, request: object, client_address: object
    ) -> None: ...
    # Stops serving, waits for every answer under way, frees both ports.
    def server_stop(self) -> None: ...
