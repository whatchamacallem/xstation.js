// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// JSLB, the wire format: a line is one JSON object ending in CR, its headers
// at the integer keys 0, 1, ... and its payload at the other keys, followed
// by the bytes of each blob the line header counts. The builders, field
// access, the encoder, the debug rendering, json_decode, and the decoder,
// which bounds the blobs of a message by blob_max, streams a blob over
// overflow_bytes into a sink that hashes it on the way, and holds a fault met
// after finished lines for the next feed.
//
// The decoders are the single door for bad numbers: no other layer checks a
// number. At read, an integer token, digits without a fraction or an
// exponent, beyond 2^53 either way is refused with jslb.integer_refused, its
// text compared by BigInt, and a number token whose double overflows to an
// infinity, such as 1e400, with jslb.number_overflow, both as WireError. The
// tokens are found by scanning the text JSON.parse accepted, strings
// skipped. json_decode applies the same rules to a JSON text read from
// anywhere but a line. The encoder keeps its own refusal of NaN and the
// infinities, jslb.number_refused, inside the same layer.
//
// A sink_close that throws while the decoder shuts a stream after a fault is
// thrown with the first fault under its innermost cause, by
// utility.cause_append, so one error holds both.
namespace jslb {
  // A line: header 0, blob headers 1 on, the payload at the other keys.
  export type Line = lines.Line;

  // The header at key 0 of a line.
  export type LineHeader = lines.LineHeader;

  // A blob header, at keys 1 on of a line.
  export type BlobHeader = lines.BlobHeader;

  // A frozen table from names to names.
  type NameTable = { readonly [name: string]: string };

  // The name tables, the limits and the patterns of the format.
  const constants = Object.freeze({
    // The short line header field names and their full forms.
    line_names: Object.freeze<NameTable>({
      t: "type",
      v: "version",
      i: "id",
      r: "reply",
      k: "key",
      b: "blobs",
    }),
    // The full line header field names.
    line_full: Object.freeze<readonly string[]>([
      "type",
      "version",
      "id",
      "reply",
      "key",
      "blobs",
    ]),
    // The short blob header field names the wire carries and their full forms.
    blob_names: Object.freeze<NameTable>({ s: "size", k: "key" }),
    // The full blob header field names the wire carries and their short forms.
    blob_short: Object.freeze<NameTable>({ size: "s", key: "k" }),
    // The blob header names `blob_make` sets itself, in either form.
    blob_reserved: Object.freeze<readonly string[]>([
      "s",
      "k",
      "d",
      "size",
      "key",
      "data",
    ]),
    // Every short field name `field_get` resolves and its full form.
    field_names: Object.freeze<NameTable>({
      t: "type",
      v: "version",
      i: "id",
      r: "reply",
      k: "key",
      b: "blobs",
      s: "size",
      d: "data",
    }),
    // The short form of every name `field_get` resolves.
    field_short: Object.freeze<NameTable>({
      t: "t",
      type: "t",
      v: "v",
      version: "v",
      i: "i",
      id: "i",
      r: "r",
      reply: "r",
      k: "k",
      key: "k",
      b: "b",
      blobs: "b",
      s: "s",
      size: "s",
      d: "d",
      data: "d",
    }),
    // The defaults of the fields that have one, by short name.
    field_defaults: Object.freeze<{ readonly [name: string]: number }>({
      v: 0,
      b: 0,
    }),
    // The fields a header of their kind must hold, by short name.
    field_required: Object.freeze<readonly string[]>(["t", "s"]),
    // A key of the decimal digits of a non negative integer, no leading zero.
    number_key: /^(?:0|[1-9][0-9]*)$/,
    // A key of decimal digits, which a payload key must not be.
    digit_key: /^[0-9]+$/,
    // A character that is half of a surrogate pair standing alone.
    lone_surrogate: new RegExp(
      `[${String.fromCharCode(0xd800)}-${String.fromCharCode(0xdfff)}]`,
      "u",
    ),
    // The byte that ends a line, CR.
    line_end: 0x0d,
    // A whole string or a number token of a JSON text.
    number_token: /"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g,
    // A number token without a fraction or an exponent.
    integer_token: /^-?\d+$/,
    // The largest magnitude an integer token may have, 2^53.
    integer_limit: 2n ** 53n,
  });

