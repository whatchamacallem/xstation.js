// The catalogue of every JSLB line type on every lane. A line is one JSON
// object: header "0", blob headers "1" to "b", the payload in every other
// key. Short names on the wire, full names in debug mode; a field at its
// default is not written. Each interface below is the payload of one
// type; the comment above it gives the lane, the direction, the blobs
// and the reply. "push" means a notification the receiver never answers.
//
// type              lane     from -> to        blobs   reply
// hello             wire     SERVER -> AI      0       HelloReply
// error             any      either, r set     0       none
// kv.get            wire     AI -> SERVER      0       KvGetReply + 1
// kv.put            wire     AI -> SERVER      1       KvPutReply
// kv.delete         wire     AI -> SERVER      0       SeqReply
// kv.list           wire     AI -> SERVER      0       KvListReply
// kv.changed        wire     SERVER -> AI      0       push
// doc.get           wire     AI -> SERVER      0       DocGetReply
// doc.put           wire     AI -> SERVER      0       DocPutReply
// doc.head          wire     AI -> SERVER      0       DocHeadReply
// sync.pull         wire     AI -> SERVER      0       SyncRows
// sync.push         wire     AI -> SERVER      N       SeqReply
// db.open           wire     AI -> SERVER      0       SeqReply
// db.list           wire     AI -> SERVER      0       DbListReply
// db.snapshot       wire     AI -> SERVER      0       DbSnapshotReply + 1
// db.restore        wire     AI -> SERVER      1       DbSnapshotReply
// sql.run           wire     AI -> SERVER      0       SqlRunReply (debug)
// log.put           wire     AI -> SERVER      0       push (debug)
// log.follow        wire     AI -> SERVER      0       Empty
// log.line          wire     SERVER -> AI      0       push
// log.tail          wire     AI -> SERVER      0       LogTailReply
// console.open      wire     AI -> SERVER      0       ConsoleOpenReply
// console.input     wire     AI -> SERVER      1       push
// console.output    wire     SERVER -> AI      1       push
// console.signal    wire     AI -> SERVER      0       push
// console.close     wire     AI -> SERVER      0       ConsoleExit
// console.exit      wire     SERVER -> AI      0       push
// mcp               wire     either            0       push (JSON-RPC)
// tap.report        wire     AI -> SERVER      0       TapReportReply
// settings.put      wire     AI -> SERVER      0       Empty (debug)
// source.put        wire     AI -> SERVER      1       Sha256Reply (debug)
// system.restart    wire     AI -> SERVER      0       push; new hello
// boot.hello        ui-ai    AI -> UI          0       push
// status            ui-ai    AI -> UI          0       push
// ai.say            ui-ai    UI -> AI          0       TurnEnd
// ai.click          ui-ai    UI -> AI          0       TurnEnd
// render            ui-ai    AI -> UI          0       Empty
// media.fetch       ui-ai    AI -> UI          0       MediaReply
// media.store       ui-ai    AI -> UI          1       MediaReply
// media.bytes       ui-ai    AI -> UI          0       MediaReply + 1
// permit.ask        ui-ai    AI -> UI          0       Empty
// permit.answer     ui-ai    UI -> AI          0       push
// console.*         ui-ai    as on the wire, relayed by the AI worker
// log.put           ui-ai    UI -> AI          0       push
// fault             ui-ai    either            0       push
// wire.close        ui-ai    UI -> AI          0       Empty
// wire.reconnect    ui-ai    UI -> AI          0       BootHello
// db.open           ai-wasm  AI -> WASM        0       SeqReply
// db.close          ai-wasm  AI -> WASM        0       Empty
// db.attach         ai-wasm  AI -> WASM        0       Empty
// db.detach         ai-wasm  AI -> WASM        0       Empty
// db.snapshot       ai-wasm  AI -> WASM        0       DbSnapshotReply + 1
// db.restore        ai-wasm  AI -> WASM        1       DbSnapshotReply
// kv.get            ai-wasm  AI -> WASM        0       KvGetReply + 1
// kv.put            ai-wasm  AI -> WASM        1       KvPutReply
// kv.delete         ai-wasm  AI -> WASM        0       SeqReply
// kv.list           ai-wasm  AI -> WASM        0       KvListReply
// kv.check          ai-wasm  AI -> WASM        0       KvCheckReply
// doc.get           ai-wasm  AI -> WASM        0       DocGetReply
// doc.put           ai-wasm  AI -> WASM        0       DocPutReply
// doc.head          ai-wasm  AI -> WASM        0       DocHeadReply
// sql.run           ai-wasm  AI -> WASM        0       SqlRunReply
// sync.pull         ai-wasm  AI -> WASM        0       SyncRows
// sync.apply        ai-wasm  AI -> WASM        N       SeqReply
// cache.open        ai-wasm  AI -> WASM        0       CacheOpenReply
// cache.append      ai-wasm  AI -> WASM        1       push
// cache.close       ai-wasm  AI -> WASM        0       Sha256Reply

