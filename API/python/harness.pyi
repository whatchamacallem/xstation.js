# The test harness beside `unittest`: the one door by which a test module
# reads `settings.json` and `test_settings.json`, the gold record of expected
# test results, both at the checkout's top. It imports the standard library
# only, so it sits below every module, and its texts are plain English. Each
# file is read once, at the first call that needs it. An id is a key, nested
# keys joined by `.`, as `python.test_jslb.limits`. A test module imports
# only its own module, the standard library and this one.

from typing import Any

# A value of `settings.json`. Raises `KeyError` on an unknown id.
def setting_get(id: str) -> Any: ...

# A value of `test_settings.json`. Raises `KeyError` on an unknown id.
def gold_get(id: str) -> Any: ...

# A deep copy of the whole of `settings.json`, as a root's settings start.
def settings_copy() -> dict[str, Any]: ...

# A deep copy of the whole of `test_settings.json`, as a root's copy starts.
def gold_copy() -> dict[str, Any]: ...
