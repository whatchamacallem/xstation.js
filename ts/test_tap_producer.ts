// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests the TAP producer: its tracker, its runner, the blocks written as their
// points arrive, every way a run of the TypeScript harness can fail, and the
// marked report. Each failure is an expected failure: the test states the
// stream the suite must write, its diagnostics by the lines they must hold,
// and passes only when the suite fails exactly that way. The fixtures are not
// exported, so that no loader collects them.

namespace test_tap_producer {
  // The lines and the names the expected streams are made of.
  const constants = Object.freeze({
    assertion_line: "    # AssertionError: 1 != 2",
    bail_line: "Bail out! failfast",
    block_name: "fixture",
    diagnostic_prefix: "    # ",
    error_line: "    # Error: fixture error",
    parent_failed: "not ok 1 - fixture",
    parent_passed: "ok 1 - fixture",
    parent_plan: "1..1",
    version_line: "TAP version 14",
  });

  // Passes.
  class PassingFixture extends unittest.TestCase {
    // Passes an assertion.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // Fails an assertion.
  class AssertionFixture extends unittest.TestCase {
    // Fails `1 != 2`.
    test_values_differ(): void {
      this.assertEqual(1, 2);
    }
  }

  // Throws an error in its test.
  class ErrorFixture extends unittest.TestCase {
    // Throws an error that is not an assertion's.
    test_error_thrown(): void {
      throw new Error("fixture error");
    }
  }

  // Throws in `setUp`.
  class SetupFixture extends unittest.TestCase {
    // Throws before the test.
    override setUp(): void {
      throw new Error("fixture error");
    }

    // Never runs.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // Throws in `tearDown` after a test that passed.
  class TeardownFixture extends unittest.TestCase {
    // Throws after the test.
    override tearDown(): void {
      throw new Error("fixture error");
    }

    // Passes an assertion.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }
  }

  // Fails its test, then throws in `tearDown`: two outcomes of one test.
  class DoubleFixture extends unittest.TestCase {
    // Throws after the test.
    override tearDown(): void {
      throw new Error("fixture error");
    }

    // Fails `1 != 2`.
    test_values_differ(): void {
      this.assertEqual(1, 2);
    }
  }

  // Expects its assertion to fail, and it does.
  class ExpectedFixture extends unittest.TestCase {
    // Fails `1 != 2` as expected.
    test_values_differ(): void {
      this.assertEqual(1, 2);
    }

    // Marks the test as expected to fail.
    static {
      unittest.expectedFailure(this.prototype.test_values_differ);
    }
  }

  // Expects its assertion to fail, and it passes.
  class SurpriseFixture extends unittest.TestCase {
    // Passes though it is expected to fail.
    test_values_equal(): void {
      this.assertEqual(1, 1);
    }

    // Marks the test as expected to fail.
    static {
      unittest.expectedFailure(this.prototype.test_values_equal);
    }
  }

  // Skips its test.
  class SkipFixture extends unittest.TestCase {
    // Skips itself with a reason.
    test_skip_self(): void {
      this.skipTest("fixture skip");
    }
  }

  // A pass, a failure, an error and a skip, in definition order.
  class MixedFixture extends unittest.TestCase {
    // Passes.
    test_alpha_passes(): void {
      this.assertEqual(1, 1);
    }

    // Fails `1 != 2`.
    test_bravo_fails(): void {
      this.assertEqual(1, 2);
    }

    // Throws an error that is not an assertion's.
    test_charlie_raises(): void {
      throw new Error("fixture error");
    }

    // Skips itself.
    test_delta_skips(): void {
      this.skipTest("fixture skip");
    }
  }

  // The load of a fixture class's tests, in definition order.
  function class_load(
    fixture: new (method_name: string) => unittest.TestCase,
  ): () => unittest.TestSuite {
    return () => new unittest.TestLoader().loadTestsFromModule({ fixture });
  }

  // A load that throws, as a module that does not load.
  function broken_load(): unittest.TestSuite {
    throw new Error("fixture error");
  }

  // The message of the error the function throws.
  function thrown_message(fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      if (!(error instanceof Error)) {
        throw new TypeError("the function threw a value that is no Error", {
          cause: error,
        });
      }
      return error.message;
    }
    throw new Error("the function threw nothing");
  }

  // The runs of consecutive diagnostic lines of a stream, in order.
  function runs_find(lines: readonly string[]): string[][] {
    const runs: string[][] = [];
    let inside = false;
    for (const line of lines) {
      const diagnostic = line.startsWith(constants.diagnostic_prefix);
      if (diagnostic && inside) {
        runs[runs.length - 1].push(line);
      } else if (diagnostic) {
        runs.push([line]);
      }
      inside = diagnostic;
    }
    return runs;
  }

