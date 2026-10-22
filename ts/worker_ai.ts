// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI worker once the start of the platform has handed over its objects:
// the settings of the hello, the task manager with its ports to the UI
// thread, the server, the console and the provider, the store and the
// replication of every line it forwards, the MCP server and clients, the
// agent, and the start that loads the databases the first turn needs and
// renders the scene. The test page's worker runs its tests on the same queue.

namespace worker_ai {
  // The owners, settings, line types, names and refs of the worker.
  const constants = Object.freeze({
    thread: "ai" as const,
    ui_owner: "ui" as const,
    server_owner: "server" as const,
    console_owner: "console" as const,
    provider_owner: "http" as const,
    debug_setting: "debug",
    synchronous_setting: "queue_synchronous",
    overflow_setting: "overflow_bytes",
    compact_setting: "turn_compact_turns",
    limit_setting: "blob_max",
    scripted_setting: "provider.scripted",
    timeout_setting: "provider.timeout_seconds",
    settings_type: "settings.set",
    hello_type: "boot.hello",
    put_type: "settings.put",
    open_type: "console.open",
    close_type: "console.close",
    exit_type: "console.exit",
    overlay_type: "overlay.line",
    verbose_type: "verbose.put",
    get_type: "kv.get",
    snapshot_type: "db.snapshot",
    store_type: "media.store",
    render_type: "render",
    mcp_type: "mcp",
    next_type: "replicate.next",
    done_type: "replicate.done",
    start_type: "worker.start",
    snapshot_wake: "worker.snapshot_reply",
    initialized_type: "worker.initialized",
    listed_type: "worker.listed",
    fetched_type: "worker.fetched",
    stored_type: "worker.stored",
    rendered_type: "worker.rendered",
    opened_type: "worker.console_opened",
    put_wake: "worker.settings_put",
    script_wake: "worker.script_fetched",
    tests_type: "worker.tests",
    handler_version: 0,
    server_name: "xsjs-browser",
    client_name: "hyperposition-engine",
    mcp_version: "0",
    browser_prefix: "browser",
    server_prefix: "server",
    metaverse: "metaverse",
    files: "_files",
    world_ref: "/metaverse/world",
    scene_key: "scene",
    universe_sql: "SELECT name FROM universe WHERE world = ?",
    // The provider script of the scripted port, a JSON value of `_files`.
    script_ref: "/_files/provider/script.json",
    // A scripted run's provider address and models, empty: it reads none.
    scripted_info: Object.freeze<lines.ProviderInfo>({
      base_url: "",
      chat_model: "",
      image_model: "",
    }),
    wire_tty: 1,
    // What names the database of each forwarded type: `db`, the key, a scene.
    database_fields: Object.freeze<{ readonly [type: string]: string }>({
      "db.create": "db",
      "db.drop": "db",
      "doc.put": "db",
      "sql.run": "db",
      "kv.put": "key",
      "kv.delete": "key",
      "turn.append": "scene",
      "turn.compact": "scene",
    }),
  });

  // Registers the handler of one line type and version, as dispatch does.
  export type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // What the start of the platform hands over once the hello is in.
  export interface WorkerStart {
    hello: lines.Line;
    wire: wire.WirePort;
    ui: MessagePort;
    base_url: string;
    sqlite3: substrate.SqliteModule;
    pool: substrate.SqlitePool;
    cache: substrate.CacheFiles;
  }

  // What the start of the test page hands over once the hello is in.
  export interface TestStart {
    hello: lines.Line;
    wire: wire.WirePort;
    ui: MessagePort;
  }

  // The store's side of replication: the reply to each forwarded line.
  export interface ForwardStore {
    forward_done(line: lines.Line, reply: lines.Line): void;
  }

  // The parts of the store that the start of the engine uses.
  export interface StartStore {
    start_open(server: { [db: string]: number }): string[];
    db_restore(db: string, data: Uint8Array | string): number;
    db_load(db: string, data: Uint8Array | string): number;
    db_list(): string[];
    kv_get(ref: lines.KvRef): substrate.KvValue;
    kv_held(ref: lines.KvRef): boolean;
    cache_fill(ref: lines.KvRef, data: Uint8Array | string): void;
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[];
    doc_get(ref: lines.DocRef): lines.Document;
  }

