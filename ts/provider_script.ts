// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The scripted provider, with no network and no AI: a port that answers the
// `http.request` lines of the provider door from a table of nodes, and the
// PNG test pattern that answers every image request, built here by hand from
// stored deflate blocks with its checksums computed in code. Every part of it
// is synchronous.

namespace provider_script {
  // The line type, the request and reply parts, and the layout of the PNG.
  const constants = Object.freeze({
    request_type: "http.request",
    full_key: "type",
    method: "POST",
    chat_path: "/chat/completions",
    image_path: "/images/generations",
    image_format: "b64_json",
    status: 200,
    content_key: "content-type",
    json_media: "application/json",
    id_prefix: "chatcmpl-synthetic-",
    assistant_role: "assistant",
    user_role: "user",
    tool_role: "tool",
    calls_reason: "tool_calls",
    stop_reason: "stop",
    // The decimal text of one integer, which a user message must be.
    integer_text: /^(?:0|-?[1-9][0-9]*)$/,
    pattern_size: 16,
    square_size: 4,
    channel_count: 3,
    light_value: 255,
    dark_value: 0,
    row_filter: 0,
    bit_depth: 8,
    color_type: 2,
    compression_method: 0,
    filter_method: 0,
    interlace_method: 0,
    // The eight bytes that start every PNG file.
    png_signature: Object.freeze([
      0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
    ]),
    header_kind: "IHDR",
    data_kind: "IDAT",
    end_kind: "IEND",
    deflate_method: 8,
    // The zlib window of 32 KiB, as its base two logarithm less 8.
    window_info: 7,
    info_shift: 4,
    fastest_level: 0,
    level_shift: 6,
    // The divisor of the check bits of a zlib header.
    check_divisor: 31,
    stored_type: 0,
    type_shift: 1,
    final_flag: 1,
    // The most bytes one stored block holds.
    block_max: 0xffff,
    block_head: 5,
    // The exponents of the `CRC-32` polynomial below its term of degree 32.
    crc_exponents: Object.freeze([
      26, 23, 22, 16, 12, 11, 10, 8, 7, 5, 4, 2, 1, 0,
    ]),
    word_bits: 32,
    word_mask: 2 ** 32 - 1,
    byte_bits: 8,
    byte_mask: 0xff,
    byte_range: 256,
    sum_range: 2 ** 16,
  });

  // One reply of the script and the node it leads to.
  export interface ScriptReply {
    // What the assistant says, `null` when it only calls tools.
    content: string | null;
    // The tools the reply calls, if any.
    tool_calls?: provider.ToolCall[];
    // The node to be in after this reply's tool results arrive.
    next: string;
  }

  // One node of the script: its replies by input and after tool results.
  export interface ScriptNode {
    // Replies by the integer the user sent, as decimal strings.
    replies: { [input: string]: ScriptReply };
    // The reply after tool results, when the node was reached by tools.
    after_tools?: ScriptReply;
  }

  // A script: the node it starts in and every node by name.
  export interface Script {
    start: string;
    nodes: { [node: string]: ScriptNode };
  }

  // An object of unknown members, as a parsed JSON body holds them.
  type FieldTable = { [key: string]: unknown };

  // The largest prime below the limit, found by trial division.
  function prime_below(limit: number): number {
    for (let candidate = limit - 1; ; candidate -= 1) {
      let divisor = 2;
      while (divisor * divisor <= candidate && candidate % divisor !== 0) {
        divisor += 1;
      }
      if (divisor * divisor > candidate) {
        return candidate;
      }
    }
  }

  // The `CRC-32` remainder of every byte value, its bits reversed.
  function table_make(): Uint32Array {
    let polynomial = 0;
    for (const exponent of constants.crc_exponents) {
      polynomial |= 1 << (constants.word_bits - 1 - exponent);
    }
    const table = new Uint32Array(constants.byte_range);
    for (let value = 0; value < table.length; value += 1) {
      let remainder = value;
      for (let bit = 0; bit < constants.byte_bits; bit += 1) {
        remainder = (remainder >>> 1) ^ (polynomial & -(remainder & 1));
      }
      table[value] = remainder;
    }
    return table;
  }

