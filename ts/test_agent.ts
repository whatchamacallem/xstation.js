// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the agent loop on doubles: a store double that answers the values,
// documents, statements and turns each test chose and keeps the turns the
// agent appends, a double of the MCP clients whose tools answer at once, a
// task queue double that keeps each submitted line, and a register function
// that keeps the handlers. Each test runs a turn as a queue would, calling
// the handlers in turn with the wake lines of the gold: the castle turn, in
// which the player answers 1 and the analyst builds the castle's gatehouse
// scene, the turn after it, short turns and a click, the system prompt, a
// scene the store compacted, failed tool calls that store no reply without
// its results, and every error the agent throws. The request frames, the
// lines the turns end with and the texts are those of the gold record.

namespace test_agent {
  // The values of the provider, the castle turn and the doubles' answers.
  const constants = Object.freeze({
    // A synthetic provider key, which every chat request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models of a run that is not scripted.
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
    // The owner whose port answers the provider's requests.
    provider_owner: "http" as const,
    // The ids the queue double hands out for the chat requests, in order.
    request_ids: Object.freeze([21, 22, 23, 24, 25, 26, 27, 28]),
    // The ids the clients double hands out for the tool calls, in order.
    call_ids: Object.freeze([31, 32, 33, 34, 35, 36, 37, 38]),
    // The types of the wakes the agent sleeps with.
    model_type: "ai.model_reply",
    tool_type: "ai.tool_reply",
    // The hyperposition scene, on screen when the castle turn starts.
    scene: "/metaverse/hyperposition/1",
    // The arrival scene the castle turn writes and enters.
    arrival: "/castle_gatehouse/scene/arrival/1",
    // The head of the analyst's prompt document in the store double.
    analyst_ref: "/metaverse/prompt/1",
    // The analyst's system prompt, which each store double holds.
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
    // The statements the agent runs: the universe of a world, a head.
    universe_sql: "SELECT name FROM universe WHERE world = ?",
    head_sql: "SELECT version FROM _head WHERE id = ?",
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
    // The arguments of the render calls of the error tests.
    render_arguments: '{"subtitle":"Fog."}',
    // The arguments of the image calls of the tests of failed calls.
    image_arguments: '{"prompt":"Fog.","key":"/_files/fog.png"}',
    // A prompt of the castle universe, for the tests of the system prompt.
    castle_prompt: "The castle is cold, and its keeper is patient.",
    // The reference string the encoded prompt document of the gold holds.
    lore: "/castle/lore",
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

  // What a tool double does with its arguments, and the result it gives.
  type ToolAnswer = (args: FieldTable) => mcp.ToolResult;

  // The tool doubles by their full name.
  type ToolTable = { [name: string]: ToolAnswer };

  // Each call a double was given: the method's name and its arguments.
  type CallRecord = [string, unknown[]];

  // The doubles the agent was registered with, and the handlers it gave.
  interface AgentBench {
    store: StoreDouble;
    clients: ClientsDouble;
    tasks: TasksDouble;
    handlers: Map<string, dispatch.Handler>;
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_agent.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_agent.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The answer the test set for the key, which must have been set.
  function answer_get<T>(answers: Map<string, T>, key: string): T {
    if (!answers.has(key)) {
      throw new Error(`The double has no answer for ${key}.`);
    }
    return answers.get(key) as T;
  }

  // The next id of the list the test chose, which must not be used up.
  function id_take(ids: number[], owner: string): number {
    const id = ids.shift();
    if (id === undefined) {
      throw new Error(`The ${owner} double has no id left.`);
    }
    return id;
  }

  // The arguments of each call of the method a double recorded, in order.
  function calls_of(calls: CallRecord[], name: string): unknown[][] {
    return calls.filter(([method]) => method === name).map(([, args]) => args);
  }

  // The key of a call of `sql_run`: its database and statements as JSON.
  function statement_key(
    db: string,
    statements: lines.SqlStatement[],
  ): string {
    return JSON.stringify([db, statements]);
  }

  // A double of the store: it keeps each call and answers what the test set.
  class StoreDouble {
    // Every call, in order.
    readonly calls: CallRecord[] = [];
    // The text of each value by its ref.
    readonly values = new Map<string, string>();
    // The head of each document by `db/id`, or the error asking it throws.
    readonly heads = new Map<string, lines.DocRef | Error>();
    // Each encoded document by its ref.
    readonly documents = new Map<string, lines.Document>();
    // The results of each call of `sql_run` by `statement_key`.
    readonly results = new Map<string, lines.SqlResult[]>();
    // The turns of each scene: those the test set, then those appended.
    readonly turns = new Map<string, substrate.TurnRow[]>();

    // The value's bytes, as a small value held in its row is read.
    kv_get(ref: lines.KvRef): { data: Uint8Array } {
      this.calls.push(["kv_get", [ref]]);
      return { data: new TextEncoder().encode(answer_get(this.values, ref)) };
    }

    // The head of the document, or the throw the test chose.
    doc_head(db: string, id: string): lines.DocRef {
      this.calls.push(["doc_head", [db, id]]);
      const head = answer_get(this.heads, `${db}/${id}`);
      if (head instanceof Error) {
        throw head;
      }
      return head;
    }

    // A copy of the encoded document under the ref.
    doc_get(ref: lines.DocRef): lines.Document {
      this.calls.push(["doc_get", [ref]]);
      return structuredClone(answer_get(this.documents, ref));
    }

    // The results the test set for the statements on the database.
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[] {
      this.calls.push(["sql_run", [db, statements]]);
      return structuredClone(
        answer_get(this.results, statement_key(db, statements)),
      );
    }

    // Keeps the turn on its scene, numbered after the scene's last.
    turn_append(
      scene: lines.DocRef,
      role: provider.Role,
      content: provider.ChatMessage,
    ): lines.TurnAppendReply {
      this.calls.push(["turn_append", [scene, role, content]]);
      const rows = answer_get(this.turns, scene);
      const n = rows.length + 1;
      rows.push({ scene, n, role, content });
      return { n };
    }

    // The turns of the scene, in order.
    turn_list(scene: lines.DocRef): substrate.TurnRow[] {
      this.calls.push(["turn_list", [scene]]);
      return structuredClone(answer_get(this.turns, scene));
    }

    // Runs the function, as the store runs it in one transaction.
    transaction_run<T>(fn: () => T): T {
      this.calls.push(["transaction_run", []]);
      return fn();
    }
  }

  // A double of the MCP clients: it lists tools and answers by its doubles.
  class ClientsDouble {
    // Every call, in order.
    readonly calls: CallRecord[] = [];
    // The tools it lists.
    readonly #tools: mcp.Tool[];
    // The tool doubles, run at the call.
    readonly #table: ToolTable;
    // The ids it hands out, in order.
    readonly #ids: number[];
    // The result of each call by its id.
    readonly #results = new Map<number, mcp.ToolResult>();

    // Takes the tools it lists, their doubles and the ids it hands out.
    constructor(tools: mcp.Tool[], table: ToolTable, ids: readonly number[]) {
      this.#tools = tools;
      this.#table = table;
      this.#ids = [...ids];
    }

    // The tools as listed.
    tools_cached(): mcp.Tool[] {
      this.calls.push(["tools_cached", []]);
      return this.#tools;
    }

    // Runs the tool's double and hands out the call's id.
    tool_call(name: string, args: FieldTable): number {
      this.calls.push(["tool_call", [name, args]]);
      if (!Object.hasOwn(this.#table, name)) {
        throw new Error(`The tool doubles have no tool ${name}.`);
      }
      const id = id_take(this.#ids, "clients");
      this.#results.set(id, this.#table[name](args));
      return id;
    }

    // The result of the call the reply answers, by the reply's `r`.
    result_of(reply: lines.Line): mcp.ToolResult {
      this.calls.push(["result_of", [reply]]);
      const id = reply[0].r;
      if (id === undefined || !this.#results.has(id)) {
        throw new Error(`The clients double made no call ${String(id)}.`);
      }
      return this.#results.get(id) as mcp.ToolResult;
    }
  }

  // A double of the task queue: it keeps each line submitted and its owner.
  class TasksDouble {
    // Every call, in order.
    readonly calls: CallRecord[] = [];
    // The ids it hands out, in order.
    readonly #ids: number[];

    // Takes the ids it hands out.
    constructor(ids: readonly number[]) {
      this.#ids = [...ids];
    }

    // Keeps the line and its owner and hands out the task's id.
    task_submit(line: lines.Line, owner: queue.ThreadName): number {
      this.calls.push(["task_submit", [line, owner]]);
      return id_take(this.#ids, "queue");
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
    properties: FieldTable,
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

  // The system prompt `prompt_build` makes on the store double.
  function prompt_of(store: StoreDouble): provider.ChatMessage[] {
    return agent.prompt_build(store as unknown as substrate.Store);
  }

  // A tool result of one text part.
  function text_result(text: string): mcp.ToolResult {
    return { content: [{ type: "text", text }] };
  }

  // A prompt document of the type given that holds the text given.
  function prompt_doc(type: string, text: unknown): lines.Document {
    return { 0: { t: type }, text };
  }

  // Answers the agent's lookup of the universe of the world with the names.
  function universe_set(
    store: StoreDouble,
    world: string,
    names: string[],
  ): void {
    const statement = { sql: constants.universe_sql, params: [world] };
    store.results.set(statement_key("metaverse", [statement]), [
      { columns: ["name"], rows: names.map((name) => [name]), changes: 0 },
    ]);
  }

  // Answers the agent's lookup of the head of the universe's prompt.
  function head_set(
    store: StoreDouble,
    universe: string,
    versions: number[],
  ): void {
    const statement = { sql: constants.head_sql, params: ["prompt"] };
    const rows = versions.map((version) => [version]);
    store.results.set(statement_key(universe, [statement]), [
      { columns: ["version"], rows, changes: 0 },
    ]);
  }

  // A store double in the hyperposition: its world, scene and the prompt.
  function store_seeded(): StoreDouble {
    const store = new StoreDouble();
    store.values.set("/metaverse/world", "metaverse");
    store.values.set("/metaverse/scene", constants.scene);
    store.heads.set("metaverse/prompt", constants.analyst_ref);
    const analyst = prompt_doc("prompt", constants.analyst);
    store.documents.set(constants.analyst_ref, analyst);
    universe_set(store, "metaverse", []);
    store.turns.set(constants.scene, []);
    return store;
  }

  // Makes the castle universe's world the current one.
  function castle_enter(store: StoreDouble): void {
    store.values.set("/metaverse/world", "castle_world");
    universe_set(store, "castle_world", ["castle"]);
  }

  // The tools of the castle turn: what each changes and the text it gives.
  function tools_recorded(store: StoreDouble): ToolTable {
    return {
      "browser.script_run": () => {
        castle_enter(store);
        return text_result(constants.bootstrap_result);
      },
      "browser.image_make": () => text_result(constants.image_result),
      "browser.doc_put": () => text_result(constants.scene_result),
      "browser.kv_put": (args: FieldTable) => {
        store.values.set(args.ref as string, args.text as string);
        return text_result(constants.enter_result);
      },
      "browser.render": () => text_result(constants.render_result),
    };
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

  // A bench of doubles on a store double, with the agent registered.
  function bench_make(
    tools_make: (store: StoreDouble) => ToolTable,
    info: lines.ProviderInfo,
  ): AgentBench {
    const store = store_seeded();
    const clients = new ClientsDouble(
      tools_listed(),
      tools_make(store),
      constants.call_ids,
    );
    const tasks = new TasksDouble(constants.request_ids);
    const handlers = new Map<string, dispatch.Handler>();
    agent.handlers_register(
      store as unknown as substrate.Store,
      clients as unknown as mcp.ClientSet,
      tasks as unknown as queue.TaskQueue,
      constants.provider_owner,
      info,
      (type: string, _version: number, fn: dispatch.Handler) => {
        handlers.set(type, fn);
      },
    );
    return { store, clients, tasks, handlers };
  }

  // A bench whose tool doubles are those of the castle turn.
  function bench_recorded(): AgentBench {
    const bench = bench_make(tools_recorded, constants.info);
    head_set(bench.store, "castle", []);
    bench.store.turns.set(constants.arrival, []);
    return bench;
  }

  // Calls the handler the agent registered for the type with the line.
  function handler_call(
    bench: AgentBench,
    type: string,
    line: lines.Line,
  ): ReturnType<dispatch.Handler> {
    const fn = bench.handlers.get(type);
    if (fn === undefined) {
      throw new Error(`The agent registered no handler for ${type}.`);
    }
    return fn(line);
  }

  // Whether a handler's outcome is a sleep, which names the type of its wake.
  function sleep_is(outcome: unknown): outcome is dispatch.Sleep {
    return (
      typeof outcome === "object" &&
      outcome !== null &&
      Object.hasOwn(outcome, "then_type")
    );
  }

  // The provider's answer to the request `id`: a completion of the message.
  function chat_reply(id: number, message: provider.ChatMessage): lines.Line {
    const line = gold_line("reply_chat");
    line[0].r = id;
    line.json = {
      id: constants.answer_id,
      model: constants.info.chat_model,
      choices: [{ index: 0, message, finish_reason: "stop" }],
    };
    return line;
  }

  // The clients' reply to the tool call `id`, whose result the double keeps.
  function tool_reply(id: number): lines.Line {
    const line = gold_line("reply_mcp");
    line[0].r = id;
    return line;
  }

  // The wake of a sleep: the model's next answer, or the tools' replies.
  function wake_next(
    sleep: dispatch.Sleep,
    left: provider.ChatMessage[],
  ): lines.Line {
    let wake: lines.Line;
    if (sleep.then_type === constants.model_type) {
      const answer = left.shift();
      if (answer === undefined) {
        throw new Error("The turn has no answer of the model left.");
      }
      wake = gold_line("wake_model");
      wake.replies = [chat_reply(sleep.wait_ids[0], answer)];
    } else if (sleep.then_type === constants.tool_type) {
      wake = gold_line("wake_tool");
      wake.replies = sleep.wait_ids.map((id) => tool_reply(id));
    } else {
      throw new Error(`The agent slept with the type ${sleep.then_type}.`);
    }
    wake.state = sleep.state;
    return wake;
  }

  // Runs a turn as a queue would, each sleep woken with what it waited for.
  function turn_run(
    bench: AgentBench,
    type: string,
    request: lines.Line,
    answers: provider.ChatMessage[],
  ): lines.Line {
    const left = [...answers];
    let outcome = handler_call(bench, type, request);
    while (sleep_is(outcome)) {
      const wake = wake_next(outcome, left);
      outcome = handler_call(bench, outcome.then_type, wake);
    }
    return outcome as lines.Line;
  }

  // Runs the castle turn, in which the player answers 1.
  function castle_run(bench: AgentBench): lines.Line {
    const say = gold_line("say_castle");
    return turn_run(bench, "ai.say", say, answers_recorded());
  }

  // The chat request the agent submits for the messages, on a gold frame.
  function request_expected(
    name: string,
    info: lines.ProviderInfo,
    messages: provider.ChatMessage[],
  ): lines.Line {
    const line = gold_line(name);
    line.json = {
      model: info.chat_model,
      messages,
      tools: functions_recorded(),
      tool_choice: "auto",
    };
    return line;
  }

  // The bodies of the chat requests the agent submitted, in order.
  function requests_of(bench: AgentBench): provider.ChatRequest[] {
    return calls_of(bench.tasks.calls, "task_submit").map(
      ([line]) => (line as lines.Line).json as provider.ChatRequest,
    );
  }

  // The contents of the turns the agent appended, in order.
  function contents_of(bench: AgentBench): unknown[] {
    return calls_of(bench.store.calls, "turn_append").map((args) => args[2]);
  }

  // An agent test, the provider key set.
  class AgentCase extends unittest.TestCase {
    // Sets the key every chat request carries.
    setUp(): void {
      provider.key_set(constants.key);
    }
  }

  // The castle turn: the player answers 1 and the analyst builds a scene.
  export class TestTurnRecorded extends AgentCase {
    // The four chat requests are the castle turn's, on the gold frame.
    test_requests_recorded(): void {
      const bench = bench_recorded();
      castle_run(bench);
      const expected = messages_recorded().map((messages) => [
        request_expected("request_chat", constants.info, messages),
        constants.provider_owner,
      ]);
      this.assertEqual(calls_of(bench.tasks.calls, "task_submit"), expected);
    }

    // Each call goes to the clients by its dotted name with its arguments.
    test_calls_recorded(): void {
      const bench = bench_recorded();
      castle_run(bench);
      const expected = calls_recorded().map((call: provider.ToolCall) => [
        call.function.name,
        JSON.parse(call.function.arguments) as unknown,
      ]);
      this.assertEqual(calls_of(bench.clients.calls, "tool_call"), expected);
    }

    // Every message of the turn is a turn of the scene, appended in order.
    test_turns_stored(): void {
      const bench = bench_recorded();
      castle_run(bench);
      const expected = contents_recorded();
      const appends = calls_of(bench.store.calls, "turn_append");
      this.assertEqual(
        appends,
        expected.map((message) => [constants.scene, message.role, message]),
      );
    }

    // The turn ends with the reply to `ai.say`: the new scene, the subtitle.
    test_reply_recorded(): void {
      const bench = bench_recorded();
      this.assertEqual(castle_run(bench), gold_line("reply_castle"));
    }
  }

  // The turn after the castle turn, in the scene that turn entered.
  export class TestTurnNext extends AgentCase {
    // The next turn is a new conversation, that of the arrival scene.
    test_scene_new(): void {
      const bench = bench_recorded();
      castle_run(bench);
      const moat = assistant_said(constants.moat_reply);
      const reply = turn_run(bench, "ai.say", gold_line("say_next"), [moat]);
      const requests = requests_of(bench);
      this.assertEqual(requests[requests.length - 1].messages, [
        system_said(constants.analyst),
        user_said("0"),
      ]);
      const arrived = calls_of(bench.store.calls, "turn_append").filter(
        ([scene]) => scene === constants.arrival,
      );
      this.assertEqual(
        arrived.map((args) => args[2]),
        [user_said("0"), moat],
      );
      this.assertEqual(reply, gold_line("reply_next"));
    }

    // The universe's prompt follows the analyst's once the scripts made one.
    test_universe_prompt(): void {
      const bench = bench_recorded();
      castle_run(bench);
      head_set(bench.store, "castle", [1]);
      const doc = prompt_doc("prompt", constants.castle_prompt);
      bench.store.documents.set("/castle/prompt/1", doc);
      const moat = assistant_said(constants.moat_reply);
      turn_run(bench, "ai.say", gold_line("say_next"), [moat]);
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
      const bench = bench_recorded();
      const nothing = assistant_said(constants.nothing_reply);
      const say = gold_line("say_full");
      const reply = turn_run(bench, "ai.say", say, [nothing]);
      this.assertEqual(contents_of(bench), [user_said("2"), nothing]);
      this.assertEqual(reply, gold_line("reply_full"));
    }

    // A click is told to the model as text, and the reply ends the turn.
    test_click_turn(): void {
      const bench = bench_recorded();
      const message = assistant_said(constants.click_reply);
      const click = gold_line("click");
      const reply = turn_run(bench, "ai.click", click, [message]);
      const said = user_said(gold_text("agent_click_text"));
      this.assertEqual(requests_of(bench)[0].messages, [
        system_said(constants.analyst),
        said,
      ]);
      this.assertEqual(contents_of(bench), [said, message]);
      this.assertEqual(reply, gold_line("reply_click"));
    }

    // The text parts of one tool result are joined by a line feed.
    test_texts_joined(): void {
      const call = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const tool_table = (): ToolTable => ({
        "browser.render": () => ({
          content: [
            { type: "text", text: "first" },
            { type: "text", text: "second" },
          ],
        }),
      });
      const bench = bench_make(tool_table, constants.info);
      const answers = [
        assistant_calls([call]),
        assistant_said(constants.nothing_reply),
      ];
      const say = gold_line("say_castle");
      const reply = turn_run(bench, "ai.say", say, answers);
      const messages = requests_of(bench)[1].messages;
      this.assertEqual(
        messages[messages.length - 1],
        tool_said(call, "first\nsecond"),
      );
      this.assertEqual(reply.subtitle, constants.nothing_reply);
    }

    // With a scripted run's empty information the request names no model.
    test_info_scripted(): void {
      const bench = bench_make(tools_recorded, constants.scripted_info);
      const nothing = assistant_said(constants.nothing_reply);
      const say = gold_line("say_nothing");
      const reply = turn_run(bench, "ai.say", say, [nothing]);
      const messages = [system_said(constants.analyst), user_said("2")];
      const expected = request_expected(
        "request_scripted",
        constants.scripted_info,
        messages,
      );
      this.assertEqual(calls_of(bench.tasks.calls, "task_submit"), [
        [expected, constants.provider_owner],
      ]);
      this.assertEqual(reply.subtitle, constants.nothing_reply);
    }
  }

  // The requests of a scene the store compacted and of one it kept whole.
  export class TestCompacted extends AgentCase {
    // A compacted scene goes to the model as listed: its summary, then more.
    test_request_compacted(): void {
      const bench = bench_recorded();
      const summary = system_said(gold_text("substrate_turns_compacted"));
      bench.store.turns.set(constants.scene, [
        { scene: constants.scene, n: 1, role: "system", content: summary },
      ]);
      const nothing = assistant_said(constants.nothing_reply);
      turn_run(bench, "ai.say", gold_line("say_nothing"), [nothing]);
      this.assertEqual(requests_of(bench)[0].messages, [
        system_said(constants.analyst),
        summary,
        user_said("2"),
      ]);
    }

    // A scene kept whole goes to the model with every turn it holds.
    test_request_whole(): void {
      const bench = bench_recorded();
      const nothing = assistant_said(constants.nothing_reply);
      turn_run(bench, "ai.say", gold_line("say_nothing"), [nothing]);
      turn_run(bench, "ai.say", gold_line("say_again"), [nothing]);
      this.assertEqual(requests_of(bench)[1].messages, [
        system_said(constants.analyst),
        user_said("2"),
        nothing,
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
      const bench = bench_make(tools_failing, constants.info);
      const say = gold_line("say_castle");
      const error = thrown_get(() =>
        turn_run(bench, "ai.say", say, [assistant_calls(calls)]),
      );
      this.assertEqual(
        error.message,
        gold_text("agent_content_unsupported_second"),
      );
      this.assertEqual(calls_of(bench.clients.calls, "tool_call").length, 2);
      this.assertEqual(contents_of(bench), [user_said("1")]);
    }

    // A call that cannot be made leaves the reply that names it unstored.
    test_call_unmade(): void {
      const call = call_make("call_1", "browser.render", "{");
      const bench = bench_recorded();
      const say = gold_line("say_castle");
      const error = thrown_get(() =>
        turn_run(bench, "ai.say", say, [assistant_calls([call])]),
      );
      this.assertEqual(
        error.message,
        gold_text("agent_arguments_invalid_unparsed"),
      );
      this.assertEqual(contents_of(bench), [user_said("1")]);
    }

    // An answered round stays stored with its results, the failed one not.
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
      const bench = bench_make(tools_failing, constants.info);
      const answers = [assistant_calls([render]), assistant_calls([image])];
      const say = gold_line("say_castle");
      const error = thrown_get(() => turn_run(bench, "ai.say", say, answers));
      this.assertEqual(
        error.message,
        gold_text("agent_content_unsupported_second"),
      );
      this.assertEqual(contents_of(bench), [
        user_said("1"),
        assistant_calls([render]),
        tool_said(render, constants.render_result),
      ]);
    }

    // The reply that calls a tool is stored with its result, after it ran.
    test_round_stored(): void {
      const render = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const seen: number[] = [];
      const tool_table = (store: StoreDouble): ToolTable => ({
        "browser.render": () => {
          seen.push(calls_of(store.calls, "turn_append").length);
          return text_result(constants.render_result);
        },
      });
      const bench = bench_make(tool_table, constants.info);
      const answers = [
        assistant_calls([render]),
        assistant_said(constants.nothing_reply),
      ];
      turn_run(bench, "ai.say", gold_line("say_castle"), answers);
      this.assertEqual(seen, [1]);
      this.assertEqual(contents_of(bench), [
        user_said("1"),
        assistant_calls([render]),
        tool_said(render, constants.render_result),
        assistant_said(constants.nothing_reply),
      ]);
    }
  }

  // The system prompt `prompt_build` makes.
  export class TestPrompt extends AgentCase {
    // In the hyperposition the system prompt is the analyst's alone.
    test_prompt_analyst(): void {
      const store = store_seeded();
      this.assertEqual(prompt_of(store), [system_said(constants.analyst)]);
    }

    // The prompt of the universe of the current world follows the analyst's.
    test_prompt_universe(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", [1]);
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store.documents.set("/castle/prompt/1", doc);
      this.assertEqual(prompt_of(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A universe without a prompt adds none.
    test_prompt_absent(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", []);
      this.assertEqual(prompt_of(store), [system_said(constants.analyst)]);
    }

    // The head of the universe's prompt is read, not an older version.
    test_prompt_head(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", [2]);
      const old = prompt_doc("prompt", "An old one.");
      store.documents.set("/castle/prompt/1", old);
      const doc = prompt_doc("prompt", constants.castle_prompt);
      store.documents.set("/castle/prompt/2", doc);
      this.assertEqual(prompt_of(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A prompt document of another type is read by its text all the same.
    test_prompt_typed(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", [1]);
      const note = prompt_doc("note", constants.castle_prompt);
      store.documents.set("/castle/prompt/1", note);
      this.assertEqual(prompt_of(store), [
        system_said(constants.analyst),
        system_said(constants.castle_prompt),
      ]);
    }

    // A prompt text that is a reference string is read back as that text.
    test_prompt_reference(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", [1]);
      const doc = gold_value("document_lore") as lines.Document;
      store.documents.set("/castle/prompt/1", doc);
      this.assertEqual(prompt_of(store), [
        system_said(constants.analyst),
        system_said(constants.lore),
      ]);
    }
  }

  // Every error the agent throws, compared with its message.
  export class TestErrors extends AgentCase {
    // Arguments that are not JSON end the turn, the decoder's error as cause.
    test_arguments_unparsed(): void {
      const call = call_make("call_1", "browser.render", "{");
      const bench = bench_recorded();
      const say = gold_line("say_castle");
      const error = thrown_get(() =>
        turn_run(bench, "ai.say", say, [assistant_calls([call])]),
      );
      this.assertEqual(
        error.message,
        gold_text("agent_arguments_invalid_unparsed"),
      );
      const cause = error.cause as Error;
      this.assertEqual(cause.constructor.name, "WireError");
      this.assertEqual(
        cause.message,
        gold_text("jslb_text_not_json").replaceAll("{0}", String(cause.cause)),
      );
      this.assertEqual(calls_of(bench.clients.calls, "tool_call").length, 0);
    }

    // Arguments holding a number that overflows a double end the turn.
    test_arguments_overflow(): void {
      const text = '{"subtitle":1e400}';
      const call = call_make("call_1", "browser.render", text);
      const bench = bench_recorded();
      const say = gold_line("say_castle");
      const error = thrown_get(() =>
        turn_run(bench, "ai.say", say, [assistant_calls([call])]),
      );
      this.assertEqual(
        error.message,
        gold_text("agent_arguments_invalid_overflow"),
      );
      const cause = error.cause as Error;
      this.assertEqual(cause.constructor.name, "WireError");
      this.assertEqual(cause.message, gold_text("jslb_number_overflow"));
      this.assertEqual(calls_of(bench.clients.calls, "tool_call").length, 0);
    }

    // Arguments that are JSON but not an object end the turn.
    test_arguments_invalid(): void {
      const cases = [
        ["[]", "array"],
        ["null", "null"],
        ["5", "number"],
        ['"Fog."', "string"],
      ];
      for (const [text, name] of cases) {
        const call = call_make("call_1", "browser.render", text);
        const bench = bench_recorded();
        const say = gold_line("say_castle");
        const error = thrown_get(() =>
          turn_run(bench, "ai.say", say, [assistant_calls([call])]),
        );
        this.assertEqual(
          error.message,
          gold_text(`agent_arguments_invalid_${name}`),
        );
      }
    }

    // A reply with neither tool calls nor content ends the turn.
    test_reply_empty(): void {
      const bench = bench_recorded();
      const empty: provider.ChatMessage = { role: "assistant", content: null };
      const say = gold_line("say_castle");
      const error = thrown_get(() => turn_run(bench, "ai.say", say, [empty]));
      this.assertEqual(error.message, gold_text("agent_reply_empty"));
      this.assertEqual(contents_of(bench), [user_said("1")]);
    }

    // A tool result holding an image ends the turn.
    test_content_unsupported(): void {
      const call = call_make(
        "call_1",
        "browser.render",
        constants.render_arguments,
      );
      const tool_table = (): ToolTable => ({
        "browser.render": () => ({
          content: [{ type: "image", data: "", mimeType: "image/png" }],
        }),
      });
      const bench = bench_make(tool_table, constants.info);
      const say = gold_line("say_castle");
      const error = thrown_get(() =>
        turn_run(bench, "ai.say", say, [assistant_calls([call])]),
      );
      this.assertEqual(
        error.message,
        gold_text("agent_content_unsupported_first"),
      );
    }

    // A prompt text not a string throws, the universe's or the analyst's.
    test_prompt_invalid(): void {
      const store = store_seeded();
      castle_enter(store);
      head_set(store, "castle", [1]);
      const number = prompt_doc("prompt", 5);
      store.documents.set("/castle/prompt/1", number);
      const first = thrown_get(() => prompt_of(store));
      this.assertEqual(
        first.message,
        gold_text("agent_prompt_invalid_universe"),
      );
      store.heads.set("metaverse/prompt", "/metaverse/prompt/2");
      store.documents.set("/metaverse/prompt/2", number);
      const second = thrown_get(() => prompt_of(store));
      this.assertEqual(
        second.message,
        gold_text("agent_prompt_invalid_analyst"),
      );
    }

    // The store's error for a missing analyst's prompt reaches the caller.
    test_analyst_missing(): void {
      const store = store_seeded();
      const missing = new Error(gold_text("substrate_id_missing"));
      store.heads.set("metaverse/prompt", missing);
      const error = thrown_get(() => prompt_of(store));
      this.assertEqual(error, missing);
      this.assertEqual(error.message, gold_text("substrate_id_missing"));
    }

    // An `error` line in answer to the chat request is no chat completion.
    test_error_line(): void {
      const bench = bench_recorded();
      const outcome = handler_call(bench, "ai.say", gold_line("say_nothing"));
      this.assertTrue(sleep_is(outcome));
      const sleep = outcome as dispatch.Sleep;
      const failure = new Error("Unauthorized");
      const line = gold_line("error_unauthorized");
      Object.assign(line[0], { reply: sleep.wait_ids[0] });
      line.stack = failure.stack;
      const wake = gold_line("wake_model");
      wake.state = sleep.state;
      wake.replies = [line];
      const error = thrown_get(() =>
        handler_call(bench, constants.model_type, wake),
      );
      this.assertEqual(error.message, gold_text("provider_reply_type"));
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
      const seen: [string, number][] = [];
      agent.handlers_register(
        store_seeded() as unknown as substrate.Store,
        new ClientsDouble([], {}, []) as unknown as mcp.ClientSet,
        new TasksDouble([]) as unknown as queue.TaskQueue,
        constants.provider_owner,
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
