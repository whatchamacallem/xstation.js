// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of script.ts on a store of the sqlite3.wasm module and OPFS pool the
// test page sets as globals: the step script that advances a region's tide,
// run and traced, the lines a run keeps at each level, a script read from the
// cache, the engine object, the exceptions a run returns and the errors it
// throws.

namespace test_script {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The settings, names, texts and digests the tests use.
  const constants = Object.freeze({
    // The `overflow_bytes` of `settings.json`, 128 KiB.
    overflow_bytes: 131072,
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_script/",
    // The files of the cache of each store a test makes.
    slot_count: 8,
    // The highest verbose level.
    level_max: 2,
    // The ref of the step script, which advances the tide of a region.
    step_ref: "/_files/script/step_tide.js",
    // The step script, 322 bytes.
    step_script:
      "// Advances the tide by args.hours in the region table" +
      " of the world.\n" +
      'const results = engine.store.sql_run("castle_world", [\n' +
      '  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n' +
      '    params: [args.hours, "castle_gatehouse"]},\n' +
      "]);\n" +
      'engine.log(1, "tide advanced by " + args.hours);\n' +
      "return {changes: results[0].changes};\n",
    // The size of the step script in bytes.
    step_size: 322,
    // The `SHA-256` of the step script.
    step_sha256:
      "dbc909cf0e2e7954d586c06b3291728e527d5dee4c109409fcb501e200756626",
    // The line the step script logs when it advances the tide by 1.
    step_line: "tide advanced by 1",
    // The arguments of the step script's call of the store, as JSON.
    step_arguments:
      '["castle_world",[{"sql":"UPDATE region SET tide = tide + ?' +
      ' WHERE name = ?","params":[1,"castle_gatehouse"]}]]',
    // The region table of the castle world.
    region_sql:
      "CREATE TABLE region" +
      " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL DEFAULT 0) STRICT",
  });

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

