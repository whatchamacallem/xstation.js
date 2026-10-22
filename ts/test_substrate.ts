// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of substrate.ts: refs, the document encoding, the sink's incremental
// hash against known digests, the cache over slot files kept in memory, and
// the store on the sqlite3.wasm module and OPFS pool the test page sets as
// globals: databases, values, documents, turns, compaction at the threshold,
// SQL, seq, snapshots, forwarded lines, the operations of the castle turn and
// two later ones replayed on a second store, the administration of the
// databases, cached values filled back and freed by budget, a put stopped
// between its cache file and its row, and the handlers. It also holds the
// pause point of that stop, which a browser rung uses to kill a worker of the
// test page there.
namespace test_substrate {
  // The initialized sqlite3.wasm module, a global the test page sets.
  declare const test_sqlite3: substrate.SqliteModule;

  // Its installed OPFS SAH pool, a global the test page sets.
  declare const test_pool: substrate.SqlitePool;

  // The settings, names, texts and digests the tests use.
  const constants = Object.freeze({
    // The `overflow_bytes` of `settings.json`, 128 KiB.
    overflow_bytes: 131072,
    // The `db_soft_bytes` of `settings.json`, 1 GiB.
    soft_bytes: 1073741824,
    // The `turn_compact_turns` of `settings.json`, 64.
    compact_turns: 64,
    // A count chosen by its writer: a threshold a test reaches in a few turns.
    compact_small: 3,
    // The start of the root of each store a test makes in the pool.
    root_prefix: "/test_substrate/",
    // A count chosen by its writer: the files of each test store's cache.
    slot_count: 8,
    // The bytes at the start of a cache file that hold its name.
    name_bytes: 64,
    // A size chosen by its writer: the bytes streamed into a sink at once.
    piece_bytes: 4096,
    // The hyperposition scene, whose conversation the turn tests append to.
    scene: "/metaverse/hyperposition/1",
    // The subtitle of the arrival scene the castle turn builds.
    arrival_subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    // The prompt of the arrival scene's image.
    image_prompt:
      "A rain dark castle gatehouse at dusk seen from the far side of a" +
      " moat, one lantern lit, painted, wide still frame, no people",
    // The arrival scene's image, a checkerboard PNG of 88 bytes, in base64.
    image_base64:
      "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAH0lEQVR42mP4jwQYkAAuc" +
      "YZBqGGQO48oDaPxMCg0AADZV36QzYI8swAAAABJRU5ErkJggg==",
    // The step script that advances the tide of a region, 322 bytes.
    step_script:
      "// Advances the tide by args.hours in the region table" +
      " of the world.\n" +
      'const results = engine.store.sql_run("castle_world", [\n' +
      '  {sql: "UPDATE region SET tide = tide + ? WHERE name = ?",\n' +
      '    params: [args.hours, "castle_gatehouse"]},\n' +
      "]);\n" +
      'engine.log(1, "tide advanced by " + args.hours);\n' +
      "return {changes: results[0].changes};\n",
    // The `SHA-256` of the text `castle_world`.
    world_sha256:
      "6d0be246127ef7993924a9ce127c6fa6c093dca368163093ab31c80273336ecd",
    // The `SHA-256` of the arrival scene's ref as text.
    scene_sha256:
      "1e2806a1029564579de9739ef0014f0332c5a8026bca9373e473224a3b094d8b",
    // The `SHA-256` of the image.
    image_sha256:
      "90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0",
    // The `SHA-256` of the map, its bytes counting 0 to 255 over and over.
    map_sha256:
      "8c6627e25bfbdef2bba5abc03123ea8e9b60d892f7f180a8b9b5079fb3233c54",
    // The `SHA-256` of the step script.
    script_sha256:
      "dbc909cf0e2e7954d586c06b3291728e527d5dee4c109409fcb501e200756626",
    // A size chosen by its writer: the map's bytes, past `overflow_bytes`.
    map_bytes: 204800,
    // The universe table, as the metaverse SQL file creates it.
    universe_sql:
      "CREATE TABLE universe (name TEXT PRIMARY KEY, title TEXT NOT NULL," +
      " player TEXT NOT NULL, world TEXT NOT NULL) WITHOUT ROWID, STRICT",
    // The world table of the castle universe.
    world_sql:
      "CREATE TABLE world" +
      " (name TEXT PRIMARY KEY, title TEXT NOT NULL) STRICT",
    // The region table of the castle world.
    region_sql:
      "CREATE TABLE region" +
      " (name TEXT PRIMARY KEY, tide INTEGER NOT NULL DEFAULT 0) STRICT",
    // The `_meta` table alone, as the substrate's SQL file creates it.
    meta_sql:
      "CREATE TABLE _meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)" +
      " WITHOUT ROWID, STRICT",
    // Text beyond ASCII for keys and values, built from its code points.
    text_wide: String.fromCodePoint(0x4e2d, 0x6587, 0x1f600),
    // The first bytes of a database file.
    file_magic: "SQLite format 3",
    // The database and key of the put that a kill stops.
    kill_db: "alpha",
    kill_key: "big",
    // The start of the SQL that writes a row to `_kv`.
    row_insert: "INSERT INTO _kv ",
    // The message of the stop that stands for the kill in the unit test.
    kill_message: "The put stopped between its cache file and its row.",
    // The start of the SQL that writes the first of the substrate's tables.
    schema_create: "CREATE TABLE _meta ",
    // The message of the failure the test makes where the schema is written.
    schema_message: "The schema failed where the test made it fail.",
  });

  // The number of the last root a test made, so that each store has its own.
  let root_count = 0;

  // One forwarded operation: its fields, the `seq` after, its line and digest.
  interface RecordedOperation {
    type: string;
    since: number;
    fields: { [key: string]: unknown };
    seq: number;
    text?: string;
    sha256?: string;
  }

  // Bytes that count up from 0 and start again at 256, as many as asked.
  function bytes_pattern(count: number): Uint8Array {
    const data = new Uint8Array(count);
    for (let index = 0; index < count; index += 1) {
      data[index] = index % 256;
    }
    return data;
  }

  // The `UTF-8` bytes of text.
  function bytes_text(text: string): Uint8Array {
    return utility.utf8_encode(text);
  }

  // The bytes of the pieces one after another.
  function bytes_join(pieces: readonly Uint8Array[]): Uint8Array {
    let length = 0;
    for (const piece of pieces) {
      length += piece.length;
    }
    const joined = new Uint8Array(length);
    let offset = 0;
    for (const piece of pieces) {
      joined.set(piece, offset);
      offset += piece.length;
    }
    return joined;
  }

  // A copy of the bytes in reverse order.
  function bytes_reversed(data: Uint8Array): Uint8Array {
    return data.slice().reverse();
  }

  // The message of the role with the text.
  function message_said(
    role: provider.Role,
    content: string,
  ): provider.ChatMessage {
    return { role, content };
  }

  // A value of exactly `overflow_bytes`, which stays in its row.
  function value_exact(): Uint8Array {
    return bytes_pattern(constants.overflow_bytes);
  }

  // A value one byte over `overflow_bytes`, which goes to the cache.
  function value_over(): Uint8Array {
    return bytes_pattern(constants.overflow_bytes + 1);
  }

  // A cache file double kept in memory, with the calls OPFS gives.
  class MemorySlot implements substrate.SlotHandle {
    // The storage, grown by doubling, zero beyond the file.
    #store = new Uint8Array(0);
    // The size of the file.
    #size = 0;

    // A copy of the bytes of the file.
    bytes_get(): Uint8Array {
      return this.#store.slice(0, this.#size);
    }

    // Replaces the bytes of the file.
    bytes_set(data: Uint8Array): void {
      this.#store = data.slice();
      this.#size = data.length;
    }

    // Reads into the buffer from the offset, as many bytes as the file has.
    read(buffer: Uint8Array, options: { at: number }): number {
      const left = this.#size - options.at;
      const count = Math.max(0, Math.min(buffer.length, left));
      buffer.set(this.#store.subarray(options.at, options.at + count));
      return count;
    }

    // Writes the buffer at the offset, the file growing with zeros.
    write(buffer: Uint8Array, options: { at: number }): number {
      const end = options.at + buffer.length;
      this.#room_make(end);
      this.#store.set(buffer, options.at);
      this.#size = Math.max(this.#size, end);
      return buffer.length;
    }

    // Sets the size, cutting the file or growing it with zeros.
    truncate(size: number): void {
      this.#room_make(size);
      this.#store.fill(0, Math.min(size, this.#size));
      this.#size = size;
    }

    // The size of the file.
    getSize(): number {
      return this.#size;
    }

    // Grows the storage by doubling until it holds the size.
    #room_make(size: number): void {
      if (size <= this.#store.length) {
        return;
      }
      const grown = new Uint8Array(Math.max(size, 2 * this.#store.length));
      grown.set(this.#store);
      this.#store = grown;
    }
  }

  // A cache file double whose reads and writes fall one byte short when told.
  class ShortSlot extends MemorySlot {
    // Whether reads and writes report one byte fewer than they moved.
    short = false;

    // Reads as the double does, reporting one byte fewer when short.
    read(buffer: Uint8Array, options: { at: number }): number {
      const count = super.read(buffer, options);
      return this.short ? count - 1 : count;
    }

    // Writes as the double does, reporting one byte fewer when short.
    write(buffer: Uint8Array, options: { at: number }): number {
      const count = super.write(buffer, options);
      return this.short ? count - 1 : count;
    }
  }

  // Empty cache file doubles, as many as asked.
  function slots_make(count: number): MemorySlot[] {
    return Array.from({ length: count }, () => new MemorySlot());
  }

  // A cache file double holding a stored value under its name.
  function slot_stored(name: string, data: Uint8Array): MemorySlot {
    const slot = new MemorySlot();
    slot.bytes_set(bytes_join([bytes_text(name), data]));
    return slot;
  }

  // A cache over empty file doubles.
  function cache_make(): substrate.CacheFiles {
    return new substrate.CacheFiles(slots_make(constants.slot_count));
  }

  // Streams bytes into a cache's sink in pieces and returns the handle.
  function sink_fill(cache: substrate.CacheFiles, data: Uint8Array): string {
    const handle = cache.sink_open({ s: data.length });
    const step = constants.piece_bytes;
    for (let offset = 0; offset < data.length; offset += step) {
      cache.sink_append(handle, data.subarray(offset, offset + step));
    }
    cache.sink_close(handle);
    return handle;
  }

  // The hash a fresh sink returns for bytes streamed in pieces of a size.
  function digest_streamed(data: Uint8Array, piece: number): string {
    const cache = new substrate.CacheFiles(slots_make(1));
    const handle = cache.sink_open({ s: data.length });
    for (let offset = 0; offset < data.length; offset += piece) {
      cache.sink_append(handle, data.subarray(offset, offset + piece));
    }
    return cache.sink_close(handle);
  }

  // The reply the server gives a forwarded line: `seq` one past `since`.
  function reply_make(line: lines.Line): lines.Line {
    const type = jslb.field_get(line[0], "type") as string;
    const header = jslb.header_make(type, { reply: 1 });
    if (type === "db.create" || type === "db.drop") {
      return jslb.line_make(header, [], {});
    }
    const since = jslb.payload_of(line).since as number;
    return jslb.line_make(header, [], { seq: since + 1 });
  }

  // A request line of the UI thread with its id, ref, blobs and payload.
  function request_make(
    type: string,
    id: number,
    payload: { [key: string]: unknown },
    key?: string,
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, { id, key }), blobs, payload);
  }

  // The rows of one statement a store runs.
  function rows_query(
    store: substrate.Store,
    db: string,
    sql: string,
  ): unknown[][] {
    return store.sql_run(db, [{ sql, params: [] }])[0].rows;
  }

  // The schema and the rows of every table of a database, in order.
  function content_dump(store: substrate.Store, db: string): unknown[] {
    const schema = rows_query(
      store,
      db,
      "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY name",
    );
    const dump: unknown[] = [schema];
    for (const row of schema) {
      if (row[0] === "table") {
        dump.push(rows_query(store, db, `SELECT * FROM "${String(row[1])}"`));
      }
    }
    return dump;
  }

  // The names of the tables of a database, in order.
  function tables_list(store: substrate.Store, db: string): string[] {
    const rows = rows_query(
      store,
      db,
      "SELECT name FROM sqlite_schema WHERE type = 'table' ORDER BY name",
    );
    return rows.map((row) => row[0] as string);
  }

  // The number the first row of a pragma holds.
  function pragma_read(
    store: substrate.Store,
    db: string,
    name: string,
  ): number {
    return rows_query(store, db, `PRAGMA ${name}`)[0][0] as number;
  }

  // The measure of a database read through SQL, as the heuristics define it.
  function stats_measured(
    store: substrate.Store,
    db: string,
    cache_bytes: number,
  ): substrate.DatabaseStats {
    const page_size = pragma_read(store, db, "page_size");
    return {
      name: db,
      bytes: pragma_read(store, db, "page_count") * page_size + cache_bytes,
      free_bytes: pragma_read(store, db, "freelist_count") * page_size,
      cache_bytes,
      seq: store.seq_get(db),
    };
  }

  // The database a forwarded operation modifies.
  function target_database(record: RecordedOperation): string {
    const fields = record.fields;
    if (Object.hasOwn(fields, "db")) {
      return fields.db as string;
    }
    const ref = Object.hasOwn(fields, "k") ? fields.k : fields.scene;
    return substrate.ref_split(ref as string).db as string;
  }

  // The payload a server applies for a forwarded line, its blob streamed.
  function payload_replayed(
    line: lines.Line,
    from: substrate.CacheFiles,
    to: substrate.CacheFiles,
  ): { [key: string]: unknown } {
    const payload = Object.fromEntries(
      Object.entries(jslb.payload_of(line)).filter(([key]) => key !== "since"),
    );
    if (jslb.field_get(line[0], "type") !== "kv.put") {
      return payload;
    }
    const k = jslb.field_get(line[0], "key");
    const blob = line[1] as lines.BlobHeader;
    const data = blob.d as Uint8Array | string;
    if (typeof data !== "string") {
      return { k, data };
    }
    return { k, data: sink_fill(to, from.cache_read(data, 0, blob.s)) };
  }

