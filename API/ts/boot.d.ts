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
// first line and the page's address.
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

declare namespace boot {
  // What the worker's `run` gets beside its queue.
  interface TestStart {
    first: lines.Line;
    base_url: string;
  }

  // What the headless worker's `run` gets beside its queue.
  interface HeadlessStart {
    first: lines.Line;
    block: string;
    failfast: boolean;
  }

  // The headless page's first message to its worker: its lanes and start.
  interface HeadlessMessage {
    server: MessagePort;
    ui: MessagePort;
    start: HeadlessStart;
  }

  // The AI worker's bring up, `run` getting its queue once the wire is up.
  function test_worker(
    run: (tasks: queue.TaskQueue, start: TestStart) => void,
  ): void;

  // The headless worker's bring up, `run` getting its queue at the start.
  function headless_worker(
    run: (tasks: queue.TaskQueue, start: HeadlessStart) => void,
  ): void;

  // The page's bring up, `run` getting the UI thread's queue at `ui.tests`.
  function test_page(run: (tasks: queue.TaskQueue) => void): void;
}
