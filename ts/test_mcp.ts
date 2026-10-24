// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the Model Context Protocol of the AI worker: the methods, errors
// and sleeping tools of the server, the exception it keeps and the failure it
// returns with its answer, each wake run through the handler table the server
// registers it in; the requests of the client through a task queue double, in
// the name form the settings pick, and the reading of its replies; and the set
// of clients. The lines the tests send, the sleeps of their tools and the
// texts they expect are read from the gold record, compared with the exact
// texts of the boot's handshake and of a stdio session where they apply.

namespace test_mcp {
  // The test type prefix, the identities and the exact texts of messages.
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
    kv_tool:
      '{"name":"kv_get","description":"Read the value a Key-Value-Ref ' +
      'names, /$db/$key, as text.","inputSchema":{"type":"object",' +
      '"properties":{"ref":{"type":"string"}},"required":["ref"]}}',
    console_tool:
      '{"name":"console_run","description":"Run one command line in the ' +
      "debug console's dash and return its output until the next prompt " +
      'or the timeout. Debug mode.","inputSchema":{"type":"object",' +
      '"properties":{"text":{"type":"string"},' +
      '"timeout_seconds":{"type":"number"}},' +
      '"required":["text","timeout_seconds"]},' +
      '"_meta":{"xsjs":{"permit":true}}}',
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
      '"required":["name","text"]}},' +
      '{"name":"system_restart","description":"Restart the server process ' +
      "in place, keeping its pid, serving the named main loop file. " +
      'Debug mode.","inputSchema":{"type":"object","properties":{' +
      '"main_loop":{"type":"string"}},"required":["main_loop"]}}]}}',
    stdio_ping: '{"jsonrpc":"2.0","id":3,"method":"ping"}',
    stdio_pong: '{"jsonrpc":"2.0","id":3,"result":{}}',
    stdio_restart:
      '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{' +
      '"name":"system_restart","arguments":{"main_loop":"main_loop.py"}}}',
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
    fault_call:
      '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{' +
      '"name":"kv_get","arguments":{"ref":"/metaverse/nothing"}}}',
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // A line the queue double was given and the owner it was given for.
  type SentLine = [lines.Line, queue.ThreadName];

  // A sleep of the gold before the wake type the test made is set on it.
  type SleepPart = Omit<dispatch.Sleep, "then_type">;

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_mcp.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_mcp.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A copy of a gold line with the payload given set on it.
  function line_filled(name: string, payload: FieldTable): lines.Line {
    return { ...gold_line(name), ...payload };
  }

  // A copy of a sleep of the gold that wakes as the type given.
  function sleep_gold(name: string, then_type: string): dispatch.Sleep {
    const sleep = gold_value(`lines.${name}`) as SleepPart;
    return { ...sleep, then_type };
  }

  // The wake of a sleep the server returned, its replies the gold line's.
  function wake_make(sleep: dispatch.Sleep, name: string): lines.Line {
    const line = gold_line(name);
    Object.assign(line[0], { type: sleep.then_type });
    line.state = sleep.state;
    return line;
  }

  // The payload of a line with no blobs: every key but its header 0.
  function payload_get(line: lines.Line): FieldTable {
    const payload: FieldTable = { ...line };
    delete payload[0];
    return payload;
  }

  // A type that no other test registers, as the handler table keeps each one.
  function type_fresh(): string {
    types_made += 1;
    return `${constants.type_prefix}${types_made}`;
  }

  // A task queue double that hands out the ids the test picks.
  class QueueDouble {
    readonly submitted: SentLine[] = [];
    readonly notified: SentLine[] = [];
    private readonly ids: number[];

    // Takes the ids to hand out, in order.
    constructor(ids: number[]) {
      this.ids = [...ids];
    }

    // Keeps the line, sets the next id on its header as the queue does.
    task_submit(line: lines.Line, owner: queue.ThreadName): number {
      const id = this.ids.shift();
      if (id === undefined) {
        throw new Error("The queue double has no id left to hand out.");
      }
      const name = Object.hasOwn(line[0], "type") ? "id" : "i";
      Object.assign(line[0], { [name]: id });
      this.submitted.push([line, owner]);
      return id;
    }

    // Keeps the line and its owner.
    line_notify(line: lines.Line, owner: queue.ThreadName): void {
      this.notified.push([line, owner]);
    }
  }

