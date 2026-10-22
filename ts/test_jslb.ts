// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of jslb.ts: the builders, field access, the encoder and its refusals,
// the debug rendering, the decoder, its limits, its deferred fault and every
// hard error, each refusal compared with its message, blobs streamed into a
// sink kept in memory, and the vectors of build/vectors, which the test page
// carries as test_vectors, each read with the limits its sidecar names, whole,
// by single bytes and split at every offset.
namespace test_jslb {
  // The vector files by name, as base64 text, a global the test page sets.
  declare const test_vectors: { readonly [name: string]: string };

  // The limits of the decoders here, and texts.
  const constants = Object.freeze({
    // The longest line read with its CR, its writer's choice.
    line_max: 4096,
    // The most bytes one message's blobs come to, its writer's choice.
    blob_max: 65536,
    // The largest blob kept in memory, its writer's choice.
    overflow_bytes: 1024,
    // The digits of a number too long for a double, its writer's choice.
    long_digits: 5000,
    echo_text: '{"0":{"t":"echo"}}',
    echo_line: '{"0":{"t":"echo"}}\r',
    vector_suffix: ".jslb",
    sidecar_suffix: ".json",
    backslash: String.fromCharCode(0x5c),
  });

  // The limits a vector's decoder is built with, as its sidecar holds them.
  interface VectorLimits {
    line_max: number;
    blob_max: number;
    overflow_bytes: number;
  }

  // A sidecar: its limits, messages, renders, and fault or `canonical`.
  interface VectorSidecar {
    limits: VectorLimits;
    messages: unknown[];
    render: string[];
    canonical?: boolean;
    error?: string;
  }

  // An error vector's expected fault: its slug, then its message.
  type FaultExpected = readonly [string, string];

  // The expected fault of each error vector, by name.
  type FaultTable = { readonly [name: string]: FaultExpected };

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

