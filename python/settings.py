# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Reads the `settings.json` file and checks that it holds exactly the keys and
# types of the tables below, with no defaults, and returns it as read.

import json
from typing import Any, cast
from i18n import i18n

# The keys of the settings object, each with the type its value must have.
_SETTING_TYPES: dict[str, type[object]] = {
    "debug": bool,
    "queue_synchronous": bool,
    "verbose_level": int,
    "verbose_ring": int,
    "verbose_forward": bool,
    "line_max": int,
    "blob_max": int,
    "overflow_bytes": int,
    "chunk_bytes": int,
    "srv_buf_size": int,
    "media_db_bytes": int,
    "files_browser_bytes": int,
    "turn_compact_tokens": int,
    "long_task_ms": int,
    "provider": dict,
}

# The keys of the provider object, each with the type its value must have.
_PROVIDER_TYPES: dict[str, type[object]] = {
    "scripted": bool,
    "base_url": str,
    "chat_model": str,
    "image_model": str,
    "timeout_seconds": int,
}


# Checks an object has exactly the keys of the table with exactly its types.
def _object_check(
    value: dict[str, Any], types: dict[str, type[object]], prefix: str
) -> None:
    for key in types:
        if key not in value:
            raise ValueError(i18n("settings.key_missing", prefix + key))
    for key in value:
        if key not in types:
            raise ValueError(i18n("settings.key_extra", prefix + key))
    for key, wanted in types.items():
        found = type(value[key])
        if found is not wanted:
            raise ValueError(
                i18n(
                    "settings.type_wrong",
                    prefix + key,
                    wanted.__name__,
                    found.__name__,
                )
            )


# Raises on a missing or extra key or a wrong type, for a settings object.
def settings_check(settings: dict[str, Any]) -> None:
    _object_check(settings, _SETTING_TYPES, "")
    _object_check(settings["provider"], _PROVIDER_TYPES, "provider.")


# Reads the file, checks it as `settings_check` does, returns it as read.
def settings_load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        data: object = json.load(file)
    settings = cast(dict[str, Any], data)
    if not isinstance(data, dict):
        raise ValueError(i18n("settings.not_object", path))
    settings_check(settings)
    return settings
