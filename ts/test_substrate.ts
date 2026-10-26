// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of substrate.ts: refs, the document encoding, the sink's incremental
// hash against known digests, the cache over slot files kept in memory, and
// the store on the sqlite3.wasm module and OPFS pool the test page sets as
// globals: databases, values, documents, turns, compaction at the threshold,
// SQL and the names the schema's triggers raise, transactions, snapshots and
// restores with their cache files, values whose cache file is lost, the push
// of each committed operation to a notifier double, a put stopped between its
// cache file and its row, and the handlers. It also holds the pause point of
// that stop, which a browser rung uses to kill a worker of the test page
// there. The texts, pushes and reply texts it expects and the lines it sends
// are its gold in `test_settings.json`, read through the harness with the
// `overflow_bytes` and `turn_compact_turns` of `settings.json` its stores
// take. Each digest and its input are one entry of `test_digests.json` in
// `test_vectors`, and the test uses that input.
namespace test_substrate {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The vector files by name, as base64 text, a global the test page sets.
  declare const test_vectors: { readonly [name: string]: string };

  // The names, texts and sizes the tests use.
  const constants = Object.freeze({
    // The `overflow_bytes` of the kill rung's store in `test_browser.py`.
    kill_overflow: 131072,
    // A count chosen by its writer: a threshold a test reaches in a few turns.
    compact_small: 3,
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_substrate/",
    // The bytes at the start of a cache file that hold its name.
    name_bytes: 64,
    // The file of the digest vectors of the test modules.
    digests_name: "test_digests.json",
    // The hyperposition scene, whose conversation the turn tests append to.
    scene: "/metaverse/hyperposition/1",
    // The subtitle of the arrival scene the castle turn builds.
    arrival_subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The universe table, as the metaverse SQL file creates it.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    // Its trigger that refuses a second row of a world, as that file has it.
    trigger_sql:
      "CREATE TRIGGER universe_world_insert BEFORE INSERT ON universe" +
      " WHEN EXISTS (SELECT 1 FROM universe" +
      " WHERE world = NEW.world AND name <> NEW.name)" +
      " BEGIN SELECT RAISE(ABORT, 'agent.content_ambiguous'); END",
    // The name of the string that trigger raises.
    trigger_name: "agent.content_ambiguous",
    // The world table of the castle universe.
    world_sql:
      "CREATE TABLE world" +
      " (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT",
    // The `_meta` table alone, as the substrate's SQL file creates it.
    meta_sql:
      "CREATE TABLE _meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)" +
      " WITHOUT ROWID, STRICT",
    // Text beyond ASCII for keys and values, built from its code points.
    text_wide: String.fromCodePoint(0x4e2d, 0x6587, 0x1f600),
    // The first bytes of a database file.
    file_magic: "SQLite format 3",
    // The database and key of the put that a kill stops.
    kill_db: "alpha",
    kill_key: "big",
    // The start of the SQL that writes a row to `_kv`.
    row_insert: "INSERT INTO _kv ",
    // The message of the stop that stands for the kill in the unit test.
    kill_message: "The put stopped between its cache file and its row.",
    // The start of the SQL that writes the first of the substrate's tables.
    schema_create: "CREATE TABLE _meta ",
    // The message of the failure the test makes where the schema is written.
    schema_message: "The schema failed where the test made it fail.",
  });

  // The number of the last root a test made, so that each store has its own.
  let root_count = 0;

  // A push a store gave its notifier: the line and its owner.
  type Pushed = [lines.Line, string | undefined];

  // An entry of the digest vectors: its input and its `SHA-256`, in hex.
  interface DigestVector {
    data: string;
    sha256: string;
  }

  // This module's entries of the digest vectors, read at their first use.
  let digests_kept: { [name: string]: DigestVector } | undefined = undefined;

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_substrate.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_substrate.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The text of a cache with no file of the name, the name known at run time.
  function unknown_text(name: string): string {
    return gold_text("substrate_cache_unknown").replaceAll("{0}", name);
  }

  // The text of a value whose cache file is lost, both known at run time.
  function lost_text(ref: string, name: string): string {
    return gold_text("substrate_file_lost")
      .replaceAll("{0}", ref)
      .replaceAll("{1}", name);
  }

  // A line of the gold the test sends, its blob 1 the bytes and their size.
  function line_blob(name: string, data: Uint8Array): lines.Line {
    const line = gold_line(name);
    line[1] = { s: data.length, d: data };
    return line;
  }

  // A push of the gold a store gives the server.
  function push_gold(name: string): Pushed {
    return [gold_line(name), "server"];
  }

  // A push of the gold, its blob 1 the bytes and their size in full names.
  function push_bytes(name: string, data: Uint8Array): Pushed {
    const line = gold_line(name);
    line[1] = { size: data.length, d: data };
    return [line, "server"];
  }

  // The entries of this module in the digest vectors of `test_vectors`.
  function digests_get(): { [name: string]: DigestVector } {
    if (digests_kept !== undefined) {
      return digests_kept;
    }
    const name = constants.digests_name;
    if (!Object.hasOwn(test_vectors, name)) {
      throw new Error(`test_vectors has no file ${name}`);
    }
    const file = Uint8Array.from(atob(test_vectors[name]), (character) =>
      character.charCodeAt(0),
    );
    const text = new TextDecoder("utf-8", { fatal: true }).decode(file);
    const vectors = JSON.parse(text) as {
      [module: string]: { [name: string]: DigestVector };
    };
    if (!Object.hasOwn(vectors, "test_substrate")) {
      throw new Error(`${name} has no module test_substrate`);
    }
    digests_kept = vectors.test_substrate;
    return digests_kept;
  }

  // The input and digest of an entry of this module's digest vectors.
  function digest_entry(name: string): { data: Uint8Array; sha256: string } {
    const entries = digests_get();
    if (!Object.hasOwn(entries, name)) {
      throw new Error(`${constants.digests_name} has no entry ${name}`);
    }
    const entry = entries[name];
    if (!/^(?:[0-9a-f]{2})*$/.test(entry.data)) {
      throw new Error(`the input of the digest entry ${name} is not hex`);
    }
    const data = new Uint8Array(entry.data.length / 2);
    for (let index = 0; index < data.length; index += 1) {
      const pair = entry.data.slice(2 * index, 2 * index + 2);
      data[index] = Number.parseInt(pair, 16);
    }
    return { data, sha256: entry.sha256 };
  }

  // The `overflow_bytes` of `settings.json`, which the test stores take.
  function overflow_get(): number {
    return harness.setting_get("overflow_bytes") as number;
  }

  // Bytes that count up from 0 and start again at 256, as many as asked.
  function bytes_pattern(count: number): Uint8Array {
    const data = new Uint8Array(count);
    for (let index = 0; index < count; index += 1) {
      data[index] = index % 256;
    }
    return data;
  }

  // The `UTF-8` bytes of text.
  function bytes_text(text: string): Uint8Array {
    return new TextEncoder().encode(text);
  }

  // The bytes of the pieces one after another.
  function bytes_join(pieces: readonly Uint8Array[]): Uint8Array {
    let length = 0;
    for (const piece of pieces) {
      length += piece.length;
    }
    const joined = new Uint8Array(length);
    let offset = 0;
    for (const piece of pieces) {
      joined.set(piece, offset);
      offset += piece.length;
    }
    return joined;
  }

  // The message of the role with the text.
  function message_said(
    role: provider.Role,
    content: string,
  ): provider.ChatMessage {
    return { role, content };
  }

  // The digest entry of exactly `overflow_bytes`, which stays in its row.
  function value_exact(): Uint8Array {
    return digest_entry("value_exact").data;
  }

  // The digest entry one byte over `overflow_bytes`, which goes to the cache.
  function value_over(): Uint8Array {
    return digest_entry("value_over").data;
  }

  // Another digest entry of the size of that one, with other bytes.
  function value_other(): Uint8Array {
    return digest_entry("value_other").data;
  }

  // A cache file double kept in memory, with the calls OPFS gives.
  class MemorySlot implements substrate.SlotHandle {
    // The storage, grown by doubling, zero beyond the file.
    #store = new Uint8Array(0);
    // The size of the file.
    #size = 0;

    // A copy of the bytes of the file.
    bytes_get(): Uint8Array {
      return this.#store.slice(0, this.#size);
    }

    // Replaces the bytes of the file.
    bytes_set(data: Uint8Array): void {
      this.#store = data.slice();
      this.#size = data.length;
    }

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

  // A cache file double whose reads and writes fall one byte short when told.
  class ShortSlot extends MemorySlot {
    // Whether reads and writes report one byte fewer than they moved.
    short = false;

    // Reads as the double does, reporting one byte fewer when short.
    read(buffer: Uint8Array, options: { at: number }): number {
      const count = super.read(buffer, options);
      return this.short ? count - 1 : count;
    }

    // Writes as the double does, reporting one byte fewer when short.
    write(buffer: Uint8Array, options: { at: number }): number {
      const count = super.write(buffer, options);
      return this.short ? count - 1 : count;
    }
  }

  // Empty cache file doubles, as many as asked.
  function slots_make(count: number): MemorySlot[] {
    return Array.from({ length: count }, () => new MemorySlot());
  }

  // A cache file double holding a stored value under its name.
  function slot_stored(name: string, data: Uint8Array): MemorySlot {
    const slot = new MemorySlot();
    slot.bytes_set(bytes_join([bytes_text(name), data]));
    return slot;
  }

  // The files of each test store's cache, a count of this module's gold.
  function slot_count(): number {
    return gold_value("slot_count") as number;
  }

  // A cache over empty file doubles.
  function cache_make(): substrate.CacheFiles {
    return new substrate.CacheFiles(slots_make(slot_count()));
  }

  // Streams bytes into a cache's sink in pieces and returns the handle.
  function sink_fill(cache: substrate.CacheFiles, data: Uint8Array): string {
    const handle = cache.sink_open({ s: data.length });
    const step = gold_value("piece_bytes") as number;
    for (let offset = 0; offset < data.length; offset += step) {
      cache.sink_append(handle, data.subarray(offset, offset + step));
    }
    cache.sink_close(handle);
    return handle;
  }

