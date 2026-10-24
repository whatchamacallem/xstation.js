// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The Model Context Protocol of the AI worker over `JSON-RPC 2.0`, revision
// `2025-06-18`: the server that answers the `mcp` line and continues a tool
// that sleeps in the wakes registered with it, the client that submits its
// requests as `mcp` lines to the owner of its server, and the set of clients
// that the agent sees as one list of prefixed tools. MCP is a testing
// protocol for now: no AI is a requirement of the tests yet.
//
// Fail loud: an exception while a request is handled answers that request,
// then the server stops. A tool's exception, thrown by the tool or by the
// wake that continues it, answers with a `tools/call` result whose `isError`
// is true and whose one text content is the JSON text of the cascade, its
// `message`, `stack` and nested `cause`, as `dispatch.cause_make` writes it.
// A protocol error, as an unknown method or tool or bad params, answers with
// a JSON-RPC error whose `data` is that cascade. `failure_take` then returns
// the exception once, and `line_handle` returns a `dispatch.Failure` that
// holds the answer and the exception, so the queue posts the answer and then
// fails. A test driver reads `isError`, or the error, to tell an exception
// from the expected response. Continuing after an exception is deferred.
// A message that is not a JSON-RPC 2.0 request is answered with -32600 and
// is no exception, as in Python. Every `mcp` line the client builds takes
// the form `settings.names_full()` picks.

namespace mcp {
  // The revision pinned, the names and codes of the protocol, the line type.
  export const constants = Object.freeze({
    protocol_version: "2025-06-18",
    jsonrpc_version: "2.0" as const,
    line_type: "mcp",
    id_field: "id",
    reply_field: "reply",
    arguments_field: "arguments",
    error_field: "error",
    method_initialize: "initialize",
    method_initialized: "notifications/initialized",
    method_ping: "ping",
    method_list: "tools/list",
    method_call: "tools/call",
    code_invalid: -32600,
    code_unknown: -32601,
    code_params: -32602,
    code_internal: -32603,
    prefix_mark: ".",
  });

  // A `JSON-RPC` id, a number or text. A notification has none.
  export type Id = number | string;

  // A request, which the other side answers with a response.
  export interface Request {
    jsonrpc: "2.0";
    id: Id;
    method: string;
    params?: { [key: string]: unknown };
  }

  // A notification, which nothing answers.
  export interface Notification {
    jsonrpc: "2.0";
    method: string;
    params?: { [key: string]: unknown };
  }

  // A response that carries the result of a request.
  export interface Response {
    jsonrpc: "2.0";
    id: Id;
    result: { [key: string]: unknown };
  }

  // A response that carries an error, its id `null` when none was readable.
  export interface ErrorResponse {
    jsonrpc: "2.0";
    id: Id | null;
    error: { code: number; message: string; data?: lines.ErrorCause };
  }

  // Any message of the protocol.
  export type Message = Request | Notification | Response | ErrorResponse;

  // A tool as `tools/list` lists it. `_meta` marks a permit tool.
  export interface Tool {
    name: string;
    description: string;
    inputSchema: {
      type: "object";
      properties: { [key: string]: unknown };
      required?: string[];
    };
    _meta?: { xsjs: { permit: boolean } };
  }

  // One block of the content of a tool result.
  export type Content =
    | { type: "text"; text: string }
    | { type: "image"; data: string; mimeType: string };

  // The result of a `tools/call`.
  export interface ToolResult {
    content: Content[];
    isError?: boolean;
  }

  // A tool: its result, or a sleep whose wake type has a registered `WakeFn`.
  export type ToolFn = (args: {
    [key: string]: unknown;
  }) => ToolResult | dispatch.Sleep;

  // A wake of a tool: from its state and replies, the result or a new sleep.
  export type WakeFn = (
    state: unknown,
    replies: lines.Line[],
  ) => ToolResult | dispatch.Sleep;

  // An object of fields by name, as a decoded message holds them.
  type FieldTable = { [key: string]: unknown };

  // A method of the server: its result, or the sleep of a tool.
  type MethodFn = (params: unknown) => FieldTable | dispatch.Sleep;

  // What the sleep of a tool holds: the `mcp` line it answers, its state.
  interface WaitState {
    request: lines.Line;
    state: unknown;
  }

