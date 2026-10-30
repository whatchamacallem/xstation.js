// tappy's producer, with the names and parameters of the Python producer:
// one TAP version 14 stream, a parent plan, and one indented block per test
// module, each with its own plan. Each line goes to the stream's writer the
// moment it is made; the bring up sends each as a `tap.line` at once. A
// block whose points arrive after the call that starts it, as line cases
// do, opens with `block_start`, which writes its plan of the count given at
// once, as every block's plan comes first, and closes with `block_end`,
// which writes its parent line, or with failfast after a failed point the
// bail out line, and returns whether it passed. A failed point is `not ok`
// without a `TODO` directive. No module or block runs while one is open, and
// the stream does not end then.

declare namespace tap_producer {
  // Writes the lines of one level of a stream the moment each is added.
  class Tracker {
    // `write` takes each line, without its newline.
    constructor(write: (text: string) => void);
    // Writes the plan at once, before the points.
    set_plan(total: number): void;
    // `class_name` is tappy's and is not written.
    add_ok(
      class_name: string,
      description: string,
      directive?: string,
      diagnostics?: string,
    ): void;
    add_not_ok(
      class_name: string,
      description: string,
      directive?: string,
      diagnostics?: string,
    ): void;
    // A passing point with a `SKIP` directive and the reason.
    add_skip(class_name: string, description: string, reason: string): void;
    // Writes the plan of the points added, for a level whose plan comes last.
    generate_tap_reports(): void;
  }

  // Turns the harness's outcomes into one point per test, as Python's does.
  class TAPTestResult extends unittest.TestResult {
    // `tracker` writes the points, `failfast` stops at the first failure.
    constructor(tracker: Tracker, failfast: boolean);
    startTest(test: unittest.TestCase): void;
    addSuccess(test: unittest.TestCase): void;
    addSkip(test: unittest.TestCase, reason: string): void;
    addFailure(test: unittest.TestCase, error: Error): void;
    addError(test: unittest.TestCase, error: Error): void;
    addExpectedFailure(test: unittest.TestCase, error: Error): void;
    addUnexpectedSuccess(test: unittest.TestCase): void;
    // Writes the point of the last test. Throws when it had no outcome.
    point_flush(): void;
  }

  // Writes TAP for a unittest run: one plan, one indented block per module.
  class TAPTestRunner {
    // As `TextTestRunner(failfast=...)`.
    constructor(failfast: boolean);
    // Whether the first failure ends the stream, as Python's runner keeps it.
    readonly failfast: boolean;
    // Sends each line to `write` as it is made, the version line first.
    set_stream(write: (text: string) => void): void;
    // Runs the suite as one block, its plan first, and returns its result.
    run(test: unittest.TestSuite): TAPTestResult;
    // Loads and runs one module as a block. True when it passed.
    module_run(module: string, load: () => unittest.TestSuite): boolean;
    // Opens a block, writes its plan of `count` points, returns its tracker.
    block_start(name: string, count: number): Tracker;
    // Writes the block's parent line, or failfast's bail out.
    block_end(name: string): boolean;
    // Writes the parent plan unless the stream bailed out. True if all passed.
    run_end(): boolean;
  }

  // Marks every `not ok` line and its diagnostic lines, for the test page.
  function report_html(text: string): string;
}
