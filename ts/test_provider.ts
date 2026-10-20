// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the provider door: the request lines it builds, the reading of the
// reply lines, the conversion of MCP tools and the key it keeps in memory.

namespace test_provider {
  // The values the tests share, as the settings and the recorded turn hold.
  const constants = Object.freeze({
    base_url: "https://api.x.ai/v1",
    key: "xai-SYNTHETIC-KEY",
    chat_url: "https://api.x.ai/v1/chat/completions",
    image_url: "https://api.x.ai/v1/images/generations",
    chat_model: "grok-4",
    image_model: "grok-2-image",
    request_type: "http.request",
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
  type Fields = { [key: string]: unknown };

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

  // A reply line to request 1 carrying the JSON body, in short names.
  function reply_build(json: unknown): lines.Line {
    const header = jslb.header_make(constants.request_type, { reply: 1 });
    return jslb.line_make(header, [], {
      status: 200,
      headers: { "content-type": "application/json" },
      json,
    });
  }

  // The headers with their names in lower case, as HTTP compares them.
  function headers_lower(value: unknown): Fields {
    const lowered: Fields = {};
    for (const [name, text] of Object.entries(value as Fields)) {
      lowered[name.toLowerCase()] = text;
    }
    return lowered;
  }

  // A tool call that every check accepts.
  function call_valid(): Fields {
    return {
      id: "call_1",
      type: "function",
      function: { name: "browser.script_run", arguments: "{}" },
    };
  }

  // An assistant message that calls that tool.
  function message_valid(): Fields {
    return { role: "assistant", content: null, tool_calls: [call_valid()] };
  }

  // A choice that holds that message.
  function choice_valid(): Fields {
    return { index: 0, message: message_valid(), finish_reason: "tool_calls" };
  }

  // A chat body with the one choice given.
  function chat_body(choice: unknown): Fields {
    return { id: "chatcmpl-synthetic-3", model: "grok-4", choices: [choice] };
  }

  // A chat body whose message has the fields given in place of its own.
  function message_with(fields: Fields): Fields {
    return chat_body({
      ...choice_valid(),
      message: { ...message_valid(), ...fields },
    });
  }

  // A chat body whose tool call has the fields given in place of its own.
  function call_with(fields: Fields): Fields {
    return message_with({ tool_calls: [{ ...call_valid(), ...fields }] });
  }

  // The chat body of the recorded turn that runs the bootstrap script.
  function recorded_calling(): Fields {
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

  // The chat body of the recorded turn that ends it with the subtitle.
  function recorded_stop(): Fields {
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
    // A chat request is one `http.request` line with no id, as recorded.
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
      this.assertEqual(line[0], { t: constants.request_type });
      this.assertEqual(
        Object.keys(line).join(","),
        "0,method,url,headers,json",
      );
      this.assertEqual(line.method, "POST");
      this.assertEqual(line.url, constants.chat_url);
      this.assertEqual(headers_lower(line.headers), {
        authorization: "Bearer xai-SYNTHETIC-KEY",
        "content-type": "application/json",
      });
      this.assertTrue(line.json === request);
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
      this.assertEqual(line[0], { t: constants.request_type });
      this.assertEqual(
        Object.keys(line).join(","),
        "0,method,url,headers,json",
      );
      this.assertEqual(line.method, "POST");
      this.assertEqual(line.url, constants.image_url);
      this.assertEqual(headers_lower(line.headers), {
        authorization: "Bearer xai-SYNTHETIC-KEY",
        "content-type": "application/json",
      });
      this.assertTrue(line.json === request);
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
    // The recorded reply that calls a tool is read whole.
    test_recorded_calls(): void {
      const response = provider.chat_response(reply_build(recorded_calling()));
      this.assertEqual(response, recorded_calling());
    }

    // The recorded reply that ends the turn has no tool calls.
    test_recorded_stop(): void {
      const response = provider.chat_response(reply_build(recorded_stop()));
      this.assertEqual(response, recorded_stop());
      const message = response.choices[0].message;
      this.assertFalse(Object.hasOwn(message, "tool_calls"));
    }

    // A reply in full names is read as one in short names.
    test_full_names(): void {
      const header = jslb.header_make(constants.request_type, {
        reply: 4,
        full: true,
      });
      const reply = jslb.line_make(header, [], { json: recorded_stop() });
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
      for (const type of ["error", "kv.get"]) {
        const header = jslb.header_make(type, { reply: 1 });
        const line = jslb.line_make(header, [], {
          message: "It failed.",
          stack: "Error: It failed.",
        });
        const expected = i18n(
          "provider.reply_type",
          type,
          constants.request_type,
        );
        const chat = thrown_get(() => provider.chat_response(line));
        this.assertEqual(chat.message, expected);
        const image = thrown_get(() => provider.image_response(line));
        this.assertEqual(image.message, expected);
      }
    }

    // Each part that is missing or not valid is named by its path.
    test_fields_invalid(): void {
      const choice = choice_valid();
      const calls = "json.choices[0].message.tool_calls";
      const cases: [string, unknown][] = [
        ["json", null],
        ["json", [1]],
        ["json.choices", { id: "c", model: "m" }],
        ["json.choices", { id: "c", model: "m", choices: [] }],
        ["json.id", { model: "m", choices: [choice] }],
        ["json.model", { id: "c", model: 5, choices: [choice] }],
        ["json.choices[0]", chat_body(5)],
        ["json.choices[0].index", chat_body({ ...choice, index: "0" })],
        ["json.choices[0].message", chat_body({ ...choice, message: [] })],
        ["json.choices[0].message.role", message_with({ role: "robot" })],
        ["json.choices[0].message.content", message_with({ content: 5 })],
        [calls, message_with({ tool_calls: {} })],
        [`${calls}[0]`, message_with({ tool_calls: [null] })],
        [`${calls}[0].id`, call_with({ id: 5 })],
        [`${calls}[0].type`, call_with({ type: "other" })],
        [`${calls}[0].function`, call_with({ function: "f" })],
        [`${calls}[0].function.name`, call_with({ function: {} })],
        [
          `${calls}[0].function.arguments`,
          call_with({ function: { name: "n", arguments: {} } }),
        ],
        [
          "json.choices[0].message.tool_call_id",
          message_with({ tool_call_id: 7 }),
        ],
        [
          "json.choices[0].finish_reason",
          chat_body({ ...choice, finish_reason: "done" }),
        ],
      ];
      for (const [path, json] of cases) {
        const error = thrown_get(() =>
          provider.chat_response(reply_build(json)),
        );
        this.assertEqual(error.message, i18n("provider.field_invalid", path));
      }
    }
  }

  // The images read out of a reply line.
  export class TestImageResponse extends unittest.TestCase {
    // The recorded reply with the test pattern as base64 is read whole.
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
        ["json.data", {}],
        ["json.data", { data: [] }],
        ["json.data", { data: { url: "u" } }],
        ["json.data[0]", { data: [5] }],
        ["json.data[0]", { data: [{}] }],
        ["json.data[0]", { data: [{ revised_prompt: "p" }] }],
        ["json.data[0].b64_json", { data: [{ b64_json: 5 }] }],
        ["json.data[1].url", { data: [{ url: "u" }, { url: 5 }] }],
        [
          "json.data[0].revised_prompt",
          { data: [{ url: "u", revised_prompt: 1 }] },
        ],
      ];
      for (const [path, json] of cases) {
        const error = thrown_get(() =>
          provider.image_response(reply_build(json)),
        );
        this.assertEqual(error.message, i18n("provider.field_invalid", path));
      }
    }
  }

  // The conversion of MCP tools into function tools.
  export class TestToolsConvert extends unittest.TestCase {
    // Each tool keeps its dotted name, its text and its schema, in order.
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
      restart._meta = { xsjs: { permit: true } };
      const converted = provider.tools_convert([create, restart]);
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
      ]);
    }

    // No tools convert to no function tools.
    test_empty_list(): void {
      this.assertEqual(provider.tools_convert([]), []);
    }
  }

  // The key `hello` brings, kept in memory.
  export class TestProviderKey extends unittest.TestCase {
    // A second key replaces the first.
    test_key_replaced(): void {
      provider.key_set("first");
      this.assertEqual(provider.key_get(), "first");
      provider.key_set("second");
      this.assertEqual(provider.key_get(), "second");
    }

    // The empty key a scripted run may carry is kept as it is.
    test_key_empty(): void {
      provider.key_set("");
      this.assertEqual(provider.key_get(), "");
    }
  }
}

Object.freeze(test_provider);