declare namespace lines {
  // Header "0". `t` type, `v` version, `i` id, `r` reply, `k` key,
  // `b` blobs. Full names in debug mode.
  interface LineHeader {
    t: string;
    v?: number;
    i?: number;
    r?: number;
    k?: string;
    b?: number;
  }

  // Headers "1" to "b". `s` size, `k` key, `d` the bytes or, for a blob
  // streamed to the cache, the cache handle. Other fields are the
  // handler's.
  interface BlobHeader {
    s: number;
    k?: string;
    d?: Uint8Array | string;
    [field: string]: unknown;
  }

  interface Line {
    "0": LineHeader;
    [key: string]: unknown;
  }

  // A SHA-256 is 64 lowercase hex characters everywhere in a payload.
  type Sha256 = string;

  // A Document-Ref: `<db>/<kind>/<name>/<version>`, the version a positive
  // integer. A path is the ref without its version. The database is the
  // one or two leading segments, which the fixed depth makes unambiguous.
  type DocRef = string;

  interface Empty {}

  interface SeqReply {
    seq: number;
  }

  interface Sha256Reply {
    sha256: Sha256;
  }

  // error: `message` and `stack` as text. The server exits 1 after it.
  interface ErrorLine {
    message: string;
    stack: string;
  }

  // hello: the server's request with `i` 1. `seq` per server database.
  interface Hello {
    bootstrap: string;
    sha256: Sha256;
    pid: number;
    python: string;
    sqlite: string;
    root: string;
    debug: boolean;
    settings: settings.Settings;
    seq: { [db: string]: number };
    console: { open: boolean };
    secrets: { provider_key: string };
  }

  // The AI worker's answer: the page's hash, a tab id made once per tab,
  // and `seq` per browser database, for reconciliation.
  interface HelloReply {
    sha256: Sha256;
    tab: string;
    seq: { [db: string]: number };
  }

  // kv.get: the key is the header's `k`.
  interface KvGet {
    db: string;
  }

  // Reply with the value as blob "1".
  interface KvGetReply {
    size: number;
    sha256: Sha256;
  }

  // kv.put: the key is the header's `k`; the value is blob "1", or on the
  // ai-wasm lane the cache handle of a streamed value, with no blob.
  interface KvPut {
    db: string;
    handle?: string;
  }

  interface KvPutReply {
    sha256: Sha256;
    seq: number;
  }

  interface KvDelete {
    db: string;
  }

  interface KvList {
    db: string;
    prefix: string;
  }

  interface KvRow {
    k: string;
    size: number;
    sha256: Sha256;
    seq: number;
  }

  interface KvListReply {
    keys: KvRow[];
  }

  // kv.changed: pushed by the server after any write to a replicated
  // database, so the browser pulls.
  interface KvChanged {
    db: string;
    seq: number;
  }

  interface KvCheckReply {
    removed: number;
  }

  interface DocGet {
    ref: DocRef;
  }

  interface DocGetReply {
    body: unknown;
  }

  interface DocPut {
    path: string;
    body: unknown;
  }

  interface DocPutReply {
    ref: DocRef;
    seq: number;
  }

  interface DocHead {
    path: string;
  }

  interface DocHeadReply {
    ref: DocRef;
  }

  interface SyncPull {
    db: string;
    since: number;
  }

  interface GoneRow {
    k: string;
    seq: number;
  }

  interface DocRow {
    path: string;
    version: number;
    body: unknown;
    seq: number;
  }

  interface HeadRow {
    path: string;
    version: number;
  }