  // The `CRC-32` of the bytes, as a PNG chunk carries it.
  function crc_compute(data: Uint8Array): number {
    const crc_table = table_make();
    let crc = constants.word_mask;
    for (const byte of data) {
      const index = (crc ^ byte) & constants.byte_mask;
      crc = crc_table[index] ^ (crc >>> constants.byte_bits);
    }
    return (crc ^ constants.word_mask) >>> 0;
  }

  // The `Adler-32` of the bytes, which ends a zlib stream.
  function adler_compute(data: Uint8Array): number {
    const adler_modulus = prime_below(constants.sum_range);
    let low = 1;
    let high = 0;
    for (const byte of data) {
      low = (low + byte) % adler_modulus;
      high = (high + low) % adler_modulus;
    }
    return high * constants.sum_range + low;
  }

  // The bytes of the parts, one after another.
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

  // The four bytes of a 32 bit number, the most significant first.
  function word_bytes(value: number): Uint8Array {
    const bytes = new Uint8Array(constants.word_bits / constants.byte_bits);
    new DataView(bytes.buffer).setUint32(0, value);
    return bytes;
  }

  // A PNG chunk: the length of its data, its type and data, their `CRC-32`.
  function chunk_make(kind: string, body: Uint8Array): Uint8Array {
    const typed = bytes_join([utility.utf8_encode(kind), body]);
    return bytes_join([
      word_bytes(body.length),
      typed,
      word_bytes(crc_compute(typed)),
    ]);
  }

  // The data of the header chunk: the size, 8 bit RGB and no interlace.
  function image_header(): Uint8Array {
    const size = word_bytes(constants.pattern_size);
    const fields = Uint8Array.from([
      constants.bit_depth,
      constants.color_type,
      constants.compression_method,
      constants.filter_method,
      constants.interlace_method,
    ]);
    return bytes_join([size, size, fields]);
  }

  // The rows of a checkerboard of light and dark squares, each unfiltered.
  function rows_draw(): Uint8Array {
    const { pattern_size, square_size, channel_count } = constants;
    const row_bytes = 1 + pattern_size * channel_count;
    const rows = new Uint8Array(pattern_size * row_bytes);
    for (let y = 0; y < pattern_size; y += 1) {
      const start = y * row_bytes;
      rows[start] = constants.row_filter;
      for (let x = 0; x < pattern_size; x += 1) {
        const squares =
          Math.floor(x / square_size) + Math.floor(y / square_size);
        const value =
          squares % 2 === 0 ? constants.light_value : constants.dark_value;
        const pixel = start + 1 + x * channel_count;
        rows.fill(value, pixel, pixel + channel_count);
      }
    }
    return rows;
  }

  // Stored deflate blocks: flags, length, its complement, then the bytes.
  function blocks_store(data: Uint8Array): Uint8Array {
    const parts: Uint8Array[] = [];
    let offset = 0;
    do {
      const length = Math.min(constants.block_max, data.length - offset);
      const last = offset + length === data.length;
      const head = new Uint8Array(constants.block_head);
      const view = new DataView(head.buffer);
      const flag = last ? constants.final_flag : 0;
      head[0] = (constants.stored_type << constants.type_shift) | flag;
      view.setUint16(1, length, true);
      view.setUint16(3, length ^ constants.block_max, true);
      parts.push(head, data.subarray(offset, offset + length));
      offset += length;
    } while (offset < data.length);
    return bytes_join(parts);
  }

  // The zlib stream of the bytes: its header, stored blocks, the `Adler-32`.
  function stream_wrap(data: Uint8Array): Uint8Array {
    const method =
      (constants.window_info << constants.info_shift) |
      constants.deflate_method;
    const level = constants.fastest_level << constants.level_shift;
    const divisor = constants.check_divisor;
    const rest = (method * constants.byte_range + level) % divisor;
    const check = (divisor - rest) % divisor;
    return bytes_join([
      Uint8Array.from([method, level | check]),
      blocks_store(data),
      word_bytes(adler_compute(data)),
    ]);
  }

