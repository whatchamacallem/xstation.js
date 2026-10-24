// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of tools_browser.ts on doubles: a server double that keeps the tools
// and wakes registered on it, a store double and its cache double that keep
// every call and give the answers each test chose, a queue double that keeps
// what the tools send and gives the ids the test picked, and a settings
// reader of harness.setting_get. They check the tools in the order and texts
// of API/mcp/tools.json, the result of every tool on the store's answers and
// the calls it made of the store, every line a tool sends against the gold
// record in full names, the results of the wakes for the castle turn's image
// and render, a console command shown first as ctrl 0 shows it, the step
// script, the store's error for a lost cache file passed on, and every
// error. The inputs and digests are those of test_digests.json. The provider
// key is set by provider.key_set, which keeps it.

namespace test_tools_browser {
  // The vectors the test page carries, each file's bytes in base64.
  declare const test_vectors: { readonly [name: string]: string };

  // Finishes a tool's result from the state and replies of its wake.
  type WakeFinish = (
    state: unknown,
    replies: lines.Line[],
  ) => mcp.ToolResult | dispatch.Sleep;

  // A line a tool sent: the line, its owner and, for a request, its id.
  interface SentLine {
    line: lines.Line;
    owner: queue.ThreadName | undefined;
    id: number | undefined;
  }

  // What a double gives for one call: the value the test chose, or a throw.
  type Answer = { value: unknown } | { error: Error };

  // One call a double was given: the method's name and its arguments.
  type Call = [string, unknown[]];

  // An input of the digest vector and its `SHA-256`.
  interface DigestEntry {
    data: Uint8Array;
    sha256: string;
  }

  // The doubles one test registers the tools on.
  interface ToolBench {
    store: StoreDouble;
    server: ServerDouble;
    tasks: TasksDouble;
  }

