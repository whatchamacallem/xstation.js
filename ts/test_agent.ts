// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the agent loop on a store over the sqlite3.wasm module and OPFS
// pool the test page sets as globals, a task queue in synchronous mode, the
// scripted provider and a double of the MCP clients whose tools answer at
// once: the castle turn, in which the player answers 1 and the analyst builds
// the castle's gatehouse scene, the turn after it, short turns and a click,
// the system prompt, the measurement over the soft limit, the request after
// the store compacted a scene at `turn_compact_turns`, failed tool calls that
// store no reply without its results, and every error the agent throws.

namespace test_agent {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The values of the settings, the seeds, the castle turn and the tests.
  const constants = Object.freeze({
    // A synthetic provider key, which every chat request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // The provider's address and models of a scripted run, empty.
    scripted_info: Object.freeze<lines.ProviderInfo>({
      base_url: "",
      chat_model: "",
      image_model: "",
    }),
    // The `overflow_bytes` of `settings.json`, 128 KiB.
    overflow_bytes: 131072,
    // The `turn_compact_turns` of `settings.json`, 64.
    compact_turns: 64,
    // A count chosen by its writer: a threshold one exchange reaches.
    compact_reached: 2,
    // A count chosen by its writer: a threshold one exchange stays under.
    compact_unreached: 3,
    // The owner whose port answers the provider's requests.
    provider_owner: "http" as const,
    // The owner whose port answers the tool calls in these tests.
    tools_owner: "server" as const,
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_agent/",
    // The hyperposition scene, on screen when the castle turn starts.
    scene: "/metaverse/hyperposition/1",
    // The arrival scene the castle turn writes and enters.
    arrival: "/castle_gatehouse/scene/arrival/1",
    // The analyst's system prompt, which each store of the tests holds.
    analyst:
      "You are a very bored British psychoanalyst. You hold the" +
      " hyperposition, a dark place of fog and a few inexplicable lights." +
      " Find the right universe for the player and act on requests without" +
      " judgement. Your scripts are the database administrator of every" +
      " universe you create: typed tables, indexes, views, no JSON columns" +
      " unless a document is what fits.",
    // The subtitle the castle turn ends with.
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The prompt of the image the castle turn makes.
    image_prompt:
      "A rain dark castle gatehouse at dusk seen from the far side of a" +
      " moat, one lantern lit, painted, wide still frame, no people",
    // The universe table, as the metaverse SQL file creates it.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    // The statements the bootstrap script runs in the castle turn.
    world_sql:
      "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL)" +
      " STRICT",
    world_insert: "INSERT INTO world VALUES (?, ?)",
    region_sql:
      "CREATE TABLE region (name TEXT PRIMARY KEY," +
      " tide INTEGER NOT NULL DEFAULT 0) STRICT",
    region_insert: "INSERT INTO region (name) VALUES (?)",
    universe_insert: "INSERT INTO universe VALUES (?, ?, ?, ?)",
    // The title the castle turn gives its universe.
    universe_title: "The castle",
    // The result texts of the castle turn's tool calls, in call order.
    bootstrap_result:
      '{"value":{"universe":"castle","world":"castle_world",' +
      '"region":"castle_gatehouse"},"lines":[]}',
    image_result:
      '{"key":"/_files/gatehouse/arrival.png","size":88,"sha256":' +
      '"90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0"}',
    scene_result: '{"ref":"/castle_gatehouse/scene/arrival/1"}',
    enter_result:
      '{"sha256":' +
      '"1e2806a1029564579de9739ef0014f0332c5a8026bca9373e473224a3b094d8b",' +
      '"seq":2}',
    render_result: "{}",
    // The replies of the test script beside the castle turn.
    nothing_reply: "Nothing happens.",
    moat_reply: "Still the moat.",
    // The reply of the answering provider in the test of a click.
    click_reply: "The lights flicker.",
    // The id of the answering provider's replies.
    answer_id: "chatcmpl-answer",
    // The arguments of the render calls of the error tests.
    render_arguments: '{"subtitle":"Fog."}',
    // The arguments of the image calls of the tests of failed calls.
    image_arguments: '{"prompt":"Fog.","key":"/_files/fog.png"}',
    // A prompt of the castle universe, for the tests of the system prompt.
    castle_prompt: "The castle is cold, and its keeper is patient.",
    // The line types the agent registers, in its order.
    agent_types: Object.freeze([
      "ai.say",
      "ai.click",
      "ai.model_reply",
      "ai.tool_reply",
    ]),
  });

  // An object of fields by name.
  type Fields = { [key: string]: unknown };

  // What a tool double does with its arguments, and the result it gives.
  type ToolAnswer = (args: Fields) => mcp.ToolResult;

  // The tool doubles by their full name.
  type ToolTable = { [name: string]: ToolAnswer };

  // A store, a synchronous queue and its ports, with the agent registered.
  interface Bench {
    store: substrate.Store;
    tasks: queue.TaskQueue;
    ui: PortDouble;
    provider_tap: PortTap;
    tools_tap: PortTap;
    forwarded: lines.Line[];
  }

  // How many roots the tests have made, so that each store has its own.
  let root_count = 0;

  // The handlers the running test's agent registered, by line type.
  const routed = new Map<string, dispatch.Handler>();

  // Whether dispatch's registry routes the agent's line types to `routed`.
  let router_installed = false;

