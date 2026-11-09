// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the provider door to xAI's Responses API: the request lines it
// builds, their url, their two headers and no other, and the order of a model
// request's body with every optional field and with none; the reading of a
// model reply, its output items kept as parsed with every field xAI sent, and
// each refusal in the order the door checks; the function calls and the
// joined texts of an output; the reading of an image reply; and the flat
// function tools made of MCP tools. The key it keeps in memory is tested in
// `test_provider_key`, and unset in `test_provider_key_unset`, whose fresh
// realm has none set. The request lines it expects, in the full names of
// debug mode, the body orders, the reply lines it reads and the texts of its
// refusals are its gold in `ts/test_setting_test_provider.json`, read through
// the harness.

namespace test_provider {
  // A provider's address, key, models and ids, and values of the castle turn.
  const constants = Object.freeze({
    base_url: "https://api.x.ai/v1",
    key: "xai-SYNTHETIC-KEY",
    chat_model: "grok-4",
    conversation: "/metaverse/hyperposition/1",
    response_id: "resp_3f2a9c0b7d1e4a56",
    reasoning_id: "rs_3f2a9c0b7d1e4a56",
    message_id: "msg_3f2a9c0b7d1e4a56",
    call_id: "fc_3f2a9c0b7d1e4a56_1",
    include_name: "reasoning.encrypted_content",
    image_model: "grok-2-image",
    bootstrap_arguments:
      '{"name":"bootstrap","args":{"universe":"castle",' +
      '"title":"The castle","world":"castle_world",' +
      '"region":"castle_gatehouse"}}',
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone, " +
      "though not necessarily you.",
    recorded_png:
      "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2" +
      "AAAAH0lEQVR42mP4jwQYkAAucYZBqGGQO48o" +
      "DaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg==",
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

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
      harness.gold_get(`typescript.test_provider.${name}`),
    );
  }

  // A text of this module's gold.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_provider.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A reply line to request 1 carrying the JSON body, in short names.
  function reply_build(json: unknown): lines.Line {
    const reply = gold_line("reply");
    reply.json = json;
    return reply;
  }

  // A copy of the fields without the one named.
  function field_drop(fields: FieldTable, key: string): FieldTable {
    const copy = { ...fields };
    delete copy[key];
    return copy;
  }

  // The items as an output, which the door's functions take.
  function output_of(...items: FieldTable[]): provider.OutputItem[] {
    return items as unknown as provider.OutputItem[];
  }

  // A reasoning item as xAI writes one, its summary a field the door skips.
  function reasoning_valid(): FieldTable {
    return {
      type: "reasoning",
      id: constants.reasoning_id,
      summary: [{ type: "summary_text", text: "Weighed the gatehouse." }],
      encrypted_content: "opaque",
      status: "completed",
    };
  }

  // A message of the model with one text part for each text.
  function message_valid(texts: string[]): FieldTable {
    return {
      type: "message",
      id: constants.message_id,
      role: "assistant",
      status: "completed",
      content: texts.map((text) => ({
        type: "output_text",
        text,
        annotations: [],
      })),
    };
  }

  // A function call of the castle turn's bootstrap script, by its call id.
  function call_valid(call_id: string): FieldTable {
    return {
      type: "function_call",
      id: constants.call_id,
      call_id,
      name: "browser_script_run",
      arguments: constants.bootstrap_arguments,
      status: "completed",
    };
  }

  // A model reply body whose output is the items given.
  function body_of(output: unknown[]): FieldTable {
    return {
      id: constants.response_id,
      object: "response",
      model: constants.chat_model,
      status: "completed",
      output,
    };
  }

  // A good model reply body with the fields given in place of its own.
  function body_with(fields: FieldTable): FieldTable {
    return { ...body_of([reasoning_valid()]), ...fields };
  }

  // A good model reply body without the field named.
  function body_without(key: string): FieldTable {
    return field_drop(body_of([reasoning_valid()]), key);
  }

  // A body whose one item is a message with the fields given in its place.
  function message_with(fields: FieldTable): FieldTable {
    return body_of([{ ...message_valid(["Noted."]), ...fields }]);
  }

  // A body whose one item is a call with the fields given in its place.
  function call_with(fields: FieldTable): FieldTable {
    return body_of([{ ...call_valid("call_1"), ...fields }]);
  }

