// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The run's three switches, --anthropic, --debug and --verbose, as
// python/switches.py's `switches_get` gives them, set once per thread from
// `tap.start`, on the AI worker and in the realms, or from `settings.set`,
// on the UI thread. A value that is not exactly those three booleans is
// refused, and every read before the set throws.

namespace switches {
  // The constants of this module.
  const constants = Object.freeze({
    // The switches' names, in the order `switches_get` of Python gives them.
    names: Object.freeze(["anthropic", "debug", "verbose"]),
  });

  // The three switches, as `tap.start` and `settings.set` carry them.
  export interface Switches {
    anthropic: boolean;
    debug: boolean;
    verbose: boolean;
  }

  // Whether the value is an object of exactly the three names, each a bool.
  function shape_is(value: unknown): value is Switches {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return false;
    }
    const keys = Object.keys(value).sort();
    if (keys.join(",") !== constants.names.join(",")) {
      return false;
    }
    const fields = value as { [name: string]: unknown };
    return constants.names.every((name) => typeof fields[name] === "boolean");
  }

  // The switches of one thread, set once.
  export class SwitchStore {
    private value: Switches | undefined = undefined;

    // Stores the switches once, frozen, refusing a value of another shape.
    value_set(value: Switches): void {
      if (this.value !== undefined) {
        throw new Error(i18n("switches.already_set"));
      }
      if (!shape_is(value)) {
        throw new Error(
          i18n("switches.malformed", String(JSON.stringify(value))),
        );
      }
      this.value = Object.freeze({
        anthropic: value.anthropic,
        debug: value.debug,
        verbose: value.verbose,
      });
    }

    // Returns the switches, throwing before the set.
    value_get(): Switches {
      if (this.value === undefined) {
        throw new Error(i18n("switches.not_set"));
      }
      return this.value;
    }
  }

  // The switches of this thread, behind the functions below.
  const store = new SwitchStore();

  // Stores the switches `tap.start` or `settings.set` carried, once.
  export function switches_set(value: Switches): void {
    store.value_set(value);
  }

  // Returns this thread's switches, throwing before `switches_set`.
  export function switches_get(): Switches {
    return store.value_get();
  }

  // Whether the run is in Anthropic's cloud container.
  export function anthropic_on(): boolean {
    return store.value_get().anthropic;
  }

  // Whether the run's debug switch is on.
  export function debug_on(): boolean {
    return store.value_get().debug;
  }
}

Object.freeze(switches);
