// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The test harness of the test bundle beside `unittest`: the one door by
// which a test module reads `settings.json` and the gold record of expected
// test results, the TypeScript suites' files `ts/test_setting_<suite>.json`
// that the page or the Node bundle defines as `test_gold`,
// `{"typescript": {suite: gold}}`, when it is built. It depends on no other
// module, so its texts are plain English. The bring-up gives each thread its
// settings once, from `tap.start`, before any suite runs, and the harness
// keeps deep frozen copies of them and of `test_gold`. An id is a key, nested keys
// joined by `.`, as `typescript.test_jslb.texts`; a refusal names the
// suite's file, or the gold when the id names no suite. A test module calls
// into other project modules only once their own suites have passed earlier
// in the run.

namespace harness {
  // The gold of the TypeScript suites, `{"typescript": {suite: gold}}`.
  export type Gold = { [key: string]: unknown };

  // The gold the page or the Node bundle defines before the bundle.
  declare const test_gold: Gold;

  // The names a refusal gives, the mark joining an id's keys, throw texts.
  const constants = Object.freeze({
    settings_name: "settings.json",
    gold_name: "the gold",
    gold_language: "typescript",
    gold_directory: "ts/",
    gold_prefix: "test_setting_",
    gold_suffix: ".json",
    id_mark: ".",
    values_twice: "the harness values are set already",
    values_missing:
      "the harness values are not set: values_set was not called",
    id_unknown: "has no value with id",
  });

  // The two values the harness keeps.
  interface HarnessValues {
    settings: unknown;
    gold: unknown;
  }

  // The deep frozen copies `values_set` made, once.
  let kept: HarnessValues | undefined = undefined;

  // Freezes the value and every object and array in it, and returns it.
  function freeze_deep<T>(value: T): T {
    if (typeof value === "object" && value !== null) {
      for (const item of Object.values(value)) {
        freeze_deep(item);
      }
      Object.freeze(value);
    }
    return value;
  }

  // Whether the value is a plain object, from a literal or a clone of one.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // The values `values_set` kept, which must have been set.
  function values_get(): HarnessValues {
    if (kept === undefined) {
      throw new Error(constants.values_missing);
    }
    return kept;
  }

  // The value under each key of the id in turn, from the file named.
  function value_find(root: unknown, file: string, id: string): unknown {
    let value = root;
    for (const key of id.split(constants.id_mark)) {
      if (!object_plain(value) || !Object.hasOwn(value, key)) {
        throw new Error(
          `${file} ${constants.id_unknown} ${JSON.stringify(id)}`,
        );
      }
      value = value[key];
    }
    return value;
  }

  // The file a refusal of the id names: its suite's, or the gold as a whole.
  function gold_file(id: string): string {
    const keys = id.split(constants.id_mark);
    if (keys.length < 2 || keys[0] !== constants.gold_language) {
      return constants.gold_name;
    }
    const name = `${constants.gold_prefix}${keys[1]}${constants.gold_suffix}`;
    return `${constants.gold_directory}${name}`;
  }

  // Keeps deep frozen copies of the settings and `test_gold`, once.
  export function values_set(value: settings.Settings): void {
    if (kept !== undefined) {
      throw new Error(constants.values_twice);
    }
    kept = {
      settings: freeze_deep(structuredClone(value)),
      gold: freeze_deep(structuredClone(test_gold)),
    };
  }

  // A value of `settings.json`. Throws before `values_set` and on unknown ids.
  export function setting_get(id: string): unknown {
    return value_find(values_get().settings, constants.settings_name, id);
  }

  // A value of the gold, a refusal naming the suite's file or the gold.
  export function gold_get(id: string): unknown {
    return value_find(values_get().gold, gold_file(id), id);
  }
}
Object.freeze(harness);
