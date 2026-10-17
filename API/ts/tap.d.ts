declare namespace tap {
  // A clone of tappy's producers writing the same text as the Python
  // original, into a stream the page keeps and sends as `tap.report`.
  class Tracker {
    constructor(stream: (text: string) => void, streaming: boolean, header: boolean);
    add_ok(class_name: string, description: string): void;
    add_not_ok(class_name: string, description: string, diagnostics: string): void;
    add_skip(class_name: string, description: string, reason: string): void;
    set_plan(total: number): void;
    generate_tap_reports(): void;
  }

  class TAPTestRunner {
    constructor(stream: (text: string) => void);
    set_stream(streaming: boolean): void;
    set_header(header: boolean): void;
    set_format(format: string): void;
    // Runs the suite, one subtest block per module, and the parent plan.
    run(suite: unittest.TestSuite, failfast: boolean): Promise<unittest.TestResult>;
  }

  // Colours every `not ok` line and its diagnostic lines red, whole
  // line, and nothing else.
  function report_html(text: string): string;
}