  // The reader of the cache, whose stored values are named by their digest.
  export interface CacheReader {
    cache_read(handle: string, offset: number, length: number): Uint8Array;
  }

  // What the start of the engine works with.
  export interface ChainParts {
    tasks: queue.TaskQueue;
    store: StartStore;
    cache: CacheReader;
    browser: mcp.Client;
    server: mcp.Client;
    hello: lines.Hello;
    full: boolean;
    script: boolean;
    provider_attach: () => void;
  }

  // A line waiting in its database's queue, its bytes, a snapshot's port.
  interface ForwardEntry {
    line: lines.Line;
    bytes: number;
    port?: queue.Port;
  }

  // What a `replicate.done` wake keeps: the line in flight and its database.
  interface FlightState {
    line: lines.Line;
    db: string;
  }

  // What a relay's wake keeps: the request it owes the reply to.
  interface RelayState {
    request: lines.Line;
  }

  // A snapshot the start fetches: its database, whether it restores, the rest.
  interface FetchState {
    db: string;
    restore: boolean;
    rest: string[];
  }

  // The scene the start shows: its ref, its subtitle and its image if any.
  interface SceneView {
    scene: lines.DocRef;
    subtitle: string;
    image?: lines.KvRef;
  }

  // Whether the lines this worker builds use full names, which is debug mode.
  export function names_full(): boolean {
    return settings.settings_get(constants.debug_setting) as boolean;
  }

  // Whether a line uses full header names.
  function full_of(line: lines.Line): boolean {
    return Object.hasOwn(line[0], "type");
  }

  // A line of a type in the name form given, with its payload, blobs and key.
  function line_build(
    type: string,
    full: boolean,
    payload: { [key: string]: unknown },
    blobs: lines.BlobHeader[] = [],
    key?: string,
  ): lines.Line {
    const header = jslb.header_make(type, { key, full });
    return jslb.line_make(header, blobs, payload);
  }

  // The data of blob 1 of a reply: its bytes, or the handle of the cache.
  function blob_data(reply: lines.Line): Uint8Array | string {
    const blob = reply[1] as lines.BlobHeader;
    return jslb.field_get(blob, "data") as Uint8Array | string;
  }

  // Blob 1 of a `db.snapshot` reply, checked against the `sha256` it sent.
  function snapshot_data(db: string, reply: lines.Line): Uint8Array | string {
    const blob = reply[1] as lines.BlobHeader;
    const data = blob_data(reply);
    // A streamed blob's digest is the one its cache file took as it came.
    const sha256 =
      typeof data === "string"
        ? (blob.sha256 as lines.Sha256)
        : utility.sha256_hex(data);
    const sent = jslb.payload_of(reply).sha256 as lines.Sha256;
    if (sha256 !== sent) {
      throw new Error(i18n("substrate.snapshot_digest", db, sha256, sent));
    }
    return data;
  }

  // The bytes a held line counts: the sizes of its blobs, never its text.
  function line_bytes(line: lines.Line): number {
    const blobs = jslb.headers_of(line).slice(1) as lines.BlobHeader[];
    let sizes = 0;
    for (const blob of blobs) {
      sizes += jslb.field_get(blob, "size") as number;
    }
    return sizes;
  }

  // The database a forwarded line writes, by its `db`, its key or its scene.
  function database_of(line: lines.Line): string {
    const type = jslb.field_get(line[0], "type") as string;
    if (!Object.hasOwn(constants.database_fields, type)) {
      throw new Error(i18n("worker_ai.forward_type", type));
    }
    const field = constants.database_fields[type];
    if (field === "db") {
      return line.db as string;
    }
    const ref = field === "key" ? jslb.field_get(line[0], "key") : line.scene;
    return substrate.ref_split(ref as string).db as string;
  }

  // The database of an external ref, which the start loads when it lacks it.
  function ref_database(ref: string): string {
    const db = substrate.ref_split(ref).db;
    if (db === undefined) {
      throw new Error(i18n("worker_ai.ref_internal", ref));
    }
    return db;
  }

