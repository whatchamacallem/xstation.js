// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the scripted provider: a script walked through the recorded turn,
// the reply lines, every refusal, the image answer, the PNG test pattern held
// against the recorded one, and the port behind a task queue in synchronous
// mode.

namespace test_provider_script {
  // The values the tests share, as the settings and the recorded turn hold.
  const constants = Object.freeze({
    base_url: "https://api.x.ai/v1",
    key: "xai-SYNTHETIC-KEY",
    chat_model: "grok-4",
    image_model: "grok-2-image",
    request_type: "http.request",
    id_prefix: "chatcmpl-synthetic-",
    type_prefix: "provider_script_test.",
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone, " +
      "though not necessarily you.",
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

  // An object of fields by name.
  type Fields = { [key: string]: unknown };

  // A port on the test script and the replies it has sent.
  interface Bench {
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

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

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

  // Registers a handler for a new type of these tests and returns the type.
  function handler_fresh(fn: dispatch.Handler): string {
    types_made += 1;
    const type = `${constants.type_prefix}${types_made}`;
    dispatch.handler_register(type, 0, fn);
    return type;
  }

  // A call of the named tool with the arguments as JSON text.
  function call_make(
    id: string,
    name: string,
    args: Fields,
  ): provider.ToolCall {
    return {
      id,
      type: "function",
      function: { name, arguments: utility.json_text(args) },
    };
  }

  // The test script: the recorded turn and a reply for each other path.
  function script_make(): provider_script.Script {
    const bootstrap = call_make("call_1", "browser.script_run", {
      name: "bootstrap",
      args: { universe: "castle", world: "castle_world" },
    });
    const image = call_make("call_2", "browser.image_make", {
      prompt: "A rain dark castle gatehouse at dusk",
      key: "/_files/gatehouse/arrival.png",
    });
    const scene = call_make("call_3", "browser.doc_put", {
      db: "castle_gatehouse",
      id: "scene/arrival",
      body: { 0: { t: "scene" }, subtitle: constants.subtitle },
    });
    const enter = call_make("call_4", "browser.kv_put", {
      ref: "/castle_world/scene",
      text: "/castle_gatehouse/scene/arrival/1",
    });
    const render = call_make("call_5", "browser.render", {
      image: "/_files/gatehouse/arrival.png",
      subtitle: constants.subtitle,
    });
    const look = call_make("call_6", "browser.kv_get", {
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

  // A port on a new test script whose receiver keeps every reply.
  function bench_make(): Bench {
    const port = new provider_script.ScriptPort(script_make());
    const received: lines.Line[] = [];
    port.line_receive((line: lines.Line) => {
      received.push(line);
    });
    return { port, received };
  }

  // A user message with the text.
  function user_say(text: string | null): provider.ChatMessage {
    return { role: "user", content: text };
  }

  // The line with the id the queue would give it, in the name form asked.
  function line_numbered(
    line: lines.Line,
    id: number,
    full: boolean,
  ): lines.Line {
    const header = jslb.header_make(constants.request_type, { id, full });
    return jslb.line_make(header, [], jslb.payload_of(line));
  }

  // A chat request line of the provider door, numbered, for the messages.
  function chat_line(
    messages: provider.ChatMessage[],
    id: number,
    full: boolean,
  ): lines.Line {
    const line = provider.chat_request(constants.base_url, constants.key, {
      model: constants.chat_model,
      messages: [...messages],
      tool_choice: "auto",
    });
    return line_numbered(line, id, full);
  }

  // Posts a chat request and reads the choice of the reply that came at once.
  function chat_post(
    bench: Bench,
    messages: provider.ChatMessage[],
    id: number,
  ): provider.ChatChoice {
    const count = bench.received.length;
    bench.port.line_post(chat_line(messages, id, false), []);
    if (bench.received.length !== count + 1) {
      throw new Error("The scripted provider did not reply within the post.");
    }
    return provider.chat_response(bench.received[count]).choices[0];
  }

  // Adds the assistant message and one tool result for each call it made.
  function results_add(
    messages: provider.ChatMessage[],
    message: provider.ChatMessage,
  ): void {
    messages.push(message);
    for (const call of message.tool_calls ?? []) {
      messages.push({ role: "tool", tool_call_id: call.id, content: "{}" });
    }
  }

  // The names of the tools a choice calls, in order.
  function names_of(choice: provider.ChatChoice): string[] {
    return (choice.message.tool_calls ?? []).map((call) => call.function.name);
  }

  // The payload of a chat request every check accepts, with fields replaced.
  function payload_with(fields: Fields): Fields {
    return {
      method: "POST",
      url: `${constants.base_url}/chat/completions`,
      headers: {},
      json: { model: constants.chat_model, messages: [user_say("2")] },
      ...fields,
    };
  }

  // A line of the type with the header options, blobs and payload given.
  function line_build(
    type: string,
    options: { id?: number },
    blobs: lines.BlobHeader[],
    payload: Fields,
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), blobs, payload);
  }

  // An image request line numbered 1 whose body is the one given.
  function image_line(json: Fields): lines.Line {
    return line_build(constants.request_type, { id: 1 }, [], {
      method: "POST",
      url: `${constants.base_url}/images/generations`,
      headers: {},
      json,
    });
  }

  // The bytes of the recorded test pattern.
  function recorded_get(): Uint8Array {
    return utility.base64_decode(constants.recorded_png);
  }

  // The chunks of a PNG after its signature, in order.
  function chunks_read(png: Uint8Array): PngChunk[] {
    const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
    const word = constants.word_bytes;
    const chunks: PngChunk[] = [];
    let offset = constants.signature_bytes;
    while (offset < png.length) {
      const length = view.getUint32(offset);
      const end = offset + 3 * word + length;
      const typed = png.subarray(offset + word, end - word);
      chunks.push({
        kind: utility.utf8_decode(typed.subarray(0, word)),
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

  // The rows of the checkerboard as the recorded turn draws them.
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
    // The recorded turn: three rounds of tool calls, then the subtitle.
    test_turn_walk(): void {
      const bench = bench_make();
      const script = script_make();
      const messages = [user_say("1")];
      const first = chat_post(bench, messages, 1);
      this.assertEqual(
        first.message.tool_calls,
        script.nodes.hyperposition.replies["1"].tool_calls,
      );
      this.assertEqual(first.message.content, null);
      this.assertEqual(first.finish_reason, "tool_calls");
      this.assertEqual(bench.port.node(), "hyperposition");
      results_add(messages, first.message);
      const second = chat_post(bench, messages, 2);
      this.assertEqual(names_of(second), ["browser.image_make"]);
      this.assertEqual(bench.port.node(), "castle");
      results_add(messages, second.message);
      const third = chat_post(bench, messages, 3);
      this.assertEqual(names_of(third), [
        "browser.doc_put",
        "browser.kv_put",
        "browser.render",
      ]);
      this.assertEqual(bench.port.node(), "imaged");
      results_add(messages, third.message);
      const last = chat_post(bench, messages, 4);
      this.assertEqual(last.message, {
        role: "assistant",
        content: constants.subtitle,
      });
      this.assertEqual(last.finish_reason, "stop");
      this.assertEqual(bench.port.node(), "gatehouse");
      messages.push(last.message, user_say("0"));
      const next = chat_post(bench, messages, 5);
      this.assertEqual(next.message.content, "Still the moat.");
      this.assertEqual(bench.port.node(), "gatehouse");
    }

    // The reply comes inside the post, shaped as the recorded replies are.
    test_reply_line(): void {
      const bench = bench_make();
      bench.port.line_post(chat_line([user_say("2")], 7, false), []);
      this.assertEqual(bench.received.length, 1);
      const reply = bench.received[0];
      this.assertEqual(reply[0], { t: constants.request_type, r: 7 });
      this.assertEqual(
        Object.keys(reply).join(","),
        "0,status,headers,json",
      );
      this.assertEqual(reply.status, 200);
      this.assertEqual(reply.headers, { "content-type": "application/json" });
      const json = reply.json as provider.ChatResponse;
      this.assertEqual(Object.keys(json).join(","), "id,model,choices");
      this.assertTrue(json.id.startsWith(constants.id_prefix));
      this.assertEqual(json.model, constants.chat_model);
      this.assertEqual(json.choices, [
        {
          index: 0,
          message: { role: "assistant", content: "Nothing happens." },
          finish_reason: "stop",
        },
      ]);
    }

    // A request in full names is answered in full names.
    test_full_names(): void {
      const bench = bench_make();
      bench.port.line_post(chat_line([user_say("2")], 7, true), []);
      this.assertEqual(bench.received[0][0], {
        type: constants.request_type,
        reply: 7,
      });
    }

    // Each chat reply has an id of its own and the model the request named.
    test_ids_distinct(): void {
      const bench = bench_make();
      bench.port.line_post(chat_line([user_say("2")], 1, false), []);
      const other = provider.chat_request(constants.base_url, constants.key, {
        model: "grok-x",
        messages: [user_say("2")],
      });
      bench.port.line_post(line_numbered(other, 2, false), []);
      const responses = bench.received.map((reply) =>
        provider.chat_response(reply),
      );
      this.assertEqual(responses.length, 2);
      this.assertTrue(responses[0].id !== responses[1].id);
      for (const response of responses) {
        this.assertTrue(response.id.startsWith(constants.id_prefix));
      }
      this.assertEqual(responses[0].model, constants.chat_model);
      this.assertEqual(responses[1].model, "grok-x");
    }

    // The calls in a reply are copies, not the script's own objects.
    test_calls_copied(): void {
      const script = script_make();
      const port = new provider_script.ScriptPort(script);
      const received: lines.Line[] = [];
      port.line_receive((line: lines.Line) => {
        received.push(line);
      });
      port.line_post(chat_line([user_say("1")], 1, false), []);
      const sent = received[0].json as provider.ChatResponse;
      const calls = sent.choices[0].message.tool_calls ?? [];
      const kept = script.nodes.hyperposition.replies["1"].tool_calls ?? [];
      this.assertEqual(calls, kept);
      this.assertEqual(calls.length, 1);
      this.assertFalse(calls[0] === kept[0]);
    }

    // A reply without tool calls moves to its next node at once.
    test_stop_moves(): void {
      const bench = bench_make();
      const messages = [user_say("5")];
      const choice = chat_post(bench, messages, 1);
      this.assertEqual(choice.message.content, "To the gatehouse.");
      this.assertEqual(choice.finish_reason, "stop");
      this.assertFalse(Object.hasOwn(choice.message, "tool_calls"));
      this.assertEqual(bench.port.node(), "gatehouse");
      messages.push(choice.message, user_say("0"));
      this.assertEqual(
        chat_post(bench, messages, 2).message.content,
        "Still the moat.",
      );
    }
  }

  // The faults of a script and of the lines it is given.
  export class TestScriptFaults extends unittest.TestCase {
    // A script whose start names no node is refused when the port is made.
    test_start_unknown(): void {
      const error = thrown_get(
        () => new provider_script.ScriptPort({ start: "nowhere", nodes: {} }),
      );
      this.assertEqual(
        error.message,
        i18n("provider_script.node_unknown", "nowhere"),
      );
    }

    // A reply that leads to no node is refused at the next request.
    test_next_unknown(): void {
      const bench = bench_make();
      const messages = [user_say("4")];
      const choice = chat_post(bench, messages, 1);
      this.assertEqual(bench.port.node(), "nowhere");
      messages.push(choice.message, user_say("1"));
      const error = thrown_get(() => chat_post(bench, messages, 2));
      this.assertEqual(
        error.message,
        i18n("provider_script.node_unknown", "nowhere"),
      );
    }

    // A user message that is not the decimal text of one integer is refused.
    test_input_invalid(): void {
      const bench = bench_make();
      const texts = ["one", "01", "1.0", " 1", "1 ", "+1", "-0", "", null];
      for (const text of texts) {
        const error = thrown_get(() => chat_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          i18n("provider_script.input_invalid", String(text)),
        );
      }
      this.assertEqual(bench.received.length, 0);
      this.assertEqual(bench.port.node(), "hyperposition");
    }

    // An integer the node has no reply for is refused.
    test_input_unknown(): void {
      const bench = bench_make();
      for (const text of ["0", "9", "-5"]) {
        const error = thrown_get(() => chat_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          i18n("provider_script.input_unknown", "hyperposition", text),
        );
      }
    }

    // Tool results after a reply that called no tool are refused.
    test_results_unasked(): void {
      const bench = bench_make();
      const messages: provider.ChatMessage[] = [
        user_say("2"),
        { role: "tool", tool_call_id: "call_1", content: "{}" },
      ];
      const error = thrown_get(() => chat_post(bench, messages, 1));
      this.assertEqual(
        error.message,
        i18n("provider_script.results_unasked", "hyperposition"),
      );
    }

    // A user message while tool results are pending is refused.
    test_results_pending(): void {
      const bench = bench_make();
      chat_post(bench, [user_say("1")], 1);
      const messages = [user_say("1"), user_say("2")];
      const error = thrown_get(() => chat_post(bench, messages, 2));
      this.assertEqual(
        error.message,
        i18n("provider_script.results_pending", "hyperposition", "castle"),
      );
    }

    // Tool results that lead to a node with no reply after them are refused.
    test_after_missing(): void {
      const bench = bench_make();
      const messages = [user_say("3")];
      results_add(messages, chat_post(bench, messages, 1).message);
      const error = thrown_get(() => chat_post(bench, messages, 2));
      this.assertEqual(
        error.message,
        i18n("provider_script.after_missing", "bare"),
      );
    }

    // A last message that is neither the user's nor a tool result is refused.
    test_role_unexpected(): void {
      const bench = bench_make();
      for (const role of ["assistant", "system"] as const) {
        const messages = [{ role, content: "Hello." }];
        const error = thrown_get(() => chat_post(bench, messages, 1));
        this.assertEqual(
          error.message,
          i18n("provider_script.role_unexpected", role),
        );
      }
    }

    // A port with no receiver, or given a second one, refuses it.
    test_receiver_rules(): void {
      const port = new provider_script.ScriptPort(script_make());
      const request = chat_line([user_say("2")], 1, false);
      const missing = thrown_get(() => port.line_post(request, []));
      this.assertEqual(
        missing.message,
        i18n("provider_script.receiver_missing"),
      );
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, i18n("provider_script.receiver_twice"));
    }

    // A line that is not a chat or image request it can read is refused.
    test_line_refused(): void {
      const bench = bench_make();
      const type = constants.request_type;
      const blob = jslb.blob_make(new Uint8Array(1));
      const unknown = `${constants.base_url}/models`;
      const no_model = payload_with({ json: { messages: [] } });
      const no_messages = payload_with({ json: { model: "m" } });
      const bad_message = payload_with({
        json: { model: "m", messages: [5] },
      });
      const cases: [lines.Line, string][] = [
        [
          line_build("kv.get", { id: 1 }, [], payload_with({})),
          i18n("provider_script.type_invalid", "kv.get", type),
        ],
        [
          line_build(type, {}, [], payload_with({})),
          i18n("provider_script.id_missing", type),
        ],
        [
          line_build(type, { id: 1 }, [blob], payload_with({})),
          i18n("provider_script.blobs_refused", type),
        ],
        [
          line_build(type, { id: 1 }, [], payload_with({ method: "GET" })),
          i18n("provider_script.field_invalid", "method"),
        ],
        [
          line_build(type, { id: 1 }, [], payload_with({ url: 5 })),
          i18n("provider_script.field_invalid", "url"),
        ],
        [
          line_build(type, { id: 1 }, [], payload_with({ url: unknown })),
          i18n("provider_script.url_unknown", unknown),
        ],
        [
          line_build(type, { id: 1 }, [], payload_with({ json: undefined })),
          i18n("provider_script.field_invalid", "json"),
        ],
        [
          line_build(type, { id: 1 }, [], no_model),
          i18n("provider_script.field_invalid", "json.model"),
        ],
        [
          line_build(type, { id: 1 }, [], no_messages),
          i18n("provider_script.field_invalid", "json.messages"),
        ],
        [
          line_build(type, { id: 1 }, [], bad_message),
          i18n("provider_script.field_invalid", "json.messages[0]"),
        ],
      ];
      for (const [line, expected] of cases) {
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(error.message, expected);
      }
      this.assertEqual(bench.received.length, 0);
      this.assertEqual(bench.port.node(), "hyperposition");
    }
  }

  // The answer to an image request.
  export class TestImageReply extends unittest.TestCase {
    // An image request is answered with the pattern as base64, and no move.
    test_image_answer(): void {
      const bench = bench_make();
      const request: provider.ImageRequest = {
        model: constants.image_model,
        prompt: "A rain dark castle gatehouse at dusk",
        n: 1,
        response_format: "b64_json",
      };
      const line = provider.image_request(
        constants.base_url,
        constants.key,
        request,
      );
      bench.port.line_post(line_numbered(line, 3, false), []);
      this.assertEqual(bench.received.length, 1);
      const reply = bench.received[0];
      this.assertEqual(reply[0], { t: constants.request_type, r: 3 });
      this.assertEqual(reply.status, 200);
      this.assertEqual(reply.headers, { "content-type": "application/json" });
      const data = (reply.json as provider.ImageResponse).data;
      this.assertEqual(data.length, 1);
      this.assertEqual(Object.keys(data[0]).join(","), "b64_json");
      this.assertEqual(typeof data[0].b64_json, "string");
      this.assertEqual(
        utility.base64_decode(data[0].b64_json as string),
        provider_script.image_pattern(),
      );
      this.assertEqual(provider.image_response(reply).data, data);
      this.assertEqual(bench.port.node(), "hyperposition");
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
      for (const format of ["url", undefined]) {
        const line = image_line({
          model: constants.image_model,
          prompt: "A gatehouse.",
          n: 1,
          response_format: format,
        });
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(
          error.message,
          i18n("provider_script.format_unsupported", String(format)),
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
          i18n("provider_script.field_invalid", "json.n"),
        );
      }
      this.assertEqual(bench.received.length, 0);
    }
  }

  // The PNG test pattern held against the recorded one.
  export class TestImagePattern extends unittest.TestCase {
    // The PNG starts with the bytes the recorded one starts with.
    test_signature_recorded(): void {
      const size = constants.signature_bytes;
      this.assertEqual(
        provider_script.image_pattern().subarray(0, size),
        recorded_get().subarray(0, size),
      );
    }

    // The chunks are a header, the data and an end, as recorded.
    test_chunks_recorded(): void {
      const kinds = kinds_of(recorded_get());
      this.assertEqual(kinds, ["IHDR", "IDAT", "IEND"]);
      this.assertEqual(kinds_of(provider_script.image_pattern()), kinds);
    }

    // The header chunk is the recorded one byte for byte, its CRC included.
    test_header_recorded(): void {
      this.assertEqual(
        chunk_find(provider_script.image_pattern(), "IHDR").whole,
        chunk_find(recorded_get(), "IHDR").whole,
      );
    }

    // The end chunk is the recorded one byte for byte.
    test_end_recorded(): void {
      this.assertEqual(
        chunk_find(provider_script.image_pattern(), "IEND").whole,
        chunk_find(recorded_get(), "IEND").whole,
      );
    }

    // The reference reads every recorded chunk's CRC, then every one made.
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
      let offset = constants.stream_head;
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

    // The stream ends in the checksum the recorded stream of the rows ends in.
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

  // The port behind a task queue in synchronous mode.
  export class TestQueueReply extends unittest.TestCase {
    // A reply made inside the post wakes the task that slept on its request.
    test_queue_synchronous(): void {
      const owners: queue.OwnerTable = {
        [constants.type_prefix]: "ai",
        "http.": "http",
      };
      const tasks = new queue.TaskQueue("ai", owners, true);
      tasks.port_add("http", new provider_script.ScriptPort(script_make()));
      const submitted: number[] = [];
      const woken: lines.Line[] = [];
      const wake = handler_fresh((line: lines.Line) => {
        woken.push(...(line.replies as lines.Line[]));
        return undefined;
      });
      const say = handler_fresh(() => {
        const request = provider.chat_request(
          constants.base_url,
          constants.key,
          { model: constants.chat_model, messages: [user_say("2")] },
        );
        submitted.push(tasks.task_submit(request));
        return dispatch.task_sleep(null, submitted, wake);
      });
      tasks.line_notify(jslb.line_make(jslb.header_make(say), [], {}), "ai");
      this.assertEqual(submitted.length, 1);
      this.assertEqual(woken.length, 1);
      this.assertEqual(jslb.field_get(woken[0][0], "reply"), submitted[0]);
      const choice = provider.chat_response(woken[0]).choices[0];
      this.assertEqual(choice.message.content, "Nothing happens.");
      this.assertEqual(tasks.depth(), 0);
    }
  }
}

Object.freeze(test_provider_script);
