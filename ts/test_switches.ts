// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the switches module: a store's set once and its reads, the values
// of another shape refused, each thrown text compared to its entry in the gold
// record, `ts/test_setting_test_switches.json`, and this realm's switches,
// which its `tap.start` carried, read alike by the module's three readers.

namespace test_switches {
  // The values a store is given, each its writer's choice.
  const constants = Object.freeze({
    // A value of the right shape, its three switches mixed.
    good: Object.freeze({ anthropic: true, debug: false, verbose: true }),
    // Values of another shape, each with the name of its text in the gold.
    malformed: Object.freeze([
      [null, "switches_malformed_null"],
      [undefined, "switches_malformed_undefined"],
      [1, "switches_malformed_number"],
      [[true, false, true], "switches_malformed_array"],
      [{ anthropic: false, debug: false }, "switches_malformed_missing"],
      [
        { anthropic: false, debug: false, verbose: false, other: false },
        "switches_malformed_extra",
      ],
      [
        { anthropic: "1", debug: false, verbose: false },
        "switches_malformed_string",
      ],
    ] as const),
  });

  // A text of this module's gold.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_switches.texts.${name}`,
    ) as string;
  }

  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // One store for each test, so no test leaves a state behind.
  export class TestSwitchStore extends unittest.TestCase {
    // A value set is read back equal and frozen.
    test_set_read(): void {
      const store = new switches.SwitchStore();
      store.value_set({ ...constants.good });
      const value = store.value_get();
      this.assertEqual(value, { ...constants.good });
      this.assertTrue(Object.isFrozen(value));
    }

    // A second set throws and keeps the first value.
    test_set_twice(): void {
      const store = new switches.SwitchStore();
      store.value_set({ ...constants.good });
      const other = { anthropic: false, debug: true, verbose: false };
      const message = message_thrown(this, () => store.value_set(other));
      this.assertEqual(message, gold_text("switches_already_set"));
      this.assertEqual(store.value_get(), { ...constants.good });
    }

    // A read before the set throws.
    test_get_unset(): void {
      const store = new switches.SwitchStore();
      const message = message_thrown(this, () => store.value_get());
      this.assertEqual(message, gold_text("switches_not_set"));
    }

    // Each value of another shape throws, naming it, and sets nothing.
    test_set_malformed(): void {
      for (const [value, name] of constants.malformed) {
        const store = new switches.SwitchStore();
        const message = message_thrown(this, () =>
          store.value_set(value as unknown as switches.Switches),
        );
        this.assertEqual(message, gold_text(name), name);
        const unset = message_thrown(this, () => store.value_get());
        this.assertEqual(unset, gold_text("switches_not_set"), name);
      }
    }
  }

  // This realm's switches, set from its `tap.start` before the block ran.
  export class TestThread extends unittest.TestCase {
    // The three readers agree, and a second set throws.
    test_thread_read(): void {
      const value = switches.switches_get();
      this.assertEqual(Object.keys(value).sort(), [
        "anthropic",
        "debug",
        "verbose",
      ]);
      this.assertEqual(switches.anthropic_on(), value.anthropic);
      this.assertEqual(switches.debug_on(), value.debug);
      const message = message_thrown(this, () =>
        switches.switches_set({ ...value }),
      );
      this.assertEqual(message, gold_text("switches_already_set"));
    }
  }
}

Object.freeze(test_switches);