  // A reply as xAI writes one: its echoes and three items of every kind.
  function recorded_body(): FieldTable {
    return {
      ...body_of([
        reasoning_valid(),
        message_valid([constants.subtitle]),
        call_valid("call_1"),
      ]),
      tool_choice: "auto",
      previous_response_id: null,
    };
  }

  // A tool as `tools/list` lists it, with the schema of one text property.
  function tool_make(
    name: string,
    description: string,
    field: string,
  ): mcp.Tool {
    return {
      name,
      description,
      inputSchema: {
        type: "object",
        properties: { [field]: { type: "string" } },
        required: [field],
      },
    };
  }

  // The request lines the two builders make.
  export class TestRequestBuild extends unittest.TestCase {
    // Checks a request line's header, url and headers against the gold.
    line_assert(line: lines.Line, name: string): void {
      const expected = gold_line(name);
      this.assertEqual(line[0], expected[0]);
      this.assertEqual(Object.keys(line), [
        "0",
        "method",
        "url",
        "headers",
        "json",
      ]);
      this.assertEqual(line.method, expected.method);
      this.assertEqual(line.url, expected.url);
      this.assertEqual(line.headers, expected.headers);
    }

    // A model request with every field writes them in the door's order.
    test_model_whole(): void {
      const tools = provider.tools_convert([
        tool_make("browser_render", "Show an image and a subtitle.", "image"),
      ]);
      const request: provider.ModelRequest = {
        include: [constants.include_name],
        prompt_cache_key: constants.conversation,
        tool_choice: "auto",
        tools,
        input: [{ role: "user", content: "1" }],
        previous_response_id: constants.response_id,
        model: constants.chat_model,
      };
      const line = provider.model_request(
        constants.base_url,
        constants.key,
        request,
      );
      this.line_assert(line, "model_request");
      const body = line.json as FieldTable;
      this.assertEqual(Object.keys(body), gold_value("orders.whole"));
      this.assertEqual(body, { ...request });
    }

    // A model request with no optional field writes the three it must.
    test_model_least(): void {
      const request: provider.ModelRequest = {
        prompt_cache_key: constants.conversation,
        input: [{ role: "system", content: "Be the castle." }],
        model: constants.chat_model,
      };
      const line = provider.model_request(
        constants.base_url,
        constants.key,
        request,
      );
      this.line_assert(line, "model_request");
      const body = line.json as FieldTable;
      this.assertEqual(Object.keys(body), gold_value("orders.least"));
      this.assertEqual(body, { ...request });
    }

    // An image request goes to the image path with its own body.
    test_image_line(): void {
      const request: provider.ImageRequest = {
        model: constants.image_model,
        prompt: "A gatehouse at dusk.",
        n: 1,
        response_format: "b64_json",
      };
      const line = provider.image_request(
        constants.base_url,
        constants.key,
        request,
      );
      this.line_assert(line, "image_request");
      this.assertTrue(line.json === request);
    }

    // The key given is the one the header carries.
    test_key_carried(): void {
      const request: provider.ModelRequest = {
        model: constants.chat_model,
        input: [],
        prompt_cache_key: constants.conversation,
      };
      for (const key of ["first", ""]) {
        const line = provider.model_request(constants.base_url, key, request);
        const headers = line.headers as FieldTable;
        this.assertEqual(headers.Authorization, `Bearer ${key}`);
      }
    }
  }

  // The model response read out of a reply line.
  export class TestModelResponse extends unittest.TestCase {
    // The four fields are read and each item is kept as parsed, whole.
    test_output_kept(): void {
      const body = recorded_body();
      const response = provider.model_response(reply_build(body));
      this.assertEqual(Object.keys(response), [
        "id",
        "model",
        "status",
        "output",
      ]);
      this.assertEqual(response, {
        id: constants.response_id,
        model: constants.chat_model,
        status: "completed",
        output: recorded_body().output,
      });
      const items = body.output as unknown[];
      this.assertEqual(response.output.length, items.length);
      for (const [index, item] of response.output.entries()) {
        this.assertTrue(item === items[index]);
      }
    }

    // A reply cut short by a limit is read, its status kept.
    test_status_incomplete(): void {
      const body = body_with({ status: "incomplete" });
      const response = provider.model_response(reply_build(body));
      this.assertEqual(response.status, "incomplete");
    }

