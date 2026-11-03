// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of substrate.ts's largest database, a block of group B in the AI
// worker, on the sqlite3.wasm module and OPFS pool the bring up sets as
// globals: a database that `kv_put` fills with values of `overflow_bytes`,
// each kept in its row, until the write past `blob_max` fails with SQLite's
// full error, which pushes nothing, then its limit read through `sql_run`,
// its file, which `db_snapshot` gives, at most `blob_max`, its rows still
// read, and the limit again once it is opened again; and a `sql_run` that
// sets the page limit refused by the store's authorizer, pushing nothing,
// the limit read back as it was. The texts of the full and the authorization
// errors are its gold in `ts/test_setting_test_substrate_limit.json`, read
// through the harness with the `overflow_bytes`, `blob_max` and
// `turn_compact_turns` of `settings.json` its store takes.
namespace test_substrate_limit {
  // The C constants of the module used here, beside the store's parts.
  interface ModuleCoded extends substrate.SqliteModule {
    capi: substrate.SqliteModule["capi"] & {
      SQLITE_FULL: number;
      SQLITE_AUTH: number;
    };
  }

  // The initialized sqlite3.wasm module, a global the bring up sets.
  declare const test_sqlite3: ModuleCoded;

  // The installed OPFS SAH pool, a global the bring up sets.
  declare const test_pool: substrate.SqlitePool;

  // An error of SQLite, with its result code.
  interface CodedError extends Error {
    resultCode: number;
  }

  // The names the test uses.
  const constants = Object.freeze({
    // The root of the store the test makes in the pool.
    root: "/test_substrate_limit",
    // The database the test fills.
    database: "alpha",
    // The thread of the store's queue and the lane of its pushes.
    thread: "ai" as const,
    server: "server" as const,
    // The settings of the queue and the store's sizes.
    synchronous_setting: "queue_synchronous",
    overflow_setting: "overflow_bytes",
    blob_setting: "blob_max",
    compact_setting: "turn_compact_turns",
    // The gold's text of SQLite's full error.
    full_id: "typescript.test_substrate_limit.texts.full",
    // The gold's text of SQLite's authorization error.
    denied_id: "typescript.test_substrate_limit.texts.denied",
    // The gold's statements that set the page limit, each refused.
    setters_id: "typescript.test_substrate_limit.limit_setters",
  });

  // The `overflow_bytes` of `settings.json`, the largest value in its row.
  function overflow_get(): number {
    return harness.setting_get(constants.overflow_setting) as number;
  }

  // The `blob_max` of `settings.json`, the largest database file.
  function blob_get(): number {
    return harness.setting_get(constants.blob_setting) as number;
  }

  // A value of exactly `overflow_bytes`, counting up from 0 and again at 256.
  function value_exact(): Uint8Array {
    const data = new Uint8Array(overflow_get());
    for (let index = 0; index < data.length; index += 1) {
      data[index] = index % 256;
    }
    return data;
  }

  // The ref of the fill's value of an index.
  function fill_ref(index: number): string {
    return `/${constants.database}/${fill_key(index)}`;
  }

  // The key of the fill's value of an index.
  function fill_key(index: number): string {
    return `fill/${String(index).padStart(3, "0")}`;
  }

  // The bytes the limit of the database's connection allows, by `sql_run`.
  function limit_bytes(store: substrate.Store): number {
    const [page_size, page_count] = store.sql_run(constants.database, [
      { sql: "PRAGMA page_size", params: [] },
      { sql: "PRAGMA max_page_count", params: [] },
    ]) as [lines.SqlResult, lines.SqlResult];
    return (
      (page_size.rows[0] as number[])[0] * (page_count.rows[0] as number[])[0]
    );
  }

  // The database filled to its limit.
  export class TestFull extends unittest.TestCase {
    // The pushes the store's server lane took.
    readonly #pushed: lines.Line[] = [];

    // The store the test made.
    #store: substrate.Store | undefined = undefined;

