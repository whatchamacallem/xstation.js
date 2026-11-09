// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the agent loop on real parts, on a real queue of thread `ai` in
// synchronous mode, which runs the turn, the client's `mcp` lines and the
// tools alike. The far ends are second real queues whose handlers are the
// test's own functions: `http` is the scripted AI, which answers each model
// request with a response of output items and keeps the request to compare
// whole, `ui` keeps the image and renders, and `server` keeps the pushes.
//
// A realm takes one registration of the agent and of the tools, so the tests
// share one bench, built at the first test, and `setUp` drops every database
// through the store's API and writes the hyperposition again. The agent's
// chains live as long as the realm, so a page load, which starts with none,
// cannot be shown here: each test's first request starts a chain as its log
// is new, and every id of the scripted AI is new in the realm, so no chain of
// an earlier test fits a later log. In the castle turn the player answers 1
// and the analyst builds the castle's gatehouse scene through the tools.

namespace test_agent {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The values of the provider, the castle turn and the bench.
  const constants = Object.freeze({
    // The id of this module's gold, in its own `test_setting_` file.
    gold_id: "typescript.test_agent",
    // A synthetic provider key, which every model request carries.
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
    blob_setting: "blob_max",
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
    // The prefix the agent lists the browser's tools under, and its mark.
    prefix: "browser",
    prefix_mark: "_",
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
      "turn.prompt",
      "sql.run",
    ]),
    // The header fields of an id, which a submit sets, in both forms.
    id_fields: Object.freeze(["i", "id"]),
    // The header fields of the id a reply answers, in both forms.
    reply_fields: Object.freeze(["r", "reply"]),
    // The ends of the paths of a model request and of an image request.
    model_path: "/responses",
    image_path: "/generations",
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
      '"region":"castle_gatehouse"}}',
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
    // The encrypted reasoning every reply of the scripted AI holds.
    reasoning_text: "weighed",
    // What every model request asks to be sent: the encrypted reasoning.
    include_text: "reasoning.encrypted_content",
    // A prompt of the castle universe, for the tests of the system prompt.
    castle_prompt: "The castle is cold, and its keeper is patient.",
    // The reference string the encoded prompt document of the gold holds.
    lore: "/castle/lore",
    // The statement a tool runs to count the turns stored of the scene.
    count_sql: "SELECT count(*) FROM _turn WHERE scene = ? AND n > 0",
    // The result of that statement while only the player's turn is stored.
    count_result:
      '{"results":[{"columns":["count(*)"],"rows":[[1]],"changes":0}]}',
    // The result of the read of the value that names the current world.
    world_result: "metaverse",
    // The text of a row appended through the store between two turns.
    noted_text: "A note between turns.",
    // What a debug mode request holds in place of its tool list.
    tools_omitted: "DEBUG_MODE_TOOL_LIST_OMITTED",
    // The fields of a chained request's body, in the order they are sent.
    body_keys: Object.freeze([
      "model",
      "previous_response_id",
      "input",
      "tools",
      "tool_choice",
      "prompt_cache_key",
      "include",
    ]),
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

  // A call the scripted AI makes: its id, the tool's name and the arguments.
  interface CallMade {
    call_id: string;
    name: string;
    arguments: string;
  }

  // A reply of the scripted AI: the response's id and its output items.
  interface ModelReply {
    id: string;
    output: FieldTable[];
  }

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
    // The replies of the scripted AI that the test scripted, in order.
    readonly models: ModelReply[];
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

  // The replies the scripted AI made in the realm, which number their ids.
  let replies_made = 0;

  // The debug mode the running test answers for itself, if it sets one.
  let debug_mode: boolean | undefined = undefined;

  // The debug reader of the agent: the test's mode first, else the thread's.
  function debug_read(): boolean {
    return debug_mode === undefined ? switches.debug_on() : debug_mode;
  }