  // A framing, header or number fault. The port that fed the decoder closes.
  export class WireError extends Error {
    // Names the class on its prototype, read when the stack header is made.
    static {
      this.prototype.name = "WireError";
    }
  }

  // Where a blob over `overflow_bytes` streams as it arrives, hashed by it.
  export interface BlobSink {
    // Starts a new blob for the header and returns its handle.
    sink_open(header: BlobHeader): string;
    // Adds bytes to the blob, a view of the fed bytes valid during the call.
    sink_append(handle: string, data: Uint8Array): void;
    // Ends the blob and returns the `SHA-256` of its bytes.
    sink_close(handle: string): lines.Sha256;
  }

  // Builds the header 0. `full` selects full names. Defaults are left out.
  export function header_make(
    type: string,
    options: {
      version?: number;
      id?: number;
      reply?: number;
      key?: string;
      full?: boolean;
    } = {},
  ): LineHeader {
    const { version = 0, id, reply, key, full = false } = options;
    const fields: [string, unknown][] = [["t", type]];
    if (version !== 0) {
      fields.push(["v", version]);
    }
    if (id !== undefined) {
      fields.push(["i", id]);
    }
    if (reply !== undefined) {
      fields.push(["r", reply]);
    }
    if (key !== undefined) {
      fields.push(["k", key]);
    }
    const names = constants.line_names;
    const named = fields.map(
      ([name, value]) => [full ? names[name] : name, value] as const,
    );
    return Object.fromEntries(named) as unknown as LineHeader;
  }

  // Builds a blob header with `d` the bytes and `s` their length.
  export function blob_make(
    data: Uint8Array,
    key?: string,
    fields: { [field: string]: unknown } = {},
  ): BlobHeader {
    const entries: [string, unknown][] = [["s", data.length]];
    if (key !== undefined) {
      entries.push(["k", key]);
    }
    for (const [name, value] of Object.entries(fields)) {
      if (constants.blob_reserved.includes(name)) {
        throw new Error(i18n("jslb.blob_field_reserved", name));
      }
      entries.push([name, value]);
    }
    entries.push(["d", data]);
    return Object.fromEntries(entries) as BlobHeader;
  }

  // Builds a line from its header, blob headers and payload, numbering them.
  export function line_make(
    header: LineHeader,
    blobs: BlobHeader[],
    payload: { [key: string]: unknown },
  ): Line {
    const fields = fields_of(header);
    const full = Object.hasOwn(fields, "type");
    if (Object.hasOwn(fields, "b") || Object.hasOwn(fields, "blobs")) {
      throw new Error(i18n("jslb.blobs_preset"));
    }
    const first: { [key: string]: unknown } = { ...fields };
    if (blobs.length > 0) {
      first[full ? "blobs" : "b"] = blobs.length;
    }
    const entries: [string, unknown][] = [["0", first]];
    for (let number = 1; number <= blobs.length; number += 1) {
      entries.push([String(number), blob_named(blobs[number - 1], full)]);
    }
    for (const [key, value] of Object.entries(payload)) {
      if (constants.digit_key.test(key)) {
        throw new WireError(i18n("jslb.payload_digit_key", key));
      }
      entries.push([key, value]);
    }
    return Object.fromEntries(entries) as Line;
  }

  // Resolves a short or full field name on a header, and its default.
  export function field_get(
    header: LineHeader | BlobHeader,
    name: string,
  ): unknown {
    if (!Object.hasOwn(constants.field_short, name)) {
      throw new Error(i18n("jslb.field_unknown", name));
    }
    const fields = fields_of(header);
    const short = constants.field_short[name];
    const full = constants.field_names[short];
    const has_short = Object.hasOwn(fields, short);
    const has_full = Object.hasOwn(fields, full);
    if (has_short && has_full) {
      throw new WireError(i18n("jslb.both_name_forms"));
    }
    if (has_short) {
      return fields[short];
    }
    if (has_full) {
      return fields[full];
    }
    if (constants.field_required.includes(short)) {
      throw new Error(i18n("jslb.field_missing", name));
    }
    const defaults = constants.field_defaults;
    return Object.hasOwn(defaults, short) ? defaults[short] : undefined;
  }

