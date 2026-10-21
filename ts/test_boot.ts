// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the bundle's entry: its frozen modules, the page's entries it
// gives, the entry of the test engine page, and the size of the pool the
// worker's start installs.

namespace test_boot {
  // The entries of the bundle and the pool the start installs.
  export class TestBootEntries extends unittest.TestCase {
    // The entry and the two thread modules are frozen objects.
    test_modules_frozen(): void {
      this.assertTrue(Object.isFrozen(boot));
      this.assertTrue(Object.isFrozen(page));
      this.assertTrue(Object.isFrozen(worker_ai));
    }

    // The page's entries are the page module's own.
    test_entries_shared(): void {
      this.assertTrue(boot.page_main === page.page_main);
      this.assertTrue(boot.DomPort === page.DomPort);
      this.assertTrue(boot.test_page === page.test_page);
      this.assertTrue(boot.test_engine === page.test_engine);
    }

    // The test engine page's entry is a frozen module of that one function.
    test_hook_frozen(): void {
      this.assertTrue(Object.isFrozen(test_hook));
      this.assertEqual(Object.keys(test_hook).join(","), "engine_run");
    }

    // The pool holds two files per database of the server, then 36 spares.
    test_pool_capacity(): void {
      this.assertEqual(boot.pool_capacity(0), 36);
      this.assertEqual(boot.pool_capacity(4), 44);
    }
  }
}

Object.freeze(test_boot);
