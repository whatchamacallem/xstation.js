// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The browser substrate, the single door to SQLite in the AI worker: one
// sqlite3.wasm connection for each database file of the OPFS pool under a
// root, the substrate's tables in each, values with overflow to a cache of
// OPFS files held open for synchronous access, documents, turns that compact
// themselves when a `user` turn finds `compact_turns` of them, SQL,
// snapshots sent as one blob, the measurement and administration of the
// databases,
// cached values filled back from the server and freed by budget, and the
// emitting side of replication, which hands on each committed modifying
// operation as the line the server applies. It is given an initialized
// module, an installed pool and open cache files, and waits on nothing.
namespace substrate {
  // The ranges of the code points Python's `str.isspace` holds, ends kept.
  const space_ranges: readonly (readonly [number, number])[] = [
    [0x09, 0x0d],
    [0x1c, 0x20],
    [0x85, 0x85],
    [0xa0, 0xa0],
    [0x1680, 0x1680],
    [0x2000, 0x200a],
    [0x2028, 0x2029],
    [0x202f, 0x202f],
    [0x205f, 0x205f],
    [0x3000, 0x3000],
  ];

  // The range of the code points of surrogates.
  const surrogate_ranges: readonly (readonly [number, number])[] = [
    [0xd800, 0xdfff],
  ];

  // The body of a character class of the ranges, as code point escapes.
  function class_text(ranges: readonly (readonly [number, number])[]): string {
    return ranges
      .map(
        ([first, last]) =>
          `\\u{${first.toString(16)}}-\\u{${last.toString(16)}}`,
      )
      .join("");
  }

