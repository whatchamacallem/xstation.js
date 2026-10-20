// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The subset of Python's unittest that the TypeScript tests use, with the
// same names, all synchronous. A test's parts run in Python's order and its
// outcomes reach a result as Python reports them, so that the TAP producer
// writes the same text in both languages.

namespace unittest {
  // The prefix of a test method, and how much of a value a message shows.
  const constants = Object.freeze({
    test_prefix: "test_",
    text_cut: " [truncated]...",
    text_max: 80,
  });

  // The test methods marked as expected to fail.
  const expected_methods = new WeakSet<object>();

  // What a failed assertion throws, which a result counts as a failure.
  class AssertionError extends Error {
    // Names the prototype, which the stack reads when the error is made.
    static {
      this.prototype.name = "AssertionError";
    }
  }

  // What `skipTest` throws, which a result counts as a skip.
  class SkipTest extends Error {
    // The name its stack shows.
    override name = "SkipTest";
  }

  // What a run reports to: Python's counts and the outcome of each test.
  export interface TestResult {
    testsRun: number;
    failures: number;
    errors: number;
    skipped: number;
    // When set, the run stops before its next test.
    shouldStop: boolean;
    // Whether no test failed or raised.
    wasSuccessful(): boolean;
    // A test starts, before its `setUp`.
    startTest(test: TestCase): void;
    // The test passed.
    addSuccess(test: TestCase): void;
    // An assertion of the test failed.
    addFailure(test: TestCase, error: Error): void;
    // The test threw an error that is not an assertion's.
    addError(test: TestCase, error: Error): void;
    // The test skipped itself.
    addSkip(test: TestCase, reason: string): void;
    // The test failed the way it was expected to.
    addExpectedFailure(test: TestCase, error: Error): void;
    // The test passed though it was expected to fail.
    addUnexpectedSuccess(test: TestCase): void;
  }

  // Marks a test method as expected to fail, as Python's decorator does.
  export function expectedFailure(method: () => unknown): void {
    expected_methods.add(method);
  }

  // One `test_` method of a subclass, run between `setUp` and `tearDown`.
  export class TestCase {
    // The test method this case runs.
    readonly #method: () => unknown;
    // The name of that method.
    readonly #method_name: string;

    // Binds the case to the named method of its class, which must exist.
    constructor(method_name: string) {
      const members = this as unknown as { [name: string]: unknown };
      const method = members[method_name];
      if (typeof method !== "function") {
        throw new TypeError(
          `${this.constructor.name} has no method ${method_name}`,
        );
      }
      this.#method = method as () => unknown;
      this.#method_name = method_name;
    }

    // Runs before the test method. Subclasses override it.
    setUp(): void {}

    // Runs after the test method when `setUp` passed.
    tearDown(): void {}

    // The test's name, `Class.method`. Python's starts with the module too.
    id(): string {
      return `${this.constructor.name}.${this.#method_name}`;
    }

