// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the scripted provider: a script walked through the castle turn,
// which builds the gatehouse scene, the reply lines, every refusal, the image
// answer, and the PNG test pattern held against a reference PNG of the same
// checkerboard in 88 bytes with other compressed data. The port is driven
// directly by `line_post` and `line_receive`. The request lines it posts, the
// reply lines it expects and the texts of the refusals are its gold in
// `test_settings.json`, read through the harness.

namespace test_provider_script {
  // A model, the castle turn's values, the PNG's.
  const constants = Object.freeze({
    image_model: "grok-2-image",
    id_prefix: "chatcmpl-synthetic-",
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
  type FieldTable = { [key: string]: unknown };

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

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_provider_script.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The bytes of a base64 text, as the platform's `atob` reads it.
  function base64_read(text: string): Uint8Array {
    return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
  }

  // A call of the named tool with the arguments as JSON text.
  function call_make(
    id: string,
    name: string,
    args: FieldTable,
  ): provider.ToolCall {
    return {
      id,
      type: "function",
      function: { name, arguments: JSON.stringify(args) },
    };
  }

  // The test script: the castle turn and a reply for each other path.
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
  function bench_make(): ScriptBench {
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

  // A chat request line of the provider door, numbered, for the messages.
  function chat_line(
    messages: provider.ChatMessage[],
    id: number,
  ): lines.Line {
    const line = gold_line("chat_request");
    line[0].i = id;
    (line.json as FieldTable).messages = [...messages];
    return line;
  }

  // Posts a chat request and reads the choice of the reply that came at once.
  function chat_post(
    bench: ScriptBench,
    messages: provider.ChatMessage[],
    id: number,
  ): provider.ChatChoice {
    const count = bench.received.length;
    bench.port.line_post(chat_line(messages, id), []);
    if (bench.received.length !== count + 1) {
      throw new Error("The scripted provider did not reply within the post.");
    }
    return (bench.received[count].json as provider.ChatResponse).choices[0];
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
    // The castle turn: three rounds of tool calls, then the subtitle.
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
      results_add(messages, first.message);
      const second = chat_post(bench, messages, 2);
      this.assertEqual(names_of(second), ["browser.image_make"]);
      results_add(messages, second.message);
      const third = chat_post(bench, messages, 3);
      this.assertEqual(names_of(third), [
        "browser.doc_put",
        "browser.kv_put",
        "browser.render",
      ]);
      results_add(messages, third.message);
      const last = chat_post(bench, messages, 4);
      this.assertEqual(last.message, {
        role: "assistant",
        content: constants.subtitle,
      });
      this.assertEqual(last.finish_reason, "stop");
      messages.push(last.message, user_say("0"));
      const next = chat_post(bench, messages, 5);
      this.assertEqual(next.message.content, "Still the moat.");
    }

    // The reply comes inside the post, shaped as a chat completion reply.
    test_reply_line(): void {
      const bench = bench_make();
      bench.port.line_post(chat_line([user_say("2")], 7), []);
      this.assertEqual(bench.received.length, 1);
      const reply = bench.received[0];
      this.assertEqual(Object.keys(reply).join(","), "0,status,headers,json");
      const json = reply.json as provider.ChatResponse;
      this.assertEqual(Object.keys(json).join(","), "id,model,choices");
      this.assertTrue(json.id.startsWith(constants.id_prefix));
      const expected = gold_line("reply_nothing");
      (expected.json as FieldTable).id = json.id;
      this.assertEqual(reply, expected);
    }

    // A request in full names is answered in full names.
    test_full_names(): void {
      const bench = bench_make();
      bench.port.line_post(gold_line("chat_full"), []);
      this.assertEqual(bench.received[0][0], gold_line("reply_full")[0]);
    }

    // Each chat reply has an id of its own and the model the request named.
    test_ids_distinct(): void {
      const bench = bench_make();
      const first = chat_line([user_say("2")], 1);
      const other = gold_line("chat_other");
      bench.port.line_post(first, []);
      bench.port.line_post(other, []);
      const responses = bench.received.map(
        (reply) => reply.json as provider.ChatResponse,
      );
      this.assertEqual(responses.length, 2);
      this.assertTrue(responses[0].id !== responses[1].id);
      for (const response of responses) {
        this.assertTrue(response.id.startsWith(constants.id_prefix));
      }
      this.assertEqual(responses[0].model, (first.json as FieldTable).model);
      this.assertEqual(responses[1].model, (other.json as FieldTable).model);
    }

    // The calls in a reply are copies, not the script's own objects.
    test_calls_copied(): void {
      const script = script_make();
      const port = new provider_script.ScriptPort(script);
      const received: lines.Line[] = [];
      port.line_receive((line: lines.Line) => {
        received.push(line);
      });
      port.line_post(chat_line([user_say("1")], 1), []);
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
        gold_text("provider_script_node_unknown"),
      );
    }

    // A reply that leads to no node is refused at the next request.
    test_next_unknown(): void {
      const bench = bench_make();
      const messages = [user_say("4")];
      const choice = chat_post(bench, messages, 1);
      this.assertEqual(choice.message.content, "Gone.");
      messages.push(choice.message, user_say("1"));
      const error = thrown_get(() => chat_post(bench, messages, 2));
      this.assertEqual(
        error.message,
        gold_text("provider_script_node_unknown"),
      );
    }

    // A user message that is not the decimal text of one integer is refused.
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
        const error = thrown_get(() => chat_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_input_invalid_${suffix}`),
        );
      }
      this.assertEqual(bench.received.length, 0);
    }

    // An integer the node has no reply for is refused.
    test_input_unknown(): void {
      const bench = bench_make();
      const cases: [string, string][] = [
        ["0", "zero"],
        ["9", "nine"],
        ["-5", "minus_five"],
      ];
      for (const [text, suffix] of cases) {
        const error = thrown_get(() => chat_post(bench, [user_say(text)], 1));
        this.assertEqual(
          error.message,
          gold_text(`provider_script_input_unknown_${suffix}`),
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
        gold_text("provider_script_results_unasked"),
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
        gold_text("provider_script_results_pending"),
      );
    }

    // Tool results whose call ids are not the calls of the reply are refused.
    test_results_unmatched(): void {
      const bench = bench_make();
      const asked = chat_post(bench, [user_say("1")], 1).message;
      const cases: [string[], string][] = [
        [["call_9"], "other"],
        [["call_1", "call_1"], "twice"],
      ];
      for (const [ids, suffix] of cases) {
        const messages: provider.ChatMessage[] = [user_say("1"), asked];
        for (const id of ids) {
          messages.push({ role: "tool", tool_call_id: id, content: "{}" });
        }
        const error = thrown_get(() => chat_post(bench, messages, 2));
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
      const messages = [user_say("3")];
      results_add(messages, chat_post(bench, messages, 1).message);
      const error = thrown_get(() => chat_post(bench, messages, 2));
      this.assertEqual(
        error.message,
        gold_text("provider_script_after_missing"),
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
          gold_text(`provider_script_role_unexpected_${role}`),
        );
      }
    }

    // A port with no receiver, or given a second one, refuses it.
    test_receiver_rules(): void {
      const port = new provider_script.ScriptPort(script_make());
      const request = chat_line([user_say("2")], 1);
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

    // A line that is not a chat or image request it can read is refused.
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
        [gold_line("refused_model"), "provider_script_field_invalid_model"],
        [
          gold_line("refused_messages"),
          "provider_script_field_invalid_messages",
        ],
        [
          gold_line("refused_message"),
          "provider_script_field_invalid_message",
        ],
      ];
      for (const [line, name] of cases) {
        const error = thrown_get(() => bench.port.line_post(line, []));
        this.assertEqual(error.message, gold_text(name));
      }
      this.assertEqual(bench.received.length, 0);
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
      this.assertEqual(Object.keys(data[0]).join(","), "b64_json");
      this.assertEqual(typeof data[0].b64_json, "string");
      this.assertEqual(
        base64_read(data[0].b64_json as string),
        provider_script.image_pattern(),
      );
      const expected = gold_line("reply_image");
      expected.json = reply.json;
      this.assertEqual(reply, expected);
      const choice = chat_post(bench, [user_say("2")], 2);
      this.assertEqual(choice.message.content, "Nothing happens.");
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
