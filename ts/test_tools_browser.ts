// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of tools_browser.ts on real parts: the tools registered on a real
// `mcp.Server` over a real `substrate.Store` on the realm's sqlite3 module and
// pool, its cache over the realm's test slots, and a real queue of thread `ai`
// in synchronous mode whose `mcp` handler hands each line to the server. A
// tool's call comes from the queue of thread `server`, whose real `mcp.Client`
// submits it from a handler of the test's own and keeps the result its wake
// reads. The far ends of the requests the tools send are second real queues
// whose handlers are the test's own functions: `http` answers the image
// requests, `ui` the image keeping, rendering and permits, and `server` the
// verbose tail, each with the reply the test scripted from the gold, keeping
// every request it got; `server` also keeps the store's pushes. A tool that
// throws stops the queue that runs it by design, so such a call goes straight
// to the server's `line_handle`, and the test reads the failure it returns.
//
// A realm takes one registration of the tools, since the server registers
// their wake types in the realm's one dispatch table, so the tests share the
// one bench, built at the first test, and each test starts with no database:
// `setUp` drops every database of the store through the store's API. The
// tools read debug mode through the settings reader the bench hands them,
// the test's own function, which a test may answer for with values of its
// own until its `tearDown`. They check the tools in the order and texts of
// API/mcp/tools.json, the result of every tool and what the store holds after
// it, every line a tool sends against the gold in full names, the castle
// turn's image and render, a denied permit, the step script, a lost cache
// file, and every error. The inputs and digests are those of
// test_digests.json. The provider key is set by provider.key_set.

namespace test_tools_browser {
  // The vectors the test page carries, each file's bytes in base64.
  declare const test_vectors: { readonly [name: string]: string };

  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // An input of the digest vector and its `SHA-256`.
  interface DigestEntry {
    data: Uint8Array;
    sha256: string;
  }

  // What the far ends got and gave in one test, and the client's answers.
  interface FarRecord {
    // The reply frames each far end still gives, by request type, in order.
    readonly replies: Map<string, lines.Line[]>;
    // Each request a far end got, in order.
    readonly got: lines.Line[];
    // Each push of the store that the server's far end got, in order.
    readonly pushes: lines.Line[];
    // What the client read from each answer, in order.
    readonly answers: unknown[];
  }

  // The real parts the tests share, built once per realm.
  interface ToolBench {
    store: substrate.Store;
    server: mcp.Server;
    tasks: queue.TaskQueue;
    service: queue.TaskQueue;
  }

  // The names, texts and data the tests use.
  const constants = Object.freeze({
    // The id of this module's gold in `test_settings.json`.
    gold_id: "typescript.test_tools_browser",
    // The file of the digest vectors and this module's object in it.
    digests_name: "test_digests.json",
    digests_module: "test_tools_browser",
    // The root of the store's databases in the realm's pool.
    root: "/test_tools_browser",
    // The settings of the store's sizes.
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    // A synthetic provider key, which every image request carries.
    key: "xai-SYNTHETIC-KEY",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // The threads of the bench: the tools', the provider's, the UI, server.
    thread: "ai" as const,
    http_thread: "http" as const,
    ui_thread: "ui" as const,
    server_thread: "server" as const,
    // The identities of the server and of the client that calls its tools.
    server_name: "xsjs-browser",
    client_name: "test_tools_browser",
    version: "0",
    // The line type of the protocol, and the version of every handler.
    line_type: "mcp",
    handler_version: 0,
    // The test's own types on the server's queue: a call, a list, an answer.
    call_type: "test_tools_browser.call",
    list_type: "test_tools_browser.list",
    answer_type: "test_tools_browser.answer",
    // The owner table of the tools' queue.
    owners: Object.freeze<queue.OwnerTable>({ mcp: "ai", "tools.": "ai" }),
    // The requests each far end answers, by its thread.
    http_types: Object.freeze(["http.request"]),
    ui_types: Object.freeze([
      "media.store",
      "media.fetch",
      "render",
      "permit.ask",
    ]),
    server_types: Object.freeze(["verbose.tail"]),
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
    // The world table of the castle universe.
    world_sql:
      "CREATE TABLE world" +
      " (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT",
    // The result of the castle's two statements.
    castle_reply:
      '{"results":[{"columns":[],"rows":[],"changes":0},' +
      '{"columns":[],"rows":[],"changes":1}]}',
    // The region table of the castle's world, which the step script changes.
    region_sql:
      "CREATE TABLE region" +
      " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL) STRICT",
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
    // The ref of the script that throws.
    stop_ref: "/_files/script/stop.js",
    // The line the step script logs when it advances the tide by 1.
    step_line: "tide advanced by 1",
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
    // The text a value over `overflow_bytes` repeats, so that it is cached.
    cached_text: "a value the cache holds. ",
  });

