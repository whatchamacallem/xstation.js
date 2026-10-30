// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The TypeScript TAP producer, with the names and the text of the Python one:
// a `Tracker` writes the lines of one level of a TAP version 14 stream the
// moment each is added, `TAPTestResult` turns the outcomes of the unittest
// harness into one point per test, and `TAPTestRunner` writes one stream: the
// version line, then per module a block indented four spaces with its plan
// first, its points and their diagnostics, then a parent line, and the parent
// plan last. With failfast the first failure ends the stream with a bail out
// line in place of the parent line and the parent plan. A block whose points
// arrive after the call that starts it opens with `block_start`, which writes
// its plan of the count given and hands out its tracker, and closes with
// `block_end`, which writes its parent line. Also marks the failed lines of a
// stream for the test page.

namespace tap_producer {
  // The fixed text of the stream and of the marked report.
  const constants = Object.freeze({
    bail_line: "Bail out! failfast",
    block_indent: "    ",
    diagnostic_prefix: "    # ",
    expected_directive: "TODO expected failure",
    line_break: /[\r\n]/,
    parent_failed: "not ok ",
    point_failed: "    not ok ",
    point_todo: " # TODO",
    todo_word: "TODO",
    span_close: "</span>",
    span_open: '<span class="failed">',
    surprise_text: "unexpected success",
    version_line: "TAP version 14",
  });

  // One outcome of a test: its word, its directive and its diagnostic text.
  interface PointPart {
    readonly word: string;
    readonly directive: string;
    readonly diagnostics: string;
  }

  // Throws unless the description and the directive each fit on one TAP line.
  function line_check(
    description: string,
    directive: string,
    diagnostics: string | undefined,
  ): void {
    if (
      description.includes("#") ||
      constants.line_break.test(description + directive)
    ) {
      throw new Error(
        `the TAP point ${JSON.stringify(description)} # ` +
          `${JSON.stringify(directive)} does not fit on one line, its ` +
          `diagnostics: ${JSON.stringify(diagnostics)}`,
      );
    }
  }

  // The directive of a skipped test, with its reason when it has one.
  function skip_directive(reason: string): string {
    return reason === "" ? "SKIP" : `SKIP ${reason}`;
  }

  // The stack of an error, the diagnostic text of every throw.
  function stack_text(name: string, error: Error): string {
    if (error.stack === undefined) {
      throw new Error(`${name} threw an error with no stack: ${error}`, {
        cause: error,
      });
    }
    return error.stack;
  }

  // The text with the characters that mean something in HTML escaped.
  function html_escape(text: string): string {
    return text
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  // Writes the lines of one level of a stream the moment each is added.
  export class Tracker {
    // Takes each line, without its newline.
    readonly #write: (text: string) => void;
    // The number of points written.
    #count = 0;

    // `write` takes each line, without its newline.
    constructor(write: (text: string) => void) {
      this.#write = write;
    }

    // Writes the plan at once, before the points, as tappy does if streaming.
    set_plan(total: number): void {
      this.#write(`1..${total}`);
    }

    // Writes a passing point. `class_name` is tappy's and is not written.
    add_ok(
      class_name: string,
      description: string,
      directive = "",
      diagnostics?: string,
    ): void {
      this.#point_add("ok", description, directive, diagnostics);
    }

    // Writes a failing point. `class_name` is tappy's and is not written.
    add_not_ok(
      class_name: string,
      description: string,
      directive = "",
      diagnostics?: string,
    ): void {
      this.#point_add("not ok", description, directive, diagnostics);
    }

    // Writes a passing point with a `SKIP` directive and the reason.
    add_skip(class_name: string, description: string, reason: string): void {
      this.#point_add("ok", description, skip_directive(reason), undefined);
    }

    // Writes the plan of the points added, for a level whose plan comes last.
    generate_tap_reports(): void {
      this.#write(`1..${this.#count}`);
    }

    // Writes the next numbered point, then a diagnostic line per text line.
    #point_add(
      word: string,
      description: string,
      directive: string,
      diagnostics: string | undefined,
    ): void {
      line_check(description, directive, diagnostics);
      this.#count += 1;
      const suffix = directive === "" ? "" : ` # ${directive}`;
      this.#write(`${word} ${this.#count} - ${description}${suffix}`);
      if (diagnostics !== undefined) {
        for (const line of diagnostics.replace(/\n$/, "").split("\n")) {
          this.#write(`# ${line}`);
        }
      }
    }
  }

  // Turns the harness's outcomes into one point per test, once all are in.
  export class TAPTestResult extends unittest.TestResult {
    // Writes the points of the block this result runs.
    readonly #tracker: Tracker;
    // The running test, until its point is written.
    #current: unittest.TestCase | null = null;
    // The outcomes of the running test so far.
    #parts: PointPart[] = [];

