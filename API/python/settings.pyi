from typing import Any

# Reads `settings.json` and checks it; the result goes into `hello` as it
# is. Raises on a missing file, invalid JSON, a missing key or a wrong
# type. The keys are those of API/settings.json.
def settings_load(path: str) -> dict[str, Any]: ...

# Checks a settings object a client sent with `settings.put` in debug
# mode, before it is written to the root.
def settings_check(settings: dict[str, Any]) -> None: ...

# Reads `secrets.json` from the root: `provider_key`. Raises when absent.
def secrets_load(path: str) -> dict[str, str]: ...
