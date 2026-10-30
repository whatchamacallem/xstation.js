// The catalogue of every JSLB line type on every lane. A line is one JSON
// object: header 0, blob headers 1 to b, the payload in every other key.
// A header field has a short name, `t`, and a full name, `type`; the thread
// that builds a line picks the form by `settings.names_full()`: full names
// in debug mode and before the settings exist, short names otherwise. The
// line that answers another takes the form of the line it answers. A field
// at its default is not written. Payload keys are always full English words:
// only the header fields have single letter names. Each interface below is
// the payload of one type; the table gives its lane, direction, blobs and
// reply. "push" is a notification the receiver never answers. An `mcp` line
// is a request, with `i` and answered by an `mcp` reply, when its `JSON-RPC`
// message is a request, and a push when that message is a notification.
//
// "commit" marks a modifying store operation that the browser's store sends
// to the server as a push once its own transaction has committed. The server
// applies it to its own store as a plain message: no ordering, no sequence
// number, no consistency check, and a line lost to a connection loss stays
// lost. A failure to apply it fails the server loud. The same types on the
// ui-ai lane are requests the UI submits to the AI thread's store, answered
// with the replies below. Whole databases move only as blobs: `db.restore`
// with the database file, then one `db.file` line per cache file its rows
// name and the sender holds.
//
// "wake" marks a line the task manager enqueues on its own thread when every
// reply a sleeping task waited for has arrived. An `error` or a `fault`
// carries a cascade of failures as nested `cause` entries, the latest
// failure outermost and the first failure innermost.
//
// type              lane     from -> to      blobs  reply
// tap.start         wire     SERVER -> AI    0      Empty; `i` is 101
// error             wire     either          0      none; see ErrorLine
// kv.put            wire     AI -> SERVER    1      push, commit
// kv.delete         wire     AI -> SERVER    0      push, commit
// doc.put           wire     AI -> SERVER    0      push, commit
// db.create         wire     AI -> SERVER    0      push, commit
// db.drop           wire     AI -> SERVER    0      push, commit
// turn.append       wire     AI -> SERVER    0      push, commit
// sql.run           wire     AI -> SERVER    0      push, commit
// db.restore        wire     SERVER -> AI    1      push; `files` db.file next
// db.file           wire     SERVER -> AI    1      push
// verbose.put       wire     AI -> SERVER    0      push (debug)
// verbose.tail      wire     AI -> SERVER    0      VerboseTailReply
// tap.line          wire     AI -> SERVER    0      push
// tap.run           wire     AI -> SERVER    0      TapRunReply (debug)
// tap.line          wire     SERVER -> AI    0      push, tap.run's stream
// mcp               wire     either          0      request or push
// settings.put      wire     AI -> SERVER    0      Empty (debug)
// source.put        wire     AI -> SERVER    1      Sha256Reply (debug)
// system.restart    wire     AI -> SERVER    0      push; a new tap.start
// echo              wire     AI -> SERVER    any    the same line, r set
// settings.set      ui-ai    AI -> UI        0      push
// ui.tests          ui-ai    AI -> UI        0      push
// error             ui-ai    either, r set   0      none
// fault             ui-ai    either          0      push
// ai.say            ui-ai    UI -> AI        0      TurnEnd
// ai.click          ui-ai    UI -> AI        0      TurnEnd
// render            ui-ai    AI -> UI        0      Empty
// media.fetch       ui-ai    AI -> UI        0      MediaReply + 1
// media.store       ui-ai    AI -> UI        1      MediaReply
// permit.ask        ui-ai    AI -> UI        0      PermitAnswer
// console.show      ui-ai    AI -> UI        0      Empty, once tty 0 is open
// console.open      ui-ai    UI -> AI        0      ConsoleOpenReply
// console.input     ui-ai    UI -> AI        1      push, to the port
// console.output    ui-ai    AI -> UI        1      push
// console.close     ui-ai    UI -> AI        0      Empty
// console.exit      ui-ai    AI -> UI        0      push
// overlay.line      ui-ai    AI -> UI        0      push (debug)
// verbose.put       ui-ai    UI -> AI        0      push, then forwarded
// tap.line          ui-ai    UI -> AI        0      push, then forwarded
// settings.put      ui-ai    UI -> AI        0      push, relayed to SERVER
// kv.get            ui-ai    UI -> AI        0      KvGetReply + 1
// kv.put            ui-ai    UI -> AI        1      KvPutReply
// kv.delete         ui-ai    UI -> AI        0      Empty
// kv.list           ui-ai    UI -> AI        0      KvListReply
// doc.put           ui-ai    UI -> AI        0      DocPutReply
// doc.head          ui-ai    UI -> AI        0      DocHeadReply
// db.create         ui-ai    UI -> AI        0      Empty
// db.drop           ui-ai    UI -> AI        0      Empty
// turn.append       ui-ai    UI -> AI        0      TurnAppendReply
// sql.run           ui-ai    UI -> AI        0      SqlRunReply
// console.input     console  AI -> CONSOLE   1      push: one message
// console.open      console  AI -> CONSOLE   0      ConsoleOpenReply
// console.read      console  AI -> CONSOLE   0      ConsoleReadReply
// dom.choice        dom      UI -> DOM       0      DomChoiceReply
// ui.input          ui       DOM -> UI       0      push, from a listener
// ui.control_key    ui       DOM -> UI       0      push, from a listener
// ai.model_reply    ai       AI -> AI        0      wake
// ai.tool_reply     ai       AI -> AI        0      wake
// tools.*_reply     ai       AI -> AI        0      wake, a tool's own
// worker.tests      ai       AI -> AI        0      push, runs the suites
// rungs.next        ai       AI -> AI        0      push, the wire rungs
// rungs.reply       ai       AI -> AI        0      wake, the wire rungs
// settings.put      ai       AI -> AI        0      push, relayed to SERVER
// worker.console_opened ai   AI -> AI        0      wake
// worker.settings_put ai     AI -> AI        0      wake
// ui.turn_end       ui       UI -> UI        0      wake
// ui.permit_reply   ui       UI -> UI        0      wake
// ui.media_reply    ui       UI -> UI        0      wake
// ui.console_reply  ui       UI -> UI        0      wake
// ui.console_closed ui       UI -> UI        0      wake
// ui.console_shown  ui       UI -> UI        0      wake
// http.request      http     any -> HTTP     0      HttpResponse
// mcp               mcp      AGENT <-> MCP   0      request or push
// tap.start         realm    DRIVER -> REALM 0      Empty; `i` is 101
// tap.line          realm    REALM -> DRIVER 0      push
// tap.pair          realm    REALM -> DRIVER 0      push, a pair test run
// verbose.put       realm    REALM -> DRIVER 0      push (debug), B's worker
// settings.set      realm    REALM -> DRIVER 0      push, B's worker's UI lane
// error             realm    REALM -> DRIVER 0      none; fails the block
// fault             realm    REALM -> DRIVER 0      push; fails the block

