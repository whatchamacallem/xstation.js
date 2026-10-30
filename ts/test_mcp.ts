// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the Model Context Protocol of the AI worker: the methods and
// errors of the server, the exception it keeps and the failure it returns
// with its answer; its sleeping tools on a real queue in synchronous mode,
// whose `mcp` handler is the test's function handing each line to the
// server, and whose lane to `server` reaches a second real queue that answers
// the requests a tool submits, each wake run by the queue; and the checks of
// the client and the set of clients, whose requests a real server answers on
// a real queue joined to theirs by linked local ports. The lines the tests
// send, the sleeps of their tools and the texts they expect are read from the
// gold record, compared with the exact texts of the boot's handshake and of a
// stdio session where they apply. The lines between a client and a server
// are the line cases of `test_integrate_mcp`.

namespace test_mcp {
  // The test type prefix, the identities and the exact texts of messages.
  const constants = Object.freeze({
    type_prefix: "mcp_test.",
    line_type: "mcp",
    thread: "ai" as const,
    far_thread: "server" as const,
    test_thread: "ui" as const,
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
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // A sleep of the gold before the wake type the test made is set on it.
  type SleepPart = Omit<dispatch.Sleep, "then_type">;

  // The state of a sleep of the gold, which waits on the ids a tool submits.
  type SleepState = Pick<dispatch.Sleep, "state">;

  // A step of a task on the clients' queue: the ids the next step sleeps on.
  type StepFn = (replies: lines.Line[]) => number[];

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // How many versions of `mcp` the server benches have registered.
  let versions_made = 0;

  // The server the `mcp` lines of the clients reach, once one is set.
  let peer: mcp.Server | undefined = undefined;

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

  // The state of a sleep of the gold, waiting on the ids given for the type.
  function sleep_on(
    name: string,
    then_type: string,
    wait_ids: number[],
  ): dispatch.Sleep {
    const { state } = gold_value(`lines.${name}`) as SleepState;
    return dispatch.task_sleep(state, wait_ids, then_type);
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

  // A line of the type with no payload, in the name form the settings pick.
  function line_typed(type: string): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], {});
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

  // The test's end of a lane: its linked local port and the lines that came.
  interface LaneEnd {
    port: queue.LocalPort;
    came: lines.Line[];
  }

  // Joins the queue to the thread by linked local ports, one end the test's.
  function lane_make(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
  ): LaneEnd {
    const near = new queue.LocalPort();
    const port = new queue.LocalPort(near);
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    tasks.port_add(thread, near);
    return { port, came };
  }

  // Joins two queues by linked local ports, each reaching the other's thread.
  function queues_join(
    near: queue.TaskQueue,
    near_thread: queue.ThreadName,
    far: queue.TaskQueue,
    far_thread: queue.ThreadName,
  ): void {
    const port = new queue.LocalPort();
    near.port_add(far_thread, port);
    far.port_add(near_thread, new queue.LocalPort(port));
  }

  // A server on a queue, the test's end of `ui`, the far queue's lines.
  interface ServerBench {
    tasks: queue.TaskQueue;
    ui: LaneEnd;
    server: mcp.Server;
    version: number;
    asked: string;
    got: lines.Line[];
  }

  // A server whose `mcp` lines of a new version a real queue hands it.
  function bench_make(): ServerBench {
    const asked = type_fresh();
    const got: lines.Line[] = [];
    // The far queue answers each request a tool submits at once.
    dispatch.handler_register(asked, 0, (line) => {
      got.push(line);
      return dispatch.reply_make(line, {});
    });
    const owners: queue.OwnerTable = {
      [constants.type_prefix]: constants.thread,
      [constants.line_type]: constants.thread,
      [asked]: constants.far_thread,
    };
    const tasks = new queue.TaskQueue(constants.thread, owners, true);
    const ui = lane_make(tasks, constants.test_thread);
    const far_owners = { [constants.type_prefix]: constants.far_thread };
    const far = new queue.TaskQueue(constants.far_thread, far_owners, true);
    queues_join(tasks, constants.thread, far, constants.far_thread);
    const server = browser_make();
    versions_made += 1;
    const version = versions_made;
    dispatch.handler_register(constants.line_type, version, (line) =>
      server.line_handle(line),
    );
    return { tasks, ui, server, version, asked, got };
  }

  // Submits the request a tool waits on, which the far queue answers.
  function ask_submit(bench: ServerBench): number {
    return bench.tasks.task_submit(line_typed(bench.asked));
  }

  // Posts a gold `mcp` line of the bench's version into its queue from `ui`.
  function request_send(bench: ServerBench, name: string): void {
    const line = gold_line(name);
    const full = Object.hasOwn(line[0], "type");
    Object.assign(line[0], { [full ? "version" : "v"]: bench.version });
    bench.ui.port.line_post(line, []);
  }

  // Sets the server the clients reach, registering `mcp` the first time.
  function peer_set(server: mcp.Server): void {
    if (peer === undefined) {
      dispatch.handler_register(constants.line_type, 0, (line) =>
        (peer as mcp.Server).line_handle(line),
      );
    }
    peer = server;
  }

  // The clients' queue, joined to a queue on which the server answers `mcp`.
  function clients_make(server: mcp.Server): queue.TaskQueue {
    peer_set(server);
    const owners = { [constants.type_prefix]: constants.thread };
    const tasks = new queue.TaskQueue(constants.thread, owners, true);
    const far_owners = { [constants.line_type]: constants.far_thread };
    const far = new queue.TaskQueue(constants.far_thread, far_owners, true);
    queues_join(tasks, constants.thread, far, constants.far_thread);
    return tasks;
  }

  // A client of the tests whose server the owner given reaches.
  function client_make(
    tasks: queue.TaskQueue,
    owner: queue.ThreadName,
  ): mcp.Client {
    return new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      owner,
    );
  }

