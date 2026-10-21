declare namespace provider {
  // The generic chat completion protocol: `POST {base_url}/chat/completions`
  // and `POST {base_url}/images/generations`, as xAI serves them. xAI is
  // the only provider tested.

  type Role = "system" | "user" | "assistant" | "tool";

  interface ToolCall {
    id: string;
    type: "function";
    function: { name: string; arguments: string };
  }

  interface ChatMessage {
    role: Role;
    content: string | null;
    tool_calls?: ToolCall[];
    tool_call_id?: string;
  }

  interface FunctionTool {
    type: "function";
    function: {
      name: string;
      description: string;
      parameters: { [key: string]: unknown };
    };
  }

  interface ChatRequest {
    model: string;
    messages: ChatMessage[];
    tools?: FunctionTool[];
    tool_choice?: "auto" | "none" | "required";
  }

  interface ChatChoice {
    index: number;
    message: ChatMessage;
    finish_reason: "stop" | "tool_calls" | "length";
  }

  interface ChatResponse {
    id: string;
    model: string;
    choices: ChatChoice[];
  }

  interface ImageRequest {
    model: string;
    prompt: string;
    n: number;
    response_format: "url" | "b64_json";
  }

  interface ImageResponse {
    data: { url?: string; b64_json?: string; revised_prompt?: string }[];
  }

  // The one door. Each builds one `http.request` line with the key in
  // the `Authorization` header; the caller submits it to the HTTP port,
  // or to the scripted port, and sleeps on the id.
  function chat_request(
    base_url: string,
    key: string,
    request: ChatRequest,
  ): lines.Line;
  function image_request(
    base_url: string,
    key: string,
    request: ImageRequest,
  ): lines.Line;

  // Read the reply line of a wake. A body that isn't the shape above
  // throws.
  function chat_response(reply: lines.Line): ChatResponse;
  function image_response(reply: lines.Line): ImageResponse;

  // Converts MCP tools to function tools for the request.
  function tools_convert(tools: mcp.Tool[]): FunctionTool[];
}
