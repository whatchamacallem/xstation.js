// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the scripted provider, the fake of xAI's Responses API: replies to
// a user message, after tool results, by `otherwise`, `after_holds` and
// `after_lacks`; a chained request, its context and due calls taken from the
// response it chains from; a restart with the whole context; `store` false;
// the output items and body fields of a reply; its `usage` in characters; its
// ids, whose digest each test computes at run time from a canonical text it
// writes literally; every refusal, in the order the port checks; the image
// answer; and the PNG test pattern held against a reference PNG of the same
// checkerboard in 88 bytes with other compressed data. The port is driven
// directly by `line_post` and `line_receive`. The request lines it posts, the
// reply lines, body orders and hand counted usages it expects and the texts
// of the refusals are its gold in `ts/test_setting_test_provider_script.json`,
// read through the harness.

namespace test_provider_script {
  // Models, ids, the tables' texts, the bounds of a tool, the PNG's layout.
  const constants = Object.freeze({
    image_model: "grok-2-image",
    other_key: "/metaverse/hyperposition/2",
    response_prefix: "resp_",
    digest_form: /^[0-9a-f]{16}$/,
    digest_digits: 16,
    reasoning_text: "scripted",
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone, " +
      "though not necessarily you.",
    otherwise_text: "That is not one of the choices.",
    nothing_text: "Nothing at all, then.",
    held_text: "hyperposition",
    seen_text: "It said hyperposition.",
    shut_text: "The console stayed shut.",
    retried_text: "Still nothing.",
    chain_said: "Looking.",
    chain_seen: "Seen.",
    chain_quiet: "Nothing.",
    tools_max: 1000,
    // What a debug mode request holds in place of its tool list.
    tools_omitted: "DEBUG_MODE_TOOL_LIST_OMITTED",
    name_max: 64,
    recorded_png:
      "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2" +
      "AAAAH0lEQVR42mP4jwQYkAAucYZBqGGQO48o" +
      "DaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg==",
    signature_bytes: 8,
    word_bytes: 4,
    word_bits: 32,
    byte_bits: 8,
    stream_head: 2,
    block_head: 5,
    check_divisor: 31,
    byte_range: 256,
    dictionary_flag: 0x20,
    length_mask: 0xffff,
    pattern_size: 16,
    square_size: 4,
    channel_count: 3,
    light_value: 255,
    dark_value: 0,
    crc_exponents: Object.freeze([
      26, 23, 22, 16, 12, 11, 10, 8, 7, 5, 4, 2, 1, 0,
    ]),
  });