  // Each line the queue double kept as its JSON text, beside its owner.
  function sent_texts(sent: SentLine[]): [string, queue.ThreadName][] {
    return sent.map(([line, owner]): [string, queue.ThreadName] => [
      JSON.stringify(line),
      owner,
    ]);
  }

  // A client of the tests whose server the owner given reaches.
  function client_make(
    tasks: QueueDouble,
    owner: queue.ThreadName,
  ): mcp.Client {
    return new mcp.Client(
      constants.client_name,
      constants.version,
      tasks as unknown as queue.TaskQueue,
      owner,
    );
  }

  // A server with the name of the browser's server, `xsjs-browser`.
  function browser_make(): mcp.Server {
    return new mcp.Server(constants.browser_name, constants.version);
  }

  // A server with the name of the Python server, `xsjs-server`.
  function server_make(): mcp.Server {
    return new mcp.Server(constants.server_name, constants.version);
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

  // A message or tool read back from its JSON text.
  function text_read(text: string): FieldTable {
    return JSON.parse(text) as FieldTable;
  }

  // A line read back from its JSON text.
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
  function call_message(
    id: number,
    name: string,
    args: FieldTable,
  ): FieldTable {
    return {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: { name, arguments: args },
    };
  }

  // What a server answers to a message, as JSON text.
  function handled_text(server: mcp.Server, message: FieldTable): string {
    const answer = server.message_handle(message as unknown as mcp.Message);
    return JSON.stringify(answer);
  }

  // An error response whose `data` is the cascade of an error with no cause.
  function exception_text(id: unknown, code: number, error: Error): string {
    const data = { message: error.message, stack: error.stack };
    const refusal = { code, message: error.message, data };
    return JSON.stringify({ jsonrpc: "2.0", id, error: refusal });
  }

  // The exception the server kept, which it must have kept.
  function kept_take(server: mcp.Server): Error {
    const error = server.failure_take();
    if (error === undefined) {
      throw new Error("The server kept no exception.");
    }
    return error;
  }

  // The failure `line_handle` returned, which must be one.
  function failure_of(
    outcome: dispatch.Reply | dispatch.Sleep | dispatch.Failure,
  ): dispatch.Failure {
    const failure = outcome as dispatch.Failure;
    if (
      outcome === undefined ||
      !(failure.error instanceof Error) ||
      Object.hasOwn(outcome, "0")
    ) {
      throw new Error("line_handle returned no failure.");
    }
    return failure;
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

    // The revision of the protocol is `2025-06-18`.
    test_version_pinned(): void {
      this.assertEqual(mcp.constants.protocol_version, "2025-06-18");
    }
  }

  // The methods of the server, compared with exact answers.
  export class TestServerMethods extends unittest.TestCase {
    // `initialize` on the line and on stdio answers with the exact text.
    test_initialize_recorded(): void {
      const browser = browser_make();
      const reply = browser.line_handle(line_read(constants.boot_initialize));
      this.assertEqual(JSON.stringify(reply), constants.boot_answer);
      const server = server_make();
      this.assertEqual(
        handled_text(server, text_read(constants.stdio_initialize)),
        constants.stdio_answer,
      );
    }

    // `ping` answers an empty result.
    test_ping_recorded(): void {
      const server = server_make();
      this.assertEqual(
        handled_text(server, text_read(constants.stdio_ping)),
        constants.stdio_pong,
      );
    }

    // `tools/list` lists the tools in the order they were registered.
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

    // Only the permit tool carries its `_meta` through `tools/list`.
    test_list_permit(): void {
      const server = browser_make();
      const texts = [constants.kv_tool, constants.console_tool];
      const entries = texts.map((text) => text_read(text));
      for (const entry of entries) {
        server.tool_register(entry as unknown as mcp.Tool, call_unexpected);
      }
      const answer = text_read(
        handled_text(server, text_read(constants.stdio_list)),
      );
      const tools = (answer.result as { tools: FieldTable[] }).tools;
      const marked = tools.filter((tool) => Object.hasOwn(tool, "_meta"));
      this.assertEqual(
        marked.map((tool) => tool.name),
        ["console_run"],
      );
      this.assertEqual(marked[0]._meta, { xsjs: { permit: true } });
      this.assertEqual(tools, entries);
    }

    // `tools/call` runs the tool on its arguments and answers its result.
    test_call_recorded(): void {
      const server = browser_make();
      const seen: FieldTable[] = [];
      server.tool_register(tool_make("kv_put"), (given) => {
        seen.push(given);
        return { content: [{ type: "text", text: constants.script_text }] };
      });
      const reply = server.line_handle(gold_line("call_kv_put"));
      this.assertEqual(JSON.stringify(reply), constants.script_answer);
      this.assertEqual(seen, [{ ref: "/_files/script/step_tide.js" }]);
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
      const seen: FieldTable[] = [];
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
        gold_text("arguments_absent_answer"),
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
      const cases: [FieldTable, string][] = [
        [{ jsonrpc: "1.0", id: 5, method: "ping" }, "request_invalid_five"],
        [{ jsonrpc: "2.0", id: 5 }, "request_invalid_five"],
        [{ jsonrpc: "2.0", id: null, method: "ping" }, "request_invalid_null"],
        [{ jsonrpc: "2.0", id: true, method: "ping" }, "request_invalid_null"],
        [{ jsonrpc: "2.0", id: 1.5, method: "ping" }, "request_invalid_null"],
      ];
      for (const [message, name] of cases) {
        this.assertEqual(handled_text(server, message), gold_text(name));
        this.assertEqual(server.failure_take(), undefined);
        const reply = server.line_handle(line_filled("mcp_request", message));
        this.assertTrue(reply !== undefined && Object.hasOwn(reply, "0"));
        this.assertEqual(server.failure_take(), undefined);
      }
    }

    // A protocol error's code, text and `data` cascade, its failure kept once.
    refusal_assert(
      server: mcp.Server,
      message: FieldTable,
      code: number,
      text: string,
    ): void {
      const answer = handled_text(server, message);
      const kept = kept_take(server);
      this.assertEqual(kept.message, text);
      this.assertEqual(answer, exception_text(message.id, code, kept));
      this.assertEqual(server.failure_take(), undefined);
      const line = line_filled("mcp_request", message);
      const failure = failure_of(server.line_handle(line));
      this.assertEqual(failure.error.message, text);
      this.assertEqual(failure.reply[0], { t: "mcp", r: 1 });
      this.assertEqual(
        JSON.stringify(payload_get(failure.reply)),
        exception_text(message.id, code, failure.error),
      );
      this.assertEqual(server.failure_take(), undefined);
    }

    // A method that is not served gets `-32601` naming it.
    test_method_unknown(): void {
      const server = browser_make();
      const message = { jsonrpc: "2.0", id: 6, method: "resources/list" };
      const text = gold_text("mcp_method_unknown");
      this.refusal_assert(server, message, -32601, text);
    }

    // `tools/call` params that are not a name and an object get `-32602`.
    test_params_invalid(): void {
      const server = browser_make();
      server.tool_register(tool_make("kv_get"), call_unexpected);
      const call = { jsonrpc: "2.0", id: 7, method: "tools/call" };
      const cases: FieldTable[] = [
        call,
        { ...call, params: "kv_get" },
        { ...call, params: { name: 3, arguments: {} } },
        { ...call, params: { name: "kv_get", arguments: [] } },
        { ...call, params: { name: "kv_get", arguments: null } },
      ];
      const text = gold_text("mcp_call_params");
      for (const message of cases) {
        this.refusal_assert(server, message, -32602, text);
      }
    }

    // A call of a tool that is not registered gets `-32602` naming it.
    test_tool_unknown(): void {
      const server = browser_make();
      const message = call_message(8, "kv_get", {});
      const text = gold_text("mcp_tool_unknown");
      this.refusal_assert(server, message, -32602, text);
    }

    // A throw in a tool answers an `isError` result holding its cascade.
    test_tool_throw(): void {
      const server = browser_make();
      const first = new Error("The store failed.");
      const failure = new Error("The tool failed.", { cause: first });
      server.tool_register(tool_make("kv_get"), () => {
        throw failure;
      });
      const cascade = {
        message: "The tool failed.",
        stack: failure.stack,
        cause: { message: "The store failed.", stack: first.stack },
      };
      const text = JSON.stringify(cascade);
      const result = { content: [{ type: "text", text }], isError: true };
      const answer = server.message_handle(
        call_message(9, "kv_get", {}) as unknown as mcp.Message,
      );
      this.assertEqual(answer, { jsonrpc: "2.0", id: 9, result });
      this.assertTrue(server.failure_take() === failure);
      this.assertEqual(server.failure_take(), undefined);
      const outcome = failure_of(server.line_handle(gold_line("call_kv_get")));
      this.assertTrue(outcome.error === failure);
      this.assertEqual(outcome.reply[0], { t: "mcp", r: 10 });
      this.assertEqual(payload_get(outcome.reply), {
        jsonrpc: "2.0",
        id: 10,
        result,
      });
      this.assertEqual(server.failure_take(), undefined);
    }

    // A tool that submits and then throws: the failure holds its answer.
    test_tool_submitted(): void {
      const tasks = new QueueDouble([7]);
      const server = browser_make();
      const failure = new Error("The tool failed.");
      server.tool_register(tool_make("render"), () => {
        tasks.task_submit(gold_line("asked"), "server");
        throw failure;
      });
      const outcome = failure_of(server.line_handle(gold_line("call_render")));
      this.assertTrue(outcome.error === failure);
      this.assertEqual(tasks.submitted.length, 1);
      this.assertEqual(outcome.reply[0], { t: "mcp", r: 4 });
      const cascade = { message: "The tool failed.", stack: failure.stack };
      const text = JSON.stringify(cascade);
      this.assertEqual(payload_get(outcome.reply).result, {
        content: [{ type: "text", text }],
        isError: true,
      });
      this.assertEqual(server.failure_take(), undefined);
    }

    // A second tool of the same name is refused.
    test_tool_twice(): void {
      const server = browser_make();
      server.tool_register(tool_make("kv_get"), call_unexpected);
      const error = thrown_get(() =>
        server.tool_register(tool_make("kv_get"), call_unexpected),
      );
      this.assertEqual(error.message, gold_text("mcp_tool_twice"));
    }
  }

  // A tool that sleeps: the request held by the sleep, answered by a wake.
  export class TestServerWakes extends unittest.TestCase {
    // `message_handle` passes the sleep of the tool on as it is.
    test_sleep_passed(): void {
      const server = browser_make();
      const wake = type_fresh();
      server.wake_register(wake, call_unexpected);
      const sleep = sleep_gold("sleep_one", wake);
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
        sleep_gold("sleep_one", wake),
      );
      const line = gold_line("call_render");
      const outcome = server.line_handle(line) as dispatch.Sleep;
      this.assertEqual(outcome.wait_ids, []);
      this.assertEqual(outcome.then_type, wake);
      const held = outcome.state as { request: lines.Line; state: unknown };
      this.assertTrue(held.request === line);
      this.assertEqual(held.state, { n: 1 });
    }

    // The wake answers the request in its name form.
    test_wake_answers(): void {
      const server = browser_make();
      const wake = type_fresh();
      const seen: unknown[] = [];
      server.wake_register(wake, (state, replies) => {
        seen.push(state, replies.length);
        return { content: [{ type: "text", text: constants.console_text }] };
      });
      server.tool_register(tool_make("console_run"), () =>
        sleep_gold("sleep_call", wake),
      );
      const line = gold_line("call_console_full");
      const sleep = server.line_handle(line) as dispatch.Sleep;
      this.assertEqual(sleep.wait_ids, [7]);
      const wakened = wake_make(sleep, "wake_seven");
      const answer = dispatch.line_dispatch(wakened) as lines.Line;
      this.assertEqual(seen, [{ call: 1 }, 1]);
      this.assertEqual(answer[0], { type: "mcp", reply: 1 });
      this.assertEqual(
        JSON.stringify(payload_get(answer)),
        constants.console_answer,
      );
    }

    // A wake may sleep again, and the last wake answers.
    test_wake_chain(): void {
      const server = browser_make();
      const first = type_fresh();
      const second = type_fresh();
      const states: unknown[] = [];
      server.wake_register(first, (state) => {
        states.push(state);
        return sleep_gold("sleep_second", second);
      });
      server.wake_register(second, (state) => {
        states.push(state);
        return { content: [], isError: true };
      });
      server.tool_register(tool_make("image_make"), () =>
        sleep_gold("sleep_first", first),
      );
      const line = gold_line("call_image_make");
      const sleep = server.line_handle(line) as dispatch.Sleep;
      this.assertEqual(sleep.wait_ids, [7]);
      const again = dispatch.line_dispatch(
        wake_make(sleep, "wake_seven"),
      ) as dispatch.Sleep;
      this.assertEqual(again.wait_ids, [8]);
      const answer = dispatch.line_dispatch(wake_make(again, "wake_eight"));
      this.assertEqual(states, [{ step: 1 }, { step: 2 }]);
      this.assertEqual(answer, {
        0: { t: "mcp", r: 3 },
        jsonrpc: "2.0",
        id: 3,
        result: { content: [], isError: true },
      });
    }

    // A throw in a wake: an `isError` result of its cascade, in the failure.
    test_wake_throw(): void {
      const server = browser_make();
      const wake = type_fresh();
      const first = new Error("The reply was wrong.");
      const failure = new Error("The wake failed.", { cause: first });
      server.wake_register(wake, () => {
        throw failure;
      });
      server.tool_register(tool_make("render"), () =>
        sleep_gold("sleep_waiting", wake),
      );
      const sleep = server.line_handle(gold_line("call_render"));
      const wakened = wake_make(sleep as dispatch.Sleep, "wake_seven");
      const outcome = failure_of(dispatch.line_dispatch(wakened));
      this.assertTrue(outcome.error === failure);
      this.assertEqual(server.failure_take(), undefined);
      this.assertEqual(outcome.reply[0], { t: "mcp", r: 4 });
      const cascade = {
        message: "The wake failed.",
        stack: failure.stack,
        cause: { message: "The reply was wrong.", stack: first.stack },
      };
      this.assertEqual(payload_get(outcome.reply), {
        jsonrpc: "2.0",
        id: 4,
        result: {
          content: [{ type: "text", text: JSON.stringify(cascade) }],
          isError: true,
        },
      });
    }

    // A sleep whose wake type the server did not register throws.
    test_wake_unknown(): void {
      const server = browser_make();
      const stray = type_fresh();
      server.tool_register(tool_make("render"), () =>
        sleep_gold("sleep_empty", stray),
      );
      const error = thrown_get(() =>
        server.line_handle(gold_line("call_render")),
      );
      const text = gold_text("mcp_wake_unknown").replaceAll("{0}", stray);
      this.assertEqual(error.message, text);
      const wake = type_fresh();
      server.wake_register(wake, () => sleep_gold("sleep_empty", stray));
      server.tool_register(tool_make("image_make"), () =>
        sleep_gold("sleep_waiting", wake),
      );
      const sleep = server.line_handle(gold_line("call_image_make"));
      const wakened = wake_make(sleep as dispatch.Sleep, "wake_seven");
      const again = thrown_get(() => dispatch.line_dispatch(wakened));
      this.assertEqual(again.message, text);
    }
  }

