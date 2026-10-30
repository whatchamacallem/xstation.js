// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the decoder of jslb.ts, a block of group B on a real
// `substrate.CacheFiles` over the open OPFS files the bring up gives the
// block as test_slots, cleared, which no other block uses: lines and blobs
// in memory, its limits, its number rules, its deferred fault and every hard
// error, each refusal compared with its message, blobs over overflow_bytes
// streamed into the cache and hashed by it, a cache with no free file, a
// file closed under a streamed blob, the encode tests that decode first, and
// the vectors of build/vectors, which the test page carries as test_vectors,
// each read with the limits its sidecar names, whole, by single bytes and
// split at every offset, a streamed blob's digest the one its sidecar holds.
// A cache is made for each decoder over the same two files, as a finished
// blob keeps its file for the life of its cache, and the close test closes
// a third, so the bring up gives at least three. The decoders built here take
// their limits from the gold, and the input of a streamed blob and its
// digest are one entry of test_digests.json, under test_jslb_decode.
namespace test_jslb_decode {
  // The vector files by name, as base64 text, a global the test page sets.
  declare const test_vectors: { readonly [name: string]: string };

  // An open OPFS file, the members of the platform's handle used here.
  interface SlotFile extends substrate.SlotHandle {
    // Closes the handle, after which every call on it throws.
    close(): void;
  }

  // The open OPFS files of this block, cleared, a global the bring up sets.
  declare const test_slots: readonly SlotFile[];

  // The texts and the names the tests use.
  const constants = Object.freeze({
    // The integers just past `2^53` either way.
    integer_above: "9007199254740993",
    integer_below: "-9007199254740993",
    echo_text: '{"0":{"t":"echo"}}',
    echo_line: '{"0":{"t":"echo"}}\r',
    vector_suffix: ".jslb",
    sidecar_suffix: ".json",
    backslash: String.fromCharCode(0x5c),
    byte_mark: String.fromCharCode(0xfeff),
    gold_id: "typescript.test_jslb_decode",
    digests_name: "test_digests.json",
    digests_module: "test_jslb_decode",
    // The files of each cache: a line here streams two blobs at most.
    cache_slots: 2,
    // The name of the fault of a call on a closed handle.
    closed_fault: "InvalidStateError",
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

  // An entry of the digest vector: an input and the `SHA-256` of it.
  interface DigestEntry {
    data: Uint8Array;
    sha256: string;
  }

  // The digest vector: each test module's entries by name, data in hex.
  type DigestFile = {
    [module: string]: { [name: string]: { data: string; sha256: string } };
  };

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`${constants.gold_id}.texts.${name}`) as string;
  }

  // A text of this module's gold with each `{n}` replaced by value n.
  function text_fill(name: string, ...values: unknown[]): string {
    let text = gold_text(name);
    values.forEach((value, index) => {
      text = text.replaceAll(`{${index}}`, () => String(value));
    });
    return text;
  }

  // The limits of the decoders built here, from this module's gold.
  function limits_get(): VectorLimits {
    return {
      line_max: gold_value("line_max") as number,
      blob_max: gold_value("blob_max") as number,
      overflow_bytes: gold_value("overflow_bytes") as number,
    };
  }