  // The stream, each diagnostic run cut to the lines its expected run states.
  function stream_reduce(
    actual: readonly string[],
    expected: readonly string[],
  ): string[] {
    const stated = runs_find(expected);
    if (runs_find(actual).length !== stated.length) {
      return [...actual];
    }
    const reduced: string[] = [];
    let run = 0;
    let wanted: string[] = [];
    let inside = false;
    for (const line of actual) {
      const diagnostic = line.startsWith(constants.diagnostic_prefix);
      if (diagnostic && !inside) {
        wanted = stated[run];
        run += 1;
      }
      if (!diagnostic) {
        reduced.push(line);
      } else if (wanted.length > 0 && wanted[0] === line) {
        reduced.push(line);
        wanted.shift();
      }
      inside = diagnostic;
    }
    return reduced;
  }

  // Runs the load as block `fixture`, failing the test unless it writes these.
  function stream_expect(
    test: unittest.TestCase,
    load: () => unittest.TestSuite,
    failfast: boolean,
    expected: readonly string[],
  ): void {
    const lines: string[] = [];
    const runner = new tap_producer.TAPTestRunner(failfast);
    runner.set_stream((text) => lines.push(text));
    const passed = runner.module_run(constants.block_name, load);
    const ended = runner.run_end();
    test.assertEqual(stream_reduce(lines, expected), expected);
    const graded = expected.includes(constants.parent_passed);
    test.assertEqual([passed, ended], [graded, graded]);
  }

  // Tests the tracker: numbered points, directives, diagnostics and plans.
  export class TestTracker extends unittest.TestCase {
    // Points are numbered in order and the plan that comes last counts them.
    test_points_numbered(): void {
      const lines: string[] = [];
      const tracker = new tap_producer.Tracker((text) => lines.push(text));
      tracker.add_ok("Case", "test_one");
      tracker.add_not_ok("Case", "test_two", "", "first\nsecond\n");
      tracker.add_skip("Case", "test_three", "why");
      tracker.add_skip("Case", "test_four", "");
      tracker.add_not_ok("Case", "test_five", "TODO later");
      tracker.generate_tap_reports();
      this.assertEqual(lines, [
        "ok 1 - test_one",
        "not ok 2 - test_two",
        "# first",
        "# second",
        "ok 3 - test_three # SKIP why",
        "ok 4 - test_four # SKIP",
        "not ok 5 - test_five # TODO later",
        "1..5",
      ]);
    }

    // A plan set first is written at once, before the points.
    test_plan_first(): void {
      const lines: string[] = [];
      const tracker = new tap_producer.Tracker((text) => lines.push(text));
      tracker.set_plan(2);
      tracker.add_ok("Case", "test_one", "", "note");
      tracker.add_ok("Case", "test_two");
      this.assertEqual(lines, [
        "1..2",
        "ok 1 - test_one",
        "# note",
        "ok 2 - test_two",
      ]);
    }

    // A blank line of diagnostic text is still a diagnostic line.
    test_diagnostics_blank(): void {
      const lines: string[] = [];
      const tracker = new tap_producer.Tracker((text) => lines.push(text));
      tracker.add_not_ok("Case", "test_one", "", "a\n\nb");
      this.assertEqual(lines, ["not ok 1 - test_one", "# a", "# ", "# b"]);
    }

    // Text that would break its line is refused with its diagnostics.
    test_line_refused(): void {
      const lines: string[] = [];
      const tracker = new tap_producer.Tracker((text) => lines.push(text));
      const refused: [string, string, string | undefined][] = [
        ["a # b", "", "trace"],
        ["a\nb", "", undefined],
        ["test_one", "SKIP a\rb", undefined],
      ];
      for (const [description, directive, diagnostics] of refused) {
        const message = thrown_message(() =>
          tracker.add_ok("Case", description, directive, diagnostics),
        );
        this.assertEqual(
          message,
          `the TAP point ${JSON.stringify(description)} # ` +
            `${JSON.stringify(directive)} does not fit on one line, its ` +
            `diagnostics: ${JSON.stringify(diagnostics)}`,
        );
      }
      this.assertEqual(lines, []);
    }
  }