  // The requests of the client as the boot sends them.
  export class TestClientRequests extends unittest.TestCase {
    // The handshake and the tool list go out and come back as exact texts.
    test_handshake_recorded(): void {
      const tasks = new QueueDouble([1, 2]);
      const client = client_make(tasks, "server");
      const browser = browser_make();
      const kv_tool = text_read(constants.kv_tool) as unknown as mcp.Tool;
      browser.tool_register(kv_tool, call_unexpected);
      this.assertEqual(client.initialize_send(), 1);
      const answer = browser.line_handle(tasks.submitted[0][0]) as lines.Line;
      this.assertEqual(JSON.stringify(answer), gold_text("boot_answer_full"));
      client.initialized_send(answer);
      this.assertEqual(client.tools_list(), 2);
      const tools = browser.line_handle(tasks.submitted[1][0]) as lines.Line;
      const read = client.tools_read(tools);
      this.assertEqual(sent_texts(tasks.submitted), [
        [gold_text("boot_initialize_full"), "server"],
        [gold_text("boot_list_full"), "server"],
      ]);
      this.assertEqual(sent_texts(tasks.notified), [
        [gold_text("boot_initialized_full"), "server"],
      ]);
      this.assertEqual(read, [kv_tool]);
      this.assertEqual(client.tools_cached(), [kv_tool]);
    }

