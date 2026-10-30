// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the agent loop on real parts: the agent registered on the realm's
// dispatch with a real `substrate.Store` on the realm's sqlite3 module and
// pool, a real `mcp.ClientSet` whose client reaches `tools_browser` on a real
// `mcp.Server` over the same store, and a real queue of thread `ai` in
// synchronous mode, which runs the turn, the client's `mcp` lines and the
// tools alike. The player's text or click comes from the queue of thread
// `ui`, whose handler of the test's own submits it and keeps the reply its
// wake gets. The far ends are second real queues whose handlers are the
// test's own functions, each answering with the reply the test scripted from
// the gold and keeping every request it got: `http` is the scripted AI,
// which answers the chat requests with the castle turn's frames and the
// image request with its image, `ui` keeps the image and renders, and
// `server` keeps the store's pushes.
//
// A realm takes one registration of the agent and of the tools, since each
// registers its line types in the realm's one dispatch table, so the tests
// share the one bench, built at the first test, and each test starts in the
// hyperposition: `setUp` drops every database of the store through its API,
// then writes the world, the scene, the analyst's prompt, the universe table
// and the bootstrap script. The castle turn, in which the player answers 1
// and the analyst builds the castle's gatehouse scene through the tools, is
// checked by its requests, the store it leaves, its turns and its reply; then
// the turn after it, short turns and a click, a compacted scene, a round
// stored only after its tool ran, and the system prompt and its errors. The
// request frames, the lines the turns end with and the texts are those of
// the gold record.

