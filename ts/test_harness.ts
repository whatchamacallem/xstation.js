// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of harness.ts on the values the bring-up set: a setting and a gold
// value read by their ids, the gold a copy of the built `test_gold`, a
// nested id, the text of an unknown id and of an id through a value that is
// no object, the refusal of a second values_set, and the deep freeze of
// what it keeps. The throw before values_set is not
// reachable from a suite, since every suite runs after the bring-up set the
// values.

namespace test_harness {
  // The gold the page or the Node bundle defines before the bundle.
  declare const test_gold: harness.Gold;

  // The texts the harness throws, written here by hand.
  const constants = Object.freeze({
    values_twice: "the harness values are set already",
    settings_unknown: "settings.json has no value with id",
    value_unknown: "has no value with id",
  });

  // The message of the error the function throws, which it must throw.
  function message_thrown(fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error.message;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // Whether the value and every object and array in it are frozen.
  function frozen_deep(value: unknown): boolean {
    if (typeof value !== "object" || value === null) {
      return true;
    }
    return Object.isFrozen(value) && Object.values(value).every(frozen_deep);
  }

  // The values the bring up gave the harness.
  export class TestValues extends unittest.TestCase {
    // The unit suites run only in debug mode, and only in the unit run.
    test_run_values(): void {
      this.assertTrue(switches.debug_on());
      this.assertEqual(harness.gold_get("typescript.test_all.run"), "unit");
    }

    // The gold is a copy of the built `test_gold`, not the object itself.
    test_gold_built(): void {
      const gold = harness.gold_get("typescript");
      this.assertEqual(
        JSON.stringify(gold),
        JSON.stringify(test_gold["typescript"]),
      );
      this.assertTrue(gold !== test_gold["typescript"]);
    }

    // A nested id reads the value under each of its keys.
    test_nested_id(): void {
      const timeout = harness.setting_get("provider.timeout_seconds");
      this.assertEqual(typeof timeout, "number");
    }

    // An unknown id, or one through a value that is no object, names its file.
    test_unknown_id(): void {
      const cases: [() => unknown, string][] = [
        [
          () => harness.setting_get("no_such_setting"),
          `${constants.settings_unknown} "no_such_setting"`,
        ],
        [
          () => harness.setting_get("queue_synchronous.value"),
          `${constants.settings_unknown} "queue_synchronous.value"`,
        ],
        [
          () => harness.gold_get("typescript.no_such_value"),
          "ts/test_setting_no_such_value.json" +
            ` ${constants.value_unknown} "typescript.no_such_value"`,
        ],
        [
          () => harness.gold_get("typescript.test_all.run.length"),
          "ts/test_setting_test_all.json" +
            ` ${constants.value_unknown} "typescript.test_all.run.length"`,
        ],
        [
          () => harness.gold_get("python.test_jslb"),
          `the gold ${constants.value_unknown} "python.test_jslb"`,
        ],
      ];
      for (const [fn, message] of cases) {
        this.assertEqual(message_thrown(fn), message);
      }
    }

    // A second `values_set` throws and the values stay as they were.
    test_set_twice(): void {
      const message = message_thrown(() =>
        harness.values_set({} as settings.Settings),
      );
      this.assertEqual(message, constants.values_twice);
      this.assertEqual(harness.gold_get("typescript.test_all.run"), "unit");
    }

    // What the harness keeps is frozen, every object and array in it too.
    test_values_frozen(): void {
      const gold = harness.gold_get("typescript");
      const provider = harness.setting_get("provider");
      this.assertEqual(typeof gold, "object");
      this.assertEqual(typeof provider, "object");
      this.assertTrue(frozen_deep(gold));
      this.assertTrue(frozen_deep(provider));
    }
  }
}
Object.freeze(test_harness);
