// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the worker's pieces of the engine in a fresh worker of the headless
// page, on a real queue of thread `ai` in synchronous mode. Its lanes to
// `server` and `ui` are linked local ports whose far ends are this file's, so
// that the chain and a turn each run within one call. The far end of `server`
// answers `mcp` lines from a real `mcp.Server` holding the gold's two tools,
// and answers `db.sync` with the restore lines of a real store it fills with
// the seed, which a value over `overflow_bytes` sends a `db.file` line for.
// The far end of `ui` answers each `render`.
//
// A realm takes one registration of the store, the tools and the chain, since
// each registers its line types in the realm's one dispatch table, so the
// chain tests share one bench, built at the first test, and one turn on the
// block's own script. The pieces that register nothing run on a store of their
// own, which each test empties first. test_engine_image.ts runs `bench_build`
// on a scene with an image, in a realm of its own.

namespace test_engine {
  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // The test slots, files cleared at start that no cache holds.
  declare const test_slots: substrate.SlotHandle[];

  // The gold, the threads, the settings and the names the tests use.
  const constants = Object.freeze({
    gold_id: "typescript.test_engine",
    thread: "ai" as const,
    server_thread: "server" as const,
    ui_thread: "ui" as const,
    overflow_setting: "overflow_bytes",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    seed_root: "/test_engine_seed",
    pieces_root: "/test_engine_pieces",
    // The test slots the seed's cache takes, the engine's cache the others.
    seed_slots: 4,
    far_name: "xsjs-server",
    far_version: "0",
    mcp_type: "mcp",
    sync_type: "db.sync",
    render_type: "render",
    restore_type: "db.restore",
    file_type: "db.file",
    metaverse: "metaverse",
    world_ref: "/metaverse/world",
    scene_ref: "/metaverse/scene",
    script_ref: "/_files/provider/script.json",
    // The value over `overflow_bytes`, which goes as a `db.file` line.
    large_ref: "/_files/test_engine/large",
    // The database of that value, which a piece restores with the file lost.
    files_db: "_files",
    // The image a piece reads, in the database every piece test has.
    image_ref: "/metaverse/place.png",
    // The document id of the scenes the pieces read.
    place_id: "place",
    // The file of the engine's `metaverse` in the pool, under its root.
    engine_file: "/engine/metaverse.sqlite",
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // The test's end of a lane: its linked local port and the lines that came.
  export interface LaneEnd {
    port: queue.LocalPort;
    came: lines.Line[];
  }

  // The store of the seed and the cache that holds its large value.
  interface SeedParts {
    store: substrate.Store;
    cache: substrate.CacheFiles;
  }

  // The real parts the chain tests share, and the lines of the chain alone.
  export interface EngineBench {
    store: substrate.Store;
    tools: engine.ToolParts;
    server: LaneEnd;
    ui: LaneEnd;
    chain_server: lines.Line[];
    chain_ui: lines.Line[];
  }

  // The lines of the block's one turn on each lane.
  interface TurnRecord {
    server: lines.Line[];
    ui: lines.Line[];
  }

  // The bench of the realm, built at the first test that needs it.
  let bench_kept: EngineBench | undefined = undefined;

  // The turn of the bench, run at the first test that needs it.
  let turn_kept: TurnRecord | undefined = undefined;

  // The store of the pieces, built at the first test that needs it.
  let pieces_kept: substrate.Store | undefined = undefined;

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A text of this module's gold.
  function gold_text(name: string): string {
    return harness.gold_get(`${constants.gold_id}.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
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

  // Joins the queue to the thread, each line kept, then given to `answer`.
  function lane_make(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
    answer: (end: LaneEnd, line: lines.Line) => void,
  ): LaneEnd {
    const near = new queue.LocalPort();
    const port = new queue.LocalPort(near);
    const end: LaneEnd = { port, came: [] };
    port.line_receive((line) => {
      end.came.push(line);
      answer(end, line);
    });
    tasks.port_add(thread, near);
    return end;
  }

  // A store under the root on a queue of its own, its pushes kept by a lane.
  function store_make(
    root: string,
    cache: substrate.CacheFiles,
  ): substrate.Store {
    const tasks = new queue.TaskQueue(constants.thread, {}, true);
    lane_make(tasks, constants.server_thread, () => undefined);
    return new substrate.Store(
      test_sqlite3,
      test_pool,
      cache,
      root,
      harness.setting_get(constants.overflow_setting) as number,
      harness.setting_get(constants.blob_setting) as number,
      harness.setting_get(constants.compact_setting) as number,
      tasks,
    );
  }

  // The bytes of the value over `overflow_bytes`.
  export function large_bytes(): Uint8Array {
    const overflow = harness.setting_get(constants.overflow_setting) as number;
    return new Uint8Array(overflow + 1);
  }

  // A store filled as a new root: the databases, the scene, prompt and script.
  function seed_make(scene: lines.Document, script: unknown): SeedParts {
    const cache = new substrate.CacheFiles(
      test_slots.slice(0, constants.seed_slots),
    );
    const store = store_make(constants.seed_root, cache);
    for (const name of gold_value("databases") as string[]) {
      store.db_create(name);
    }
    store.sql_run(constants.metaverse, [
      { sql: gold_value("universe_sql") as string, params: [] },
    ]);
    const { ref } = store.doc_put(constants.metaverse, "hyperposition", scene);
    store.doc_put(
      constants.metaverse,
      "prompt",
      gold_value("prompt") as lines.Document,
    );
    const world = utility.utf8_encode(constants.metaverse);
    store.kv_put(constants.world_ref, world);
    store.kv_put(constants.scene_ref, utility.utf8_encode(ref));
    const text = utility.json_text(script);
    store.kv_put(constants.script_ref, utility.utf8_encode(text));
    store.kv_put(constants.large_ref, large_bytes());
    return { store, cache };
  }

  // The `db.restore` line of a database, then its `db.file` lines.
  function restore_lines(seed: SeedParts, db: string): lines.Line[] {
    const full = settings.names_full();
    const image = seed.store.db_snapshot(db);
    const limit = harness.setting_get(constants.blob_setting) as number;
    const restore = jslb.line_make(
      jslb.header_make(constants.restore_type, { full }),
      [jslb.blob_make(image.data)],
      { db, files: image.files.length },
    );
    const files = image.files.map((name) =>
      jslb.line_make(
        jslb.header_make(constants.file_type, { full }),
        [jslb.blob_make(seed.cache.cache_read(name, 0, limit))],
        { db },
      ),
    );
    return [restore, ...files];
  }

  // The real server that answers the far end's `mcp` lines, the gold's tools.
  function far_make(): mcp.Server {
    const far = new mcp.Server(constants.far_name, constants.far_version);
    for (const tool of gold_value("server_tools") as mcp.Tool[]) {
      far.tool_register(tool, () => ({ content: [] }));
    }
    return far;
  }

  // Answers an `mcp` request or `db.sync` as the server does, keeps the rest.
  function server_answer(
    seed: SeedParts,
    far: mcp.Server,
    end: LaneEnd,
    line: lines.Line,
  ): void {
    const type = type_of(line);
    if (type === constants.mcp_type) {
      const message = jslb.payload_of(line) as unknown as mcp.Message;
      const answer = far.message_handle(message);
      if (answer !== undefined) {
        const fields = answer as unknown as FieldTable;
        end.port.line_post(dispatch.reply_make(line, fields), []);
      }
    } else if (type === constants.sync_type) {
      const databases = seed.store.db_list();
      for (const db of databases) {
        for (const piece of restore_lines(seed, db)) {
          end.port.line_post(piece, []);
        }
      }
      end.port.line_post(dispatch.reply_make(line, { databases }), []);
    }
  }

  // Answers a `render` as the UI thread does, leaving any other line waiting.
  function ui_answer(end: LaneEnd, line: lines.Line): void {
    if (type_of(line) === constants.render_type) {
      end.port.line_post(dispatch.reply_make(line, {}), []);
    }
  }

  // What the boot hands the worker's program, the first line given.
  function start_make(
    first: lines.Line,
    cache: substrate.CacheFiles,
  ): boot.WorkerStart {
    return {
      first,
      base_url: location.href,
      sqlite3: test_sqlite3,
      pool: test_pool,
      cache,
    };
  }

  // Builds the store, the tools and the chain, and runs it till it waits.
  export function bench_build(
    scene: lines.Document,
    script: unknown,
  ): EngineBench {
    const seed = seed_make(scene, script);
    const far = far_make();
    const owners = worker_ai.owners_make();
    const tasks = new queue.TaskQueue(constants.thread, owners, true);
    const server = lane_make(
      tasks,
      constants.server_thread,
      (end, line) => server_answer(seed, far, end, line),
    );
    const ui = lane_make(tasks, constants.ui_thread, ui_answer);
    const cache = new substrate.CacheFiles(
      test_slots.slice(constants.seed_slots),
    );
    const start = start_make(gold_line("first"), cache);
    const store = engine.store_build(tasks, start);
    const tools = engine.tools_build(tasks, store);
    engine.chain_register(tasks, store, tools);
    engine.chain_start(tasks);
    return {
      store,
      tools,
      server,
      ui,
      chain_server: [...server.came],
      chain_ui: [...ui.came],
    };
  }

  // The bench of the realm, built at its first use.
  function bench_get(): EngineBench {
    if (bench_kept === undefined) {
      bench_kept = bench_build(
        gold_value("hyperposition") as lines.Document,
        gold_value("script"),
      );
    }
    return bench_kept;
  }

  // The lines of the turn in which the player says 1, run at its first use.
  function turn_get(): TurnRecord {
    if (turn_kept === undefined) {
      const { server, ui } = bench_get();
      const server_start = server.came.length;
      const ui_start = ui.came.length;
      ui.port.line_post(gold_line("say_one"), []);
      turn_kept = {
        server: server.came.slice(server_start),
        ui: ui.came.slice(ui_start),
      };
    }
    return turn_kept;
  }

  // The store of the pieces, built at its first use.
  function pieces_get(): substrate.Store {
    if (pieces_kept === undefined) {
      const cache = new substrate.CacheFiles([]);
      pieces_kept = store_make(constants.pieces_root, cache);
    }
    return pieces_kept;
  }

  // Writes a document and makes it the scene on screen. Returns its ref.
  function scene_write(store: substrate.Store, name: string): lines.DocRef {
    const body = gold_value(`scenes.${name}`) as lines.Document;
    const { metaverse, place_id } = constants;
    const { ref } = store.doc_put(metaverse, place_id, body);
    store.kv_put(constants.scene_ref, utility.utf8_encode(ref));
    return ref;
  }

  // The chain and a turn on the bench, seen from the far ends of its lanes.
  export class TestEngineChain extends unittest.TestCase {
    // The server's lane holds the handshake, then the sync, in that order.
    test_server_lines(): void {
      const { chain_server } = bench_get();
      this.assertEqual(chain_server, gold_value("chain_server"));
    }

    // The agent lists the browser's tools, then the server's under `server`.
    test_tools_listed(): void {
      const tools = bench_get().tools.clients.tools_cached();
      const names = tools.map((tool) => tool.name);
      this.assertEqual(names, gold_value("tool_names"));
    }

    // The store sits under the root `/engine` of the pool it was given.
    test_store_root(): void {
      bench_get();
      this.assertIn(constants.engine_file, test_pool.getFileNames());
    }

    // The sync's wake finds every database of the seed restored.
    test_databases_restored(): void {
      const { store } = bench_get();
      this.assertEqual(store.db_list(), gold_value("databases"));
    }

    // A `db.file` line kept its value in the cache the start gave the store.
    test_file_restored(): void {
      const { ui } = bench_get();
      const before = ui.came.length;
      ui.port.line_post(gold_line("get_large"), []);
      const reply = ui.came[before];
      const { size, sha256 } = jslb.payload_of(reply);
      const expected = large_bytes();
      this.assertEqual(size, expected.length);
      this.assertEqual(sha256, utility.sha256_hex(expected));
    }

    // The UI thread's store requests reach the store, its handlers registered.
    test_store_requests(): void {
      const { ui } = bench_get();
      const before = ui.came.length;
      ui.port.line_post(gold_line("list_world"), []);
      const keys = jslb.payload_of(ui.came[before]).keys as lines.KvRow[];
      this.assertEqual(
        keys.map((row) => row.k),
        gold_value("world_keys"),
      );
    }

    // The first render reaches the UI lane holding the seed's remark.
    test_first_render(): void {
      const { chain_ui } = bench_get();
      this.assertEqual(chain_ui, [gold_line("first_render")]);
    }

    // The scripted port needs a key, which the chain sets to the fixed text.
    test_provider_key(): void {
      bench_get();
      this.assertEqual(provider.key_get(), gold_text("provider_key"));
    }

    // The turn's tool renders on the UI lane, then the turn ends there.
    test_turn_ended(): void {
      const { ui } = turn_get();
      this.assertEqual(ui, [
        gold_line("turn_render"),
        gold_line("turn_answer"),
      ]);
    }

    // The turn's rows go to the server as commits.
    test_turn_committed(): void {
      const { server } = turn_get();
      this.assertEqual(server.map(type_of), gold_value("turn_commits"));
    }
  }

  // The pieces that register nothing, and the module itself.
  export class TestEnginePieces extends unittest.TestCase {
    // Starts each test on an empty store whose world is the metaverse.
    setUp(): void {
      const store = pieces_get();
      for (const name of store.db_list()) {
        store.db_drop(name);
      }
      store.db_create(constants.metaverse);
      store.kv_put(
        constants.world_ref,
        utility.utf8_encode(constants.metaverse),
      );
    }

    // The module is a frozen object holding its functions and nothing else.
    test_module_frozen(): void {
      this.assertTrue(Object.isFrozen(engine));
      this.assertEqual(Object.keys(engine).sort(), gold_value("module_names"));
    }

    // A false `provider.scripted` throws before anything is built.
    test_scripted_off(): void {
      const owners = worker_ai.owners_make();
      const tasks = new queue.TaskQueue(constants.thread, owners, true);
      const cache = new substrate.CacheFiles([]);
      const start = start_make(gold_line("first_unscripted"), cache);
      const error = thrown_get(() => engine.worker_run(tasks, start));
      this.assertEqual(error.message, gold_text("scripted_off"));
    }

    // A reply naming the store's databases passes.
    test_sync_same(): void {
      engine.sync_check(pieces_get(), gold_line("sync_same"));
    }

    // A reply naming others throws, naming both lists.
    test_sync_differs(): void {
      const line = gold_line("sync_other");
      const error = thrown_get(() => engine.sync_check(pieces_get(), line));
      this.assertEqual(error.message, gold_text("sync_differs"));
    }

    // A scene with no image renders its subtitle alone.
    test_render_plain(): void {
      const store = pieces_get();
      scene_write(store, "plain");
      const line = engine.render_make(store);
      this.assertEqual(line, gold_line("render_plain"));
    }

    // A scene's image renders as the reference its document holds.
    test_render_image(): void {
      const store = pieces_get();
      scene_write(store, "pictured");
      const line = engine.render_make(store);
      this.assertEqual(line, gold_line("render_image"));
    }

    // An image's line carries its bytes, read out of the store, under its ref.
    test_media_line(): void {
      const store = pieces_get();
      const data = utility.utf8_encode(gold_text("image_text"));
      store.kv_put(constants.image_ref, data);
      const expected = gold_line("media_small");
      expected[1] = { size: data.length, d: data };
      const line = engine.media_make(store, constants.image_ref);
      this.assertEqual(line, expected);
    }

    // A row whose cache file is lost fails as the store says.
    test_media_lost(): void {
      const { files_db, large_ref } = constants;
      const image = bench_get().store.db_snapshot(files_db);
      const store = pieces_get();
      store.db_restore(files_db, image.data, []);
      const error = thrown_get(() => engine.media_make(store, large_ref));
      const sha256 = utility.sha256_hex(large_bytes());
      this.assertEqual(
        error.message,
        gold_text("file_lost").replaceAll("{1}", sha256),
      );
    }

    // A key with no row fails as the store says.
    test_media_unknown(): void {
      const { image_ref } = constants;
      const error = thrown_get(() =>
        engine.media_make(pieces_get(), image_ref),
      );
      this.assertEqual(error.message, gold_text("key_missing"));
    }

    // A document with no subtitle is not a scene.
    test_subtitle_missing(): void {
      const store = pieces_get();
      scene_write(store, "untitled");
      const error = thrown_get(() => engine.render_make(store));
      this.assertEqual(error.message, gold_text("scene_invalid"));
    }

    // A document whose image is not text is not a scene.
    test_image_invalid(): void {
      const store = pieces_get();
      scene_write(store, "numbered");
      const error = thrown_get(() => engine.render_make(store));
      this.assertEqual(error.message, gold_text("scene_invalid"));
    }
  }
}

Object.freeze(test_engine);
