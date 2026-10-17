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
    inputSchema: { type: "object"; properties: { [key: string]: unknown }; required?: string[] };
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

  // The methods served and called: `initialize`,
  // `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
  // Revision `settings.mcp_protocol_version`; capability `tools` only.

  interface Transport {
    send(message: Message): void;
    receive(fn: (message: Message) => void): void;
  }

  // Same thread: a pair of ports wired to each other.
  class LocalTransport implements Transport {
    send(message: Message): void;
    receive(fn: (message: Message) => void): void;
    // The other end.
    peer(): Transport;
  }

  // Over the wire: each message is the payload of one `mcp` line.
  class JslbTransport implements Transport {
    constructor(tasks: queue.TaskQueue);
    send(message: Message): void;
    receive(fn: (message: Message) => void): void;
  }

  class Server {
    constructor(name: string, version: string, transport: Transport);
    tool_register(tool: Tool, fn: (args: { [key: string]: unknown }) => Promise<ToolResult>): void;
    // Handles one message; a method's throw becomes an error response.
    message_handle(message: Message): Promise<Message | undefined>;
  }

  class Client {
    constructor(name: string, version: string, transport: Transport);
    // `initialize`, then `notifications/initialized`; resolves with the
    // server's capabilities.
    initialize_send(): Promise<{ [key: string]: unknown }>;
    tools_list(): Promise<Tool[]>;
    tool_call(name: string, args: { [key: string]: unknown }): Promise<ToolResult>;
  }

  // The agent's view of several servers as one flat tool list, each
  // tool named `<prefix>.<name>`.
  class ClientSet {
    client_add(prefix: string, client: Client): void;
    tools_list(): Promise<Tool[]>;
    tool_call(name: string, args: { [key: string]: unknown }): Promise<ToolResult>;
  }
}