    // An output with no item, and a reasoning item with no content, are read.
    test_output_least(): void {
      const empty = provider.model_response(reply_build(body_of([])));
      this.assertEqual(empty.output, []);
      const bare = { type: "reasoning", id: constants.reasoning_id };
      const response = provider.model_response(reply_build(body_of([bare])));
      this.assertEqual(response.output, [bare]);
    }

    // A reply in full names is read as one in short names.
    test_full_names(): void {
      const reply = gold_line("reply_full");
      reply.json = recorded_body();
      const response = provider.model_response(reply);
      this.assertEqual(response.output, recorded_body().output);
    }

    // An `error` line or a line of another type is refused by its type.
    test_type_refused(): void {
      for (const suffix of ["error", "kv_get"]) {
        const line = gold_line(`refused_${suffix}`);
        const expected = gold_text(`provider_reply_type_${suffix}`);
        const model = thrown_get(() => provider.model_response(line));
        this.assertEqual(model.message, expected);
        const image = thrown_get(() => provider.image_response(line));
        this.assertEqual(image.message, expected);
      }
    }

    // Each part missing or not valid is named, the first in the door's order.
    test_fields_invalid(): void {
      const text_part = { type: "output_text", text: "Noted." };
      const cases: [string, unknown][] = [
        ["json", null],
        ["json", [1]],
        ["id", body_without("id")],
        ["id", body_with({ id: 5, model: 5 })],
        ["model", body_without("model")],
        ["model", body_with({ model: 5, status: "failed" })],
        ["status", body_without("status")],
        ["status", body_with({ status: "in_progress", output: {} })],
        ["status", body_with({ status: "failed" })],
        ["output", body_without("output")],
        ["output", body_with({ output: {} })],
        ["item", body_of([5])],
        ["item_type", body_of([{ id: constants.reasoning_id }])],
        ["item_type", body_of([{ type: "web_search_call", id: "ws_1" }])],
        ["item_type", body_of([{ type: "image_generation_call" }, 5])],
        ["reasoning_id", body_of([field_drop(reasoning_valid(), "id")])],
        ["reasoning_id", body_of([{ ...reasoning_valid(), id: 5 }])],
        ["message_role", message_with({ role: "user", content: 5 })],
        [
          "message_role",
          body_of([field_drop(message_valid(["Noted."]), "role")]),
        ],
        ["message_content", message_with({ content: "Noted." })],
        ["part", message_with({ content: [5] })],
        [
          "part_type",
          message_with({ content: [{ type: "refusal", refusal: "No." }] }),
        ],
        ["part_type", message_with({ content: [{ type: "input_text" }] })],
        ["part_text", message_with({ content: [{ type: "output_text" }] })],
        [
          "part_second",
          message_with({ content: [text_part, { type: "output_text" }] }),
        ],
        ["call_id", call_with({ call_id: 5, name: 5 })],
        ["call_id", body_of([field_drop(call_valid("call_1"), "call_id")])],
        ["call_name", body_of([field_drop(call_valid("call_1"), "name")])],
        ["call_name", call_with({ name: 5, arguments: 5 })],
        ["call_arguments", call_with({ arguments: {} })],
        ["second_item", body_of([reasoning_valid(), { type: "other" }])],
      ];
      for (const [suffix, json] of cases) {
        const error = thrown_get(() =>
          provider.model_response(reply_build(json)),
        );
        const expected = gold_text(`provider_field_invalid_${suffix}`);
        this.assertEqual(error.message, expected);
      }
    }
  }

  // The function calls and the texts of an output.
  export class TestOutputRead extends unittest.TestCase {
    // The calls are found in order, as the very items of the output.
    test_calls_found(): void {
      const first = call_valid("call_1");
      const second = { ...call_valid("call_2"), name: "browser_render" };
      const output = output_of(
        reasoning_valid(),
        first,
        message_valid(["Noted."]),
        second,
      );
      const calls: unknown[] = provider.calls_find(output);
      this.assertEqual(calls, [first, second]);
      this.assertTrue(calls[0] === first);
      this.assertTrue(calls[1] === second);
    }

    // An output with no call has none.
    test_calls_none(): void {
      const output = output_of(reasoning_valid(), message_valid(["Noted."]));
      this.assertEqual(provider.calls_find(output), []);
      this.assertEqual(provider.calls_find([]), []);
    }

