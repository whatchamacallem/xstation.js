// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the AI worker with a synchronous queue, port doubles and a store
// double: the owner tables, the replication queue, the wire's overlay tap,
// the relays of the console and of the settings, the start from the hello
// to the render, and the provider script.

namespace test_worker_ai {
  // The types the worker registers, routed by the tests, and the values used.
  const constants = Object.freeze({
    routed_types: Object.freeze([
      "replicate.next",
      "replicate.done",
      "console.open",
      "worker.console_opened",
      "console.close",
      "worker.start",
      "worker.snapshot_head",
      "worker.snapshot_piece",
      "worker.initialized",
      "worker.listed",
      "worker.fetched",
      "worker.stored",
      "worker.rendered",
    ]),
    bootstrap: "/home/t/.cache/xsjs/bootstrap.py",
    bootstrap_sha256:
      "ab30a921f2faeb729bc35cdbc0a4f5a8bb70c95624eb5bfc2ff778db2cb22f88",
    root: "/home/t/.cache/xsjs",
    pid: 4242,
    provider_key: "xai-SYNTHETIC-KEY",
    hyperposition: "/metaverse/hyperposition/1",
    greeting: "How can I help you?",
    scene: "/castle_gatehouse/scene/arrival/1",
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    image: "/_files/gatehouse/arrival.png",
    image_sha256:
      "90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0",
    image_size: 88,
    script_ref: "/_files/provider/script.json",
    // The provider's address and models a hello carries when not scripted.
    info: Object.freeze<lines.ProviderInfo>({
      base_url: "https://api.x.ai/v1",
      chat_model: "grok-4",
      image_model: "grok-2-image",
    }),
    // A type routed to the relay of `settings.put`, which test pages register.
    put_alias: "worker_test.settings_put",
  });

  // An object of fields by name.
  type Fields = { [key: string]: unknown };

  // The handlers the code under test registered, by line type.
  const routed = new Map<string, dispatch.Handler>();

  // Whether dispatch's registry routes the worker's types to `routed`.
  let router_installed = false;

  // Routes the worker's types from dispatch's registry, once per thread.
  function router_install(): void {
    if (router_installed) {
      return;
    }
    router_installed = true;
    for (const type of constants.routed_types) {
      dispatch.handler_register(type, 0, (line: lines.Line) => {
        const fn = routed.get(type);
        if (fn === undefined) {
          throw new Error(`No handler is routed for ${type}.`);
        }
        return fn(line);
      });
    }
    dispatch.handler_register(constants.put_alias, 0, (line: lines.Line) => {
      const relay = routed.get("settings.put") as dispatch.Handler;
      return relay(line);
    });
  }

  // A register that keeps each handler in `routed`.
  function register_route(
    type: string,
    _version: number,
    fn: dispatch.Handler,
  ): void {
    routed.set(type, fn);
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A port double: it keeps what the queue posts and hands it lines.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    private receiver: ((line: lines.Line) => void) | undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the queue as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
    }

