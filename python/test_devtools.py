# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of devtools.py that need no browser: WebSocket frames with
# and without masks, the handshake, joining a message from its fragments, the
# relay and stop scripts, the DevTools address, the timers, a client reading
# canned bytes or an empty pipe, the synchronous loads picked out of a trace,
# the workers and pauses kept, and a browser's page, trace and worker calls
# and waits with canned bytes, a scratch profile and a patched removal. No
# process is started. The waits the tests give are the gold's.

import devtools, errno, functools, harness, io, json, os, subprocess
import tempfile, time, unittest.mock
from typing import Any, cast

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"
)

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_devtools"

# A wait no test reaches the end of, for the replies the bytes hold.
_WAIT_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.wait_seconds")

# A wait that ends soon, for the replies and events that never come.
_EXPIRY_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.expiry_seconds")

# What DevTools answers a navigation to an address nothing listens on yet.
_REFUSED_RESULT = {
    "errorText": "net::ERR_CONNECTION_REFUSED",
    "frameId": "F",
    "loaderId": "L0",
}

# RFC 6455's sample key.
_SAMPLE_KEY = "dGhlIHNhbXBsZSBub25jZQ=="

# The accept value the sample key must give.
_SAMPLE_ACCEPT = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="

# The upgrade answer that accepts the sample key.
_ACCEPT_HEAD = (
    b"HTTP/1.1 101 Switching Protocols\r\n"
    b"Upgrade: websocket\r\n"
    b"Connection: Upgrade\r\n"
    b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
    b"\r\n"
)

# The mask in RFC 6455's example of a masked text frame holding Hello.
_SAMPLE_MASK = bytes.fromhex("37fa213d")

# That frame, masked.
_HELLO_MASKED = bytes.fromhex("818537fa213d7f9f4d5158")

# The same frame as a server sends it, with no mask.
_HELLO_PLAIN = bytes.fromhex("810548656c6c6f")

# A mask that leaves the payload as it is.
_ZERO_MASK = bytes(4)


# Serves canned bytes as the relay's pipe would, ignoring the timer.
class CannedReader:
    # Keeps the bytes to serve.
    def __init__(self, data: bytes) -> None:
        self.stream = io.BytesIO(data)

    # Returns up to count of the bytes, and nothing once they run out.
    def bytes_next(self, timer: devtools.WaitTimer, count: int) -> bytes:
        return self.stream.read(count)


# Keeps the frames a reader sent, in order.
class FrameRecorder:
    # Starts with no frames.
    def __init__(self) -> None:
        self.frames: list[tuple[int, bytes]] = []

    # Keeps one frame sent.
    def frame_record(self, opcode: int, payload: bytes) -> None:
        self.frames.append((opcode, payload))


# A client reading canned bytes, with what it wrote and what it passed on.
class ClientRig:
    # Makes the client and the lists its writes and events go to.
    def __init__(self, data: bytes, wait_seconds: float) -> None:
        self.writes: list[bytes] = []
        self.events: list[dict[str, Any]] = []
        self.client = devtools.ProtocolClient(
            CannedReader(data).bytes_next,
            self.writes.append,
            self.events.append,
            wait_seconds,
        )


# A browser process that has not exited.
class RunningProcess:
    # Returns no exit code, as a running process does.
    def poll(self) -> int | None:
        return None


# Returns the event of a target attached from the page, with its session.
def attach_event(kind: str, session_id: str, title: str) -> dict[str, Any]:
    return {
        "method": "Target.attachedToTarget",
        "sessionId": "P",
        "params": {
            "sessionId": session_id,
            "targetInfo": {
                "targetId": "T" + session_id,
                "type": kind,
                "title": title,
                "url": "blob:http://x/1",
                "attached": True,
            },
            "waitingForDebugger": False,
        },
    }


# Returns a browser that starts nothing and whose client reads the bytes.
def browser_make(data: bytes, writes: list[bytes]) -> devtools.Browser:
    with unittest.mock.patch("shutil.which", return_value="/w/ps.exe"):
        browser = devtools.Browser(800, 600)
    browser.client = devtools.ProtocolClient(
        CannedReader(data).bytes_next,
        writes.append,
        browser.events.message_handle,
        _WAIT_SECONDS,
    )
    return browser


# Returns the frame a server sends for a DevTools message.
def message_frame(message: dict[str, Any]) -> bytes:
    payload = json.dumps(message).encode()
    return devtools.frame_encode(0x1, payload, _ZERO_MASK)


# Returns the event of a debugger paused on the session.
def paused_event(session_id: str) -> dict[str, Any]:
    return {
        "method": "Debugger.paused",
        "sessionId": session_id,
        "params": {"callFrames": [], "reason": "other"},
    }


# Returns the DevTools request inside a frame the client wrote.
def request_decode(frame: bytes) -> dict[str, Any]:
    decoded = devtools.frame_decode(io.BytesIO(frame).read)
    request: dict[str, Any] = json.loads(decoded.payload)
    return request


# Returns the metadata event that names a thread of a process.
def thread_metadata(pid: int, tid: int, name: str) -> dict[str, Any]:
    return {
        "args": {"name": name},
        "cat": "__metadata",
        "name": "thread_name",
        "ph": "M",
        "pid": pid,
        "tid": tid,
        "ts": 0,
    }


