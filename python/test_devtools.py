# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of devtools.py that need no browser: WebSocket frames with
# and without masks, the handshake, joining a message from its fragments, the
# relay script and the PowerShell arguments, the DevTools address, the
# timers, a client on real pipes, filled before it reads or never written
# to, a descriptor moved above the Linux browser's 3 and 4, the synchronous
# loads picked out of a trace, and the page's loads, trace, workers and
# pauses kept. Every byte a function reads, and every
# frame a client writes, rides a real pipe, and a pipe in packet mode gives
# the short reads. No process is started. The waits the tests give and the
# size of a pipe are the gold's.

import devtools, errno, fcntl, functools, harness, json, os, time, unittest
from collections.abc import Callable
from typing import Any, BinaryIO

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_devtools"

# A wait no test reaches the end of, for the replies the bytes hold.
_WAIT_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.wait_seconds")

# A wait that ends soon, for the replies and events that never come.
_EXPIRY_SECONDS: float = harness.gold_get(f"{_GOLD_ID}.expiry_seconds")

# A size chosen by its writer: a pipe's buffer, room for all a test writes.
_PIPE_BYTES: int = harness.gold_get(f"{_GOLD_ID}.pipe_bytes")

# The flags of a pipe, closed across an exec as `os.pipe` makes one.
_PIPE_FLAGS = os.O_CLOEXEC

# The flags of a pipe in packet mode, where a read takes one write at most.
_PACKET_FLAGS = os.O_CLOEXEC | os.O_DIRECT

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
def request_decode(frame: devtools.SocketFrame) -> dict[str, Any]:
    request: dict[str, Any] = json.loads(frame.payload)
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


# Gives each test real pipes, each end closed when the test ends.
class PipeCase(unittest.TestCase):
    # The read end of the pipe a client writes to, and the file it writes by.
    written_fd: int
    writer: BinaryIO

    # Returns the read end of a pipe of the flags holding the chunks, ended.
    def pipe_filled(self, chunks: list[bytes], flags: int) -> int:
        read_fd, write_fd = os.pipe2(flags)
        self.addCleanup(os.close, read_fd)
        with open(write_fd, "wb", buffering=0) as pipe_file:
            fcntl.fcntl(write_fd, fcntl.F_SETPIPE_SZ, _PIPE_BYTES)
            for chunk in chunks:
                self.assertEqual(pipe_file.write(chunk), len(chunk))
        return read_fd

    # Returns a reader of a pipe that holds the bytes, its write end closed.
    def reader_filled(self, data: bytes) -> Callable[[int], bytes]:
        read_fd = self.pipe_filled([data], _PIPE_FLAGS)
        return functools.partial(os.read, read_fd)

    # Returns the read end of a pipe nothing is written to, its writer open.
    def pipe_idle(self) -> int:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, read_fd)
        self.addCleanup(os.close, write_fd)
        return read_fd

    # Returns a WebSocket channel reading the descriptor, writing a new pipe.
    def channel_make(self, read_fd: int) -> devtools.SocketChannel:
        self.written_fd, write_fd = os.pipe()
        self.addCleanup(os.close, self.written_fd)
        self.writer = open(write_fd, "wb")
        self.addCleanup(self.writer.close)
        return devtools.SocketChannel(
            functools.partial(devtools.pipe_read, read_fd),
            functools.partial(devtools.stream_write, self.writer),
        )

    # Returns a client on a channel reading the descriptor, its events kept.
    def client_make(
        self, read_fd: int, wait_seconds: float, events: list[dict[str, Any]]
    ) -> devtools.ProtocolClient:
        return devtools.ProtocolClient(
            self.channel_make(read_fd), events.append, wait_seconds
        )

    # Returns a client reading the bytes from a pipe, its events kept.
    def client_filled(
        self, data: bytes, wait_seconds: float, events: list[dict[str, Any]]
    ) -> devtools.ProtocolClient:
        read_fd = self.pipe_filled([data], _PIPE_FLAGS)
        return self.client_make(read_fd, wait_seconds, events)

    # Returns a client on a pipe nothing is written to, its events kept.
    def client_idle(
        self, wait_seconds: float, events: list[dict[str, Any]]
    ) -> devtools.ProtocolClient:
        return self.client_make(self.pipe_idle(), wait_seconds, events)

    # Returns the frames the client wrote, which must be all it wrote.
    def frames_written(self, count: int) -> list[devtools.SocketFrame]:
        self.writer.close()
        read = functools.partial(os.read, self.written_fd)
        frames = [devtools.frame_decode(read) for _ in range(count)]
        self.assertEqual(os.read(self.written_fd, 1), b"")
        return frames


