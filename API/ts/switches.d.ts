// The run's three switches, `--anthropic`, `--debug` and `--verbose`, as
// python/switches.py's `switches_get` gives them, set once per thread from
// `tap.start`, on the AI worker and in the realms, or from `settings.set`,
// on the UI thread. A value that is not exactly those three booleans is
// refused, and every read before the set throws.

declare namespace switches {
  // The three switches, as `tap.start` and `settings.set` carry them.
  interface Switches {
    anthropic: boolean;
    debug: boolean;
    verbose: boolean;
  }

  // The switches of one thread, set once.
  class SwitchStore {
    // Stores the switches once, frozen, refusing a value of another shape.
    value_set(value: Switches): void;
    // Returns the switches, throwing before the set.
    value_get(): Switches;
  }

  // Stores the switches `tap.start` or `settings.set` carried, once.
  function switches_set(value: Switches): void;

  // Returns this thread's switches, throwing before `switches_set`.
  function switches_get(): Switches;

  // Whether the run is in Anthropic's cloud container.
  function anthropic_on(): boolean;

  // Whether the run's debug switch is on.
  function debug_on(): boolean;

  // Whether the run's verbose switch is on.
  function verbose_on(): boolean;
}