# Returns a complete trace event of the name, run on a thread of a process.
def thread_span(pid: int, tid: int, name: str) -> dict[str, Any]:
    return {
        "args": {},
        "cat": "loading",
        "dur": 5,
        "name": name,
        "ph": "X",
        "pid": pid,
        "tid": tid,
        "ts": 100,
    }


# Returns the event that ends a trace, saying whether it lost events.
def trace_complete(lost: bool) -> dict[str, Any]:
    return {
        "method": "Tracing.tracingComplete",
        "params": {"dataLossOccurred": lost},
    }


# Returns the event that carries some of a trace's events.
def trace_data(values: list[dict[str, Any]]) -> dict[str, Any]:
    return {"method": "Tracing.dataCollected", "params": {"value": values}}


# Frames encode and decode as RFC 6455 says, with and without masks.
class TestFrames(unittest.TestCase):
    # A masked text frame is RFC 6455's example.
    def test_encode_masked(self) -> None:
        frame = devtools.frame_encode(0x1, b"Hello", _SAMPLE_MASK)
        self.assertEqual(frame, _HELLO_MASKED)

    # The length field grows to 2 bytes at 126 and to 8 bytes at 65536.
    def test_encode_lengths(self) -> None:
        heads = {
            125: b"\x81\xfd",
            126: b"\x81\xfe\x00\x7e",
            65535: b"\x81\xfe\xff\xff",
            65536: b"\x81\xff" + (65536).to_bytes(8, "big"),
        }
        for size, head in heads.items():
            frame = devtools.frame_encode(0x1, bytes(size), _ZERO_MASK)
            self.assertEqual(frame[: len(head)], head)
            self.assertEqual(len(frame), len(head) + 4 + size)

    # The mask repeats every 4 bytes.
    def test_encode_cycle(self) -> None:
        frame = devtools.frame_encode(0x2, bytes(6), bytes([1, 2, 3, 4]))
        expected = bytes([0x82, 0x86, 1, 2, 3, 4, 1, 2, 3, 4, 1, 2])
        self.assertEqual(frame, expected)

    # A frame as a server sends it, with no mask, decodes.
    def test_decode_plain(self) -> None:
        frame = devtools.frame_decode(io.BytesIO(_HELLO_PLAIN).read)
        self.assertEqual(frame, devtools.SocketFrame(True, 0x1, b"Hello"))

    # A masked frame is unmasked.
    def test_decode_masked(self) -> None:
        frame = devtools.frame_decode(io.BytesIO(_HELLO_MASKED).read)
        self.assertEqual(frame, devtools.SocketFrame(True, 0x1, b"Hello"))

    # Lengths of 2 bytes and of 8 bytes decode.
    def test_decode_lengths(self) -> None:
        medium = bytes(index % 251 for index in range(300))
        data = b"\x81\x7e" + (300).to_bytes(2, "big") + medium
        frame = devtools.frame_decode(io.BytesIO(data).read)
        self.assertEqual(frame.payload, medium)
        large = bytes(index % 251 for index in range(70000))
        data = b"\x81\x7f" + (70000).to_bytes(8, "big") + large
        frame = devtools.frame_decode(io.BytesIO(data).read)
        self.assertEqual(frame.payload, large)

    # A frame encoded with a mask decodes to its payload.
    def test_decode_cycle(self) -> None:
        payload = bytes(index % 251 for index in range(70000))
        frame = devtools.frame_encode(0x1, payload, bytes([9, 8, 7, 6]))
        decoded = devtools.frame_decode(io.BytesIO(frame).read)
        self.assertEqual(decoded, devtools.SocketFrame(True, 0x1, payload))

    # A fragment that doesn't end its message decodes with its flag clear.
    def test_decode_fragment(self) -> None:
        stream = io.BytesIO(bytes.fromhex("010348656c80026c6f"))
        first = devtools.frame_decode(stream.read)
        second = devtools.frame_decode(stream.read)
        self.assertEqual(first, devtools.SocketFrame(False, 0x1, b"Hel"))
        self.assertEqual(second, devtools.SocketFrame(True, 0x0, b"lo"))

    # A frame cut short fails loud.
    def test_decode_short(self) -> None:
        with self.assertRaises(ConnectionError) as caught:
            devtools.frame_decode(io.BytesIO(_HELLO_PLAIN[:-1]).read)
        self.assertEqual(
            str(caught.exception), "DevTools closed the connection"
        )


