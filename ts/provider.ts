// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The door to xAI's Responses API: the `http.request` lines that ask a
// provider for a model response, `POST {base_url}/responses`, or for an image,
// the reading of the reply lines that answer them, and the conversion of MCP
// tools to flat function tools. It starts no request. Each request line is
// built in the form `settings.names_full()` picks, a model request's body
// written field by field in a fixed order, a field not given left out. A
// reply's output items are kept as parsed, with every field xAI sent, once
// the fields the agent reads are checked, so that they can go back as input.
// The request builders take the key as an argument, and the one copy it
// holds is the key `key_set` keeps, which the engine's program sets to the
// fixed text `scripted`: `provider.set` is deferred. The copy is in memory
// only.

namespace provider {
  // The line type, the request parts, the header names and the item types.
  const constants = Object.freeze({
    request_type: "http.request",
    method: "POST",
    model_path: "/responses",
    image_path: "/images/generations",
    authorization_name: "Authorization",
    authorization_scheme: "Bearer",
    content_name: "Content-Type",
    json_media: "application/json",
    function_type: "function" as const,
    reasoning_type: "reasoning",
    message_type: "message",
    call_type: "function_call",
    text_type: "output_text",
    assistant_role: "assistant",
    // The fields of a function call that the agent reads.
    call_fields: Object.freeze(["call_id", "name", "arguments"]),
    // What joins the texts of an output's messages.
    text_separator: "\n",
  });

  // What a request holds in place of its tool list in debug mode.
  export const tools_omitted = "DEBUG_MODE_TOOL_LIST_OMITTED";

  // The author of a turn of the log, the column `role` of its row.
  export type Role = "system" | "user" | "assistant" | "tool";

  // A message of the input: the system prompt or the player's text.
  export interface InputMessage {
    role: "system" | "user";
    content: string;
  }

  // A text part of an output message.
  export interface OutputText {
    type: "output_text";
    text: string;
  }

  // The model's message, its text in parts.
  export interface OutputMessage {
    type: "message";
    role: "assistant";
    content: OutputText[];
  }

  // A call of a function that the model asks for.
  export interface FunctionCall {
    type: "function_call";
    call_id: string;
    name: string;
    arguments: string;
  }

  // The model's reasoning, its encrypted content kept to be sent back.
  export interface ReasoningItem {
    type: "reasoning";
    id: string;
    encrypted_content?: string;
  }

  // The output of a function call, which answers it by `call_id`.
  export interface CallOutput {
    type: "function_call_output";
    call_id: string;
    output: string;
  }

  // An item of a reply's output.
  export type OutputItem = OutputMessage | FunctionCall | ReasoningItem;

  // An item of a request's input, and of a turn's row.
  export type InputItem = InputMessage | OutputItem | CallOutput;

  // A function the model may call, described by a JSON schema.
  export interface FunctionTool {
    type: "function";
    name: string;
    description: string;
    parameters: { [key: string]: unknown };
  }

  // The body of a model request. `previous_response_id` chains it.
  export interface ModelRequest {
    model: string;
    input: InputItem[];
    previous_response_id?: string;
    tools?: FunctionTool[] | typeof tools_omitted;
    tool_choice?: "auto" | "none" | "required";
    prompt_cache_key: string;
    include?: string[];
  }

  // The body of a model reply, as far as the door reads it.
  export interface ModelResponse {
    id: string;
    model: string;
    status: "completed" | "incomplete";
    output: OutputItem[];
  }

  // The body of an image request.
  export interface ImageRequest {
    model: string;
    prompt: string;
    n: number;
    response_format: "url" | "b64_json";
  }

  // The body of an image reply.
  export interface ImageResponse {
    data: { url?: string; b64_json?: string; revised_prompt?: string }[];
  }

  // An object of unknown members, as a parsed JSON body holds them.
  type FieldTable = { [key: string]: unknown };

  // The members of one image of an image reply.
  type ImageEntry = ImageResponse["data"][number];

  // Whether the value is an object that is neither an array nor `null`.
  function fields_is(value: unknown): value is FieldTable {
    return (
      typeof value === "object" && value !== null && !Array.isArray(value)
    );
  }

  // Whether the value is one of the two statuses of a reply the door takes.
  function status_is(value: unknown): value is ModelResponse["status"] {
    return value === "completed" || value === "incomplete";
  }

  // Throws the error for a part of the reply that is missing or not valid.
  function field_invalid(path: string): never {
    return utility.fail_now(i18n("provider.field_invalid", path));
  }

  // The object at the path of the reply, or a throw when it is not one.
  function fields_read(value: unknown, path: string): FieldTable {
    if (!fields_is(value)) {
      return field_invalid(path);
    }
    return value;
  }

  // The text at the key of the object, or a throw when it is not text.
  function text_read(fields: FieldTable, key: string, path: string): string {
    const value = fields[key];
    if (typeof value !== "string") {
      return field_invalid(`${path}.${key}`);
    }
    return value;
  }

  // Refuses a message that is not the model's or holds a part not of text.
  function message_check(fields: FieldTable, path: string): void {
    if (fields.role !== constants.assistant_role) {
      field_invalid(`${path}.role`);
    }
    const content = fields.content;
    if (!Array.isArray(content)) {
      return field_invalid(`${path}.content`);
    }
    content.forEach((value: unknown, index: number) => {
      const part_path = `${path}.content[${index}]`;
      const part = fields_read(value, part_path);
      if (part.type !== constants.text_type) {
        field_invalid(`${part_path}.type`);
      }
      text_read(part, "text", part_path);
    });
  }