  // Puts the text of a script under its name in `_files`.
  function script_put(
    store: substrate.Store,
    name: string,
    text: string,
  ): { row: lines.KvRow; seq: number } {
    const ref = `/_files/script/${name}.js`;
    return store.kv_put(ref, utility.utf8_encode(text));
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

  // The level and text of each line, which leave out the time.
  function lines_shown(
    kept: lines.VerboseLine[],
  ): { level: number; text: string }[] {
    return kept.map((line) => ({ level: line.level, text: line.text }));
  }

  // A script test: the module and pool read in `setUp`, its roots removed.
  class ScriptCase extends unittest.TestCase {
    // The module the test page provides, read in `setUp`.
    #sqlite: substrate.SqliteModule | undefined = undefined;
    // The pool the test page provides, read in `setUp`.
    #pool: substrate.SqlitePool | undefined = undefined;
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made.
    readonly #stores: substrate.Store[] = [];

    // Reads the module and the pool the test page provides.
    setUp(): void {
      this.#sqlite = test_sqlite3;
      this.#pool = test_pool;
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

    // A store on a new root and cache, forwarding nowhere, with `_files`.
    store_fresh(): substrate.Store {
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
      );
      store.forward_set(() => undefined, false);
      this.#stores.push(store);
      store.db_create("_files");
      return store;
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
    // The step script returns its change and logs its line.
    test_step_recorded(): void {
      const store = this.store_fresh();
      castle_make(store);
      const data = utility.utf8_encode(constants.step_script);
      const put = store.kv_put(constants.step_ref, data);
      this.assertEqual(put.row.size, constants.step_size);
      this.assertEqual(put.row.sha256, constants.step_sha256);
      const result = script.script_run(store, "step_tide", { hours: 1 }, 1);
      this.assertEqual(Object.keys(result), ["value", "lines"]);
      this.assertEqual(result.value, { changes: 1 });
      this.assertEqual(lines_shown(result.lines), [
        { level: 1, text: constants.step_line },
      ]);
      this.assertEqual(typeof result.lines[0].at, "number");
    }

    // At level 2 the call of the store is traced before the script's line.
    test_step_traced(): void {
      const store = this.store_fresh();
      castle_make(store);
      script_put(store, "step_tide", constants.step_script);
      const result = script.script_run(store, "step_tide", { hours: 1 }, 2);
      this.assertEqual(result.value, { changes: 1 });
      const trace = i18n(
        "script.trace_call",
        "sql_run",
        constants.step_arguments,
      );
      this.assertEqual(lines_shown(result.lines), [
        { level: 2, text: trace },
        { level: 1, text: constants.step_line },
      ]);
    }

    // A run keeps the lines at or below its level, in order.
    test_levels_kept(): void {
      const store = this.store_fresh();
      script_put(
        store,
        "levels",
        'engine.log(0, "zero");\n' +
          'engine.log(1, "one");\n' +
          'engine.log(2, "two");\n' +
          "return null;\n",
      );
      const texts = ["zero", "one", "two"];
      for (let level = 0; level <= constants.level_max; level += 1) {
        const result = script.script_run(store, "levels", {}, level);
        this.assertEqual(result.value, null);
        const kept = texts
          .slice(0, level + 1)
          .map((text, index) => ({ level: index, text }));
        this.assertEqual(lines_shown(result.lines), kept);
      }
    }

    // A line the script logs also reaches the thread's verbose ring.
    test_thread_logged(): void {
      const store = this.store_fresh();
      script_put(store, "thread", 'engine.log(0, "to the thread");\n');
      script.script_run(store, "thread", {}, 0);
      this.assertEqual(verbose.history_get(1)[0].text, "to the thread");
    }

    // Only a run at level 2 traces the calls of the store.
    test_trace_level(): void {
      const store = this.store_fresh();
      script_put(store, "list", "return engine.store.db_list();\n");
      const plain = script.script_run(store, "list", {}, 1);
      this.assertEqual(plain, { value: ["_files"], lines: [] });
      const traced = script.script_run(store, "list", {}, 2);
      this.assertEqual(traced.value, ["_files"]);
      const trace = i18n("script.trace_call", "db_list", "[]");
      this.assertEqual(lines_shown(traced.lines), [{ level: 2, text: trace }]);
    }

    // A trace shows the bytes an argument holds by their count.
    test_bytes_counted(): void {
      const store = this.store_fresh();
      script_put(
        store,
        "note",
        'const data = new TextEncoder().encode("abc");\n' +
          'engine.store.kv_put("/_files/note", data);\n',
      );
      const result = script.script_run(store, "note", {}, 2);
      const shown = '["/_files/note",{"bytes":3}]';
      const trace = i18n("script.trace_call", "kv_put", shown);
      this.assertEqual(lines_shown(result.lines), [{ level: 2, text: trace }]);
      const value = store.kv_get("/_files/note").data;
      this.assertEqual(value, utility.utf8_encode("abc"));
    }

    // The arguments reach the script as they were given.
    test_args_passed(): void {
      const store = this.store_fresh();
      script_put(store, "echo", "return args;\n");
      const args = { list: [1, "two"], flag: true };
      this.assertEqual(script.script_run(store, "echo", args, 1).value, args);
    }

    // The engine is frozen and holds the store, the log and `i18n`.
    test_engine_frozen(): void {
      const store = this.store_fresh();
      script_put(
        store,
        "engine",
        "return [Object.isFrozen(engine), Object.keys(engine)," +
          " typeof engine.i18n];\n",
      );
      this.assertEqual(script.script_run(store, "engine", {}, 1).value, [
        true,
        ["store", "log", "i18n"],
        "function",
      ]);
    }

    // A script larger than `overflow_bytes` is read from the cache.
    test_cached_script(): void {
      const store = this.store_fresh();
      const padding = "x".repeat(constants.overflow_bytes);
      script_put(store, "large", `// ${padding}\nreturn 7;\n`);
      const value = store.kv_get("/_files/script/large.js");
      this.assertEqual(typeof value.data, "string");
      this.assertEqual(script.script_run(store, "large", {}, 1).value, 7);
    }
  }

  // What a run returns for an exception, and what it throws itself.
  export class TestErrors extends ScriptCase {
    // An `Error` the script throws comes back with its text and stack.
    test_error_returned(): void {
      const store = this.store_fresh();
      script_put(store, "far", 'throw new RangeError("far");\n');
      const result = script.script_run(store, "far", {}, 1);
      this.assertEqual(Object.keys(result), ["error", "stack", "lines"]);
      this.assertEqual(result.error, "RangeError: far");
      this.assertIn("RangeError: far", result.stack);
      this.assertEqual(result.lines, []);
    }

    // A value that is no `Error` comes back as its text, with no stack.
    test_value_thrown(): void {
      const store = this.store_fresh();
      script_put(store, "plain", 'throw "plain";\n');
      this.assertEqual(script.script_run(store, "plain", {}, 1), {
        error: "plain",
        lines: [],
      });
    }

    // A script that does not compile returns its `SyntaxError`.
    test_syntax_returned(): void {
      const store = this.store_fresh();
      script_put(store, "broken", "return (;\n");
      const result = script.script_run(store, "broken", {}, 1);
      this.assertTrue(String(result.error).startsWith("SyntaxError: "));
      this.assertFalse("value" in result);
    }

    // The lines logged before the exception are kept.
    test_lines_before(): void {
      const store = this.store_fresh();
      script_put(
        store,
        "late",
        'engine.log(1, "before");\nthrow new Error("after");\n',
      );
      const result = script.script_run(store, "late", {}, 1);
      this.assertEqual(result.error, "Error: after");
      this.assertEqual(lines_shown(result.lines), [
        { level: 1, text: "before" },
      ]);
    }

    // A log above level 2 is the script's exception, with verbose's text.
    test_log_refused(): void {
      const store = this.store_fresh();
      script_put(store, "high", 'engine.log(3, "high");\n');
      const result = script.script_run(store, "high", {}, 2);
      const message = i18n("verbose.level_invalid", 3, constants.level_max);
      this.assertEqual(result.error, `Error: ${message}`);
    }

    // A call of the store that fails is the script's exception.
    test_store_refused(): void {
      const store = this.store_fresh();
      script_put(
        store,
        "absent",
        'return engine.store.kv_get("/_files/absent");\n',
      );
      const result = script.script_run(store, "absent", {}, 1);
      const message = i18n("substrate.key_missing", "absent", "_files");
      this.assertEqual(result.error, `Error: ${message}`);
    }

    // A name with no script throws the store's error.
    test_script_missing(): void {
      const store = this.store_fresh();
      this.raised_assert(
        i18n("substrate.key_missing", "script/missing.js", "_files"),
        () => script.script_run(store, "missing", {}, 1),
      );
    }

    // A level outside 0 to 2 throws before anything is read.
    test_level_refused(): void {
      const store = this.store_fresh();
      for (const level of [-1, 3, 1.5]) {
        this.raised_assert(
          i18n("script.level_invalid", level, constants.level_max),
          () => script.script_run(store, "missing", {}, level),
        );
      }
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