# A message is joined from its frames, with pings answered on the way.
class TestMessages(unittest.TestCase):
    # Returns the message read from the frames, and the frames sent meanwhile.
    def frames_read(
        self, frames: str
    ) -> tuple[bytes, list[tuple[int, bytes]]]:
        recorder = FrameRecorder()
        message = devtools.message_read(
            io.BytesIO(bytes.fromhex(frames)).read, recorder.frame_record
        )
        return message, recorder.frames

    # A message in one frame is returned as it is.
    def test_read_single(self) -> None:
        self.assertEqual(self.frames_read("810548656c6c6f"), (b"Hello", []))

    # Fragments are joined, as in RFC 6455's example.
    def test_read_fragments(self) -> None:
        message, sent = self.frames_read("010348656c80026c6f")
        self.assertEqual(message, b"Hello")
        self.assertEqual(sent, [])

    # A ping is answered with a pong holding its payload.
    def test_read_ping(self) -> None:
        message, sent = self.frames_read("89026162" + "81017a")
        self.assertEqual(message, b"z")
        self.assertEqual(sent, [(0xA, b"ab")])

    # A pong is ignored.
    def test_read_pong(self) -> None:
        self.assertEqual(self.frames_read("8a00" + "81017a"), (b"z", []))

    # A ping between fragments is answered and the fragments still join.
    def test_read_between(self) -> None:
        message, sent = self.frames_read("010161" + "8900" + "800162")
        self.assertEqual(message, b"ab")
        self.assertEqual(sent, [(0xA, b"")])

    # A close frame fails loud.
    def test_read_close(self) -> None:
        with self.assertRaises(ConnectionError) as caught:
            self.frames_read("8800")
        self.assertEqual(
            str(caught.exception), "DevTools closed the connection"
        )

    # A frame out of order, or of an opcode DevTools doesn't use, fails loud.
    def test_read_order(self) -> None:
        refusals = {
            "800161": "DevTools sent WebSocket opcode 0 where 1 was due",
            "010161" + "810162": "DevTools sent WebSocket opcode 1 where 0"
            " was due",
            "820161": "DevTools sent WebSocket opcode 2 where 1 was due",
        }
        for frames, message in refusals.items():
            with self.assertRaises(ConnectionError, msg=frames) as caught:
                self.frames_read(frames)
            self.assertEqual(str(caught.exception), message)


# The WebSocket upgrade request and its answer.
class TestHandshake(unittest.TestCase):
    # The sample key gives the accept value RFC 6455 gives.
    def test_accept_sample(self) -> None:
        self.assertEqual(devtools.accept_key(_SAMPLE_KEY), _SAMPLE_ACCEPT)

    # The upgrade request has each header, ended by a blank line.
    def test_request_text(self) -> None:
        request = devtools.handshake_request(
            "127.0.0.1:9222", "/devtools/browser/abc", _SAMPLE_KEY
        )
        self.assertEqual(
            request,
            b"GET /devtools/browser/abc HTTP/1.1\r\n"
            b"Host: 127.0.0.1:9222\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            b"Sec-WebSocket-Version: 13\r\n"
            b"\r\n",
        )

    # An answer that switches protocols with the right accept value passes.
    def test_check_accepted(self) -> None:
        self.assertIsNone(devtools.handshake_check(_SAMPLE_KEY, _ACCEPT_HEAD))

    # An answer that isn't a switch of protocols, or is empty, fails loud.
    def test_check_status(self) -> None:
        refusals = {
            b"HTTP/1.1 400 Bad Request\r\n\r\n": "DevTools answered HTTP/1.1"
            " 400 Bad Request",
            b"": "DevTools answered nothing",
        }
        for head, message in refusals.items():
            with self.assertRaises(ConnectionError, msg=head) as caught:
                devtools.handshake_check(_SAMPLE_KEY, head)
            self.assertEqual(str(caught.exception), message)

    # A wrong accept value, or none, fails loud.
    def test_check_key(self) -> None:
        wrong = _ACCEPT_HEAD.replace(b"s3pPLM", b"S3pPLM")
        missing = b"HTTP/1.1 101 Switching Protocols\r\n\r\n"
        for head in (wrong, missing):
            with self.assertRaises(ConnectionError, msg=head) as caught:
                devtools.handshake_check(_SAMPLE_KEY, head)
            self.assertEqual(
                str(caught.exception),
                "DevTools answered a WebSocket key wrongly",
            )

    # The head is read up to the blank line and no further.
    def test_head_read(self) -> None:
        stream = io.BytesIO(_ACCEPT_HEAD + b"rest")
        self.assertEqual(devtools.head_read(stream.read), _ACCEPT_HEAD)
        self.assertEqual(stream.read(), b"rest")


# The address the browser writes to its port file.
class TestAddress(unittest.TestCase):
    # The port and the path are split from the file's two lines.
    def test_parse_pair(self) -> None:
        address = devtools.address_parse("9222\n/devtools/browser/abc\n")
        self.assertEqual(
            address, devtools.EndpointAddress(9222, "/devtools/browser/abc")
        )

    # Text that isn't a port then a path fails loud.
    def test_parse_malformed(self) -> None:
        refusals = {
            "": "DevToolsActivePort holds '', not a port and a path",
            "9222": "DevToolsActivePort holds '9222', not a port and a path",
            "9222\n/a\n/b": "DevToolsActivePort holds '9222\\n/a\\n/b', not"
            " a port and a path",
            "port\n/a": "invalid literal for int() with base 10: 'port'",
        }
        for text, message in refusals.items():
            with self.assertRaises(ValueError, msg=repr(text)) as caught:
                devtools.address_parse(text)
            self.assertEqual(str(caught.exception), message)


