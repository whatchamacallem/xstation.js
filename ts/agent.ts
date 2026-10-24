// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The agent loop on the AI thread, a turn as a chain of tasks. The player's
// text or click joins the conversation of the scene on screen and goes to the
// provider after the system prompt. A reply's tool calls go to the MCP
// clients, and once every result is in the reply and its results are stored
// together, so that no stored call lacks its answer, and go back to the
// provider. The reply with no tool calls is stored and ends the turn with its
// text as the subtitle. Nothing measures the databases: no request carries
// their sizes, and the loop reads no setting. A tool call's arguments are
// read by `jslb.json_decode`. Two `universe` rows cannot name one world: the
// triggers of API/sql/metaverse.sql refuse the second with
// `agent.content_ambiguous` before it is added.

namespace agent {
  // The line types, refs, ids and statements the loop uses.
  const constants = Object.freeze({
    say_type: "ai.say",
    click_type: "ai.click",
    model_type: "ai.model_reply",
    tool_type: "ai.tool_reply",
    handler_version: 0,
    metaverse: "metaverse",
    world_ref: "/metaverse/world",
    scene_key: "scene",
    prompt_id: "prompt",
    part_separator: "\n",
    tool_choice: "auto" as const,
    // The universe whose row names a world, one at most by the triggers.
    universe_sql: "SELECT name FROM universe WHERE world = ?",
    // The version of the head of a document id, in the substrate's own table.
    head_sql: "SELECT version FROM _head WHERE id = ?",
  });

  // Registers the handler of one line type and version.
  type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // What a turn waiting on the model keeps: the request it owes, its scene.
  interface TurnState {
    request: lines.Line;
    scene: lines.DocRef;
  }

  // What a turn waiting on tools keeps besides: the reply that called them.
  interface CallState extends TurnState {
    asked: provider.ChatMessage;
  }

  // The text of a value held in its row, as a small value is.
  function text_get(store: substrate.Store, ref: lines.KvRef): string {
    return utility.utf8_decode(store.kv_get(ref).data as Uint8Array);
  }

  // The database of the current world, the value of `/metaverse/world`.
  function world_current(store: substrate.Store): string {
    return text_get(store, constants.world_ref);
  }

  // The scene on screen, the `Document-Ref` in the row `scene` of the world.
  function scene_current(store: substrate.Store): lines.DocRef {
    const world = world_current(store);
    return text_get(store, `/${world}/${constants.scene_key}`);
  }

  // The text of a prompt document, the string its member `text` holds.
  function prompt_text(store: substrate.Store, ref: lines.DocRef): string {
    const text = substrate.doc_decode(store.doc_get(ref)).text;
    if (typeof text !== "string") {
      throw new Error(i18n("agent.prompt_invalid", ref));
    }
    return text;
  }

  // The universe whose row names the current world, when one does.
  function universe_current(store: substrate.Store): string | undefined {
    const world = world_current(store);
    const statement = { sql: constants.universe_sql, params: [world] };
    const rows = store.sql_run(constants.metaverse, [statement])[0].rows;
    return rows.length === 0 ? undefined : (rows[0][0] as string);
  }

  // The text of a tool result for its tool message, its text parts joined.
  function result_text(result: mcp.ToolResult, call_id: string): string {
    const texts = result.content.map((part: mcp.Content): string => {
      if (part.type !== "text") {
        throw new Error(i18n("agent.content_unsupported", call_id, part.type));
      }
      return part.text;
    });
    return texts.join(constants.part_separator);
  }

  // The system prompt: the analyst's prompt, then the universe's when present.
  export function prompt_build(
    store: substrate.Store,
  ): provider.ChatMessage[] {
    const analyst = store.doc_head(constants.metaverse, constants.prompt_id);
    const messages: provider.ChatMessage[] = [
      { role: "system", content: prompt_text(store, analyst) },
    ];
    const universe = universe_current(store);
    if (universe === undefined) {
      return messages;
    }
    const statement = {
      sql: constants.head_sql,
      params: [constants.prompt_id],
    };
    const rows = store.sql_run(universe, [statement])[0].rows;
    if (rows.length > 0) {
      const ref = `/${universe}/${constants.prompt_id}/${String(rows[0][0])}`;
      messages.push({ role: "system", content: prompt_text(store, ref) });
    }
    return messages;
  }

  // One registration of the loop: what it works with and what it holds.
  class TurnLoop {
    // The store of every database, which holds the turns.
    readonly #store: substrate.Store;
    // The MCP clients that run the tool calls.
    readonly #clients: mcp.ClientSet;
    // The task manager of this thread.
    readonly #tasks: queue.TaskQueue;
    // The owner whose port answers the provider's requests.
    readonly #provider_owner: queue.ThreadName;
    // The provider's address and the model every chat request names.
    readonly #info: lines.ProviderInfo;