  // The arrival scene of the castle gatehouse in its stored form.
  function arrival_make(): lines.Document {
    return {
      0: { t: "scene" },
      1: "/_files/gatehouse/arrival.png",
      subtitle: constants.arrival_subtitle,
      image: { $ref: 1 },
    };
  }

  // The stored text of the arrival scene, its encoded document as JSON.
  function arrival_stored(): string {
    return (
      '{"0":{"t":"scene"},"1":"/_files/gatehouse/arrival.png","subtitle":"' +
      constants.arrival_subtitle +
      '","image":{"$ref":1}}'
    );
  }

  // A document in its normal form, with refs, shared refs and plain text.
  function fog_normal(): { [key: string]: unknown } {
    return {
      0: { t: "scene", v: 2 },
      subtitle: "Fog " + constants.text_wide,
      image: "/_files/fog.png",
      links: [
        "/metaverse/world",
        { to: "/_files/fog.png", note: "/not a ref" },
      ],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // That document encoded, its refs moved into headers 1 and 2.
  function fog_encoded(): lines.Document {
    return {
      0: { t: "scene", v: 2 },
      1: "/_files/fog.png",
      2: "/metaverse/world",
      subtitle: "Fog " + constants.text_wide,
      image: { $ref: 1 },
      links: [{ $ref: 2 }, { to: { $ref: 1 }, note: "/not a ref" }],
      local: "world",
      slash: "/",
      count: 3,
      ratio: 0.5,
      shown: true,
      none: null,
    };
  }

  // A document with integer keys below the top level.
  function nested_make(): lines.Document {
    return {
      0: { t: "nest" },
      1: "/_files/fog.png",
      inner: {
        b: 1,
        2: constants.text_wide,
        a: [{ z: null, 0: 0.5 }],
        1: { $ref: 1 },
      },
      count: -3,
    };
  }

  // An assistant message with tool calls: id, function name, arguments.
  function calls_make(
    calls: readonly (readonly [string, string, string])[],
  ): provider.ChatMessage {
    return {
      role: "assistant",
      content: null,
      tool_calls: calls.map(([id, name, args]): provider.ToolCall => ({
        id,
        type: "function",
        function: { name, arguments: args },
      })),
    };
  }

  // The forwarded operations of the castle turn and two later ones, in order.
  function recorded_make(): RecordedOperation[] {
    const scene = constants.scene;
    const subtitle = constants.arrival_subtitle;
    const image = "/_files/gatehouse/arrival.png";
    const script = utility.json_text({
      name: "bootstrap",
      args: {
        universe: "castle",
        title: "The castle",
        world: "castle_world",
        region: "castle_gatehouse",
      },
    });
    const drawn = utility.json_text({
      prompt: constants.image_prompt,
      key: image,
    });
    const document = utility.json_text({
      db: "castle_gatehouse",
      id: "scene/arrival",
      body: arrival_make(),
    });
    const pointer = utility.json_text({
      ref: "/castle_world/scene",
      text: "/castle_gatehouse/scene/arrival/1",
    });
    const rendered = utility.json_text({ image, subtitle });
    const user: provider.ChatMessage = { role: "user", content: "1" };
    const final: provider.ChatMessage = {
      role: "assistant",
      content: subtitle,
    };
    return [
      {
        type: "turn.append",
        since: 5,
        fields: { scene, role: "user", content: user },
        seq: 6,
        text:
          '{"0":{"t":"turn.append"},"scene":"/metaverse/hyperposition/1",' +
          '"role":"user","content":{"role":"user","content":"1"},"since":5}',
      },
      {
        type: "turn.append",
        since: 6,
        fields: {
          scene,
          role: "assistant",
          content: calls_make([["call_1", "browser.script_run", script]]),
        },
        seq: 7,
      },
      {
        type: "db.create",
        since: 0,
        fields: { db: "castle" },
        seq: 0,
        text: '{"0":{"t":"db.create"},"db":"castle","since":0}',
      },
      {
        type: "sql.run",
        since: 0,
        fields: {
          db: "castle",
          statements: [
            { sql: constants.world_sql, params: [] },
            {
              sql: "INSERT INTO world VALUES (?, ?)",
              params: ["castle_world", "The castle"],
            },
          ],
        },
        seq: 1,
        text:
          '{"0":{"t":"sql.run"},"db":"castle","statements":[{"sql":"' +
          constants.world_sql +
          '","params":[]},{"sql":"INSERT INTO world VALUES (?, ?)",' +
          '"params":["castle_world","The castle"]}],"since":0}',
      },
      {
        type: "db.create",
        since: 0,
        fields: { db: "castle_world" },
        seq: 0,
        text: '{"0":{"t":"db.create"},"db":"castle_world","since":0}',
      },
      {
        type: "sql.run",
        since: 0,
        fields: {
          db: "castle_world",
          statements: [
            { sql: constants.region_sql, params: [] },
            {
              sql: "INSERT INTO region (name) VALUES (?)",
              params: ["castle_gatehouse"],
            },
          ],
        },
        seq: 1,
        text:
          '{"0":{"t":"sql.run"},"db":"castle_world","statements":[{"sql":"' +
          constants.region_sql +
          '","params":[]},{"sql":"INSERT INTO region (name) VALUES (?)",' +
          '"params":["castle_gatehouse"]}],"since":0}',
      },
      {
        type: "db.create",
        since: 0,
        fields: { db: "castle_gatehouse" },
        seq: 0,
        text: '{"0":{"t":"db.create"},"db":"castle_gatehouse","since":0}',
      },
      {
        type: "sql.run",
        since: 7,
        fields: {
          db: "metaverse",
          statements: [
            {
              sql: "INSERT INTO universe VALUES (?, ?, ?, ?)",
              params: ["castle", "The castle", "player", "castle_world"],
            },
          ],
        },
        seq: 8,
        text:
          '{"0":{"t":"sql.run"},"db":"metaverse","statements":[{"sql":' +
          '"INSERT INTO universe VALUES (?, ?, ?, ?)","params":["castle",' +
          '"The castle","player","castle_world"]}],"since":7}',
      },
      {
        type: "kv.put",
        since: 8,
        fields: { k: "/metaverse/world", data: bytes_text("castle_world") },
        seq: 9,
        text:
          '{"0":{"t":"kv.put","k":"/metaverse/world","b":1},' +
          '"1":{"s":12},"since":8}<blob "n"=1>',
        sha256: constants.world_sha256,
      },
      {
        type: "turn.append",
        since: 9,
        fields: {
          scene,
          role: "assistant",
          content: calls_make([["call_2", "browser.image_make", drawn]]),
        },
        seq: 10,
      },
      {
        type: "kv.put",
        since: 1,
        fields: {
          k: image,
          data: utility.base64_decode(constants.image_base64),
        },
        seq: 2,
        text:
          '{"0":{"t":"kv.put","k":"/_files/gatehouse/arrival.png","b":1},' +
          '"1":{"s":88},"since":1}<blob "n"=1>',
        sha256: constants.image_sha256,
      },
      {
        type: "turn.append",
        since: 10,
        fields: {
          scene,
          role: "assistant",
          content: calls_make([
            ["call_3", "browser.doc_put", document],
            ["call_4", "browser.kv_put", pointer],
            ["call_5", "browser.render", rendered],
          ]),
        },
        seq: 11,
      },
      {
        type: "doc.put",
        since: 0,
        fields: {
          db: "castle_gatehouse",
          id: "scene/arrival",
          body: arrival_make(),
        },
        seq: 1,
        text:
          '{"0":{"t":"doc.put"},"db":"castle_gatehouse",' +
          '"id":"scene/arrival","body":' +
          arrival_stored() +
          ',"since":0}',
      },
      {
        type: "kv.put",
        since: 1,
        fields: {
          k: "/castle_world/scene",
          data: bytes_text("/castle_gatehouse/scene/arrival/1"),
        },
        seq: 2,
        text:
          '{"0":{"t":"kv.put","k":"/castle_world/scene","b":1},' +
          '"1":{"s":33},"since":1}<blob "n"=1>',
        sha256: constants.scene_sha256,
      },
      {
        type: "turn.append",
        since: 11,
        fields: { scene, role: "assistant", content: final },
        seq: 12,
        text:
          '{"0":{"t":"turn.append"},"scene":"/metaverse/hyperposition/1",' +
          '"role":"assistant","content":{"role":"assistant","content":"' +
          subtitle +
          '"},"since":11}',
      },
      {
        type: "sql.run",
        since: 1,
        fields: {
          db: "castle",
          statements: [
            {
              sql: "UPDATE world SET title = ? WHERE name = ?",
              params: ["The castle at dusk", "castle_world"],
            },
          ],
        },
        seq: 2,
        text:
          '{"0":{"t":"sql.run"},"db":"castle","statements":[{"sql":' +
          '"UPDATE world SET title = ? WHERE name = ?","params":' +
          '["The castle at dusk","castle_world"]}],"since":1}',
      },
      {
        type: "kv.put",
        since: 2,
        fields: {
          k: "/_files/maps/castle.bin",
          data: bytes_pattern(constants.map_bytes),
        },
        seq: 3,
        text:
          '{"0":{"t":"kv.put","k":"/_files/maps/castle.bin","b":1},' +
          '"1":{"s":204800},"since":2}<blob "n"=1>',
        sha256: constants.map_sha256,
      },
    ];
  }

  // A database of the pool that runs `stop` before SQL with a given start.
  class StoppedDatabase implements substrate.SqliteDatabase {
    // The database of the pool.
    readonly #inner: substrate.SqliteDatabase;
    // What runs in place of the SQL.
    readonly #stop: () => never;
    // The start of the SQL that the stop runs before.
    readonly #prefix: string;

    // Takes the database it wraps, the stop and the start of the SQL.
    constructor(
      inner: substrate.SqliteDatabase,
      stop: () => never,
      prefix: string,
    ) {
      this.#inner = inner;
      this.#stop = stop;
      this.#prefix = prefix;
    }

    // The `sqlite3` pointer of the connection.
    get pointer(): number {
      return this.#inner.pointer;
    }

    // Runs the SQL, stopping before it when it starts with the prefix.
    exec(options: substrate.ExecOptions): unknown {
      if (options.sql.startsWith(this.#prefix)) {
        this.#stop();
      }
      return this.#inner.exec(options);
    }

    // The first column of the first row the SQL returns.
    selectValue(sql: string, bind?: unknown[]): unknown {
      return this.#inner.selectValue(sql, bind);
    }

    // Prepares the first statement of the SQL.
    prepare(sql: string): substrate.SqliteStatement {
      return this.#inner.prepare(sql);
    }

    // The rows the last statement changed, or all since opening when total.
    changes(total: boolean): number {
      return this.#inner.changes(total);
    }

    // Closes the connection.
    close(): void {
      this.#inner.close();
    }
  }

  // The pool's files, its databases stopping before SQL with the start.
  function pool_stopped(
    pool: substrate.SqlitePool,
    stop: () => never,
    prefix: string,
  ): substrate.SqlitePool {
    // The pool's database class, its databases wrapped to stop.
    class PausedDatabase extends StoppedDatabase {
      // Opens the file as the pool's own class does.
      constructor(options: { filename: string; flags: string }) {
        super(new pool.OpfsSAHPoolDb(options), stop, prefix);
      }
    }
    return {
      OpfsSAHPoolDb: PausedDatabase,
      getFileNames: () => pool.getFileNames(),
      importDb: (name, bytes) => pool.importDb(name, bytes),
      unlink: (name) => pool.unlink(name),
    };
  }

  // The pause point: the pool's files, its databases stopping before a row.
  export function kill_pool(
    pool: substrate.SqlitePool,
    stop: () => never,
  ): substrate.SqlitePool {
    return pool_stopped(pool, stop, constants.row_insert);
  }

  // Creates `alpha` and puts a value over `overflow_bytes` under `big` in it.
  export function kill_put(store: substrate.Store): void {
    store.db_create(constants.kill_db);
    store.kv_put(`/${constants.kill_db}/${constants.kill_key}`, value_over());
  }

  // Says it is paused, then holds the worker in a loop until it is killed.
  export function kill_hold(paused: () => void): never {
    paused();
    for (;;) {}
  }

  // Opens `alpha` after the kill: the rows of `big`, the files then removed.
  export function kill_check(store: substrate.Store): {
    rows: number;
    removed: number;
  } {
    store.db_open(constants.kill_db);
    return {
      rows: store.kv_list(constants.kill_db, constants.kill_key).length,
      removed: store.kv_check(constants.kill_db),
    };
  }

  // A test case with the asserts of a refusal and its message.
  class RefusalCase extends unittest.TestCase {
    // Asserts the call throws a plain `Error` with exactly the message.
    raised_assert(message: string, fn: () => unknown, note?: string): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor === Error) {
          this.assertEqual(error.message, message, note);
          return;
        }
        throw error;
      }
      const standard = "Error not raised";
      this.fail(note === undefined ? standard : `${standard} : ${note}`);
    }

    // Asserts the call throws an error of SQLite holding the text.
    sqlite_assert(text: string, fn: () => unknown): void {
      try {
        fn();
      } catch (error) {
        if (error instanceof Error && error.constructor !== Error) {
          this.assertIn(text, error.message);
          return;
        }
        throw error;
      }
      this.fail("SQLite raised nothing");
    }
  }

  // A store test: the module and pool read in `setUp`, its roots removed.
  class StoreCase extends RefusalCase {
    // The module the test page provides, read in `setUp`.
    #sqlite: substrate.SqliteModule | undefined = undefined;
    // The pool the test page provides, read in `setUp`.
    #pool: substrate.SqlitePool | undefined = undefined;
    // The roots this test made.
    readonly #roots: string[] = [];
    // The stores this test made, each with the lines it forwarded.
    readonly #stores = new Map<substrate.Store, lines.Line[]>();

    // Reads the module and the pool the test page provides.
    setUp(): void {
      this.#sqlite = test_sqlite3;
      this.#pool = test_pool;
    }

    // Closes every database of the stores and removes the roots' files.
    tearDown(): void {
      for (const store of this.#stores.keys()) {
        for (const name of store.db_list()) {
          store.db_close(name);
        }
      }
      const pool = this.pool_get();
      for (const root of this.#roots) {
        for (const file of pool.getFileNames()) {
          if (file.startsWith(`${root}/`)) {
            pool.unlink(file);
          }
        }
      }
    }