  // The base64 text of the bytes.
  function base64_encode(data: Uint8Array): string {
    let binary = "";
    for (const byte of data) {
      binary += String.fromCharCode(byte);
    }
    return btoa(binary);
  }

  // Whether the value is an object that is neither an array nor `null`.
  function fields_is(value: unknown): value is FieldTable {
    return (
      typeof value === "object" && value !== null && !Array.isArray(value)
    );
  }

  // Throws the error for a request field that is missing or not valid.
  function field_invalid(path: string): never {
    return utility.fail_now(i18n("provider_script.field_invalid", path));
  }

  // The object at the path of the request, or a throw when it is not one.
  function fields_read(value: unknown, path: string): FieldTable {
    if (!fields_is(value)) {
      return field_invalid(path);
    }
    return value;
  }

  // The node of the script by its name, or a throw when it has none.
  function node_get(script: Script, name: string): ScriptNode {
    if (!Object.hasOwn(script.nodes, name)) {
      throw new Error(i18n("provider_script.node_unknown", name));
    }
    return script.nodes[name];
  }

  // The body that answers an image request: the pattern as base64, `n` times.
  function image_answer(body: FieldTable): FieldTable {
    const format = body.response_format;
    if (format !== constants.image_format) {
      throw new Error(
        i18n("provider_script.format_unsupported", String(format)),
      );
    }
    const count = body.n;
    if (
      typeof count !== "number" ||
      !Number.isSafeInteger(count) ||
      count < 1
    ) {
      return field_invalid("json.n");
    }
    const text = base64_encode(image_pattern());
    const data: FieldTable[] = [];
    for (let made = 0; made < count; made += 1) {
      data.push({ b64_json: text });
    }
    return { data };
  }

  // The `tool_call_id` of each tool result that ends the messages, in order.
  function results_ids(messages: unknown[]): unknown[] {
    let start = messages.length;
    while (
      start > 0 &&
      fields_read(messages[start - 1], `json.messages[${start - 1}]`).role ===
        constants.tool_role
    ) {
      start -= 1;
    }
    return messages
      .slice(start)
      .map((message: unknown) => (message as FieldTable).tool_call_id);
  }

  // A port that answers each request from the script before its post returns.
  export class ScriptPort implements queue.Port {
    private readonly script: Script;
    private current: string;
    private pending: string | undefined;
    // The ids of the calls whose tool results are pending, in order.
    private pending_ids: string[] = [];
    private chats_answered = 0;
    private receiver: ((line: lines.Line) => void) | undefined;

    // Takes the script, whose start must name one of its nodes.
    constructor(script: Script) {
      node_get(script, script.start);
      this.script = script;
      this.current = script.start;
    }

