// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The test of the provider key unset, a block of its own so that its realm
// starts with no key set: nothing sets it at bring up, and no other test of
// the block sets one. On the shared realm of the ttyd page this block runs
// before any suite that sets a key. The text of the refusal is its gold in
// `test_settings.json`, read through the harness.

namespace test_provider_key_unset {
  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A text of this module's gold.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_provider_key_unset.texts.${name}`,
    ) as string;
  }

  // The key `key_get` reads before any is set.
  export class TestProviderKey extends unittest.TestCase {
    // With no key set in this realm, `key_get` refuses.
    test_key_unset(): void {
      const error = thrown_get(() => provider.key_get());
      this.assertEqual(error.message, gold_text("provider_key_missing"));
    }
  }
}

Object.freeze(test_provider_key_unset);