    // Runs the parts of the test in Python's order, reporting each outcome.
    run(result: TestResult): void {
      result.startTest(this);
      const expecting = expected_methods.has(this.#method);
      const outcome: { expected: Error | null } = { expected: null };
      let passed = part_run(this, result, () => this.setUp());
      if (passed) {
        passed = part_run(this, result, () => {
          if (expecting) {
            outcome.expected = failure_catch(this.#method, this);
          } else {
            this.#method.call(this);
          }
        });
        passed = part_run(this, result, () => this.tearDown()) && passed;
      }
      if (!passed) {
        return;
      }
      if (!expecting) {
        result.addSuccess(this);
      } else if (outcome.expected === null) {
        result.addUnexpectedSuccess(this);
      } else {
        result.addExpectedFailure(this, outcome.expected);
      }
    }

    // Fails unless the values are equal, arrays, bytes and objects by content.
    assertEqual(first: unknown, second: unknown, message?: string): void {
      if (!value_equal(first, second)) {
        failure_throw(
          `${value_text(first)} != ${value_text(second)}`,
          message,
        );
      }
    }

    // Fails unless the value is truthy.
    assertTrue(value: unknown, message?: string): void {
      if (!value) {
        failure_throw(`${value_text(value)} is not true`, message);
      }
    }

    // Fails unless the value is falsy.
    assertFalse(value: unknown, message?: string): void {
      if (value) {
        failure_throw(`${value_text(value)} is not false`, message);
      }
    }

    // Fails unless the function throws the error class. Others pass through.
    assertRaises(
      error: new (...args: never[]) => Error,
      fn: () => unknown,
    ): void {
      try {
        fn();
      } catch (thrown) {
        if (thrown instanceof error) {
          return;
        }
        throw thrown;
      }
      failure_throw(`${error.name} not raised`, undefined);
    }

    // Fails unless the member is in the container: text, array or object.
    assertIn(member: unknown, container: unknown, message?: string): void {
      if (!member_in(member, container)) {
        failure_throw(
          `${value_text(member)} not found in ${value_text(container)}`,
          message,
        );
      }
    }

    // Ends the test as skipped, with the reason.
    skipTest(reason: string): never {
      throw new SkipTest(reason);
    }

    // Ends the test as failed, with the message.
    fail(message: string): never {
      throw new AssertionError(message);
    }
  }

  // An ordered collection of tests and suites.
  export class TestSuite {
    // The tests and suites, in the order they were added.
    readonly #tests: (TestCase | TestSuite)[] = [];

    // Adds a test or a suite at the end.
    addTest(test: TestCase | TestSuite): void {
      this.#tests.push(test);
    }

    // The number of test methods held, inner suites included.
    countTestCases(): number {
      let count = 0;
      for (const test of this.#tests) {
        count += test instanceof TestSuite ? test.countTestCases() : 1;
      }
      return count;
    }

    // Runs each test in order until the result asks to stop.
    run(result: TestResult): void {
      for (const test of this.#tests) {
        if (result.shouldStop) {
          return;
        }
        test.run(result);
      }
    }
  }

  // Collects the tests of a module object.
  export class TestLoader {
    // A suite per `TestCase` class in the module, in definition order.
    loadTestsFromModule(module: { [name: string]: unknown }): TestSuite {
      const suite = new TestSuite();
      for (const value of Object.values(module)) {
        if (
          typeof value === "function" &&
          value.prototype instanceof TestCase
        ) {
          suite.addTest(
            class_load(value as new (method_name: string) => TestCase),
          );
        }
      }
      return suite;
    }
  }

  // A suite of the class's own `test_` methods, in definition order.
  function class_load(
    test_class: new (method_name: string) => TestCase,
  ): TestSuite {
    const suite = new TestSuite();
    for (const name of Object.getOwnPropertyNames(test_class.prototype)) {
      if (name.startsWith(constants.test_prefix)) {
        suite.addTest(new test_class(name));
      }
    }
    return suite;
  }

  // Runs one part of a test and reports a throw as a skip, failure or error.
  function part_run(
    test: TestCase,
    result: TestResult,
    part: () => void,
  ): boolean {
    try {
      part();
    } catch (error) {
      if (!(error instanceof Error)) {
        throw new TypeError(`${test.id()} threw a value that is no Error`, {
          cause: error,
        });
      }
      if (error instanceof SkipTest) {
        result.addSkip(test, error.message);
      } else if (error instanceof AssertionError) {
        result.addFailure(test, error);
      } else {
        result.addError(test, error);
      }
      return false;
    }
    return true;
  }

  // Calls a test method expected to fail and returns its error, null if none.
  function failure_catch(method: () => unknown, test: TestCase): Error | null {
    try {
      method.call(test);
    } catch (error) {
      if (error instanceof SkipTest || !(error instanceof Error)) {
        throw error;
      }
      return error;
    }
    return null;
  }

  // Throws a failure, the caller's message after the standard one, as Python.
  function failure_throw(
    standard: string,
    message: string | undefined,
  ): never {
    throw new AssertionError(
      message === undefined ? standard : `${standard} : ${message}`,
    );
  }

  // Whether the values are equal: arrays, bytes and plain objects by content.
  function value_equal(first: unknown, second: unknown): boolean {
    if (first === second) {
      return true;
    }
    if (Array.isArray(first) && Array.isArray(second)) {
      const items: readonly unknown[] = first;
      const others: readonly unknown[] = second;
      return (
        items.length === others.length &&
        items.every((item, index) => value_equal(item, others[index]))
      );
    }
    if (first instanceof Uint8Array && second instanceof Uint8Array) {
      const others = second;
      return (
        first.length === others.length &&
        first.every((byte, index) => byte === others[index])
      );
    }
    if (object_plain(first) && object_plain(second)) {
      const keys = Object.keys(first);
      if (keys.length !== Object.keys(second).length) {
        return false;
      }
      for (const key of keys) {
        if (
          !Object.hasOwn(second, key) ||
          !value_equal(first[key], second[key])
        ) {
          return false;
        }
      }
      return true;
    }
    return false;
  }

  // Whether the value is a plain object, from a literal or `JSON.parse`.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // Whether the member is in the text, array by value, or object's keys.
  function member_in(member: unknown, container: unknown): boolean {
    if (typeof container === "string") {
      if (typeof member !== "string") {
        throw new TypeError(`${value_text(member)} is no text to search for`);
      }
      return container.includes(member);
    }
    if (Array.isArray(container)) {
      const items: readonly unknown[] = container;
      return items.some((item) => value_equal(item, member));
    }
    if (object_plain(container)) {
      return typeof member === "string" && Object.hasOwn(container, member);
    }
    throw new TypeError(`cannot search in ${value_text(container)}`);
  }

  // A value as message text, cut short as Python's `safe_repr` does.
  function value_text(value: unknown): string {
    const structured = typeof value === "object" && value !== null;
    const text =
      structured || typeof value === "string"
        ? JSON.stringify(value)
        : String(value);
    return text.length < constants.text_max
      ? text
      : text.slice(0, constants.text_max) + constants.text_cut;
  }
}
Object.freeze(unittest);
