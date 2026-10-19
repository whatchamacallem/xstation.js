// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire module that need no socket: ttyd's message kinds, the
// input frames, `hello`, the close fault and the console reads.

namespace test_wire {
  // The sizes of the settings, a page address and ttyd's message kinds.
  const constants = Object.freeze({
    line_max: 1048576,
    blob_max: 1073741824,
    overflow_bytes: 131072,
    chunk_bytes: 1048576,
    base_url: "http://127.0.0.1:7681/",
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    unused_sink: "No blob of these tests streams to a sink.",
  });

  // A blob sink these tests never reach, as their blobs stay in memory.
  class UnusedSink implements jslb.BlobSink {
    // Fails, as no blob streams.
    sink_open(): string {
      throw new Error(constants.unused_sink);
    }

    // Fails, as no blob streams.
    sink_append(): void {
      throw new Error(constants.unused_sink);
    }

    // Fails, as no blob streams.
    sink_close(): lines.Sha256 {
      throw new Error(constants.unused_sink);
    }
  }

  // A decoder with the sizes of the settings.
  function decoder_make(): jslb.LineDecoder {
    return new jslb.LineDecoder(
      constants.line_max,
      constants.blob_max,
      constants.overflow_bytes,
      new UnusedSink()
    );
  }

  // A wire port that is never opened.
  function port_make(): wire.WirePort {
    return new wire.WirePort(
      constants.base_url,
      constants.chunk_bytes,
      decoder_make()
    );
  }

  // The parts joined into one array of bytes.
  function bytes_join(parts: Uint8Array[]): Uint8Array {
    let total = 0;
    for (const part of parts) {
      total += part.length;
    }
    const joined = new Uint8Array(total);
    let offset = 0;
    for (const part of parts) {
      joined.set(part, offset);
      offset += part.length;
    }
    return joined;
  }

  // The encoded bytes of a line whose blobs are in memory.
  function line_bytes(line: lines.Line): Uint8Array {
    const parts: Uint8Array[] = [];
    for (const piece of jslb.line_encode(line)) {
      if (typeof piece === "string") {
        throw new Error(`The line holds the cache handle ${piece}.`);
      }
      parts.push(piece);
    }
    return bytes_join(parts);
  }

  // A message of ttyd's: the kind byte, then the body.
  function message_make(kind: number, body: Uint8Array): Uint8Array {
    return bytes_join([Uint8Array.of(kind), body]);
  }

  // A message of ttyd's of the kind with a text body.
  function message_text(kind: number, text: string): Uint8Array {
    return message_make(kind, utility.utf8_encode(text));
  }

  // An output message of ttyd's holding the text.
  function output_text(text: string): Uint8Array {
    return message_text(constants.output_kind, text);
  }

  // An output message of ttyd's holding the encoded lines.
  function output_lines(...list: lines.Line[]): Uint8Array {
    const body = bytes_join(list.map((line) => line_bytes(line)));
    return message_make(constants.output_kind, body);
  }

  // The server's `hello`, a request with id 1.
  function hello_make(): lines.Line {
    return jslb.line_make(jslb.header_make("hello", { id: 1 }), [], {
      pid: 4242,
    });
  }

  // A notification of the type with no payload.
  function notice_make(type: string): lines.Line {
    return jslb.line_make(jslb.header_make(type), [], {});
  }