namespace test_agent {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The values of the provider, the castle turn and the bench.
  const constants = Object.freeze({
    // The id of this module's gold in `test_settings.json`.
    gold_id: "typescript.test_agent",
    // A synthetic provider key, which every chat request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models of a run that is not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // The root of the store's databases in the realm's pool.
    root: "/test_agent",
    // The settings of the store's sizes.
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    // The threads of the bench: the agent's, the provider's, the UI, server.
    thread: "ai" as const,
    http_thread: "http" as const,
    ui_thread: "ui" as const,
    server_thread: "server" as const,
    // The identities of the browser's server and of the agent's client.
    server_name: "xsjs-browser",
    client_name: "hyperposition-engine",
    version: "0",
    // The prefix the agent lists the browser's tools under.
    prefix: "browser",
    // The line type of the protocol, and the version of every handler.
    line_type: "mcp",
    handler_version: 0,
    // The test's own types: the handshake's steps, the player's turn.
    handshake_type: "test_agent.handshake",
    initialized_type: "test_agent.initialized",
    listed_type: "test_agent.listed",
    say_type: "test_agent_ui.say",
    said_type: "test_agent_ui.said",
    // The owner table of the agent's queue.
    owners: Object.freeze<queue.OwnerTable>({
      mcp: "ai",
      "ai.": "ai",
      "tools.": "ai",
      "test_agent.": "ai",
    }),
    // The requests each far end answers, by its thread.
    http_types: Object.freeze(["http.request"]),
    ui_types: Object.freeze(["media.store", "render"]),
    // The pushes of the store, which the server's far end keeps.
    push_types: Object.freeze([
      "db.create",
      "db.drop",
      "kv.put",
      "kv.delete",
      "doc.put",
      "turn.append",
      "sql.run",
    ]),
    // The header fields of an id, which a submit sets, in both forms.
    id_fields: Object.freeze(["i", "id"]),
    // The header fields of the id a reply answers, in both forms.
    reply_fields: Object.freeze(["r", "reply"]),
    // The hyperposition scene, on screen when the castle turn starts.
    scene: "/metaverse/hyperposition/1",
    // The arrival scene the castle turn writes and enters.
    arrival: "/castle_gatehouse/scene/arrival/1",
    // The analyst's system prompt, the prompt document of the metaverse.
    analyst:
      "You are a very bored British psychoanalyst. You hold the" +
      " hyperposition, a dark place of fog and a few inexplicable lights." +
      " Find the right universe for the player and act on requests without" +
      " judgement. Your scripts are the database administrator of every" +
      " universe you create: typed tables, indexes, views, no JSON columns" +
      " unless a document is what fits.",
    // The universe table and its trigger, as API/sql/metaverse.sql has them.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    trigger_sql:
      "CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe" +
      " WHEN EXISTS (SELECT 1 FROM universe" +
      " WHERE world = NEW.world AND name <> NEW.name)" +
      " BEGIN SELECT RAISE(ABORT, 'agent.content_ambiguous'); END",
    // The ref of the bootstrap script, which the castle turn runs.
    bootstrap_ref: "/_files/script/bootstrap.js",
    // The subtitle the castle turn ends with.
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The prompt of the image the castle turn makes.
    image_prompt:
      "A rain dark castle gatehouse at dusk seen from the far side of a" +
      " moat, one lantern lit, painted, wide still frame, no people",
    // The ref of that image.
    image_ref: "/_files/gatehouse/arrival.png",
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
      '"1e2806a1029564579de9739ef0014f0332c5a8026bca9373e473224a3b094d8b"}',
    render_result: "{}",
    // The replies of the model beside the castle turn.
    nothing_reply: "Nothing happens.",
    moat_reply: "Still the moat.",
    // The reply of the model in the test of a click.
    click_reply: "The lights flicker.",
    // The id of the model's replies.
    answer_id: "chatcmpl-answer",
    // A prompt of the castle universe, for the tests of the system prompt.
    castle_prompt: "The castle is cold, and its keeper is patient.",
    // The reference string the encoded prompt document of the gold holds.
    lore: "/castle/lore",
    // The statement a tool runs to count the turns stored of the scene.
    count_sql: "SELECT count(*) FROM _turn WHERE scene = ?",
    // The result of that statement while only the player's turn is stored.
    count_result:
      '{"results":[{"columns":["count(*)"],"rows":[[1]],"changes":0}]}',
    // The line types the agent registers, in its order.
    agent_types: Object.freeze([
      "ai.say",
      "ai.click",
      "ai.model_reply",
      "ai.tool_reply",
    ]),
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // What the far ends got and gave in one test, and the turns' replies.
  interface FarRecord {
    // The reply frames each far end still gives, by request type, in order.
    readonly replies: Map<string, lines.Line[]>;
    // Each request a far end got, in order.
    readonly got: lines.Line[];
    // Each push of the store that the server's far end got, in order.
    readonly pushes: lines.Line[];
    // The ids the UI's queue gave the turns it submitted, in order.
    readonly asked: number[];
    // The reply each turn ended with, in order.
    readonly answers: lines.Line[];
  }

  // The real parts the tests share, built once per realm.
  interface AgentBench {
    store: substrate.Store;
    clients: mcp.ClientSet;
    tasks: queue.TaskQueue;
    ui: queue.TaskQueue;
  }

  // The bench of the realm, built at the first test.
  let bench_kept: AgentBench | undefined = undefined;

  // What the far ends got and gave in the test that runs.
  let far: FarRecord = far_fresh();

  // A record of the far ends with nothing scripted and nothing got.
  function far_fresh(): FarRecord {
    return {
      replies: new Map(),
      got: [],
      pushes: [],
      asked: [],
      answers: [],
    };
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`${constants.gold_id}.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The fields of a header, to read and write by name.
  function fields_of(line: lines.Line): FieldTable {
    return line[0] as unknown as FieldTable;
  }

  // A copy of a line, its header's fields of the names taken off.
  function line_without(
    line: lines.Line,
    names: readonly string[],
  ): lines.Line {
    const copy = structuredClone(line);
    for (const name of names) {
      delete fields_of(copy)[name];
    }
    return copy;
  }

  // A line of the test's own type and payload, in the form the settings pick.
  function line_typed(type: string, payload: FieldTable): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
  }

  // A far end's answer to a request: the next reply the test scripted for it.
  function far_answer(line: lines.Line): lines.Line {
    far.got.push(line);
    const type = jslb.field_get(line[0], "type") as string;
    const frame = far.replies.get(type)?.shift();
    if (frame === undefined) {
      throw new Error(`the test scripted no reply to ${type}`);
    }
    const blobs = jslb.headers_of(frame).slice(1) as lines.BlobHeader[];
    return dispatch.reply_make(line, jslb.payload_of(frame), blobs);
  }

  // Joins a far queue of the thread to the agent's queue by linked ports.
  function far_join(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
    types: readonly string[],
  ): queue.TaskQueue {
    const owners = Object.fromEntries(types.map((type) => [type, thread]));
    const far_tasks = new queue.TaskQueue(thread, owners, true);
    const port = new queue.LocalPort();
    tasks.port_add(thread, port);
    far_tasks.port_add(constants.thread, new queue.LocalPort(port));
    return far_tasks;
  }

  // Registers the far ends' answers and keepers, the test's own functions.
  function far_register(ui: queue.TaskQueue): void {
    const version = constants.handler_version;
    for (const type of [...constants.http_types, ...constants.ui_types]) {
      dispatch.handler_register(type, version, far_answer);
    }
    for (const type of constants.push_types) {
      dispatch.handler_register(type, version, (line) => {
        far.pushes.push(line);
        return undefined;
      });
    }
    dispatch.handler_register(constants.say_type, version, (line) => {
      const request = jslb.payload_of(line).request as lines.Line;
      const id = ui.task_submit(request, constants.thread);
      far.asked.push(id);
      return dispatch.task_sleep(null, [id], constants.said_type);
    });
    dispatch.handler_register(constants.said_type, version, (line) => {
      far.answers.push((line.replies as lines.Line[])[0]);
      return undefined;
    });
  }

  // Registers the steps of the client's handshake, the test's own handlers.
  function handshake_register(client: mcp.Client): void {
    const version = constants.handler_version;
    dispatch.handler_register(constants.handshake_type, version, () =>
      dispatch.task_sleep(
        null,
        [client.initialize_send()],
        constants.initialized_type,
      ),
    );
    dispatch.handler_register(constants.initialized_type, version, (line) => {
      client.initialized_send((line.replies as lines.Line[])[0]);
      const id = client.tools_list();
      return dispatch.task_sleep(null, [id], constants.listed_type);
    });
    dispatch.handler_register(constants.listed_type, version, (line) => {
      client.tools_read((line.replies as lines.Line[])[0]);
      return undefined;
    });
  }

  // Builds the bench: the agent and the tools on real parts and queues.
  function bench_build(): AgentBench {
    const tasks = new queue.TaskQueue(
      constants.thread,
      constants.owners,
      true,
    );
    far_join(tasks, constants.http_thread, constants.http_types);
    const ui = far_join(tasks, constants.ui_thread, [
      ...constants.ui_types,
      constants.say_type,
      constants.said_type,
    ]);
    far_join(tasks, constants.server_thread, constants.push_types);
    far_register(ui);
    const store = new substrate.Store(
      test_sqlite3,
      test_pool,
      new substrate.CacheFiles([...test_slots]),
      constants.root,
      harness.setting_get(constants.overflow_setting) as number,
      harness.setting_get(constants.compact_setting) as number,
      tasks,
    );
    const server = new mcp.Server(constants.server_name, constants.version);
    tools_browser.tools_register(
      server,
      store,
      tasks,
      constants.http_thread,
      constants.info,
      harness.setting_get,
    );
    dispatch.handler_register(
      constants.line_type,
      constants.handler_version,
      (line) => server.line_handle(line),
    );
    const client = new mcp.Client(
      constants.client_name,
      constants.version,
      tasks,
      constants.thread,
    );
    handshake_register(client);
    tasks.line_notify(line_typed(constants.handshake_type, {}));
    const clients = new mcp.ClientSet();
    clients.client_add(constants.prefix, client);
    agent.handlers_register(
      store,
      clients,
      tasks,
      constants.http_thread,
      constants.info,
      dispatch.handler_register,
    );
    return { store, clients, tasks, ui };
  }

  // The bench of the realm, built at its first use.
  function bench_get(): AgentBench {
    if (bench_kept === undefined) {
      bench_kept = bench_build();
    }
    return bench_kept;
  }

  // The store the agent and the tools use.
  function store_get(): substrate.Store {
    return bench_get().store;
  }

  // Writes the hyperposition: its world, scene, prompt, table and script.
  function hyperposition_write(store: substrate.Store): void {
    store.db_create("metaverse");
    store.db_create("_files");
    store.sql_run("metaverse", [
      { sql: constants.universe_sql, params: [] },
      { sql: constants.trigger_sql, params: [] },
    ]);
    store.kv_put("/metaverse/world", utility.utf8_encode("metaverse"));
    store.kv_put("/metaverse/scene", utility.utf8_encode(constants.scene));
    store.doc_put(
      "metaverse",
      "prompt",
      prompt_doc("prompt", constants.analyst),
    );
    const bootstrap = gold_value("bootstrap_script") as string;
    store.kv_put(constants.bootstrap_ref, utility.utf8_encode(bootstrap));
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
          '"key":"gatehouse/arrival.png"}',
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

  // The function tools every chat request lists: the browser's, prefixed.
  function functions_recorded(): provider.FunctionTool[] {
    const tools = gold_value("tools") as mcp.Tool[];
    return tools.map((tool: mcp.Tool): provider.FunctionTool => ({
      type: "function",
      function: {
        name: `${constants.prefix}.${tool.name}`,
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

  // The model's replies of the castle turn, in order.
  function answers_recorded(): provider.ChatMessage[] {
    const [bootstrap, image, scene, enter, render] = calls_recorded();
    return [
      assistant_calls([bootstrap]),
      assistant_calls([image]),
      assistant_calls([scene, enter, render]),
      assistant_said(constants.subtitle),
    ];
  }

  // A prompt document of the type given that holds the text given.
  function prompt_doc(type: string, text: unknown): lines.Document {
    return { 0: { t: type }, text };
  }

  // The provider's answer frame: a completion of the message.
  function chat_reply(message: provider.ChatMessage): lines.Line {
    const line = gold_line("reply_chat");
    line.json = {
      id: constants.answer_id,
      model: constants.info.chat_model,
      choices: [{ index: 0, message, finish_reason: "stop" }],
    };
    return line;
  }

  // The chat request the agent submits for the messages, on a gold frame.
  function request_expected(messages: provider.ChatMessage[]): lines.Line {
    const line = gold_line("request_chat");
    line.json = {
      model: constants.info.chat_model,
      messages,
      tools: functions_recorded(),
      tool_choice: "auto",
    };
    return line;
  }

  // The image answer of the castle turn, its image the gold's.
  function image_reply(): lines.Line {
    const line = gold_line("image_answer");
    const images = line.json as { data: { b64_json?: string }[] };
    images.data[0].b64_json = gold_value("image_base64") as string;
    return line;
  }

  // The contents of the turns of the scene as the store holds them.
  function contents_of(scene: lines.DocRef): provider.ChatMessage[] {
    return store_get()
      .turn_list(scene)
      .map((row) => row.content);
  }

  // Makes the castle universe's world the current one, its row written.
  function castle_enter(store: substrate.Store): void {
    store.db_create("castle");
    store.sql_run("metaverse", [
      {
        sql: "INSERT INTO universe VALUES (?, ?, ?, ?)",
        params: ["castle", "The castle", "player", "castle_world"],
      },
    ]);
    store.kv_put("/metaverse/world", utility.utf8_encode("castle_world"));
  }

  // An agent test: the provider key set, the store in the hyperposition.
  class AgentCase extends unittest.TestCase {
    // Sets the key, then drops every database and writes the hyperposition.
    setUp(): void {
      provider.key_set(constants.key);
      const store = store_get();
      for (const name of store.db_list()) {
        store.db_drop(name);
      }
      hyperposition_write(store);
      far = far_fresh();
    }

    // Checks every scripted reply was given.
    tearDown(): void {
      for (const [type, left] of far.replies) {
        this.assertEqual(left, [], `replies to ${type} were left`);
      }
    }

    // Scripts the far end's reply to the next request of the type.
    reply_script(type: string, frame: lines.Line): void {
      const left = far.replies.get(type);
      if (left === undefined) {
        far.replies.set(type, [frame]);
      } else {
        left.push(frame);
      }
    }

    // Runs a turn of the gold line, the model answering in order, its reply.
    turn_run(name: string, answers: provider.ChatMessage[]): lines.Line {
      for (const answer of answers) {
        this.reply_script("http.request", chat_reply(answer));
      }
      const request = line_without(gold_line(name), constants.id_fields);
      const before = far.answers.length;
      bench_get().ui.line_notify(line_typed(constants.say_type, { request }));
      this.assertEqual(far.answers.length, before + 1, "the turn did not end");
      return far.answers[before];
    }

    // Runs the castle turn, in which the player answers 1.
    castle_run(): lines.Line {
      const answers = answers_recorded();
      for (const answer of answers.slice(0, 2)) {
        this.reply_script("http.request", chat_reply(answer));
      }
      this.reply_script("http.request", image_reply());
      this.reply_script("media.store", gold_line("media_store_reply"));
      this.reply_script("render", gold_line("render_reply"));
      return this.turn_run("say_castle", answers.slice(2));
    }

    // Asserts the reply is the gold line's, to the turn the UI asked last.
    reply_assert(reply: lines.Line, name: string): void {
      const expected = gold_line(name);
      const header = fields_of(expected);
      const field = constants.reply_fields.find((key) =>
        Object.hasOwn(header, key),
      ) as string;
      header[field] = far.asked[far.asked.length - 1];
      this.assertEqual(reply, expected);
    }

    // The chat requests the scripted AI got, in order, their ids taken off.
    chats_got(): lines.Line[] {
      return far.got
        .filter((line) => jslb.field_get(line[0], "type") === "http.request")
        .filter((line) => (line.url as string).endsWith("/chat/completions"))
        .map((line) => line_without(line, constants.id_fields));
    }

    // The messages of the chat requests the scripted AI got, in order.
    messages_got(): provider.ChatMessage[][] {
      return this.chats_got().map(
        (line) => (line.json as provider.ChatRequest).messages,
      );
    }

    // The error the function throws, which must be an `Error`.
    thrown_get(fn: () => unknown): Error {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error) {
          return error;
        }
        throw error;
      }
      return this.fail("Nothing was thrown.");
    }
  }

  // The castle turn: the player answers 1 and the analyst builds a scene.
  export class TestTurnRecorded extends AgentCase {
    // The four chat requests and the image request are the castle turn's.
    test_requests_recorded(): void {
      this.castle_run();
      const chats = messages_recorded().map((messages) =>
        request_expected(messages),
      );
      this.assertEqual(this.chats_got(), chats);
      const images = far.got
        .filter((line) => jslb.field_get(line[0], "type") === "http.request")
        .filter((line) => (line.url as string).endsWith("/generations"))
        .map((line) => line_without(line, constants.id_fields));
      this.assertEqual(images, [gold_line("image_request")]);
    }

    // Each call reached its tool with its arguments, as the store now shows.
    test_calls_recorded(): void {
      this.castle_run();
      const store = store_get();
      this.assertEqual(store.db_list(), [
        "_files",
        "castle",
        "castle_gatehouse",
        "castle_world",
        "metaverse",
      ]);
      const [, , scene] = calls_recorded();
      const body = (JSON.parse(scene.function.arguments) as FieldTable).body;
      this.assertEqual(store.doc_get(constants.arrival), body);
      const entered = utility.utf8_decode(
        store.kv_get("/castle_world/scene").data as Uint8Array,
      );
      this.assertEqual(entered, constants.arrival);
      const image = store.kv_get(constants.image_ref);
      this.assertEqual(image.sha256, gold_value("image_sha256"));
      const shown = far.got
        .filter((line) => jslb.field_get(line[0], "type") !== "http.request")
        .map((line) => line_without(line, constants.id_fields));
      const stored = gold_line("media_store");
      stored[1] = {
        size: image.size,
        d: utility.base64_decode(gold_value("image_base64") as string),
      };
      this.assertEqual(shown, [stored, gold_line("render_arrival")]);
    }

    // Every message of the turn is a turn of the scene, appended in order.
    test_turns_stored(): void {
      this.castle_run();
      const rows = store_get().turn_list(constants.scene);
      const expected = contents_recorded();
      this.assertEqual(
        rows.map((row) => [row.scene, row.n, row.role, row.content]),
        expected.map((message, index) => [
          constants.scene,
          index + 1,
          message.role,
          message,
        ]),
      );
    }

    // The turn ends with the reply to `ai.say`: the new scene, the subtitle.
    test_reply_recorded(): void {
      this.reply_assert(this.castle_run(), "reply_castle");
    }
  }

  // The turn after the castle turn, in the scene that turn entered.
  export class TestTurnNext extends AgentCase {
    // The next turn is a new conversation, that of the arrival scene.
    test_scene_new(): void {
      this.castle_run();
      const moat = assistant_said(constants.moat_reply);
      const reply = this.turn_run("say_next", [moat]);
      const requests = this.messages_got();
      this.assertEqual(requests[requests.length - 1], [
        system_said(constants.analyst),
        user_said("0"),
      ]);
      this.assertEqual(contents_of(constants.arrival), [user_said("0"), moat]);
      this.reply_assert(reply, "reply_next");
    }

    // The universe's prompt follows the analyst's once the scripts made one.
    test_universe_prompt(): void {
      this.castle_run();
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store_get().doc_put("castle", "prompt", doc);
      const moat = assistant_said(constants.moat_reply);
      this.turn_run("say_next", [moat]);
      const requests = this.messages_got();
      this.assertEqual(requests[requests.length - 1], [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
        user_said("0"),
      ]);
    }
  }

  // Turns with no tool calls and a click.
  export class TestTurnShort extends AgentCase {
    // A reply with no tool calls ends the turn, in the request's name form.
    test_turn_short(): void {
      const nothing = assistant_said(constants.nothing_reply);
      const reply = this.turn_run("say_full", [nothing]);
      this.assertEqual(contents_of(constants.scene), [
        user_said("2"),
        nothing,
      ]);
      this.reply_assert(reply, "reply_full");
      this.assertEqual(this.chats_got(), [
        request_expected([system_said(constants.analyst), user_said("2")]),
      ]);
    }

    // A click is told to the model as text, and the reply ends the turn.
    test_click_turn(): void {
      const message = assistant_said(constants.click_reply);
      const reply = this.turn_run("click", [message]);
      const said = user_said(gold_text("agent_click_text"));
      this.assertEqual(this.messages_got(), [
        [system_said(constants.analyst), said],
      ]);
      this.assertEqual(contents_of(constants.scene), [said, message]);
      this.reply_assert(reply, "reply_click");
    }
  }

  // The requests of a scene the store compacted and of one it kept whole.
  export class TestCompacted extends AgentCase {
    // A compacted scene goes to the model as listed: its summary, then more.
    test_request_compacted(): void {
      const store = store_get();
      const text = gold_text("substrate_turns_compacted");
      store.turn_append(constants.scene, "user", user_said("1"));
      const said = assistant_said(constants.nothing_reply);
      store.turn_append(constants.scene, "assistant", said);
      store.turn_compact(constants.scene, 2, text);
      const nothing = assistant_said(constants.nothing_reply);
      this.turn_run("say_nothing", [nothing]);
      this.assertEqual(this.messages_got(), [
        [system_said(constants.analyst), system_said(text), user_said("2")],
      ]);
    }

    // A scene kept whole goes to the model with every turn it holds.
    test_request_whole(): void {
      const nothing = assistant_said(constants.nothing_reply);
      this.turn_run("say_nothing", [nothing]);
      this.turn_run("say_again", [nothing]);
      this.assertEqual(this.messages_got()[1], [
        system_said(constants.analyst),
        user_said("2"),
        nothing,
        user_said("2"),
      ]);
    }
  }

  // A round of tool calls is stored with its results, after the tools ran.
  export class TestRounds extends AgentCase {
    // The reply that calls a tool is stored with its result, after it ran.
    test_round_stored(): void {
      const statement = {
        sql: constants.count_sql,
        params: [constants.scene],
      };
      const count = call_make(
        "call_1",
        "browser.sql_run",
        JSON.stringify({ db: "metaverse", statements: [statement] }),
      );
      const nothing = assistant_said(constants.nothing_reply);
      this.turn_run("say_castle", [assistant_calls([count]), nothing]);
      this.assertEqual(contents_of(constants.scene), [
        user_said("1"),
        assistant_calls([count]),
        tool_said(count, constants.count_result),
        nothing,
      ]);
    }
  }

  // The system prompt `prompt_build` makes from the store.
  export class TestPrompt extends AgentCase {
    // In the hyperposition the system prompt is the analyst's alone.
    test_prompt_analyst(): void {
      this.assertEqual(agent.prompt_build(store_get()), [
        system_said(constants.analyst),
      ]);
    }

    // The prompt of the universe of the current world follows the analyst's.
    test_prompt_universe(): void {
      const store = store_get();
      castle_enter(store);
      store.doc_put(
        "castle",
        "prompt",
        prompt_doc("prompt", constants.castle_prompt),
      );
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A universe without a prompt adds none.
    test_prompt_absent(): void {
      const store = store_get();
      castle_enter(store);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
      ]);
    }

    // The head of the universe's prompt is read, not an older version.
    test_prompt_head(): void {
      const store = store_get();
      castle_enter(store);
      store.doc_put("castle", "prompt", prompt_doc("prompt", "An old one."));
      store.doc_put(
        "castle",
        "prompt",
        prompt_doc("prompt", constants.castle_prompt),
      );
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A prompt document of another type is read by its text all the same.
    test_prompt_typed(): void {
      const store = store_get();
      castle_enter(store);
      store.doc_put(
        "castle",
        "prompt",
        prompt_doc("note", constants.castle_prompt),
      );
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A prompt text that is a reference string is read back as that text.
    test_prompt_reference(): void {
      const store = store_get();
      castle_enter(store);
      const doc = gold_value("document_lore") as lines.Document;
      store.doc_put("castle", "prompt", doc);
      this.assertEqual(agent.prompt_build(store), [
        system_said(constants.analyst),
        system_said(constants.lore),
      ]);
    }
  }

  // The errors of the system prompt, compared with their messages.
  export class TestErrors extends AgentCase {
    // A prompt text not a string throws, the universe's or the analyst's.
    test_prompt_invalid(): void {
      const store = store_get();
      castle_enter(store);
      store.doc_put("castle", "prompt", prompt_doc("prompt", 5));
      const first = this.thrown_get(() => agent.prompt_build(store));
      this.assertEqual(
        first.message,
        gold_text("agent_prompt_invalid_universe"),
      );
      store.doc_put("metaverse", "prompt", prompt_doc("prompt", 5));
      const second = this.thrown_get(() => agent.prompt_build(store));
      this.assertEqual(
        second.message,
        gold_text("agent_prompt_invalid_analyst"),
      );
    }

    // The store's error for a missing analyst's prompt reaches the caller.
    test_analyst_missing(): void {
      const store = store_get();
      store.db_drop("metaverse");
      store.db_create("metaverse");
      const error = this.thrown_get(() => agent.prompt_build(store));
      this.assertEqual(error.message, gold_text("substrate_id_missing"));
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
      const bench = bench_get();
      const seen: [string, number][] = [];
      agent.handlers_register(
        bench.store,
        bench.clients,
        bench.tasks,
        constants.http_thread,
        constants.info,
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
