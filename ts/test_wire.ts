// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire module that need no socket: the input frames and their
// limits, cache files read in ranges, hello and the settings that size the
// port after it, the close fault, the console port and the console reads.

namespace test_wire {
  // Addresses, the root a hello names, ttyd's message kinds and a handle.
  const constants = Object.freeze({
    base_url: "http://127.0.0.1:7681/",
    socket_url: "ws://127.0.0.1:7681/ws",
    console_url: "ws://127.0.0.1:7681/ws?arg=console",
    root: "/home/t/.cache/xsjs",
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    handle: "cache/0001",
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

  // Cache files held in memory, read in ranges that are recorded.
  class CacheDouble {
    readonly files = new Map<string, Uint8Array>();
    readonly ranges: number[][] = [];

    // Reads a range of a file, fewer bytes at its end, as a cache file does.
    read = (handle: string, offset: number, length: number): Uint8Array => {
      this.ranges.push([offset, length]);
      const file = this.files.get(handle) as Uint8Array;
      return file.subarray(offset, offset + length);
    };
  }

  // The settings of `settings.json`, every key of the interface.
  function settings_make(): settings.Settings {
    return {
      debug: true,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      line_max: 1048576,
      blob_max: 2147483391,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      db_soft_bytes: 1073741824,
      turn_compact_turns: 64,
      long_task_ms: 5,
      provider: {
        scripted: true,
        timeout_seconds: 120,
      },
    };
  }

  // The reader of a settings store that holds the settings given.
  function reader_from(value: settings.Settings): (id: string) => unknown {
    const store = new settings.ValueStore();
    store.value_set(value);
    return (id: string) => store.value_get(id);
  }

  // A wire port that is never opened, sized by the settings given.
  function port_make(value: settings.Settings): wire.WirePort {
    return new wire.WirePort(
      constants.base_url,
      new UnusedSink(),
      reader_from(value),
    );
  }

  // A wire port whose settings were never set.
  function port_unset(): wire.WirePort {
    const store = new settings.ValueStore();
    return new wire.WirePort(constants.base_url, new UnusedSink(), (id) =>
      store.value_get(id),
    );
  }

  // A console port with the settings of `settings.json`, in debug mode.
  function console_make(): wire.ConsolePort {
    const read = reader_from(settings_make());
    return new wire.ConsolePort(constants.base_url, read);
  }

  // A frame queue with the chunk given and the limits of the settings.
  function frames_make(chunk: number): wire.FrameQueue {
    const value = settings_make();
    return new wire.FrameQueue(chunk, value.line_max, value.blob_max);
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

  // The JSON bytes of a line, its CR included.
  function json_bytes(line: lines.Line): Uint8Array {
    return jslb.line_encode(line)[0] as Uint8Array;
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

  // The server's `hello`, a request with id 1 that names the root given.
  function hello_make(root: string): lines.Line {
    return jslb.line_make(jslb.header_make("hello", { id: 1 }), [], {
      pid: 4242,
      root,
    });
  }

  // A notification of the type with no payload.
  function notice_make(type: string): lines.Line {
    return jslb.line_make(jslb.header_make(type), [], {});
  }

  // A `kv.put` request whose one blob is the header given.
  function put_make(blob: lines.BlobHeader): lines.Line {
    const header = jslb.header_make("kv.put", { id: 1, key: "/m/big" });
    return jslb.line_make(header, [blob], {});
  }

  // The server's `error` line answering request 1.
  function error_make(): lines.Line {
    return jslb.line_make(jslb.header_make("error", { reply: 1 }), [], {
      message: "kv_get: /metaverse/nothing: no such key",
      stack: "Traceback (most recent call last):",
    });
  }

  // The server's `error` line in place of hello, which answers nothing.
  function refusal_make(): lines.Line {
    return jslb.line_make(jslb.header_make("error"), [], {
      message: "The engine lock /home/t/.cache/xsjs/engine.lock is held.",
      stack: "Traceback (most recent call last):",
    });
  }

  // A `console.read` request in full names, with its payload as given.
  function read_make(
    id: number,
    until: unknown,
    seconds: unknown,
  ): lines.Line {
    const header = jslb.header_make("console.read", { id, full: true });
    return jslb.line_make(header, [], { until, timeout_seconds: seconds });
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // The reply field of a line, undefined for a line that answers nothing.
  function reply_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "reply");
  }

  // The bytes of blob 1 of a line.
  function blob_data(line: lines.Line): Uint8Array {
    const blob = line[1] as lines.BlobHeader;
    return jslb.field_get(blob, "data") as Uint8Array;
  }

  // Moves a line's blob buffers away, as a post to another thread does.
  function buffers_move(line: lines.Line): void {
    for (const blob of jslb.headers_of(line).slice(1)) {
      const header = blob as lines.BlobHeader;
      const data = jslb.field_get(header, "data") as Uint8Array;
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
      const line = notice_make("mcp");
      const frames = frames_make(1024);
      frames.line_add(line, undefined);
      this.assertEqual(frames_drain(frames), [
        message_make(constants.input_kind, line_bytes(line)),
      ]);
    }

    // A large line is cut into frames of at most the chunk, piece by piece.
    test_chunk_limit(): void {
      const chunk = 4096;
      const data = bytes_count(10000);
      const line = put_make(jslb.blob_make(data));
      const frames = frames_make(chunk);
      frames.line_add(line, undefined);
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
      const first = notice_make("a");
      const second = notice_make("b");
      const frames = frames_make(chunk);
      frames.line_add(first, undefined);
      frames.line_add(second, undefined);
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
      const line = put_make(jslb.blob_make(new Uint8Array(0)));
      const frames = frames_make(1024);
      frames.line_add(line, undefined);
      this.assertEqual(frames_drain(frames), [
        message_make(constants.input_kind, json_bytes(line)),
      ]);
    }

    // A line of exactly `line_max` goes, and one byte more is refused.
    test_line_limit(): void {
      const line = notice_make("mcp");
      const size = line_bytes(line).length;
      const limit = settings_make().blob_max;
      const fits = new wire.FrameQueue(1024, size, limit);
      fits.line_add(line, undefined);
      this.assertEqual(bodies_join(frames_drain(fits)), line_bytes(line));
      const over = new wire.FrameQueue(1024, size - 1, limit);
      const message = message_thrown(this, () =>
        over.line_add(line, undefined),
      );
      this.assertEqual(message, i18n("wire.line_over", "mcp", size, size - 1));
      this.assertFalse(over.frames_left());
    }

    // Blobs of exactly `blob_max` go beside their line, one byte more not.
    test_blobs_limit(): void {
      const line = put_make(jslb.blob_make(bytes_count(100)));
      const size = json_bytes(line).length;
      const fits = new wire.FrameQueue(1024, size, 100);
      fits.line_add(line, undefined);
      this.assertEqual(bodies_join(frames_drain(fits)), line_bytes(line));
      const over = new wire.FrameQueue(1024, size, 99);
      const message = message_thrown(this, () =>
        over.line_add(line, undefined),
      );
      this.assertEqual(message, i18n("wire.blobs_over", "kv.put", 100, 99));
      this.assertFalse(over.frames_left());
    }

    // Blobs that would pass `blob_max` with those held wait for blob frames.
    test_queue_limit(): void {
      const first = put_make(jslb.blob_make(bytes_count(10)));
      const notice = notice_make("a");
      const second = put_make(jslb.blob_make(bytes_count(6)));
      const frames = new wire.FrameQueue(8, settings_make().line_max, 15);
      frames.line_add(first, undefined);
      frames.line_add(notice, undefined);
      const refused = i18n("wire.queue_over", "kv.put", 6, 10, 15);
      const second_add = () => frames.line_add(second, undefined);
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
        i18n("wire.frames_none"),
      );
    }

    // A chunk that cannot hold the kind and one byte is refused.
    test_chunk_invalid(): void {
      const value = settings_make();
      for (const chunk of [-4, 0, 1, 1.5, NaN, Infinity]) {
        const message = message_thrown(
          this,
          () => new wire.FrameQueue(chunk, value.line_max, value.blob_max),
        );
        this.assertEqual(message, i18n("wire.chunk_invalid", chunk));
      }
    }
  }

  // Blobs held as cache files, read in ranges as their frames are sent.
  export class TestCacheFrames extends unittest.TestCase {
    // A cache file is read in ranges of a frame's bytes and sent whole.
    test_handle_read(): void {
      const data = bytes_count(20);
      const cache = new CacheDouble();
      cache.files.set(constants.handle, data);
      const blob = jslb.blob_make(constants.handle, undefined, {}, 20);
      const line = put_make(blob);
      const frames = frames_make(8);
      frames.line_add(line, cache.read);
      this.assertEqual(
        bodies_join(frames_drain(frames)),
        bytes_join([json_bytes(line), data]),
      );
      this.assertEqual(cache.ranges, [
        [0, 7],
        [7, 7],
        [14, 6],
      ]);
    }

    // The size of a cache file's blob counts toward `blob_max`.
    test_handle_counted(): void {
      const cache = new CacheDouble();
      cache.files.set(constants.handle, bytes_count(20));
      const blob = jslb.blob_make(constants.handle, undefined, {}, 20);
      const line = put_make(blob);
      const size = json_bytes(line).length;
      const frames = new wire.FrameQueue(1024, size, 19);
      const message = message_thrown(this, () =>
        frames.line_add(line, cache.read),
      );
      this.assertEqual(message, i18n("wire.blobs_over", "kv.put", 20, 19));
      this.assertEqual(cache.ranges, []);
    }

    // With no reader of cache files a handle refuses the whole line.
    test_handle_unsent(): void {
      const blob = jslb.blob_make(constants.handle, undefined, {}, 20);
      const line = put_make(blob);
      const frames = frames_make(16);
      const message = message_thrown(this, () =>
        frames.line_add(line, undefined),
      );
      this.assertEqual(message, i18n("wire.handle_unsent", constants.handle));
      this.assertFalse(frames.frames_left());
    }

    // A cache file shorter than its blob's size is a fault, not a short send.
    test_handle_short(): void {
      const cache = new CacheDouble();
      cache.files.set(constants.handle, bytes_count(15));
      const blob = jslb.blob_make(constants.handle, undefined, {}, 20);
      const line = put_make(blob);
      const frames = frames_make(8);
      frames.line_add(line, cache.read);
      const message = message_thrown(this, () => frames_drain(frames));
      this.assertEqual(
        message,
        i18n("wire.handle_differs", constants.handle, 14, 6, 1),
      );
    }
  }

  // What the wire port does with ttyd's messages before and after hello.
  export class TestWireMessages extends unittest.TestCase {
    // Title and preferences are kept and never decoded, then hello arrives.
    test_hello_first(): void {
      const port = port_make(settings_make());
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
      port.message_take(output_lines(hello_make(constants.root)));
      this.assertEqual(hellos.length, 1);
      this.assertEqual(type_of(hellos[0]), "hello");
      this.assertEqual(jslb.field_get(hellos[0][0], "id"), 1);
      this.assertEqual(received.length, 0);
      port.message_take(output_lines(notice_make("mcp")));
      this.assertEqual(hellos.length, 1);
      this.assertEqual(received.map(type_of), ["mcp"]);
    }

    // Nothing may follow hello before its reply, whole or in part.
    test_hello_trailing(): void {
      const port = port_make(settings_make());
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      port.line_receive(() => {});
      const whole = output_lines(hello_make(constants.root), notice_make("a"));
      this.assertEqual(
        message_thrown(this, () => port.message_take(whole)),
        i18n("wire.hello_trailing"),
      );
      this.assertEqual(hellos.length, 1);
      const other = port_make(settings_make());
      other.hello_receive(() => {});
      const bytes = bytes_join([
        line_bytes(hello_make(constants.root)),
        line_bytes(notice_make("a")).subarray(0, 4),
      ]);
      const part = message_make(constants.output_kind, bytes);
      this.assertEqual(
        message_thrown(this, () => other.message_take(part)),
        i18n("wire.hello_trailing"),
      );
    }

    // A hello split over two output messages arrives once it is whole.
    test_hello_split(): void {
      const port = port_make(settings_make());
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      const bytes = line_bytes(hello_make(constants.root));
      const half = Math.floor(bytes.length / 2);
      const kind = constants.output_kind;
      port.message_take(message_make(kind, bytes.subarray(0, half)));
      this.assertEqual(hellos.length, 0);
      port.message_take(message_make(kind, bytes.subarray(half)));
      this.assertEqual(hellos.length, 1);
    }

    // A line other than hello or error before hello is a fault.
    test_hello_missing(): void {
      const port = port_make(settings_make());
      port.hello_receive(() => {});
      port.line_receive(() => {});
      const message = message_thrown(this, () =>
        port.message_take(output_lines(notice_make("mcp"))),
      );
      this.assertEqual(message, i18n("wire.hello_missing", "mcp"));
    }

    // A second hello, which a restart of the server sends, is a fault.
    test_hello_twice(): void {
      const port = port_make(settings_make());
      port.hello_receive(() => {});
      port.line_receive(() => {});
      port.message_take(output_lines(hello_make(constants.root)));
      const message = message_thrown(this, () =>
        port.message_take(output_lines(hello_make(constants.root))),
      );
      this.assertEqual(message, i18n("wire.hello_twice"));
    }

    // Nothing is posted before hello.
    test_post_early(): void {
      const port = port_make(settings_make());
      const message = message_thrown(this, () =>
        port.line_post(notice_make("verbose.put"), []),
      );
      this.assertEqual(message, i18n("wire.post_early", "verbose.put"));
    }

    // An empty message, or one of a kind ttyd never sends, is a fault.
    test_kind_unknown(): void {
      const port = port_make(settings_make());
      this.assertEqual(
        message_thrown(this, () => port.message_take(new Uint8Array(0))),
        i18n("wire.message_empty"),
      );
      this.assertEqual(
        message_thrown(this, () => port.message_take(message_text(0x33, ""))),
        i18n("wire.kind_unknown", 0x33),
      );
      this.assertEqual(
        message_thrown(this, () => port.message_take(message_text(0x7b, "}"))),
        i18n("wire.kind_unknown", 0x7b),
      );
    }

    // Output bytes the decoder refuses throw its fault.
    test_decoder_fault(): void {
      const port = port_make(settings_make());
      port.hello_receive(() => {});
      const message = message_thrown(this, () =>
        port.message_take(output_text("{}\r")),
      );
      this.assertEqual(message, i18n("jslb.no_header_zero"));
    }

    // The lines before a fault reach their receiver, then the fault throws.
    test_fault_held(): void {
      const port = port_make(settings_make());
      const received: lines.Line[] = [];
      port.hello_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      port.message_take(output_lines(hello_make(constants.root)));
      const bytes = bytes_join([
        line_bytes(notice_make("mcp")),
        utility.utf8_encode("{}\r"),
      ]);
      const output = message_make(constants.output_kind, bytes);
      const message = message_thrown(this, () => port.message_take(output));
      this.assertEqual(received.map(type_of), ["mcp"]);
      this.assertEqual(message, i18n("jslb.no_header_zero"));
    }

    // A line with no receiver set is a fault.
    test_receiver_missing(): void {
      const port = port_make(settings_make());
      const message = message_thrown(this, () =>
        port.message_take(output_lines(hello_make(constants.root))),
      );
      this.assertEqual(message, i18n("wire.receiver_missing", "hello"));
    }

    // Each receiver and the reader of cache files are set once.
    test_receiver_twice(): void {
      const port = port_make(settings_make());
      const cache = new CacheDouble();
      port.hello_receive(() => {});
      port.line_receive(() => {});
      port.close_receive(() => {});
      port.cache_attach(cache.read);
      this.assertEqual(
        message_thrown(this, () => port.hello_receive(() => {})),
        i18n("wire.receiver_twice", "hello_receive"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_receive(() => {})),
        i18n("wire.receiver_twice", "line_receive"),
      );
      this.assertEqual(
        message_thrown(this, () => port.close_receive(() => {})),
        i18n("wire.receiver_twice", "close_receive"),
      );
      this.assertEqual(
        message_thrown(this, () => port.cache_attach(cache.read)),
        i18n("wire.receiver_twice", "cache_attach"),
      );
    }

    // Only a page served over http or https has ttyd's sockets.
    test_scheme_unknown(): void {
      for (const base_url of ["ftp://127.0.0.1/", "file:///tmp/"]) {
        const read = reader_from(settings_make());
        const sink = new UnusedSink();
        this.assertEqual(
          message_thrown(this, () => new wire.WirePort(base_url, sink, read)),
          i18n("wire.scheme_unknown", base_url),
        );
        this.assertEqual(
          message_thrown(this, () => new wire.ConsolePort(base_url, read)),
          i18n("wire.scheme_unknown", base_url),
        );
      }
    }
  }

  // The hello phase sizes, then the settings that size the port after hello.
  export class TestSettingsPhase extends unittest.TestCase {
    // Hello is read with the hello phase sizes, which allow no blob.
    test_hello_blob(): void {
      const port = port_make(settings_make());
      port.hello_receive(() => {});
      const header = jslb.header_make("hello", { id: 1 });
      const blob = jslb.blob_make(Uint8Array.of(7));
      const hello = jslb.line_make(header, [blob], {});
      const message = message_thrown(this, () =>
        port.message_take(output_lines(hello)),
      );
      this.assertEqual(message, i18n("jslb.blobs_over", 1, 0));
    }

    // The settings size the decoder only once hello has come.
    test_settings_sized(): void {
      const value = settings_make();
      value.line_max = 64;
      const port = port_make(value);
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      port.line_receive(() => {});
      const text = "x".repeat(100);
      port.message_take(output_lines(hello_make(text)));
      this.assertEqual(hellos.length, 1);
      const long = jslb.line_make(jslb.header_make("mcp"), [], { text });
      const message = message_thrown(this, () =>
        port.message_take(output_lines(long)),
      );
      this.assertEqual(message, i18n("jslb.line_over_max", 64));
    }

    // Hello needs no settings, and the first post after it reads them.
    test_settings_unset(): void {
      const port = port_unset();
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      const hello = hello_make(constants.root);
      port.message_take(output_lines(hello));
      this.assertEqual(hellos.length, 1);
      const message = message_thrown(this, () =>
        port.line_post(dispatch.reply_make(hello, {}), []),
      );
      this.assertEqual(message, i18n("settings.not_set"));
    }

    // Blobs over `blob_max` are refused before they are queued.
    test_blobs_over(): void {
      const value = settings_make();
      value.blob_max = 64;
      const port = port_make(value);
      port.hello_receive(() => {});
      port.message_take(output_lines(hello_make(constants.root)));
      const line = put_make(jslb.blob_make(bytes_count(100)));
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, i18n("wire.blobs_over", "kv.put", 100, 64));
    }

    // A line over `line_max` is refused before it is queued.
    test_line_over(): void {
      const value = settings_make();
      value.line_max = 64;
      const port = port_make(value);
      port.hello_receive(() => {});
      port.message_take(output_lines(hello_make(constants.root)));
      const line = jslb.line_make(jslb.header_make("mcp"), [], {
        text: "x".repeat(100),
      });
      const size = line_bytes(line).length;
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(message, i18n("wire.line_over", "mcp", size, 64));
    }

    // A line within the limits is queued, and sending it needs the socket.
    test_socket_missing(): void {
      const port = port_make(settings_make());
      port.hello_receive(() => {});
      const hello = hello_make(constants.root);
      port.message_take(output_lines(hello));
      const message = message_thrown(this, () =>
        port.line_post(dispatch.reply_make(hello, {}), []),
      );
      this.assertEqual(
        message,
        i18n("wire.socket_missing", constants.socket_url),
      );
    }
  }

  // The close of the wire and the fault it is without an error line.
  export class TestCloseFault extends unittest.TestCase {
    // A close with no error line is the fault, after its receiver hears it.
    test_close_silent(): void {
      const port = port_make(settings_make());
      const closes: unknown[] = [];
      port.hello_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(hello_make(constants.root)));
      const message = message_thrown(this, () => port.close_take(1006));
      this.assertEqual(message, i18n("wire.close_silent", 1006));
      this.assertEqual(closes, [[1006, false]]);
    }

    // An error line before the close leaves the fault to that line.
    test_close_error(): void {
      const port = port_make(settings_make());
      const closes: unknown[] = [];
      const received: lines.Line[] = [];
      port.hello_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      port.message_take(output_lines(hello_make(constants.root)));
      port.message_take(output_lines(error_make()));
      port.close_take(1006);
      this.assertEqual(closes, [[1006, true]]);
      this.assertEqual(received.map(type_of), ["error"]);
    }

    // An error line in place of hello, a refused lock, throws its message.
    test_error_first(): void {
      const port = port_make(settings_make());
      const closes: unknown[] = [];
      const hellos: lines.Line[] = [];
      port.hello_receive((line) => {
        hellos.push(line);
      });
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      const refusal = refusal_make();
      const payload = jslb.payload_of(refusal);
      const message = message_thrown(this, () =>
        port.message_take(output_lines(refusal)),
      );
      this.assertEqual(
        message,
        i18n("wire.error_first", payload.message, payload.stack),
      );
      port.close_take(1006);
      this.assertEqual(hellos.length, 0);
      this.assertEqual(closes, [[1006, true]]);
    }

    // An error line before hello is not passed on, though a receiver is set.
    test_error_unpassed(): void {
      const port = port_make(settings_make());
      const received: lines.Line[] = [];
      port.hello_receive(() => {});
      port.line_receive((line) => {
        received.push(line);
      });
      const refusal = refusal_make();
      const payload = jslb.payload_of(refusal);
      const message = message_thrown(this, () =>
        port.message_take(output_lines(refusal)),
      );
      this.assertEqual(
        message,
        i18n("wire.error_first", payload.message, payload.stack),
      );
      this.assertEqual(received.length, 0);
    }

    // A close with no receiver set is still the fault, naming its code.
    test_close_unheard(): void {
      const port = port_make(settings_make());
      const message = message_thrown(this, () => port.close_take(1000));
      this.assertEqual(message, i18n("wire.close_silent", 1000));
    }

    // A close in the middle of a message is a fault of its own.
    test_close_partial(): void {
      const port = port_make(settings_make());
      const closes: unknown[] = [];
      port.hello_receive(() => {});
      port.close_receive((code, had_error) => {
        closes.push([code, had_error]);
      });
      const bytes = line_bytes(hello_make(constants.root)).subarray(0, 8);
      port.message_take(message_make(constants.output_kind, bytes));
      const message = message_thrown(this, () => port.close_take(1006));
      this.assertEqual(message, i18n("wire.close_partial", 1006));
      this.assertEqual(closes, [[1006, false]]);
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
      port.line_post(read_make(1, "$ ", 60), []);
      port.message_take(output_text("hi\r\n$ "));
      this.assertEqual(received.map(type_of), [
        "console.output",
        "console.read",
      ]);
      this.assertEqual(blob_data(received[0]).length, 0);
      this.assertEqual(reply_of(received[1]), 1);
      this.assertEqual(jslb.payload_of(received[1]), {
        text: "hi\r\n$ ",
        timed_out: false,
      });
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
      port.line_post(read_make(1, "$ ", 60), []);
      port.message_take(output_text("partial"));
      port.close_take(1006);
      this.assertEqual(received.map(type_of), [
        "console.output",
        "console.read",
      ]);
      this.assertEqual(reply_of(received[1]), 1);
      this.assertEqual(jslb.payload_of(received[1]), {
        text: "partial",
        timed_out: true,
      });
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
      port.line_post(read_make(1, "$ ", 60), []);
      port.close_take(1006);
      port.line_post(read_make(2, "$ ", 60), []);
      port.message_take(output_text("$ "));
      this.assertEqual(received.map(reply_of), [1, undefined, 2]);
      this.assertEqual(jslb.payload_of(received[2]), {
        text: "$ ",
        timed_out: false,
      });
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

    // A line of a type the console port does not take is refused.
    test_type_refused(): void {
      const port = console_make();
      const message = message_thrown(this, () =>
        port.line_post(notice_make("console.output"), []),
      );
      this.assertEqual(message, i18n("wire.console_type", "console.output"));
    }

    // An open or a read that is not a request with an id is refused.
    test_id_missing(): void {
      const port = console_make();
      const open_header = jslb.header_make("console.open", { full: true });
      const open = jslb.line_make(open_header, [], {});
      this.assertEqual(
        message_thrown(this, () => port.line_post(open, [])),
        i18n("wire.id_missing", "console.open"),
      );
      const read_header = jslb.header_make("console.read", { full: true });
      const read = jslb.line_make(read_header, [], {
        until: "$ ",
        timeout_seconds: 5,
      });
      this.assertEqual(
        message_thrown(this, () => port.line_post(read, [])),
        i18n("wire.id_missing", "console.read"),
      );
    }

    // A read needs text to wait for and a number of seconds from 0.
    test_read_invalid(): void {
      const port = console_make();
      const until = read_make(1, 5, 5);
      const negative = read_make(1, "$ ", -1);
      const text = read_make(1, "$ ", "5");
      this.assertEqual(
        message_thrown(this, () => port.line_post(until, [])),
        i18n("wire.read_until"),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_post(negative, [])),
        i18n("wire.read_seconds", -1),
      );
      this.assertEqual(
        message_thrown(this, () => port.line_post(text, [])),
        i18n("wire.read_seconds", "5"),
      );
    }

    // Input needs the socket, which only `console.open` makes.
    test_input_unopened(): void {
      const port = console_make();
      const header = jslb.header_make("console.input", { full: true });
      const blob = jslb.blob_make(Uint8Array.of(0x30, 0x0a));
      const line = jslb.line_make(header, [blob], {});
      const message = message_thrown(this, () => port.line_post(line, []));
      this.assertEqual(
        message,
        i18n("wire.socket_missing", constants.console_url),
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
        i18n("wire.read_none"),
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
        i18n("wire.read_twice", "$ "),
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
        i18n("wire.message_empty"),
      );
      this.assertEqual(
        message_thrown(this, () =>
          reader.message_take(message_text(0x33, "x")),
        ),
        i18n("wire.kind_unknown", 0x33),
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
        i18n("wire.output_invalid", "$ "),
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
        i18n("wire.output_invalid", "/"),
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