# The scripts and arguments handed to PowerShell.
class TestScripts(unittest.TestCase):
    # The relay script sets the port first and has its here string whole.
    def test_relay_port(self) -> None:
        script = devtools.relay_script(1234)
        self.assertTrue(script.startswith("$port_ = 1234\n"))
        self.assertIn("Add-Type -TypeDefinition @'\n", script)
        self.assertIn("\n'@\n", script)
        self.assertIn("[XsjsDevToolsRelay]::RelayRun($port_)", script)

    # The relay script is plain ASCII with LF line ends.
    def test_relay_ascii(self) -> None:
        script = devtools.relay_script(1)
        self.assertTrue(script.isascii())
        self.assertNotIn("\r", script)

    # The stop script fails loud but for a helper gone with the browser.
    def test_stop_loud(self) -> None:
        script: str = getattr(devtools, "_STOP_SCRIPT")
        self.assertNotIn("-ErrorAction SilentlyContinue", script)
        self.assertIn("-ErrorAction Stop", script)
        self.assertIn("-ne 'ObjectNotFound'", script)

    # The script goes in as base64 of its `UTF-16` little endian bytes.
    def test_command_encoded(self) -> None:
        arguments = devtools.powershell_command("ps.exe", "a")
        self.assertEqual(
            arguments,
            [
                "ps.exe",
                "-NoProfile",
                "-NonInteractive",
                "-EncodedCommand",
                "YQA=",
            ],
        )


