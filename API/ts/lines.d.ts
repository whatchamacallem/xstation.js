// The payloads of the JSLB line types, each interface below the payload of one
// type, the wire API. A line is one JSON object: header 0, blob headers 1 to
// b, the payload in every other key. A field at its default is not written.
//
// The browser pulls the databases by `db.sync`, so a suite sending none sees
// no new line. The server answers with the whole of every database it holds:
// for each in name order its `db.restore` line and its `db.file` lines, then
// `DbSyncReply`, which names them in that order. The
// browser's queue runs the pushes in order, before the reply, so the task that
// wakes on the reply finds every database restored and checks the list against
// its own. No count and no end marker is needed: the reply is the end.
//
// `provider.set` is deferred and not built. The engine role reads the root's
// `provider.json` and, from its environment, which the serve program and ttyd
// pass on, the variable the settings name, `XSJS_PROVIDER_KEY`. When
// `provider.scripted` is false it pushes this line at once after the Empty
// reply to `tap.start`, before the program sends anything. The audit writes it
// as its header only. The worker's handler sets the key in the provider door,
// keeps the three names for the agent and the image tool, and the `http` owner
// becomes the HTTP port with `timeout_seconds`.

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

  // The provider's address and model names. A scripted run's cannot resolve.
  interface ProviderInfo {
    base_url: string;
    chat_model: string;
    image_model: string;
  }

  // provider.set: the server to the AI worker, no blobs. Deferred, not built.
  interface ProviderSet extends ProviderInfo {
    key: string;
  }

  // tap.start: the first line: settings and switches, no gold.
  interface TapStart {
    settings: settings.Settings;
    switches: switches.Switches;
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

  // db.sync: the AI worker to the server, no blobs and no payload.
  interface DbSync {}

  // The reply to db.sync: the databases sent, in the order they were sent.
  interface DbSyncReply {
    databases: string[];
  }

  // turn.append: one turn of a scene's log, its input items.
  interface TurnAppend {
    scene: DocRef;
    role: provider.Role;
    content: provider.InputItem[];
  }

  interface TurnAppendReply {
    n: number;
  }

  // turn.prompt: a conversation's system prompt, stored once before turn 1.
  interface TurnPrompt {
    scene: DocRef;
    messages: provider.InputMessage[];
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

  // audit.line: a page thread's record of a line, its JSON text as blob 1.
  interface AuditLine {
    sender: queue.ThreadName;
    receiver: queue.ThreadName;
    at: number;
  }

  // audit.note: a page thread's note of what no line says, a task's sleep.
  interface AuditNote {
    thread: "ui" | "ai";
    at: number;
    text: string;
  }

  // audit.tail: the audit's newest entries, `count` a maximum, debug mode.
  interface AuditTail {
    count: number;
  }

  // The newest whole entries that fit one reply below `line_max`, in order.
  interface AuditTailReply {
    text: string;
  }

  // audit.dump: no payload. On the wire blob 1 is the browser's views as JSON.
  interface AuditDump {}

  // audit.overlay: no payload. ctrl 1, from a listener, run by the UI thread.
  interface AuditOverlay {}

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
    category: "smoke-test" | "test-all" | "test-disabled";
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
    switches: switches.Switches;
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

  // render: paints `image`, kept by `media.store` first, or black, and text.
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

  // `ui.control_key`: a digit but 1 typed with control, from a listener.
  interface UiControlKey {
    digit: number;
  }

  // console.show: shows the console view as ctrl 0 does, tty 0 asked for.
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

  // console.write: the AI's text, which tty 0's writer types line by line.
  interface ConsoleWrite {
    text: string;
  }

  // console.busy and console.idle: the view takes no keys between the two.
  interface ConsoleTurn {}

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
