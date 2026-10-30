// The bring-up of the one page, the test page, on both of its threads. The
// page's last script, `test_all.suites_run()`, reads `self.name`: "ai" in the
// AI worker, "" on the main thread, never undefined. No program but the test
// suites runs: there is no hello, no start chain and no first render.
//
// The worker: the error overlay first, then the page's first message, the
// wire to the server, whose first line is `tap.start` with `i` 101, then
// sqlite3.wasm and the test pool, cleared at start, set as the globals
// `test_sqlite3` and `test_pool`, the test slots, files cleared at start that
// no cache holds, set as the global `test_slots`, and the test cache, its
// files cleared at start, as the wire's sink, so that a reply's blob over
// `overflow_bytes` streams to a file, then `worker_ai.tap_start`, which
// answers `tap.start` and runs the worker's suites, whose stream sends
// `ui.tests` at its end. `run` gets the queue and, for the wire rungs, the
// first line and the page's address.
//
// The page: the error overlay first, the AI worker made from the texts of the
// worker scripts, then at `settings.set` the UI thread's queue, whose
// `ui.tests` handler runs the UI thread's suites.

declare namespace boot {
  // What the worker's `run` gets beside its queue.
  interface TestStart {
    first: lines.Line;
    base_url: string;
  }

  // The AI worker's bring up, `run` getting its queue once the wire is up.
  function test_worker(
    run: (tasks: queue.TaskQueue, start: TestStart) => void,
  ): void;

  // The page's bring up, `run` getting the UI thread's queue at `ui.tests`.
  function test_page(run: (tasks: queue.TaskQueue) => void): void;
}
