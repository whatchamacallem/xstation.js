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
// its pool and test slots cleared at start unless the start's `clear` is
// false, when the worker keeps what the worker before it left in them. Such
// a worker first waits for every file of the pool's directory and of the
// slots' directory to open, since the platform frees the files of a worker
// it terminated in a loop about 2 s later and tells no one: it opens each
// file for synchronous access and closes it at once, and a refusal of a file
// still held, a `DOMException` named `NoModificationAllowedError`, ends the
// try, which comes again 10 ms later; anything else is thrown. Once a try is
// refused after the start's `wait_seconds`, it throws `boot.files_busy` with
// that refusal as its `cause`. The wait comes before the pool's install,
// since SQLite keeps a failed install as the answer to every later one. Then
// comes `worker_ai.tap_start`, the realm lane its server's port, a
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

  // A handle for synchronous access, which the wait closes once it opens.
  interface SyncHandle extends substrate.SlotHandle {
    close(): void;
  }

  // A file of OPFS that opens a handle for synchronous access in a worker.
  interface SyncOpener {
    createSyncAccessHandle(): Promise<SyncHandle>;
  }

  // A directory of OPFS listing its entries, which the DOM types lack.
  interface EntryLister {
    values(): AsyncIterable<FileSystemHandle>;
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

  // What every start of the headless worker holds.
  interface StartFields {
    first: lines.Line;
    block: string;
    failfast: boolean;
  }

  // A start that clears the test pool and slots, or keeps them and waits.
  export type HeadlessStart = StartFields &
    ({ clear: true } | { clear: false; wait_seconds: number });

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
    // The test slots, its writer's choice, for two caches of four files.
    test_slots_count: 8,
    // The name of the platform's refusal to open a file another worker holds.
    busy_name: "NoModificationAllowedError",
    // Between tries of held files: a try took 3.5 ms, the release 2.05 s.
    busy_ms: 10,
    second_ms: 1000,
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
  function platform_open(clear: boolean): Promise<void> {
    return module_init().then((sqlite3) =>
      sqlite3
        .installOpfsSAHPoolVfs({
          name: constants.test_pool_name,
          directory: constants.test_pool_directory,
          initialCapacity: constants.test_capacity,
          clearOnInit: clear,
        })
        .then((pool) =>
          slots_open(
            constants.test_slots_directory,
            constants.test_slots_count,
          ).then((test_slots) => {
            // Cleared at start when the test pool is.
            if (clear) {
              for (const slot of test_slots) {
                slot.truncate(0);
              }
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

  // The files under an OPFS directory, those of its subdirectories included.
  async function files_under(
    directory: FileSystemDirectoryHandle,
  ): Promise<FileSystemFileHandle[]> {
    const files: FileSystemFileHandle[] = [];
    for await (const entry of (directory as unknown as EntryLister).values()) {
      if (entry.kind === "file") {
        files.push(entry as FileSystemFileHandle);
      } else {
        files.push(...(await files_under(entry as FileSystemDirectoryHandle)));
      }
    }
    return files;
  }

  // Opens and closes each file of the directories, a refusal of a held one.
  async function files_try(
    names: readonly string[],
  ): Promise<DOMException | undefined> {
    const root = await navigator.storage.getDirectory();
    for (const name of names) {
      const directory = await root.getDirectoryHandle(name, { create: true });
      for (const file of await files_under(directory)) {
        const opener = file as unknown as SyncOpener;
        try {
          (await opener.createSyncAccessHandle()).close();
        } catch (error) {
          if (
            error instanceof DOMException &&
            error.name === constants.busy_name
          ) {
            return error;
          }
          throw error;
        }
      }
    }
    return undefined;
  }

  // Waits until no file of the pool or the slots is held, or throws.
  async function files_wait(seconds: number): Promise<void> {
    const end = performance.now() + seconds * constants.second_ms;
    const names = [
      constants.test_pool_directory,
      constants.test_slots_directory,
    ];
    for (;;) {
      const busy = await files_try(names);
      if (busy === undefined) {
        return;
      }
      if (performance.now() >= end) {
        throw utility.error_wrap(i18n("boot.files_busy", seconds), busy);
      }
      await new Promise<void>((resolve) => {
        setTimeout(resolve, constants.busy_ms);
      });
    }
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
      platform_open(true)
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
    const opened = start.clear
      ? platform_open(true)
      : files_wait(start.wait_seconds).then(() => platform_open(false));
    opened.then(() => {
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
