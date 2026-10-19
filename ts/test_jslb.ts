// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of jslb.ts: the builders, field access, the encoder and its refusals,
// the debug rendering, the decoder and every hard error, blobs streamed into a
// sink kept in memory, and the vectors of python/vectors, which the test page
// carries as test_vectors, each read whole, by single bytes and split at every
// offset.
namespace test_jslb {
  // The vector files by name, as base64 text, a global the test page sets.
  declare const test_vectors: { readonly [name: string]: string };

  // The limits of the decoders here, as the vectors were made, and texts.
  const constants = Object.freeze({
    line_max: 4096,
    blob_max: 65536,
    overflow_bytes: 1024,
    echo_line: '{"0":{"t":"echo"}}\r',
    vector_suffix: ".jslb",
    sidecar_suffix: ".json",
    backslash: String.fromCharCode(0x5c),
  });

  // A sidecar of `vectors_make.py`: messages and renders, or a fault.
  interface Sidecar {
    messages?: unknown[];
    render?: string[];
    error?: string;
  }

  // The bytes of text whose characters are all below 256, one byte each.
  function bytes_of(text: string): Uint8Array {
    return Uint8Array.from(text, (character) => character.charCodeAt(0));
  }

  // The bytes of the pieces one after another.
  function bytes_join(pieces: readonly Uint8Array[]): Uint8Array {
    let length = 0;
    for (const piece of pieces) {
      length += piece.length;
    }
    const joined = new Uint8Array(length);
    let offset = 0;
    for (const piece of pieces) {
      joined.set(piece, offset);
      offset += piece.length;
    }
    return joined;
  }

  // The bytes as lowercase hex, two characters each.
  function hex_of(data: Uint8Array): string {
    return Array.from(data, (byte) => byte.toString(16).padStart(2, "0")).join(
      "",
    );
  }

  // Bytes that count up from 0 and start again at the period.
  function pattern_make(count: number, period: number): Uint8Array {
    const data = new Uint8Array(count);
    for (let index = 0; index < count; index += 1) {
      data[index] = index % period;
    }
    return data;
  }

  // A `BlobSink` double that keeps each streamed blob in memory by handle.
  class MemorySink implements jslb.BlobSink {
    // The headers given to `sink_open`, in order.
    readonly headers: jslb.BlobHeader[] = [];
    // The pieces of each open blob, by handle.
    readonly #open = new Map<string, Uint8Array[]>();
    // The bytes of each closed blob, by handle.
    readonly #closed = new Map<string, Uint8Array>();

    // Keeps the header and returns a new handle for its blob.
    sink_open(header: jslb.BlobHeader): string {
      this.headers.push(header);
      const handle = `blob_${this.headers.length}`;
      this.#open.set(handle, []);
      return handle;
    }

    // Adds a copy of the bytes to the open blob.
    sink_append(handle: string, data: Uint8Array): void {
      this.#pieces_get(handle).push(data.slice());
    }

    // Ends the blob and returns the `SHA-256` of its bytes.
    sink_close(handle: string): string {
      const data = bytes_join(this.#pieces_get(handle));
      this.#open.delete(handle);
      this.#closed.set(handle, data);
      return utility.sha256_hex(data);
    }

    // The bytes of a closed blob.
    bytes_get(handle: string): Uint8Array {
      const data = this.#closed.get(handle);
      if (data === undefined) {
        throw new Error(`the sink has no closed blob ${handle}`);
      }
      return data;
    }

    // The pieces of an open blob.
    #pieces_get(handle: string): Uint8Array[] {
      const pieces = this.#open.get(handle);
      if (pieces === undefined) {
        throw new Error(`the sink has no open blob ${handle}`);
      }
      return pieces;
    }
  }

  // A `BlobSink` double that has no room for any blob.
  class FullSink implements jslb.BlobSink {
    // Refuses every blob.
    sink_open(): string {
      throw new RangeError("the sink is full");
    }

    // Refuses the bytes, as no blob is open.
    sink_append(): void {
      throw new RangeError("the sink has no open blob");
    }

    // Refuses the end, as no blob is open.
    sink_close(): string {
      throw new RangeError("the sink has no open blob");
    }
  }

  // A new decoder with the limits here, streaming into the sink.
  function decoder_make(sink: jslb.BlobSink): jslb.LineDecoder {
    return new jslb.LineDecoder(
      constants.line_max,
      constants.blob_max,
      constants.overflow_bytes,
      sink,
    );
  }

  // Feeds the pieces to a new decoder and returns every line they finish.
  function pieces_decode(
    sink: jslb.BlobSink,
    pieces: readonly Uint8Array[],
  ): jslb.Line[] {
    const decoder = decoder_make(sink);
    const found: jslb.Line[] = [];
    for (const piece of pieces) {
      found.push(...decoder.bytes_feed(piece));
    }
    return found;
  }

