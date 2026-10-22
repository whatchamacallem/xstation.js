// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests the unittest subset: the outcome each kind of test reports, expected
// failures, the order of a test's parts, the loader, the stop flag, the
// asserts and the stack of a failed assertion. The fixtures are nested in the
// test class so that no loader collects them.

namespace test_unittest {
  // A result that records each event it receives as one line of text.
  class EventLog implements unittest.TestResult {
    // The counts of Python's `TestResult`, and its stop flag.
    testsRun = 0;
    failures = 0;
    errors = 0;
    skipped = 0;
    shouldStop = false;

    // The events in the order they came.
    readonly events: string[] = [];

    // Whether no test failed or raised.
    wasSuccessful(): boolean {
      return this.failures === 0 && this.errors === 0;
    }

    // Records that a test started.
    startTest(test: unittest.TestCase): void {
      this.testsRun += 1;
      this.events.push(`start ${test.id()}`);
    }

    // Records a pass.
    addSuccess(test: unittest.TestCase): void {
      this.events.push(`success ${test.id()}`);
    }

    // Records a failure and its message.
    addFailure(test: unittest.TestCase, error: Error): void {
      this.failures += 1;
      this.events.push(`failure ${test.id()} ${error.message}`);
    }

    // Records an error and its message.
    addError(test: unittest.TestCase, error: Error): void {
      this.errors += 1;
      this.events.push(`error ${test.id()} ${error.message}`);
    }

    // Records a skip and its reason.
    addSkip(test: unittest.TestCase, reason: string): void {
      this.skipped += 1;
      this.events.push(`skip ${test.id()} ${reason}`);
    }

    // Records an expected failure and its message.
    addExpectedFailure(test: unittest.TestCase, error: Error): void {
      this.events.push(`expected ${test.id()} ${error.message}`);
    }

    // Records an unexpected success.
    addUnexpectedSuccess(test: unittest.TestCase): void {
      this.events.push(`unexpected ${test.id()}`);
    }
  }

  // The nested fixture's tests, loaded from a module object that holds it.
  function fixture_suite(): unittest.TestSuite {
    return new unittest.TestLoader().loadTestsFromModule({
      NestedFixture: TestUnittest.NestedFixture,
    });
  }

