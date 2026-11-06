// The headless realm of one block of group B or C: the main thread opens the
// lane `realm` to the driver over DevTools. The driver adds the binding
// `realm_line` before the page loads, then calls `realm_start(BLOCK, FAILFAST,
// LINE)`, LINE the base64 of `tap.start` with `i` 101.
//
// A block runs on one side: `ui`, on the main thread in its own page load;
// `worker`, in a fresh worker; `lanes`, on the main thread over a fresh
// worker; or `workers`, on the main thread over a fresh worker for each case.
// In `lanes` and `workers` the page writes the TAP and the worker runs no
// block.
//
// Each `workers` case first sends the notice `test_headless.worker_start`,
// `{clear}` with `wait_seconds` too when `clear` is false: the junction ends
// the case before's worker and brings up a fresh one. Its other lines are held
// until the worker sends `test_headless.worker_ready`. Every line of the
// server lane goes to the test's end but `verbose.put`, and every line of the
// UI channel but `settings.set`, which go to the driver. A `fault` line that
// differs from the worker's `error` line, or has none by the worker's end,
// goes to the driver, which fails the block.

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