  // The headers of an object, 0 on, found by probing the integer keys.
  export function headers_of(object: { [key: string]: unknown }): unknown[] {
    const headers: unknown[] = [];
    while (Object.hasOwn(object, String(headers.length))) {
      headers.push(object[String(headers.length)]);
    }
    return headers;
  }

  // The payload: the keys of the line that aren't integer keys.
  export function payload_of(line: Line): { [key: string]: unknown } {
    return Object.fromEntries(
      Object.entries(line).filter(([key]) => !constants.number_key.test(key)),
    );
  }

  // Returns the JSON bytes ending in CR, then each blob's `d` as it is.
  export function line_encode(line: Line): (Uint8Array | string)[] {
    const sizes = line_check(line, false);
    const text = line_text(line, sizes.length) + "\r";
    const pieces: (Uint8Array | string)[] = [utility.utf8_encode(text)];
    for (let number = 1; number <= sizes.length; number += 1) {
      const size = sizes[number - 1];
      const data = header_at(line, number).d;
      if (data instanceof Uint8Array) {
        if (data.length !== size) {
          throw new Error(
            i18n("jslb.blob_size_differs", number, size, data.length),
          );
        }
        pieces.push(data);
      } else if (typeof data === "string") {
        pieces.push(data);
      } else {
        throw new Error(i18n("jslb.blob_data_missing", number));
      }
    }
    return pieces;
  }

  // The JSON text of a line followed by one `<blob "n"=K>` tag per blob.
  export function line_render(line: Line): string {
    const count = line_check(line, false).length;
    let tags = "";
    for (let number = 1; number <= count; number += 1) {
      tags += `<blob "n"=${number}>`;
    }
    return line_text(line, count) + tags;
  }

  // Parses a JSON text by the decoder's number rules, any JSON value.
  export function json_decode(text: string): unknown {
    let value: unknown;
    try {
      value = JSON.parse(text) as unknown;
    } catch (error) {
      throw new WireError(i18n("jslb.text_not_json", String(error)), {
        cause: error,
      });
    }
    numbers_check(text);
    return value;
  }

  // Views a header as the plain object of fields that it is.
  function fields_of(header: object): { [key: string]: unknown } {
    return header as { [key: string]: unknown };
  }

  // Whether the value is a plain object, from a literal or `JSON.parse`.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // Copies a blob header with its size and key named in the line's form.
  function blob_named(blob: BlobHeader, full: boolean): BlobHeader {
    const renames = full ? constants.blob_names : constants.blob_short;
    const entries = Object.entries(blob).map(
      ([name, value]) =>
        [Object.hasOwn(renames, name) ? renames[name] : name, value] as const,
    );
    return Object.fromEntries(entries) as BlobHeader;
  }

  // Returns the header at the key, which must be a JSON object.
  function header_at(
    line: { [key: string]: unknown },
    number: number,
  ): { [key: string]: unknown } {
    const header = line[String(number)];
    if (!object_plain(header)) {
      throw new WireError(i18n("jslb.header_not_object", number));
    }
    return header;
  }

  // Whether a header uses full names, `undefined` when it uses neither.
  function form_get(
    header: { [key: string]: unknown },
    names: NameTable,
  ): boolean | undefined {
    const shorts = Object.keys(names);
    const short = shorts.some((name) => Object.hasOwn(header, name));
    const full = shorts.some((name) => Object.hasOwn(header, names[name]));
    if (short && full) {
      throw new WireError(i18n("jslb.both_name_forms"));
    }
    return short || full ? full : undefined;
  }