  // Runs each step as a task woken by the replies to the step before.
  function steps_run(tasks: queue.TaskQueue, steps: readonly StepFn[]): void {
    const types = steps.map(() => type_fresh());
    for (const [index, step] of steps.entries()) {
      const next = types.at(index + 1);
      dispatch.handler_register(types[index], 0, (line) => {
        const replies = index === 0 ? [] : (line.replies as lines.Line[]);
        const ids = step(replies);
        if (next === undefined) {
          return undefined;
        }
        return dispatch.task_sleep(null, ids, next);
      });
    }
    tasks.line_notify(line_typed(types[0]));
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

    // A tool that submits, then throws: the answer, then the unawaited fault.
    test_tool_submitted(): void {
      const bench = bench_make();
      const failure = new Error("The tool failed.");
      bench.server.tool_register(tool_make("render"), () => {
        ask_submit(bench);
        throw failure;
      });
      const thrown = thrown_get(() => request_send(bench, "call_render"));
      this.assertEqual(thrown.message, gold_text("queue_wait_missing_mcp"));
      this.assertTrue(thrown.cause === failure);
      this.assertEqual(bench.got.length, 1);
      this.assertEqual(bench.ui.came.length, 1);
      const answer = bench.ui.came[0];
      this.assertEqual(answer[0], { t: "mcp", r: 4 });
      const cascade = { message: "The tool failed.", stack: failure.stack };
      const text = JSON.stringify(cascade);
      this.assertEqual(payload_get(answer).result, {
        content: [{ type: "text", text }],
        isError: true,
      });
      this.assertEqual(bench.server.failure_take(), undefined);
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

    // The queue's wake answers the request in its name form.
    test_wake_answers(): void {
      const bench = bench_make();
      const wake = type_fresh();
      const seen: unknown[] = [];
      bench.server.wake_register(wake, (state, replies) => {
        seen.push(state, replies.length);
        return { content: [{ type: "text", text: constants.console_text }] };
      });
      bench.server.tool_register(tool_make("console_run"), () =>
        sleep_on("sleep_call", wake, [ask_submit(bench)]),
      );
      request_send(bench, "call_console_full");
      this.assertEqual(seen, [{ call: 1 }, 1]);
      this.assertEqual(bench.ui.came.length, 1);
      const answer = bench.ui.came[0];
      this.assertEqual(answer[0], { type: "mcp", reply: 1 });
      this.assertEqual(
        JSON.stringify(payload_get(answer)),
        constants.console_answer,
      );
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A wake may sleep again, and the last wake answers.
    test_wake_chain(): void {
      const bench = bench_make();
      const first = type_fresh();
      const second = type_fresh();
      const states: unknown[] = [];
      bench.server.wake_register(first, (state) => {
        states.push(state);
        return sleep_on("sleep_second", second, [ask_submit(bench)]);
      });
      bench.server.wake_register(second, (state) => {
        states.push(state);
        return { content: [], isError: true };
      });
      bench.server.tool_register(tool_make("image_make"), () =>
        sleep_on("sleep_first", first, [ask_submit(bench)]),
      );
      request_send(bench, "call_image_make");
      this.assertEqual(states, [{ step: 1 }, { step: 2 }]);
      this.assertEqual(bench.got.length, 2);
      this.assertEqual(bench.ui.came, [
        {
          0: { t: "mcp", r: 3 },
          jsonrpc: "2.0",
          id: 3,
          result: { content: [], isError: true },
        },
      ]);
    }

    // A throw in a wake: its `isError` answer goes out, then the queue fails.
    test_wake_throw(): void {
      const bench = bench_make();
      const wake = type_fresh();
      const first = new Error("The reply was wrong.");
      const failure = new Error("The wake failed.", { cause: first });
      bench.server.wake_register(wake, () => {
        throw failure;
      });
      bench.server.tool_register(tool_make("render"), () =>
        sleep_on("sleep_waiting", wake, [ask_submit(bench)]),
      );
      const thrown = thrown_get(() => request_send(bench, "call_render"));
      this.assertTrue(thrown === failure);
      this.assertEqual(bench.server.failure_take(), undefined);
      this.assertEqual(bench.ui.came.length, 1);
      const answer = bench.ui.came[0];
      this.assertEqual(answer[0], { t: "mcp", r: 4 });
      const cascade = {
        message: "The wake failed.",
        stack: failure.stack,
        cause: { message: "The reply was wrong.", stack: first.stack },
      };
      this.assertEqual(payload_get(answer), {
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
      const bench = bench_make();
      const wake = type_fresh();
      bench.server.wake_register(wake, () => sleep_gold("sleep_empty", stray));
      bench.server.tool_register(tool_make("image_make"), () =>
        sleep_on("sleep_waiting", wake, [ask_submit(bench)]),
      );
      const again = thrown_get(() => request_send(bench, "call_image_make"));
      this.assertEqual(again.message, text);
      this.assertEqual(bench.ui.came.length, 0);
    }
  }

  // The checks a client makes of the replies it reads, each thrown.
  export class TestClientChecks extends unittest.TestCase {
    // The tools of a client cannot be had before they are read.
    test_tools_unread(): void {
      const tasks = clients_make(server_make());
      const client = client_make(tasks, constants.far_thread);
      const error = thrown_get(() => client.tools_cached());
      this.assertEqual(error.message, gold_text("mcp_tools_unread"));
    }

    // A `tools/list` result whose entry is not a tool is refused.
    test_tools_invalid(): void {
      const server = server_make();
      const entry = gold_value("tools.undescribed") as mcp.Tool;
      server.tool_register(entry, call_unexpected);
      const tasks = clients_make(server);
      const client = client_make(tasks, constants.far_thread);
      const errors: Error[] = [];
      steps_run(tasks, [
        () => [client.tools_list()],
        ([reply]) => {
          errors.push(thrown_get(() => client.tools_read(reply)));
          return [];
        },
      ]);
      this.assertEqual(
        errors.map((error) => error.message),
        [gold_text("mcp_result_invalid_entry")],
      );
    }

    // A result whose content or error flag is not valid is refused.
    test_result_invalid(): void {
      const server = server_make();
      const content = gold_value("results.content_text") as mcp.ToolResult;
      const flag = gold_value("results.flag_text") as mcp.ToolResult;
      server.tool_register(tool_make("render"), () => content);
      server.tool_register(tool_make("source_put"), () => flag);
      const tasks = clients_make(server);
      const client = client_make(tasks, constants.far_thread);
      const errors: Error[] = [];
      steps_run(tasks, [
        () => [client.tool_call("render", {})],
        ([reply]) => {
          errors.push(thrown_get(() => client.result_of(reply)));
          return [client.tool_call("source_put", {})];
        },
        ([reply]) => {
          errors.push(thrown_get(() => client.result_of(reply)));
          return [];
        },
      ]);
      this.assertEqual(
        errors.map((error) => error.message),
        [
          gold_text("mcp_result_invalid_content"),
          gold_text("mcp_result_invalid_flag"),
        ],
      );
    }

    // A reply to a request of another client, or read twice, is refused.
    test_reply_unknown(): void {
      const server = server_make();
      server.tool_register(tool_make("render"), () => ({ content: [] }));
      const tasks = clients_make(server);
      const caller = client_make(tasks, constants.far_thread);
      const other = client_make(tasks, constants.far_thread);
      const errors: Error[] = [];
      const read: mcp.ToolResult[] = [];
      steps_run(tasks, [
        () => [caller.tool_call("render", {})],
        ([reply]) => {
          errors.push(thrown_get(() => other.result_of(reply)));
          read.push(caller.result_of(reply));
          errors.push(thrown_get(() => caller.result_of(reply)));
          return [];
        },
      ]);
      this.assertEqual(read, [{ content: [] }]);
      this.assertEqual(
        errors.map((error) => error.message),
        [
          gold_text("mcp_reply_unknown_stray"),
          gold_text("mcp_reply_unknown_again"),
        ],
      );
    }

    // A reply read as the answer of another method is refused.
    test_reply_method(): void {
      const tasks = clients_make(server_make());
      const client = client_make(tasks, constants.far_thread);
      const errors: Error[] = [];
      steps_run(tasks, [
        () => [client.tools_list()],
        ([reply]) => {
          errors.push(thrown_get(() => client.result_of(reply)));
          return [];
        },
      ]);
      this.assertEqual(
        errors.map((error) => error.message),
        [gold_text("mcp_reply_method")],
      );
    }
  }

  // The set of clients: the prefixes it refuses and the replies it reads.
  export class TestClientSet extends unittest.TestCase {
    // A prefix that is empty, dotted or already added is refused.
    test_prefix_refused(): void {
      const tasks = clients_make(server_make());
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(tasks, constants.far_thread));
      const cases: [string, string][] = [
        ["", "mcp_prefix_refused_empty"],
        ["browser.tools", "mcp_prefix_refused_dotted"],
        ["server", "mcp_prefix_refused_taken"],
      ];
      for (const [prefix, text] of cases) {
        const error = thrown_get(() =>
          set.client_add(prefix, client_make(tasks, constants.test_thread)),
        );
        this.assertEqual(error.message, gold_text(text));
      }
    }

    // A name with no dot or with a prefix of no client is refused.
    test_prefix_unknown(): void {
      const tasks = clients_make(server_make());
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(tasks, constants.far_thread));
      const cases: [string, string][] = [
        ["kv_get", "mcp_prefix_unknown_bare"],
        ["browser.kv_get", "mcp_prefix_unknown_browser"],
      ];
      for (const [name, text] of cases) {
        const error = thrown_get(() => set.tool_call(name, {}));
        this.assertEqual(error.message, gold_text(text));
      }
    }

    // A reply to a call of a client outside the set is refused.
    test_reply_stray(): void {
      const server = server_make();
      server.tool_register(tool_make("render"), () => ({ content: [] }));
      const tasks = clients_make(server);
      const outside = client_make(tasks, constants.far_thread);
      const set = new mcp.ClientSet();
      set.client_add("server", client_make(tasks, constants.far_thread));
      const errors: Error[] = [];
      steps_run(tasks, [
        () => [outside.tool_call("render", {})],
        ([reply]) => {
          errors.push(thrown_get(() => set.result_of(reply)));
          return [];
        },
      ]);
      this.assertEqual(
        errors.map((error) => error.message),
        [gold_text("mcp_reply_unknown_stray")],
      );
    }
  }
}

Object.freeze(test_mcp);
