# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of devtools.py that need no browser: WebSocket frames with
# and without masks, the handshake, joining a message from its fragments, the
# relay script, the DevTools address, the timers, and a client reading canned
# bytes or an empty pipe. No process is started.

import devtools, functools, io, json, os, unittest
from typing import Any

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


# Returns the frame a server sends for a DevTools message.
def message_frame(message: dict[str, Any]) -> bytes:
    payload = json.dumps(message).encode()
    return devtools.frame_encode(0x1, payload, _ZERO_MASK)


# Returns the DevTools request inside a frame the client wrote.
def request_decode(frame: bytes) -> dict[str, Any]:
    decoded = devtools.frame_decode(io.BytesIO(frame).read)
    request: dict[str, Any] = json.loads(decoded.payload)
    return request


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
        with self.assertRaises(ConnectionError):
            devtools.frame_decode(io.BytesIO(_HELLO_PLAIN[:-1]).read)


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
        with self.assertRaises(ConnectionError):
            self.frames_read("8800")

    # A frame out of order, or of an opcode DevTools doesn't use, fails loud.
    def test_read_order(self) -> None:
        for frames in ("800161", "010161" + "810162", "820161"):
            with self.assertRaises(ConnectionError):
                self.frames_read(frames)


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
        for head in (b"HTTP/1.1 400 Bad Request\r\n\r\n", b""):
            with self.assertRaises(ConnectionError):
                devtools.handshake_check(_SAMPLE_KEY, head)

    # A wrong accept value, or none, fails loud.
    def test_check_key(self) -> None:
        wrong = _ACCEPT_HEAD.replace(b"s3pPLM", b"S3pPLM")
        missing = b"HTTP/1.1 101 Switching Protocols\r\n\r\n"
        for head in (wrong, missing):
            with self.assertRaises(ConnectionError):
                devtools.handshake_check(_SAMPLE_KEY, head)

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
        for text in ("", "9222", "9222\n/a\n/b", "port\n/a"):
            with self.assertRaises(ValueError):
                devtools.address_parse(text)


# The scripts and arguments handed to PowerShell.
class TestScripts(unittest.TestCase):
    # The relay script sets the port first and has its here string whole.
    def test_relay_port(self) -> None:
        script = devtools.relay_script(1234)
        self.assertTrue(script.startswith("$port_ = 1234\n"))
        self.assertIn("Add-Type -TypeDefinition @'\n", script)
        self.assertIn("\n'@\n", script)
        self.assertIn("[XsjsDevToolsRelay]::Run($port_)", script)

    # The relay script is plain ASCII with LF line ends.
    def test_relay_ascii(self) -> None:
        script = devtools.relay_script(1)
        self.assertTrue(script.isascii())
        self.assertNotIn("\r", script)

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
        left = devtools.WaitTimer("the thing", 1000).seconds_left()
        self.assertGreater(left, 0)
        self.assertLessEqual(left, 1000)

    # A pipe nothing is written to fails when its timer ends.
    def test_pipe_timeout(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        timer = devtools.WaitTimer("bytes that never come", 0.05)
        with self.assertRaises(TimeoutError) as caught:
            devtools.pipe_read(read_fd, timer, 1)
        self.assertEqual(
            str(caught.exception),
            "gave up after 0.05 s waiting for bytes that never come",
        )

    # A pipe gives no more than the count asked for.
    def test_pipe_read(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        os.write(write_fd, b"abc")
        timer = devtools.WaitTimer("bytes", 60)
        self.assertEqual(devtools.pipe_read(read_fd, timer, 2), b"ab")
        self.assertEqual(devtools.pipe_read(read_fd, timer, 2), b"c")

    # A pipe whose writer is gone reads as empty.
    def test_pipe_ended(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        os.close(write_fd)
        timer = devtools.WaitTimer("bytes", 60)
        self.assertEqual(devtools.pipe_read(read_fd, timer, 4), b"")

    # Short reads are joined until the count is reached.
    def test_bytes_joined(self) -> None:
        stream = io.BytesIO(b"abc")
        data = devtools.bytes_exact(lambda count: stream.read(1), 3)
        self.assertEqual(data, b"abc")

    # A reader that runs dry first fails loud.
    def test_bytes_short(self) -> None:
        stream = io.BytesIO(b"ab")
        with self.assertRaises(ConnectionError):
            devtools.bytes_exact(lambda count: stream.read(1), 3)


# The protocol client's calls, events and timers, on canned bytes or a pipe.
class TestClient(unittest.TestCase):
    # A reply is matched by its id and events before it are passed on.
    def test_call_reply(self) -> None:
        event = {"method": "Page.frameNavigated", "params": {}}
        reply = {"id": 1, "result": {"frameId": "F"}}
        rig = ClientRig(message_frame(event) + message_frame(reply), 60)
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
            60,
        )
        rig.client.session_id = "S"
        rig.client.method_call("Runtime.enable")
        rig.client.method_call("Target.getTargets")
        self.assertEqual(request_decode(rig.writes[0])["sessionId"], "S")
        self.assertNotIn("sessionId", request_decode(rig.writes[1]))

    # An error reply fails loud with the method and DevTools' message.
    def test_call_error(self) -> None:
        error = {"code": -32601, "message": "nope"}
        rig = ClientRig(message_frame({"id": 1, "error": error}), 60)
        with self.assertRaises(RuntimeError) as caught:
            rig.client.method_call("Page.enable")
        self.assertEqual(str(caught.exception), "Page.enable: nope")

    # A reply to another call fails loud.
    def test_call_mismatch(self) -> None:
        rig = ClientRig(message_frame({"id": 5, "result": {}}), 60)
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
            60,
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
            0.05,
        )
        with self.assertRaises(TimeoutError) as caught:
            client.method_call("Page.navigate")
        self.assertEqual(
            str(caught.exception),
            "gave up after 0.05 s waiting for the reply to Page.navigate",
        )
        self.assertEqual(len(writes), 1)

    # Events are passed on until the condition holds.
    def test_pump_events(self) -> None:
        first = {"method": "A.one", "params": {}}
        second = {"method": "A.two", "params": {}}
        rig = ClientRig(message_frame(first) + message_frame(second), 60)
        rig.client.events_pump("two events", lambda: len(rig.events) == 2)
        self.assertEqual(rig.events, [first, second])

    # A reply while no call waits fails loud.
    def test_pump_reply(self) -> None:
        rig = ClientRig(message_frame({"id": 1, "result": {}}), 60)
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
            0.05,
        )
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        self.assertEqual(
            str(caught.exception), "gave up after 0.05 s waiting for a load"
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