  // The text of strict `UTF-8` bytes.
  function text_decode(data: Uint8Array): string {
    return new TextDecoder("utf-8", { fatal: true }).decode(data);
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

  // The bytes that lowercase hex text spells, two characters each.
  function hex_bytes(text: string): Uint8Array {
    if (!/^(?:[0-9a-f]{2})*$/.test(text)) {
      throw new Error("the digest vector's data is not lowercase hex");
    }
    const data = new Uint8Array(text.length / 2);
    for (let index = 0; index < data.length; index += 1) {
      data[index] = Number.parseInt(text.slice(2 * index, 2 * index + 2), 16);
    }
    return data;
  }

  // Bytes that count up from 0 and start again at the period.
  function pattern_make(count: number, period: number): Uint8Array {
    const data = new Uint8Array(count);
    for (let index = 0; index < count; index += 1) {
      data[index] = index % period;
    }
    return data;
  }

  // What a call throws, which it must throw.
  function thrown_value(call: () => unknown): unknown {
    try {
      call();
    } catch (error) {
      return error;
    }
    throw new Error("the call threw nothing");
  }

  // The text of what a call throws, which it must throw.
  function thrown_text(call: () => unknown): string {
    return String(thrown_value(call));
  }

  // An `echo` line whose payload `n` is the number token as it is written.
  function number_line(token: string): Uint8Array {
    return bytes_of(`{"0":{"t":"echo"},"n":${token}}\r`);
  }

  // The message the decoder gives for line text that JSON cannot parse.
  function parse_refusal(text: string): string {
    const reason = thrown_text(() => JSON.parse(text));
    return text_fill("jslb_line_not_json", reason);
  }

  // The bring up's files from `first` to before `end`, which it must hold.
  function files_get(first: number, end: number): SlotFile[] {
    if (test_slots.length < end) {
      throw new Error(
        `test_slots holds ${test_slots.length} files, fewer than ${end}`,
      );
    }
    return test_slots.slice(first, end);
  }

  // A new cache over the files of the caches, whose blobs a later one reuses.
  function cache_make(): substrate.CacheFiles {
    return new substrate.CacheFiles(files_get(0, constants.cache_slots));
  }

  // A new decoder with the limits of the gold, streaming into the cache.
  function decoder_make(cache: substrate.CacheFiles): jslb.LineDecoder {
    const limits = limits_get();
    return new jslb.LineDecoder(
      limits.line_max,
      limits.blob_max,
      limits.overflow_bytes,
      cache,
    );
  }

  // A new decoder with a sidecar's limits, streaming into the cache.
  function sidecar_decoder(
    sidecar: VectorSidecar,
    cache: substrate.CacheFiles,
  ): jslb.LineDecoder {
    const limits = sidecar.limits;
    return new jslb.LineDecoder(
      limits.line_max,
      limits.blob_max,
      limits.overflow_bytes,
      cache,
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

  // The bytes of a streamed blob, read back from the cache that holds them.
  function blob_bytes(
    cache: substrate.CacheFiles,
    blob: jslb.BlobHeader,
  ): Uint8Array {
    const handle = blob.d;
    if (typeof handle !== "string") {
      throw new Error("the blob was not streamed");
    }
    const size = jslb.field_get(blob, "size") as number;
    return cache.cache_read(handle, 0, size);
  }

  // The JSON text the encoder writes for a line, its CR included.
  function encoded_text(line: jslb.Line): string {
    const first = jslb.line_encode(line)[0];
    if (typeof first === "string") {
      throw new Error("the encoder gave a handle before the JSON bytes");
    }
    return text_decode(first);
  }

  // The bytes a line encodes to whose blobs are all bytes, none a handle.
  function bytes_encoded(line: jslb.Line): Uint8Array {
    return bytes_join(
      jslb.line_encode(line).map((piece) => {
        if (typeof piece === "string") {
          throw new Error("internal error");
        }
        return piece;
      }),
    );
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

  // The bytes a decoded line encodes to, each streamed blob read back.
  function line_bytes(
    line: jslb.Line,
    cache: substrate.CacheFiles,
  ): Uint8Array {
    const pieces = jslb.line_encode(line_sent(line));
    return bytes_join(
      pieces.map((piece, number) =>
        typeof piece === "string"
          ? blob_bytes(cache, blob_at(line, number))
          : piece,
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
    return bytes_encoded(jslb.line_make(header, made, { pad }));
  }

  // A decoded line as a sidecar holds it, each blob's `d` in hex.
  function line_plain(
    line: jslb.Line,
    cache: substrate.CacheFiles,
  ): { [key: string]: unknown } {
    const plain: { [key: string]: unknown } = { ...line };
    const count = jslb.headers_of(line).length - 1;
    for (let number = 1; number <= count; number += 1) {
      const header = blob_at(line, number);
      const data = header.d;
      const bytes =
        typeof data === "string" ? blob_bytes(cache, header) : data;
      if (bytes === undefined) {
        throw new Error(`blob header ${number} has no d`);
      }
      plain[number] = { ...header, d: hex_of(bytes) };
    }
    return plain;
  }

  // The bytes of a file the test page carries in `test_vectors`.
  function file_bytes(name: string): Uint8Array {
    if (!Object.hasOwn(test_vectors, name)) {
      throw new Error(`test_vectors has no file ${name}`);
    }
    return Uint8Array.from(atob(test_vectors[name]), (character) =>
      character.charCodeAt(0),
    );
  }

  // The sidecar of a vector.
  function sidecar_read(name: string): VectorSidecar {
    const file = file_bytes(name + constants.sidecar_suffix);
    return JSON.parse(text_decode(file)) as VectorSidecar;
  }

  // The input and digest of this module's entry of the digest vector.
  function digest_entry(name: string): DigestEntry {
    const file = file_bytes(constants.digests_name);
    const digests = JSON.parse(text_decode(file)) as DigestFile;
    const owner = constants.digests_module;
    if (!Object.hasOwn(digests, owner)) {
      throw new Error(`${constants.digests_name} has no module ${owner}`);
    }
    if (!Object.hasOwn(digests[owner], name)) {
      throw new Error(`${constants.digests_name} has no entry ${name}`);
    }
    const entry = digests[owner][name];
    return { data: hex_bytes(entry.data), sha256: entry.sha256 };
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
      text_fill("jslb_blobs_over", blob_max + 1, blob_max),
    ];
    const header: FaultExpected = [
      "no_header_zero",
      gold_text("jslb_no_header_zero"),
    ];
    const size: FaultExpected = ["bad_size", gold_text("jslb_bad_size")];
    const forms: FaultExpected = [
      "both_name_forms",
      gold_text("jslb_both_name_forms"),
    ];
    const typed: FaultExpected = ["no_type", gold_text("jslb_no_type")];
    const utf8: FaultExpected = [
      "line_not_utf8",
      gold_text("jslb_line_not_utf8"),
    ];
    return {
      error_after_line: header,
      error_bad_size_boolean: size,
      error_bad_size_fraction: size,
      error_bad_size_missing: size,
      error_bad_size_negative: size,
      error_bad_size_string: size,
      error_blob_data: ["blob_data_field", gold_text("jslb_blob_data_field")],
      error_blob_gap: ["blob_gap", gold_text("jslb_blob_gap_middle")],
      error_blob_gap_first: ["blob_gap", gold_text("jslb_blob_gap_first")],
      error_blob_over_max: over,
      error_blobs_mismatch: [
        "blobs_mismatch",
        gold_text("jslb_blobs_mismatch_over"),
      ],
      error_blobs_mismatch_boolean: [
        "blobs_mismatch",
        gold_text("jslb_blobs_mismatch_boolean"),
      ],
      error_blobs_mismatch_extra: [
        "blobs_mismatch",
        gold_text("jslb_blobs_mismatch_extra"),
      ],
      error_blobs_over: over,
      error_both_name_forms: forms,
      error_both_name_forms_blob: forms,
      error_header_not_object: [
        "header_not_object",
        gold_text("jslb_header_not_object_line"),
      ],
      error_header_not_object_blob: [
        "header_not_object",
        gold_text("jslb_header_not_object_blob"),
      ],
      error_infinity: [
        "line_not_json",
        parse_refusal('{"0":{"t":"echo"},"n":Infinity}'),
      ],
      error_integer_above: [
        "integer_refused",
        gold_text("jslb_integer_refused_above"),
      ],
      error_integer_below: [
        "integer_refused",
        gold_text("jslb_integer_refused_below"),
      ],
      error_integer_digits_310: [
        "integer_refused",
        text_fill("jslb_integer_refused", "1" + "0".repeat(309)),
      ],
      error_integer_digits_4301: [
        "integer_refused",
        text_fill("jslb_integer_refused", "1" + "0".repeat(4300)),
      ],
      error_line_over_max: [
        "line_over_max",
        text_fill("jslb_line_over_max", line_max),
      ],
      error_nan: [
        "line_not_json",
        parse_refusal('{"0":{"t":"echo"},"n":NaN}'),
      ],
      error_no_header_zero: header,
      error_no_type: typed,
      error_no_type_string: typed,
      error_not_object: ["line_not_object", gold_text("jslb_line_not_object")],
      error_number_overflow: [
        "number_overflow",
        gold_text("jslb_number_overflow_positive"),
      ],
      error_number_overflow_negative: [
        "number_overflow",
        gold_text("jslb_number_overflow_negative"),
      ],
      error_payload_digit_key: [
        "payload_digit_key",
        gold_text("jslb_payload_digit_key_01"),
      ],
      error_unknown_line_field: [
        "unknown_line_field",
        gold_text("jslb_unknown_line_field_x"),
      ],
      error_utf8_overlong: utf8,
      error_utf8_surrogate: utf8,
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
    refused_assert(data: Uint8Array, message: string): substrate.CacheFiles {
      const cache = cache_make();
      const decoder = decoder_make(cache);
      this.raised_assert(jslb.WireError, message, () =>
        decoder.bytes_feed(data),
      );
      const failed = gold_text("jslb_decoder_failed");
      this.raised_assert(jslb.WireError, failed, () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
      return cache;
    }
  }

  // Tests `line_encode` on lines the decoder read.
  export class TestEncode extends RefusalCase {
    // Each blob's `d` follows the JSON as the same bytes object or handle.
    test_encode_blobs(): void {
      const data = Uint8Array.of(0x0d, 0x03, 0x04);
      const over = digest_entry("stream_over");
      const size = over.data.length;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${size},"k":"k"}}\r`;
      const streamed = pieces_decode(decoder_make(cache_make()), [
        bytes_of(text),
        over.data,
      ]);
      const handle = blob_at(line_sent(streamed[0]), 1);
      const blobs = [jslb.blob_make(data), handle];
      const line = jslb.line_make(jslb.header_make("echo"), blobs, {});
      const pieces = jslb.line_encode(line);
      this.assertEqual(pieces.length, 3);
      this.assertEqual(
        pieces[0],
        bytes_of(
          `{"0":{"t":"echo","b":2},"1":{"s":3},"2":{"s":${size},"k":"k"}}\r`,
        ),
      );
      this.assertTrue(pieces[1] === data);
      this.assertEqual(typeof handle.d, "string");
      this.assertEqual(pieces[2], handle.d);
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
      const found = pieces_decode(decoder_make(cache_make()), [sent]);
      this.assertEqual(found.length, 1);
      this.assertEqual(jslb.payload_of(found[0]), { n: 1e16, m: -1e300 });
      this.assertEqual(
        encoded_text(found[0]),
        '{"0":{"t":"echo"},"n":10000000000000000,"m":-1e+300}\r',
      );
    }
  }

  // Tests `LineDecoder` on lines, blobs in memory, its limits and every fault.
  export class TestDecode extends RefusalCase {
    // A line decodes to plain objects, and integer keys encode first again.
    test_decode_line(): void {
      const text = '{"0":{"t":"echo","i":1},"x":[{"02":4,"2":3}]}\r';
      const decoder = decoder_make(cache_make());
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
      const decoder = decoder_make(cache_make());
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
      const decoder = decoder_make(cache_make());
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
      const decoder = decoder_make(cache_make());
      const text = '{"0":{"t":"echo","b":1},"1":{"s":0}}\r';
      const found = decoder.bytes_feed(bytes_of(text));
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_at(found[0], 1).d, new Uint8Array(0));
    }

    // Lines come back when their last byte arrives, several in one call.
    test_decode_pieces(): void {
      const decoder = decoder_make(cache_make());
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
      const found = pieces_decode(decoder_make(cache_make()), [
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
      const decoder = decoder_make(cache_make());
      const echo = constants.echo_line;
      const data = bytes_of(echo + '{"t":"echo"}\r' + echo);
      this.assertEqual(decoder.bytes_feed(data), [{ 0: { t: "echo" } }]);
      this.assertFalse(decoder.idle());
      const empty = new Uint8Array(0);
      const no_header = gold_text("jslb_no_header_zero");
      this.raised_assert(jslb.WireError, no_header, () =>
        decoder.bytes_feed(empty),
      );
      const failed = gold_text("jslb_decoder_failed");
      this.raised_assert(jslb.WireError, failed, () =>
        decoder.bytes_feed(empty),
      );
    }

    // The decoder is idle between messages only, and never after a fault.
    test_idle_states(): void {
      const decoder = decoder_make(cache_make());
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
      const { line_max } = limits_get();
      const prefix = '{"0":{"t":"echo"},"pad":"';
      const suffix = '"}\r';
      const length = line_max - prefix.length - suffix.length;
      const pad = "a".repeat(length);
      const text = prefix + pad + suffix;
      const decoder = decoder_make(cache_make());
      this.assertEqual(pieces_decode(decoder, [bytes_of(text)]).length, 1);
      const message = text_fill("jslb_line_over_max", line_max);
      this.refused_assert(bytes_of(prefix + pad + "a" + suffix), message);
    }

    // A line is refused once it passes `line_max`, before its CR arrives.
    test_line_early(): void {
      const { line_max } = limits_get();
      const decoder = decoder_make(cache_make());
      const open = "{".repeat(line_max - 1);
      this.assertEqual(decoder.bytes_feed(bytes_of(open)), []);
      const message = text_fill("jslb_line_over_max", line_max);
      this.raised_assert(jslb.WireError, message, () =>
        decoder.bytes_feed(bytes_of("{")),
      );
    }

    // A blob of `blob_max` bytes is read, one more refused before buffering.
    test_blob_max(): void {
      const largest = limits_get().blob_max;
      const head = `{"0":{"t":"echo","b":1},"1":{"s":${largest + 1}}}\r`;
      const over = bytes_join([bytes_of(head), new Uint8Array(largest + 1)]);
      const message = text_fill("jslb_blobs_over", largest + 1, largest);
      const cache = this.refused_assert(over, message);
      this.assertEqual(cache.slots_free(), constants.cache_slots);
      const entry = digest_entry("blob_largest");
      this.assertEqual(entry.data.length, largest);
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${largest}}}\r`;
      const found = pieces_decode(decoder_make(cache_make()), [
        bytes_of(text),
        entry.data,
      ]);
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_at(found[0], 1)["sha256"], entry.sha256);
    }

    // Blobs of `blob_max` in all pass with a longest line, one byte more not.
    test_blobs_summed(): void {
      const { line_max, blob_max } = limits_get();
      const half = digest_entry("blob_half");
      const first = half.data;
      const rest = blob_max - first.length;
      const over = message_padded(line_max, [first, new Uint8Array(rest + 1)]);
      const message = text_fill("jslb_blobs_over", blob_max + 1, blob_max);
      const cache = this.refused_assert(over, message);
      this.assertEqual(cache.slots_free(), constants.cache_slots);
      const data = message_padded(line_max, [first, half.data]);
      this.assertEqual(data.length, line_max + blob_max);
      const found = pieces_decode(decoder_make(cache_make()), [data]);
      this.assertEqual(found.length, 1);
      for (const number of [1, 2]) {
        this.assertEqual(blob_at(found[0], number)["sha256"], half.sha256);
      }
    }

    // A line without header 0 is refused.
    test_header_missing(): void {
      const message = gold_text("jslb_no_header_zero");
      this.refused_assert(bytes_of('{"t":"echo"}\r'), message);
      this.refused_assert(bytes_of('{"1":{"s":0}}\r'), message);
    }

    // A header that is not a JSON object is refused.
    test_header_object(): void {
      this.refused_assert(
        bytes_of('{"0":"echo"}\r'),
        gold_text("jslb_header_not_object_line"),
      );
      this.refused_assert(
        bytes_of('{"0":{"t":"echo","b":1},"1":[]}\r'),
        gold_text("jslb_header_not_object_blob"),
      );
    }

    // A line header without a type string is refused.
    test_type_missing(): void {
      const message = gold_text("jslb_no_type");
      this.refused_assert(bytes_of('{"0":{"i":1}}\r'), message);
      this.refused_assert(bytes_of('{"0":{"t":null}}\r'), message);
      this.refused_assert(bytes_of('{"0":{"t":1}}\r'), message);
      this.refused_assert(bytes_of('{"0":{}}\r'), message);
    }

    // A blob count that differs from the blob headers is refused.
    test_count_mismatch(): void {
      const cases: [string, string][] = [
        ['{"0":{"t":"echo","b":2},"1":{"s":0}}\r', "over"],
        ['{"0":{"t":"echo"},"1":{"s":0}}\r', "extra"],
        ['{"0":{"t":"echo","b":true},"1":{"s":0}}\r', "boolean"],
        ['{"0":{"t":"echo","b":-1}}\r', "negative"],
        ['{"0":{"t":"echo","b":0.5}}\r', "fraction"],
      ];
      for (const [text, kind] of cases) {
        const message = gold_text(`jslb_blobs_mismatch_${kind}`);
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A gap in the blob headers is refused, a huge integer key too.
    test_header_gap(): void {
      const cases: [string, string][] = [
        ['{"0":{"t":"echo","b":2},"1":{"s":0},"3":{"s":0}}\r', "middle"],
        ['{"0":{"t":"echo","b":1},"2":{"s":0}}\r', "first"],
        ['{"0":{"t":"echo"},"4294967296":{}}\r', "huge"],
      ];
      for (const [text, kind] of cases) {
        const message = gold_text(`jslb_blob_gap_${kind}`);
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A size that is not a non negative integer is refused.
    test_size_invalid(): void {
      const message = gold_text("jslb_bad_size");
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
        const message = gold_text(`jslb_payload_digit_key_${key}`);
        const text = `{"0":{"t":"echo"},"${key}":1}\r`;
        this.refused_assert(bytes_of(text), message);
      }
    }

    // Short and full names in one line are refused, across headers too.
    test_forms_mixed(): void {
      const message = gold_text("jslb_both_name_forms");
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
        const message = gold_text(`jslb_unknown_line_field_${name}`);
        const text = `{"0":{"t":"echo","${name}":1}}\r`;
        this.refused_assert(bytes_of(text), message);
      }
    }

    // A blob header that carries `d` or `data` on the wire is refused.
    test_data_sent(): void {
      const message = gold_text("jslb_blob_data_field");
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
        this.refused_assert(data, gold_text("jslb_line_not_utf8"));
      }
      const mark = Uint8Array.of(0xef, 0xbb, 0xbf);
      const marked = bytes_join([mark, bytes_of(constants.echo_text)]);
      this.refused_assert(
        bytes_join([marked, line_end]),
        parse_refusal(constants.byte_mark + constants.echo_text),
      );
      this.refused_assert(bytes_of("{\r"), parse_refusal("{"));
      this.refused_assert(
        bytes_of('[{"0":{"t":"echo"}}]\r'),
        gold_text("jslb_line_not_object"),
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
  }

  // Tests the decoder's number rules, the one door for bad numbers.
  export class TestNumbers extends RefusalCase {
    // The `n` of the one line the decoder reads from the bytes.
    number_read(data: Uint8Array): unknown {
      const found = pieces_decode(decoder_make(cache_make()), [data]);
      this.assertEqual(found.length, 1);
      return found[0]["n"];
    }

    // `2^53` either way reads as the integer, one past either is refused.
    test_integer_edges(): void {
      for (const token of ["9007199254740992", "-9007199254740992"]) {
        this.assertEqual(this.number_read(number_line(token)), Number(token));
      }
      const cases: [string, string][] = [
        [constants.integer_above, "jslb_integer_refused_above"],
        [constants.integer_below, "jslb_integer_refused_below"],
      ];
      for (const [token, refused] of cases) {
        this.refused_assert(number_line(token), gold_text(refused));
      }
    }

    // A size past `2^53` is a refused integer before it is a bad size.
    test_size_integer(): void {
      const token = constants.integer_above;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${token}}}\r`;
      const message = gold_text("jslb_integer_refused_above");
      this.refused_assert(bytes_of(text), message);
    }

    // An integer of 17 digits or of 310 digits is refused.
    test_integer_digits(): void {
      for (const token of ["1".repeat(17), "1" + "0".repeat(309)]) {
        const message = text_fill("jslb_integer_refused", token);
        this.refused_assert(number_line(token), message);
      }
    }

    // A token whose double overflows to an infinity is refused.
    test_number_overflow(): void {
      const cases: [string, string][] = [
        ["1e400", "jslb_number_overflow_positive"],
        ["-1e400", "jslb_number_overflow_negative"],
        ["1.5e400", "jslb_number_overflow_fraction"],
      ];
      for (const [token, refused] of cases) {
        this.refused_assert(number_line(token), gold_text(refused));
      }
    }

    // A token with an exponent within the doubles reads as its double.
    test_double_read(): void {
      for (const token of ["1e+300", "9.007199254740994e+15"]) {
        this.assertEqual(this.number_read(number_line(token)), Number(token));
      }
    }

    // Digits in a key or a string are no number, however many they are.
    test_digits_text(): void {
      const digits = "1".repeat(20);
      const quote = `${constants.backslash}"`;
      const member = `"${digits}":"${quote}${digits}"`;
      const text = `{"0":{"t":"echo"},"n":{${member}}}\r`;
      this.assertEqual(this.number_read(bytes_of(text)), {
        [digits]: `"${digits}`,
      });
    }

    // The first refused token in the text is the one reported.
    test_number_first(): void {
      const above = constants.integer_above;
      const overflow = `[1e400,${above}]`;
      const message = gold_text("jslb_number_overflow_positive");
      this.refused_assert(number_line(overflow), message);
      const integer = `[${above},1e400]`;
      const refused = gold_text("jslb_integer_refused_above");
      this.refused_assert(number_line(integer), refused);
    }

    // The encoder's digits for a double past `2^53` are refused at read.
    test_encoded_refused(): void {
      const header = jslb.header_make("echo");
      const line = jslb.line_make(header, [], { n: 2 ** 53 + 2 });
      const text = encoded_text(line);
      this.assertEqual(text, '{"0":{"t":"echo"},"n":9007199254740994}\r');
      const message = gold_text("jslb_integer_refused_encoded");
      this.refused_assert(bytes_of(text), message);
    }
  }

  // Tests blobs over `overflow_bytes`, streamed into the cache.
  export class TestStream extends RefusalCase {
    // A blob one byte over goes to the cache, `d` its handle, then `sha256`.
    test_stream_sink(): void {
      const over = digest_entry("stream_over");
      const cache = cache_make();
      const data = over.data;
      this.assertEqual(data.length, limits_get().overflow_bytes + 1);
      const text =
        `{"0":{"t":"echo","b":2},"1":{"s":${data.length},"k":"big"},` +
        '"2":{"s":1}}\r';
      const pieces = [bytes_of(text), data, bytes_of("x")];
      const found = pieces_decode(decoder_make(cache), pieces);
      this.assertEqual(found.length, 1);
      const blob = blob_at(found[0], 1);
      this.assertEqual(Object.keys(blob), ["s", "k", "d", "sha256"]);
      this.assertEqual(typeof blob.d, "string");
      this.assertEqual(blob["sha256"], over.sha256);
      this.assertEqual(blob_bytes(cache, blob), data);
      this.assertEqual(cache.slots_free(), constants.cache_slots - 1);
      this.assertEqual(blob_at(found[0], 2).d, bytes_of("x"));
    }

    // A blob of exactly `overflow_bytes` stays in memory, with no file.
    test_stream_exact(): void {
      const cache = cache_make();
      const data = pattern_make(limits_get().overflow_bytes, 256);
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${data.length}}}\r`;
      const stream = bytes_join([bytes_of(text), data]);
      const found = pieces_decode(decoder_make(cache), [stream]);
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_at(found[0], 1).d, data);
      this.assertFalse(Object.hasOwn(blob_at(found[0], 1), "sha256"));
      this.assertEqual(cache.slots_free(), constants.cache_slots);
    }

    // A streamed blob fed one byte at a time gives the same bytes and hash.
    test_stream_bytes(): void {
      const long = digest_entry("stream_long");
      const cache = cache_make();
      const data = long.data;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${data.length}}}\r`;
      const stream = bytes_join([bytes_of(text), data]);
      const found = pieces_decode(
        decoder_make(cache),
        Array.from(stream, (_byte, index) =>
          stream.subarray(index, index + 1),
        ),
      );
      this.assertEqual(found.length, 1);
      this.assertEqual(blob_bytes(cache, blob_at(found[0], 1)), data);
      const sha256 = blob_at(found[0], 1)["sha256"];
      this.assertEqual(sha256, long.sha256);
    }

    // A cache with no free file ends the feed, and the decoder is unusable.
    test_sink_failure(): void {
      const decoder = decoder_make(new substrate.CacheFiles([]));
      const size = limits_get().overflow_bytes + 1;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\r`;
      this.raised_assert(Error, gold_text("substrate_cache_full"), () =>
        decoder.bytes_feed(bytes_of(text)),
      );
      const failed = gold_text("jslb_decoder_failed");
      this.raised_assert(jslb.WireError, failed, () =>
        decoder.bytes_feed(bytes_of(constants.echo_line)),
      );
    }

    // A file closed under a streamed blob fails its append, then its close.
    test_close_failure(): void {
      const size = limits_get().overflow_bytes + 1;
      const text = `{"0":{"t":"echo","b":1},"1":{"s":${size}}}\r`;
      const end = constants.cache_slots + 1;
      const [file] = files_get(constants.cache_slots, end);
      const decoder = decoder_make(new substrate.CacheFiles([file]));
      this.assertEqual(decoder.bytes_feed(bytes_of(text)), []);
      file.close();
      const thrown = thrown_value(() => decoder.bytes_feed(bytes_of("x")));
      if (
        !(thrown instanceof DOMException) ||
        !(thrown.cause instanceof DOMException)
      ) {
        throw new TypeError("the close threw no fault over a fault", {
          cause: thrown,
        });
      }
      this.assertEqual(thrown.name, constants.closed_fault);
      this.assertEqual(thrown.cause.name, constants.closed_fault);
      this.assertTrue(thrown.cause !== thrown);
      this.assertTrue(thrown.cause.cause === undefined);
    }

    // A sent `sha256` is replaced on a streamed blob, kept on one in memory.
    test_hash_sent(): void {
      const over = digest_entry("stream_over");
      const cache = cache_make();
      const sent = "0".repeat(64);
      const data = over.data;
      const text =
        `{"0":{"t":"echo","b":2},"1":{"s":${data.length},` +
        `"sha256":"${sent}"},"2":{"s":1,"sha256":"${sent}"}}\r`;
      const stream = bytes_join([bytes_of(text), data, bytes_of("x")]);
      const found = pieces_decode(decoder_make(cache), [stream]);
      this.assertEqual(found.length, 1);
      const blob = blob_at(found[0], 1);
      this.assertEqual(Object.entries(blob), [
        ["s", data.length],
        ["sha256", over.sha256],
        ["d", blob.d],
      ]);
      this.assertEqual(blob_bytes(cache, blob), data);
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
        const cache = cache_make();
        const decoded = pieces_decode(sidecar_decoder(sidecar, cache), [data]);
        const encoded = bytes_join(
          decoded.map((line) => line_bytes(line, cache)),
        );
        const same = bytes_equal(encoded, data);
        this.assertEqual(same, sidecar.canonical, name);
        for (const source of same ? [data] : [data, encoded]) {
          for (const pieces of feeds_make(source)) {
            const feed_cache = cache_make();
            const decoder = sidecar_decoder(sidecar, feed_cache);
            const found = pieces_decode(decoder, pieces);
            const plain = found.map((line) => line_plain(line, feed_cache));
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
          const cache = cache_make();
          const decoder = sidecar_decoder(sidecar, cache);
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
          const plain = found.map((line) => line_plain(line, cache));
          this.assertEqual(JSON.stringify(plain), messages, name);
          const renders = found.map((line) => jslb.line_render(line));
          this.assertEqual(renders, sidecar.render, name);
        }
      }
    }
  }
}
Object.freeze(test_jslb_decode);