  // The ways to feed bytes: whole, by single bytes, split at each offset.
  function feeds_make(data: Uint8Array): Uint8Array[][] {
    const feeds: Uint8Array[][] = [[data]];
    feeds.push(
      Array.from(data, (_byte, index) => data.subarray(index, index + 1)),
    );
    for (let index = 0; index <= data.length; index += 1) {
      feeds.push([data.subarray(0, index), data.subarray(index)]);
    }
    return feeds;
  }

  // The blob header at a number of a line.
  function blob_at(line: jslb.Line, number: number): jslb.BlobHeader {
    return line[number] as jslb.BlobHeader;
  }

  // The size of a blob header, in either name form.
  function size_of(header: jslb.BlobHeader): number {
    const size = jslb.field_get(header, "size");
    if (typeof size !== "number") {
      throw new Error(`the blob size ${String(size)} is no number`);
    }
    return size;
  }

  // The JSON text the encoder writes for a line, its CR included.
  function encoded_text(line: jslb.Line): string {
    const first = jslb.line_encode(line)[0];
    if (typeof first === "string") {
      throw new Error("the encoder gave a handle before the JSON bytes");
    }
    return utility.utf8_decode(first);
  }

  // The bytes the encoder's pieces stand for, each handle read from the sink.
  function pieces_join(
    pieces: readonly (Uint8Array | string)[],
    sink: MemorySink,
  ): Uint8Array {
    return bytes_join(
      pieces.map((piece) =>
        typeof piece === "string" ? sink.bytes_get(piece) : piece,
      ),
    );
  }

  // A decoded line as a sidecar holds it, each blob's `d` in hex.
  function line_plain(
    line: jslb.Line,
    sink: MemorySink,
  ): { [key: string]: unknown } {
    const plain: { [key: string]: unknown } = { ...line };
    const count = jslb.headers_of(line).length - 1;
    for (let number = 1; number <= count; number += 1) {
      const header = blob_at(line, number);
      const data = header.d;
      const bytes = typeof data === "string" ? sink.bytes_get(data) : data;
      if (bytes === undefined) {
        throw new Error(`blob header ${number} has no d`);
      }
      plain[number] = { ...header, d: hex_of(bytes) };
    }
    return plain;
  }

  // A decoded line without the `sha256` added to each streamed blob.
  function line_sent(line: jslb.Line): jslb.Line {
    const sent: jslb.Line = { ...line };
    const count = jslb.headers_of(line).length - 1;
    for (let number = 1; number <= count; number += 1) {
      const header = blob_at(line, number);
      if (size_of(header) > constants.overflow_bytes) {
        sent[number] = Object.fromEntries(
          Object.entries(header).filter(([name]) => name !== "sha256"),
        );
      }
    }
    return sent;
  }

  // The bytes of a file the test page carries in `test_vectors`.
  function file_bytes(name: string): Uint8Array {
    if (!Object.hasOwn(test_vectors, name)) {
      throw new Error(`test_vectors has no file ${name}`);
    }
    return utility.base64_decode(test_vectors[name]);
  }

  // The sidecar of a vector.
  function sidecar_read(name: string): Sidecar {
    const file = file_bytes(name + constants.sidecar_suffix);
    return JSON.parse(utility.utf8_decode(file)) as Sidecar;
  }

  // The sorted names of the vectors whose sidecar holds a fault, or not.
  function vector_names(error: boolean): string[] {
    const suffix = constants.vector_suffix;
    return Object.keys(test_vectors)
      .filter((file) => file.endsWith(suffix))
      .map((file) => file.slice(0, -suffix.length))
      .sort()
      .filter((name) => (sidecar_read(name).error !== undefined) === error);
  }

