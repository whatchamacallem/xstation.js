declare namespace tap_producer {
  // tappy's `Tracker`, with the names and parameters of the Python producer.
  class Tracker {
    add_ok(
      class_name: string,
      description: string,
      directive?: string,
      diagnostics?: string
    ): void;
    add_not_ok(
      class_name: string,
      description: string,
      directive?: string,
      diagnostics?: string
    ): void;
    add_skip(class_name: string, description: string, reason: string): void;
    // Sets the number of points the plan line announces.
    set_plan(total: number): void;
    // Writes the points collected so far as TAP.
    generate_tap_reports(): void;
  }

  // tappy's `TAPTestRunner`: runs a suite as Python's
  // `unittest.TextTestRunner` does, its results written as TAP.
  class TAPTestRunner {
    // As `TextTestRunner(failfast=...)`.
    constructor(failfast: boolean);
    // Streams each TAP line as it is produced; the test page submits each
    // as `tap.line` at once.
    set_stream(streaming: boolean): void;
    run(test: unittest.TestSuite): unittest.TestResult;
  }

  // Marks every `not ok` line and its diagnostic lines, whole line, and
  // nothing else, for test.html.
  function report_html(text: string): string;
}
