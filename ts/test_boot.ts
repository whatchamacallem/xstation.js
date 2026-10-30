// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the bring up's entries: its frozen module and the three entries
// it gives, the page's its own, the one check that still names the page. The
// frozen page and AI worker modules are their own tests' to check. Run last
// on the UI thread, as boot depends on the page and on the AI worker.

namespace test_boot {
  // The entries of the bring up.
  export class TestBootEntries extends unittest.TestCase {
    // The module is a frozen object.
    test_modules_frozen(): void {
      this.assertTrue(Object.isFrozen(boot));
    }

    // The module holds the three entries and nothing else.
    test_entries_only(): void {
      this.assertEqual(Object.keys(boot).sort(), [
        "headless_worker",
        "test_page",
        "test_worker",
      ]);
    }

    // The page's entry is the page module's own.
    test_entries_shared(): void {
      this.assertTrue(boot.test_page === page.test_page);
    }
  }
}

Object.freeze(test_boot);
