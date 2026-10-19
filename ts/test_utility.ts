// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the shared routines in `utility.ts`. Every one is synchronous.
namespace test_utility {
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

  // The digests of the standard test messages, empty, short, long and huge.
  export class TestDigest extends unittest.TestCase {
    // No bytes at all still hash the one padding block.
    test_empty_input(): void {
      this.assertEqual(
        utility.sha256_hex(new Uint8Array(0)),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
      );
    }

    // The standard three byte message.
    test_short_text(): void {
      this.assertEqual(
        utility.sha256_hex(ascii_bytes("abc")),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
      );
    }

    // The standard 448 bit message, whose padding spills into a second block.
    test_padding_block(): void {
      const text = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
      this.assertEqual(text.length, 56);
      this.assertEqual(
        utility.sha256_hex(ascii_bytes(text)),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
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
        "cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1"
      );
    }

    // The standard message of a million letters a, many chunks.
    test_million_bytes(): void {
      this.assertEqual(
        utility.sha256_hex(new Uint8Array(1000000).fill(0x61)),
        "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
      );
    }

    // Bytes that start inside a larger buffer hash as they would alone.
    test_view_offset(): void {
      const padded = Uint8Array.of(0, 0x61, 0x62, 0x63, 0);
      this.assertEqual(
        utility.sha256_hex(padded.subarray(1, 4)),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
      );
    }
  }

  // The `UTF-8` routines, with characters of every length.
  export class TestEncoding extends unittest.TestCase {
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
        euro
      );
    }

    // `U+1F600` takes four bytes.
    test_four_bytes(): void {
      const text = String.fromCodePoint(0x1f600);
      this.assertEqual(
        bytes_text(utility.utf8_encode(text)),
        "240,159,152,128"
      );
      this.assertEqual(
        utility.utf8_decode(Uint8Array.of(0xf0, 0x9f, 0x98, 0x80)),
        text
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

    // A byte that no sequence can hold throws.
    test_lone_byte(): void {
      this.assertRaises(Error, () => utility.utf8_decode(Uint8Array.of(0xff)));
    }

    // A lead byte without a continuation byte after it throws.
    test_bad_continuation(): void {
      this.assertRaises(Error, () =>
        utility.utf8_decode(Uint8Array.of(0xc3, 0x28))
      );
    }

    // An overlong form of a slash throws.
    test_overlong_form(): void {
      this.assertRaises(Error, () =>
        utility.utf8_decode(Uint8Array.of(0xc0, 0xaf))
      );
    }

    // The bytes of the surrogate `U+D800` throw.
    test_surrogate_bytes(): void {
      this.assertRaises(Error, () =>
        utility.utf8_decode(Uint8Array.of(0xed, 0xa0, 0x80))
      );
    }

    // A sequence cut short at the end throws.
    test_truncated_form(): void {
      this.assertRaises(Error, () =>
        utility.utf8_decode(Uint8Array.of(0xe2, 0x82))
      );
    }

    // A code point beyond `U+10FFFF` throws.
    test_range_limit(): void {
      this.assertRaises(Error, () =>
        utility.utf8_decode(Uint8Array.of(0xf4, 0x90, 0x80, 0x80))
      );
    }
  }

  // The base64 routine.
  export class TestDecoding extends unittest.TestCase {
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
          encoded
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
      this.assertRaises(Error, () => utility.base64_decode("****"));
    }

    // A length that no padding can complete throws.
    test_bad_length(): void {
      this.assertRaises(Error, () => utility.base64_decode("A"));
    }
  }

  // The JSON text routine.
  export class TestJsonText extends unittest.TestCase {
    // No whitespace is written outside strings, and inside them it is kept.
    test_compact_output(): void {
      const value = { list: [1, 2, 3], text: "a b", flag: true, none: null };
      this.assertEqual(
        utility.json_text(value),
        '{"list":[1,2,3],"text":"a b","flag":true,"none":null}'
      );
    }

    // Integer like keys come first in ascending order, the rest as inserted.
    test_key_order(): void {
      this.assertEqual(
        utility.json_text({ b: 1, 2: "x", a: 2, 1: "y" }),
        '{"1":"y","2":"x","b":1,"a":2}'
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

    // NaN and the infinities throw, at any depth.
    test_non_finite(): void {
      this.assertRaises(Error, () => utility.json_text(NaN));
      this.assertRaises(Error, () => utility.json_text(Infinity));
      this.assertRaises(Error, () => utility.json_text(-Infinity));
      this.assertRaises(Error, () => utility.json_text({ nested: [1, NaN] }));
    }

    // Integers up to 2 to the 53 are written, larger ones throw.
    test_integer_limit(): void {
      this.assertEqual(utility.json_text(2 ** 53), "9007199254740992");
      this.assertEqual(utility.json_text(-(2 ** 53)), "-9007199254740992");
      this.assertRaises(Error, () => utility.json_text(2 ** 53 + 2));
      this.assertRaises(Error, () => utility.json_text(-(2 ** 53) - 2));
      this.assertRaises(Error, () => utility.json_text({ big: 1e300 }));
    }

    // A value with no JSON text throws and does not give undefined.
    test_no_text(): void {
      this.assertRaises(Error, () => utility.json_text(undefined));
      this.assertRaises(Error, () => utility.json_text(() => 1));
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
      let message = "";
      try {
        utility.fail_now("boom");
      } catch (error) {
        message = error instanceof Error ? error.message : String(error);
      }
      this.assertEqual(message, "boom");
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
    // The module is frozen and holds the eight routines of its declaration.
    test_frozen_names(): void {
      const names = [
        "base64_decode",
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