  // The schema, names, patterns and sizes, and the fields of the operations.
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
    // The first rows of `_meta`: `seq` 0 and the schema version bound.
    meta_insert:
      "INSERT INTO _meta (name, value)" +
      " VALUES ('seq', '0'), ('schema', ?)",
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
    // The largest magnitude of a number in stored JSON, as on the wire.
    integer_limit: 2 ** 53,
    // A database name, a C identifier.
    c_identifier: /^[A-Za-z_][A-Za-z0-9_]*$/,
    // An external ref: a slash, a database name, a slash and a key.
    external_ref: /^\/([A-Za-z_][A-Za-z0-9_]*)\/(.+)$/su,
    // A reference string: an external ref whose key holds no Python space.
    reference_string: new RegExp(
      `^/[A-Za-z_][A-Za-z0-9_]*/[^${class_text(space_ranges)}]+$`,
      "u",
    ),
    // A surrogate standing alone, which `UTF-8` cannot encode.
    lone_surrogate: new RegExp(`[${class_text(surrogate_ranges)}]`, "u"),
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
    // The sizes of `SHA-256`, in bytes, words, rounds and bits.
    block_bytes: 64,
    block_words: 16,
    round_count: 64,
    hash_words: 8,
    word_bytes: 4,
    length_bytes: 8,
    byte_bits: 8,
    padding_marker: 0x80,
    word_range: 2 ** 32,
    // The payload fields of each forwarded operation, sorted.
    operation_fields: Object.freeze<{
      readonly [type: string]: readonly string[];
    }>({
      "db.create": ["db"],
      "db.drop": ["db"],
      "doc.put": ["body", "db", "id"],
      "kv.delete": ["k"],
      "kv.put": ["data", "k"],
      "sql.run": ["db", "statements"],
      "turn.append": ["content", "role", "scene"],
      "turn.compact": ["scene", "summary", "through"],
    }),
    // The fields of a statement of `sql.run`, sorted.
    statement_fields: Object.freeze<readonly string[]>(["params", "sql"]),
    // The forwarded operations whose replies carry no `seq`.
    seqless_types: Object.freeze<readonly string[]>(["db.create", "db.drop"]),
  });

  // The first prime numbers, as many as asked for.
  function primes_first(count: number): number[] {
    const primes: number[] = [];
    for (let candidate = 2; primes.length < count; candidate += 1) {
      if (primes.every((prime) => candidate % prime !== 0)) {
        primes.push(candidate);
      }
    }
    return primes;
  }

  // The first 32 bits of the fractional part of a positive number.
  function fraction_bits(value: number): number {
    return Math.floor((value - Math.floor(value)) * constants.word_range);
  }

  // The round constants: cube root fractions of the first 64 primes.
  const round_table = Uint32Array.from(
    primes_first(constants.round_count),
    (prime) => fraction_bits(Math.cbrt(prime)),
  );

  // The first hash state: square root fractions of the first 8 primes.
  const hash_start = Uint32Array.from(
    primes_first(constants.hash_words),
    (prime) => fraction_bits(Math.sqrt(prime)),
  );

  // Rotates the 32 bits of a word right by a count of bits.
  function bits_rotate(word: number, count: number): number {
    return (word >>> count) | (word << (32 - count));
  }

  // Mixes the block of 64 bytes at the offset into the hash state.
  function block_mix(
    state: Uint32Array,
    schedule: Uint32Array,
    view: DataView,
    offset: number,
  ): void {
    const { block_words, round_count, word_bytes } = constants;
    for (let index = 0; index < block_words; index += 1) {
      schedule[index] = view.getUint32(offset + index * word_bytes);
    }
    for (let index = block_words; index < round_count; index += 1) {
      const early = schedule[index - 15];
      const late = schedule[index - 2];
      const sigma_early =
        bits_rotate(early, 7) ^ bits_rotate(early, 18) ^ (early >>> 3);
      const sigma_late =
        bits_rotate(late, 17) ^ bits_rotate(late, 19) ^ (late >>> 10);
      schedule[index] =
        schedule[index - 16] + sigma_early + schedule[index - 7] + sigma_late;
    }
    // The working variables are named as in the standard.
    let [a, b, c, d, e, f, g, h] = state;
    for (let index = 0; index < round_count; index += 1) {
      const sigma_e =
        bits_rotate(e, 6) ^ bits_rotate(e, 11) ^ bits_rotate(e, 25);
      const choice = (e & f) ^ (~e & g);
      const first =
        (h + sigma_e + choice + round_table[index] + schedule[index]) | 0;
      const sigma_a =
        bits_rotate(a, 2) ^ bits_rotate(a, 13) ^ bits_rotate(a, 22);
      const majority = (a & b) ^ (a & c) ^ (b & c);
      const second = (sigma_a + majority) | 0;
      h = g;
      g = f;
      f = e;
      e = (d + first) | 0;
      d = c;
      c = b;
      b = a;
      a = (first + second) | 0;
    }
    const working = [a, b, c, d, e, f, g, h];
    for (let index = 0; index < constants.hash_words; index += 1) {
      state[index] += working[index];
    }
  }

  // A `SHA-256` fed in pieces of any size, as a streamed blob arrives.
  class HashStream {
    // The hash state after every whole block fed.
    readonly #state = new Uint32Array(hash_start);
    // The message schedule a block is mixed with.
    readonly #schedule = new Uint32Array(constants.round_count);
    // The bytes of the block not yet whole.
    readonly #block = new Uint8Array(constants.block_bytes);
    // A view of those bytes as words.
    readonly #view = new DataView(this.#block.buffer);
    // How many bytes of the block are filled.
    #filled = 0;
    // How many bytes were fed in all.
    #length = 0;

    // Feeds bytes, keeping none of the caller's view after the call.
    bytes_add(data: Uint8Array): void {
      const { block_bytes } = constants;
      this.#length += data.length;
      let offset = 0;
      if (this.#filled > 0) {
        offset = Math.min(block_bytes - this.#filled, data.length);
        this.#block.set(data.subarray(0, offset), this.#filled);
        this.#filled += offset;
        if (this.#filled < block_bytes) {
          return;
        }
        block_mix(this.#state, this.#schedule, this.#view, 0);
        this.#filled = 0;
      }
      const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
      for (; offset + block_bytes <= data.length; offset += block_bytes) {
        block_mix(this.#state, this.#schedule, view, offset);
      }
      this.#block.set(data.subarray(offset));
      this.#filled = data.length - offset;
    }

    // The hash of the bytes fed so far as 64 lowercase hex characters.
    digest_hex(): lines.Sha256 {
      const { block_bytes, length_bytes, word_bytes, word_range } = constants;
      const state = new Uint32Array(this.#state);
      const filled = this.#filled;
      const tail_length =
        filled < block_bytes - length_bytes ? block_bytes : 2 * block_bytes;
      const tail = new Uint8Array(tail_length);
      tail.set(this.#block.subarray(0, filled));
      tail[filled] = constants.padding_marker;
      const bits = this.#length * constants.byte_bits;
      const view = new DataView(tail.buffer);
      const high = Math.floor(bits / word_range);
      view.setUint32(tail_length - length_bytes, high);
      view.setUint32(tail_length - word_bytes, bits % word_range);
      for (let offset = 0; offset < tail_length; offset += block_bytes) {
        block_mix(state, this.#schedule, view, offset);
      }
      let hex = "";
      for (const word of state) {
        hex += word.toString(16).padStart(word_bytes * 2, "0");
      }
      return hex;
    }
  }

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

  // The measure of an open database, by heuristics, and its `seq`.
  export interface DatabaseStats {
    name: string;
    bytes: number;
    free_bytes: number;
    cache_bytes: number;
    seq: number;
  }

  // The measure of the open databases against the soft limit.
  export interface StoreStats {
    databases: DatabaseStats[];
    total_bytes: number;
    soft_bytes: number;
    over: boolean;
  }

  // The bytes of a database before and after its compaction.
  export interface CompactBytes {
    before: number;
    after: number;
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
    hash: HashStream;
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

  // A forwarded operation not yet answered: type, database, since, holds.
  interface FlightRecord {
    type: string;
    db: string;
    since: number;
    names: string[];
  }

  // A forwarded line and its record.
  interface Forward {
    line: lines.Line;
    record: FlightRecord;
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

  // The database an external ref names. An internal ref throws.
  function ref_database(ref: string): string {
    const db = ref_split(ref).db;
    if (db === undefined) {
      throw new Error(i18n("substrate.ref_internal", ref));
    }
    return db;
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

  // The canonical JSON text of a value: at every level integer keys first.
  function json_canonical(value: unknown): string {
    if (value === null || typeof value === "boolean") {
      return String(value);
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        throw new Error(i18n("substrate.number_refused", value));
      }
      if (Math.abs(value) > constants.integer_limit) {
        throw new Error(i18n("substrate.integer_range", value));
      }
      return utility.json_text(value);
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

  // The `seq` of a database, the decimal text of its `_meta` row.
  function seq_read(database: SqliteDatabase): number {
    return Number(
      database.selectValue("SELECT value FROM _meta WHERE name = 'seq'"),
    );
  }

  // Adds one to the `seq` of a database and returns it.
  function seq_bump(database: SqliteDatabase): number {
    const seq = seq_read(database) + 1;
    database.exec({
      sql: "UPDATE _meta SET value = ? WHERE name = 'seq'",
      bind: [String(seq)],
    });
    return seq;
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

  // Throws the desync of replication when `since` is not the `seq`.
  function since_check(
    type: string,
    since: number,
    seq: number,
    db: string,
  ): void {
    if (since !== seq) {
      throw new Error(i18n("substrate.since_stale", type, since, seq, db));
    }
  }

  // Throws unless the object holds exactly the fields, which are sorted.
  function fields_check(
    type: string,
    value: object,
    fields: readonly string[],
  ): void {
    const keys = Object.keys(value).sort();
    if (keys.join() !== fields.join()) {
      throw new Error(
        i18n("substrate.payload_keys", type, fields.join(), keys.join()),
      );
    }
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
    database.exec(options);
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
      const hash = new HashStream();
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
      const hash = new HashStream();
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

  // The cache over `overflow_bytes` in open OPFS files, and the sink of hello.
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
    // The open databases, by name.
    readonly #connections = new Map<string, SqliteDatabase>();
    // The databases the server holds that this side does not, until loaded.
    readonly #unloaded = new Set<string>();
    // The forwarded lines not yet answered.
    readonly #flights = new Map<lines.Line, FlightRecord>();
    // The cache files forwarded lines still read, with their counts.
    readonly #holds = new Map<string, number>();
    // The databases the running transaction began, in order.
    #joined: SqliteDatabase[] | undefined = undefined;
    // The cache files the running transaction stopped naming.
    #unlinks = new Set<string>();
    // The lines of the running transaction, emitted after its commit.
    #pending: Forward[] = [];
    // The function that takes each forwarded line.
    #forward: ((line: lines.Line) => void) | undefined = undefined;
    // Whether forwarded lines use full names.
    #full = false;

    // Takes the initialized module, the installed pool, the cache, the root.
    constructor(
      sqlite3: SqliteModule,
      pool: SqlitePool,
      cache: CacheFiles,
      root: string,
      overflow_bytes: number,
      compact_turns: number,
    ) {
      this.#sqlite = sqlite3;
      this.#pool = pool;
      this.#cache = cache;
      this.#slots = pool_of(cache);
      this.#root = root;
      this.#overflow_bytes = overflow_bytes;
      this.#compact_turns = compact_turns;
    }

    // Opens `<root>/<name>.sqlite`, applying the schema. Returns its `seq`.
    db_open(name: string): number {
      name_check(name);
      this.#loaded_check(name);
      if (this.#connections.has(name)) {
        throw new Error(i18n("substrate.db_open", name));
      }
      if (!this.#file_exists(name)) {
        throw new Error(i18n("substrate.db_absent", name));
      }
      return this.#database_open(name, constants.open_write);
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

    // Creates and opens a new database at `seq` 0 and forwards it.
    db_create(name: string): void {
      name_check(name);
      this.#loaded_check(name);
      this.#forward_live("db.create");
      if (this.#file_exists(name)) {
        throw new Error(i18n("substrate.db_exists", name));
      }
      try {
        this.#database_open(name, constants.open_create);
      } catch (error) {
        this.#pool.unlink(this.#path_find(name));
        throw error;
      }
      this.#forward_emit(
        this.#forward_make(
          "db.create",
          name,
          0,
          { db: name },
          undefined,
          [],
          [],
        ),
      );
    }

    // Closes and deletes a database and its cache files, and forwards it.
    db_drop(name: string): void {
      const since = seq_read(this.#connection_get(name));
      this.#forward_live("db.drop");
      this.#file_remove(name);
      this.#forward_emit(
        this.#forward_make(
          "db.drop",
          name,
          since,
          { db: name },
          undefined,
          [],
          [],
        ),
      );
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
      return { data: data === null ? hex : data, size, sha256: hex };
    }

    // Writes bytes, or moves a cache handle's file. Returns the row and `seq`.
    kv_put(
      ref: lines.KvRef,
      data: Uint8Array | string,
      db?: string,
    ): { row: lines.KvRow; seq: number } {
      const [name, key] = ref_resolve(ref, db);
      const database = this.#connection_get(name);
      return this.transaction_run(() =>
        this.#value_put(name, database, key, data),
      );
    }

    // Deletes the row, its cache file when no row names it. Returns `seq`.
    kv_delete(ref: lines.KvRef, db?: string): number {
      const [name, key] = ref_resolve(ref, db);
      const database = this.#connection_get(name);
      return this.transaction_run(() =>
        this.#value_delete(name, database, key),
      );
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
        if (!named.has(name) && !this.#holds.has(name)) {
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

    // Writes version head plus one, moves the head, returns ref and `seq`.
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
          this.#threshold_compact(name, database, scene);
        }
        return this.#turn_add(name, database, scene, role, text);
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

    // Replaces turns 1 to `through` with one summary turn at `n` 1.
    turn_compact(
      scene: lines.DocRef,
      through: number,
      summary: string,
    ): number {
      if (through < 1) {
        throw new Error(i18n("substrate.through_bad", through));
      }
      const name = scene_database(scene);
      const database = this.#connection_get(name);
      return this.transaction_run(() =>
        this.#turns_compact(name, database, scene, through, summary),
      );
    }

    // Runs the statements in order, in the running transaction.
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[] {
      const database = this.#connection_get(db);
      return this.transaction_run(() =>
        this.#statements_run(db, database, statements),
      );
    }

    // The serialized bytes of a database, and its `seq`.
    db_snapshot(db: string): { data: Uint8Array; seq: number } {
      const database = this.#connection_get(db);
      return this.transaction_run(() => {
        this.#transaction_join(database);
        return {
          data: this.#sqlite.capi.sqlite3_js_db_export(database.pointer),
          seq: seq_read(database),
        };
      });
    }

    // Replaces a database by snapshot bytes or a cache handle. Returns `seq`.
    db_restore(db: string, data: Uint8Array | string): number {
      return this.#file_load(db, data);
    }

    // Applies one forwarded operation when `since` is the database's `seq`.
    operation_apply(
      type: string,
      since: number,
      payload: { [key: string]: unknown },
    ): number {
      if (!Object.hasOwn(constants.operation_fields, type)) {
        throw new Error(i18n("substrate.operation_type", type));
      }
      fields_check(type, payload, constants.operation_fields[type]);
      const appliers: { [type: string]: () => number } = {
        // `k` the external ref, `data` bytes or a cache handle.
        "kv.put": () => {
          const k = payload.k as string;
          const data = payload.data as Uint8Array | string;
          return this.#since_apply(type, since, ref_database(k), () =>
            this.kv_put(k, data),
          );
        },
        // `k` the external ref.
        "kv.delete": () => {
          const k = payload.k as string;
          return this.#since_apply(type, since, ref_database(k), () =>
            this.kv_delete(k),
          );
        },
        // `db`, `id` and `body`, the document encoded.
        "doc.put": () => {
          const db = payload.db as string;
          return this.#since_apply(type, since, db, () =>
            this.doc_put(
              db,
              payload.id as string,
              payload.body as lines.Document,
            ),
          );
        },
        // `db`, which has `seq` 0 before it exists and after.
        "db.create": () => {
          const db = payload.db as string;
          since_check(type, since, 0, db);
          this.db_create(db);
          return this.seq_get(db);
        },
        // `db`. A database that no longer exists has `seq` 0.
        "db.drop": () => {
          const db = payload.db as string;
          since_check(type, since, this.seq_get(db), db);
          this.db_drop(db);
          return 0;
        },
        // `scene`, `role` and `content`, applied as it is, never compacting.
        "turn.append": () => {
          const scene = payload.scene as string;
          const name = scene_database(scene);
          return this.#since_apply(type, since, name, () =>
            this.#turn_add(
              name,
              this.#connection_get(name),
              scene,
              payload.role as provider.Role,
              json_canonical(payload.content),
            ),
          );
        },
        // `scene`, `through` and `summary`.
        "turn.compact": () => {
          const scene = payload.scene as string;
          return this.#since_apply(type, since, scene_database(scene), () =>
            this.turn_compact(
              scene,
              payload.through as number,
              payload.summary as string,
            ),
          );
        },
        // `db` and `statements`, each exactly `sql` and `params`.
        "sql.run": () => {
          const db = payload.db as string;
          const statements = payload.statements as lines.SqlStatement[];
          for (const statement of statements) {
            fields_check(type, statement, constants.statement_fields);
          }
          return this.#since_apply(type, since, db, () =>
            this.sql_run(db, statements),
          );
        },
      };
      return appliers[type]();
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
      for (const forward of pending) {
        this.#forward_emit(forward);
      }
      return result;
    }

    // Sets the one function that takes each forwarded line, and its form.
    forward_set(fn: (line: lines.Line) => void, full: boolean): void {
      if (this.#forward !== undefined) {
        throw new Error(i18n("substrate.forward_twice"));
      }
      this.#forward = fn;
      this.#full = full;
    }

    // The streaming sink of the decoder, the cache this store was given.
    sink(): jslb.BlobSink {
      return this.#cache;
    }

    // Registers the handlers of the lines the UI thread submits, version 0.
    handlers_register(register: HandlerRegister): void {
      for (const [type, fn] of Object.entries(this.#handlers_make())) {
        register(type, 0, fn);
      }
    }

    // The `seq` of an open database.
    seq_get(db: string): number {
      return seq_read(this.#connection_get(db));
    }

    // Takes the reply to a forwarded line: checks its `seq`, frees its holds.
    forward_done(line: lines.Line, reply: lines.Line): void {
      const record = this.#flights.get(line);
      if (record === undefined) {
        throw new Error(
          i18n("substrate.forward_unknown", jslb.field_get(line[0], "type")),
        );
      }
      if (!constants.seqless_types.includes(record.type)) {
        const seq = jslb.payload_of(reply).seq;
        const due = record.since + 1;
        if (seq !== due) {
          throw new Error(
            i18n("substrate.reply_desync", record.type, seq, due, record.db),
          );
        }
      }
      this.#flights.delete(line);
      this.#holds_drop(record.names);
      this.#cache_prune(new Set(record.names));
    }

    // Measures each open database and their total against the soft limit.
    db_stats(soft_bytes: number): StoreStats {
      const databases = this.db_list().map((name) => this.#stats_read(name));
      let total_bytes = 0;
      for (const stats of databases) {
        total_bytes += stats.bytes;
      }
      return {
        databases,
        total_bytes,
        soft_bytes,
        over: total_bytes > soft_bytes,
      };
    }

    // Runs `VACUUM`, which changes no content nor `seq`, forwarding nothing.
    db_compact(db: string): CompactBytes {
      const database = this.#connection_get(db);
      if (this.#in_transaction(database)) {
        throw new Error(i18n("substrate.db_busy", db));
      }
      const before = this.#stats_read(db).bytes;
      database.exec({ sql: "VACUUM" });
      return { before, after: this.#stats_read(db).bytes };
    }

    // Deletes this side's copy, which the server keeps, until `db_load`.
    db_unload(db: string): void {
      this.#connection_get(db);
      this.#flights_check(db);
      this.#file_remove(db);
      this.#unloaded.add(db);
    }

    // Opens the server's snapshot of a database as at start. Returns `seq`.
    db_load(db: string, data: Uint8Array | string): number {
      this.#flights_check(db);
      return this.#file_load(db, data);
    }

    // At start, opens what matches the server and returns what to replace.
    start_open(server: { [db: string]: number }): string[] {
      const held = this.#files_held();
      const replace: string[] = [];
      for (const name of held) {
        const seq = this.db_open(name);
        if (!Object.hasOwn(server, name)) {
          this.#file_remove(name);
        } else if (seq !== server[name]) {
          this.db_close(name);
          this.#unloaded.add(name);
          replace.push(name);
        }
      }
      for (const name of Object.keys(server)) {
        if (!held.includes(name)) {
          this.#unloaded.add(name);
        }
      }
      return replace;
    }

    // Whether this side holds the bytes of a value, in its row or a file.
    kv_held(ref: lines.KvRef, db?: string): boolean {
      const value = this.kv_get(ref, db);
      return (
        typeof value.data !== "string" || this.#slots.name_held(value.data)
      );
    }

    // Puts back the file of a cached value from bytes with the row's digest.
    cache_fill(
      ref: lines.KvRef,
      data: Uint8Array | string,
      db?: string,
    ): void {
      const value = this.kv_get(ref, db);
      const handle = typeof data === "string";
      const sha256 = handle
        ? this.#slots.handle_hash(data)
        : utility.sha256_hex(data);
      if (sha256 !== value.sha256) {
        throw new Error(
          i18n("substrate.fill_desync", ref, sha256, value.sha256),
        );
      }
      if (handle) {
        this.#slots.handle_store(data, sha256);
      } else {
        this.#slots.bytes_store(sha256, data);
      }
    }

    // Frees a database's cached values by key until they fit the budget.
    cache_evict(db: string, keep: readonly string[], budget: number): number {
      const database = this.#connection_get(db);
      // The names that other databases' rows and the kept refs hold stay.
      const kept = this.#hashes_named(db);
      for (const ref of keep) {
        const parts = ref_split(ref);
        if (parts.db === db) {
          const rows = rows_select(
            database,
            "SELECT sha256 FROM _kv WHERE key = ? AND data IS NULL",
            [parts.key],
          );
          for (const row of rows) {
            kept.add(hex_of(row[0] as Uint8Array));
          }
        }
      }
      const cached = rows_select(
        database,
        "SELECT sha256, size FROM _kv WHERE data IS NULL ORDER BY key",
        [],
      );
      const sizes = new Map<string, number>();
      for (const row of cached) {
        const name = hex_of(row[0] as Uint8Array);
        if (this.#slots.name_held(name)) {
          sizes.set(name, row[1] as number);
        }
      }
      let held = 0;
      for (const size of sizes.values()) {
        held += size;
      }
      let freed = 0;
      for (const [name, size] of sizes) {
        if (held <= budget) {
          break;
        }
        if (!kept.has(name) && !this.#holds.has(name)) {
          this.#slots.name_remove(name);
          held -= size;
          freed += 1;
        }
      }
      return freed;
    }

    // Opens a database file with the flags, applying the schema.
    #database_open(name: string, flags: string): number {
      const database = new this.#pool.OpfsSAHPoolDb({
        filename: this.#path_find(name),
        flags,
      });
      try {
        database.exec({ sql: "PRAGMA foreign_keys = ON" });
        this.#schema_apply(database);
        const seq = seq_read(database);
        this.#connections.set(name, database);
        return seq;
      } catch (error) {
        database.close();
        throw error;
      }
    }

    // Throws naming `db_load` when the database is unloaded.
    #loaded_check(name: string): void {
      if (this.#unloaded.has(name)) {
        throw new Error(i18n("substrate.db_unloaded", name));
      }
    }

    // The connection of an open database. Any other database throws.
    #connection_get(name: string): SqliteDatabase {
      this.#loaded_check(name);
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

    // Checks snapshot bytes in a file of their own, then replaces the copy.
    #file_load(db: string, data: Uint8Array | string): number {
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
      this.#unloaded.delete(db);
      return this.#database_open(db, constants.open_write);
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
        for (const forward of this.#pending) {
          this.#holds_drop(forward.record.names);
        }
        this.#pending = [];
        throw error;
      } finally {
        this.#joined = undefined;
      }
    }

    // Writes a value inside the transaction, forwarding it when it changed.
    #value_put(
      name: string,
      database: SqliteDatabase,
      key: string,
      data: Uint8Array | string,
    ): { row: lines.KvRow; seq: number } {
      this.#transaction_join(database);
      const since = seq_read(database);
      const written = this.#row_write(database, key, data);
      const { row } = written;
      if (!written.changed) {
        return { row, seq: since };
      }
      const seq = seq_bump(database);
      // A value in its row goes as a copy, as the caller may move its bytes.
      const blob = written.cached
        ? jslb.blob_make(row.sha256, undefined, {}, row.size)
        : jslb.blob_make((data as Uint8Array).slice());
      this.#pending.push(
        this.#forward_make(
          "kv.put",
          name,
          since,
          {},
          `/${name}/${key}`,
          [blob],
          written.cached ? [row.sha256] : [],
        ),
      );
      return { row, seq };
    }

    // Deletes a row inside the transaction, forwarding it when it existed.
    #value_delete(
      name: string,
      database: SqliteDatabase,
      key: string,
    ): number {
      this.#transaction_join(database);
      const since = seq_read(database);
      const old = rows_select(
        database,
        "SELECT sha256, data IS NULL FROM _kv WHERE key = ?",
        [key],
      );
      if (old.length === 0) {
        return since;
      }
      database.exec({ sql: "DELETE FROM _kv WHERE key = ?", bind: [key] });
      if (old[0][1] === 1) {
        this.#unlinks.add(hex_of(old[0][0] as Uint8Array));
      }
      const seq = seq_bump(database);
      this.#pending.push(
        this.#forward_make(
          "kv.delete",
          name,
          since,
          {},
          `/${name}/${key}`,
          [],
          [],
        ),
      );
      return seq;
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

    // Writes the next version of a document, moves its head, forwards it.
    #document_put(
      db: string,
      database: SqliteDatabase,
      id: string,
      data: Uint8Array,
      text: string,
    ): lines.DocPutReply {
      this.#transaction_join(database);
      const since = seq_read(database);
      const rows = rows_select(
        database,
        "SELECT version FROM _head WHERE id = ?",
        [id],
      );
      const version = rows.length === 0 ? 1 : (rows[0][0] as number) + 1;
      const key = `${id}/${String(version)}`;
      const exists = rows_select(
        database,
        "SELECT 1 FROM _kv WHERE key = ?",
        [key],
      );
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
      const seq = seq_bump(database);
      const body = JSON.parse(text) as lines.Document;
      this.#pending.push(
        this.#forward_make(
          "doc.put",
          db,
          since,
          { db, id, body },
          undefined,
          [],
          [],
        ),
      );
      return { ref: `/${db}/${key}`, seq };
    }

    // Compacts the scene's turns 1 to its last once they are `compact_turns`.
    #threshold_compact(
      name: string,
      database: SqliteDatabase,
      scene: string,
    ): void {
      this.#transaction_join(database);
      const [count, last] = rows_select(
        database,
        "SELECT COUNT(*), MAX(n) FROM _turn WHERE scene = ?",
        [scene],
      )[0] as [number, number];
      if (count >= this.#compact_turns) {
        const summary = i18n("substrate.turns_compacted", last, count);
        this.#turns_compact(name, database, scene, last, summary);
      }
    }

    // Inserts a turn after the last of its scene and forwards it.
    #turn_add(
      name: string,
      database: SqliteDatabase,
      scene: string,
      role: provider.Role,
      text: string,
    ): lines.TurnAppendReply {
      this.#transaction_join(database);
      const since = seq_read(database);
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
      const seq = seq_bump(database);
      const content = JSON.parse(text) as provider.ChatMessage;
      this.#pending.push(
        this.#forward_make(
          "turn.append",
          name,
          since,
          { scene, role, content },
          undefined,
          [],
          [],
        ),
      );
      return { n, seq };
    }

    // Deletes turns 1 to `through`, inserts the summary at 1, forwards it.
    #turns_compact(
      name: string,
      database: SqliteDatabase,
      scene: string,
      through: number,
      summary: string,
    ): number {
      this.#transaction_join(database);
      const since = seq_read(database);
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
      const seq = seq_bump(database);
      this.#pending.push(
        this.#forward_make(
          "turn.compact",
          name,
          since,
          { scene, through, summary },
          undefined,
          [],
          [],
        ),
      );
      return seq;
    }

    // Runs the statements, counting a change of a row or of the schema.
    #statements_run(
      db: string,
      database: SqliteDatabase,
      statements: lines.SqlStatement[],
    ): lines.SqlResult[] {
      this.#transaction_join(database);
      const since = seq_read(database);
      const changes = database.changes(true);
      const schema = schema_read(database);
      const results = statements.map((statement) =>
        statement_run(database, statement),
      );
      if (
        database.changes(true) !== changes ||
        schema_read(database) !== schema
      ) {
        seq_bump(database);
        this.#pending.push(
          this.#forward_make(
            "sql.run",
            db,
            since,
            { db, statements: structuredClone(statements) },
            undefined,
            [],
            [],
          ),
        );
      }
      return results;
    }

    // Runs a forwarded operation in a transaction when `since` is the `seq`.
    #since_apply(
      type: string,
      since: number,
      db: string,
      fn: () => unknown,
    ): number {
      const database = this.#connection_get(db);
      return this.transaction_run(() => {
        this.#transaction_join(database);
        since_check(type, since, seq_read(database), db);
        fn();
        return seq_read(database);
      });
    }

    // The function that takes forwarded lines. Unset, it throws.
    #forward_live(type: string): (line: lines.Line) => void {
      const fn = this.#forward;
      if (fn === undefined) {
        throw new Error(i18n("substrate.forward_unset", type));
      }
      return fn;
    }

    // Builds the forwarded line of an operation and holds its cache files.
    #forward_make(
      type: string,
      db: string,
      since: number,
      fields: { [key: string]: unknown },
      key: string | undefined,
      blobs: lines.BlobHeader[],
      names: string[],
    ): Forward {
      this.#forward_live(type);
      const header = jslb.header_make(type, { key, full: this.#full });
      const line = jslb.line_make(header, blobs, { ...fields, since });
      for (const name of names) {
        const count = this.#holds.get(name);
        this.#holds.set(name, count === undefined ? 1 : count + 1);
      }
      return { line, record: { type, db, since, names } };
    }

    // Hands a forwarded line on, recorded until its reply comes.
    #forward_emit(forward: Forward): void {
      const fn = this.#forward_live(forward.record.type);
      this.#flights.set(forward.line, forward.record);
      fn(forward.line);
    }

    // Lets go of the cache files a forwarded line held.
    #holds_drop(names: string[]): void {
      for (const name of names) {
        const count = this.#holds.get(name) as number;
        if (count === 1) {
          this.#holds.delete(name);
        } else {
          this.#holds.set(name, count - 1);
        }
      }
    }

    // Throws when forwarded lines of the database wait for their replies.
    #flights_check(db: string): void {
      let count = 0;
      for (const record of this.#flights.values()) {
        if (record.db === db) {
          count += 1;
        }
      }
      if (count > 0) {
        throw new Error(i18n("substrate.forward_pending", db, count));
      }
    }

    // Removes the cache files of the names that no row and no line holds.
    #cache_prune(names: Set<string>): void {
      if (names.size === 0) {
        return;
      }
      const named = this.#hashes_named();
      for (const name of [...names].sort()) {
        if (!named.has(name) && !this.#holds.has(name)) {
          this.#slots.name_remove(name);
        }
      }
    }

    // The cache names the rows of each database file but the skipped one hold.
    #hashes_named(skip?: string): Set<string> {
      const named = new Set<string>();
      for (const name of this.#files_held()) {
        if (name === skip) {
          continue;
        }
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

    // The measure of an open database: pages, free pages, cached values.
    #stats_read(name: string): DatabaseStats {
      const database = this.#connection_get(name);
      const page_size = select_number(database, "PRAGMA page_size");
      const pages = select_number(database, "PRAGMA page_count");
      const free_pages = select_number(database, "PRAGMA freelist_count");
      const cache_bytes = select_number(
        database,
        "SELECT COALESCE(SUM(size), 0) FROM _kv WHERE data IS NULL",
      );
      return {
        name,
        bytes: pages * page_size + cache_bytes,
        free_bytes: free_pages * page_size,
        cache_bytes,
        seq: seq_read(database),
      };
    }

    // The bytes of a value, read from the cache when it is held there.
    #value_bytes(value: KvValue): Uint8Array {
      return typeof value.data === "string"
        ? this.#slots.handle_bytes(value.data)
        : value.data;
    }

    // The handlers of the lines the UI thread submits, by type.
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
          const blob = line[1] as lines.BlobHeader;
          const data = jslb.field_get(blob, "data") as Uint8Array | string;
          const written = this.kv_put(ref_of(line), data);
          return dispatch.reply_make(line, {
            sha256: written.row.sha256,
            seq: written.seq,
          });
        },
        // Deletes the ref's row.
        "kv.delete": (line) =>
          dispatch.reply_make(line, { seq: this.kv_delete(ref_of(line)) }),
        // Lists the rows under a prefix.
        "kv.list": (line) => {
          const { db, prefix } = payload_read<lines.KvList>(line);
          return dispatch.reply_make(line, { keys: this.kv_list(db, prefix) });
        },
        // Writes a document.
        "doc.put": (line) => {
          const { db, id, body } = payload_read<lines.DocPut>(line);
          return dispatch.reply_make(line, { ...this.doc_put(db, id, body) });
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
        // Answers a database's digest and `seq`, its file as blob 1.
        "db.snapshot": (line) => {
          const { db } = payload_read<lines.DbName>(line);
          const { data, seq } = this.db_snapshot(db);
          const sha256 = utility.sha256_hex(data);
          return dispatch.reply_make(line, { sha256, seq }, [
            jslb.blob_make(data),
          ]);
        },
        // Appends a turn.
        "turn.append": (line) => {
          const { scene, role, content } =
            payload_read<lines.TurnAppend>(line);
          return dispatch.reply_make(line, {
            ...this.turn_append(scene, role, content),
          });
        },
        // Compacts a scene's turns.
        "turn.compact": (line) => {
          const { scene, through, summary } =
            payload_read<lines.TurnCompact>(line);
          return dispatch.reply_make(line, {
            seq: this.turn_compact(scene, through, summary),
          });
        },
        // Runs statements, the reply carrying the `seq` after them.
        "sql.run": (line) => {
          const { db, statements } = payload_read<lines.SqlRun>(line);
          const results = this.sql_run(db, statements);
          return dispatch.reply_make(line, { results, seq: this.seq_get(db) });
        },
      };
    }
  }
}
Object.freeze(substrate);