  // The name and the message of the error the function throws.
  function thrown_text(fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      if (!(error instanceof Error)) {
        throw new TypeError("the function threw a value that is no Error", {
          cause: error,
        });
      }
      return `${error.name}: ${error.message}`;
    }
    throw new Error("the function threw nothing");
  }

  // Tests the unittest subset on the fixtures nested here.
  export class TestUnittest extends unittest.TestCase {
    // A pass, a failure, an error and a skip, recording the parts that ran.
    static readonly NestedFixture = class NestedFixture
      extends unittest.TestCase
    {
      // The parts of the test that ran, in order.
      readonly calls: string[] = [];

      // Records that `setUp` ran.
      override setUp(): void {
        this.calls.push("setUp");
      }

      // Records that `tearDown` ran.
      override tearDown(): void {
        this.calls.push("tearDown");
      }

      // Passes.
      test_alpha_passes(): void {
        this.calls.push("test_alpha_passes");
      }

      // Fails an assertion.
      test_bravo_fails(): void {
        this.calls.push("test_bravo_fails");
        this.assertEqual(1, 2);
      }

      // Throws an error that is not an assertion's.
      test_charlie_raises(): void {
        this.calls.push("test_charlie_raises");
        throw new Error("fixture error");
      }

      // Skips itself.
      test_delta_skips(): void {
        this.calls.push("test_delta_skips");
        this.skipTest("fixture skip");
      }
    };

    // Test methods defined out of name order, and a method that is no test.
    static readonly OrderFixture = class OrderFixture
      extends unittest.TestCase
    {
      // Defined first.
      test_zulu_first(): void {}

      // Defined second.
      test_alpha_second(): void {}

      // Not a test.
      helper_method(): void {}
    };

    // Tests expected to fail: one fails, one throws, one passes, one skips.
    static readonly ExpectedFixture = class ExpectedFixture
      extends unittest.TestCase
    {
      // Fails an assertion.
      test_assertion_fails(): void {
        this.assertEqual(1, 2);
      }

      // Throws an error that is not an assertion's.
      test_error_thrown(): void {
        throw new Error("fixture error");
      }

      // Passes.
      test_values_equal(): void {
        this.assertEqual(1, 1);
      }

      // Skips itself.
      test_skip_self(): void {
        this.skipTest("fixture skip");
      }

      // Marks every test of the class as expected to fail.
      static {
        unittest.expectedFailure(this.prototype.test_assertion_fails);
        unittest.expectedFailure(this.prototype.test_error_thrown);
        unittest.expectedFailure(this.prototype.test_values_equal);
        unittest.expectedFailure(this.prototype.test_skip_self);
      }
    };

    // A test expected to fail whose `setUp` throws.
    static readonly SetupFixture = class SetupFixture
      extends unittest.TestCase
    {
      // Throws before the test.
      override setUp(): void {
        throw new Error("fixture error");
      }

      // Never runs.
      test_values_differ(): void {
        this.assertEqual(1, 2);
      }

      // Marks the test as expected to fail.
      static {
        unittest.expectedFailure(this.prototype.test_values_differ);
      }
    };

    // Each kind of test reports the outcome Python reports.
    test_outcome_events(): void {
      const log = new EventLog();
      fixture_suite().run(log);
      this.assertEqual(log.events, [
        "start NestedFixture.test_alpha_passes",
        "success NestedFixture.test_alpha_passes",
        "start NestedFixture.test_bravo_fails",
        "failure NestedFixture.test_bravo_fails 1 != 2",
        "start NestedFixture.test_charlie_raises",
        "error NestedFixture.test_charlie_raises fixture error",
        "start NestedFixture.test_delta_skips",
        "skip NestedFixture.test_delta_skips fixture skip",
      ]);
      this.assertEqual(
        [log.testsRun, log.failures, log.errors, log.skipped],
        [4, 1, 1, 1],
      );
      this.assertFalse(log.wasSuccessful());
    }

    // `tearDown` runs after a test that passed and after one that failed.
    test_part_order(): void {
      const passing = new TestUnittest.NestedFixture("test_alpha_passes");
      passing.run(new EventLog());
      this.assertEqual(passing.calls, [
        "setUp",
        "test_alpha_passes",
        "tearDown",
      ]);
      const failing = new TestUnittest.NestedFixture("test_bravo_fails");
      failing.run(new EventLog());
      this.assertEqual(failing.calls, [
        "setUp",
        "test_bravo_fails",
        "tearDown",
      ]);
    }

    // The loader takes `TestCase` classes only, methods in definition order.
    test_loader_order(): void {
      const suite = new unittest.TestLoader().loadTestsFromModule({
        count: 3,
        OrderFixture: TestUnittest.OrderFixture,
        plain: Object,
      });
      this.assertEqual(suite.countTestCases(), 2);
      const log = new EventLog();
      suite.run(log);
      this.assertEqual(log.events, [
        "start OrderFixture.test_zulu_first",
        "success OrderFixture.test_zulu_first",
        "start OrderFixture.test_alpha_second",
        "success OrderFixture.test_alpha_second",
      ]);
    }

    // A test expected to fail reports a throw as expected and a pass as not.
    test_expected_outcomes(): void {
      const log = new EventLog();
      const suite = new unittest.TestLoader().loadTestsFromModule({
        ExpectedFixture: TestUnittest.ExpectedFixture,
      });
      suite.run(log);
      this.assertEqual(log.events, [
        "start ExpectedFixture.test_assertion_fails",
        "expected ExpectedFixture.test_assertion_fails 1 != 2",
        "start ExpectedFixture.test_error_thrown",
        "expected ExpectedFixture.test_error_thrown fixture error",
        "start ExpectedFixture.test_values_equal",
        "unexpected ExpectedFixture.test_values_equal",
        "start ExpectedFixture.test_skip_self",
        "skip ExpectedFixture.test_skip_self fixture skip",
      ]);
    }

    // An error in `setUp` of a test expected to fail is an error.
    test_expected_setup(): void {
      const log = new EventLog();
      new TestUnittest.SetupFixture("test_values_differ").run(log);
      this.assertEqual(log.events, [
        "start SetupFixture.test_values_differ",
        "error SetupFixture.test_values_differ fixture error",
      ]);
    }

    // The stack of a failed assertion starts with its name and message.
    test_stack_header(): void {
      let header = "";
      try {
        this.fail("header check");
      } catch (error) {
        header = String((error as Error).stack).split("\n")[0];
      }
      this.assertEqual(header, "AssertionError: header check");
    }

    // A result that asks to stop before the first test runs nothing.
    test_stop_flag(): void {
      const log = new EventLog();
      log.shouldStop = true;
      fixture_suite().run(log);
      this.assertEqual(log.events, []);
    }

    // A case bound to a method its class lacks is refused.
    test_missing_method(): void {
      this.assertEqual(
        thrown_text(() => new TestUnittest.NestedFixture("test_missing")),
        "TypeError: NestedFixture has no method test_missing",
      );
    }

    // `assertEqual` compares arrays, bytes and plain objects by content.
    test_assert_equal(): void {
      this.assertEqual([1, [2, "x"]], [1, [2, "x"]]);
      this.assertEqual({ a: 1, b: [2] }, { b: [2], a: 1 });
      this.assertEqual(new Uint8Array([1, 2]), new Uint8Array([1, 2]));
      this.assertEqual(
        thrown_text(() => this.assertEqual([1], [1, 2])),
        "AssertionError: [1] != [1,2]",
      );
      this.assertEqual(
        thrown_text(() => this.assertEqual({ a: 1 }, { a: 1, b: 2 })),
        'AssertionError: {"a":1} != {"a":1,"b":2}',
      );
      this.assertEqual(
        thrown_text(() =>
          this.assertEqual(new Uint8Array([1]), new Uint8Array([2])),
        ),
        'AssertionError: {"0":1} != {"0":2}',
      );
      this.assertEqual(
        thrown_text(() => this.assertEqual("1", 1)),
        'AssertionError: "1" != 1',
      );
    }

    // `assertIn` searches text, arrays by value and object keys.
    test_assert_in(): void {
      this.assertIn("b", "abc");
      this.assertIn([2], [[1], [2]]);
      this.assertIn("k", { k: 1 });
      this.assertEqual(
        thrown_text(() => this.assertIn("z", "abc")),
        'AssertionError: "z" not found in "abc"',
      );
      this.assertEqual(
        thrown_text(() => this.assertIn(3, [1, 2])),
        "AssertionError: 3 not found in [1,2]",
      );
      this.assertEqual(
        thrown_text(() => this.assertIn("j", { k: 1 })),
        'AssertionError: "j" not found in {"k":1}',
      );
      this.assertEqual(
        thrown_text(() => this.assertIn(1, "abc")),
        "TypeError: 1 is no text to search for",
      );
      this.assertEqual(
        thrown_text(() => this.assertIn(1, 5)),
        "TypeError: cannot search in 5",
      );
    }

    // `assertRaises` passes on its class, fails on no throw, passes others on.
    test_assert_raises(): void {
      this.assertRaises(RangeError, () => {
        throw new RangeError("range");
      });
      this.assertEqual(
        thrown_text(() => this.assertRaises(RangeError, () => 0)),
        "AssertionError: RangeError not raised",
      );
      this.assertEqual(
        thrown_text(() =>
          this.assertRaises(RangeError, () => {
            throw new TypeError("type");
          }),
        ),
        "TypeError: type",
      );
    }

    // `assertTrue` and `assertFalse` follow JavaScript truth.
    test_truth_asserts(): void {
      this.assertTrue(1);
      this.assertFalse("");
      this.assertEqual(
        thrown_text(() => this.assertTrue(0)),
        "AssertionError: 0 is not true",
      );
      this.assertEqual(
        thrown_text(() => this.assertFalse("x")),
        'AssertionError: "x" is not false',
      );
    }
  }
}
Object.freeze(test_unittest);
