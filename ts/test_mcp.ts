// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the Model Context Protocol of the AI worker: the methods, errors
// and sleeping tools of the server, the requests of the client and the
// reading of its replies, and the set of clients, compared with the recorded
// transcripts where they hold the value.

namespace test_mcp {
  // The test type prefix, the identities and the texts the transcripts hold.
  const constants = Object.freeze({
    type_prefix: "mcp_test.",
    client_name: "hyperposition-engine",
    browser_name: "xsjs-browser",
    server_name: "xsjs-server",
    version: "0",
    boot_initialize:
      '{"0":{"t":"mcp","i":1},"jsonrpc":"2.0","id":1,"method":"initialize",' +
      '"params":{"protocolVersion":"2025-06-18","capabilities":{},' +
      '"clientInfo":{"name":"hyperposition-engine","version":"0"}}}',
    boot_answer:
      '{"0":{"t":"mcp","r":1},"jsonrpc":"2.0","id":1,"result":{' +
      '"protocolVersion":"2025-06-18","capabilities":{"tools":{}},' +
      '"serverInfo":{"name":"xsjs-browser","version":"0"}}}',
    boot_initialized:
      '{"0":{"t":"mcp"},"jsonrpc":"2.0",' +
      '"method":"notifications/initialized"}',
    boot_list:
      '{"0":{"t":"mcp","i":2},"jsonrpc":"2.0","id":2,' +
      '"method":"tools/list"}',
    kv_tool:
      '{"name":"kv_get","description":"Read the value a Key-Value-Ref ' +
      'names, /$db/$key, as text.","inputSchema":{"type":"object",' +
      '"properties":{"ref":{"type":"string"}},"required":["ref"]}}',
    stdio_initialize:
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{' +
      '"protocolVersion":"2025-06-18","capabilities":{},' +
      '"clientInfo":{"name":"external-agent","version":"0"}}}',
    stdio_answer:
      '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",' +
      '"capabilities":{"tools":{}},' +
      '"serverInfo":{"name":"xsjs-server","version":"0"}}}',
    stdio_initialized:
      '{"jsonrpc":"2.0","method":"notifications/initialized"}',
    stdio_list: '{"jsonrpc":"2.0","id":2,"method":"tools/list"}',
    stdio_tools:
      '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"source_put",' +
      '"description":"Write a main loop file into the server\'s main_loop ' +
      'directory for system_restart to serve. Debug mode.",' +
      '"inputSchema":{"type":"object","properties":{' +
      '"name":{"type":"string"},"text":{"type":"string"}},' +
      '"required":["name","text"]},"_meta":{"xsjs":{"permit":true}}},' +
      '{"name":"system_restart","description":"Restart the server process ' +
      "in place, keeping its pid, serving the named main loop file. " +
      'Debug mode.","inputSchema":{"type":"object","properties":{' +
      '"main_loop":{"type":"string"}},"required":["main_loop"]},' +
      '"_meta":{"xsjs":{"permit":true}}}]}}',
    stdio_ping: '{"jsonrpc":"2.0","id":3,"method":"ping"}',
    stdio_pong: '{"jsonrpc":"2.0","id":3,"result":{}}',
    stdio_restart:
      '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{' +
      '"name":"system_restart","arguments":{"main_loop":"main_loop.py"}}}',
    stdio_refusal:
      '{"jsonrpc":"2.0","id":4,"error":{"code":-32000,"message":' +
      '"system_restart needs a permit and stdio has no UI to ask"}}',
    script_text:
      '{"sha256":"dbc909cf0e2e7954d586c06b3291728e527d5dee4c109409fcb501e' +
      '200756626","seq":5}',
    script_answer:
      '{"0":{"t":"mcp","r":1},"jsonrpc":"2.0","id":1,"result":{"content":[' +
      '{"type":"text","text":"{\\"sha256\\":\\"dbc909cf0e2e7954d586c06b3291' +
      '728e527d5dee4c109409fcb501e200756626\\",\\"seq\\":5}"}]}}',
    console_text: '{"output":"hi\\n","timed_out":false}',
    console_answer:
      '{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text",' +
      '"text":"{\\"output\\":\\"hi\\\\n\\",\\"timed_out\\":false}"}]}}',
    console_call:
      '{"0":{"type":"mcp","id":1},"jsonrpc":"2.0","id":1,' +
      '"method":"tools/call","params":{"name":"console_run",' +
      '"arguments":{"text":"echo hi","timeout_seconds":5}}}',
    fault_call:
      '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{' +
      '"name":"kv_get","arguments":{"ref":"/metaverse/nothing"}}}',
  });

  // An object of fields by name.
  type Fields = { [key: string]: unknown };

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // A type that no other test registers, which the bench runs on its thread.
  function type_fresh(): string {
    types_made += 1;
    return `${constants.type_prefix}${types_made}`;
  }

  // Registers a handler for a new type and returns that type.
  function handler_fresh(fn: dispatch.Handler): string {
    const type = type_fresh();
    dispatch.handler_register(type, 0, fn);
    return type;
  }

  // A port double: it keeps what the queue posts and hands it lines.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    private receiver: ((line: lines.Line) => void) | undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the queue as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
    }
  }

  // A synchronous queue of the thread `ai` with doubles of `server` and `ui`.
  interface QueueBench {
    tasks: queue.TaskQueue;
    far: PortDouble;
    near: PortDouble;
  }

  // Makes a bench whose owner table runs the test types on its own thread.
  function bench_make(): QueueBench {
    const owners: queue.OwnerTable = { [constants.type_prefix]: "ai" };
    const tasks = new queue.TaskQueue("ai", owners, true);
    const far = new PortDouble();
    const near = new PortDouble();
    tasks.port_add("server", far);
    tasks.port_add("ui", near);
    return { tasks, far, near };
  }

  // A client of the tests whose server the owner given reaches.
  function client_make(
    bench: QueueBench,
    owner: queue.ThreadName,
  ): mcp.Client {
    return new mcp.Client(
      constants.client_name,
      constants.version,
      bench.tasks,
      owner,
    );
  }

  // A server with the name the boot transcript gives the browser's.
  function browser_make(): mcp.Server {
    return new mcp.Server(constants.browser_name, constants.version);
  }

  // A server with the name the stdio transcript gives the Python server.
  function server_make(): mcp.Server {
    return new mcp.Server(constants.server_name, constants.version);
  }

  // A line with no blobs of the type, header options and payload given.
  function line_build(
    type: string,
    options: { id?: number; reply?: number; full?: boolean },
    payload: Fields,
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), [], payload);
  }

  // Runs the function as the handler of a notification from `server`.
  function task_run(
    bench: QueueBench,
    fn: () => dispatch.Sleep | undefined,
  ): void {
    const type = handler_fresh(() => fn());
    bench.far.line_send(line_build(type, {}, {}));
  }

  // Submits one request inside a task that sleeps on it, and returns its id.
  function request_run(bench: QueueBench, send: () => number): number {
    let id = 0;
    task_run(bench, () => {
      id = send();
      return dispatch.task_sleep(null, [id], type_fresh());
    });
    return id;
  }

  // Submits an empty request of the type to `server` and returns its id.
  function far_submit(bench: QueueBench, type: string): number {
    return bench.tasks.task_submit(line_build(type, {}, {}), "server");
  }

  // Answers with an empty payload the request posted to `server` at the index.
  function request_answer(bench: QueueBench, index: number): void {
    const request = bench.far.posted[index];
    const type = jslb.field_get(request[0], "type") as string;
    const id = jslb.field_get(request[0], "id") as number;
    bench.far.line_send(line_build(type, { reply: id }, {}));
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

  // A recorded message or tool read back from its JSON text.
  function text_read(text: string): Fields {
    return JSON.parse(text) as Fields;
  }

  // A recorded line read back from its JSON text.
  function line_read(text: string): lines.Line {
    return JSON.parse(text) as lines.Line;
  }

  // A tool of the tests with the name given, which takes any object.
  function tool_make(name: string): mcp.Tool {
    return {
      name,
      description: "A tool of the tests.",
      inputSchema: { type: "object", properties: {} },
    };
  }

  // The function of a tool or a wake that the test does not expect to run.
  function call_unexpected(): mcp.ToolResult {
    throw new Error("The test did not expect this function to run.");
  }

  // A `tools/call` request of the tool on the arguments, with the id given.
  function call_message(id: number, name: string, args: Fields): Fields {
    return {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: { name, arguments: args },
    };
  }

  // The `tools/call` line of a type whose line id is its `JSON-RPC` id.
  function call_line(
    type: string,
    id: number,
    name: string,
    args: Fields,
  ): lines.Line {
    return line_build(type, { id }, call_message(id, name, args));
  }

  // The `mcp` reply line to request `id` carrying the payload given.
  function reply_build(id: number, payload: Fields): lines.Line {
    return line_build("mcp", { reply: id }, payload);
  }

  // The replies a wake line carries.
  function replies_of(line: lines.Line): lines.Line[] {
    return line.replies as lines.Line[];
  }

  // What a server answers to a message, as JSON text.
  function handled_text(server: mcp.Server, message: Fields): string {
    const answer = server.message_handle(message as unknown as mcp.Message);
    return utility.json_text(answer);
  }

  // An error response with no data, as JSON text.
  function refusal_text(id: unknown, code: number, message: string): string {
    return utility.json_text({ jsonrpc: "2.0", id, error: { code, message } });
  }

  // The frozen surface of the module and the revision it pins.
  export class TestSurface extends unittest.TestCase {
    // The module and its constants are frozen and it exports its classes.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(mcp));
      this.assertTrue(Object.isFrozen(mcp.constants));
      this.assertEqual(Object.keys(mcp).sort(), [
        "Client",
        "ClientSet",
        "Server",
        "constants",
      ]);
    }

    // The revision is the one the boot transcript records.
    test_version_pinned(): void {
      this.assertEqual(mcp.constants.protocol_version, "2025-06-18");
    }
  }

  // The methods of the server, compared with the recorded answers.
  export class TestServerMethods extends unittest.TestCase {
    // `initialize` on the line and on stdio answers as recorded.
    test_initialize_recorded(): void {
      const browser = browser_make();
      const reply = browser.line_handle(line_read(constants.boot_initialize));
      this.assertEqual(
        jslb.line_render(reply as lines.Line),
        constants.boot_answer,
      );
      const server = server_make();
      this.assertEqual(
        handled_text(server, text_read(constants.stdio_initialize)),
        constants.stdio_answer,
      );
    }

    // `ping` answers an empty result as the stdio session records.
    test_ping_recorded(): void {
      const server = server_make();
      this.assertEqual(
        handled_text(server, text_read(constants.stdio_ping)),
        constants.stdio_pong,
      );
    }

    // `tools/list` lists the tools in order, `_meta` kept, as recorded.
    test_list_recorded(): void {
      const server = server_make();
      const recorded = text_read(constants.stdio_tools);
      const listed = recorded.result as { tools: mcp.Tool[] };
      for (const tool of listed.tools) {
        server.tool_register(tool, call_unexpected);
      }
      this.assertEqual(
        handled_text(server, text_read(constants.stdio_list)),
        constants.stdio_tools,
      );
    }

    // `tools/call` runs the tool on its arguments and answers as recorded.
    test_call_recorded(): void {
      const server = browser_make();
      const args = { ref: "/_files/script/step_tide.js" };
      const seen: Fields[] = [];
      server.tool_register(tool_make("kv_put"), (given) => {
        seen.push(given);
        return { content: [{ type: "text", text: constants.script_text }] };
      });
      const reply = server.line_handle(call_line("mcp", 1, "kv_put", args));
      this.assertEqual(
        jslb.line_render(reply as lines.Line),
        constants.script_answer,
      );
      this.assertEqual(seen, [args]);
    }

    // A notification, known or not, gets no answer.
    test_notification_none(): void {
      const server = browser_make();
      const line = line_read(constants.boot_initialized);
      this.assertEqual(server.line_handle(line), undefined);
      const recorded = text_read(constants.stdio_initialized);
      const message = recorded as unknown as mcp.Message;
      this.assertEqual(server.message_handle(message), undefined);
      const other: mcp.Message = {
        jsonrpc: "2.0",
        method: "notifications/cancelled",
      };
      this.assertEqual(server.message_handle(other), undefined);
    }

    // A call with no arguments runs the tool on an empty object.
    test_arguments_absent(): void {
      const server = browser_make();
      const seen: Fields[] = [];
      server.tool_register(tool_make("render"), (given) => {
        seen.push(given);
        return { content: [] };
      });
      const message = {
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: { name: "render" },
      };
      this.assertEqual(
        handled_text(server, message),
        utility.json_text({ jsonrpc: "2.0", id: 2, result: { content: [] } }),
      );
      this.assertEqual(seen, [{}]);
    }

    // The error flag a tool sets reaches the result.
    test_error_flag(): void {
      const server = browser_make();
      const result: mcp.ToolResult = {
        content: [{ type: "text", text: "denied" }],
        isError: true,
      };
      server.tool_register(tool_make("console_run"), () => result);
      const answer = server.message_handle(
        call_message(3, "console_run", {}) as unknown as mcp.Message,
      );
      this.assertEqual(answer, { jsonrpc: "2.0", id: 3, result });
    }
  }

  // The error responses of the server, with its codes and texts.
  export class TestServerErrors extends unittest.TestCase {
    // A message that is not a valid request gets `-32600`.
    test_request_invalid(): void {
      const server = browser_make();
      const text = i18n("mcp.request_invalid");
      const cases: [Fields, unknown][] = [
        [{ jsonrpc: "1.0", id: 5, method: "ping" }, 5],
        [{ jsonrpc: "2.0", id: 5 }, 5],
        [{ jsonrpc: "2.0", id: null, method: "ping" }, null],
        [{ jsonrpc: "2.0", id: true, method: "ping" }, null],
        [{ jsonrpc: "2.0", id: 1.5, method: "ping" }, null],
      ];
      for (const [message, id] of cases) {
        this.assertEqual(
          handled_text(server, message),
          refusal_text(id, -32600, text),
        );
      }
    }

    // A method that is not served gets `-32601` naming it.
    test_method_unknown(): void {
      const server = browser_make();
      const message = { jsonrpc: "2.0", id: 6, method: "resources/list" };
      this.assertEqual(
        handled_text(server, message),
        refusal_text(
          6,
          -32601,
          i18n("mcp.method_unknown", "resources/list"),
        ),
      );
    }

    // `tools/call` params that are not a name and an object get `-32602`.
    test_params_invalid(): void {
      const server = browser_make();
      server.tool_register(tool_make("kv_get"), call_unexpected);
      const call = { jsonrpc: "2.0", id: 7, method: "tools/call" };
      const cases: Fields[] = [
        call,
        { ...call, params: "kv_get" },
        { ...call, params: { name: 3, arguments: {} } },
        { ...call, params: { name: "kv_get", arguments: [] } },
        { ...call, params: { name: "kv_get", arguments: null } },
      ];
      const text = i18n("mcp.call_params");
      for (const message of cases) {
        this.assertEqual(
          handled_text(server, message),
          refusal_text(7, -32602, text),
        );
      }
    }

    // A call of a tool that is not registered gets `-32602` naming it.
    test_tool_unknown(): void {
      const server = browser_make();
      this.assertEqual(
        handled_text(server, call_message(8, "kv_get", {})),
        refusal_text(8, -32602, i18n("mcp.tool_unknown", "kv_get")),
      );
    }

    // A throw in a tool gets `-32603` with its message and its stack.
    test_tool_throw(): void {
      const server = browser_make();
      const failure = new Error("The tool failed.");
      server.tool_register(tool_make("kv_get"), () => {
        throw failure;
      });
      const answer = server.message_handle(
        call_message(9, "kv_get", {}) as unknown as mcp.Message,
      );
      this.assertEqual(answer, {
        jsonrpc: "2.0",
        id: 9,
        error: {
          code: -32603,
          message: "The tool failed.",
          data: { stack: failure.stack },
        },
      });
    }

    // A second tool of the same name is refused.
    test_tool_twice(): void {
      const server = browser_make();
      server.tool_register(tool_make("kv_get"), call_unexpected);
      const error = thrown_get(() =>
        server.tool_register(tool_make("kv_get"), call_unexpected),
      );
      this.assertEqual(error.message, i18n("mcp.tool_twice", "kv_get"));
    }
  }

  // A tool that sleeps: the request held by the sleep, answered by a wake.
  export class TestServerWakes extends unittest.TestCase {
    // `message_handle` passes the sleep of the tool on as it is.
    test_sleep_passed(): void {
      const server = browser_make();
      const wake = type_fresh();
      server.wake_register(wake, call_unexpected);
      const sleep = dispatch.task_sleep({ n: 1 }, [], wake);
      server.tool_register(tool_make("render"), () => sleep);
      const outcome = server.message_handle(
        call_message(4, "render", {}) as unknown as mcp.Message,
      );
      this.assertTrue(outcome === sleep);
    }

    // `line_handle` holds the request line beside the state of the tool.
    test_sleep_held(): void {
      const server = browser_make();
      const wake = type_fresh();
      server.wake_register(wake, call_unexpected);
      server.tool_register(tool_make("render"), () =>
        dispatch.task_sleep({ n: 1 }, [], wake),
      );
      const line = call_line("mcp", 4, "render", {});
      const outcome = server.line_handle(line) as dispatch.Sleep;
      this.assertEqual(outcome.wait_ids, []);
      this.assertEqual(outcome.then_type, wake);
      const held = outcome.state as { request: lines.Line; state: unknown };
      this.assertTrue(held.request === line);
      this.assertEqual(held.state, { n: 1 });
    }

    // The wake answers the request on its port in its name form, as recorded.
    test_wake_answers(): void {
      const bench = bench_make();
      const server = browser_make();
      const asked = type_fresh();
      const wake = type_fresh();
      const seen: unknown[] = [];
      server.wake_register(wake, (state, replies) => {
        seen.push(state, replies.length);
        return { content: [{ type: "text", text: constants.console_text }] };
      });
      server.tool_register(tool_make("console_run"), () => {
        const id = far_submit(bench, asked);
        return dispatch.task_sleep({ call: 1 }, [id], wake);
      });
      const carrier = handler_fresh((line) => server.line_handle(line));
      const args = { text: "echo hi", timeout_seconds: 5 };
      const message = call_message(1, "console_run", args);
      bench.far.line_send(line_build(carrier, { id: 1, full: true }, message));
      this.assertEqual(bench.far.posted.length, 1);
      request_answer(bench, 0);
      this.assertEqual(seen, [{ call: 1 }, 1]);
      this.assertEqual(bench.far.posted.length, 2);
      const answer = bench.far.posted[1];
      this.assertEqual(answer[0], { type: carrier, reply: 1 });
      this.assertEqual(
        utility.json_text(jslb.payload_of(answer)),
        constants.console_answer,
      );
    }

    // A wake may sleep again, and the last wake answers.
    test_wake_chain(): void {
      const bench = bench_make();
      const server = browser_make();
      const asked = type_fresh();
      const first = type_fresh();
      const second = type_fresh();
      const states: unknown[] = [];
      server.wake_register(first, (state) => {
        states.push(state);
        const id = far_submit(bench, asked);
        return dispatch.task_sleep({ step: 2 }, [id], second);
      });
      server.wake_register(second, (state) => {
        states.push(state);
        return { content: [], isError: true };
      });
      server.tool_register(tool_make("image_make"), () => {
        const id = far_submit(bench, asked);
        return dispatch.task_sleep({ step: 1 }, [id], first);
      });
      const carrier = handler_fresh((line) => server.line_handle(line));
      bench.far.line_send(call_line(carrier, 3, "image_make", {}));
      request_answer(bench, 0);
      this.assertEqual(bench.far.posted.length, 2);
      request_answer(bench, 1);
      this.assertEqual(states, [{ step: 1 }, { step: 2 }]);
      const answer = bench.far.posted[2];
      this.assertEqual(answer[0], { t: carrier, r: 3 });
      this.assertEqual(jslb.payload_of(answer), {
        jsonrpc: "2.0",
        id: 3,
        result: { content: [], isError: true },
      });
    }

    // A throw in a wake answers `-32603` with its message and its stack.
    test_wake_throw(): void {
      const bench = bench_make();
      const server = browser_make();
      const asked = type_fresh();
      const wake = type_fresh();
      const failure = new Error("The wake failed.");
      server.wake_register(wake, () => {
        throw failure;
      });
      server.tool_register(tool_make("render"), () => {
        const id = far_submit(bench, asked);
        return dispatch.task_sleep(null, [id], wake);
      });
      const carrier = handler_fresh((line) => server.line_handle(line));
      bench.far.line_send(call_line(carrier, 2, "render", {}));
      request_answer(bench, 0);
      const answer = bench.far.posted[1];
      this.assertEqual(answer[0], { t: carrier, r: 2 });
      this.assertEqual(jslb.payload_of(answer), {
        jsonrpc: "2.0",
        id: 2,
        error: {
          code: -32603,
          message: "The wake failed.",
          data: { stack: failure.stack },
        },
      });
    }

    // A sleep whose wake type the server did not register throws.
    test_wake_unknown(): void {
      const server = browser_make();
      const stray = type_fresh();
      server.tool_register(tool_make("render"), () =>
        dispatch.task_sleep(null, [], stray),
      );
      const error = thrown_get(() =>
        server.line_handle(call_line("mcp", 1, "render", {})),
      );
      this.assertEqual(error.message, i18n("mcp.wake_unknown", stray));
      const bench = bench_make();
      const asked = type_fresh();
      const wake = type_fresh();
      server.wake_register(wake, () => dispatch.task_sleep(null, [], stray));
      server.tool_register(tool_make("image_make"), () => {
        const id = far_submit(bench, asked);
        return dispatch.task_sleep(null, [id], wake);
      });
      const carrier = handler_fresh((line) => server.line_handle(line));
      bench.far.line_send(call_line(carrier, 1, "image_make", {}));
      const again = thrown_get(() => request_answer(bench, 0));
      this.assertEqual(again.message, i18n("mcp.wake_unknown", stray));
    }
  }

  // The requests of the client as the recorded boot sends them.
  export class TestClientRequests extends unittest.TestCase {
    // The handshake and the tool list go out and come back as recorded.
    test_handshake_recorded(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const browser = browser_make();
      const kv_tool = text_read(constants.kv_tool) as unknown as mcp.Tool;
      browser.tool_register(kv_tool, call_unexpected);
      const read: mcp.Tool[][] = [];
      const listed = handler_fresh((line) => {
        read.push(client.tools_read(replies_of(line)[0]));
        return undefined;
      });
      const answered = handler_fresh((line) => {
        client.initialized_send(replies_of(line)[0]);
        return dispatch.task_sleep(null, [client.tools_list()], listed);
      });
      task_run(bench, () =>
        dispatch.task_sleep(null, [client.initialize_send()], answered),
      );
      const answer = browser.line_handle(bench.far.posted[0]) as lines.Line;
      this.assertEqual(jslb.line_render(answer), constants.boot_answer);
      bench.far.line_send(answer);
      const tools = browser.line_handle(bench.far.posted[2]) as lines.Line;
      bench.far.line_send(tools);
      this.assertEqual(
        bench.far.posted.map((line) => jslb.line_render(line)),
        [
          constants.boot_initialize,
          constants.boot_initialized,
          constants.boot_list,
        ],
      );
      this.assertEqual(read, [[kv_tool]]);
      this.assertEqual(client.tools_cached(), [kv_tool]);
    }

    // A client of full names sends its lines in full names.
    test_names_full(): void {
      const bench = bench_make();
      const client = new mcp.Client(
        constants.client_name,
        constants.version,
        bench.tasks,
        "server",
        true,
      );
      const args = { text: "echo hi", timeout_seconds: 5 };
      request_run(bench, () => client.tool_call("console_run", args));
      this.assertEqual(
        jslb.line_render(bench.far.posted[0]),
        constants.console_call,
      );
    }

    // An `initialize` answer of another revision is refused, nothing sent.
    test_version_refused(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const id = request_run(bench, () => client.initialize_send());
      const result = {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: {
          name: constants.server_name,
          version: constants.version,
        },
      };
      const reply = reply_build(id, { jsonrpc: "2.0", id: 1, result });
      const error = thrown_get(() => client.initialized_send(reply));
      this.assertEqual(
        error.message,
        i18n("mcp.version_refused", "2024-11-05", "2025-06-18"),
      );
      this.assertEqual(bench.far.posted.length, 1);
    }

    // The tools of a client cannot be had before they are read.
    test_tools_unread(): void {
      const client = client_make(bench_make(), "server");
      const error = thrown_get(() => client.tools_cached());
      this.assertEqual(error.message, i18n("mcp.tools_unread", "server"));
    }

    // A `tools/list` result that is not a list of tools is refused.
    test_tools_invalid(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const cases: Fields[] = [
        { tools: {} },
        { tools: [{ name: "kv_get", inputSchema: { type: "object" } }] },
      ];
      for (const [index, result] of cases.entries()) {
        const id = request_run(bench, () => client.tools_list());
        const payload = { jsonrpc: "2.0", id: index + 1, result };
        const error = thrown_get(() =>
          client.tools_read(reply_build(id, payload)),
        );
        this.assertEqual(
          error.message,
          i18n(
            "mcp.result_invalid",
            "tools/list",
            id,
            utility.json_text(result),
          ),
        );
      }
    }
  }

  // The reading of the replies of a client, and every reply it refuses.
  export class TestClientReplies extends unittest.TestCase {
    // A result is read with the error flag when the server sends one.
    test_result_read(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const first = request_run(bench, () =>
        client.tool_call("source_put", {}),
      );
      const flagged = {
        content: [{ type: "text", text: "{}" }],
        isError: false,
      };
      const read = client.result_of(
        reply_build(first, { jsonrpc: "2.0", id: 1, result: flagged }),
      );
      this.assertEqual(read, flagged);
      const second = request_run(bench, () => client.tool_call("render", {}));
      const plain = { content: [{ type: "text", text: "{}" }] };
      const bare = client.result_of(
        reply_build(second, { jsonrpc: "2.0", id: 2, result: plain }),
      );
      this.assertEqual(bare, plain);
      this.assertFalse(Object.hasOwn(bare, "isError"));
    }

    // A result whose content or error flag is not valid is refused.
    test_result_invalid(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const cases: Fields[] = [
        { content: "{}" },
        { content: [], isError: "no" },
      ];
      for (const [index, result] of cases.entries()) {
        const id = request_run(bench, () => client.tool_call("render", {}));
        const payload = { jsonrpc: "2.0", id: index + 1, result };
        const error = thrown_get(() =>
          client.result_of(reply_build(id, payload)),
        );
        this.assertEqual(
          error.message,
          i18n(
            "mcp.result_invalid",
            "tools/call",
            id,
            utility.json_text(result),
          ),
        );
      }
    }

    // A reply to no request of the client, or read twice, is refused.
    test_reply_unknown(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const stray = thrown_get(() => client.result_of(reply_build(9, {})));
      this.assertEqual(stray.message, i18n("mcp.reply_unknown", 9));
      const id = request_run(bench, () => client.tool_call("render", {}));
      const payload = { jsonrpc: "2.0", id: 1, result: { content: [] } };
      const reply = reply_build(id, payload);
      client.result_of(reply);
      const again = thrown_get(() => client.result_of(reply));
      this.assertEqual(again.message, i18n("mcp.reply_unknown", id));
    }

    // A reply read as the answer of another method is refused.
    test_reply_method(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const id = request_run(bench, () => client.tools_list());
      const payload = { jsonrpc: "2.0", id: 1, result: { tools: [] } };
      const error = thrown_get(() =>
        client.result_of(reply_build(id, payload)),
      );
      this.assertEqual(
        error.message,
        i18n("mcp.reply_method", id, "tools/list", "tools/call"),
      );
    }

    // An error response throws with the error the server sent.
    test_reply_error(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const args = { main_loop: "main_loop.py" };
      const id = request_run(bench, () =>
        client.tool_call("system_restart", args),
      );
      const recorded = text_read(constants.stdio_refusal);
      const payload = { jsonrpc: "2.0", id: 1, error: recorded.error };
      const error = thrown_get(() =>
        client.result_of(reply_build(id, payload)),
      );
      this.assertEqual(
        error.message,
        i18n("mcp.reply_error", id, utility.json_text(recorded.error)),
      );
    }

    // A reply that is not a response to the id that was sent is refused.
    test_response_invalid(): void {
      const bench = bench_make();
      const client = client_make(bench, "server");
      const refusal = { code: -32600, message: i18n("mcp.request_invalid") };
      const cases: Fields[] = [
        { jsonrpc: "1.0", id: 1, result: {} },
        { jsonrpc: "2.0", id: 1, result: {} },
        { jsonrpc: "2.0", id: 3 },
        { jsonrpc: "2.0", id: 4, result: [] },
        { jsonrpc: "2.0", id: null, error: refusal },
      ];
      for (const [index, payload] of cases.entries()) {
        const id = request_run(bench, () => client.tool_call("render", {}));
        const error = thrown_get(() =>
          client.result_of(reply_build(id, payload)),
        );
        this.assertEqual(
          error.message,
          i18n(
            "mcp.response_invalid",
            id,
            index + 1,
            utility.json_text(payload),
          ),
        );
      }
    }
  }

  // The set of clients: prefixed tools, routed calls and their errors.
  export class TestClientSet extends unittest.TestCase {
    // The tools of every client are listed in order under dotted names.
    test_tools_prefixed(): void {
      const bench = bench_make();
      const browser = client_make(bench, "ui");
      const server = client_make(bench, "server");
      const kv_tool = text_read(constants.kv_tool);
      const recorded = text_read(constants.stdio_tools);
      const near_id = request_run(bench, () => browser.tools_list());
      const list = { jsonrpc: "2.0", id: 1, result: { tools: [kv_tool] } };
      browser.tools_read(reply_build(near_id, list));
      request_run(bench, () => server.initialize_send());
      const far_id = request_run(bench, () => server.tools_list());
      server.tools_read(reply_build(far_id, recorded));
      const set = new mcp.ClientSet();
      set.client_add("browser", browser);
      set.client_add("server", server);
      const listed = (recorded.result as { tools: Fields[] }).tools;
      this.assertEqual(set.tools_cached(), [
        { ...kv_tool, name: "browser.kv_get" },
        { ...listed[0], name: "server.source_put" },
        { ...listed[1], name: "server.system_restart" },
      ]);
    }

    // A call goes to the client of its prefix by the bare name, and back.
    test_calls_routed(): void {
      const bench = bench_make();
      const browser = client_make(bench, "ui");
      const server = client_make(bench, "server");
      const set = new mcp.ClientSet();
      set.client_add("browser", browser);
      set.client_add("server", server);
      const ids: number[] = [];
      task_run(bench, () => {
        const nothing = { ref: "/metaverse/nothing" };
        const restart = { main_loop: "main_loop.py" };
        ids.push(set.tool_call("browser.kv_get", nothing));
        ids.push(set.tool_call("server.system_restart", restart));
        return dispatch.task_sleep(null, [...ids], type_fresh());
      });
      const sent = bench.near.posted[0];
      this.assertEqual(
        utility.json_text(jslb.payload_of(sent)),
        constants.fault_call,
      );
      const recorded = text_read(constants.stdio_restart);
      const routed = jslb.payload_of(bench.far.posted[0]);
      this.assertEqual(routed.params, recorded.params);
      const tools = browser_make();
      const result: mcp.ToolResult = {
        content: [{ type: "text", text: "{}" }],
      };
      tools.tool_register(tool_make("kv_get"), () => result);
      const answer = tools.line_handle(sent) as lines.Line;
      this.assertEqual(set.result_of(answer), result);
      const refusal = text_read(constants.stdio_refusal);
      const payload = { jsonrpc: "2.0", id: 1, error: refusal.error };
      const error = thrown_get(() =>
        set.result_of(reply_build(ids[1], payload)),
      );
      this.assertEqual(
        error.message,
        i18n("mcp.reply_error", ids[1], utility.json_text(refusal.error)),
      );
    }

    // A prefix that is empty, dotted or already added is refused.
    test_prefix_refused(): void {
      const bench = bench_make();
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(bench, "server"));
      for (const prefix of ["", "browser.tools", "server"]) {
        const error = thrown_get(() =>
          set.client_add(prefix, client_make(bench, "ui")),
        );
        this.assertEqual(error.message, i18n("mcp.prefix_refused", prefix));
      }
    }

    // A name with no dot or with a prefix of no client is refused.
    test_prefix_unknown(): void {
      const bench = bench_make();
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(bench, "server"));
      for (const name of ["kv_get", "browser.kv_get"]) {
        const error = thrown_get(() => set.tool_call(name, {}));
        this.assertEqual(error.message, i18n("mcp.prefix_unknown", name));
      }
      this.assertEqual(bench.far.posted.length, 0);
    }

    // A reply to no call of the set is refused.
    test_reply_stray(): void {
      const set = new mcp.ClientSet();
      const error = thrown_get(() => set.result_of(reply_build(7, {})));
      this.assertEqual(error.message, i18n("mcp.reply_unknown", 7));
    }
  }
}

Object.freeze(test_mcp);
