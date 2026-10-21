// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The entry of the one bundle on both threads, chosen by the thread's name,
// and the initialization of the AI worker: the page's channel and address,
// the wire to the server, and once the hello is in, sqlite3.wasm from its
// base64 text, the OPFS SAH pool with room for every database the server
// holds, and the cache's files opened for synchronous access. Initialization
// waits on the platform's promises here, the one module that does so outside
// the task manager. Once it hands its objects over, the worker runs on the
// task manager alone.

namespace boot {
  // The options of `installOpfsSAHPoolVfs` that the start sets.
  interface PoolOptions {
    name: string;
    directory: string;
    initialCapacity: number;
    clearOnInit: boolean;
  }

  // The module `sqlite3InitModule` resolves to, with the pool's installer.
  interface SqliteStart extends substrate.SqliteModule {
    installOpfsSAHPoolVfs(options: PoolOptions): Promise<substrate.SqlitePool>;
  }

  // A file of OPFS that opens a handle for synchronous access in a worker.
  interface SyncOpener {
    createSyncAccessHandle(): Promise<substrate.SlotHandle>;
  }

  // The page's first message to the worker: the channel's end and its address.
  interface StartMessage {
    port: MessagePort;
    base_url: string;
  }

  // The module and the pool the start hands over.
  interface SqliteParts {
    sqlite3: substrate.SqliteModule;
    pool: substrate.SqlitePool;
  }

  // The text of sqlite3.wasm in base64, which a worker script defines.
  declare const sqlite3_wasm_base64: string;

  // The module factory of SQLite's glue, which a worker script defines.
  declare function sqlite3InitModule(options: {
    wasmBinary: Uint8Array;
  }): Promise<SqliteStart>;

  // The worker's name, the pools, the cache's files.
  const constants = Object.freeze({
    worker_name: "ai",
    pool_name: "xsjs-pool",
    pool_directory: ".xsjs-pool",
    // The pool's files of one database: its file and its journal.
    database_files: 2,
    // A default chosen by its writer: 16 more databases, 4 temporary files.
    pool_spare: 36,
    cache_directory: "xsjs-cache",
    // The cache's files, a default chosen by its writer.
    slot_count: 256,
    test_pool_name: "xsjs-test-pool",
    test_pool_directory: ".xsjs-test-pool",
    // The test page's pool, cleared at start, a default chosen by its writer.
    test_capacity: 32,
  });

  // The pool files for the server's databases, a journal each, and spares.
  export function pool_capacity(databases: number): number {
    return databases * constants.database_files + constants.pool_spare;
  }

  // Calls `fn` with the page's first message, which starts the worker.
  function start_await(fn: (message: StartMessage) => void): void {
    self.onmessage = (event: MessageEvent<unknown>) => {
      fn(event.data as StartMessage);
    };
  }

  // Initializes sqlite3.wasm from the base64 text of its binary.
  function module_init(): Promise<SqliteStart> {
    const binary = utility.base64_decode(sqlite3_wasm_base64);
    return sqlite3InitModule({ wasmBinary: binary });
  }

  // Opens the cache's files in their OPFS directory for synchronous access.
  function slots_open(): Promise<substrate.SlotHandle[]> {
    return navigator.storage
      .getDirectory()
      .then((root) =>
        root.getDirectoryHandle(constants.cache_directory, { create: true }),
      )
      .then((directory) =>
        Promise.all(
          Array.from({ length: constants.slot_count }, (_value, index) =>
            directory
              .getFileHandle(String(index), { create: true })
              .then((file) =>
                (file as unknown as SyncOpener).createSyncAccessHandle(),
              ),
          ),
        ),
      );
  }

  // The module, the pool for the server's databases, the cache's files.
  function engine_platform(
    databases: number,
    cache: substrate.CacheFiles,
  ): Promise<SqliteParts> {
    return module_init().then((sqlite3) =>
      sqlite3
        .installOpfsSAHPoolVfs({
          name: constants.pool_name,
          directory: constants.pool_directory,
          initialCapacity: pool_capacity(databases),
          clearOnInit: false,
        })
        .then((pool) =>
          slots_open().then((slots) => {
            for (const slot of slots) {
              cache.slot_add(slot);
            }
            return { sqlite3, pool };
          }),
        ),
    );
  }

  // Opens the wire, and at the hello readies the platform and runs the worker.
  function engine_open(message: StartMessage): void {
    const cache = new substrate.CacheFiles([]);
    const port = new wire.WirePort(
      message.base_url,
      cache,
      settings.settings_get,
    );
    port.cache_attach((handle, offset, length) =>
      cache.cache_read(handle, offset, length),
    );
    port.wire_open((hello: lines.Line) => {
      const seq = hello.seq as { [db: string]: number };
      engine_platform(Object.keys(seq).length, cache).then((parts) =>
        worker_ai.worker_start({
          hello,
          wire: port,
          ui: message.port,
          base_url: message.base_url,
          sqlite3: parts.sqlite3,
          pool: parts.pool,
          cache,
        }),
      );
    });
  }

  // Opens the wire, and at the hello sets the test globals and runs the tests.
  function tests_open(
    message: StartMessage,
    run: (tasks: queue.TaskQueue) => void,
  ): void {
    const port = new wire.WirePort(
      message.base_url,
      new substrate.CacheFiles([]),
      settings.settings_get,
    );
    port.wire_open((hello: lines.Line) => {
      module_init().then((sqlite3) =>
        sqlite3
          .installOpfsSAHPoolVfs({
            name: constants.test_pool_name,
            directory: constants.test_pool_directory,
            initialCapacity: constants.test_capacity,
            clearOnInit: true,
          })
          .then((pool) => {
            Object.assign(globalThis, {
              test_sqlite3: sqlite3,
              test_pool: pool,
            });
            worker_ai.test_start({ hello, wire: port, ui: message.port }, run);
          }),
      );
    });
  }

  // The UI thread of the engine page.
  export const page_main = page.page_main;

  // The DOM port of the UI thread.
  export type DomPort = page.DomPort;

  // The DOM port of the UI thread, the class itself.
  export const DomPort = page.DomPort;

  // The UI thread of the test page, which runs the tests it is given.
  export const test_page = page.test_page;

  // The UI thread of the engine page, which gives its live queue to a caller.
  export const test_engine = page.test_engine;

  // The AI worker of the engine page: faults first, then the page's message.
  export function worker_ai_main(): void {
    error_overlay.overlay_install();
    start_await((message) => engine_open(message));
  }

  // The AI worker of the test page, which runs the tests it is given.
  export function test_worker(run: (tasks: queue.TaskQueue) => void): void {
    error_overlay.overlay_install();
    start_await((message) => tests_open(message, run));
  }

  // Runs the worker when the thread's name is `ai`, else the page.
  export function boot_run(): void {
    if (self.name === constants.worker_name) {
      worker_ai_main();
    } else {
      page_main();
    }
  }
}

Object.freeze(boot);