  // A test case with the asserts of the two kinds of refusal.
  class RefusalCase extends unittest.TestCase {
    // Asserts the call throws exactly the class. Other throws pass through.
    raised_assert(
      kind: new (...args: never[]) => Error,
      fn: () => unknown,
      message?: string,
    ): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === kind) {
          return;
        }
        throw error;
      }
      const standard = `${kind.name} not raised`;
      this.fail(message === undefined ? standard : `${standard} : ${message}`);
    }

    // Asserts the bytes throw `WireError` and leave the decoder unusable.
    refused_assert(data: Uint8Array): void {
      const decoder = decoder_make(new MemorySink());
      this.raised_assert(jslb.WireError, () => decoder.bytes_feed(data));
      this.raised_assert(jslb.WireError, () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
    }
  }

  // Tests `header_make`, `blob_make` and `line_make`.
  export class TestBuild extends RefusalCase {
    // A header holds only its type when every field is at its default.
    test_header_defaults(): void {
      const header = jslb.header_make("echo", { version: 0 });
      this.assertEqual(Object.entries(header), [["t", "echo"]]);
      const full = jslb.header_make("echo", { full: true });
      this.assertEqual(Object.entries(full), [["type", "echo"]]);
    }

    // Every field is set, in order, with short names.
    test_header_short(): void {
      const header = jslb.header_make("kv.put", {
        version: 1,
        id: 2,
        reply: 3,
        key: "a",
      });
      this.assertEqual(Object.entries(header), [
        ["t", "kv.put"],
        ["v", 1],
        ["i", 2],
        ["r", 3],
        ["k", "a"],
      ]);
    }

    // Every field is set, in order, with full names.
    test_header_full(): void {
      const header = jslb.header_make("kv.put", {
        version: 1,
        id: 2,
        reply: 3,
        key: "a",
        full: true,
      });
      this.assertEqual(Object.entries(header), [
        ["type", "kv.put"],
        ["version", 1],
        ["id", 2],
        ["reply", 3],
        ["key", "a"],
      ]);
    }

    // A blob of bytes is measured and keeps the same bytes object as `d`.
    test_blob_bytes(): void {
      const data = Uint8Array.of(0x0d, 0x0a, 0x03);
      const blob = jslb.blob_make(data, "a/b", { mime: "text/plain" });
      this.assertEqual(Object.keys(blob), ["s", "k", "mime", "d"]);
      this.assertEqual(blob.s, 3);
      this.assertTrue(blob.d === data);
    }

    // A handle names bytes that `blob_make` cannot measure, so it is refused.
    test_blob_handle(): void {
      this.raised_assert(Error, () => jslb.blob_make("blob_1"));
    }

    // A field that `blob_make` sets cannot be given as a handler field.
    test_blob_reserved(): void {
      for (const name of ["s", "k", "d", "size", "key", "data"]) {
        const fields = { [name]: 1 };
        this.raised_assert(
          Error,
          () => jslb.blob_make(new Uint8Array(0), undefined, fields),
          name,
        );
      }
    }

    // Blob headers are numbered from 1 and counted in a copy of the header.
    test_line_numbering(): void {
      const header = jslb.header_make("echo", { id: 1 });
      const first = jslb.blob_make(bytes_of("one"));
      const second = jslb.blob_make(bytes_of("two"), "k");
      const line = jslb.line_make(header, [first, second], { text: "x" });
      this.assertEqual(Object.keys(line), ["0", "1", "2", "text"]);
      this.assertEqual(Object.entries(line[0]), [
        ["t", "echo"],
        ["i", 1],
        ["b", 2],
      ]);
      this.assertEqual(Object.entries(header), [
        ["t", "echo"],
        ["i", 1],
      ]);
      this.assertEqual(line[1], first);
      this.assertEqual(line[2], second);
    }

    // A line with no blobs leaves the count out.
    test_line_empty(): void {
      const line = jslb.line_make(jslb.header_make("echo"), [], {});
      this.assertEqual(line, { 0: { t: "echo" } });
    }

    // A full header gives the blob headers full names for size and key.
    test_line_full(): void {
      const header = jslb.header_make("echo", { full: true });
      const data = bytes_of("ab");
      const blob = jslb.blob_make(data, "k", { n: 1 });
      const line = jslb.line_make(header, [blob], {});
      this.assertEqual(Object.entries(line[0]), [
        ["type", "echo"],
        ["blobs", 1],
      ]);
      this.assertEqual(Object.entries(blob_at(line, 1)), [
        ["size", 2],
        ["key", "k"],
        ["n", 1],
        ["d", data],
      ]);
    }

    // A header that already counts blobs is refused.
    test_line_counted(): void {
      const header: jslb.LineHeader = { ...jslb.header_make("echo"), b: 1 };
      const blob = jslb.blob_make(bytes_of("x"));
      this.raised_assert(Error, () => jslb.line_make(header, [blob], {}));
    }

    // A payload key of decimal digits would read as a header, so is refused.
    test_payload_refused(): void {
      const header = jslb.header_make("echo");
      for (const key of ["0", "5", "01", "00"]) {
        const payload = { [key]: 1 };
        this.raised_assert(
          jslb.WireError,
          () => jslb.line_make(header, [], payload),
          key,
        );
      }
    }
  }

  // Tests `field_get`, `headers_of` and `payload_of`.
  export class TestFields extends RefusalCase {
    // Either name form finds each field of a short header.
    test_field_short(): void {
      const made = jslb.header_make("echo", {
        version: 2,
        id: 3,
        reply: 4,
        key: "k",
      });
      const header: jslb.LineHeader = { ...made, b: 1 };
      const expected: [string, string, unknown][] = [
        ["t", "type", "echo"],
        ["v", "version", 2],
        ["i", "id", 3],
        ["r", "reply", 4],
        ["k", "key", "k"],
        ["b", "blobs", 1],
      ];
      for (const [short, full, value] of expected) {
        this.assertEqual(jslb.field_get(header, short), value);
        this.assertEqual(jslb.field_get(header, full), value);
      }
    }

    // Either name form finds each field of full headers, blob headers too.
    test_field_full(): void {
      const header = jslb.header_make("echo", { version: 2, full: true });
      this.assertEqual(jslb.field_get(header, "t"), "echo");
      this.assertEqual(jslb.field_get(header, "version"), 2);
      const data = bytes_of("ab");
      const line = jslb.line_make(header, [jslb.blob_make(data, "k")], {});
      const blob = blob_at(line, 1);
      this.assertEqual(jslb.field_get(blob, "s"), 2);
      this.assertEqual(jslb.field_get(blob, "key"), "k");
      this.assertTrue(jslb.field_get(blob, "data") === data);
    }

    // An absent field gives its default, or `undefined` when it has none.
    test_field_defaults(): void {
      const header = jslb.header_make("echo");
      this.assertEqual(jslb.field_get(header, "version"), 0);
      this.assertEqual(jslb.field_get(header, "b"), 0);
      for (const name of ["i", "reply", "k"]) {
        this.assertTrue(jslb.field_get(header, name) === undefined, name);
      }
      this.assertTrue(jslb.field_get({ s: 0 }, "d") === undefined);
    }

    // An absent required field throws, as does a name that is no field.
    test_field_refused(): void {
      const line_header = {} as jslb.LineHeader;
      this.raised_assert(Error, () => jslb.field_get(line_header, "type"));
      const blob_header = {} as jslb.BlobHeader;
      this.raised_assert(Error, () => jslb.field_get(blob_header, "s"));
      const header = jslb.header_make("echo");
      this.raised_assert(Error, () => jslb.field_get(header, "sha256"));
    }

    // A header holding both forms of a field throws.
    test_field_forms(): void {
      const header = { ...jslb.header_make("echo"), type: "echo" };
      this.raised_assert(jslb.WireError, () => jslb.field_get(header, "t"));
    }

    // Probing stops at the first missing integer key, strings included.
    test_headers_probing(): void {
      const stored = {
        0: jslb.header_make("scene"),
        1: "/metaverse/castle/1",
        2: "/metaverse/hall/3",
        4: "/metaverse/after/gap",
        body: { text: "x" },
      };
      this.assertEqual(jslb.headers_of(stored), [
        { t: "scene" },
        "/metaverse/castle/1",
        "/metaverse/hall/3",
      ]);
      this.assertEqual(jslb.headers_of({}), []);
    }

    // The payload is every key that is not an integer key, in order.
    test_payload_keys(): void {
      const blob = jslb.blob_make(bytes_of("x"));
      const header = jslb.header_make("echo");
      const line = jslb.line_make(header, [blob], { b: 1, a: 2 });
      this.assertEqual(Object.entries(jslb.payload_of(line)), [
        ["b", 1],
        ["a", 2],
      ]);
    }
  }

  // Tests `line_encode` and its refusals.
  export class TestEncode extends RefusalCase {
    // A line with no blobs is its JSON text with no spaces and a CR.
    test_encode_empty(): void {
      const header = jslb.header_make("echo");
      const line = jslb.line_make(header, [], { a: [1, { b: null }] });
      this.assertEqual(jslb.line_encode(line), [
        bytes_of('{"0":{"t":"echo"},"a":[1,{"b":null}]}\r'),
      ]);
    }

    // Integer keys come first in ascending order, in nested objects too.
    test_encode_order(): void {
      const line: jslb.Line = {
        z: { y: 1, 1: "one", 0: "zero" },
        1: jslb.blob_make(bytes_of("x")),
        0: { t: "echo", b: 1 },
      };
      this.assertEqual(
        encoded_text(line),
        '{"0":{"t":"echo","b":1},"1":{"s":1},' +
          '"z":{"0":"zero","1":"one","y":1}}\r',
      );
    }

    // Digit keys beyond the array indices are integer keys all the same.
    test_encode_keys(): void {
      const value = {
        b: 1,
        "4294967296": 2,
        "4294967295": 3,
        "9007199254740993": 4,
        "9007199254740992": 5,
        7: 6,
        "01": 7,
      };
      const line = jslb.line_make(jslb.header_make("echo"), [], { value });
      this.assertEqual(
        encoded_text(line),
        '{"0":{"t":"echo"},"value":{"7":6,"4294967295":3,"4294967296":2,' +
          '"9007199254740992":5,"9007199254740993":4,"b":1,"01":7}}\r',
      );
    }

    // Each blob's `d` follows the JSON as the same bytes object or handle.
    test_encode_blobs(): void {
      const data = Uint8Array.of(0x0d, 0x03, 0x04);
      const handle: jslb.BlobHeader = { s: 10, k: "k", d: "blob_9" };
      const blobs = [jslb.blob_make(data), handle];
      const line = jslb.line_make(jslb.header_make("echo"), blobs, {});
      const pieces = jslb.line_encode(line);
      this.assertEqual(pieces.length, 3);
      this.assertEqual(
        pieces[0],
        bytes_of(
          '{"0":{"t":"echo","b":2},"1":{"s":3},"2":{"s":10,"k":"k"}}\r',
        ),
      );
      this.assertTrue(pieces[1] === data);
      this.assertEqual(pieces[2], "blob_9");
    }

    // Text is raw `UTF-8`, escaped as JSON does, with no CR but the last.
    test_encode_text(): void {
      const raw = String.fromCodePoint(0xe9, 0x4e2d, 0x1f600, 0x7f, 0x2028);
      const slash = constants.backslash;
      const text = raw + "\r\n" + String.fromCharCode(0) + '"' + slash;
      const line = jslb.line_make(jslb.header_make("echo"), [], { text });
      const escapes = [`${slash}r`, `${slash}n`, `${slash}u0000`];
      const quoted = `${escapes.join("")}${slash}"${slash}${slash}`;
      const expected = `{"0":{"t":"echo"},"text":"${raw}${quoted}"}\r`;
      const encoded = encoded_text(line);
      this.assertEqual(encoded, expected);
      this.assertEqual(encoded.split("\r").length, 2);
    }

    // Integers within `2 ** 53` either way are written, larger ones refused.
    test_integer_limits(): void {
      const header = jslb.header_make("echo");
      const line = jslb.line_make(header, [], {
        high: 2 ** 53,
        low: -(2 ** 53),
      });
      this.assertEqual(
        encoded_text(line),
        '{"0":{"t":"echo"},"high":9007199254740992,' +
          '"low":-9007199254740992}\r',
      );
      const values: unknown[] = [
        2 ** 53 + 2,
        -(2 ** 53) - 2,
        [2 ** 60],
        { a: 2 ** 60 },
        1e300,
      ];
      for (const value of values) {
        const refused = jslb.line_make(header, [], { value });
        this.raised_assert(Error, () => jslb.line_encode(refused));
      }
    }

    // `NaN` and the infinities are refused.
    test_float_refused(): void {
      const header = jslb.header_make("echo");
      for (const value of [NaN, Infinity, -Infinity, [NaN]]) {
        const refused = jslb.line_make(header, [], { value });
        this.raised_assert(Error, () => jslb.line_encode(refused));
      }
    }

    // A value that JSON has no text for is refused, not dropped or changed.
    test_value_refused(): void {
      const header = jslb.header_make("echo");
      const values: unknown[] = [
        undefined,
        [undefined],
        new Array(1),
        () => 1,
        BigInt(1),
        Symbol("x"),
        new Uint8Array(1),
        new Map(),
        new Date(0),
      ];
      for (const value of values) {
        const refused = jslb.line_make(header, [], { value });
        this.raised_assert(Error, () => jslb.line_encode(refused));
      }
    }

    // Text holding half a surrogate pair is refused, in values and keys.
    test_text_refused(): void {
      const header = jslb.header_make("echo");
      const high = String.fromCharCode(0xd800);
      const low = String.fromCharCode(0xdc00);
      const payloads = [{ text: "a" + high }, { value: { [low]: 1 } }];
      for (const payload of payloads) {
        const refused = jslb.line_make(header, [], payload);
        this.raised_assert(Error, () => jslb.line_encode(refused));
        this.raised_assert(Error, () => jslb.line_render(refused));
      }
    }

    // A payload key of digits is refused, a nested one is written as it is.
    test_key_digits(): void {
      const line: jslb.Line = { 0: { t: "echo" }, "01": 1 };
      this.raised_assert(jslb.WireError, () => jslb.line_encode(line));
      const header = jslb.header_make("echo");
      const value = { "01": 1, 5: 2 };
      const nested = jslb.line_make(header, [], { value });
      this.assertEqual(
        encoded_text(nested),
        '{"0":{"t":"echo"},"value":{"5":2,"01":1}}\r',
      );
    }

    // A blob whose `d` is missing or of another size is refused.
    test_size_differs(): void {
      const header = jslb.header_make("echo");
      const blob = { ...jslb.blob_make(bytes_of("abc")), s: 4 };
      const differs = jslb.line_make(header, [blob], {});
      this.raised_assert(Error, () => jslb.line_encode(differs));
      const bare: jslb.BlobHeader = { s: 3 };
      const missing = jslb.line_make(header, [bare], {});
      this.raised_assert(Error, () => jslb.line_encode(missing));
    }

    // The encoder refuses a line that the decoder would refuse.
    test_encode_checked(): void {
      const empty = {} as jslb.Line;
      this.raised_assert(jslb.WireError, () => jslb.line_encode(empty));
      const blob = jslb.blob_make(bytes_of("x"));
      const counted = jslb.line_make(jslb.header_make("echo"), [blob], {});
      counted[0].b = 2;
      this.raised_assert(jslb.WireError, () => jslb.line_encode(counted));
      const header = { ...jslb.header_make("echo"), x: 1 };
      const extra = jslb.line_make(header, [], {});
      this.raised_assert(jslb.WireError, () => jslb.line_encode(extra));
    }
  }

  // Tests `line_render`, the debug form.
  export class TestRender extends unittest.TestCase {
    // The JSON text is followed by one tag per blob, numbered from 1.
    test_render_blobs(): void {
      const blobs = [
        jslb.blob_make(bytes_of("\r")),
        jslb.blob_make(bytes_of("ab"), "k"),
      ];
      const header = jslb.header_make("echo", { id: 1 });
      const line = jslb.line_make(header, blobs, { n: 1 });
      this.assertEqual(
        jslb.line_render(line),
        '{"0":{"t":"echo","i":1,"b":2},"1":{"s":1},"2":{"s":2,"k":"k"},' +
          '"n":1}<blob "n"=1><blob "n"=2>',
      );
    }

    // A line with no blobs renders as its JSON text alone.
    test_render_plain(): void {
      const header = jslb.header_make("echo", { full: true });
      const line = jslb.line_make(header, [], {});
      this.assertEqual(jslb.line_render(line), '{"0":{"type":"echo"}}');
    }
  }

  // Tests `LineDecoder` on lines and blobs in memory and on every hard error.
  export class TestDecode extends RefusalCase {
    // A line decodes to plain objects, and integer keys encode first again.
    test_decode_line(): void {
      const text = '{"0":{"t":"echo","i":1},"x":[{"02":4,"2":3}]}\r';
      const found = pieces_decode(new MemorySink(), [bytes_of(text)]);
      this.assertEqual(found.length, 1);
      const line = found[0];
      this.assertEqual(Object.keys(line), ["0", "x"]);
      this.assertEqual(Object.entries(line[0]), [
        ["t", "echo"],
        ["i", 1],
      ]);
      this.assertEqual(line["x"], [{ 2: 3, "02": 4 }]);
      this.assertEqual(
        encoded_text(line),
        '{"0":{"t":"echo","i":1},"x":[{"2":3,"02":4}]}\r',
      );
    }

    // Nested digit keys beyond the array indices encode as integer keys.
    test_decode_keys(): void {
      const text = '{"0":{"t":"echo"},"x":{"b":1,"4294967296":2,"7":3}}\r';
      const found = pieces_decode(new MemorySink(), [bytes_of(text)]);
      this.assertEqual(found.length, 1);
      this.assertEqual(
        encoded_text(found[0]),
        '{"0":{"t":"echo"},"x":{"7":3,"4294967296":2,"b":1}}\r',
      );
    }

    // Blobs follow the CR, each `d` set to its bytes, empty ones too.
    test_decode_blobs(): void {
      const text =
        '{"0":{"t":"echo","b":3},"1":{"s":2},"2":{"s":0},' +
        '"3":{"s":0,"k":"z"}}\r\r\n';
      const found = pieces_decode(new MemorySink(), [bytes_of(text)]);
      this.assertEqual(found.length, 1);
      const line = found[0];
      this.assertEqual(blob_at(line, 1).d, bytes_of("\r\n"));
      this.assertFalse(Object.hasOwn(blob_at(line, 1), "sha256"));
      this.assertEqual(blob_at(line, 2).d, new Uint8Array(0));
      this.assertEqual(Object.entries(blob_at(line, 3)), [
        ["s", 0],
        ["k", "z"],
        ["d", new Uint8Array(0)],
      ]);
    }

    // A line whose blobs are all empty is complete at its CR.
    test_blob_empty(): void {
      const decoder = decoder_make(new MemorySink());
      const text = '{"0":{"t":"echo","b":1},"1":{"s":0}}\r';
      const found = decoder.bytes_feed(bytes_of(text));
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_at(found[0], 1).d, new Uint8Array(0));
    }

    // Lines come back when their last byte arrives, several in one call.
    test_decode_pieces(): void {
      const decoder = decoder_make(new MemorySink());
      const first = '{"0":{"t":"a","b":1},"1":{"s":3}}\rxy';
      this.assertEqual(decoder.bytes_feed(bytes_of(first)), []);
      const second = 'z{"0":{"t":"b"}}\r{"0":{"t":"c"}}\r{"0"';
      const found = decoder.bytes_feed(bytes_of(second));
      this.assertEqual(
        found.map((line) => line[0].t),
        ["a", "b", "c"],
      );
      this.assertEqual(blob_at(found[0], 1).d, bytes_of("xyz"));
      this.assertEqual(decoder.bytes_feed(new Uint8Array(0)), []);
      const last = decoder.bytes_feed(bytes_of(':{"t":"d"}}\r'));
      this.assertEqual(
        last.map((line) => line[0].t),
        ["d"],
      );
    }

    // A line of `line_max` bytes with its CR is read, one byte more is not.
    test_line_max(): void {
      const prefix = '{"0":{"t":"echo"},"pad":"';
      const suffix = '"}\r';
      const length = constants.line_max - prefix.length - suffix.length;
      const pad = "a".repeat(length);
      const text = prefix + pad + suffix;
      this.assertEqual(
        pieces_decode(new MemorySink(), [bytes_of(text)]).length,
        1,
      );
      this.refused_assert(bytes_of(prefix + pad + "a" + suffix));
    }

    // A line is refused once it passes `line_max`, before its CR arrives.
    test_line_early(): void {
      const decoder = decoder_make(new MemorySink());
      const open = "{".repeat(constants.line_max - 1);
      this.assertEqual(decoder.bytes_feed(bytes_of(open)), []);
      this.raised_assert(jslb.WireError, () =>
        decoder.bytes_feed(bytes_of("{")),
      );
    }

    // A blob of `blob_max` bytes is read, one more is refused at the CR.
    test_blob_max(): void {
      const largest = constants.blob_max;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${largest}}}\r`;
      const data = new Uint8Array(largest);
      const found = pieces_decode(new MemorySink(), [bytes_of(text), data]);
      this.assertEqual(found.length, 1);
      const over = `{"0":{"t":"echo","b":1},"1":{"s":${largest + 1}}}\r`;
      this.refused_assert(bytes_of(over));
    }

    // A line without header 0 is refused.
    test_header_missing(): void {
      this.refused_assert(bytes_of('{"t":"echo"}\r'));
      this.refused_assert(bytes_of('{"1":{"s":0}}\r'));
    }

    // A header that is not a JSON object is refused.
    test_header_object(): void {
      this.refused_assert(bytes_of('{"0":"echo"}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo","b":1},"1":[]}\r'));
    }

    // A line header without a type string is refused.
    test_type_missing(): void {
      this.refused_assert(bytes_of('{"0":{"i":1}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":null}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":1}}\r'));
      this.refused_assert(bytes_of('{"0":{}}\r'));
    }

    // A blob count that differs from the blob headers is refused.
    test_count_mismatch(): void {
      this.refused_assert(bytes_of('{"0":{"t":"echo","b":2},"1":{"s":0}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo"},"1":{"s":0}}\r'));
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":true},"1":{"s":0}}\r'),
      );
      this.refused_assert(bytes_of('{"0":{"t":"echo","b":-1}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo","b":0.5}}\r'));
    }

    // A gap in the blob headers is refused, a huge integer key too.
    test_header_gap(): void {
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":2},"1":{"s":0},"3":{"s":0}}\r'),
      );
      this.refused_assert(bytes_of('{"0":{"t":"echo","b":1},"2":{"s":0}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo"},"4294967296":{}}\r'));
    }

    // A size that is not a non negative integer is refused.
    test_size_invalid(): void {
      for (const size of ["-1", "1.5", '"1"', "true", "null"]) {
        const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\r`;
        this.refused_assert(bytes_of(text));
      }
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"k":"a"}}\r'),
      );
    }

    // A payload key of decimal digits is refused.
    test_payload_digits(): void {
      this.refused_assert(bytes_of('{"0":{"t":"echo"},"01":1}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo"},"00":1}\r'));
    }

    // Short and full names in one line are refused, across headers too.
    test_forms_mixed(): void {
      this.refused_assert(bytes_of('{"0":{"t":"echo","version":1}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo","type":"echo"}}\r'));
      this.refused_assert(
        bytes_of('{"0":{"type":"echo","blobs":1},"1":{"s":0}}\r'),
      );
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"s":0,"key":"a"}}\r'),
      );
    }

    // An unknown field in the line header is refused.
    test_line_field(): void {
      this.refused_assert(bytes_of('{"0":{"t":"echo","x":1}}\r'));
      this.refused_assert(bytes_of('{"0":{"t":"echo","s":1}}\r'));
    }

    // A blob header that carries `d` or `data` on the wire is refused.
    test_data_sent(): void {
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"s":0,"d":""}}\r'),
      );
      this.refused_assert(
        bytes_of('{"0":{"type":"echo","blobs":1},"1":{"size":0,"data":""}}\r'),
      );
    }

    // A line that is not strict `UTF-8` or not a JSON object is refused.
    test_text_invalid(): void {
      const start = bytes_of('{"0":{"t":"');
      const end = bytes_of('"}}\r');
      const middles = [[0xff], [0xed, 0xa0, 0x80], [0xc0, 0x80]];
      for (const middle of middles) {
        this.refused_assert(bytes_join([start, Uint8Array.from(middle), end]));
      }
      const mark = Uint8Array.of(0xef, 0xbb, 0xbf);
      this.refused_assert(bytes_join([mark, bytes_of(constants.echo_line)]));
      this.refused_assert(bytes_of("{\r"));
      this.refused_assert(bytes_of('[{"0":{"t":"echo"}}]\r'));
      this.refused_assert(bytes_of("\r"));
    }

    // The `NaN` and `Infinity` constants are refused.
    test_constant_refused(): void {
      for (const constant of ["NaN", "Infinity", "-Infinity"]) {
        this.refused_assert(bytes_of(`{"0":{"t":"echo"},"n":${constant}}\r`));
      }
    }
  }

  // Tests blobs over `overflow_bytes`, streamed into the sink.
  export class TestStream extends RefusalCase {
    // A blob one byte over goes to the sink, `d` its handle, then `sha256`.
    test_stream_sink(): void {
      const sink = new MemorySink();
      const data = pattern_make(constants.overflow_bytes + 1, 256);
      const text =
        `{"0":{"t":"echo","b":2},"1":{"s":${data.length},"k":"big"},` +
        '"2":{"s":1}}\r';
      const pieces = [bytes_of(text), data, bytes_of("x")];
      const found = pieces_decode(sink, pieces);
      this.assertEqual(found.length, 1);
      const blob = blob_at(found[0], 1);
      this.assertTrue(sink.headers[0] === blob);
      this.assertEqual(Object.keys(blob), ["s", "k", "d", "sha256"]);
      this.assertEqual(blob.d, "blob_1");
      this.assertEqual(blob["sha256"], utility.sha256_hex(data));
      this.assertEqual(sink.bytes_get("blob_1"), data);
      this.assertEqual(blob_at(found[0], 2).d, bytes_of("x"));
    }

    // A blob of exactly `overflow_bytes` stays in memory, with no sink.
    test_stream_exact(): void {
      const sink = new MemorySink();
      const data = pattern_make(constants.overflow_bytes, 256);
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${data.length}}}\r`;
      const found = pieces_decode(sink, [bytes_join([bytes_of(text), data])]);
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_at(found[0], 1).d, data);
      this.assertFalse(Object.hasOwn(blob_at(found[0], 1), "sha256"));
      this.assertEqual(sink.headers.length, 0);
    }

    // A streamed blob fed one byte at a time gives the same bytes and hash.
    test_stream_bytes(): void {
      const sink = new MemorySink();
      const data = pattern_make(3 * constants.overflow_bytes, 251);
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${data.length}}}\r`;
      const stream = bytes_join([bytes_of(text), data]);
      const found = pieces_decode(
        sink,
        Array.from(stream, (_byte, index) =>
          stream.subarray(index, index + 1),
        ),
      );
      this.assertEqual(found.length, 1);
      this.assertEqual(sink.bytes_get("blob_1"), data);
      const sha256 = blob_at(found[0], 1)["sha256"];
      this.assertEqual(sha256, utility.sha256_hex(data));
    }

    // A sink that throws ends the feed, and the decoder is unusable after.
    test_sink_failure(): void {
      const decoder = decoder_make(new FullSink());
      const size = constants.overflow_bytes + 1;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\r`;
      this.raised_assert(RangeError, () => decoder.bytes_feed(bytes_of(text)));
      this.raised_assert(jslb.WireError, () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
    }
  }

  // Reads each vector of `test_vectors`, whole, by bytes and split.
  export class TestVectors extends RefusalCase {
    // Each success vector decodes to its sidecar and encodes to its bytes.
    test_vectors_success(): void {
      const names = vector_names(false);
      this.assertTrue(names.length > 0, "no success vectors in test_vectors");
      for (const name of names) {
        const data = file_bytes(name + constants.vector_suffix);
        const sidecar = sidecar_read(name);
        const messages = JSON.stringify(sidecar.messages);
        for (const pieces of feeds_make(data)) {
          const sink = new MemorySink();
          const found = pieces_decode(sink, pieces);
          const plain = found.map((line) => line_plain(line, sink));
          this.assertEqual(JSON.stringify(plain), messages, name);
          const renders = found.map((line) => jslb.line_render(line));
          this.assertEqual(renders, sidecar.render, name);
        }
        const encoder_sink = new MemorySink();
        const encoded = pieces_decode(encoder_sink, [data]).map((line) =>
          pieces_join(jslb.line_encode(line_sent(line)), encoder_sink),
        );
        this.assertEqual(bytes_join(encoded), data, name);
      }
    }

    // Each error vector throws `WireError` however it is fed.
    test_vectors_error(): void {
      const names = vector_names(true);
      this.assertTrue(names.length > 0, "no error vectors in test_vectors");
      for (const name of names) {
        const data = file_bytes(name + constants.vector_suffix);
        for (const pieces of feeds_make(data)) {
          this.raised_assert(
            jslb.WireError,
            () => pieces_decode(new MemorySink(), pieces),
            name,
          );
        }
      }
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its declaration.
    test_frozen_names(): void {
      const names = [
        "LineDecoder",
        "WireError",
        "blob_make",
        "field_get",
        "header_make",
        "headers_of",
        "line_encode",
        "line_make",
        "line_render",
        "payload_of",
      ];
      this.assertTrue(Object.isFrozen(jslb));
      this.assertEqual(Object.keys(jslb).sort(), names);
      this.assertTrue(new jslb.WireError("x") instanceof Error);
    }
  }
}
Object.freeze(test_jslb);