  // The stored text of the arrival scene, its encoded document as JSON.
  const arrival_text =
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"' +
    constants.arrival_subtitle +
    '","image":{"$ref":1}}';

  // This module's object of the digest vector, parsed at the first read.
  let digests: { [name: string]: unknown } | undefined = undefined;

  // The bench of the realm, built at the first test.
  let bench_kept: ToolBench | undefined = undefined;

  // What the far ends got and gave in the test that runs.
  let far: FarRecord = far_fresh();

  // The settings the running test answers for itself, by id.
  let overrides: { [id: string]: unknown } = {};

  // A record of the far ends with nothing scripted and nothing got.
  function far_fresh(): FarRecord {
    return { replies: new Map(), got: [], pushes: [], answers: [] };
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

  // This module's object of the digest vector the test page carries.
  function digests_read(): { [name: string]: unknown } {
    if (digests === undefined) {
      const name = constants.digests_name;
      if (!Object.hasOwn(test_vectors, name)) {
        throw new Error(`test_vectors has no file ${name}`);
      }
      const file = utility.base64_decode(test_vectors[name]);
      const vector = JSON.parse(utility.utf8_decode(file)) as {
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

  // The base64 text of bytes, as a provider's answer carries an image.
  function base64_encode(data: Uint8Array): string {
    const text = Array.from(data, (byte) => String.fromCharCode(byte));
    return btoa(text.join(""));
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

  // The text of each line, which leaves out the time.
  function lines_shown(kept: lines.VerboseLine[]): string[] {
    return kept.map((line) => line.text);
  }

  // A copy of a line a far end got, its id, which a submit set, taken off.
  function line_unmarked(line: lines.Line): lines.Line {
    const copy = structuredClone(line);
    for (const field of constants.id_fields) {
      delete (copy[0] as unknown as { [name: string]: unknown })[field];
    }
    return copy;
  }

  // A line of the test's own type and payload, in the form the settings pick.
  function line_typed(
    type: string,
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
  }

  // The settings reader of the tools: the test's values first, else harness.
  function setting_read(id: string): unknown {
    return Object.hasOwn(overrides, id)
      ? overrides[id]
      : harness.setting_get(id);
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

  // Joins a far queue of the thread to the tools' queue by linked ports.
  function far_join(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
    owners: queue.OwnerTable,
  ): queue.TaskQueue {
    const far_tasks = new queue.TaskQueue(thread, owners, true);
    const port = new queue.LocalPort();
    tasks.port_add(thread, port);
    far_tasks.port_add(constants.thread, new queue.LocalPort(port));
    return far_tasks;
  }

  // The owner table of a far queue: each of its types its own.
  function owners_of(
    thread: queue.ThreadName,
    types: readonly string[],
  ): queue.OwnerTable {
    return Object.fromEntries(types.map((type) => [type, thread]));
  }

  // Registers the far ends' answers and keepers, the test's own functions.
  function far_register(): void {
    const version = constants.handler_version;
    const types = [
      ...constants.http_types,
      ...constants.ui_types,
      ...constants.server_types,
    ];
    for (const type of types) {
      dispatch.handler_register(type, version, far_answer);
    }
    for (const type of constants.push_types) {
      dispatch.handler_register(type, version, (line) => {
        far.pushes.push(line);
        return undefined;
      });
    }
  }

  // Registers the server's handler of `mcp` and the client's own types.
  function client_register(server: mcp.Server, client: mcp.Client): void {
    const version = constants.handler_version;
    const answer = constants.answer_type;
    dispatch.handler_register(constants.line_type, version, (line) =>
      server.line_handle(line),
    );
    dispatch.handler_register(constants.call_type, version, (line) => {
      const { name, args } = jslb.payload_of(line);
      const fields = args as { [key: string]: unknown };
      const id = client.tool_call(name as string, fields);
      return dispatch.task_sleep(false, [id], answer);
    });
    dispatch.handler_register(constants.list_type, version, () =>
      dispatch.task_sleep(true, [client.tools_list()], answer),
    );
    dispatch.handler_register(answer, version, (line) => {
      const [reply] = line.replies as lines.Line[];
      const listed = line.state as boolean;
      far.answers.push(
        listed ? client.tools_read(reply) : client.result_of(reply),
      );
      return undefined;
    });
  }

  // Builds the bench: the tools on a real server, store and queues.
  function bench_build(): ToolBench {
    const tasks = new queue.TaskQueue(
      constants.thread,
      constants.owners,
      true,
    );
    const { http_thread, ui_thread, server_thread } = constants;
    far_join(tasks, http_thread, owners_of(http_thread, constants.http_types));
    far_join(tasks, ui_thread, owners_of(ui_thread, constants.ui_types));
    const service = far_join(
      tasks,
      server_thread,
      owners_of(server_thread, [
        ...constants.server_types,
        ...constants.push_types,
        constants.call_type,
        constants.list_type,
        constants.answer_type,
      ]),
    );
    far_register();
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
      setting_read,
    );
    const client = new mcp.Client(
      constants.client_name,
      constants.version,
      service,
      constants.thread,
    );
    client_register(server, client);
    return { store, server, tasks, service };
  }

  // The bench of the realm, built at its first use.
  function bench_get(): ToolBench {
    if (bench_kept === undefined) {
      bench_kept = bench_build();
    }
    return bench_kept;
  }

  // A tool test: the provider key set, no database, nothing scripted.
  class ToolCase extends unittest.TestCase {
    // Sets the provider key and drops every database the store holds.
    setUp(): void {
      provider.key_set(constants.key);
      const store = bench_get().store;
      for (const name of store.db_list()) {
        store.db_drop(name);
      }
      far = far_fresh();
    }

    // Ends the test's own settings and checks every scripted reply was given.
    tearDown(): void {
      overrides = {};
      for (const [type, left] of far.replies) {
        this.assertEqual(left, [], `replies to ${type} were left`);
      }
    }

    // The store the tools use.
    store_get(): substrate.Store {
      return bench_get().store;
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

    // What the client read from the one answer to a line of the server.
    answer_take(line: lines.Line): unknown {
      const before = far.answers.length;
      bench_get().service.line_notify(line);
      this.assertEqual(far.answers.length, before + 1, "no answer came");
      return far.answers[before];
    }

    // Calls a tool by name on its arguments, as the server's client does.
    tool_call(name: string, args: { [key: string]: unknown }): mcp.ToolResult {
      return this.answer_take(
        line_typed(constants.call_type, { name, args }),
      ) as mcp.ToolResult;
    }

    // The tools the server lists, as the server's client reads them.
    tools_listed(): mcp.Tool[] {
      return this.answer_take(
        line_typed(constants.list_type, {}),
      ) as mcp.Tool[];
    }

    // The failure the server returns for a call whose tool throws.
    failure_of(name: string, args: { [key: string]: unknown }): Error {
      const header = jslb.header_make(constants.line_type, {
        id: 1,
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [], {
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: { name, arguments: args },
      });
      const outcome = bench_get().server.line_handle(line);
      this.assertTrue(
        outcome !== undefined && Object.hasOwn(outcome, "error"),
        "a failure was expected",
      );
      const failure = outcome as dispatch.Failure;
      const answer = jslb.payload_of(failure.reply);
      if (Object.hasOwn(answer, "result")) {
        const result = answer.result as mcp.ToolResult;
        this.assertEqual(result.isError, true);
      }
      return failure.error;
    }

    // The text of a result that holds one text block and is no error.
    text_of(result: mcp.ToolResult): string {
      this.assertFalse("isError" in result);
      this.assertEqual(result.content.length, 1);
      const block = result.content[0];
      this.assertEqual(block.type, "text");
      return (block as { type: "text"; text: string }).text;
    }

    // The requests the far ends got, each with its id taken off.
    got_unmarked(): lines.Line[] {
      return far.got.map(line_unmarked);
    }

    // The text of a value of the store, read whole.
    value_text(ref: string): string {
      return utility.utf8_decode(
        this.store_get().kv_get(ref).data as Uint8Array,
      );
    }

    // Creates the databases with the store's own method.
    dbs_create(names: string[]): void {
      for (const name of names) {
        this.store_get().db_create(name);
      }
    }
  }

  // The tools registered on the server.
  export class TestRegistry extends ToolCase {
    // The tools are those of `API/mcp/tools.json`, whole and in its order.
    test_tools_recorded(): void {
      const recorded = constants.recorded_tools.map(
        (text) => JSON.parse(text) as mcp.Tool,
      );
      this.assertEqual(recorded.length, 16);
      this.assertEqual(
        JSON.stringify(this.tools_listed()),
        JSON.stringify(recorded),
      );
    }
  }

  // The tools of SQL and of creating and dropping databases.
  export class TestDatabases extends ToolCase {
    // `sql_run` runs the statements on the store and answers its results.
    test_sql_recorded(): void {
      this.dbs_create(["castle"]);
      const statements = [
        { sql: constants.world_sql, params: [] },
        {
          sql: "INSERT INTO world VALUES (?, ?)",
          params: ["castle_world", "The castle"],
        },
      ];
      const result = this.tool_call("sql_run", { db: "castle", statements });
      this.assertEqual(this.text_of(result), constants.castle_reply);
      const read = { sql: "SELECT name, title FROM world", params: [] };
      const [rows] = this.store_get().sql_run("castle", [read]);
      this.assertEqual(rows.rows, [["castle_world", "The castle"]]);
    }

    // `db_create` and `db_drop` add and remove a database.
    test_create_drop(): void {
      const store = this.store_get();
      const created = this.tool_call("db_create", { db: "alpha" });
      this.assertEqual(this.text_of(created), "{}");
      this.assertEqual(store.db_list(), ["alpha"]);
      const dropped = this.tool_call("db_drop", { db: "alpha" });
      this.assertEqual(this.text_of(dropped), "{}");
      this.assertEqual(store.db_list(), []);
    }
  }

  // The tools of values: put, get, delete and list.
  export class TestValues extends ToolCase {
    // `kv_put` writes the text's bytes and returns the row's digest.
    test_put_recorded(): void {
      this.dbs_create(["metaverse", "castle_world", "_files"]);
      const cases: [string, string][] = [
        ["/metaverse/world", "castle_world"],
        ["/castle_world/scene", "arrival_ref"],
        [constants.step_ref, "step_script"],
      ];
      for (const [ref, name] of cases) {
        const entry = digest_entry(name);
        const text = utility.utf8_decode(entry.data);
        const result = this.tool_call("kv_put", { ref, text });
        const sha256 = entry.sha256;
        this.assertEqual(this.text_of(result), JSON.stringify({ sha256 }));
        this.assertEqual(this.store_get().kv_get(ref).data, entry.data);
      }
    }

    // `kv_get` reads a value as its text.
    test_get_text(): void {
      this.dbs_create(["alpha"]);
      const entry = digest_entry("text_wide");
      this.store_get().kv_put("/alpha/a", entry.data);
      const result = this.tool_call("kv_get", { ref: "/alpha/a" });
      const text = String.fromCodePoint(0x4e2d, 0x6587, 0x1f600) + " text";
      this.assertEqual(this.text_of(result), text);
    }

    // `kv_get` reads a value held in the cache through its handle.
    test_get_cached(): void {
      this.dbs_create(["alpha"]);
      const store = this.store_get();
      const overflow = harness.setting_get(constants.overflow_setting);
      const count = Math.ceil(
        ((overflow as number) + 1) / constants.cached_text.length,
      );
      const text = constants.cached_text.repeat(count);
      store.kv_put("/alpha/big", utility.utf8_encode(text));
      this.assertEqual(typeof store.kv_get("/alpha/big").data, "string");
      const result = this.tool_call("kv_get", { ref: "/alpha/big" });
      this.assertEqual(this.text_of(result), text);
    }

    // `kv_get` of bytes that are not `UTF-8` throws.
    test_get_refused(): void {
      this.dbs_create(["alpha"]);
      this.store_get().kv_put("/alpha/raw", digest_entry("byte_ff").data);
      const error = this.failure_of("kv_get", { ref: "/alpha/raw" });
      this.assertEqual(error.message, gold_text("utility_bytes_refused"));
    }

    // `kv_delete` deletes the row and returns an empty object.
    test_delete_empty(): void {
      this.dbs_create(["alpha"]);
      const store = this.store_get();
      store.kv_put("/alpha/a", digest_entry("note_a").data);
      const result = this.tool_call("kv_delete", { ref: "/alpha/a" });
      this.assertEqual(this.text_of(result), "{}");
      this.assertEqual(store.kv_list("alpha", ""), []);
    }

    // The store's throw for a value whose cache file is lost passes through.
    test_file_lost(): void {
      this.dbs_create(["alpha"]);
      const store = this.store_get();
      const overflow = harness.setting_get(constants.overflow_setting);
      const count = Math.ceil(
        ((overflow as number) + 1) / constants.cached_text.length,
      );
      const text = constants.cached_text.repeat(count);
      store.kv_put("/alpha/big", utility.utf8_encode(text));
      store.doc_put("alpha", "note", { 0: { t: "note" }, text });
      const image = store.db_snapshot("alpha");
      store.kv_delete("/alpha/big");
      store.kv_delete("/alpha/note/1");
      store.db_restore("alpha", image.data, []);
      const rows = new Map(
        store.kv_list("alpha", "").map((row) => [row.k, row.sha256]),
      );
      const cases: [string, string, string][] = [
        ["kv_get", "/alpha/big", "value"],
        ["doc_get", "/alpha/note/1", "document"],
      ];
      for (const [tool, lost, name] of cases) {
        const sha256 = rows.get(lost.slice("/alpha/".length)) as string;
        const text_lost = gold_text(`substrate_file_lost_${name}`);
        const error = this.failure_of(tool, { ref: lost });
        this.assertEqual(error.message, text_lost.replaceAll("{1}", sha256));
      }
      this.assertEqual(far.got, []);
    }

    // `kv_list` returns the rows under the prefix.
    test_list_keys(): void {
      this.dbs_create(["alpha"]);
      const store = this.store_get();
      const keys = ["note_a", "note_b"].map((name) => {
        const entry = digest_entry(name);
        const k = utility.utf8_decode(entry.data);
        store.kv_put(`/alpha/${k}`, entry.data);
        return row_make(k, entry);
      });
      const result = this.tool_call("kv_list", {
        db: "alpha",
        prefix: "note/",
      });
      this.assertEqual(this.text_of(result), JSON.stringify({ keys }));
    }
  }

  // The tools of documents.
  export class TestDocuments extends ToolCase {
    // The arrival scene is put, read back as its stored document, and found.
    test_doc_recorded(): void {
      this.dbs_create(["castle_gatehouse"]);
      const body = JSON.parse(arrival_text) as lines.Document;
      const where = { db: "castle_gatehouse", id: "scene/arrival" };
      const ref = constants.arrival_ref;
      const put = this.tool_call("doc_put", { ...where, body });
      this.assertEqual(this.text_of(put), constants.doc_result);
      const read = this.tool_call("doc_get", { ref });
      this.assertEqual(JSON.parse(this.text_of(read)), body);
      const head = this.tool_call("doc_head", where);
      this.assertEqual(this.text_of(head), constants.doc_result);
    }
  }

  // The tools that run scripts.
  export class TestScripts extends ToolCase {
    // A world with the gatehouse's tide at 0, and the scripts in `_files`.
    setUp(): void {
      super.setUp();
      this.dbs_create(["castle_world", "_files"]);
      const store = this.store_get();
      store.sql_run("castle_world", [
        { sql: constants.region_sql, params: [] },
        {
          sql: "INSERT INTO region VALUES (?, ?)",
          params: ["castle_gatehouse", 0],
        },
      ]);
      store.kv_put(constants.step_ref, digest_entry("step_script").data);
      store.kv_put(constants.stop_ref, digest_entry("script_stop").data);
    }

    // The tide of the gatehouse as the store holds it.
    tide_read(): unknown {
      const read = { sql: "SELECT tide FROM region", params: [] };
      return this.store_get().sql_run("castle_world", [read])[0].rows;
    }

    // The step script reads its text, runs its statement, returns its line.
    test_run_recorded(): void {
      const result = this.tool_call("script_run", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(Object.keys(run), ["value", "lines"]);
      this.assertEqual(run.value, { changes: 1 });
      this.assertEqual(lines_shown(run.lines), [constants.step_line]);
      this.assertEqual(this.tide_read(), [[1]]);
    }

    // `script_debug` traces the store's call before the script's line.
    test_debug_traced(): void {
      const result = this.tool_call("script_debug", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(run.value, { changes: 1 });
      const trace = gold_text("script_trace_call");
      this.assertEqual(lines_shown(run.lines), [trace, constants.step_line]);
      this.assertEqual(this.tide_read(), [[1]]);
    }

    // A script that throws gives a result marked as an error.
    test_error_marked(): void {
      const result = this.tool_call("script_run", { name: "stop", args: {} });
      this.assertEqual(result.isError, true);
      const block = result.content[0] as { type: "text"; text: string };
      const run = JSON.parse(block.text) as script.ScriptResult;
      this.assertEqual(run.error, "Error: stop");
      this.assertEqual(run.lines, []);
      this.assertEqual(this.tide_read(), [[0]]);
    }
  }

  // The tool that makes images, through the provider and the UI.
  export class TestImages extends ToolCase {
    // The `_files` database, which keeps the images.
    setUp(): void {
      super.setUp();
      this.dbs_create(["_files"]);
    }

    // The castle turn's image is asked for, kept, sent to the UI, returned.
    test_image_recorded(): void {
      const image = digest_entry("arrival_image");
      const answer = gold_line("image_answer");
      const images = answer.json as { data: { b64_json?: string }[] };
      images.data[0].b64_json = base64_encode(image.data);
      this.reply_script("http.request", answer);
      const kept = gold_line("media_store_reply");
      kept.size = image.data.length;
      kept.sha256 = image.sha256;
      this.reply_script("media.store", kept);
      const result = this.tool_call("image_make", {
        prompt: constants.image_prompt,
        key: constants.image_key,
      });
      this.assertEqual(this.text_of(result), image_result(image));
      const stored = gold_line("media_store");
      stored[1] = { size: image.data.length, d: image.data };
      const [request, media] = this.got_unmarked();
      this.assertEqual(far.got.length, 2);
      this.assertEqual(request, gold_line("image_request"));
      this.assertEqual(JSON.stringify(request.json), constants.image_json);
      this.assertEqual(media, stored);
      const row = this.store_get().kv_get(constants.image_ref);
      this.assertEqual(row.data, image.data);
    }

    // An image answered by url is downloaded by the UI and kept here.
    test_image_fetched(): void {
      const image = digest_entry("arrival_image");
      this.reply_script("http.request", gold_line("image_answer_url"));
      const fetched = gold_line("media_fetch_reply");
      fetched[1] = { s: image.data.length, d: image.data };
      fetched.size = image.data.length;
      fetched.sha256 = image.sha256;
      this.reply_script("media.fetch", fetched);
      const result = this.tool_call("image_make", {
        prompt: constants.image_prompt,
        key: constants.image_key,
      });
      this.assertEqual(this.text_of(result), image_result(image));
      const [request, download] = this.got_unmarked();
      this.assertEqual(far.got.length, 2);
      this.assertEqual(request, gold_line("image_request"));
      this.assertEqual(download, gold_line("media_fetch"));
      const row = this.store_get().kv_get(constants.image_ref);
      this.assertEqual(row.data, image.data);
    }
  }

  // The tool that renders the current scene.
  export class TestRender extends ToolCase {
    // Keeps the world's name and its scene's ref, read as the tool reads.
    scene_put(world: string, scene: string): void {
      const store = this.store_get();
      const names = world === "metaverse" ? [world] : ["metaverse", world];
      this.dbs_create(names);
      store.kv_put("/metaverse/world", digest_entry(world).data);
      store.kv_put(`/${world}/scene`, digest_entry(scene).data);
    }

    // The render names the world's scene, the image and the subtitle.
    test_render_recorded(): void {
      this.scene_put("castle_world", "arrival_ref");
      this.reply_script("render", gold_line("render_reply"));
      const result = this.tool_call("render", {
        image: constants.image_ref,
        subtitle: constants.arrival_subtitle,
      });
      this.assertEqual(this.text_of(result), "{}");
      this.assertEqual(this.got_unmarked(), [gold_line("render_arrival")]);
    }

    // A render with no image is black, as the boot's render is.
    test_render_black(): void {
      this.scene_put("metaverse", "hyperposition_ref");
      this.reply_script("render", gold_line("render_reply"));
      const result = this.tool_call("render", {
        subtitle: constants.hyperposition_subtitle,
      });
      this.assertEqual(this.text_of(result), "{}");
      this.assertEqual(this.got_unmarked(), [gold_line("render_black")]);
    }
  }

  // The tool that runs a command line in the debug console, to its permit.
  export class TestConsole extends ToolCase {
    // A denial returns an error to the model and sends nothing on.
    test_permit_denied(): void {
      this.reply_script("permit.ask", gold_line("permit_deny"));
      const result = this.tool_call("console_run", {
        text: "echo hi",
        timeout_seconds: 5,
      });
      const text = gold_text("tools_browser_permit_denied");
      this.assertEqual(result, {
        content: [{ type: "text", text }],
        isError: true,
      });
      this.assertEqual(this.got_unmarked(), [gold_line("permit_ask")]);
    }

    // Outside debug mode the tool throws and asks the player nothing.
    test_debug_off(): void {
      overrides = { debug: false };
      const error = this.failure_of("console_run", {
        text: "echo hi",
        timeout_seconds: 5,
      });
      this.assertEqual(error.message, gold_text("tools_browser_debug_off"));
      this.assertEqual(far.got, []);
    }
  }

  // The verbose tail, the one verbose tool, as the runtime has no level.
  export class TestVerbose extends ToolCase {
    // No tool sets a verbose level, and the server refuses a call of one.
    test_level_gone(): void {
      const names = this.tools_listed().map((tool) => tool.name);
      this.assertFalse(names.includes("verbose_level"));
      this.assertTrue(names.includes("verbose_tail"));
      const error = this.failure_of("verbose_level", {});
      this.assertEqual(error.message, gold_text("mcp_tool_unknown"));
    }

    // The tail is asked of the server and its lines are returned.
    test_tail_asked(): void {
      const reply = gold_line("tail_reply");
      this.reply_script("verbose.tail", reply);
      const result = this.tool_call("verbose_tail", {
        thread: "server",
        count: 5,
      });
      const tail = { lines: reply.lines };
      this.assertEqual(this.text_of(result), JSON.stringify(tail));
      this.assertEqual(this.got_unmarked(), [gold_line("verbose_tail")]);
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
