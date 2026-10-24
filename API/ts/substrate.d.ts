// The store on the AI thread: sqlite3.wasm on the OPFS SAH pool VFS under a
// root, and the OPFS cache files beside it, which hold the values over
// `overflow_bytes` by their digest. Every method is synchronous and runs
// inside the task that called it. Names and parameters follow
// API/python/substrate.pyi, the server's store, except where each store does
// its own maintenance: only this one compacts turns, inside `turn_append` at
// the threshold and by `turn_compact`, which the AI's scripts call through
// `engine.store`. Nothing of a compaction goes to the server.
//
// Each modifying operation goes to the server as one push line of the same
// type, built in the form `settings.names_full()` picks and given to
// `tasks.line_notify(line, "server")`: `db.create` and `db.drop` once done,
// the others once the outermost transaction that ran them commits, in order.
// A `kv.put` carries its value's bytes as blob 1, read out of the cache file
// when the value is one, never a cache handle. An operation that changes
// nothing sends nothing, and a rolled back transaction sends nothing. Nothing
// waits for, numbers or checks what the server does with it: the sync is
// lossy by design.
//
// A value whose row names a cache file this side does not hold is lost: its
// row stays, `kv_list` lists it, `kv_put` replaces it, `kv_check` counts
// nothing for it, and `kv_get` throws `substrate.file_lost`. `db_snapshot`
// names only the cache files this side holds, and `db_restore` tolerates
// such rows, so a database restored without some of its cache files works
// but for those values. A cache handle is a name this store's cache holds or
// a blob its sink finished: `db_snapshot` gives names, and `db_restore` takes
// either, or the bytes, keeping each file under the digest of its bytes.
//
// The handlers of the store's lines: the ui-ai requests of `lines.d.ts`,
// answered with their replies, and the server's pushes `db.restore` and
// `db.file`. A `db.restore` waits for its `files` lines of `db.file`, then
// `db_restore` runs, at once when `files` is 0. A second `db.restore` while
// one waits throws `substrate.restore_pending`, and a `db.file` with no
// restore of its database waiting throws `substrate.file_unexpected`.
//
// The schema's triggers raise the name of a string of the strings table, as
// `agent.content_ambiguous`: a statement that fails with such a message
// throws that string, the SQLite error as its `cause`.

declare namespace substrate {
  // A file of the cache held open for synchronous access, as OPFS gives it.
  interface SlotHandle {
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
  interface ExecOptions {
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
  interface SqliteStatement {
    // The number of parameters the statement takes.
    readonly parameterCount: number;
    // Frees the statement.
    finalize(): unknown;
  }

  // A database of the pool's class `OpfsSAHPoolDb`, the parts used here.
  interface SqliteDatabase {
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
  interface SqliteModule {
    // The C functions used here.
    capi: {
      sqlite3_js_db_export(pointer: number): Uint8Array;
      sqlite3_get_autocommit(pointer: number): number;
    };
  }

  // The OPFS SAH pool `installOpfsSAHPoolVfs` resolves to, parts used.
  interface SqlitePool {
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
  interface KvValue {
    data: Uint8Array | string;
    size: number;
    sha256: lines.Sha256;
  }

  interface TurnRow {
    scene: lines.DocRef;
    n: number;
    role: provider.Role;
    content: provider.ChatMessage;
  }

  interface RefParts {
    db?: string;
    key: string;
    version?: number;
  }

  // A database as one blob: its file and the cache files its rows name.
  interface DbImage {
    data: Uint8Array;
    files: string[];
  }

  // What the store gives each committed operation to: the thread's queue.
  interface Notifier {
    line_notify(line: lines.Line, owner?: queue.ThreadName): void;
  }

  // Splits a `Key-Value-Ref` or `Document-Ref`. A bad ref throws.
  function ref_split(ref: string): RefParts;

  // Moves a document's reference strings into its headers 1 on.
  function doc_encode(normal: { [key: string]: unknown }): lines.Document;

  // Puts the reference strings back. `doc_decode(doc_encode(x))` is `x`.
  function doc_decode(encoded: lines.Document): { [key: string]: unknown };

  // The cache files, opened by the boot, and the decoder's streaming sink.
  class CacheFiles implements jslb.BlobSink {
    constructor(slots: SlotHandle[]);
    slot_add(slot: SlotHandle): void;
    slots_free(): number;
    sink_open(header: lines.BlobHeader): string;
    sink_append(handle: string, data: Uint8Array): void;
    sink_close(handle: string): lines.Sha256;
    cache_read(handle: string, offset: number, length: number): Uint8Array;
  }

  class Store {
    constructor(
      sqlite3: SqliteModule,
      pool: SqlitePool,
      cache: CacheFiles,
      root: string,
      overflow_bytes: number,
      compact_turns: number,
      tasks: Notifier,
    );
    db_open(name: string): void;
    db_close(name: string): void;
    db_list(): string[];
    db_create(name: string): void;
    db_drop(name: string): void;
    kv_get(ref: lines.KvRef, db?: string): KvValue;
    kv_put(
      ref: lines.KvRef,
      data: Uint8Array | string,
      db?: string,
    ): lines.KvRow;
    kv_delete(ref: lines.KvRef, db?: string): void;
    kv_list(db: string, prefix: string): lines.KvRow[];
    // Removes the cache files no row names. Returns their count.
    kv_check(db: string): number;
    doc_get(ref: lines.DocRef, db?: string): lines.Document;
    doc_put(db: string, id: string, body: lines.Document): lines.DocPutReply;
    doc_head(db: string, id: string): lines.DocRef;
    // A `user` turn on a scene of `compact_turns` turns compacts them first.
    turn_append(
      scene: lines.DocRef,
      role: provider.Role,
      content: provider.ChatMessage,
    ): lines.TurnAppendReply;
    turn_list(scene: lines.DocRef): TurnRow[];
    // Replaces turns 1 to `through` by one summary turn at 1, this side only.
    turn_compact(scene: lines.DocRef, through: number, summary: string): void;
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[];
    // The file and the handles of the cache files its rows name and it holds.
    db_snapshot(db: string): DbImage;
    // Replaces the database by the file and keeps the cache files given.
    db_restore(
      db: string,
      data: Uint8Array | string,
      files: (Uint8Array | string)[],
    ): void;
    transaction_run<T>(fn: () => T): T;
    // The streaming sink of the decoder: the cache this store was given.
    sink(): jslb.BlobSink;
    // Registers the handlers of the store's lines on this thread.
    handlers_register(
      register: (type: string, version: number, fn: dispatch.Handler) => void,
    ): void;
  }
}
