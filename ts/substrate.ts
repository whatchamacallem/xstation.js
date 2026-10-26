// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The browser's store, the single door to SQLite in the AI worker: one
// sqlite3.wasm connection for each database file of the OPFS pool under a
// root, the substrate's tables in each, values with overflow to a cache of
// OPFS files held open for synchronous access, documents, turns that compact
// themselves for this side alone when a `user` turn finds `compact_turns` of
// them, SQL, and whole databases as a file and the cache files its rows name.
// Each committed modifying operation goes to the server as one push line of
// its type, given to the thread's queue, which nothing waits for, numbers or
// checks: the sync is lossy. A row whose cache file this side lacks stays,
// and only a read of its value fails. A statement a schema trigger stops
// throws the string whose name the trigger raises. The handlers answer the
// UI thread's requests and take the server's restores. It is given an
// initialized module, an installed pool and open cache files, and waits on
// nothing.
namespace substrate {
  // The schema, names, patterns and sizes the store uses.
  const constants = Object.freeze({
    // The substrate's tables, one statement each, as the server makes them.
    schema_statements: Object.freeze<readonly string[]>([
      "CREATE TABLE _meta (\n    name  TEXT PRIMARY KEY,\n" +
        "    value TEXT NOT NULL\n) WITHOUT ROWID, STRICT",
      "CREATE TABLE _kv (\n    key    TEXT    PRIMARY KEY,\n" +
        "    size   INTEGER NOT NULL,\n    sha256 BLOB    NOT NULL,\n" +
        "    data   BLOB\n) WITHOUT ROWID, STRICT",
      "CREATE TABLE _head (\n    id      TEXT    PRIMARY KEY,\n" +
        "    version INTEGER NOT NULL\n) WITHOUT ROWID, STRICT",
      "CREATE TABLE _turn (\n    scene   TEXT    NOT NULL,\n" +
        "    n       INTEGER NOT NULL,\n    role    TEXT    NOT NULL,\n" +
        "    content TEXT    NOT NULL CHECK (json_valid(content)),\n" +
        "    PRIMARY KEY (scene, n)\n) WITHOUT ROWID, STRICT",
    ]),
    // The first row of `_meta`: the schema version bound.
    meta_insert: "INSERT INTO _meta (name, value) VALUES ('schema', ?)",
    // The names of the substrate's tables, in order.
    schema_tables: Object.freeze<readonly string[]>([
      "_head",
      "_kv",
      "_meta",
      "_turn",
    ]),
    // The version of the substrate's tables, the `schema` row of `_meta`.
    schema_version: "1",
    // The extension of a database file under the root.
    db_extension: ".sqlite",
    // The suffix of the file a restore checks before it replaces a database.
    restore_suffix: "-restore",
    // The flags that open an existing database to read and write.
    open_write: "w",
    // The flags that create a database file and open it.
    open_create: "c",
    // The flags that open a database only to read it.
    open_read: "r",
    // The role of the summary turn that compaction writes.
    summary_role: "system",
    // The role of the turn that compacts a scene at the threshold first.
    compact_role: "user",
    // The names of the strings the schema's triggers raise.
    trigger_names: Object.freeze<readonly string[]>([
      "agent.content_ambiguous",
    ]),
    // The smallest magnitude Python's `repr` writes in fixed notation.
    fixed_min: 1e-4,
    // A database name, a C identifier.
    c_identifier: /^[A-Za-z_][A-Za-z0-9_]*$/,
    // An external ref: a slash, a database name, a slash and a key.
    external_ref: /^\/([A-Za-z_][A-Za-z0-9_]*)\/(.+)$/su,
    // A reference string: an external ref, no Python `str.isspace` in its key.
    reference_string: new RegExp(
      "^/[A-Za-z_][A-Za-z0-9_]*/[^\\u{9}-\\u{d}\\u{1c}-\\u{20}\\u{85}" +
        "\\u{a0}\\u{1680}\\u{2000}-\\u{200a}\\u{2028}\\u{2029}\\u{202f}" +
        "\\u{205f}\\u{3000}]+$",
      "u",
    ),
    // A surrogate standing alone, which `UTF-8` cannot encode.
    lone_surrogate: /[\u{d800}-\u{dfff}]/u,
    // An integer literal: decimal digits with no sign and no leading zero.
    integer_literal: /^(?:0|[1-9][0-9]*)$/,
    // Decimal digits, which no payload key of a document may be.
    digit_key: /^[0-9]+$/,
    // The name of a stored cache file, its `SHA-256` in lowercase hex.
    stored_name: /^[0-9a-f]{64}$/,
    // The bytes at the start of a cache file that hold its stored name.
    name_bytes: 64,
    // The bytes read at once when a cache file is hashed.
    read_bytes: 1048576,
    // The start of the handle of a blob the sink writes.
    sink_prefix: "sink/",
    // The owner the push of each committed operation goes to.
    push_owner: "server" as const,
  });

  // A file of the cache held open for synchronous access, as OPFS gives it.
  export interface SlotHandle {
    // Reads into the buffer from the offset and returns the bytes read.
    read(buffer: Uint8Array, options: { at: number }): number;
    // Writes the buffer at the offset and returns the bytes written.
    write(buffer: Uint8Array, options: { at: number }): number;
    // Sets the size of the file.
    truncate(size: number): void;
    // The size of the file.
    getSize(): number;
  }

  // What `exec` of a database takes: the SQL, its parameters, what to keep.
  export interface ExecOptions {
    // The SQL text.
    sql: string;
    // The parameters of its first statement that has any.
    bind?: unknown[];
    // Rows as arrays.
    rowMode?: "array";
    // Where the rows go.
    resultRows?: unknown[][];
    // Where the column names go.
    columnNames?: string[];
    // Where the text of each statement run goes.
    saveSql?: string[];
  }

  // A prepared statement of the pool's database class.
  export interface SqliteStatement {
    // The number of parameters the statement takes.
    readonly parameterCount: number;
    // Frees the statement.
    finalize(): unknown;
  }

  // A database of the pool's class `OpfsSAHPoolDb`, the parts used here.
  export interface SqliteDatabase {
    // The `sqlite3` pointer of the connection.
    readonly pointer: number;
    // Runs SQL, keeping rows, column names and statements as asked.
    exec(options: ExecOptions): unknown;
    // The first column of the first row the SQL returns.
    selectValue(sql: string, bind?: unknown[]): unknown;
    // Prepares the first statement of the SQL.
    prepare(sql: string): SqliteStatement;
    // The rows the last statement changed, or all since opening when total.
    changes(total: boolean): number;
    // Closes the connection.
    close(): void;
  }

  // The sqlite3.wasm module `sqlite3InitModule` resolves to, parts used.
  export interface SqliteModule {
    // The C functions used here.
    capi: {
      sqlite3_js_db_export(pointer: number): Uint8Array;
      sqlite3_get_autocommit(pointer: number): number;
    };
  }

  // The OPFS SAH pool `installOpfsSAHPoolVfs` resolves to, parts used.
  export interface SqlitePool {
    // The database class whose files are in the pool.
    OpfsSAHPoolDb: new (options: {
      filename: string;
      flags: string;
    }) => SqliteDatabase;
    // The names of the files in the pool.
    getFileNames(): string[];
    // Writes database bytes as the named file, replacing any.
    importDb(name: string, bytes: Uint8Array): unknown;
    // Removes the named file and says whether it was there.
    unlink(name: string): boolean;
  }