  // Routes the agent's line types from dispatch's registry, once per page.
  function router_install(): void {
    if (router_installed) {
      return;
    }
    router_installed = true;
    for (const type of constants.agent_types) {
      dispatch.handler_register(type, 0, (line: lines.Line) => {
        const fn = routed.get(type);
        if (fn === undefined) {
          throw new Error(`No handler of the agent is routed for ${type}.`);
        }
        return fn(line);
      });
    }
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // The settings of `settings.json`, every key with its value.
  function settings_make(): settings.Settings {
    return {
      debug: true,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      line_max: 1048576,
      blob_max: 2147483391,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      db_soft_bytes: 1073741824,
      turn_compact_turns: 64,
      long_task_ms: 5,
      provider: {
        scripted: true,
        timeout_seconds: 120,
      },
    };
  }

  // The reader of a settings store that holds the settings given.
  function reader_from(value: settings.Settings): (id: string) => unknown {
    const store = new settings.ValueStore();
    store.value_set(value);
    return (id: string) => store.value_get(id);
  }

  // A call of the named tool with its arguments as JSON text.
  function call_make(
    id: string,
    name: string,
    text: string,
  ): provider.ToolCall {
    return { id, type: "function", function: { name, arguments: text } };
  }

  // The calls of the castle turn, each with its arguments as JSON text.
  function calls_recorded(): provider.ToolCall[] {
    return [
      call_make(
        "call_1",
        "browser.script_run",
        '{"name":"bootstrap","args":{"universe":"castle",' +
          '"title":"The castle","world":"castle_world",' +
          '"region":"castle_gatehouse"}}',
      ),
      call_make(
        "call_2",
        "browser.image_make",
        `{"prompt":"${constants.image_prompt}",` +
          '"key":"/_files/gatehouse/arrival.png"}',
      ),
      call_make(
        "call_3",
        "browser.doc_put",
        '{"db":"castle_gatehouse","id":"scene/arrival","body":' +
          '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png",' +
          `"subtitle":"${constants.subtitle}","image":{"$ref":1}}}`,
      ),
      call_make(
        "call_4",
        "browser.kv_put",
        '{"ref":"/castle_world/scene",' +
          '"text":"/castle_gatehouse/scene/arrival/1"}',
      ),
      call_make(
        "call_5",
        "browser.render",
        '{"image":"/_files/gatehouse/arrival.png",' +
          `"subtitle":"${constants.subtitle}"}`,
      ),
    ];
  }

  // A tool of the properties given, as the MCP clients list it.
  function tool_make(
    name: string,
    description: string,
    properties: Fields,
    required: string[],
  ): mcp.Tool {
    return {
      name,
      description,
      inputSchema: { type: "object", properties, required },
    };
  }

  // The castle turn's tools as the MCP clients list them, in its order.
  function tools_listed(): mcp.Tool[] {
    const text_type = { type: "string" };
    const object_type = { type: "object" };
    return [
      tool_make(
        "browser.kv_put",
        "Write text under a Key-Value-Ref, /$db/$key. A script is the row" +
          " /_files/script/<name>.js.",
        { ref: text_type, text: text_type },
        ["ref", "text"],
      ),
      tool_make(
        "browser.doc_put",
        "Write a new version of document $id in database $db and move its" +
          " head. Returns the new Document-Ref.",
        { db: text_type, id: text_type, body: object_type },
        ["db", "id", "body"],
      ),
      tool_make(
        "browser.script_run",
        "Run the script /_files/script/<name>.js with args as a task in this" +
          " worker. Returns its value or exception and the verbose lines it" +
          " wrote.",
        { name: text_type, args: object_type },
        ["name", "args"],
      ),
      tool_make(
        "browser.image_make",
        "Generate an image from a prompt and keep it under /_files/<key>." +
          " Returns the key, size and sha256.",
        { prompt: text_type, key: text_type },
        ["prompt", "key"],
      ),
      tool_make(
        "browser.render",
        "Show an image by its Key-Value-Ref with a subtitle. No image means" +
          " black.",
        { image: text_type, subtitle: text_type },
        ["subtitle"],
      ),
    ];
  }

  // The function tools the castle turn's requests list for those tools.
  function functions_recorded(): provider.FunctionTool[] {
    return tools_listed().map((tool: mcp.Tool): provider.FunctionTool => ({
      type: "function",
      function: {
        name: tool.name,
        description: tool.description,
        parameters: tool.inputSchema,
      },
    }));
  }

  // The system message of the text.
  function system_said(text: string): provider.ChatMessage {
    return { role: "system", content: text };
  }

  // The user message of the text.
  function user_said(text: string): provider.ChatMessage {
    return { role: "user", content: text };
  }

  // The assistant message that ends a turn with the text.
  function assistant_said(text: string): provider.ChatMessage {
    return { role: "assistant", content: text };
  }

  // The assistant message that makes the calls.
  function assistant_calls(calls: provider.ToolCall[]): provider.ChatMessage {
    return { role: "assistant", content: null, tool_calls: calls };
  }

  // The tool message of a call's result.
  function tool_said(
    call: provider.ToolCall,
    text: string,
  ): provider.ChatMessage {
    return { role: "tool", tool_call_id: call.id, content: text };
  }

  // The rounds of the castle turn: the calls, then their results.
  function rounds_recorded(): provider.ChatMessage[][] {
    const [bootstrap, image, scene, enter, render] = calls_recorded();
    return [
      [
        assistant_calls([bootstrap]),
        tool_said(bootstrap, constants.bootstrap_result),
      ],
      [assistant_calls([image]), tool_said(image, constants.image_result)],
      [
        assistant_calls([scene, enter, render]),
        tool_said(scene, constants.scene_result),
        tool_said(enter, constants.enter_result),
        tool_said(render, constants.render_result),
      ],
    ];
  }

  // The messages of each chat request of the castle turn, in order.
  function messages_recorded(): provider.ChatMessage[][] {
    const start = [system_said(constants.analyst), user_said("1")];
    const [first, second, third] = rounds_recorded();
    return [
      start,
      [...start, ...first],
      [...start, ...first, ...second],
      [...start, ...first, ...second, ...third],
    ];
  }

  // The messages the castle turn stores as turns of its scene, in order.
  function contents_recorded(): provider.ChatMessage[] {
    return [
      user_said("1"),
      ...rounds_recorded().flat(),
      assistant_said(constants.subtitle),
    ];
  }

  // The script of the castle turn, with the replies the tests add.
  function script_recorded(): provider_script.Script {
    const [bootstrap, image, scene, enter, render] = calls_recorded();
    return {
      start: "hyperposition",
      nodes: {
        hyperposition: {
          replies: {
            "1": { content: null, tool_calls: [bootstrap], next: "castle" },
            "2": { content: constants.nothing_reply, next: "hyperposition" },
          },
        },
        castle: {
          replies: {},
          after_tools: { content: null, tool_calls: [image], next: "imaged" },
        },
        imaged: {
          replies: {},
          after_tools: {
            content: null,
            tool_calls: [scene, enter, render],
            next: "entered",
          },
        },
        entered: {
          replies: {},
          after_tools: { content: constants.subtitle, next: "gatehouse" },
        },
        gatehouse: {
          replies: {
            "0": { content: constants.moat_reply, next: "gatehouse" },
          },
        },
      },
    };
  }

  // A script whose reply to 1 leads to the node `after`, which is given.
  function script_one(
    reply: provider_script.ScriptReply,
    after: provider_script.ScriptNode,
  ): provider_script.Script {
    return {
      start: "hyperposition",
      nodes: { hyperposition: { replies: { "1": reply } }, after },
    };
  }

  // A tool result of one text part.
  function text_result(text: string): mcp.ToolResult {
    return { content: [{ type: "text", text }] };
  }

  // Adds a row of the universe table for the universe and world given.
  function row_add(store: substrate.Store, name: string, world: string): void {
    const params = [name, constants.universe_title, "player", world];
    store.sql_run("metaverse", [{ sql: constants.universe_insert, params }]);
  }

  // Creates a universe's database and its row for the world given.
  function universe_add(
    store: substrate.Store,
    name: string,
    world: string,
  ): void {
    store.db_create(name);
    row_add(store, name, world);
  }

  // Makes the world given the current one.
  function world_set(store: substrate.Store, world: string): void {
    store.kv_put("/metaverse/world", utility.utf8_encode(world));
  }

  // A prompt document of the type given that holds the text given.
  function prompt_doc(type: string, text: unknown): lines.Document {
    return { 0: { t: type }, text };
  }

  // The store changes the seeded bootstrap script makes in the castle turn.
  function bootstrap_run(store: substrate.Store, args: Fields): void {
    const universe = args.universe as string;
    const title = args.title as string;
    const world = args.world as string;
    const region = args.region as string;
    store.db_create(universe);
    store.sql_run(universe, [
      { sql: constants.world_sql, params: [] },
      { sql: constants.world_insert, params: [world, title] },
    ]);
    store.db_create(world);
    store.sql_run(world, [
      { sql: constants.region_sql, params: [] },
      { sql: constants.region_insert, params: [region] },
    ]);
    store.db_create(region);
    const params = [universe, title, "player", world];
    store.sql_run("metaverse", [{ sql: constants.universe_insert, params }]);
    world_set(store, world);
  }

  // The tools of the castle turn: what each changes and the text it gives.
  function tools_recorded(store: substrate.Store): ToolTable {
    return {
      "browser.script_run": (args: Fields) => {
        bootstrap_run(store, args.args as Fields);
        return text_result(constants.bootstrap_result);
      },
      "browser.image_make": () => text_result(constants.image_result),
      "browser.doc_put": (args: Fields) => {
        const body = args.body as lines.Document;
        const put = store.doc_put(args.db as string, args.id as string, body);
        return text_result(utility.json_text({ ref: put.ref }));
      },
      "browser.kv_put": (args: Fields) => {
        const data = utility.utf8_encode(args.text as string);
        const put = store.kv_put(args.ref as string, data);
        const result = { sha256: put.row.sha256, seq: put.seq };
        return text_result(utility.json_text(result));
      },
      "browser.render": () => text_result(constants.render_result),
    };
  }

  // The `mcp` reply to a `tools/call` line, with its tool double's result.
  function tool_reply(line: lines.Line, table: ToolTable): lines.Line {
    const payload = jslb.payload_of(line);
    const params = payload.params as { name: string; arguments: Fields };
    if (!Object.hasOwn(table, params.name)) {
      throw new Error(`The tool doubles have no tool ${params.name}.`);
    }
    const id = jslb.field_get(line[0], "id") as number;
    return jslb.line_make(jslb.header_make("mcp", { reply: id }), [], {
      jsonrpc: "2.0",
      id: payload.id,
      result: table[params.name](params.arguments),
    });
  }

  // The reply of a provider that answers a chat request with the message.
  function chat_answer(
    line: lines.Line,
    message: provider.ChatMessage,
  ): lines.Line {
    const id = jslb.field_get(line[0], "id") as number;
    const header = jslb.header_make("http.request", { reply: id });
    return jslb.line_make(header, [], {
      status: 200,
      headers: { "content-type": "application/json" },
      json: {
        id: constants.answer_id,
        model: constants.info.chat_model,
        choices: [{ index: 0, message, finish_reason: "stop" }],
      },
    });
  }

  // The payload of the chat request the provider door makes for messages.
  function request_expected(messages: provider.ChatMessage[]): Fields {
    const { base_url, chat_model } = constants.info;
    const line = provider.chat_request(base_url, constants.key, {
      model: chat_model,
      messages,
      tools: functions_recorded(),
      tool_choice: "auto",
    });
    return jslb.payload_of(line);
  }

  // Hands the UI's request to the queue: its type, header, payload.
  function request_send(
    bench: Bench,
    type: string,
    header: { id: number; full?: boolean },
    payload: Fields,
  ): void {
    const line = jslb.line_make(jslb.header_make(type, header), [], payload);
    bench.ui.line_send(line);
  }

  // Hands the player's text to the queue as `ai.say` with the id.
  function say_send(bench: Bench, id: number, text: string): void {
    request_send(bench, "ai.say", { id }, { text });
  }

  // The bodies of the chat requests the agent submitted, in order.
  function requests_of(bench: Bench): provider.ChatRequest[] {
    return bench.provider_tap.posted.map(
      (line: lines.Line) => line.json as provider.ChatRequest,
    );
  }

  // The number of system messages of each chat request, in order.
  function systems_counted(bench: Bench): number[] {
    return requests_of(bench).map(
      (request: provider.ChatRequest) =>
        request.messages.filter((message) => message.role === "system").length,
    );
  }

  // The payloads of the `turn.append` lines the store forwarded, in order.
  function appends_of(bench: Bench): Fields[] {
    return bench.forwarded
      .filter((line) => jslb.field_get(line[0], "type") === "turn.append")
      .map((line) => jslb.payload_of(line));
  }

  // Tool doubles: a render that answers, an image the agent refuses.
  function tools_failing(): ToolTable {
    return {
      "browser.render": () => text_result(constants.render_result),
      "browser.image_make": () => ({
        content: [{ type: "image", data: "", mimeType: "image/png" }],
      }),
    };
  }

  // A port double: it keeps what the queue posts and hands it lines.
  class PortDouble implements queue.Port {
    // The lines the queue posted, in order.
    readonly posted: lines.Line[] = [];
    // The receiver, which is the queue.
    #receiver: ((line: lines.Line) => void) | undefined = undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.#receiver = fn;
    }

    // Hands a line to the queue as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.#receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
    }
  }

  // A port that keeps the lines both ways and passes them through another.
  class PortTap implements queue.Port {
    // The lines the queue posted, in order.
    readonly posted: lines.Line[] = [];
    // The lines the port it wraps answered, in order.
    readonly received: lines.Line[] = [];
    // The port it wraps.
    readonly #inner: queue.Port;

    // Takes the port it wraps.
    constructor(inner: queue.Port) {
      this.#inner = inner;
    }

    // Keeps a posted line and posts it on the port it wraps.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      this.posted.push(line);
      this.#inner.line_post(line, transfer);
    }

    // Keeps each line the wrapped port delivers and hands it on.
    line_receive(fn: (line: lines.Line) => void): void {
      this.#inner.line_receive((line: lines.Line) => {
        this.received.push(line);
        fn(line);
      });
    }
  }

  // A port that answers each line at once with the line its function makes.
  class AnswerPort implements queue.Port {
    // The function that makes the answer to a line.
    readonly #answer: (line: lines.Line) => lines.Line;
    // The receiver, which is the queue.
    #receiver: ((line: lines.Line) => void) | undefined = undefined;

    // Takes the function that makes the answer to a line.
    constructor(answer: (line: lines.Line) => lines.Line) {
      this.#answer = answer;
    }

    // Answers the line through the receiver before it returns.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const receiver = this.#receiver;
      if (receiver === undefined) {
        throw new Error("The answering port has no receiver.");
      }
      receiver(this.#answer(line));
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.#receiver = fn;
    }
  }

  // A double of the MCP clients: it lists tools and calls them over a port.
  class ClientsDouble extends mcp.ClientSet {
    // The task manager the calls are submitted to.
    readonly #tasks: queue.TaskQueue;
    // The tools it lists.
    readonly #tools: mcp.Tool[];
    // The number of calls made, the last id of `JSON-RPC` given.
    #count = 0;

    // Takes the task manager and the tools it lists.
    constructor(tasks: queue.TaskQueue, tools: mcp.Tool[]) {
      super();
      this.#tasks = tasks;
      this.#tools = tools;
    }

    // The tools as listed.
    tools_cached(): mcp.Tool[] {
      return this.#tools;
    }

    // Submits a `tools/call` line to the owner of the tool doubles' port.
    tool_call(name: string, args: { [key: string]: unknown }): number {
      this.#count += 1;
      const line = jslb.line_make(jslb.header_make("mcp"), [], {
        jsonrpc: "2.0",
        id: this.#count,
        method: "tools/call",
        params: { name, arguments: args },
      });
      return this.#tasks.task_submit(line, constants.tools_owner);
    }

    // The result a reply of the tool doubles carries.
    result_of(reply: lines.Line): mcp.ToolResult {
      return jslb.payload_of(reply).result as mcp.ToolResult;
    }
  }

  // An agent test: the module and pool read in `setUp`, its roots removed.
  class AgentCase extends unittest.TestCase {
    // The module the test page provides, read in `setUp`.
    #sqlite: substrate.SqliteModule | undefined = undefined;
    // The pool the test page provides, read in `setUp`.
    #pool: substrate.SqlitePool | undefined = undefined;
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made.
    readonly #stores: substrate.Store[] = [];

    // Reads the test page's globals, routes the agent's types, sets the key.
    setUp(): void {
      this.#sqlite = test_sqlite3;
      this.#pool = test_pool;
      router_install();
      routed.clear();
      provider.key_set(constants.key);
    }

    // Closes every database of the stores and removes the roots' files.
    tearDown(): void {
      for (const store of this.#stores) {
        for (const name of store.db_list()) {
          store.db_close(name);
        }
      }
      const pool = this.#pool as substrate.SqlitePool;
      for (const root of this.#roots) {
        for (const file of pool.getFileNames()) {
          if (file.startsWith(`${root}/`)) {
            pool.unlink(file);
          }
        }
      }
    }

    // A store on a new root whose metaverse holds what the agent reads.
    store_make(
      forwarded: lines.Line[],
      prompt: boolean,
      compact_turns: number = constants.compact_turns,
    ): substrate.Store {
      root_count += 1;
      const root = constants.root_prefix + String(root_count);
      this.#roots.push(root);
      const store = new substrate.Store(
        this.#sqlite as substrate.SqliteModule,
        this.#pool as substrate.SqlitePool,
        new substrate.CacheFiles([]),
        root,
        constants.overflow_bytes,
        compact_turns,
      );
      this.#stores.push(store);
      store.forward_set((line: lines.Line) => {
        forwarded.push(line);
      }, false);
      store.db_create("metaverse");
      const statement = { sql: constants.universe_sql, params: [] };
      store.sql_run("metaverse", [statement]);
      if (prompt) {
        const doc = prompt_doc("prompt", constants.analyst);
        store.doc_put("metaverse", "prompt", doc);
      }
      store.kv_put("/metaverse/player", utility.utf8_encode("player"));
      world_set(store, "metaverse");
      store.kv_put("/metaverse/scene", utility.utf8_encode(constants.scene));
      forwarded.splice(0);
      return store;
    }

    // A bench on a new store: a queue, its ports and the agent registered.
    bench_make(
      provider_port: queue.Port,
      value: settings.Settings,
      tools_make: (store: substrate.Store) => ToolTable,
      info: lines.ProviderInfo,
    ): Bench {
      const forwarded: lines.Line[] = [];
      const store = this.store_make(forwarded, true, value.turn_compact_turns);
      const tasks = new queue.TaskQueue("ai", { "ai.": "ai" }, true);
      const ui = new PortDouble();
      const provider_tap = new PortTap(provider_port);
      const table = tools_make(store);
      const tools_tap = new PortTap(
        new AnswerPort((line: lines.Line) => tool_reply(line, table)),
      );
      tasks.port_add("ui", ui);
      tasks.port_add(constants.provider_owner, provider_tap);
      tasks.port_add(constants.tools_owner, tools_tap);
      agent.handlers_register(
        store,
        new ClientsDouble(tasks, tools_listed()),
        tasks,
        constants.provider_owner,
        info,
        reader_from(value),
        (type: string, _version: number, fn: dispatch.Handler) => {
          routed.set(type, fn);
        },
      );
      return { store, tasks, ui, provider_tap, tools_tap, forwarded };
    }

    // A bench whose tool doubles are those of the castle turn.
    bench_recorded(
      provider_port: queue.Port,
      value: settings.Settings,
    ): Bench {
      return this.bench_make(
        provider_port,
        value,
        tools_recorded,
        constants.info,
      );
    }
  }

  // The castle turn: the player answers 1 and the analyst builds a scene.
  export class TestTurnRecorded extends AgentCase {
    // The four chat requests are the castle turn's, made by the door.
    test_requests_recorded(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      say_send(bench, 1, "1");
      const expected = messages_recorded();
      const posted = bench.provider_tap.posted;
      this.assertEqual(posted.length, expected.length);
      for (let index = 0; index < posted.length; index += 1) {
        const line = posted[index];
        this.assertEqual(jslb.field_get(line[0], "type"), "http.request");
        this.assertEqual(
          jslb.payload_of(line),
          request_expected(expected[index]),
        );
      }
    }

    // Each call goes to the clients by its dotted name with its arguments.
    test_calls_recorded(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      say_send(bench, 1, "1");
      const params = bench.tools_tap.posted.map(
        (line: lines.Line) => jslb.payload_of(line).params,
      );
      const expected = calls_recorded().map((call: provider.ToolCall) => ({
        name: call.function.name,
        arguments: JSON.parse(call.function.arguments) as unknown,
      }));
      this.assertEqual(params, expected);
    }

    // Every message of the turn is a turn of the scene, forwarded in order.
    test_turns_stored(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      const since = bench.store.seq_get("metaverse");
      say_send(bench, 1, "1");
      const expected = contents_recorded();
      const appends = appends_of(bench);
      this.assertEqual(
        appends.map((payload) => payload.content),
        expected,
      );
      this.assertEqual(
        appends.map((payload) => payload.role),
        expected.map((message) => message.role),
      );
      this.assertEqual(
        appends.map((payload) => payload.scene),
        expected.map(() => constants.scene),
      );
      this.assertEqual(appends[0].since, since);
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        expected,
      );
    }

    // The turn ends with the reply to `ai.say`: the new scene, the subtitle.
    test_reply_recorded(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      say_send(bench, 1, "1");
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(bench.ui.posted.length, 1);
      const reply = bench.ui.posted[0];
      this.assertEqual(reply[0], { t: "ai.say", r: 1 });
      this.assertEqual(jslb.payload_of(reply), {
        turn: rows[rows.length - 1].n,
        scene: constants.arrival,
        subtitle: constants.subtitle,
      });
      this.assertEqual(script.node(), "gatehouse");
      this.assertEqual(bench.tasks.depth(), 0);
    }
  }

  // The turn after the castle turn, in the scene that turn entered.
  export class TestTurnNext extends AgentCase {
    // The next turn is a new conversation, that of the arrival scene.
    test_scene_new(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      say_send(bench, 1, "1");
      say_send(bench, 2, "0");
      const requests = requests_of(bench);
      this.assertEqual(requests[requests.length - 1].messages, [
        system_said(constants.analyst),
        user_said("0"),
      ]);
      const rows = bench.store.turn_list(constants.arrival);
      this.assertEqual(
        rows.map((row) => row.content),
        [user_said("0"), assistant_said(constants.moat_reply)],
      );
      const reply = bench.ui.posted[1];
      this.assertEqual(reply[0], { t: "ai.say", r: 2 });
      this.assertEqual(jslb.payload_of(reply), {
        turn: rows[1].n,
        scene: constants.arrival,
        subtitle: constants.moat_reply,
      });
    }

    // The universe's prompt follows the analyst's once the scripts made one.
    test_universe_prompt(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      say_send(bench, 1, "1");
      const doc = prompt_doc("prompt", constants.castle_prompt);
      bench.store.doc_put("castle", "prompt", doc);
      say_send(bench, 2, "0");
      const requests = requests_of(bench);
      this.assertEqual(requests[requests.length - 1].messages, [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
        user_said("0"),
      ]);
    }
  }

  // Turns with no tool calls, a click, and a result of several parts.
  export class TestTurnShort extends AgentCase {
    // A reply with no tool calls ends the turn, in the request's name form.
    test_turn_short(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, settings_make());
      request_send(bench, "ai.say", { id: 7, full: true }, { text: "2" });
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        [user_said("2"), assistant_said(constants.nothing_reply)],
      );
      const reply = bench.ui.posted[0];
      this.assertEqual(reply[0], { type: "ai.say", reply: 7 });
      this.assertEqual(jslb.payload_of(reply), {
        turn: rows[1].n,
        scene: constants.scene,
        subtitle: constants.nothing_reply,
      });
    }

    // A click is told to the model as text, and the reply ends the turn.
    test_click_turn(): void {
      const message = assistant_said(constants.click_reply);
      const port = new AnswerPort((line: lines.Line) =>
        chat_answer(line, message),
      );
      const bench = this.bench_recorded(port, settings_make());
      request_send(bench, "ai.click", { id: 1 }, { x: 10, y: 20 });
      const said = user_said(i18n("agent.click_text", 10, 20));
      this.assertEqual(requests_of(bench)[0].messages, [
        system_said(constants.analyst),
        said,
      ]);
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        [said, message],
      );
      const reply = bench.ui.posted[0];
      this.assertEqual(reply[0], { t: "ai.click", r: 1 });
      this.assertEqual(jslb.payload_of(reply), {
        turn: rows[1].n,
        scene: constants.scene,
        subtitle: constants.click_reply,
      });
    }

    // The text parts of one tool result are joined by a line feed.
    test_texts_joined(): void {
      const call = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const script = script_one(
        { content: null, tool_calls: [call], next: "after" },
        {
          replies: {},
          after_tools: { content: constants.nothing_reply, next: "after" },
        },
      );
      const tools = (): ToolTable => ({
        "browser.render": () => ({
          content: [
            { type: "text", text: "first" },
            { type: "text", text: "second" },
          ],
        }),
      });
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_make(
        port,
        settings_make(),
        tools,
        constants.info,
      );
      say_send(bench, 1, "1");
      const messages = requests_of(bench)[1].messages;
      this.assertEqual(
        messages[messages.length - 1],
        tool_said(call, "first\nsecond"),
      );
      const reply = bench.ui.posted[0];
      this.assertEqual(
        jslb.payload_of(reply).subtitle,
        constants.nothing_reply,
      );
    }

    // With a scripted run's empty information the request names no model.
    test_info_scripted(): void {
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_make(
        script,
        settings_make(),
        tools_recorded,
        constants.scripted_info,
      );
      say_send(bench, 1, "2");
      const posted = bench.provider_tap.posted;
      this.assertEqual(posted.length, 1);
      this.assertEqual(posted[0].url, "/chat/completions");
      this.assertEqual(requests_of(bench)[0].model, "");
      const answer = provider.chat_response(bench.provider_tap.received[0]);
      this.assertEqual(answer.model, "");
      this.assertEqual(
        jslb.payload_of(bench.ui.posted[0]).subtitle,
        constants.nothing_reply,
      );
    }
  }

  // The measurement of the open databases against `db_soft_bytes`.
  export class TestSoftLimit extends AgentCase {
    // Over the limit, the next request carries it after the system prompt.
    test_soft_over(): void {
      const value = settings_make();
      value.db_soft_bytes = 0;
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, value);
      say_send(bench, 1, "2");
      const stats = bench.store.db_stats(0);
      this.assertTrue(stats.over);
      say_send(bench, 2, "2");
      const requests = requests_of(bench);
      this.assertEqual(requests[0].messages, [
        system_said(constants.analyst),
        user_said("2"),
      ]);
      this.assertEqual(requests[1].messages, [
        system_said(constants.analyst),
        system_said(utility.json_text(stats)),
        user_said("2"),
        assistant_said(constants.nothing_reply),
        user_said("2"),
      ]);
    }

    // Only the first request after the turn carries it, not the later ones.
    test_soft_once(): void {
      const value = settings_make();
      value.db_soft_bytes = 0;
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, value);
      say_send(bench, 1, "2");
      say_send(bench, 2, "1");
      this.assertEqual(systems_counted(bench), [1, 2, 1, 1, 1]);
    }

    // Under the limit of `settings.json`, no request carries a measurement.
    test_soft_under(): void {
      const value = settings_make();
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, value);
      say_send(bench, 1, "2");
      say_send(bench, 2, "2");
      this.assertFalse(bench.store.db_stats(value.db_soft_bytes).over);
      this.assertEqual(systems_counted(bench), [1, 1]);
    }
  }

  // The request after the store compacted a scene at `turn_compact_turns`.
  export class TestCompacted extends AgentCase {
    // At the threshold the player's next message follows one summary turn.
    test_request_compacted(): void {
      const value = settings_make();
      value.turn_compact_turns = constants.compact_reached;
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, value);
      say_send(bench, 1, "2");
      bench.forwarded.splice(0);
      say_send(bench, 2, "2");
      const summary = i18n("substrate.turns_compacted", 2, 2);
      this.assertEqual(requests_of(bench)[1].messages, [
        system_said(constants.analyst),
        system_said(summary),
        user_said("2"),
      ]);
      this.assertEqual(
        bench.forwarded.map((line) => jslb.field_get(line[0], "type")),
        ["turn.compact", "turn.append", "turn.append"],
      );
    }

    // Below the threshold the next request carries the whole conversation.
    test_request_whole(): void {
      const value = settings_make();
      value.turn_compact_turns = constants.compact_unreached;
      const script = new provider_script.ScriptPort(script_recorded());
      const bench = this.bench_recorded(script, value);
      say_send(bench, 1, "2");
      say_send(bench, 2, "2");
      this.assertEqual(requests_of(bench)[1].messages, [
        system_said(constants.analyst),
        user_said("2"),
        assistant_said(constants.nothing_reply),
        user_said("2"),
      ]);
    }
  }

  // A failed tool call leaves no stored reply that calls tools unanswered.
  export class TestFailure extends AgentCase {
    // A failed result stores neither the reply nor the results of its round.
    test_result_failed(): void {
      const calls = [
        call_make("call_1", "browser.render", constants.render_arguments),
        call_make("call_2", "browser.image_make", constants.image_arguments),
      ];
      const script = script_one(
        { content: null, tool_calls: calls, next: "after" },
        { replies: {} },
      );
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_make(
        port,
        settings_make(),
        tools_failing,
        constants.info,
      );
      const error = thrown_get(() => say_send(bench, 1, "1"));
      this.assertEqual(
        error.message,
        i18n("agent.content_unsupported", "call_2", "image"),
      );
      this.assertEqual(bench.tools_tap.posted.length, 2);
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        [user_said("1")],
      );
      this.assertEqual(
        appends_of(bench).map((payload) => payload.content),
        [user_said("1")],
      );
    }

    // A call that cannot be made leaves the reply that names it unstored.
    test_call_unmade(): void {
      const call = call_make("call_1", "browser.render", "{");
      const script = script_one(
        { content: null, tool_calls: [call], next: "after" },
        { replies: {} },
      );
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_recorded(port, settings_make());
      const error = thrown_get(() => say_send(bench, 1, "1"));
      this.assertEqual(
        error.message,
        i18n("agent.arguments_invalid", "call_1", "browser.render", "{"),
      );
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        [user_said("1")],
      );
      this.assertEqual(
        appends_of(bench).map((payload) => payload.content),
        [user_said("1")],
      );
    }

    // An answered round stays stored with its results; the failed one not.
    test_round_answered(): void {
      const render = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const image = call_make(
        "call_2",
        "browser.image_make",
        constants.image_arguments,
      );
      const script = script_one(
        { content: null, tool_calls: [render], next: "after" },
        {
          replies: {},
          after_tools: { content: null, tool_calls: [image], next: "after" },
        },
      );
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_make(
        port,
        settings_make(),
        tools_failing,
        constants.info,
      );
      const error = thrown_get(() => say_send(bench, 1, "1"));
      this.assertEqual(
        error.message,
        i18n("agent.content_unsupported", "call_2", "image"),
      );
      const expected = [
        user_said("1"),
        assistant_calls([render]),
        tool_said(render, constants.render_result),
      ];
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        expected,
      );
      this.assertEqual(
        appends_of(bench).map((payload) => payload.content),
        expected,
      );
    }

    // The reply that calls a tool is stored with its result, after it ran.
    test_round_stored(): void {
      const render = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const script = script_one(
        { content: null, tool_calls: [render], next: "after" },
        {
          replies: {},
          after_tools: { content: constants.nothing_reply, next: "after" },
        },
      );
      const seen: number[] = [];
      const tools = (store: substrate.Store): ToolTable => ({
        "browser.render": () => {
          seen.push(store.turn_list(constants.scene).length);
          return text_result(constants.render_result);
        },
      });
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_make(
        port,
        settings_make(),
        tools,
        constants.info,
      );
      const since = bench.store.seq_get("metaverse");
      say_send(bench, 1, "1");
      this.assertEqual(seen, [1]);
      const appends = appends_of(bench);
      this.assertEqual(
        appends.map((payload) => payload.since),
        [since, since + 1, since + 2, since + 3],
      );
      this.assertEqual(
        appends.map((payload) => payload.content),
        [
          user_said("1"),
          assistant_calls([render]),
          tool_said(render, constants.render_result),
          assistant_said(constants.nothing_reply),
        ],
      );
    }
  }

  // The system prompt `prompt_build` makes.
  export class TestPrompt extends AgentCase {
    // In the hyperposition the system prompt is the analyst's alone.
    test_prompt_analyst(): void {
      const store = this.store_make([], true);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
      ]);
    }

    // The prompt of the universe of the current world follows the analyst's.
    test_prompt_universe(): void {
      const store = this.store_make([], true);
      universe_add(store, "castle", "castle_world");
      world_set(store, "castle_world");
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store.doc_put("castle", "prompt", doc);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A universe without a prompt adds none, nor does another world's one.
    test_prompt_absent(): void {
      const store = this.store_make([], true);
      universe_add(store, "castle", "castle_world");
      universe_add(store, "keep", "keep_world");
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store.doc_put("keep", "prompt", doc);
      world_set(store, "castle_world");
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
      ]);
    }

    // The head of the universe's prompt is read, not an older version.
    test_prompt_head(): void {
      const store = this.store_make([], true);
      universe_add(store, "castle", "castle_world");
      world_set(store, "castle_world");
      store.doc_put("castle", "prompt", prompt_doc("prompt", "An old one."));
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store.doc_put("castle", "prompt", doc);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A prompt text that is a reference string is read back as that text.
    test_prompt_reference(): void {
      const store = this.store_make([], true);
      universe_add(store, "castle", "castle_world");
      world_set(store, "castle_world");
      const lore = "/castle/lore";
      const doc = substrate.doc_encode({ 0: { t: "prompt" }, text: lore });
      store.doc_put("castle", "prompt", doc);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(lore),
      ]);
    }
  }

  // Every error the agent throws, compared with its message.
  export class TestErrors extends AgentCase {
    // Arguments that are not JSON end the turn, the parse error as cause.
    test_arguments_unparsed(): void {
      const text = "{";
      const call = call_make("call_1", "browser.render", text);
      const script = script_one(
        { content: null, tool_calls: [call], next: "after" },
        { replies: {} },
      );
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_recorded(port, settings_make());
      const error = thrown_get(() => say_send(bench, 1, "1"));
      this.assertEqual(
        error.message,
        i18n("agent.arguments_invalid", "call_1", "browser.render", text),
      );
      this.assertTrue(error.cause instanceof SyntaxError);
      this.assertEqual(bench.tools_tap.posted.length, 0);
    }

    // Arguments that are JSON but not an object end the turn.
    test_arguments_invalid(): void {
      for (const text of ["[]", "null", "5", '"Fog."']) {
        const call = call_make("call_1", "browser.render", text);
        const script = script_one(
          { content: null, tool_calls: [call], next: "after" },
          { replies: {} },
        );
        const port = new provider_script.ScriptPort(script);
        const bench = this.bench_recorded(port, settings_make());
        const error = thrown_get(() => say_send(bench, 1, "1"));
        this.assertEqual(
          error.message,
          i18n("agent.arguments_invalid", "call_1", "browser.render", text),
        );
      }
    }

    // A reply with neither tool calls nor content ends the turn.
    test_reply_empty(): void {
      const script = script_one(
        { content: null, next: "after" },
        { replies: {} },
      );
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_recorded(port, settings_make());
      const error = thrown_get(() => say_send(bench, 1, "1"));
      const answer = provider.chat_response(bench.provider_tap.received[0]);
      this.assertEqual(error.message, i18n("agent.reply_empty", answer.id));
      this.assertEqual(bench.ui.posted.length, 0);
      const rows = bench.store.turn_list(constants.scene);
      this.assertEqual(
        rows.map((row) => row.content),
        [user_said("1")],
      );
    }

    // A tool result holding an image ends the turn.
    test_content_unsupported(): void {
      const call = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const script = script_one(
        { content: null, tool_calls: [call], next: "after" },
        { replies: {} },
      );
      const tools = (): ToolTable => ({
        "browser.render": () => ({
          content: [{ type: "image", data: "", mimeType: "image/png" }],
        }),
      });
      const port = new provider_script.ScriptPort(script);
      const bench = this.bench_make(
        port,
        settings_make(),
        tools,
        constants.info,
      );
      const error = thrown_get(() => say_send(bench, 1, "1"));
      this.assertEqual(
        error.message,
        i18n("agent.content_unsupported", "call_1", "image"),
      );
    }

    // A prompt of another type, or whose text is not text, is refused.
    test_prompt_invalid(): void {
      const store = this.store_make([], true);
      universe_add(store, "castle", "castle_world");
      world_set(store, "castle_world");
      const note = prompt_doc("note", constants.castle_prompt);
      const typed = store.doc_put("castle", "prompt", note).ref;
      const first = thrown_get(() => agent.prompt_build(store));
      this.assertEqual(first.message, i18n("agent.prompt_invalid", typed));
      const number = prompt_doc("prompt", 5);
      const untexted = store.doc_put("metaverse", "prompt", number).ref;
      const second = thrown_get(() => agent.prompt_build(store));
      this.assertEqual(second.message, i18n("agent.prompt_invalid", untexted));
    }

    // Two universes of the current world make the universe prompt ambiguous.
    test_universe_ambiguous(): void {
      const store = this.store_make([], true);
      row_add(store, "castle", "castle_world");
      row_add(store, "keep", "castle_world");
      world_set(store, "castle_world");
      const error = thrown_get(() => agent.prompt_build(store));
      this.assertEqual(
        error.message,
        i18n("agent.universe_ambiguous", 2, "castle_world"),
      );
    }

    // Without the analyst's prompt document there is no system prompt.
    test_analyst_missing(): void {
      const store = this.store_make([], false);
      const error = thrown_get(() => agent.prompt_build(store));
      this.assertEqual(
        error.message,
        i18n("substrate.id_missing", "prompt", "metaverse"),
      );
    }

    // An `error` line in answer to the chat request is a fault, not a reply.
    test_error_line(): void {
      const failure = new Error("Unauthorized");
      const port = new AnswerPort((line: lines.Line) =>
        dispatch.error_make(line, failure),
      );
      const bench = this.bench_recorded(port, settings_make());
      const error = thrown_get(() => say_send(bench, 1, "2"));
      this.assertEqual(
        error.message,
        i18n(
          "queue.error_line",
          "ai",
          constants.provider_owner,
          failure.message,
          failure.stack,
        ),
      );
      this.assertEqual(bench.ui.posted.length, 0);
    }
  }

  // The shape of the module object and what it registers.
  export class TestSurface extends AgentCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(agent));
      this.assertEqual(Object.keys(agent).sort(), [
        "handlers_register",
        "prompt_build",
      ]);
    }

    // The four line types are registered at version 0, in order.
    test_types_registered(): void {
      const store = this.store_make([], true);
      const tasks = new queue.TaskQueue("ai", {}, true);
      const seen: [string, number][] = [];
      agent.handlers_register(
        store,
        new ClientsDouble(tasks, []),
        tasks,
        constants.provider_owner,
        constants.info,
        reader_from(settings_make()),
        (type: string, version: number) => {
          seen.push([type, version]);
        },
      );
      this.assertEqual(
        seen,
        constants.agent_types.map((type) => [type, 0]),
      );
    }
  }
}

Object.freeze(test_agent);
