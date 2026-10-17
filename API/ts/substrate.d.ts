declare namespace substrate {
  // The bytes of a value, or the cache handle when over `overflow_bytes`.
  interface KvValue {
    data: Uint8Array | string;
    size: number;
    sha256: lines.Sha256;
  }

  // The store API, shared by the WASM thread's `Store` and the AI
  // thread's `StoreProxy`. Names and parameters are those of
  // API/python/substrate.pyi; every method returns a promise here.
  interface StoreApi {
    db_open(name: string, kind: lines.DbOpen["kind"]): Promise<number>;
    db_close(name: string): Promise<void>;
    db_list(): Promise<string[]>;
    db_attach(universe: string, region: string): Promise<void>;
    db_detach(universe: string): Promise<void>;
    kv_get(db: string, key: string): Promise<KvValue>;
    kv_put(db: string, key: string, data: Uint8Array | string): Promise<lines.KvRow>;
    kv_delete(db: string, key: string): Promise<number>;
    kv_list(db: string, prefix: string): Promise<lines.KvRow[]>;
    kv_check(db: string): Promise<number>;
    doc_get(ref: lines.DocRef): Promise<unknown>;
    doc_put(path: string, body: unknown): Promise<lines.DocPutReply>;
    doc_head(path: string): Promise<lines.DocRef>;
    turn_append(scene: lines.DocRef, role: provider.Role, content: provider.ChatMessage): Promise<number>;
    turn_list(scene: lines.DocRef): Promise<lines.TurnRow[]>;
    turn_compact(scene: lines.DocRef, through: number, summary: string): Promise<void>;
    sql_run(db: string, statements: lines.SqlStatement[]): Promise<lines.SqlResult[]>;
    db_snapshot(db: string): Promise<{ data: Uint8Array; seq: number }>;
    db_restore(db: string, data: Uint8Array | string): Promise<number>;
    sync_pull(db: string, since: number): Promise<lines.SyncRows>;
    sync_apply(db: string, rows: lines.SyncRows, blobs: Map<lines.Sha256, Uint8Array | string>): Promise<number>;
  }

  // Splits a ref or path into database, kind, name and version.
  function ref_split(ref: string): { db: string; kind: string; name: string; version?: number };

  // On the WASM thread: sqlite3.wasm on the OPFS SAH pool VFS under
  // `root`, the OPFS cache directory beside it. Each handler is one
  // transaction. The methods are synchronous inside; the promise shape
  // is the shared interface.
  class Store implements StoreApi {
    constructor(sqlite3: unknown, root: string, overflow_bytes: number);
    db_open(name: string, kind: lines.DbOpen["kind"]): Promise<number>;
    db_close(name: string): Promise<void>;
    db_list(): Promise<string[]>;
    db_attach(universe: string, region: string): Promise<void>;
    db_detach(universe: string): Promise<void>;
    kv_get(db: string, key: string): Promise<KvValue>;
    kv_put(db: string, key: string, data: Uint8Array | string): Promise<lines.KvRow>;
    kv_delete(db: string, key: string): Promise<number>;
    kv_list(db: string, prefix: string): Promise<lines.KvRow[]>;
    kv_check(db: string): Promise<number>;
    doc_get(ref: lines.DocRef): Promise<unknown>;
    doc_put(path: string, body: unknown): Promise<lines.DocPutReply>;
    doc_head(path: string): Promise<lines.DocRef>;
    turn_append(scene: lines.DocRef, role: provider.Role, content: provider.ChatMessage): Promise<number>;
    turn_list(scene: lines.DocRef): Promise<lines.TurnRow[]>;
    turn_compact(scene: lines.DocRef, through: number, summary: string): Promise<void>;
    sql_run(db: string, statements: lines.SqlStatement[]): Promise<lines.SqlResult[]>;
    db_snapshot(db: string): Promise<{ data: Uint8Array; seq: number }>;
    db_restore(db: string, data: Uint8Array | string): Promise<number>;
    sync_pull(db: string, since: number): Promise<lines.SyncRows>;
    sync_apply(db: string, rows: lines.SyncRows, blobs: Map<lines.Sha256, Uint8Array | string>): Promise<number>;
    // The streaming sink: a cache file by handle, closed with its hash.
    cache_open(): string;
    cache_append(handle: string, data: Uint8Array): void;
    cache_close(handle: string): lines.Sha256;
    // Registers every `db.*`, `kv.*`, `doc.*`, `sql.*`, `sync.*` and
    // `cache.*` handler on the WASM thread's dispatcher.
    handlers_register(): void;
  }

  // On the AI thread: the same API, each method one task to WASM.
  class StoreProxy implements StoreApi {
    constructor(tasks: queue.TaskQueue);
    db_open(name: string, kind: lines.DbOpen["kind"]): Promise<number>;
    db_close(name: string): Promise<void>;
    db_list(): Promise<string[]>;
    db_attach(universe: string, region: string): Promise<void>;
    db_detach(universe: string): Promise<void>;
    kv_get(db: string, key: string): Promise<KvValue>;
    kv_put(db: string, key: string, data: Uint8Array | string): Promise<lines.KvRow>;
    kv_delete(db: string, key: string): Promise<number>;
    kv_list(db: string, prefix: string): Promise<lines.KvRow[]>;
    kv_check(db: string): Promise<number>;
    doc_get(ref: lines.DocRef): Promise<unknown>;
    doc_put(path: string, body: unknown): Promise<lines.DocPutReply>;
    doc_head(path: string): Promise<lines.DocRef>;
    turn_append(scene: lines.DocRef, role: provider.Role, content: provider.ChatMessage): Promise<number>;
    turn_list(scene: lines.DocRef): Promise<lines.TurnRow[]>;
    turn_compact(scene: lines.DocRef, through: number, summary: string): Promise<void>;
    sql_run(db: string, statements: lines.SqlStatement[]): Promise<lines.SqlResult[]>;
    db_snapshot(db: string): Promise<{ data: Uint8Array; seq: number }>;
    db_restore(db: string, data: Uint8Array | string): Promise<number>;
    sync_pull(db: string, since: number): Promise<lines.SyncRows>;
    sync_apply(db: string, rows: lines.SyncRows, blobs: Map<lines.Sha256, Uint8Array | string>): Promise<number>;
    // The decoder's sink on the AI thread, posting `cache.*` to WASM.
    sink(): jslb.BlobSink;
  }
}