    // Answers an `http.request` line through the receiver, before returning.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error(i18n("provider_script.receiver_missing"));
      }
      const header = line[0];
      const type = jslb.field_get(header, "type");
      if (type !== constants.request_type) {
        throw new Error(
          i18n("provider_script.type_invalid", type, constants.request_type),
        );
      }
      const id = jslb.field_get(header, "id");
      if (typeof id !== "number") {
        throw new Error(
          i18n("provider_script.id_missing", constants.request_type),
        );
      }
      if (jslb.headers_of(line).length > 1) {
        throw new Error(
          i18n("provider_script.blobs_refused", constants.request_type),
        );
      }
      const json = this.body_answer(jslb.payload_of(line));
      const reply_header = jslb.header_make(constants.request_type, {
        reply: id,
        full: Object.hasOwn(header, constants.full_key),
      });
      const reply = jslb.line_make(reply_header, [], {
        status: constants.status,
        headers: { [constants.content_key]: constants.json_media },
        json,
      });
      receiver(reply);
    }

    // Sets the one receiver of the reply lines.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiver !== undefined) {
        throw new Error(i18n("provider_script.receiver_twice"));
      }
      this.receiver = fn;
    }

    // The node the script is in, for assertions.
    node(): string {
      return this.current;
    }

    // The JSON body that answers the request, chosen by the path of its url.
    private body_answer(payload: FieldTable): FieldTable {
      if (payload.method !== constants.method) {
        return field_invalid("method");
      }
      const url = payload.url;
      if (typeof url !== "string") {
        return field_invalid("url");
      }
      if (url.endsWith(constants.chat_path)) {
        return this.chat_answer(fields_read(payload.json, "json"));
      }
      if (url.endsWith(constants.image_path)) {
        return image_answer(fields_read(payload.json, "json"));
      }
      throw new Error(i18n("provider_script.url_unknown", url));
    }

    // The body that answers a chat request, which moves the script on.
    private chat_answer(body: FieldTable): FieldTable {
      const model = body.model;
      if (typeof model !== "string") {
        return field_invalid("json.model");
      }
      const messages = body.messages;
      if (!Array.isArray(messages) || messages.length === 0) {
        return field_invalid("json.messages");
      }
      const index = messages.length - 1;
      const last = fields_read(messages[index], `json.messages[${index}]`);
      const reply = this.reply_choose(last, messages);
      const calls = reply.tool_calls ?? [];
      const message: FieldTable = {
        role: constants.assistant_role,
        content: reply.content,
      };
      if (calls.length > 0) {
        message.tool_calls = structuredClone(calls);
        this.pending = reply.next;
        this.pending_ids = calls.map((call) => call.id);
      } else {
        this.current = reply.next;
      }
      this.chats_answered += 1;
      const reason =
        calls.length > 0 ? constants.calls_reason : constants.stop_reason;
      return {
        id: `${constants.id_prefix}${this.chats_answered}`,
        model,
        choices: [{ index: 0, message, finish_reason: reason }],
      };
    }

    // The reply to the last message: after tool results, or for the input.
    private reply_choose(last: FieldTable, messages: unknown[]): ScriptReply {
      const role = last.role;
      const pending = this.pending;
      if (role === constants.tool_role) {
        if (pending === undefined) {
          throw new Error(
            i18n("provider_script.results_unasked", this.current),
          );
        }
        const answered = results_ids(messages);
        const asked = this.pending_ids;
        if (
          answered.length !== asked.length ||
          answered.some((id: unknown, index: number) => id !== asked[index])
        ) {
          throw new Error(
            i18n(
              "provider_script.results_unmatched",
              this.current,
              utility.json_text(answered),
              utility.json_text(asked),
            ),
          );
        }
        const after = node_get(this.script, pending).after_tools;
        if (after === undefined) {
          throw new Error(i18n("provider_script.after_missing", pending));
        }
        this.current = pending;
        this.pending = undefined;
        return after;
      }
      if (role !== constants.user_role) {
        throw new Error(i18n("provider_script.role_unexpected", String(role)));
      }
      if (pending !== undefined) {
        throw new Error(
          i18n("provider_script.results_pending", this.current, pending),
        );
      }
      const input = last.content;
      if (typeof input !== "string" || !constants.integer_text.test(input)) {
        throw new Error(i18n("provider_script.input_invalid", String(input)));
      }
      const replies = node_get(this.script, this.current).replies;
      if (!Object.hasOwn(replies, input)) {
        throw new Error(
          i18n("provider_script.input_unknown", this.current, input),
        );
      }
      return replies[input];
    }
  }

  // The PNG test pattern: a checkerboard with hard pixel edges, made anew.
  export function image_pattern(): Uint8Array {
    return bytes_join([
      Uint8Array.from(constants.png_signature),
      chunk_make(constants.header_kind, image_header()),
      chunk_make(constants.data_kind, stream_wrap(rows_draw())),
      chunk_make(constants.end_kind, new Uint8Array(0)),
    ]);
  }
}

Object.freeze(provider_script);