  // Tests the runner: the stream of modules that pass and fail, and its ends.
  export class TestRunner extends unittest.TestCase {
    // Blocks plan first, parents follow, and the parent plan comes last.
    test_modules_pass(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const load = class_load(PassingFixture);
      this.assertTrue(runner.module_run("first", load));
      this.assertTrue(
        runner.module_run("second", () => new unittest.TestSuite()),
      );
      this.assertTrue(runner.run_end());
      this.assertEqual(lines, [
        constants.version_line,
        "    1..1",
        "    ok 1 - test_values_equal",
        "ok 1 - first",
        "    1..0",
        "ok 2 - second",
        "1..2",
      ]);
    }

    // Without failfast a failed module is graded and the stream goes on.
    test_module_fails(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const load = class_load(AssertionFixture);
      this.assertFalse(runner.module_run("first", load));
      this.assertTrue(
        runner.module_run("second", () => new unittest.TestSuite()),
      );
      this.assertFalse(runner.run_end());
      const expected = [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_differ",
        constants.assertion_line,
        "not ok 1 - first",
        "    1..0",
        "ok 2 - second",
        "1..2",
      ];
      this.assertEqual(stream_reduce(lines, expected), expected);
    }

    // A stream that bailed out takes no other module and writes no plan.
    test_bail_ends(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(true);
      runner.set_stream((text) => lines.push(text));
      const load = class_load(AssertionFixture);
      this.assertFalse(runner.module_run("first", load));
      const message = thrown_message(() =>
        runner.module_run("second", () => new unittest.TestSuite()),
      );
      this.assertEqual(message, 'the TAP stream ended before "second"');
      this.assertFalse(runner.run_end());
      this.assertEqual(lines.at(-1), constants.bail_line);
    }

    // The stream ends once, and takes no module after its end.
    test_end_twice(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      this.assertTrue(runner.run_end());
      const twice = thrown_message(() => runner.run_end());
      this.assertEqual(twice, "the TAP stream has ended already");
      const late = thrown_message(() =>
        runner.module_run("late", () => new unittest.TestSuite()),
      );
      this.assertEqual(late, 'the TAP stream ended before "late"');
      this.assertEqual(lines, [constants.version_line, "1..0"]);
    }

    // The stream is set once, and a block before it is refused.
    test_stream_once(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      const early = thrown_message(() =>
        runner.module_run("early", () => new unittest.TestSuite()),
      );
      this.assertEqual(early, 'set_stream was not called before "    1..0"');
      runner.set_stream((text) => lines.push(text));
      const twice = thrown_message(() =>
        runner.set_stream((text) => lines.push(text)),
      );
      this.assertEqual(twice, "the TAP stream is set already");
      this.assertEqual(lines, [constants.version_line]);
    }

    // A module name that would break its lines is refused before any block.
    test_name_refused(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const message = thrown_message(() =>
        runner.module_run("a # b", () => new unittest.TestSuite()),
      );
      this.assertEqual(
        message,
        'the TAP point "a # b" # "" does not fit on one line, its ' +
          "diagnostics: undefined",
      );
      this.assertEqual(lines, [constants.version_line]);
    }
  }

  // Tests the blocks whose points are added after `block_start` returns.
  export class TestBlocks extends unittest.TestCase {
    // The plan comes at the start, points stream as added, then the parent.
    test_block_passes(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const tracker = runner.block_start("first", 3);
      this.assertEqual(lines.at(-1), "    1..3");
      tracker.add_ok("Case", "case_one");
      this.assertEqual(lines.at(-1), "    ok 1 - case_one");
      tracker.add_not_ok("Case", "case_two", "TODO later", "note");
      tracker.add_skip("Case", "case_three", "why");
      this.assertTrue(runner.block_end("first"));
      this.assertTrue(runner.module_run("second", class_load(PassingFixture)));
      this.assertTrue(runner.run_end());
      this.assertEqual(lines, [
        constants.version_line,
        "    1..3",
        "    ok 1 - case_one",
        "    not ok 2 - case_two # TODO later",
        "    # note",
        "    ok 3 - case_three # SKIP why",
        "ok 1 - first",
        "    1..1",
        "    ok 1 - test_values_equal",
        "ok 2 - second",
        "1..2",
      ]);
    }

    // Without failfast a failed point fails the block and the stream goes on.
    test_block_fails(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const tracker = runner.block_start("first", 2);
      tracker.add_not_ok("Case", "case_one", "", "why");
      tracker.add_ok("Case", "case_two");
      this.assertFalse(runner.block_end("first"));
      runner.block_start("second", 0);
      this.assertTrue(runner.block_end("second"));
      this.assertFalse(runner.run_end());
      this.assertEqual(lines, [
        constants.version_line,
        "    1..2",
        "    not ok 1 - case_one",
        "    # why",
        "    ok 2 - case_two",
        "not ok 1 - first",
        "    1..0",
        "ok 2 - second",
        "1..2",
      ]);
    }