  // Checks a line's headers and payload keys and returns each blob's size.
  function line_check(
    line: { [key: string]: unknown },
    wire: boolean,
  ): number[] {
    if (!Object.hasOwn(line, "0")) {
      throw new WireError(i18n("jslb.no_header_zero"));
    }
    const header = header_at(line, 0);
    for (const name of Object.keys(header)) {
      if (
        !Object.hasOwn(constants.line_names, name) &&
        !constants.line_full.includes(name)
      ) {
        throw new WireError(i18n("jslb.unknown_line_field", name));
      }
    }
    const full = form_get(header, constants.line_names);
    if (typeof header[full ? "type" : "t"] !== "string") {
      throw new WireError(i18n("jslb.no_type"));
    }
    const count_name = full ? "blobs" : "b";
    const count = Object.hasOwn(header, count_name) ? header[count_name] : 0;
    let probed = 0;
    while (Object.hasOwn(line, String(probed + 1))) {
      probed += 1;
    }
    for (const key of Object.keys(line)) {
      if (constants.number_key.test(key) && Number(key) > probed) {
        throw new WireError(i18n("jslb.blob_gap", probed + 1, key));
      }
    }
    if (
      typeof count !== "number" ||
      !Number.isInteger(count) ||
      count !== probed
    ) {
      throw new WireError(i18n("jslb.blobs_mismatch", count, probed));
    }
    const sizes: number[] = [];
    for (let number = 1; number <= probed; number += 1) {
      const blob = header_at(line, number);
      if (Object.hasOwn(blob, "data") || (wire && Object.hasOwn(blob, "d"))) {
        throw new WireError(i18n("jslb.blob_data_field", number));
      }
      const form = form_get(blob, constants.blob_names);
      if (form !== undefined && form !== full) {
        throw new WireError(i18n("jslb.both_name_forms"));
      }
      const size = blob[full ? "size" : "s"];
      if (typeof size !== "number" || !Number.isInteger(size) || size < 0) {
        throw new WireError(i18n("jslb.bad_size", number));
      }
      sizes.push(size);
    }
    for (const key of Object.keys(line)) {
      if (constants.digit_key.test(key) && !constants.number_key.test(key)) {
        throw new WireError(i18n("jslb.payload_digit_key", key));
      }
    }
    return sizes;
  }

  // Returns the JSON text the encoder writes for a line with `count` blobs.
  function line_text(line: { [key: string]: unknown }, count: number): string {
    const sent: { [key: string]: unknown } = { ...line };
    for (let number = 1; number <= count; number += 1) {
      const header = header_at(line, number);
      sent[String(number)] = Object.fromEntries(
        Object.entries(header).filter(([name]) => name !== "d"),
      );
    }
    return json_write(sent);
  }

