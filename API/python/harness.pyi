# The test harness beside `unittest`: the one door by which a test module
# reads `settings.json`, at the checkout's top, and the gold record of
# expected test results, one file per suite, `test_setting_<suite>.json`
# beside the suite's module: `python/` for `python`, `ts/` for `typescript`
# and `powershell/` for `powershell`. It imports the standard library only,
# so it sits below every module, and its texts are plain English. Each file
# is read once, at the first call that needs it. An id is a key, nested keys
# joined by `.`, as `python.test_jslb.limits`: the language, the suite, then
# the keys of the suite's file. A test module imports the standard library,
# this one, the modules it tests, and other project modules only once their
# own suites have passed earlier in the run.

from typing import Any

# A value of `settings.json`. Raises `KeyError` on an unknown id.
def setting_get(id: str) -> Any: ...

# A value of the gold. Raises `KeyError` naming the suite's file or the gold.
def gold_get(id: str) -> Any: ...

# A deep copy of the whole of `settings.json`, as a root's settings start.
def settings_copy() -> dict[str, Any]: ...

# A deep copy of every suite's file, `{language: {suite: gold}}`.
def gold_copy() -> dict[str, Any]: ...