  // The hash a fresh sink returns for bytes streamed in pieces of a size.
  function digest_streamed(data: Uint8Array, piece: number): string {
    const cache = new substrate.CacheFiles(slots_make(1));
    const handle = cache.sink_open({ s: data.length });
    for (let offset = 0; offset < data.length; offset += piece) {
      cache.sink_append(handle, data.subarray(offset, offset + piece));
    }
    return cache.sink_close(handle);
  }

  // The type of a push, whose header is in full names in debug mode.
  function type_pushed(line: lines.Line): unknown {
    return (line[0] as unknown as { [name: string]: unknown }).type;
  }

  // The JSON text of a line, each blob header without its bytes `d`.
  function line_text(line: lines.Line): string {
    const shown: { [key: string]: unknown } = { ...line };
    for (let number = 1; Object.hasOwn(line, String(number)); number += 1) {
      const header = line[String(number)] as { [name: string]: unknown };
      shown[String(number)] = Object.fromEntries(
        Object.entries(header).filter(([name]) => name !== "d"),
      );
    }
    return JSON.stringify(shown);
  }

  // The rows of one statement a store runs.
  function rows_query(
    store: substrate.Store,
    db: string,
    sql: string,
  ): unknown[][] {
    return store.sql_run(db, [{ sql, params: [] }])[0].rows;
  }

  // The schema and the rows of every table of a database, in order.
  function content_dump(store: substrate.Store, db: string): unknown[] {
    const schema = rows_query(
      store,
      db,
      "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY name",
    );
    const dump: unknown[] = [schema];
    for (const row of schema) {
      if (row[0] === "table") {
        dump.push(rows_query(store, db, `SELECT * FROM "${String(row[1])}"`));
      }
    }
    return dump;
  }

  // The names of the tables of a database, in order.
  function tables_list(store: substrate.Store, db: string): string[] {
    const rows = rows_query(
      store,
      db,
      "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name",
    );
    return rows.map((row) => row[0] as string);
  }

  // The arrival scene of the castle gatehouse in its stored form.
  function arrival_make(): lines.Document {
    return {
      0: { t: "scene" },
      1: "/_files/gatehouse/arrival.png",
      subtitle: constants.arrival_subtitle,
      image: { $ref: 1 },
    };
  }

  // The stored text of the arrival scene, its encoded document as JSON.
  function arrival_stored(): string {
    return (
      '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"' +
      constants.arrival_subtitle +
      '","image":{"$ref":1}}'
    );
  }

  // A document in its normal form, with refs, shared refs and plain text.
  function fog_normal(): { [key: string]: unknown } {
    return {
      0: { t: "scene", v: 2 },
      subtitle: "Fog " + constants.text_wide,
      image: "/_files/fog.png",
      links: [
        "/metaverse/world",
        { to: "/_files/fog.png", note: "/not a ref" },
      ],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // That document encoded, its refs moved into headers 1 and 2.
  function fog_encoded(): lines.Document {
    return {
      0: { t: "scene", v: 2 },
      1: "/_files/fog.png",
      2: "/metaverse/world",
      subtitle: "Fog " + constants.text_wide,
      image: { $ref: 1 },
      links: [{ $ref: 2 }, { to: { $ref: 1 }, note: "/not a ref" }],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // A document with integer keys below the top level.
  function nested_make(): lines.Document {
    return {
      0: { t: "nest" },
      1: "/_files/fog.png",
      inner: {
        b: 1,
        2: constants.text_wide,
        a: [{ z: null, 0: 0.5 }],
        1: { $ref: 1 },
      },
      count: -3,
    };
  }

  // A database of the pool that runs `stop` before SQL with a given start.
  class StoppedDatabase implements substrate.SqliteDatabase {
    // The database of the pool.
    readonly #inner: substrate.SqliteDatabase;
    // What runs in place of the SQL.
    readonly #stop: () => never;
    // The start of the SQL that the stop runs before.
    readonly #prefix: string;

    // Takes the database it wraps, the stop and the start of the SQL.
    constructor(
      inner: substrate.SqliteDatabase,
      stop: () => never,
      prefix: string,
    ) {
      this.#inner = inner;
      this.#stop = stop;
      this.#prefix = prefix;
    }

    // The `sqlite3` pointer of the connection.
    get pointer(): number {
      return this.#inner.pointer;
    }

    // Runs the SQL, stopping before it when it starts with the prefix.
    exec(options: substrate.ExecOptions): unknown {
      if (options.sql.startsWith(this.#prefix)) {
        this.#stop();
      }
      return this.#inner.exec(options);
    }

    // The first column of the first row the SQL returns.
    selectValue(sql: string, bind?: unknown[]): unknown {
      return this.#inner.selectValue(sql, bind);
    }

    // Prepares the first statement of the SQL.
    prepare(sql: string): substrate.SqliteStatement {
      return this.#inner.prepare(sql);
    }

    // The rows the last statement changed, or all since opening when total.
    changes(total: boolean): number {
      return this.#inner.changes(total);
    }

    // Closes the connection.
    close(): void {
      this.#inner.close();
    }
  }

  // The pool's files, its databases stopping before SQL with the start.
  function pool_stopped(
    pool: substrate.SqlitePool,
    stop: () => never,
    prefix: string,
  ): substrate.SqlitePool {
    // The pool's database class, its databases wrapped to stop.
    class PausedDatabase extends StoppedDatabase {
      // Opens the file as the pool's own class does.
      constructor(options: { filename: string; flags: string }) {
        super(new pool.OpfsSAHPoolDb(options), stop, prefix);
      }
    }
    return {
      OpfsSAHPoolDb: PausedDatabase,
      getFileNames: () => pool.getFileNames(),
      importDb: (name, bytes) => pool.importDb(name, bytes),
      unlink: (name) => pool.unlink(name),
    };
  }

  // The pause point: the pool's files, its databases stopping before a row.
  export function kill_pool(
    pool: substrate.SqlitePool,
    stop: () => never,
  ): substrate.SqlitePool {
    return pool_stopped(pool, stop, constants.row_insert);
  }

  // Creates `alpha` and puts a value over `overflow_bytes` under `big` in it.
  export function kill_put(store: substrate.Store): void {
    store.db_create(constants.kill_db);
    const value = bytes_pattern(constants.kill_overflow + 1);
    store.kv_put(`/${constants.kill_db}/${constants.kill_key}`, value);
  }

  // Says it is paused, then holds the worker in a loop until it is killed.
  export function kill_hold(paused: () => void): never {
    paused();
    for (;;) {}
  }

  // Opens `alpha` after the kill: the rows of `big`, the files then removed.
  export function kill_check(store: substrate.Store): {
    rows: number;
    removed: number;
  } {
    store.db_open(constants.kill_db);
    return {
      rows: store.kv_list(constants.kill_db, constants.kill_key).length,
      removed: store.kv_check(constants.kill_db),
    };
  }

  // A test case with the asserts of a refusal and its message.
  class RefusalCase extends unittest.TestCase {
    // Asserts the call throws a plain `Error` with exactly the message.
    raised_assert(message: string, fn: () => unknown, note?: string): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === Error) {
          this.assertEqual(error.message, message, note);
          return;
        }
        throw error;
      }
      const standard = "Error not raised";
      this.fail(note === undefined ? standard : `${standard} : ${note}`);
    }

    // Asserts the call throws an error of SQLite holding the text.
    sqlite_assert(text: string, fn: () => unknown): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor !== Error) {
          this.assertIn(text, error.message);
          return;
        }
        throw error;
      }
      this.fail("SQLite raised nothing");
    }

    // The `Error` the call throws, failing when it throws none.
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
  }

  // A store test: the module and pool read in `setUp`, its roots removed.
  class StoreCase extends RefusalCase {
    // The module the test page provides, read in `setUp`.
    #sqlite: substrate.SqliteModule | undefined = undefined;
    // The pool the test page provides, read in `setUp`.
    #pool: substrate.SqlitePool | undefined = undefined;
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made, each with the pushes its notifier kept.
    readonly #stores = new Map<substrate.Store, Pushed[]>();

    // Reads the module and the pool the test page provides.
    setUp(): void {
      this.#sqlite = test_sqlite3;
      this.#pool = test_pool;
    }

    // Closes every database of the stores and removes the roots' files.
    tearDown(): void {
      for (const store of this.#stores.keys()) {
        for (const name of store.db_list()) {
          store.db_close(name);
        }
      }
      const pool = this.pool_get();
      for (const root of this.#roots) {
        for (const file of pool.getFileNames()) {
          if (file.startsWith(`${root}/`)) {
            pool.unlink(file);
          }
        }
      }
    }

    // The module the test page provides.
    sqlite_get(): substrate.SqliteModule {
      return this.#sqlite as substrate.SqliteModule;
    }

    // The pool the test page provides.
    pool_get(): substrate.SqlitePool {
      return this.#pool as substrate.SqlitePool;
    }

    // A new root no other test uses.
    root_make(): string {
      root_count += 1;
      const root = constants.root_prefix + String(root_count);
      this.#roots.push(root);
      return root;
    }

    // A store on the root whose notifier double keeps each push and owner.
    store_make(
      root: string,
      cache: substrate.CacheFiles,
      pool: substrate.SqlitePool = this.pool_get(),
      compact_turns = harness.setting_get("turn_compact_turns") as number,
    ): substrate.Store {
      const pushed: Pushed[] = [];
      const store = new substrate.Store(
        this.sqlite_get(),
        pool,
        cache,
        root,
        overflow_get(),
        compact_turns,
        {
          line_notify: (line: lines.Line, owner?: string) => {
            pushed.push([line, owner]);
          },
        },
      );
      this.#stores.set(store, pushed);
      return store;
    }

    // A store on a new root with a new cache.
    store_fresh(): substrate.Store {
      return this.store_make(this.root_make(), cache_make());
    }

    // The pushes a store gave its notifier that no test took yet.
    pushes_of(store: substrate.Store): Pushed[] {
      return this.#stores.get(store) as Pushed[];
    }

    // The pushes a store gave its notifier, which are then let go.
    pushes_taken(store: substrate.Store): Pushed[] {
      return this.pushes_of(store).splice(0);
    }

    // The types of the pushes a store gave, which are then let go.
    types_taken(store: substrate.Store): unknown[] {
      return this.pushes_taken(store).map(([line]) => type_pushed(line));
    }