  // Returns the JSON text of a value, integer keys first, numbers checked.
  function json_write(value: unknown): string {
    if (value === null || typeof value === "boolean") {
      return String(value);
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new Error(i18n("jslb.number_refused", value));
      }
      return utility.json_text(value);
    }
    if (typeof value === "string") {
      return text_write(value);
    }
    if (Array.isArray(value)) {
      const items: readonly unknown[] = value;
      return `[${Array.from(items, (item) => json_write(item)).join(",")}]`;
    }
    if (object_plain(value)) {
      const object: { [key: string]: unknown } = value;
      const keys = Object.keys(object);
      const numbers = keys.filter((key) => constants.number_key.test(key));
      const names = keys.filter((key) => !constants.number_key.test(key));
      const members = [...numbers.sort(key_compare), ...names].map(
        (key) => `${text_write(key)}:${json_write(object[key])}`,
      );
      return `{${members.join(",")}}`;
    }
    throw new Error(
      i18n("jslb.value_refused", Object.prototype.toString.call(value)),
    );
  }

  // Returns the JSON text of a string, which must be valid Unicode.
  function text_write(text: string): string {
    if (constants.lone_surrogate.test(text)) {
      throw new Error(i18n("jslb.text_refused"));
    }
    return utility.json_text(text);
  }

  // Orders two distinct integer keys by their value, however many digits.
  function key_compare(first: string, second: string): number {
    if (first.length !== second.length) {
      return first.length - second.length;
    }
    return first < second ? -1 : 1;
  }

  // Decodes the bytes of a line as strict `UTF-8`, a leading BOM kept.
  function text_decode(data: Uint8Array): string {
    try {
      return utility.utf8_decode(data);
    } catch (error) {
      throw new WireError(i18n("jslb.line_not_utf8", String(error)), {
        cause: error,
      });
    }
  }

  // Parses the text of a line as JSON.
  function json_parse(text: string): unknown {
    try {
      return JSON.parse(text) as unknown;
    } catch (error) {
      throw new WireError(i18n("jslb.line_not_json", String(error)), {
        cause: error,
      });
    }
  }

  // Refuses the first number token of a parsed text that is a bad number.
  function numbers_check(text: string): void {
    for (const match of text.matchAll(constants.number_token)) {
      const token = match[0];
      if (token.startsWith('"')) {
        continue;
      }
      if (constants.integer_token.test(token)) {
        const value = BigInt(token);
        const limit = constants.integer_limit;
        if (value > limit || value < -limit) {
          throw new WireError(i18n("jslb.integer_refused", token));
        }
      } else if (!Number.isFinite(Number(token))) {
        throw new WireError(i18n("jslb.number_overflow", token));
      }
    }
  }

  // Parses line bytes as strict `UTF-8` JSON into a plain object.
  function line_decode(data: Uint8Array): { [key: string]: unknown } {
    const text = text_decode(data);
    const value = json_parse(text);
    numbers_check(text);
    if (!object_plain(value)) {
      throw new WireError(i18n("jslb.line_not_object"));
    }
    return value;
  }

  // Reads lines and their blobs from a byte stream fed in pieces of any size.
  export class LineDecoder {
    // The longest line read, its CR included.
    readonly #line_max: number;
    // The most bytes the blobs of one message come to.
    readonly #blob_max: number;
    // The largest blob kept in memory, larger ones stream to the sink.
    readonly #overflow_bytes: number;
    // Where a blob over `overflow_bytes` streams.
    readonly #sink: BlobSink;
    // Whether a feed met a fault, after which every feed throws.
    #failed = false;
    // A fault a feed met after finishing lines, which the next feed throws.
    #fault: { thrown: unknown } | undefined = undefined;
    // The pieces of the line read so far, before its CR.
    #pieces: Uint8Array[] = [];
    // The number of bytes in those pieces.
    #length = 0;
    // The line whose blobs are being read, if any.
    #line: { [key: string]: unknown } | undefined = undefined;
    // The sizes of the blobs of that line.
    #sizes: number[] = [];
    // The number of the blob being read, from 1.
    #number = 0;
    // The bytes of that blob still to come.
    #left = 0;
    // The bytes of a blob kept in memory, sized to fit it.
    #memory = new Uint8Array(0);
    // How many bytes of that memory are filled.
    #filled = 0;
    // The handle of the sink for the blob being streamed, if any.
    #handle: string | undefined = undefined;

    // Takes the limits in bytes and the sink of blobs over `overflow_bytes`.
    constructor(
      line_max: number,
      blob_max: number,
      overflow_bytes: number,
      sink: BlobSink,
    ) {
      this.#line_max = line_max;
      this.#blob_max = blob_max;
      this.#overflow_bytes = overflow_bytes;
      this.#sink = sink;
    }

    // Returns the lines finished. A fault after them throws on the next call.
    bytes_feed(data: Uint8Array): Line[] {
      const fault = this.#fault;
      if (fault !== undefined) {
        this.#fault = undefined;
        throw fault.thrown;
      }
      if (this.#failed) {
        throw new WireError(i18n("jslb.decoder_failed"));
      }
      this.#failed = true;
      const found: Line[] = [];
      try {
        this.#bytes_read(data, found);
        this.#failed = false;
      } catch (error) {
        let fault: unknown = error;
        try {
          this.#stream_shut();
        } catch (second) {
          fault = utility.cause_append(second, error);
        }
        if (found.length === 0) {
          throw fault;
        }
        this.#fault = { thrown: fault };
      }
      return found;
    }

    // Whether the decoder stands between messages and has not failed.
    idle(): boolean {
      return !this.#failed && this.#line === undefined && this.#length === 0;
    }

    // Reads the bytes, adding each line they finish to `found`.
    #bytes_read(data: Uint8Array, found: Line[]): void {
      let offset = 0;
      for (;;) {
        const line = this.#line;
        if (line === undefined) {
          const end = data.indexOf(constants.line_end, offset);
          if (end < 0) {
            this.#length_check(data.length - offset);
            this.#text_add(data.slice(offset));
            return;
          }
          this.#length_check(end - offset);
          this.#text_add(data.subarray(offset, end));
          offset = end + 1;
          const parsed = this.#line_parse();
          if (this.#sizes.length === 0) {
            found.push(parsed as Line);
          } else {
            this.#line = parsed;
            this.#blob_start(parsed, 1);
          }
          continue;
        }
        const count = Math.min(this.#left, data.length - offset);
        if (count > 0) {
          this.#blob_write(data.subarray(offset, offset + count));
          offset += count;
        }
        if (this.#left > 0) {
          return;
        }
        this.#blob_finish(line);
        if (this.#number < this.#sizes.length) {
          this.#blob_start(line, this.#number + 1);
          continue;
        }
        found.push(line as Line);
        this.#line = undefined;
      }
    }

    // Closes the sink's blob when one is open, the bytes it holds kept.
    #stream_shut(): void {
      const handle = this.#handle;
      if (handle !== undefined) {
        this.#handle = undefined;
        this.#sink.sink_close(handle);
      }
    }

    // Refuses a line once its bytes and its CR would pass `line_max`.
    #length_check(more: number): void {
      if (this.#length + more + 1 > this.#line_max) {
        throw new WireError(i18n("jslb.line_over_max", this.#line_max));
      }
    }

    // Keeps a piece of the line being read.
    #text_add(piece: Uint8Array): void {
      this.#pieces.push(piece);
      this.#length += piece.length;
    }

    // Parses and checks the line read, refusing blobs over `blob_max` in all.
    #line_parse(): { [key: string]: unknown } {
      const text = new Uint8Array(this.#length);
      let offset = 0;
      for (const piece of this.#pieces) {
        text.set(piece, offset);
        offset += piece.length;
      }
      this.#pieces = [];
      this.#length = 0;
      const line = line_decode(text);
      const sizes = line_check(line, true);
      const total = sizes.reduce((sum, size) => sum + size, 0);
      if (total > this.#blob_max) {
        throw new WireError(i18n("jslb.blobs_over", total, this.#blob_max));
      }
      this.#sizes = sizes;
      return line;
    }

    // Starts blob `number` of the line, in memory or in the sink.
    #blob_start(line: { [key: string]: unknown }, number: number): void {
      this.#number = number;
      this.#left = this.#sizes[number - 1];
      if (this.#left > this.#overflow_bytes) {
        const header = header_at(line, number) as BlobHeader;
        this.#handle = this.#sink.sink_open(header);
      } else {
        this.#memory = new Uint8Array(this.#left);
        this.#filled = 0;
      }
    }

    // Adds bytes to the blob being read, in memory or through the sink.
    #blob_write(piece: Uint8Array): void {
      const handle = this.#handle;
      if (handle === undefined) {
        this.#memory.set(piece, this.#filled);
        this.#filled += piece.length;
      } else {
        this.#sink.sink_append(handle, piece);
      }
      this.#left -= piece.length;
    }

    // Sets `d` on the finished blob, and if streamed `sha256`, over any sent.
    #blob_finish(line: { [key: string]: unknown }): void {
      const header = header_at(line, this.#number);
      const handle = this.#handle;
      if (handle === undefined) {
        header.d = this.#memory;
        this.#memory = new Uint8Array(0);
        return;
      }
      this.#handle = undefined;
      const sha256 = this.#sink.sink_close(handle);
      header.d = handle;
      header.sha256 = sha256;
    }
  }
}
Object.freeze(jslb);
