// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the shared routines in `utility.ts`. Every one is synchronous.
// The digest vectors of build/vectors, inputs at the edges of the padding of
// `SHA-256`, which the test page carries in test_vectors as sha256.json, are
// checked by `sha256_hex` and by `HashStream` fed whole and in pieces. The
// texts of the refusals are compared to the gold record, test_settings.json.
namespace test_utility {
  // The vector files by name, as base64 text, a global the test page sets.
  declare const test_vectors: { readonly [name: string]: string };

  // The file of the digest vectors and the size of each vector's input.
  const constants = Object.freeze({
    digests_name: "sha256.json",
    digest_sizes: Object.freeze<{ readonly [name: string]: number }>({
      sha256_55: 55,
      sha256_56: 56,
      sha256_64: 64,
    }),
  });

  // A digest vector: its input and that input's `SHA-256`, in lowercase hex.
  interface DigestVector {
    data: string;
    sha256: string;
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_utility.texts.${name}`) as string;
  }

  // The bytes of ASCII only text, made without the code under test.
  function ascii_bytes(text: string): Uint8Array {
    return Uint8Array.from(text, (character) => character.charCodeAt(0));
  }

  // The values of the bytes as comma separated decimal text.
  function bytes_text(bytes: Uint8Array): string {
    return Array.from(bytes).join(",");
  }

  // The character codes of ASCII only text as comma separated decimal text.
  function codes_text(text: string): string {
    return Array.from(text, (character) => character.charCodeAt(0)).join(",");
  }

  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // The bytes as lowercase hex, two characters each.
  function hex_of(data: Uint8Array): string {
    return Array.from(data, (byte) => byte.toString(16).padStart(2, "0")).join(
      "",
    );
  }

  // The bytes `index % 256` for each index below the count.
  function pattern_make(count: number): Uint8Array {
    return Uint8Array.from({ length: count }, (_item, index) => index % 256);
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

  // The digest a new `HashStream` gives for the pieces fed one after another.
  function stream_digest(pieces: readonly Uint8Array[]): string {
    const hash = new utility.HashStream();
    for (const piece of pieces) {
      hash.bytes_add(piece);
    }
    return hash.digest_hex();
  }

  // The digests of the standard test messages, empty, short, long and huge.
  export class TestDigest extends unittest.TestCase {
    // No bytes at all still hash the one padding block.
    test_empty_input(): void {
      this.assertEqual(
        utility.sha256_hex(new Uint8Array(0)),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      );
    }

    // The standard three byte message.
    test_short_text(): void {
      this.assertEqual(
        utility.sha256_hex(ascii_bytes("abc")),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
      );
    }

    // The standard 448 bit message, whose padding spills into a second block.
    test_padding_block(): void {
      const text = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
      this.assertEqual(text.length, 56);
      this.assertEqual(
        utility.sha256_hex(ascii_bytes(text)),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
      );
    }

    // The standard 896 bit message, whose own bytes span two chunks.
    test_two_chunks(): void {
      const text =
        "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmn" +
        "hijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu";
      this.assertEqual(text.length, 112);
      this.assertEqual(
        utility.sha256_hex(ascii_bytes(text)),
        "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1",
      );
    }

    // The standard message of a million letters a, many chunks.
    test_million_bytes(): void {
      this.assertEqual(
        utility.sha256_hex(new Uint8Array(1000000).fill(0x61)),
        "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0",
      );
    }

    // Bytes that start inside a larger buffer hash as they would alone.
    test_view_offset(): void {
      const padded = Uint8Array.of(0, 0x61, 0x62, 0x63, 0);
      this.assertEqual(
        utility.sha256_hex(padded.subarray(1, 4)),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
      );
    }

    // Inputs of 55, 56 and 64 bytes, whole and in pieces, give their digest.
    test_padding_vectors(): void {
      const name = constants.digests_name;
      if (!Object.hasOwn(test_vectors, name)) {
        throw new Error(`test_vectors has no file ${name}`);
      }
      const file = utility.base64_decode(test_vectors[name]);
      const vectors = JSON.parse(utility.utf8_decode(file)) as {
        [name: string]: DigestVector;
      };
      const sizes = constants.digest_sizes;
      this.assertEqual(Object.keys(vectors).sort(), Object.keys(sizes).sort());
      for (const [key, size] of Object.entries(sizes)) {
        const vector = vectors[key];
        const data = pattern_make(size);
        this.assertEqual(vector.data, hex_of(data), key);
        this.assertEqual(utility.sha256_hex(data), vector.sha256, key);
        for (const pieces of feeds_make(data)) {
          this.assertEqual(stream_digest(pieces), vector.sha256, key);
        }
      }
    }
  }

  // The streamed `SHA-256`, fed in pieces.
  export class TestHashStream extends unittest.TestCase {
    // A digest taken midway leaves the stream to go on to the whole digest.
    test_digest_midway(): void {
      const hash = new utility.HashStream();
      hash.bytes_add(ascii_bytes("abc"));
      this.assertEqual(
        hash.digest_hex(),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
      );
      hash.bytes_add(
        ascii_bytes("dbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
      );
      this.assertEqual(
        hash.digest_hex(),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
      );
    }

    // A view into a larger buffer is read from its offset, and not kept.
    test_view_offset(): void {
      const padded = Uint8Array.of(0, 0x61, 0x62, 0x63, 0);
      const hash = new utility.HashStream();
      hash.bytes_add(padded.subarray(1, 4));
      padded.fill(0);
      this.assertEqual(
        hash.digest_hex(),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
      );
    }
  }

  // The `UTF-8` routines, with characters of every length.
  export class TestEncoding extends unittest.TestCase {
    // Checks that decoding the bytes throws the message of invalid `UTF-8`.
    bytes_refused(bytes: Uint8Array): void {
      this.assertEqual(
        message_thrown(this, () => utility.utf8_decode(bytes)),
        gold_text("utility_bytes_refused"),
        bytes_text(bytes),
      );
    }

    // No text gives no bytes.
    test_empty_text(): void {
      this.assertEqual(utility.utf8_encode("").length, 0);
      this.assertEqual(utility.utf8_decode(new Uint8Array(0)), "");
    }

    // ASCII is one byte each.
    test_ascii_bytes(): void {
      this.assertEqual(bytes_text(utility.utf8_encode("abc")), "97,98,99");
    }

    // `U+00E9` takes two bytes.
    test_two_bytes(): void {
      const text = String.fromCodePoint(0xe9);
      this.assertEqual(bytes_text(utility.utf8_encode(text)), "195,169");
      this.assertEqual(utility.utf8_decode(Uint8Array.of(0xc3, 0xa9)), text);
    }

    // `U+20AC` and `U+4E2D` take three bytes.
    test_three_bytes(): void {
      const euro = String.fromCodePoint(0x20ac);
      const middle = String.fromCodePoint(0x4e2d);
      this.assertEqual(bytes_text(utility.utf8_encode(euro)), "226,130,172");
      this.assertEqual(bytes_text(utility.utf8_encode(middle)), "228,184,173");
      this.assertEqual(
        utility.utf8_decode(Uint8Array.of(0xe2, 0x82, 0xac)),
        euro,
      );
    }

    // `U+1F600` takes four bytes.
    test_four_bytes(): void {
      const text = String.fromCodePoint(0x1f600);
      this.assertEqual(
        bytes_text(utility.utf8_encode(text)),
        "240,159,152,128",
      );
      this.assertEqual(
        utility.utf8_decode(Uint8Array.of(0xf0, 0x9f, 0x98, 0x80)),
        text,
      );
    }

    // Text of every length survives encoding and decoding.
    test_round_trip(): void {
      const text =
        "a" +
        String.fromCodePoint(0) +
        String.fromCodePoint(0x7f) +
        String.fromCodePoint(0xe9) +
        String.fromCodePoint(0x20ac) +
        String.fromCodePoint(0x1f600) +
        "z";
      this.assertEqual(utility.utf8_decode(utility.utf8_encode(text)), text);
    }

    // A leading byte order mark is kept as the character `U+FEFF`.
    test_byte_order(): void {
      const text = utility.utf8_decode(Uint8Array.of(0xef, 0xbb, 0xbf, 0x61));
      this.assertEqual(text, String.fromCodePoint(0xfeff) + "a");
    }

    // A surrogate that is not half of a pair throws, wherever it stands.
    test_lone_surrogate(): void {
      const texts = [
        String.fromCharCode(0xd800),
        "a" + String.fromCharCode(0xdfff) + "b",
        String.fromCharCode(0xdc00, 0xd800),
        String.fromCodePoint(0x1f600) + String.fromCharCode(0xd83d),
      ];
      for (const [index, text] of texts.entries()) {
        this.assertEqual(
          message_thrown(this, () => utility.utf8_encode(text)),
          gold_text("utility_text_refused"),
          String(index),
        );
      }
    }

    // A byte that no sequence can hold throws.
    test_lone_byte(): void {
      this.bytes_refused(Uint8Array.of(0xff));
    }

    // A lead byte without a continuation byte after it throws.
    test_bad_continuation(): void {
      this.bytes_refused(Uint8Array.of(0xc3, 0x28));
    }

    // An overlong form of a slash throws.
    test_overlong_form(): void {
      this.bytes_refused(Uint8Array.of(0xc0, 0xaf));
    }

    // The bytes of the surrogate `U+D800` throw.
    test_surrogate_bytes(): void {
      this.bytes_refused(Uint8Array.of(0xed, 0xa0, 0x80));
    }

    // A sequence cut short at the end throws.
    test_truncated_form(): void {
      this.bytes_refused(Uint8Array.of(0xe2, 0x82));
    }

    // A code point beyond `U+10FFFF` throws.
    test_range_limit(): void {
      this.bytes_refused(Uint8Array.of(0xf4, 0x90, 0x80, 0x80));
    }
  }

  // The base64 routine.
  export class TestDecoding extends unittest.TestCase {
    // Checks that decoding each text throws the message of strict base64.
    base64_refused(texts: string[]): void {
      for (const text of texts) {
        this.assertEqual(
          message_thrown(this, () => utility.base64_decode(text)),
          gold_text("utility_base64_refused"),
          codes_text(text),
        );
      }
    }

    // The test vectors of the base64 standard, with and without padding.
    test_standard_vectors(): void {
      const vectors: [string, string][] = [
        ["", ""],
        ["Zg==", "f"],
        ["Zm8=", "fo"],
        ["Zm9v", "foo"],
        ["Zm9vYg==", "foob"],
        ["Zm9vYmE=", "fooba"],
        ["Zm9vYmFy", "foobar"],
      ];
      for (const [encoded, plain] of vectors) {
        this.assertEqual(
          bytes_text(utility.base64_decode(encoded)),
          codes_text(plain),
          encoded,
        );
      }
    }

    // Bytes above 127 and the last two characters of the alphabet.
    test_high_bytes(): void {
      const high = utility.base64_decode("//79");
      this.assertEqual(bytes_text(high), "255,254,253");
      this.assertEqual(bytes_text(utility.base64_decode("ABCD")), "0,16,131");
    }

    // A character outside the alphabet throws.
    test_bad_character(): void {
      this.base64_refused(["****", "Zm9v-_==", "Zm9v.A=="]);
    }

    // A length that no padding can complete throws.
    test_bad_length(): void {
      this.base64_refused(["A", "Zm9vY", "Zg===", "=", "===="]);
    }

    // Text whose padding is missing throws.
    test_missing_padding(): void {
      this.base64_refused(["Zg", "Zm8", "Zm9vYg", "Zg="]);
    }

    // A last character whose unused bits are not zero throws.
    test_trailing_bits(): void {
      this.base64_refused(["Zh==", "Zm9=", "Zm9vYh==", "Zm9vYmF="]);
    }

    // White space anywhere throws.
    test_white_space(): void {
      this.base64_refused([" Zg==", "Zg== ", "Zm9v Zg==", "Zm9v\nZg==", "\t"]);
    }
  }

  // The JSON text routine.
  export class TestJsonText extends unittest.TestCase {
    // No whitespace is written outside strings, and inside them it is kept.
    test_compact_output(): void {
      const value = { list: [1, 2, 3], text: "a b", flag: true, none: null };
      this.assertEqual(
        utility.json_text(value),
        '{"list":[1,2,3],"text":"a b","flag":true,"none":null}',
      );
    }

    // Integer like keys come first in ascending order, the rest as inserted.
    test_key_order(): void {
      this.assertEqual(
        utility.json_text({ b: 1, 2: "x", a: 2, 1: "y" }),
        '{"1":"y","2":"x","b":1,"a":2}',
      );
    }

    // Characters beyond ASCII are written as they are.
    test_raw_characters(): void {
      const text = String.fromCodePoint(0xe9) + String.fromCodePoint(0x1f600);
      this.assertEqual(utility.json_text(text), '"' + text + '"');
    }

    // Control characters are escaped.
    test_escaped_controls(): void {
      this.assertEqual(utility.json_text("a\nb"), '"a\\nb"');
    }

    // Every finite double is written, those beyond 2 to the 53 too.
    test_double_range(): void {
      this.assertEqual(utility.json_text(2 ** 53), "9007199254740992");
      this.assertEqual(utility.json_text(-(2 ** 53)), "-9007199254740992");
      this.assertEqual(utility.json_text(2 ** 53 + 2), "9007199254740994");
      this.assertEqual(utility.json_text(1e16), "10000000000000000");
      this.assertEqual(utility.json_text({ big: -1e300 }), '{"big":-1e+300}');
      this.assertEqual(
        utility.json_text(Number.MAX_VALUE),
        "1.7976931348623157e+308",
      );
    }

    // A value with no JSON text throws and does not give undefined.
    test_no_text(): void {
      const values = [undefined, (): number => 1];
      for (const value of values) {
        this.assertEqual(
          message_thrown(this, () => utility.json_text(value)),
          gold_text("utility_value_refused"),
        );
      }
    }
  }

  // The error helpers.
  export class TestFailure extends unittest.TestCase {
    // The wrapper is an `Error` with the message and the very same cause.
    test_wrap_cause(): void {
      const cause = new Error("inner");
      const wrapped = utility.error_wrap("outer", cause);
      this.assertTrue(wrapped instanceof Error);
      this.assertEqual(wrapped.message, "outer");
      this.assertTrue(wrapped.cause === cause);
    }

    // A cause that is not an `Error` is kept as it is.
    test_wrap_value(): void {
      this.assertTrue(utility.error_wrap("outer", "text").cause === "text");
    }

    // The throw carries the message.
    test_fail_now(): void {
      this.assertEqual(
        message_thrown(this, () => utility.fail_now("boom")),
        "boom",
      );
    }
  }

  // The cascade of a fault met while another fault is handled.
  export class TestCauseAppend extends unittest.TestCase {
    // An `Error` with no `cause` takes `first` as it, and is returned itself.
    test_no_cause(): void {
      const error = new Error("second");
      const first = new Error("first");
      const top = utility.cause_append(error, first);
      this.assertTrue(top === error);
      this.assertTrue(error.cause === first);
    }

    // In a chain of two, `first` goes under the innermost.
    test_chain(): void {
      const inner = new Error("inner");
      const error = new Error("outer", { cause: inner });
      const first = new Error("first");
      const top = utility.cause_append(error, first);
      this.assertTrue(top === error);
      this.assertTrue(error.cause === inner);
      this.assertTrue(inner.cause === first);
    }

    // A thrown value that is no `Error` becomes one, its text the message.
    test_value_thrown(): void {
      const first = new Error("first");
      const top = utility.cause_append("second", first);
      this.assertTrue(top instanceof Error);
      this.assertEqual(top.message, "second");
      this.assertTrue(top.cause === first);
    }

    // An innermost `cause` that is no `Error` becomes an `Error` of its text.
    test_cause_value(): void {
      const error = new Error("outer", { cause: 7 });
      const first = new Error("first");
      this.assertTrue(utility.cause_append(error, first) === error);
      const kept = error.cause;
      if (!(kept instanceof Error)) {
        throw new TypeError("the cause is no Error", { cause: kept });
      }
      this.assertEqual(kept.message, "7");
      this.assertTrue(kept.cause === first);
    }
  }

  // The clock.
  export class TestClock extends unittest.TestCase {
    // The time is a whole number between two readings of the platform clock.
    test_clock_bounds(): void {
      const before = Date.now();
      const now = utility.time_now();
      const after = Date.now();
      this.assertTrue(Number.isInteger(now));
      this.assertTrue(before <= now && now <= after);
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the ten names of its declaration.
    test_frozen_names(): void {
      const names = [
        "HashStream",
        "base64_decode",
        "cause_append",
        "error_wrap",
        "fail_now",
        "json_text",
        "sha256_hex",
        "time_now",
        "utf8_decode",
        "utf8_encode",
      ];
      this.assertTrue(Object.isFrozen(utility));
      this.assertEqual(Object.keys(utility).sort().join(","), names.join(","));
    }
  }
}
Object.freeze(test_utility);