    // The names of the files under a root, in order.
    files_under(root: string): string[] {
      const prefix = `${root}/`;
      return this.pool_get()
        .getFileNames()
        .filter((file) => file.startsWith(prefix))
        .map((file) => file.slice(prefix.length))
        .sort();
    }

    // Opens a file of the pool apart from any store.
    raw_open(path: string, flags: string): substrate.SqliteDatabase {
      const pool = this.pool_get();
      return new pool.OpfsSAHPoolDb({ filename: path, flags });
    }

    // Runs statements on a file of the pool apart from any store.
    raw_run(
      path: string,
      flags: string,
      statements: substrate.ExecOptions[],
    ): void {
      const database = this.raw_open(path, flags);
      try {
        for (const statement of statements) {
          database.exec(statement);
        }
      } finally {
        database.close();
      }
    }

    // The serialized bytes of a file of the pool, read apart from any store.
    raw_export(path: string): Uint8Array {
      const database = this.raw_open(path, "r");
      try {
        return this.sqlite_get().capi.sqlite3_js_db_export(database.pointer);
      } finally {
        database.close();
      }
    }
  }

  // `Key-Value-Ref` and `Document-Ref` splitting, bad refs, their database.
  export class TestRefs extends StoreCase {
    // Each form splits into its database, its key and its version.
    test_split_forms(): void {
      const cases: [string, substrate.RefParts][] = [
        [
          constants.scene,
          { db: "metaverse", key: "hyperposition/1", version: 1 },
        ],
        ["/metaverse/world", { db: "metaverse", key: "world" }],
        ["script/bootstrap.js", { key: "script/bootstrap.js" }],
        ["scene/arrival/12", { key: "scene/arrival/12", version: 12 }],
        ["/_files/a//b/", { db: "_files", key: "a//b/" }],
        ["maps/01", { key: "maps/01" }],
        ["7", { key: "7" }],
        [
          "/x/" + constants.text_wide + "/0",
          { db: "x", key: constants.text_wide + "/0", version: 0 },
        ],
        ["/x/line\nbreak", { db: "x", key: "line\nbreak" }],
      ];
      for (const [ref, parts] of cases) {
        this.assertEqual(substrate.ref_split(ref), parts, ref);
      }
    }

    // An empty ref, a missing key and a bad database name throw.
    test_refs_bad(): void {
      const refs: [string, string][] = [
        ["", "substrate_ref_bad_empty"],
        ["/", "substrate_ref_bad_slash"],
        ["//key", "substrate_ref_bad_db_empty"],
        ["/metaverse", "substrate_ref_bad_key_none"],
        ["/metaverse/", "substrate_ref_bad_key_empty"],
        ["/1db/key", "substrate_ref_bad_db_digit"],
        ["/d-b/key", "substrate_ref_bad_db_dash"],
        [
          "/caf" + String.fromCodePoint(0xe9) + "/key",
          "substrate_ref_bad_db_wide",
        ],
      ];
      for (const [ref, text] of refs) {
        this.raised_assert(gold_text(text), () => substrate.ref_split(ref));
      }
    }

    // An internal ref needs a database and an external ref takes none.
    test_ref_database(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const value = bytes_text("x");
      this.raised_assert(gold_text("substrate_ref_internal"), () =>
        store.kv_put("world", value),
      );
      const both = gold_text("substrate_ref_both");
      this.raised_assert(both, () =>
        store.kv_put("/alpha/world", value, "alpha"),
      );
      this.raised_assert(both, () => store.kv_get("/alpha/world", "alpha"));
      this.raised_assert(gold_text("substrate_db_closed_beta"), () =>
        store.kv_put("/beta/world", value),
      );
      this.raised_assert(gold_text("substrate_document_ref_key"), () =>
        store.doc_get("/alpha/world"),
      );
      this.assertEqual(store.kv_list("alpha", ""), []);
    }
  }

  // Documents: versions and heads, the round trip, reference strings, faults.
  export class TestDocuments extends StoreCase {
    // Each put writes the next version and moves the head, versions stay.
    test_document_heads(): void {
      const store = this.store_fresh();
      const db = "castle_gatehouse";
      store.db_create(db);
      const first = store.doc_put(db, "scene/arrival", arrival_make());
      this.assertEqual(first, { ref: "/castle_gatehouse/scene/arrival/1" });
      this.assertEqual(store.doc_head(db, "scene/arrival"), first.ref);
      this.assertEqual(
        store.kv_get(first.ref).data,
        bytes_text(arrival_stored()),
      );
      const changed = { ...arrival_make(), subtitle: "The keeper waves." };
      const second = store.doc_put(db, "scene/arrival", changed);
      this.assertEqual(second, { ref: "/castle_gatehouse/scene/arrival/2" });
      this.assertEqual(store.doc_head(db, "scene/arrival"), second.ref);
      this.assertEqual(store.doc_get(first.ref), arrival_make());
      const text = JSON.stringify(store.doc_get(first.ref));
      this.assertEqual(text, arrival_stored());
      this.assertEqual(store.doc_get("scene/arrival/2", db), changed);
      this.raised_assert(gold_text("substrate_id_missing_absent"), () =>
        store.doc_head(db, "scene/absent"),
      );
      this.raised_assert(gold_text("substrate_key_missing_version"), () =>
        store.doc_get("/castle_gatehouse/scene/arrival/3"),
      );
      this.raised_assert(gold_text("substrate_document_ref_scene"), () =>
        store.doc_get("/castle_gatehouse/scene/arrival"),
      );
    }

    // A put whose next version is already a row throws and moves no head.
    test_version_exists(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/note/1", bytes_text("{}"));
      this.raised_assert(gold_text("substrate_version_exists"), () =>
        store.doc_put("alpha", "note", { 0: { t: "note" } }),
      );
      this.raised_assert(gold_text("substrate_id_missing_note"), () =>
        store.doc_head("alpha", "note"),
      );
      this.assertEqual(
        store.kv_list("alpha", "").map((row) => row.k),
        ["note/1"],
      );
    }

    // A nested document is stored as the text the wire's encoder writes.
    test_nested_text(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const ref = store.doc_put("alpha", "nest", nested_make()).ref;
      const stored = store.kv_get(ref).data as Uint8Array;
      this.assertEqual(stored, bytes_text(gold_text("nested_stored")));
      this.assertEqual(store.doc_get(ref), nested_make());
    }

    // Encoding moves refs into shared headers and decoding restores them.
    test_round_trip(): void {
      const encoded = substrate.doc_encode(fog_normal());
      this.assertEqual(encoded, fog_encoded());
      this.assertEqual(JSON.stringify(encoded), JSON.stringify(fog_encoded()));
      const decoded = substrate.doc_decode(encoded);
      this.assertEqual(decoded, fog_normal());
      this.assertEqual(JSON.stringify(decoded), JSON.stringify(fog_normal()));
    }

