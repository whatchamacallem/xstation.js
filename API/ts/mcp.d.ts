declare namespace mcp {
  // JSON-RPC 2.0. An id is a number or string; a notification has none.
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
    error: { code: number; message: string; data?: unknown };
  }

  type Message = Request | Notification | Response | ErrorResponse;

  // A tool as `tools/list` lists it. `_meta.xsjs.permit` marks one the
  // UI must confirm before it runs.
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

  // The revision pinned, a constant: "2025-06-18". The methods served
  // and called: `initialize`, `notifications/initialized`, `ping`,
  // `tools/list`, `tools/call`; capability `tools` only.
  const constants: { readonly protocol_version: string };

  // A tool function runs inside the `mcp` line's handler: it returns the
  // result, or a sleep whose wake produces the result.
  type ToolFn = (args: {
    [key: string]: unknown;
  }) => ToolResult | dispatch.Sleep;

  class Server {
    constructor(name: string, version: string);
    tool_register(tool: Tool, fn: ToolFn): void;
    // Handles one message; a method's throw becomes an error response.
    message_handle(message: Message): Message | dispatch.Sleep | undefined;
  }

  // The client sends each message as the payload of an `mcp` line on a
  // port of the queue and reads the response from the wake.
  class Client {
    constructor(
      name: string,
      version: string,
      tasks: queue.TaskQueue,
      owner: queue.ThreadName,
    );
    // Submits `initialize`; the wake carries the server's capabilities,
    // after which `notifications/initialized` is sent.
    initialize_send(): number;
    tools_list(): number;
    tool_call(name: string, args: { [key: string]: unknown }): number;
    // Reads the result out of the reply line a wake delivered.
    result_of(reply: lines.Line): ToolResult;
  }

  // The agent's view of several servers as one flat tool list, each
  // tool named `<prefix>.<name>`.
  class ClientSet {
    client_add(prefix: string, client: Client): void;
    tools_cached(): Tool[];
    tool_call(name: string, args: { [key: string]: unknown }): number;
  }
}
