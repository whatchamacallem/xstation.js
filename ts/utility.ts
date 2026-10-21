// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The routines the other modules share: error helpers, `SHA-256`, `UTF-8`,
// base64 and JSON text. Every one is synchronous. Its messages come from
// `i18n`, called only when a routine throws.
namespace utility {
  // The sizes and limits of the routines below.
  const constants = Object.freeze({
    block_bytes: 64,
    block_words: 16,
    round_count: 64,
    hash_words: 8,
    word_bytes: 4,
    length_bytes: 8,
    byte_bits: 8,
    padding_marker: 0x80,
    word_range: 2 ** 32,
    surrogate_first: 0xd800,
    surrogate_last: 0xdfff,
  });

  // Matches a surrogate that is not half of a pair, read by code points.
  const surrogate_lone = new RegExp(
    `[${String.fromCharCode(constants.surrogate_first)}-` +
      `${String.fromCharCode(constants.surrogate_last)}]`,
    "u",
  );

  // Matches strict base64: padded, no white space, zero unused bits.
  const base64_form = new RegExp(
    "^(?:[A-Za-z0-9+/]{4})*" +
      "(?:[A-Za-z0-9+/][AQgw]==|[A-Za-z0-9+/]{2}[AEIMQUYcgkosw048]=)?$",
  );

  // The first prime numbers, as many as asked for.
  function primes_first(count: number): number[] {
    const primes: number[] = [];
    for (let candidate = 2; primes.length < count; candidate += 1) {
      if (primes.every((prime) => candidate % prime !== 0)) {
        primes.push(candidate);
      }
    }
    return primes;
  }

  // The first 32 bits of the fractional part of a positive number.
  function fraction_bits(value: number): number {
    return Math.floor((value - Math.floor(value)) * constants.word_range);
  }

  // The round constants: cube root fractions of the first 64 primes.
  const round_table = Uint32Array.from(
    primes_first(constants.round_count),
    (prime) => fraction_bits(Math.cbrt(prime)),
  );

  // The first hash state: square root fractions of the first 8 primes.
  const hash_start = Uint32Array.from(
    primes_first(constants.hash_words),
    (prime) => fraction_bits(Math.sqrt(prime)),
  );

  // The strict `UTF-8` decoder, which keeps a leading byte order mark.
  const text_decoder = new TextDecoder("utf-8", {
    fatal: true,
    ignoreBOM: true,
  });

  // The `UTF-8` encoder.
  const text_encoder = new TextEncoder();

  // Rotates the 32 bits of a word right by a count of bits.
  function bits_rotate(word: number, count: number): number {
    return (word >>> count) | (word << (32 - count));
  }

  // Mixes the block of 64 bytes at the offset into the hash state.
  function block_run(
    state: Uint32Array,
    schedule: Uint32Array,
    view: DataView,
    offset: number,
  ): void {
    const { block_words, round_count, word_bytes } = constants;
    for (let index = 0; index < block_words; index += 1) {
      schedule[index] = view.getUint32(offset + index * word_bytes);
    }
    for (let index = block_words; index < round_count; index += 1) {
      const early = schedule[index - 15];
      const late = schedule[index - 2];
      const sigma_early =
        bits_rotate(early, 7) ^ bits_rotate(early, 18) ^ (early >>> 3);
      const sigma_late =
        bits_rotate(late, 17) ^ bits_rotate(late, 19) ^ (late >>> 10);
      schedule[index] =
        schedule[index - 16] + sigma_early + schedule[index - 7] + sigma_late;
    }
    // The working variables are named as in the standard.
    let [a, b, c, d, e, f, g, h] = state;
    for (let index = 0; index < round_count; index += 1) {
      const sigma_e =
        bits_rotate(e, 6) ^ bits_rotate(e, 11) ^ bits_rotate(e, 25);
      const choice = (e & f) ^ (~e & g);
      const first =
        (h + sigma_e + choice + round_table[index] + schedule[index]) | 0;
      const sigma_a =
        bits_rotate(a, 2) ^ bits_rotate(a, 13) ^ bits_rotate(a, 22);
      const majority = (a & b) ^ (a & c) ^ (b & c);
      const second = (sigma_a + majority) | 0;
      h = g;
      g = f;
      f = e;
      e = (d + first) | 0;
      d = c;
      c = b;
      b = a;
      a = (first + second) | 0;
    }
    const working = [a, b, c, d, e, f, g, h];
    for (let index = 0; index < constants.hash_words; index += 1) {
      state[index] += working[index];
    }
  }

  // Makes an `Error` with `cause` set.
  export function error_wrap(message: string, cause: unknown): Error {
    return new Error(message, { cause });
  }

  // Throws an `Error`, so that a throw can stand where an expression is.
  export function fail_now(message: string): never {
    throw new Error(message);
  }

  // Hashes the bytes with `SHA-256` and returns 64 lowercase hex characters.
  export function sha256_hex(data: Uint8Array): lines.Sha256 {
    const { block_bytes, length_bytes, word_bytes, word_range } = constants;
    const state = new Uint32Array(hash_start);
    const schedule = new Uint32Array(constants.round_count);
    const remainder = data.length % block_bytes;
    const body_length = data.length - remainder;
    const body = new DataView(data.buffer, data.byteOffset, body_length);
    for (let offset = 0; offset < body_length; offset += block_bytes) {
      block_run(state, schedule, body, offset);
    }
    const tail_length =
      remainder < block_bytes - length_bytes ? block_bytes : 2 * block_bytes;
    const tail = new Uint8Array(tail_length);
    tail.set(data.subarray(body_length));
    tail[remainder] = constants.padding_marker;
    const bits = data.length * constants.byte_bits;
    const tail_view = new DataView(tail.buffer);
    const high = Math.floor(bits / word_range);
    tail_view.setUint32(tail_length - length_bytes, high);
    tail_view.setUint32(tail_length - word_bytes, bits % word_range);
    for (let offset = 0; offset < tail_length; offset += block_bytes) {
      block_run(state, schedule, tail_view, offset);
    }
    let hex = "";
    for (const word of state) {
      hex += word.toString(16).padStart(word_bytes * 2, "0");
    }
    return hex;
  }

  // Encodes text as `UTF-8` and throws on a lone surrogate.
  export function utf8_encode(text: string): Uint8Array {
    if (surrogate_lone.test(text)) {
      fail_now(i18n("utility.text_refused"));
    }
    return text_encoder.encode(text);
  }

  // Decodes `UTF-8` and throws on an invalid sequence.
  export function utf8_decode(data: Uint8Array): string {
    try {
      return text_decoder.decode(data);
    } catch (error) {
      throw error_wrap(i18n("utility.bytes_refused"), error);
    }
  }

  // Decodes strict base64 text into bytes and throws on any other text.
  export function base64_decode(text: string): Uint8Array {
    if (!base64_form.test(text)) {
      fail_now(i18n("utility.base64_refused"));
    }
    const binary = atob(text);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }

  // A JSON replacer that throws on `NaN` and the infinities, which JSON lacks.
  function number_check(_key: string, value: unknown): unknown {
    if (typeof value === "number" && !Number.isFinite(value)) {
      fail_now(i18n("utility.number_refused", value));
    }
    return value;
  }

  // Writes a value as JSON text with no whitespace outside strings.
  export function json_text(value: unknown): string {
    const text: unknown = JSON.stringify(value, number_check);
    if (typeof text !== "string") {
      return fail_now(i18n("utility.value_refused"));
    }
    return text;
  }

  // Milliseconds since the epoch.
  export function time_now(): number {
    return Date.now();
  }
}
Object.freeze(utility);