  // The bytes of a value: a copy of its row's, or read from its cache file.
  function value_bytes(
    store: StartStore,
    cache: CacheReader,
    ref: lines.KvRef,
  ): Uint8Array {
    const value = store.kv_get(ref);
    return typeof value.data === "string"
      ? cache.cache_read(value.data, 0, value.size)
      : value.data.slice();
  }

  // The text of a value, read from the cache when it is held there.
  function value_text(
    store: StartStore,
    cache: CacheReader,
    ref: lines.KvRef,
  ): string {
    return utility.utf8_decode(value_bytes(store, cache, ref));
  }

  // The owner table of the AI thread, with `tap.` on the test page.
  export function owners_make(test: boolean): queue.OwnerTable {
    const owners: queue.OwnerTable = {
      "ai.": "ai",
      "worker.": "ai",
      "replicate.": "ai",
      "tools.": "ai",
      "kv.": "ai",
      "doc.": "ai",
      "db.": "ai",
      "turn.": "ai",
      "sql.": "ai",
      "settings.put": "ai",
      "console.": "ai",
      "console.input": "console",
      "console.output": "ui",
      "console.exit": "ui",
      "verbose.": "server",
    };
    return test ? { ...owners, "tap.": "server" } : owners;
  }

  // The replication: a queue of forwarded lines per database, one in flight.
  export class ForwardQueue {
    private readonly store: ForwardStore;
    private readonly tasks: queue.TaskQueue;
    private readonly settings_get: (id: string) => unknown;
    private readonly full: boolean;
    private readonly waiting = new Map<string, ForwardEntry[]>();
    private readonly flying = new Set<string>();
    private held = 0;

    // Takes the store, the queue, the reader of `blob_max`, the name form.
    constructor(
      store: ForwardStore,
      tasks: queue.TaskQueue,
      settings_get: (id: string) => unknown,
      full: boolean,
    ) {
      this.store = store;
      this.tasks = tasks;
      this.settings_get = settings_get;
      this.full = full;
    }

    // Holds a line the store forwarded and asks for a step of its database.
    line_add(line: lines.Line): void {
      const bytes = line_bytes(line);
      const limit = this.settings_get(constants.limit_setting) as number;
      if (this.held + bytes > limit) {
        const header = utility.json_text(line[0]);
        throw new Error(
          i18n("worker_ai.queue_over", header, bytes, this.held, limit),
        );
      }
      const db = database_of(line);
      let entries = this.waiting.get(db);
      if (entries === undefined) {
        entries = [];
        this.waiting.set(db, entries);
      }
      entries.push({ line, bytes });
      this.held += bytes;
      this.next_notify(db);
    }

    // Sends the oldest line of a database that has none in flight.
    next_take(line: lines.Line): dispatch.Sleep | undefined {
      const db = line.db as string;
      // A step finds nothing when a line of it flies or went with a step.
      if (this.flying.has(db) || !this.waiting.has(db)) {
        return undefined;
      }
      const entry = this.entry_take(db);
      const port = entry.port;
      // A snapshot held behind the lines answered goes out, then the next.
      if (port !== undefined) {
        port.line_post(entry.line, []);
        return this.next_take(line);
      }
      this.held -= entry.bytes;
      this.flying.add(db);
      const id = this.tasks.task_submit(entry.line, constants.server_owner);
      const state: FlightState = { line: entry.line, db };
      return dispatch.task_sleep(state, [id], constants.done_type);
    }

    // Gives the server's reply to the store, then asks for the next line.
    done_take(wake: lines.Line): void {
      const state = wake.state as FlightState;
      const replies = wake.replies as lines.Line[];
      this.store.forward_done(state.line, replies[0]);
      this.flying.delete(state.db);
      if (this.waiting.has(state.db)) {
        this.next_notify(state.db);
      }
    }

    // The blob bytes of the lines held and not yet sent.
    held_bytes(): number {
      return this.held;
    }

    // Holds a snapshot behind its database's waiting lines, false if none.
    fetch_hold(line: lines.Line, port: queue.Port): boolean {
      const entries = this.waiting.get(line.db as string);
      if (entries === undefined) {
        return false;
      }
      entries.push({ line, bytes: 0, port });
      return true;
    }

    // Takes the oldest entry of a database's queue, dropping an empty queue.
    private entry_take(db: string): ForwardEntry {
      const entries = this.waiting.get(db) as ForwardEntry[];
      const entry = entries.shift() as ForwardEntry;
      if (entries.length === 0) {
        this.waiting.delete(db);
      }
      return entry;
    }

