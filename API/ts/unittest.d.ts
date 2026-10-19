declare namespace unittest {
  // The subset of Python's unittest the tests use, same names, all
  // synchronous.
  class TestCase {
    setUp(): void;
    tearDown(): void;
    assertEqual(first: unknown, second: unknown, message?: string): void;
    assertTrue(value: unknown, message?: string): void;
    assertFalse(value: unknown, message?: string): void;
    assertRaises(
      error: new (...args: never[]) => Error,
      fn: () => unknown
    ): void;
    assertIn(member: unknown, container: unknown, message?: string): void;
    skipTest(reason: string): never;
    fail(message: string): never;
  }

  class TestSuite {
    addTest(test: TestCase | TestSuite): void;
    countTestCases(): number;
  }

  class TestLoader {
    // Every `test_` method of every TestCase class in the module object,
    // in definition order.
    loadTestsFromModule(module: { [name: string]: unknown }): TestSuite;
  }

  interface TestResult {
    testsRun: number;
    failures: number;
    errors: number;
    skipped: number;
    wasSuccessful(): boolean;
  }
}
