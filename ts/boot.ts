// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The bring-up of the three pages. API/ts/boot.d.ts holds its order.
// Initialization waits on the platform's promises here, the one module that
// does so outside the task manager.
//
// A headless worker with `clear` false and the engine worker first wait for
// their files to open. A file still held refuses with a `DOMException` named
// `NoModificationAllowedError`, which ends the try, and the next comes 10 ms
// later; anything else is thrown. The wait comes before the pool's install,
// since SQLite keeps a failed install as the answer to every later one.

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

  // What the worker's `run` gets beside its queue: its platform and wire sink.
  export interface WorkerStart {
    first: lines.Line;
    base_url: string;
    sqlite3: substrate.SqliteModule;
    pool: substrate.SqlitePool;
    cache: substrate.CacheFiles;
  }

  // sqlite3.wasm once it has started and its pool once it is installed.
  interface PoolParts {
    sqlite3: substrate.SqliteModule;
    pool: substrate.SqlitePool;
  }

  // What sets the test worker's bring up and the engine worker's apart.
  interface WorkerPlan {
    platform: () => Promise<PoolParts>;
    cache_directory: string;
    cache_count: number;
    overlay: boolean;
  }

  // What every start of the headless worker holds.
  export interface StartFields {
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

  // The pools and the caches' files of the test and engine platforms.
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
    engine_pool_name: "xsjs-engine-pool",
    engine_pool_directory: ".xsjs-engine-pool",
    // The engine page's pool, cleared at start.
    engine_capacity: 64,
    engine_cache_directory: "xsjs-engine-cache",
    // The engine page's cache, cleared at start.
    engine_slot_count: 64,
    // The wait for the files of a reloaded page, past their 2.05 s release.
    engine_wait_seconds: 5,
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

  // Starts sqlite3.wasm and installs its pool.
  function pool_open(options: PoolOptions): Promise<PoolParts> {
    return module_init().then((sqlite3) =>
      sqlite3
        .installOpfsSAHPoolVfs(options)
        .then((pool) => ({ sqlite3, pool })),
    );
  }

  // Starts sqlite3.wasm, the test pool and the test slots, and sets them.
  function platform_open(clear: boolean): Promise<PoolParts> {
    return pool_open({
      name: constants.test_pool_name,
      directory: constants.test_pool_directory,
      initialCapacity: constants.test_capacity,
      clearOnInit: clear,
    }).then((parts) =>
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
          test_sqlite3: parts.sqlite3,
          test_pool: parts.pool,
          test_slots,
        });
        return parts;
      }),
    );
  }

  // Waits for the files a reload left held, then starts the cleared pool.
  function engine_open(): Promise<PoolParts> {
    return files_wait(
      [constants.engine_pool_directory, constants.engine_cache_directory],
      constants.engine_wait_seconds,
    ).then(() =>
      pool_open({
        name: constants.engine_pool_name,
        directory: constants.engine_pool_directory,
        initialCapacity: constants.engine_capacity,
        clearOnInit: true,
      }),
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

  // Waits until no file of the directories is held, or throws.
  async function files_wait(
    names: readonly string[],
    seconds: number,
  ): Promise<void> {
    const end = performance.now() + seconds * constants.second_ms;
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

  // The test worker's platform, its wire's lines kept off the overlay.
  const test_plan = Object.freeze<WorkerPlan>({
    platform: () => platform_open(true),
    cache_directory: constants.test_cache_directory,
    cache_count: constants.test_slot_count,
    overlay: false,
  });

  // The engine worker's platform, its wire's lines shown on the overlay.
  const engine_plan = Object.freeze<WorkerPlan>({
    platform: engine_open,
    cache_directory: constants.engine_cache_directory,
    cache_count: constants.engine_slot_count,
    overlay: true,
  });

  // Opens the wire, and at `tap.start` readies the plan's platform and runs.
  function worker_open(
    message: StartMessage,
    plan: WorkerPlan,
    run: (tasks: queue.TaskQueue, start: WorkerStart) => void,
  ): void {
    const cache = new substrate.CacheFiles([]);
    const port = new wire.WirePort(
      message.base_url,
      cache,
      settings.settings_get,
    );
    port.wire_open((first: lines.Line) => {
      plan.platform().then(({ sqlite3, pool }) =>
        slots_open(plan.cache_directory, plan.cache_count).then((slots) => {
          // Cleared at start, as the pool is.
          for (const slot of slots) {
            slot.truncate(0);
            cache.slot_add(slot);
          }
          const { base_url } = message;
          const start = { first, base_url, sqlite3, pool, cache };
          const parts: worker_ai.TapParts = {
            first,
            server: port,
            end: (line, done) => port.wire_end(line, done),
            ui: message.port,
            console: new wire.ConsolePort(base_url),
            overlay: plan.overlay,
          };
          worker_ai.tap_start(parts, (tasks) => run(tasks, start));
        }),
      );
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
      : files_wait(
          [constants.test_pool_directory, constants.test_slots_directory],
          start.wait_seconds,
        ).then(() => platform_open(false));
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
        // The headless page has no ttyd, so no tty 0.
        console: undefined,
        overlay: false,
      };
      worker_ai.tap_start(parts, (tasks) => run(tasks, start));
    });
  }

  // The page's bring up, `run` getting the UI thread's queue at `ui.tests`.
  export const test_page = page.test_page;

  // The AI worker's bring up, `run` getting its queue once the wire is up.
  export function test_worker(
    run: (tasks: queue.TaskQueue, start: WorkerStart) => void,
  ): void {
    error_overlay.overlay_install();
    start_await<StartMessage>((message) =>
      worker_open(message, test_plan, run),
    );
  }

  // The engine page's AI worker's bring up, `run` as in `test_worker`.
  export function engine_worker(
    run: (tasks: queue.TaskQueue, start: WorkerStart) => void,
  ): void {
    error_overlay.overlay_install();
    start_await<StartMessage>((message) =>
      worker_open(message, engine_plan, run),
    );
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
