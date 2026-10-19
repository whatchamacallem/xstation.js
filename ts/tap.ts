// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The TAP producer: runs unittest suites and writes TAP version 14 with the
// same text as the Python producer, one line at a time, one indented subtest
// block per module with its plan last, a parent line for each module, then
// the parent plan. With failfast the first failure ends the stream with a
// bail out line. Also marks the failed lines of a stream for the test page.

namespace tap {
  // The fixed text of the stream and of the marked report.
  const constants = Object.freeze({
    bail_line: "Bail out! failfast",
    diagnostic_prefix: "    # ",
    name_forbidden: "#\n\r",
    parent_failed: "not ok ",
    point_failed: "    not ok ",
    reason_forbidden: "\n\r",
    span_close: "</span>",
    span_open: '<span class="failed">',
    subtest_prefix: "    # Subtest: ",
    version_line: "TAP version 14",
  });

  // Throws when the text holds a character that would break its TAP line.
  function text_check(text: string, forbidden: string): void {
    for (const character of forbidden) {
      if (text.includes(character)) {
        const shown = JSON.stringify(character);
        throw new Error(`TAP text ${JSON.stringify(text)} holds ${shown}`);
      }
    }
  }

  // The text with the characters that mean something in HTML escaped.
  function html_escape(text: string): string {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  // Writes one test point per test as its outcome arrives, then any stack.
  class TapResult implements unittest.TestResult {
    // The counts of Python's `TestResult`, and its stop flag.
    testsRun = 0;
    failures = 0;
    errors = 0;
    skipped = 0;
    shouldStop = false;

    // Takes each line as it is produced.
    readonly #write: (text: string) => void;
    // Whether the first failure ends the stream.
    readonly #failfast: boolean;
    // The running test, until its outcome is written.
    #current: unittest.TestCase | null = null;

    // `write` takes each line, and `failfast` stops at the first failure.
    constructor(write: (text: string) => void, failfast: boolean) {
      this.#write = write;
      this.#failfast = failfast;
    }

    // Whether no test failed or raised.
    wasSuccessful(): boolean {
      return this.failures === 0 && this.errors === 0;
    }

    // Marks the test as the one whose outcome comes next.
    startTest(test: unittest.TestCase): void {
      this.testsRun += 1;
      this.#current = test;
    }

    // Writes `ok` for a test that passed.
    addSuccess(test: unittest.TestCase): void {
      this.#point_write(test, "ok", "");
    }

    // Writes `ok` with a `SKIP` directive and the reason, if any.
    addSkip(test: unittest.TestCase, reason: string): void {
      text_check(reason, constants.reason_forbidden);
      this.skipped += 1;
      const directive = reason === "" ? " # SKIP" : ` # SKIP ${reason}`;
      this.#point_write(test, "ok", directive);
    }

    // Writes `not ok` and the stack of a failed assertion.
    addFailure(test: unittest.TestCase, error: Error): void {
      this.failures += 1;
      this.#failure_write(test, error);
    }

    // Writes `not ok` and the stack of an error that is not an assertion's.
    addError(test: unittest.TestCase, error: Error): void {
      this.errors += 1;
      this.#failure_write(test, error);
    }

    // Writes the running test's point, throwing on a second outcome.
    #point_write(
      test: unittest.TestCase,
      word: string,
      directive: string,
    ): void {
      if (test !== this.#current) {
        throw new Error(`${test.id()} has no running test point`);
      }
      this.#current = null;
      this.#write(`    ${word} ${this.testsRun} - ${test.id()}${directive}`);
    }

    // Writes `not ok` and the stack, then ends a failfast stream.
    #failure_write(test: unittest.TestCase, error: Error): void {
      this.#point_write(test, "not ok", "");
      if (error.stack === undefined) {
        throw new Error(`${test.id()} threw an error with no stack`, {
          cause: error,
        });
      }
      for (const line of error.stack.split("\n")) {
        this.#write(constants.diagnostic_prefix + line);
      }
      if (this.#failfast) {
        this.shouldStop = true;
        this.#write(constants.bail_line);
      }
    }
  }

  // Writes TAP for a unittest run: one plan, one indented block per module.
  export class TapRunner {
    // Takes each line as it is produced.
    readonly #write: (text: string) => void;
    // Whether the first failure ends the stream.
    readonly #failfast: boolean;
    // The number of blocks written whole.
    #modules = 0;
    // Whether every module so far passed.
    #passed = true;
    // Whether a failfast bail out ended the stream.
    #bailed = false;
    // Whether `run_end` was called.
    #ended = false;

    // `write` gets each TAP line as it is produced, with no buffering.
    constructor(write: (text: string) => void, failfast: boolean) {
      this.#write = write;
      this.#failfast = failfast;
      write(constants.version_line);
    }

    // Runs one module's suite as a subtest block named `module`.
    module_run(module: string, suite: unittest.TestSuite): boolean {
      if (this.#bailed || this.#ended) {
        throw new Error(`the TAP stream ended before ${module}`);
      }
      text_check(module, constants.name_forbidden);
      this.#write(constants.subtest_prefix + module);
      const result = new TapResult(this.#write, this.#failfast);
      suite.run(result);
      if (result.shouldStop) {
        this.#bailed = true;
        this.#passed = false;
        return false;
      }
      this.#modules += 1;
      this.#write(`    1..${result.testsRun}`);
      const passed = result.wasSuccessful();
      const word = passed ? "ok" : "not ok";
      this.#write(`${word} ${this.#modules} - ${module}`);
      this.#passed = this.#passed && passed;
      return passed;
    }

    // Writes the parent plan. Returns whether every module passed.
    run_end(): boolean {
      if (this.#ended) {
        throw new Error("the TAP stream has ended already");
      }
      this.#ended = true;
      if (!this.#bailed) {
        this.#write(`1..${this.#modules}`);
      }
      return this.#passed;
    }
  }

  // Escapes the text and wraps each failed line and its stack in a span.
  export function report_html(text: string): string {
    let html = "";
    let open = false;
    for (const [index, line] of text.split("\n").entries()) {
      if (open && !line.startsWith(constants.diagnostic_prefix)) {
        html += constants.span_close;
        open = false;
      }
      if (index > 0) {
        html += "\n";
      }
      if (line.startsWith(constants.point_failed)) {
        html += constants.span_open + html_escape(line);
        open = true;
      } else if (line.startsWith(constants.parent_failed)) {
        html += constants.span_open + html_escape(line) + constants.span_close;
      } else {
        html += html_escape(line);
      }
    }
    if (open) {
      html += constants.span_close;
    }
    return html;
  }
}
Object.freeze(tap);