    // Asks this thread for a step of the database.
    private next_notify(db: string): void {
      const line = line_build(constants.next_type, this.full, { db });
      this.tasks.line_notify(line, constants.thread);
    }
  }

  // Registers the steps of the replication.
  export function forwards_register(
    forwards: ForwardQueue,
    register: HandlerRegister,
  ): void {
    const version = constants.handler_version;
    register(constants.next_type, version, (line) => forwards.next_take(line));
    register(constants.done_type, version, (line) => {
      forwards.done_take(line);
      return undefined;
    });
  }

  // The server's port, where a snapshot waits behind its database's lines.
  export class ServerHold implements queue.Port {
    private readonly inner: queue.Port;
    private forwards: ForwardQueue | undefined = undefined;

    // Takes the port it wraps, the wire or its tap.
    constructor(inner: queue.Port) {
      this.inner = inner;
    }

    // Sets the replication whose waiting lines a snapshot goes behind.
    forwards_attach(forwards: ForwardQueue): void {
      this.forwards = forwards;
    }

    // Posts a line, or holds a snapshot while lines of its database wait.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      const forwards = this.forwards as ForwardQueue;
      const type = jslb.field_get(line[0], "type");
      if (
        type === constants.snapshot_type &&
        forwards.fetch_hold(line, this.inner)
      ) {
        return;
      }
      this.inner.line_post(line, transfer);
    }