    // The module the test page provides.
    sqlite_get(): substrate.SqliteModule {
      return this.#sqlite as substrate.SqliteModule;
    }

    // The pool the test page provides.
    pool_get(): substrate.SqlitePool {
      return this.#pool as substrate.SqlitePool;
    }

    // A new root no other test uses.
    root_make(): string {
      root_count += 1;
      const root = constants.root_prefix + String(root_count);
      this.#roots.push(root);
      return root;
    }

    // A store on the root, keeping its forwarded lines when it forwards.
    store_make(
      root: string,
      cache: substrate.CacheFiles,
      forwards: boolean,
      pool: substrate.SqlitePool = this.pool_get(),
      compact_turns: number = constants.compact_turns,
    ): substrate.Store {
      const store = new substrate.Store(
        this.sqlite_get(),
        pool,
        cache,
        root,
        constants.overflow_bytes,
        compact_turns,
      );
      const forwarded: lines.Line[] = [];
      if (forwards) {
        store.forward_set((line) => {
          forwarded.push(line);
        }, false);
      }
      this.#stores.set(store, forwarded);
      return store;
    }

    // A forwarding store on a new root with a new cache.
    store_fresh(): substrate.Store {
      return this.store_make(this.root_make(), cache_make(), true);
    }

    // The lines a store forwarded that were not answered.
    lines_of(store: substrate.Store): lines.Line[] {
      return this.#stores.get(store) as lines.Line[];
    }

    // Answers every line a store forwarded, as the server would.
    lines_answer(store: substrate.Store): void {
      for (const line of this.lines_of(store).splice(0)) {
        store.forward_done(line, reply_make(line));
      }
    }

    // The rendered lines a store forwarded, which are then let go.
    lines_taken(store: substrate.Store): string[] {
      return this.lines_of(store)
        .splice(0)
        .map((line) => jslb.line_render(line));
    }

    // The names of the files under a root, in order.
    files_under(root: string): string[] {
      const prefix = `${root}/`;
      return this.pool_get()
        .getFileNames()
        .filter((file) => file.startsWith(prefix))
        .map((file) => file.slice(prefix.length))
        .sort();
    }

    // Opens a file of the pool apart from any store.
    raw_open(path: string, flags: string): substrate.SqliteDatabase {
      const pool = this.pool_get();
      return new pool.OpfsSAHPoolDb({ filename: path, flags });
    }

    // Runs statements on a file of the pool apart from any store.
    raw_run(
      path: string,
      flags: string,
      statements: substrate.ExecOptions[],
    ): void {
      const database = this.raw_open(path, flags);
      try {
        for (const statement of statements) {
          database.exec(statement);
        }
      } finally {
        database.close();
      }
    }

    // The serialized bytes of a file of the pool, read apart from any store.
    raw_export(path: string): Uint8Array {
      const database = this.raw_open(path, "r");
      try {
        return this.sqlite_get().capi.sqlite3_js_db_export(database.pointer);
      } finally {
        database.close();
      }
    }
  }

  // `Key-Value-Ref` and `Document-Ref` splitting, bad refs, their database.
  export class TestRefs extends StoreCase {
    // Each form splits into its database, its key and its version.
    test_split_forms(): void {
      const cases: [string, substrate.RefParts][] = [
        [
          constants.scene,
          { db: "metaverse", key: "hyperposition/1", version: 1 },
        ],
        ["/metaverse/world", { db: "metaverse", key: "world" }],
        ["script/bootstrap.js", { key: "script/bootstrap.js" }],
        ["scene/arrival/12", { key: "scene/arrival/12", version: 12 }],
        ["/_files/a//b/", { db: "_files", key: "a//b/" }],
        ["maps/01", { key: "maps/01" }],
        ["7", { key: "7" }],
        [
          "/x/" + constants.text_wide + "/0",
          { db: "x", key: constants.text_wide + "/0", version: 0 },
        ],
        ["/x/line\nbreak", { db: "x", key: "line\nbreak" }],
      ];
      for (const [ref, parts] of cases) {
        this.assertEqual(substrate.ref_split(ref), parts, ref);
      }
    }

    // An empty ref, a missing key and a bad database name throw.
    test_refs_bad(): void {
      const refs = [
        "",
        "/",
        "//key",
        "/metaverse",
        "/metaverse/",
        "/1db/key",
        "/d-b/key",
        "/caf" + String.fromCodePoint(0xe9) + "/key",
      ];
      for (const ref of refs) {
        this.raised_assert(i18n("substrate.ref_bad", ref), () =>
          substrate.ref_split(ref),
        );
      }
    }

    // An internal ref needs a database and an external ref takes none.
    test_ref_database(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const value = bytes_text("x");
      this.raised_assert(i18n("substrate.ref_internal", "world"), () =>
        store.kv_put("world", value),
      );
      const both = i18n("substrate.ref_both", "/alpha/world", "alpha");
      this.raised_assert(both, () =>
        store.kv_put("/alpha/world", value, "alpha"),
      );
      this.raised_assert(both, () => store.kv_get("/alpha/world", "alpha"));
      this.raised_assert(i18n("substrate.db_closed", "beta"), () =>
        store.kv_put("/beta/world", value),
      );
      this.raised_assert(i18n("substrate.document_ref", "/alpha/world"), () =>
        store.doc_get("/alpha/world"),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
    }
  }

  // Documents: versions and heads, the round trip, reference strings, faults.
  export class TestDocuments extends StoreCase {
    // Each put writes the next version and moves the head, versions stay.
    test_document_heads(): void {
      const store = this.store_fresh();
      const db = "castle_gatehouse";
      store.db_create(db);
      const first = store.doc_put(db, "scene/arrival", arrival_make());
      this.assertEqual(first, {
        ref: "/castle_gatehouse/scene/arrival/1",
        seq: 1,
      });
      this.assertEqual(store.doc_head(db, "scene/arrival"), first.ref);
      this.assertEqual(
        store.kv_get(first.ref).data,
        bytes_text(arrival_stored()),
      );
      const changed = { ...arrival_make(), subtitle: "The keeper waves." };
      const second = store.doc_put(db, "scene/arrival", changed);
      this.assertEqual(second, {
        ref: "/castle_gatehouse/scene/arrival/2",
        seq: 2,
      });
      this.assertEqual(store.doc_head(db, "scene/arrival"), second.ref);
      this.assertEqual(store.doc_get(first.ref), arrival_make());
      const text = utility.json_text(store.doc_get(first.ref));
      this.assertEqual(text, arrival_stored());
      this.assertEqual(store.doc_get("scene/arrival/2", db), changed);
      this.raised_assert(
        i18n("substrate.id_missing", "scene/absent", db),
        () => store.doc_head(db, "scene/absent"),
      );
      this.raised_assert(
        i18n("substrate.key_missing", "scene/arrival/3", db),
        () => store.doc_get("/castle_gatehouse/scene/arrival/3"),
      );
      this.raised_assert(
        i18n("substrate.document_ref", "/castle_gatehouse/scene/arrival"),
        () => store.doc_get("/castle_gatehouse/scene/arrival"),
      );
    }

    // A put whose next version is already a row throws and moves no head.
    test_version_exists(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/note/1", bytes_text("{}"));
      this.raised_assert(
        i18n("substrate.version_exists", "note/1", "alpha"),
        () => store.doc_put("alpha", "note", { 0: { t: "note" } }),
      );
      this.raised_assert(i18n("substrate.id_missing", "note", "alpha"), () =>
        store.doc_head("alpha", "note"),
      );
      this.assertEqual(store.seq_get("alpha"), 1);
    }

    // A nested document is stored as the text the wire's encoder writes.
    test_nested_text(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const ref = store.doc_put("alpha", "nest", nested_make()).ref;
      const stored = store.kv_get(ref).data as Uint8Array;
      const line = jslb.line_make(jslb.header_make("doc.put"), [], {
        db: "alpha",
        id: "nest",
        body: nested_make(),
      });
      this.assertEqual(jslb.line_encode(line), [
        bytes_join([
          bytes_text('{"0":{"t":"doc.put"},"db":"alpha","id":"nest","body":'),
          stored,
          bytes_text("}\r"),
        ]),
      ]);
      this.assertEqual(store.doc_get(ref), nested_make());
    }

    // Encoding moves refs into shared headers and decoding restores them.
    test_round_trip(): void {
      const encoded = substrate.doc_encode(fog_normal());
      this.assertEqual(encoded, fog_encoded());
      this.assertEqual(
        utility.json_text(encoded),
        utility.json_text(fog_encoded()),
      );
      const decoded = substrate.doc_decode(encoded);
      this.assertEqual(decoded, fog_normal());
      this.assertEqual(
        utility.json_text(decoded),
        utility.json_text(fog_normal()),
      );
    }

    // Documents that would not round trip, or are malformed, throw.
    test_documents_bad(): void {
      const normals: [{ [key: string]: unknown }, string][] = [
        [{ subtitle: "x" }, i18n("substrate.header_missing")],
        [
          { 0: { t: "scene", v: 0 } },
          i18n("substrate.header_bad", '{"t":"scene","v":0}'),
        ],
        [{ 0: { v: 2 } }, i18n("substrate.header_bad", '{"v":2}')],
        [
          { 0: { t: "scene", x: 1 } },
          i18n("substrate.header_bad", '{"t":"scene","x":1}'),
        ],
        [{ 0: "scene" }, i18n("substrate.header_bad", "scene")],
        [
          { 0: { t: "scene" }, 1: "/a/b" },
          i18n("substrate.header_normal", "1"),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, i18n("substrate.key_digits", "07")],
        [
          { 0: { t: "scene" }, x: { $ref: 1 } },
          i18n("substrate.ref_shape", '{"$ref":1}'),
        ],
      ];
      for (const [normal, message] of normals) {
        this.raised_assert(message, () => substrate.doc_encode(normal));
      }
      const encodeds: [lines.Document, string][] = [
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: 2 } },
          i18n("substrate.ref_index", 2),
        ],
        [
          { 0: { t: "scene" }, 2: "/a/b", x: { $ref: 2 } },
          i18n("substrate.header_gap", "2"),
        ],
        [
          { 0: { t: "scene" }, 1: 5, x: { $ref: 1 } },
          i18n("substrate.header_ref", 1),
        ],
        [
          { 0: { t: "scene" }, 1: "world", x: { $ref: 1 } },
          i18n("substrate.header_ref", 1),
        ],
        [
          { 0: { t: "scene" }, 1: "/a/b", x: { $ref: true } },
          i18n("substrate.ref_index", true),
        ],
        [{ 0: { t: "scene" }, "07": "x" }, i18n("substrate.key_digits", "07")],
      ];
      for (const [encoded, message] of encodeds) {
        this.raised_assert(message, () => substrate.doc_decode(encoded));
      }
    }