  // The names, texts and data the tests use.
  const constants = Object.freeze({
    // The id of this module's gold in `test_settings.json`.
    gold_id: "typescript.test_tools_browser",
    // The file of the digest vectors and this module's object in it.
    digests_name: "test_digests.json",
    digests_module: "test_tools_browser",
    // The store's methods the tools and the script module call or bind.
    store_methods: Object.freeze<readonly string[]>([
      "sql_run",
      "db_list",
      "db_create",
      "db_drop",
      "kv_get",
      "kv_put",
      "kv_delete",
      "kv_list",
      "doc_get",
      "doc_put",
      "doc_head",
      "turn_append",
      "turn_list",
      "turn_compact",
      "transaction_run",
      "sink",
    ]),
    // The handle the store double gives for a value held in the cache.
    cache_handle: "cache/0001",
    // A synthetic provider key, which every image request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // The owner the image requests go to.
    provider_owner: "http" as const,
    // The tools of `tools/list` as `API/mcp/tools.json` holds them.
    recorded_tools: Object.freeze<readonly string[]>([
      '{"name":"sql_run","description":"Run SQL statements in one' +
        " transaction on a database. DDL is allowed: your scripts are the" +
        ' database administrator.","inputSchema":{"type":"object",' +
        '"properties":{"db":{"type":"string"},"statements":{"type":"array",' +
        '"items":{"type":"object","properties":{"sql":{"type":"string"},' +
        '"params":{"type":"array"}},"required":["sql","params"]}}},' +
        '"required":["db","statements"]}}',
      '{"name":"db_create","description":"Create an empty database. The' +
        ' name is a C identifier.","inputSchema":{"type":"object",' +
        '"properties":{"db":{"type":"string"}},"required":["db"]}}',
      '{"name":"db_drop","description":"Delete a database and everything' +
        ' in it.","inputSchema":{"type":"object","properties":{"db":' +
        '{"type":"string"}},"required":["db"]}}',
      '{"name":"kv_get","description":"Read the value a Key-Value-Ref' +
        ' names, /$db/$key, as text.","inputSchema":{"type":"object",' +
        '"properties":{"ref":{"type":"string"}},"required":["ref"]}}',
      '{"name":"kv_put","description":"Write text under a Key-Value-Ref,' +
        " /$db/$key, and return its sha256. A script is the row" +
        ' /_files/script/<name>.js.",' +
        '"inputSchema":{"type":"object","properties":{"ref":' +
        '{"type":"string"},"text":{"type":"string"}},"required":' +
        '["ref","text"]}}',
      '{"name":"kv_delete","description":"Delete the row a Key-Value-Ref' +
        ' names.","inputSchema":{"type":"object","properties":{"ref":' +
        '{"type":"string"}},"required":["ref"]}}',
      '{"name":"kv_list","description":"List the keys of a database under' +
        ' a prefix with sizes and hashes.","inputSchema":{"type":"object",' +
        '"properties":{"db":{"type":"string"},"prefix":{"type":"string"}},' +
        '"required":["db","prefix"]}}',
      '{"name":"doc_get","description":"Read a document by Document-Ref,' +
        " /$db/$id/$version, in its encoded form: header 0, references at" +
        ' 1 on, {\\"$ref\\": n} in the body.","inputSchema":' +
        '{"type":"object","properties":{"ref":{"type":"string"}},' +
        '"required":["ref"]}}',
      '{"name":"doc_put","description":"Write a new version of document' +
        " $id in database $db and move its head. Returns the new" +
        ' Document-Ref.","inputSchema":{"type":"object","properties":' +
        '{"db":{"type":"string"},"id":{"type":"string"},"body":' +
        '{"type":"object"}},"required":["db","id","body"]}}',
      '{"name":"doc_head","description":"The current Document-Ref of' +
        ' document $id in database $db.","inputSchema":{"type":"object",' +
        '"properties":{"db":{"type":"string"},"id":{"type":"string"}},' +
        '"required":["db","id"]}}',
      '{"name":"script_run","description":"Run the script' +
        " /_files/script/<name>.js with args as a task in this worker." +
        " Returns its value or exception and the verbose lines it" +
        ' wrote.","inputSchema":{"type":"object","properties":{"name":' +
        '{"type":"string"},"args":{"type":"object"}},"required":' +
        '["name","args"]}}',
      '{"name":"script_debug","description":"Run the script as' +
        " script_run does, tracing every substrate call it makes" +
        ' first.","inputSchema":{"type":"object","properties":{"name":' +
        '{"type":"string"},"args":{"type":"object"}},"required":' +
        '["name","args"]}}',
      '{"name":"image_make","description":"Generate an image from a' +
        " prompt and keep it under /_files/<key>. Returns the key, size" +
        ' and sha256.","inputSchema":{"type":"object","properties":' +
        '{"prompt":{"type":"string"},"key":{"type":"string"}},' +
        '"required":["prompt","key"]}}',
      '{"name":"render","description":"Show an image by its' +
        ' Key-Value-Ref with a subtitle. No image means black.",' +
        '"inputSchema":{"type":"object","properties":{"image":' +
        '{"type":"string"},"subtitle":{"type":"string"}},"required":' +
        '["subtitle"]}}',
      '{"name":"console_run","description":"Show the debug console as' +
        " ctrl-0 does, run one command line in its dash and return its" +
        " output until the next prompt or the timeout. Debug mode." +
        '","inputSchema":' +
        '{"type":"object","properties":{"text":{"type":"string"},' +
        '"timeout_seconds":{"type":"number"}},"required":' +
        '["text","timeout_seconds"]},"_meta":{"xsjs":{"permit":true}}}',
      '{"name":"verbose_tail","description":"The last lines of a' +
        ' thread\'s verbose ring: ui, ai or server.","inputSchema":' +
        '{"type":"object","properties":{"thread":{"type":"string"},' +
        '"count":{"type":"integer"}},"required":["thread","count"]}}',
    ]),
    // The wake types the tools sleep with.
    wake_types: [
      "tools.image_reply",
      "tools.media_reply",
      "tools.fetch_reply",
      "tools.render_reply",
      "tools.permit_reply",
      "tools.console_reply",
      "tools.tail_reply",
      "tools.show_reply",
    ],
    // The world table of the castle universe.
    world_sql:
      "CREATE TABLE world" +
      " (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT",
    // The result of the castle's two statements.
    castle_reply:
      '{"results":[{"columns":[],"rows":[],"changes":0},' +
      '{"columns":[],"rows":[],"changes":1}]}',
    // The ref of the arrival scene of the castle turn.
    arrival_ref: "/castle_gatehouse/scene/arrival/1",
    // The result of `doc_put` for the arrival scene, its first version.
    doc_result: '{"ref":"/castle_gatehouse/scene/arrival/1"}',
    // The subtitle of the arrival scene of the castle turn.
    arrival_subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The ref of the step script, which advances the tide of a region.
    step_ref: "/_files/script/step_tide.js",
    // The line the step script logs when it advances the tide by 1.
    step_line: "tide advanced by 1",
    // The arguments of the step script's call of the store, as JSON.
    step_arguments:
      '["castle_world",[{"sql":"UPDATE region SET tide = tide + ?' +
      ' WHERE name = ?","params":[1,"castle_gatehouse"]}]]',
    // The prompt of the image the castle turn makes.
    image_prompt:
      "A rain dark castle gatehouse at dusk seen from the far side of a" +
      " moat, one lantern lit, painted, wide still frame, no people",
    // The key in `_files` of that image.
    image_key: "gatehouse/arrival.png",
    // The ref of that image.
    image_ref: "/_files/gatehouse/arrival.png",
    // The body of the image request of the castle turn.
    image_json:
      '{"model":"grok-2-image","prompt":"A rain dark castle gatehouse at' +
      " dusk seen from the far side of a moat, one lantern lit, painted," +
      ' wide still frame, no people","n":1,"response_format":"b64_json"}',
    // The subtitle of the hyperposition, the scene the boot renders.
    hyperposition_subtitle: "How can I help you?",
    // The input message of ttyd's protocol that types `echo hi`.
    console_input: "0echo hi\n",
    // The result of `console_run` for the output of `echo hi`, trimmed.
    console_result: '{"output":"hi\\n","timed_out":false}',
  });

  // The stored text of the arrival scene, its encoded document as JSON.
  const arrival_text =
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"' +
    constants.arrival_subtitle +
    '","image":{"$ref":1}}';

  // This module's object of the digest vector, parsed at the first read.
  let digests: { [name: string]: unknown } | undefined = undefined;

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

  // A copy of a reply line of the gold, to the request of the id.
  function reply_gold(name: string, id: number): lines.Line {
    const line = gold_line(name);
    line[0].r = id;
    return line;
  }