  // The server's `error` line answering request 1.
  function error_make(): lines.Line {
    return jslb.line_make(jslb.header_make("error", { reply: 1 }), [], {
      message: "kv_get: /metaverse/nothing: no such key",
      stack: "Traceback (most recent call last):",
    });
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // Every frame the queue holds, in order.
  function frames_drain(frames: wire.FrameQueue): Uint8Array[] {
    const list: Uint8Array[] = [];
    while (frames.frames_left()) {
      list.push(new Uint8Array(frames.frame_next()));
    }
    return list;
  }

  // The message of the error the function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => void): string {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error.message;
      }
      throw error;
    }
    return test.fail("Nothing was thrown.");
  }

  // The input frames that carry encoded lines to the server.
  export class TestInputFrames extends unittest.TestCase {
    // A short piece goes as one frame: the input kind, then the bytes.
    test_input_prefix(): void {
      const frames = new wire.FrameQueue(16);
      frames.pieces_add([Uint8Array.of(1, 2, 3)]);
      this.assertEqual(frames_drain(frames), [
        Uint8Array.of(constants.input_kind, 1, 2, 3),
      ]);
    }

    // A large line is cut into frames of at most the chunk, piece by piece.
    test_chunk_limit(): void {
      const chunk = 4096;
      const data = new Uint8Array(10000);
      for (let index = 0; index < data.length; index += 1) {
        data[index] = index % 251;
      }
      const header = jslb.header_make("kv.put", { id: 1, key: "/m/big" });
      const line = jslb.line_make(header, [jslb.blob_make(data)], {});
      const frames = new wire.FrameQueue(chunk);
      frames.pieces_add(jslb.line_encode(line));
      const list = frames_drain(frames);
      for (const frame of list) {
        this.assertTrue(frame.length > 1 && frame.length <= chunk);
        this.assertEqual(frame[0], constants.input_kind);
      }
      const bodies = list.map((frame) => frame.subarray(1));
      this.assertEqual(bytes_join(bodies), line_bytes(line));
      const json_length = line_bytes(line).length - data.length;
      const count =
        Math.ceil(json_length / (chunk - 1)) +
        Math.ceil(data.length / (chunk - 1));
      this.assertEqual(list.length, count);
    }

    // Lines queued one after another leave in the order they came.
    test_line_order(): void {
      const frames = new wire.FrameQueue(4);
      frames.pieces_add([Uint8Array.of(1, 2, 3, 4)]);
      frames.pieces_add([Uint8Array.of(5), Uint8Array.of(6, 7)]);
      const kind = constants.input_kind;
      this.assertEqual(frames_drain(frames), [
        Uint8Array.of(kind, 1, 2, 3),
        Uint8Array.of(kind, 4),
        Uint8Array.of(kind, 5),
        Uint8Array.of(kind, 6, 7),
      ]);
    }

    // A piece of no bytes, an empty blob, sends no frame.
    test_empty_piece(): void {
      const frames = new wire.FrameQueue(16);
      frames.pieces_add([Uint8Array.of(9), new Uint8Array(0)]);
      this.assertEqual(frames_drain(frames), [
        Uint8Array.of(constants.input_kind, 9),
      ]);
    }

    // A cache handle refuses the whole line and leaves the queue empty.
    test_handle_refused(): void {
      const frames = new wire.FrameQueue(16);
      this.assertRaises(Error, () =>
        frames.pieces_add([Uint8Array.of(1), "cache/handle"])
      );
      this.assertFalse(frames.frames_left());
    }

    // An empty queue has no frame to give.
    test_queue_empty(): void {
      const frames = new wire.FrameQueue(16);
      this.assertFalse(frames.frames_left());
      this.assertRaises(Error, () => frames.frame_next());
    }

    // A chunk that cannot hold the kind and one byte is refused.
    test_chunk_invalid(): void {
      for (const chunk of [-4, 0, 1, 1.5, NaN, Infinity]) {
        this.assertRaises(Error, () => new wire.FrameQueue(chunk));
        this.assertRaises(
          Error,
          () => new wire.WirePort(constants.base_url, chunk, decoder_make())
        );
      }
    }
  }

  // What the wire port does with ttyd's messages before and after hello.
  export class TestWireMessages extends unittest.TestCase {
    // Title and preferences are kept and never decoded, then hello arrives.
    test_hello_first(): void {
      const port = port_make();
      const hellos: lines.Line[] = [];
      const received: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      port.line_receive((line) => {
        received.push(line);
      });
      // The carriage return would end a line the decoder refuses.
      port.message_take(message_text(constants.title_kind, "dash (xt)\r"));
      port.message_take(message_text(constants.preferences_kind, "{}"));
      this.assertEqual(port.title, "dash (xt)\r");
      this.assertEqual(port.preferences, {});
      port.message_take(output_lines(hello_make()));
      this.assertEqual(hellos.length, 1);
      this.assertEqual(type_of(hellos[0]), "hello");
      this.assertEqual(jslb.field_get(hellos[0][0], "id"), 1);
      this.assertEqual(received.length, 0);
      port.message_take(output_lines(notice_make("mcp")));
      this.assertEqual(hellos.length, 1);
      this.assertEqual(received.map(type_of), ["mcp"]);
    }

    // Hello and the lines after it in one message reach their receivers.
    test_hello_batch(): void {
      const port = port_make();
      const order: unknown[] = [];
      port.hello_receive((line) => {
        order.push(["hello", type_of(line)]);
      });
      port.line_receive((line) => {
        order.push(["line", type_of(line)]);
      });
      port.message_take(
        output_lines(hello_make(), notice_make("a"), notice_make("b"))
      );
      this.assertEqual(order, [
        ["hello", "hello"],
        ["line", "a"],
        ["line", "b"],
      ]);
    }

    // A hello split over two output messages arrives once it is whole.
    test_hello_split(): void {
      const port = port_make();
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      const bytes = line_bytes(hello_make());
      const half = Math.floor(bytes.length / 2);
      const kind = constants.output_kind;
      port.message_take(message_make(kind, bytes.subarray(0, half)));
      this.assertEqual(hellos.length, 0);
      port.message_take(message_make(kind, bytes.subarray(half)));
      this.assertEqual(hellos.length, 1);
    }

    // A line other than hello or error before hello is a fault.
    test_hello_missing(): void {
      const port = port_make();
      port.hello_receive(() => {});
      port.line_receive(() => {});
      this.assertRaises(Error, () =>
        port.message_take(output_lines(notice_make("mcp")))
      );
    }

    // Nothing is posted before hello.
    test_post_early(): void {
      const port = port_make();
      this.assertRaises(Error, () =>
        port.line_post(notice_make("verbose.put"), [])
      );
    }

    // An empty message, or one of a kind ttyd never sends, is a fault.
    test_kind_unknown(): void {
      const port = port_make();
      this.assertRaises(Error, () => port.message_take(new Uint8Array(0)));
      this.assertRaises(Error, () =>
        port.message_take(message_text(0x33, ""))
      );
      this.assertRaises(Error, () =>
        port.message_take(message_text(0x7b, "}"))
      );
    }

    // Output bytes the decoder refuses throw.
    test_decoder_fault(): void {
      const port = port_make();
      port.hello_receive(() => {});
      this.assertRaises(Error, () =>
        port.message_take(output_text("not a line\r"))
      );
    }

    // A line with no receiver set is a fault.
    test_receiver_missing(): void {
      const port = port_make();
      this.assertRaises(Error, () =>
        port.message_take(output_lines(hello_make()))
      );
    }

    // Each receiver is set once.
    test_receiver_twice(): void {
      const port = port_make();
      port.hello_receive(() => {});
      port.line_receive(() => {});
      port.close_receive(() => {});
      this.assertRaises(Error, () => port.hello_receive(() => {}));
      this.assertRaises(Error, () => port.line_receive(() => {}));
      this.assertRaises(Error, () => port.close_receive(() => {}));
    }

    // Only a page served over http or https has ttyd's sockets.
    test_scheme_unknown(): void {
      for (const base_url of ["ftp://127.0.0.1/", "file:///tmp/"]) {
        this.assertRaises(
          Error,
          () =>
            new wire.WirePort(base_url, constants.chunk_bytes, decoder_make())
        );
        this.assertRaises(Error, () => new wire.ConsolePort(base_url));
      }
    }
  }

  // The close of the wire and the fault it is without an error line.
  export class TestCloseFault extends unittest.TestCase {
    // A close with no error line is the fault, after its receiver hears it.
    test_close_silent(): void {
      const port = port_make();
      const closes: unknown[] = [];
      port.hello_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(hello_make()));
      const message = message_thrown(this, () => port.close_take(1006));
      this.assertEqual(
        message,
        "connection closed with code 1006 and no error line"
      );
      this.assertEqual(closes, [[1006, false]]);
    }

    // An error line before the close leaves the fault to that line.
    test_close_error(): void {
      const port = port_make();
      const closes: unknown[] = [];
      const received: lines.Line[] = [];
      port.hello_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(hello_make(), error_make()));
      port.close_take(1006);
      this.assertEqual(closes, [[1006, true]]);
      this.assertEqual(received.map(type_of), ["error"]);
    }

    // An error line in place of hello, a refused lock, reaches the receiver.
    test_error_first(): void {
      const port = port_make();
      const closes: unknown[] = [];
      const hellos: lines.Line[] = [];
      const received: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(error_make()));
      port.close_take(1006);
      this.assertEqual(hellos.length, 0);
      this.assertEqual(received.map(type_of), ["error"]);
      this.assertEqual(closes, [[1006, true]]);
    }

    // A close with no receiver set is still the fault, naming its code.
    test_close_unheard(): void {
      const port = port_make();
      const message = message_thrown(this, () => port.close_take(1000));
      this.assertEqual(
        message,
        "connection closed with code 1000 and no error line"
      );
    }
  }

  // The reads of the console output that `console_run` waits on.
  export class TestConsoleRead extends unittest.TestCase {
    // A read answers with the output after it once `until` shows.
    test_until_found(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      const echo = output_text("echo hi\r\n");
      this.assertEqual(reader.message_take(echo), undefined);
      this.assertEqual(reader.message_take(output_text("hi\r\n$ ")), {
        text: "echo hi\r\nhi\r\n$ ",
        timed_out: false,
      });
    }

    // Output before the read is not part of it, so an old prompt is not one.
    test_output_before(): void {
      const reader = new wire.ConsoleReader();
      this.assertEqual(reader.message_take(output_text("$ ")), undefined);
      reader.read_start("$ ");
      this.assertEqual(
        reader.message_take(output_text("echo hi\r\nhi\r\n$ ")),
        { text: "echo hi\r\nhi\r\n$ ", timed_out: false }
      );
    }

    // An `until` split over two messages is found.
    test_until_split(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      this.assertEqual(reader.message_take(output_text("hi\r\n$")), undefined);
      this.assertEqual(reader.message_take(output_text(" ")), {
        text: "hi\r\n$ ",
        timed_out: false,
      });
    }

    // The timer ends a read with the output so far, and then none waits.
    test_timer_expiry(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      this.assertEqual(reader.message_take(output_text("partial")), undefined);
      this.assertEqual(reader.read_expire(), {
        text: "partial",
        timed_out: true,
      });
      this.assertRaises(Error, () => reader.read_expire());
    }

    // A read that times out with no output has empty text.
    test_timer_silent(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      this.assertEqual(reader.read_expire(), { text: "", timed_out: true });
    }

    // A second read while one waits throws, and the first one stays.
    test_read_twice(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      this.assertRaises(Error, () => reader.read_start("# "));
      this.assertEqual(reader.message_take(output_text("# $ ")), {
        text: "# $ ",
        timed_out: false,
      });
    }

    // Title and preferences are not output text.
    test_title_skipped(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      const title = message_text(constants.title_kind, "$ dash (xt)");
      const preferences = message_text(constants.preferences_kind, "{}");
      this.assertEqual(reader.message_take(title), undefined);
      this.assertEqual(reader.message_take(preferences), undefined);
      this.assertEqual(reader.read_expire(), { text: "", timed_out: true });
    }

    // Each read starts empty after the one before it ended.
    test_reads_consecutive(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("$ ");
      this.assertEqual(reader.message_take(output_text("a$ ")), {
        text: "a$ ",
        timed_out: false,
      });
      this.assertEqual(reader.message_take(output_text("between")), undefined);
      reader.read_start("$ ");
      this.assertEqual(reader.message_take(output_text("b$ ")), {
        text: "b$ ",
        timed_out: false,
      });
    }

    // An empty message, or one of a kind ttyd never sends, is a fault.
    test_kind_refused(): void {
      const reader = new wire.ConsoleReader();
      this.assertRaises(Error, () => reader.message_take(new Uint8Array(0)));
      this.assertRaises(Error, () =>
        reader.message_take(message_text(0x33, "x"))
      );
    }
  }

  // The console output is read as strict `UTF-8`.
  export class TestStrictText extends unittest.TestCase {
    // A character split over two messages is decoded whole.
    test_character_split(): void {
      const reader = new wire.ConsoleReader();
      const character = String.fromCodePoint(0x4e2d);
      const kind = constants.output_kind;
      reader.read_start(character);
      const first = message_make(kind, Uint8Array.of(0xe4, 0xb8));
      const second = message_make(kind, Uint8Array.of(0xad));
      this.assertEqual(reader.message_take(first), undefined);
      this.assertEqual(reader.message_take(second), {
        text: character,
        timed_out: false,
      });
    }

    // An invalid sequence throws, whether a read waits or not.
    test_invalid_bytes(): void {
      const kind = constants.output_kind;
      const idle = new wire.ConsoleReader();
      this.assertRaises(TypeError, () =>
        idle.message_take(message_make(kind, Uint8Array.of(0xff)))
      );
      const reading = new wire.ConsoleReader();
      reading.read_start("$ ");
      this.assertRaises(TypeError, () =>
        reading.message_take(message_make(kind, Uint8Array.of(0xc3, 0x28)))
      );
    }

    // An overlong encoding of a slash is refused.
    test_overlong_refused(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("/");
      const kind = constants.output_kind;
      this.assertRaises(TypeError, () =>
        reader.message_take(message_make(kind, Uint8Array.of(0xc0, 0xaf)))
      );
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds its two ports and the parts they use.
    test_frozen_names(): void {
      const names = ["ConsolePort", "ConsoleReader", "FrameQueue", "WirePort"];
      this.assertTrue(Object.isFrozen(wire));
      this.assertEqual(Object.keys(wire).sort().join(","), names.join(","));
    }
  }
}

Object.freeze(test_wire);
