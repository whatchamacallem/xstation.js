from typing import Any

# Reads settings.json. Raises on a missing or extra key or a wrong type.
def settings_load(path: str) -> dict[str, Any]: ...

# Checks a settings object as `settings_load` does, for `settings.put`.
def settings_check(settings: dict[str, Any]) -> None: ...