    // `tracker` writes the points, and `failfast` stops at the first failure.
    constructor(tracker: Tracker, failfast: boolean) {
      super(failfast);
      this.#tracker = tracker;
    }

    // Writes the point of the test before, then marks this one as running.
    override startTest(test: unittest.TestCase): void {
      this.point_flush();
      super.startTest(test);
      this.#current = test;
    }

    // Keeps a pass.
    override addSuccess(test: unittest.TestCase): void {
      super.addSuccess(test);
      this.#part_add(test, { word: "ok", directive: "", diagnostics: "" });
    }

    // Keeps a skip and its reason.
    override addSkip(test: unittest.TestCase, reason: string): void {
      super.addSkip(test, reason);
      const directive = skip_directive(reason);
      this.#part_add(test, { word: "ok", directive, diagnostics: "" });
    }

    // Keeps a failed assertion and the stack the result kept of it.
    override addFailure(test: unittest.TestCase, error: Error): void {
      super.addFailure(test, error);
      this.#failing_add(test, this.failures[this.failures.length - 1][1]);
    }

    // Keeps an error that is not an assertion's, and its stack.
    override addError(test: unittest.TestCase, error: Error): void {
      super.addError(test, error);
      this.#failing_add(test, this.errors[this.errors.length - 1][1]);
    }