  // A turn of a scene's conversation, in metaverse only; `content` is
  // one provider message.
  interface TurnRow {
    scene: DocRef;
    n: number;
    role: provider.Role;
    content: provider.ChatMessage;
    seq: number;
  }

  // sync.pull's reply, and the rows part of sync.push and sync.apply.
  // The engine's tables only; the AI's own tables travel by snapshot.
  interface SyncRows {
    db: string;
    seq: number;
    kv: KvRow[];
    gone: GoneRow[];
    doc: DocRow[];
    head: HeadRow[];
    turn: TurnRow[];
  }

  // sync.push and sync.apply: `blobs` lists the hashes whose bytes follow
  // as blobs "1" on, in that order, for rows the receiver lacks.
  interface SyncPush extends SyncRows {
    blobs: Sha256[];
  }

  interface DbOpen {
    db: string;
    kind: "engine" | "metaverse" | "log";
  }

  interface DbName {
    db: string;
  }

  interface DbAttach {
    universe: string;
    region: string;
  }

  interface DbListReply {
    dbs: { db: string; seq: number }[];
  }

  // db.snapshot's reply carries the file as blob "1"; db.restore takes it.
  interface DbSnapshotReply {
    sha256: Sha256;
    seq: number;
  }

  interface SqlStatement {
    sql: string;
    params: unknown[];
  }

  interface SqlRun {
    db: string;
    statements: SqlStatement[];
  }

  interface SqlResult {
    columns: string[];
    rows: unknown[][];
    changes: number;
  }

  interface SqlRunReply {
    results: SqlResult[];
  }

  interface LogLine {
    at: number;
    level: number;
    text: string;
  }

  interface LogPut {
    lines: LogLine[];
  }

  interface LogTail {
    count: number;
  }

  interface LogTailReply {
    lines: LogLine[];
  }

  interface ConsoleOpen {
    columns: number;
    rows: number;
  }

  interface ConsoleOpenReply {
    pid: number;
  }

  interface ConsoleSignal {
    signal: number;
  }

  interface ConsoleExit {
    code: number;
  }

  // mcp: the payload is the JSON-RPC message itself. See mcp.d.ts.
  type Mcp = mcp.Message;

  interface TapReport {
    language: "python" | "typescript";
    text: string;
  }

  interface TapReportReply {
    ok: boolean;
    pass: number;
    fail: number;
    skip: number;
  }

  interface SettingsPut {
    settings: settings.Settings;
  }

  // source.put: blob "1" is the file written as `name` into the package.
  interface SourcePut {
    name: string;
  }

  // boot.hello: what the UI shows of the hello and the page.
  interface BootHello {
    bootstrap: string;
    sha256: Sha256;
    pid: number;
    python: string;
    sqlite: string;
    debug: boolean;
    page_sha256: Sha256;
    tab: string;
  }

  interface Status {
    state: "connecting" | "syncing" | "ready" | "turn" | "closed";
    detail: string;
  }

  interface AiSay {
    text: string;
  }

  interface AiClick {
    x: number;
    y: number;
  }

  interface TurnEnd {
    turn: number;
    scene: DocRef;
    subtitle: string;
  }

  // render: the UI paints the image it holds under `image` and shows the
  // subtitle. `image` absent means black.
  interface Render {
    scene: DocRef;
    subtitle: string;
    image?: string;
  }

  // media.fetch: the UI downloads `url` and keeps it as `k`.
  interface MediaFetch {
    url: string;
    k: string;
  }

  // media.store: blob "1" is the image to keep as `k`.
  interface MediaStore {
    k: string;
  }

  // media.bytes: the UI replies with the bytes of `k` as blob "1".
  interface MediaBytes {
    k: string;
  }

  interface MediaReply {
    k: string;
    size: number;
    sha256: Sha256;
  }

  interface PermitAsk {
    permit: number;
    tool: string;
    input: unknown;
  }

  interface PermitAnswer {
    permit: number;
    choice: "accept" | "deny" | "always";
  }

  interface Fault {
    thread: "ui" | "ai" | "wasm" | "server";
    message: string;
    stack: string;
  }

  interface CacheOpenReply {
    handle: string;
  }

  interface CacheHandle {
    handle: string;
  }
}
