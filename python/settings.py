# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The reader of `settings.json`. Every key of the file is checked against a
# table of its type, with no defaults: the top level keys, the keys of
# `provider` and the keys of `powershell`, the constants of the PowerShell
# scripts. A type is a bool, an int, a str, a list of str, a dict of str to
# str, or a nested object checked by its own table. The file is read by
# `jslb.json_decode`, the decoders' door for bad numbers, and returned as
# read.

import jslb
from internationalization import i18n
from typing import Any, cast

# A list of strings in a table, every item checked.
_LIST_TYPE = list[str]

# A dict of strings to strings in a table, every key and value checked.
_TABLE_TYPE = dict[str, str]

# The names the type error gives the list and the dict of strings.
_LIST_NAME = "list of str"
_TABLE_NAME = "dict of str to str"

# The keys of the settings object, each with the type its value must have.
_SETTING_TYPES: dict[str, object] = {
    "debug": bool,
    "queue_synchronous": bool,
    "verbose_level": int,
    "verbose_ring": int,
    "line_max": int,
    "blob_max": int,
    "overflow_bytes": int,
    "chunk_bytes": int,
    "srv_buf_size": int,
    "media_db_bytes": int,
    # The compaction threshold, 64, a default chosen by its writer.
    "turn_compact_turns": int,
    "provider": dict,
    "powershell": dict,
}

# The keys of the provider object, each with the type its value must have.
_PROVIDER_TYPES: dict[str, object] = {
    "scripted": bool,
    "timeout_seconds": int,
    "variable": str,
}

# The keys of the PowerShell object, in the order of `settings.json`.
_POWERSHELL_TYPES: dict[str, object] = {
    "windows_port": int,
    "linux_port": int,
    "bind_address": str,
    "bootstrap_script": str,
    "engine_page": str,
    "ttyd_build": str,
    "ttyd_archive": str,
    "ttyd_patches": str,
    "terminal_type": str,
    "linux_folder": str,
    "distribution": str,
    "task_name": str,
    "firewall_rule": str,
    "state_folder": str,
    "certificate_file": str,
    "key_file": str,
    "certificate_days": int,
    "runner_file": str,
    "ttyd_log_file": str,
    "poll_tries": int,
    "poll_milliseconds": int,
    "output_width": int,
    "root_files": _LIST_TYPE,
    "runtime_modules": _LIST_TYPE,
    "build_tools": _TABLE_TYPE,
    "build_headers": _TABLE_TYPE,
}


# Whether a value is a list whose every item is a `str`.
def _list_is(value: object) -> bool:
    if type(value) is not list:
        return False
    items = cast(list[object], value)
    return all(type(item) is str for item in items)


# Whether a value is a dict whose every key and value is a `str`.
def _table_is(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    pairs = cast(dict[object, object], value)
    return all(type(k) is str and type(v) is str for k, v in pairs.items())


# Checks an object's keys and types, any `dict` subclass passing as `dict`.
def _object_check(
    value: dict[str, Any], types: dict[str, object], prefix: str
) -> None:
    for key in types:
        if key not in value:
            raise ValueError(i18n("settings.key_missing", prefix + key))
    for key in value:
        if key not in types:
            raise ValueError(i18n("settings.key_extra", prefix + key))
    for key, wanted in types.items():
        item: object = value[key]
        if wanted == _LIST_TYPE:
            matches = _list_is(item)
            name = _LIST_NAME
        elif wanted == _TABLE_TYPE:
            matches = _table_is(item)
            name = _TABLE_NAME
        elif wanted is dict:
            matches = isinstance(item, dict)
            name = dict.__name__
        else:
            scalar = cast(type[object], wanted)
            matches = type(item) is scalar
            name = scalar.__name__
        if not matches:
            raise ValueError(
                i18n(
                    "settings.type_wrong",
                    prefix + key,
                    name,
                    type(item).__name__,
                )
            )


# Raises on a missing or extra key or a wrong type, for a settings object.
def settings_check(settings: dict[str, Any]) -> None:
    _object_check(settings, _SETTING_TYPES, "")
    _object_check(settings["provider"], _PROVIDER_TYPES, "provider.")
    _object_check(settings["powershell"], _POWERSHELL_TYPES, "powershell.")


# Reads the file, checks it as `settings_check` does, returns it as read.
def settings_load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        text = file.read()
    data: object = jslb.json_decode(text)
    if not isinstance(data, dict):
        raise ValueError(i18n("settings.not_object", path))
    settings = cast(dict[str, Any], data)
    settings_check(settings)
    return settings
