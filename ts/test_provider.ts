// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the provider door: the request lines it builds, the reading of the
// reply lines and the conversion of MCP tools. The key it keeps in memory is
// tested in `test_provider_key`, whose fresh realm has none set.
// The request lines it expects, in the full names of debug mode, the reply
// lines it reads and the texts of its refusals are its gold in
// `test_settings.json`, read through the harness.

namespace test_provider {
  // A provider's address, key and models, and values of the castle turn.
  const constants = Object.freeze({
    base_url: "https://api.x.ai/v1",
    key: "xai-SYNTHETIC-KEY",
    chat_model: "grok-4",
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

  // A text of this module's gold, a run time `{n}` left for the test to fill.
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

  // The headers with their names in lower case, as HTTP compares them.
  function headers_lower(value: unknown): FieldTable {
    const lowered: FieldTable = {};
    for (const [name, text] of Object.entries(value as FieldTable)) {
      lowered[name.toLowerCase()] = text;
    }
    return lowered;
  }

  // A tool call that every check accepts.
  function call_valid(): FieldTable {
    return {
      id: "call_1",
      type: "function",
      function: { name: "browser.script_run", arguments: "{}" },
    };
  }

  // An assistant message that calls that tool.
  function message_valid(): FieldTable {
    return { role: "assistant", content: null, tool_calls: [call_valid()] };
  }

  // A choice that holds that message.
  function choice_valid(): FieldTable {
    return { index: 0, message: message_valid(), finish_reason: "tool_calls" };
  }

  // A chat body with the one choice given.
  function chat_body(choice: unknown): FieldTable {
    return { id: "chatcmpl-synthetic-3", model: "grok-4", choices: [choice] };
  }

  // A chat body whose message has the fields given in place of its own.
  function message_with(fields: FieldTable): FieldTable {
    return chat_body({
      ...choice_valid(),
      message: { ...message_valid(), ...fields },
    });
  }

  // A chat body whose tool call has the fields given in place of its own.
  function call_with(fields: FieldTable): FieldTable {
    return message_with({ tool_calls: [{ ...call_valid(), ...fields }] });
  }

  // The chat body of the castle turn that runs the bootstrap script.
  function recorded_calling(): FieldTable {
    return {
      id: "chatcmpl-synthetic-3",
      model: constants.chat_model,
      choices: [
        {
          index: 0,
          message: {
            role: "assistant",
            content: null,
            tool_calls: [
              {
                id: "call_1",
                type: "function",
                function: {
                  name: "browser.script_run",
                  arguments: constants.bootstrap_arguments,
                },
              },
            ],
          },
          finish_reason: "tool_calls",
        },
      ],
    };
  }

  // The chat body of the castle turn that ends it with the subtitle.
  function recorded_stop(): FieldTable {
    return {
      id: "chatcmpl-synthetic-60",
      model: constants.chat_model,
      choices: [
        {
          index: 0,
          message: { role: "assistant", content: constants.subtitle },
          finish_reason: "stop",
        },
      ],
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
    // Checks a request line against the gold, its body the one given.
    line_assert(line: lines.Line, name: string, request: object): void {
      const expected = gold_line(name);
      this.assertEqual(line[0], expected[0]);
      this.assertEqual(
        Object.keys(line).join(","),
        "0,method,url,headers,json",
      );
      this.assertEqual(line.method, expected.method);
      this.assertEqual(line.url, expected.url);
      this.assertEqual(headers_lower(line.headers), expected.headers);
      this.assertTrue(line.json === request);
    }

    // A chat request is one `http.request` line with no id.
    test_chat_line(): void {
      const request: provider.ChatRequest = {
        model: constants.chat_model,
        messages: [{ role: "user", content: "1" }],
        tool_choice: "auto",
      };
      const line = provider.chat_request(
        constants.base_url,
        constants.key,
        request,
      );
      this.line_assert(line, "chat_request", request);
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
      this.line_assert(line, "image_request", request);
    }

    // The key given is the one the header carries.
    test_key_carried(): void {
      const request: provider.ChatRequest = {
        model: constants.chat_model,
        messages: [],
      };
      for (const key of ["first", ""]) {
        const line = provider.chat_request(constants.base_url, key, request);
        this.assertEqual(
          headers_lower(line.headers).authorization,
          `Bearer ${key}`,
        );
      }
    }
  }

  // The chat completion read out of a reply line.
  export class TestChatResponse extends unittest.TestCase {
    // The castle turn's reply that calls a tool is read whole.
    test_recorded_calls(): void {
      const response = provider.chat_response(reply_build(recorded_calling()));
      this.assertEqual(response, recorded_calling());
    }

    // The castle turn's reply that ends the turn has no tool calls.
    test_recorded_stop(): void {
      const response = provider.chat_response(reply_build(recorded_stop()));
      this.assertEqual(response, recorded_stop());
      const message = response.choices[0].message;
      this.assertFalse(Object.hasOwn(message, "tool_calls"));
    }

    // A reply in full names is read as one in short names.
    test_full_names(): void {
      const reply = gold_line("reply_full");
      reply.json = recorded_stop();
      this.assertEqual(provider.chat_response(reply), recorded_stop());
    }

    // A tool message's call id is kept.
    test_call_id(): void {
      const message = { role: "tool", content: "{}", tool_call_id: "call_1" };
      const choice = { ...choice_valid(), message };
      const response = provider.chat_response(reply_build(chat_body(choice)));
      this.assertEqual(response.choices[0].message, message);
    }

    // An `error` line or a line of another type is refused by its type.
    test_type_refused(): void {
      for (const suffix of ["error", "kv_get"]) {
        const line = gold_line(`refused_${suffix}`);
        const expected = gold_text(`provider_reply_type_${suffix}`);
        const chat = thrown_get(() => provider.chat_response(line));
        this.assertEqual(chat.message, expected);
        const image = thrown_get(() => provider.image_response(line));
        this.assertEqual(image.message, expected);
      }
    }

    // Each part that is missing or not valid is named by its path.
    test_fields_invalid(): void {
      const choice = choice_valid();
      const cases: [string, unknown][] = [
        ["json", null],
        ["json", [1]],
        ["choices", { id: "c", model: "m" }],
        ["choices", { id: "c", model: "m", choices: [] }],
        ["id", { model: "m", choices: [choice] }],
        ["model", { id: "c", model: 5, choices: [choice] }],
        ["choice", chat_body(5)],
        ["choice_index", chat_body({ ...choice, index: "0" })],
        ["message", chat_body({ ...choice, message: [] })],
        ["message_role", message_with({ role: "robot" })],
        ["message_content", message_with({ content: 5 })],
        ["calls", message_with({ tool_calls: {} })],
        ["call", message_with({ tool_calls: [null] })],
        ["call_id", call_with({ id: 5 })],
        ["call_type", call_with({ type: "other" })],
        ["call_function", call_with({ function: "f" })],
        ["call_name", call_with({ function: {} })],
        [
          "call_arguments",
          call_with({ function: { name: "n", arguments: {} } }),
        ],
        ["message_call_id", message_with({ tool_call_id: 7 })],
        ["finish_reason", chat_body({ ...choice, finish_reason: "done" })],
      ];
      for (const [suffix, json] of cases) {
        const error = thrown_get(() =>
          provider.chat_response(reply_build(json)),
        );
        const expected = gold_text(`provider_field_invalid_${suffix}`);
        this.assertEqual(error.message, expected);
      }
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

  // The conversion of MCP tools into function tools.
  export class TestToolsConvert extends unittest.TestCase {
    // Each tool keeps its dotted name, text and schema, in order, not `_meta`.
    test_dotted_names(): void {
      const create = tool_make(
        "browser.db_create",
        "Create an empty database. The name is a C identifier.",
        "db",
      );
      const restart = tool_make(
        "server.system_restart",
        "Restart the server process in place, keeping its pid, serving " +
          "the named main loop file. Debug mode.",
        "main_loop",
      );
      const console_run: mcp.Tool = {
        ...tool_make(
          "browser.console_run",
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
          function: {
            name: "browser.db_create",
            description: create.description,
            parameters: {
              type: "object",
              properties: { db: { type: "string" } },
              required: ["db"],
            },
          },
        },
        {
          type: "function",
          function: {
            name: "server.system_restart",
            description: restart.description,
            parameters: {
              type: "object",
              properties: { main_loop: { type: "string" } },
              required: ["main_loop"],
            },
          },
        },
        {
          type: "function",
          function: {
            name: "browser.console_run",
            description: console_run.description,
            parameters: {
              type: "object",
              properties: { text: { type: "string" } },
              required: ["text"],
            },
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