    // A client takes no name form: its lines take the form the settings pick.
    test_names_full(): void {
      const tasks = new QueueDouble([1]);
      const client = client_make(tasks, "server");
      const args = { text: "echo hi", timeout_seconds: 5 };
      this.assertEqual(client.tool_call("console_run", args), 1);
      const header = tasks.submitted[0][0][0];
      const full = harness.setting_get("debug") === true;
      this.assertEqual(Object.hasOwn(header, "type"), full);
      this.assertEqual(sent_texts(tasks.submitted), [
        [gold_text("console_call_full"), "server"],
      ]);
    }

    // An `initialize` answer of another revision is refused, nothing sent.
    test_version_refused(): void {
      const tasks = new QueueDouble([7]);
      const client = client_make(tasks, "server");
      client.initialize_send();
      const error = thrown_get(() =>
        client.initialized_send(gold_line("version_reply")),
      );
      this.assertEqual(error.message, gold_text("mcp_version_refused"));
      this.assertEqual(tasks.submitted.length, 1);
      this.assertEqual(tasks.notified.length, 0);
    }

    // The tools of a client cannot be had before they are read.
    test_tools_unread(): void {
      const client = client_make(new QueueDouble([]), "server");
      const error = thrown_get(() => client.tools_cached());
      this.assertEqual(error.message, gold_text("mcp_tools_unread"));
    }