declare namespace lines {
  // Header 0: `t` type, `v` version, `i` id, `r` reply, `k` key, `b` blobs.
  interface LineHeader {
    t: string;
    v?: number;
    i?: number;
    r?: number;
    k?: string;
    b?: number;
  }

  // Headers 1 to b: `s` size, `k` key, `d` the bytes or a cache handle.
  interface BlobHeader {
    s: number;
    k?: string;
    d?: Uint8Array | string;
    [field: string]: unknown;
  }

  interface Line {
    0: LineHeader;
    [key: string]: unknown;
  }

  // A digest is 64 lowercase hex characters, the `SHA-256` of the bytes.
  type Sha256 = string;

  // A `Key-Value-Ref`: `/$db/$key` external, `$key` internal.
  type KvRef = string;

  // A `Document-Ref`: a `Key-Value-Ref` whose key is `$id/$version`.
  type DocRef = string;

  // A stored document: header 0 with `t` and `v`, references at 1 on.
  interface Document {
    0: { t: string; v?: number };
    [key: string]: unknown;
  }

  interface Empty {}

  interface Sha256Reply {
    sha256: Sha256;
  }

  // One failure of a cascade and, under `cause`, the failure before it.
  interface ErrorCause {
    message: string;
    stack: string;
    cause?: ErrorCause;
  }

  // error: with `r`, the failure of that request, else of its sender.
  interface ErrorLine {
    message: string;
    stack: string;
    cause?: ErrorCause;
  }

  // The provider's address and model names, none empty.
  interface ProviderInfo {
    base_url: string;
    chat_model: string;
    image_model: string;
  }

  // tap.start: the first line, `settings.json` and, in debug mode, the gold.
  interface TapStart {
    settings: settings.Settings;
    test_settings?: harness.Gold;
  }

  // kv.get: the ref is the header's `k`. The reply carries the value as 1.
  interface KvGet {}

  interface KvGetReply {
    size: number;
    sha256: Sha256;
  }

  // kv.put: the ref is the header's `k`, the value is blob 1.
  interface KvPut {}

  interface KvPutReply {
    sha256: Sha256;
  }

