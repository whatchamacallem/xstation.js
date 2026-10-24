// The Model Context Protocol over JSON-RPC 2.0, revision "2025-06-18" pinned.
// The methods served and called: `initialize`, `notifications/initialized`,
// `ping`, `tools/list` and `tools/call`; the capability `tools` only. MCP is
// a testing protocol for now: no AI is a requirement of the tests yet.
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

declare namespace mcp {
  // An id is a number or a string, and a notification has none.
  type Id = number | string;

  interface Request {
    jsonrpc: "2.0";
    id: Id;
    method: string;
    params?: { [key: string]: unknown };
  }

  interface Notification {
    jsonrpc: "2.0";
    method: string;
    params?: { [key: string]: unknown };
  }

  interface Response {
    jsonrpc: "2.0";
    id: Id;
    result: { [key: string]: unknown };
  }

  interface ErrorResponse {
    jsonrpc: "2.0";
    id: Id | null;
    error: { code: number; message: string; data?: lines.ErrorCause };
  }

  type Message = Request | Notification | Response | ErrorResponse;

  // A tool as `tools/list` lists it. `_meta.xsjs.permit` asks the UI first.
  interface Tool {
    name: string;
    description: string;
    inputSchema: {
      type: "object";
      properties: { [key: string]: unknown };
      required?: string[];
    };
    _meta?: { xsjs: { permit: boolean } };
  }

  // The content of a `tools/call` result.
  type Content =
    | { type: "text"; text: string }
    | { type: "image"; data: string; mimeType: string };

  interface ToolResult {
    content: Content[];
    isError?: boolean;
  }

  const constants: { readonly protocol_version: string };

  // A tool runs inside the `mcp` line's handler: its result or a sleep.
  type ToolFn = (args: {
    [key: string]: unknown;
  }) => ToolResult | dispatch.Sleep;

  // A tool's wake continues it from its state and the replies it awaited.
  type WakeFn = (
    state: unknown,
    replies: lines.Line[],
  ) => ToolResult | dispatch.Sleep;

  class Server {
    constructor(name: string, version: string);
    tool_register(tool: Tool, fn: ToolFn): void;
    // Registers a wake type a tool sleeps with and the function it runs.
    wake_register(then_type: string, fn: WakeFn): void;
    // Handles one message: the response, a tool's sleep, or nothing.
    message_handle(message: Message): Message | dispatch.Sleep | undefined;
    // The exception of the last request answered with one, then undefined.
    failure_take(): Error | undefined;
    // Handles one `mcp` line: the reply, a sleep, a failure, or nothing.
    line_handle(
      line: lines.Line,
    ): dispatch.Reply | dispatch.Sleep | dispatch.Failure;
  }

  // The client of one server, which submits `mcp` lines to the owner given.
  class Client {
    constructor(
      name: string,
      version: string,
      tasks: queue.TaskQueue,
      owner: queue.ThreadName,
    );
    // Submits `initialize`. Returns the id to sleep on.
    initialize_send(): number;
    // Checks the revision the reply gives, then sends `initialized`.
    initialized_send(reply: lines.Line): void;
    tools_list(): number;
    // Keeps the tools a `tools/list` reply holds.
    tools_read(reply: lines.Line): Tool[];
    tools_cached(): Tool[];
    tool_call(name: string, args: { [key: string]: unknown }): number;
    // Reads the result out of the reply line a wake delivered.
    result_of(reply: lines.Line): ToolResult;
  }

  // Several servers as one flat tool list, each tool `prefix.name`.
  class ClientSet {
    client_add(prefix: string, client: Client): void;
    tools_cached(): Tool[];
    tool_call(name: string, args: { [key: string]: unknown }): number;
    result_of(reply: lines.Line): ToolResult;
  }
}
