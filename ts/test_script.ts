// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of script.ts on a store double that records each call and answers
// what the test chose: the step script that advances a region's tide, run
// and traced, every line a run keeps, a script read from the cache, the
// engine object and its store of routine methods, the exceptions a run
// returns and the errors it throws. The trace texts are entries of the gold
// record, test_settings.json.

namespace test_script {
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
    // The row of the step script.
    step_ref: "/_files/script/step_tide.js",
    // The line the step script logs when it advances the tide by 1.
    step_line: "tide advanced by 1",
    // The handle of a script the store holds in its cache.
    cached_handle: "cache/0001",
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
  });

  // What the store double answers to one call: a value or an error thrown.
  type StoreAnswer = { value: unknown } | { thrown: Error };

  // One call of a double: the method's name and its arguments.
  type DoubleCall = [string, unknown[]];

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_script.texts.${name}`) as string;
  }

  // A cache double: the bytes of each handle the test put, each read kept.
  class CacheDouble {
    // Every read, its handle, offset and length, in order.
    readonly reads: [string, number, number][] = [];
    // The bytes the test put under each handle.
    readonly #files = new Map<string, Uint8Array>();

    // Puts the bytes under the handle.
    file_put(handle: string, data: Uint8Array): void {
      this.#files.set(handle, data);
    }

    // Keeps the read and gives the bytes, which the test must have put.
    cache_read(handle: string, offset: number, length: number): Uint8Array {
      this.reads.push([handle, offset, length]);
      const data = this.#files.get(handle);
      if (data === undefined) {
        throw new Error(`the cache double has no file ${handle}`);
      }
      return data.subarray(offset, offset + length);
    }
  }

  // A store double: each call kept, answered by the test's next answer.
  class StoreDouble {
    // Every call, in order.
    readonly calls: DoubleCall[] = [];
    // The cache double that `sink` gives.
    readonly cache = new CacheDouble();
    // The answers still to give, by method name, the first set given first.
    readonly #answers = new Map<string, StoreAnswer[]>();

    // Sets the answer of the next call of the method not yet answered.
    answer_add(name: string, answer: StoreAnswer): void {
      const answers = this.#answers.get(name);
      if (answers === undefined) {
        this.#answers.set(name, [answer]);
      } else {
        answers.push(answer);
      }
    }

    // Sets a script's text, in memory, as the next answer of `kv_get`.
    script_add(text: string): void {
      const data = new TextEncoder().encode(text);
      this.answer_add("kv_get", { value: { data, size: data.length } });
    }

    // Keeps the call and gives its answer, which the test must have set.
    #call(name: string, values: unknown[]): unknown {
      this.calls.push([name, values]);
      const answer = this.#answers.get(name)?.shift();
      if (answer === undefined) {
        throw new Error(`the store double has no answer for ${name}`);
      }
      if ("thrown" in answer) {
        throw answer.thrown;
      }
      return answer.value;
    }

    // Keeps the call and gives the cache double.
    sink(): CacheDouble {
      this.calls.push(["sink", []]);
      return this.cache;
    }

    // The fifteen routine methods `script_run` binds, each kept and answered.
    sql_run(...values: unknown[]): unknown {
      return this.#call("sql_run", values);
    }
    db_list(...values: unknown[]): unknown {
      return this.#call("db_list", values);
    }
    db_create(...values: unknown[]): unknown {
      return this.#call("db_create", values);
    }
    db_drop(...values: unknown[]): unknown {
      return this.#call("db_drop", values);
    }
    kv_get(...values: unknown[]): unknown {
      return this.#call("kv_get", values);
    }
    kv_put(...values: unknown[]): unknown {
      return this.#call("kv_put", values);
    }
    kv_delete(...values: unknown[]): unknown {
      return this.#call("kv_delete", values);
    }
    kv_list(...values: unknown[]): unknown {
      return this.#call("kv_list", values);
    }
    doc_get(...values: unknown[]): unknown {
      return this.#call("doc_get", values);
    }
    doc_put(...values: unknown[]): unknown {
      return this.#call("doc_put", values);
    }
    doc_head(...values: unknown[]): unknown {
      return this.#call("doc_head", values);
    }
    turn_append(...values: unknown[]): unknown {
      return this.#call("turn_append", values);
    }
    turn_list(...values: unknown[]): unknown {
      return this.#call("turn_list", values);
    }
    turn_compact(...values: unknown[]): unknown {
      return this.#call("turn_compact", values);
    }
    transaction_run(...values: unknown[]): unknown {
      return this.#call("transaction_run", values);
    }
  }

  // A store double holding one script, read in memory, for each run asked.
  function store_make(text: string, runs = 1): StoreDouble {
    const store = new StoreDouble();
    for (let run = 0; run < runs; run += 1) {
      store.script_add(text);
    }
    return store;
  }

  // Runs the script of the name on the store double.
  function run_double(
    store: StoreDouble,
    name: string,
    args: unknown,
    trace: boolean,
  ): script.ScriptResult {
    const door = store as unknown as substrate.Store;
    return script.script_run(door, name, args, trace);
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

  // A script test, with an assertion of a plain `Error`.
  class ScriptCase extends unittest.TestCase {
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
    // The step script reads its row, calls the store, returns and logs.
    test_step_recorded(): void {
      const store = store_make(constants.step_script);
      const changed = { columns: [], rows: [], changes: 1 };
      store.answer_add("sql_run", { value: [changed] });
      const result = run_double(store, "step_tide", { hours: 1 }, false);
      this.assertEqual(Object.keys(result), ["value", "lines"]);
      this.assertEqual(result.value, { changes: 1 });
      this.assertEqual(lines_shown(result.lines), [constants.step_line]);
      this.assertEqual(Object.keys(result.lines[0]), ["at", "text"]);
      this.assertEqual(typeof result.lines[0].at, "number");
      const statement = {
        sql: "UPDATE region SET tide = tide + ? WHERE name = ?",
        params: [1, "castle_gatehouse"],
      };
      this.assertEqual(store.calls, [
        ["kv_get", [constants.step_ref]],
        ["sink", []],
        ["sql_run", ["castle_world", [statement]]],
      ]);
    }

    // A traced run traces the call of the store before the script's line.
    test_step_traced(): void {
      const store = store_make(constants.step_script);
      const changed = { columns: [], rows: [], changes: 1 };
      store.answer_add("sql_run", { value: [changed] });
      const result = run_double(store, "step_tide", { hours: 1 }, true);
      this.assertEqual(result.value, { changes: 1 });
      this.assertEqual(lines_shown(result.lines), [
        gold_text("script_trace_call_sql_run"),
        constants.step_line,
      ]);
    }

    // A run keeps every line it logs, in order, traced or not.
    test_lines_kept(): void {
      const store = store_make(
        'engine.log("zero");\n' +
          'engine.log("one");\n' +
          'engine.log("two");\n' +
          "return null;\n",
        2,
      );
      for (const trace of [false, true]) {
        const result = run_double(store, "lines", {}, trace);
        this.assertEqual(result.value, null);
        this.assertEqual(lines_shown(result.lines), ["zero", "one", "two"]);
      }
    }

    // A line the script logs to the thread is one of the run's lines.
    test_thread_logged(): void {
      const store = store_make('engine.log("to the thread");\n');
      const result = run_double(store, "thread", {}, false);
      this.assertEqual(lines_shown(result.lines), ["to the thread"]);
    }

    // Only a traced run traces the calls of the store.
    test_trace_only(): void {
      const store = store_make("return engine.store.db_list();\n", 2);
      store.answer_add("db_list", { value: ["_files"] });
      store.answer_add("db_list", { value: ["_files"] });
      const plain = run_double(store, "list", {}, false);
      this.assertEqual(plain, { value: ["_files"], lines: [] });
      const traced = run_double(store, "list", {}, true);
      this.assertEqual(traced.value, ["_files"]);
      const trace = gold_text("script_trace_call_db_list");
      this.assertEqual(lines_shown(traced.lines), [trace]);
      const listed = store.calls.filter(([name]) => name === "db_list");
      this.assertEqual(listed, [
        ["db_list", []],
        ["db_list", []],
      ]);
    }

    // A trace shows the bytes an argument holds by their count.
    test_bytes_counted(): void {
      const store = store_make(
        'const data = new TextEncoder().encode("abc");\n' +
          'engine.store.kv_put("/_files/note", data);\n',
      );
      store.answer_add("kv_put", { value: undefined });
      const result = run_double(store, "note", {}, true);
      const trace = gold_text("script_trace_call_kv_put");
      this.assertEqual(lines_shown(result.lines), [trace]);
      const put = store.calls.filter(([name]) => name === "kv_put");
      const data = new TextEncoder().encode("abc");
      this.assertEqual(put, [["kv_put", ["/_files/note", data]]]);
    }

    // The arguments reach the script as they were given.
    test_args_passed(): void {
      const store = store_make("return args;\n");
      const args = { list: [1, "two"], flag: true };
      const result = run_double(store, "echo", args, false);
      this.assertEqual(result.value, args);
    }

    // The engine is frozen and holds the store, the log and `i18n`.
    test_engine_frozen(): void {
      const store = store_make(
        "return [Object.isFrozen(engine), Object.keys(engine)," +
          " typeof engine.i18n];\n",
      );
      this.assertEqual(run_double(store, "engine", {}, false).value, [
        true,
        ["store", "log", "i18n"],
        "function",
      ]);
    }

    // The store is frozen and holds the routine methods only, traced or not.
    test_store_routine(): void {
      const store = store_make(
        "return [Object.isFrozen(engine.store)," +
          " Object.keys(engine.store)];\n",
        2,
      );
      for (const trace of [false, true]) {
        const result = run_double(store, "methods", {}, trace);
        this.assertEqual(result.value, [true, [...constants.store_names]]);
      }
    }

    // The store's machinery is not there: calling it is the engine's error.
    test_store_machinery(): void {
      for (const call of ['db_snapshot("_files")', "sink()"]) {
        const store = store_make(`return engine.store.${call};\n`);
        const result = run_double(store, "machinery", {}, false);
        this.assertTrue(String(result.error).startsWith("TypeError: "));
        this.assertFalse("value" in result);
      }
    }

    // A script the store holds in its cache is read from the cache.
    test_cached_script(): void {
      const store = new StoreDouble();
      const data = new TextEncoder().encode("// cached\nreturn 7;\n");
      store.cache.file_put(constants.cached_handle, data);
      const value = { data: constants.cached_handle, size: data.length };
      store.answer_add("kv_get", { value });
      this.assertEqual(run_double(store, "large", {}, false).value, 7);
      const read = ["kv_get", ["/_files/script/large.js"]];
      this.assertEqual(store.calls[0], read);
      this.assertEqual(store.cache.reads, [
        [constants.cached_handle, 0, data.length],
      ]);
    }
  }

  // What a run returns for an exception, and what it throws itself.
  export class TestErrors extends ScriptCase {
    // An `Error` the script throws comes back with its text and stack.
    test_error_returned(): void {
      const store = store_make('throw new RangeError("far");\n');
      const result = run_double(store, "far", {}, false);
      this.assertEqual(Object.keys(result), ["error", "stack", "lines"]);
      this.assertEqual(result.error, "RangeError: far");
      this.assertIn("RangeError: far", result.stack);
      this.assertEqual(result.lines, []);
    }

    // A value that is no `Error` comes back as its text, with no stack.
    test_value_thrown(): void {
      const store = store_make('throw "plain";\n');
      this.assertEqual(run_double(store, "plain", {}, false), {
        error: "plain",
        lines: [],
      });
    }

    // A script that does not compile returns its `SyntaxError`.
    test_syntax_returned(): void {
      const store = store_make("return (;\n");
      const result = run_double(store, "broken", {}, false);
      this.assertTrue(String(result.error).startsWith("SyntaxError: "));
      this.assertFalse("value" in result);
    }

    // The lines logged before the exception are kept.
    test_lines_before(): void {
      const store = store_make(
        'engine.log("before");\nthrow new Error("after");\n',
      );
      const result = run_double(store, "late", {}, false);
      this.assertEqual(result.error, "Error: after");
      this.assertEqual(lines_shown(result.lines), ["before"]);
    }

    // A value JSON cannot carry is the run's exception, not the tool's.
    test_value_uncarried(): void {
      const store = store_make('engine.log("before");\nreturn BigInt(1);\n');
      const result = run_double(store, "uncarried", {}, false);
      this.assertEqual(result.error, refusal_text(BigInt(1)));
      this.assertEqual(typeof result.stack, "string");
      this.assertFalse("value" in result);
      this.assertEqual(lines_shown(result.lines), ["before"]);
    }

    // NaN and the infinities are returned, as no decoder lets them in.
    test_value_unchecked(): void {
      for (const value of ["NaN", "Infinity"]) {
        const store = store_make(`engine.log("before");\nreturn ${value};\n`);
        const result = run_double(store, "unchecked", {}, false);
        this.assertEqual(Object.keys(result), ["value", "lines"]);
        this.assertEqual(String(result.value), value);
        this.assertEqual(lines_shown(result.lines), ["before"]);
      }
    }

    // A call of the store that fails is the script's exception.
    test_store_refused(): void {
      const store = store_make(
        'return engine.store.kv_get("/_files/absent");\n',
      );
      const thrown = new Error("the store refused the read");
      store.answer_add("kv_get", { thrown });
      const result = run_double(store, "absent", {}, false);
      this.assertEqual(result.error, "Error: the store refused the read");
      this.assertEqual(store.calls[2], ["kv_get", ["/_files/absent"]]);
    }

    // A name with no script throws the store's error.
    test_script_missing(): void {
      const store = new StoreDouble();
      const thrown = new Error("the store has no such row");
      store.answer_add("kv_get", { thrown });
      this.raised_assert("the store has no such row", () =>
        run_double(store, "missing", {}, false),
      );
      this.assertEqual(store.calls, [
        ["kv_get", ["/_files/script/missing.js"]],
      ]);
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
