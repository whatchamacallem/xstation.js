// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of jslb.ts that need no decoder: the builders, field access, the
// encoder and its refusals, the debug rendering and json_decode, each
// refusal compared with its message, the texts of the gold record. The
// decoder's tests, which stream into a real cache, are test_jslb_decode's.
namespace test_jslb {
  // The texts and the names the tests use.
  const constants = Object.freeze({
    // The integers just past `2^53` either way.
    integer_above: "9007199254740993",
    integer_below: "-9007199254740993",
    backslash: String.fromCharCode(0x5c),
    gold_id: "typescript.test_jslb",
  });

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

  // The text of strict `UTF-8` bytes.
  function text_decode(data: Uint8Array): string {
    return new TextDecoder("utf-8", { fatal: true }).decode(data);
  }

  // The bytes of text whose characters are all below 256, one byte each.
  function bytes_of(text: string): Uint8Array {
    return Uint8Array.from(text, (character) => character.charCodeAt(0));
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
    return text_decode(first);
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

    // A field that `blob_make` sets cannot be given as a handler field.
    test_blob_reserved(): void {
      for (const name of ["s", "k", "d", "size", "key", "data"]) {
        const fields = { [name]: 1 };
        this.raised_assert(
          Error,
          gold_text(`jslb_blob_field_reserved_${name}`),
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
      this.raised_assert(Error, gold_text("jslb_blobs_preset"), () =>
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
          gold_text(`jslb_payload_digit_key_${key}`),
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
      this.raised_assert(Error, gold_text("jslb_field_missing_type"), () =>
        jslb.field_get(line_header, "type"),
      );
      const blob_header = {} as jslb.BlobHeader;
      this.raised_assert(Error, gold_text("jslb_field_missing_s"), () =>
        jslb.field_get(blob_header, "s"),
      );
      const header = jslb.header_make("echo");
      this.raised_assert(Error, gold_text("jslb_field_unknown"), () =>
        jslb.field_get(header, "sha256"),
      );
    }

    // A header holding both forms of a field throws.
    test_field_forms(): void {
      const header = { ...jslb.header_make("echo"), type: "echo" };
      const forms = gold_text("jslb_both_name_forms");
      this.raised_assert(jslb.WireError, forms, () =>
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

    // `NaN` and the infinities are refused.
    test_float_refused(): void {
      const header = jslb.header_make("echo");
      const cases: [unknown, string][] = [
        [NaN, "jslb_number_refused_nan"],
        [Infinity, "jslb_number_refused_infinity"],
        [-Infinity, "jslb_number_refused_negative"],
        [[NaN], "jslb_number_refused_nan"],
      ];
      for (const [value, refused] of cases) {
        const line = jslb.line_make(header, [], { value });
        this.raised_assert(Error, gold_text(refused), () =>
          jslb.line_encode(line),
        );
      }
    }

    // A value that JSON has no text for is refused, not dropped or changed.
    test_value_refused(): void {
      const header = jslb.header_make("echo");
      const cases: [unknown, string][] = [
        [undefined, "undefined"],
        [[undefined], "undefined"],
        [new Array(1), "undefined"],
        [() => 1, "function"],
        [BigInt(1), "bigint"],
        [Symbol("x"), "symbol"],
        [new Uint8Array(1), "uint8array"],
        [new Map(), "map"],
        [new Date(0), "date"],
      ];
      for (const [value, kind] of cases) {
        const line = jslb.line_make(header, [], { value });
        const message = gold_text(`jslb_value_refused_${kind}`);
        this.raised_assert(Error, message, () => jslb.line_encode(line));
      }
    }

    // Text holding half a surrogate pair is refused, in values and keys.
    test_text_refused(): void {
      const header = jslb.header_make("echo");
      const high = String.fromCharCode(0xd800);
      const low = String.fromCharCode(0xdc00);
      const payloads = [{ text: "a" + high }, { value: { [low]: 1 } }];
      const refused = gold_text("jslb_text_refused");
      for (const payload of payloads) {
        const line = jslb.line_make(header, [], payload);
        this.raised_assert(Error, refused, () => jslb.line_encode(line));
        this.raised_assert(Error, refused, () => jslb.line_render(line));
      }
    }

    // A payload key of digits is refused, a nested one is written as it is.
    test_key_digits(): void {
      const line: jslb.Line = { 0: { t: "echo" }, "01": 1 };
      const refused = gold_text("jslb_payload_digit_key_01");
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
      this.raised_assert(Error, gold_text("jslb_blob_size_differs"), () =>
        jslb.line_encode(differs),
      );
      const bare: jslb.BlobHeader = { s: 3 };
      const missing = jslb.line_make(header, [bare], {});
      this.raised_assert(Error, gold_text("jslb_blob_data_missing"), () =>
        jslb.line_encode(missing),
      );
    }

    // The encoder refuses a line that the decoder would refuse.
    test_encode_checked(): void {
      const empty = {} as jslb.Line;
      const no_header = gold_text("jslb_no_header_zero");
      this.raised_assert(jslb.WireError, no_header, () =>
        jslb.line_encode(empty),
      );
      const blob = jslb.blob_make(bytes_of("x"));
      const counted = jslb.line_make(jslb.header_make("echo"), [blob], {});
      counted[0].b = 2;
      this.raised_assert(
        jslb.WireError,
        gold_text("jslb_blobs_mismatch_over"),
        () => jslb.line_encode(counted),
      );
      const header = { ...jslb.header_make("echo"), x: 1 };
      const extra = jslb.line_make(header, [], {});
      this.raised_assert(
        jslb.WireError,
        gold_text("jslb_unknown_line_field_x"),
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

  // Tests `json_decode`, the decoder's number rules on any JSON text.
  export class TestJsonDecode extends RefusalCase {
    // Any JSON value is returned, an array and a bare number too.
    test_values(): void {
      this.assertEqual(jslb.json_decode('[1,"a",{"b":null}]'), [
        1,
        "a",
        { b: null },
      ]);
      this.assertEqual(jslb.json_decode("12"), 12);
      this.assertEqual(jslb.json_decode('{"0":{"t":"echo"}}'), {
        0: { t: "echo" },
      });
    }

    // The tokens a line reads, read here the same.
    test_numbers_read(): void {
      const tokens = [
        "9007199254740992",
        "-9007199254740992",
        "1e+300",
        "9.007199254740994e+15",
      ];
      for (const token of tokens) {
        this.assertEqual(jslb.json_decode(`[${token}]`), [Number(token)]);
      }
      const digits = "1".repeat(20);
      this.assertEqual(jslb.json_decode(`{"${digits}":"${digits}"}`), {
        [digits]: digits,
      });
    }

    // The tokens a line refuses, refused here the same.
    test_numbers_refused(): void {
      const seventeen = "1".repeat(17);
      const long = "1" + "0".repeat(309);
      const integers: [string, string][] = [
        [constants.integer_above, gold_text("jslb_integer_refused_above")],
        [constants.integer_below, gold_text("jslb_integer_refused_below")],
        [seventeen, text_fill("jslb_integer_refused", seventeen)],
        [long, text_fill("jslb_integer_refused", long)],
      ];
      for (const [token, message] of integers) {
        this.raised_assert(jslb.WireError, message, () =>
          jslb.json_decode(`{"n":${token}}`),
        );
      }
      const overflows: [string, string][] = [
        ["1e400", "jslb_number_overflow_positive"],
        ["-1e400", "jslb_number_overflow_negative"],
        ["1.5e400", "jslb_number_overflow_fraction"],
      ];
      for (const [token, refused] of overflows) {
        this.raised_assert(jslb.WireError, gold_text(refused), () =>
          jslb.json_decode(token),
        );
      }
    }

    // A text that is not JSON is refused, the parse error its cause.
    test_not_json(): void {
      for (const text of ["{", "", "NaN", "[1,]"]) {
        const reason = thrown_value(() => JSON.parse(text));
        const error = thrown_value(() => jslb.json_decode(text));
        if (!(error instanceof jslb.WireError)) {
          throw new TypeError("json_decode threw no WireError", {
            cause: error,
          });
        }
        const message = text_fill("jslb_text_not_json", String(reason));
        this.assertEqual(error.message, message, text);
        this.assertTrue(error.cause instanceof SyntaxError, text);
        this.assertEqual(String(error.cause), String(reason), text);
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
        "json_decode",
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