# Every wait has a timer that ends it, and reads that return too little.
class TestTimers(unittest.TestCase):
    # A wait with no time left fails, naming what it waited for.
    def test_timer_expired(self) -> None:
        timer = devtools.WaitTimer("the thing", 0)
        with self.assertRaises(TimeoutError) as caught:
            timer.seconds_left()
        self.assertEqual(
            str(caught.exception), "gave up after 0 s waiting for the thing"
        )

    # A wait with time left returns it.
    def test_timer_running(self) -> None:
        left = devtools.WaitTimer("the thing", _WAIT_SECONDS).seconds_left()
        self.assertGreater(left, 0)
        self.assertLessEqual(left, _WAIT_SECONDS)

    # A pipe nothing is written to fails when its timer ends.
    def test_pipe_timeout(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        timer = devtools.WaitTimer("bytes that never come", _EXPIRY_SECONDS)
        with self.assertRaises(TimeoutError) as caught:
            devtools.pipe_read(read_fd, timer, 1)
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for bytes that"
            " never come",
        )

    # A pipe gives no more than the count asked for.
    def test_pipe_read(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        os.write(write_fd, b"abc")
        timer = devtools.WaitTimer("bytes", _WAIT_SECONDS)
        self.assertEqual(devtools.pipe_read(read_fd, timer, 2), b"ab")
        self.assertEqual(devtools.pipe_read(read_fd, timer, 2), b"c")

    # A pipe whose writer is gone reads as empty.
    def test_pipe_ended(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        os.close(write_fd)
        timer = devtools.WaitTimer("bytes", _WAIT_SECONDS)
        self.assertEqual(devtools.pipe_read(read_fd, timer, 4), b"")

    # Short reads are joined until the count is reached.
    def test_bytes_joined(self) -> None:
        stream = io.BytesIO(b"abc")
        data = devtools.bytes_exact(lambda count: stream.read(1), 3)
        self.assertEqual(data, b"abc")

    # A reader that runs dry first fails loud.
    def test_bytes_short(self) -> None:
        stream = io.BytesIO(b"ab")
        with self.assertRaises(ConnectionError) as caught:
            devtools.bytes_exact(lambda count: stream.read(1), 3)
        self.assertEqual(
            str(caught.exception), "DevTools closed the connection"
        )


# The protocol client's calls, events and timers, on canned bytes or a pipe.
class TestClient(unittest.TestCase):
    # A reply is matched by its id and events before it are passed on.
    def test_call_reply(self) -> None:
        event = {"method": "Page.frameNavigated", "params": {}}
        reply = {"id": 1, "result": {"frameId": "F"}}
        rig = ClientRig(
            message_frame(event) + message_frame(reply), _WAIT_SECONDS
        )
        result = rig.client.method_call("Page.navigate", {"url": "u"})
        self.assertEqual(result, {"frameId": "F"})
        self.assertEqual(rig.events, [event])
        self.assertEqual(
            request_decode(rig.writes[0]),
            {"id": 1, "method": "Page.navigate", "params": {"url": "u"}},
        )

    # Page methods carry the session and browser and target methods don't.
    def test_call_session(self) -> None:
        rig = ClientRig(
            message_frame({"id": 1, "result": {}})
            + message_frame({"id": 2, "result": {}}),
            _WAIT_SECONDS,
        )
        rig.client.session_id = "S"
        rig.client.method_call("Runtime.enable")
        rig.client.method_call("Target.getTargets")
        self.assertEqual(request_decode(rig.writes[0])["sessionId"], "S")
        self.assertNotIn("sessionId", request_decode(rig.writes[1]))

    # A call on a named session carries it, even for a target method.
    def test_call_named(self) -> None:
        rig = ClientRig(
            message_frame({"id": 1, "result": {}})
            + message_frame({"id": 2, "result": {}}),
            _WAIT_SECONDS,
        )
        rig.client.session_id = "P"
        rig.client.session_call("W", "Target.setAutoAttach", {"flatten": True})
        rig.client.session_call("", "Runtime.enable")
        self.assertEqual(
            request_decode(rig.writes[0]),
            {
                "id": 1,
                "method": "Target.setAutoAttach",
                "params": {"flatten": True},
                "sessionId": "W",
            },
        )
        self.assertNotIn("sessionId", request_decode(rig.writes[1]))

    # An error reply fails loud with the method and DevTools' message.
    def test_call_error(self) -> None:
        error = {"code": -32601, "message": "nope"}
        rig = ClientRig(
            message_frame({"id": 1, "error": error}), _WAIT_SECONDS
        )
        with self.assertRaises(RuntimeError) as caught:
            rig.client.method_call("Page.enable")
        self.assertEqual(str(caught.exception), "Page.enable: nope")

    # A reply to another call fails loud.
    def test_call_mismatch(self) -> None:
        rig = ClientRig(message_frame({"id": 5, "result": {}}), _WAIT_SECONDS)
        with self.assertRaises(RuntimeError) as caught:
            rig.client.method_call("Page.enable")
        self.assertEqual(
            str(caught.exception),
            "DevTools answered call 5 while call 1 was waiting",
        )

    # A ping during a call is answered with a pong.
    def test_call_ping(self) -> None:
        rig = ClientRig(
            bytes.fromhex("89026162") + message_frame({"id": 1, "result": {}}),
            _WAIT_SECONDS,
        )
        rig.client.method_call("Page.enable")
        self.assertEqual(len(rig.writes), 2)
        pong = devtools.frame_decode(io.BytesIO(rig.writes[1]).read)
        self.assertEqual(pong, devtools.SocketFrame(True, 0xA, b"ab"))

    # A call nothing answers fails when its timer ends, naming the method.
    def test_call_timeout(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        writes: list[bytes] = []
        events: list[dict[str, Any]] = []
        client = devtools.ProtocolClient(
            functools.partial(devtools.pipe_read, read_fd),
            writes.append,
            events.append,
            _EXPIRY_SECONDS,
        )
        with self.assertRaises(TimeoutError) as caught:
            client.method_call("Page.navigate")
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for the reply to"
            " Page.navigate",
        )
        self.assertEqual(len(writes), 1)

    # Events are passed on until the condition holds.
    def test_pump_events(self) -> None:
        first = {"method": "A.one", "params": {}}
        second = {"method": "A.two", "params": {}}
        rig = ClientRig(
            message_frame(first) + message_frame(second), _WAIT_SECONDS
        )
        rig.client.events_pump("two events", lambda: len(rig.events) == 2)
        self.assertEqual(rig.events, [first, second])

    # A reply while no call waits fails loud.
    def test_pump_reply(self) -> None:
        rig = ClientRig(message_frame({"id": 1, "result": {}}), _WAIT_SECONDS)
        with self.assertRaises(RuntimeError) as caught:
            rig.client.events_pump("an event", lambda: False)
        self.assertEqual(
            str(caught.exception),
            "DevTools answered call 1 while no call was waiting",
        )

    # An event that never comes fails when its timer ends.
    def test_pump_timeout(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        events: list[dict[str, Any]] = []
        client = devtools.ProtocolClient(
            functools.partial(devtools.pipe_read, read_fd),
            lambda data: None,
            events.append,
            _EXPIRY_SECONDS,
        )
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for a load",
        )

    # Returns a client on a pipe nothing is written to, keeping its writes.
    def client_idle(
        self, wait_seconds: float, writes: list[bytes]
    ) -> devtools.ProtocolClient:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        return devtools.ProtocolClient(
            functools.partial(devtools.pipe_read, read_fd),
            writes.append,
            lambda message: None,
            wait_seconds,
        )

    # A deadline before the client's own wait ends a call, naming the call.
    def test_deadline_first(self) -> None:
        writes: list[bytes] = []
        client = self.client_idle(_WAIT_SECONDS, writes)
        client.deadline_set(time.monotonic() + _EXPIRY_SECONDS)
        with self.assertRaises(TimeoutError) as caught:
            client.method_call("Page.navigate")
        self.assertEqual(
            str(caught.exception),
            "gave up at the deadline waiting for the reply to Page.navigate",
        )
        self.assertEqual(len(writes), 1)

    # A deadline after the client's own wait leaves that wait as it is.
    def test_deadline_later(self) -> None:
        client = self.client_idle(_EXPIRY_SECONDS, [])
        client.deadline_set(time.monotonic() + _WAIT_SECONDS)
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for a load",
        )

    # A deadline already passed ends a later wait at once.
    def test_deadline_passed(self) -> None:
        client = self.client_idle(_WAIT_SECONDS, [])
        client.deadline_set(time.monotonic())
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        self.assertEqual(
            str(caught.exception), "gave up at the deadline waiting for a load"
        )


# What the page's events and exceptions are turned into.
class TestPage(unittest.TestCase):
    # A lifecycle event is kept by loader and name, other events are ignored.
    def test_lifecycle_kept(self) -> None:
        events = devtools.PageEvents()
        events.message_handle(
            {
                "method": "Page.lifecycleEvent",
                "params": {"loaderId": "L", "name": "load"},
            }
        )
        events.message_handle({"method": "Page.frameNavigated", "params": {}})
        self.assertEqual(events.lifecycle, {("L", "load")})

    # A console message reaches every follower as its text.
    def test_console_followed(self) -> None:
        events = devtools.PageEvents()
        first: list[str] = []
        second: list[str] = []
        events.followers.append(first.append)
        events.followers.append(second.append)
        events.message_handle(
            {
                "method": "Runtime.consoleAPICalled",
                "params": {
                    "type": "log",
                    "args": [
                        {"type": "string", "value": "ok 1 - x"},
                        {"type": "number", "value": 2, "description": "2"},
                    ],
                },
            }
        )
        self.assertEqual(first, ["ok 1 - x 2"])
        self.assertEqual(second, ["ok 1 - x 2"])

    # Each kind of console argument becomes text.
    def test_console_values(self) -> None:
        args: list[dict[str, Any]] = [
            {"type": "string", "value": chr(0x4E2D)},
            {"type": "number", "value": 2.5},
            {"type": "boolean", "value": True},
            {"type": "object", "subtype": "null", "value": None},
            {"type": "undefined"},
            {
                "type": "number",
                "unserializableValue": "NaN",
                "description": "NaN",
            },
            {"type": "object", "className": "Object", "description": "Object"},
        ]
        self.assertEqual(
            devtools.console_text(args),
            chr(0x4E2D) + " 2.5 true null undefined NaN Object",
        )

    # An Error's description is its message and its stack, and is all given.
    def test_exception_error(self) -> None:
        description = "Error: boom\n    at <anonymous>:1:7"
        details: dict[str, Any] = {
            "text": "Uncaught",
            "exception": {
                "type": "object",
                "subtype": "error",
                "description": description,
            },
        }
        self.assertEqual(devtools.exception_text(details), description)

    # A thrown value gets its text and its stack frames, numbered from 1.
    def test_exception_value(self) -> None:
        frames = [
            {
                "functionName": "run",
                "url": "http://x/",
                "lineNumber": 2,
                "columnNumber": 4,
            },
            {
                "functionName": "",
                "url": "",
                "lineNumber": 0,
                "columnNumber": 6,
            },
        ]
        details: dict[str, Any] = {
            "text": "Uncaught",
            "exception": {"type": "string", "value": "boom"},
            "stackTrace": {"callFrames": frames},
        }
        self.assertEqual(
            devtools.exception_text(details),
            'Uncaught "boom"\n    at run (http://x/:3:5)\n'
            "    at <anonymous> (:1:7)",
        )

    # An exception with nothing but its text gives that text.
    def test_exception_bare(self) -> None:
        self.assertEqual(
            devtools.exception_text({"text": "Script error"}), "Script error"
        )


# The synchronous loads picked out of a trace, and the trace's events kept.
class TestTrace(unittest.TestCase):
    # A load on a renderer's main thread is found, on any other it is not.
    def test_find_main(self) -> None:
        events = [
            thread_metadata(1, 10, "CrRendererMain"),
            thread_metadata(1, 11, "DedicatedWorker thread"),
            thread_metadata(2, 20, "CrBrowserMain"),
            thread_span(1, 10, "URLLoader::loadSynchronously"),
            thread_span(1, 11, "URLLoader::loadSynchronously"),
            thread_span(2, 20, "URLLoader::loadSynchronously"),
            thread_span(1, 10, "ResourceSendRequest"),
        ]
        self.assertEqual(devtools.blocking_find(events), [events[3]])

    # Each name Chrome's versions give a synchronous load is found.
    def test_find_names(self) -> None:
        names = (
            "URLLoader::loadSynchronously",
            "WebURLLoader::loadSynchronously",
            "WebURLLoaderImpl::loadSynchronously",
        )
        for name in names:
            load = thread_span(1, 10, name)
            events = [thread_metadata(1, 10, "CrRendererMain"), load]
            self.assertEqual(devtools.blocking_find(events), [load], msg=name)

    # The main threads of two renderers both count.
    def test_find_renderers(self) -> None:
        events = [
            thread_metadata(1, 10, "CrRendererMain"),
            thread_metadata(3, 30, "CrRendererMain"),
            thread_span(1, 10, "URLLoader::loadSynchronously"),
            thread_span(3, 30, "URLLoader::loadSynchronously"),
        ]
        self.assertEqual(devtools.blocking_find(events), events[2:])

    # A main thread that ran no synchronous load gives nothing.
    def test_find_none(self) -> None:
        events = [
            thread_metadata(1, 10, "CrRendererMain"),
            thread_span(1, 10, "ResourceSendRequest"),
        ]
        self.assertEqual(devtools.blocking_find(events), [])

    # A trace that names no renderer's main thread fails loud.
    def test_find_unnamed(self) -> None:
        events = [
            thread_metadata(2, 20, "CrBrowserMain"),
            thread_span(2, 20, "URLLoader::loadSynchronously"),
        ]
        with self.assertRaises(RuntimeError) as caught:
            devtools.blocking_find(events)
        self.assertEqual(
            str(caught.exception), "the trace names no CrRendererMain thread"
        )

    # Trace data is joined in order, and its end is kept with its loss.
    def test_data_joined(self) -> None:
        events = devtools.PageEvents()
        first = thread_metadata(1, 10, "CrRendererMain")
        second = thread_span(1, 10, "ResourceSendRequest")
        third = thread_span(1, 10, "ResourceFinish")
        events.message_handle(trace_data([first, second]))
        events.message_handle(trace_data([third]))
        self.assertFalse(events.trace_done)
        events.message_handle(trace_complete(True))
        self.assertEqual(events.trace, [first, second, third])
        self.assertTrue(events.trace_done)
        self.assertTrue(events.trace_lost)


# The workers attached from the page and the pauses of their debuggers.
class TestWorkers(unittest.TestCase):
    # An attached worker is kept by its title, and an attached page is not.
    def test_worker_attached(self) -> None:
        events = devtools.PageEvents()
        events.message_handle(attach_event("page", "Q", "about:blank"))
        events.message_handle(attach_event("worker", "W", "ai"))
        self.assertEqual(events.workers, {"ai": "W"})

    # A pause is kept by the session it came on.
    def test_pause_kept(self) -> None:
        events = devtools.PageEvents()
        events.message_handle(paused_event("W"))
        self.assertEqual(events.paused, {"W"})

    # A detached worker is forgotten with its pause, and the others stay.
    def test_worker_detached(self) -> None:
        events = devtools.PageEvents()
        events.message_handle(attach_event("worker", "W", "ai"))
        events.message_handle(attach_event("worker", "V", "other"))
        events.message_handle(paused_event("W"))
        events.message_handle(paused_event("V"))
        events.message_handle(
            {
                "method": "Target.detachedFromTarget",
                "sessionId": "P",
                "params": {"sessionId": "W", "targetId": "TW"},
            }
        )
        self.assertEqual(events.workers, {"other": "V"})
        self.assertEqual(events.paused, {"V"})


# A browser's page calls and waits, on canned bytes and a scratch profile.
class TestBrowser(unittest.TestCase):
    # Makes the scratch directory a profile is in.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch_path = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )

    # Returns a browser waiting on a port file that holds the text.
    def browser_waiting(self, text: str) -> devtools.Browser:
        port_path = os.path.join(self.scratch_path, "DevToolsActivePort")
        with open(port_path, "w") as port_file:
            port_file.write(text)
        browser = browser_make(b"", [])
        browser.profile_path = self.scratch_path
        browser.executable_name = "chrome.exe"
        browser.browser_process = cast(
            subprocess.Popen[bytes], RunningProcess()
        )
        return browser

    # A refused navigation is sent again until one loads.
    def test_open_refused(self) -> None:
        loaded = {"frameId": "F", "loaderId": "L1"}
        event = {
            "method": "Page.lifecycleEvent",
            "params": {"loaderId": "L1", "name": "load"},
        }
        writes: list[bytes] = []
        browser = browser_make(
            message_frame({"id": 1, "result": _REFUSED_RESULT})
            + message_frame({"id": 2, "result": loaded})
            + message_frame(event),
            writes,
        )
        browser.page_open("http://u/")
        self.assertEqual(
            [request_decode(write) for write in writes],
            [
                {
                    "id": call_id,
                    "method": "Page.navigate",
                    "params": {"url": "http://u/"},
                }
                for call_id in (1, 2)
            ],
        )

    # Any other navigation error fails at once.
    def test_open_error(self) -> None:
        failed = {"errorText": "net::ERR_NAME_NOT_RESOLVED", "loaderId": "L0"}
        writes: list[bytes] = []
        browser = browser_make(
            message_frame({"id": 1, "result": failed}), writes
        )
        with self.assertRaises(RuntimeError) as caught:
            browser.page_open("http://u/")
        self.assertEqual(
            str(caught.exception), "http://u/: net::ERR_NAME_NOT_RESOLVED"
        )
        self.assertEqual(len(writes), 1)

    # A navigation refused until its timer ends fails, naming the URL.
    def test_open_timeout(self) -> None:
        writes: list[bytes] = []
        browser = browser_make(
            message_frame({"id": 1, "result": _REFUSED_RESULT}), writes
        )
        with (
            unittest.mock.patch.object(devtools, "_SERVER_WAIT_SECONDS", 0),
            self.assertRaises(TimeoutError) as caught,
        ):
            browser.page_open("http://u/")
        self.assertEqual(
            str(caught.exception),
            "gave up after 0 s waiting for http://u/ to accept connections"
            " after net::ERR_CONNECTION_REFUSED",
        )
        self.assertEqual(len(writes), 1)

    # Closing the page names its target and reads nothing of the result.
    def test_close_target(self) -> None:
        writes: list[bytes] = []
        browser = browser_make(message_frame({"id": 1, "result": {}}), writes)
        browser.target_id = "T"
        browser.page_close()
        self.assertEqual(
            request_decode(writes[0]),
            {
                "id": 1,
                "method": "Target.closeTarget",
                "params": {"targetId": "T"},
            },
        )

    # A port file with fewer than two fields is still being written.
    def test_port_partial(self) -> None:
        for text in ("", "9222", "9222\n"):
            browser = self.browser_waiting(text)
            with (
                unittest.mock.patch.object(
                    devtools, "_DEVTOOLS_WAIT_SECONDS", 0
                ),
                self.assertRaises(TimeoutError, msg=repr(text)) as caught,
            ):
                browser.devtools_wait()
            self.assertEqual(
                str(caught.exception),
                "gave up after 0 s waiting for chrome.exe to serve DevTools",
            )

    # A port file with a port and a path gives the address.
    def test_port_written(self) -> None:
        browser = self.browser_waiting("9222\n/devtools/browser/abc")
        self.assertEqual(
            browser.devtools_wait(),
            devtools.EndpointAddress(9222, "/devtools/browser/abc"),
        )

    # A profile a helper still holds is removed once it lets go.
    def test_remove_busy(self) -> None:
        browser = browser_make(b"", [])
        browser.profile_path = self.scratch_path
        held = PermissionError(errno.EACCES, "Permission denied")
        with unittest.mock.patch(
            "shutil.rmtree", side_effect=[held, None]
        ) as rmtree:
            browser.profile_remove()
        self.assertEqual(rmtree.call_count, 2)

    # A profile held past its timer fails, with the last error as context.
    def test_remove_timeout(self) -> None:
        browser = browser_make(b"", [])
        browser.profile_path = self.scratch_path
        held = PermissionError(errno.EACCES, "Permission denied")
        with (
            unittest.mock.patch.object(devtools, "_PROFILE_REMOVE_SECONDS", 0),
            unittest.mock.patch("shutil.rmtree", side_effect=held),
            self.assertRaises(TimeoutError) as caught,
        ):
            browser.profile_remove()
        self.assertEqual(
            str(caught.exception),
            f"gave up after 0 s waiting for {self.scratch_path} to be"
            " removable",
        )
        self.assertIs(caught.exception.__context__, held)

    # Any other error of the removal fails at once.
    def test_remove_failed(self) -> None:
        browser = browser_make(b"", [])
        browser.profile_path = self.scratch_path
        failed = OSError(errno.EIO, "Input/output error")
        with (
            unittest.mock.patch("shutil.rmtree", side_effect=failed) as rmtree,
            self.assertRaises(OSError) as caught,
        ):
            browser.profile_remove()
        self.assertIs(caught.exception, failed)
        self.assertEqual(rmtree.call_count, 1)

    # A trace starts afresh on the page, its categories reported as events.
    def test_trace_start(self) -> None:
        writes: list[bytes] = []
        browser = browser_make(message_frame({"id": 1, "result": {}}), writes)
        browser.client_get().session_id = "P"
        browser.events.trace = [thread_metadata(1, 10, "CrRendererMain")]
        browser.events.trace_done = True
        browser.events.trace_lost = True
        browser.trace_start(devtools.blocking_categories())
        self.assertEqual(
            request_decode(writes[0]),
            {
                "id": 1,
                "method": "Tracing.start",
                "params": {
                    "transferMode": "ReportEvents",
                    "traceConfig": {
                        "includedCategories": ["loading", "__metadata"],
                    },
                },
                "sessionId": "P",
            },
        )
        self.assertEqual(browser.events.trace, [])
        self.assertFalse(browser.events.trace_done)
        self.assertFalse(browser.events.trace_lost)

    # Ending a trace returns every event sent until the trace completed.
    def test_trace_end(self) -> None:
        name = thread_metadata(1, 10, "CrRendererMain")
        load = thread_span(1, 10, "URLLoader::loadSynchronously")
        writes: list[bytes] = []
        browser = browser_make(
            message_frame({"id": 1, "result": {}})
            + message_frame(trace_data([name]))
            + message_frame(trace_data([load]))
            + message_frame(trace_complete(False)),
            writes,
        )
        browser.client_get().session_id = "P"
        self.assertEqual(browser.trace_end(), [name, load])
        self.assertEqual(
            request_decode(writes[0]),
            {
                "id": 1,
                "method": "Tracing.end",
                "params": {},
                "sessionId": "P",
            },
        )

    # A trace that lost events fails loud.
    def test_trace_lost(self) -> None:
        browser = browser_make(
            message_frame({"id": 1, "result": {}})
            + message_frame(trace_complete(True)),
            [],
        )
        with self.assertRaises(RuntimeError) as caught:
            browser.trace_end()
        self.assertEqual(
            str(caught.exception),
            "the trace lost events, so it can't show everything that ran",
        )

    # The worker is attached from the page, its debugger enabled and paused.
    def test_worker_pause(self) -> None:
        writes: list[bytes] = []
        browser = browser_make(
            message_frame(attach_event("worker", "V", "other"))
            + message_frame({"id": 1, "result": {}})
            + message_frame(attach_event("worker", "W", "ai"))
            + message_frame({"id": 2, "result": {"debuggerId": "D"}})
            + message_frame({"id": 3, "result": {}})
            + message_frame(paused_event("W")),
            writes,
        )
        browser.client_get().session_id = "P"
        browser.worker_pause("ai")
        self.assertEqual(
            [request_decode(write) for write in writes],
            [
                {
                    "id": 1,
                    "method": "Target.setAutoAttach",
                    "params": {
                        "autoAttach": True,
                        "waitForDebuggerOnStart": False,
                        "flatten": True,
                    },
                    "sessionId": "P",
                },
                {
                    "id": 2,
                    "method": "Debugger.enable",
                    "params": {},
                    "sessionId": "W",
                },
                {
                    "id": 3,
                    "method": "Debugger.pause",
                    "params": {},
                    "sessionId": "W",
                },
            ],
        )