    // With failfast a failed point ends the stream before its planned points.
    test_block_failfast(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(true);
      runner.set_stream((text) => lines.push(text));
      this.assertTrue(runner.failfast);
      const tracker = runner.block_start("first", 3);
      tracker.add_ok("Case", "case_one");
      tracker.add_not_ok("Case", "case_two");
      this.assertFalse(runner.block_end("first"));
      const late = thrown_message(() => runner.block_start("second", 0));
      this.assertEqual(late, 'the TAP stream ended before "second"');
      this.assertFalse(runner.run_end());
      this.assertEqual(lines, [
        constants.version_line,
        "    1..3",
        "    ok 1 - case_one",
        "    not ok 2 - case_two",
        constants.bail_line,
      ]);
    }

    // An open block takes no other block or module, and must end by its name.
    test_block_open(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const unopened = thrown_message(() => runner.block_end("first"));
      this.assertEqual(unopened, 'no TAP block is open to end as "first"');
      runner.block_start("first", 0);
      const texts = [
        thrown_message(() => runner.block_start("second", 0)),
        thrown_message(() =>
          runner.module_run("second", () => new unittest.TestSuite()),
        ),
        thrown_message(() => runner.block_end("second")),
        thrown_message(() => runner.run_end()),
      ];
      this.assertEqual(texts, [
        'the TAP block "first" is open before "second"',
        'the TAP block "first" is open before "second"',
        'the TAP block "first" is open, not "second"',
        'the TAP block "first" is open at the end',
      ]);
      this.assertTrue(runner.block_end("first"));
      this.assertTrue(runner.run_end());
      this.assertEqual(lines, [
        constants.version_line,
        "    1..0",
        "ok 1 - first",
        "1..1",
      ]);
    }

    // A block name that would break its lines is refused, and no block opens.
    test_block_refused(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      const message = thrown_message(() => runner.block_start("a # b", 0));
      this.assertEqual(
        message,
        'the TAP point "a # b" # "" does not fit on one line, its ' +
          "diagnostics: undefined",
      );
      this.assertTrue(runner.run_end());
      this.assertEqual(lines, [constants.version_line, "1..0"]);
    }
  }