  // A record of the far ends with nothing scripted and nothing got.
  function far_fresh(): FarRecord {
    return {
      replies: new Map(),
      got: [],
      pushes: [],
      asked: [],
      answers: [],
      models: [],
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
      harness.setting_get(constants.blob_setting) as number,
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
      switches.debug_on,
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
      debug_read,
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
  function call_make(call_id: string, name: string, text: string): CallMade {
    return { call_id, name, arguments: text };
  }

  // The calls of the castle turn, each with its arguments as JSON text.
  function calls_recorded(): CallMade[] {
    return [
      call_make(
        "call_1",
        "browser_script_run",
        '{"name":"bootstrap","args":{"universe":"castle",' +
          '"title":"The castle","world":"castle_world",' +
          '"region":"castle_gatehouse"}}',
      ),
      call_make(
        "call_2",
        "browser_image_make",
        `{"prompt":"${constants.image_prompt}",` +
          '"key":"gatehouse/arrival.png"}',
      ),
      call_make(
        "call_3",
        "browser_doc_put",
        '{"db":"castle_gatehouse","id":"scene/arrival","body":' +
          '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png",' +
          `"subtitle":"${constants.subtitle}","image":{"$ref":1}}}`,
      ),
      call_make(
        "call_4",
        "browser_kv_put",
        '{"ref":"/castle_world/scene",' +
          '"text":"/castle_gatehouse/scene/arrival/1"}',
      ),
      call_make(
        "call_5",
        "browser_render",
        '{"image":"/_files/gatehouse/arrival.png",' +
          `"subtitle":"${constants.subtitle}"}`,
      ),
    ];
  }

  // The flat function tools every model request lists: the browser's.
  function functions_recorded(): provider.FunctionTool[] {
    const tools = gold_value("tools") as mcp.Tool[];
    return tools.map((tool: mcp.Tool): provider.FunctionTool => ({
      type: "function",
      name: constants.prefix + constants.prefix_mark + tool.name,
      description: tool.description,
      parameters: tool.inputSchema,
    }));
  }

  // The system message of the text.
  function system_said(text: string): provider.InputMessage {
    return { role: "system", content: text };
  }

  // The user message of the text.
  function user_said(text: string): provider.InputMessage {
    return { role: "user", content: text };
  }

  // The item that answers the call with its output text.
  function output_of(call: CallMade, text: string): provider.CallOutput {
    return {
      type: "function_call_output",
      call_id: call.call_id,
      output: text,
    };
  }

  // Whether an input item is a system message.
  function system_held(item: unknown): boolean {
    return (item as FieldTable).role === "system";
  }

  // A reply of the scripted AI: its reasoning, its message, then its calls.
  function reply_made(text: string | null, calls: CallMade[]): ModelReply {
    replies_made += 1;
    const made = replies_made;
    const output: FieldTable[] = [
      {
        type: "reasoning",
        id: `rs_${made}`,
        summary: [],
        encrypted_content: constants.reasoning_text,
        status: "completed",
      },
    ];
    if (text !== null) {
      output.push({
        type: "message",
        id: `msg_${made}`,
        role: "assistant",
        status: "completed",
        content: [{ type: "output_text", text, annotations: [] }],
      });
    }
    calls.forEach((call: CallMade, index: number) => {
      output.push({
        type: "function_call",
        id: `fc_${made}_${index + 1}`,
        call_id: call.call_id,
        name: call.name,
        arguments: call.arguments,
        status: "completed",
      });
    });
    return { id: `resp_${made}`, output };
  }

  // The reply of the scripted AI that ends a turn with the text.
  function text_reply(text: string): ModelReply {
    return reply_made(text, []);
  }

  // The reply of the scripted AI that makes the calls.
  function calls_reply(calls: CallMade[]): ModelReply {
    return reply_made(null, calls);
  }

  // The scripted AI's answer frame: a completed response of the reply.
  function model_frame(reply: ModelReply): lines.Line {
    const line = gold_line("reply_model");
    line.json = {
      id: reply.id,
      object: "response",
      model: constants.info.chat_model,
      status: "completed",
      output: structuredClone(reply.output),
    };
    return line;
  }

  // The model request of the scene the agent submits, chained when given.
  function request_expected(
    scene: lines.DocRef,
    input: unknown[],
    chained?: ModelReply,
  ): lines.Line {
    const line = gold_line("request_model");
    const json: FieldTable = { model: constants.info.chat_model };
    if (chained !== undefined) {
      json.previous_response_id = chained.id;
    }
    json.input = input;
    json.tools = debug_read() ? constants.tools_omitted : functions_recorded();
    json.tool_choice = "auto";
    json.prompt_cache_key = scene;
    json.include = [constants.include_text];
    line.json = json;
    return line;
  }

  // The model requests of the castle turn, each chained from a reply given.
  function castle_requests(replies: ModelReply[]): lines.Line[] {
    const [first, second, third] = replies;
    const [bootstrap, image, scene, enter, render] = calls_recorded();
    const start = [system_said(constants.analyst), user_said("1")];
    return [
      request_expected(constants.scene, start),
      request_expected(
        constants.scene,
        [output_of(bootstrap, constants.bootstrap_result)],
        first,
      ),
      request_expected(
        constants.scene,
        [output_of(image, constants.image_result)],
        second,
      ),
      request_expected(
        constants.scene,
        [
          output_of(scene, constants.scene_result),
          output_of(enter, constants.enter_result),
          output_of(render, constants.render_result),
        ],
        third,
      ),
    ];
  }

  // The rows the castle turn stores, each its number, role and content.
  function castle_rows(replies: ModelReply[]): unknown[][] {
    const [first, second, third, last] = replies;
    const [bootstrap, image, scene, enter, render] = calls_recorded();
    const rows: [provider.Role, unknown[]][] = [
      ["system", [system_said(constants.analyst)]],
      ["user", [user_said("1")]],
      ["assistant", first.output],
      ["tool", [output_of(bootstrap, constants.bootstrap_result)]],
      ["assistant", second.output],
      ["tool", [output_of(image, constants.image_result)]],
      ["assistant", third.output],
      ["tool", [output_of(scene, constants.scene_result)]],
      ["tool", [output_of(enter, constants.enter_result)]],
      ["tool", [output_of(render, constants.render_result)]],
      ["assistant", last.output],
    ];
    return rows.map(([role, content], n) => [n, role, content]);
  }

  // The image answer of the castle turn, its image the gold's.
  function image_reply(): lines.Line {
    const line = gold_line("image_answer");
    const images = line.json as { data: { b64_json?: string }[] };
    images.data[0].b64_json = gold_value("image_base64") as string;
    return line;
  }

  // The `turn.prompt` lines the server's far end got, in order.
  function prompts_pushed(): lines.Line[] {
    return far.pushes.filter(
      (line) => jslb.field_get(line[0], "type") === "turn.prompt",
    );
  }

  // The rows of the scene's log as the store holds them: n, role, content.
  function rows_of(scene: lines.DocRef): unknown[][] {
    return store_get()
      .turn_list(scene)
      .map((row) => [row.n, row.role, row.content]);
  }

  // The contents of the scene's log as the store holds them.
  function contents_of(scene: lines.DocRef): provider.InputItem[][] {
    return store_get()
      .turn_list(scene)
      .map((row) => row.content);
  }

  // A prompt document of the type given that holds the text given.
  function prompt_doc(type: string, text: unknown): lines.Document {
    return { 0: { t: type }, text };
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
      debug_mode = undefined;
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

    // Scripts the scripted AI's reply to the next request, and keeps it.
    model_script(reply: ModelReply): void {
      far.models.push(reply);
      this.reply_script("http.request", model_frame(reply));
    }

    // Runs a turn of the gold line, the model answering in order, its reply.
    turn_run(name: string, replies: ModelReply[]): lines.Line {
      for (const reply of replies) {
        this.model_script(reply);
      }
      const request = line_without(gold_line(name), constants.id_fields);
      const before = far.answers.length;
      bench_get().ui.line_notify(line_typed(constants.say_type, { request }));
      this.assertEqual(far.answers.length, before + 1, "the turn did not end");
      return far.answers[before];
    }

    // Runs the castle turn, in which the player answers 1.
    castle_run(): lines.Line {
      const [bootstrap, image, scene, enter, render] = calls_recorded();
      this.model_script(calls_reply([bootstrap]));
      this.model_script(calls_reply([image]));
      this.reply_script("http.request", image_reply());
      // The image tool keeps the picture, and the render sends it again.
      this.reply_script("media.store", gold_line("media_store_reply"));
      this.reply_script("media.store", gold_line("media_store_reply"));
      this.reply_script("render", gold_line("render_reply"));
      return this.turn_run("say_castle", [
        calls_reply([scene, enter, render]),
        text_reply(constants.subtitle),
      ]);
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

    // The model requests the scripted AI got, in order, their ids taken off.
    models_got(): lines.Line[] {
      return far.got
        .filter((line) => jslb.field_get(line[0], "type") === "http.request")
        .filter((line) => (line.url as string).endsWith(constants.model_path))
        .map((line) => line_without(line, constants.id_fields));
    }

    // The input of each model request the scripted AI got, in order.
    inputs_got(): unknown[][] {
      return this.models_got().map(
        (line) => (line.json as provider.ModelRequest).input,
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
    // The first request holds the log, each later one the call outputs.
    test_requests_recorded(): void {
      this.castle_run();
      this.assertEqual(this.models_got(), castle_requests(far.models));
      const images = far.got
        .filter((line) => jslb.field_get(line[0], "type") === "http.request")
        .filter((line) => (line.url as string).endsWith(constants.image_path))
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
      const body = (JSON.parse(scene.arguments) as FieldTable).body;
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
      this.assertEqual(shown, [stored, stored, gold_line("render_arrival")]);
    }

    // The prompt at 0 as `[message]`, then each reply as sent, each output.
    test_turns_stored(): void {
      this.castle_run();
      this.assertEqual(rows_of(constants.scene), castle_rows(far.models));
    }

    // Each turn's row goes to the server as stored, the prompt as messages.
    test_turns_pushed(): void {
      this.castle_run();
      const appended = far.pushes
        .filter((line) => jslb.field_get(line[0], "type") === "turn.append")
        .map((line) => jslb.payload_of(line));
      const rows = castle_rows(far.models).slice(1);
      this.assertEqual(
        appended,
        rows.map(([, role, content]) => ({
          scene: constants.scene,
          role,
          content,
        })),
      );
      const messages = [system_said(constants.analyst)];
      this.assertEqual(
        prompts_pushed().map((line) => jslb.payload_of(line)),
        [{ scene: constants.scene, messages }],
      );
    }

    // The turn ends with the reply to `ai.say`: the new scene, the subtitle.
    test_reply_recorded(): void {
      this.reply_assert(this.castle_run(), "reply_castle");
    }
  }

  // The turn after the castle turn, in the scene that turn entered.
  export class TestTurnNext extends AgentCase {
    // The next turn is a new conversation, whose first request is whole.
    test_scene_new(): void {
      this.castle_run();
      const moat = text_reply(constants.moat_reply);
      const reply = this.turn_run("say_next", [moat]);
      const requests = this.models_got();
      const start = [system_said(constants.analyst), user_said("0")];
      this.assertEqual(
        requests[requests.length - 1],
        request_expected(constants.arrival, start),
      );
      this.assertEqual(rows_of(constants.arrival), [
        [0, "system", [start[0]]],
        [1, "user", [start[1]]],
        [2, "assistant", moat.output],
      ]);
      this.reply_assert(reply, "reply_next");
    }

    // The universe's prompt follows the analyst's once the scripts made one.
    test_universe_prompt(): void {
      this.castle_run();
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store_get().doc_put("castle", "prompt", doc);
      const moat = text_reply(constants.moat_reply);
      this.turn_run("say_next", [moat]);
      const requests = this.models_got();
      const analyst = system_said(constants.analyst);
      const castle = system_said(constants.castle_prompt);
      this.assertEqual(
        requests[requests.length - 1],
        request_expected(constants.arrival, [analyst, castle, user_said("0")]),
      );
      this.assertEqual(rows_of(constants.arrival), [
        [-1, "system", [analyst]],
        [0, "system", [castle]],
        [1, "user", [user_said("0")]],
        [2, "assistant", moat.output],
      ]);
    }
  }

  // Turns with no tool calls and a click.
  export class TestTurnShort extends AgentCase {
    // A reply with no calls ends the turn, in the request's name form.
    test_turn_short(): void {
      const nothing = text_reply(constants.nothing_reply);
      const reply = this.turn_run("say_full", [nothing]);
      const start = [system_said(constants.analyst), user_said("2")];
      this.assertEqual(rows_of(constants.scene), [
        [0, "system", [start[0]]],
        [1, "user", [start[1]]],
        [2, "assistant", nothing.output],
      ]);
      this.reply_assert(reply, "reply_full");
      this.assertEqual(this.models_got(), [
        request_expected(constants.scene, start),
      ]);
    }

    // A click is told to the model as text, and the reply ends the turn.
    test_click_turn(): void {
      const answer = text_reply(constants.click_reply);
      const reply = this.turn_run("click", [answer]);
      const said = user_said(gold_text("agent_click_text"));
      const start = [system_said(constants.analyst), said];
      this.assertEqual(this.models_got(), [
        request_expected(constants.scene, start),
      ]);
      this.assertEqual(contents_of(constants.scene), [
        [start[0]],
        [said],
        answer.output,
      ]);
      this.reply_assert(reply, "reply_click");
    }
  }

  // A scene's chain: chained while the log adds rows, else a chain's first.
  export class TestChain extends AgentCase {
    // The next turn sends its user item alone, after the last response.
    test_turn_chained(): void {
      const first = text_reply(constants.nothing_reply);
      this.turn_run("say_nothing", [first]);
      const second = text_reply(constants.moat_reply);
      this.turn_run("say_again", [second]);
      const requests = this.models_got();
      this.assertEqual(requests, [
        request_expected(constants.scene, [
          system_said(constants.analyst),
          user_said("2"),
        ]),
        request_expected(constants.scene, [user_said("2")], first),
      ]);
      this.assertEqual(Object.keys(requests[1].json as FieldTable), [
        ...constants.body_keys,
      ]);
      this.assertEqual(contents_of(constants.scene), [
        [system_said(constants.analyst)],
        [user_said("2")],
        first.output,
        [user_said("2")],
        second.output,
      ]);
    }

    // Calls run before their reply is stored, their outputs go chained.
    test_results_chained(): void {
      const statement = {
        sql: constants.count_sql,
        params: [constants.scene],
      };
      const count = call_make(
        "call_1",
        "browser_sql_run",
        JSON.stringify({ db: "metaverse", statements: [statement] }),
      );
      const world = call_make(
        "call_2",
        "browser_kv_get",
        '{"ref":"/metaverse/world"}',
      );
      const calls = calls_reply([count, world]);
      const nothing = text_reply(constants.nothing_reply);
      this.turn_run("say_castle", [calls, nothing]);
      const outputs = [
        output_of(count, constants.count_result),
        output_of(world, constants.world_result),
      ];
      this.assertEqual(
        this.models_got()[1],
        request_expected(constants.scene, outputs, calls),
      );
      this.assertEqual(rows_of(constants.scene), [
        [0, "system", [system_said(constants.analyst)]],
        [1, "user", [user_said("1")]],
        [2, "assistant", calls.output],
        [3, "tool", [outputs[0]]],
        [4, "tool", [outputs[1]]],
        [5, "assistant", nothing.output],
      ]);
    }

    // Rows a script appends between turns go in the chained request.
    test_rows_appended(): void {
      const first = text_reply(constants.nothing_reply);
      this.turn_run("say_nothing", [first]);
      const noted = user_said(constants.noted_text);
      store_get().turn_append(constants.scene, "user", [noted]);
      this.turn_run("say_again", [text_reply(constants.nothing_reply)]);
      this.assertEqual(
        this.models_got()[1],
        request_expected(constants.scene, [noted, user_said("2")], first),
      );
    }

    // A compaction at the threshold makes the next request a chain's first.
    test_threshold_restart(): void {
      const store = store_get();
      const threshold = harness.setting_get(
        constants.compact_setting,
      ) as number;
      // Turns enough that the first turn's reply reaches the threshold.
      for (let n = 1; n <= threshold - 2; n += 1) {
        store.turn_append(constants.scene, "user", [user_said(String(n))]);
      }
      this.turn_run("say_nothing", [text_reply(constants.nothing_reply)]);
      this.turn_run("say_again", [text_reply(constants.nothing_reply)]);
      const summary = gold_text("substrate_turns_compacted_at").replaceAll(
        "{0}",
        String(threshold),
      );
      const requests = this.models_got();
      this.assertEqual(requests.length, 2);
      const first = requests[0].json as FieldTable;
      this.assertFalse(Object.hasOwn(first, "previous_response_id"));
      this.assertEqual(
        requests[1],
        request_expected(constants.scene, [
          system_said(constants.analyst),
          system_said(summary),
          user_said("2"),
        ]),
      );
    }
  }

  // The tool list a request holds: the text that omits it in debug mode alone.
  export class TestToolList extends AgentCase {
    // In debug mode a request holds the omission's text, not the tools.
    test_tools_omitted(): void {
      debug_mode = true;
      this.turn_run("say_nothing", [text_reply(constants.nothing_reply)]);
      const json = this.models_got()[0].json as FieldTable;
      this.assertEqual(json.tools, constants.tools_omitted);
    }

    // Outside debug mode a request lists every tool, flat, as xAI takes it.
    test_tools_listed(): void {
      debug_mode = false;
      this.turn_run("say_nothing", [text_reply(constants.nothing_reply)]);
      const json = this.models_got()[0].json as FieldTable;
      this.assertEqual(json.tools, functions_recorded());
    }
  }

  // A conversation gets its system prompt once, whatever follows.
  export class TestPromptOnce extends AgentCase {
    // One commit before the first turn, and a chain's first alone sends it.
    test_commit_once(): void {
      this.castle_run();
      const types = far.pushes.map((line) => jslb.field_get(line[0], "type"));
      this.assertEqual(types.slice(0, 2), ["turn.prompt", "turn.append"]);
      const prompts = prompts_pushed();
      this.assertEqual(prompts.length, 1);
      const analyst = system_said(constants.analyst);
      this.assertEqual(jslb.payload_of(prompts[0]).messages, [analyst]);
      const [first, ...chained] = this.inputs_got();
      this.assertEqual(first[0], analyst);
      this.assertEqual(first.filter(system_held), [analyst]);
      this.assertEqual(chained.length, 3);
      for (const input of chained) {
        this.assertEqual(input.filter(system_held), []);
      }
    }

    // A later turn stores no prompt and sends none, and an edit stays unread.
    test_prompt_kept(): void {
      this.turn_run("say_nothing", [text_reply(constants.nothing_reply)]);
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store_get().doc_put("metaverse", "prompt", doc);
      this.turn_run("say_again", [text_reply(constants.nothing_reply)]);
      this.assertEqual(prompts_pushed().length, 1);
      this.assertEqual(this.inputs_got()[1], [user_said("2")]);
      this.assertEqual(contents_of(constants.scene)[0], [
        system_said(constants.analyst),
      ]);
    }

    // A compaction between turns restarts the chain, the prompt sent once.
    test_compaction_kept(): void {
      this.turn_run("say_nothing", [text_reply(constants.nothing_reply)]);
      const text = gold_text("substrate_turns_compacted");
      store_get().turn_compact(constants.scene, 2, text);
      this.turn_run("say_again", [text_reply(constants.nothing_reply)]);
      this.assertEqual(prompts_pushed().length, 1);
      this.assertEqual(
        this.models_got()[1],
        request_expected(constants.scene, [
          system_said(constants.analyst),
          system_said(text),
          user_said("2"),
        ]),
      );
    }
  }

  // The system prompt `prompt_build` makes from the store, its messages.
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
        debug_read,
      );
      this.assertEqual(
        seen,
        constants.agent_types.map((type) => [type, 0]),
      );
    }
  }
}

Object.freeze(test_agent);