    // Documents that would not round trip, or are malformed, throw.
    test_documents_bad(): void {
      const normals: [{ [key: string]: unknown }, string][] = [
        [{ subtitle: "x" }, gold_text("substrate_header_missing")],
        [
          { 0: { t: "scene", v: 0 } },
          gold_text("substrate_header_bad_version"),
        ],
        [{ 0: { v: 2 } }, gold_text("substrate_header_bad_type")],
        [{ 0: { t: "scene", x: 1 } }, gold_text("substrate_header_bad_field")],
        [{ 0: "scene" }, gold_text("substrate_header_bad_text")],
        [
          { 0: { t: "scene" }, 1: "/a/b" },
          gold_text("substrate_header_normal"),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, gold_text("substrate_key_digits")],
        [
          { 0: { t: "scene" }, x: { $ref: 1 } },
          gold_text("substrate_ref_shape"),
        ],
      ];
      for (const [normal, message] of normals) {
        this.raised_assert(message, () => substrate.doc_encode(normal));
      }
      const encodeds: [lines.Document, string][] = [
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: 2 } },
          gold_text("substrate_ref_index_two"),
        ],
        [
          { 0: { t: "scene" }, 2: "/a/b", x: { $ref: 2 } },
          gold_text("substrate_header_gap"),
        ],
        [
          { 0: { t: "scene" }, 1: 5, x: { $ref: 1 } },
          gold_text("substrate_header_ref"),
        ],
        [
          { 0: { t: "scene" }, 1: "world", x: { $ref: 1 } },
          gold_text("substrate_header_ref"),
        ],
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: true } },
          gold_text("substrate_ref_index_true"),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, gold_text("substrate_key_digits")],
      ];
      for (const [encoded, message] of encodeds) {
        this.raised_assert(message, () => substrate.doc_decode(encoded));
      }
    }

    // A string whose key holds a space, as Python counts space, stays text.
    test_spaces_kept(): void {
      const lines_kept = [
        "/me/ waves and leaves",
        "/me/waves and\nleaves",
        "/me/a b",
      ];
      const python_spaces = [0x1c, 0x1f, 0x85].map(
        (point) => "/me/a" + String.fromCodePoint(point) + "b",
      );
      const marked = "/me/a" + String.fromCodePoint(0xfeff) + "b";
      const normal = {
        0: { t: "scene" },
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: "/me/waves",
        marked,
      };
      const expected = {
        0: { t: "scene" },
        1: "/me/waves",
        2: marked,
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: { $ref: 1 },
        marked: { $ref: 2 },
      };
      this.assertEqual(substrate.doc_encode(normal), expected);
      this.assertEqual(substrate.doc_decode(expected), normal);
      const kept = ["/me waves/ and leaves", ...lines_kept, ...python_spaces];
      for (const text of kept) {
        this.raised_assert(gold_text("substrate_header_ref"), () =>
          substrate.doc_decode({ 0: { t: "scene" }, 1: text }),
        );
      }
    }
  }

  // The sink's incremental `SHA-256`, against the digests of the vectors.
  export class TestHash extends RefusalCase {
    // Streamed values give their known digests.
    test_digest_recorded(): void {
      const names = [
        "castle_world",
        "arrival_ref",
        "arrival_image",
        "step_script",
        "map",
      ];
      for (const name of names) {
        const { data, sha256 } = digest_entry(name);
        for (const piece of [1, 7, 64, 4097, data.length]) {
          this.assertEqual(digest_streamed(data, piece), sha256);
        }
      }
    }

    // Every length around the block and padding bounds, in pieces of any size.
    test_digest_lengths(): void {
      const lengths = [0, 1, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 1000];
      for (const length of lengths) {
        const entry = digest_entry(`pattern_${String(length)}`);
        const data = entry.data;
        const digest = entry.sha256;
        for (const piece of [1, 7, 63, 64, 65, Math.max(1, length)]) {
          this.assertEqual(
            digest_streamed(data, piece),
            digest,
            `${String(length)} by ${String(piece)}`,
          );
        }
      }
    }
  }

  // The cache: the sink, ranges, partial blobs, files found and faults.
  export class TestCache extends RefusalCase {
    // A finished blob reads back by range, a copy of the bytes it was given.
    test_sink_read(): void {
      const cache = new substrate.CacheFiles(slots_make(2));
      const entry = digest_entry("pattern_10");
      const data = entry.data;
      const handle = cache.sink_open({ s: 10 });
      const first = data.slice(0, 4);
      cache.sink_append(handle, first);
      first.fill(255);
      cache.sink_append(handle, data.subarray(4));
      this.assertEqual(cache.sink_close(handle), entry.sha256);
      this.assertEqual(cache.cache_read(handle, 0, 10), data);
      this.assertEqual(cache.cache_read(handle, 3, 4), data.subarray(3, 7));
      this.assertEqual(cache.cache_read(handle, 8, 5), data.subarray(8));
      this.assertEqual(cache.cache_read(handle, 10, 4), new Uint8Array(0));
      this.assertEqual(cache.cache_read(handle, 12, 4), new Uint8Array(0));
      this.assertEqual(cache.slots_free(), 1);
    }

    // A blob closed short of its size, after a decoder fault, is freed.
    test_sink_partial(): void {
      const cache = new substrate.CacheFiles(slots_make(1));
      const handle = cache.sink_open({ s: 10 });
      this.assertEqual(cache.slots_free(), 0);
      const entry = digest_entry("pattern_4");
      cache.sink_append(handle, entry.data);
      this.assertEqual(cache.sink_close(handle), entry.sha256);
      this.assertEqual(cache.slots_free(), 1);
      const unknown = unknown_text(handle);
      this.raised_assert(unknown, () => cache.cache_read(handle, 0, 1));
      this.raised_assert(unknown, () =>
        cache.sink_append(handle, bytes_pattern(1)),
      );
      this.raised_assert(unknown, () => cache.sink_close(handle));
    }

    // A cache with no free file refuses a blob until a file is added.
    test_cache_full(): void {
      const cache = new substrate.CacheFiles(slots_make(1));
      cache.sink_open({ s: 1 });
      this.raised_assert(gold_text("substrate_cache_full_one"), () =>
        cache.sink_open({ s: 1 }),
      );
      const empty = new substrate.CacheFiles([]);
      this.raised_assert(gold_text("substrate_cache_full_none"), () =>
        empty.sink_open({ s: 1 }),
      );
      empty.slot_add(new MemorySlot());
      this.assertEqual(empty.slots_free(), 1);
      empty.sink_open({ s: 1 });
      this.assertEqual(empty.slots_free(), 0);
    }

    // Files hold the value their first bytes name, others are free.
    test_slots_found(): void {
      const entry = digest_entry("pattern_100");
      const data = entry.data;
      const name = entry.sha256;
      const left = new MemorySlot();
      left.bytes_set(bytes_join([new Uint8Array(constants.name_bytes), data]));
      const empty = new MemorySlot();
      const cache = new substrate.CacheFiles([
        slot_stored(name, data),
        left,
        empty,
      ]);
      this.assertEqual(cache.slots_free(), 2);
      this.assertEqual(cache.cache_read(name, 0, 100), data);
      this.assertEqual(cache.cache_read(name, 90, 20), data.subarray(90));
      const handle = cache.sink_open({ s: 3 });
      cache.sink_append(handle, bytes_pattern(3));
      cache.sink_close(handle);
      this.assertEqual(cache.slots_free(), 1);
      this.assertEqual(
        empty.bytes_get(),
        bytes_join([new Uint8Array(constants.name_bytes), bytes_pattern(3)]),
      );
    }

    // A file whose first bytes name no `SHA-256`, or a name twice, throws.
    test_names_bad(): void {
      const garbled = "z".repeat(constants.name_bytes);
      this.raised_assert(gold_text("substrate_cache_header"), () => {
        new substrate.CacheFiles([slot_stored(garbled, bytes_pattern(1))]);
      });
      const { data, sha256 } = digest_entry("pattern_1");
      const twice = gold_text("substrate_cache_twice");
      this.raised_assert(twice.replaceAll("{0}", sha256), () => {
        new substrate.CacheFiles([
          slot_stored(sha256, data),
          slot_stored(sha256, data),
        ]);
      });
    }

    // A read or write the file reports short throws.
    test_short_io(): void {
      const free = new ShortSlot();
      const writer = new substrate.CacheFiles([free]);
      free.short = true;
      this.raised_assert(gold_text("substrate_write_short"), () =>
        writer.sink_open({ s: 1 }),
      );
      const { data, sha256: name } = digest_entry("pattern_10");
      const stored = new ShortSlot();
      stored.bytes_set(bytes_join([bytes_text(name), data]));
      const reader = new substrate.CacheFiles([stored]);
      stored.short = true;
      this.raised_assert(gold_text("substrate_read_short"), () =>
        reader.cache_read(name, 0, 10),
      );
    }
  }

  // Databases: tables on first use, names, creating, opening, dropping.
  export class TestDatabases extends StoreCase {
    // A new database gets the substrate's tables and the `schema` row 1.
    test_tables_created(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.assertEqual(tables_list(store, "alpha"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
      ]);
      const meta = "SELECT name, value FROM _meta ORDER BY name";
      this.assertEqual(rows_query(store, "alpha", meta), [["schema", "1"]]);
      this.assertEqual(store.db_list(), ["alpha"]);
    }

    // A database file made elsewhere gets the tables when first opened.
    test_tables_foreign(): void {
      const root = this.root_make();
      this.raw_run(`${root}/beta.sqlite`, "c", [
        { sql: "CREATE TABLE note (text TEXT)" },
        { sql: "INSERT INTO note VALUES (?)", bind: [constants.text_wide] },
      ]);
      const store = this.store_make(root, cache_make());
      store.db_open("beta");
      this.assertEqual(tables_list(store, "beta"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
        "note",
      ]);
      this.assertEqual(rows_query(store, "beta", "SELECT text FROM note"), [
        [constants.text_wide],
      ]);
    }

    // A name that is not a C identifier throws and makes no file.
    test_names_bad(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      const names: [string, string][] = [
        ["", "substrate_name_bad_empty"],
        ["1abc", "substrate_name_bad_digit"],
        ["a-b", "substrate_name_bad_dash"],
        ["a b", "substrate_name_bad_space"],
        ["a.b", "substrate_name_bad_dot"],
        ["a/b", "substrate_name_bad_slash"],
        ["caf" + String.fromCodePoint(0xe9), "substrate_name_bad_wide"],
      ];
      for (const [name, text] of names) {
        const message = gold_text(text);
        this.raised_assert(message, () => store.db_create(name));
        this.raised_assert(message, () => store.db_open(name));
      }
      this.assertEqual(this.files_under(root), []);
      this.assertEqual(store.db_list(), []);
      this.assertEqual(this.pushes_of(store), []);
    }

    // A second create, a second open, a missing file and a close all throw.
    test_create_twice(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      this.raised_assert(gold_text("substrate_db_exists"), () =>
        store.db_create("alpha"),
      );
      this.raised_assert(gold_text("substrate_db_open"), () =>
        store.db_open("alpha"),
      );
      this.raised_assert(gold_text("substrate_db_absent"), () =>
        store.db_open("gamma"),
      );
      this.assertEqual(this.files_under(root), ["alpha.sqlite"]);
      this.raised_assert(gold_text("substrate_db_closed_gamma"), () =>
        store.db_close("gamma"),
      );
      this.assertEqual(this.types_taken(store), ["db.create"]);
    }

    // A create whose schema fails throws it, leaves no file, and is redone.
    test_create_failed(): void {
      const root = this.root_make();
      // The failure the test makes where the schema is written.
      const schema_stop = (): never => {
        throw new Error(constants.schema_message);
      };
      const prefix = constants.schema_create;
      const pool = pool_stopped(this.pool_get(), schema_stop, prefix);
      const failing = this.store_make(root, cache_make(), pool);
      this.raised_assert(constants.schema_message, () =>
        failing.db_create("alpha"),
      );
      this.assertEqual(this.files_under(root), []);
      this.assertEqual(failing.db_list(), []);
      this.assertEqual(this.pushes_of(failing), []);
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      this.assertEqual(store.db_list(), ["alpha"]);
    }

    // A file with only some of the substrate's tables throws, kept as it is.
    test_schema_partial(): void {
      const root = this.root_make();
      const path = `${root}/beta.sqlite`;
      this.raw_run(path, "c", [{ sql: constants.meta_sql }]);
      const store = this.store_make(root, cache_make());
      this.raised_assert(gold_text("substrate_schema_partial_meta"), () =>
        store.db_open("beta"),
      );
      this.assertEqual(store.db_list(), []);
      const raw = this.raw_open(path, "r");
      const rows: unknown[][] = [];
      try {
        raw.exec({
          sql: "SELECT name FROM sqlite_schema WHERE type = 'table'",
          rowMode: "array",
          resultRows: rows,
        });
      } finally {
        raw.close();
      }
      this.assertEqual(rows, [["_meta"]]);
    }

    // A file whose `schema` row is not the substrate's version throws.
    test_schema_version(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("beta");
      store.db_close("beta");
      this.raw_run(`${root}/beta.sqlite`, "w", [
        {
          sql: "UPDATE _meta SET value = ? WHERE name = 'schema'",
          bind: ["2"],
        },
      ]);
      this.raised_assert(gold_text("substrate_schema_version"), () =>
        store.db_open("beta"),
      );
      this.assertEqual(store.db_list(), []);
    }

    // Closing, dropping or restoring a database a transaction wrote throws.
    test_database_busy(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      const data = store.db_snapshot("alpha").data;
      const files = this.files_under(root);
      this.pushes_taken(store);
      const calls: (() => unknown)[] = [
        () => store.db_close("alpha"),
        () => store.db_drop("alpha"),
        () => store.db_restore("alpha", data, []),
      ];
      for (const call of calls) {
        this.raised_assert(gold_text("substrate_db_busy"), () =>
          store.transaction_run(() => {
            store.kv_put("/alpha/busy", bytes_text("busy"));
            call();
          }),
        );
        this.assertEqual(store.db_list(), ["alpha"]);
        this.assertEqual(store.kv_list("alpha", ""), []);
        this.assertEqual(this.files_under(root), files);
        this.assertEqual(this.pushes_of(store), []);
      }
    }

    // Dropping removes the file and the cache files no other database names.
    test_drop_files(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache);
      store.db_create("alpha");
      store.db_create("beta");
      const alone = value_other();
      const alone_name = digest_entry("value_other").sha256;
      const shared_name = digest_entry("value_over").sha256;
      store.kv_put("/alpha/shared", value_over());
      store.kv_put("/alpha/alone", alone);
      store.kv_put("/beta/shared", value_over());
      store.db_drop("alpha");
      this.assertEqual(this.files_under(root), ["beta.sqlite"]);
      this.raised_assert(unknown_text(alone_name), () =>
        cache.cache_read(alone_name, 0, 1),
      );
      this.assertEqual(cache.cache_read(shared_name, 0, 1).length, 1);
      this.assertEqual(store.db_list(), ["beta"]);
      this.assertEqual(store.kv_get("/beta/shared").data, shared_name);
      store.db_drop("beta");
      this.raised_assert(unknown_text(shared_name), () =>
        cache.cache_read(shared_name, 0, 1),
      );
      this.assertEqual(this.files_under(root), []);
    }
  }

  // Values: both ref forms, the overflow limit, shared and lost cache files.
  export class TestValues extends StoreCase {
    // A value put by one ref form is read by the other, listed and deleted.
    test_refs_both(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const key = "greeting/" + constants.text_wide;
      const { data: value, sha256: digest } = digest_entry("hello_wide");
      const row = { k: key, size: value.length, sha256: digest };
      this.assertEqual(store.kv_put("/alpha/" + key, value), row);
      this.assertEqual(store.kv_get(key, "alpha"), {
        data: value,
        size: value.length,
        sha256: digest,
      });
      const world = bytes_text("world");
      const place = store.kv_put("place/a/b", world, "alpha");
      this.assertEqual(place.k, "place/a/b");
      this.assertEqual(store.kv_get("/alpha/place/a/b").data, world);
      this.assertEqual(store.kv_list("alpha", "greeting/"), [row]);
      this.assertEqual(
        store.kv_list("alpha", "").map((listed) => listed.k),
        [key, "place/a/b"],
      );
      this.assertEqual(store.kv_delete(key, "alpha"), undefined);
      this.raised_assert(gold_text("substrate_key_missing_wide"), () =>
        store.kv_get("/alpha/" + key),
      );
    }

    // A value of exactly `overflow_bytes` stays in its row, one byte more not.
    test_overflow_boundary(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache);
      store.db_create("alpha");
      store.kv_put("/alpha/exact", value_exact());
      const exact = store.kv_get("/alpha/exact");
      this.assertEqual(exact.data, value_exact());
      this.assertEqual(exact.size, overflow_get());
      const exact_name = digest_entry("value_exact").sha256;
      this.raised_assert(unknown_text(exact_name), () =>
        cache.cache_read(exact_name, 0, 1),
      );
      store.kv_put("/alpha/over", value_over());
      const name = digest_entry("value_over").sha256;
      this.assertEqual(store.kv_get("/alpha/over"), {
        data: name,
        size: overflow_get() + 1,
        sha256: name,
      });
      this.assertEqual(
        cache.cache_read(name, 0, overflow_get() + 1),
        value_over(),
      );
    }

    // A cache file stays while any row of any database names its hash.
    test_cache_shared(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache);
      const name = digest_entry("value_over").sha256;
      // The bytes the cache file gives from its start, one when it is there.
      const cache_present = (): number => cache.cache_read(name, 0, 1).length;
      store.db_create("alpha");
      store.db_create("beta");
      store.kv_put("/alpha/one", value_over());
      store.kv_put("/alpha/two", value_over());
      store.kv_put("/beta/three", value_over());
      store.kv_delete("/alpha/one");
      this.assertEqual(cache_present(), 1);
      store.kv_put("/alpha/two", bytes_text("small"));
      this.assertEqual(cache_present(), 1);
      store.db_close("beta");
      store.kv_put("/alpha/two", value_over());
      store.kv_delete("/alpha/two");
      this.assertEqual(cache_present(), 1);
      store.db_open("beta");
      store.kv_delete("/beta/three");
      this.raised_assert(unknown_text(name), cache_present);
      this.assertEqual(store.kv_check("alpha"), 0);
    }

    // A blob the sink streamed moves into place, a small one is refused.
    test_handle_moved(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache);
      store.db_create("alpha");
      const handle = sink_fill(cache, value_over());
      const name = digest_entry("value_over").sha256;
      const size = overflow_get() + 1;
      this.assertEqual(store.kv_put("/alpha/streamed", handle), {
        k: "streamed",
        size,
        sha256: name,
      });
      this.raised_assert(unknown_text(handle), () =>
        cache.cache_read(handle, 0, 1),
      );
      this.assertEqual(store.kv_get("/alpha/streamed").data, name);
      const small = sink_fill(cache, value_exact());
      const overflow = String(overflow_get());
      this.raised_assert(
        gold_text("substrate_file_small")
          .replaceAll("{0}", small)
          .replaceAll("{1}", overflow)
          .replaceAll("{2}", overflow),
        () => store.kv_put("/alpha/small", small),
      );
      this.assertEqual(
        store.kv_list("alpha", "").map((row) => row.k),
        ["streamed"],
      );
      this.assertEqual(store.kv_check("alpha"), 0);
      this.assertEqual(cache.cache_read(small, 0, 1).length, 1);
    }

    // A row whose cache file this store lacks stays, and only its read throws.
    test_file_lost(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      store.kv_put("/alpha/big", value_over());
      const text = "x".repeat(overflow_get() + 1);
      const body = { 0: { t: "note" }, text };
      const ref = store.doc_put("alpha", "note", body).ref;
      store.db_close("alpha");
      const again = this.store_make(root, cache_make());
      again.db_open("alpha");
      const name = digest_entry("value_over").sha256;
      const big = gold_text("substrate_file_lost_big").replaceAll("{1}", name);
      this.raised_assert(big, () => again.kv_get("/alpha/big"));
      const note = again.kv_list("alpha", "note/")[0].sha256;
      this.raised_assert(lost_text(ref, note), () => again.doc_get(ref));
      this.assertEqual(again.kv_list("alpha", "big"), [
        { k: "big", size: overflow_get() + 1, sha256: name },
      ]);
      again.kv_put("/alpha/big", bytes_text("new"));
      this.assertEqual(again.kv_get("/alpha/big").data, bytes_text("new"));
      this.assertEqual(again.kv_check("alpha"), 0);
    }
  }

  // Documents in a store: stored text and numbers, wide versions, refusals.
  export class TestStored extends StoreCase {
    // An encoded document is stored and read back as the same text.
    test_stored_trip(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const put = store.doc_put("metaverse", "fog", fog_encoded());
      this.assertEqual(put, { ref: "/metaverse/fog/1" });
      const stored = store.doc_get(put.ref);
      this.assertEqual(JSON.stringify(stored), JSON.stringify(fog_encoded()));
      this.assertEqual(substrate.doc_decode(stored), fog_normal());
    }

    // Numbers below `1e-4` are stored as Python's `repr` writes them.
    test_numbers_small(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const body = { 0: { t: "note" }, a: 0.00001, b: -1.5e-7, c: 0.0001 };
      const ref = store.doc_put("alpha", "note", body).ref;
      this.assertEqual(
        store.kv_get(ref).data,
        bytes_text('{"0":{"t":"note"},"a":1e-05,"b":-1.5e-07,"c":0.0001}'),
      );
    }

    // A head past `2^53` moves to the exact next version, as in Python.
    test_version_wide(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.sql_run("alpha", [
        {
          sql: "INSERT INTO _head (id, version) VALUES (?, ?)",
          params: ["note", "9007199254740993"],
        },
      ]);
      const put = store.doc_put("alpha", "note", { 0: { t: "note" } });
      this.assertEqual(put.ref, "/alpha/note/9007199254740994");
      this.assertEqual(store.doc_head("alpha", "note"), put.ref);
      const head = "SELECT CAST(version AS TEXT) FROM _head";
      this.assertEqual(rows_query(store, "alpha", head), [
        ["9007199254740994"],
      ]);
    }

    // Values JSON cannot carry, and bad ids and headers, throw.
    test_values_refused(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const note = { t: "note" };
      const cases: [lines.Document, string][] = [
        [
          { 0: note, x: "a" + String.fromCharCode(0xd800) },
          gold_text("substrate_text_refused"),
        ],
        [
          { 0: note, x: new Uint8Array(1) },
          gold_text("substrate_value_refused_bytes"),
        ],
        [
          { 0: note, x: undefined },
          gold_text("substrate_value_refused_undefined"),
        ],
        [{ 0: note, 2: "/a/b" }, gold_text("substrate_header_gap")],
      ];
      for (const [body, message] of cases) {
        this.raised_assert(message, () => store.doc_put("alpha", "x", body));
      }
      this.raised_assert(gold_text("substrate_id_empty"), () =>
        store.doc_put("alpha", "", { 0: note }),
      );
      this.assertEqual(store.kv_list("alpha", ""), []);
    }
  }

  // Turns: appended in order, listed, and compacted into one summary.
  export class TestTurns extends StoreCase {
    // Turns number from 1 in their scene, a bad scene or content throws.
    test_turns_append(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const scene = constants.scene;
      const user: provider.ChatMessage = { role: "user", content: "1" };
      const answer: provider.ChatMessage = {
        role: "assistant",
        content: constants.text_wide,
      };
      this.assertEqual(store.turn_append(scene, "user", user), { n: 1 });
      this.assertEqual(store.turn_append(scene, "assistant", answer), {
        n: 2,
      });
      this.assertEqual(store.turn_list(scene), [
        { scene, n: 1, role: "user", content: user },
        { scene, n: 2, role: "assistant", content: answer },
      ]);
      this.assertEqual(store.turn_list("/metaverse/elsewhere/1"), []);
      const scenes_bad: [string, string][] = [
        ["hyperposition/1", "substrate_scene_bad_internal"],
        ["/metaverse/world", "substrate_scene_bad_key"],
      ];
      for (const [bad, text] of scenes_bad) {
        this.raised_assert(gold_text(text), () =>
          store.turn_append(bad, "user", user),
        );
      }
      this.sqlite_assert("CHECK constraint failed: json_valid(content)", () =>
        store.sql_run("metaverse", [
          {
            sql:
              "INSERT INTO _turn (scene, n, role, content)" +
              " VALUES (?, ?, ?, ?)",
            params: [scene, 3, "user", "not json"],
          },
        ]),
      );
      this.assertEqual(store.turn_list(scene).length, 2);
    }

    // Compaction replaces turns 1 to `through` by one summary turn at 1.
    test_turns_compact(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const scene = constants.scene;
      for (const text of ["1", "2", "3", "4"]) {
        store.turn_append(scene, "user", { role: "user", content: text });
      }
      this.pushes_taken(store);
      this.assertEqual(
        store.turn_compact(scene, 3, "Asked thrice."),
        undefined,
      );
      this.assertEqual(this.pushes_of(store), []);
      const fourth: provider.ChatMessage = { role: "user", content: "4" };
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: { role: "system", content: "Asked thrice." },
        },
        { scene, n: 4, role: "user", content: fourth },
      ]);
      this.assertEqual(store.turn_append(scene, "user", fourth), { n: 5 });
      this.assertEqual(this.types_taken(store), ["turn.append"]);
      this.raised_assert(gold_text("substrate_through_bad"), () =>
        store.turn_compact(scene, 0, "None."),
      );
      const elsewhere = "/metaverse/elsewhere/1";
      this.raised_assert(gold_text("substrate_turns_none"), () =>
        store.turn_compact(elsewhere, 2, "None."),
      );
      this.assertEqual(store.turn_list(scene).length, 3);
    }
  }

  // Compaction at `turn_compact_turns`: when it runs, what it writes, sends.
  export class TestCompaction extends StoreCase {
    // A `user` turn at the threshold compacts its scene first, sending none.
    test_threshold_reached(): void {
      const store = this.store_compacting();
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      const other = "/alpha/scene/2";
      store.turn_append(scene, "user", message_said("user", "1"));
      store.turn_append(scene, "assistant", message_said("assistant", "2"));
      this.assertEqual(
        store.turn_append(scene, "user", message_said("user", "3")),
        { n: 3 },
      );
      this.assertEqual(
        store.turn_append(scene, "assistant", message_said("assistant", "4")),
        { n: 4 },
      );
      this.assertEqual(
        store.turn_append(other, "user", message_said("user", "a")),
        { n: 1 },
      );
      this.pushes_taken(store);
      const fifth = message_said("user", "5");
      this.assertEqual(store.turn_append(scene, "user", fifth), { n: 2 });
      const summary = gold_text("substrate_turns_compacted_four");
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: message_said("system", summary),
        },
        { scene, n: 2, role: "user", content: fifth },
      ]);
      this.assertEqual(this.types_taken(store), ["turn.append"]);
      const opening = message_said("user", "a");
      this.assertEqual(store.turn_list(other), [
        { scene: other, n: 1, role: "user", content: opening },
      ]);
      this.assertEqual(
        store.turn_append(scene, "user", message_said("user", "6")),
        { n: 3 },
      );
      this.assertEqual(store.turn_list(scene).length, 3);
    }

    // The compaction rolls back with the transaction of its `user` turn.
    test_compaction_rolled(): void {
      const store = this.store_compacting();
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      for (const text of ["1", "2", "3"]) {
        store.turn_append(scene, "assistant", message_said("assistant", text));
      }
      this.pushes_taken(store);
      const before = store.turn_list(scene);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.turn_append(scene, "user", message_said("user", "4"));
          throw new Error("rolled back");
        }),
      );
      this.assertEqual(store.turn_list(scene), before);
      this.assertEqual(this.pushes_of(store), []);
    }

    // A store on a new root whose threshold is small.
    store_compacting(): substrate.Store {
      return this.store_make(
        this.root_make(),
        cache_make(),
        this.pool_get(),
        constants.compact_small,
      );
    }
  }

  // SQL: the results of statements, what is refused, the trigger names.
  export class TestSql extends StoreCase {
    // Statements return columns, rows and changes, and only writes count.
    test_sql_results(): void {
      const store = this.store_fresh();
      store.db_create("castle");
      const results = store.sql_run("castle", [
        { sql: constants.world_sql, params: [] },
        {
          sql: "INSERT INTO world VALUES (?, ?)",
          params: ["castle_world", "The castle"],
        },
      ]);
      this.assertEqual(results, [
        { columns: [], rows: [], changes: 0 },
        { columns: [], rows: [], changes: 1 },
      ]);
      const selected = store.sql_run("castle", [
        { sql: "SELECT name, title FROM world", params: [] },
      ]);
      this.assertEqual(selected, [
        {
          columns: ["name", "title"],
          rows: [["castle_world", "The castle"]],
          changes: 0,
        },
      ]);
    }

    // Two statements in one, a parameter count that differs, an SQL error.
    test_statements_refused(): void {
      const store = this.store_fresh();
      store.db_create("castle");
      this.pushes_taken(store);
      const twice = "SELECT 1; SELECT 2";
      this.raised_assert(gold_text("substrate_statement_many"), () =>
        store.sql_run("castle", [{ sql: twice, params: [] }]),
      );
      this.raised_assert(gold_text("substrate_params_count_missing"), () =>
        store.sql_run("castle", [{ sql: "SELECT ?", params: [] }]),
      );
      this.raised_assert(gold_text("substrate_params_count_extra"), () =>
        store.sql_run("castle", [{ sql: "SELECT 1", params: [1] }]),
      );
      this.sqlite_assert("no such table: absent", () =>
        store.sql_run("castle", [
          { sql: "INSERT INTO absent VALUES (1)", params: [] },
        ]),
      );
      this.assertEqual(this.pushes_of(store), []);
    }

    // A trigger's name of a string is thrown as that string, SQLite's cause.
    test_trigger_name(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      store.sql_run("metaverse", [
        { sql: constants.universe_sql, params: [] },
        { sql: constants.trigger_sql, params: [] },
      ]);
      const insert = "INSERT INTO universe VALUES (?, ?, ?, ?)";
      store.sql_run("metaverse", [
        {
          sql: insert,
          params: ["castle", "The castle", "player", "castle_world"],
        },
      ]);
      this.pushes_taken(store);
      const error = this.error_get(() =>
        store.sql_run("metaverse", [
          {
            sql: insert,
            params: ["moat", "The moat", "player", "castle_world"],
          },
        ]),
      );
      this.assertTrue(error.constructor === Error, "a plain Error expected");
      this.assertEqual(error.message, gold_text("agent_content_ambiguous"));
      const cause = error.cause;
      this.assertTrue(cause instanceof Error, "an Error cause was expected");
      const message = (cause as Error).message;
      this.assertTrue(message.endsWith(constants.trigger_name), message);
      const names = "SELECT name FROM universe ORDER BY name";
      this.assertEqual(rows_query(store, "metaverse", names), [["castle"]]);
      this.assertEqual(this.pushes_of(store), []);
    }
  }

  // Transactions, and what survives closing and reopening.
  export class TestTransactions extends StoreCase {
    // Writes in one `transaction_run` commit together or roll back together.
    test_transaction_whole(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.db_create("beta");
      store.transaction_run(() => {
        store.kv_put("/alpha/a", bytes_text("1"));
        store.kv_put("/beta/b", bytes_text("2"));
        store.kv_put("/alpha/c", bytes_text("3"));
      });
      this.assertEqual(
        store.kv_list("alpha", "").map((row) => row.k),
        ["a", "c"],
      );
      this.assertEqual(store.kv_get("/beta/b").data, bytes_text("2"));
      this.pushes_taken(store);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/d", value_over());
          store.kv_delete("/alpha/a");
          throw new Error("rolled back");
        }),
      );
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("1"));
      this.raised_assert(gold_text("substrate_key_missing_d"), () =>
        store.kv_get("/alpha/d"),
      );
      this.assertEqual(this.pushes_of(store), []);
      this.assertEqual(store.kv_check("alpha"), 1);
    }

    // A failure after one of two databases was written rolls both back.
    test_transaction_split(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.db_create("beta");
      this.sqlite_assert("no such table: absent", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/a", bytes_text("1"));
          store.sql_run("beta", [
            { sql: "CREATE TABLE note (x TEXT)", params: [] },
            { sql: "INSERT INTO absent VALUES (1)", params: [] },
          ]);
        }),
      );
      this.raised_assert(gold_text("substrate_key_missing_a"), () =>
        store.kv_get("/alpha/a"),
      );
      this.assertEqual(store.kv_list("alpha", ""), []);
      this.assertEqual(tables_list(store, "beta"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
      ]);
      this.assertEqual(this.types_taken(store), ["db.create", "db.create"]);
    }

    // Rows and values survive closing, reopening and a new store on the root.
    test_reopen(): void {
      const root = this.root_make();
      const slots = slots_make(slot_count());
      const first = new substrate.CacheFiles(slots);
      const store = this.store_make(root, first);
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      store.kv_put("/alpha/big", value_over());
      const note = { 0: { t: "note" }, text: constants.text_wide };
      const ref = store.doc_put("alpha", "note", note).ref;
      const scene = "/alpha/scene/1";
      const hi = message_said("user", "hi");
      store.turn_append(scene, "user", hi);
      const rows = store.kv_list("alpha", "");
      store.db_close("alpha");
      this.assertEqual(store.db_list(), []);
      store.db_open("alpha");
      this.assertEqual(store.kv_list("alpha", ""), rows);
      store.db_close("alpha");
      const cache = new substrate.CacheFiles(slots);
      const again = this.store_make(root, cache);
      again.db_open("alpha");
      this.assertEqual(again.kv_list("alpha", ""), rows);
      this.assertEqual(again.kv_get("/alpha/a").data, bytes_text("one"));
      const name = digest_entry("value_over").sha256;
      this.assertEqual(again.kv_get("/alpha/big").data, name);
      this.assertEqual(
        cache.cache_read(name, 0, overflow_get() + 1),
        value_over(),
      );
      this.assertEqual(again.doc_get(ref), note);
      this.assertEqual(again.turn_list(scene), [
        { scene, n: 1, role: "user", content: hi },
      ]);
    }
  }

  // Snapshots with the cache files they name, and restores with or without.
  export class TestSnapshot extends StoreCase {
    // A restore brings back the rows of the snapshot and pushes nothing.
    test_snapshot_restore(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      store.sql_run("alpha", [
        { sql: "CREATE TABLE t (x TEXT)", params: [] },
        { sql: "INSERT INTO t VALUES (?)", params: [constants.text_wide] },
      ]);
      const snapshot = store.db_snapshot("alpha");
      this.assertEqual(
        snapshot.data.subarray(0, 16),
        bytes_join([bytes_text(constants.file_magic), new Uint8Array(1)]),
      );
      this.assertEqual(snapshot.files, []);
      const dump = content_dump(store, "alpha");
      store.kv_put("/alpha/a", bytes_text("two"));
      store.kv_put("/alpha/b", bytes_text("three"));
      store.sql_run("alpha", [{ sql: "DELETE FROM t", params: [] }]);
      this.pushes_taken(store);
      store.db_restore("alpha", snapshot.data, []);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("one"));
      this.raised_assert(gold_text("substrate_key_missing_b"), () =>
        store.kv_get("/alpha/b"),
      );
      this.assertEqual(content_dump(store, "alpha"), dump);
      this.assertEqual(this.pushes_of(store), []);
      const cache = cache_make();
      const second = this.store_make(this.root_make(), cache);
      const handle = sink_fill(cache, snapshot.data);
      second.db_restore("alpha", handle, []);
      this.raised_assert(unknown_text(handle), () =>
        cache.cache_read(handle, 0, 1),
      );
      this.assertEqual(content_dump(second, "alpha"), dump);
      this.assertEqual(this.pushes_of(second), []);
    }

    // A file without the substrate's tables throws and the old one stays.
    test_restore_foreign(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      const foreign = `${root}/foreign.sqlite`;
      this.raw_run(foreign, "c", [{ sql: "CREATE TABLE note (x TEXT)" }]);
      const data = this.raw_export(foreign);
      const files = this.files_under(root);
      this.raised_assert(gold_text("substrate_schema_partial_none"), () =>
        store.db_restore("alpha", data, []),
      );
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("one"));
      this.assertEqual(this.files_under(root), files);
    }

    // A restore file left by an earlier restore throws, and stays.
    test_restore_left(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      const data = store.db_snapshot("alpha").data;
      const left = `${root}/alpha.sqlite-restore`;
      this.raw_run(left, "c", [{ sql: "CREATE TABLE note (x TEXT)" }]);
      const text = gold_text("substrate_restore_left").replaceAll("{0}", left);
      this.raised_assert(text, () => store.db_restore("alpha", data, []));
      this.assertEqual(this.files_under(root), [
        "alpha.sqlite",
        "alpha.sqlite-restore",
      ]);
      this.assertEqual(store.db_list(), ["alpha"]);
    }

    // Two snapshots of one database taken apart hold their own bytes.
    test_snapshots_apart(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const first = store.db_snapshot("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      const second = store.db_snapshot("alpha");
      this.assertEqual([first.files, second.files], [[], []]);
      const same =
        first.data.length === second.data.length &&
        first.data.every((byte, index) => byte === second.data[index]);
      this.assertFalse(same);
    }

    // A cached value stays held through a snapshot and a restore of no file.
    test_value_held(): void {
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache);
      store.db_create("alpha");
      store.kv_put("/alpha/big", value_over());
      const snapshot = store.db_snapshot("alpha");
      const name = digest_entry("value_over").sha256;
      this.assertEqual(snapshot.files, [name]);
      store.db_restore("alpha", snapshot.data, []);
      const size = overflow_get() + 1;
      this.assertEqual(store.kv_get("/alpha/big"), {
        data: name,
        size,
        sha256: name,
      });
      this.assertEqual(cache.cache_read(name, 0, size), value_over());
    }

    // A restore given one of two cache files reads all but the lost value.
    test_restore_files_lost(): void {
      const source_cache = cache_make();
      const source = this.store_make(this.root_make(), source_cache);
      source.db_create("alpha");
      const big: [string, string][] = [
        ["/alpha/one", "value_over"],
        ["/alpha/two", "value_other"],
      ];
      for (const [ref, entry] of big) {
        source.kv_put(ref, digest_entry(entry).data);
      }
      source.kv_put("/alpha/small", bytes_text("small"));
      const image = source.db_snapshot("alpha");
      const names = big.map(([, entry]) => digest_entry(entry).sha256);
      this.assertEqual(image.files, [...names].sort());
      const size = overflow_get() + 1;
      const [first, second] = image.files;
      const kept = source_cache.cache_read(first, 0, size);
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache);
      store.db_restore("alpha", image.data, [kept]);
      // The refs of the value whose file came and of the one whose did not.
      const kept_ref = big[names.indexOf(first)][0];
      const lost_ref = big[names.indexOf(second)][0];
      this.assertEqual(store.kv_get(kept_ref).data, first);
      this.assertEqual(cache.cache_read(first, 0, size), kept);
      this.assertEqual(store.kv_get("/alpha/small").data, bytes_text("small"));
      this.raised_assert(lost_text(lost_ref, second), () =>
        store.kv_get(lost_ref),
      );
      this.assertEqual(
        store.kv_list("alpha", ""),
        source.kv_list("alpha", ""),
      );
      this.assertEqual(store.kv_list("alpha", "").length, 3);
      store.kv_put(lost_ref, bytes_text("again"));
      this.assertEqual(store.kv_get(lost_ref).data, bytes_text("again"));
      this.assertEqual(store.kv_check("alpha"), 0);
    }

    // A restore takes the database and a file as handles of its own cache.
    test_restore_handle(): void {
      const source_cache = cache_make();
      const source = this.store_make(this.root_make(), source_cache);
      source.db_create("alpha");
      source.kv_put("/alpha/big", value_over());
      const image = source.db_snapshot("alpha");
      const name = digest_entry("value_over").sha256;
      const size = overflow_get() + 1;
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache);
      const data = sink_fill(cache, image.data);
      const file = sink_fill(cache, source_cache.cache_read(name, 0, size));
      store.db_restore("alpha", data, [file]);
      this.assertEqual(store.kv_get("/alpha/big").data, name);
      this.assertEqual(cache.cache_read(name, 0, size), value_over());
      for (const handle of [data, file]) {
        this.raised_assert(unknown_text(handle), () =>
          cache.cache_read(handle, 0, 1),
        );
      }
      store.db_restore("alpha", image.data, [name]);
      this.assertEqual(cache.cache_read(name, 0, size), value_over());
      const absent = digest_entry("absent").sha256;
      this.raised_assert(unknown_text(absent), () =>
        store.db_restore("alpha", image.data, [absent]),
      );
    }

    // A snapshot names only the cache files its store holds, throwing none.
    test_snapshot_missing_file(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make());
      store.db_create("alpha");
      store.kv_put("/alpha/one", value_over());
      store.kv_put("/alpha/two", value_other());
      store.db_close("alpha");
      const name = digest_entry("value_over").sha256;
      const slots = [
        slot_stored(name, value_over()),
        ...slots_make(slot_count() - 1),
      ];
      const second = this.store_make(root, new substrate.CacheFiles(slots));
      second.db_open("alpha");
      this.assertEqual(second.db_snapshot("alpha").files, [name]);
    }
  }

  // The push of each committed operation: its line, its owner, its timing.
  export class TestPush extends StoreCase {
    // A create and a drop each push the database's name at once.
    test_databases_pushed(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.assertEqual(this.pushes_taken(store), [
        push_gold("push_db_create"),
      ]);
      store.db_drop("alpha");
      this.assertEqual(this.pushes_taken(store), [push_gold("push_db_drop")]);
    }

    // A value in its row goes as a copy of its bytes, a delete by its ref.
    test_values_pushed(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.pushes_taken(store);
      const value = bytes_text("one");
      store.kv_put("/alpha/a", value);
      const pushed = this.pushes_taken(store);
      this.assertEqual(pushed, [push_bytes("push_kv_put_a", value)]);
      this.assertFalse((pushed[0][0][1] as lines.BlobHeader).d === value);
      store.kv_put("/alpha/a", bytes_text("one"));
      store.kv_delete("/alpha/absent");
      store.sql_run("alpha", [{ sql: "SELECT 1", params: [] }]);
      this.assertEqual(this.pushes_of(store), []);
      store.kv_delete("/alpha/a");
      this.assertEqual(this.pushes_taken(store), [
        push_gold("push_kv_delete_a"),
      ]);
    }

    // A value over `overflow_bytes` goes as its file's bytes, never a handle.
    test_files_pushed(): void {
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache);
      store.db_create("alpha");
      this.pushes_taken(store);
      store.kv_put("/alpha/big", value_over());
      const other = value_other();
      store.kv_put("/alpha/streamed", sink_fill(cache, other));
      const pushed = this.pushes_taken(store);
      this.assertEqual(pushed, [
        push_bytes("push_kv_put_big", value_over()),
        push_bytes("push_kv_put_streamed", other),
      ]);
      for (const [line] of pushed) {
        const blob = line[1] as lines.BlobHeader;
        this.assertTrue(blob.d instanceof Uint8Array, "bytes were expected");
      }
    }

    // Documents, turns and statements that change something push payloads.
    test_writes_pushed(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.pushes_taken(store);
      const body = { 0: { t: "note" } };
      store.doc_put("alpha", "note", body);
      const scene = "/alpha/scene/1";
      const user = message_said("user", "hi");
      store.turn_append(scene, "user", user);
      const created: lines.SqlStatement[] = [
        { sql: "CREATE TABLE t (x TEXT)", params: [] },
      ];
      const inserted: lines.SqlStatement[] = [
        { sql: "INSERT INTO t VALUES (?)", params: ["a"] },
      ];
      store.sql_run("alpha", created);
      store.sql_run("alpha", inserted);
      store.sql_run("alpha", [{ sql: "SELECT x FROM t", params: [] }]);
      store.sql_run("alpha", [
        { sql: "UPDATE t SET x = ? WHERE x = ?", params: ["b", "absent"] },
      ]);
      const pushed = this.pushes_taken(store);
      this.assertEqual(pushed, [
        push_gold("push_doc_put"),
        push_gold("push_turn_append_hi"),
        push_gold("push_sql_run_create"),
        push_gold("push_sql_run_insert"),
      ]);
      this.assertFalse(pushed[2][0].statements === created);
    }

    // The pushes of one transaction follow its commit, in order, or none.
    test_transaction_pushed(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.pushes_taken(store);
      const value = bytes_text("1");
      store.transaction_run(() => {
        store.kv_put("/alpha/a", value);
        store.kv_delete("/alpha/a");
        this.assertEqual(this.pushes_of(store), []);
      });
      this.assertEqual(this.pushes_taken(store), [
        push_bytes("push_kv_put_a", value),
        push_gold("push_kv_delete_a"),
      ]);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/b", bytes_text("2"));
          throw new Error("rolled back");
        }),
      );
      this.assertEqual(this.pushes_of(store), []);
    }

    // A `user` turn at the threshold compacts first and pushes only itself.
    test_threshold_pushed(): void {
      const store = this.store_make(
        this.root_make(),
        cache_make(),
        this.pool_get(),
        constants.compact_small,
      );
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      for (const text of ["1", "2", "3"]) {
        store.turn_append(scene, "assistant", message_said("assistant", text));
      }
      this.pushes_taken(store);
      const user = message_said("user", "4");
      this.assertEqual(store.turn_append(scene, "user", user), { n: 2 });
      this.assertEqual(this.pushes_taken(store), [
        push_gold("push_turn_append_four"),
      ]);
      const summary = gold_text("substrate_turns_compacted_three");
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: message_said("system", summary),
        },
        { scene, n: 2, role: "user", content: user },
      ]);
    }
  }

  // A put stopped between its cache file and its row, as a kill stops it.
  export class TestCrash extends StoreCase {
    // The stopped put leaves a file and no row, and `kv_check` removes it.
    test_kill_between(): void {
      const root = this.root_make();
      const slots = slots_make(slot_count());
      // The stop that stands for the kill: it throws where the rung kills.
      const kill_stop = (): never => {
        throw new Error(constants.kill_message);
      };
      const pool = kill_pool(this.pool_get(), kill_stop);
      const cache = new substrate.CacheFiles(slots);
      const paused = this.store_make(root, cache, pool);
      this.raised_assert(constants.kill_message, () => kill_put(paused));
      paused.db_close(constants.kill_db);
      const name = digest_entry("value_over").sha256;
      const after = new substrate.CacheFiles(slots);
      this.assertEqual(
        after.cache_read(name, 0, 8),
        value_over().subarray(0, 8),
      );
      const checked = this.store_make(root, after);
      this.assertEqual(kill_check(checked), { rows: 0, removed: 1 });
      this.raised_assert(unknown_text(name), () =>
        after.cache_read(name, 0, 1),
      );
      this.assertEqual(checked.kv_check(constants.kill_db), 0);
    }
  }

  // The handlers of the UI thread's requests and of the server's pushes.
  export class TestHandlers extends StoreCase {
    // Every type is registered at version 0.
    test_types_registered(): void {
      const table = this.handlers_get(this.store_fresh());
      this.assertEqual([...table.keys()].sort(), [
        "db.create",
        "db.drop",
        "db.file",
        "db.restore",
        "doc.head",
        "doc.put",
        "kv.delete",
        "kv.get",
        "kv.list",
        "kv.put",
        "sql.run",
        "turn.append",
      ]);
    }

    // `kv.put` and `kv.get` answer with the known digest and the bytes.
    test_values_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("metaverse");
      const { data: world, sha256 } = digest_entry("castle_world");
      const put = this.answer_get(
        table,
        line_blob("request_kv_put_world", world.slice()),
      );
      this.assertEqual(
        line_text(put),
        gold_text("reply_kv_put").replaceAll("{0}", sha256),
      );
      const got = this.answer_get(table, gold_line("request_kv_get_world"));
      this.assertEqual(
        line_text(got),
        gold_text("reply_kv_get").replaceAll("{0}", sha256),
      );
      this.assertEqual((got[1] as lines.BlobHeader).d, world);
      this.answer_get(table, line_blob("request_kv_put_big", value_over()));
      const big = this.answer_get(table, gold_line("request_kv_get_big"));
      this.assertEqual((big[1] as lines.BlobHeader).d, value_over());
    }

    // `sql.run`, `kv.list` and `kv.delete` answer their results.
    test_rows_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("castle");
      const ran = this.answer_get(table, gold_line("request_sql_run"));
      this.assertEqual(line_text(ran), gold_text("reply_sql_run"));
      const { data: world, sha256 } = digest_entry("castle_world");
      store.kv_put("/castle/world", world);
      const listed = this.answer_get(table, gold_line("request_kv_list"));
      this.assertEqual(
        line_text(listed),
        gold_text("reply_kv_list").replaceAll("{0}", sha256),
      );
      const deleted = this.answer_get(table, gold_line("request_kv_delete"));
      this.assertEqual(line_text(deleted), gold_text("reply_kv_delete"));
    }

    // Documents and turns answer with their refs and numbers.
    test_documents_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("castle_gatehouse");
      store.db_create("metaverse");
      const put = this.answer_get(table, gold_line("request_doc_put"));
      this.assertEqual(line_text(put), gold_text("reply_doc_put"));
      const head = this.answer_get(table, gold_line("request_doc_head"));
      this.assertEqual(line_text(head), gold_text("reply_doc_head"));
      const appended = this.answer_get(
        table,
        gold_line("request_turn_append"),
      );
      this.assertEqual(line_text(appended), gold_text("reply_turn_append"));
    }

    // Databases are created and dropped by their lines.
    test_databases_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      const created = this.answer_get(table, gold_line("request_db_create"));
      this.assertEqual(line_text(created), gold_text("reply_db_create"));
      this.assertEqual(store.db_list(), ["alpha"]);
      const dropped = this.answer_get(table, gold_line("request_db_drop"));
      this.assertEqual(line_text(dropped), gold_text("reply_db_drop"));
      this.assertEqual(store.db_list(), []);
    }

    // A restore waits for its `db.file` lines, or runs at once with none.
    test_restore_answered(): void {
      const source_cache = cache_make();
      const source = this.store_make(this.root_make(), source_cache);
      source.db_create("alpha");
      source.db_create("beta");
      source.kv_put("/alpha/one", value_over());
      source.kv_put("/alpha/two", value_other());
      source.kv_put("/beta/small", bytes_text("small"));
      const alpha = source.db_snapshot("alpha");
      const beta = source.db_snapshot("beta");
      const size = overflow_get() + 1;
      const files = alpha.files.map((name) =>
        source_cache.cache_read(name, 0, size),
      );
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache);
      const table = this.handlers_get(store);
      this.push_give(table, line_blob("restore_alpha", alpha.data));
      this.push_give(table, line_blob("file_alpha", files[0]));
      this.assertEqual(store.db_list(), []);
      this.push_give(table, line_blob("file_alpha", files[1]));
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(
        store.kv_list("alpha", ""),
        source.kv_list("alpha", ""),
      );
      for (const [index, name] of alpha.files.entries()) {
        this.assertEqual(cache.cache_read(name, 0, size), files[index]);
      }
      this.push_give(table, line_blob("restore_beta_none", beta.data));
      this.assertEqual(store.db_list(), ["alpha", "beta"]);
      this.assertEqual(store.kv_get("/beta/small").data, bytes_text("small"));
      this.assertEqual(this.pushes_of(store), []);
    }

    // A restore while one waits, or a file no restore waits for, throws.
    test_restore_refused(): void {
      const source = this.store_fresh();
      source.db_create("alpha");
      const data = source.db_snapshot("alpha").data;
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      const file = value_over();
      this.raised_assert(gold_text("substrate_file_unexpected_alpha"), () =>
        this.push_give(table, line_blob("file_alpha", file)),
      );
      this.push_give(table, line_blob("restore_alpha", data));
      const again = line_blob("restore_beta_one", data);
      this.raised_assert(gold_text("substrate_restore_pending"), () =>
        this.push_give(table, again),
      );
      this.raised_assert(gold_text("substrate_file_unexpected_beta"), () =>
        this.push_give(table, line_blob("file_beta", file)),
      );
      this.assertEqual(store.db_list(), []);
    }

    // The handlers a store registers, by type, each checked at version 0.
    handlers_get(store: substrate.Store): Map<string, dispatch.Handler> {
      const table = new Map<string, dispatch.Handler>();
      store.handlers_register((type, version, fn) => {
        this.assertEqual(version, 0, type);
        table.set(type, fn);
      });
      return table;
    }

    // The reply line the handler of a request's type, its short `t`, returns.
    answer_get(
      table: Map<string, dispatch.Handler>,
      request: lines.Line,
    ): lines.Line {
      const fn = table.get(request[0].t) as dispatch.Handler;
      return fn(request) as lines.Line;
    }

    // Gives a push to the handler of its type, which must return nothing.
    push_give(table: Map<string, dispatch.Handler>, push: lines.Line): void {
      const fn = table.get(push[0].t) as dispatch.Handler;
      this.assertEqual(fn(push), undefined);
    }
  }

  // The shape of the module object and its classes.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(substrate));
      this.assertEqual(Object.keys(substrate).sort(), [
        "CacheFiles",
        "Store",
        "doc_decode",
        "doc_encode",
        "ref_split",
      ]);
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.Store.prototype).sort(),
        [
          "constructor",
          "db_close",
          "db_create",
          "db_drop",
          "db_list",
          "db_open",
          "db_restore",
          "db_snapshot",
          "doc_get",
          "doc_head",
          "doc_put",
          "handlers_register",
          "kv_check",
          "kv_delete",
          "kv_get",
          "kv_list",
          "kv_put",
          "sink",
          "sql_run",
          "transaction_run",
          "turn_append",
          "turn_compact",
          "turn_list",
        ],
      );
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.CacheFiles.prototype).sort(),
        [
          "cache_read",
          "constructor",
          "sink_append",
          "sink_close",
          "sink_open",
          "slot_add",
          "slots_free",
        ],
      );
    }
  }
}
Object.freeze(test_substrate);