  // The bytes of a value, or the cache handle when over `overflow_bytes`.
  export interface KvValue {
    data: Uint8Array | string;
    size: number;
    sha256: lines.Sha256;
  }

  // A turn of a scene: its number in the scene, its role and its message.
  export interface TurnRow {
    scene: lines.DocRef;
    n: number;
    role: provider.Role;
    content: provider.ChatMessage;
  }

  // A ref split: the database when external, the key, the version if any.
  export interface RefParts {
    db?: string;
    key: string;
    version?: number;
  }

  // A database as one blob: its file and the cache files its rows name.
  export interface DbImage {
    data: Uint8Array;
    files: string[];
  }

  // What the store gives each committed operation to: the thread's queue.
  export interface Notifier {
    line_notify(line: lines.Line, owner?: queue.ThreadName): void;
  }

  // Registers the handler of one line type and version.
  export type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // A blob the sink is writing: its slot, size, bytes so far and hash.
  interface SinkOpen {
    slot: number;
    size: number;
    written: number;
    hash: utility.HashStream;
  }

  // A cache file found by handle: its slot and the size of its value.
  interface FileSpan {
    slot: number;
    size: number;
  }

  // A row written: its fields, whether it changed, whether it is cached.
  interface RowWritten {
    row: lines.KvRow;
    changed: boolean;
    cached: boolean;
  }

  // A `db.restore` waiting for its `db.file` lines: the file, those in, left.
  interface RestoreWait {
    db: string;
    data: Uint8Array | string;
    files: (Uint8Array | string)[];
    left: number;
  }

  // Throws unless the name is a C identifier, as a database name must be.
  function name_check(name: string): void {
    if (!constants.c_identifier.test(name)) {
      throw new Error(i18n("substrate.name_bad", name));
    }
  }

  // The version a key ends in, when its last segment is an integer literal.
  function version_find(key: string): number | undefined {
    const index = key.lastIndexOf("/");
    const tail = key.slice(index + 1);
    return index > 0 && constants.integer_literal.test(tail)
      ? Number(tail)
      : undefined;
  }

  // The parts of a ref: its database when external, its key and version.
  function parts_make(db: string | undefined, key: string): RefParts {
    const version = version_find(key);
    return {
      ...(db === undefined ? {} : { db }),
      key,
      ...(version === undefined ? {} : { version }),
    };
  }

  // Splits a `Key-Value-Ref` or `Document-Ref`. A bad ref throws.
  export function ref_split(ref: string): RefParts {
    if (!ref.startsWith("/")) {
      if (ref === "") {
        throw new Error(i18n("substrate.ref_bad", ref));
      }
      return parts_make(undefined, ref);
    }
    const match = constants.external_ref.exec(ref);
    if (match === null) {
      throw new Error(i18n("substrate.ref_bad", ref));
    }
    return parts_make(match[1], match[2]);
  }

  // The database and key of a ref, `db` naming an internal ref's database.
  function ref_resolve(ref: string, db: string | undefined): [string, string] {
    const parts = ref_split(ref);
    if (parts.db === undefined) {
      if (db === undefined) {
        throw new Error(i18n("substrate.ref_internal", ref));
      }
      return [db, parts.key];
    }
    if (db !== undefined) {
      throw new Error(i18n("substrate.ref_both", ref, db));
    }
    return [parts.db, parts.key];
  }

  // The database of a scene, whose ref must be an external `Document-Ref`.
  function scene_database(scene: string): string {
    const parts = ref_split(scene);
    if (parts.db === undefined || parts.version === undefined) {
      throw new Error(i18n("substrate.scene_bad", scene));
    }
    return parts.db;
  }

  // Whether the value is a plain object, from a literal or `JSON.parse`.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // Whether an object has the shape of a header reference, `$ref` alone.
  function ref_shaped(value: { [key: string]: unknown }): boolean {
    const keys = Object.keys(value);
    return keys.length === 1 && keys[0] === "$ref";
  }

  // A value as message text: objects and arrays as JSON, the rest as text.
  function value_show(value: unknown): string {
    return object_plain(value) || Array.isArray(value)
      ? JSON.stringify(value)
      : String(value);
  }

  // A copy of header 0: the type `t` and, when not 0, the version `v`.
  function header_copy(document: { [key: string]: unknown }): {
    t: string;
    v?: number;
  } {
    if (!Object.hasOwn(document, "0")) {
      throw new Error(i18n("substrate.header_missing"));
    }
    const header = document["0"];
    if (!object_plain(header)) {
      throw new Error(i18n("substrate.header_bad", value_show(header)));
    }
    const typed = typeof header.t === "string";
    const versioned =
      !Object.hasOwn(header, "v") ||
      (Number.isInteger(header.v) && header.v !== 0);
    const known = Object.keys(header).every(
      (name) => name === "t" || name === "v",
    );
    if (!(typed && versioned && known)) {
      throw new Error(i18n("substrate.header_bad", value_show(header)));
    }
    return { ...header } as { t: string; v?: number };
  }

  // Throws on a payload key of decimal digits, which would read as a header.
  function key_check(key: string): void {
    if (constants.digit_key.test(key)) {
      throw new Error(i18n("substrate.key_digits", key));
    }
  }

