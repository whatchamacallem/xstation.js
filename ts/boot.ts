// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The bring-up of the two test pages. The ttyd page, on both of its threads:
// its last script, `test_all.suites_run()`, reads `self.name`: "ai" in the
// AI worker, "" on the main thread, never undefined. No program but the test
// suites runs: there is no hello, no start chain and no first render.
//
// The worker: the error overlay first, then the page's first message, the
// wire to the server, whose first line is `tap.start` with `i` 101, then the
// platform: sqlite3.wasm and the test pool, cleared at start, set as the
// globals `test_sqlite3` and `test_pool`, and the test slots, files cleared
// at start that no cache holds, set as the global `test_slots`; then the
// test cache, its files cleared at start, as the wire's sink, so that a
// reply's blob over `overflow_bytes` streams to a file, then
// `worker_ai.tap_start`, the wire its server's port and `wire_end` its end,
// which answers `tap.start` and runs the worker's suites, whose stream sends
// `ui.tests` at its end. `run` gets the queue and, for the wire rungs, the
// first line and the page's address. Initialization waits on the platform's
// promises here, the one module that does so outside the task manager.
//
// The page: the error overlay first, the AI worker made from the texts of the
// worker scripts, then at `settings.set` the UI thread's queue, whose
// `ui.tests` handler runs the UI thread's suites.
//
// The headless worker, whose page `test_headless` runs: the error overlay
// first, then the page's first message, which holds the worker's end of the
// realm lane, its end of the UI channel, and the start: `tap.start`, which
// the page took from the driver, and the block the driver named with its
// failfast. The platform then starts by the same code as the ttyd worker's,
// then `worker_ai.tap_start`, the realm lane its server's port, a
// `queue.ThreadPort`, whose end posts the line on the lane and calls back at
// once, since the lane keeps its order and the page relays each line to the
// driver as it comes. `run` gets the queue and the start.

namespace boot {
  // The options of `installOpfsSAHPoolVfs` that the bring up sets.
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

  // What the worker's `run` gets beside its queue.
  export interface TestStart {
    first: lines.Line;
    base_url: string;
  }

  // What the headless worker's `run` gets beside its queue.
  export interface HeadlessStart {
    first: lines.Line;
    block: string;
    failfast: boolean;
  }

  // The headless page's first message to its worker: its lanes and start.
  export interface HeadlessMessage {
    server: MessagePort;
    ui: MessagePort;
    start: HeadlessStart;
  }

  // The text of sqlite3.wasm in base64, which a worker script defines.
  declare const sqlite3_wasm_base64: string;

  // The module factory of SQLite's glue, which a worker script defines.
  declare function sqlite3InitModule(options: {
    wasmBinary: Uint8Array;
  }): Promise<SqliteStart>;

  // The test pool and the test cache's files.
  const constants = Object.freeze({
    test_pool_name: "xsjs-test-pool",
    test_pool_directory: ".xsjs-test-pool",
    // The test page's pool, cleared at start, a default chosen by its writer.
    test_capacity: 32,
    test_cache_directory: "xsjs-test-cache",
    // The test cache's files, its writer's choice, for three streamed echoes.
    test_slot_count: 8,
    test_slots_directory: "xsjs-test-slots",
    // The test slots, its writer's choice, for two caches and a closed file.
    test_slots_count: 3,
  });

  // Calls `fn` with the page's first message, which starts the worker.
  function start_await<Message>(fn: (message: Message) => void): void {
    self.onmessage = (event: MessageEvent<unknown>) => {
      fn(event.data as Message);
    };
  }

  // Initializes sqlite3.wasm from the base64 text of its binary.
  function module_init(): Promise<SqliteStart> {
    const binary = utility.base64_decode(sqlite3_wasm_base64);
    return sqlite3InitModule({ wasmBinary: binary });
  }

  // Opens `count` files of an OPFS directory for synchronous access.
  function slots_open(
    name: string,
    count: number,
  ): Promise<substrate.SlotHandle[]> {
    return navigator.storage
      .getDirectory()
      .then((root) => root.getDirectoryHandle(name, { create: true }))
      .then((directory) =>
        Promise.all(
          Array.from({ length: count }, (_value, index) =>
            directory
              .getFileHandle(String(index), { create: true })
              .then((file) =>
                (file as unknown as SyncOpener).createSyncAccessHandle(),
              ),
          ),
        ),
      );
  }

  // Starts sqlite3.wasm, the test pool and the test slots, and sets them.
  function platform_open(): Promise<void> {
    return module_init().then((sqlite3) =>
      sqlite3
        .installOpfsSAHPoolVfs({
          name: constants.test_pool_name,
          directory: constants.test_pool_directory,
          initialCapacity: constants.test_capacity,
          clearOnInit: true,
        })
        .then((pool) =>
          slots_open(
            constants.test_slots_directory,
            constants.test_slots_count,
          ).then((test_slots) => {
            // Cleared at start, as the test pool is.
            for (const slot of test_slots) {
              slot.truncate(0);
            }
            Object.assign(globalThis, {
              test_sqlite3: sqlite3,
              test_pool: pool,
              test_slots,
            });
          }),
        ),
    );
  }

  // Opens the wire, and at `tap.start` readies the test platform and runs.
  function tests_open(
    message: StartMessage,
    run: (tasks: queue.TaskQueue, start: TestStart) => void,
  ): void {
    const cache = new substrate.CacheFiles([]);
    const port = new wire.WirePort(
      message.base_url,
      cache,
      settings.settings_get,
    );
    port.wire_open((first: lines.Line) => {
      platform_open()
        .then(() =>
          slots_open(
            constants.test_cache_directory,
            constants.test_slot_count,
          ),
        )
        .then((slots) => {
          // Cleared at start, as the test pool is.
          for (const slot of slots) {
            slot.truncate(0);
            cache.slot_add(slot);
          }
          const start = { first, base_url: message.base_url };
          const parts: worker_ai.TapParts = {
            first,
            server: port,
            end: (line, done) => port.wire_end(line, done),
            ui: message.port,
          };
          worker_ai.tap_start(parts, (tasks) => run(tasks, start));
        });
    });
  }

  // Takes the headless page's start, readies the test platform and runs.
  function headless_open(
    message: HeadlessMessage,
    run: (tasks: queue.TaskQueue, start: HeadlessStart) => void,
  ): void {
    const server = new queue.ThreadPort(message.server);
    const start = message.start;
    platform_open().then(() => {
      const parts: worker_ai.TapParts = {
        first: start.first,
        server,
        // The lane keeps its order, and the page relays each line at once.
        end: (line, done) => {
          server.line_post(line, []);
          done();
        },
        ui: message.ui,
      };
      worker_ai.tap_start(parts, (tasks) => run(tasks, start));
    });
  }

  // The page's bring up, `run` getting the UI thread's queue at `ui.tests`.
  export const test_page = page.test_page;

  // The AI worker's bring up, `run` getting its queue once the wire is up.
  export function test_worker(
    run: (tasks: queue.TaskQueue, start: TestStart) => void,
  ): void {
    error_overlay.overlay_install();
    start_await<StartMessage>((message) => tests_open(message, run));
  }

  // The headless worker's bring up, `run` getting its queue at the start.
  export function headless_worker(
    run: (tasks: queue.TaskQueue, start: HeadlessStart) => void,
  ): void {
    error_overlay.overlay_install();
    start_await<HeadlessMessage>((message) => headless_open(message, run));
  }
}

Object.freeze(boot);
