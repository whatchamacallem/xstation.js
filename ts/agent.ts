// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The agent loop on the AI thread, a turn as a chain of tasks. The player's
// text or click joins the conversation of the scene on screen, whose log gets
// the system prompt once, before its first model call. A row of the log holds
// one turn's input items of the Responses API. A reply's function calls go to
// the MCP clients, and once every result is in, the reply and its call outputs
// are stored together, so that no stored call lacks its output, and the model
// is asked again. The reply with no calls is stored and ends the turn with its
// text as the subtitle. Per scene the loop keeps in memory a chain, the last
// response's id and the rows its context holds: a request whose log still
// begins with those rows sends the rows after them, chained by
// `previous_response_id`, and any other sends the whole log, as the first
// after a page load or a compaction. Nothing measures the databases, and the
// loop reads no setting. A call's arguments are read by `jslb.json_decode`.
// The triggers of API/sql/metaverse.sql refuse a second `universe` row naming
// one world with `agent.content_ambiguous`.
// In debug mode, by its reader, the tools sent are `provider.tools_omitted`.

namespace agent {
  // The line types, refs, ids, roles and statements the loop uses.
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
    // The reasoning every reply carries encrypted, to be sent back in the log.
    include_reasoning: "reasoning.encrypted_content",
    // The roles of the rows the loop stores.
    system_role: "system" as const,
    user_role: "user" as const,
    reply_role: "assistant" as const,
    output_role: "tool" as const,
    // The type of the item that answers a function call.
    output_type: "function_call_output" as const,
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

  // A scene's chain: the last response's id and its context's row texts.
  interface SceneChain {
    id: string;
    texts: string[];
  }

  // What a turn waiting on the model keeps: its request, scene and row texts.
  interface TurnState {
    request: lines.Line;
    scene: lines.DocRef;
    texts: string[];
  }

  // What a turn waiting on functions keeps besides: the reply's id and output.
  interface CallState extends TurnState {
    response: string;
    output: provider.OutputItem[];
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

  // The text of a tool result for its call's output, its text parts joined.
  function result_text(result: mcp.ToolResult, call_id: string): string {
    const texts = result.content.map((part: mcp.Content): string => {
      if (part.type !== "text") {
        throw new Error(i18n("agent.content_unsupported", call_id, part.type));
      }
      return part.text;
    });
    return texts.join(constants.part_separator);
  }

  // The text a row compares by, the JSON text of its parsed content.
  function row_text(row: substrate.TurnRow): string {
    return utility.json_text(row.content);
  }

  // Whether the texts begin with the prefix's texts, each at its place.
  function prefix_holds(prefix: string[], texts: string[]): boolean {
    return (
      prefix.length <= texts.length &&
      prefix.every((text, index) => text === texts[index])
    );
  }