    // A `tools/list` result that is not a list of tools is refused.
    test_tools_invalid(): void {
      const client = client_make(new QueueDouble([7, 8]), "server");
      const cases: [string, string][] = [
        ["tools_invalid_object", "mcp_result_invalid_object"],
        ["tools_invalid_entry", "mcp_result_invalid_entry"],
      ];
      for (const [reply, text] of cases) {
        client.tools_list();
        const error = thrown_get(() => client.tools_read(gold_line(reply)));
        this.assertEqual(error.message, gold_text(text));
      }
    }
  }

  // The reading of the replies of a client, and every reply it refuses.
  export class TestClientReplies extends unittest.TestCase {
    // A result is read with the error flag when the server sends one.
    test_result_read(): void {
      const client = client_make(new QueueDouble([7, 8]), "server");
      client.tool_call("source_put", {});
      const read = client.result_of(gold_line("result_flagged"));
      this.assertEqual(read, {
        content: [{ type: "text", text: "{}" }],
        isError: false,
      });
      client.tool_call("render", {});
      const bare = client.result_of(gold_line("result_plain"));
      this.assertEqual(bare, { content: [{ type: "text", text: "{}" }] });
      this.assertFalse(Object.hasOwn(bare, "isError"));
    }

    // A result whose content or error flag is not valid is refused.
    test_result_invalid(): void {
      const client = client_make(new QueueDouble([7, 8]), "server");
      const cases: [string, string][] = [
        ["result_content_text", "mcp_result_invalid_content"],
        ["result_flag_text", "mcp_result_invalid_flag"],
      ];
      for (const [reply, text] of cases) {
        client.tool_call("render", {});
        const error = thrown_get(() => client.result_of(gold_line(reply)));
        this.assertEqual(error.message, gold_text(text));
      }
    }

