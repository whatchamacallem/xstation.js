declare namespace provider {
  // The generic chat completion protocol: `POST {base_url}/chat/completions`
  // and `POST {base_url}/images/generations`, as xAI and OpenAI serve them
  // and Anthropic's compatibility endpoint serves the first.

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
    usage?: { prompt_tokens: number; completion_tokens: number };
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

  // The one door. `provider_script.ScriptProvider` implements it too.
  interface Provider {
    chat_complete(request: ChatRequest): Promise<ChatResponse>;
    image_generate(request: ImageRequest): Promise<ImageResponse>;
  }

  // One HTTPS request per call from the AI worker, the key in the
  // `Authorization` header, `timeout_seconds` from settings. A non-2xx
  // status or a body that isn't the shape above throws.
  class HttpProvider implements Provider {
    constructor(base_url: string, key: string, timeout_seconds: number);
    chat_complete(request: ChatRequest): Promise<ChatResponse>;
    image_generate(request: ImageRequest): Promise<ImageResponse>;
  }

  // Converts MCP tools to function tools for the request.
  function tools_convert(tools: mcp.Tool[]): FunctionTool[];
}
