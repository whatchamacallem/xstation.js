// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire module with no socket and no cache: the input frames
// and their limits, the console port's relay, reads and close, the console
// reads in strict text, and the module's surface. The lines the tests send
// and expect and the texts of the faults are the gold of test_settings.json;
// the bytes the server sends are a line's JSON text, its CR, then its blobs.

namespace test_wire {
  // An address, ttyd's message kinds, a handle.
  const constants = Object.freeze({
    base_url: "http://127.0.0.1:7681/",
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    handle: "cache/0001",
  });

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_wire.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_wire.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A number of `settings.json`.
  function setting_number(id: string): number {
    return harness.setting_get(id) as number;
  }

  // A console port, which builds its lines as this thread's settings say.
  function console_make(): wire.ConsolePort {
    return new wire.ConsolePort(constants.base_url);
  }

  // A frame queue with the chunk given and the limits of the settings.
  function frames_make(chunk: number): wire.FrameQueue {
    return new wire.FrameQueue(
      chunk,
      setting_number("line_max"),
      setting_number("blob_max"),
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

  // Bytes that count up from 0, wrapping at 251.
  function bytes_count(length: number): Uint8Array {
    const data = new Uint8Array(length);
    for (let index = 0; index < length; index += 1) {
      data[index] = index % 251;
    }
    return data;
  }

  // A blob header of a short named line, its size and its bytes.
  function blob_of(data: Uint8Array): lines.BlobHeader {
    return { s: data.length, d: data };
  }

  // The JSON text the encoder writes for a line, each blob's `d` left out.
  function line_text(line: lines.Line): string {
    const sent: { [key: string]: unknown } = { ...line };
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const blob = { ...(line[String(number)] as lines.BlobHeader) };
      delete blob.d;
      sent[String(number)] = blob;
    }
    return JSON.stringify(sent);
  }

  // The JSON bytes of a line, its CR included.
  function json_bytes(line: lines.Line): Uint8Array {
    return new TextEncoder().encode(line_text(line) + "\r");
  }

  // The encoded bytes of a line whose blobs are in memory.
  function line_bytes(line: lines.Line): Uint8Array {
    const parts = [json_bytes(line)];
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const data = (line[String(number)] as lines.BlobHeader).d;
      if (!(data instanceof Uint8Array)) {
        throw new Error(`The line holds the cache handle ${String(data)}.`);
      }
      parts.push(data);
    }
    return bytes_join(parts);
  }

  // A message of ttyd's: the kind byte, then the body.
  function message_make(kind: number, body: Uint8Array): Uint8Array {
    return bytes_join([Uint8Array.of(kind), body]);
  }

  // A message of ttyd's of the kind with a text body.
  function message_text(kind: number, text: string): Uint8Array {
    return message_make(kind, new TextEncoder().encode(text));
  }

  // An output message of ttyd's holding the text.
  function output_text(text: string): Uint8Array {
    return message_text(constants.output_kind, text);
  }

  // A `kv.put` request whose one blob is the header given.
  function put_make(blob: lines.BlobHeader): lines.Line {
    const line = gold_line("put");
    line[1] = blob;
    return line;
  }

  // The bytes of blob 1 of a line.
  function blob_data(line: lines.Line): Uint8Array {
    return (line[1] as lines.BlobHeader).d as Uint8Array;
  }

