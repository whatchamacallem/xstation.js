// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of script.ts, a block of group B in the AI worker, on a real store:
// the sqlite3.wasm module and OPFS pool the bring up sets as globals, a cache
// over the first of the open OPFS files it gives the block as `test_slots`,
// cleared, and a real `queue.TaskQueue` whose server lane ends at the test's
// own receiver, which keeps the store's pushes. Each test puts its scripts
// in the store at the ref of the gold: the step script that advances a
// region's tide, run and traced, every line a run keeps, a script read from
// the cache, the engine object and its store of routine methods, the
// exceptions a run returns and the errors it throws. The trace texts, the
// store's refusals and the pushes the runs make are entries of the gold
// record, test_settings.json.

namespace test_script {
  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // The installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // The open OPFS files of this block, cleared, a global the bring up sets.
  declare const test_slots: readonly substrate.SlotHandle[];

  // The names, texts and calls the tests use.
  const constants = Object.freeze({
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
    // The world the step script writes, its region table and its one row.
    world_db: "castle_world",
    region_sql:
      "CREATE TABLE region" +
      " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL) STRICT",
    region_row: "INSERT INTO region VALUES ('castle_gatehouse', 0)",
    tide_sql: "SELECT tide FROM region WHERE name = 'castle_gatehouse'",
    // The routine methods of `engine.store`, in the order of the stub.
    store_names: Object.freeze([
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
    ]),
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_script/",
    // The files of each store's cache: one holds a script cached whole.
    cache_slots: 1,
    // The thread of each store's queue and the owner its pushes go to.
    thread: "ai" as const,
    server: "server" as const,
    // The settings of a store and of the mode of its queue.
    synchronous_setting: "queue_synchronous",
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
  });