  // A request the client submitted: its `JSON-RPC` id and its method.
  interface SentRequest {
    rpc: number;
    method: string;
  }

  // A `JSON-RPC` error with its code, which a method throws.
  class ProtocolError extends Error {
    readonly code: number;

    // Keeps the code beside the message.
    constructor(code: number, message: string) {
      super(message);
      this.code = code;
    }
  }

  // Whether a value is an object that is neither an array nor `null`.
  function fields_is(value: unknown): value is FieldTable {
    return (
      typeof value === "object" && value !== null && !Array.isArray(value)
    );
  }

  // Whether a value can be a request id: text or a whole number.
  function id_valid(value: unknown): value is Id {
    return typeof value === "string" || Number.isInteger(value);
  }

  // Whether an outcome is a sleep, by its three fields.
  function sleep_is(value: object): value is dispatch.Sleep {
    return "state" in value && "wait_ids" in value && "then_type" in value;
  }

  // Whether a `tools/list` entry has a name, a description and a schema.
  function tool_valid(entry: unknown): boolean {
    return (
      fields_is(entry) &&
      typeof entry.name === "string" &&
      typeof entry.description === "string" &&
      fields_is(entry.inputSchema)
    );
  }

  // The id of the request a reply line answers.
  function reply_of(reply: lines.Line): number {
    return jslb.field_get(reply[0], constants.reply_field) as number;
  }

  // A response that carries the result.
  function result_make(id: Id, result: FieldTable): Response {
    return { jsonrpc: constants.jsonrpc_version, id, result };
  }

  // An error response with a code and a message and no data.
  function error_make(
    id: Id | null,
    code: number,
    message: string,
  ): ErrorResponse {
    return {
      jsonrpc: constants.jsonrpc_version,
      id,
      error: { code, message },
    };
  }

  // The error response to a message that is not a valid request.
  function invalid_make(id: Id | null): ErrorResponse {
    return error_make(id, constants.code_invalid, i18n("mcp.request_invalid"));
  }

  // The error response to a throw, a protocol error's code else -32603, its
  // cascade in `data`.
  function exception_make(id: Id, error: Error): ErrorResponse {
    const code =
      error instanceof ProtocolError ? error.code : constants.code_internal;
    const data = dispatch.cause_make(error);
    return {
      jsonrpc: constants.jsonrpc_version,
      id,
      error: { code, message: error.message, data },
    };
  }

  // The exception a throw leaves: the Error thrown, or an Error of its text.
  function error_of(thrown: unknown): Error {
    return thrown instanceof Error ? thrown : new Error(String(thrown));
  }

  // The outcome of a tool as a method's: its sleep, or a copy of its result.
  function outcome_fields(
    outcome: ToolResult | dispatch.Sleep,
  ): FieldTable | dispatch.Sleep {
    return sleep_is(outcome) ? outcome : { ...outcome };
  }

  // The MCP server of the AI worker, its tools listed in registration order.
  export class Server {
    private readonly name: string;
    private readonly version: string;
    private readonly tools = new Map<string, Tool>();
    private readonly calls = new Map<string, ToolFn>();
    private readonly wakes = new Set<string>();
    private readonly methods: Map<string, MethodFn>;
    // The exception of the last request answered with one, until taken.
    private failure: Error | undefined = undefined;

    // Keeps the identity `initialize` reports and starts with no tools.
    constructor(name: string, version: string) {
      this.name = name;
      this.version = version;
      this.methods = new Map<string, MethodFn>([
        [constants.method_initialize, () => this.initialize_run()],
        [constants.method_ping, () => ({})],
        [constants.method_list, () => this.list_run()],
        [constants.method_call, (params: unknown) => this.call_run(params)],
      ]);
    }

    // Registers a tool and the function that runs it. A second name throws.
    tool_register(tool: Tool, fn: ToolFn): void {
      if (this.tools.has(tool.name)) {
        throw new Error(i18n("mcp.tool_twice", tool.name));
      }
      this.tools.set(tool.name, tool);
      this.calls.set(tool.name, fn);
    }