    // Gives the receiver to the port it wraps.
    line_receive(fn: (line: lines.Line) => void): void {
      this.inner.line_receive(fn);
    }
  }

  // A port that shows the lines it carries in the overlay of the wire's tty.
  export class WireTap implements queue.Port {
    private readonly inner: queue.Port;
    private readonly note: (text: string) => void;

    // Takes the port it wraps and what takes the text of each line.
    constructor(inner: queue.Port, note: (text: string) => void) {
      this.inner = inner;
      this.note = note;
    }

    // Shows the line as sent unless it forwards the view, then posts it.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      // Shown, a `verbose.put` would be forwarded and shown again, forever.
      if (jslb.field_get(line[0], "type") !== constants.verbose_type) {
        this.note(i18n("worker_ai.overlay_sent", jslb.line_render(line)));
      }
      this.inner.line_post(line, transfer);
    }

    // Shows each line received before the receiver takes it.
    line_receive(fn: (line: lines.Line) => void): void {
      this.inner.line_receive((line: lines.Line) => {
        this.note(i18n("worker_ai.overlay_received", jslb.line_render(line)));
        fn(line);
      });
    }
  }

  // The start of the engine as a chain of tasks, from the hello to the render.
  export class StartChain {
    private readonly parts: ChainParts;

    // Takes what the start works with.
    constructor(parts: ChainParts) {
      this.parts = parts;
    }

    // Tells the UI of the hello, opens what matches, asks for what differs.
    start_take(): dispatch.Sleep {
      const { tasks, store, hello, full } = this.parts;
      const shown = {
        bootstrap: hello.bootstrap,
        sha256: hello.sha256,
        pid: hello.pid,
        root: hello.root,
      };
      const notice = line_build(constants.hello_type, full, shown);
      tasks.line_notify(notice, constants.ui_owner);
      const names = store.start_open(hello.seq);
      return this.restore_next(names);
    }

    // Checks a snapshot's digest, opens it, checks its `seq` and goes on.
    snapshot_take(wake: lines.Line): dispatch.Sleep {
      const state = wake.state as FetchState;
      const replies = wake.replies as lines.Line[];
      const { store } = this.parts;
      const { db } = state;
      const data = snapshot_data(db, replies[0]);
      const seq = state.restore
        ? store.db_restore(db, data)
        : store.db_load(db, data);
      const sent = jslb.payload_of(replies[0]).seq as number;
      if (seq !== sent) {
        throw new Error(i18n("worker_ai.snapshot_desync", db, seq, sent));
      }
      return state.restore ? this.restore_next(state.rest) : this.load_next();
    }

    // Ends both initializations and asks both servers for their tools.
    initialized_take(wake: lines.Line): dispatch.Sleep {
      const { browser, server } = this.parts;
      const replies = wake.replies as lines.Line[];
      browser.initialized_send(replies[0]);
      server.initialized_send(replies[1]);
      const ids = [browser.tools_list(), server.tools_list()];
      return dispatch.task_sleep({}, ids, constants.listed_type);
    }

    // Keeps both lists of tools, then gives the UI the scene's image.
    listed_take(wake: lines.Line): dispatch.Sleep {
      const replies = wake.replies as lines.Line[];
      this.parts.browser.tools_read(replies[0]);
      this.parts.server.tools_read(replies[1]);
      return this.media_start();
    }

    // Fills back the Script the server sent, then starts the handshakes.
    script_take(wake: lines.Line): dispatch.Sleep {
      const replies = wake.replies as lines.Line[];
      const data = blob_data(replies[0]);
      this.parts.store.cache_fill(constants.script_ref, data);
      return this.handshake_send();
    }

    // Fills back the image the server sent and gives it to the UI.
    fetched_take(wake: lines.Line): dispatch.Sleep {
      const view = wake.state as SceneView;
      const replies = wake.replies as lines.Line[];
      const image = view.image as string;
      const { store, cache } = this.parts;
      store.cache_fill(image, blob_data(replies[0]));
      return this.store_submit(view, value_bytes(store, cache, image));
    }

    // Renders the scene once the UI holds its image.
    stored_take(wake: lines.Line): dispatch.Sleep {
      return this.render_submit(wake.state as SceneView);
    }

    // Ends the start once the UI has rendered the scene.
    rendered_take(): undefined {
      return undefined;
    }

    // Fetches the first database left to restore, or loads what is lacking.
    private restore_next(names: string[]): dispatch.Sleep {
      if (names.length === 0) {
        return this.load_next();
      }
      return this.fetch_start(names[0], true, names.slice(1));
    }

    // Asks the server for a database's snapshot, one at a time, and sleeps.
    private fetch_start(
      db: string,
      restore: boolean,
      rest: string[],
    ): dispatch.Sleep {
      const { tasks, full } = this.parts;
      const ask = line_build(constants.snapshot_type, full, { db });
      const id = tasks.task_submit(ask, constants.server_owner);
      const state: FetchState = { db, restore, rest };
      return dispatch.task_sleep(state, [id], constants.snapshot_wake);
    }

    // Asks for the next database the start lacks, or starts the handshakes.
    private load_next(): dispatch.Sleep {
      const missing = this.missing_find();
      if (missing === undefined) {
        return this.handshake_start();
      }
      return this.fetch_start(missing, false, []);
    }

    // The first database the first turn needs that is not open, if any.
    private missing_find(): string | undefined {
      const store = this.parts.store;
      const open = store.db_list();
      for (const db of [constants.metaverse, constants.files]) {
        if (!open.includes(db)) {
          return db;
        }
      }
      const world = this.text_read(constants.world_ref);
      if (!open.includes(world)) {
        return world;
      }
      const statement = { sql: constants.universe_sql, params: [world] };
      const rows = store.sql_run(constants.metaverse, [statement])[0].rows;
      for (const row of rows) {
        const universe = row[0] as string;
        if (!open.includes(universe)) {
          return universe;
        }
      }
      const scene = this.scene_current();
      const scene_db = ref_database(scene);
      if (!open.includes(scene_db)) {
        return scene_db;
      }
      const image = this.scene_read(scene).image;
      if (image === undefined) {
        return undefined;
      }
      const image_db = ref_database(image);
      return open.includes(image_db) ? undefined : image_db;
    }

    // Asks the server for the scripted provider's Script when not held.
    private handshake_start(): dispatch.Sleep {
      const { tasks, store, full, script } = this.parts;
      const ref = constants.script_ref;
      if (script && !store.kv_held(ref)) {
        const ask = line_build(constants.get_type, full, {}, [], ref);
        const id = tasks.task_submit(ask, constants.server_owner);
        return dispatch.task_sleep({}, [id], constants.script_wake);
      }
      return this.handshake_send();
    }

    // Adds the provider's port and starts both MCP handshakes.
    private handshake_send(): dispatch.Sleep {
      const { browser, server } = this.parts;
      this.parts.provider_attach();
      const ids = [browser.initialize_send(), server.initialize_send()];
      return dispatch.task_sleep({}, ids, constants.initialized_type);
    }

    // Gives the UI the scene's image: held here, or asked of the server.
    private media_start(): dispatch.Sleep {
      const { tasks, store, cache, full } = this.parts;
      const view = this.scene_read(this.scene_current());
      const image = view.image;
      if (image === undefined) {
        return this.render_submit(view);
      }
      if (!store.kv_held(image)) {
        const ask = line_build(constants.get_type, full, {}, [], image);
        const id = tasks.task_submit(ask, constants.server_owner);
        return dispatch.task_sleep(view, [id], constants.fetched_type);
      }
      return this.store_submit(view, value_bytes(store, cache, image));
    }

    // Gives the UI the image's bytes and sleeps until it holds them.
    private store_submit(view: SceneView, bytes: Uint8Array): dispatch.Sleep {
      const { tasks, full } = this.parts;
      const line = line_build(constants.store_type, full, { k: view.image }, [
        jslb.blob_make(bytes),
      ]);
      const id = tasks.task_submit(line, constants.ui_owner);
      return dispatch.task_sleep(view, [id], constants.stored_type);
    }

    // Asks the UI to render the scene and sleeps until it has.
    private render_submit(view: SceneView): dispatch.Sleep {
      const { tasks, full } = this.parts;
      const line = line_build(constants.render_type, full, { ...view });
      const id = tasks.task_submit(line, constants.ui_owner);
      return dispatch.task_sleep({}, [id], constants.rendered_type);
    }

    // The ref of the scene on screen, in the row `scene` of the world.
    private scene_current(): lines.DocRef {
      const world = this.text_read(constants.world_ref);
      return this.text_read(`/${world}/${constants.scene_key}`);
    }

    // The subtitle and image of a scene, which the scene's contract fixes.
    private scene_read(scene: lines.DocRef): SceneView {
      const normal = substrate.doc_decode(this.parts.store.doc_get(scene));
      const subtitle = normal.subtitle;
      const image = normal.image;
      if (typeof subtitle !== "string") {
        throw new Error(i18n("worker_ai.scene_invalid", scene));
      }
      if (image === undefined) {
        return { scene, subtitle };
      }
      if (typeof image !== "string") {
        throw new Error(i18n("worker_ai.scene_invalid", scene));
      }
      return { scene, subtitle, image };
    }

    // The text of a value of the store.
    private text_read(ref: lines.KvRef): string {
      return value_text(this.parts.store, this.parts.cache, ref);
    }
  }

  // Registers the steps of the start, one line type each.
  export function chain_register(
    chain: StartChain,
    register: HandlerRegister,
  ): void {
    const version = constants.handler_version;
    register(constants.start_type, version, () => chain.start_take());
    register(constants.snapshot_wake, version, (line) =>
      chain.snapshot_take(line),
    );
    register(constants.script_wake, version, (line) =>
      chain.script_take(line),
    );
    register(constants.initialized_type, version, (line) =>
      chain.initialized_take(line),
    );
    register(constants.listed_type, version, (line) =>
      chain.listed_take(line),
    );
    register(constants.fetched_type, version, (line) =>
      chain.fetched_take(line),
    );
    register(constants.stored_type, version, (line) =>
      chain.stored_take(line),
    );
    register(constants.rendered_type, version, () => chain.rendered_take());
  }

  // The script the scripted port answers from, a JSON value of `_files`.
  export function script_read(
    store: StartStore,
    cache: CacheReader,
  ): provider_script.Script {
    const text = value_text(store, cache, constants.script_ref);
    try {
      return JSON.parse(text) as provider_script.Script;
    } catch (error) {
      throw utility.error_wrap(
        i18n("worker_ai.script_invalid", constants.script_ref, String(error)),
        error,
      );
    }
  }

  // The provider's address and models: the hello's, or empty when scripted.
  export function info_read(
    hello: lines.Hello,
    scripted: boolean,
  ): lines.ProviderInfo {
    if (scripted) {
      return constants.scripted_info;
    }
    return hello.provider_info as lines.ProviderInfo;
  }

  // Adds the provider's port: the scripted one, else HTTPS under its timer.
  function provider_attach(
    tasks: queue.TaskQueue,
    store: StartStore,
    cache: CacheReader,
    scripted: boolean,
  ): void {
    const port = scripted
      ? new provider_script.ScriptPort(script_read(store, cache))
      : new http.HttpPort(
          settings.settings_get(constants.timeout_setting) as number,
        );
    tasks.port_add(constants.provider_owner, port);
  }

  // Registers the relays of the UI's `console.open` and `console.close`.
  export function console_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
    close: () => void,
  ): void {
    const version = constants.handler_version;
    // Opens tty 0 through the console port and sleeps until it is open.
    register(constants.open_type, version, (line) => {
      const header = jslb.header_make(constants.open_type, {
        full: full_of(line),
      });
      const copy = jslb.line_make(header, [], {});
      const id = tasks.task_submit(copy, constants.console_owner);
      const state: RelayState = { request: line };
      return dispatch.task_sleep(state, [id], constants.opened_type);
    });
    // Answers the UI with the token the console port fetched.
    register(constants.opened_type, version, (line) => {
      const { request } = line.state as RelayState;
      const replies = line.replies as lines.Line[];
      const token = jslb.payload_of(replies[0]).token;
      return dispatch.reply_make(request, { token });
    });
    // Closes tty 0 through the console port, whose end follows as the exit.
    register(constants.close_type, version, (line) => {
      close();
      return dispatch.reply_make(line, {});
    });
  }

  // Registers the relay of a `settings.put` notice to the server as a request.
  export function settings_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
    live: settings.Settings,
  ): void {
    const version = constants.handler_version;
    // Changes this thread's live settings, then submits them to the server.
    register(constants.put_type, version, (line) => {
      const payload = jslb.payload_of(line);
      // A copy, so a later change of the live value cannot alter the line.
      Object.assign(live, JSON.parse(utility.json_text(payload.settings)));
      const header = jslb.header_make(constants.put_type, {
        full: full_of(line),
      });
      const copy = jslb.line_make(header, [], payload);
      const id = tasks.task_submit(copy, constants.server_owner);
      return dispatch.task_sleep(null, [id], constants.put_wake);
    });
    register(constants.put_wake, version, () => undefined);
  }

  // What takes each rendered line of the wire: tty 1's overlay, then `log`.
  export function note_make(
    tasks: queue.TaskQueue,
    full: boolean,
    log: (text: string) => void,
  ): (text: string) => void {
    return (text: string) => {
      const line = line_build(constants.overlay_type, full, {
        tty: constants.wire_tty,
        text,
      });
      tasks.line_notify(line, constants.ui_owner);
      log(text);
    };
  }

  // Synchronous mode, from `queue_synchronous`, which needs debug mode.
  export function synchronous_read(
    settings_get: (id: string) => unknown,
  ): boolean {
    const synchronous = settings_get(constants.synchronous_setting) === true;
    if (synchronous && settings_get(constants.debug_setting) !== true) {
      throw new Error(i18n("worker_ai.synchronous_release"));
    }
    return synchronous;
  }

  // The console port, whose close the UI hears as `console.exit`.
  function console_make(
    tasks: queue.TaskQueue,
    base_url: string,
    full: boolean,
  ): wire.ConsolePort {
    const port = new wire.ConsolePort(base_url, settings.settings_get);
    port.close_receive((code: number) => {
      const line = line_build(constants.exit_type, full, { code });
      tasks.line_notify(line, constants.ui_owner);
    });
    return port;
  }

  // Sets the hello's settings, then the queue, its sink and its UI port.
  function thread_open(
    hello: lines.Line,
    ui: MessagePort,
    test: boolean,
  ): queue.TaskQueue {
    const value = (jslb.payload_of(hello) as unknown as lines.Hello).settings;
    settings.settings_set(value);
    const tasks = new queue.TaskQueue(
      constants.thread,
      owners_make(test),
      synchronous_read(settings.settings_get),
    );
    tasks.sink_attach(verbose.sink_set, settings.settings_get);
    tasks.port_add(constants.ui_owner, new queue.ThreadPort(ui));
    settings_register(tasks, dispatch.handler_register, value);
    settings.sender_register((put: lines.SettingsPut) => {
      const line = line_build(constants.put_type, names_full(), {
        settings: put.settings,
      });
      tasks.line_notify(line, constants.thread);
    });
    return tasks;
  }

  // Sends the settings to the UI first, then the empty reply to the hello.
  function hello_answer(
    tasks: queue.TaskQueue,
    hello: lines.Line,
    server: queue.Port,
  ): void {
    const value = (jslb.payload_of(hello) as unknown as lines.Hello).settings;
    const line = line_build(constants.settings_type, names_full(), {
      settings: value,
    });
    tasks.line_notify(line, constants.ui_owner);
    server.line_post(dispatch.reply_make(hello, {}), []);
  }

  // Runs the engine's worker on the objects the start of the platform made.
  export function worker_start(start: WorkerStart): void {
    const hello = jslb.payload_of(start.hello) as unknown as lines.Hello;
    const tasks = thread_open(start.hello, start.ui, false);
    const full = names_full();
    const debug = settings.settings_get(constants.debug_setting) === true;
    const scripted =
      settings.settings_get(constants.scripted_setting) === true;
    const tap = debug
      ? new WireTap(start.wire, note_make(tasks, full, verbose.log))
      : undefined;
    const wire_port: queue.Port = tap ?? start.wire;
    const server = new ServerHold(wire_port);
    tasks.port_add(constants.server_owner, server);
    const console_port = console_make(tasks, start.base_url, full);
    tasks.port_add(constants.console_owner, console_port);
    console_register(tasks, dispatch.handler_register, () =>
      console_port.console_close(),
    );
    provider.key_set(hello.provider_key);
    const store = new substrate.Store(
      start.sqlite3,
      start.pool,
      start.cache,
      hello.root,
      settings.settings_get(constants.overflow_setting) as number,
      settings.settings_get(constants.compact_setting) as number,
    );
    const forwards = new ForwardQueue(
      store,
      tasks,
      settings.settings_get,
      full,
    );
    server.forwards_attach(forwards);
    store.forward_set((line: lines.Line) => forwards.line_add(line), full);
    forwards_register(forwards, dispatch.handler_register);
    store.handlers_register(dispatch.handler_register);
    const mcp_server = new mcp.Server(
      constants.server_name,
      constants.mcp_version,
    );
    const info = info_read(hello, scripted);
    tools_browser.tools_register(
      mcp_server,
      store,
      tasks,
      constants.provider_owner,
      info,
      settings.settings_get,
    );
    dispatch.handler_register(
      constants.mcp_type,
      constants.handler_version,
      (line: lines.Line) => mcp_server.line_handle(line),
    );
    const browser = new mcp.Client(
      constants.client_name,
      constants.mcp_version,
      tasks,
      constants.thread,
      full,
    );
    const server_client = new mcp.Client(
      constants.client_name,
      constants.mcp_version,
      tasks,
      constants.server_owner,
      full,
    );
    const clients = new mcp.ClientSet();
    clients.client_add(constants.browser_prefix, browser);
    clients.client_add(constants.server_prefix, server_client);
    agent.handlers_register(
      store,
      clients,
      tasks,
      constants.provider_owner,
      info,
      settings.settings_get,
      dispatch.handler_register,
    );
    const chain = new StartChain({
      tasks,
      store,
      cache: start.cache,
      browser,
      server: server_client,
      hello,
      full,
      script: scripted,
      provider_attach: () =>
        provider_attach(tasks, store, start.cache, scripted),
    });
    chain_register(chain, dispatch.handler_register);
    hello_answer(tasks, start.hello, wire_port);
    const begin = line_build(constants.start_type, full, {});
    tasks.line_notify(begin, constants.thread);
  }

  // Runs the test page's worker: the queue, then the tests when the UI asks.
  export function test_start(
    start: TestStart,
    run: (tasks: queue.TaskQueue) => void,
  ): void {
    const tasks = thread_open(start.hello, start.ui, true);
    tasks.port_add(constants.server_owner, start.wire);
    dispatch.handler_register(
      constants.tests_type,
      constants.handler_version,
      () => {
        run(tasks);
        return undefined;
      },
    );
    hello_answer(tasks, start.hello, start.wire);
  }
}

Object.freeze(worker_ai);