    // A reply to no request of the client, or read twice, is refused.
    test_reply_unknown(): void {
      const client = client_make(new QueueDouble([7]), "server");
      const stray = thrown_get(() =>
        client.result_of(gold_line("reply_nine")),
      );
      this.assertEqual(stray.message, gold_text("mcp_reply_unknown_stray"));
      client.tool_call("render", {});
      const reply = gold_line("render_reply");
      client.result_of(reply);
      const again = thrown_get(() => client.result_of(reply));
      this.assertEqual(again.message, gold_text("mcp_reply_unknown_again"));
    }

    // A reply read as the answer of another method is refused.
    test_reply_method(): void {
      const client = client_make(new QueueDouble([7]), "server");
      client.tools_list();
      const error = thrown_get(() =>
        client.result_of(gold_line("tools_empty")),
      );
      this.assertEqual(error.message, gold_text("mcp_reply_method"));
    }

    // An error response throws with the error the server sent.
    test_reply_error(): void {
      const client = client_make(new QueueDouble([8]), "server");
      client.tool_call("system_restart", { main_loop: "main_loop.py" });
      const error = thrown_get(() =>
        client.result_of(gold_line("restart_refused")),
      );
      this.assertEqual(error.message, gold_text("mcp_reply_error"));
    }

    // A reply that is not a response to the id that was sent is refused.
    test_response_invalid(): void {
      const tasks = new QueueDouble([7, 8, 9, 10, 11]);
      const client = client_make(tasks, "server");
      const cases: [string, string][] = [
        ["response_version", "mcp_response_invalid_version"],
        ["response_id", "mcp_response_invalid_id"],
        ["response_empty", "mcp_response_invalid_empty"],
        ["response_list", "mcp_response_invalid_list"],
        ["response_null", "mcp_response_invalid_null"],
      ];
      for (const [reply, text] of cases) {
        client.tool_call("render", {});
        const error = thrown_get(() => client.result_of(gold_line(reply)));
        this.assertEqual(error.message, gold_text(text));
      }
    }
  }