    // A string whose key holds a space, as Python counts space, stays text.
    test_spaces_kept(): void {
      const lines_kept = [
        "/me/ waves and leaves",
        "/me/waves and\nleaves",
        "/me/a b",
      ];
      const python_spaces = [0x1c, 0x1f, 0x85].map(
        (point) => "/me/a" + String.fromCodePoint(point) + "b",
      );
      const marked = "/me/a" + String.fromCodePoint(0xfeff) + "b";
      const normal = {
        0: { t: "scene" },
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: "/me/waves",
        marked,
      };
      const expected = {
        0: { t: "scene" },
        1: "/me/waves",
        2: marked,
        subtitle: "/me waves/ and leaves",
        lines: lines_kept,
        python: python_spaces,
        image: { $ref: 1 },
        marked: { $ref: 2 },
      };
      this.assertEqual(substrate.doc_encode(normal), expected);
      this.assertEqual(substrate.doc_decode(expected), normal);
      const kept = ["/me waves/ and leaves", ...lines_kept, ...python_spaces];
      for (const text of kept) {
        this.raised_assert(i18n("substrate.header_ref", 1), () =>
          substrate.doc_decode({ 0: { t: "scene" }, 1: text }),
        );
      }
    }
  }

  // The sink's incremental `SHA-256`, against known and one shot digests.
  export class TestHash extends RefusalCase {
    // Streamed values give their known digests.
    test_digest_recorded(): void {
      const cases: [Uint8Array, string][] = [
        [bytes_text("castle_world"), constants.world_sha256],
        [
          bytes_text("/castle_gatehouse/scene/arrival/1"),
          constants.scene_sha256,
        ],
        [
          utility.base64_decode(constants.image_base64),
          constants.image_sha256,
        ],
        [bytes_text(constants.step_script), constants.script_sha256],
        [bytes_pattern(constants.map_bytes), constants.map_sha256],
      ];
      for (const [data, digest] of cases) {
        for (const piece of [1, 7, 64, 4097, data.length]) {
          this.assertEqual(digest_streamed(data, piece), digest);
        }
      }
    }

    // Every length around the block and padding bounds, in pieces of any size.
    test_digest_lengths(): void {
      const lengths = [0, 1, 55, 56, 57, 63, 64, 65, 119, 120, 127, 128, 1000];
      for (const length of lengths) {
        const data = bytes_pattern(length);
        const digest = utility.sha256_hex(data);
        for (const piece of [1, 7, 63, 64, 65, Math.max(1, length)]) {
          this.assertEqual(
            digest_streamed(data, piece),
            digest,
            `${String(length)} by ${String(piece)}`,
          );
        }
      }
    }
  }

  // The cache: the sink, ranges, partial blobs, files found and faults.
  export class TestCache extends RefusalCase {
    // A finished blob reads back by range, a copy of the bytes it was given.
    test_sink_read(): void {
      const cache = new substrate.CacheFiles(slots_make(2));
      const data = bytes_pattern(10);
      const handle = cache.sink_open({ s: 10 });
      const first = data.slice(0, 4);
      cache.sink_append(handle, first);
      first.fill(255);
      cache.sink_append(handle, data.subarray(4));
      this.assertEqual(cache.sink_close(handle), utility.sha256_hex(data));
      this.assertEqual(cache.cache_read(handle, 0, 10), data);
      this.assertEqual(cache.cache_read(handle, 3, 4), data.subarray(3, 7));
      this.assertEqual(cache.cache_read(handle, 8, 5), data.subarray(8));
      this.assertEqual(cache.cache_read(handle, 10, 4), new Uint8Array(0));
      this.assertEqual(cache.cache_read(handle, 12, 4), new Uint8Array(0));
      this.assertEqual(cache.slots_free(), 1);
    }

    // A blob closed short of its size, after a decoder fault, is freed.
    test_sink_partial(): void {
      const cache = new substrate.CacheFiles(slots_make(1));
      const handle = cache.sink_open({ s: 10 });
      this.assertEqual(cache.slots_free(), 0);
      cache.sink_append(handle, bytes_pattern(4));
      this.assertEqual(
        cache.sink_close(handle),
        utility.sha256_hex(bytes_pattern(4)),
      );
      this.assertEqual(cache.slots_free(), 1);
      const unknown = i18n("substrate.cache_unknown", handle);
      this.raised_assert(unknown, () => cache.cache_read(handle, 0, 1));
      this.raised_assert(unknown, () =>
        cache.sink_append(handle, bytes_pattern(1)),
      );
      this.raised_assert(unknown, () => cache.sink_close(handle));
    }

    // A cache with no free file refuses a blob until a file is added.
    test_cache_full(): void {
      const cache = new substrate.CacheFiles(slots_make(1));
      cache.sink_open({ s: 1 });
      this.raised_assert(i18n("substrate.cache_full", 1), () =>
        cache.sink_open({ s: 1 }),
      );
      const empty = new substrate.CacheFiles([]);
      this.raised_assert(i18n("substrate.cache_full", 0), () =>
        empty.sink_open({ s: 1 }),
      );
      empty.slot_add(new MemorySlot());
      this.assertEqual(empty.slots_free(), 1);
      empty.sink_open({ s: 1 });
      this.assertEqual(empty.slots_free(), 0);
    }

    // Files hold the value their first bytes name, others are free.
    test_slots_found(): void {
      const data = bytes_pattern(100);
      const name = utility.sha256_hex(data);
      const left = new MemorySlot();
      left.bytes_set(bytes_join([new Uint8Array(constants.name_bytes), data]));
      const empty = new MemorySlot();
      const cache = new substrate.CacheFiles([
        slot_stored(name, data),
        left,
        empty,
      ]);
      this.assertEqual(cache.slots_free(), 2);
      this.assertEqual(cache.cache_read(name, 0, 100), data);
      this.assertEqual(cache.cache_read(name, 90, 20), data.subarray(90));
      const handle = cache.sink_open({ s: 3 });
      cache.sink_append(handle, bytes_pattern(3));
      cache.sink_close(handle);
      this.assertEqual(cache.slots_free(), 1);
      this.assertEqual(
        empty.bytes_get(),
        bytes_join([new Uint8Array(constants.name_bytes), bytes_pattern(3)]),
      );
    }

    // A file whose first bytes name no `SHA-256`, or a name twice, throws.
    test_names_bad(): void {
      const garbled = "z".repeat(constants.name_bytes);
      this.raised_assert(i18n("substrate.cache_header", 0, garbled), () => {
        new substrate.CacheFiles([slot_stored(garbled, bytes_pattern(1))]);
      });
      const name = utility.sha256_hex(bytes_pattern(1));
      this.raised_assert(i18n("substrate.cache_twice", name), () => {
        new substrate.CacheFiles([
          slot_stored(name, bytes_pattern(1)),
          slot_stored(name, bytes_pattern(1)),
        ]);
      });
    }

    // A read or write the file reports short throws.
    test_short_io(): void {
      const free = new ShortSlot();
      const writer = new substrate.CacheFiles([free]);
      free.short = true;
      this.raised_assert(
        i18n("substrate.write_short", 0, constants.name_bytes - 1, 64),
        () => writer.sink_open({ s: 1 }),
      );
      const data = bytes_pattern(10);
      const name = utility.sha256_hex(data);
      const stored = new ShortSlot();
      stored.bytes_set(bytes_join([bytes_text(name), data]));
      const reader = new substrate.CacheFiles([stored]);
      stored.short = true;
      this.raised_assert(i18n("substrate.read_short", 0, 9, 10), () =>
        reader.cache_read(name, 0, 10),
      );
    }
  }

  // Databases: tables on first use, names, creating, opening, dropping.
  export class TestDatabases extends StoreCase {
    // A new database gets the substrate's tables, `seq` 0 and `schema` 1.
    test_tables_created(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.assertEqual(tables_list(store, "alpha"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
      ]);
      const meta = "SELECT name, value FROM _meta ORDER BY name";
      this.assertEqual(rows_query(store, "alpha", meta), [
        ["schema", "1"],
        ["seq", "0"],
      ]);
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A database file made elsewhere gets the tables when first opened.
    test_tables_foreign(): void {
      const root = this.root_make();
      this.raw_run(`${root}/beta.sqlite`, "c", [
        { sql: "CREATE TABLE note (text TEXT)" },
        { sql: "INSERT INTO note VALUES (?)", bind: [constants.text_wide] },
      ]);
      const store = this.store_make(root, cache_make(), true);
      this.assertEqual(store.db_open("beta"), 0);
      this.assertEqual(tables_list(store, "beta"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
        "note",
      ]);
      this.assertEqual(rows_query(store, "beta", "SELECT text FROM note"), [
        [constants.text_wide],
      ]);
    }

    // A name that is not a C identifier throws and makes no file.
    test_names_bad(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      const names = [
        "",
        "1abc",
        "a-b",
        "a b",
        "a.b",
        "a/b",
        "caf" + String.fromCodePoint(0xe9),
      ];
      for (const name of names) {
        const message = i18n("substrate.name_bad", name);
        this.raised_assert(message, () => store.db_create(name));
        this.raised_assert(message, () => store.db_open(name));
      }
      this.assertEqual(this.files_under(root), []);
      this.assertEqual(store.db_list(), []);
    }

    // A second create, a second open, a missing file and a close all throw.
    test_create_twice(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      this.raised_assert(i18n("substrate.db_exists", "alpha"), () =>
        store.db_create("alpha"),
      );
      this.raised_assert(i18n("substrate.db_open", "alpha"), () =>
        store.db_open("alpha"),
      );
      this.raised_assert(i18n("substrate.db_absent", "gamma"), () =>
        store.db_open("gamma"),
      );
      this.assertEqual(this.files_under(root), ["alpha.sqlite"]);
      this.raised_assert(i18n("substrate.db_closed", "gamma"), () =>
        store.db_close("gamma"),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A create whose schema fails throws it, leaves no file, and is redone.
    test_create_failed(): void {
      const root = this.root_make();
      // The failure the test makes where the schema is written.
      const schema_stop = (): never => {
        throw new Error(constants.schema_message);
      };
      const prefix = constants.schema_create;
      const pool = pool_stopped(this.pool_get(), schema_stop, prefix);
      const failing = this.store_make(root, cache_make(), true, pool);
      this.raised_assert(constants.schema_message, () =>
        failing.db_create("alpha"),
      );
      this.assertEqual(this.files_under(root), []);
      this.assertEqual(failing.db_list(), []);
      this.assertEqual(this.lines_of(failing), []);
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A file with only some of the substrate's tables throws, kept as it is.
    test_schema_partial(): void {
      const root = this.root_make();
      const path = `${root}/beta.sqlite`;
      this.raw_run(path, "c", [{ sql: constants.meta_sql }]);
      const store = this.store_make(root, cache_make(), true);
      this.raised_assert(i18n("substrate.schema_partial", '["_meta"]'), () =>
        store.db_open("beta"),
      );
      this.assertEqual(store.db_list(), []);
      const raw = this.raw_open(path, "r");
      const rows: unknown[][] = [];
      try {
        raw.exec({
          sql: "SELECT name FROM sqlite_schema WHERE type = 'table'",
          rowMode: "array",
          resultRows: rows,
        });
      } finally {
        raw.close();
      }
      this.assertEqual(rows, [["_meta"]]);
    }

    // A file whose `schema` row is not the substrate's version throws.
    test_schema_version(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("beta");
      store.db_close("beta");
      this.raw_run(`${root}/beta.sqlite`, "w", [
        {
          sql: "UPDATE _meta SET value = ? WHERE name = 'schema'",
          bind: ["2"],
        },
      ]);
      this.raised_assert(i18n("substrate.schema_version", "2", "1"), () =>
        store.db_open("beta"),
      );
      this.assertEqual(store.db_list(), []);
    }

    // Closing, dropping or restoring a database a transaction wrote throws.
    test_database_busy(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      const data = store.db_snapshot("alpha").data;
      const files = this.files_under(root);
      this.lines_answer(store);
      const calls: (() => unknown)[] = [
        () => store.db_close("alpha"),
        () => store.db_drop("alpha"),
        () => store.db_restore("alpha", data),
      ];
      for (const call of calls) {
        this.raised_assert(i18n("substrate.db_busy", "alpha"), () =>
          store.transaction_run(() => {
            store.kv_put("/alpha/busy", bytes_text("busy"));
            call();
          }),
        );
        this.assertEqual(store.db_list(), ["alpha"]);
        this.assertEqual(store.seq_get("alpha"), 0);
        this.assertEqual(this.files_under(root), files);
        this.assertEqual(this.lines_of(store), []);
      }
    }

    // Dropping removes the file and the cache files no other database names.
    test_drop_files(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      store.db_create("alpha");
      store.db_create("beta");
      const alone = bytes_reversed(value_over());
      const alone_name = utility.sha256_hex(alone);
      const shared_name = utility.sha256_hex(value_over());
      store.kv_put("/alpha/shared", value_over());
      store.kv_put("/alpha/alone", alone);
      store.kv_put("/beta/shared", value_over());
      this.lines_answer(store);
      store.db_drop("alpha");
      this.assertEqual(this.files_under(root), ["beta.sqlite"]);
      this.raised_assert(i18n("substrate.cache_unknown", alone_name), () =>
        cache.cache_read(alone_name, 0, 1),
      );
      this.assertEqual(cache.cache_read(shared_name, 0, 1).length, 1);
      this.assertEqual(store.db_list(), ["beta"]);
      this.assertEqual(store.kv_get("/beta/shared").data, shared_name);
      store.db_drop("beta");
      this.raised_assert(i18n("substrate.cache_unknown", shared_name), () =>
        cache.cache_read(shared_name, 0, 1),
      );
      this.assertEqual(this.files_under(root), []);
    }
  }

  // Values: both ref forms, the overflow limit, shared cache files, handles.
  export class TestValues extends StoreCase {
    // A value put by one ref form is read by the other, listed and deleted.
    test_refs_both(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const key = "greeting/" + constants.text_wide;
      const value = bytes_text("hello " + constants.text_wide);
      const digest = utility.sha256_hex(value);
      const row = { k: key, size: value.length, sha256: digest };
      this.assertEqual(store.kv_put("/alpha/" + key, value), { row, seq: 1 });
      this.assertEqual(store.kv_get(key, "alpha"), {
        data: value,
        size: value.length,
        sha256: digest,
      });
      const world = bytes_text("world");
      this.assertEqual(store.kv_put("place/a/b", world, "alpha").seq, 2);
      this.assertEqual(store.kv_get("/alpha/place/a/b").data, world);
      this.assertEqual(store.kv_list("alpha", "greeting/"), [row]);
      this.assertEqual(
        store.kv_list("alpha", "").map((listed) => listed.k),
        [key, "place/a/b"],
      );
      this.assertEqual(store.kv_delete(key, "alpha"), 3);
      this.raised_assert(i18n("substrate.key_missing", key, "alpha"), () =>
        store.kv_get("/alpha/" + key),
      );
    }

    // A value of exactly `overflow_bytes` stays in its row, one byte more not.
    test_overflow_boundary(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      store.db_create("alpha");
      store.kv_put("/alpha/exact", value_exact());
      const exact = store.kv_get("/alpha/exact");
      this.assertEqual(exact.data, value_exact());
      this.assertEqual(exact.size, constants.overflow_bytes);
      const exact_name = utility.sha256_hex(value_exact());
      this.raised_assert(i18n("substrate.cache_unknown", exact_name), () =>
        cache.cache_read(exact_name, 0, 1),
      );
      store.kv_put("/alpha/over", value_over());
      const name = utility.sha256_hex(value_over());
      this.assertEqual(store.kv_get("/alpha/over"), {
        data: name,
        size: constants.overflow_bytes + 1,
        sha256: name,
      });
      this.assertEqual(
        cache.cache_read(name, 0, constants.overflow_bytes + 1),
        value_over(),
      );
    }

    // A cache file stays while any row of any database names its hash.
    test_cache_shared(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      const name = utility.sha256_hex(value_over());
      // The bytes the cache file gives from its start, one when it is there.
      const cache_present = (): number => cache.cache_read(name, 0, 1).length;
      store.db_create("alpha");
      store.db_create("beta");
      store.kv_put("/alpha/one", value_over());
      store.kv_put("/alpha/two", value_over());
      store.kv_put("/beta/three", value_over());
      store.kv_delete("/alpha/one");
      this.lines_answer(store);
      this.assertEqual(cache_present(), 1);
      store.kv_put("/alpha/two", bytes_text("small"));
      this.lines_answer(store);
      this.assertEqual(cache_present(), 1);
      store.db_close("beta");
      store.kv_put("/alpha/two", value_over());
      store.kv_delete("/alpha/two");
      this.lines_answer(store);
      this.assertEqual(cache_present(), 1);
      store.db_open("beta");
      store.kv_delete("/beta/three");
      this.lines_answer(store);
      this.raised_assert(i18n("substrate.cache_unknown", name), cache_present);
      this.assertEqual(store.kv_check("alpha"), 0);
    }

    // A blob the sink streamed moves into place, a small one is refused.
    test_handle_moved(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      store.db_create("alpha");
      const handle = sink_fill(cache, value_over());
      const name = utility.sha256_hex(value_over());
      const size = constants.overflow_bytes + 1;
      this.assertEqual(store.kv_put("/alpha/streamed", handle), {
        row: { k: "streamed", size, sha256: name },
        seq: 1,
      });
      this.raised_assert(i18n("substrate.cache_unknown", handle), () =>
        cache.cache_read(handle, 0, 1),
      );
      this.assertEqual(store.kv_get("/alpha/streamed").data, name);
      const small = sink_fill(cache, value_exact());
      this.raised_assert(
        i18n(
          "substrate.file_small",
          small,
          constants.overflow_bytes,
          constants.overflow_bytes,
        ),
        () => store.kv_put("/alpha/small", small),
      );
      this.assertEqual(store.seq_get("alpha"), 1);
      this.lines_answer(store);
      this.assertEqual(store.kv_check("alpha"), 0);
      this.assertEqual(cache.cache_read(small, 0, 1).length, 1);
    }
  }

  // Documents in a store: stored text and numbers, wide versions, refusals.
  export class TestStored extends StoreCase {
    // An encoded document is stored and read back as the same text.
    test_stored_trip(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const put = store.doc_put("metaverse", "fog", fog_encoded());
      this.assertEqual(put, { ref: "/metaverse/fog/1", seq: 1 });
      const stored = store.doc_get(put.ref);
      this.assertEqual(
        utility.json_text(stored),
        utility.json_text(fog_encoded()),
      );
      this.assertEqual(substrate.doc_decode(stored), fog_normal());
    }

    // Numbers below 1e-4 are stored as Python's `repr` writes them.
    test_numbers_small(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const body = { 0: { t: "note" }, a: 0.00001, b: -1.5e-7, c: 0.0001 };
      const ref = store.doc_put("alpha", "note", body).ref;
      this.assertEqual(
        store.kv_get(ref).data,
        bytes_text('{"0":{"t":"note"},"a":1e-05,"b":-1.5e-07,"c":0.0001}'),
      );
    }

    // A head past 2^53 moves to the exact next version, as in Python.
    test_version_wide(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.sql_run("alpha", [
        {
          sql: "INSERT INTO _head (id, version) VALUES (?, ?)",
          params: ["note", "9007199254740993"],
        },
      ]);
      const put = store.doc_put("alpha", "note", { 0: { t: "note" } });
      this.assertEqual(put.ref, "/alpha/note/9007199254740994");
      this.assertEqual(store.doc_head("alpha", "note"), put.ref);
      const head = "SELECT CAST(version AS TEXT) FROM _head";
      this.assertEqual(rows_query(store, "alpha", head), [
        ["9007199254740994"],
      ]);
    }

    // Values JSON or the wire cannot carry, and bad ids and headers, throw.
    test_values_refused(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const note = { t: "note" };
      const cases: [lines.Document, string][] = [
        [
          { 0: note, x: [Number.POSITIVE_INFINITY] },
          i18n("substrate.number_refused", Number.POSITIVE_INFINITY),
        ],
        [
          { 0: note, x: Number.NaN },
          i18n("substrate.number_refused", Number.NaN),
        ],
        [
          { 0: note, n: 2 ** 53 + 2 },
          i18n("substrate.integer_range", 2 ** 53 + 2),
        ],
        [
          { 0: note, x: "a" + String.fromCharCode(0xd800) },
          i18n("substrate.text_refused"),
        ],
        [
          { 0: note, x: new Uint8Array(1) },
          i18n("substrate.value_refused", "[object Uint8Array]"),
        ],
        [
          { 0: note, x: undefined },
          i18n("substrate.value_refused", "[object Undefined]"),
        ],
        [{ 0: note, 2: "/a/b" }, i18n("substrate.header_gap", "2")],
      ];
      for (const [body, message] of cases) {
        this.raised_assert(message, () => store.doc_put("alpha", "x", body));
      }
      this.raised_assert(i18n("substrate.id_empty"), () =>
        store.doc_put("alpha", "", { 0: note }),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
    }
  }

  // Turns: appended in order, listed, and compacted into one summary.
  export class TestTurns extends StoreCase {
    // Turns number from 1 in their scene, a bad scene or content throws.
    test_turns_append(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const scene = constants.scene;
      const user: provider.ChatMessage = { role: "user", content: "1" };
      const answer: provider.ChatMessage = {
        role: "assistant",
        content: constants.text_wide,
      };
      this.assertEqual(store.turn_append(scene, "user", user), {
        n: 1,
        seq: 1,
      });
      this.assertEqual(store.turn_append(scene, "assistant", answer), {
        n: 2,
        seq: 2,
      });
      this.assertEqual(store.turn_list(scene), [
        { scene, n: 1, role: "user", content: user },
        { scene, n: 2, role: "assistant", content: answer },
      ]);
      this.assertEqual(store.turn_list("/metaverse/elsewhere/1"), []);
      for (const bad of ["hyperposition/1", "/metaverse/world"]) {
        this.raised_assert(i18n("substrate.scene_bad", bad), () =>
          store.turn_append(bad, "user", user),
        );
      }
      this.sqlite_assert("CHECK constraint failed: json_valid(content)", () =>
        store.sql_run("metaverse", [
          {
            sql:
              "INSERT INTO _turn (scene, n, role, content)" +
              " VALUES (?, ?, ?, ?)",
            params: [scene, 3, "user", "not json"],
          },
        ]),
      );
      this.assertEqual(store.seq_get("metaverse"), 2);
    }

    // Compaction replaces turns 1 to `through` by one summary turn at 1.
    test_turns_compact(): void {
      const store = this.store_fresh();
      store.db_create("metaverse");
      const scene = constants.scene;
      for (const text of ["1", "2", "3", "4"]) {
        store.turn_append(scene, "user", { role: "user", content: text });
      }
      this.assertEqual(store.turn_compact(scene, 3, "Asked thrice."), 5);
      const fourth: provider.ChatMessage = { role: "user", content: "4" };
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: { role: "system", content: "Asked thrice." },
        },
        { scene, n: 4, role: "user", content: fourth },
      ]);
      this.assertEqual(store.turn_append(scene, "user", fourth), {
        n: 5,
        seq: 6,
      });
      this.raised_assert(i18n("substrate.through_bad", 0), () =>
        store.turn_compact(scene, 0, "None."),
      );
      const elsewhere = "/metaverse/elsewhere/1";
      this.raised_assert(i18n("substrate.turns_none", elsewhere, 2), () =>
        store.turn_compact(elsewhere, 2, "None."),
      );
      this.assertEqual(store.seq_get("metaverse"), 6);
    }
  }

  // Compaction at `turn_compact_turns`: when it runs, what it writes, sends.
  export class TestCompaction extends StoreCase {
    // A `user` turn at the threshold compacts its scene first, sent first.
    test_threshold_reached(): void {
      const store = this.store_compacting();
      store.db_create("alpha");
      this.lines_answer(store);
      const scene = "/alpha/scene/1";
      const other = "/alpha/scene/2";
      store.turn_append(scene, "user", message_said("user", "1"));
      store.turn_append(scene, "assistant", message_said("assistant", "2"));
      this.assertEqual(
        store.turn_append(scene, "user", message_said("user", "3")),
        { n: 3, seq: 3 },
      );
      this.assertEqual(
        store.turn_append(scene, "assistant", message_said("assistant", "4")),
        { n: 4, seq: 4 },
      );
      this.assertEqual(
        store.turn_append(other, "user", message_said("user", "a")),
        { n: 1, seq: 5 },
      );
      this.lines_answer(store);
      const fifth = message_said("user", "5");
      this.assertEqual(store.turn_append(scene, "user", fifth), {
        n: 2,
        seq: 7,
      });
      const summary = i18n("substrate.turns_compacted", 4, 4);
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: message_said("system", summary),
        },
        { scene, n: 2, role: "user", content: fifth },
      ]);
      this.assertEqual(
        this.lines_of(store).map((line) => jslb.line_render(line)),
        [
          '{"0":{"t":"turn.compact"},"scene":"/alpha/scene/1","through":4,' +
            `"summary":${utility.json_text(summary)},"since":5}`,
          '{"0":{"t":"turn.append"},"scene":"/alpha/scene/1","role":"user",' +
            '"content":{"role":"user","content":"5"},"since":6}',
        ],
      );
      this.lines_answer(store);
      const opening = message_said("user", "a");
      this.assertEqual(store.turn_list(other), [
        { scene: other, n: 1, role: "user", content: opening },
      ]);
      this.assertEqual(
        store.turn_append(scene, "user", message_said("user", "6")),
        { n: 3, seq: 8 },
      );
      this.assertEqual(store.turn_list(scene).length, 3);
    }

    // The compaction rolls back with the transaction of its `user` turn.
    test_compaction_rolled(): void {
      const store = this.store_compacting();
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      for (const text of ["1", "2", "3"]) {
        store.turn_append(scene, "assistant", message_said("assistant", text));
      }
      this.lines_answer(store);
      const before = store.turn_list(scene);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.turn_append(scene, "user", message_said("user", "4"));
          throw new Error("rolled back");
        }),
      );
      this.assertEqual(store.turn_list(scene), before);
      this.assertEqual(store.seq_get("alpha"), 3);
      this.assertEqual(this.lines_of(store), []);
    }

    // A forwarded `turn.append` applies as it is and never compacts.
    test_applied_exactly(): void {
      const store = this.store_compacting();
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      for (const text of ["1", "2", "3"]) {
        store.turn_append(scene, "assistant", message_said("assistant", text));
      }
      this.lines_answer(store);
      const user = message_said("user", "4");
      this.assertEqual(
        store.operation_apply("turn.append", 3, {
          scene,
          role: "user",
          content: user,
        }),
        4,
      );
      this.assertEqual(
        store.turn_list(scene).map((row) => row.content),
        [
          message_said("assistant", "1"),
          message_said("assistant", "2"),
          message_said("assistant", "3"),
          user,
        ],
      );
      this.assertEqual(this.lines_taken(store), [
        '{"0":{"t":"turn.append"},"scene":"/alpha/scene/1","role":"user",' +
          '"content":{"role":"user","content":"4"},"since":3}',
      ]);
    }

    // A forwarding store on a new root whose threshold is small.
    store_compacting(): substrate.Store {
      return this.store_make(
        this.root_make(),
        cache_make(),
        true,
        this.pool_get(),
        constants.compact_small,
      );
    }
  }

  // SQL: the results of statements, what counts, and what is refused.
  export class TestSql extends StoreCase {
    // Statements return columns, rows and changes, and only writes count.
    test_sql_results(): void {
      const store = this.store_fresh();
      store.db_create("castle");
      const results = store.sql_run("castle", [
        { sql: constants.world_sql, params: [] },
        {
          sql: "INSERT INTO world VALUES (?, ?)",
          params: ["castle_world", "The castle"],
        },
      ]);
      this.assertEqual(results, [
        { columns: [], rows: [], changes: 0 },
        { columns: [], rows: [], changes: 1 },
      ]);
      this.assertEqual(store.seq_get("castle"), 1);
      const selected = store.sql_run("castle", [
        { sql: "SELECT name, title FROM world", params: [] },
      ]);
      this.assertEqual(selected, [
        {
          columns: ["name", "title"],
          rows: [["castle_world", "The castle"]],
          changes: 0,
        },
      ]);
      this.assertEqual(store.seq_get("castle"), 1);
    }

    // Two statements in one, a parameter count that differs, an SQL error.
    test_statements_refused(): void {
      const store = this.store_fresh();
      store.db_create("castle");
      const twice = "SELECT 1; SELECT 2";
      this.raised_assert(i18n("substrate.statement_many", 2, twice), () =>
        store.sql_run("castle", [{ sql: twice, params: [] }]),
      );
      this.raised_assert(
        i18n("substrate.params_count", 1, 0, "SELECT ?"),
        () => store.sql_run("castle", [{ sql: "SELECT ?", params: [] }]),
      );
      this.raised_assert(
        i18n("substrate.params_count", 0, 1, "SELECT 1"),
        () => store.sql_run("castle", [{ sql: "SELECT 1", params: [1] }]),
      );
      this.sqlite_assert("no such table: absent", () =>
        store.sql_run("castle", [
          { sql: "INSERT INTO absent VALUES (1)", params: [] },
        ]),
      );
      this.assertEqual(store.seq_get("castle"), 0);
    }
  }

  // The rules of `seq`: what counts, what does not, and transactions.
  export class TestSeq extends StoreCase {
    // Changes count once each, no change and a failure count nothing.
    test_seq_rules(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      // Runs one statement in `alpha`.
      const statement_run = (sql: string, params: unknown[]): void => {
        store.sql_run("alpha", [{ sql, params }]);
      };
      this.assertEqual(store.kv_put("/alpha/a", bytes_text("one")).seq, 1);
      this.assertEqual(store.kv_put("/alpha/a", bytes_text("one")).seq, 1);
      this.assertEqual(store.kv_put("/alpha/a", bytes_text("two")).seq, 2);
      this.assertEqual(store.kv_delete("/alpha/absent"), 2);
      this.assertEqual(store.kv_delete("/alpha/a"), 3);
      statement_run("SELECT 1", []);
      this.assertEqual(store.seq_get("alpha"), 3);
      statement_run("CREATE TABLE t (x TEXT)", []);
      this.assertEqual(store.seq_get("alpha"), 4);
      statement_run("INSERT INTO t VALUES (?)", ["a"]);
      this.assertEqual(store.seq_get("alpha"), 5);
      statement_run("UPDATE t SET x = ? WHERE x = ?", ["b", "absent"]);
      this.assertEqual(store.seq_get("alpha"), 5);
      this.sqlite_assert("no such table: absent", () =>
        store.sql_run("alpha", [
          { sql: "INSERT INTO t VALUES (?)", params: ["b"] },
          { sql: "INSERT INTO absent VALUES (1)", params: [] },
        ]),
      );
      this.assertEqual(store.seq_get("alpha"), 5);
      this.assertEqual(rows_query(store, "alpha", "SELECT x FROM t"), [["a"]]);
    }

    // Writes in one `transaction_run` commit together or roll back together.
    test_transaction_whole(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.db_create("beta");
      store.transaction_run(() => {
        store.kv_put("/alpha/a", bytes_text("1"));
        store.kv_put("/beta/b", bytes_text("2"));
        store.kv_put("/alpha/c", bytes_text("3"));
      });
      this.assertEqual(store.seq_get("alpha"), 2);
      this.assertEqual(store.seq_get("beta"), 1);
      this.lines_answer(store);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/d", value_over());
          store.kv_delete("/alpha/a");
          throw new Error("rolled back");
        }),
      );
      this.assertEqual(store.seq_get("alpha"), 2);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("1"));
      this.raised_assert(i18n("substrate.key_missing", "d", "alpha"), () =>
        store.kv_get("/alpha/d"),
      );
      this.assertEqual(this.lines_of(store), []);
      this.assertEqual(store.kv_check("alpha"), 1);
    }

    // A failure after one of two databases was written rolls both back.
    test_transaction_split(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.db_create("beta");
      this.sqlite_assert("no such table: absent", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/a", bytes_text("1"));
          store.sql_run("beta", [
            { sql: "CREATE TABLE note (x TEXT)", params: [] },
            { sql: "INSERT INTO absent VALUES (1)", params: [] },
          ]);
        }),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
      this.assertEqual(store.seq_get("beta"), 0);
      this.raised_assert(i18n("substrate.key_missing", "a", "alpha"), () =>
        store.kv_get("/alpha/a"),
      );
      this.assertEqual(tables_list(store, "beta"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
      ]);
    }

    // `seq` survives closing, reopening and a new store on the same root.
    test_seq_reopen(): void {
      const root = this.root_make();
      const slots = slots_make(constants.slot_count);
      const first = new substrate.CacheFiles(slots);
      const store = this.store_make(root, first, true);
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      store.kv_put("/alpha/big", value_over());
      store.doc_put("alpha", "note", {
        0: { t: "note" },
        text: constants.text_wide,
      });
      store.turn_append("/alpha/scene/1", "user", {
        role: "user",
        content: "hi",
      });
      this.assertEqual(store.seq_get("alpha"), 4);
      store.db_close("alpha");
      this.assertEqual(store.db_list(), []);
      this.assertEqual(store.db_open("alpha"), 4);
      store.db_close("alpha");
      const cache = new substrate.CacheFiles(slots);
      const again = this.store_make(root, cache, true);
      this.assertEqual(again.db_open("alpha"), 4);
      this.assertEqual(again.kv_get("/alpha/a").data, bytes_text("one"));
      const name = utility.sha256_hex(value_over());
      this.assertEqual(again.kv_get("/alpha/big").data, name);
      this.assertEqual(
        cache.cache_read(name, 0, constants.overflow_bytes + 1),
        value_over(),
      );
    }
  }

  // Snapshots: serialized bytes with `seq`, restored from bytes or a handle.
  export class TestSnapshot extends StoreCase {
    // A restore brings back the rows and the `seq` of the snapshot.
    test_snapshot_restore(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      store.sql_run("alpha", [
        { sql: "CREATE TABLE t (x TEXT)", params: [] },
        { sql: "INSERT INTO t VALUES (?)", params: [constants.text_wide] },
      ]);
      const snapshot = store.db_snapshot("alpha");
      this.assertEqual(
        snapshot.data.subarray(0, 16),
        bytes_join([bytes_text(constants.file_magic), new Uint8Array(1)]),
      );
      this.assertEqual(snapshot.seq, 2);
      const dump = content_dump(store, "alpha");
      store.kv_put("/alpha/a", bytes_text("two"));
      store.kv_put("/alpha/b", bytes_text("three"));
      store.sql_run("alpha", [{ sql: "DELETE FROM t", params: [] }]);
      this.assertEqual(store.seq_get("alpha"), 5);
      this.lines_answer(store);
      this.assertEqual(store.db_restore("alpha", snapshot.data), 2);
      this.assertEqual(store.seq_get("alpha"), 2);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("one"));
      this.raised_assert(i18n("substrate.key_missing", "b", "alpha"), () =>
        store.kv_get("/alpha/b"),
      );
      this.assertEqual(content_dump(store, "alpha"), dump);
      this.assertEqual(this.lines_of(store), []);
      const cache = cache_make();
      const second = this.store_make(this.root_make(), cache, true);
      const handle = sink_fill(cache, snapshot.data);
      this.assertEqual(second.db_restore("alpha", handle), 2);
      this.raised_assert(i18n("substrate.cache_unknown", handle), () =>
        cache.cache_read(handle, 0, 1),
      );
      this.assertEqual(content_dump(second, "alpha"), dump);
    }

    // A file without the substrate's tables throws and the old one stays.
    test_restore_foreign(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      const foreign = `${root}/foreign.sqlite`;
      this.raw_run(foreign, "c", [{ sql: "CREATE TABLE note (x TEXT)" }]);
      const data = this.raw_export(foreign);
      const files = this.files_under(root);
      this.raised_assert(i18n("substrate.schema_partial", "[]"), () =>
        store.db_restore("alpha", data),
      );
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("one"));
      this.assertEqual(store.seq_get("alpha"), 1);
      this.assertEqual(this.files_under(root), files);
    }

    // A restore file left by an earlier restore throws, and stays.
    test_restore_left(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      const data = store.db_snapshot("alpha").data;
      const left = `${root}/alpha.sqlite-restore`;
      this.raw_run(left, "c", [{ sql: "CREATE TABLE note (x TEXT)" }]);
      this.raised_assert(i18n("substrate.restore_left", left), () =>
        store.db_restore("alpha", data),
      );
      this.assertEqual(this.files_under(root), [
        "alpha.sqlite",
        "alpha.sqlite-restore",
      ]);
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // Two snapshots of one database taken apart hold their own bytes and seq.
    test_snapshots_apart(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const first = store.db_snapshot("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      const second = store.db_snapshot("alpha");
      this.assertEqual([first.seq, second.seq], [0, 1]);
      this.assertFalse(
        utility.sha256_hex(first.data) === utility.sha256_hex(second.data),
      );
    }

    // A cached value stays held through a snapshot and its restore.
    test_value_held(): void {
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache, true);
      store.db_create("alpha");
      store.kv_put("/alpha/big", value_over());
      this.lines_answer(store);
      const snapshot = store.db_snapshot("alpha");
      this.assertEqual(store.db_restore("alpha", snapshot.data), snapshot.seq);
      const name = utility.sha256_hex(value_over());
      const size = constants.overflow_bytes + 1;
      this.assertEqual(store.kv_get("/alpha/big"), {
        data: name,
        size,
        sha256: name,
      });
      this.assertEqual(cache.cache_read(name, 0, size), value_over());
    }
  }

  // Forwarded lines: after the commit, in order, with `since`, held files.
  export class TestForward extends StoreCase {
    // Each modifying operation forwards its line, a copy of its bytes.
    test_lines_after(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const value = bytes_text("one");
      store.kv_put("/alpha/a", value);
      const forwarded = this.lines_of(store);
      this.assertEqual(
        forwarded.map((line) => jslb.line_render(line)),
        [
          '{"0":{"t":"db.create"},"db":"alpha","since":0}',
          '{"0":{"t":"kv.put","k":"/alpha/a","b":1},"1":{"s":3},"since":0}' +
            '<blob "n"=1>',
        ],
      );
      const blob = forwarded[1][1] as lines.BlobHeader;
      this.assertEqual(blob.d, value);
      this.assertFalse(blob.d === value);
      this.lines_answer(store);
      store.kv_delete("/alpha/a");
      store.turn_append("/alpha/scene/1", "user", {
        role: "user",
        content: "hi",
      });
      store.turn_compact("/alpha/scene/1", 1, "Said hi.");
      store.doc_put("alpha", "note", { 0: { t: "note" } });
      this.assertEqual(this.lines_taken(store), [
        '{"0":{"t":"kv.delete","k":"/alpha/a"},"since":1}',
        '{"0":{"t":"turn.append"},"scene":"/alpha/scene/1","role":"user",' +
          '"content":{"role":"user","content":"hi"},"since":2}',
        '{"0":{"t":"turn.compact"},"scene":"/alpha/scene/1","through":1,' +
          '"summary":"Said hi.","since":3}',
        '{"0":{"t":"doc.put"},"db":"alpha","id":"note",' +
          '"body":{"0":{"t":"note"}},"since":4}',
      ]);
    }

    // The lines of one transaction go after its commit, in order.
    test_lines_order(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.lines_answer(store);
      store.transaction_run(() => {
        store.kv_put("/alpha/a", bytes_text("1"));
        store.kv_put("/alpha/b", bytes_text("2"));
        store.sql_run("alpha", [
          { sql: "CREATE TABLE t (x TEXT)", params: [] },
        ]);
        this.assertEqual(this.lines_of(store), []);
      });
      this.assertEqual(this.lines_taken(store), [
        '{"0":{"t":"kv.put","k":"/alpha/a","b":1},"1":{"s":1},"since":0}' +
          '<blob "n"=1>',
        '{"0":{"t":"kv.put","k":"/alpha/b","b":1},"1":{"s":1},"since":1}' +
          '<blob "n"=1>',
        '{"0":{"t":"sql.run"},"db":"alpha","statements":[{"sql":' +
          '"CREATE TABLE t (x TEXT)","params":[]}],"since":2}',
      ]);
    }

    // A transaction rolled back forwards nothing, a change nothing either.
    test_lines_unsent(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      this.lines_answer(store);
      this.raised_assert("rolled back", () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/b", bytes_text("two"));
          throw new Error("rolled back");
        }),
      );
      store.kv_put("/alpha/a", bytes_text("one"));
      store.kv_delete("/alpha/absent");
      store.sql_run("alpha", [{ sql: "SELECT 1", params: [] }]);
      this.assertEqual(this.lines_of(store), []);
      this.assertEqual(store.seq_get("alpha"), 1);
    }

    // A cached value's line holds its file until the reply comes.
    test_handle_held(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      store.db_create("alpha");
      this.lines_answer(store);
      const name = utility.sha256_hex(value_over());
      store.kv_put("/alpha/big", value_over());
      store.kv_put("/alpha/big", bytes_text("small"));
      const [held, small] = this.lines_of(store).splice(0);
      this.assertEqual(
        jslb.line_render(held),
        '{"0":{"t":"kv.put","k":"/alpha/big","b":1},"1":{"s":131073},' +
          '"since":0}<blob "n"=1>',
      );
      this.assertEqual((held[1] as lines.BlobHeader).d, name);
      this.assertEqual(
        cache.cache_read(name, 0, constants.overflow_bytes + 1),
        value_over(),
      );
      store.forward_done(held, reply_make(held));
      this.raised_assert(i18n("substrate.cache_unknown", name), () =>
        cache.cache_read(name, 0, 1),
      );
      store.forward_done(small, reply_make(small));
    }

    // A reply with another `seq`, or to no line in flight, throws.
    test_replies_checked(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.lines_answer(store);
      store.kv_put("/alpha/a", bytes_text("one"));
      const [line] = this.lines_of(store).splice(0);
      const wrong = jslb.line_make(
        jslb.header_make("kv.put", { reply: 1 }),
        [],
        { seq: 5 },
      );
      this.raised_assert(
        i18n("substrate.reply_desync", "kv.put", 5, 1, "alpha"),
        () => store.forward_done(line, wrong),
      );
      store.forward_done(line, reply_make(line));
      this.raised_assert(i18n("substrate.forward_unknown", "kv.put"), () =>
        store.forward_done(line, reply_make(line)),
      );
    }

    // A store with no function to forward to writes nothing, and throws.
    test_forward_unset(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      store.db_close("alpha");
      const bare = this.store_make(root, cache_make(), false);
      this.raised_assert(i18n("substrate.forward_unset", "db.create"), () =>
        bare.db_create("beta"),
      );
      this.assertEqual(this.files_under(root), ["alpha.sqlite"]);
      this.assertEqual(bare.db_open("alpha"), 0);
      this.raised_assert(i18n("substrate.forward_unset", "kv.put"), () =>
        bare.kv_put("/alpha/a", bytes_text("one")),
      );
      this.assertEqual(bare.seq_get("alpha"), 0);
      this.raised_assert(i18n("substrate.key_missing", "a", "alpha"), () =>
        bare.kv_get("/alpha/a"),
      );
      this.raised_assert(i18n("substrate.forward_twice"), () =>
        store.forward_set(() => undefined, false),
      );
    }

    // Lines use full names when the store is told to.
    test_names_full(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), false);
      const forwarded: lines.Line[] = [];
      store.forward_set((line) => {
        forwarded.push(line);
      }, true);
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      this.assertEqual(
        forwarded.map((line) => jslb.line_render(line)),
        [
          '{"0":{"type":"db.create"},"db":"alpha","since":0}',
          '{"0":{"type":"kv.put","key":"/alpha/a","blobs":1},' +
            '"1":{"size":3},"since":0}<blob "n"=1>',
        ],
      );
    }

    // A drop forwards its `seq`, and replies with no `seq` are taken.
    test_create_drop(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      store.db_drop("alpha");
      const forwarded = this.lines_of(store);
      this.assertEqual(
        jslb.line_render(forwarded[2]),
        '{"0":{"t":"db.drop"},"db":"alpha","since":1}',
      );
      this.lines_answer(store);
      this.assertEqual(store.db_list(), []);
    }
  }

  // Replication: known sequences replayed, stale lines, bad lines.
  export class TestReplay extends StoreCase {
    // The castle turn's operations and two more give their lines and `seq`.
    test_recorded_replay(): void {
      const first_root = this.root_make();
      const second_root = this.root_make();
      const first_cache = cache_make();
      const second_cache = cache_make();
      const first = this.store_make(first_root, first_cache, true);
      const second = this.store_make(second_root, second_cache, true);
      this.hello_make(first);
      this.hello_make(second);
      for (const record of recorded_make()) {
        const line = this.modifier_call(first, record);
        const note = `${record.type} since ${String(record.since)}`;
        this.assertEqual(jslb.payload_of(line).since, record.since, note);
        const db = target_database(record);
        this.assertEqual(first.seq_get(db), record.seq, note);
        if (record.text !== undefined) {
          this.assertEqual(jslb.line_render(line), record.text, note);
        }
        if (record.sha256 !== undefined) {
          const k = record.fields.k as string;
          this.assertEqual(first.kv_get(k).sha256, record.sha256, note);
        }
        const payload = payload_replayed(line, first_cache, second_cache);
        this.assertEqual(
          second.operation_apply(record.type, record.since, payload),
          record.seq,
          note,
        );
        this.assertEqual(
          this.lines_taken(second),
          [jslb.line_render(line)],
          note,
        );
      }
      const names = first.db_list();
      this.assertEqual(names, [
        "_files",
        "castle",
        "castle_gatehouse",
        "castle_world",
        "metaverse",
      ]);
      this.assertEqual(second.db_list(), names);
      for (const name of names) {
        this.assertEqual(
          content_dump(first, name),
          content_dump(second, name),
          name,
        );
      }
      const map = bytes_pattern(constants.map_bytes);
      for (const cache of [first_cache, second_cache]) {
        this.assertEqual(
          cache.cache_read(constants.map_sha256, 0, constants.map_bytes),
          map,
        );
      }
      const k = "/_files/script/step_tide.js";
      const data = bytes_text(constants.step_script);
      second.kv_put(k, data);
      this.raised_assert(
        i18n("substrate.since_stale", "kv.put", 3, 4, "_files"),
        () => second.operation_apply("kv.put", 3, { k, data }),
      );
      this.assertEqual(second.seq_get("_files"), 4);
    }

    // A `since` that is not the `seq` throws the desync and changes nothing.
    test_since_stale(): void {
      const root = this.root_make();
      const store = this.store_make(root, cache_make(), true);
      store.db_create("alpha");
      const data = bytes_text("x");
      this.raised_assert(
        i18n("substrate.since_stale", "kv.put", 1, 0, "alpha"),
        () => store.operation_apply("kv.put", 1, { k: "/alpha/a", data }),
      );
      this.raised_assert(
        i18n("substrate.since_stale", "db.create", 1, 0, "beta"),
        () => store.operation_apply("db.create", 1, { db: "beta" }),
      );
      this.assertEqual(this.files_under(root), ["alpha.sqlite"]);
      this.raised_assert(
        i18n("substrate.since_stale", "db.drop", 1, 0, "alpha"),
        () => store.operation_apply("db.drop", 1, { db: "alpha" }),
      );
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(store.seq_get("alpha"), 0);
      this.raised_assert(i18n("substrate.key_missing", "a", "alpha"), () =>
        store.kv_get("/alpha/a"),
      );
      this.assertEqual(
        store.operation_apply("kv.put", 0, { k: "/alpha/a", data }),
        1,
      );
      const dropped = store.operation_apply("db.drop", 1, { db: "alpha" });
      this.assertEqual(dropped, 0);
      this.assertEqual(store.db_list(), []);
    }

    // A stale `doc.put` throws and writes no version.
    test_stale_document(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.raised_assert(
        i18n("substrate.since_stale", "doc.put", 1, 0, "alpha"),
        () =>
          store.operation_apply("doc.put", 1, {
            db: "alpha",
            id: "note",
            body: { 0: { t: "note" } },
          }),
      );
      this.raised_assert(i18n("substrate.id_missing", "note", "alpha"), () =>
        store.doc_head("alpha", "note"),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A stale `turn.append` throws and appends no turn.
    test_stale_turn(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      const scene = "/alpha/scene/1";
      this.raised_assert(
        i18n("substrate.since_stale", "turn.append", 1, 0, "alpha"),
        () =>
          store.operation_apply("turn.append", 1, {
            scene,
            role: "user",
            content: { role: "user", content: "1" },
          }),
      );
      this.assertEqual(store.turn_list(scene), []);
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A stale `sql.run` throws and runs no statement.
    test_stale_sql(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.raised_assert(
        i18n("substrate.since_stale", "sql.run", 1, 0, "alpha"),
        () =>
          store.operation_apply("sql.run", 1, {
            db: "alpha",
            statements: [{ sql: "CREATE TABLE note (x TEXT)", params: [] }],
          }),
      );
      this.assertEqual(tables_list(store, "alpha"), [
        "_head",
        "_kv",
        "_meta",
        "_turn",
      ]);
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // A delete, a compaction and a drop, which the replay lacks, apply.
    test_operations_unrecorded(): void {
      const store = this.store_fresh();
      const scene = "/alpha/scene/1";
      const created = store.operation_apply("db.create", 0, { db: "alpha" });
      this.assertEqual(created, 0);
      this.assertEqual(
        store.operation_apply("kv.put", 0, {
          k: "/alpha/a",
          data: bytes_text("one"),
        }),
        1,
      );
      this.assertEqual(
        store.operation_apply("kv.delete", 1, { k: "/alpha/a" }),
        2,
      );
      this.assertEqual(
        store.operation_apply("turn.append", 2, {
          scene,
          role: "user",
          content: { role: "user", content: "1" },
        }),
        3,
      );
      this.assertEqual(
        store.operation_apply("turn.compact", 3, {
          scene,
          through: 1,
          summary: "Answered 1.",
        }),
        4,
      );
      this.assertEqual(store.turn_list(scene), [
        {
          scene,
          n: 1,
          role: "system",
          content: { role: "system", content: "Answered 1." },
        },
      ]);
      const dropped = store.operation_apply("db.drop", 4, { db: "alpha" });
      this.assertEqual(dropped, 0);
      this.assertEqual(store.db_list(), []);
    }

    // An unknown type, other fields or an internal ref throw.
    test_operation_bad(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      this.raised_assert(i18n("substrate.operation_type", "kv.get"), () =>
        store.operation_apply("kv.get", 0, { k: "/alpha/a" }),
      );
      this.raised_assert(
        i18n("substrate.payload_keys", "kv.put", "data,k", "k"),
        () => store.operation_apply("kv.put", 0, { k: "/alpha/a" }),
      );
      const extra = { k: "/alpha/a", db: "alpha" };
      this.raised_assert(
        i18n("substrate.payload_keys", "kv.delete", "k", "db,k"),
        () => store.operation_apply("kv.delete", 0, extra),
      );
      this.raised_assert(i18n("substrate.ref_internal", "a"), () =>
        store.operation_apply("kv.delete", 0, { k: "a" }),
      );
      this.raised_assert(
        i18n("substrate.payload_keys", "sql.run", "params,sql", "sql"),
        () =>
          store.operation_apply("sql.run", 0, {
            db: "alpha",
            statements: [{ sql: "SELECT 1" }],
          }),
      );
      this.assertEqual(store.seq_get("alpha"), 0);
    }

    // Makes the databases the replay starts from by writes, each counted.
    hello_make(store: substrate.Store): void {
      store.db_create("_files");
      store.db_create("metaverse");
      store.sql_run("metaverse", [
        { sql: constants.universe_sql, params: [] },
      ]);
      store.doc_put("metaverse", "hyperposition", {
        0: { t: "scene" },
        subtitle: "How can I help you?",
      });
      const values: [string, string][] = [
        ["/_files/script/bootstrap.js", "// Makes a universe.\n"],
        ["/metaverse/player", "player"],
        ["/metaverse/world", "metaverse"],
        ["/metaverse/scene", constants.scene],
      ];
      for (const [ref, text] of values) {
        store.kv_put(ref, bytes_text(text));
      }
      this.assertEqual(store.seq_get("_files"), 1);
      this.assertEqual(store.seq_get("metaverse"), 5);
      this.lines_of(store).splice(0);
    }

    // Makes a forwarded operation's call and returns the one line it sent.
    modifier_call(
      store: substrate.Store,
      record: RecordedOperation,
    ): lines.Line {
      const fields = record.fields;
      const calls: { [type: string]: () => unknown } = {
        // A value under an external ref.
        "kv.put": () =>
          store.kv_put(fields.k as string, fields.data as Uint8Array),
        // A document.
        "doc.put": () =>
          store.doc_put(
            fields.db as string,
            fields.id as string,
            fields.body as lines.Document,
          ),
        // A database.
        "db.create": () => store.db_create(fields.db as string),
        // A turn.
        "turn.append": () =>
          store.turn_append(
            fields.scene as string,
            fields.role as provider.Role,
            fields.content as provider.ChatMessage,
          ),
        // Statements.
        "sql.run": () =>
          store.sql_run(
            fields.db as string,
            fields.statements as lines.SqlStatement[],
          ),
      };
      calls[record.type]();
      const forwarded = this.lines_of(store).splice(0);
      this.assertEqual(forwarded.length, 1, record.type);
      return forwarded[0];
    }
  }

  // Administration: the measure, compaction, unloading, loading, the start.
  export class TestAdmin extends StoreCase {
    // Each open database is measured by pages and cached values, then all.
    test_stats_measured(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.db_create("beta");
      store.kv_put("/alpha/big", value_over());
      store.kv_put("/alpha/small", bytes_text("small"));
      store.kv_put("/beta/big", bytes_reversed(value_over()));
      const cached = constants.overflow_bytes + 1;
      const databases = [
        stats_measured(store, "alpha", cached),
        stats_measured(store, "beta", cached),
      ];
      const total = databases[0].bytes + databases[1].bytes;
      this.assertEqual(store.db_stats(constants.soft_bytes), {
        databases,
        total_bytes: total,
        soft_bytes: constants.soft_bytes,
        over: false,
      });
      this.assertTrue(store.db_stats(total - 1).over);
      this.assertFalse(store.db_stats(total).over);
    }

    // `VACUUM` frees pages, keeps content and `seq`, and forwards nothing.
    test_compact_vacuum(): void {
      const store = this.store_fresh();
      store.db_create("alpha");
      store.sql_run("alpha", [
        { sql: "CREATE TABLE note (x TEXT)", params: [] },
        {
          sql:
            "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL" +
            " SELECT i + 1 FROM n WHERE i < 2000)" +
            " INSERT INTO note SELECT printf('%0100d', i) FROM n",
          params: [],
        },
      ]);
      store.sql_run("alpha", [{ sql: "DELETE FROM note", params: [] }]);
      this.lines_answer(store);
      const seq = store.seq_get("alpha");
      const dump = content_dump(store, "alpha");
      const before = store.db_stats(constants.soft_bytes).databases[0];
      this.assertTrue(before.free_bytes > 0);
      const compacted = store.db_compact("alpha");
      const after = store.db_stats(constants.soft_bytes).databases[0];
      this.assertEqual(compacted, {
        before: before.bytes,
        after: after.bytes,
      });
      this.assertTrue(after.bytes < before.bytes);
      this.assertEqual(after.free_bytes, 0);
      this.assertEqual(store.seq_get("alpha"), seq);
      this.assertEqual(content_dump(store, "alpha"), dump);
      this.assertEqual(this.lines_of(store), []);
      this.raised_assert(i18n("substrate.db_busy", "alpha"), () =>
        store.transaction_run(() => {
          store.kv_put("/alpha/a", bytes_text("one"));
          store.db_compact("alpha");
        }),
      );
    }

    // Unloading deletes the copy and the files only it names, until loaded.
    test_unload_files(): void {
      const root = this.root_make();
      const cache = cache_make();
      const store = this.store_make(root, cache, true);
      store.db_create("alpha");
      store.db_create("beta");
      const alone = bytes_reversed(value_over());
      const alone_name = utility.sha256_hex(alone);
      const shared_name = utility.sha256_hex(value_over());
      store.kv_put("/alpha/shared", value_over());
      store.kv_put("/alpha/alone", alone);
      store.kv_put("/beta/shared", value_over());
      this.lines_answer(store);
      store.db_unload("alpha");
      this.assertEqual(this.files_under(root), ["beta.sqlite"]);
      this.raised_assert(i18n("substrate.cache_unknown", alone_name), () =>
        cache.cache_read(alone_name, 0, 1),
      );
      this.assertEqual(cache.cache_read(shared_name, 0, 1).length, 1);
      this.assertEqual(this.lines_of(store), []);
      this.assertEqual(store.db_list(), ["beta"]);
      const unloaded = i18n("substrate.db_unloaded", "alpha");
      const calls: (() => unknown)[] = [
        () => store.kv_get("/alpha/shared"),
        () => store.db_open("alpha"),
        () => store.db_create("alpha"),
        () => store.db_drop("alpha"),
        () => store.seq_get("alpha"),
        () => store.db_unload("alpha"),
      ];
      for (const call of calls) {
        this.raised_assert(unloaded, call);
      }
      const measured = store.db_stats(constants.soft_bytes).databases;
      this.assertEqual(
        measured.map((stats) => stats.name),
        ["beta"],
      );
    }

    // Unloading and loading go on with lines in flight, which end after.
    test_load_pending(): void {
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache, true);
      store.db_create("alpha");
      store.kv_put("/alpha/a", bytes_text("one"));
      const snapshot = store.db_snapshot("alpha");
      this.lines_answer(store);
      store.kv_put("/alpha/big", value_over());
      store.db_unload("alpha");
      const name = utility.sha256_hex(value_over());
      this.assertEqual(cache.cache_read(name, 0, 1).length, 1);
      this.assertEqual(store.db_load("alpha", snapshot.data), 1);
      this.assertEqual(store.db_list(), ["alpha"]);
      this.assertEqual(store.kv_get("/alpha/a").data, bytes_text("one"));
      this.raised_assert(i18n("substrate.key_missing", "big", "alpha"), () =>
        store.kv_get("/alpha/big"),
      );
      this.assertEqual(store.kv_put("/alpha/b", bytes_text("two")).seq, 2);
      this.assertEqual(this.lines_of(store).length, 2);
      this.lines_answer(store);
      this.raised_assert(i18n("substrate.cache_unknown", name), () =>
        cache.cache_read(name, 0, 1),
      );
      this.assertEqual(this.lines_of(store), []);
    }

    // At start the held files that match open, the rest wait for a load.
    test_start_open(): void {
      const root = this.root_make();
      const slots = slots_make(constants.slot_count);
      const held = new substrate.CacheFiles(slots);
      const first = this.store_make(root, held, true);
      first.db_create("alpha");
      first.db_create("beta");
      first.db_create("gamma");
      first.kv_put("/alpha/a", bytes_text("one"));
      first.kv_put("/beta/a", bytes_text("one"));
      first.kv_put("/beta/b", bytes_text("two"));
      const snapshot = first.db_snapshot("beta");
      for (const name of first.db_list()) {
        first.db_close(name);
      }
      const cache = new substrate.CacheFiles(slots);
      const second = this.store_make(root, cache, true);
      this.assertEqual(second.start_open({ alpha: 1, beta: 3, delta: 4 }), [
        "beta",
      ]);
      this.assertEqual(second.db_list(), ["alpha"]);
      this.assertEqual(second.seq_get("alpha"), 1);
      this.assertEqual(this.files_under(root), [
        "alpha.sqlite",
        "beta.sqlite",
      ]);
      this.raised_assert(i18n("substrate.db_unloaded", "beta"), () =>
        second.kv_get("/beta/a"),
      );
      this.raised_assert(i18n("substrate.db_unloaded", "delta"), () =>
        second.seq_get("delta"),
      );
      this.assertEqual(second.db_load("beta", snapshot.data), 2);
      this.assertEqual(second.kv_get("/beta/b").data, bytes_text("two"));
      this.assertEqual(second.db_list(), ["alpha", "beta"]);
      this.assertEqual(this.lines_of(second), []);
    }

    // Cached values an unload freed are held again once filled after a load.
    test_value_filled(): void {
      const cache = cache_make();
      const store = this.store_make(this.root_make(), cache, true);
      const other = bytes_reversed(value_over());
      store.db_create("alpha");
      store.kv_put("/alpha/big", value_over());
      store.kv_put("/alpha/other", other);
      store.kv_put("/alpha/small", bytes_text("small"));
      this.lines_answer(store);
      const snapshot = store.db_snapshot("alpha");
      store.db_unload("alpha");
      this.assertEqual(store.db_load("alpha", snapshot.data), 3);
      this.assertFalse(store.kv_held("/alpha/big"));
      this.assertFalse(store.kv_held("/alpha/other"));
      this.assertTrue(store.kv_held("/alpha/small"));
      const name = utility.sha256_hex(value_over());
      this.raised_assert(i18n("substrate.cache_unknown", name), () =>
        cache.cache_read(name, 0, 1),
      );
      const wrong = utility.sha256_hex(other);
      this.raised_assert(
        i18n("substrate.fill_desync", "/alpha/big", wrong, name),
        () => store.cache_fill("/alpha/big", other),
      );
      this.assertFalse(store.kv_held("/alpha/big"));
      store.cache_fill("/alpha/big", sink_fill(cache, value_over()));
      store.cache_fill("/alpha/other", other.slice());
      this.assertTrue(store.kv_held("/alpha/big"));
      this.assertTrue(store.kv_held("/alpha/other"));
      const size = value_over().length;
      this.assertEqual(cache.cache_read(name, 0, size), value_over());
      this.assertEqual(cache.cache_read(wrong, 0, size), other);
      this.assertEqual(store.seq_get("alpha"), 3);
      this.assertEqual(this.lines_of(store), []);
    }
  }

  // The cached values of a database freed by key until they fit a budget.
  export class TestEvict extends StoreCase {
    // Values go by key until the rest fit, the kept ones and the rows staying.
    test_evict_budget(): void {
      const store = this.store_fresh();
      store.db_create("_files");
      const values: [string, Uint8Array][] = [
        ["a", value_over()],
        ["b", bytes_reversed(value_over())],
        ["c", bytes_pattern(constants.overflow_bytes + 2)],
      ];
      for (const [key, data] of values) {
        store.kv_put(`/_files/${key}`, data);
      }
      this.lines_answer(store);
      // The kept refs: one of `_files`, one of another database, one internal.
      const keep = ["/_files/b", "/metaverse/c", "c"];
      const each = constants.overflow_bytes + 1;
      // Whether each value is held, in the order of their keys.
      const values_held = (): boolean[] =>
        values.map(([key]) => store.kv_held(`/_files/${key}`));
      this.assertEqual(store.cache_evict("_files", keep, 3 * each + 1), 0);
      this.assertEqual(values_held(), [true, true, true]);
      this.assertEqual(store.cache_evict("_files", keep, 2 * each + 1), 1);
      this.assertEqual(values_held(), [false, true, true]);
      this.assertEqual(store.cache_evict("_files", keep, 0), 1);
      this.assertEqual(values_held(), [false, true, false]);
      this.assertEqual(store.kv_list("_files", "").length, 3);
      this.assertEqual(store.seq_get("_files"), 3);
      this.assertEqual(this.lines_of(store), []);
    }

    // A value another database names or a line in flight holds stays.
    test_evict_named(): void {
      const store = this.store_fresh();
      store.db_create("_files");
      store.db_create("beta");
      store.kv_put("/_files/shared", value_over());
      store.kv_put("/beta/shared", value_over());
      store.kv_put("/_files/alone", bytes_reversed(value_over()));
      this.lines_answer(store);
      const flying = bytes_pattern(constants.overflow_bytes + 2);
      store.kv_put("/_files/flying", flying);
      this.assertEqual(store.cache_evict("_files", [], 0), 1);
      this.assertFalse(store.kv_held("/_files/alone"));
      this.assertTrue(store.kv_held("/_files/flying"));
      this.assertTrue(store.kv_held("/_files/shared"));
      this.lines_answer(store);
      this.assertEqual(store.cache_evict("_files", [], 0), 1);
      this.assertFalse(store.kv_held("/_files/flying"));
      this.assertTrue(store.kv_held("/_files/shared"));
      this.assertTrue(store.kv_held("/beta/shared"));
    }
  }

  // A put stopped between its cache file and its row, as a kill stops it.
  export class TestCrash extends StoreCase {
    // The stopped put leaves a file and no row, and `kv_check` removes it.
    test_kill_between(): void {
      const root = this.root_make();
      const slots = slots_make(constants.slot_count);
      // The stop that stands for the kill: it throws where the rung kills.
      const kill_stop = (): never => {
        throw new Error(constants.kill_message);
      };
      const pool = kill_pool(this.pool_get(), kill_stop);
      const cache = new substrate.CacheFiles(slots);
      const paused = this.store_make(root, cache, true, pool);
      this.raised_assert(constants.kill_message, () => kill_put(paused));
      paused.db_close(constants.kill_db);
      const name = utility.sha256_hex(value_over());
      const after = new substrate.CacheFiles(slots);
      this.assertEqual(
        after.cache_read(name, 0, 8),
        value_over().subarray(0, 8),
      );
      const checked = this.store_make(root, after, true);
      this.assertEqual(kill_check(checked), { rows: 0, removed: 1 });
      this.assertEqual(checked.seq_get(constants.kill_db), 0);
      this.raised_assert(i18n("substrate.cache_unknown", name), () =>
        after.cache_read(name, 0, 1),
      );
      this.assertEqual(checked.kv_check(constants.kill_db), 0);
    }
  }

  // The handlers of the lines the UI thread submits to the AI thread.
  export class TestHandlers extends StoreCase {
    // Every type is registered at version 0.
    test_types_registered(): void {
      const table = this.handlers_get(this.store_fresh());
      this.assertEqual([...table.keys()].sort(), [
        "db.create",
        "db.drop",
        "db.snapshot",
        "doc.head",
        "doc.put",
        "kv.delete",
        "kv.get",
        "kv.list",
        "kv.put",
        "sql.run",
        "turn.append",
        "turn.compact",
      ]);
    }

    // `kv.put` and `kv.get` answer with the known digest and the bytes.
    test_values_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("metaverse");
      const world = bytes_text("castle_world");
      const put = this.answer_get(
        table,
        request_make("kv.put", 7, {}, "/metaverse/world", [
          jslb.blob_make(world.slice()),
        ]),
      );
      this.assertEqual(
        jslb.line_render(put),
        '{"0":{"t":"kv.put","r":7},"sha256":"' +
          constants.world_sha256 +
          '","seq":1}',
      );
      const got = this.answer_get(
        table,
        request_make("kv.get", 8, {}, "/metaverse/world"),
      );
      this.assertEqual(
        jslb.line_render(got),
        '{"0":{"t":"kv.get","r":8,"b":1},"1":{"s":12},"size":12,"sha256":"' +
          constants.world_sha256 +
          '"}<blob "n"=1>',
      );
      this.assertEqual((got[1] as lines.BlobHeader).d, world);
      this.answer_get(
        table,
        request_make("kv.put", 9, {}, "/metaverse/big", [
          jslb.blob_make(value_over().slice()),
        ]),
      );
      const big = this.answer_get(
        table,
        request_make("kv.get", 10, {}, "/metaverse/big"),
      );
      this.assertEqual((big[1] as lines.BlobHeader).d, value_over());
    }

    // `sql.run`, `kv.list` and `kv.delete` answer their results and `seq`.
    test_rows_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("castle");
      const statements: lines.SqlStatement[] = [
        { sql: constants.world_sql, params: [] },
        {
          sql: "INSERT INTO world VALUES (?, ?)",
          params: ["castle_world", "The castle"],
        },
      ];
      const ran = this.answer_get(
        table,
        request_make("sql.run", 4, { db: "castle", statements }),
      );
      this.assertEqual(
        jslb.line_render(ran),
        '{"0":{"t":"sql.run","r":4},"results":[{"columns":[],"rows":[],' +
          '"changes":0},{"columns":[],"rows":[],"changes":1}],"seq":1}',
      );
      store.kv_put("/castle/world", bytes_text("castle_world"));
      const listed = this.answer_get(
        table,
        request_make("kv.list", 5, { db: "castle", prefix: "wor" }),
      );
      this.assertEqual(
        jslb.line_render(listed),
        '{"0":{"t":"kv.list","r":5},"keys":[{"k":"world","size":12,' +
          '"sha256":"' +
          constants.world_sha256 +
          '"}]}',
      );
      const deleted = this.answer_get(
        table,
        request_make("kv.delete", 6, {}, "/castle/world"),
      );
      this.assertEqual(
        jslb.line_render(deleted),
        '{"0":{"t":"kv.delete","r":6},"seq":3}',
      );
    }

    // Documents and turns answer with their refs, numbers and `seq`.
    test_documents_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      store.db_create("castle_gatehouse");
      store.db_create("metaverse");
      const db = "castle_gatehouse";
      const id = "scene/arrival";
      const put = this.answer_get(
        table,
        request_make("doc.put", 13, { db, id, body: arrival_make() }),
      );
      this.assertEqual(
        jslb.line_render(put),
        '{"0":{"t":"doc.put","r":13},' +
          '"ref":"/castle_gatehouse/scene/arrival/1","seq":1}',
      );
      const head = this.answer_get(
        table,
        request_make("doc.head", 14, { db, id }),
      );
      this.assertEqual(
        jslb.line_render(head),
        '{"0":{"t":"doc.head","r":14},' +
          '"ref":"/castle_gatehouse/scene/arrival/1"}',
      );
      const scene = constants.scene;
      const appended = this.answer_get(
        table,
        request_make("turn.append", 15, {
          scene,
          role: "user",
          content: { role: "user", content: "1" },
        }),
      );
      this.assertEqual(
        jslb.line_render(appended),
        '{"0":{"t":"turn.append","r":15},"n":1,"seq":1}',
      );
      const compacted = this.answer_get(
        table,
        request_make("turn.compact", 16, {
          scene,
          through: 1,
          summary: "Answered 1.",
        }),
      );
      this.assertEqual(
        jslb.line_render(compacted),
        '{"0":{"t":"turn.compact","r":16},"seq":2}',
      );
    }

    // Databases are created, sent as one blob and dropped by their lines.
    test_databases_answered(): void {
      const store = this.store_fresh();
      const table = this.handlers_get(store);
      const created = this.answer_get(
        table,
        request_make("db.create", 17, { db: "alpha" }),
      );
      this.assertEqual(
        jslb.line_render(created),
        '{"0":{"t":"db.create","r":17}}',
      );
      this.assertEqual(store.db_list(), ["alpha"]);
      const data = store.db_snapshot("alpha").data;
      const snapshot = this.answer_get(
        table,
        request_make("db.snapshot", 18, { db: "alpha" }),
      );
      this.assertEqual(snapshot[0], { t: "db.snapshot", r: 18, b: 1 });
      this.assertEqual(jslb.payload_of(snapshot), {
        sha256: utility.sha256_hex(data),
        seq: 0,
      });
      const size = String(data.length);
      this.assertEqual(
        jslb.line_render(snapshot),
        `{"0":{"t":"db.snapshot","r":18,"b":1},"1":{"s":${size}},` +
          `"sha256":"${utility.sha256_hex(data)}","seq":0}<blob "n"=1>`,
      );
      this.assertEqual((snapshot[1] as lines.BlobHeader).d, data);
      this.assertEqual(data.subarray(0, 15), bytes_text(constants.file_magic));
      this.assertFalse(table.has("db.chunk"));
      const dropped = this.answer_get(
        table,
        request_make("db.drop", 21, { db: "alpha" }),
      );
      this.assertEqual(
        jslb.line_render(dropped),
        '{"0":{"t":"db.drop","r":21}}',
      );
      this.assertEqual(store.db_list(), []);
    }

    // The handlers a store registers, by type, each checked at version 0.
    handlers_get(store: substrate.Store): Map<string, dispatch.Handler> {
      const table = new Map<string, dispatch.Handler>();
      store.handlers_register((type, version, fn) => {
        this.assertEqual(version, 0, type);
        table.set(type, fn);
      });
      return table;
    }

    // The reply line the handler of a request's type returns.
    answer_get(
      table: Map<string, dispatch.Handler>,
      request: lines.Line,
    ): lines.Line {
      const type = jslb.field_get(request[0], "type") as string;
      const fn = table.get(type) as dispatch.Handler;
      return fn(request) as lines.Line;
    }
  }

  // The shape of the module object and its classes.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(substrate));
      this.assertEqual(Object.keys(substrate).sort(), [
        "CacheFiles",
        "Store",
        "doc_decode",
        "doc_encode",
        "ref_split",
      ]);
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.Store.prototype).sort(),
        [
          "cache_evict",
          "cache_fill",
          "constructor",
          "db_close",
          "db_compact",
          "db_create",
          "db_drop",
          "db_list",
          "db_load",
          "db_open",
          "db_restore",
          "db_snapshot",
          "db_stats",
          "db_unload",
          "doc_get",
          "doc_head",
          "doc_put",
          "forward_done",
          "forward_set",
          "handlers_register",
          "kv_check",
          "kv_delete",
          "kv_get",
          "kv_held",
          "kv_list",
          "kv_put",
          "operation_apply",
          "seq_get",
          "sink",
          "sql_run",
          "start_open",
          "transaction_run",
          "turn_append",
          "turn_compact",
          "turn_list",
        ],
      );
      this.assertEqual(
        Object.getOwnPropertyNames(substrate.CacheFiles.prototype).sort(),
        [
          "cache_read",
          "constructor",
          "sink_append",
          "sink_close",
          "sink_open",
          "slot_add",
          "slots_free",
        ],
      );
    }
  }
}
Object.freeze(test_substrate);