# Frames encode and decode as RFC 6455 says, with and without masks.
class TestFrames(PipeCase):
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
        frame = devtools.frame_decode(self.reader_filled(_HELLO_PLAIN))
        self.assertEqual(frame, devtools.SocketFrame(True, 0x1, b"Hello"))

    # A masked frame is unmasked.
    def test_decode_masked(self) -> None:
        frame = devtools.frame_decode(self.reader_filled(_HELLO_MASKED))
        self.assertEqual(frame, devtools.SocketFrame(True, 0x1, b"Hello"))

    # Lengths of 2 bytes and of 8 bytes decode.
    def test_decode_lengths(self) -> None:
        medium = bytes(index % 251 for index in range(300))
        data = b"\x81\x7e" + (300).to_bytes(2, "big") + medium
        frame = devtools.frame_decode(self.reader_filled(data))
        self.assertEqual(frame.payload, medium)
        large = bytes(index % 251 for index in range(70000))
        data = b"\x81\x7f" + (70000).to_bytes(8, "big") + large
        frame = devtools.frame_decode(self.reader_filled(data))
        self.assertEqual(frame.payload, large)

    # A frame encoded with a mask decodes to its payload.
    def test_decode_cycle(self) -> None:
        payload = bytes(index % 251 for index in range(70000))
        frame = devtools.frame_encode(0x1, payload, bytes([9, 8, 7, 6]))
        decoded = devtools.frame_decode(self.reader_filled(frame))
        self.assertEqual(decoded, devtools.SocketFrame(True, 0x1, payload))

    # A fragment that doesn't end its message decodes with its flag clear.
    def test_decode_fragment(self) -> None:
        read = self.reader_filled(bytes.fromhex("010348656c80026c6f"))
        first = devtools.frame_decode(read)
        second = devtools.frame_decode(read)
        self.assertEqual(first, devtools.SocketFrame(False, 0x1, b"Hel"))
        self.assertEqual(second, devtools.SocketFrame(True, 0x0, b"lo"))

    # A frame cut short fails loud.
    def test_decode_short(self) -> None:
        with self.assertRaises(ConnectionError) as caught:
            devtools.frame_decode(self.reader_filled(_HELLO_PLAIN[:-1]))
        self.assertEqual(
            str(caught.exception), "DevTools closed the connection"
        )


# A message is joined from its frames, with pings answered on the way.
class TestMessages(PipeCase):
    # Returns the message read from the frames and the frames sent meanwhile.
    def frames_read(
        self, frames: str, sent: int
    ) -> tuple[bytes, list[devtools.SocketFrame]]:
        channel = self.channel_make(self.pipe_idle())
        message = devtools.message_read(
            self.reader_filled(bytes.fromhex(frames)), channel.frame_send
        )
        return message, self.frames_written(sent)

    # A message in one frame is returned as it is.
    def test_read_single(self) -> None:
        self.assertEqual(self.frames_read("810548656c6c6f", 0), (b"Hello", []))

    # Fragments are joined, as in RFC 6455's example.
    def test_read_fragments(self) -> None:
        message, sent = self.frames_read("010348656c80026c6f", 0)
        self.assertEqual(message, b"Hello")
        self.assertEqual(sent, [])

    # A ping is answered with a pong holding its payload.
    def test_read_ping(self) -> None:
        message, sent = self.frames_read("89026162" + "81017a", 1)
        self.assertEqual(message, b"z")
        self.assertEqual(sent, [devtools.SocketFrame(True, 0xA, b"ab")])

    # A pong is ignored.
    def test_read_pong(self) -> None:
        self.assertEqual(self.frames_read("8a00" + "81017a", 0), (b"z", []))

    # A ping between fragments is answered and the fragments still join.
    def test_read_between(self) -> None:
        message, sent = self.frames_read("010161" + "8900" + "800162", 1)
        self.assertEqual(message, b"ab")
        self.assertEqual(sent, [devtools.SocketFrame(True, 0xA, b"")])

    # A close frame fails loud.
    def test_read_close(self) -> None:
        with self.assertRaises(ConnectionError) as caught:
            self.frames_read("8800", 0)
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
                self.frames_read(frames, 0)
            self.assertEqual(str(caught.exception), message)