    // The parts of a message are joined in order by a line break.
    test_parts_joined(): void {
      const output = output_of(
        reasoning_valid(),
        message_valid(["The moat.", "The gate."]),
      );
      this.assertEqual(provider.text_join(output), "The moat.\nThe gate.");
    }

    // The messages are joined in order, a call between them skipped.
    test_messages_joined(): void {
      const output = output_of(
        message_valid(["The moat.", "The gate."]),
        call_valid("call_1"),
        message_valid(["The keep."]),
      );
      this.assertEqual(
        provider.text_join(output),
        "The moat.\nThe gate.\nThe keep.",
      );
    }

    // An output that holds no message has no text, `null`.
    test_text_none(): void {
      const output = output_of(reasoning_valid(), call_valid("call_1"));
      this.assertEqual(provider.text_join(output), null);
      this.assertEqual(provider.text_join([]), null);
    }

    // A message with no part says the empty text, which is not `null`.
    test_parts_none(): void {
      const output = output_of(reasoning_valid(), message_valid([]));
      this.assertEqual(provider.text_join(output), "");
    }
  }

  // The images read out of a reply line.
  export class TestImageResponse extends unittest.TestCase {
    // A reply with a checkerboard PNG of 88 bytes as base64 is read whole.
    test_recorded_image(): void {
      const json = { data: [{ b64_json: constants.recorded_png }] };
      this.assertEqual(provider.image_response(reply_build(json)), json);
    }

    // An image given by url is read with its revised prompt.
    test_url_kept(): void {
      const image = {
        url: "https://images.example.test/gatehouse.png",
        revised_prompt: "A gatehouse at dusk.",
      };
      const json = { data: [image] };
      this.assertEqual(provider.image_response(reply_build(json)), json);
    }

    // Each part that is missing or not valid is named by its path.
    test_fields_invalid(): void {
      const cases: [string, unknown][] = [
        ["json", "text"],
        ["data", {}],
        ["data", { data: [] }],
        ["data", { data: { url: "u" } }],
        ["image", { data: [5] }],
        ["image", { data: [{}] }],
        ["image", { data: [{ revised_prompt: "p" }] }],
        ["image_base64", { data: [{ b64_json: 5 }] }],
        ["second_url", { data: [{ url: "u" }, { url: 5 }] }],
        ["image_prompt", { data: [{ url: "u", revised_prompt: 1 }] }],
      ];
      for (const [suffix, json] of cases) {
        const error = thrown_get(() =>
          provider.image_response(reply_build(json)),
        );
        const expected = gold_text(`provider_field_invalid_${suffix}`);
        this.assertEqual(error.message, expected);
      }
    }
  }

  // The conversion of MCP tools into flat function tools.
  export class TestToolsConvert extends unittest.TestCase {
    // Each tool keeps its name, text and schema, in order, and not `_meta`.
    test_flat_tools(): void {
      const create = tool_make(
        "browser_db_create",
        "Create an empty database. The name is a C identifier.",
        "db",
      );
      const restart = tool_make(
        "server_system_restart",
        "Restart the server process in place, keeping its pid, serving " +
          "the named main loop file. Debug mode.",
        "main_loop",
      );
      const console_run: mcp.Tool = {
        ...tool_make(
          "browser_console_run",
          "Run one command line in the debug console's dash and return its " +
            "output until the next prompt or the timeout. Debug mode.",
          "text",
        ),
        _meta: { xsjs: { permit: true } },
      };
      const converted = provider.tools_convert([create, restart, console_run]);
      this.assertEqual(converted, [
        {
          type: "function",
          name: "browser_db_create",
          description: create.description,
          parameters: {
            type: "object",
            properties: { db: { type: "string" } },
            required: ["db"],
          },
        },
        {
          type: "function",
          name: "server_system_restart",
          description: restart.description,
          parameters: {
            type: "object",
            properties: { main_loop: { type: "string" } },
            required: ["main_loop"],
          },
        },
        {
          type: "function",
          name: "browser_console_run",
          description: console_run.description,
          parameters: {
            type: "object",
            properties: { text: { type: "string" } },
            required: ["text"],
          },
        },
      ]);
    }

    // No tools convert to no function tools.
    test_empty_list(): void {
      this.assertEqual(provider.tools_convert([]), []);
    }
  }
}

Object.freeze(test_provider);
