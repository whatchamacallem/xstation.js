// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// A test block that fails by design, which test_all.py lists apart from the
// blocks so that only --module runs it: a run of it with --failures checks
// that the failing tests of a TypeScript block relayed into the stream are
// reported, and that the count is right. Each test ends one way a test can
// end in TypeScript's unittest: one passes, one fails an assertion, one
// throws an error, one is skipped, one fails as it is expected to and one
// passes though it is expected to fail. Without failfast its block holds 3
// failing points; with failfast its stream ends at the first with a bail
// out.

namespace failing_block {
  // Tests that end each way a test can end, 3 of them failing.
  export class TestOutcomes extends unittest.TestCase {
    // Passes.
    test_passed(): void {
      this.assertEqual(1, 1);
    }

    // Fails an assertion.
    test_failed(): void {
      this.assertEqual(1, 2);
    }

    // Throws an error that is no assertion.
    test_errored(): void {
      throw new Error("an error by design");
    }

    // Is skipped.
    test_skipped(): void {
      this.skipTest("skipped by design");
    }

    // Fails as it is expected to, which counts as no failure.
    test_expected_failed(): void {
      this.assertEqual(1, 2);
    }

    // Passes though it is expected to fail, which counts as a failure.
    test_unexpected_passed(): void {
      this.assertEqual(1, 1);
    }

    // Marks the two tests as expected to fail.
    static {
      unittest.expectedFailure(this.prototype.test_expected_failed);
      unittest.expectedFailure(this.prototype.test_unexpected_passed);
    }
  }
}

Object.freeze(failing_block);
