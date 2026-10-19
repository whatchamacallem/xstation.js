declare namespace tap {
  // The producer: writes TAP for a unittest run with the same text as
  // python/tap/producer.py, one plan, one indented block per module.
  class TapRunner {
    // `write` gets each TAP line as it is produced; the test page submits
    // it as `tap.line` at once.
    constructor(write: (text: string) => void, failfast: boolean);
    module_run(module: string, suite: unittest.TestSuite): boolean;
    // Writes the parent plan. Returns whether every module passed.
    run_end(): boolean;
  }

  // Marks every `not ok` line and its diagnostic lines, whole line, and
  // nothing else, for test.html.
  function report_html(text: string): string;
}