  // kv.delete: the ref is the header's `k`.
  interface KvDelete {}

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
  }

  interface DocPutReply {
    ref: DocRef;
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

  // db.restore: blob 1 is the database file, `files` cache files follow.
  interface DbRestore {
    db: string;
    files: number;
  }

  // db.file: blob 1 is one cache file of the database being restored.
  interface DbFile {
    db: string;
  }

  interface TurnAppend {
    scene: DocRef;
    role: provider.Role;
    content: provider.ChatMessage;
  }

  interface TurnAppendReply {
    n: number;
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

  interface VerboseLine {
    at: number;
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

  // tap.line: one line of the page's TAP stream, or of a `tap.run`'s.
  interface TapLine {
    language: "typescript" | "python";
    text: string;
  }

  // The oracle of one block of a pair run: its `unittest.TestResult` counts.
  interface TapPairBlock {
    module: string;
    // What `TAPTestRunner.module_run` returned for the block.
    passed: boolean;
    // The `countTestCases` of the block's suite.
    cases: number;
    tests_run: number;
    failures: number;
    errors: number;
    skipped: number;
    expected_failures: number;
    unexpected_successes: number;
  }

  // tap.pair: one run of the pair fixtures, its TAP lines and its oracle.
  interface TapPair {
    run: string;
    failfast: boolean;
    lines: string[];
    blocks: TapPairBlock[];
  }

  // tap.run: only `tap_loop.py` serves it, each line of the run a push.
  interface TapRun {
    category: "smoke-test" | "normal-test";
    failfast: boolean;
    // The failing tests the run expects: it passes only with exactly these.
    failures: number;
    modules: string[];
  }

  // The exit code of `test_all.py` and all it wrote to stderr.
  interface TapRunReply {
    code: number;
    stderr: string;
  }

  // mcp: the payload is the `JSON-RPC` message itself, see `mcp.d.ts`.
  type Mcp = mcp.Message;

  interface SettingsPut {
    settings: settings.Settings;
  }

  // source.put: blob 1 is the file written as `main_loop/<name>`.
  interface SourcePut {
    name: string;
  }

  interface SystemRestart {
    main_loop: string;
  }

  // settings.set: what `tap.start` carried, for the UI thread.
  interface SettingsSet {
    settings: settings.Settings;
    test_settings?: harness.Gold;
  }

  // ui.tests: the worker's suites ended, so the UI thread runs its own.
  interface UiTests {}

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

  // render: the UI paints the image under `image`, or black, and the text.
  interface Render {
    scene: DocRef;
    subtitle: string;
    image?: KvRef;
  }

  // media.fetch: the UI downloads `url`, keeps it as `k`, replies with it.
  interface MediaFetch {
    url: string;
    k: KvRef;
  }

  // media.store: blob 1 is the image to keep as `k`.
  interface MediaStore {
    k: KvRef;
  }

  interface MediaReply {
    k: KvRef;
    size: number;
    sha256: Sha256;
  }

  // permit.ask: the UI shows Accept, Deny and Always Allow, then replies.
  interface PermitAsk {
    permit: number;
    tool: string;
    input: unknown;
  }

  interface PermitAnswer {
    permit: number;
    choice: "accept" | "deny" | "always";
  }

  // dom.choice: the DOM port answers when one of the buttons is clicked.
  interface DomChoice {
    permit: number;
    choices: string[];
  }

  interface DomChoiceReply {
    choice: string;
  }

  // ui.input: the player's text or click, from a DOM listener.
  interface UiInput {
    text?: string;
    x?: number;
    y?: number;
  }

  // `ui.control_key`: a digit typed with the control key, from a listener.
  interface UiControlKey {
    digit: number;
  }

  // console.show: shows the console view as ctrl 0 does, answered when open.
  interface ConsoleShow {}

  // The reply to console.open: the token ttyd gave for tty 0.
  interface ConsoleOpenReply {
    token: string;
  }

  // console.input and console.output: blob 1 is one message of tty 0.
  interface ConsoleBytes {}

  // console.read: the output since the last read once `until` appears in it.
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

  // fault: a failure of a thread that stops it, its cascade under `cause`.
  interface Fault {
    thread: "ui" | "ai";
    message: string;
    stack: string;
    cause?: ErrorCause;
  }

  // A wake: the sleeping handler's `state` and the replies it waited for.
  interface Wake {
    state: unknown;
    replies: Line[];
  }

  // http.request: `json` is sent as the body when present, else `body`.
  interface HttpRequest {
    method: "GET" | "POST";
    url: string;
    headers: { [name: string]: string };
    json?: unknown;
    body?: string;
  }

  // The answer of http.request: `json` for a JSON body, else `text`.
  interface HttpResponse {
    status: number;
    headers: { [name: string]: string };
    json?: unknown;
    text?: string;
  }
}
