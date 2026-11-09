// xAI's Responses API, `POST {base_url}/responses`, and its image endpoint,
// `POST {base_url}/images/generations`. xAI is the only provider tested. The
// one door: each request is one `http.request` line, built in the form
// `settings.names_full()` picks, with the key in the `Authorization` header,
// which the caller submits to the HTTP port or to the scripted port and sleeps
// on. The key stays in this module's memory and on the line, and the queue's
// audit masks it out of the debug record. A model request names the
// conversation by `prompt_cache_key`, so that xAI routes it to the server
// holding its cache, and asks for the encrypted reasoning by `include`. A
// reply's output items are kept as xAI sent them, once the fields the agent
// reads are checked, so that they can go back as input.

declare namespace provider {
  // What a request holds in place of its tool list in debug mode.
  const tools_omitted: "DEBUG_MODE_TOOL_LIST_OMITTED";

  // The author of a turn of the log, the column `role` of its row.
  type Role = "system" | "user" | "assistant" | "tool";

  // A message of the input: the system prompt or the player's text.
  interface InputMessage {
    role: "system" | "user";
    content: string;
  }

  // A text part of an output message.
  interface OutputText {
    type: "output_text";
    text: string;
  }

  // The model's message, its text in parts.
  interface OutputMessage {
    type: "message";
    role: "assistant";
    content: OutputText[];
  }

  // A call of a function that the model asks for.
  interface FunctionCall {
    type: "function_call";
    call_id: string;
    name: string;
    arguments: string;
  }

  // The model's reasoning, its encrypted content kept to be sent back.
  interface ReasoningItem {
    type: "reasoning";
    id: string;
    encrypted_content?: string;
  }

  // The output of a function call, which answers it by `call_id`.
  interface CallOutput {
    type: "function_call_output";
    call_id: string;
    output: string;
  }

  // An item of a reply's output.
  type OutputItem = OutputMessage | FunctionCall | ReasoningItem;

  // An item of a request's input, and of a turn's row.
  type InputItem = InputMessage | OutputItem | CallOutput;

  // A function the model may call, described by a JSON schema.
  interface FunctionTool {
    type: "function";
    name: string;
    description: string;
    parameters: { [key: string]: unknown };
  }

  // The body of a model request. `previous_response_id` chains it.
  interface ModelRequest {
    model: string;
    input: InputItem[];
    previous_response_id?: string;
    tools?: FunctionTool[] | typeof tools_omitted;
    tool_choice?: "auto" | "none" | "required";
    prompt_cache_key: string;
    include?: string[];
  }

  // The body of a model reply, as far as the door reads it.
  interface ModelResponse {
    id: string;
    model: string;
    status: "completed" | "incomplete";
    output: OutputItem[];
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

  function model_request(
    base_url: string,
    key: string,
    request: ModelRequest,
  ): lines.Line;

  function image_request(
    base_url: string,
    key: string,
    request: ImageRequest,
  ): lines.Line;

  // Reads the reply line of a wake. A body of another shape throws.
  function model_response(reply: lines.Line): ModelResponse;
  function image_response(reply: lines.Line): ImageResponse;

  // The function calls of an output, in order.
  function calls_find(output: OutputItem[]): FunctionCall[];

  // The texts of an output's messages joined, or null when it holds none.
  function text_join(output: OutputItem[]): string | null;

  // Converts MCP tools to function tools, keeping the order and the names.
  function tools_convert(tools: mcp.Tool[]): FunctionTool[];

  // Keeps the provider key in memory, replacing the one set before.
  function key_set(key: string): void;

  // The key that was set. Throws `provider.key_missing` when none is.
  function key_get(): string;
}
