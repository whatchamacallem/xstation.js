// The subset of Python's unittest the tests use, the same names, all
// synchronous. A test module references only its own module, this one and
// `harness`, which reads the settings and the gold record.

declare namespace unittest {
  // What a run reports to: Python's counts and the outcome of each test.
  interface TestResult {
    testsRun: number;
    failures: number;
    errors: number;
    skipped: number;
    // When set, the run stops before its next test.
    shouldStop: boolean;
    wasSuccessful(): boolean;
    startTest(test: TestCase): void;
    addSuccess(test: TestCase): void;
    addFailure(test: TestCase, error: Error): void;
    addError(test: TestCase, error: Error): void;
    addSkip(test: TestCase, reason: string): void;
    addExpectedFailure(test: TestCase, error: Error): void;
    addUnexpectedSuccess(test: TestCase): void;
  }

  // Marks a test method as expected to fail, as Python's decorator does.
  function expectedFailure(method: () => unknown): void;

  // One `test_` method of a subclass, run between `setUp` and `tearDown`.
  class TestCase {
    // Binds the case to the named method of its class, which must exist.
    constructor(method_name: string);
    setUp(): void;
    tearDown(): void;
    // The test's name, `Class.method`.
    id(): string;
    // Runs the parts of the test in Python's order, reporting each outcome.
    run(result: TestResult): void;
    assertEqual(first: unknown, second: unknown, message?: string): void;
    assertTrue(value: unknown, message?: string): void;
    assertFalse(value: unknown, message?: string): void;
    // Fails unless the function throws the error class. Others pass through.
    assertRaises(
      error: new (...args: never[]) => Error,
      fn: () => unknown,
    ): void;
    assertIn(member: unknown, container: unknown, message?: string): void;
    skipTest(reason: string): never;
    fail(message: string): never;
  }

  // An ordered collection of tests and suites.
  class TestSuite {
    addTest(test: TestCase | TestSuite): void;
    countTestCases(): number;
    // Runs each test in order until the result asks to stop.
    run(result: TestResult): void;
  }

  class TestLoader {
    // A suite per `TestCase` class in the module, in definition order.
    loadTestsFromModule(module: { [name: string]: unknown }): TestSuite;
  }
}