  // The set of clients: prefixed tools, routed calls and their errors.
  export class TestClientSet extends unittest.TestCase {
    // The tools of every client are listed in order under dotted names.
    test_tools_prefixed(): void {
      const tasks = new QueueDouble([7, 8, 9]);
      const browser = client_make(tasks, "ui");
      const server = client_make(tasks, "server");
      const kv_tool = text_read(constants.kv_tool);
      const recorded = text_read(constants.stdio_tools);
      browser.tools_list();
      const list = { jsonrpc: "2.0", id: 1, result: { tools: [kv_tool] } };
      browser.tools_read(line_filled("reply_seven", list));
      server.initialize_send();
      server.tools_list();
      server.tools_read(line_filled("reply_nine", recorded));
      const set = new mcp.ClientSet();
      set.client_add("browser", browser);
      set.client_add("server", server);
      const listed = (recorded.result as { tools: FieldTable[] }).tools;
      this.assertEqual(set.tools_cached(), [
        { ...kv_tool, name: "browser.kv_get" },
        { ...listed[0], name: "server.source_put" },
        { ...listed[1], name: "server.system_restart" },
      ]);
    }

    // A call goes to the client of its prefix by the bare name, and back.
    test_calls_routed(): void {
      const tasks = new QueueDouble([7, 8]);
      const browser = client_make(tasks, "ui");
      const server = client_make(tasks, "server");
      const set = new mcp.ClientSet();
      set.client_add("browser", browser);
      set.client_add("server", server);
      const nothing = { ref: "/metaverse/nothing" };
      const restart = { main_loop: "main_loop.py" };
      this.assertEqual(set.tool_call("browser.kv_get", nothing), 7);
      this.assertEqual(set.tool_call("server.system_restart", restart), 8);
      const [sent, near] = tasks.submitted[0];
      this.assertEqual(near, "ui");
      this.assertEqual(
        JSON.stringify(payload_get(sent)),
        constants.fault_call,
      );
      const [routed, far] = tasks.submitted[1];
      this.assertEqual(far, "server");
      const recorded = text_read(constants.stdio_restart);
      this.assertEqual(payload_get(routed).params, recorded.params);
      const tools = browser_make();
      const result: mcp.ToolResult = {
        content: [{ type: "text", text: "{}" }],
      };
      tools.tool_register(tool_make("kv_get"), () => result);
      const answer = tools.line_handle(sent) as lines.Line;
      this.assertEqual(set.result_of(answer), result);
      const error = thrown_get(() =>
        set.result_of(gold_line("restart_refused")),
      );
      this.assertEqual(error.message, gold_text("mcp_reply_error"));
    }

    // A prefix that is empty, dotted or already added is refused.
    test_prefix_refused(): void {
      const tasks = new QueueDouble([]);
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(tasks, "server"));
      const cases: [string, string][] = [
        ["", "mcp_prefix_refused_empty"],
        ["browser.tools", "mcp_prefix_refused_dotted"],
        ["server", "mcp_prefix_refused_taken"],
      ];
      for (const [prefix, text] of cases) {
        const error = thrown_get(() =>
          set.client_add(prefix, client_make(tasks, "ui")),
        );
        this.assertEqual(error.message, gold_text(text));
      }
    }

    // A name with no dot or with a prefix of no client is refused.
    test_prefix_unknown(): void {
      const tasks = new QueueDouble([]);
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(tasks, "server"));
      const cases: [string, string][] = [
        ["kv_get", "mcp_prefix_unknown_bare"],
        ["browser.kv_get", "mcp_prefix_unknown_browser"],
      ];
      for (const [name, text] of cases) {
        const error = thrown_get(() => set.tool_call(name, {}));
        this.assertEqual(error.message, gold_text(text));
      }
      this.assertEqual(tasks.submitted.length, 0);
    }

    // A reply to no call of the set is refused.
    test_reply_stray(): void {
      const set = new mcp.ClientSet();
      const error = thrown_get(() => set.result_of(gold_line("reply_nine")));
      this.assertEqual(error.message, gold_text("mcp_reply_unknown_stray"));
    }
  }
}

Object.freeze(test_mcp);