# The WebSocket upgrade request and its answer.
class TestHandshake(PipeCase):
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
        read_fd = self.pipe_filled([_ACCEPT_HEAD + b"rest"], _PIPE_FLAGS)
        read = functools.partial(os.read, read_fd)
        self.assertEqual(devtools.head_read(read), _ACCEPT_HEAD)
        self.assertEqual(os.read(read_fd, _PIPE_BYTES), b"rest")


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
class TestTimers(PipeCase):
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
        read_fd = self.pipe_filled([b"a", b"b", b"c"], _PACKET_FLAGS)
        read = functools.partial(os.read, read_fd)
        self.assertEqual(devtools.bytes_exact(read, 3), b"abc")

    # A reader that runs dry first fails loud.
    def test_bytes_short(self) -> None:
        read_fd = self.pipe_filled([b"a", b"b"], _PACKET_FLAGS)
        read = functools.partial(os.read, read_fd)
        with self.assertRaises(ConnectionError) as caught:
            devtools.bytes_exact(read, 3)
        self.assertEqual(
            str(caught.exception), "DevTools closed the connection"
        )


# A pipe's end moved above 4, so that the Linux browser's 3 and 4 are copies.
class TestDescriptors(unittest.TestCase):
    # The end moves above 4, closed at an exec, and the old number closes.
    def test_raise_above(self) -> None:
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, write_fd)
        raised = devtools.descriptor_raise(read_fd)
        self.addCleanup(os.close, raised)
        self.assertGreater(raised, 4)
        self.assertFalse(os.get_inheritable(raised))
        with self.assertRaises(OSError) as caught:
            os.fstat(read_fd)
        self.assertEqual(caught.exception.errno, errno.EBADF)
        os.write(write_fd, b"a")
        self.assertEqual(os.read(raised, 1), b"a")


