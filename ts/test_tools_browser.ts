// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of tools_browser.ts on a store of the sqlite3.wasm module and OPFS
// pool the test page sets as globals, with a server double that keeps the
// tools and wakes registered on it and a queue double that keeps what the
// tools submit: the tools in their listed order and texts, the result of
// every tool, the requests of the tools that sleep and the results of their
// wakes on the values of the castle turn, which builds the gatehouse scene,
// of a console command and of the step script, the administration of the
// databases with a snapshot loaded as one blob, values asked of the server
// again after an unload and a load, the values of `_files` freed when a
// render leaves its scene, and every error.

namespace test_tools_browser {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

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

  // The store of one test and the doubles its tools are registered on.
  interface ToolBench {
    store: substrate.Store;
    server: ServerDouble;
    tasks: TasksDouble;
  }

  // The settings, names, texts and digests the tests use.
  const constants = Object.freeze({
    // The `overflow_bytes` of `settings.json`, 128 KiB.
    overflow_bytes: 131072,
    // The `db_soft_bytes` of `settings.json`, 1 GiB.
    soft_bytes: 1073741824,
    // The `turn_compact_turns` of `settings.json`, 64.
    compact_turns: 64,
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_tools_browser/",
    // The files of the cache of each store a test makes.
    slot_count: 8,
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
    // The first tools of `tools/list` as `API/mcp/tools.json` holds them.
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
        ' /$db/$key. A script is the row /_files/script/<name>.js.",' +
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
      '{"name":"console_run","description":"Run one command line in the' +
        " debug console's dash and return its output until the next" +
        ' prompt or the timeout. Debug mode.","inputSchema":' +
        '{"type":"object","properties":{"text":{"type":"string"},' +
        '"timeout_seconds":{"type":"number"}},"required":' +
        '["text","timeout_seconds"]},"_meta":{"xsjs":{"permit":true}}}',
      '{"name":"verbose_tail","description":"The last lines of a' +
        ' thread\'s verbose ring: ui, ai or server.","inputSchema":' +
        '{"type":"object","properties":{"thread":{"type":"string"},' +
        '"count":{"type":"integer"}},"required":["thread","count"]}}',
    ]),
    // The tools that follow the first ones, in order.
    added_tools: ["db_stats", "db_compact", "db_unload", "db_load"],
    // The wake types the tools sleep with.
    wake_types: [
      "tools.image_reply",
      "tools.media_reply",
      "tools.fetch_reply",
      "tools.render_reply",
      "tools.permit_reply",
      "tools.console_reply",
      "tools.tail_reply",
      "tools.snapshot_reply",
      "tools.value_reply",
    ],
    // The world table of the castle universe.
    world_sql:
      "CREATE TABLE world" +
      " (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT",
    // The region table of the castle world.
    region_sql:
      "CREATE TABLE region" +
      " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL DEFAULT 0) STRICT",
    // The result of the castle's two statements and the `seq` after them.
    castle_reply:
      '{"results":[{"columns":[],"rows":[],"changes":0},' +
      '{"columns":[],"rows":[],"changes":1}],"seq":1}',
    // The ref of the arrival scene of the castle turn.
    arrival_ref: "/castle_gatehouse/scene/arrival/1",
    // The result of `doc_put` for the arrival scene, its first version.
    doc_result: '{"ref":"/castle_gatehouse/scene/arrival/1"}',
    // The subtitle of the arrival scene of the castle turn.
    arrival_subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The `SHA-256` of the text `castle_world`.
    world_sha256:
      "6d0be246127ef7993924a9ce127c6fa6c093dca368163093ab31c80273336ecd",
    // The `SHA-256` of the arrival scene's ref as text.
    scene_sha256:
      "1e2806a1029564579de9739ef0014f0332c5a8026bca9373e473224a3b094d8b",
    // The ref of the step script, which advances the tide of a region.
    step_ref: "/_files/script/step_tide.js",
    // The step script, 319 bytes.
    step_script:
      "// Advances the tide by args.hours in the region table" +
      " of the world.\n" +
      'const results = engine.store.sql_run("castle_world", [\n' +
      '  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n' +
      '    params: [args.hours, "castle_gatehouse"]},\n' +
      "]);\n" +
      'engine.log("tide advanced by " + args.hours);\n' +
      "return {changes: results[0].changes};\n",
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
    // The image the provider answers, a checkerboard PNG, in base64.
    image_base64:
      "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4jwQYkAAuc" +
      "YZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg==",
    // The size of the image in bytes.
    image_size: 88,
    // The `SHA-256` of the image.
    image_sha256:
      "90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0",
    // The body of the image request of the castle turn.
    image_json:
      '{"model":"grok-2-image","prompt":"A rain dark castle gatehouse at' +
      " dusk seen from the far side of a moat, one lantern lit, painted," +
      ' wide still frame, no people","n":1,"response_format":"b64_json"}',
    // The result of `image_make`: the image's ref, size and digest.
    image_result:
      '{"key":"/_files/gatehouse/arrival.png","size":88,"sha256":' +
      '"90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0"}',
    // A url an image answer may hold instead of base64, a reserved name.
    image_url: "https://images.invalid/gatehouse/arrival.png",
    // The payload of the render of the arrival scene.
    render_payload:
      '{"scene":"/castle_gatehouse/scene/arrival/1","subtitle":"Mind the' +
      " moat. The gatehouse keeper has been expecting someone, though not" +
      ' necessarily you.","image":"/_files/gatehouse/arrival.png"}',
    // The hyperposition, the scene the boot renders.
    hyperposition_ref: "/metaverse/hyperposition/1",
    // The subtitle of the hyperposition.
    hyperposition_subtitle: "How can I help you?",
    // The payload of the render of the hyperposition, black.
    black_payload:
      '{"scene":"/metaverse/hyperposition/1",' +
      '"subtitle":"How can I help you?"}',
    // The payload of the first permit request, for `echo hi`.
    permit_payload:
      '{"permit":1,"tool":"browser.console_run",' +
      '"input":{"text":"echo hi","timeout_seconds":5}}',
    // The input message of ttyd's protocol that types `echo hi`, 9 bytes.
    console_input: "0echo hi\n",
    // The size of that message.
    input_size: 9,
    // The payload of the console read that waits for the prompt.
    read_payload: '{"until":"$ ","timeout_seconds":5}',
    // The output of `echo hi`: its echo, its line and the prompt.
    console_text: "echo hi\r\nhi\r\n$ ",
    // The result of `console_run` for that output, trimmed.
    console_result: '{"output":"hi\\n","timed_out":false}',
    // A verbose line the step script logs, with a time.
    verbose_line: { at: 1760800000000, text: "tide advanced by 1" },
  });

  // The stored text of the arrival scene, its encoded document as JSON.
  const arrival_text =
    '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"' +
    constants.arrival_subtitle +
    '","image":{"$ref":1}}';

  // The number of the last root a test made, so each store has its own.
  let root_count = 0;

  // A cache file double kept in memory, with the calls OPFS gives.
  class MemorySlot implements substrate.SlotHandle {
    // The storage, grown by doubling, zero beyond the file.
    #store = new Uint8Array(0);
    // The size of the file.
    #size = 0;

    // Reads into the buffer from the offset, as many bytes as the file has.
    read(buffer: Uint8Array, options: { at: number }): number {
      const left = this.#size - options.at;
      const count = Math.max(0, Math.min(buffer.length, left));
      buffer.set(this.#store.subarray(options.at, options.at + count));
      return count;
    }

    // Writes the buffer at the offset, the file growing with zeros.
    write(buffer: Uint8Array, options: { at: number }): number {
      const end = options.at + buffer.length;
      this.#room_make(end);
      this.#store.set(buffer, options.at);
      this.#size = Math.max(this.#size, end);
      return buffer.length;
    }

    // Sets the size, cutting the file or growing it with zeros.
    truncate(size: number): void {
      this.#room_make(size);
      this.#store.fill(0, Math.min(size, this.#size));
      this.#size = size;
    }

    // The size of the file.
    getSize(): number {
      return this.#size;
    }

    // Grows the storage by doubling until it holds the size.
    #room_make(size: number): void {
      if (size <= this.#store.length) {
        return;
      }
      const grown = new Uint8Array(Math.max(size, 2 * this.#store.length));
      grown.set(this.#store);
      this.#store = grown;
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

  // A queue double that keeps each line the tools submit or notify.
  class TasksDouble {
    // The lines sent, in order.
    readonly sent: SentLine[] = [];
    // The id of the last request.
    #last = 0;

    // Keeps a request and returns its id, counting from 1.
    task_submit(line: lines.Line, owner?: queue.ThreadName): number {
      this.#last += 1;
      this.sent.push({ line, owner, id: this.#last });
      return this.#last;
    }

    // Keeps a notification.
    line_notify(line: lines.Line, owner?: queue.ThreadName): void {
      this.sent.push({ line, owner, id: undefined });
    }
  }

  // A complete settings object with the values of `settings.json`.
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

  // The reader of a settings store: the values of `settings.json`, changed.
  function reader_make(
    changes: Partial<settings.Settings>,
  ): (id: string) => unknown {
    const values = new settings.ValueStore();
    values.value_set({ ...settings_make(), ...changes });
    return (id: string) => values.value_get(id);
  }

  // The reply the server gives a forwarded line: `seq` one past `since`.
  function answer_make(line: lines.Line): lines.Line {
    const type = jslb.field_get(line[0], "type") as string;
    const header = jslb.header_make(type, { reply: 1 });
    if (type === "db.create" || type === "db.drop") {
      return jslb.line_make(header, [], {});
    }
    const since = jslb.payload_of(line).since as number;
    return jslb.line_make(header, [], { seq: since + 1 });
  }

  // A reply line to request `id` of the type, with its payload and blobs.
  function reply_build(
    type: string,
    id: number,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type, { reply: id });
    return jslb.line_make(header, blobs, payload);
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // The JSON text of the payload of a line.
  function payload_text(line: lines.Line): string {
    return utility.json_text(jslb.payload_of(line));
  }

  // The text of each line, which leaves out the time.
  function lines_shown(kept: lines.VerboseLine[]): string[] {
    return kept.map((line) => line.text);
  }

  // Makes the castle world database, its region table and one region.
  function castle_make(store: substrate.Store): void {
    store.db_create("castle_world");
    store.sql_run("castle_world", [
      { sql: constants.region_sql, params: [] },
      {
        sql: "INSERT INTO region (name) VALUES (?)",
        params: ["castle_gatehouse"],
      },
    ]);
  }

  // A tool test: the module and pool read in `setUp`, its roots removed.
  class ToolCase extends unittest.TestCase {
    // The module the test page provides, read in `setUp`.
    #sqlite: substrate.SqliteModule | undefined = undefined;
    // The pool the test page provides, read in `setUp`.
    #pool: substrate.SqlitePool | undefined = undefined;
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made, each with the lines it forwarded.
    readonly #stores = new Map<substrate.Store, lines.Line[]>();

    // Reads the module and the pool the test page provides, and sets the key.
    setUp(): void {
      this.#sqlite = test_sqlite3;
      this.#pool = test_pool;
      provider.key_set(constants.key);
    }

    // Closes every database of the stores and removes the roots' files.
    tearDown(): void {
      for (const store of this.#stores.keys()) {
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

    // A store on a new root, with the tools registered on new doubles.
    bench_make(changes: Partial<settings.Settings> = {}): ToolBench {
      root_count += 1;
      const root = constants.root_prefix + String(root_count);
      this.#roots.push(root);
      const slots = Array.from(
        { length: constants.slot_count },
        () => new MemorySlot(),
      );
      const store = new substrate.Store(
        this.#sqlite as substrate.SqliteModule,
        this.#pool as substrate.SqlitePool,
        new substrate.CacheFiles(slots),
        root,
        constants.overflow_bytes,
        constants.compact_turns,
      );
      const forwarded: lines.Line[] = [];
      store.forward_set((line) => {
        forwarded.push(line);
      }, false);
      this.#stores.set(store, forwarded);
      const server = new ServerDouble();
      const tasks = new TasksDouble();
      tools_browser.tools_register(
        server as unknown as mcp.Server,
        store,
        tasks as unknown as queue.TaskQueue,
        constants.provider_owner,
        constants.info,
        reader_make(changes),
      );
      return { store, server, tasks };
    }

    // Answers every line a store forwarded, as the server would.
    lines_answer(store: substrate.Store): void {
      const forwarded = this.#stores.get(store) as lines.Line[];
      for (const line of forwarded.splice(0)) {
        store.forward_done(line, answer_make(line));
      }
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
  }

  // The tools and the wakes registered on the server.
  export class TestRegistry extends ToolCase {
    // The first tools come in their order.
    test_tools_recorded(): void {
      const bench = this.bench_make();
      const recorded = constants.recorded_tools.map(
        (text) => JSON.parse(text) as mcp.Tool,
      );
      const listed = bench.server.tools.slice(0, recorded.length);
      this.assertEqual(utility.json_text(listed), utility.json_text(recorded));
    }

    // The four tools of the administration of the databases follow.
    test_tools_added(): void {
      const bench = this.bench_make();
      const added = bench.server.tools.slice(constants.recorded_tools.length);
      this.assertEqual(
        added.map((tool) => tool.name),
        constants.added_tools,
      );
      this.assertEqual(added[0].inputSchema, {
        type: "object",
        properties: {},
      });
      const named = {
        type: "object",
        properties: { db: { type: "string" } },
        required: ["db"],
      };
      for (const tool of added.slice(1)) {
        this.assertEqual(tool.inputSchema, named);
      }
      for (const tool of added) {
        this.assertFalse("_meta" in tool);
      }
    }

    // Every tool has its function, and every wake type has its function.
    test_functions_registered(): void {
      const bench = this.bench_make();
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
    // `sql_run` answers the results and the `seq` of the castle's statements.
    test_sql_recorded(): void {
      const bench = this.bench_make();
      bench.store.db_create("castle");
      const result = this.tool_run(bench, "sql_run", {
        db: "castle",
        statements: [
          { sql: constants.world_sql, params: [] },
          {
            sql: "INSERT INTO world VALUES (?, ?)",
            params: ["castle_world", "The castle"],
          },
        ],
      });
      this.assertEqual(this.text_of(result), constants.castle_reply);
    }

    // `db_create` and `db_drop` add and remove a database.
    test_create_drop(): void {
      const bench = this.bench_make();
      const created = this.tool_run(bench, "db_create", { db: "alpha" });
      this.assertEqual(this.text_of(created), "{}");
      this.assertEqual(bench.store.db_list(), ["alpha"]);
      const dropped = this.tool_run(bench, "db_drop", { db: "alpha" });
      this.assertEqual(this.text_of(dropped), "{}");
      this.assertEqual(bench.store.db_list(), []);
    }
  }

  // The tools of values: put, get, delete and list.
  export class TestValues extends ToolCase {
    // `kv_put` writes the text's bytes and returns their known digests.
    test_put_recorded(): void {
      const bench = this.bench_make();
      for (const db of ["metaverse", "castle_world", "_files"]) {
        bench.store.db_create(db);
      }
      const step_sha256 = utility.sha256_hex(
        utility.utf8_encode(constants.step_script),
      );
      const cases: [string, string, string][] = [
        ["/metaverse/world", "castle_world", constants.world_sha256],
        ["/castle_world/scene", constants.arrival_ref, constants.scene_sha256],
        [constants.step_ref, constants.step_script, step_sha256],
      ];
      for (const [ref, text, sha256] of cases) {
        const db = substrate.ref_split(ref).db as string;
        const since = bench.store.seq_get(db);
        const result = this.tool_run(bench, "kv_put", { ref, text });
        const expected = utility.json_text({ sha256, seq: since + 1 });
        this.assertEqual(this.text_of(result), expected);
        const data = bench.store.kv_get(ref).data;
        this.assertEqual(data, utility.utf8_encode(text));
      }
    }

    // `kv_get` reads a value as its text.
    test_get_text(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      const text = String.fromCodePoint(0x4e2d, 0x6587, 0x1f600) + " text";
      bench.store.kv_put("/alpha/a", utility.utf8_encode(text));
      const result = this.tool_run(bench, "kv_get", { ref: "/alpha/a" });
      this.assertEqual(this.text_of(result), text);
    }

    // `kv_get` reads a value held in the cache.
    test_get_cached(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      const text = "x".repeat(constants.overflow_bytes + 1);
      this.tool_run(bench, "kv_put", { ref: "/alpha/big", text });
      const value = bench.store.kv_get("/alpha/big");
      this.assertEqual(typeof value.data, "string");
      const result = this.tool_run(bench, "kv_get", { ref: "/alpha/big" });
      this.assertEqual(this.text_of(result), text);
    }

    // `kv_get` of bytes that are not `UTF-8` throws.
    test_get_refused(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.kv_put("/alpha/raw", new Uint8Array([0xff]));
      this.raised_assert(i18n("utility.bytes_refused"), () =>
        this.tool_run(bench, "kv_get", { ref: "/alpha/raw" }),
      );
    }

    // `kv_delete` removes the row and returns the `seq` after.
    test_delete_seq(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.kv_put("/alpha/a", utility.utf8_encode("one"));
      const since = bench.store.seq_get("alpha");
      const result = this.tool_run(bench, "kv_delete", { ref: "/alpha/a" });
      const expected = utility.json_text({ seq: since + 1 });
      this.assertEqual(this.text_of(result), expected);
      this.raised_assert(i18n("substrate.key_missing", "a", "alpha"), () =>
        bench.store.kv_get("/alpha/a"),
      );
    }

    // `kv_list` returns the rows under the prefix.
    test_list_keys(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      for (const key of ["note/a", "note/b", "other"]) {
        bench.store.kv_put(`/alpha/${key}`, utility.utf8_encode(key));
      }
      const result = this.tool_run(bench, "kv_list", {
        db: "alpha",
        prefix: "note/",
      });
      const keys = bench.store.kv_list("alpha", "note/");
      this.assertEqual(this.text_of(result), utility.json_text({ keys }));
      this.assertEqual(
        keys.map((row) => row.k),
        ["note/a", "note/b"],
      );
    }
  }

  // The tools of documents.
  export class TestDocuments extends ToolCase {
    // The arrival scene is put, read back as its stored text, and found.
    test_doc_recorded(): void {
      const bench = this.bench_make();
      bench.store.db_create("castle_gatehouse");
      const body = JSON.parse(arrival_text) as lines.Document;
      const where = { db: "castle_gatehouse", id: "scene/arrival" };
      const put = this.tool_run(bench, "doc_put", { ...where, body });
      this.assertEqual(this.text_of(put), constants.doc_result);
      const read = this.tool_run(bench, "doc_get", {
        ref: constants.arrival_ref,
      });
      this.assertEqual(this.text_of(read), arrival_text);
      const head = this.tool_run(bench, "doc_head", where);
      this.assertEqual(this.text_of(head), constants.doc_result);
    }
  }

  // The tools that run scripts.
  export class TestScripts extends ToolCase {
    // The step script returns its change and its line.
    test_run_recorded(): void {
      const bench = this.bench_make();
      bench.store.db_create("_files");
      castle_make(bench.store);
      this.tool_run(bench, "kv_put", {
        ref: constants.step_ref,
        text: constants.step_script,
      });
      const result = this.tool_run(bench, "script_run", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(Object.keys(run), ["value", "lines"]);
      this.assertEqual(run.value, { changes: 1 });
      this.assertEqual(lines_shown(run.lines), [constants.step_line]);
    }

    // `script_debug` traces the store's call before the script's line.
    test_debug_traced(): void {
      const bench = this.bench_make();
      bench.store.db_create("_files");
      castle_make(bench.store);
      this.tool_run(bench, "kv_put", {
        ref: constants.step_ref,
        text: constants.step_script,
      });
      const result = this.tool_run(bench, "script_debug", {
        name: "step_tide",
        args: { hours: 1 },
      });
      const run = JSON.parse(this.text_of(result)) as script.ScriptResult;
      this.assertEqual(run.value, { changes: 1 });
      const trace = i18n(
        "script.trace_call",
        "sql_run",
        constants.step_arguments,
      );
      this.assertEqual(lines_shown(run.lines), [trace, constants.step_line]);
    }

    // A script that throws gives a result marked as an error.
    test_error_marked(): void {
      const bench = this.bench_make();
      bench.store.db_create("_files");
      const text = 'throw new Error("stop");\n';
      this.tool_run(bench, "kv_put", { ref: "/_files/script/stop.js", text });
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
    }
  }

  // The tool that makes images, through the provider and the UI.
  export class TestImages extends ToolCase {
    // The castle turn's image is asked for, kept, sent to the UI, returned.
    test_image_recorded(): void {
      const bench = this.bench_make();
      bench.store.db_create("_files");
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
      const expected = provider.image_request(
        constants.info.base_url,
        constants.key,
        {
          model: constants.info.image_model,
          prompt: constants.image_prompt,
          n: 1,
          response_format: "b64_json",
        },
      );
      this.assertEqual(
        utility.json_text(request.line),
        utility.json_text(expected),
      );
      const body = jslb.payload_of(request.line).json;
      this.assertEqual(utility.json_text(body), constants.image_json);
      const answer = reply_build("http.request", request.id as number, {
        status: 200,
        headers: { "content-type": "application/json" },
        json: { data: [{ b64_json: constants.image_base64 }] },
      });
      const keeping = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [answer]),
        1,
        "tools.media_reply",
      );
      const value = bench.store.kv_get(constants.image_ref);
      this.assertEqual(value.size, constants.image_size);
      this.assertEqual(value.sha256, constants.image_sha256);
      const media = bench.tasks.sent[1];
      this.assertEqual(media.owner, "ui");
      this.assertEqual(type_of(media.line), "media.store");
      this.assertEqual(jslb.payload_of(media.line), {
        k: constants.image_ref,
      });
      const blob = media.line[1] as lines.BlobHeader;
      this.assertEqual(jslb.field_get(blob, "size"), constants.image_size);
      this.assertEqual(blob.d, value.data);
      const kept = reply_build("media.store", media.id as number, {
        k: constants.image_ref,
        size: constants.image_size,
        sha256: constants.image_sha256,
      });
      const result = this.wake_run(bench, keeping, [kept]);
      this.assertEqual(this.text_of(result), constants.image_result);
    }

    // An image answered by url is downloaded by the UI and kept here.
    test_image_fetched(): void {
      const bench = this.bench_make();
      bench.store.db_create("_files");
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
      const answer = reply_build("http.request", request.id as number, {
        status: 200,
        headers: { "content-type": "application/json" },
        json: { data: [{ url: constants.image_url }] },
      });
      const fetching = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [answer]),
        1,
        "tools.fetch_reply",
      );
      const download = bench.tasks.sent[1];
      this.assertEqual(download.owner, "ui");
      this.assertEqual(type_of(download.line), "media.fetch");
      this.assertEqual(jslb.payload_of(download.line), {
        url: constants.image_url,
        k: constants.image_ref,
      });
      const image = utility.base64_decode(constants.image_base64);
      const fetched = reply_build(
        "media.fetch",
        download.id as number,
        {
          k: constants.image_ref,
          size: constants.image_size,
          sha256: constants.image_sha256,
        },
        [jslb.blob_make(image)],
      );
      const result = this.wake_run(bench, fetching, [fetched]);
      this.assertEqual(this.text_of(result), constants.image_result);
      const value = bench.store.kv_get(constants.image_ref);
      this.assertEqual(value.sha256, constants.image_sha256);
    }
  }

  // The tool that renders the current scene.
  export class TestRender extends ToolCase {
    // The render names the world's scene, the image and the subtitle.
    test_render_recorded(): void {
      const bench = this.bench_make();
      bench.store.db_create("metaverse");
      bench.store.db_create("castle_world");
      const world = utility.utf8_encode("castle_world");
      bench.store.kv_put("/metaverse/world", world);
      const scene = utility.utf8_encode(constants.arrival_ref);
      bench.store.kv_put("/castle_world/scene", scene);
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "render", {
          image: constants.image_ref,
          subtitle: constants.arrival_subtitle,
        }),
        0,
        "tools.render_reply",
      );
      const render = bench.tasks.sent[0];
      this.assertEqual(render.owner, "ui");
      this.assertEqual(type_of(render.line), "render");
      this.assertEqual(payload_text(render.line), constants.render_payload);
      const shown = reply_build("render", render.id as number, {});
      const result = this.wake_run(bench, asked, [shown]);
      this.assertEqual(this.text_of(result), "{}");
    }

    // A render with no image is black, as the boot's render is.
    test_render_black(): void {
      const bench = this.bench_make();
      bench.store.db_create("metaverse");
      const world = utility.utf8_encode("metaverse");
      bench.store.kv_put("/metaverse/world", world);
      const scene = utility.utf8_encode(constants.hyperposition_ref);
      bench.store.kv_put("/metaverse/scene", scene);
      this.sleep_check(
        bench,
        this.tool_run(bench, "render", {
          subtitle: constants.hyperposition_subtitle,
        }),
        0,
        "tools.render_reply",
      );
      const render = bench.tasks.sent[0];
      this.assertEqual(payload_text(render.line), constants.black_payload);
    }

    // Leaving a scene frees the `_files` values the new one does not name.
    test_render_evicts(): void {
      const each = constants.overflow_bytes + 1;
      const bench = this.bench_make({ files_browser_bytes: each });
      const store = bench.store;
      store.db_create("metaverse");
      store.db_create("_files");
      store.kv_put("/metaverse/world", utility.utf8_encode("metaverse"));
      const scenes: string[] = [];
      for (const name of ["a", "b"]) {
        const body = {
          0: { t: "scene" },
          1: `/_files/${name}.png`,
          subtitle: name,
          image: { $ref: 1 },
        };
        scenes.push(store.doc_put("metaverse", `scene/${name}`, body).ref);
      }
      for (const [index, name] of ["a", "b", "c", "d"].entries()) {
        const data = new Uint8Array(each).fill(index + 1);
        store.kv_put(`/_files/${name}.png`, data);
      }
      this.lines_answer(store);
      // Whether each image is held, in the order of their keys.
      const images_held = (): boolean[] =>
        ["a", "b", "c", "d"].map((name) =>
          store.kv_held(`/_files/${name}.png`),
        );
      // Makes the scene current and renders the image in it.
      const scene_show = (scene: string, image: string): void => {
        store.kv_put("/metaverse/scene", utility.utf8_encode(scene));
        this.lines_answer(store);
        this.tool_run(bench, "render", { image, subtitle: "" });
      };
      scene_show(scenes[0], "/_files/d.png");
      this.assertEqual(images_held(), [true, false, false, true]);
      store.kv_put("/_files/c.png", new Uint8Array(each).fill(9));
      this.lines_answer(store);
      scene_show(scenes[0], "/_files/d.png");
      this.assertEqual(images_held(), [true, false, true, true]);
      scene_show(scenes[1], "/_files/c.png");
      this.assertEqual(images_held(), [false, false, true, false]);
      this.assertEqual(store.kv_list("_files", "").length, 4);
      const renders = bench.tasks.sent.filter(
        (entry) => type_of(entry.line) === "render",
      );
      this.assertEqual(renders.length, 3);
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

    // The permit's reply with the choice, to the last request sent.
    choice_make(bench: ToolBench, choice: string): lines.Line {
      const ask = bench.tasks.sent[bench.tasks.sent.length - 1];
      const permit = jslb.payload_of(ask.line).permit;
      return reply_build("permit.ask", ask.id as number, { permit, choice });
    }

    // A command asks, runs and returns its output trimmed.
    test_console_recorded(): void {
      const bench = this.bench_make();
      const asked = this.permit_start(bench, "echo hi");
      const ask = bench.tasks.sent[0];
      this.assertEqual(ask.owner, "ui");
      this.assertEqual(type_of(ask.line), "permit.ask");
      this.assertEqual(payload_text(ask.line), constants.permit_payload);
      const reading = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [this.choice_make(bench, "accept")]),
        1,
        "tools.console_reply",
      );
      const [input, read] = bench.tasks.sent.slice(1);
      this.assertEqual(input.owner, "console");
      this.assertEqual(input.id, undefined);
      this.assertEqual(type_of(input.line), "console.input");
      const blob = input.line[1] as lines.BlobHeader;
      this.assertEqual(jslb.field_get(blob, "size"), constants.input_size);
      this.assertEqual(blob.d, utility.utf8_encode(constants.console_input));
      this.assertEqual(read.owner, "console");
      this.assertEqual(type_of(read.line), "console.read");
      this.assertEqual(payload_text(read.line), constants.read_payload);
      const output = reply_build("console.read", read.id as number, {
        text: constants.console_text,
        timed_out: false,
      });
      const result = this.wake_run(bench, reading, [output]);
      this.assertEqual(this.text_of(result), constants.console_result);
    }

    // A denial returns an error to the model and sends nothing on.
    test_permit_denied(): void {
      const bench = this.bench_make();
      const asked = this.permit_start(bench, "echo hi");
      const denied = this.wake_run(bench, asked, [
        this.choice_make(bench, "deny"),
      ]);
      const text = i18n("tools_browser.permit_denied", "browser.console_run");
      this.assertEqual(this.result_of(denied), {
        content: [{ type: "text", text }],
        isError: true,
      });
      this.assertEqual(bench.tasks.sent.length, 1);
    }

    // Outside debug mode the tool throws and asks the player nothing.
    test_debug_off(): void {
      const bench = this.bench_make({ debug: false });
      const text = i18n("tools_browser.debug_off", "browser.console_run");
      this.raised_assert(text, () =>
        this.tool_run(bench, "console_run", {
          text: "echo hi",
          timeout_seconds: 5,
        }),
      );
      this.assertEqual(bench.tasks.sent.length, 0);
    }

    // Always Allow runs this command and every later one with no ask.
    test_permit_always(): void {
      const bench = this.bench_make();
      const asked = this.permit_start(bench, "echo hi");
      this.sleep_check(
        bench,
        this.wake_run(bench, asked, [this.choice_make(bench, "always")]),
        1,
        "tools.console_reply",
      );
      this.sleep_check(
        bench,
        this.tool_run(bench, "console_run", {
          text: "pwd",
          timeout_seconds: 5,
        }),
        3,
        "tools.console_reply",
      );
      const later = bench.tasks.sent.slice(3);
      const types = later.map((entry) => type_of(entry.line));
      this.assertEqual(types, ["console.input", "console.read"]);
    }

    // Each permit asked has the next number, and Accept lasts one command.
    test_permits_counted(): void {
      const bench = this.bench_make();
      for (const number of [1, 2]) {
        const start = bench.tasks.sent.length;
        const asked = this.permit_start(bench, `echo ${number}`);
        const ask = bench.tasks.sent[start];
        this.assertEqual(jslb.payload_of(ask.line).permit, number);
        this.sleep_check(
          bench,
          this.wake_run(bench, asked, [this.choice_make(bench, "accept")]),
          start + 1,
          "tools.console_reply",
        );
      }
    }

    // A read that timed out keeps the output after the echo, with no prompt.
    test_console_expired(): void {
      const bench = this.bench_make();
      const asked = this.permit_start(bench, "sleep 600");
      const reading = this.sleep_check(
        bench,
        this.wake_run(bench, asked, [this.choice_make(bench, "accept")]),
        1,
        "tools.console_reply",
      );
      const read = bench.tasks.sent[2];
      const output = reply_build("console.read", read.id as number, {
        text: "sleep 600\r\n",
        timed_out: true,
      });
      const result = this.wake_run(bench, reading, [output]);
      const expected = utility.json_text({ output: "", timed_out: true });
      this.assertEqual(this.text_of(result), expected);
    }
  }

  // The verbose tail, the one verbose tool, as the runtime has no level.
  export class TestVerbose extends ToolCase {
    // No tool sets a verbose level, and none is registered to run one.
    test_level_gone(): void {
      const bench = this.bench_make();
      const names = bench.server.tools.map((tool) => tool.name);
      this.assertFalse(names.includes("verbose_level"));
      this.assertFalse(bench.server.runs.has("verbose_level"));
      this.assertTrue(names.includes("verbose_tail"));
    }

    // The tail is asked of the server and its lines are returned.
    test_tail_asked(): void {
      const bench = this.bench_make();
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "verbose_tail", { thread: "server", count: 5 }),
        0,
        "tools.tail_reply",
      );
      const request = bench.tasks.sent[0];
      this.assertEqual(request.owner, "server");
      this.assertEqual(type_of(request.line), "verbose.tail");
      const asked_text = '{"thread":"server","count":5}';
      this.assertEqual(payload_text(request.line), asked_text);
      const tail = { lines: [constants.verbose_line] };
      const reply = reply_build("verbose.tail", request.id as number, tail);
      const result = this.wake_run(bench, asked, [reply]);
      this.assertEqual(this.text_of(result), utility.json_text(tail));
    }
  }

  // The tools of the administration of the databases.
  export class TestAdmin extends ToolCase {
    // `db_stats` returns the measure of the open databases and the limit.
    test_stats_measured(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.db_create("beta");
      const big = new Uint8Array(constants.overflow_bytes + 1);
      bench.store.kv_put("/alpha/big", big);
      bench.store.kv_put("/beta/small", utility.utf8_encode("small"));
      const text = this.text_of(this.tool_run(bench, "db_stats", {}));
      const measured = bench.store.db_stats(constants.soft_bytes);
      this.assertEqual(text, utility.json_text(measured));
      const stats = JSON.parse(text) as substrate.StoreStats;
      this.assertEqual(
        stats.databases.map((entry) => entry.name),
        ["alpha", "beta"],
      );
      this.assertEqual(stats.databases[0].cache_bytes, big.length);
      this.assertEqual(stats.soft_bytes, constants.soft_bytes);
      this.assertFalse(stats.over);
    }

    // `db_compact` returns the bytes before and after, fewer after.
    test_compact_bytes(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.sql_run("alpha", [
        { sql: "CREATE TABLE note (x TEXT)", params: [] },
        {
          sql:
            "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL" +
            " SELECT i + 1 FROM n WHERE i < 2000)" +
            " INSERT INTO note SELECT printf('%0100d', i) FROM n",
          params: [],
        },
      ]);
      bench.store.sql_run("alpha", [{ sql: "DELETE FROM note", params: [] }]);
      const soft = constants.soft_bytes;
      const before = bench.store.db_stats(soft).databases[0].bytes;
      const result = this.tool_run(bench, "db_compact", { db: "alpha" });
      const after = bench.store.db_stats(soft).databases[0].bytes;
      const expected = utility.json_text({ before, after });
      this.assertEqual(this.text_of(result), expected);
      this.assertTrue(after < before);
    }

    // `db_unload` drops this side's copy, and a later read names `db_load`.
    test_unload_refused(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.kv_put("/alpha/a", utility.utf8_encode("one"));
      this.lines_answer(bench.store);
      const result = this.tool_run(bench, "db_unload", { db: "alpha" });
      this.assertEqual(this.text_of(result), "{}");
      this.assertEqual(bench.store.db_list(), []);
      this.raised_assert(i18n("substrate.db_unloaded", "alpha"), () =>
        this.tool_run(bench, "kv_get", { ref: "/alpha/a" }),
      );
    }

    // `db_load` asks the server's snapshot and opens its one blob.
    test_load_snapshot(): void {
      const bench = this.bench_make();
      const snapshot = this.snapshot_unloaded(bench);
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "db_load", { db: "alpha" }),
        0,
        "tools.snapshot_reply",
      );
      const request = bench.tasks.sent[0];
      this.assertEqual(request.owner, "server");
      this.assertEqual(type_of(request.line), "db.snapshot");
      this.assertEqual(payload_text(request.line), '{"db":"alpha"}');
      const reply = this.snapshot_reply(
        request,
        jslb.blob_make(snapshot.data),
        utility.sha256_hex(snapshot.data),
        snapshot.seq,
      );
      const result = this.wake_run(bench, asked, [reply]);
      this.assertEqual(bench.tasks.sent.length, 1);
      const expected = utility.json_text({ seq: snapshot.seq });
      this.assertEqual(this.text_of(result), expected);
      this.assertEqual(bench.store.db_list(), ["alpha"]);
      const read = this.tool_run(bench, "kv_get", { ref: "/alpha/a" });
      this.assertEqual(this.text_of(read), "one");
    }

    // `db_load` of a loaded database unloads it before asking, then opens it.
    test_load_loaded(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      bench.store.kv_put("/alpha/a", utility.utf8_encode("one"));
      const snapshot = bench.store.db_snapshot("alpha");
      this.lines_answer(bench.store);
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "db_load", { db: "alpha" }),
        0,
        "tools.snapshot_reply",
      );
      this.assertEqual(bench.store.db_list(), []);
      this.raised_assert(i18n("substrate.db_unloaded", "alpha"), () =>
        bench.store.kv_get("/alpha/a"),
      );
      const reply = this.snapshot_reply(
        bench.tasks.sent[0],
        jslb.blob_make(snapshot.data),
        utility.sha256_hex(snapshot.data),
        snapshot.seq,
      );
      const result = this.wake_run(bench, asked, [reply]);
      const expected = utility.json_text({ seq: snapshot.seq });
      this.assertEqual(this.text_of(result), expected);
      this.assertEqual(bench.store.db_list(), ["alpha"]);
    }

    // A snapshot streamed to the cache opens from its handle, sink digest kept.
    test_load_streamed(): void {
      const bench = this.bench_make();
      bench.store.db_create("alpha");
      const text = "y".repeat(constants.overflow_bytes);
      bench.store.kv_put("/alpha/text", utility.utf8_encode(text));
      const snapshot = bench.store.db_snapshot("alpha");
      this.lines_answer(bench.store);
      bench.store.db_unload("alpha");
      const size = snapshot.data.length;
      this.assertTrue(size > constants.overflow_bytes);
      const sink = bench.store.sink();
      const handle = sink.sink_open({ s: size });
      sink.sink_append(handle, snapshot.data);
      const sha256 = sink.sink_close(handle);
      const blob = jslb.blob_make(handle, undefined, { sha256 }, size);
      const result = this.blob_load(bench, blob, sha256, snapshot.seq);
      this.assertEqual(this.text_of(result), utility.json_text({ seq: 1 }));
      const read = this.tool_run(bench, "kv_get", { ref: "/alpha/text" });
      this.assertEqual(this.text_of(read), text);
    }

    // A snapshot whose bytes are not those of the digest it came with throws.
    test_load_digest(): void {
      const bench = this.bench_make();
      const snapshot = this.snapshot_unloaded(bench);
      const sha256 = utility.sha256_hex(snapshot.data);
      const wrong = "0".repeat(64);
      const blob = jslb.blob_make(snapshot.data);
      this.raised_assert(
        i18n("substrate.snapshot_digest", "alpha", sha256, wrong),
        () => this.blob_load(bench, blob, wrong, snapshot.seq),
      );
      this.assertEqual(bench.store.db_list(), []);
    }

    // A snapshot that opens at another `seq` than its reply's throws.
    test_load_desync(): void {
      const bench = this.bench_make();
      const snapshot = this.snapshot_unloaded(bench);
      const sent = snapshot.seq + 1;
      this.raised_assert(
        i18n("tools_browser.load_desync", "alpha", snapshot.seq, sent),
        () => this.load_run(bench, snapshot.data, sent),
      );
    }

    // A cached value or document the unload freed is asked of the server.
    test_value_fetched(): void {
      const bench = this.bench_make();
      const store = bench.store;
      store.db_create("alpha");
      const text = "x".repeat(constants.overflow_bytes + 1);
      store.kv_put("/alpha/big", utility.utf8_encode(text));
      const body = { 0: { t: "note" }, text };
      const ref = store.doc_put("alpha", "note", body).ref;
      this.lines_answer(store);
      const snapshot = store.db_snapshot("alpha");
      store.db_unload("alpha");
      this.load_run(bench, snapshot.data, snapshot.seq);
      this.assertFalse(store.kv_held("/alpha/big"));
      this.assertFalse(store.kv_held(ref));
      const cases: [string, string, string][] = [
        ["kv_get", "/alpha/big", text],
        ["doc_get", ref, utility.json_text(body)],
      ];
      for (const [tool, asked_ref, expected] of cases) {
        const start = bench.tasks.sent.length;
        const asking = this.sleep_check(
          bench,
          this.tool_run(bench, tool, { ref: asked_ref }),
          start,
          "tools.value_reply",
        );
        const request = bench.tasks.sent[start];
        this.assertEqual(request.owner, "server");
        this.assertEqual(type_of(request.line), "kv.get");
        this.assertEqual(jslb.field_get(request.line[0], "key"), asked_ref);
        const value = store.kv_get(asked_ref);
        const reply = reply_build(
          "kv.get",
          request.id as number,
          { size: value.size, sha256: value.sha256 },
          [jslb.blob_make(utility.utf8_encode(expected))],
        );
        const result = this.wake_run(bench, asking, [reply]);
        this.assertEqual(this.text_of(result), expected);
        this.assertTrue(store.kv_held(asked_ref));
        const again = this.tool_run(bench, tool, { ref: asked_ref });
        this.assertEqual(this.text_of(again), expected);
      }
      this.assertEqual(store.seq_get("alpha"), snapshot.seq);
    }

    // The snapshot of a database `alpha` with one value, then unloaded.
    snapshot_unloaded(bench: ToolBench): { data: Uint8Array; seq: number } {
      bench.store.db_create("alpha");
      bench.store.kv_put("/alpha/a", utility.utf8_encode("one"));
      const snapshot = bench.store.db_snapshot("alpha");
      this.lines_answer(bench.store);
      bench.store.db_unload("alpha");
      return snapshot;
    }

    // Runs `db_load` of `alpha` against bytes as the server sends them.
    load_run(bench: ToolBench, data: Uint8Array, seq: number): mcp.ToolResult {
      const sha256 = utility.sha256_hex(data);
      return this.blob_load(bench, jslb.blob_make(data), sha256, seq);
    }

    // Runs `db_load` of `alpha` against a reply of the blob, digest and `seq`.
    blob_load(
      bench: ToolBench,
      blob: lines.BlobHeader,
      sha256: lines.Sha256,
      seq: number,
    ): mcp.ToolResult {
      const start = bench.tasks.sent.length;
      const asked = this.sleep_check(
        bench,
        this.tool_run(bench, "db_load", { db: "alpha" }),
        start,
        "tools.snapshot_reply",
      );
      const request = bench.tasks.sent[start];
      const reply = this.snapshot_reply(request, blob, sha256, seq);
      return this.result_of(this.wake_run(bench, asked, [reply]));
    }

    // The server's `db.snapshot` reply: the digest and `seq` given, the blob.
    snapshot_reply(
      request: SentLine,
      blob: lines.BlobHeader,
      sha256: lines.Sha256,
      seq: number,
    ): lines.Line {
      this.assertEqual(type_of(request.line), "db.snapshot");
      const payload = { sha256, seq };
      return reply_build("db.snapshot", request.id as number, payload, [blob]);
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
