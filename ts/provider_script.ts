// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The scripted provider, with no network and no AI: a synchronous port that
// answers the `http.request` lines of the provider door from one place in a
// table of nodes. A user message's text, its ends trimmed and its letters
// lowered, picks the reply its node's `replies` holds under that text, a
// number, a word or a phrase, else `otherwise`, else a refusal, as is a
// content that is no text; a key no input can match is refused when the
// port is made. The outputs of the last reply's calls take the `after_tools`
// of the node it names, or `after_lacks` when one lacks `after_holds`. A
// reply's `quote`, a path into the JSON of the last call output, says that
// string before its `content`. An image request gets a PNG test pattern built
// here from stored deflate blocks. Once it has chosen, it holds the request
// to xAI's rules and refuses the first bad field. It keeps each response
// under its id, unless `store` is false, for a chained request. Each reply
// holds a reasoning item and xAI's echoes; its ids carry the `SHA-256` of the
// cache key and context, its `usage` counts characters. In debug mode, by
// its reader, it takes `provider.tools_omitted` for tools.

namespace provider_script {
  // The line type, the request and reply parts, and the layout of the PNG.
  const constants = Object.freeze({
    request_type: "http.request",
    full_key: "type",
    method: "POST",
    model_path: "/responses",
    image_path: "/images/generations",
    image_format: "b64_json",
    status: 200,
    content_key: "content-type",
    json_media: "application/json",
    function_type: "function",
    key_header: "Authorization",
    key_start: "Bearer ",
    media_header: "Content-Type",
    url_start: "https://",
    // What a function's name may hold: OpenAI's rule, as xAI follows that API.
    tool_name: /^[a-zA-Z0-9_-]{1,64}$/,
    tools_max: 1000,
    tool_choices: Object.freeze(["auto", "none", "required"]),
    user_role: "user",
    assistant_role: "assistant",
    // The roles of an input message, an item with no type.
    input_roles: Object.freeze(["system", "user"]),
    reasoning_type: "reasoning",
    message_type: "message",
    call_type: "function_call",
    output_type: "function_call_output",
    text_type: "output_text",
    // The types of the model's items, a run of which starts with reasoning.
    model_types: Object.freeze(["reasoning", "message", "function_call"]),
    // The fields of a function call item, each text.
    call_fields: Object.freeze(["call_id", "name", "arguments"]),
    completed_status: "completed",
    response_object: "response",
    response_prefix: "resp_",
    reasoning_prefix: "rs_",
    message_prefix: "msg_",
    call_prefix: "fc_",
    // The hexadecimal digits of the digest that the ids carry.
    digest_digits: 16,
    // The encrypted reasoning of every reply, which a restart sends back.
    reasoning_text: "scripted",
    // The mark between the members of a quote's path.
    quote_separator: ".",
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

  // A call of the script, which the reply sends as a `function_call` item.
  export interface ScriptCall {
    call_id: string;
    name: string;
    arguments: string;
  }

  // One reply of the script and the node it leads to.
  export interface ScriptReply {
    // What the assistant says, null when it only calls tools or only quotes.
    content: string | null;
    // A path of members joined by `.` into the JSON of the last tool result.
    quote?: string;
    // The tools the reply calls, if any.
    tool_calls?: ScriptCall[];
    // The node to be in after this reply's tool results arrive.
    next: string;
  }

  // One node of the script: its replies by input and after tool results.
  export interface ScriptNode {
    // Replies by the text the user sent, its ends trimmed, in lower case.
    replies: { [input: string]: ScriptReply };
    // The reply to any other text the user sent.
    otherwise?: ScriptReply;
    // The reply after tool results, when the node was reached by tools.
    after_tools?: ScriptReply;
    // A text every tool result must hold for `after_tools` to follow.
    after_holds?: string;
    // The reply after tool results of which one lacks `after_holds`.
    after_lacks?: ScriptReply;
  }

  // A script: the node it starts in and every node by name.
  export interface Script {
    start: string;
    nodes: { [node: string]: ScriptNode };
  }

  // An object of unknown members, as a parsed JSON body holds them.
  type FieldTable = { [key: string]: unknown };

  // The reply chosen for a request, the node it was chosen in and its text.
  interface ChosenReply {
    reply: ScriptReply;
    node: string;
    // What the reply says, its quote resolved, or null for no message.
    text: string | null;
  }

  // The node the outputs of a reply's calls lead to, and the ids of the calls.
  interface PendingCalls {
    node: string;
    ids: string[];
  }

  // A response the port keeps: its context then its output, and its calls.
  interface HeldResponse {
    context: unknown[];
    calls: string[];
  }

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

  // The JSON text of a value with the keys of every object in it sorted.
  function canonical_text(value: unknown): string {
    if (Array.isArray(value)) {
      return `[${value.map(canonical_text).join(",")}]`;
    }
    if (fields_is(value)) {
      const fields = value;
      const members = Object.keys(fields)
        .sort()
        .map(
          (key) => `${utility.json_text(key)}:${canonical_text(fields[key])}`,
        );
      return `{${members.join(",")}}`;
    }
    return utility.json_text(value);
  }

  // The sum of the lengths of the texts, characters standing for tokens.
  function size_sum(texts: string[]): number {
    return texts.reduce((sum, text) => sum + text.length, 0);
  }

  // The first hexadecimal digits of the `SHA-256` of the key and context.
  function digest_make(key: string, context: unknown[]): string {
    const text = canonical_text([key, context]);
    const digest = utility.sha256_hex(utility.utf8_encode(text));
    return digest.slice(0, constants.digest_digits);
  }

  // The calls of a reply of the script, none when it names none.
  function reply_calls(reply: ScriptReply): ScriptCall[] {
    return reply.tool_calls ?? [];
  }

  // The normal form of a text, its ends trimmed and its letters lowered.
  function text_normal(text: string): string {
    return text.trim().toLowerCase();
  }

  // Refuses the first reply key, in the table's order, not in normal form.
  function keys_check(script: Script): void {
    for (const [name, node] of Object.entries(script.nodes)) {
      for (const key of Object.keys(node.replies)) {
        if (text_normal(key) !== key) {
          throw new Error(
            i18n("provider_script.key_unnormal", name, utility.json_text(key)),
          );
        }
      }
    }
  }

  // Refuses an address or a header that the real endpoint would refuse.
  function post_check(payload: FieldTable): void {
    if (!(payload.url as string).startsWith(constants.url_start)) {
      field_invalid("url");
    }
    const headers = fields_read(payload.headers, "headers");
    const key = headers[constants.key_header];
    if (
      typeof key !== "string" ||
      !key.startsWith(constants.key_start) ||
      key === constants.key_start
    ) {
      field_invalid(`headers.${constants.key_header}`);
    }
    if (headers[constants.media_header] !== constants.json_media) {
      field_invalid(`headers.${constants.media_header}`);
    }
  }

  // Refuses in debug mode all but the omission, else the first bad definition.
  function tools_check(tools: unknown, debug: boolean): void {
    if (tools === undefined) {
      return;
    }
    if (debug) {
      if (tools !== provider.tools_omitted) {
        field_invalid("json.tools");
      }
      return;
    }
    if (!Array.isArray(tools) || tools.length > constants.tools_max) {
      return field_invalid("json.tools");
    }
    tools.forEach((tool: unknown, index: number) => {
      const path = `json.tools[${index}]`;
      const fields = fields_read(tool, path);
      if (fields.type !== constants.function_type) {
        field_invalid(`${path}.type`);
      }
      const name = fields.name;
      if (typeof name !== "string" || !constants.tool_name.test(name)) {
        field_invalid(`${path}.name`);
      }
      if (typeof fields.description !== "string") {
        field_invalid(`${path}.description`);
      }
      fields_read(fields.parameters, `${path}.parameters`);
    });
  }

  // Refuses an input message, an item with no type, of another role or text.
  function message_check(item: FieldTable, path: string): void {
    if (!constants.input_roles.includes(item.role as string)) {
      field_invalid(`${path}.role`);
    }
    if (typeof item.content !== "string") {
      field_invalid(`${path}.content`);
    }
  }

  // Refuses a message item that is not the model's or holds a part not text.
  function reply_check(item: FieldTable, path: string): void {
    if (item.role !== constants.assistant_role) {
      field_invalid(`${path}.role`);
    }
    const content = item.content;
    if (!Array.isArray(content)) {
      return field_invalid(`${path}.content`);
    }
    content.forEach((value: unknown, index: number) => {
      const part_path = `${path}.content[${index}]`;
      const part = fields_read(value, part_path);
      if (part.type !== constants.text_type) {
        field_invalid(`${part_path}.type`);
      }
      if (typeof part.text !== "string") {
        field_invalid(`${part_path}.text`);
      }
    });
  }

  // Refuses a function call item whose id, name or arguments are not text.
  function call_check(item: FieldTable, path: string): void {
    for (const key of constants.call_fields) {
      if (typeof item[key] !== "string") {
        field_invalid(`${path}.${key}`);
      }
    }
  }

  // Refuses the first input item the real endpoint would refuse or miss by.
  function items_check(input: unknown[], due_start: string[]): void {
    const due = [...due_start];
    let made: string[] = [];
    let model_before = false;
    input.forEach((value: unknown, index: number) => {
      const path = `json.input[${index}]`;
      const item = fields_read(value, path);
      const type = item.type;
      const model = constants.model_types.includes(type as string);
      if (!model) {
        due.push(...made);
        made = [];
      }
      if (type === constants.output_type) {
        const asked = due.shift();
        if (asked === undefined || item.call_id !== asked) {
          field_invalid(`${path}.call_id`);
        }
        if (typeof item.output !== "string") {
          field_invalid(`${path}.output`);
        }
      } else if (due.length > 0) {
        field_invalid(`${path}.type`);
      } else if (model && !model_before && type !== constants.reasoning_type) {
        field_invalid(`${path}.type`);
      } else if (type === undefined) {
        message_check(item, path);
      } else if (type === constants.message_type) {
        reply_check(item, path);
      } else if (type === constants.call_type) {
        call_check(item, path);
        made.push(item.call_id as string);
      } else if (type !== constants.reasoning_type) {
        field_invalid(`${path}.type`);
      }
      model_before = model;
    });
    due.push(...made);
    if (due.length > 0) {
      field_invalid("json.input");
    }
  }

  // A reply's output: its reasoning, its message when it says one, its calls.
  function output_make(chosen: ChosenReply, digest: string): FieldTable[] {
    const output: FieldTable[] = [
      {
        type: constants.reasoning_type,
        id: `${constants.reasoning_prefix}${digest}`,
        summary: [],
        encrypted_content: constants.reasoning_text,
        status: constants.completed_status,
      },
    ];
    if (chosen.text !== null) {
      output.push({
        type: constants.message_type,
        id: `${constants.message_prefix}${digest}`,
        role: constants.assistant_role,
        status: constants.completed_status,
        content: [
          { type: constants.text_type, text: chosen.text, annotations: [] },
        ],
      });
    }
    reply_calls(chosen.reply).forEach((call: ScriptCall, index: number) => {
      output.push({
        type: constants.call_type,
        id: `${constants.call_prefix}${digest}_${index + 1}`,
        call_id: call.call_id,
        name: call.name,
        arguments: call.arguments,
        status: constants.completed_status,
      });
    });
    return output;
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
    if (typeof count !== "number" || !Number.isInteger(count) || count < 1) {
      return field_invalid("json.n");
    }
    const text = base64_encode(image_pattern());
    const data: FieldTable[] = [];
    for (let made = 0; made < count; made += 1) {
      data.push({ b64_json: text });
    }
    return { data };
  }

  // The index of the first of the call outputs that end the input.
  function results_start(input: unknown[]): number {
    let start = input.length;
    while (
      start > 0 &&
      fields_read(input[start - 1], `json.input[${start - 1}]`).type ===
        constants.output_type
    ) {
      start -= 1;
    }
    return start;
  }

  // The `call_id` of each call output that ends the input, in order.
  function results_ids(input: unknown[]): unknown[] {
    return input
      .slice(results_start(input))
      .map((item: unknown) => (item as FieldTable).call_id);
  }

  // The output text of each call output that ends the input, in order.
  function results_texts(input: unknown[]): string[] {
    const start = results_start(input);
    return input.slice(start).map((item: unknown, index: number) => {
      const text = (item as FieldTable).output;
      if (typeof text !== "string") {
        return field_invalid(`json.input[${start + index}].output`);
      }
      return text;
    });
  }

  // The reply that follows tool results in the node, by the text they hold.
  function after_read(
    node: ScriptNode,
    name: string,
    input: unknown[],
  ): ScriptReply {
    const { after_tools, after_holds, after_lacks } = node;
    if (after_tools === undefined) {
      throw new Error(i18n("provider_script.after_missing", name));
    }
    if (after_holds === undefined && after_lacks === undefined) {
      return after_tools;
    }
    if (after_holds === undefined || after_lacks === undefined) {
      throw new Error(i18n("provider_script.after_unpaired", name));
    }
    const held = results_texts(input).every((text) =>
      text.includes(after_holds),
    );
    return held ? after_tools : after_lacks;
  }

  // The reply of a node to a text in normal form, its own else `otherwise`.
  function input_reply(
    node: ScriptNode,
    name: string,
    text: string,
  ): ScriptReply {
    if (Object.hasOwn(node.replies, text)) {
      return node.replies[text];
    }
    if (node.otherwise !== undefined) {
      return node.otherwise;
    }
    throw new Error(i18n("provider_script.input_unknown", name, text));
  }

  // The value of a call output's JSON text, which a quote at the path reads.
  function quote_parse(text: string, node: string, path: string): unknown {
    try {
      return jslb.json_decode(text);
    } catch (error) {
      throw utility.error_wrap(
        i18n("provider_script.quote_missing", node, path),
        error,
      );
    }
  }

  // The text at the path of members in a call output's JSON, else a throw.
  function quote_read(text: string, node: string, path: string): string {
    let value: unknown = quote_parse(text, node, path);
    for (const member of path.split(constants.quote_separator)) {
      if (!fields_is(value) || !Object.hasOwn(value, member)) {
        throw new Error(i18n("provider_script.quote_missing", node, path));
      }
      value = value[member];
    }
    if (typeof value !== "string") {
      throw new Error(i18n("provider_script.quote_missing", node, path));
    }
    return value;
  }

  // The text a reply says: the quote of the last call output, then `content`.
  function reply_text(
    reply: ScriptReply,
    node: string,
    input: unknown[],
  ): string | null {
    const path = reply.quote;
    if (path === undefined) {
      return reply.content;
    }
    const texts = results_texts(input);
    const quoted = quote_read(texts[texts.length - 1], node, path);
    return reply.content === null ? quoted : `${quoted} ${reply.content}`;
  }

  // A port that answers each request from the script before its post returns.
  export class ScriptPort implements queue.Port {
    private readonly script: Script;
    // Whether debug mode is on, whose requests hold no tool list.
    private readonly debug: () => boolean;
    // The node the next user message is answered in.
    private current: string;
    // The calls of the last reply whose outputs are still to come.
    private pending: PendingCalls | undefined = undefined;
    // Each response by its id, but those whose request set `store` false.
    private readonly responses = new Map<string, HeldResponse>();
    // The canonical text of each item of a key's last context and output.
    private readonly caches = new Map<string, string[]>();
    private receiver: ((line: lines.Line) => void) | undefined;

    // Takes the script, its start a node and its keys normal, and the mode.
    constructor(script: Script, debug: () => boolean) {
      node_get(script, script.start);
      keys_check(script);
      this.script = script;
      this.debug = debug;
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

    // The JSON body that answers the request, chosen by the path of its url.
    private body_answer(payload: FieldTable): FieldTable {
      if (payload.method !== constants.method) {
        return field_invalid("method");
      }
      const url = payload.url;
      if (typeof url !== "string") {
        return field_invalid("url");
      }
      if (url.endsWith(constants.model_path)) {
        return this.model_answer(payload, fields_read(payload.json, "json"));
      }
      if (url.endsWith(constants.image_path)) {
        const body = fields_read(payload.json, "json");
        const answer = image_answer(body);
        post_check(payload);
        if (typeof body.model !== "string" || body.model === "") {
          field_invalid("json.model");
        }
        return answer;
      }
      throw new Error(i18n("provider_script.url_unknown", url));
    }

    // The body that answers a model request, which moves the script on.
    private model_answer(payload: FieldTable, body: FieldTable): FieldTable {
      const input = body.input;
      if (!Array.isArray(input) || input.length === 0) {
        return field_invalid("json.input");
      }
      const chosen = this.reply_choose(input);
      post_check(payload);
      const model = body.model;
      if (typeof model !== "string" || model === "") {
        return field_invalid("json.model");
      }
      tools_check(body.tools, this.debug());
      const choice = body.tool_choice;
      if (
        choice !== undefined &&
        !constants.tool_choices.includes(choice as string)
      ) {
        field_invalid("json.tool_choice");
      }
      const key = body.prompt_cache_key;
      if (typeof key !== "string" || key === "") {
        return field_invalid("json.prompt_cache_key");
      }
      const previous = body.previous_response_id;
      if (previous !== undefined && body.instructions !== undefined) {
        field_invalid("json.instructions");
      }
      const held = this.held_read(previous);
      const store = body.store;
      if (store !== undefined && typeof store !== "boolean") {
        field_invalid("json.store");
      }
      items_check(input, held === undefined ? [] : held.calls);
      const context =
        held === undefined ? [...input] : [...held.context, ...input];
      const digest = digest_make(key, context);
      const output = output_make(chosen, digest);
      const id = `${constants.response_prefix}${digest}`;
      const answer: FieldTable = {
        id,
        object: constants.response_object,
        model,
        status: constants.completed_status,
        output,
      };
      if (body.tools !== undefined) {
        answer.tools = structuredClone(body.tools);
      }
      if (choice !== undefined) {
        answer.tool_choice = choice;
      }
      answer.previous_response_id = previous === undefined ? null : previous;
      answer.usage = this.usage_make(key, context, output);
      if (store !== false) {
        this.responses.set(id, {
          context: structuredClone([...context, ...output]),
          calls: reply_calls(chosen.reply).map((call) => call.call_id),
        });
      }
      this.state_apply(chosen);
      return answer;
    }

    // The response a request chains from, `undefined` for a chain's first.
    private held_read(previous: unknown): HeldResponse | undefined {
      if (previous === undefined) {
        return undefined;
      }
      if (typeof previous !== "string" || !this.responses.has(previous)) {
        return field_invalid("json.previous_response_id");
      }
      return this.responses.get(previous);
    }

    // Characters for tokens, the cached the leading items held for the key.
    private usage_make(
      key: string,
      context: unknown[],
      output: FieldTable[],
    ): FieldTable {
      const texts = context.map(canonical_text);
      const outputs = output.map(canonical_text);
      const last = this.caches.get(key);
      let cached = 0;
      if (last !== undefined) {
        for (const [index, text] of texts.entries()) {
          if (text !== last[index]) {
            break;
          }
          cached += text.length;
        }
      }
      this.caches.set(key, [...texts, ...outputs]);
      const input_tokens = size_sum(texts);
      const output_tokens = size_sum(outputs);
      return {
        input_tokens,
        input_tokens_details: { cached_tokens: cached },
        output_tokens,
        // The reasoning item comes first in every output.
        output_tokens_details: { reasoning_tokens: outputs[0].length },
        total_tokens: input_tokens + output_tokens,
      };
    }

    // Moves the script on by the chosen reply, once the request is answered.
    private state_apply(chosen: ChosenReply): void {
      const calls = reply_calls(chosen.reply);
      this.current = chosen.node;
      if (calls.length > 0) {
        this.pending = {
          node: chosen.reply.next,
          ids: calls.map((call) => call.call_id),
        };
      } else {
        this.current = chosen.reply.next;
        this.pending = undefined;
      }
    }

    // The reply to the last input item: after call outputs, or for the input.
    private reply_choose(input: unknown[]): ChosenReply {
      const index = input.length - 1;
      const last = fields_read(input[index], `json.input[${index}]`);
      const pending = this.pending;
      if (last.type === constants.output_type) {
        if (pending === undefined) {
          throw new Error(
            i18n("provider_script.results_unasked", this.current),
          );
        }
        const answered = results_ids(input);
        const asked = pending.ids;
        if (
          answered.length !== asked.length ||
          answered.some((id: unknown, place: number) => id !== asked[place])
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
        const reached = node_get(this.script, pending.node);
        const after = after_read(reached, pending.node, input);
        const said = reply_text(after, pending.node, input);
        return { reply: after, node: pending.node, text: said };
      }
      if (last.type !== undefined || last.role !== constants.user_role) {
        throw new Error(
          i18n("provider_script.role_unexpected", utility.json_text(last)),
        );
      }
      if (pending !== undefined) {
        throw new Error(
          i18n("provider_script.results_pending", this.current, pending.node),
        );
      }
      const text = last.content;
      if (typeof text !== "string") {
        throw new Error(i18n("provider_script.input_invalid", String(text)));
      }
      const node = node_get(this.script, this.current);
      const reply = input_reply(node, this.current, text_normal(text));
      if (reply.quote !== undefined) {
        throw new Error(i18n("provider_script.quote_unreached", this.current));
      }
      return { reply, node: this.current, text: reply.content };
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