    // Registers a wake type a tool sleeps with and the function it runs.
    wake_register(then_type: string, fn: WakeFn): void {
      dispatch.handler_register(then_type, 0, (line: lines.Line) =>
        this.wake_handle(line, fn),
      );
      this.wakes.add(then_type);
    }

    // Handles one message: the response, the sleep of a tool, or nothing.
    message_handle(message: Message): Message | dispatch.Sleep | undefined {
      const fields = message as unknown as FieldTable;
      const method = fields.method;
      const raw = fields.id;
      const id = id_valid(raw) ? raw : null;
      if (
        fields.jsonrpc !== constants.jsonrpc_version ||
        typeof method !== "string"
      ) {
        return invalid_make(id);
      }
      if (!Object.hasOwn(fields, constants.id_field)) {
        return undefined;
      }
      if (id === null) {
        return invalid_make(null);
      }
      return this.outcome_take(id, () =>
        this.method_run(method, fields.params),
      );
    }

    // The exception of the last request answered with one, then undefined.
    failure_take(): Error | undefined {
      const failure = this.failure;
      this.failure = undefined;
      return failure;
    }

    // Handles one `mcp` line: the reply, a sleep, a failure, or nothing.
    line_handle(
      line: lines.Line,
    ): dispatch.Reply | dispatch.Sleep | dispatch.Failure {
      const message = jslb.payload_of(line) as unknown as Message;
      const outcome = this.message_handle(message);
      if (outcome === undefined) {
        return undefined;
      }
      return this.answer_take(line, outcome);
    }

    // Continues a tool in its wake and answers the line its sleep holds.
    private wake_handle(
      line: lines.Line,
      fn: WakeFn,
    ): dispatch.Reply | dispatch.Sleep | dispatch.Failure {
      const wait = line.state as WaitState;
      const replies = line.replies as lines.Line[];
      const id = jslb.payload_of(wait.request).id as Id;
      const outcome = this.outcome_take(id, () =>
        this.tool_run(() => fn(wait.state, replies)),
      );
      return this.answer_take(wait.request, outcome);
    }

    // The answer to the request, a failure holding it when an exception is
    // kept, which comes with an answer and never with a sleep.
    private answer_take(
      request: lines.Line,
      outcome: Message | dispatch.Sleep,
    ): dispatch.Reply | dispatch.Sleep | dispatch.Failure {
      const answer = this.answer_make(request, outcome);
      const failure = this.failure_take();
      if (failure === undefined) {
        return answer;
      }
      return dispatch.failure_make(answer as lines.Line, failure);
    }

    // The reply line to the request, or the sleep that holds the request.
    private answer_make(
      request: lines.Line,
      outcome: Message | dispatch.Sleep,
    ): dispatch.Reply | dispatch.Sleep {
      if (sleep_is(outcome)) {
        return this.sleep_wrap(request, outcome);
      }
      return dispatch.reply_make(request, outcome as unknown as FieldTable);
    }

    // Runs a method or a continuation, a throw becoming an error response
    // whose exception is kept.
    private outcome_take(
      id: Id,
      run: () => FieldTable | dispatch.Sleep,
    ): Message | dispatch.Sleep {
      try {
        const outcome = run();
        return sleep_is(outcome) ? outcome : result_make(id, outcome);
      } catch (thrown) {
        const error = error_of(thrown);
        this.failure = error;
        return exception_make(id, error);
      }
    }

    // Runs a tool or its wake, a throw becoming the `isError` result of its
    // cascade, the exception kept.
    private tool_run(
      run: () => ToolResult | dispatch.Sleep,
    ): FieldTable | dispatch.Sleep {
      let outcome: ToolResult | dispatch.Sleep;
      try {
        outcome = run();
      } catch (thrown) {
        const text = utility.json_text(dispatch.cause_make(thrown));
        this.failure = error_of(thrown);
        return { content: [{ type: "text", text }], isError: true };
      }
      return outcome_fields(outcome);
    }

    // The sleep of a tool holding the request, its wake type registered here.
    private sleep_wrap(
      request: lines.Line,
      sleep: dispatch.Sleep,
    ): dispatch.Sleep {
      if (!this.wakes.has(sleep.then_type)) {
        throw new Error(i18n("mcp.wake_unknown", sleep.then_type));
      }
      const wait: WaitState = { request, state: sleep.state };
      return dispatch.task_sleep(wait, sleep.wait_ids, sleep.then_type);
    }