  // Moves a line's blob buffers away, as a post to another thread does.
  function buffers_move(line: lines.Line): void {
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const data = (line[String(number)] as lines.BlobHeader).d as Uint8Array;
      structuredClone(data, { transfer: [data.buffer as ArrayBuffer] });
    }
  }

  // Every frame the queue holds, in order.
  function frames_drain(frames: wire.FrameQueue): Uint8Array[] {
    const list: Uint8Array[] = [];
    while (frames.frames_left()) {
      list.push(new Uint8Array(frames.frame_next()));
    }
    return list;
  }

  // The bodies of the frames joined, which is what reaches the server.
  function bodies_join(list: Uint8Array[]): Uint8Array {
    return bytes_join(list.map((frame) => frame.subarray(1)));
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
    // A short line goes as one frame: the input kind, then its bytes.
    test_input_prefix(): void {
      const line = gold_line("notice_mcp");
      const frames = frames_make(1024);
      frames.line_add(line);
      this.assertEqual(frames_drain(frames), [
        message_make(constants.input_kind, line_bytes(line)),
      ]);
    }

    // A large line is cut into frames of at most the chunk, piece by piece.
    test_chunk_limit(): void {
      const chunk = 4096;
      const data = bytes_count(10000);
      const line = put_make(blob_of(data));
      const frames = frames_make(chunk);
      frames.line_add(line);
      const list = frames_drain(frames);
      for (const frame of list) {
        this.assertTrue(frame.length > 1 && frame.length <= chunk);
        this.assertEqual(frame[0], constants.input_kind);
      }
      this.assertEqual(bodies_join(list), line_bytes(line));
      const count =
        Math.ceil(json_bytes(line).length / (chunk - 1)) +
        Math.ceil(data.length / (chunk - 1));
      this.assertEqual(list.length, count);
    }

    // Lines queued one after another leave in order, no frame holding two.
    test_line_order(): void {
      const chunk = 8;
      const first = gold_line("notice_a");
      const second = gold_line("notice_b");
      const frames = frames_make(chunk);
      frames.line_add(first);
      frames.line_add(second);
      const list = frames_drain(frames);
      this.assertEqual(
        bodies_join(list),
        bytes_join([line_bytes(first), line_bytes(second)]),
      );
      const count =
        Math.ceil(line_bytes(first).length / (chunk - 1)) +
        Math.ceil(line_bytes(second).length / (chunk - 1));
      this.assertEqual(list.length, count);
    }

    // A blob of no bytes sends no frame.
    test_empty_piece(): void {
      const line = put_make(blob_of(new Uint8Array(0)));
      const frames = frames_make(1024);
      frames.line_add(line);
      this.assertEqual(frames_drain(frames), [
        message_make(constants.input_kind, json_bytes(line)),
      ]);
    }

    // A line of exactly `line_max` goes, and one byte more is refused.
    test_line_limit(): void {
      const line = gold_line("notice_mcp");
      const size = line_bytes(line).length;
      const limit = setting_number("blob_max");
      const fits = new wire.FrameQueue(1024, size, limit);
      fits.line_add(line);
      this.assertEqual(bodies_join(frames_drain(fits)), line_bytes(line));
      const over = new wire.FrameQueue(1024, size - 1, limit);
      const message = message_thrown(this, () => over.line_add(line));
      const expected = gold_text("wire_line_over_frames")
        .replaceAll("{1}", String(size))
        .replaceAll("{2}", String(size - 1));
      this.assertEqual(message, expected);
      this.assertFalse(over.frames_left());
    }

    // Blobs of exactly `blob_max` go beside their line, one byte more not.
    test_blobs_limit(): void {
      const line = put_make(blob_of(bytes_count(100)));
      const size = json_bytes(line).length;
      const fits = new wire.FrameQueue(1024, size, 100);
      fits.line_add(line);
      this.assertEqual(bodies_join(frames_drain(fits)), line_bytes(line));
      const over = new wire.FrameQueue(1024, size, 99);
      const message = message_thrown(this, () => over.line_add(line));
      this.assertEqual(message, gold_text("wire_blobs_over_frames"));
      this.assertFalse(over.frames_left());
    }

    // Blobs that would pass `blob_max` with those held wait for blob frames.
    test_queue_limit(): void {
      const first = put_make(blob_of(bytes_count(10)));
      const notice = gold_line("notice_a");
      const second = put_make(blob_of(bytes_count(6)));
      const frames = new wire.FrameQueue(8, setting_number("line_max"), 15);
      frames.line_add(first);
      frames.line_add(notice);
      const refused = gold_text("wire_queue_over");
      const second_add = () => frames.line_add(second);
      this.assertEqual(message_thrown(this, second_add), refused);
      // The frames of the first line's JSON free no room, a blob's frame does.
      const taken: Uint8Array[] = [];
      const json_frames = Math.ceil(json_bytes(first).length / 7);
      for (let index = 0; index < json_frames; index += 1) {
        taken.push(new Uint8Array(frames.frame_next()).subarray(1));
      }
      this.assertEqual(message_thrown(this, second_add), refused);
      taken.push(new Uint8Array(frames.frame_next()).subarray(1));
      second_add();
      taken.push(bodies_join(frames_drain(frames)));
      const sent = [first, notice, second].map((line) => line_bytes(line));
      this.assertEqual(bytes_join(taken), bytes_join(sent));
    }

    // An empty queue has no frame to give.
    test_queue_empty(): void {
      const frames = frames_make(16);
      this.assertFalse(frames.frames_left());
      this.assertEqual(
        message_thrown(this, () => frames.frame_next()),
        gold_text("wire_frames_none"),
      );
    }

    // A chunk that cannot hold the kind and one byte is refused.
    test_chunk_invalid(): void {
      const line_max = setting_number("line_max");
      const blob_max = setting_number("blob_max");
      const cases: [number, string][] = [
        [-4, "negative"],
        [0, "zero"],
        [1, "one"],
        [1.5, "fraction"],
        [NaN, "nan"],
        [Infinity, "infinity"],
      ];
      for (const [chunk, name] of cases) {
        const message = message_thrown(
          this,
          () => new wire.FrameQueue(chunk, line_max, blob_max),
        );
        this.assertEqual(message, gold_text(`wire_chunk_invalid_${name}`));
      }
    }

    // A blob held as a cache handle refuses the whole line, as none is sent.
    test_handle_unsent(): void {
      const line = put_make({ s: 20, d: constants.handle });
      const frames = frames_make(16);
      const message = message_thrown(this, () => frames.line_add(line));
      this.assertEqual(message, gold_text("wire_handle_unsent"));
      this.assertFalse(frames.frames_left());
    }
  }

  // The console port's relay, its reads and its close, with no socket.
  export class TestConsolePort extends unittest.TestCase {
    // The read takes a message before its relay moves the buffer away.
    test_output_relay(): void {
      const port = console_make();
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        buffers_move(line);
        received.push(line);
      });
      port.line_post(gold_line("read_request_1"), []);
      port.message_take(output_text("hi\r\n$ "));
      this.assertEqual(received.length, 2);
      this.assertEqual(received[0][0], gold_line("output")[0]);
      this.assertEqual(blob_data(received[0]).length, 0);
      this.assertEqual(received[1], gold_line("read_reply_found"));
    }

    // The port's lines take full names exactly when the settings say debug.
    test_names_full(): void {
      const port = console_make();
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      port.line_post(gold_line("read_request_1"), []);
      port.message_take(output_text("$ "));
      const full = harness.setting_get("debug") === true;
      this.assertEqual(received.length, 2);
      for (const line of received) {
        this.assertEqual(Object.hasOwn(line[0], "type"), full);
        this.assertEqual(Object.hasOwn(line[0], "t"), !full);
      }
    }

    // A read waiting when the socket closes is answered as timed out.
    test_close_read(): void {
      const port = console_make();
      const received: lines.Line[] = [];
      const closes: number[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code) => {
        closes.push(code);
      });
      port.line_post(gold_line("read_request_1"), []);
      port.message_take(output_text("partial"));
      port.close_take(1006);
      this.assertEqual(received.length, 2);
      this.assertEqual(received[0][0], gold_line("output")[0]);
      this.assertEqual(received[1], gold_line("read_reply_partial"));
      this.assertEqual(closes, [1006]);
    }

    // After a close the port takes a new read, as a reopened console needs.
    test_read_reopened(): void {
      const port = console_make();
      const received: lines.Line[] = [];
      const closes: number[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code) => {
        closes.push(code);
      });
      port.line_post(gold_line("read_request_1"), []);
      port.close_take(1006);
      port.line_post(gold_line("read_request_2"), []);
      port.message_take(output_text("$ "));
      this.assertEqual(received.length, 3);
      this.assertEqual(received[0], gold_line("read_reply_expired"));
      this.assertEqual(received[1][0], gold_line("output")[0]);
      this.assertEqual(received[2], gold_line("read_reply_second"));
      this.assertEqual(closes, [1006]);
    }

    // A close with no read waiting only reports its code.
    test_close_idle(): void {
      const port = console_make();
      const received: lines.Line[] = [];
      const closes: number[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code) => {
        closes.push(code);
      });
      port.close_take(1000);
      this.assertEqual(received.length, 0);
      this.assertEqual(closes, [1000]);
    }

    // A close with no close receiver set is a fault, as nobody hears it.
    test_close_unheard(): void {
      const port = console_make();
      this.assertEqual(
        message_thrown(this, () => port.close_take(1000)),
        gold_text("wire_receiver_missing_close"),
      );
    }

    // A line of a type the console port does not take is refused.
    test_type_refused(): void {
      const port = console_make();
      const message = message_thrown(this, () =>
        port.line_post(gold_line("notice_console_output"), []),
      );
      this.assertEqual(message, gold_text("wire_console_type"));
    }

    // An open or a read that is not a request with an id is refused.
    test_id_missing(): void {
      const port = console_make();
      const open = gold_line("open_unnumbered");
      this.assertEqual(
        message_thrown(this, () => port.line_post(open, [])),
        gold_text("wire_id_missing_open"),
      );
      const read = gold_line("read_unnumbered");
      this.assertEqual(
        message_thrown(this, () => port.line_post(read, [])),
        gold_text("wire_id_missing_read"),
      );
    }

    // A read needs text to wait for and seconds from 0 that a timer holds.
    test_read_invalid(): void {
      const port = console_make();
      const until = gold_line("read_until_number");
      const negative = gold_line("read_seconds_negative");
      const text = gold_line("read_seconds_text");
      const long = gold_line("read_seconds_long");
      this.assertEqual(
        message_thrown(this, () => port.line_post(until, [])),
        gold_text("wire_read_until"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_post(negative, [])),
        gold_text("wire_read_seconds_negative"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_post(text, [])),
        gold_text("wire_read_seconds_text"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_post(long, [])),
        gold_text("wire_read_seconds_long"),
      );
    }

    // Input needs the socket, which only `console.open` makes.
    test_input_unopened(): void {
      const port = console_make();
      const line = gold_line("input");
      const data = Uint8Array.of(0x30, 0x0a);
      line[1] = { size: data.length, d: data };
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, gold_text("wire_socket_missing_console"));
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
        { text: "echo hi\r\nhi\r\n$ ", timed_out: false },
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
      this.assertEqual(
        message_thrown(this, () => reader.read_expire()),
        gold_text("wire_read_none"),
      );
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
      this.assertEqual(
        message_thrown(this, () => reader.read_start("# ")),
        gold_text("wire_read_twice"),
      );
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
      this.assertEqual(
        message_thrown(this, () => reader.message_take(new Uint8Array(0))),
        gold_text("wire_message_empty"),
      );
      this.assertEqual(
        message_thrown(this, () =>
          reader.message_take(message_text(0x33, "x")),
        ),
        gold_text("wire_kind_unknown_digit"),
      );
    }
  }

  // The console output a read takes is strict `UTF-8`, and no other is read.
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

    // Ignored output harms no read, as each read decodes from its own start.
    test_invalid_bytes(): void {
      const kind = constants.output_kind;
      const reader = new wire.ConsoleReader();
      const binary = message_make(kind, Uint8Array.of(0xff));
      const half = message_make(kind, Uint8Array.of(0xe4, 0xb8));
      this.assertEqual(reader.message_take(binary), undefined);
      this.assertEqual(reader.message_take(half), undefined);
      reader.read_start("$ ");
      this.assertEqual(reader.message_take(output_text("$ ")), {
        text: "$ ",
        timed_out: false,
      });
      reader.read_start("$ ");
      const invalid = message_make(kind, Uint8Array.of(0xc3, 0x28));
      this.assertEqual(
        message_thrown(this, () => reader.message_take(invalid)),
        gold_text("wire_output_invalid_prompt"),
      );
    }

    // An overlong encoding of a slash is refused.
    test_overlong_refused(): void {
      const reader = new wire.ConsoleReader();
      reader.read_start("/");
      const kind = constants.output_kind;
      const overlong = message_make(kind, Uint8Array.of(0xc0, 0xaf));
      this.assertEqual(
        message_thrown(this, () => reader.message_take(overlong)),
        gold_text("wire_output_invalid_slash"),
      );
    }
  }

  // The shape of the module object.
  export class TestModuleSurface extends unittest.TestCase {
    // The module is frozen and holds its two ports and the parts they use.
    test_frozen_names(): void {
      const names = ["ConsolePort", "ConsoleReader", "FrameQueue", "WirePort"];
      this.assertTrue(Object.isFrozen(wire));
      this.assertEqual(Object.keys(wire).sort().join(","), names.join(","));
    }
  }
}

Object.freeze(test_wire);