  // This module's object of the digest vector the test page carries.
  function digests_read(): { [name: string]: unknown } {
    if (digests === undefined) {
      const name = constants.digests_name;
      if (!Object.hasOwn(test_vectors, name)) {
        throw new Error(`test_vectors has no file ${name}`);
      }
      const file = Uint8Array.from(atob(test_vectors[name]), (c) =>
        c.charCodeAt(0),
      );
      const vector = JSON.parse(text_decode(file)) as {
        [module: string]: { [name: string]: unknown };
      };
      if (!Object.hasOwn(vector, constants.digests_module)) {
        throw new Error(`${name} has no object ${constants.digests_module}`);
      }
      digests = vector[constants.digests_module];
    }
    return digests;
  }

  // The input and the digest of an entry of this module's digest vector.
  function digest_entry(name: string): DigestEntry {
    const entries = digests_read();
    if (!Object.hasOwn(entries, name)) {
      throw new Error(`${constants.digests_name} has no entry ${name}`);
    }
    const entry = entries[name] as { data: string; sha256: string };
    const data = new Uint8Array(entry.data.length / 2);
    for (let index = 0; index < data.length; index += 1) {
      const pair = entry.data.slice(2 * index, 2 * index + 2);
      data[index] = Number.parseInt(pair, 16);
    }
    return { data, sha256: entry.sha256 };
  }

  // The text of strict `UTF-8` bytes.
  function text_decode(data: Uint8Array): string {
    return new TextDecoder("utf-8", { fatal: true }).decode(data);
  }

  // The base64 text of bytes, as a provider's answer carries an image.
  function base64_encode(data: Uint8Array): string {
    const text = Array.from(data, (byte) => String.fromCharCode(byte));
    return btoa(text.join(""));
  }

  // The value the store double gives for an input of the digest vector.
  function value_answer(entry: DigestEntry): Answer {
    const { data, sha256 } = entry;
    return { value: { data, size: data.length, sha256 } };
  }

  // The row of an input of the digest vector kept under the key.
  function row_make(k: string, entry: DigestEntry): lines.KvRow {
    return { k, size: entry.data.length, sha256: entry.sha256 };
  }

  // The result of `image_make` for the image of the digest vector.
  function image_result(image: DigestEntry): string {
    const { image_ref } = constants;
    const size = image.data.length;
    return JSON.stringify({ key: image_ref, size, sha256: image.sha256 });
  }

  // The line of the gold that types a message into tty 0, its blob set.
  function input_line(typed: string): lines.Line {
    const data = new TextEncoder().encode(typed);
    const line = gold_line("console_input");
    line[1] = { size: data.length, d: data };
    return line;
  }

  // A settings reader: the test's own values for some ids, else the harness.
  function reader_make(values: {
    [id: string]: unknown;
  }): (id: string) => unknown {
    return (id: string) =>
      Object.hasOwn(values, id) ? values[id] : harness.setting_get(id);
  }

  // The text of each line, which leaves out the time.
  function lines_shown(kept: lines.VerboseLine[]): string[] {
    return kept.map((line) => line.text);
  }

  // Keeps each call and gives the next answer the test added for its method.
  class CallDouble {
    // The calls, in order.
    readonly calls: Call[] = [];
    // The answers not yet given, by method.
    readonly #answers = new Map<string, Answer[]>();

    // Adds the answer of a later call of the method, after those added.
    answer_add(name: string, answer: Answer): void {
      const left = this.#answers.get(name);
      if (left === undefined) {
        this.#answers.set(name, [answer]);
      } else {
        left.push(answer);
      }
    }

    // Keeps the call and gives its answer, or throws when none is left.
    call_answer(name: string, values: unknown[]): unknown {
      this.calls.push([name, values]);
      const left = this.#answers.get(name);
      const answer = left === undefined ? undefined : left.shift();
      if (answer === undefined) {
        throw new Error(`the double has no answer for a call of ${name}`);
      }
      if ("error" in answer) {
        throw answer.error;
      }
      return answer.value;
    }
  }

  // A store double with every method the tools and the script module call.
  class StoreDouble extends CallDouble {
    // Makes each method of the store keep its call and give its answer.
    constructor() {
      super();
      const methods = this as unknown as { [name: string]: unknown };
      for (const name of constants.store_methods) {
        methods[name] = (...values: unknown[]): unknown =>
          this.call_answer(name, values);
      }
    }
  }

  // A cache double: `cache_read`, the one call the tools make of the cache.
  class CacheDouble extends CallDouble {
    // Keeps the call and gives the bytes the test chose.
    cache_read(handle: string, offset: number, length: number): unknown {
      return this.call_answer("cache_read", [handle, offset, length]);
    }
  }

  // A server double that keeps the tools and the wakes registered on it.
  class ServerDouble {
    // The tools, in the order they were registered.
    readonly tools: mcp.Tool[] = [];
    // The function of each tool, by name.
    readonly runs = new Map<string, mcp.ToolFn>();
    // The function of each wake, by type.
    readonly wakes = new Map<string, WakeFinish>();

    // Keeps a tool and its function.
    tool_register(tool: mcp.Tool, fn: mcp.ToolFn): void {
      this.tools.push(tool);
      this.runs.set(tool.name, fn);
    }

