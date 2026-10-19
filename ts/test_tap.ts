// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests the TAP producer on a fixture of one passing, one failing, one
// raising and one skipped test, nested in the test class so that no loader
// collects it, and the marked report. The Python producer test expects the
// same text.

namespace test_tap {
  // The streams the tests expect, without traceback lines, and their prefixes.
  const constants = Object.freeze({
    diagnostic_prefix: "    # ",
    empty_lines: [
      "TAP version 14",
      "    # Subtest: empty",
      "    1..0",
      "ok 1 - empty",
      "1..1",
    ],
    failfast_lines: [
      "TAP version 14",
      "    # Subtest: fixture",
      "    ok 1 - NestedFixture.test_alpha_passes",
      "    not ok 2 - NestedFixture.test_bravo_fails",
      "Bail out! failfast",
    ],
    fixture_lines: [
      "TAP version 14",
      "    # Subtest: fixture",
      "    ok 1 - NestedFixture.test_alpha_passes",
      "    not ok 2 - NestedFixture.test_bravo_fails",
      "    not ok 3 - NestedFixture.test_charlie_raises",
      "    ok 4 - NestedFixture.test_delta_skips # SKIP fixture skip",
      "    1..4",
      "not ok 1 - fixture",
      "1..1",
    ],
    subtest_prefix: "    # Subtest: ",
  });

  // The lines without the traceback lines under each failed test point.
  function tracebacks_drop(lines: readonly string[]): string[] {
    return lines.filter(
      (line) =>
        !line.startsWith(constants.diagnostic_prefix) ||
        line.startsWith(constants.subtest_prefix),
    );
  }

  // Whether a traceback line follows every failed test point.
  function tracebacks_follow(lines: readonly string[]): boolean {
    return lines.every(
      (line, index) =>
        !line.startsWith("    not ok ") ||
        lines.at(index + 1)?.startsWith(constants.diagnostic_prefix) === true,
    );
  }

  // The nested fixture's tests, loaded from a module object that holds it.
  function fixture_suite(): unittest.TestSuite {
    return new unittest.TestLoader().loadTestsFromModule({
      NestedFixture: TestTap.NestedFixture,
    });
  }

  // Tests `TapRunner` and `report_html`.
  export class TestTap extends unittest.TestCase {
    // A pass, a failure, an error and a skip, in name order.
    static readonly NestedFixture =
      class NestedFixture extends unittest.TestCase {
        // Passes.
        test_alpha_passes(): void {
          this.assertTrue(true);
        }

        // Fails an assertion.
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
      };

    // The fixture's stream is the expected text, traceback lines aside.
    test_fixture_stream(): void {
      const lines: string[] = [];
      const runner = new tap.TapRunner((text) => lines.push(text), false);
      this.assertFalse(runner.module_run("fixture", fixture_suite()));
      this.assertFalse(runner.run_end());
      this.assertEqual(tracebacks_drop(lines), constants.fixture_lines);
      this.assertTrue(tracebacks_follow(lines));
    }

    // With failfast the stream ends at the first failure, and says so.
    test_failfast_stream(): void {
      const lines: string[] = [];
      const runner = new tap.TapRunner((text) => lines.push(text), true);
      this.assertFalse(runner.module_run("fixture", fixture_suite()));
      this.assertFalse(runner.run_end());
      this.assertEqual(tracebacks_drop(lines), constants.failfast_lines);
      this.assertTrue(tracebacks_follow(lines));
      this.assertRaises(Error, () =>
        runner.module_run("fixture", new unittest.TestSuite()),
      );
    }

    // An empty suite passes, and the stream ends once.
    test_empty_suite(): void {
      const lines: string[] = [];
      const runner = new tap.TapRunner((text) => lines.push(text), false);
      this.assertTrue(runner.module_run("empty", new unittest.TestSuite()));
      this.assertTrue(runner.run_end());
      this.assertEqual(lines, constants.empty_lines);
      this.assertRaises(Error, () => runner.run_end());
    }

    // A module name that would break its line is refused before any write.
    test_name_check(): void {
      const lines: string[] = [];
      const runner = new tap.TapRunner((text) => lines.push(text), false);
      this.assertRaises(Error, () =>
        runner.module_run("a # b", new unittest.TestSuite()),
      );
      this.assertRaises(Error, () =>
        runner.module_run("a\nb", new unittest.TestSuite()),
      );
      this.assertEqual(lines, ["TAP version 14"]);
    }

    // A failed point with its traceback, and a failed parent, are wrapped.
    test_report_spans(): void {
      const text = [
        "TAP version 14",
        "    # Subtest: first",
        "    ok 1 - Case.test_one",
        "    not ok 2 - Case.test_two",
        "    # trace one",
        "    # trace two",
        "    1..2",
        "not ok 1 - first",
        "    # Subtest: second",
        "    not ok 1 - Case.test_three",
        "    # trace three",
        "Bail out! failfast",
        "",
      ];
      const html = [
        "TAP version 14",
        "    # Subtest: first",
        "    ok 1 - Case.test_one",
        '<span class="failed">    not ok 2 - Case.test_two',
        "    # trace one",
        "    # trace two</span>",
        "    1..2",
        '<span class="failed">not ok 1 - first</span>',
        "    # Subtest: second",
        '<span class="failed">    not ok 1 - Case.test_three',
        "    # trace three</span>",
        "Bail out! failfast",
        "",
      ];
      this.assertEqual(tap.report_html(text.join("\n")), html.join("\n"));
    }

    // The text is escaped as HTML, inside a span and out of it.
    test_report_escape(): void {
      const text = [
        "ok 1 - a<b>&c",
        "    not ok 2 - Case.test_two",
        "    # x < y & z",
      ];
      const html = [
        "ok 1 - a&lt;b&gt;&amp;c",
        '<span class="failed">    not ok 2 - Case.test_two',
        "    # x &lt; y &amp; z</span>",
      ];
      this.assertEqual(tap.report_html(text.join("\n")), html.join("\n"));
    }
  }
}
Object.freeze(test_tap);