  // The output item at the path of the reply, as parsed, once it is checked.
  function item_read(value: unknown, path: string): OutputItem {
    const fields = fields_read(value, path);
    const type = fields.type;
    if (type === constants.reasoning_type) {
      text_read(fields, "id", path);
    } else if (type === constants.message_type) {
      message_check(fields, path);
    } else if (type === constants.call_type) {
      for (const key of constants.call_fields) {
        text_read(fields, key, path);
      }
    } else {
      field_invalid(`${path}.type`);
    }
    return value as OutputItem;
  }

  // The image at the path of the reply, which has a url or base64 text.
  function image_read(value: unknown, path: string): ImageEntry {
    const fields = fields_read(value, path);
    const image: ImageEntry = {};
    for (const key of ["url", "b64_json", "revised_prompt"] as const) {
      if (Object.hasOwn(fields, key)) {
        image[key] = text_read(fields, key, path);
      }
    }
    if (image.url === undefined && image.b64_json === undefined) {
      return field_invalid(path);
    }
    return image;
  }

  // The JSON object a reply line carries, or a throw for any other reply.
  function body_read(reply: lines.Line): FieldTable {
    const type = jslb.field_get(reply[0], "type");
    const payload = jslb.payload_of(reply);
    if (type !== constants.request_type) {
      return utility.fail_now(
        i18n("provider.reply_type", type, constants.request_type),
      );
    }
    return fields_read(payload.json, "json");
  }

  // The `http.request` line that posts the body to the path of the base url.
  function post_make(
    base_url: string,
    key: string,
    path: string,
    body: FieldTable | ImageRequest,
  ): lines.Line {
    const scheme = constants.authorization_scheme;
    const headers = {
      [constants.authorization_name]: `${scheme} ${key}`,
      [constants.content_name]: constants.json_media,
    };
    const header = jslb.header_make(constants.request_type, {
      full: settings.names_full(),
    });
    return jslb.line_make(header, [], {
      method: constants.method,
      url: base_url + path,
      headers,
      json: body,
    });
  }

  // Builds the line that asks for a model response, to be submitted.
  export function model_request(
    base_url: string,
    key: string,
    request: ModelRequest,
  ): lines.Line {
    const body: FieldTable = { model: request.model };
    if (request.previous_response_id !== undefined) {
      body.previous_response_id = request.previous_response_id;
    }
    body.input = request.input;
    if (request.tools !== undefined) {
      body.tools = request.tools;
    }
    if (request.tool_choice !== undefined) {
      body.tool_choice = request.tool_choice;
    }
    body.prompt_cache_key = request.prompt_cache_key;
    if (request.include !== undefined) {
      body.include = request.include;
    }
    return post_make(base_url, key, constants.model_path, body);
  }

  // Builds the line that asks for an image, to be submitted.
  export function image_request(
    base_url: string,
    key: string,
    request: ImageRequest,
  ): lines.Line {
    return post_make(base_url, key, constants.image_path, request);
  }

  // Reads the model response out of the reply line a wake delivered.
  export function model_response(reply: lines.Line): ModelResponse {
    const body = body_read(reply);
    const id = text_read(body, "id", "json");
    const model = text_read(body, "model", "json");
    const status = body.status;
    if (!status_is(status)) {
      return field_invalid("json.status");
    }
    const output = body.output;
    if (!Array.isArray(output)) {
      return field_invalid("json.output");
    }
    return {
      id,
      model,
      status,
      output: output.map((item: unknown, index: number) =>
        item_read(item, `json.output[${index}]`),
      ),
    };
  }

  // Reads the images out of the reply line a wake delivered.
  export function image_response(reply: lines.Line): ImageResponse {
    const data = body_read(reply).data;
    if (!Array.isArray(data) || data.length === 0) {
      return field_invalid("json.data");
    }
    return {
      data: data.map((image: unknown, index: number) =>
        image_read(image, `json.data[${index}]`),
      ),
    };
  }

  // The function calls of an output, in order.
  export function calls_find(output: OutputItem[]): FunctionCall[] {
    return output.filter(
      (item: OutputItem): item is FunctionCall =>
        item.type === constants.call_type,
    );
  }

  // The texts of an output's messages joined, or `null` when it holds none.
  export function text_join(output: OutputItem[]): string | null {
    const messages = output.filter(
      (item: OutputItem): item is OutputMessage =>
        item.type === constants.message_type,
    );
    if (messages.length === 0) {
      return null;
    }
    return messages
      .flatMap((message) => message.content.map((part) => part.text))
      .join(constants.text_separator);
  }

  // Converts MCP tools to flat function tools, keeping the order and names.
  export function tools_convert(tools: mcp.Tool[]): FunctionTool[] {
    return tools.map((tool: mcp.Tool): FunctionTool => ({
      type: constants.function_type,
      name: tool.name,
      description: tool.description,
      parameters: tool.inputSchema,
    }));
  }

  // The provider key as set, or `undefined` before that.
  let key_stored: string | undefined = undefined;

  // Keeps the provider key in memory, replacing the one set before.
  export function key_set(key: string): void {
    key_stored = key;
  }

  // The provider key that was set, or a throw when none was.
  export function key_get(): string {
    if (key_stored === undefined) {
      return utility.fail_now(i18n("provider.key_missing"));
    }
    return key_stored;
  }
}

Object.freeze(provider);
