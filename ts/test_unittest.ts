// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests the unittest subset through its real result: the outcome each kind of
// test reports, expected failures, the order of a test's parts and of its
// reports, the loader, the stop flag and failfast, the asserts and the stack
// of a failed assertion. The fixtures are nested in the test class so that no
// loader collects them.

namespace test_unittest {
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

  // Each outcome a result kept, as its test's id and its text's first line.
  function outcomes_read(
    outcomes: readonly [unittest.TestCase, string][],
  ): [string, string][] {
    return outcomes.map(([test, text]) => [test.id(), text.split("\n")[0]]);
  }

  // The ids of the tests a result kept.
  function ids_read(tests: readonly unittest.TestCase[]): string[] {
    return tests.map((test) => test.id());
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

    // Records what the result it is run on holds at each of its parts.
    static readonly CountFixture = class CountFixture
      extends unittest.TestCase
    {
      // The result this fixture is run on, which its parts read.
      readonly result = new unittest.TestResult(false);
      // Each part with the tests run and the failures kept when it ran.
      readonly counts: string[] = [];

      // Records the counts at `setUp`.
      override setUp(): void {
        this.count_add("setUp");
      }

      // Records the counts at `tearDown`.
      override tearDown(): void {
        this.count_add("tearDown");
      }

      // Records the counts, then fails an assertion.
      test_values_differ(): void {
        this.count_add("test_values_differ");
        this.assertEqual(1, 2);
      }

      // Records the part with the tests run and the failures kept so far.
      count_add(part: string): void {
        const { testsRun, failures } = this.result;
        this.counts.push(`${part} ${testsRun} ${failures.length}`);
      }
    };

    // Test methods defined out of name order, and a method that is no test.
    static readonly OrderFixture = class OrderFixture
      extends unittest.TestCase
    {
      // Defined first, skips with a reason that says so.
      test_zulu_first(): void {
        this.skipTest("first");
      }

      // Defined second, skips with a reason that says so.
      test_alpha_second(): void {
        this.skipTest("second");
      }

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

    // Throws an Error made with no stack.
    static readonly StacklessFixture = class StacklessFixture
      extends unittest.TestCase
    {
      // Throws an Error that no constructor gave a stack.
      test_stack_missing(): void {
        throw Object.create(Error.prototype) as Error;
      }
    };

    // Each kind of test is kept as Python keeps it.
    test_outcome_lists(): void {
      const result = new unittest.TestResult(false);
      fixture_suite().run(result);
      this.assertEqual(result.testsRun, 4);
      this.assertEqual(outcomes_read(result.failures), [
        ["NestedFixture.test_bravo_fails", "AssertionError: 1 != 2"],
      ]);
      this.assertEqual(outcomes_read(result.errors), [
        ["NestedFixture.test_charlie_raises", "Error: fixture error"],
      ]);
      this.assertEqual(outcomes_read(result.skipped), [
        ["NestedFixture.test_delta_skips", "fixture skip"],
      ]);
      this.assertEqual(result.expectedFailures, []);
      this.assertEqual(result.unexpectedSuccesses, []);
      this.assertFalse(result.shouldStop);
      this.assertFalse(result.wasSuccessful());
    }

    // A pass is kept by no list, and leaves the result successful.
    test_success_unkept(): void {
      const result = new unittest.TestResult(false);
      new TestUnittest.NestedFixture("test_alpha_passes").run(result);
      this.assertEqual(result.testsRun, 1);
      this.assertEqual(
        [result.failures, result.errors, result.skipped],
        [[], [], []],
      );
      this.assertEqual(result.expectedFailures, []);
      this.assertEqual(result.unexpectedSuccesses, []);
      this.assertTrue(result.wasSuccessful());
    }

    // `tearDown` runs after a test that passed and after one that failed.
    test_part_order(): void {
      const passing = new TestUnittest.NestedFixture("test_alpha_passes");
      passing.run(new unittest.TestResult(false));
      this.assertEqual(passing.calls, [
        "setUp",
        "test_alpha_passes",
        "tearDown",
      ]);
      const failing = new TestUnittest.NestedFixture("test_bravo_fails");
      failing.run(new unittest.TestResult(false));
      this.assertEqual(failing.calls, [
        "setUp",
        "test_bravo_fails",
        "tearDown",
      ]);
    }

    // A test starts before `setUp`, and a failure is kept before `tearDown`.
    test_report_order(): void {
      const fixture = new TestUnittest.CountFixture("test_values_differ");
      fixture.run(fixture.result);
      this.assertEqual(fixture.counts, [
        "setUp 1 0",
        "test_values_differ 1 0",
        "tearDown 1 1",
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
      const result = new unittest.TestResult(false);
      suite.run(result);
      this.assertEqual(result.testsRun, 2);
      this.assertEqual(outcomes_read(result.skipped), [
        ["OrderFixture.test_zulu_first", "first"],
        ["OrderFixture.test_alpha_second", "second"],
      ]);
      this.assertTrue(result.wasSuccessful());
    }

    // A test expected to fail keeps a throw as expected and a pass as not.
    test_expected_outcomes(): void {
      const result = new unittest.TestResult(false);
      const suite = new unittest.TestLoader().loadTestsFromModule({
        ExpectedFixture: TestUnittest.ExpectedFixture,
      });
      suite.run(result);
      this.assertEqual(result.testsRun, 4);
      this.assertEqual(outcomes_read(result.expectedFailures), [
        ["ExpectedFixture.test_assertion_fails", "AssertionError: 1 != 2"],
        ["ExpectedFixture.test_error_thrown", "Error: fixture error"],
      ]);
      this.assertEqual(ids_read(result.unexpectedSuccesses), [
        "ExpectedFixture.test_values_equal",
      ]);
      this.assertEqual(outcomes_read(result.skipped), [
        ["ExpectedFixture.test_skip_self", "fixture skip"],
      ]);
      this.assertEqual([result.failures, result.errors], [[], []]);
      this.assertFalse(result.wasSuccessful());
    }

    // An error in `setUp` of a test expected to fail is an error.
    test_expected_setup(): void {
      const result = new unittest.TestResult(false);
      new TestUnittest.SetupFixture("test_values_differ").run(result);
      this.assertEqual(outcomes_read(result.errors), [
        ["SetupFixture.test_values_differ", "Error: fixture error"],
      ]);
      this.assertEqual(result.expectedFailures, []);
      this.assertEqual(result.testsRun, 1);
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
      const result = new unittest.TestResult(false);
      result.stop();
      fixture_suite().run(result);
      this.assertEqual(result.testsRun, 0);
      this.assertTrue(result.shouldStop);
    }

    // With failfast a failure stops the run, and so does an unexpected pass.
    test_failfast_stops(): void {
      const failed = new unittest.TestResult(true);
      fixture_suite().run(failed);
      this.assertEqual(failed.testsRun, 2);
      this.assertEqual(outcomes_read(failed.failures), [
        ["NestedFixture.test_bravo_fails", "AssertionError: 1 != 2"],
      ]);
      this.assertEqual([failed.errors, failed.skipped], [[], []]);
      this.assertTrue(failed.shouldStop);
      const surprised = new unittest.TestResult(true);
      new unittest.TestLoader()
        .loadTestsFromModule({ ExpectedFixture: TestUnittest.ExpectedFixture })
        .run(surprised);
      this.assertEqual(surprised.testsRun, 3);
      this.assertEqual(ids_read(surprised.unexpectedSuccesses), [
        "ExpectedFixture.test_values_equal",
      ]);
      this.assertEqual(surprised.skipped, []);
      this.assertTrue(surprised.shouldStop);
    }

    // A throw with no stack has no text to keep, and the result says so.
    test_stack_missing(): void {
      const fixture = new TestUnittest.StacklessFixture("test_stack_missing");
      const result = new unittest.TestResult(false);
      this.assertEqual(
        thrown_text(() => fixture.run(result)),
        "Error: StacklessFixture.test_stack_missing threw an error with no " +
          "stack: Error",
      );
      this.assertEqual(result.errors, []);
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
