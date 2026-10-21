declare namespace substrate {
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

  // Splits a Key-Value-Ref or Document-Ref. A bad ref throws.
  function ref_split(ref: string): RefParts;

  // Moves a document's reference strings into its headers 1 on,
  // sharing equal strings, and leaves `{"$ref": n}` behind.
  function doc_encode(normal: { [key: string]: unknown }): lines.Document;

  // Puts the reference strings back. `doc_decode(doc_encode(x))` is `x`.
  function doc_decode(encoded: lines.Document): { [key: string]: unknown };

  // The store on the AI thread: sqlite3.wasm on the OPFS SAH pool VFS
  // under `root`, the OPFS cache directory beside it. Names and
  // parameters are those of API/python/substrate.pyi; every method is
  // synchronous and runs inside the task that called it.
  class Store {
    constructor(
      sqlite3: unknown,
      root: string,
      overflow_bytes: number,
      compact_turns: number
    );
    db_open(name: string): number;
    db_close(name: string): void;
    db_list(): string[];
    db_create(name: string): void;
    db_drop(name: string): void;
    kv_get(ref: lines.KvRef, db?: string): KvValue;
    kv_put(
      ref: lines.KvRef,
      data: Uint8Array | string,
      db?: string
    ): { row: lines.KvRow; seq: number };
    kv_delete(ref: lines.KvRef, db?: string): number;
    kv_list(db: string, prefix: string): lines.KvRow[];
    kv_check(db: string): number;
    doc_get(ref: lines.DocRef, db?: string): lines.Document;
    doc_put(db: string, id: string, body: lines.Document): lines.DocPutReply;
    doc_head(db: string, id: string): lines.DocRef;
    // A `user` turn on a scene of `compact_turns` turns first compacts them.
    turn_append(
      scene: lines.DocRef,
      role: provider.Role,
      content: provider.ChatMessage
    ): lines.TurnAppendReply;
    turn_list(scene: lines.DocRef): TurnRow[];
    turn_compact(
      scene: lines.DocRef,
      through: number,
      summary: string
    ): number;
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[];
    db_snapshot(db: string): { data: Uint8Array; seq: number };
    db_restore(db: string, data: Uint8Array | string): number;
    // Whether this side holds a value's bytes, in its row or a file.
    kv_held(ref: lines.KvRef, db?: string): boolean;
    // Puts back a value's cache file from bytes with the row's digest.
    cache_fill(ref: lines.KvRef, data: Uint8Array | string, db?: string): void;
    // Frees a database's unkept cache files to the budget; their count.
    cache_evict(db: string, keep: readonly string[], budget: number): number;
    operation_apply(
      type: string,
      since: number,
      payload: { [key: string]: unknown }
    ): number;
    transaction_run<T>(fn: () => T): T;
    // The emitting side of replication: after every committed modifying
    // operation, `fn` gets the same operation as a wire line with
    // `since` set, to submit to the server, one in flight per database.
    forward_set(fn: (line: lines.Line) => void): void;
    // The streaming sink of the decoder: a cache file by handle.
    sink(): jslb.BlobSink;
    // Registers every `db.*`, `kv.*`, `doc.*`, `turn.*` and `sql.*`
    // handler on this thread's dispatcher.
    handlers_register(): void;
  }
}