    // Keeps a wake type and its function.
    wake_register(then_type: string, fn: WakeFinish): void {
      this.wakes.set(then_type, fn);
    }
  }

  // A queue double that keeps each line and gives the ids the test picked.
  class TasksDouble {
    // The lines sent, in order.
    readonly sent: SentLine[] = [];
    // The ids not yet given, in the order the requests get them.
    readonly #ids: number[];

    // Keeps the ids the test picked for the requests to come.
    constructor(ids: number[]) {
      this.#ids = [...ids];
    }

    // Keeps a request and gives it the next id, or throws when none is left.
    task_submit(line: lines.Line, owner?: queue.ThreadName): number {
      const id = this.#ids.shift();
      if (id === undefined) {
        throw new Error("the queue double has no id left for a request");
      }
      this.sent.push({ line, owner, id });
      return id;
    }

    // Keeps a notification.
    line_notify(line: lines.Line, owner?: queue.ThreadName): void {
      this.sent.push({ line, owner, id: undefined });
    }
  }

  // A tool test: the provider key set, the tools on new doubles.
  class ToolCase extends unittest.TestCase {
    // Sets the provider key, which the image requests carry.
    setUp(): void {
      provider.key_set(constants.key);
    }

    // The tools registered on new doubles, the queue giving the ids picked.
    bench_make(
      ids: number[],
      values: { [id: string]: unknown } = {},
    ): ToolBench {
      const store = new StoreDouble();
      const server = new ServerDouble();
      const tasks = new TasksDouble(ids);
      tools_browser.tools_register(
        server as unknown as mcp.Server,
        store as unknown as substrate.Store,
        tasks as unknown as queue.TaskQueue,
        constants.provider_owner,
        constants.info,
        reader_make(values),
      );
      return { store, server, tasks };
    }

    // Runs a tool by name on its arguments.
    tool_run(
      bench: ToolBench,
      name: string,
      args: { [key: string]: unknown },
    ): mcp.ToolResult | dispatch.Sleep {
      const fn = bench.server.runs.get(name) as mcp.ToolFn;
      return fn(args);
    }

    // Runs the wake a sleep names with the replies it waited for.
    wake_run(
      bench: ToolBench,
      sleep: dispatch.Sleep,
      replies: lines.Line[],
    ): mcp.ToolResult | dispatch.Sleep {
      const fn = bench.server.wakes.get(sleep.then_type) as WakeFinish;
      return fn(sleep.state, replies);
    }

    // The result a tool or a wake returned, which must be no sleep.
    result_of(value: mcp.ToolResult | dispatch.Sleep): mcp.ToolResult {
      this.assertTrue("content" in value, "a result was expected");
      return value as mcp.ToolResult;
    }

    // The text of a result that holds one text block and is no error.
    text_of(value: mcp.ToolResult | dispatch.Sleep): string {
      const result = this.result_of(value);
      this.assertFalse("isError" in result);
      this.assertEqual(result.content.length, 1);
      const block = result.content[0];
      this.assertEqual(block.type, "text");
      return (block as { type: "text"; text: string }).text;
    }

    // A sleep of the type, waiting on exactly the requests sent from `start`.
    sleep_check(
      bench: ToolBench,
      value: mcp.ToolResult | dispatch.Sleep,
      start: number,
      then_type: string,
    ): dispatch.Sleep {
      this.assertTrue("then_type" in value, "a sleep was expected");
      const sleep = value as dispatch.Sleep;
      this.assertEqual(sleep.then_type, then_type);
      const ids = bench.tasks.sent
        .slice(start)
        .filter((entry) => entry.id !== undefined)
        .map((entry) => entry.id);
      this.assertEqual(sleep.wait_ids, ids);
      return sleep;
    }