  // The number of the last root a test made, so that each store has its own.
  let root_count = 0;

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_script.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return structuredClone(
      harness.gold_get(`typescript.test_script.lines.${name}`),
    ) as lines.Line;
  }

  // A push of the gold, its blob 1 the bytes and their size in full names.
  function push_bytes(name: string, data: Uint8Array): lines.Line {
    const line = gold_line(name);
    line[1] = { size: data.length, d: data };
    return line;
  }

  // The ref of the row of a script, by the gold's form of it.
  function script_ref(name: string): string {
    const form = harness.gold_get("typescript.test_script.script_ref");
    return (form as string).replaceAll("{0}", name);
  }

  // The database the scripts' rows are in, the one their refs name.
  function files_db(): string {
    return substrate.ref_split(script_ref("")).db as string;
  }

  // The `overflow_bytes` of `settings.json`, which the test stores take.
  function overflow_get(): number {
    return harness.setting_get(constants.overflow_setting) as number;
  }

  // The `UTF-8` bytes of text.
  function bytes_text(text: string): Uint8Array {
    return new TextEncoder().encode(text);
  }

  // The text of each line, which leaves out the time.
  function lines_shown(kept: lines.VerboseLine[]): string[] {
    return kept.map((line) => line.text);
  }

  // The text of the error JSON throws for a value it has no text for.
  function refusal_text(value: unknown): string {
    try {
      JSON.stringify(value);
    } catch (error) {
      return String(error);
    }
    throw new Error("JSON wrote the value.");
  }

  // A script test on stores of its own, each root's files then removed.
  class ScriptCase extends unittest.TestCase {
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made, each with the pushes its server lane took.
    readonly #stores = new Map<substrate.Store, lines.Line[]>();

    // Closes every database of the stores and removes the roots' files.
    tearDown(): void {
      for (const store of this.#stores.keys()) {
        for (const name of store.db_list()) {
          store.db_close(name);
        }
      }
      for (const root of this.#roots) {
        for (const file of test_pool.getFileNames()) {
          if (file.startsWith(`${root}/`)) {
            test_pool.unlink(file);
          }
        }
      }
    }

    // A store on a new root, its scripts' database created, its pushes kept.
    store_make(): substrate.Store {
      root_count += 1;
      const root = constants.root_prefix + String(root_count);
      this.#roots.push(root);
      if (test_slots.length < constants.cache_slots) {
        throw new Error(
          `test_slots holds ${test_slots.length} files,` +
            ` fewer than ${constants.cache_slots}`,
        );
      }
      const slots = test_slots.slice(0, constants.cache_slots);
      for (const slot of slots) {
        slot.truncate(0);
      }
      const pushed: lines.Line[] = [];
      const far = new queue.LocalPort();
      far.line_receive((line) => {
        pushed.push(line);
      });
      const synchronous = harness.setting_get(
        constants.synchronous_setting,
      ) as boolean;
      const tasks = new queue.TaskQueue(constants.thread, {}, synchronous);
      tasks.port_add(constants.server, new queue.LocalPort(far));
      const store = new substrate.Store(
        test_sqlite3,
        test_pool,
        new substrate.CacheFiles(slots),
        root,
        overflow_get(),
        harness.setting_get(constants.compact_setting) as number,
        tasks,
      );
      this.#stores.set(store, pushed);
      store.db_create(files_db());
      return store;
    }

    // A new store holding the script of the name, its pushes so far let go.
    store_script(name: string, text: string): substrate.Store {
      const store = this.store_make();
      store.kv_put(script_ref(name), bytes_text(text));
      this.pushes_taken(store);
      return store;
    }

    // The pushes a store's server lane took, which are then let go.
    pushes_taken(store: substrate.Store): lines.Line[] {
      return (this.#stores.get(store) as lines.Line[]).splice(0);
    }

    // Creates the world of the step script, its tide 0, its pushes let go.
    world_make(store: substrate.Store): void {
      store.db_create(constants.world_db);
      store.sql_run(constants.world_db, [
        { sql: constants.region_sql, params: [] },
        { sql: constants.region_row, params: [] },
      ]);
      this.pushes_taken(store);
    }

    // The tide of the gatehouse in the world of the step script.
    tide_get(store: substrate.Store): unknown {
      const statement = { sql: constants.tide_sql, params: [] };
      return store.sql_run(constants.world_db, [statement])[0].rows;
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

  // Runs of a script: the value, the kept lines, the trace and the engine.
  export class TestRun extends ScriptCase {
    // The step script reads its row, runs its statement, returns and logs.
    test_step_recorded(): void {
      const store = this.store_script("step_tide", constants.step_script);
      this.world_make(store);
      const result = script.script_run(
        store,
        "step_tide",
        { hours: 1 },
        false,
      );
      this.assertEqual(Object.keys(result), ["value", "lines"]);
      this.assertEqual(result.value, { changes: 1 });
      this.assertEqual(lines_shown(result.lines), [constants.step_line]);
      this.assertEqual(Object.keys(result.lines[0]), ["at", "text"]);
      this.assertEqual(typeof result.lines[0].at, "number");
      this.assertEqual(this.tide_get(store), [[1]]);
      this.assertEqual(this.pushes_taken(store), [
        gold_line("push_sql_run_tide"),
      ]);
    }

    // A traced run traces the call of the store before the script's line.
    test_step_traced(): void {
      const store = this.store_script("step_tide", constants.step_script);
      this.world_make(store);
      const result = script.script_run(store, "step_tide", { hours: 1 }, true);
      this.assertEqual(result.value, { changes: 1 });
      this.assertEqual(lines_shown(result.lines), [
        gold_text("script_trace_call_sql_run"),
        constants.step_line,
      ]);
      this.assertEqual(this.tide_get(store), [[1]]);
    }

    // A run keeps every line it logs, in order, traced or not.
    test_lines_kept(): void {
      const store = this.store_script(
        "lines",
        'engine.log("zero");\n' +
          'engine.log("one");\n' +
          'engine.log("two");\n' +
          "return null;\n",
      );
      for (const trace of [false, true]) {
        const result = script.script_run(store, "lines", {}, trace);
        this.assertEqual(result.value, null);
        this.assertEqual(lines_shown(result.lines), ["zero", "one", "two"]);
      }
    }

    // A line the script logs to the thread is one of the run's lines.
    test_thread_logged(): void {
      const store = this.store_script(
        "thread",
        'engine.log("to the thread");\n',
      );
      const result = script.script_run(store, "thread", {}, false);
      this.assertEqual(lines_shown(result.lines), ["to the thread"]);
    }

    // Only a traced run traces the calls of the store.
    test_trace_only(): void {
      const store = this.store_script(
        "list",
        "return engine.store.db_list();\n",
      );
      const plain = script.script_run(store, "list", {}, false);
      this.assertEqual(plain, { value: [files_db()], lines: [] });
      const traced = script.script_run(store, "list", {}, true);
      this.assertEqual(traced.value, [files_db()]);
      const trace = gold_text("script_trace_call_db_list");
      this.assertEqual(lines_shown(traced.lines), [trace]);
    }

    // A trace shows the bytes an argument holds by their count.
    test_bytes_counted(): void {
      const store = this.store_script(
        "note",
        'const data = new TextEncoder().encode("abc");\n' +
          'engine.store.kv_put("/_files/note", data);\n',
      );
      const result = script.script_run(store, "note", {}, true);
      const trace = gold_text("script_trace_call_kv_put");
      this.assertEqual(lines_shown(result.lines), [trace]);
      const data = bytes_text("abc");
      this.assertEqual(store.kv_get("/_files/note").data, data);
      this.assertEqual(this.pushes_taken(store), [
        push_bytes("push_kv_put_note", data),
      ]);
    }

    // The arguments reach the script as they were given.
    test_args_passed(): void {
      const store = this.store_script("echo", "return args;\n");
      const args = { list: [1, "two"], flag: true };
      const result = script.script_run(store, "echo", args, false);
      this.assertEqual(result.value, args);
    }

    // The engine is frozen and holds the store, the log and `i18n`.
    test_engine_frozen(): void {
      const store = this.store_script(
        "engine",
        "return [Object.isFrozen(engine), Object.keys(engine)," +
          " typeof engine.i18n];\n",
      );
      this.assertEqual(script.script_run(store, "engine", {}, false).value, [
        true,
        ["store", "log", "i18n"],
        "function",
      ]);
    }

    // The store is frozen and holds the routine methods only, traced or not.
    test_store_routine(): void {
      const store = this.store_script(
        "methods",
        "return [Object.isFrozen(engine.store)," +
          " Object.keys(engine.store)];\n",
      );
      for (const trace of [false, true]) {
        const result = script.script_run(store, "methods", {}, trace);
        this.assertEqual(result.value, [true, [...constants.store_names]]);
      }
    }

    // The store's machinery is not there: calling it is the engine's error.
    test_store_machinery(): void {
      for (const call of ['db_snapshot("_files")', "sink()"]) {
        const store = this.store_script(
          "machinery",
          `return engine.store.${call};\n`,
        );
        const result = script.script_run(store, "machinery", {}, false);
        this.assertTrue(String(result.error).startsWith("TypeError: "));
        this.assertFalse("value" in result);
      }
    }

    // A script the store holds in its cache is read from the cache.
    test_cached_script(): void {
      const text = "// " + "x".repeat(overflow_get()) + "\nreturn 7;\n";
      const store = this.store_script("large", text);
      const held = store.kv_get(script_ref("large"));
      this.assertEqual(typeof held.data, "string");
      this.assertEqual(held.size, bytes_text(text).length);
      this.assertEqual(script.script_run(store, "large", {}, false).value, 7);
    }
  }

  // What a run returns for an exception, and what it throws itself.
  export class TestErrors extends ScriptCase {
    // An `Error` the script throws comes back with its text and stack.
    test_error_returned(): void {
      const store = this.store_script("far", 'throw new RangeError("far");\n');
      const result = script.script_run(store, "far", {}, false);
      this.assertEqual(Object.keys(result), ["error", "stack", "lines"]);
      this.assertEqual(result.error, "RangeError: far");
      this.assertIn("RangeError: far", result.stack);
      this.assertEqual(result.lines, []);
    }

    // A value that is no `Error` comes back as its text, with no stack.
    test_value_thrown(): void {
      const store = this.store_script("plain", 'throw "plain";\n');
      this.assertEqual(script.script_run(store, "plain", {}, false), {
        error: "plain",
        lines: [],
      });
    }

    // A script that does not compile returns its `SyntaxError`.
    test_syntax_returned(): void {
      const store = this.store_script("broken", "return (;\n");
      const result = script.script_run(store, "broken", {}, false);
      this.assertTrue(String(result.error).startsWith("SyntaxError: "));
      this.assertFalse("value" in result);
    }

    // The lines logged before the exception are kept.
    test_lines_before(): void {
      const store = this.store_script(
        "late",
        'engine.log("before");\nthrow new Error("after");\n',
      );
      const result = script.script_run(store, "late", {}, false);
      this.assertEqual(result.error, "Error: after");
      this.assertEqual(lines_shown(result.lines), ["before"]);
    }

    // A value JSON cannot carry is the run's exception, not the tool's.
    test_value_uncarried(): void {
      const store = this.store_script(
        "uncarried",
        'engine.log("before");\nreturn BigInt(1);\n',
      );
      const result = script.script_run(store, "uncarried", {}, false);
      this.assertEqual(result.error, refusal_text(BigInt(1)));
      this.assertEqual(typeof result.stack, "string");
      this.assertFalse("value" in result);
      this.assertEqual(lines_shown(result.lines), ["before"]);
    }

    // NaN and the infinities are returned, as no decoder lets them in.
    test_value_unchecked(): void {
      for (const value of ["NaN", "Infinity"]) {
        const store = this.store_script(
          "unchecked",
          `engine.log("before");\nreturn ${value};\n`,
        );
        const result = script.script_run(store, "unchecked", {}, false);
        this.assertEqual(Object.keys(result), ["value", "lines"]);
        this.assertEqual(String(result.value), value);
        this.assertEqual(lines_shown(result.lines), ["before"]);
      }
    }

    // A call of the store that fails is the script's exception.
    test_store_refused(): void {
      const store = this.store_script(
        "absent",
        'return engine.store.kv_get("/_files/absent");\n',
      );
      const result = script.script_run(store, "absent", {}, false);
      const refused = gold_text("substrate_key_missing_absent");
      this.assertEqual(result.error, `Error: ${refused}`);
      this.assertFalse("value" in result);
    }

    // A name with no script throws the store's error.
    test_script_missing(): void {
      const store = this.store_make();
      this.raised_assert(gold_text("substrate_key_missing_script"), () =>
        script.script_run(store, "missing", {}, false),
      );
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds only `script_run`.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(script));
      this.assertEqual(Object.keys(script), ["script_run"]);
    }
  }
}

Object.freeze(test_script);
