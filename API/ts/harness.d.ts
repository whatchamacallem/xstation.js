// The test harness of the test bundle beside `unittest`: the one door by which
// a test module reads `settings.json` and `test_settings.json`, the gold
// record of expected test results. It depends on no other module, so its
// texts are plain English. The bring-up gives each thread its values once,
// from `tap.start`, before any suite runs. An id is a key, nested keys joined
// by `.`, as `typescript.test_jslb.limits`. A test module references only
// its own module, `unittest` and this one.

declare namespace harness {
  // The object of `test_settings.json`.
  type Gold = { [key: string]: unknown };

  // Keeps deep frozen copies of both values, once: a second call throws.
  function values_set(value: settings.Settings, gold: Gold): void;

  // A value of `settings.json`. Throws before `values_set` and on unknown ids.
  function setting_get(id: string): unknown;

  // A value of `test_settings.json`. Throws as `setting_get` does.
  function gold_get(id: string): unknown;
}