# The protocol client's calls, events and timers, on real pipes.
class TestClient(PipeCase):
    # A reply is matched by its id and events before it are passed on.
    def test_call_reply(self) -> None:
        event: dict[str, Any] = {"method": "Page.frameNavigated", "params": {}}
        reply = {"id": 1, "result": {"frameId": "F"}}
        events: list[dict[str, Any]] = []
        client = self.client_filled(
            message_frame(event) + message_frame(reply), _WAIT_SECONDS, events
        )
        result = client.method_call("Page.navigate", {"url": "u"})
        self.assertEqual(result, {"frameId": "F"})
        self.assertEqual(events, [event])
        request = request_decode(self.frames_written(1)[0])
        self.assertEqual(
            request,
            {"id": 1, "method": "Page.navigate", "params": {"url": "u"}},
        )

    # A call on a named session carries it, even for a target method.
    def test_call_named(self) -> None:
        client = self.client_filled(
            message_frame({"id": 1, "result": {}})
            + message_frame({"id": 2, "result": {}}),
            _WAIT_SECONDS,
            [],
        )
        client.session_call("W", "Target.setAutoAttach", {"flatten": True})
        client.session_call("", "Runtime.enable")
        first, second = self.frames_written(2)
        self.assertEqual(
            request_decode(first),
            {
                "id": 1,
                "method": "Target.setAutoAttach",
                "params": {"flatten": True},
                "sessionId": "W",
            },
        )
        self.assertNotIn("sessionId", request_decode(second))

    # An error reply fails loud with the method and DevTools' message.
    def test_call_error(self) -> None:
        error = {"code": -32601, "message": "nope"}
        client = self.client_filled(
            message_frame({"id": 1, "error": error}), _WAIT_SECONDS, []
        )
        with self.assertRaises(RuntimeError) as caught:
            client.method_call("Page.enable")
        self.assertEqual(str(caught.exception), "Page.enable: nope")

    # A reply to another call fails loud.
    def test_call_mismatch(self) -> None:
        client = self.client_filled(
            message_frame({"id": 5, "result": {}}), _WAIT_SECONDS, []
        )
        with self.assertRaises(RuntimeError) as caught:
            client.method_call("Page.enable")
        self.assertEqual(
            str(caught.exception),
            "DevTools answered call 5 while call 1 was waiting",
        )

    # A ping during a call is answered with a pong.
    def test_call_ping(self) -> None:
        client = self.client_filled(
            bytes.fromhex("89026162") + message_frame({"id": 1, "result": {}}),
            _WAIT_SECONDS,
            [],
        )
        client.method_call("Page.enable")
        pong = self.frames_written(2)[1]
        self.assertEqual(pong, devtools.SocketFrame(True, 0xA, b"ab"))

    # A call nothing answers fails when its timer ends, naming the method.
    def test_call_timeout(self) -> None:
        client = self.client_idle(_EXPIRY_SECONDS, [])
        with self.assertRaises(TimeoutError) as caught:
            client.method_call("Page.navigate")
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for the reply to"
            " Page.navigate",
        )
        request = request_decode(self.frames_written(1)[0])
        self.assertEqual(
            request, {"id": 1, "method": "Page.navigate", "params": {}}
        )

    # Events are passed on until the condition holds.
    def test_pump_events(self) -> None:
        first: dict[str, Any] = {"method": "A.one", "params": {}}
        second: dict[str, Any] = {"method": "A.two", "params": {}}
        events: list[dict[str, Any]] = []
        client = self.client_filled(
            message_frame(first) + message_frame(second), _WAIT_SECONDS, events
        )
        client.events_pump("two events", lambda: len(events) == 2)
        self.assertEqual(events, [first, second])

    # A reply while no call waits fails loud.
    def test_pump_reply(self) -> None:
        client = self.client_filled(
            message_frame({"id": 1, "result": {}}), _WAIT_SECONDS, []
        )
        with self.assertRaises(RuntimeError) as caught:
            client.events_pump("an event", lambda: False)
        self.assertEqual(
            str(caught.exception),
            "DevTools answered call 1 while no call was waiting",
        )

    # An event that never comes fails when its timer ends.
    def test_pump_timeout(self) -> None:
        client = self.client_idle(_EXPIRY_SECONDS, [])
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        self.assertEqual(
            str(caught.exception),
            f"gave up after {_EXPIRY_SECONDS:g} s waiting for a load",
        )

    # A deadline before the client's own wait ends a call, naming the call.
    def test_deadline_first(self) -> None:
        client = self.client_idle(_WAIT_SECONDS, [])
        client.deadline_set(time.monotonic() + _EXPIRY_SECONDS)
        with self.assertRaises(TimeoutError) as caught:
            client.method_call("Page.navigate")
        self.assertEqual(
            str(caught.exception),
            "gave up at the deadline waiting for the reply to Page.navigate",
        )
        request = request_decode(self.frames_written(1)[0])
        self.assertEqual(
            request, {"id": 1, "method": "Page.navigate", "params": {}}
        )

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

    # A limit ends a wait at its end alone, past the client's own wait.
    def test_limit_alone(self) -> None:
        client = self.client_idle(_EXPIRY_SECONDS, [])
        started = time.monotonic()
        client.limit_set(started + 2 * _EXPIRY_SECONDS)
        with self.assertRaises(TimeoutError) as caught:
            client.events_pump("a load", lambda: False)
        waited = time.monotonic() - started
        self.assertGreaterEqual(waited, 2 * _EXPIRY_SECONDS)
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
