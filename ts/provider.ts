// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The door to the chat completion protocol: the `http.request` lines that ask
// a provider for a chat completion or an image, the reading of the reply
// lines that answer them, and the conversion of MCP tools to function tools.
// It starts no request. The request builders take the key as an argument, and
// the one copy it holds is the key that `hello` brings, in memory only.

namespace provider {
  // The line type, the request parts, the header names and the tool type.
  const constants = Object.freeze({
    request_type: "http.request",
    method: "POST",
    chat_path: "/chat/completions",
    image_path: "/images/generations",
    authorization_name: "Authorization",
    authorization_scheme: "Bearer",
    content_name: "Content-Type",
    json_media: "application/json",
    function_type: "function" as const,
  });

  // The author of a chat message.
  export type Role = "system" | "user" | "assistant" | "tool";

  // A call of a function that the model asks for.
  export interface ToolCall {
    id: string;
    type: "function";
    function: { name: string; arguments: string };
  }

  // One message of a conversation.
  export interface ChatMessage {
    role: Role;
    content: string | null;
    tool_calls?: ToolCall[];
    tool_call_id?: string;
  }

  // A function the model may call, described by a JSON schema.
  export interface FunctionTool {
    type: "function";
    function: {
      name: string;
      description: string;
      parameters: { [key: string]: unknown };
    };
  }

  // The body of a chat completion request.
  export interface ChatRequest {
    model: string;
    messages: ChatMessage[];
    tools?: FunctionTool[];
    tool_choice?: "auto" | "none" | "required";
  }

  // One answer of a chat completion.
  export interface ChatChoice {
    index: number;
    message: ChatMessage;
    finish_reason: "stop" | "tool_calls" | "length";
  }

  // The body of a chat completion reply.
  export interface ChatResponse {
    id: string;
    model: string;
    choices: ChatChoice[];
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
  type Fields = { [key: string]: unknown };

  // The members of one image of an image reply.
  type ImageEntry = ImageResponse["data"][number];

  // Whether the value is an object that is neither an array nor `null`.
  function fields_is(value: unknown): value is Fields {
    return (
      typeof value === "object" && value !== null && !Array.isArray(value)
    );
  }

  // Whether the value is one of the four roles.
  function role_is(value: unknown): value is Role {
    return (
      value === "system" ||
      value === "user" ||
      value === "assistant" ||
      value === "tool"
    );
  }

  // Whether the value is one of the three finish reasons.
  function reason_is(value: unknown): value is ChatChoice["finish_reason"] {
    return value === "stop" || value === "tool_calls" || value === "length";
  }

  // Throws the error for a part of the reply that is missing or not valid.
  function field_invalid(path: string): never {
    return utility.fail_now(i18n("provider.field_invalid", path));
  }

  // The object at the path of the reply, or a throw when it is not one.
  function fields_read(value: unknown, path: string): Fields {
    if (!fields_is(value)) {
      return field_invalid(path);
    }
    return value;
  }

  // The text at the key of the object, or a throw when it is not text.
  function text_read(fields: Fields, key: string, path: string): string {
    const value = fields[key];
    if (typeof value !== "string") {
      return field_invalid(`${path}.${key}`);
    }
    return value;
  }

  // The content of a message: text, or `null` when it only calls tools.
  function content_read(fields: Fields, path: string): string | null {
    const value = fields.content;
    if (value !== null && typeof value !== "string") {
      return field_invalid(`${path}.content`);
    }
    return value;
  }

  // The tool call at the path of the reply.
  function call_read(value: unknown, path: string): ToolCall {
    const fields = fields_read(value, path);
    const id = text_read(fields, "id", path);
    if (fields.type !== constants.function_type) {
      return field_invalid(`${path}.type`);
    }
    const body_path = `${path}.function`;
    const body = fields_read(fields.function, body_path);
    const name = text_read(body, "name", body_path);
    const args = text_read(body, "arguments", body_path);
    return {
      id,
      type: constants.function_type,
      function: { name, arguments: args },
    };
  }

  // The tool calls at the path of the reply.
  function calls_read(value: unknown, path: string): ToolCall[] {
    if (!Array.isArray(value)) {
      return field_invalid(path);
    }
    return value.map((call: unknown, index: number) =>
      call_read(call, `${path}[${index}]`),
    );
  }

  // The chat message at the path of the reply.
  function message_read(value: unknown, path: string): ChatMessage {
    const fields = fields_read(value, path);
    const role = fields.role;
    if (!role_is(role)) {
      return field_invalid(`${path}.role`);
    }
    const content = content_read(fields, path);
    const message: ChatMessage = { role, content };
    if (Object.hasOwn(fields, "tool_calls")) {
      message.tool_calls = calls_read(fields.tool_calls, `${path}.tool_calls`);
    }
    if (Object.hasOwn(fields, "tool_call_id")) {
      message.tool_call_id = text_read(fields, "tool_call_id", path);
    }
    return message;
  }

  // The chat choice at the path of the reply.
  function choice_read(value: unknown, path: string): ChatChoice {
    const fields = fields_read(value, path);
    const index = fields.index;
    if (typeof index !== "number") {
      return field_invalid(`${path}.index`);
    }
    const message = message_read(fields.message, `${path}.message`);
    const reason = fields.finish_reason;
    if (!reason_is(reason)) {
      return field_invalid(`${path}.finish_reason`);
    }
    return { index, message, finish_reason: reason };
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
  function body_read(reply: lines.Line): Fields {
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
    body: ChatRequest | ImageRequest,
  ): lines.Line {
    const scheme = constants.authorization_scheme;
    const headers = {
      [constants.authorization_name]: `${scheme} ${key}`,
      [constants.content_name]: constants.json_media,
    };
    return jslb.line_make(jslb.header_make(constants.request_type), [], {
      method: constants.method,
      url: base_url + path,
      headers,
      json: body,
    });
  }

  // Builds the line that asks for a chat completion, to be submitted.
  export function chat_request(
    base_url: string,
    key: string,
    request: ChatRequest,
  ): lines.Line {
    return post_make(base_url, key, constants.chat_path, request);
  }

  // Builds the line that asks for an image, to be submitted.
  export function image_request(
    base_url: string,
    key: string,
    request: ImageRequest,
  ): lines.Line {
    return post_make(base_url, key, constants.image_path, request);
  }

  // Reads the chat completion out of the reply line a wake delivered.
  export function chat_response(reply: lines.Line): ChatResponse {
    const body = body_read(reply);
    const choices = body.choices;
    if (!Array.isArray(choices) || choices.length === 0) {
      return field_invalid("json.choices");
    }
    return {
      id: text_read(body, "id", "json"),
      model: text_read(body, "model", "json"),
      choices: choices.map((choice: unknown, index: number) =>
        choice_read(choice, `json.choices[${index}]`),
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

  // Converts MCP tools to function tools, keeping the order and dotted names.
  export function tools_convert(tools: mcp.Tool[]): FunctionTool[] {
    return tools.map(
      (tool: mcp.Tool): FunctionTool => ({
        type: constants.function_type,
        function: {
          name: tool.name,
          description: tool.description,
          parameters: tool.inputSchema,
        },
      }),
    );
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
