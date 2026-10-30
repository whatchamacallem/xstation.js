// The subset of Python's unittest the tests use, the same names, all
// synchronous.

declare namespace unittest {
  // Python's result: the tests run and each outcome, kept as Python keeps it.
  class TestResult {
    testsRun: number;
    // Each failed assertion's test and stack: an Error with no stack throws.
    readonly failures: [TestCase, string][];
    // Each other throw's test and stack, as `failures` keeps them.
    readonly errors: [TestCase, string][];
    // Each skipped test and its reason.
    readonly skipped: [TestCase, string][];
    // Each test that failed as expected, and the stack of its error.
    readonly expectedFailures: [TestCase, string][];
    // Each test that passed though it was expected to fail.
    readonly unexpectedSuccesses: TestCase[];
    // When set, the run stops before its next test.
    shouldStop: boolean;
    // A failure, an error or an unexpected success stops the run when set.
    readonly failfast: boolean;
    constructor(failfast: boolean);
    // Whether no test failed, threw or passed when it was expected to fail.
    wasSuccessful(): boolean;
    // Sets `shouldStop`.
    stop(): void;
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