  // Tests each way a run can fail, each stated as the stream it must write.
  export class TestFailures extends unittest.TestCase {
    // A failed assertion is a failing point with the assertion's text.
    test_assertion_fails(): void {
      stream_expect(this, class_load(AssertionFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_differ",
        constants.assertion_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // An error thrown in a test is a failing point with the error's text.
    test_error_thrown(): void {
      stream_expect(this, class_load(ErrorFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_error_thrown",
        constants.error_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // An error in `setUp` fails the test's point.
    test_setup_throws(): void {
      stream_expect(this, class_load(SetupFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_equal",
        constants.error_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // An error in `tearDown` fails the point of a test that passed.
    test_teardown_throws(): void {
      stream_expect(this, class_load(TeardownFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_equal",
        constants.error_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // A second outcome of one test adds its diagnostics to the same point.
    test_outcomes_two(): void {
      stream_expect(this, class_load(DoubleFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_differ",
        constants.assertion_line,
        constants.error_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // An expected failure is a `TODO` point that does not fail the block.
    test_failure_expected(): void {
      stream_expect(this, class_load(ExpectedFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_differ # TODO expected failure",
        constants.assertion_line,
        constants.parent_passed,
        constants.parent_plan,
      ]);
    }

    // An unexpected success fails its point and says so.
    test_success_unexpected(): void {
      stream_expect(this, class_load(SurpriseFixture), false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_values_equal",
        "    # unexpected success",
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // A skip is a passing point with its reason.
    test_skip_reason(): void {
      stream_expect(this, class_load(SkipFixture), false, [
        constants.version_line,
        "    1..1",
        "    ok 1 - test_skip_self # SKIP fixture skip",
        constants.parent_passed,
        constants.parent_plan,
      ]);
    }

    // Without failfast every test runs and the failures fail the block.
    test_mixed_outcomes(): void {
      stream_expect(this, class_load(MixedFixture), false, [
        constants.version_line,
        "    1..4",
        "    ok 1 - test_alpha_passes",
        "    not ok 2 - test_bravo_fails",
        constants.assertion_line,
        "    not ok 3 - test_charlie_raises",
        constants.error_line,
        "    ok 4 - test_delta_skips # SKIP fixture skip",
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // With failfast the first failure ends the stream with a bail out line.
    test_failfast_bails(): void {
      stream_expect(this, class_load(MixedFixture), true, [
        constants.version_line,
        "    1..4",
        "    ok 1 - test_alpha_passes",
        "    not ok 2 - test_bravo_fails",
        constants.assertion_line,
        constants.bail_line,
      ]);
    }

    // A module that does not load is one failing point with its stack.
    test_load_fails(): void {
      stream_expect(this, broken_load, false, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - fixture",
        constants.error_line,
        constants.parent_failed,
        constants.parent_plan,
      ]);
    }

    // With failfast a module that does not load ends the stream.
    test_load_failfast(): void {
      stream_expect(this, broken_load, true, [
        constants.version_line,
        "    1..1",
        "    not ok 1 - fixture",
        constants.error_line,
        constants.bail_line,
      ]);
    }
  }

  // Tests the expected failure check: stated lines match, others do not.
  export class TestExpectation extends unittest.TestCase {
    // Diagnostic lines not stated are dropped, stated ones kept in order.
    test_stated_lines(): void {
      const actual = ["    not ok 1 - a", "    # x", "    # y", "    # z"];
      const expected = ["    not ok 1 - a", "    # x", "    # z"];
      this.assertEqual(stream_reduce(actual, expected), expected);
    }

    // A stated line the run lacks leaves the streams different.
    test_line_missing(): void {
      const actual = ["    not ok 1 - a", "    # x", "1..1"];
      const expected = ["    not ok 1 - a", "    # y", "1..1"];
      const reduced = stream_reduce(actual, expected);
      this.assertEqual(reduced, ["    not ok 1 - a", "1..1"]);
    }

    // A run of diagnostics the expectation does not state is kept whole.
    test_run_unstated(): void {
      const actual = [
        "    not ok 1 - a",
        "    # x",
        "    ok 2 - b",
        "    # y",
      ];
      const expected = ["    not ok 1 - a", "    # x", "    ok 2 - b"];
      this.assertEqual(stream_reduce(actual, expected), actual);
    }

    // A suite that fails another way does not match the stated failure.
    test_failure_other(): void {
      const lines: string[] = [];
      const runner = new tap_producer.TAPTestRunner(false);
      runner.set_stream((text) => lines.push(text));
      runner.module_run(constants.block_name, class_load(ErrorFixture));
      runner.run_end();
      const expected = [
        constants.version_line,
        "    1..1",
        "    not ok 1 - test_error_thrown",
        constants.assertion_line,
        constants.parent_failed,
        constants.parent_plan,
      ];
      const reduced = stream_reduce(lines, expected);
      this.assertFalse(
        reduced.length === expected.length &&
          reduced.every((line, index) => line === expected[index]),
      );
    }
  }

  // Tests the marked report of a stream for the test page.
  export class TestReport extends unittest.TestCase {
    // Failing points with their diagnostics, and failed parents, are wrapped.
    test_report_spans(): void {
      const text = [
        "TAP version 14",
        "    1..3",
        "    ok 1 - test_one",
        "    not ok 2 - test_two",
        "    # trace one",
        "    # trace two",
        "    not ok 3 - test_three # TODO expected failure",
        "    # trace three",
        "not ok 1 - first",
        "    1..1",
        "    not ok 1 - test_four",
        "    # trace four",
        "Bail out! failfast",
        "",
      ];
      const html = [
        "TAP version 14",
        "    1..3",
        "    ok 1 - test_one",
        '<span class="failed">    not ok 2 - test_two',
        "    # trace one",
        "    # trace two</span>",
        "    not ok 3 - test_three # TODO expected failure",
        "    # trace three",
        '<span class="failed">not ok 1 - first</span>',
        "    1..1",
        '<span class="failed">    not ok 1 - test_four',
        "    # trace four</span>",
        "Bail out! failfast",
        "",
      ];
      const report = tap_producer.report_html(text.join("\n"));
      this.assertEqual(report, html.join("\n"));
    }

    // The text is escaped as HTML, inside a span and out of it.
    test_report_escape(): void {
      const text = [
        "ok 1 - a<b>&c",
        "    not ok 2 - test_two",
        "    # x < y & z",
      ];
      const html = [
        "ok 1 - a&lt;b&gt;&amp;c",
        '<span class="failed">    not ok 2 - test_two',
        "    # x &lt; y &amp; z</span>",
      ];
      const report = tap_producer.report_html(text.join("\n"));
      this.assertEqual(report, html.join("\n"));
    }
  }
}
Object.freeze(test_tap_producer);