  // Canonical texts of the cache keys and items, `{0}` their reply's digest.
  const canonical = Object.freeze({
    key: '"/metaverse/hyperposition/1"',
    other_key: '"/metaverse/hyperposition/2"',
    user_zero: '{"content":"0","role":"user"}',
    user_one: '{"content":"1","role":"user"}',
    user_two: '{"content":"2","role":"user"}',
    reasoning:
      '{"encrypted_content":"scripted","id":"rs_{0}","status":"completed",' +
      '"summary":[],"type":"reasoning"}',
    looking:
      '{"content":[{"annotations":[],"text":"Looking.",' +
      '"type":"output_text"}],"id":"msg_{0}","role":"assistant",' +
      '"status":"completed","type":"message"}',
    seen:
      '{"content":[{"annotations":[],"text":"Seen.",' +
      '"type":"output_text"}],"id":"msg_{0}","role":"assistant",' +
      '"status":"completed","type":"message"}',
    render:
      '{"arguments":"{}","call_id":"call_1","id":"fc_{0}_1",' +
      '"name":"browser_render","status":"completed","type":"function_call"}',
    done: '{"call_id":"call_1","output":"done","type":"function_call_output"}',
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // The usage of a reply, in characters.
  interface UsageBody {
    input_tokens: number;
    input_tokens_details: { cached_tokens: number };
    output_tokens: number;
    output_tokens_details: { reasoning_tokens: number };
    total_tokens: number;
  }

  // The body of a model reply, as the tests read it.
  interface ResponseBody {
    id: string;
    object: string;
    model: string;
    status: string;
    output: FieldTable[];
    tools?: unknown;
    tool_choice?: unknown;
    previous_response_id: string | null;
    usage: UsageBody;
  }

  // A port on the test script and the replies it has sent.
  interface ScriptBench {
    port: provider_script.ScriptPort;
    received: lines.Line[];
  }

  // One chunk of a PNG: its type, its bytes and the `CRC-32` stored after.
  interface PngChunk {
    kind: string;
    typed: Uint8Array;
    body: Uint8Array;
    crc: number;
    whole: Uint8Array;
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_provider_script.${name}`),
    );
  }

  // A text of this module's gold.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_provider_script.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The refusal of the request field at the path.
  function field_text(path: string): string {
    return i18n("provider_script.field_invalid", path);
  }

  // The bytes of a base64 text, as the platform's `atob` reads it.
  function base64_read(text: string): Uint8Array {
    return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
  }

  // The first hexadecimal digits of the `SHA-256` of a canonical text.
  function digest_expected(text: string): string {
    const digest = utility.sha256_hex(utility.utf8_encode(text));
    return digest.slice(0, constants.digest_digits);
  }

  // The canonical text of a cache key and a context, from their own texts.
  function context_text(key: string, items: string[]): string {
    return `[${key},[${items.join(",")}]]`;
  }

  // The canonical texts with the digest of their reply in place of `{0}`.
  function items_fill(texts: string[], digest: string): string[] {
    return texts.map((text) => text.replaceAll("{0}", digest));
  }

  // The sum of the lengths of the texts, characters standing for tokens.
  function sizes_sum(texts: string[]): number {
    return texts.reduce((sum, text) => sum + text.length, 0);
  }

  // The usage of a context's texts, its cached characters and its output's.
  function usage_expected(
    inputs: string[],
    cached: number,
    outputs: string[],
  ): UsageBody {
    const input_tokens = sizes_sum(inputs);
    const output_tokens = sizes_sum(outputs);
    return {
      input_tokens,
      input_tokens_details: { cached_tokens: cached },
      output_tokens,
      output_tokens_details: { reasoning_tokens: outputs[0].length },
      total_tokens: input_tokens + output_tokens,
    };
  }

  // The digest the ids of a reply carry, read from its response id.
  function digest_read(response: ResponseBody): string {
    return response.id.slice(constants.response_prefix.length);
  }

  // The reasoning item of every reply, its id of the reply's digest.
  function reasoning_expected(digest: string): FieldTable {
    return {
      type: "reasoning",
      id: `rs_${digest}`,
      summary: [],
      encrypted_content: constants.reasoning_text,
      status: "completed",
    };
  }

  // The message item of a reply that says the text.
  function message_expected(digest: string, text: string): FieldTable {
    return {
      type: "message",
      id: `msg_${digest}`,
      role: "assistant",
      status: "completed",
      content: [{ type: "output_text", text, annotations: [] }],
    };
  }

  // Sets the ids of a gold reply body, `{0}` standing for the digest.
  function ids_fill(json: FieldTable, digest: string): void {
    json.id = (json.id as string).replaceAll("{0}", digest);
    for (const item of json.output as FieldTable[]) {
      item.id = (item.id as string).replaceAll("{0}", digest);
    }
  }

  // A call of the named tool with the arguments as JSON text.
  function call_make(
    call_id: string,
    name: string,
    args: FieldTable,
  ): provider_script.ScriptCall {
    return { call_id, name, arguments: utility.json_text(args) };
  }

  // The test script: the castle turn and a reply for each other path.
  function script_make(): provider_script.Script {
    const bootstrap = call_make("call_1", "browser_script_run", {
      name: "bootstrap",
      args: { universe: "castle", world: "castle_world" },
    });
    const image = call_make("call_2", "browser_image_make", {
      prompt: "A rain dark castle gatehouse at dusk",
      key: "/_files/gatehouse/arrival.png",
    });
    const scene = call_make("call_3", "browser_doc_put", {
      db: "castle_gatehouse",
      id: "scene/arrival",
      body: { 0: { t: "scene" }, subtitle: constants.subtitle },
    });
    const enter = call_make("call_4", "browser_kv_put", {
      ref: "/castle_world/scene",
      text: "/castle_gatehouse/scene/arrival/1",
    });
    const render = call_make("call_5", "browser_render", {
      image: "/_files/gatehouse/arrival.png",
      subtitle: constants.subtitle,
    });
    const look = call_make("call_6", "browser_kv_get", {
      ref: "/metaverse/world",
    });
    return {
      start: "hyperposition",
      nodes: {
        hyperposition: {
          replies: {
            "1": { content: null, tool_calls: [bootstrap], next: "castle" },
            "2": { content: "Nothing happens.", next: "hyperposition" },
            "3": { content: null, tool_calls: [look], next: "bare" },
            "4": { content: "Gone.", next: "nowhere" },
            "5": { content: "To the gatehouse.", next: "gatehouse" },
            "6": { content: null, tool_calls: [look], next: "nowhere" },
          },
        },
        castle: {
          replies: {},
          after_tools: { content: null, tool_calls: [image], next: "imaged" },
        },
        imaged: {
          replies: {},
          after_tools: {
            content: null,
            tool_calls: [scene, enter, render],
            next: "entered",
          },
        },
        entered: {
          replies: {},
          after_tools: { content: constants.subtitle, next: "gatehouse" },
        },
        gatehouse: {
          replies: { "0": { content: "Still the moat.", next: "gatehouse" } },
        },
        bare: { replies: {} },
      },
    };
  }

  // A table as the seed's: `otherwise`, `after_holds` and `after_lacks`.
  function analyst_make(): provider_script.Script {
    const run = call_make("call_1", "browser_console_run", { text: "look" });
    const note = call_make("call_2", "browser_kv_get", {
      ref: "/metaverse/world",
    });
    const read = call_make("call_3", "browser_console_read", { until: "$ " });
    const { otherwise_text, nothing_text, seen_text, shut_text } = constants;
    return {
      start: "start",
      nodes: {
        start: {
          otherwise: { content: otherwise_text, next: "menu" },
          replies: { "0": { content: nothing_text, next: "menu" } },
        },
        menu: {
          otherwise: { content: otherwise_text, next: "menu" },
          replies: {
            "0": { content: nothing_text, next: "menu" },
            "1": { content: null, tool_calls: [run], next: "looked" },
            "2": { content: null, tool_calls: [run, note], next: "looked" },
            "3": { content: null, tool_calls: [run], next: "retried" },
            "4": { content: null, tool_calls: [run], next: "lone_holds" },
            "5": { content: null, tool_calls: [run], next: "lone_lacks" },
            "6": { content: "Ask away.", next: "asking" },
          },
        },
        asking: {
          otherwise: { content: null, tool_calls: [run], next: "looked" },
          replies: {},
        },
        looked: {
          after_holds: constants.held_text,
          after_lacks: { content: shut_text, next: "menu" },
          after_tools: { content: seen_text, next: "menu" },
          replies: {},
        },
        retried: {
          after_holds: constants.held_text,
          after_lacks: { content: null, tool_calls: [read], next: "given_up" },
          after_tools: { content: seen_text, next: "menu" },
          replies: {},
        },
        given_up: {
          after_tools: { content: constants.retried_text, next: "menu" },
          replies: {},
        },
        lone_holds: {
          after_holds: constants.held_text,
          after_tools: { content: seen_text, next: "menu" },
          replies: {},
        },
        lone_lacks: {
          after_lacks: { content: shut_text, next: "menu" },
          after_tools: { content: seen_text, next: "menu" },
          replies: {},
        },
      },
    };
  }

  // A table of one call whose reply also speaks, so that a chain is short.
  function chain_make(): provider_script.Script {
    const render: provider_script.ScriptCall = {
      call_id: "call_1",
      name: "browser_render",
      arguments: "{}",
    };
    return {
      start: "start",
      nodes: {
        start: {
          replies: {
            "0": { content: constants.chain_quiet, next: "start" },
            "1": {
              content: constants.chain_said,
              tool_calls: [render],
              next: "seen",
            },
          },
        },
        seen: {
          after_tools: { content: constants.chain_seen, next: "start" },
          replies: {},
        },
      },
    };
  }

  // A port on the script whose receiver keeps every reply, in the mode given.
  function bench_on(
    script: provider_script.Script,
    debug = false,
  ): ScriptBench {
    const port = new provider_script.ScriptPort(script, () => debug);
    const received: lines.Line[] = [];
    port.line_receive((line: lines.Line) => {
      received.push(line);
    });
    return { port, received };
  }

  // A port on a new test script whose receiver keeps every reply.
  function bench_make(): ScriptBench {
    return bench_on(script_make());
  }

  // A user message with the text.
  function user_say(text: string | null): FieldTable {
    return { role: "user", content: text };
  }

  // The output of the chain table's one call.
  function done_output(): FieldTable {
    return { type: "function_call_output", call_id: "call_1", output: "done" };
  }

  // A model request line of the gold, numbered, chained when an id is given.
  function model_line(
    input: unknown[],
    id: number,
    previous?: string,
  ): lines.Line {
    const line = gold_line("model_request");
    line[0].i = id;
    const body = line.json as FieldTable;
    body.input = [...input];
    if (previous !== undefined) {
      body.previous_response_id = previous;
    }
    return line;
  }

  // Posts the line and reads the body of the reply that came within the post.
  function line_answer(bench: ScriptBench, line: lines.Line): ResponseBody {
    const count = bench.received.length;
    bench.port.line_post(line, []);
    if (bench.received.length !== count + 1) {
      throw new Error("The scripted provider did not reply within the post.");
    }
    return bench.received[count].json as ResponseBody;
  }

  // Posts a model request of the input and reads the response that came.
  function model_post(
    bench: ScriptBench,
    input: unknown[],
    id: number,
    previous?: string,
  ): ResponseBody {
    return line_answer(bench, model_line(input, id, previous));
  }

  // The types of the output items of a response, in order.
  function types_of(response: ResponseBody): unknown[] {
    return response.output.map((item) => item.type);
  }

  // The calls of a response, as the script writes them.
  function calls_of(response: ResponseBody): provider_script.ScriptCall[] {
    return response.output
      .filter((item) => item.type === "function_call")
      .map((item) => ({
        call_id: item.call_id as string,
        name: item.name as string,
        arguments: item.arguments as string,
      }));
  }

  // The names of the tools a response calls, in order.
  function names_of(response: ResponseBody): string[] {
    return calls_of(response).map((call) => call.name);
  }

  // The texts of the parts of a response's messages, in order.
  function texts_of(response: ResponseBody): unknown[] {
    return response.output
      .filter((item) => item.type === "message")
      .flatMap((item) => (item.content as FieldTable[]).map((p) => p.text));
  }

  // The output of each call of a response, its text the one at its place.
  function outputs_give(
    response: ResponseBody,
    texts: unknown[],
  ): FieldTable[] {
    const calls = calls_of(response);
    if (calls.length !== texts.length) {
      throw new Error("The test gives one output text for each call.");
    }
    return calls.map((call, index) => ({
      type: "function_call_output",
      call_id: call.call_id,
      output: texts[index],
    }));
  }

  // The output `{}` of each call of a response.
  function outputs_make(response: ResponseBody): FieldTable[] {
    return outputs_give(
      response,
      calls_of(response).map(() => "{}"),
    );
  }

  // The response to the input, asked in the menu the reply to 0 leads to.
  function menu_ask(bench: ScriptBench, input: string): ResponseBody {
    const first = model_post(bench, [user_say("0")], 1);
    return model_post(bench, [user_say(input)], 2, first.id);
  }

  // An image request line numbered 1 whose body is the one given.
  function image_line(json: FieldTable): lines.Line {
    const line = gold_line("image_post");
    line.json = json;
    return line;
  }

  // The bytes of the reference PNG of the checkerboard.
  function recorded_get(): Uint8Array {
    return base64_read(constants.recorded_png);
  }

  // The chunks of a PNG after its signature, in order.
  function chunks_read(png: Uint8Array): PngChunk[] {
    const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
    const word = constants.word_bytes;
    const chunks: PngChunk[] = [];
    let offset: number = constants.signature_bytes;
    while (offset < png.length) {
      const length = view.getUint32(offset);
      const end = offset + 3 * word + length;
      const typed = png.subarray(offset + word, end - word);
      chunks.push({
        kind: new TextDecoder("utf-8", { fatal: true }).decode(
          typed.subarray(0, word),
        ),
        typed,
        body: typed.subarray(word),
        crc: view.getUint32(end - word),
        whole: png.subarray(offset, end),
      });
      offset = end;
    }
    return chunks;
  }

  // The types of the chunks of a PNG, in order.
  function kinds_of(png: Uint8Array): string[] {
    return chunks_read(png).map((chunk) => chunk.kind);
  }

  // The one chunk of the type in a PNG, which must be there.
  function chunk_find(png: Uint8Array, kind: string): PngChunk {
    const found = chunks_read(png).find((chunk) => chunk.kind === kind);
    if (found === undefined) {
      throw new Error(`The PNG has no ${kind} chunk.`);
    }
    return found;
  }

  // The `CRC-32` of the bytes a bit at a time, its polynomial from exponents.
  function crc_reference(data: Uint8Array): number {
    let polynomial = 0;
    for (const exponent of constants.crc_exponents) {
      polynomial |= 1 << (constants.word_bits - 1 - exponent);
    }
    let crc = ~0;
    for (const byte of data) {
      crc ^= byte;
      for (let bit = 0; bit < constants.byte_bits; bit += 1) {
        crc = (crc & 1) !== 0 ? (crc >>> 1) ^ polynomial : crc >>> 1;
      }
    }
    return ~crc >>> 0;
  }

  // The rows of the checkerboard, 16 by 16 pixels in squares of 4.
  function rows_expected(): Uint8Array {
    const { pattern_size, square_size, channel_count } = constants;
    const bytes: number[] = [];
    for (let y = 0; y < pattern_size; y += 1) {
      bytes.push(0);
      for (let x = 0; x < pattern_size; x += 1) {
        const squares =
          Math.floor(x / square_size) + Math.floor(y / square_size);
        const light = squares % 2 === 0;
        for (let channel = 0; channel < channel_count; channel += 1) {
          bytes.push(light ? constants.light_value : constants.dark_value);
        }
      }
    }
    return Uint8Array.from(bytes);
  }

  // The walk of a script and the reply lines that carry it.
  export class TestScriptWalk extends unittest.TestCase {
    // The castle turn, chained: three rounds of calls, then the subtitle.
    test_turn_walk(): void {
      const bench = bench_make();
      const script = script_make();
      const first = model_post(bench, [user_say("1")], 1);
      this.assertEqual(types_of(first), ["reasoning", "function_call"]);
      this.assertEqual(
        calls_of(first),
        script.nodes.hyperposition.replies["1"].tool_calls,
      );
      const second = model_post(bench, outputs_make(first), 2, first.id);
      this.assertEqual(names_of(second), ["browser_image_make"]);
      const third = model_post(bench, outputs_make(second), 3, second.id);
      this.assertEqual(names_of(third), [
        "browser_doc_put",
        "browser_kv_put",
        "browser_render",
      ]);
      const last = model_post(bench, outputs_make(third), 4, third.id);
      this.assertEqual(types_of(last), ["reasoning", "message"]);
      this.assertEqual(texts_of(last), [constants.subtitle]);
      const next = model_post(bench, [user_say("0")], 5, last.id);
      this.assertEqual(texts_of(next), ["Still the moat."]);
    }

    // The reply comes inside the post, whole as the gold has it.
    test_reply_line(): void {
      const bench = bench_make();
      bench.port.line_post(model_line([user_say("2")], 7), []);
      this.assertEqual(bench.received.length, 1);
      const reply = bench.received[0];
      this.assertEqual(Object.keys(reply), ["0", "status", "headers", "json"]);
      const json = reply.json as FieldTable;
      this.assertEqual(Object.keys(json), gold_value("orders.reply"));
      const expected = gold_line("reply_nothing");
      const text = context_text(canonical.key, [canonical.user_two]);
      ids_fill(expected.json as FieldTable, digest_expected(text));
      this.assertEqual(reply, expected);
    }

    // A request in full names is answered in full names.
    test_full_names(): void {
      const bench = bench_make();
      bench.port.line_post(gold_line("model_full"), []);
      this.assertEqual(bench.received[0][0], gold_line("reply_full")[0]);
    }

    // A reply that only calls has no message, and its calls are numbered.
    test_calls_numbered(): void {
      const bench = bench_make();
      const first = model_post(bench, [user_say("1")], 1);
      const second = model_post(bench, outputs_make(first), 2, first.id);
      const third = model_post(bench, outputs_make(second), 3, second.id);
      const digest = digest_read(third);
      this.assertEqual(
        third.output.map((item) => item.id),
        [`rs_${digest}`, `fc_${digest}_1`, `fc_${digest}_2`, `fc_${digest}_3`],
      );
    }

    // A reply that speaks and calls holds its reasoning, message and call.
    test_output_items(): void {
      const text = context_text(canonical.key, [canonical.user_one]);
      const digest = digest_expected(text);
      const response = model_post(bench_on(chain_make()), [user_say("1")], 1);
      this.assertEqual(response.id, `resp_${digest}`);
      this.assertEqual(response.output, [
        reasoning_expected(digest),
        message_expected(digest, constants.chain_said),
        {
          type: "function_call",
          id: `fc_${digest}_1`,
          call_id: "call_1",
          name: "browser_render",
          arguments: "{}",
          status: "completed",
        },
      ]);
    }

    // The body echoes `tools` and `tool_choice` when given, and the model.
    test_echoes_kept(): void {
      const bench = bench_on(chain_make());
      const tools = [
        {
          type: "function",
          name: "browser_render",
          description: "Show an image and a subtitle.",
          parameters: { type: "object" },
        },
      ];
      const line = model_line([user_say("1")], 1);
      const body = line.json as FieldTable;
      body.model = "grok-x";
      body.tools = tools;
      body.tool_choice = "required";
      const first = line_answer(bench, line);
      this.assertEqual(Object.keys(first), gold_value("orders.reply_tools"));
      this.assertEqual(first.object, "response");
      this.assertEqual(first.model, "grok-x");
      this.assertEqual(first.status, "completed");
      this.assertEqual(first.tools, tools);
      this.assertFalse(first.tools === tools);
      this.assertEqual(first.tool_choice, "required");
      this.assertEqual(first.previous_response_id, null);
      const bare = model_line([done_output()], 2, first.id);
      delete (bare.json as FieldTable).tool_choice;
      const second = line_answer(bench, bare);
      this.assertEqual(Object.keys(second), gold_value("orders.reply_bare"));
      this.assertEqual(second.previous_response_id, first.id);
    }

    // A reply without calls moves to its next node at once.
    test_stop_moves(): void {
      const bench = bench_make();
      const moved = model_post(bench, [user_say("5")], 1);
      this.assertEqual(texts_of(moved), ["To the gatehouse."]);
      this.assertEqual(types_of(moved), ["reasoning", "message"]);
      const next = model_post(bench, [user_say("0")], 2, moved.id);
      this.assertEqual(texts_of(next), ["Still the moat."]);
    }

    // The port keeps one place for every chain, so a new chain goes on there.
    test_place_shared(): void {
      const bench = bench_make();
      model_post(bench, [user_say("5")], 1);
      const fresh = model_post(bench, [user_say("0")], 2);
      this.assertEqual(texts_of(fresh), ["Still the moat."]);
      this.assertEqual(fresh.previous_response_id, null);
    }
  }

  // The ids, arithmetic on the cache key and the context.
  export class TestScriptIds extends unittest.TestCase {
    // One request to two new ports is answered alike, ids included.
    test_ids_repeated(): void {
      const first = model_post(bench_on(chain_make()), [user_say("1")], 1);
      const second = model_post(bench_on(chain_make()), [user_say("1")], 1);
      this.assertEqual(first, second);
      this.assertTrue(constants.digest_form.test(digest_read(first)));
    }

    // Another context, or one context under another key, has another digest.
    test_ids_differ(): void {
      const zero = model_post(bench_on(chain_make()), [user_say("0")], 1);
      const one = model_post(bench_on(chain_make()), [user_say("1")], 1);
      const line = model_line([user_say("0")], 1);
      (line.json as FieldTable).prompt_cache_key = constants.other_key;
      const other = line_answer(bench_on(chain_make()), line);
      const digests = [zero, one, other].map(digest_read);
      this.assertEqual(digests, [
        digest_expected(context_text(canonical.key, [canonical.user_zero])),
        digest_expected(context_text(canonical.key, [canonical.user_one])),
        digest_expected(
          context_text(canonical.other_key, [canonical.user_zero]),
        ),
      ]);
      this.assertEqual(new Set(digests).size, 3);
    }
  }

  // A chain of responses by `previous_response_id`, and its restart.
  export class TestScriptChain extends unittest.TestCase {
    // A chained request's context is its response's context, output and input.
    test_chain_context(): void {
      const bench = bench_on(chain_make());
      const first = model_post(bench, [user_say("1")], 1);
      const second = model_post(bench, [done_output()], 2, first.id);
      const held = items_fill(
        [
          canonical.user_one,
          canonical.reasoning,
          canonical.looking,
          canonical.render,
        ],
        digest_read(first),
      );
      const text = context_text(canonical.key, [...held, canonical.done]);
      const digest = digest_expected(text);
      this.assertEqual(second.id, `resp_${digest}`);
      this.assertEqual(second.previous_response_id, first.id);
      this.assertEqual(second.output, [
        reasoning_expected(digest),
        message_expected(digest, constants.chain_seen),
      ]);
    }

    // A restart of the whole context with no chain is answered as the chain.
    test_restart_whole(): void {
      const chained = bench_on(chain_make());
      const first = model_post(chained, [user_say("1")], 1);
      const second = model_post(chained, [done_output()], 2, first.id);
      const restarted = bench_on(chain_make());
      const again = model_post(restarted, [user_say("1")], 1);
      const input = [user_say("1"), ...again.output, done_output()];
      const whole = model_post(restarted, input, 2);
      this.assertEqual(whole.previous_response_id, null);
      this.assertEqual(whole.id, second.id);
      this.assertEqual(whole.output, second.output);
      this.assertEqual(whole.usage, second.usage);
    }

    // The calls due at a chained request's start are its response's calls.
    test_due_seeded(): void {
      const bench = bench_make();
      const quiet = model_post(bench, [user_say("2")], 1);
      const asked = model_post(bench, [user_say("1")], 2);
      const outputs = outputs_make(asked);
      const error = thrown_get(() => model_post(bench, outputs, 3, quiet.id));
      this.assertEqual(error.message, field_text("json.input[0].call_id"));
      const answered = model_post(bench, outputs, 4, asked.id);
      this.assertEqual(names_of(answered), ["browser_image_make"]);
    }

    // A chain's first request has no call due, so an output answers none.
    test_first_undue(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("1")], 1);
      const error = thrown_get(() =>
        model_post(bench, outputs_make(asked), 2),
      );
      this.assertEqual(error.message, field_text("json.input[0].call_id"));
    }

    // A response another port answered is not held by this one.
    test_chain_foreign(): void {
      const other = model_post(bench_make(), [user_say("2")], 1);
      const error = thrown_get(() =>
        model_post(bench_make(), [user_say("2")], 1, other.id),
      );
      this.assertEqual(error.message, field_text("json.previous_response_id"));
    }

    // With `store` false no chain follows, but the key's cache is kept.
    test_store_false(): void {
      const bench = bench_on(chain_make());
      const line = model_line([user_say("1")], 1);
      (line.json as FieldTable).store = false;
      const first = line_answer(bench, line);
      const error = thrown_get(() =>
        model_post(bench, [done_output()], 2, first.id),
      );
      this.assertEqual(error.message, field_text("json.previous_response_id"));
      const input = [user_say("1"), ...first.output, done_output()];
      const whole = model_post(bench, input, 3);
      const held = items_fill(
        [
          canonical.user_one,
          canonical.reasoning,
          canonical.looking,
          canonical.render,
        ],
        digest_read(first),
      );
      this.assertEqual(
        whole.usage.input_tokens_details.cached_tokens,
        sizes_sum(held),
      );
    }

    // With `store` true the response is held, as with no `store`.
    test_store_true(): void {
      const bench = bench_on(chain_make());
      const line = model_line([user_say("1")], 1);
      (line.json as FieldTable).store = true;
      const first = line_answer(bench, line);
      const second = model_post(bench, [done_output()], 2, first.id);
      this.assertEqual(texts_of(second), [constants.chain_seen]);
    }

    // `instructions` is refused beside a chain only, and taken alone.
    test_instructions_alone(): void {
      const bench = bench_make();
      const line = model_line([user_say("2")], 1);
      (line.json as FieldTable).instructions = "Be brief.";
      const response = line_answer(bench, line);
      this.assertEqual(texts_of(response), ["Nothing happens."]);
    }
  }

  // The usage of a reply, arithmetic in characters on the context.
  export class TestScriptUsage extends unittest.TestCase {
    // A chain's first request counts its input and output, nothing cached.
    test_usage_first(): void {
      const response = model_post(bench_on(chain_make()), [user_say("1")], 1);
      const output = items_fill(
        [canonical.reasoning, canonical.looking, canonical.render],
        digest_read(response),
      );
      const usage = usage_expected([canonical.user_one], 0, output);
      this.assertEqual(response.usage, usage);
      this.assertEqual(response.usage, gold_value("usages.first"));
    }

    // A chained request counts the whole context, the key's last one cached.
    test_usage_chained(): void {
      const bench = bench_on(chain_make());
      const first = model_post(bench, [user_say("1")], 1);
      const second = model_post(bench, [done_output()], 2, first.id);
      const held = items_fill(
        [
          canonical.user_one,
          canonical.reasoning,
          canonical.looking,
          canonical.render,
        ],
        digest_read(first),
      );
      const output = items_fill(
        [canonical.reasoning, canonical.seen],
        digest_read(second),
      );
      const usage = usage_expected(
        [...held, canonical.done],
        sizes_sum(held),
        output,
      );
      this.assertEqual(second.usage, usage);
      this.assertEqual(second.usage, gold_value("usages.chained"));
    }

    // The cache is the key's: another key caches nothing of the first.
    test_cache_keyed(): void {
      const bench = bench_on(chain_make());
      model_post(bench, [user_say("0")], 1);
      const line = model_line([user_say("0")], 2);
      (line.json as FieldTable).prompt_cache_key = constants.other_key;
      const other = line_answer(bench, line);
      this.assertEqual(other.usage.input_tokens_details.cached_tokens, 0);
      const again = model_post(bench, [user_say("0")], 3);
      this.assertEqual(
        again.usage.input_tokens_details.cached_tokens,
        canonical.user_zero.length,
      );
    }
  }

  // The faults of a script and of the lines it is given.
  export class TestScriptFaults extends unittest.TestCase {
    // A script whose start names no node is refused when the port is made.
    test_start_unknown(): void {
      const error = thrown_get(
        () =>
          new provider_script.ScriptPort(
            { start: "nowhere", nodes: {} },
            () => false,
          ),
      );
      this.assertEqual(
        error.message,
        gold_text("provider_script_node_unknown"),
      );
    }

    // A reply that leads to no node is refused at the next request.
    test_next_unknown(): void {
      const bench = bench_make();
      const gone = model_post(bench, [user_say("4")], 1);
      this.assertEqual(texts_of(gone), ["Gone."]);
      const error = thrown_get(() =>
        model_post(bench, [user_say("1")], 2, gone.id),
      );
      this.assertEqual(
        error.message,
        gold_text("provider_script_node_unknown"),
      );
    }

    // Results that lead to no node are refused when they come.
    test_after_unknown(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("6")], 1);
      const error = thrown_get(() =>
        model_post(bench, outputs_make(asked), 2, asked.id),
      );
      this.assertEqual(
        error.message,
        gold_text("provider_script_node_unknown"),
      );
    }

    // With no `otherwise`, a content that is no decimal integer is refused.
    test_input_invalid(): void {
      const bench = bench_make();
      const cases: [string | null, string][] = [
        ["one", "word"],
        ["01", "zero_led"],
        ["1.0", "fraction"],
        [" 1", "space_before"],
        ["1 ", "space_after"],
        ["+1", "plus"],
        ["-0", "minus_zero"],
        ["", "empty"],
        [null, "null"],
      ];
      for (const [text, suffix] of cases) {
        const error = thrown_get(() => model_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_input_invalid_${suffix}`),
        );
      }
      this.assertEqual(bench.received.length, 0);
    }

    // With no `otherwise`, an integer the node has no reply for is refused.
    test_input_unknown(): void {
      const bench = bench_make();
      const cases: [string, string][] = [
        ["0", "zero"],
        ["9", "nine"],
        ["-5", "minus_five"],
      ];
      for (const [text, suffix] of cases) {
        const error = thrown_get(() => model_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_input_unknown_${suffix}`),
        );
      }
    }

    // Tool results after a reply that called no tool are refused.
    test_results_unasked(): void {
      const bench = bench_make();
      const input = [
        user_say("2"),
        { type: "function_call_output", call_id: "call_1", output: "{}" },
      ];
      const error = thrown_get(() => model_post(bench, input, 1));
      this.assertEqual(
        error.message,
        gold_text("provider_script_results_unasked"),
      );
    }

    // A user message while tool results are pending is refused.
    test_results_pending(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("1")], 1);
      const error = thrown_get(() =>
        model_post(bench, [user_say("2")], 2, asked.id),
      );
      this.assertEqual(
        error.message,
        gold_text("provider_script_results_pending"),
      );
    }

    // Tool results whose call ids are not the calls of the reply are refused.
    test_results_unmatched(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("1")], 1);
      const cases: [string[], string][] = [
        [["call_9"], "other"],
        [["call_1", "call_1"], "twice"],
      ];
      for (const [ids, suffix] of cases) {
        const outputs = ids.map((call_id) => ({
          type: "function_call_output",
          call_id,
          output: "{}",
        }));
        const error = thrown_get(() =>
          model_post(bench, outputs, 2, asked.id),
        );
        this.assertEqual(
          error.message,
          gold_text(`provider_script_results_unmatched_${suffix}`),
        );
      }
      this.assertEqual(bench.received.length, 1);
    }

    // Tool results that lead to a node with no reply after them are refused.
    test_after_missing(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("3")], 1);
      const error = thrown_get(() =>
        model_post(bench, outputs_make(asked), 2, asked.id),
      );
      this.assertEqual(
        error.message,
        gold_text("provider_script_after_missing"),
      );
    }

    // A last item that is neither a user message nor a result is refused.
    test_role_unexpected(): void {
      const bench = bench_make();
      const cases: [FieldTable, string][] = [
        [{ role: "assistant", content: "Hello." }, "assistant"],
        [{ role: "system", content: "Hello." }, "system"],
        [
          {
            type: "function_call",
            call_id: "call_1",
            name: "browser_render",
            arguments: "{}",
          },
          "call",
        ],
      ];
      for (const [item, suffix] of cases) {
        const error = thrown_get(() => model_post(bench, [item], 1));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_role_unexpected_${suffix}`),
        );
      }
    }

    // A port with no receiver, or given a second one, refuses it.
    test_receiver_rules(): void {
      const port = new provider_script.ScriptPort(script_make(), () => false);
      const request = model_line([user_say("2")], 1);
      const missing = thrown_get(() => port.line_post(request, []));
      this.assertEqual(
        missing.message,
        gold_text("provider_script_receiver_missing"),
      );
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(
        twice.message,
        gold_text("provider_script_receiver_twice"),
      );
    }

    // A line it cannot read is refused before the script chooses, in order.
    test_line_refused(): void {
      const bench = bench_make();
      const blobs = gold_line("refused_blobs");
      (blobs[1] as lines.BlobHeader).d = new Uint8Array(1);
      const cases: [lines.Line, string][] = [
        [gold_line("refused_type"), "provider_script_type_invalid"],
        [gold_line("refused_id"), "provider_script_id_missing"],
        [blobs, "provider_script_blobs_refused"],
        [gold_line("refused_method"), "provider_script_field_invalid_method"],
        [gold_line("refused_url"), "provider_script_field_invalid_url"],
        [gold_line("refused_unknown"), "provider_script_url_unknown"],
        [gold_line("refused_json"), "provider_script_field_invalid_json"],
        [gold_line("refused_input"), "provider_script_field_invalid_input"],
        [gold_line("refused_empty"), "provider_script_field_invalid_input"],
        [gold_line("refused_item"), "provider_script_field_invalid_item"],
      ];
      for (const [line, name] of cases) {
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(error.message, gold_text(name));
      }
      this.assertEqual(bench.received.length, 0);
    }
  }

  // The reply to a text the node does not hold, and what it does not cover.
  export class TestScriptOtherwise extends unittest.TestCase {
    // Every text `replies` lacks gets `otherwise`, the click's words included.
    test_otherwise_answers(): void {
      const texts = [
        "one",
        "",
        " 1",
        "01",
        "-0",
        "1.0",
        "9",
        "-5",
        i18n("agent.click_text", 2, -1),
      ];
      for (const text of texts) {
        const bench = bench_on(analyst_make());
        const response = model_post(bench, [user_say(text)], 1);
        this.assertEqual(types_of(response), ["reasoning", "message"]);
        this.assertEqual(texts_of(response), [constants.otherwise_text]);
      }
    }

    // `otherwise` moves to its next node, where the choices then answer.
    test_otherwise_moves(): void {
      const bench = bench_on(analyst_make());
      const first = model_post(bench, [user_say("word")], 1);
      const second = model_post(bench, [user_say("1")], 2, first.id);
      this.assertEqual(names_of(second), ["browser_console_run"]);
    }

    // An input the node holds takes its own reply, not `otherwise`.
    test_replies_first(): void {
      const bench = bench_on(analyst_make());
      const response = model_post(bench, [user_say("0")], 1);
      this.assertEqual(texts_of(response), [constants.nothing_text]);
    }

    // An `otherwise` that calls tools moves on once their results are back.
    test_otherwise_calls(): void {
      const bench = bench_on(analyst_make());
      const asked = menu_ask(bench, "6");
      const called = model_post(bench, [user_say("word")], 3, asked.id);
      this.assertEqual(names_of(called), ["browser_console_run"]);
      const results = outputs_give(called, [constants.held_text]);
      const last = model_post(bench, results, 4, called.id);
      this.assertEqual(texts_of(last), [constants.seen_text]);
    }

    // A content that is not a string is refused with `otherwise` in the node.
    test_content_refused(): void {
      const bench = bench_on(analyst_make());
      const error = thrown_get(() => model_post(bench, [user_say(null)], 1));
      this.assertEqual(
        error.message,
        gold_text("provider_script_input_invalid_null"),
      );
      this.assertEqual(bench.received.length, 0);
    }
  }

  // The reply after tool results, by the text the results hold.
  export class TestScriptAfter extends unittest.TestCase {
    // Results that each hold the text are followed by `after_tools`.
    test_holds_followed(): void {
      const bench = bench_on(analyst_make());
      const asked = menu_ask(bench, "2");
      const output = `{"output":"${constants.held_text}\\n"}`;
      const results = outputs_give(asked, [output, constants.held_text]);
      const response = model_post(bench, results, 3, asked.id);
      this.assertEqual(texts_of(response), [constants.seen_text]);
    }

    // One result of the reply that lacks the text gives `after_lacks`.
    test_lacks_followed(): void {
      const { held_text } = constants;
      const cases = [
        ["denied", held_text],
        [held_text, "denied"],
        ["", ""],
      ];
      for (const texts of cases) {
        const bench = bench_on(analyst_make());
        const asked = menu_ask(bench, "2");
        const results = outputs_give(asked, texts);
        const response = model_post(bench, results, 3, asked.id);
        this.assertEqual(texts_of(response), [constants.shut_text]);
      }
    }

    // `after_lacks` moves to its next node as `after_tools` does.
    test_lacks_moves(): void {
      const bench = bench_on(analyst_make());
      const asked = menu_ask(bench, "1");
      const results = outputs_give(asked, ["denied"]);
      const shut = model_post(bench, results, 3, asked.id);
      const next = model_post(bench, [user_say("0")], 4, shut.id);
      this.assertEqual(texts_of(next), [constants.nothing_text]);
    }

    // The calls of `after_lacks` wait for their results, as any reply's do.
    test_lacks_calls(): void {
      const bench = bench_on(analyst_make());
      const asked = menu_ask(bench, "3");
      const results = outputs_give(asked, ["denied"]);
      const retried = model_post(bench, results, 3, asked.id);
      this.assertEqual(names_of(retried), ["browser_console_read"]);
      this.assertEqual(types_of(retried), ["reasoning", "function_call"]);
      const last = model_post(bench, outputs_make(retried), 4, retried.id);
      this.assertEqual(texts_of(last), [constants.retried_text]);
    }

    // A node with one of `after_holds` and `after_lacks` is a broken table.
    test_after_unpaired(): void {
      const cases: [string, string][] = [
        ["4", "holds"],
        ["5", "lacks"],
      ];
      for (const [input, suffix] of cases) {
        const bench = bench_on(analyst_make());
        const asked = menu_ask(bench, input);
        const results = outputs_give(asked, [constants.held_text]);
        const error = thrown_get(() =>
          model_post(bench, results, 3, asked.id),
        );
        this.assertEqual(
          error.message,
          gold_text(`provider_script_after_unpaired_${suffix}`),
        );
      }
    }

    // A tool result whose output is not text cannot be read for the text.
    test_result_refused(): void {
      const bench = bench_on(analyst_make());
      const asked = menu_ask(bench, "1");
      const results = outputs_give(asked, [5]);
      const error = thrown_get(() => model_post(bench, results, 3, asked.id));
      this.assertEqual(error.message, field_text("json.input[0].output"));
    }
  }

  // A request the port answers from its table, then held to xAI's rules.
  export class TestRequestChecks extends unittest.TestCase {
    // Each row of the gold breaks a good request, its first break named.
    test_each_refused(): void {
      const rows = gold_value("bad_requests") as FieldTable[];
      for (const row of rows) {
        const bench = bench_make();
        const line = model_line([user_say("2")], 1);
        const body = line.json as FieldTable;
        if (Object.hasOwn(row, "headers")) {
          Object.assign(line.headers as FieldTable, row.headers);
        }
        if (Object.hasOwn(row, "line")) {
          Object.assign(line, row.line);
        }
        if (Object.hasOwn(row, "body")) {
          Object.assign(body, row.body);
        }
        if (Object.hasOwn(row, "absent")) {
          for (const key of row.absent as string[]) {
            delete body[key];
          }
        }
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(
          error.message,
          field_text(row.path as string),
          utility.json_text(row),
        );
      }
    }

    // The script chooses first, so its refusal comes before a bad field's.
    test_choice_first(): void {
      const bench = bench_make();
      const line = model_line([user_say("9")], 1);
      line.url = "http://api.x.ai/v1/responses";
      (line.json as FieldTable).model = "";
      const error = thrown_get(() => bench.port.line_post(line, []));
      this.assertEqual(
        error.message,
        gold_text("provider_script_input_unknown_nine"),
      );
    }

    // A request of 1000 tools is taken, and one of 1001 refused.
    test_tools_bounded(): void {
      const tool = {
        type: "function",
        name: "browser_render",
        description: "Show an image and a subtitle.",
        parameters: { type: "object" },
      };
      const bench = bench_make();
      const line = model_line([user_say("2")], 1);
      const most = constants.tools_max;
      (line.json as FieldTable).tools = new Array(most).fill(tool);
      const answered = line_answer(bench, line);
      this.assertEqual((answered.tools as unknown[]).length, most);
      const over = model_line([user_say("2")], 2);
      (over.json as FieldTable).tools = new Array(most + 1).fill(tool);
      const error = thrown_get(() => bench.port.line_post(over, []));
      this.assertEqual(error.message, field_text("json.tools"));
    }

    // In debug mode the omission's text is taken and echoed, a list refused.
    test_tools_omitted(): void {
      const bench = bench_on(script_make(), true);
      const line = model_line([user_say("2")], 1);
      (line.json as FieldTable).tools = constants.tools_omitted;
      const answered = line_answer(bench, line);
      this.assertEqual(answered.tools, constants.tools_omitted);
      const listed = model_line([user_say("2")], 2);
      (listed.json as FieldTable).tools = [];
      const error = thrown_get(() => bench.port.line_post(listed, []));
      this.assertEqual(error.message, field_text("json.tools"));
    }

    // Outside debug mode the omission's text is refused, as xAI would.
    test_omission_refused(): void {
      const bench = bench_make();
      const line = model_line([user_say("2")], 1);
      (line.json as FieldTable).tools = constants.tools_omitted;
      const error = thrown_get(() => bench.port.line_post(line, []));
      this.assertEqual(error.message, field_text("json.tools"));
    }

    // A name of 64 letters, digits, `_` and `-` is taken, one of 65 refused.
    test_tool_names(): void {
      const bench = bench_make();
      const tool_line = (name: string, id: number): lines.Line => {
        const line = model_line([user_say("2")], id);
        (line.json as FieldTable).tools = [
          {
            type: "function",
            name,
            description: "Show an image and a subtitle.",
            parameters: { type: "object" },
          },
        ];
        return line;
      };
      const longest = "n".repeat(constants.name_max);
      for (const [index, name] of ["a-b_C9", longest].entries()) {
        const answered = line_answer(bench, tool_line(name, index + 1));
        this.assertEqual(texts_of(answered), ["Nothing happens."]);
      }
      const error = thrown_get(() =>
        bench.port.line_post(tool_line(`${longest}n`, 3), []),
      );
      this.assertEqual(error.message, field_text("json.tools[0].name"));
    }

    // A log of every kind of item, two calls answered in order, is taken.
    test_history_accepted(): void {
      const bench = bench_make();
      const input = [
        { role: "system", content: "Be the castle." },
        user_say("1"),
        { type: "reasoning", id: "rs_1" },
        {
          type: "message",
          role: "assistant",
          content: [{ type: "output_text", text: "Two calls." }],
        },
        {
          type: "function_call",
          call_id: "call_7",
          name: "browser_render",
          arguments: "{}",
        },
        {
          type: "function_call",
          call_id: "call_8",
          name: "browser_kv_get",
          arguments: "{}",
        },
        { type: "function_call_output", call_id: "call_7", output: "{}" },
        { type: "function_call_output", call_id: "call_8", output: "{}" },
        { type: "reasoning", id: "rs_2", encrypted_content: "scripted" },
        { type: "message", role: "assistant", content: [] },
        user_say("2"),
      ];
      const response = model_post(bench, input, 1);
      this.assertEqual(texts_of(response), ["Nothing happens."]);
    }

    // A reply resent without its reasoning item is refused at its first item.
    test_reasoning_lost(): void {
      const bench = bench_make();
      const moved = model_post(bench, [user_say("5")], 1);
      const said = moved.output.filter((item) => item.type === "message");
      const input = [user_say("5"), ...said, user_say("0")];
      const error = thrown_get(() => model_post(bench, input, 2));
      this.assertEqual(error.message, field_text("json.input[1].type"));
    }

    // Calls still due at the end of the input are refused by the input.
    test_due_end(): void {
      const bench = bench_make();
      const asked = model_post(bench, [user_say("1")], 1);
      const extra = {
        type: "function_call",
        call_id: "call_9",
        name: "browser_render",
        arguments: "{}",
      };
      const input = [
        user_say("1"),
        ...asked.output,
        extra,
        ...outputs_make(asked),
      ];
      const error = thrown_get(() => model_post(bench, input, 2));
      this.assertEqual(error.message, field_text("json.input"));
    }
  }

  // The answer to an image request.
  export class TestImageReply extends unittest.TestCase {
    // An image request is answered with the pattern as base64, and no move.
    test_image_answer(): void {
      const bench = bench_make();
      bench.port.line_post(gold_line("image_request"), []);
      this.assertEqual(bench.received.length, 1);
      const reply = bench.received[0];
      const data = (reply.json as provider.ImageResponse).data;
      this.assertEqual(data.length, 1);
      this.assertEqual(Object.keys(data[0]), ["b64_json"]);
      this.assertEqual(typeof data[0].b64_json, "string");
      this.assertEqual(
        base64_read(data[0].b64_json as string),
        provider_script.image_pattern(),
      );
      const expected = gold_line("reply_image");
      expected.json = reply.json;
      this.assertEqual(reply, expected);
      const response = model_post(bench, [user_say("2")], 2);
      this.assertEqual(texts_of(response), ["Nothing happens."]);
    }

    // The pattern is given as many times as the request asks.
    test_image_count(): void {
      const bench = bench_make();
      bench.port.line_post(
        image_line({
          model: constants.image_model,
          prompt: "Two gatehouses.",
          n: 2,
          response_format: "b64_json",
        }),
        [],
      );
      const data = (bench.received[0].json as provider.ImageResponse).data;
      this.assertEqual(data.length, 2);
      this.assertEqual(data[0], data[1]);
    }

    // An image request it cannot answer is refused by its field.
    test_image_refused(): void {
      const bench = bench_make();
      const formats: [string | undefined, string][] = [
        ["url", "url"],
        [undefined, "undefined"],
      ];
      for (const [format, suffix] of formats) {
        const line = image_line({
          model: constants.image_model,
          prompt: "A gatehouse.",
          n: 1,
          response_format: format,
        });
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_format_unsupported_${suffix}`),
        );
      }
      for (const count of [0, -1, 1.5, "1", undefined]) {
        const line = image_line({
          model: constants.image_model,
          prompt: "A gatehouse.",
          n: count,
          response_format: "b64_json",
        });
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(
          error.message,
          gold_text("provider_script_field_invalid_n"),
        );
      }
      this.assertEqual(bench.received.length, 0);
    }
  }

  // The PNG test pattern held against the reference PNG.
  export class TestImagePattern extends unittest.TestCase {
    // The PNG starts with the bytes the reference starts with.
    test_signature_recorded(): void {
      const size = constants.signature_bytes;
      this.assertEqual(
        provider_script.image_pattern().subarray(0, size),
        recorded_get().subarray(0, size),
      );
    }

    // The chunks are a header, the data and an end, as the reference's are.
    test_chunks_recorded(): void {
      const kinds = kinds_of(recorded_get());
      this.assertEqual(kinds, ["IHDR", "IDAT", "IEND"]);
      this.assertEqual(kinds_of(provider_script.image_pattern()), kinds);
    }

    // The header chunk is the reference's byte for byte, its CRC included.
    test_header_recorded(): void {
      this.assertEqual(
        chunk_find(provider_script.image_pattern(), "IHDR").whole,
        chunk_find(recorded_get(), "IHDR").whole,
      );
    }

    // The end chunk is the reference's byte for byte.
    test_end_recorded(): void {
      this.assertEqual(
        chunk_find(provider_script.image_pattern(), "IEND").whole,
        chunk_find(recorded_get(), "IEND").whole,
      );
    }

    // The bitwise CRC matches each chunk of the reference, then each one made.
    test_chunk_crcs(): void {
      for (const chunk of chunks_read(recorded_get())) {
        this.assertEqual(crc_reference(chunk.typed), chunk.crc);
      }
      for (const chunk of chunks_read(provider_script.image_pattern())) {
        this.assertEqual(crc_reference(chunk.typed), chunk.crc);
      }
    }

    // The data is a zlib stream of stored blocks that hold the rows.
    test_stored_blocks(): void {
      const stream = chunk_find(provider_script.image_pattern(), "IDAT").body;
      const recorded = chunk_find(recorded_get(), "IDAT").body;
      const method = stream[0];
      const flags = stream[1];
      this.assertEqual(method, recorded[0]);
      const header = method * constants.byte_range + flags;
      this.assertEqual(header % constants.check_divisor, 0);
      this.assertEqual(flags & constants.dictionary_flag, 0);
      const view = new DataView(
        stream.buffer,
        stream.byteOffset,
        stream.byteLength,
      );
      const rows: number[] = [];
      let offset: number = constants.stream_head;
      let last = false;
      while (!last) {
        const head = stream[offset];
        last = (head & 1) === 1;
        this.assertEqual(head >> 1, 0);
        const length = view.getUint16(offset + 1, true);
        const complement = view.getUint16(offset + 3, true);
        this.assertEqual(complement, length ^ constants.length_mask);
        const start = offset + constants.block_head;
        rows.push(...stream.subarray(start, start + length));
        offset = start + length;
      }
      this.assertEqual(offset, stream.length - constants.word_bytes);
      this.assertEqual(Uint8Array.from(rows), rows_expected());
    }

    // The stream ends in the checksum the reference's stream of the rows does.
    test_adler_recorded(): void {
      const stream = chunk_find(provider_script.image_pattern(), "IDAT").body;
      const recorded = chunk_find(recorded_get(), "IDAT").body;
      const size = constants.word_bytes;
      this.assertEqual(
        stream.subarray(stream.length - size),
        recorded.subarray(recorded.length - size),
      );
    }

    // Each call makes new bytes, equal to those of the call before.
    test_pattern_fresh(): void {
      const first = provider_script.image_pattern();
      const second = provider_script.image_pattern();
      this.assertEqual(first, second);
      this.assertFalse(first === second);
    }
  }
}

Object.freeze(test_provider_script);