    // Keeps a failure the test was expected to have, with its stack.
    override addExpectedFailure(test: unittest.TestCase, error: Error): void {
      super.addExpectedFailure(test, error);
      const kept = this.expectedFailures;
      this.#part_add(test, {
        word: "not ok",
        directive: constants.expected_directive,
        diagnostics: kept[kept.length - 1][1],
      });
    }

    // Keeps the pass of a test that was expected to fail, which fails it.
    override addUnexpectedSuccess(test: unittest.TestCase): void {
      super.addUnexpectedSuccess(test);
      this.#failing_add(test, constants.surprise_text);
    }

    // Writes the point of the last test, throwing when it had no outcome.
    point_flush(): void {
      const test = this.#current;
      if (test === null) {
        return;
      }
      const parts = this.#parts;
      this.#current = null;
      this.#parts = [];
      if (parts.length === 0) {
        throw new Error(`${test.id()} ended with no TAP outcome`);
      }
      const failing = parts.filter((part) => part.word === "not ok");
      const lead = failing.find((part) => part.directive === "") ?? parts[0];
      const lines: string[] = [];
      for (const part of parts) {
        if (part !== lead && part.directive !== "") {
          lines.push(part.directive);
        }
        if (part.diagnostics !== "") {
          lines.push(part.diagnostics);
        }
      }
      const id = test.id();
      const name = id.slice(id.lastIndexOf(".") + 1);
      const diagnostics = lines.length === 0 ? undefined : lines.join("\n");
      const owner = test.constructor.name;
      if (lead.word === "ok") {
        this.#tracker.add_ok(owner, name, lead.directive, diagnostics);
      } else {
        this.#tracker.add_not_ok(owner, name, lead.directive, diagnostics);
      }
    }

    // Keeps a failing part, the result having stopped the run if failfast.
    #failing_add(test: unittest.TestCase, diagnostics: string): void {
      this.#part_add(test, { word: "not ok", directive: "", diagnostics });
    }

    // Keeps a part of the running test, throwing for an outcome of any other.
    #part_add(test: unittest.TestCase, part: PointPart): void {
      if (test !== this.#current) {
        throw new Error(
          `${test.id()} has an outcome outside a running test: ` +
            JSON.stringify(part),
        );
      }
      this.#parts.push(part);
    }
  }

  // A block's tracker, which keeps whether a point failed.
  class BlockTracker extends Tracker {
    // Whether a point was `not ok` without a `TODO` directive.
    failed = false;

    // Writes a failing point and keeps that it failed unless it is a `TODO`.
    override add_not_ok(
      class_name: string,
      description: string,
      directive = "",
      diagnostics?: string,
    ): void {
      super.add_not_ok(class_name, description, directive, diagnostics);
      if (!directive.startsWith(constants.todo_word)) {
        this.failed = true;
      }
    }
  }

  // The block written as its points arrive, until `block_end` closes it.
  interface OpenBlock {
    readonly name: string;
    readonly tracker: BlockTracker;
  }

  // Writes TAP for a unittest run: one plan, one indented block per module.
  export class TAPTestRunner {
    // Whether the first failure ends the stream, as Python's runner keeps it.
    readonly failfast: boolean;
    // Where the lines go, once `set_stream` has set it.
    #write: ((text: string) => void) | null = null;
    // Writes the parent lines and the parent plan.
    readonly #parent: Tracker;
    // Whether every module so far passed.
    #passed = true;
    // Whether a bail out line ended the stream.
    #bailed = false;
    // Whether `run_end` was called.
    #ended = false;
    // The block `block_start` opened, until `block_end` closes it.
    #open: OpenBlock | null = null;

    // `failfast` ends the stream at the first failure, as unittest's does.
    constructor(failfast: boolean) {
      this.failfast = failfast;
      this.#parent = new Tracker((text) => this.#line_write(text));
    }

    // Sends each line to `write` as it is made, the version line first.
    set_stream(write: (text: string) => void): void {
      if (this.#write !== null) {
        throw new Error("the TAP stream is set already");
      }
      this.#write = write;
      write(constants.version_line);
    }

    // Runs the suite as one block, its plan first, and returns its result.
    run(test: unittest.TestSuite): TAPTestResult {
      const block = new Tracker((text) => this.#block_write(text));
      block.set_plan(test.countTestCases());
      const result = new TAPTestResult(block, this.failfast);
      test.run(result);
      result.point_flush();
      return result;
    }

    // Loads and runs one module as a block, then closes the block.
    module_run(module: string, load: () => unittest.TestSuite): boolean {
      this.#block_check(module);
      line_check(module, "", undefined);
      let suite: unittest.TestSuite;
      try {
        suite = load();
      } catch (error) {
        if (!(error instanceof Error)) {
          throw new TypeError(`${module} threw a value that is no Error`, {
            cause: error,
          });
        }
        const block = new Tracker((text) => this.#block_write(text));
        block.set_plan(1);
        block.add_not_ok(module, module, "", stack_text(module, error));
        return this.#block_end(module, false, this.failfast);
      }
      const result = this.run(suite);
      return this.#block_end(
        module,
        result.wasSuccessful(),
        result.shouldStop,
      );
    }

    // Opens a block, writes its plan of `count` points, returns its tracker.
    block_start(name: string, count: number): Tracker {
      this.#block_check(name);
      line_check(name, "", undefined);
      const tracker = new BlockTracker((text) => this.#block_write(text));
      tracker.set_plan(count);
      this.#open = { name, tracker };
      return tracker;
    }

    // Writes the block's parent line, or failfast's bail out.
    block_end(name: string): boolean {
      const open = this.#open;
      if (open === null) {
        throw new Error(
          `no TAP block is open to end as ${JSON.stringify(name)}`,
        );
      }
      if (open.name !== name) {
        throw new Error(
          `the TAP block ${JSON.stringify(open.name)} is open, not ` +
            JSON.stringify(name),
        );
      }
      this.#open = null;
      const failed = open.tracker.failed;
      return this.#block_end(name, !failed, failed && this.failfast);
    }

    // Writes the parent plan unless the stream bailed out. True if all passed.
    run_end(): boolean {
      if (this.#ended) {
        throw new Error("the TAP stream has ended already");
      }
      const open = this.#open;
      if (open !== null) {
        throw new Error(
          `the TAP block ${JSON.stringify(open.name)} is open at the end`,
        );
      }
      this.#ended = true;
      if (!this.#bailed) {
        this.#parent.generate_tap_reports();
      }
      return this.#passed;
    }

    // Throws once the stream ended, or while a block is open, before `name`.
    #block_check(name: string): void {
      if (this.#bailed || this.#ended) {
        throw new Error(`the TAP stream ended before ${JSON.stringify(name)}`);
      }
      const open = this.#open;
      if (open !== null) {
        throw new Error(
          `the TAP block ${JSON.stringify(open.name)} is open before ` +
            JSON.stringify(name),
        );
      }
    }

    // Bails out when the block stopped the run, else writes its parent line.
    #block_end(module: string, passed: boolean, stopped: boolean): boolean {
      if (stopped) {
        this.#line_write(constants.bail_line);
        this.#bailed = true;
        this.#passed = false;
        return false;
      }
      if (passed) {
        this.#parent.add_ok(module, module);
      } else {
        this.#parent.add_not_ok(module, module);
      }
      this.#passed = this.#passed && passed;
      return passed;
    }

    // Writes a line of a block, indented one level.
    #block_write(text: string): void {
      this.#line_write(constants.block_indent + text);
    }

    // Writes a line of the stream, which `set_stream` must have set.
    #line_write(text: string): void {
      const write = this.#write;
      if (write === null) {
        throw new Error(
          `set_stream was not called before ${JSON.stringify(text)}`,
        );
      }
      write(text);
    }
  }

  // Escapes the text and puts each failing line and its diagnostics in a span.
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
      const todo = line.includes(constants.point_todo);
      if (line.startsWith(constants.point_failed) && !todo) {
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
Object.freeze(tap_producer);
