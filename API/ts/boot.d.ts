// The bring-up of the two test pages. The ttyd page's last script,
// `test_all.suites_run()`, reads `self.name`: "ai" in the AI worker, "" on the
// main thread, never undefined. No program but the test suites runs: there is
// no hello, no start chain and no first render.
//
// The worker: the error overlay first, then the page's first message, the
// wire, then the platform, whose sqlite3.wasm, test pool and test slots are
// set as the globals `test_sqlite3`, `test_pool` and `test_slots`, then the
// test cache as the wire's sink, then `worker_ai.tap_start`. The page: the
// error overlay first, the AI worker made from the texts of the worker
// scripts, then at `settings.set` the UI thread's queue.
//
// The headless worker, whose page `test_headless` runs, takes the worker's
// ends of the realm lane and the UI channel and the start from the page's
// first message. With `clear` false it keeps what the worker before it left,
// and first waits for every file to open, since the platform frees the files
// of a worker it terminated in a loop about 2 s later and tells no one. Past
// `wait_seconds` it throws `boot.files_busy`, the refusal as its `cause`. The
// realm lane's end calls back at once, since the lane keeps its order and the
// page relays each line to the driver as it comes.

declare namespace boot {
  // What the worker's `run` gets beside its queue.
  interface TestStart {
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
  type HeadlessStart = StartFields &
    ({ clear: true } | { clear: false; wait_seconds: number });

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