    // Runs the method a request names. An unknown one is a protocol error.
    private method_run(
      method: string,
      params: unknown,
    ): FieldTable | dispatch.Sleep {
      const run = this.methods.get(method);
      if (run === undefined) {
        throw new ProtocolError(
          constants.code_unknown,
          i18n("mcp.method_unknown", method),
        );
      }
      return run(params);
    }

    // Answers `initialize` with the revision, the capability and the name.
    private initialize_run(): FieldTable {
      return {
        protocolVersion: constants.protocol_version,
        capabilities: { tools: {} },
        serverInfo: { name: this.name, version: this.version },
      };
    }

    // Answers `tools/list` with the tools in the order they were registered.
    private list_run(): FieldTable {
      return { tools: [...this.tools.values()] };
    }

    // Runs the tool a `tools/call` names on its arguments, empty when absent.
    private call_run(params: unknown): FieldTable | dispatch.Sleep {
      if (!fields_is(params)) {
        throw new ProtocolError(
          constants.code_params,
          i18n("mcp.call_params"),
        );
      }
      const name = params.name;
      const args = Object.hasOwn(params, constants.arguments_field)
        ? params.arguments
        : {};
      if (typeof name !== "string" || !fields_is(args)) {
        throw new ProtocolError(
          constants.code_params,
          i18n("mcp.call_params"),
        );
      }
      const fn = this.calls.get(name);
      if (fn === undefined) {
        throw new ProtocolError(
          constants.code_params,
          i18n("mcp.tool_unknown", name),
        );
      }
      return this.tool_run(() => fn(args));
    }
  }

  // The client of one server, which submits `mcp` lines to the owner given.
  export class Client {
    private readonly name: string;
    private readonly version: string;
    private readonly tasks: queue.TaskQueue;
    private readonly owner: queue.ThreadName;
    private readonly sent = new Map<number, SentRequest>();
    private rpc_last = 0;
    private tools: Tool[] | undefined;

    // Keeps the identity, the queue and the owner of the server.
    constructor(
      name: string,
      version: string,
      tasks: queue.TaskQueue,
      owner: queue.ThreadName,
    ) {
      this.name = name;
      this.version = version;
      this.tasks = tasks;
      this.owner = owner;
    }

    // Submits `initialize` and returns the id to sleep on.
    initialize_send(): number {
      return this.request_send(constants.method_initialize, {
        params: {
          protocolVersion: constants.protocol_version,
          capabilities: {},
          clientInfo: { name: this.name, version: this.version },
        },
      });
    }

    // Checks the revision `initialize` answered, then sends `initialized`.
    initialized_send(reply: lines.Line): void {
      const result = this.result_read(reply, constants.method_initialize);
      const version = result.protocolVersion;
      if (version !== constants.protocol_version) {
        throw new Error(
          i18n("mcp.version_refused", version, constants.protocol_version),
        );
      }
      const line = this.line_build({
        jsonrpc: constants.jsonrpc_version,
        method: constants.method_initialized,
      });
      this.tasks.line_notify(line, this.owner);
    }

    // Submits `tools/list` and returns the id to sleep on.
    tools_list(): number {
      return this.request_send(constants.method_list, {});
    }

    // Reads the tools out of the `tools/list` reply and keeps them.
    tools_read(reply: lines.Line): Tool[] {
      const result = this.result_read(reply, constants.method_list);
      const tools = result.tools;
      if (!Array.isArray(tools) || !tools.every(tool_valid)) {
        throw new Error(
          i18n(
            "mcp.result_invalid",
            constants.method_list,
            reply_of(reply),
            utility.json_text(result),
          ),
        );
      }
      const read = tools as Tool[];
      this.tools = read;
      return read;
    }

    // The tools the `tools/list` reply gave, which must have been read.
    tools_cached(): Tool[] {
      const tools = this.tools;
      if (tools === undefined) {
        throw new Error(i18n("mcp.tools_unread", this.owner));
      }
      return tools;
    }

    // Submits `tools/call` of a tool by the server's name for it.
    tool_call(name: string, args: { [key: string]: unknown }): number {
      return this.request_send(constants.method_call, {
        params: { name, arguments: args },
      });
    }