    // The last line posted of a type.
    last_of(type: string): lines.Line {
      const found = this.posted.filter((line) => type_of(line) === type);
      if (found.length === 0) {
        throw new Error(`The port double was posted no ${type}.`);
      }
      return found[found.length - 1];
    }
  }

  // A synchronous queue of the AI thread and doubles of four of its ports.
  interface Bench {
    tasks: queue.TaskQueue;
    ui: PortDouble;
    server: PortDouble;
    console: PortDouble;
    http: PortDouble;
  }

  // Makes a bench with the engine's owner table and no handler routed.
  function bench_make(): Bench {
    router_install();
    routed.clear();
    const owners = worker_ai.owners_make(false);
    const tasks = new queue.TaskQueue("ai", owners, true);
    const bench = {
      tasks,
      ui: new PortDouble(),
      server: new PortDouble(),
      console: new PortDouble(),
      http: new PortDouble(),
    };
    tasks.port_add("ui", bench.ui);
    tasks.port_add("server", bench.server);
    tasks.port_add("console", bench.console);
    tasks.port_add("http", bench.http);
    return bench;
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // The header options the tests set.
  type HeaderOptions = {
    id?: number;
    reply?: number;
    key?: string;
    full?: boolean;
  };

  // A line in short names from its type, payload, header options and blobs.
  function line_short(
    type: string,
    payload: Fields = {},
    options: HeaderOptions = {},
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), blobs, payload);
  }

  // The reply to a request a double received, with its payload and blobs.
  function reply_to(
    request: lines.Line,
    payload: Fields,
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type_of(request) as string, {
      reply: jslb.field_get(request[0], "id") as number,
      full: Object.hasOwn(request[0], "type"),
    });
    return jslb.line_make(header, blobs, payload);
  }

  // The settings of `settings.json`, every key with its value.
  function settings_make(): settings.Settings {
    return {
      debug: true,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      verbose_forward: true,
      line_max: 1048576,
      blob_max: 10485760,
      message_max: 10485760,
      queue_max: 104857600,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      db_soft_bytes: 1073741824,
      turn_compact_tokens: 65536,
      long_task_ms: 5,
      provider: {
        scripted: true,
        timeout_seconds: 120,
      },
    };
  }

  // The reader of a settings store that holds the settings given.
  function reader_from(value: settings.Settings): (id: string) => unknown {
    const store = new settings.ValueStore();
    store.value_set(value);
    return (id: string) => store.value_get(id);
  }

  // A hello of a scripted run, which carries no provider information.
  function hello_make(): lines.Hello {
    return {
      bootstrap: constants.bootstrap,
      sha256: constants.bootstrap_sha256,
      pid: constants.pid,
      root: constants.root,
      settings: settings_make(),
      seq: { _settings: 15, _files: 1, _preferences: 0, metaverse: 5 },
      provider_key: constants.provider_key,
    };
  }

  // A forwarded `sql.run` of a database with the `since` given.
  function sql_line(db: string, since: number): lines.Line {
    return line_short("sql.run", { db, statements: [], since });
  }

  // A forwarded `kv.put` of a ref with three bytes as its blob.
  function kv_line(ref: string): lines.Line {
    const blob = jslb.blob_make(new Uint8Array([1, 2, 3]));
    return line_short("kv.put", { since: 0 }, { key: ref }, [blob]);
  }

  // A forwarded `turn.append` of a scene.
  function turn_line(scene: string): lines.Line {
    return line_short("turn.append", {
      scene,
      role: "user",
      content: { role: "user", content: "1" },
      since: 0,
    });
  }

  // The bytes the replication counts for a line without blobs.
  function text_bytes(line: lines.Line): number {
    return utility.utf8_encode(utility.json_text(line)).length;
  }

  // A store double for replication: it keeps each line and reply it gets.
  class ForwardDouble implements worker_ai.ForwardStore {
    readonly done: [lines.Line, lines.Line][] = [];

    // Keeps the forwarded line and its reply.
    forward_done(line: lines.Line, reply: lines.Line): void {
      this.done.push([line, reply]);
    }
  }

  // A store double for the start: databases, values, documents, calls.
  class StoreDouble implements worker_ai.StartStore {
    readonly open: string[] = [];
    readonly calls: string[] = [];
    readonly values = new Map<string, substrate.KvValue>();
    readonly documents = new Map<string, lines.Document>();
    readonly seqs = new Map<string, number>();
    replace: string[] = [];
    universes: string[] = [];

    // Records the server's `seq` and returns the databases to replace.
    start_open(server: { [db: string]: number }): string[] {
      this.calls.push(`start_open ${utility.json_text(server)}`);
      return this.replace;
    }

    // Opens a database from a snapshot and returns its `seq`.
    db_restore(db: string, data: Uint8Array | string): number {
      return this.snapshot_open("db_restore", db, data);
    }

    // Opens a database from a snapshot and returns its `seq`.
    db_load(db: string, data: Uint8Array | string): number {
      return this.snapshot_open("db_load", db, data);
    }

    // The bytes of a piece, which the tests send as bytes.
    blob_take(data: Uint8Array | string): Uint8Array {
      return data as Uint8Array;
    }

    // The open databases.
    db_list(): string[] {
      return [...this.open];
    }

    // The value of a ref, which the double must hold.
    kv_get(ref: lines.KvRef): substrate.KvValue {
      return this.value_get(ref);
    }

    // Records the write and returns the row the value already has.
    kv_put(
      ref: lines.KvRef,
      data: Uint8Array | string,
    ): { row: lines.KvRow; seq: number } {
      const shown = typeof data === "string" ? data : "bytes";
      this.calls.push(`kv_put ${ref} ${shown}`);
      const value = this.value_get(ref);
      return {
        row: { k: ref, size: value.size, sha256: value.sha256 },
        seq: 0,
      };
    }

    // Records the statements and returns the universes as rows of names.
    sql_run(db: string, statements: lines.SqlStatement[]): lines.SqlResult[] {
      this.calls.push(`sql_run ${db} ${utility.json_text(statements)}`);
      const rows = this.universes.map((name) => [name]);
      return [{ columns: ["name"], rows, changes: 0 }];
    }

    // The document of a ref, which the double must hold.
    doc_get(ref: lines.DocRef): lines.Document {
      const document_held = this.documents.get(ref);
      if (document_held === undefined) {
        throw new Error(`The store double has no document ${ref}.`);
      }
      return document_held;
    }

    // Holds text as the value of a ref, in its row.
    text_set(ref: string, text: string): void {
      const data = utility.utf8_encode(text);
      const sha256 = utility.sha256_hex(data);
      this.values.set(ref, { data, size: data.length, sha256 });
    }

    // Records the opening of a snapshot and opens the database.
    private snapshot_open(
      call: string,
      db: string,
      data: Uint8Array | string,
    ): number {
      const shown = typeof data === "string" ? data : "bytes";
      this.calls.push(`${call} ${db} ${shown}`);
      this.open.push(db);
      return this.seqs.get(db) as number;
    }

    // The value of a ref, which the double must hold.
    private value_get(ref: string): substrate.KvValue {
      const value = this.values.get(ref);
      if (value === undefined) {
        throw new Error(`The store double has no value ${ref}.`);
      }
      return value;
    }
  }

  // A cache double: files by handle and the handles read.
  class CacheDouble implements worker_ai.CacheReader {
    readonly files = new Map<string, Uint8Array>();
    readonly reads: string[] = [];

    // Reads a range of a file the double holds.
    cache_read(handle: string, offset: number, length: number): Uint8Array {
      this.reads.push(handle);
      const file = this.files.get(handle) as Uint8Array;
      return file.subarray(offset, offset + length);
    }
  }

  // A store double holding the seeded metaverse and its scene.
  function store_seeded(): StoreDouble {
    const store = new StoreDouble();
    store.text_set("/metaverse/world", "metaverse");
    store.text_set("/metaverse/scene", constants.hyperposition);
    store.documents.set(constants.hyperposition, {
      0: { t: "scene" },
      subtitle: constants.greeting,
    });
    store.seqs.set("metaverse", 5);
    store.seqs.set("_files", 1);
    return store;
  }

  // Registers a start on the bench whose browser server is the `http` double.
  function chain_make(
    bench: Bench,
    store: StoreDouble,
    cache: CacheDouble,
    attached: string[],
    changes: Partial<settings.Settings> = {},
  ): void {
    const browser = new mcp.Client(
      "hyperposition-engine",
      "0",
      bench.tasks,
      "http",
      false,
    );
    const server = new mcp.Client(
      "hyperposition-engine",
      "0",
      bench.tasks,
      "server",
      false,
    );
    const chain = new worker_ai.StartChain({
      tasks: bench.tasks,
      store,
      cache,
      browser,
      server,
      hello: hello_make(),
      full: false,
      settings_get: reader_from({ ...settings_make(), ...changes }),
      provider_attach: () => {
        attached.push("provider");
      },
    });
    worker_ai.chain_register(chain, register_route);
  }

  // Starts the chain as the hello's follow up task does.
  function chain_start(bench: Bench): void {
    bench.tasks.line_notify(line_short("worker.start"), "ai");
  }

  // The head of a snapshot of the bytes that the server keeps as number 3.
  function head_make(data: Uint8Array, seq: number): Fields {
    const sha256 = utility.sha256_hex(data);
    return { snapshot: 3, size: data.length, sha256, seq };
  }

  // Answers the last snapshot request of the server double: head, one piece.
  function snapshot_answer(bench: Bench, seq: number): void {
    const data = new Uint8Array([7]);
    const ask = bench.server.last_of("db.snapshot");
    bench.server.line_send(reply_to(ask, head_make(data, seq)));
    const piece = bench.server.last_of("db.chunk");
    bench.server.line_send(reply_to(piece, {}, [jslb.blob_make(data)]));
  }

  // The payloads of the piece requests the server double was asked.
  function pieces_asked(bench: Bench): Fields[] {
    return bench.server.posted
      .filter((line) => type_of(line) === "db.chunk")
      .map((line) => jslb.payload_of(line));
  }

  // The `JSON-RPC` response to an `mcp` request a double received.
  function mcp_answer(request: lines.Line, result: Fields): lines.Line {
    return reply_to(request, { jsonrpc: "2.0", id: request.id, result });
  }

  // Answers both initializations, then both lists of tools, with none.
  function handshake_answer(bench: Bench): void {
    const result = {
      protocolVersion: mcp.constants.protocol_version,
      capabilities: { tools: {} },
      serverInfo: { name: "xsjs-browser", version: "0" },
    };
    bench.http.line_send(mcp_answer(bench.http.last_of("mcp"), result));
    bench.server.line_send(mcp_answer(bench.server.last_of("mcp"), result));
    bench.http.line_send(mcp_answer(bench.http.last_of("mcp"), { tools: [] }));
    const listed = bench.server.last_of("mcp");
    bench.server.line_send(mcp_answer(listed, { tools: [] }));
  }

  // The databases whose snapshots the server double was asked for.
  function snapshots_asked(bench: Bench): unknown[] {
    return bench.server.posted
      .filter((line) => type_of(line) === "db.snapshot")
      .map((line) => line.db);
  }

  // The owner tables of the engine's worker and of the test page's.
  export class TestOwnerTables extends unittest.TestCase {
    // The console's lines go here, to its port or to the UI, verbose out.
    test_engine_routes(): void {
      const owners = worker_ai.owners_make(false);
      this.assertEqual(owners["console."], "ai");
      this.assertEqual(owners["console.input"], "console");
      this.assertEqual(owners["console.output"], "ui");
      this.assertEqual(owners["console.exit"], "ui");
      this.assertEqual(owners["verbose."], "server");
      this.assertEqual(owners["ai."], "ai");
      this.assertEqual(owners["replicate."], "ai");
      this.assertEqual(owners["worker."], "ai");
      this.assertEqual(owners["settings.put"], "ai");
      this.assertEqual(owners["kv."], "ai");
      this.assertFalse(Object.hasOwn(owners, "mcp"));
      this.assertFalse(Object.hasOwn(owners, "tap."));
    }

    // The test page's table sends `tap.` lines to the server too.
    test_tap_route(): void {
      const owners = worker_ai.owners_make(true);
      this.assertEqual(owners["tap."], "server");
      this.assertEqual(owners["verbose."], "server");
    }

    // Lines from the UI for the console port and the server pass unchanged.
    test_lines_passed(): void {
      const bench = bench_make();
      const input = line_short("console.input", {}, {}, [
        jslb.blob_make(new Uint8Array([0x30])),
      ]);
      bench.ui.line_send(input);
      this.assertTrue(bench.console.posted[0] === input);
      const put = line_short("verbose.put", { thread: "ui", lines: [] });
      bench.ui.line_send(put);
      this.assertTrue(bench.server.posted[0] === put);
    }

    // The name form is the thread's debug setting.
    test_names_debug(): void {
      this.assertEqual(worker_ai.names_full(), settings.settings_get("debug"));
    }
  }

  // The replication: a queue per database, one line in flight in each.
  export class TestForwardQueue extends unittest.TestCase {
    // A second line of a database waits for the reply to the first.
    test_one_flight(): void {
      const bench = bench_make();
      const store = new ForwardDouble();
      const reader = reader_from(settings_make());
      const forwards = new worker_ai.ForwardQueue(
        store,
        bench.tasks,
        reader,
        false,
      );
      worker_ai.forwards_register(forwards, register_route);
      const first = sql_line("castle", 0);
      const second = sql_line("castle", 1);
      const other = sql_line("castle_world", 0);
      forwards.line_add(first);
      forwards.line_add(second);
      forwards.line_add(other);
      this.assertEqual(bench.server.posted.length, 2);
      this.assertTrue(bench.server.posted[0] === first);
      this.assertTrue(bench.server.posted[1] === other);
      this.assertEqual(forwards.held_bytes(), text_bytes(second));
      const reply = reply_to(first, { results: [], seq: 1 });
      bench.server.line_send(reply);
      this.assertEqual(store.done.length, 1);
      this.assertTrue(store.done[0][0] === first);
      this.assertTrue(store.done[0][1] === reply);
      this.assertEqual(bench.server.posted.length, 3);
      this.assertTrue(bench.server.posted[2] === second);
      this.assertEqual(forwards.held_bytes(), 0);
      this.assertEqual(bench.tasks.depth(), 2);
    }

    // A key, a `db` and a scene each name the database a line waits on.
    test_database_named(): void {
      const bench = bench_make();
      const store = new ForwardDouble();
      const reader = reader_from(settings_make());
      const forwards = new worker_ai.ForwardQueue(
        store,
        bench.tasks,
        reader,
        false,
      );
      worker_ai.forwards_register(forwards, register_route);
      forwards.line_add(kv_line("/castle/k"));
      forwards.line_add(sql_line("castle", 1));
      forwards.line_add(turn_line("/castle/scene/1"));
      for (let seq = 1; seq <= 3; seq += 1) {
        this.assertEqual(bench.server.posted.length, seq);
        const sent = bench.server.posted[seq - 1];
        bench.server.line_send(reply_to(sent, { seq }));
      }
      const types = bench.server.posted.map((line) => type_of(line));
      this.assertEqual(types, ["kv.put", "sql.run", "turn.append"]);
      this.assertEqual(store.done.length, 3);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // Holding a line over `queue_max` throws and holds nothing more.
    test_queue_over(): void {
      const bench = bench_make();
      const bytes = text_bytes(sql_line("castle", 0));
      const value = settings_make();
      value.queue_max = bytes;
      const forwards = new worker_ai.ForwardQueue(
        new ForwardDouble(),
        bench.tasks,
        reader_from(value),
        false,
      );
      worker_ai.forwards_register(forwards, register_route);
      forwards.line_add(sql_line("castle", 0));
      forwards.line_add(sql_line("castle", 1));
      const over = sql_line("castle", 2);
      const error = thrown_get(() => forwards.line_add(over));
      this.assertEqual(
        error.message,
        i18n(
          "worker_ai.queue_over",
          utility.json_text(over[0]),
          bytes,
          bytes,
          bytes,
        ),
      );
      this.assertEqual(forwards.held_bytes(), bytes);
    }

    // A line of a type that writes no database is refused.
    test_type_refused(): void {
      const bench = bench_make();
      const forwards = new worker_ai.ForwardQueue(
        new ForwardDouble(),
        bench.tasks,
        reader_from(settings_make()),
        false,
      );
      const line = line_short("kv.get", {}, { key: "/castle/k" });
      const error = thrown_get(() => forwards.line_add(line));
      const expected = i18n("worker_ai.forward_type", "kv.get");
      this.assertEqual(error.message, expected);
    }
  }

  // The tap that shows the wire's lines in the overlay of tty 1.
  export class TestWireTap extends unittest.TestCase {
    // Each line is shown as sent or received and passes unchanged.
    test_both_ways(): void {
      const inner = new PortDouble();
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      const sent = line_short("kv.list", { db: "castle", prefix: "" }, {
        id: 1,
      });
      tap.line_post(sent, []);
      this.assertTrue(inner.posted[0] === sent);
      const taken: lines.Line[] = [];
      tap.line_receive((line) => {
        taken.push(line);
      });
      const received = line_short("kv.list", { keys: [] }, { reply: 1 });
      inner.line_send(received);
      this.assertTrue(taken[0] === received);
      this.assertEqual(notes, [
        i18n("worker_ai.overlay_sent", jslb.line_render(sent)),
        i18n("worker_ai.overlay_received", jslb.line_render(received)),
      ]);
    }

    // The page's view forwarded as `verbose.put` passes and is not shown.
    test_forward_unshown(): void {
      const inner = new PortDouble();
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      for (const full of [true, false]) {
        const put = line_short("verbose.put", { thread: "ui", lines: [] }, {
          full,
        });
        tap.line_post(put, []);
        this.assertTrue(inner.posted[inner.posted.length - 1] === put);
      }
      const sent = line_short("kv.list", { db: "castle", prefix: "" }, {
        id: 2,
      });
      tap.line_post(sent, []);
      this.assertEqual(inner.posted.length, 3);
      this.assertEqual(notes, [
        i18n("worker_ai.overlay_sent", jslb.line_render(sent)),
      ]);
    }
  }

  // The relays of the UI's console opening and close, and of the settings.
  export class TestRelays extends unittest.TestCase {
    // The UI's opening goes to the console port, and its token comes back.
    test_console_opened(): void {
      const bench = bench_make();
      let closes = 0;
      worker_ai.console_register(bench.tasks, register_route, () => {
        closes += 1;
      });
      const request = line_short("console.open", {}, { id: 7, full: true });
      bench.ui.line_send(request);
      const opening = bench.console.posted[0];
      this.assertEqual(type_of(opening), "console.open");
      this.assertTrue(Object.hasOwn(opening[0], "type"));
      this.assertTrue(opening !== request);
      bench.console.line_send(reply_to(opening, { token: "abc" }));
      const answer = bench.ui.posted[0];
      this.assertEqual(jslb.field_get(answer[0], "reply"), 7);
      this.assertEqual(answer.token, "abc");
      this.assertEqual(bench.tasks.depth(), 0);
      this.assertEqual(closes, 0);
    }

    // The UI's close closes the console port once and is answered at once.
    test_console_closed(): void {
      const bench = bench_make();
      let closes = 0;
      worker_ai.console_register(bench.tasks, register_route, () => {
        closes += 1;
      });
      const request = line_short("console.close", {}, { id: 8, full: true });
      bench.ui.line_send(request);
      this.assertEqual(closes, 1);
      this.assertEqual(bench.console.posted.length, 0);
      this.assertEqual(bench.ui.posted.length, 1);
      const answer = bench.ui.posted[0];
      this.assertEqual(type_of(answer), "console.close");
      this.assertEqual(jslb.field_get(answer[0], "reply"), 8);
      this.assertTrue(Object.hasOwn(answer[0], "type"));
      this.assertEqual(jslb.payload_of(answer), {});
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A notice of new settings goes to the server as a request, then ends.
    test_settings_sent(): void {
      const bench = bench_make();
      worker_ai.settings_register(bench.tasks, register_route);
      const value = settings_make();
      const notice = line_short(constants.put_alias, { settings: value });
      bench.tasks.line_notify(notice, "ai");
      this.assertEqual(bench.server.posted.length, 1);
      const put = bench.server.posted[0];
      this.assertEqual(type_of(put), "settings.put");
      this.assertEqual(typeof jslb.field_get(put[0], "id"), "number");
      this.assertEqual(put.settings, value);
      this.assertEqual(bench.tasks.depth(), 1);
      const wake = line_short("worker.settings_put", {
        state: null,
        replies: [reply_to(put, {})],
      });
      const done = routed.get("worker.settings_put") as dispatch.Handler;
      this.assertEqual(done(wake), undefined);
      this.assertEqual(bench.ui.posted.length, 0);
    }
  }

  // The start from the hello to the render, on a store double.
  export class TestStartChain extends unittest.TestCase {
    // A fresh store loads the metaverse and `_files`, then renders black.
    test_fresh_start(): void {
      const bench = bench_make();
      const store = store_seeded();
      const attached: string[] = [];
      chain_make(bench, store, new CacheDouble(), attached);
      chain_start(bench);
      const hello = bench.ui.posted[0];
      this.assertEqual(type_of(hello), "boot.hello");
      this.assertEqual(jslb.payload_of(hello), {
        bootstrap: constants.bootstrap,
        sha256: constants.bootstrap_sha256,
        pid: constants.pid,
        root: constants.root,
      });
      snapshot_answer(bench, 5);
      snapshot_answer(bench, 1);
      this.assertEqual(snapshots_asked(bench), ["metaverse", "_files"]);
      this.assertEqual(attached, ["provider"]);
      handshake_answer(bench);
      const render = bench.ui.last_of("render");
      this.assertEqual(jslb.payload_of(render), {
        scene: constants.hyperposition,
        subtitle: constants.greeting,
      });
      bench.ui.line_send(reply_to(render, {}));
      this.assertEqual(store.calls.slice(0, 3), [
        `start_open ${utility.json_text(hello_make().seq)}`,
        "db_load metaverse bytes",
        "db_load _files bytes",
      ]);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A database whose `seq` differs is restored before anything loads.
    test_restore_first(): void {
      const bench = bench_make();
      const store = store_seeded();
      store.open.push("metaverse");
      store.replace = ["_files"];
      chain_make(bench, store, new CacheDouble(), []);
      chain_start(bench);
      this.assertEqual(snapshots_asked(bench), ["_files"]);
      snapshot_answer(bench, 1);
      this.assertIn("db_restore _files bytes", store.calls);
      this.assertEqual(snapshots_asked(bench), ["_files"]);
      this.assertEqual(type_of(bench.http.posted[0]), "mcp");
    }

    // A snapshot that opens at another `seq` than the server's is a fault.
    test_snapshot_desync(): void {
      const bench = bench_make();
      chain_make(bench, store_seeded(), new CacheDouble(), []);
      chain_start(bench);
      const error = thrown_get(() => snapshot_answer(bench, 6));
      this.assertEqual(
        error.message,
        i18n("worker_ai.snapshot_desync", "metaverse", 5, 6),
      );
    }

    // The databases to restore are fetched one after another, in order.
    test_restores_turns(): void {
      const bench = bench_make();
      const store = store_seeded();
      store.replace = ["_files", "metaverse"];
      chain_make(bench, store, new CacheDouble(), []);
      chain_start(bench);
      this.assertEqual(snapshots_asked(bench), ["_files"]);
      snapshot_answer(bench, 1);
      this.assertEqual(snapshots_asked(bench), ["_files", "metaverse"]);
      snapshot_answer(bench, 5);
      this.assertEqual(store.calls.slice(1, 3), [
        "db_restore _files bytes",
        "db_restore metaverse bytes",
      ]);
      this.assertEqual(snapshots_asked(bench), ["_files", "metaverse"]);
      this.assertEqual(type_of(bench.http.posted[0]), "mcp");
    }

    // A snapshot's pieces are asked one at a time, each once the last came.
    test_pieces_turns(): void {
      const bench = bench_make();
      const store = store_seeded();
      chain_make(bench, store, new CacheDouble(), [], {
        line_max: 1024,
        message_max: 1026,
      });
      chain_start(bench);
      const data = new Uint8Array([7, 8, 9]);
      const ask = bench.server.last_of("db.snapshot");
      bench.server.line_send(reply_to(ask, head_make(data, 5)));
      const first = { snapshot: 3, offset: 0, size: 2 };
      this.assertEqual(pieces_asked(bench), [first]);
      const piece = jslb.blob_make(data.slice(0, 2));
      bench.server.line_send(
        reply_to(bench.server.last_of("db.chunk"), {}, [piece]),
      );
      const second = { snapshot: 3, offset: 2, size: 1 };
      this.assertEqual(pieces_asked(bench), [first, second]);
      this.assertEqual(store.open, []);
      const rest = jslb.blob_make(data.slice(2));
      bench.server.line_send(
        reply_to(bench.server.last_of("db.chunk"), {}, [rest]),
      );
      this.assertEqual(store.calls.slice(1), ["db_load metaverse bytes"]);
      this.assertEqual(snapshots_asked(bench), ["metaverse", "_files"]);
    }

    // The world, universe and scene load in turn, then the image is fetched.
    test_scene_loaded(): void {
      const bench = bench_make();
      const store = store_seeded();
      const cache = new CacheDouble();
      store.open.push("metaverse", "_files");
      store.text_set("/metaverse/world", "castle_world");
      store.text_set("/castle_world/scene", constants.scene);
      store.universes = ["castle"];
      store.documents.set(constants.scene, {
        0: { t: "scene" },
        1: constants.image,
        subtitle: constants.subtitle,
        image: { $ref: 1 },
      });
      store.values.set(constants.image, {
        data: constants.image_sha256,
        size: constants.image_size,
        sha256: constants.image_sha256,
      });
      const bytes = new Uint8Array(constants.image_size).fill(9);
      cache.files.set(constants.image_sha256, bytes);
      for (const db of ["castle_world", "castle", "castle_gatehouse"]) {
        store.seqs.set(db, 2);
      }
      chain_make(bench, store, cache, []);
      chain_start(bench);
      for (let count = 0; count < 3; count += 1) {
        snapshot_answer(bench, 2);
      }
      this.assertEqual(snapshots_asked(bench), [
        "castle_world",
        "castle",
        "castle_gatehouse",
      ]);
      handshake_answer(bench);
      const ask = bench.server.last_of("kv.get");
      this.assertEqual(jslb.field_get(ask[0], "key"), constants.image);
      const handle = jslb.blob_make("sink/1", undefined, {}, 88);
      const fetched = reply_to(
        ask,
        { size: constants.image_size, sha256: constants.image_sha256 },
        [handle],
      );
      bench.server.line_send(fetched);
      this.assertIn(`kv_put ${constants.image} sink/1`, store.calls);
      this.assertEqual(cache.reads, [constants.image_sha256]);
      const kept = bench.ui.last_of("media.store");
      this.assertEqual(kept.k, constants.image);
      const data = jslb.field_get(kept[1] as lines.BlobHeader, "data");
      this.assertEqual(data, new Uint8Array(constants.image_size).fill(9));
      bench.ui.line_send(reply_to(kept, {}));
      const render = bench.ui.last_of("render");
      this.assertEqual(jslb.payload_of(render), {
        scene: constants.scene,
        subtitle: constants.subtitle,
        image: constants.image,
      });
      bench.ui.line_send(reply_to(render, {}));
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // An image held in its row goes to the UI without asking the server.
    test_image_row(): void {
      const bench = bench_make();
      const store = store_seeded();
      store.open.push("metaverse", "_files");
      store.documents.set(constants.hyperposition, {
        0: { t: "scene" },
        1: constants.image,
        subtitle: constants.greeting,
        image: { $ref: 1 },
      });
      store.text_set(constants.image, "png");
      chain_make(bench, store, new CacheDouble(), []);
      chain_start(bench);
      handshake_answer(bench);
      this.assertEqual(bench.server.posted.length, 3);
      const kept = bench.ui.last_of("media.store");
      const data = jslb.field_get(kept[1] as lines.BlobHeader, "data");
      this.assertEqual(data, utility.utf8_encode("png"));
    }

    // A scene with no text subtitle or an image that is no ref is refused.
    test_scene_invalid(): void {
      for (const body of [{}, { subtitle: "Fog.", image: 3 }]) {
        const bench = bench_make();
        const store = store_seeded();
        store.open.push("metaverse", "_files");
        store.documents.set(constants.hyperposition, {
          0: { t: "scene" },
          ...body,
        });
        chain_make(bench, store, new CacheDouble(), []);
        const error = thrown_get(() => chain_start(bench));
        this.assertEqual(
          error.message,
          i18n("worker_ai.scene_invalid", constants.hyperposition),
        );
      }
    }

    // A scene named by an internal ref has no database to load.
    test_ref_internal(): void {
      const bench = bench_make();
      const store = store_seeded();
      store.open.push("metaverse", "_files");
      store.text_set("/metaverse/scene", "hyperposition/1");
      chain_make(bench, store, new CacheDouble(), []);
      const error = thrown_get(() => chain_start(bench));
      this.assertEqual(
        error.message,
        i18n("worker_ai.ref_internal", "hyperposition/1"),
      );
    }
  }

  // The provider's address and models the worker hands the agent and tools.
  export class TestProviderInfo extends unittest.TestCase {
    // Not scripted, they are the information the hello carries.
    test_info_hello(): void {
      const hello = { ...hello_make(), provider_info: constants.info };
      this.assertEqual(worker_ai.info_read(hello, false), constants.info);
    }

    // Scripted, they are empty text, and the hello carries none.
    test_info_scripted(): void {
      const hello = hello_make();
      this.assertFalse(Object.hasOwn(hello, "provider_info"));
      this.assertEqual(worker_ai.info_read(hello, true), {
        base_url: "",
        chat_model: "",
        image_model: "",
      });
    }
  }

  // The provider script, read from `_files`.
  export class TestScriptRead extends unittest.TestCase {
    // A script in its row or in the cache is read as JSON.
    test_script_parsed(): void {
      const text = '{"start":"a","nodes":{"a":{"replies":{}}}}';
      const store = new StoreDouble();
      store.text_set(constants.script_ref, text);
      const script = worker_ai.script_read(store, new CacheDouble());
      this.assertEqual(script, { start: "a", nodes: { a: { replies: {} } } });
      const cache = new CacheDouble();
      const data = utility.utf8_encode(text);
      cache.files.set("cached", data);
      store.values.set(constants.script_ref, {
        data: "cached",
        size: data.length,
        sha256: utility.sha256_hex(data),
      });
      this.assertEqual(worker_ai.script_read(store, cache), script);
    }

    // A script that is not JSON is refused, naming its ref and the cause.
    test_script_invalid(): void {
      const store = new StoreDouble();
      store.text_set(constants.script_ref, "{");
      const cause = thrown_get(() => JSON.parse("{"));
      const error = thrown_get(() =>
        worker_ai.script_read(store, new CacheDouble()),
      );
      this.assertEqual(
        error.message,
        i18n("worker_ai.script_invalid", constants.script_ref, String(cause)),
      );
    }
  }
}

Object.freeze(test_worker_ai);
