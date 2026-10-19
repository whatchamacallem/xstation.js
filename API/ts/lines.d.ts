// The catalogue of every JSLB line type on every lane. A line is one JSON
// object: header "0", blob headers "1" to "b", the payload in every other
// key. Short names on the wire, full names in debug mode; a field at its
// default is not written. Each interface below is the payload of one
// type; the comment above it gives the lane, the direction, the blobs
// and the reply. "push" means a notification the receiver never answers.
// "fwd" marks a modifying substrate operation the browser forwards to the
// server after its commit, carrying `since`; on the ui-ai lane the same
// types travel without `since` as tasks the UI submits to the AI thread.
// "wake" marks a line the task manager enqueues on its own thread when
// every reply a sleeping task waited for has arrived.
//
// type              lane     from -> to      blobs  reply
// hello             wire     SERVER -> AI    0      Empty
// error             any      either, r set   0      none
// kv.get            wire     AI -> SERVER    0      KvGetReply + 1
// kv.put            wire     AI -> SERVER    1      KvPutReply, fwd
// kv.delete         wire     AI -> SERVER    0      SeqReply, fwd
// kv.list           wire     AI -> SERVER    0      KvListReply
// doc.put           wire     AI -> SERVER    0      DocPutReply, fwd
// doc.head          wire     AI -> SERVER    0      DocHeadReply
// db.create         wire     AI -> SERVER    0      Empty, fwd
// db.drop           wire     AI -> SERVER    0      Empty, fwd
// db.snapshot       wire     AI -> SERVER    0      DbSnapshotReply + 1
// turn.append       wire     AI -> SERVER    0      TurnAppendReply, fwd
// turn.compact      wire     AI -> SERVER    0      SeqReply, fwd
// sql.run           wire     AI -> SERVER    0      SqlRunReply, fwd
// verbose.put       wire     AI -> SERVER    0      push (debug)
// verbose.tail      wire     AI -> SERVER    0      VerboseTailReply
// tap.line          wire     AI -> SERVER    0      push
// mcp               wire     either          0      push (JSON-RPC)
// settings.put      wire     AI -> SERVER    0      Empty (debug)
// source.put        wire     AI -> SERVER    1      Sha256Reply (debug)
// system.restart    wire     AI -> SERVER    0      push; a new hello
// settings.set      ui-ai    AI -> UI        0      push
// boot.hello        ui-ai    AI -> UI        0      push
// ai.say            ui-ai    UI -> AI        0      TurnEnd
// ai.click          ui-ai    UI -> AI        0      TurnEnd
// render            ui-ai    AI -> UI        0      Empty
// media.fetch       ui-ai    AI -> UI        0      MediaReply + 1
// media.store       ui-ai    AI -> UI        1      MediaReply
// permit.ask        ui-ai    AI -> UI        0      PermitAnswer
// console.open      ui-ai    UI -> AI        0      Empty
// console.input     ui-ai    UI -> AI        1      push, to the port
// console.output    ui-ai    AI -> UI        1      push
// console.close     ui-ai    UI -> AI        0      Empty
// console.exit      ui-ai    AI -> UI        0      push
// overlay.line      ui-ai    AI -> UI        0      push (debug)
// verbose.put       ui-ai    UI -> AI        0      push, then forwarded
// fault             ui-ai    either          0      push
// kv.* doc.* db.*   ui-ai    UI -> AI        as on the wire, no since
// turn.* sql.*
// console.input     console  AI -> CONSOLE   1      push: one message
// console.read      console  AI -> CONSOLE   0      ConsoleRead
// dom.choice        dom      UI -> DOM       0      DomChoice
// ui.input          ui       DOM -> UI       0      push, from a listener
// ai.model_reply    ai       AI -> AI        0      wake
// ai.tool_reply     ai       AI -> AI        0      wake
// tools.*_reply     ai       AI -> AI        0      wake, a tool's own
// ui.turn_end       ui       UI -> UI        0      wake
// ui.permit_reply   ui       UI -> UI        0      wake
// http.request      http     any -> HTTP     0      HttpResponse
// mcp               mcp      AGENT <-> MCP   0      push (JSON-RPC)

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

  // A Key-Value-Ref: `/$db/$key` external, `$key` internal. `$db` is a C
  // identifier; `$key` is any non-empty text and may contain `/`.
  type KvRef = string;

  // A Document-Ref: a Key-Value-Ref whose key is `$id/$version`, the
  // version an integer literal and the last segment.
  type DocRef = string;

  // A document in its stored form: header "0" with `t` the document type
  // and `v` its format version, reference strings at "1" on, and
  // `{"$ref": n}` in the body where header n is meant.
  interface Document {
    "0": { t: string; v?: number };
    [key: string]: unknown;
  }

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
  // `provider_key` is the environment's `XSJS_PROVIDER_KEY`.
  interface Hello {
    bootstrap: string;
    sha256: Sha256;
    pid: number;
    root: string;
    settings: settings.Settings;
    seq: { [db: string]: number };
    provider_key: string;
  }

  // kv.get: the ref is the header's `k`. Reply with the value as blob
  // "1".
  interface KvGet {}

  interface KvGetReply {
    size: number;
    sha256: Sha256;
  }

  // kv.put: the ref is the header's `k`; the value is blob "1". On the
  // wire `since` is the browser's `seq` before the write.
  interface KvPut {
    since?: number;
  }

  interface KvPutReply {
    sha256: Sha256;
    seq: number;
  }

  interface KvDelete {
    since?: number;
  }

  interface KvList {
    db: string;
    prefix: string;
  }

  interface KvRow {
    k: string;
    size: number;
    sha256: Sha256;
  }

  interface KvListReply {
    keys: KvRow[];
  }

  interface DocPut {
    db: string;
    id: string;
    body: Document;
    since?: number;
  }

  interface DocPutReply {
    ref: DocRef;
    seq: number;
  }

  interface DocHead {
    db: string;
    id: string;
  }

  interface DocHeadReply {
    ref: DocRef;
  }

  interface DbName {
    db: string;
  }

  // db.snapshot's reply carries the file as blob "1".
  interface DbSnapshotReply {
    sha256: Sha256;
    seq: number;
  }

  interface TurnAppend {
    scene: DocRef;
    role: provider.Role;
    content: provider.ChatMessage;
    since?: number;
  }

  interface TurnAppendReply {
    n: number;
    seq: number;
  }

  interface TurnCompact {
    scene: DocRef;
    through: number;
    summary: string;
    since?: number;
  }

  interface SqlStatement {
    sql: string;
    params: unknown[];
  }

  interface SqlRun {
    db: string;
    statements: SqlStatement[];
    since?: number;
  }

  interface SqlResult {
    columns: string[];
    rows: unknown[][];
    changes: number;
  }

  interface SqlRunReply {
    results: SqlResult[];
    seq: number;
  }

  interface VerboseLine {
    at: number;
    level: number;
    text: string;
  }

  interface VerbosePut {
    thread: "ui" | "ai";
    lines: VerboseLine[];
  }

  interface VerboseTail {
    thread: "ui" | "ai" | "server";
    count: number;
  }

  interface VerboseTailReply {
    lines: VerboseLine[];
  }

  interface TapLine {
    language: "python" | "typescript";
    text: string;
  }

  // mcp: the payload is the JSON-RPC message itself. See mcp.d.ts.
  type Mcp = mcp.Message;

  interface SettingsPut {
    settings: settings.Settings;
  }

  // source.put: blob "1" is the file written as `main_loop/<name>`.
  interface SourcePut {
    name: string;
  }

  interface SystemRestart {
    main_loop: string;
  }

  interface SettingsSet {
    settings: settings.Settings;
  }

  // boot.hello: what the UI shows of the hello.
  interface BootHello {
    bootstrap: string;
    sha256: Sha256;
    pid: number;
    root: string;
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
    image?: KvRef;
  }

  // media.fetch: the UI downloads `url`, keeps it as `k`, and replies
  // with the bytes as blob "1" so the AI worker can back them up.
  interface MediaFetch {
    url: string;
    k: KvRef;
  }

  // media.store: blob "1" is the image to keep as `k`.
  interface MediaStore {
    k: KvRef;
  }

  interface MediaReply {
    k: KvRef;
    size: number;
    sha256: Sha256;
  }

  // permit.ask: the UI shows Accept, Deny and Always Allow, sleeps on
  // `dom.choice`, and replies with the choice when a button is clicked.
  interface PermitAsk {
    permit: number;
    tool: string;
    input: unknown;
  }

  interface PermitAnswer {
    permit: number;
    choice: "accept" | "deny" | "always";
  }

  // dom.choice: the DOM port of page.ts answers when one of the buttons
  // is clicked.
  interface DomChoice {
    permit: number;
    choices: string[];
  }

  interface DomChoiceReply {
    choice: string;
  }

  // ui.input: a DOM listener's notification of the player's text or
  // click; the handler submits `ai.say` or `ai.click` and sleeps with
  // `ui.turn_end`.
  interface UiInput {
    text?: string;
    x?: number;
    y?: number;
  }

  // console.input and console.output: blob "1" is one message of ttyd's
  // own protocol, as the client or the server would send it on tty 0.
  interface ConsoleBytes {}

  // console.read: the console port replies with the output received
  // since the last read once `until` appears in it, or when the timer
  // of `timeout_seconds` expires.
  interface ConsoleRead {
    until: string;
    timeout_seconds: number;
  }

  interface ConsoleReadReply {
    text: string;
    timed_out: boolean;
  }

  interface ConsoleExit {
    code: number;
  }

  // overlay.line: one rendered line of tty `tty` for the UI's ring.
  interface OverlayLine {
    tty: number;
    text: string;
  }

  interface Fault {
    thread: "ui" | "ai" | "server";
    message: string;
    stack: string;
  }

  // A wake: `state` as the sleeping handler left it, and the reply lines
  // it waited for, in the order they were submitted.
  interface Wake {
    state: unknown;
    replies: Line[];
  }

  // http.request: `json` is serialized as the body when present, else
  // `body` is sent as is. The port answers with HttpResponse, or `error`
  // when `timeout_seconds` expires or the fetch fails.
  interface HttpRequest {
    method: "GET" | "POST";
    url: string;
    headers: { [name: string]: string };
    json?: unknown;
    body?: string;
  }

  // http.response: `json` when the content type is JSON, else `text`;
  // `data` as blob "1" when the request asked for `binary`.
  interface HttpResponse {
    status: number;
    headers: { [name: string]: string };
    json?: unknown;
    text?: string;
  }
}