    // Closes the databases and removes the files of the pool under the root.
    tearDown(): void {
      const store = this.#store as substrate.Store;
      for (const name of store.db_list()) {
        store.db_close(name);
      }
      for (const file of test_pool.getFileNames()) {
        if (file.startsWith(`${constants.root}/`)) {
          test_pool.unlink(file);
        }
      }
    }

    // A store on the root whose queue's server lane keeps each push.
    store_make(): substrate.Store {
      const far = new queue.LocalPort();
      far.line_receive((line) => {
        this.#pushed.push(line);
      });
      const synchronous = harness.setting_get(
        constants.synchronous_setting,
      ) as boolean;
      const tasks = new queue.TaskQueue(constants.thread, {}, synchronous);
      tasks.port_add(constants.server, new queue.LocalPort(far));
      this.#store = new substrate.Store(
        test_sqlite3,
        test_pool,
        new substrate.CacheFiles([]),
        constants.root,
        overflow_get(),
        blob_get(),
        harness.setting_get(constants.compact_setting) as number,
        tasks,
      );
      return this.#store;
    }

    // Asserts the error is SQLite's full error with the gold's text.
    full_assert(error: Error): void {
      this.assertTrue(error.constructor !== Error, error.message);
      this.assertEqual(
        (error as CodedError).resultCode,
        test_sqlite3.capi.SQLITE_FULL,
      );
      this.assertIn(harness.gold_get(constants.full_id), error.message);
    }

    // The error the call throws, failing when it throws none.
    error_get(fn: () => unknown): Error {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error) {
          return error;
        }
        throw error;
      }
      return this.fail("Error not raised");
    }

    // Puts until the put past `blob_max` fails full, giving the count put.
    fill_full(store: substrate.Store): number {
      const value = value_exact();
      const puts_max = Math.floor(blob_get() / overflow_get()) + 1;
      let count = 0;
      const error = this.error_get(() => {
        for (let index = 0; index < puts_max; index += 1) {
          store.kv_put(fill_ref(index), value);
          count = index + 1;
        }
      });
      this.full_assert(error);
      return count;
    }

    // The put past `blob_max` fails full, and the file, rows and limit hold.
    test_full_refused(): void {
      const store = this.store_make();
      store.db_create(constants.database);
      this.assertEqual(limit_bytes(store), blob_get());
      const count = this.fill_full(store);
      this.assertEqual(this.#pushed.length, count + 1);
      const keys = Array.from({ length: count }, (_, index) =>
        fill_key(index),
      );
      const rows = store.kv_list(constants.database, "fill/");
      this.assertEqual(
        rows.map((row) => row.k),
        keys,
      );
      this.assertEqual(store.kv_get(fill_ref(0)).data, value_exact());
      this.assertEqual(store.kv_get(fill_ref(count - 1)).data, value_exact());
      const image = store.db_snapshot(constants.database);
      this.assertTrue(
        image.data.length <= blob_get(),
        String(image.data.length),
      );
      store.db_close(constants.database);
      store.db_open(constants.database);
      this.assertEqual(limit_bytes(store), blob_get());
      this.assertEqual(store.kv_list(constants.database, "fill/"), rows);
      const error = this.error_get(() =>
        store.kv_put(fill_ref(count), value_exact()),
      );
      this.full_assert(error);
      this.assertEqual(store.kv_list(constants.database, "fill/"), rows);
      this.assertEqual(this.#pushed.length, count + 1);
    }

    // Each statement that sets the limit is refused, and the limit holds.
    test_limit_refused(): void {
      const store = this.store_make();
      store.db_create(constants.database);
      const pushed = this.#pushed.length;
      const setters = harness.gold_get(constants.setters_id) as string[];
      for (const sql of setters) {
        const error = this.error_get(() =>
          store.sql_run(constants.database, [{ sql, params: [] }]),
        );
        this.assertTrue(error.constructor !== Error, error.message);
        this.assertEqual(
          (error as CodedError).resultCode,
          test_sqlite3.capi.SQLITE_AUTH,
        );
        this.assertIn(harness.gold_get(constants.denied_id), error.message);
        this.assertEqual(limit_bytes(store), blob_get());
      }
      this.assertEqual(this.#pushed.length, pushed);
    }
  }
}