    // Reads the tool result out of the `tools/call` reply a wake delivered.
    result_of(reply: lines.Line): ToolResult {
      const result = this.result_read(reply, constants.method_call);
      const flag = result.isError;
      if (
        !Array.isArray(result.content) ||
        (flag !== undefined && typeof flag !== "boolean")
      ) {
        throw new Error(
          i18n(
            "mcp.result_invalid",
            constants.method_call,
            reply_of(reply),
            utility.json_text(result),
          ),
        );
      }
      return result as unknown as ToolResult;
    }

    // Submits a request with the next `JSON-RPC` id and keeps what it sent.
    private request_send(method: string, fields: FieldTable): number {
      this.rpc_last += 1;
      const rpc = this.rpc_last;
      const message = {
        jsonrpc: constants.jsonrpc_version,
        id: rpc,
        method,
        ...fields,
      };
      const id = this.tasks.task_submit(this.line_build(message), this.owner);
      this.sent.set(id, { rpc, method });
      return id;
    }

    // Builds the `mcp` line of a message in the form the settings pick.
    private line_build(message: FieldTable): lines.Line {
      const header = jslb.header_make(constants.line_type, {
        full: settings.names_full(),
      });
      return jslb.line_make(header, [], message);
    }

    // The result of the reply to a request this client sent for the method.
    private result_read(reply: lines.Line, method: string): FieldTable {
      const id = reply_of(reply);
      const sent = this.sent.get(id);
      if (sent === undefined) {
        throw new Error(i18n("mcp.reply_unknown", id));
      }
      this.sent.delete(id);
      if (sent.method !== method) {
        throw new Error(i18n("mcp.reply_method", id, sent.method, method));
      }
      const message = jslb.payload_of(reply);
      if (
        message.jsonrpc !== constants.jsonrpc_version ||
        message.id !== sent.rpc
      ) {
        throw new Error(
          i18n(
            "mcp.response_invalid",
            id,
            sent.rpc,
            utility.json_text(message),
          ),
        );
      }
      if (Object.hasOwn(message, constants.error_field)) {
        throw new Error(
          i18n("mcp.reply_error", id, utility.json_text(message.error)),
        );
      }
      const result = message.result;
      if (!fields_is(result)) {
        throw new Error(
          i18n(
            "mcp.response_invalid",
            id,
            sent.rpc,
            utility.json_text(message),
          ),
        );
      }
      return result;
    }
  }

  // The view of several servers as one list of tools named `prefix.name`.
  export class ClientSet {
    private readonly clients = new Map<string, Client>();
    private readonly calls = new Map<number, Client>();

    // Adds a client under a new prefix that is not empty and holds no dot.
    client_add(prefix: string, client: Client): void {
      if (
        prefix === "" ||
        prefix.includes(constants.prefix_mark) ||
        this.clients.has(prefix)
      ) {
        throw new Error(i18n("mcp.prefix_refused", prefix));
      }
      this.clients.set(prefix, client);
    }

    // The tools of every client in the order added, each name prefixed.
    tools_cached(): Tool[] {
      const tools: Tool[] = [];
      for (const [prefix, client] of this.clients) {
        for (const tool of client.tools_cached()) {
          const name = prefix + constants.prefix_mark + tool.name;
          tools.push({ ...tool, name });
        }
      }
      return tools;
    }

    // Calls a prefixed tool through its client by the server's name for it.
    tool_call(name: string, args: { [key: string]: unknown }): number {
      const mark = name.indexOf(constants.prefix_mark);
      const client =
        mark < 0 ? undefined : this.clients.get(name.slice(0, mark));
      if (client === undefined) {
        throw new Error(i18n("mcp.prefix_unknown", name));
      }
      const id = client.tool_call(name.slice(mark + 1), args);
      this.calls.set(id, client);
      return id;
    }

    // Reads the tool result of a reply through the client that sent the call.
    result_of(reply: lines.Line): ToolResult {
      const id = reply_of(reply);
      const client = this.calls.get(id);
      if (client === undefined) {
        throw new Error(i18n("mcp.reply_unknown", id));
      }
      this.calls.delete(id);
      return client.result_of(reply);
    }
  }
}

Object.freeze(mcp);