    // Takes what the handlers work with.
    constructor(
      store: substrate.Store,
      clients: mcp.ClientSet,
      tasks: queue.TaskQueue,
      provider_owner: queue.ThreadName,
      info: lines.ProviderInfo,
    ) {
      this.#store = store;
      this.#clients = clients;
      this.#tasks = tasks;
      this.#provider_owner = provider_owner;
      this.#info = info;
    }

    // Starts a turn with the text the player said.
    say_handle(line: lines.Line): dispatch.Sleep {
      return this.turn_start(line, line.text as string);
    }

    // Starts a turn with the place the player clicked, told as text.
    click_handle(line: lines.Line): dispatch.Sleep {
      return this.turn_start(line, i18n("agent.click_text", line.x, line.y));
    }

    // Calls the reply's tools, keeping it unstored, or stores it as the end.
    model_handle(line: lines.Line): lines.Line | dispatch.Sleep {
      const state = line.state as TurnState;
      const [reply] = line.replies as lines.Line[];
      const response = provider.chat_response(reply);
      const message = response.choices[0].message;
      const calls = message.tool_calls ?? [];
      if (calls.length > 0) {
        const ids = calls.map((call) => this.call_submit(call));
        const next: CallState = {
          request: state.request,
          scene: state.scene,
          asked: message,
        };
        return dispatch.task_sleep(next, ids, constants.tool_type);
      }
      const subtitle = message.content;
      if (subtitle === null) {
        throw new Error(i18n("agent.reply_empty", response.id));
      }
      const store = this.#store;
      const appended = store.turn_append(state.scene, message.role, message);
      const scene = scene_current(store);
      return dispatch.reply_make(state.request, {
        turn: appended.n,
        scene,
        subtitle,
      });
    }

    // Stores the reply that called the tools and their results, then asks.
    tool_handle(line: lines.Line): dispatch.Sleep {
      const state = line.state as CallState;
      const replies = line.replies as lines.Line[];
      const calls = state.asked.tool_calls as provider.ToolCall[];
      const answers = replies.map(
        (reply: lines.Line, index: number): provider.ChatMessage => {
          const call_id = calls[index].id;
          const result = this.#clients.result_of(reply);
          return {
            role: "tool",
            tool_call_id: call_id,
            content: result_text(result, call_id),
          };
        },
      );
      const store = this.#store;
      store.transaction_run(() => {
        for (const message of [state.asked, ...answers]) {
          store.turn_append(state.scene, message.role, message);
        }
      });
      return this.request_submit(state.request, state.scene);
    }

    // Appends the player's message to the scene on screen and asks the model.
    turn_start(request: lines.Line, text: string): dispatch.Sleep {
      const scene = scene_current(this.#store);
      const message: provider.ChatMessage = { role: "user", content: text };
      this.#store.turn_append(scene, message.role, message);
      return this.request_submit(request, scene);
    }

    // Submits the chat request of the scene's conversation and sleeps on it.
    request_submit(request: lines.Line, scene: lines.DocRef): dispatch.Sleep {
      const store = this.#store;
      const messages = prompt_build(store);
      for (const row of store.turn_list(scene)) {
        messages.push(row.content);
      }
      const info = this.#info;
      const line = provider.chat_request(info.base_url, provider.key_get(), {
        model: info.chat_model,
        messages,
        tools: provider.tools_convert(this.#clients.tools_cached()),
        tool_choice: constants.tool_choice,
      });
      const id = this.#tasks.task_submit(line, this.#provider_owner);
      const state: TurnState = { request, scene };
      return dispatch.task_sleep(state, [id], constants.model_type);
    }

    // Submits one tool call, whose arguments must be a JSON object.
    call_submit(call: provider.ToolCall): number {
      const name = call.function.name;
      const text = call.function.arguments;
      let args: unknown;
      try {
        args = jslb.json_decode(text);
      } catch (error) {
        throw utility.error_wrap(
          i18n("agent.arguments_invalid", call.id, name, text),
          error,
        );
      }
      if (typeof args !== "object" || args === null || Array.isArray(args)) {
        throw new Error(i18n("agent.arguments_invalid", call.id, name, text));
      }
      return this.#clients.tool_call(name, args as { [key: string]: unknown });
    }
  }

  // Registers the handlers of a turn's lines with the register given.
  export function handlers_register(
    store: substrate.Store,
    clients: mcp.ClientSet,
    tasks: queue.TaskQueue,
    provider_owner: queue.ThreadName,
    info: lines.ProviderInfo,
    register: HandlerRegister,
  ): void {
    const loop = new TurnLoop(store, clients, tasks, provider_owner, info);
    const version = constants.handler_version;
    register(constants.say_type, version, (line) => loop.say_handle(line));
    register(constants.click_type, version, (line) => loop.click_handle(line));
    register(constants.model_type, version, (line) => loop.model_handle(line));
    register(constants.tool_type, version, (line) => loop.tool_handle(line));
  }
}

Object.freeze(agent);
