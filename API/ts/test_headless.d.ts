// The headless realm of one block of group B or C, on the page whose last
// script, a worker script, is `test_headless.realm_open()`: on the main
// thread it opens the lane `realm` to the driver over DevTools, and in the
// worker named "ai" it brings the worker up by `boot.headless_worker`. The
// driver adds the binding `realm_line` before the page loads, then calls
// `realm_start(BLOCK, FAILFAST, LINE)`, LINE the base64 of the bytes of
// `tap.start` with `i` 101. A block runs on one side: `ui`, on the main
// thread in its own page load; `worker`, in a fresh worker; `lanes`, on
// the main thread over a fresh worker brought up as a worker block's is; or
// `workers`, on the main thread over a fresh worker for each case.
//
// A block of the side `lanes` gives a `LanesBuild`. The page sets the
// settings and the harness's values, answers `tap.start` with an Empty
// reply, brings the worker up with the same start, and runs
// `line_case.block_run` on the gold `typescript.BLOCK` with the topology
// that calls the `LanesBuild` with the first line, the page's ends of the
// worker's two channels, its lane to the server and its channel to the UI
// thread, and the writer of a line to the driver. It returns the test's end.
// The page writes the TAP, and the worker runs no block.
//
// A block of the side `workers` gives a `WorkerRun`. The page sets the
// settings and the harness's values, answers `tap.start`, and runs
// `line_case.block_run` on the gold `typescript.BLOCK` with a topology of
// its own, whose junction takes the lines each case sends. Each case sends
// first the notice `test_headless.worker_start`, whose payload is
// `{clear}`, with `wait_seconds` too when `clear` is false: the junction
// ends the worker of the case before, then brings up a fresh worker with the
// page's start, that `clear` and those `wait_seconds`. Each other line
// a case sends is held, then posted in order on the worker's UI channel
// once the worker has sent the notice `test_headless.worker_ready` on its
// server lane. Every line of the server lane goes to the test's end but
// each `verbose.put`, which goes to the driver, and every line of the UI
// channel but `settings.set`, which goes to the driver. The worker's
// `fault` line is held and checked against its `error` line, the same
// message, stack and cause chain; one that differs, or that has no `error`
// line by the worker's end, goes to the driver, which fails the block. A
// worker is ended by `Worker.terminate`, at once, unless it sent an `error`
// line whose `fault` line has not come, then when it comes; the last one at
// the block's end. In each worker the `WorkerRun` runs in the task of
// `worker.tests`, and the worker runs no block. The page writes the TAP.

declare namespace test_headless {
  // Builds the far ends of a fresh worker's channels, the test's end of them.
  type LanesBuild = (
    first: lines.Line,
    server: MessagePort,
    ui: MessagePort,
    relay: (line: lines.Line) => void,
  ) => queue.ThreadPort;

  // Runs a block's part in each fresh worker, `ready` once its topology is up.
  type WorkerRun = (
    tasks: queue.TaskQueue,
    start: boot.HeadlessStart,
    ready: () => void,
  ) => void;

  // Opens the realm lane on the main thread, or brings the worker up.
  function realm_open(): void;

  // Takes the driver's block, failfast and first line, and runs the block.
  function realm_start(block: string, failfast: boolean, line: string): void;
}