    // Asserts the call throws a plain `Error` with exactly the message.
    raised_assert(message: string, fn: () => unknown): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === Error) {
          this.assertEqual(error.message, message);
          return;
        }
        throw error;
      }
      this.fail("Error not raised");
    }

    // Gives the store's answers for reading a script of the digest vector.
    script_answer(bench: ToolBench, entry: DigestEntry): void {
      bench.store.answer_add("kv_get", value_answer(entry));
      bench.store.answer_add("sink", { value: new CacheDouble() });
    }
  }

  // The tools and the wakes registered on the server.
  export class TestRegistry extends ToolCase {
    // The tools are those of `API/mcp/tools.json`, whole and in its order.
    test_tools_recorded(): void {
      const bench = this.bench_make([]);
      const recorded = constants.recorded_tools.map(
        (text) => JSON.parse(text) as mcp.Tool,
      );
      this.assertEqual(recorded.length, 16);
      this.assertEqual(
        JSON.stringify(bench.server.tools),
        JSON.stringify(recorded),
      );
    }

    // Every tool has its function, and every wake type has its function.
    test_functions_registered(): void {
      const bench = this.bench_make([]);
      const names = bench.server.tools.map((tool) => tool.name);
      this.assertEqual([...bench.server.runs.keys()], names);
      for (const fn of bench.server.runs.values()) {
        this.assertEqual(typeof fn, "function");
      }
      this.assertEqual(
        [...bench.server.wakes.keys()].sort(),
        [...constants.wake_types].sort(),
      );
      for (const fn of bench.server.wakes.values()) {
        this.assertEqual(typeof fn, "function");
      }
    }
  }

  // The tools of SQL and of creating and dropping databases.
  export class TestDatabases extends ToolCase {
    // `sql_run` runs the statements on the store and answers its results.
    test_sql_recorded(): void {
      const bench = this.bench_make([]);
      const statements = [
        { sql: constants.world_sql, params: [] },
        {
          sql: "INSERT INTO world VALUES (?, ?)",
          params: ["castle_world", "The castle"],
        },
      ];
      const results = [
        { columns: [], rows: [], changes: 0 },
        { columns: [], rows: [], changes: 1 },
      ];
      bench.store.answer_add("sql_run", { value: results });
      const result = this.tool_run(bench, "sql_run", {
        db: "castle",
        statements,
      });
      this.assertEqual(this.text_of(result), constants.castle_reply);
      this.assertEqual(bench.store.calls, [
        ["sql_run", ["castle", statements]],
      ]);
    }

    // `db_create` and `db_drop` add and remove a database.
    test_create_drop(): void {
      const bench = this.bench_make([]);
      bench.store.answer_add("db_create", { value: undefined });
      bench.store.answer_add("db_drop", { value: undefined });
      const created = this.tool_run(bench, "db_create", { db: "alpha" });
      this.assertEqual(this.text_of(created), "{}");
      const dropped = this.tool_run(bench, "db_drop", { db: "alpha" });
      this.assertEqual(this.text_of(dropped), "{}");
      this.assertEqual(bench.store.calls, [
        ["db_create", ["alpha"]],
        ["db_drop", ["alpha"]],
      ]);
    }
  }

  // The tools of values: put, get, delete and list.
  export class TestValues extends ToolCase {
    // `kv_put` writes the text's bytes and returns the row's digest.
    test_put_recorded(): void {
      const bench = this.bench_make([]);
      const cases: [string, string, string][] = [
        ["/metaverse/world", "world", "castle_world"],
        ["/castle_world/scene", "scene", "arrival_ref"],
        [constants.step_ref, "script/step_tide.js", "step_script"],
      ];
      for (const [ref, key, name] of cases) {
        const entry = digest_entry(name);
        bench.store.answer_add("kv_put", { value: row_make(key, entry) });
        const text = text_decode(entry.data);
        const result = this.tool_run(bench, "kv_put", { ref, text });
        const sha256 = entry.sha256;
        this.assertEqual(this.text_of(result), JSON.stringify({ sha256 }));
      }
      const puts = cases.map(([ref, , name]) => [
        "kv_put",
        [ref, digest_entry(name).data],
      ]);
      this.assertEqual(bench.store.calls, puts);
    }

    // `kv_get` reads a value as its text.
    test_get_text(): void {
      const bench = this.bench_make([]);
      const entry = digest_entry("text_wide");
      bench.store.answer_add("kv_get", value_answer(entry));
      bench.store.answer_add("sink", { value: new CacheDouble() });
      const result = this.tool_run(bench, "kv_get", { ref: "/alpha/a" });
      const text = String.fromCodePoint(0x4e2d, 0x6587, 0x1f600) + " text";
      this.assertEqual(this.text_of(result), text);
      this.assertEqual(bench.store.calls, [
        ["kv_get", ["/alpha/a"]],
        ["sink", []],
      ]);
    }

    // `kv_get` reads a value held in the cache through its handle.
    test_get_cached(): void {
      const bench = this.bench_make([]);
      const { data, sha256 } = digest_entry("value_cached");
      const cache = new CacheDouble();
      cache.answer_add("cache_read", { value: data });
      const handle = constants.cache_handle;
      const value = { data: handle, size: data.length, sha256 };
      bench.store.answer_add("kv_get", { value });
      bench.store.answer_add("sink", { value: cache });
      const result = this.tool_run(bench, "kv_get", { ref: "/alpha/big" });
      this.assertEqual(this.text_of(result), text_decode(data));
      const read = ["cache_read", [handle, 0, data.length]];
      this.assertEqual(cache.calls, [read]);
    }

    // `kv_get` of bytes that are not `UTF-8` throws.
    test_get_refused(): void {
      const bench = this.bench_make([]);
      bench.store.answer_add("kv_get", value_answer(digest_entry("byte_ff")));
      bench.store.answer_add("sink", { value: new CacheDouble() });
      this.raised_assert(gold_text("utility_bytes_refused"), () =>
        this.tool_run(bench, "kv_get", { ref: "/alpha/raw" }),
      );
    }

    // `kv_delete` deletes the row and returns an empty object.
    test_delete_empty(): void {
      const bench = this.bench_make([]);
      bench.store.answer_add("kv_delete", { value: undefined });
      const result = this.tool_run(bench, "kv_delete", { ref: "/alpha/a" });
      this.assertEqual(this.text_of(result), "{}");
      this.assertEqual(bench.store.calls, [["kv_delete", ["/alpha/a"]]]);
    }

    // The store's throw for a value whose cache file is lost passes through.
    test_file_lost(): void {
      const bench = this.bench_make([]);
      const cases: [string, string, string][] = [
        ["kv_get", "/alpha/big", "value"],
        ["doc_get", "/alpha/note/1", "document"],
      ];
      for (const [tool, lost, name] of cases) {
        const sha256 = digest_entry(`${name}_lost`).sha256;
        const text = gold_text(`substrate_file_lost_${name}`);
        const message = text.replaceAll("{1}", sha256);
        bench.store.answer_add(tool, { error: new Error(message) });
        this.raised_assert(message, () =>
          this.tool_run(bench, tool, { ref: lost }),
        );
      }
      this.assertEqual(bench.store.calls, [
        ["kv_get", ["/alpha/big"]],
        ["doc_get", ["/alpha/note/1"]],
      ]);
      this.assertEqual(bench.tasks.sent, []);
    }

    // `kv_list` returns the rows under the prefix.
    test_list_keys(): void {
      const bench = this.bench_make([]);
      const keys = [
        row_make("note/a", digest_entry("note_a")),
        row_make("note/b", digest_entry("note_b")),
      ];
      bench.store.answer_add("kv_list", { value: keys });
      const result = this.tool_run(bench, "kv_list", {
        db: "alpha",
        prefix: "note/",
      });
      this.assertEqual(this.text_of(result), JSON.stringify({ keys }));
      this.assertEqual(bench.store.calls, [["kv_list", ["alpha", "note/"]]]);
    }
  }

  // The tools of documents.
  export class TestDocuments extends ToolCase {
    // The arrival scene is put, read back as its stored text, and found.
    test_doc_recorded(): void {
      const bench = this.bench_make([]);
      const body = JSON.parse(arrival_text) as lines.Document;
      const where = { db: "castle_gatehouse", id: "scene/arrival" };
      const ref = constants.arrival_ref;
      bench.store.answer_add("doc_put", { value: { ref } });
      bench.store.answer_add("doc_get", { value: JSON.parse(arrival_text) });
      bench.store.answer_add("doc_head", { value: ref });
      const put = this.tool_run(bench, "doc_put", { ...where, body });
      this.assertEqual(this.text_of(put), constants.doc_result);
      const read = this.tool_run(bench, "doc_get", { ref });
      this.assertEqual(this.text_of(read), arrival_text);
      const head = this.tool_run(bench, "doc_head", where);
      this.assertEqual(this.text_of(head), constants.doc_result);
      this.assertEqual(bench.store.calls, [
        ["doc_put", [where.db, where.id, body]],
        ["doc_get", [ref]],
        ["doc_head", [where.db, where.id]],
      ]);
    }
  }

  // The tools that run scripts.
  export class TestScripts extends ToolCase {
    // The step script reads its text, runs its statement, returns its line.
    test_run_recorded(): void {
      const bench = this.bench_make([]);
      this.script_answer(bench, digest_entry("step_script"));
      const changed = [{ columns: [], rows: [], changes: 1 }];
      bench.store.answer_add("sql_run", { value: changed });
      const result = this.tool_run(bench, "script_run", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(Object.keys(run), ["value", "lines"]);
      this.assertEqual(run.value, { changes: 1 });
      this.assertEqual(lines_shown(run.lines), [constants.step_line]);
      this.assertEqual(bench.store.calls, [
        ["kv_get", [constants.step_ref]],
        ["sink", []],
        ["sql_run", JSON.parse(constants.step_arguments)],
      ]);
    }

    // `script_debug` traces the store's call before the script's line.
    test_debug_traced(): void {
      const bench = this.bench_make([]);
      this.script_answer(bench, digest_entry("step_script"));
      const changed = [{ columns: [], rows: [], changes: 1 }];
      bench.store.answer_add("sql_run", { value: changed });
      const result = this.tool_run(bench, "script_debug", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(run.value, { changes: 1 });
      const trace = gold_text("script_trace_call");
      this.assertEqual(lines_shown(run.lines), [trace, constants.step_line]);
      const statement = JSON.parse(constants.step_arguments) as unknown[];
      this.assertEqual(bench.store.calls[2], ["sql_run", statement]);
    }

    // A script that throws gives a result marked as an error.
    test_error_marked(): void {
      const bench = this.bench_make([]);
      this.script_answer(bench, digest_entry("script_stop"));
      const value = this.tool_run(bench, "script_run", {
        name: "stop",
        args: {},
      });
      const result = this.result_of(value);
      this.assertEqual(result.isError, true);
      const block = result.content[0] as { type: "text"; text: string };
      const run = JSON.parse(block.text) as script.ScriptResult;
      this.assertEqual(run.error, "Error: stop");
      this.assertEqual(run.lines, []);
      this.assertEqual(bench.store.calls, [
        ["kv_get", ["/_files/script/stop.js"]],
        ["sink", []],
      ]);
    }
  }

  // The tool that makes images, through the provider and the UI.
  export class TestImages extends ToolCase {
    // The castle turn's image is asked for, kept, sent to the UI, returned.
    test_image_recorded(): void {
      const bench = this.bench_make([31, 32]);
      const image = digest_entry("arrival_image");
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "image_make", {
          prompt: constants.image_prompt,
          key: constants.image_key,
        }),
        0,
        "tools.image_reply",
      );
      const request = bench.tasks.sent[0];
      this.assertEqual(request.owner, constants.provider_owner);
      this.assertEqual(request.line, gold_line("image_request"));
      const body = JSON.stringify(request.line.json);
      this.assertEqual(body, constants.image_json);
      const answer = reply_gold("image_answer", request.id as number);
      const images = answer.json as { data: { b64_json?: string }[] };
      images.data[0].b64_json = base64_encode(image.data);
      const row = row_make(constants.image_key, image);
      bench.store.answer_add("kv_put", { value: row });
      const keeping = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [answer]),
        1,
        "tools.media_reply",
      );
      this.assertEqual(bench.store.calls, [
        ["kv_put", [constants.image_ref, image.data]],
      ]);
      const media = bench.tasks.sent[1];
      this.assertEqual(media.owner, "ui");
      const stored = gold_line("media_store");
      stored[1] = { size: image.data.length, d: image.data };
      this.assertEqual(media.line, stored);
      const kept = reply_gold("media_store_reply", media.id as number);
      kept.size = image.data.length;
      kept.sha256 = image.sha256;
      const result = this.wake_run(bench, keeping, [kept]);
      this.assertEqual(this.text_of(result), image_result(image));
    }

    // An image answered by url is downloaded by the UI and kept here.
    test_image_fetched(): void {
      const bench = this.bench_make([33, 34]);
      const image = digest_entry("arrival_image");
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "image_make", {
          prompt: constants.image_prompt,
          key: constants.image_key,
        }),
        0,
        "tools.image_reply",
      );
      const request = bench.tasks.sent[0];
      const answer = reply_gold("image_answer_url", request.id as number);
      const fetching = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [answer]),
        1,
        "tools.fetch_reply",
      );
      const download = bench.tasks.sent[1];
      this.assertEqual(download.owner, "ui");
      this.assertEqual(download.line, gold_line("media_fetch"));
      const fetched = reply_gold("media_fetch_reply", download.id as number);
      fetched[1] = { s: image.data.length, d: image.data };
      fetched.size = image.data.length;
      fetched.sha256 = image.sha256;
      const row = row_make(constants.image_key, image);
      bench.store.answer_add("kv_put", { value: row });
      const result = this.wake_run(bench, fetching, [fetched]);
      this.assertEqual(this.text_of(result), image_result(image));
      this.assertEqual(bench.store.calls, [
        ["kv_put", [constants.image_ref, image.data]],
      ]);
    }
  }

  // The tool that renders the current scene.
  export class TestRender extends ToolCase {
    // Gives the store's answers for the world's name and its scene's ref.
    scene_answer(bench: ToolBench, world: string, scene: string): void {
      for (const name of [world, scene]) {
        bench.store.answer_add("kv_get", value_answer(digest_entry(name)));
        bench.store.answer_add("sink", { value: new CacheDouble() });
      }
    }

    // The render names the world's scene, the image and the subtitle.
    test_render_recorded(): void {
      const bench = this.bench_make([35]);
      this.scene_answer(bench, "castle_world", "arrival_ref");
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "render", {
          image: constants.image_ref,
          subtitle: constants.arrival_subtitle,
        }),
        0,
        "tools.render_reply",
      );
      this.assertEqual(bench.store.calls, [
        ["kv_get", ["/metaverse/world"]],
        ["sink", []],
        ["kv_get", ["/castle_world/scene"]],
        ["sink", []],
      ]);
      const render = bench.tasks.sent[0];
      this.assertEqual(render.owner, "ui");
      this.assertEqual(render.line, gold_line("render_arrival"));
      const shown = reply_gold("render_reply", render.id as number);
      const result = this.wake_run(bench, asked, [shown]);
      this.assertEqual(this.text_of(result), "{}");
    }

    // A render with no image is black, as the boot's render is.
    test_render_black(): void {
      const bench = this.bench_make([36]);
      this.scene_answer(bench, "metaverse", "hyperposition_ref");
      this.sleep_check(
        bench,
        this.tool_run(bench, "render", {
          subtitle: constants.hyperposition_subtitle,
        }),
        0,
        "tools.render_reply",
      );
      this.assertEqual(bench.store.calls[2], ["kv_get", ["/metaverse/scene"]]);
      const render = bench.tasks.sent[0];
      this.assertEqual(render.line, gold_line("render_black"));
    }
  }

  // The tool that runs a command line in the debug console.
  export class TestConsole extends ToolCase {
    // Runs the tool on a command and returns its sleep on the permit.
    permit_start(bench: ToolBench, text: string): dispatch.Sleep {
      const start = bench.tasks.sent.length;
      return this.sleep_check(
        bench,
        this.tool_run(bench, "console_run", { text, timeout_seconds: 5 }),
        start,
        "tools.permit_reply",
      );
    }

    // The permit's reply of the gold, to the last request sent.
    choice_make(bench: ToolBench, name: string): lines.Line {
      const ask = bench.tasks.sent[bench.tasks.sent.length - 1];
      const reply = reply_gold(name, ask.id as number);
      reply.permit = ask.line.permit;
      return reply;
    }

    // The sleep on the `console.show` sent at `start`, then on the read.
    show_answer(
      bench: ToolBench,
      value: mcp.ToolResult | dispatch.Sleep,
      start: number,
    ): dispatch.Sleep {
      const wake = "tools.show_reply";
      const showing = this.sleep_check(bench, value, start, wake);
      const show = bench.tasks.sent[start];
      this.assertEqual(show.owner, "ui");
      this.assertEqual(show.line, gold_line("console_show"));
      const shown = reply_gold("show_reply", show.id as number);
      return this.sleep_check(
        bench,
        this.wake_run(bench, showing, [shown]),
        start + 1,
        "tools.console_reply",
      );
    }

    // A command asks, shows the console, runs and returns its output trimmed.
    test_console_recorded(): void {
      const bench = this.bench_make([41, 42, 43]);
      const asked = this.permit_start(bench, "echo hi");
      const ask = bench.tasks.sent[0];
      this.assertEqual(ask.owner, "ui");
      this.assertEqual(ask.line, gold_line("permit_ask"));
      const accepted = this.choice_make(bench, "permit_accept");
      const reading = this.show_answer(
        bench,
        this.wake_run(bench, asked, [accepted]),
        1,
      );
      const [input, read] = bench.tasks.sent.slice(2);
      this.assertEqual(input.owner, "console");
      this.assertEqual(input.id, undefined);
      this.assertEqual(input.line, input_line(constants.console_input));
      this.assertEqual(read.owner, "console");
      this.assertEqual(read.line, gold_line("console_read"));
      const output = reply_gold("read_reply", read.id as number);
      const result = this.wake_run(bench, reading, [output]);
      this.assertEqual(this.text_of(result), constants.console_result);
    }

    // A denial returns an error to the model and sends nothing on.
    test_permit_denied(): void {
      const bench = this.bench_make([44]);
      const asked = this.permit_start(bench, "echo hi");
      const denied = this.wake_run(bench, asked, [
        this.choice_make(bench, "permit_deny"),
      ]);
      const text = gold_text("tools_browser_permit_denied");
      this.assertEqual(this.result_of(denied), {
        content: [{ type: "text", text }],
        isError: true,
      });
      this.assertEqual(bench.tasks.sent.length, 1);
    }

    // Outside debug mode the tool throws and asks the player nothing.
    test_debug_off(): void {
      const bench = this.bench_make([], { debug: false });
      this.raised_assert(gold_text("tools_browser_debug_off"), () =>
        this.tool_run(bench, "console_run", {
          text: "echo hi",
          timeout_seconds: 5,
        }),
      );
      this.assertEqual(bench.tasks.sent.length, 0);
    }

    // Always Allow shows and runs this command and every later one, no ask.
    test_permit_always(): void {
      const bench = this.bench_make([45, 46, 47, 48, 49]);
      const asked = this.permit_start(bench, "echo hi");
      const always = this.choice_make(bench, "permit_always");
      this.show_answer(bench, this.wake_run(bench, asked, [always]), 1);
      this.show_answer(
        bench,
        this.tool_run(bench, "console_run", {
          text: "pwd",
          timeout_seconds: 5,
        }),
        4,
      );
      const later = bench.tasks.sent.slice(4).map((entry) => entry.line);
      this.assertEqual(later, [
        gold_line("console_show"),
        input_line("0pwd\n"),
        gold_line("console_read"),
      ]);
    }

    // Each permit asked has the next number, and Accept lasts one command.
    test_permits_counted(): void {
      const bench = this.bench_make([51, 52, 53, 54, 55, 56]);
      for (const number of [1, 2]) {
        const start = bench.tasks.sent.length;
        const asked = this.permit_start(bench, `echo ${number}`);
        const ask = bench.tasks.sent[start];
        this.assertEqual(ask.line.permit, number);
        this.show_answer(
          bench,
          this.wake_run(bench, asked, [
            this.choice_make(bench, "permit_accept"),
          ]),
          start + 1,
        );
      }
    }

    // A read that timed out keeps the output after the echo, with no prompt.
    test_console_expired(): void {
      const bench = this.bench_make([57, 58, 59]);
      const asked = this.permit_start(bench, "sleep 600");
      const accepted = this.choice_make(bench, "permit_accept");
      const reading = this.show_answer(
        bench,
        this.wake_run(bench, asked, [accepted]),
        1,
      );
      const read = bench.tasks.sent[3];
      const output = reply_gold("read_reply_expired", read.id as number);
      const result = this.wake_run(bench, reading, [output]);
      this.assertEqual(this.text_of(result), gold_value("result_expired"));
    }
  }

  // The verbose tail, the one verbose tool, as the runtime has no level.
  export class TestVerbose extends ToolCase {
    // No tool sets a verbose level, and none is registered to run one.
    test_level_gone(): void {
      const bench = this.bench_make([]);
      const names = bench.server.tools.map((tool) => tool.name);
      this.assertFalse(names.includes("verbose_level"));
      this.assertFalse(bench.server.runs.has("verbose_level"));
      this.assertTrue(names.includes("verbose_tail"));
    }

    // The tail is asked of the server and its lines are returned.
    test_tail_asked(): void {
      const bench = this.bench_make([61]);
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "verbose_tail", { thread: "server", count: 5 }),
        0,
        "tools.tail_reply",
      );
      const request = bench.tasks.sent[0];
      this.assertEqual(request.owner, "server");
      this.assertEqual(request.line, gold_line("verbose_tail"));
      const reply = reply_gold("tail_reply", request.id as number);
      const result = this.wake_run(bench, asked, [reply]);
      const tail = { lines: reply.lines };
      this.assertEqual(this.text_of(result), JSON.stringify(tail));
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds only `tools_register`.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(tools_browser));
      this.assertEqual(Object.keys(tools_browser), ["tools_register"]);
    }
  }
}

Object.freeze(test_tools_browser);
