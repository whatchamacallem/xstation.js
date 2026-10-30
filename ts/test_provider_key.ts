// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the provider key that `provider.key_set` keeps in memory, each
// test setting the key it reads.

namespace test_provider_key {
  // The key `key_set` keeps in memory.
  export class TestProviderKey extends unittest.TestCase {
    // A second key replaces the first.
    test_key_replaced(): void {
      provider.key_set("first");
      this.assertEqual(provider.key_get(), "first");
      provider.key_set("second");
      this.assertEqual(provider.key_get(), "second");
    }

    // The empty key a scripted run may carry is kept as it is.
    test_key_empty(): void {
      provider.key_set("");
      this.assertEqual(provider.key_get(), "");
    }
  }
}

Object.freeze(test_provider_key);