  // Replaces each reference string in a body value by `{"$ref": n}`.
  function refs_take(value: unknown, refs: Map<string, number>): unknown {
    if (typeof value === "string") {
      if (!constants.reference_string.test(value)) {
        return value;
      }
      if (!refs.has(value)) {
        refs.set(value, refs.size + 1);
      }
      return { $ref: refs.get(value) };
    }
    if (Array.isArray(value)) {
      return value.map((item: unknown) => refs_take(item, refs));
    }
    if (object_plain(value)) {
      if (ref_shaped(value)) {
        throw new Error(i18n("substrate.ref_shape", value_show(value)));
      }
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [
          key,
          refs_take(item, refs),
        ]),
      );
    }
    return value;
  }

  // Replaces each `{"$ref": n}` in a body value by the string of header n.
  function refs_restore(value: unknown, refs: string[]): unknown {
    if (Array.isArray(value)) {
      return value.map((item: unknown) => refs_restore(item, refs));
    }
    if (object_plain(value)) {
      if (ref_shaped(value)) {
        const index = value.$ref as number;
        if (!Number.isInteger(index) || index < 1 || index > refs.length) {
          throw new Error(i18n("substrate.ref_index", value_show(index)));
        }
        return refs[index - 1];
      }
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [
          key,
          refs_restore(item, refs),
        ]),
      );
    }
    return value;
  }

  // Moves a document's reference strings into its headers 1 on.
  export function doc_encode(normal: {
    [key: string]: unknown;
  }): lines.Document {
    const header = header_copy(normal);
    const refs = new Map<string, number>();
    const body: [string, unknown][] = [];
    for (const [key, value] of Object.entries(normal)) {
      if (constants.integer_literal.test(key)) {
        if (key !== "0") {
          throw new Error(i18n("substrate.header_normal", key));
        }
      } else {
        key_check(key);
        body.push([key, refs_take(value, refs)]);
      }
    }
    const headers: [string, unknown][] = [["0", header]];
    for (const [text, index] of refs) {
      headers.push([String(index), text]);
    }
    return Object.fromEntries([...headers, ...body]) as lines.Document;
  }

  // Puts the headers' reference strings back where `{"$ref": n}` names them.
  export function doc_decode(encoded: lines.Document): {
    [key: string]: unknown;
  } {
    const fields: { [key: string]: unknown } = encoded;
    const header = header_copy(fields);
    const refs: string[] = [];
    while (Object.hasOwn(fields, String(refs.length + 1))) {
      const text = fields[String(refs.length + 1)];
      if (typeof text !== "string" || !constants.reference_string.test(text)) {
        throw new Error(i18n("substrate.header_ref", refs.length + 1));
      }
      refs.push(text);
    }
    const normal: [string, unknown][] = [["0", header]];
    for (const [key, value] of Object.entries(fields)) {
      if (constants.integer_literal.test(key)) {
        if (Number(key) > refs.length) {
          throw new Error(i18n("substrate.header_gap", key));
        }
      } else {
        key_check(key);
        normal.push([key, refs_restore(value, refs)]);
      }
    }
    return Object.fromEntries(normal);
  }

  // Orders two distinct integer keys by their value, however many digits.
  function key_compare(first: string, second: string): number {
    if (first.length !== second.length) {
      return first.length - second.length;
    }
    return first < second ? -1 : 1;
  }

  // The JSON text of a string, which must be valid Unicode.
  function text_canonical(text: string): string {
    if (constants.lone_surrogate.test(text)) {
      throw new Error(i18n("substrate.text_refused"));
    }
    return utility.json_text(text);
  }

  // A number as Python's `repr` writes it, which differs below `1e-4` only.
  function number_canonical(value: number): string {
    const magnitude = Math.abs(value);
    if (magnitude === 0 || magnitude >= constants.fixed_min) {
      return utility.json_text(value);
    }
    const [digits, exponent] = value.toExponential().split("e");
    return `${digits}e${exponent[0]}${exponent.slice(1).padStart(2, "0")}`;
  }

  // The canonical JSON text of a value: at every level integer keys first.
  function json_canonical(value: unknown): string {
    if (value === null || typeof value === "boolean") {
      return String(value);
    }
    if (typeof value === "number") {
      return number_canonical(value);
    }
    if (typeof value === "string") {
      return text_canonical(value);
    }
    if (Array.isArray(value)) {
      const items: readonly unknown[] = value;
      const texts = Array.from(items, (item) => json_canonical(item));
      return `[${texts.join(",")}]`;
    }
    if (object_plain(value)) {
      const object: { [key: string]: unknown } = value;
      const keys = Object.keys(object);
      const literal = constants.integer_literal;
      const numbers = keys.filter((key) => literal.test(key));
      const names = keys.filter((key) => !literal.test(key));
      const members = [...numbers.sort(key_compare), ...names].map(
        (key) => `${text_canonical(key)}:${json_canonical(object[key])}`,
      );
      return `{${members.join(",")}}`;
    }
    throw new Error(
      i18n("substrate.value_refused", Object.prototype.toString.call(value)),
    );
  }

  // The bytes as lowercase hex, two characters each.
  function hex_of(data: Uint8Array): string {
    let hex = "";
    for (const byte of data) {
      hex += byte.toString(16).padStart(2, "0");
    }
    return hex;
  }

  // The bytes lowercase hex text spells, two characters each.
  function bytes_of(hex: string): Uint8Array {
    const data = new Uint8Array(hex.length / 2);
    for (let index = 0; index < data.length; index += 1) {
      data[index] = Number.parseInt(hex.slice(2 * index, 2 * index + 2), 16);
    }
    return data;
  }

  // The rows one statement returns, each an array.
  function rows_select(
    database: SqliteDatabase,
    sql: string,
    bind: unknown[],
  ): unknown[][] {
    const rows: unknown[][] = [];
    const options: ExecOptions = { sql, rowMode: "array", resultRows: rows };
    if (bind.length > 0) {
      options.bind = bind;
    }
    database.exec(options);
    return rows;
  }

  // The number the first column of the first row of the SQL holds.
  function select_number(database: SqliteDatabase, sql: string): number {
    return database.selectValue(sql) as number;
  }

  // The `schema_version` pragma, which every change of the schema moves.
  function schema_read(database: SqliteDatabase): number {
    return select_number(database, "PRAGMA schema_version");
  }

  // The substrate's tables that a database holds, in order.
  function tables_found(database: SqliteDatabase): string[] {
    const rows = rows_select(
      database,
      "SELECT name FROM sqlite_schema WHERE type = 'table'",
      [],
    );
    return rows
      .map((row) => row[0] as string)
      .filter((name) => constants.schema_tables.includes(name))
      .sort();
  }

  // Throws unless the tables found are all of the substrate's, its version.
  function schema_check(database: SqliteDatabase, found: string[]): void {
    if (found.join() !== constants.schema_tables.join()) {
      throw new Error(i18n("substrate.schema_partial", JSON.stringify(found)));
    }
    const row = database.selectValue(
      "SELECT value FROM _meta WHERE name = 'schema'",
    );
    const version = constants.schema_version;
    if (row !== version) {
      throw new Error(i18n("substrate.schema_version", String(row), version));
    }
  }

  // The names of the cache files the rows of a database hold.
  function hashes_read(database: SqliteDatabase): Set<string> {
    const rows = rows_select(
      database,
      "SELECT sha256 FROM _kv WHERE data IS NULL",
      [],
    );
    return new Set(rows.map((row) => hex_of(row[0] as Uint8Array)));
  }

  // The string a trigger's failure names as its message's end, else the error.
  function trigger_error(error: unknown): unknown {
    if (!(error instanceof Error)) {
      return error;
    }
    const message = error.message;
    const name = constants.trigger_names.find((candidate) =>
      message.endsWith(candidate),
    );
    if (name === undefined) {
      return error;
    }
    return new Error(i18n(name), { cause: error });
  }

  // Runs one statement with its parameters and counts the rows it changed.
  function statement_run(
    database: SqliteDatabase,
    statement: lines.SqlStatement,
  ): lines.SqlResult {
    const { sql, params } = statement;
    const prepared = database.prepare(sql);
    const count = prepared.parameterCount;
    prepared.finalize();
    if (count !== params.length) {
      throw new Error(
        i18n("substrate.params_count", count, params.length, sql),
      );
    }
    const before = database.changes(true);
    const rows: unknown[][] = [];
    const columns: string[] = [];
    const saved: string[] = [];
    const options: ExecOptions = {
      sql,
      rowMode: "array",
      resultRows: rows,
      columnNames: columns,
      saveSql: saved,
    };
    if (params.length > 0) {
      options.bind = params;
    }
    try {
      database.exec(options);
    } catch (error) {
      throw trigger_error(error);
    }
    if (saved.length > 1) {
      throw new Error(i18n("substrate.statement_many", saved.length, sql));
    }
    return { columns, rows, changes: database.changes(true) - before };
  }

  // The payload of a line read as the shape its type gives it.
  function payload_read<T>(line: lines.Line): T {
    return jslb.payload_of(line) as unknown as T;
  }

  // The ref of a `kv.*` line, the header's key.
  function ref_of(line: lines.Line): string {
    return jslb.field_get(line[0], "key") as string;
  }

  // The data of blob 1 of a line: its bytes, or a handle of the cache.
  function blob_data(line: lines.Line): Uint8Array | string {
    const blob = line[1] as lines.BlobHeader;
    return jslb.field_get(blob, "data") as Uint8Array | string;
  }

  // The push line of an operation, in the name form this thread picks.
  function push_make(
    type: string,
    payload: { [key: string]: unknown },
    key?: string,
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const full = settings.names_full();
    const header = jslb.header_make(type, { key, full });
    return jslb.line_make(header, blobs, payload);
  }

  // The files of the cache: slots of OPFS files, free or holding a value.
  class SlotPool {
    // The open files, by slot number.
    readonly #slots: SlotHandle[] = [];
    // The slots that hold nothing, the last freed taken first.
    readonly #free: number[] = [];
    // The slot of each stored value, by its `SHA-256`.
    readonly #stored = new Map<string, number>();
    // The blobs the sink is writing, by handle.
    readonly #open = new Map<string, SinkOpen>();
    // The blobs the sink finished that no store took yet, by handle.
    readonly #closed = new Map<string, FileSpan>();
    // The number of the last sink handle made.
    #count = 0;

    // Adds an open file, free unless its first bytes name a stored value.
    slot_add(handle: SlotHandle): void {
      const slot = this.#slots.length;
      this.#slots.push(handle);
      const name = this.#name_read(slot);
      if (name === "") {
        this.#free.push(slot);
        return;
      }
      if (this.#stored.has(name)) {
        throw new Error(i18n("substrate.cache_twice", name));
      }
      this.#stored.set(name, slot);
    }

    // The number of slots that hold nothing.
    slots_free(): number {
      return this.#free.length;
    }

    // Starts a blob of the header's size in a free slot. Returns its handle.
    sink_open(header: jslb.BlobHeader): string {
      const size = jslb.field_get(header, "size") as number;
      const slot = this.#slot_take();
      this.#count += 1;
      const handle = constants.sink_prefix + String(this.#count);
      const hash = new utility.HashStream();
      this.#open.set(handle, { slot, size, written: 0, hash });
      return handle;
    }

    // Writes bytes to the blob, a copy, and hashes them on the way.
    sink_append(handle: string, data: Uint8Array): void {
      const sink = this.#open.get(handle);
      if (sink === undefined) {
        throw new Error(i18n("substrate.cache_unknown", handle));
      }
      this.#bytes_write(sink.slot, constants.name_bytes + sink.written, data);
      sink.hash.bytes_add(data);
      sink.written += data.length;
    }

    // Ends the blob and returns its hash. A blob short of its size is freed.
    sink_close(handle: string): lines.Sha256 {
      const sink = this.#open.get(handle);
      if (sink === undefined) {
        throw new Error(i18n("substrate.cache_unknown", handle));
      }
      this.#open.delete(handle);
      if (sink.written === sink.size) {
        this.#closed.set(handle, { slot: sink.slot, size: sink.size });
      } else {
        this.#slot_free(sink.slot);
      }
      return sink.hash.digest_hex();
    }

    // Reads `length` bytes from `offset`, fewer only at the end of the file.
    cache_read(handle: string, offset: number, length: number): Uint8Array {
      const file = this.#file_find(handle);
      const count = Math.max(0, Math.min(length, file.size - offset));
      return this.#bytes_read(file.slot, constants.name_bytes + offset, count);
    }

    // The size of the value a handle names.
    handle_size(handle: string): number {
      return this.#file_find(handle).size;
    }

    // The `SHA-256` of the value a handle names, read in pieces.
    handle_hash(handle: string): lines.Sha256 {
      const file = this.#file_find(handle);
      const hash = new utility.HashStream();
      for (
        let offset = 0;
        offset < file.size;
        offset += constants.read_bytes
      ) {
        const count = Math.min(constants.read_bytes, file.size - offset);
        hash.bytes_add(
          this.#bytes_read(file.slot, constants.name_bytes + offset, count),
        );
      }
      return hash.digest_hex();
    }

    // The bytes of the value a handle names, all of them.
    handle_bytes(handle: string): Uint8Array {
      const file = this.#file_find(handle);
      return this.#bytes_read(file.slot, constants.name_bytes, file.size);
    }

    // Stores bytes under their name unless a file already holds them.
    bytes_store(name: string, data: Uint8Array): void {
      if (this.#stored.has(name)) {
        return;
      }
      const slot = this.#slot_take();
      this.#bytes_write(slot, constants.name_bytes, data);
      this.#name_write(slot, name);
      this.#stored.set(name, slot);
    }

    // Moves a finished blob under its name, freed when the name is held.
    handle_store(handle: string, name: string): void {
      const closed = this.#closed.get(handle);
      // A handle that is no finished blob is a stored name, already in place.
      if (closed === undefined) {
        return;
      }
      this.#closed.delete(handle);
      if (this.#stored.has(name)) {
        this.#slot_free(closed.slot);
        return;
      }
      this.#name_write(closed.slot, name);
      this.#stored.set(name, closed.slot);
    }

    // Frees a finished blob that a restore has read.
    handle_discard(handle: string): void {
      const closed = this.#closed.get(handle);
      if (closed !== undefined) {
        this.#closed.delete(handle);
        this.#slot_free(closed.slot);
      }
    }

    // The names of the stored values, in order.
    names_stored(): string[] {
      return [...this.#stored.keys()].sort();
    }

    // Whether a file holds the stored value of the name.
    name_held(name: string): boolean {
      return this.#stored.has(name);
    }

    // Frees the file of a stored value.
    name_remove(name: string): void {
      const slot = this.#stored.get(name);
      // A name no file holds meets the removal, and a read of it still throws.
      if (slot === undefined) {
        return;
      }
      this.#stored.delete(name);
      this.#slot_free(slot);
    }

    // The slot and value size of a stored name or a finished blob.
    #file_find(handle: string): FileSpan {
      const slot = this.#stored.get(handle);
      if (slot !== undefined) {
        const size = this.#slots[slot].getSize() - constants.name_bytes;
        return { slot, size };
      }
      const closed = this.#closed.get(handle);
      if (closed === undefined) {
        throw new Error(i18n("substrate.cache_unknown", handle));
      }
      return closed;
    }

    // The stored name in a slot's first bytes, empty when it holds none.
    #name_read(slot: number): string {
      if (this.#slots[slot].getSize() < constants.name_bytes) {
        return "";
      }
      const header = this.#bytes_read(slot, 0, constants.name_bytes);
      if (header[0] === 0) {
        return "";
      }
      const name = String.fromCharCode(...header);
      if (!constants.stored_name.test(name)) {
        throw new Error(i18n("substrate.cache_header", slot, name));
      }
      return name;
    }

    // Takes a free slot, emptied, its name bytes zero until it is stored.
    #slot_take(): number {
      const slot = this.#free.pop();
      if (slot === undefined) {
        throw new Error(i18n("substrate.cache_full", this.#slots.length));
      }
      this.#slots[slot].truncate(0);
      this.#bytes_write(slot, 0, new Uint8Array(constants.name_bytes));
      return slot;
    }

    // Empties a slot and makes it free.
    #slot_free(slot: number): void {
      this.#slots[slot].truncate(0);
      this.#free.push(slot);
    }

    // Writes a stored name into a slot's first bytes.
    #name_write(slot: number, name: string): void {
      this.#bytes_write(slot, 0, utility.utf8_encode(name));
    }

    // Writes bytes at an offset of a slot, all of them.
    #bytes_write(slot: number, at: number, data: Uint8Array): void {
      const written = this.#slots[slot].write(data, { at });
      if (written !== data.length) {
        throw new Error(
          i18n("substrate.write_short", slot, written, data.length),
        );
      }
    }

    // Reads exactly `count` bytes at an offset of a slot.
    #bytes_read(slot: number, at: number, count: number): Uint8Array {
      const data = new Uint8Array(count);
      const read = this.#slots[slot].read(data, { at });
      if (read !== count) {
        throw new Error(i18n("substrate.read_short", slot, read, count));
      }
      return data;
    }
  }

  // The slot pool behind each cache, which only this module reaches.
  const pools = new WeakMap<CacheFiles, SlotPool>();

  // The slot pool of a cache.
  function pool_of(cache: CacheFiles): SlotPool {
    return pools.get(cache) as SlotPool;
  }

  // The cache files, opened by the boot, and the decoder's streaming sink.
  export class CacheFiles implements jslb.BlobSink {
    // Takes the open files, each holding the value its first bytes name.
    constructor(slots: SlotHandle[]) {
      const pool = new SlotPool();
      pools.set(this, pool);
      for (const slot of slots) {
        pool.slot_add(slot);
      }
    }

    // Adds an open file, which the worker opened when free slots ran low.
    slot_add(slot: SlotHandle): void {
      pool_of(this).slot_add(slot);
    }

    // The number of files that hold nothing.
    slots_free(): number {
      return pool_of(this).slots_free();
    }

    // Starts a blob in a free file and returns its handle.
    sink_open(header: jslb.BlobHeader): string {
      return pool_of(this).sink_open(header);
    }

    // Writes a copy of the bytes, valid only during the call, and hashes them.
    sink_append(handle: string, data: Uint8Array): void {
      pool_of(this).sink_append(handle, data);
    }

    // Ends the blob and returns its `SHA-256`. A short blob is freed.
    sink_close(handle: string): lines.Sha256 {
      return pool_of(this).sink_close(handle);
    }

    // Reads `length` bytes from `offset`, fewer only at the end of the file.
    cache_read(handle: string, offset: number, length: number): Uint8Array {
      return pool_of(this).cache_read(handle, offset, length);
    }
  }

  // One owner's databases under one root in the pool, the single door.
  export class Store {
    // The sqlite3.wasm module.
    readonly #sqlite: SqliteModule;
    // The OPFS pool of the database files.
    readonly #pool: SqlitePool;
    // The cache and its sink.
    readonly #cache: CacheFiles;
    // The slots of the cache.
    readonly #slots: SlotPool;
    // The prefix of the database files in the pool.
    readonly #root: string;
    // The largest value kept in its row.
    readonly #overflow_bytes: number;
    // The count of a scene's turns at which a `user` turn compacts them.
    readonly #compact_turns: number;
    // What takes the push of each committed operation.
    readonly #tasks: Notifier;
    // The open databases, by name.
    readonly #connections = new Map<string, SqliteDatabase>();
    // The databases the running transaction began, in order.
    #joined: SqliteDatabase[] | undefined = undefined;
    // The cache files the running transaction stopped naming.
    #unlinks = new Set<string>();
    // The pushes of the running transaction, given on after its commit.
    #pending: lines.Line[] = [];
    // The `db.restore` waiting for its `db.file` lines, if any.
    #restore_wait: RestoreWait | undefined = undefined;

    // Takes the module, the pool, the cache, the root, its sizes, the queue.
    constructor(
      sqlite3: SqliteModule,
      pool: SqlitePool,
      cache: CacheFiles,
      root: string,
      overflow_bytes: number,
      compact_turns: number,
      tasks: Notifier,
    ) {
      this.#sqlite = sqlite3;
      this.#pool = pool;
      this.#cache = cache;
      this.#slots = pool_of(cache);
      this.#root = root;
      this.#overflow_bytes = overflow_bytes;
      this.#compact_turns = compact_turns;
      this.#tasks = tasks;
    }

    // Opens `<root>/<name>.sqlite`, applying the schema.
    db_open(name: string): void {
      name_check(name);
      if (this.#connections.has(name)) {
        throw new Error(i18n("substrate.db_open", name));
      }
      if (!this.#file_exists(name)) {
        throw new Error(i18n("substrate.db_absent", name));
      }
      this.#database_open(name, constants.open_write);
    }

    // Closes an open database, which must not be inside a transaction.
    db_close(name: string): void {
      const database = this.#connection_get(name);
      if (this.#in_transaction(database)) {
        throw new Error(i18n("substrate.db_busy", name));
      }
      database.close();
      this.#connections.delete(name);
    }

    // The open database names.
    db_list(): string[] {
      return [...this.#connections.keys()].sort();
    }

    // Creates and opens a new database, then pushes it at once.
    db_create(name: string): void {
      name_check(name);
      if (this.#file_exists(name)) {
        throw new Error(i18n("substrate.db_exists", name));
      }
      try {
        this.#database_open(name, constants.open_create);
      } catch (error) {
        this.#pool.unlink(this.#path_find(name));
        throw error;
      }
      this.#push_send(push_make("db.create", { db: name }));
    }

    // Closes and deletes a database and its cache files, then pushes it.
    db_drop(name: string): void {
      this.#file_remove(name);
      this.#push_send(push_make("db.drop", { db: name }));
    }

    // The value a ref names. `db` is the database an internal ref is in.
    kv_get(ref: lines.KvRef, db?: string): KvValue {
      const [name, key] = ref_resolve(ref, db);
      const rows = rows_select(
        this.#connection_get(name),
        "SELECT size, sha256, data FROM _kv WHERE key = ?",
        [key],
      );
      if (rows.length === 0) {
        throw new Error(i18n("substrate.key_missing", key, name));
      }
      const [size, sha256, data] = rows[0] as [
        number,
        Uint8Array,
        Uint8Array | null,
      ];
      const hex = hex_of(sha256);
      if (data === null && !this.#slots.name_held(hex)) {
        throw new Error(i18n("substrate.file_lost", ref, hex));
      }
      return { data: data === null ? hex : data, size, sha256: hex };
    }

    // Writes bytes, or moves a cache handle's file. Returns the row.
    kv_put(
      ref: lines.KvRef,
      data: Uint8Array | string,
      db?: string,
    ): lines.KvRow {
      const [name, key] = ref_resolve(ref, db);
      const database = this.#connection_get(name);
      return this.transaction_run(() =>
        this.#value_put(name, database, key, data),
      );
    }

    // Deletes the row, its cache file when no row names it.
    kv_delete(ref: lines.KvRef, db?: string): void {
      const [name, key] = ref_resolve(ref, db);
      const database = this.#connection_get(name);
      this.transaction_run(() => this.#value_delete(name, database, key));
    }

    // The rows of a database whose keys start with the prefix, by key.
    kv_list(db: string, prefix: string): lines.KvRow[] {
      const rows = rows_select(
        this.#connection_get(db),
        "SELECT key, size, sha256 FROM _kv" +
          " WHERE substr(key, 1, length(?1)) = ?1 ORDER BY key",
        [prefix],
      );
      return rows.map((row) => ({
        k: row[0] as string,
        size: row[1] as number,
        sha256: hex_of(row[2] as Uint8Array),
      }));
    }

    // Removes the stored cache files no row names. Returns their count.
    kv_check(db: string): number {
      this.#connection_get(db);
      const named = this.#hashes_named();
      let removed = 0;
      for (const name of this.#slots.names_stored()) {
        if (!named.has(name)) {
          this.#slots.name_remove(name);
          removed += 1;
        }
      }
      return removed;
    }

    // The document a `Document-Ref` names, in its encoded form.
    doc_get(ref: lines.DocRef, db?: string): lines.Document {
      if (ref_split(ref).version === undefined) {
        throw new Error(i18n("substrate.document_ref", ref));
      }
      const data = this.#value_bytes(this.kv_get(ref, db));
      return JSON.parse(utility.utf8_decode(data)) as lines.Document;
    }

    // Writes version head plus one, moves the head, returns the new ref.
    doc_put(db: string, id: string, body: lines.Document): lines.DocPutReply {
      if (id === "") {
        throw new Error(i18n("substrate.id_empty"));
      }
      doc_decode(body);
      const text = json_canonical(body);
      const data = utility.utf8_encode(text);
      const database = this.#connection_get(db);
      return this.transaction_run(() =>
        this.#document_put(db, database, id, data, text),
      );
    }

    // The current `Document-Ref` of an id. An unknown id throws.
    doc_head(db: string, id: string): lines.DocRef {
      const rows = rows_select(
        this.#connection_get(db),
        "SELECT version FROM _head WHERE id = ?",
        [id],
      );
      if (rows.length === 0) {
        throw new Error(i18n("substrate.id_missing", id, db));
      }
      return `/${db}/${id}/${String(rows[0][0])}`;
    }

    // A `user` turn on a scene of `compact_turns` turns first compacts them.
    turn_append(
      scene: lines.DocRef,
      role: provider.Role,
      content: provider.ChatMessage,
    ): lines.TurnAppendReply {
      const name = scene_database(scene);
      const text = json_canonical(content);
      const database = this.#connection_get(name);
      return this.transaction_run(() => {
        if (role === constants.compact_role) {
          this.#threshold_compact(database, scene);
        }
        return this.#turn_add(database, scene, role, text);
      });
    }

    // The scene's turns in order.
    turn_list(scene: lines.DocRef): TurnRow[] {
      const rows = rows_select(
        this.#connection_get(scene_database(scene)),
        "SELECT scene, n, role, content FROM _turn" +
          " WHERE scene = ? ORDER BY n",
        [scene],
      );
      return rows.map((row) => ({
        scene: row[0] as string,
        n: row[1] as number,
        role: row[2] as provider.Role,
        content: JSON.parse(row[3] as string) as provider.ChatMessage,
      }));
    }

    // Replaces turns 1 to `through` by one summary turn at 1, this side only.
    turn_compact(scene: lines.DocRef, through: number, summary: string): void {
      if (through < 1) {
        throw new Error(i18n("substrate.through_bad", through));
      }
      const name = scene_database(scene);
      const database = this.#connection_get(name);
      this.transaction_run(() =>
        this.#turns_compact(database, scene, through, summary),
      );
    }

    // Runs the statements in order, in the running transaction.
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[] {
      const database = this.#connection_get(db);
      return this.transaction_run(() =>
        this.#statements_run(db, database, statements),
      );
    }

    // The file and the handles of the cache files its rows name and it holds.
    db_snapshot(db: string): DbImage {
      const database = this.#connection_get(db);
      return this.transaction_run(() => {
        this.#transaction_join(database);
        const files = [...hashes_read(database)]
          .filter((name) => this.#slots.name_held(name))
          .sort();
        return {
          data: this.#sqlite.capi.sqlite3_js_db_export(database.pointer),
          files,
        };
      });
    }

    // Replaces the database by the file and keeps the cache files given.
    db_restore(
      db: string,
      data: Uint8Array | string,
      files: (Uint8Array | string)[],
    ): void {
      this.#file_load(db, data);
      for (const file of files) {
        if (typeof file === "string") {
          const sha256 = this.#slots.handle_hash(file);
          this.#slots.handle_store(file, sha256);
        } else {
          this.#slots.bytes_store(utility.sha256_hex(file), file);
        }
      }
    }

    // Runs `fn` in one transaction: commit on return, roll back on a throw.
    transaction_run<T>(fn: () => T): T {
      if (this.#joined !== undefined) {
        return fn();
      }
      const result = this.#outermost_run(fn);
      const pending = this.#pending;
      this.#pending = [];
      this.#cache_prune(this.#unlinks);
      for (const line of pending) {
        this.#push_send(line);
      }
      return result;
    }

    // The streaming sink of the decoder, the cache this store was given.
    sink(): jslb.BlobSink {
      return this.#cache;
    }

    // Registers the handlers of the store's lines on this thread, version 0.
    handlers_register(register: HandlerRegister): void {
      for (const [type, fn] of Object.entries(this.#handlers_make())) {
        register(type, 0, fn);
      }
    }

    // Opens a database file with the flags, applying the schema.
    #database_open(name: string, flags: string): void {
      const database = new this.#pool.OpfsSAHPoolDb({
        filename: this.#path_find(name),
        flags,
      });
      try {
        database.exec({ sql: "PRAGMA foreign_keys = ON" });
        this.#schema_apply(database);
        this.#connections.set(name, database);
      } catch (error) {
        database.close();
        throw error;
      }
    }

    // The connection of an open database. Any other database throws.
    #connection_get(name: string): SqliteDatabase {
      const database = this.#connections.get(name);
      if (database === undefined) {
        throw new Error(i18n("substrate.db_closed", name));
      }
      return database;
    }

    // The file of a database in the pool.
    #path_find(name: string): string {
      return `${this.#root}/${name}${constants.db_extension}`;
    }

    // Whether the pool holds the database's file.
    #file_exists(name: string): boolean {
      return this.#pool.getFileNames().includes(this.#path_find(name));
    }

    // The names of the database files under the root, in order.
    #files_held(): string[] {
      const prefix = `${this.#root}/`;
      const extension = constants.db_extension;
      const names: string[] = [];
      for (const file of this.#pool.getFileNames()) {
        if (file.startsWith(prefix) && file.endsWith(extension)) {
          const end = file.length - extension.length;
          const name = file.slice(prefix.length, end);
          if (constants.c_identifier.test(name)) {
            names.push(name);
          }
        }
      }
      return names.sort();
    }

    // Closes and deletes an open database's file, then its cache files.
    #file_remove(name: string): void {
      const hashes = hashes_read(this.#connection_get(name));
      this.db_close(name);
      this.#pool.unlink(this.#path_find(name));
      this.#cache_prune(hashes);
    }

    // Checks a database file in a file of its own, then replaces the copy.
    #file_load(db: string, data: Uint8Array | string): void {
      name_check(db);
      const path = this.#path_find(db);
      const temporary = path + constants.restore_suffix;
      if (this.#pool.getFileNames().includes(temporary)) {
        throw new Error(i18n("substrate.restore_left", temporary));
      }
      const bytes =
        typeof data === "string" ? this.#slots.handle_bytes(data) : data;
      try {
        this.#pool.importDb(temporary, bytes);
        this.#schema_verify(temporary);
        if (this.#connections.has(db)) {
          this.db_close(db);
        }
        this.#pool.importDb(path, bytes);
      } finally {
        this.#pool.unlink(temporary);
      }
      if (typeof data === "string") {
        this.#slots.handle_discard(data);
      }
      this.#database_open(db, constants.open_write);
    }

    // Creates the substrate's tables in a database that lacks them.
    #schema_apply(database: SqliteDatabase): void {
      database.exec({ sql: "BEGIN IMMEDIATE" });
      try {
        const found = tables_found(database);
        if (found.length > 0) {
          schema_check(database, found);
        } else {
          for (const statement of constants.schema_statements) {
            database.exec({ sql: statement });
          }
          database.exec({
            sql: constants.meta_insert,
            bind: [constants.schema_version],
          });
        }
        database.exec({ sql: "COMMIT" });
      } catch (error) {
        if (this.#in_transaction(database)) {
          database.exec({ sql: "ROLLBACK" });
        }
        throw error;
      }
    }

    // Throws unless a database file holds the substrate's tables, read only.
    #schema_verify(path: string): void {
      const database = new this.#pool.OpfsSAHPoolDb({
        filename: path,
        flags: constants.open_read,
      });
      try {
        schema_check(database, tables_found(database));
      } finally {
        database.close();
      }
    }

    // Whether a connection is inside a transaction.
    #in_transaction(database: SqliteDatabase): boolean {
      return this.#sqlite.capi.sqlite3_get_autocommit(database.pointer) === 0;
    }

    // Begins the running transaction on a connection at its first use.
    #transaction_join(database: SqliteDatabase): void {
      const joined = this.#joined as SqliteDatabase[];
      if (!joined.includes(database)) {
        database.exec({ sql: "BEGIN IMMEDIATE" });
        joined.push(database);
      }
    }

    // Runs the outermost transaction: commits all, or rolls all back.
    #outermost_run<T>(fn: () => T): T {
      const joined: SqliteDatabase[] = [];
      this.#joined = joined;
      this.#unlinks = new Set();
      this.#pending = [];
      try {
        const result = fn();
        for (const database of joined) {
          database.exec({ sql: "COMMIT" });
        }
        return result;
      } catch (error) {
        for (const database of joined) {
          if (this.#in_transaction(database)) {
            database.exec({ sql: "ROLLBACK" });
          }
        }
        this.#pending = [];
        throw error;
      } finally {
        this.#joined = undefined;
      }
    }

    // Writes a value inside the transaction, pushing it when it changed.
    #value_put(
      name: string,
      database: SqliteDatabase,
      key: string,
      data: Uint8Array | string,
    ): lines.KvRow {
      this.#transaction_join(database);
      const written = this.#row_write(database, key, data);
      const { row } = written;
      if (!written.changed) {
        return row;
      }
      // A cache file read whole, or a copy, as the caller may move its bytes.
      const bytes = written.cached
        ? this.#slots.handle_bytes(row.sha256)
        : (data as Uint8Array).slice();
      this.#pending.push(
        push_make("kv.put", {}, `/${name}/${key}`, [jslb.blob_make(bytes)]),
      );
      return row;
    }

    // Deletes a row inside the transaction, pushing it when it existed.
    #value_delete(name: string, database: SqliteDatabase, key: string): void {
      this.#transaction_join(database);
      const old = rows_select(
        database,
        "SELECT sha256, data IS NULL FROM _kv WHERE key = ?",
        [key],
      );
      if (old.length === 0) {
        return;
      }
      database.exec({ sql: "DELETE FROM _kv WHERE key = ?", bind: [key] });
      if (old[0][1] === 1) {
        this.#unlinks.add(hex_of(old[0][0] as Uint8Array));
      }
      this.#pending.push(push_make("kv.delete", {}, `/${name}/${key}`));
    }

    // Writes a row, its cache file first, and says whether the row changed.
    #row_write(
      database: SqliteDatabase,
      key: string,
      data: Uint8Array | string,
    ): RowWritten {
      const handle = typeof data === "string";
      const size = handle ? this.#slots.handle_size(data) : data.length;
      const sha256 = handle
        ? this.#slots.handle_hash(data)
        : utility.sha256_hex(data);
      if (handle && size <= this.#overflow_bytes) {
        throw new Error(
          i18n("substrate.file_small", data, size, this.#overflow_bytes),
        );
      }
      const cached = size > this.#overflow_bytes;
      if (cached) {
        if (handle) {
          this.#slots.handle_store(data, sha256);
        } else {
          this.#slots.bytes_store(sha256, data);
        }
      }
      const row = { k: key, size, sha256 };
      const old = rows_select(
        database,
        "SELECT sha256, data IS NULL FROM _kv WHERE key = ?",
        [key],
      );
      if (old.length > 0 && hex_of(old[0][0] as Uint8Array) === sha256) {
        return { row, changed: false, cached };
      }
      database.exec({
        sql:
          "INSERT INTO _kv (key, size, sha256, data) VALUES (?, ?, ?, ?)" +
          " ON CONFLICT (key) DO UPDATE SET size = excluded.size," +
          " sha256 = excluded.sha256, data = excluded.data",
        bind: [key, size, bytes_of(sha256), cached ? null : data],
      });
      if (old.length > 0 && old[0][1] === 1) {
        this.#unlinks.add(hex_of(old[0][0] as Uint8Array));
      }
      return { row, changed: true, cached };
    }

    // Writes the next version of a document, moves its head, pushes it.
    #document_put(
      db: string,
      database: SqliteDatabase,
      id: string,
      data: Uint8Array,
      text: string,
    ): lines.DocPutReply {
      this.#transaction_join(database);
      // The next version is counted by SQLite, exact past `2^53`, as text.
      const rows = rows_select(
        database,
        "SELECT CAST(version + 1 AS TEXT) FROM _head WHERE id = ?",
        [id],
      );
      const version = rows.length === 0 ? "1" : (rows[0][0] as string);
      const key = `${id}/${version}`;
      const exists = rows_select(database, "SELECT 1 FROM _kv WHERE key = ?", [
        key,
      ]);
      if (exists.length > 0) {
        throw new Error(i18n("substrate.version_exists", key, db));
      }
      this.#row_write(database, key, data);
      database.exec({
        sql:
          "INSERT INTO _head (id, version) VALUES (?, ?)" +
          " ON CONFLICT (id) DO UPDATE SET version = excluded.version",
        bind: [id, version],
      });
      const body = JSON.parse(text) as lines.Document;
      this.#pending.push(push_make("doc.put", { db, id, body }));
      return { ref: `/${db}/${key}` };
    }

    // Compacts the scene's turns 1 to its last once they are `compact_turns`.
    #threshold_compact(database: SqliteDatabase, scene: string): void {
      this.#transaction_join(database);
      const [count, last] = rows_select(
        database,
        "SELECT COUNT(*), MAX(n) FROM _turn WHERE scene = ?",
        [scene],
      )[0] as [number, number];
      if (count >= this.#compact_turns) {
        const summary = i18n("substrate.turns_compacted", last, count);
        this.#turns_compact(database, scene, last, summary);
      }
    }

    // Inserts a turn after the last of its scene and pushes it.
    #turn_add(
      database: SqliteDatabase,
      scene: string,
      role: provider.Role,
      text: string,
    ): lines.TurnAppendReply {
      this.#transaction_join(database);
      const n = database.selectValue(
        "SELECT COALESCE(MAX(n), 0) + 1 FROM _turn WHERE scene = ?",
        [scene],
      ) as number;
      database.exec({
        sql:
          "INSERT INTO _turn (scene, n, role, content)" +
          " VALUES (?, ?, ?, ?)",
        bind: [scene, n, role, text],
      });
      const content = JSON.parse(text) as provider.ChatMessage;
      this.#pending.push(push_make("turn.append", { scene, role, content }));
      return { n };
    }

    // Deletes turns 1 to `through` and inserts the summary at 1, sending none.
    #turns_compact(
      database: SqliteDatabase,
      scene: string,
      through: number,
      summary: string,
    ): void {
      this.#transaction_join(database);
      database.exec({
        sql: "DELETE FROM _turn WHERE scene = ? AND n <= ?",
        bind: [scene, through],
      });
      if (database.changes(false) === 0) {
        throw new Error(i18n("substrate.turns_none", scene, through));
      }
      const content = json_canonical({
        role: constants.summary_role,
        content: summary,
      });
      database.exec({
        sql:
          "INSERT INTO _turn (scene, n, role, content)" +
          " VALUES (?, 1, ?, ?)",
        bind: [scene, constants.summary_role, content],
      });
    }

    // Runs the statements, counting a change of a row or of the schema.
    #statements_run(
      db: string,
      database: SqliteDatabase,
      statements: lines.SqlStatement[],
    ): lines.SqlResult[] {
      this.#transaction_join(database);
      const changes = database.changes(true);
      const schema = schema_read(database);
      const results = statements.map((statement) =>
        statement_run(database, statement),
      );
      if (
        database.changes(true) !== changes ||
        schema_read(database) !== schema
      ) {
        const copy = structuredClone(statements);
        this.#pending.push(push_make("sql.run", { db, statements: copy }));
      }
      return results;
    }

    // Gives a push line to the queue, for the server.
    #push_send(line: lines.Line): void {
      this.#tasks.line_notify(line, constants.push_owner);
    }

    // Removes the cache files of the names that no row holds.
    #cache_prune(names: Set<string>): void {
      if (names.size === 0) {
        return;
      }
      const named = this.#hashes_named();
      for (const name of [...names].sort()) {
        if (!named.has(name)) {
          this.#slots.name_remove(name);
        }
      }
    }

    // The cache names the rows of each database file under the root hold.
    #hashes_named(): Set<string> {
      const named = new Set<string>();
      for (const name of this.#files_held()) {
        const open = this.#connections.get(name);
        if (open !== undefined) {
          for (const hash of hashes_read(open)) {
            named.add(hash);
          }
          continue;
        }
        const database = new this.#pool.OpfsSAHPoolDb({
          filename: this.#path_find(name),
          flags: constants.open_read,
        });
        try {
          for (const hash of hashes_read(database)) {
            named.add(hash);
          }
        } finally {
          database.close();
        }
      }
      return named;
    }

    // The bytes of a value, read from the cache when it is held there.
    #value_bytes(value: KvValue): Uint8Array {
      return typeof value.data === "string"
        ? this.#slots.handle_bytes(value.data)
        : value.data;
    }

    // The handlers of the UI thread's requests and the server's pushes.
    #handlers_make(): { [type: string]: dispatch.Handler } {
      return {
        // Reads a value, its bytes as blob 1, read whole from the cache.
        "kv.get": (line) => {
          const value = this.kv_get(ref_of(line));
          return dispatch.reply_make(
            line,
            { size: value.size, sha256: value.sha256 },
            [jslb.blob_make(this.#value_bytes(value))],
          );
        },
        // Writes blob 1 under the ref.
        "kv.put": (line) => {
          const row = this.kv_put(ref_of(line), blob_data(line));
          return dispatch.reply_make(line, { sha256: row.sha256 });
        },
        // Deletes the ref's row.
        "kv.delete": (line) => {
          this.kv_delete(ref_of(line));
          return dispatch.reply_make(line, {});
        },
        // Lists the rows under a prefix.
        "kv.list": (line) => {
          const { db, prefix } = payload_read<lines.KvList>(line);
          return dispatch.reply_make(line, { keys: this.kv_list(db, prefix) });
        },
        // Writes a document.
        "doc.put": (line) => {
          const { db, id, body } = payload_read<lines.DocPut>(line);
          const { ref } = this.doc_put(db, id, body);
          return dispatch.reply_make(line, { ref });
        },
        // Reads a document's head.
        "doc.head": (line) => {
          const { db, id } = payload_read<lines.DocHead>(line);
          return dispatch.reply_make(line, { ref: this.doc_head(db, id) });
        },
        // Creates a database.
        "db.create": (line) => {
          this.db_create(payload_read<lines.DbName>(line).db);
          return dispatch.reply_make(line, {});
        },
        // Drops a database.
        "db.drop": (line) => {
          this.db_drop(payload_read<lines.DbName>(line).db);
          return dispatch.reply_make(line, {});
        },
        // Appends a turn.
        "turn.append": (line) => {
          const { scene, role, content } =
            payload_read<lines.TurnAppend>(line);
          const { n } = this.turn_append(scene, role, content);
          return dispatch.reply_make(line, { n });
        },
        // Runs statements and answers their results.
        "sql.run": (line) => {
          const { db, statements } = payload_read<lines.SqlRun>(line);
          const results = this.sql_run(db, statements);
          return dispatch.reply_make(line, { results });
        },
        // Restores at once with no cache file, else waits for its files.
        "db.restore": (line) => {
          const { db, files } = payload_read<lines.DbRestore>(line);
          const waiting = this.#restore_wait;
          if (waiting !== undefined) {
            throw new Error(
              i18n("substrate.restore_pending", db, waiting.db, waiting.left),
            );
          }
          const data = blob_data(line);
          if (files === 0) {
            this.db_restore(db, data, []);
          } else {
            this.#restore_wait = { db, data, files: [], left: files };
          }
          return undefined;
        },
        // Keeps one cache file of the waiting restore, which runs at the last.
        "db.file": (line) => {
          const { db } = payload_read<lines.DbFile>(line);
          const waiting = this.#restore_wait;
          if (waiting === undefined || waiting.db !== db) {
            throw new Error(i18n("substrate.file_unexpected", db));
          }
          waiting.files.push(blob_data(line));
          waiting.left -= 1;
          if (waiting.left === 0) {
            this.#restore_wait = undefined;
            this.db_restore(db, waiting.data, waiting.files);
          }
          return undefined;
        },
      };
    }
  }
}
Object.freeze(substrate);
