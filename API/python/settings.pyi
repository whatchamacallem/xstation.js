# The reader of `settings.json`. Every key of the file is checked against a
# table of its type: the top level keys, the keys of `provider` and the keys
# of `powershell`, the constants of the PowerShell scripts. A type is a
# bool, an int, a str, a list of str, a dict of str to str, or a nested
# object checked by its own table. The file is read by `jslb.json_decode`,
# the decoders' door for bad numbers.

from typing import Any

# Reads `settings.json`. Raises on a missing or extra key or a wrong type.
def settings_load(path: str) -> dict[str, Any]: ...

# Checks a settings object as `settings_load` does, for `settings.put`.
def settings_check(settings: dict[str, Any]) -> None: ...