  // The system prompt: the analyst's prompt, then the universe's when present.
  export function prompt_build(
    store: substrate.Store,
  ): provider.InputMessage[] {
    const analyst = store.doc_head(constants.metaverse, constants.prompt_id);
    const messages: provider.InputMessage[] = [
      { role: constants.system_role, content: prompt_text(store, analyst) },
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
      messages.push({
        role: constants.system_role,
        content: prompt_text(store, ref),
      });
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
    // The provider's address and the model every model request names.
    readonly #info: lines.ProviderInfo;
    // Whether debug mode is on, which sends no tool list.
    readonly #debug: () => boolean;
    // The chain of each scene by its ref, held in memory alone.
    readonly #chains = new Map<lines.DocRef, SceneChain>();

    // Takes what the handlers work with.
    constructor(
      store: substrate.Store,
      clients: mcp.ClientSet,
      tasks: queue.TaskQueue,
      provider_owner: queue.ThreadName,
      info: lines.ProviderInfo,
      debug: () => boolean,
    ) {
      this.#store = store;
      this.#clients = clients;
      this.#tasks = tasks;
      this.#provider_owner = provider_owner;
      this.#info = info;
      this.#debug = debug;
    }

    // Starts a turn with the text the player said.
    say_handle(line: lines.Line): dispatch.Sleep {
      return this.turn_start(line, line.text as string);
    }

    // Starts a turn with the place the player clicked, told as text.
    click_handle(line: lines.Line): dispatch.Sleep {
      return this.turn_start(line, i18n("agent.click_text", line.x, line.y));
    }

    // Calls the reply's functions, keeping it unstored, or stores it, the end.
    model_handle(line: lines.Line): lines.Line | dispatch.Sleep {
      const state = line.state as TurnState;
      const [reply] = line.replies as lines.Line[];
      const response = provider.model_response(reply);
      const calls = provider.calls_find(response.output);
      if (calls.length > 0) {
        const ids = calls.map((call) => this.call_submit(call));
        const next: CallState = {
          request: state.request,
          scene: state.scene,
          texts: state.texts,
          response: response.id,
          output: response.output,
        };
        return dispatch.task_sleep(next, ids, constants.tool_type);
      }
      const subtitle = provider.text_join(response.output);
      if (subtitle === null) {
        throw new Error(i18n("agent.reply_empty", response.id));
      }
      const store = this.#store;
      const appended = store.turn_append(
        state.scene,
        constants.reply_role,
        response.output,
      );
      this.chain_keep(state, response.id, appended.n);
      const scene = scene_current(store);
      return dispatch.reply_make(state.request, {
        turn: appended.n,
        scene,
        subtitle,
      });
    }

    // Stores the reply that called the functions and their outputs, then asks.
    tool_handle(line: lines.Line): dispatch.Sleep {
      const state = line.state as CallState;
      const replies = line.replies as lines.Line[];
      const calls = provider.calls_find(state.output);
      const outputs = replies.map(
        (reply: lines.Line, index: number): provider.CallOutput => {
          const call_id = calls[index].call_id;
          const result = this.#clients.result_of(reply);
          return {
            type: constants.output_type,
            call_id,
            output: result_text(result, call_id),
          };
        },
      );
      const store = this.#store;
      const scene = state.scene;
      const appended = store.transaction_run(() => {
        const stored = store.turn_append(
          scene,
          constants.reply_role,
          state.output,
        );
        for (const output of outputs) {
          store.turn_append(scene, constants.output_role, [output]);
        }
        return stored;
      });
      this.chain_keep(state, state.response, appended.n);
      return this.request_submit(state.request, scene);
    }

    // Appends the player's message to the scene's log, and asks the model.
    turn_start(request: lines.Line, text: string): dispatch.Sleep {
      const store = this.#store;
      const scene = scene_current(store);
      if (!store.turn_prompted(scene)) {
        store.turn_prompt(scene, prompt_build(store));
      }
      const message: provider.InputMessage = {
        role: constants.user_role,
        content: text,
      };
      store.turn_append(scene, message.role, [message]);
      return this.request_submit(request, scene);
    }

    // Submits the model request and sleeps on it, chained when the log allows.
    request_submit(request: lines.Line, scene: lines.DocRef): dispatch.Sleep {
      const rows = this.#store.turn_list(scene);
      const texts = rows.map(row_text);
      const chain = this.chain_find(scene, texts);
      const kept = chain === undefined ? 0 : chain.texts.length;
      const input = rows.slice(kept).flatMap((row) => row.content);
      const info = this.#info;
      const body: provider.ModelRequest = {
        model: info.chat_model,
        input,
        tools: this.#debug()
          ? provider.tools_omitted
          : provider.tools_convert(this.#clients.tools_cached()),
        tool_choice: constants.tool_choice,
        prompt_cache_key: scene,
        include: [constants.include_reasoning],
      };
      if (chain !== undefined) {
        body.previous_response_id = chain.id;
      }
      const line = provider.model_request(
        info.base_url,
        provider.key_get(),
        body,
      );
      const id = this.#tasks.task_submit(line, this.#provider_owner);
      const state: TurnState = { request, scene, texts };
      return dispatch.task_sleep(state, [id], constants.model_type);
    }

    // The scene's chain when the log adds rows after all of it, else deleted.
    chain_find(scene: lines.DocRef, texts: string[]): SceneChain | undefined {
      const chain = this.#chains.get(scene);
      if (
        chain !== undefined &&
        texts.length > chain.texts.length &&
        prefix_holds(chain.texts, texts)
      ) {
        return chain;
      }
      this.#chains.delete(scene);
      return undefined;
    }

    // Chains the response when the log read back is the request's, then row n.
    chain_keep(state: TurnState, id: string, n: number): void {
      const rows = this.#store.turn_list(state.scene);
      const after = rows.at(state.texts.length);
      if (
        after !== undefined &&
        after.n === n &&
        prefix_holds(state.texts, rows.map(row_text))
      ) {
        const texts = [...state.texts, row_text(after)];
        this.#chains.set(state.scene, { id, texts });
        return;
      }
      this.#chains.delete(state.scene);
    }

    // Submits one function call, whose arguments must be a JSON object.
    call_submit(call: provider.FunctionCall): number {
      const name = call.name;
      const text = call.arguments;
      let args: unknown;
      try {
        args = jslb.json_decode(text);
      } catch (error) {
        throw utility.error_wrap(
          i18n("agent.arguments_invalid", call.call_id, name, text),
          error,
        );
      }
      if (typeof args !== "object" || args === null || Array.isArray(args)) {
        throw new Error(
          i18n("agent.arguments_invalid", call.call_id, name, text),
        );
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
    debug: () => boolean,
  ): void {
    const loop = new TurnLoop(
      store,
      clients,
      tasks,
      provider_owner,
      info,
      debug,
    );
    const version = constants.handler_version;
    register(constants.say_type, version, (line) => loop.say_handle(line));
    register(constants.click_type, version, (line) => loop.click_handle(line));
    register(constants.model_type, version, (line) => loop.model_handle(line));
    register(constants.tool_type, version, (line) => loop.tool_handle(line));
  }
}

Object.freeze(agent);