  // Whether two byte arrays hold the same bytes.
  function bytes_equal(first: Uint8Array, second: Uint8Array): boolean {
    return (
      first.length === second.length &&
      first.every((byte, index) => byte === second[index])
    );
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

  // The text of what a call throws, which it must throw.
  function thrown_text(call: () => unknown): string {
    try {
      call();
    } catch (error) {
      return String(error);
    }
    throw new Error("the call threw nothing");
  }

  // The message the decoder gives for line text that JSON cannot parse.
  function parse_refusal(text: string): string {
    const reason = thrown_text(() => JSON.parse(text));
    return i18n("jslb.line_not_json", reason);
  }

  // The message the decoder gives for line bytes that are not `UTF-8`.
  function decode_refusal(data: Uint8Array): string {
    const reason = thrown_text(() => utility.utf8_decode(data));
    return i18n("jslb.line_not_utf8", reason);
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

  // A `BlobSink` double whose appends fail as on a full disk, closes recorded.
  class FailingSink implements jslb.BlobSink {
    // The text of the error every append throws.
    readonly message = "the sink has no room left";
    // The handles closed, in order.
    readonly closed: string[] = [];

    // Opens the one blob the double holds.
    sink_open(): string {
      return "blob_1";
    }

    // Refuses the bytes, as a full disk does.
    sink_append(): void {
      throw new RangeError(this.message);
    }

    // Records the close and returns the hash of the bytes it kept, none.
    sink_close(handle: string): string {
      this.closed.push(handle);
      return utility.sha256_hex(new Uint8Array(0));
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

  // A new decoder with a sidecar's limits, streaming into the sink.
  function sidecar_decoder(
    sidecar: VectorSidecar,
    sink: jslb.BlobSink,
  ): jslb.LineDecoder {
    const limits = sidecar.limits;
    return new jslb.LineDecoder(
      limits.line_max,
      limits.blob_max,
      limits.overflow_bytes,
      sink,
    );
  }

  // Feeds the pieces to the decoder and returns every line they finish.
  function pieces_decode(
    decoder: jslb.LineDecoder,
    pieces: readonly Uint8Array[],
  ): jslb.Line[] {
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

  // An `echo` message, its line padded to the length in bytes, then blobs.
  function message_padded(
    length: number,
    blobs: readonly Uint8Array[],
  ): Uint8Array {
    const made = blobs.map((data) => jslb.blob_make(data));
    const header = jslb.header_make("echo");
    const empty = jslb.line_make(header, made, { pad: "" });
    const short = jslb.line_encode(empty)[0].length;
    const pad = "a".repeat(length - short);
    const line = jslb.line_make(header, made, { pad });
    return pieces_join(jslb.line_encode(line), new MemorySink());
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
      if (typeof header.d === "string") {
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
  function sidecar_read(name: string): VectorSidecar {
    const file = file_bytes(name + constants.sidecar_suffix);
    return JSON.parse(utility.utf8_decode(file)) as VectorSidecar;
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

  // Each error vector's slug and its message under the limits, by name.
  function errors_expected(limits: VectorLimits): FaultTable {
    const { line_max, blob_max } = limits;
    const over: FaultExpected = [
      "blobs_over",
      i18n("jslb.blobs_over", blob_max + 1, blob_max),
    ];
    const start = bytes_of('{"0":{"t":"');
    const end = bytes_of('"}}');
    const overlong = bytes_join([start, Uint8Array.of(0xc0, 0x80), end]);
    const surrogate = bytes_join([
      start,
      Uint8Array.of(0xed, 0xa0, 0x80),
      end,
    ]);
    const header: FaultExpected = [
      "no_header_zero",
      i18n("jslb.no_header_zero"),
    ];
    const size: FaultExpected = ["bad_size", i18n("jslb.bad_size", 1)];
    const forms: FaultExpected = [
      "both_name_forms",
      i18n("jslb.both_name_forms"),
    ];
    const typed: FaultExpected = ["no_type", i18n("jslb.no_type")];
    return {
      error_after_line: header,
      error_bad_size_boolean: size,
      error_bad_size_fraction: size,
      error_bad_size_missing: size,
      error_bad_size_negative: size,
      error_bad_size_string: size,
      error_blob_data: ["blob_data_field", i18n("jslb.blob_data_field", 1)],
      error_blob_gap: ["blob_gap", i18n("jslb.blob_gap", 2, 3)],
      error_blob_gap_first: ["blob_gap", i18n("jslb.blob_gap", 1, 2)],
      error_blob_over_max: over,
      error_blobs_mismatch: [
        "blobs_mismatch",
        i18n("jslb.blobs_mismatch", 2, 1),
      ],
      error_blobs_mismatch_boolean: [
        "blobs_mismatch",
        i18n("jslb.blobs_mismatch", true, 1),
      ],
      error_blobs_mismatch_extra: [
        "blobs_mismatch",
        i18n("jslb.blobs_mismatch", 0, 1),
      ],
      error_blobs_over: over,
      error_both_name_forms: forms,
      error_both_name_forms_blob: forms,
      error_header_not_object: [
        "header_not_object",
        i18n("jslb.header_not_object", 0),
      ],
      error_header_not_object_blob: [
        "header_not_object",
        i18n("jslb.header_not_object", 1),
      ],
      error_infinity: [
        "line_not_json",
        parse_refusal('{"0":{"t":"echo"},"n":Infinity}'),
      ],
      error_line_over_max: [
        "line_over_max",
        i18n("jslb.line_over_max", line_max),
      ],
      error_nan: [
        "line_not_json",
        parse_refusal('{"0":{"t":"echo"},"n":NaN}'),
      ],
      error_no_header_zero: header,
      error_no_type: typed,
      error_no_type_string: typed,
      error_not_object: ["line_not_object", i18n("jslb.line_not_object")],
      error_payload_digit_key: [
        "payload_digit_key",
        i18n("jslb.payload_digit_key", "01"),
      ],
      error_unknown_line_field: [
        "unknown_line_field",
        i18n("jslb.unknown_line_field", "x"),
      ],
      error_utf8_overlong: ["line_not_utf8", decode_refusal(overlong)],
      error_utf8_surrogate: ["line_not_utf8", decode_refusal(surrogate)],
    };
  }

  // A test case with the asserts of a refusal and its message.
  class RefusalCase extends unittest.TestCase {
    // Asserts the call throws exactly the class with exactly the message.
    raised_assert(
      kind: new (...args: never[]) => Error,
      message: string,
      fn: () => unknown,
      note?: string,
    ): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === kind) {
          this.assertEqual(error.message, message, note);
          return;
        }
        throw error;
      }
      const standard = `${kind.name} not raised`;
      this.fail(note === undefined ? standard : `${standard} : ${note}`);
    }

    // Asserts the bytes throw the message and leave the decoder unusable.
    refused_assert(data: Uint8Array, message: string): MemorySink {
      const sink = new MemorySink();
      const decoder = decoder_make(sink);
      this.raised_assert(jslb.WireError, message, () =>
        decoder.bytes_feed(data),
      );
      this.raised_assert(jslb.WireError, i18n("jslb.decoder_failed"), () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
      return sink;
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

    // A handle takes the size its caller gives, which bytes refuse.
    test_blob_handle(): void {
      const blob = jslb.blob_make("blob_1", "k", { n: 1 }, 10);
      this.assertEqual(Object.entries(blob), [
        ["s", 10],
        ["k", "k"],
        ["n", 1],
        ["d", "blob_1"],
      ]);
      const unmeasured = i18n("jslb.handle_unmeasured", "blob_1");
      this.raised_assert(Error, unmeasured, () => jslb.blob_make("blob_1"));
      const unwanted = i18n("jslb.size_unwanted", 3);
      this.raised_assert(Error, unwanted, () =>
        jslb.blob_make(bytes_of("abc"), undefined, {}, 3),
      );
    }

    // A field that `blob_make` sets cannot be given as a handler field.
    test_blob_reserved(): void {
      for (const name of ["s", "k", "d", "size", "key", "data"]) {
        const fields = { [name]: 1 };
        this.raised_assert(
          Error,
          i18n("jslb.blob_field_reserved", name),
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
      this.raised_assert(Error, i18n("jslb.blobs_preset"), () =>
        jslb.line_make(header, [blob], {}),
      );
    }

    // A payload key of decimal digits would read as a header, so is refused.
    test_payload_refused(): void {
      const header = jslb.header_make("echo");
      for (const key of ["0", "5", "01", "00"]) {
        const payload = { [key]: 1 };
        this.raised_assert(
          jslb.WireError,
          i18n("jslb.payload_digit_key", key),
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
      this.raised_assert(Error, i18n("jslb.field_missing", "type"), () =>
        jslb.field_get(line_header, "type"),
      );
      const blob_header = {} as jslb.BlobHeader;
      this.raised_assert(Error, i18n("jslb.field_missing", "s"), () =>
        jslb.field_get(blob_header, "s"),
      );
      const header = jslb.header_make("echo");
      this.raised_assert(Error, i18n("jslb.field_unknown", "sha256"), () =>
        jslb.field_get(header, "sha256"),
      );
    }

    // A header holding both forms of a field throws.
    test_field_forms(): void {
      const header = { ...jslb.header_make("echo"), type: "echo" };
      this.raised_assert(jslb.WireError, i18n("jslb.both_name_forms"), () =>
        jslb.field_get(header, "t"),
      );
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
      const handle = jslb.blob_make("blob_9", "k", {}, 10);
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

    // Doubles beyond `2 ** 53` are written as JSON writes them, and read back.
    test_double_range(): void {
      const header = jslb.header_make("echo");
      const line = jslb.line_make(header, [], {
        high: 2 ** 53,
        low: -(2 ** 53),
        above: 2 ** 53 + 2,
        tenth: 1e16,
        large: [-1e300],
        top: { a: Number.MAX_VALUE },
      });
      const text =
        '{"0":{"t":"echo"},"high":9007199254740992,' +
        '"low":-9007199254740992,"above":9007199254740994,' +
        '"tenth":10000000000000000,"large":[-1e+300],' +
        '"top":{"a":1.7976931348623157e+308}}';
      this.assertEqual(encoded_text(line), text + "\r");
      this.assertEqual(jslb.line_render(line), text);
      const sent = bytes_of('{"0":{"t":"echo"},"n":1e+16,"m":-1e+300}\r');
      const found = pieces_decode(decoder_make(new MemorySink()), [sent]);
      this.assertEqual(found.length, 1);
      this.assertEqual(jslb.payload_of(found[0]), { n: 1e16, m: -1e300 });
      this.assertEqual(
        encoded_text(found[0]),
        '{"0":{"t":"echo"},"n":10000000000000000,"m":-1e+300}\r',
      );
    }

    // `NaN` and the infinities are refused.
    test_float_refused(): void {
      const header = jslb.header_make("echo");
      const cases: [unknown, number][] = [
        [NaN, NaN],
        [Infinity, Infinity],
        [-Infinity, -Infinity],
        [[NaN], NaN],
      ];
      for (const [value, refused] of cases) {
        const line = jslb.line_make(header, [], { value });
        this.raised_assert(Error, i18n("jslb.number_refused", refused), () =>
          jslb.line_encode(line),
        );
      }
    }

    // A value that JSON has no text for is refused, not dropped or changed.
    test_value_refused(): void {
      const header = jslb.header_make("echo");
      const cases: [unknown, string][] = [
        [undefined, "[object Undefined]"],
        [[undefined], "[object Undefined]"],
        [new Array(1), "[object Undefined]"],
        [() => 1, "[object Function]"],
        [BigInt(1), "[object BigInt]"],
        [Symbol("x"), "[object Symbol]"],
        [new Uint8Array(1), "[object Uint8Array]"],
        [new Map(), "[object Map]"],
        [new Date(0), "[object Date]"],
      ];
      for (const [value, kind] of cases) {
        const line = jslb.line_make(header, [], { value });
        this.raised_assert(Error, i18n("jslb.value_refused", kind), () =>
          jslb.line_encode(line),
        );
      }
    }

    // Text holding half a surrogate pair is refused, in values and keys.
    test_text_refused(): void {
      const header = jslb.header_make("echo");
      const high = String.fromCharCode(0xd800);
      const low = String.fromCharCode(0xdc00);
      const payloads = [{ text: "a" + high }, { value: { [low]: 1 } }];
      const refused = i18n("jslb.text_refused");
      for (const payload of payloads) {
        const line = jslb.line_make(header, [], payload);
        this.raised_assert(Error, refused, () => jslb.line_encode(line));
        this.raised_assert(Error, refused, () => jslb.line_render(line));
      }
    }

    // A payload key of digits is refused, a nested one is written as it is.
    test_key_digits(): void {
      const line: jslb.Line = { 0: { t: "echo" }, "01": 1 };
      const refused = i18n("jslb.payload_digit_key", "01");
      this.raised_assert(jslb.WireError, refused, () =>
        jslb.line_encode(line),
      );
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
      this.raised_assert(Error, i18n("jslb.blob_size_differs", 1, 4, 3), () =>
        jslb.line_encode(differs),
      );
      const bare: jslb.BlobHeader = { s: 3 };
      const missing = jslb.line_make(header, [bare], {});
      this.raised_assert(Error, i18n("jslb.blob_data_missing", 1), () =>
        jslb.line_encode(missing),
      );
    }

    // The encoder refuses a line that the decoder would refuse.
    test_encode_checked(): void {
      const empty = {} as jslb.Line;
      this.raised_assert(jslb.WireError, i18n("jslb.no_header_zero"), () =>
        jslb.line_encode(empty),
      );
      const blob = jslb.blob_make(bytes_of("x"));
      const counted = jslb.line_make(jslb.header_make("echo"), [blob], {});
      counted[0].b = 2;
      this.raised_assert(
        jslb.WireError,
        i18n("jslb.blobs_mismatch", 2, 1),
        () => jslb.line_encode(counted),
      );
      const header = { ...jslb.header_make("echo"), x: 1 };
      const extra = jslb.line_make(header, [], {});
      this.raised_assert(
        jslb.WireError,
        i18n("jslb.unknown_line_field", "x"),
        () => jslb.line_encode(extra),
      );
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

  // Tests `LineDecoder` on lines, blobs in memory, its limits and every fault.
  export class TestDecode extends RefusalCase {
    // A line decodes to plain objects, and integer keys encode first again.
    test_decode_line(): void {
      const text = '{"0":{"t":"echo","i":1},"x":[{"02":4,"2":3}]}\r';
      const decoder = decoder_make(new MemorySink());
      const found = pieces_decode(decoder, [bytes_of(text)]);
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
      const decoder = decoder_make(new MemorySink());
      const found = pieces_decode(decoder, [bytes_of(text)]);
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
      const decoder = decoder_make(new MemorySink());
      const found = pieces_decode(decoder, [bytes_of(text)]);
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

    // An integral float count or size reads as an integer, in either form.
    test_integral_floats(): void {
      const found = pieces_decode(decoder_make(new MemorySink()), [
        bytes_of('{"0":{"t":"echo","b":1.0},"1":{"s":2.0}}\rxy'),
        bytes_of('{"0":{"type":"echo","blobs":1e0},"1":{"size":1.0}}\rz'),
      ]);
      this.assertEqual(found.length, 2);
      for (const [index, data] of ["xy", "z"].entries()) {
        const blob = blob_at(found[index], 1);
        this.assertEqual(jslb.field_get(found[index][0], "blobs"), 1);
        this.assertEqual(jslb.field_get(blob, "size"), data.length);
        this.assertEqual(blob.d, bytes_of(data));
      }
      this.assertEqual(
        jslb.line_render(found[0]),
        '{"0":{"t":"echo","b":1},"1":{"s":2}}<blob "n"=1>',
      );
    }

    // Lines before a fault are returned and the next call throws the fault.
    test_fault_deferred(): void {
      const decoder = decoder_make(new MemorySink());
      const echo = constants.echo_line;
      const data = bytes_of(echo + '{"t":"echo"}\r' + echo);
      this.assertEqual(decoder.bytes_feed(data), [{ 0: { t: "echo" } }]);
      this.assertFalse(decoder.idle());
      const empty = new Uint8Array(0);
      this.raised_assert(jslb.WireError, i18n("jslb.no_header_zero"), () =>
        decoder.bytes_feed(empty),
      );
      this.raised_assert(jslb.WireError, i18n("jslb.decoder_failed"), () =>
        decoder.bytes_feed(empty),
      );
    }

    // The decoder is idle between messages only, and never after a fault.
    test_idle_states(): void {
      const decoder = decoder_make(new MemorySink());
      this.assertTrue(decoder.idle());
      const head = bytes_of('{"0":{"t":"echo","b":1}');
      this.assertEqual(decoder.bytes_feed(head), []);
      this.assertFalse(decoder.idle());
      const rest = bytes_of(',"1":{"s":2}}\rx');
      this.assertEqual(decoder.bytes_feed(rest), []);
      this.assertFalse(decoder.idle());
      this.assertEqual(decoder.bytes_feed(bytes_of("y")).length, 1);
      this.assertTrue(decoder.idle());
      this.raised_assert(jslb.WireError, parse_refusal(""), () =>
        decoder.bytes_feed(bytes_of("\r")),
      );
      this.assertFalse(decoder.idle());
    }

    // A line of `line_max` bytes with its CR is read, one byte more is not.
    test_line_max(): void {
      const prefix = '{"0":{"t":"echo"},"pad":"';
      const suffix = '"}\r';
      const length = constants.line_max - prefix.length - suffix.length;
      const pad = "a".repeat(length);
      const text = prefix + pad + suffix;
      const decoder = decoder_make(new MemorySink());
      this.assertEqual(pieces_decode(decoder, [bytes_of(text)]).length, 1);
      const message = i18n("jslb.line_over_max", constants.line_max);
      this.refused_assert(bytes_of(prefix + pad + "a" + suffix), message);
    }

    // A line is refused once it passes `line_max`, before its CR arrives.
    test_line_early(): void {
      const decoder = decoder_make(new MemorySink());
      const open = "{".repeat(constants.line_max - 1);
      this.assertEqual(decoder.bytes_feed(bytes_of(open)), []);
      const message = i18n("jslb.line_over_max", constants.line_max);
      this.raised_assert(jslb.WireError, message, () =>
        decoder.bytes_feed(bytes_of("{")),
      );
    }

    // A blob of `blob_max` bytes is read, one more refused before buffering.
    test_blob_max(): void {
      const largest = constants.blob_max;
      const head = `{"0":{"t":"echo","b":1},"1":{"s":${largest + 1}}}\r`;
      const over = bytes_join([bytes_of(head), new Uint8Array(largest + 1)]);
      const message = i18n("jslb.blobs_over", largest + 1, largest);
      const sink = this.refused_assert(over, message);
      this.assertEqual(sink.headers.length, 0);
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${largest}}}\r`;
      const found = pieces_decode(decoder_make(new MemorySink()), [
        bytes_of(text),
        new Uint8Array(largest),
      ]);
      this.assertEqual(found.length, 1);
    }

    // Blobs of `blob_max` in all pass with a longest line, one byte more not.
    test_blobs_summed(): void {
      const { line_max, blob_max } = constants;
      const first = new Uint8Array(blob_max / 2);
      const rest = blob_max - first.length;
      const over = message_padded(line_max, [first, new Uint8Array(rest + 1)]);
      const message = i18n("jslb.blobs_over", blob_max + 1, blob_max);
      const sink = this.refused_assert(over, message);
      this.assertEqual(sink.headers.length, 0);
      const data = message_padded(line_max, [first, new Uint8Array(rest)]);
      this.assertEqual(data.length, line_max + blob_max);
      const found = pieces_decode(decoder_make(new MemorySink()), [data]);
      this.assertEqual(found.length, 1);
    }

    // A line without header 0 is refused.
    test_header_missing(): void {
      const message = i18n("jslb.no_header_zero");
      this.refused_assert(bytes_of('{"t":"echo"}\r'), message);
      this.refused_assert(bytes_of('{"1":{"s":0}}\r'), message);
    }

    // A header that is not a JSON object is refused.
    test_header_object(): void {
      this.refused_assert(
        bytes_of('{"0":"echo"}\r'),
        i18n("jslb.header_not_object", 0),
      );
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":[]}\r'),
        i18n("jslb.header_not_object", 1),
      );
    }

    // A line header without a type string is refused.
    test_type_missing(): void {
      const message = i18n("jslb.no_type");
      this.refused_assert(bytes_of('{"0":{"i":1}}\r'), message);
      this.refused_assert(bytes_of('{"0":{"t":null}}\r'), message);
      this.refused_assert(bytes_of('{"0":{"t":1}}\r'), message);
      this.refused_assert(bytes_of('{"0":{}}\r'), message);
    }

    // A blob count that differs from the blob headers is refused.
    test_count_mismatch(): void {
      const cases: [string, unknown, number][] = [
        ['{"0":{"t":"echo","b":2},"1":{"s":0}}\r', 2, 1],
        ['{"0":{"t":"echo"},"1":{"s":0}}\r', 0, 1],
        ['{"0":{"t":"echo","b":true},"1":{"s":0}}\r', true, 1],
        ['{"0":{"t":"echo","b":-1}}\r', -1, 0],
        ['{"0":{"t":"echo","b":0.5}}\r', 0.5, 0],
      ];
      for (const [text, count, probed] of cases) {
        const message = i18n("jslb.blobs_mismatch", count, probed);
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A gap in the blob headers is refused, a huge integer key too.
    test_header_gap(): void {
      const cases: [string, number, number][] = [
        ['{"0":{"t":"echo","b":2},"1":{"s":0},"3":{"s":0}}\r', 2, 3],
        ['{"0":{"t":"echo","b":1},"2":{"s":0}}\r', 1, 2],
        ['{"0":{"t":"echo"},"4294967296":{}}\r', 1, 4294967296],
      ];
      for (const [text, missing, present] of cases) {
        const message = i18n("jslb.blob_gap", missing, present);
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A size that is not a non negative integer is refused.
    test_size_invalid(): void {
      const message = i18n("jslb.bad_size", 1);
      for (const size of ["-1", "1.5", '"1"', "true", "null"]) {
        const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\r`;
        this.refused_assert(bytes_of(text), message);
      }
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"k":"a"}}\r'),
        message,
      );
    }

    // A payload key of decimal digits is refused.
    test_payload_digits(): void {
      for (const key of ["01", "00"]) {
        const message = i18n("jslb.payload_digit_key", key);
        const text = `{"0":{"t":"echo"},"${key}":1}\r`;
        this.refused_assert(bytes_of(text), message);
      }
    }

    // Short and full names in one line are refused, across headers too.
    test_forms_mixed(): void {
      const message = i18n("jslb.both_name_forms");
      for (const field of ['"version":1', '"type":"echo"']) {
        const text = `{"0":{"t":"echo",${field}}}\r`;
        this.refused_assert(bytes_of(text), message);
      }
      this.refused_assert(
        bytes_of('{"0":{"type":"echo","blobs":1},"1":{"s":0}}\r'),
        message,
      );
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"s":0,"key":"a"}}\r'),
        message,
      );
    }

    // An unknown field in the line header is refused.
    test_line_field(): void {
      for (const name of ["x", "s"]) {
        const message = i18n("jslb.unknown_line_field", name);
        const text = `{"0":{"t":"echo","${name}":1}}\r`;
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A blob header that carries `d` or `data` on the wire is refused.
    test_data_sent(): void {
      const message = i18n("jslb.blob_data_field", 1);
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":{"s":0,"d":""}}\r'),
        message,
      );
      this.refused_assert(
        bytes_of('{"0":{"type":"echo","blobs":1},"1":{"size":0,"data":""}}\r'),
        message,
      );
    }

    // A line that is not strict `UTF-8` or not a JSON object is refused.
    test_text_invalid(): void {
      const start = bytes_of('{"0":{"t":"');
      const end = bytes_of('"}}');
      const line_end = bytes_of("\r");
      const middles = [[0xff], [0xed, 0xa0, 0x80], [0xc0, 0x80]];
      for (const middle of middles) {
        const line = bytes_join([start, Uint8Array.from(middle), end]);
        const data = bytes_join([line, line_end]);
        this.refused_assert(data, decode_refusal(line));
      }
      const mark = Uint8Array.of(0xef, 0xbb, 0xbf);
      const marked = bytes_join([mark, bytes_of(constants.echo_text)]);
      this.refused_assert(
        bytes_join([marked, line_end]),
        parse_refusal(utility.utf8_decode(marked)),
      );
      this.refused_assert(bytes_of("{\r"), parse_refusal("{"));
      this.refused_assert(
        bytes_of('[{"0":{"t":"echo"}}]\r'),
        i18n("jslb.line_not_object"),
      );
      this.refused_assert(bytes_of("\r"), parse_refusal(""));
    }

    // The `NaN` and `Infinity` constants are refused as not JSON.
    test_constant_refused(): void {
      for (const constant of ["NaN", "Infinity", "-Infinity"]) {
        const text = `{"0":{"t":"echo"},"n":${constant}}`;
        this.refused_assert(bytes_of(text + "\r"), parse_refusal(text));
      }
    }

    // A number too long for a double reads as `Infinity`, Python refusing it.
    test_number_long(): void {
      const digits = "1".repeat(constants.long_digits);
      const data = bytes_of(`{"0":{"t":"echo"},"n":${digits}}\r`);
      const decoder = new jslb.LineDecoder(
        2 * data.length,
        constants.blob_max,
        constants.overflow_bytes,
        new MemorySink(),
      );
      const found = pieces_decode(decoder, [data]);
      this.assertEqual(found.length, 1);
      this.assertEqual(found[0]["n"], Infinity);
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
      const found = pieces_decode(decoder_make(sink), pieces);
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
      const stream = bytes_join([bytes_of(text), data]);
      const found = pieces_decode(decoder_make(sink), [stream]);
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
        decoder_make(sink),
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
      this.raised_assert(RangeError, "the sink is full", () =>
        decoder.bytes_feed(bytes_of(text)),
      );
      this.raised_assert(jslb.WireError, i18n("jslb.decoder_failed"), () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
    }

    // A streamed blob's handle is closed when an append fails, then or later.
    test_stream_closed(): void {
      const size = constants.overflow_bytes + 1;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\rx`;
      const failing = new FailingSink();
      const decoder = decoder_make(failing);
      this.raised_assert(RangeError, failing.message, () =>
        decoder.bytes_feed(bytes_of(text)),
      );
      this.assertEqual(failing.closed, ["blob_1"]);
      const later = new FailingSink();
      const deferred = decoder_make(later);
      const found = deferred.bytes_feed(bytes_of(constants.echo_line + text));
      this.assertEqual(found, [{ 0: { t: "echo" } }]);
      this.assertEqual(later.closed, ["blob_1"]);
      this.raised_assert(RangeError, later.message, () =>
        deferred.bytes_feed(new Uint8Array(0)),
      );
    }

    // A sent `sha256` is replaced on a streamed blob, kept on one in memory.
    test_hash_sent(): void {
      const sink = new MemorySink();
      const sent = "0".repeat(64);
      const data = new Uint8Array(constants.overflow_bytes + 1);
      const text =
        `{"0":{"t":"echo","b":2},"1":{"s":${data.length},` +
        `"sha256":"${sent}"},"2":{"s":1,"sha256":"${sent}"}}\r`;
      const stream = bytes_join([bytes_of(text), data, bytes_of("x")]);
      const found = pieces_decode(decoder_make(sink), [stream]);
      this.assertEqual(found.length, 1);
      this.assertEqual(Object.entries(blob_at(found[0], 1)), [
        ["s", data.length],
        ["sha256", utility.sha256_hex(data)],
        ["d", "blob_1"],
      ]);
      this.assertEqual(Object.entries(blob_at(found[0], 2)), [
        ["s", 1],
        ["sha256", sent],
        ["d", bytes_of("x")],
      ]);
    }
  }

  // Reads each vector of `test_vectors`, whole, by bytes and split.
  export class TestVectors extends RefusalCase {
    // Each success vector, and the bytes it encodes to, decode to its sidecar.
    test_vectors_success(): void {
      const names = vector_names(false);
      this.assertTrue(names.length > 0, "no success vectors in test_vectors");
      for (const name of names) {
        const data = file_bytes(name + constants.vector_suffix);
        const sidecar = sidecar_read(name);
        const messages = JSON.stringify(sidecar.messages);
        const sink = new MemorySink();
        const decoded = pieces_decode(sidecar_decoder(sidecar, sink), [data]);
        const encoded = bytes_join(
          decoded.map((line) =>
            pieces_join(jslb.line_encode(line_sent(line)), sink),
          ),
        );
        const same = bytes_equal(encoded, data);
        this.assertEqual(same, sidecar.canonical, name);
        for (const source of same ? [data] : [data, encoded]) {
          for (const pieces of feeds_make(source)) {
            const feed_sink = new MemorySink();
            const decoder = sidecar_decoder(sidecar, feed_sink);
            const found = pieces_decode(decoder, pieces);
            const plain = found.map((line) => line_plain(line, feed_sink));
            this.assertEqual(JSON.stringify(plain), messages, name);
            const renders = found.map((line) => jslb.line_render(line));
            this.assertEqual(renders, sidecar.render, name);
          }
        }
      }
    }

    // Each error vector gives its lines, then its fault, however it is fed.
    test_vectors_error(): void {
      const names = vector_names(true);
      this.assertTrue(names.length > 0, "no error vectors in test_vectors");
      for (const name of names) {
        const data = file_bytes(name + constants.vector_suffix);
        const sidecar = sidecar_read(name);
        const expected = errors_expected(sidecar.limits);
        this.assertEqual(Object.keys(expected).sort(), names);
        const [slug, message] = expected[name];
        this.assertEqual(sidecar.error, slug, name);
        const messages = JSON.stringify(sidecar.messages);
        for (const pieces of feeds_make(data)) {
          const sink = new MemorySink();
          const decoder = sidecar_decoder(sidecar, sink);
          const found: jslb.Line[] = [];
          this.raised_assert(
            jslb.WireError,
            message,
            () => {
              for (const piece of pieces) {
                found.push(...decoder.bytes_feed(piece));
              }
              decoder.bytes_feed(new Uint8Array(0));
            },
            name,
          );
          const plain = found.map((line) => line_plain(line, sink));
          this.assertEqual(JSON.stringify(plain), messages, name);
          const renders = found.map((line) => jslb.line_render(line));
          this.assertEqual(renders, sidecar.render, name);
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

    // The error is named on its prototype, so its stack header shows it.
    test_error_name(): void {
      const error = new jslb.WireError("x");
      this.assertEqual(error.name, "WireError");
      this.assertFalse(Object.hasOwn(error, "name"));
      this.assertTrue(String(error.stack).startsWith("WireError: x"));
    }
  }
}
Object.freeze(test_jslb);
