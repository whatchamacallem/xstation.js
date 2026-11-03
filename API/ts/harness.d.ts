// The test harness of the test bundle beside `unittest`: the one door by which
// a test module reads `settings.json` and the gold record of expected test
// results, the TypeScript suites' files `ts/test_setting_<suite>.json` that
// the page or the Node bundle defines as `test_gold`,
// `{"typescript": {suite: gold}}`, when it is built. It depends on no other
// module, so its texts are plain English. The bring-up gives each thread
// its settings once, from `tap.start`, before any suite runs, and the
// harness then keeps the gold of `test_gold` with them. An id is a
// key, nested keys joined by `.`, as `typescript.test_jslb.texts`. A test
// module calls into other project modules only once their own suites have
// passed earlier in the run.

declare namespace harness {
  // The gold of the TypeScript suites, `{"typescript": {suite: gold}}`.
  type Gold = { [key: string]: unknown };

  // Keeps deep frozen copies of the settings and `test_gold`, once.
  function values_set(value: settings.Settings): void;

  // A value of `settings.json`. Throws before `values_set` and on unknown ids.
  function setting_get(id: string): unknown;

  // A value of the gold, a refusal naming the suite's file or the gold.
  function gold_get(id: string): unknown;
}
