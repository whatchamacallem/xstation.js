# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the settings check on good objects, plain and as read off the wire,
# each object a `jslb.Object`, the class the decoder makes, and on copies
# with a missing key, an extra key or a wrong type, a list or a dict of
# strings with one wrong item among them, the load from scratch files, and
# the real file. The expected texts are the gold's.

import copy, harness, json, os, settings, tempfile, unittest
from typing import Any, cast

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The settings file at the top level of the checkout.
_SETTINGS_PATH = os.path.join(_ROOT_PATH, "settings.json")

# A good settings object, which each test copies before it damages the copy.
_GOOD_SETTINGS: dict[str, Any] = {
    "debug": True,
    "queue_synchronous": False,
    "verbose_level": 1,
    "verbose_ring": 1000,
    "line_max": 1048576,
    "blob_max": 2147483391,
    "overflow_bytes": 131072,
    "chunk_bytes": 1048576,
    "srv_buf_size": 1048576,
    "media_db_bytes": 268435456,
    "turn_compact_turns": 64,
    "provider": {
        "scripted": True,
        "timeout_seconds": 120,
        "variable": "XSJS_PROVIDER_KEY",
    },
    "powershell": {
        "windows_port": 5768,
        "linux_port": 5769,
        "bind_address": "127.0.0.1",
        "bootstrap_script": "bootstrap.py",
        "engine_page": "hyperposition-engine.html",
        "ttyd_build": "build/ttyd",
        "ttyd_archive": "third_party/ttyd-1.7.7.tar.gz",
        "ttyd_patches": "third_party/ttyd",
        "terminal_type": "dumb",
        "linux_folder": ".cache/xsjs",
        "distribution": "Ubuntu",
        "task_name": "xstation.js",
        "firewall_rule": "xstation.js",
        "state_folder": "xstation.js",
        "certificate_file": "_cached_cert.pem",
        "key_file": "_cached_key.pem",
        "certificate_days": 825,
        "runner_file": "serve.ps1",
        "ttyd_log_file": "ttyd.log",
        "poll_tries": 30,
        "poll_milliseconds": 500,
        "output_width": 200,
        "root_files": ["settings.json", "test_settings.json", "provider.json"],
        "runtime_modules": [
            "internationalization",
            "jslb",
            "settings",
            "main_loop",
        ],
        "build_tools": {"cmake": "cmake", "patch": "patch"},
        "build_headers": {"uv.h": "libuv1-dev", "zlib.h": "zlib1g-dev"},
    },
}

# The paths of the values that are bools, nested names joined by `.`.
_BOOL_PATHS = (
    "debug",
    "queue_synchronous",
    "provider.scripted",
)

# The paths of the values that are ints.
_INT_PATHS = (
    "verbose_level",
    "verbose_ring",
    "line_max",
    "blob_max",
    "overflow_bytes",
    "chunk_bytes",
    "srv_buf_size",
    "media_db_bytes",
    "turn_compact_turns",
    "provider.timeout_seconds",
    "powershell.windows_port",
    "powershell.linux_port",
    "powershell.certificate_days",
    "powershell.poll_tries",
    "powershell.poll_milliseconds",
    "powershell.output_width",
)

# The paths of the values that are strings.
_STR_PATHS = (
    "provider.variable",
    "powershell.bind_address",
    "powershell.bootstrap_script",
    "powershell.engine_page",
    "powershell.ttyd_build",
    "powershell.ttyd_archive",
    "powershell.ttyd_patches",
    "powershell.terminal_type",
    "powershell.linux_folder",
    "powershell.distribution",
    "powershell.task_name",
    "powershell.firewall_rule",
    "powershell.state_folder",
    "powershell.certificate_file",
    "powershell.key_file",
    "powershell.runner_file",
    "powershell.ttyd_log_file",
)

# The paths of the values that are lists of strings.
_LIST_PATHS = ("powershell.root_files", "powershell.runtime_modules")

# The paths of the values that are dicts of strings to strings.
_TABLE_PATHS = ("powershell.build_tools", "powershell.build_headers")

# The paths of the provider values that the provider file holds instead.
_MOVED_PATHS = (
    "provider.base_url",
    "provider.chat_model",
    "provider.image_model",
)

# The paths of the windows that `blob_max` replaced, refused as extra keys.
_WINDOW_PATHS = ("message_max", "queue_max")

# The paths of the values that are objects checked by their own tables.
_OBJECT_PATHS = ("provider", "powershell")

# The type names the check gives a list and a dict of strings.
_LIST_NAME = "list of str"
_TABLE_NAME = "dict of str to str"

# Values that are not a bool. An int is not a bool.
_NOT_BOOL: tuple[Any, ...] = (None, 0, 1, 1.5, "true", [], {})

# Values that are not an int. A bool is not an int and nor is a float.
_NOT_INT: tuple[Any, ...] = (None, False, True, 1.0, 1.5, "1", [], {})

# Values that are not a string. A list of one string is not one.
_NOT_STR: tuple[Any, ...] = (None, False, 0, 1.5, ["text"], {})

# Values that are not a list of strings, two with one wrong item among them.
_NOT_LIST: tuple[Any, ...] = (None, "text", 0, {}, ["a", 1], ["a", None])

# Values that are not a dict of strings, with a wrong key or value among.
_NOT_TABLE: tuple[Any, ...] = (None, "text", 0, ["a"], {"a": 1}, {1: "a"})

# Values that are not an object.
_NOT_OBJECT: tuple[Any, ...] = (None, False, 0, 1.5, "text", [])

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_settings"


# A text of this module's gold, each `{n}` replaced by the value `n`.
def _text_fill(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for index, value in enumerate(values):
        text = text.replace("{" + str(index) + "}", value)
    return text


# Returns a copy of the good object, for a test to damage.
def _good_make() -> dict[str, Any]:
    return copy.deepcopy(_GOOD_SETTINGS)


# A copy of a JSON value with each object a `jslb.Object`, at every depth.
def _objects_wire(value: Any) -> Any:
    if isinstance(value, dict):
        pairs = cast(dict[str, Any], value).items()
        return settings.jslb.Object(
            {key: _objects_wire(item) for key, item in pairs}
        )
    if isinstance(value, list):
        return [_objects_wire(item) for item in cast(list[Any], value)]
    return value


# Returns the good object as `settings.put` carries it, read off the wire.
def _wire_make() -> dict[str, Any]:
    wire: dict[str, Any] = _objects_wire(_GOOD_SETTINGS)
    return wire


# Returns the object that holds the path, and the last name of the path.
def _holder_find(
    value: dict[str, Any], path: str
) -> tuple[dict[str, Any], str]:
    names = path.split(".")
    for name in names[:-1]:
        value = value[name]
    return value, names[-1]


# Tests of the check on good objects and on damaged copies read off the wire.
class TestCheck(unittest.TestCase):
    # Asserts the check refuses the object with exactly the expected message.
    def check_fails(
        self, bad: dict[str, Any], expected: str, note: str
    ) -> None:
        with self.assertRaises(ValueError, msg=note) as context:
            settings.settings_check(bad)
        self.assertEqual(str(context.exception), expected, note)

    # Asserts each value, put in place of each path's value, is refused.
    def values_refuse(
        self, paths: tuple[str, ...], wanted: str, values: tuple[Any, ...]
    ) -> None:
        for path in paths:
            for value in values:
                bad = _wire_make()
                holder, name = _holder_find(bad, path)
                holder[name] = value
                found = type(value).__name__
                fill = (path, wanted, found)
                expected = _text_fill("settings_type_wrong", *fill)
                self.check_fails(bad, expected, f"{path} {value!r}")

    # A value that is not a bool is refused where a bool belongs.
    def test_bool_wrong(self) -> None:
        self.values_refuse(_BOOL_PATHS, "bool", _NOT_BOOL)

    # A good plain object passes and the check leaves it as it was.
    def test_good_object(self) -> None:
        good = _good_make()
        settings.settings_check(good)
        self.assertEqual(good, _GOOD_SETTINGS)

    # A value that is not an int is refused where an int belongs.
    def test_int_wrong(self) -> None:
        self.values_refuse(_INT_PATHS, "int", _NOT_INT)

    # A value that is not a string is refused where a string belongs.
    def test_str_wrong(self) -> None:
        self.values_refuse(_STR_PATHS, "str", _NOT_STR)

    # A list with a wrong item, or no list, is refused as a list of strings.
    def test_list_wrong(self) -> None:
        self.values_refuse(_LIST_PATHS, _LIST_NAME, _NOT_LIST)

    # A dict with a wrong key or value, or no dict, is refused as a table.
    def test_table_wrong(self) -> None:
        self.values_refuse(_TABLE_PATHS, _TABLE_NAME, _NOT_TABLE)

    # Empty lists and tables of strings pass, as no item is wrong.
    def test_empty_pass(self) -> None:
        good = _wire_make()
        for path in _LIST_PATHS:
            holder, name = _holder_find(good, path)
            holder[name] = []
        for path in _TABLE_PATHS:
            holder, name = _holder_find(good, path)
            holder[name] = {}
        settings.settings_check(good)

    # An extra key, the provider file's and the old windows' among them, fails.
    def test_key_extra(self) -> None:
        paths = ("extra", "provider.extra", "powershell.extra")
        for path in paths + _MOVED_PATHS + _WINDOW_PATHS:
            bad = _wire_make()
            holder, name = _holder_find(bad, path)
            holder[name] = 0
            expected = _text_fill("settings_key_extra", path)
            self.check_fails(bad, expected, path)

    # Each missing key, at the top level or in a nested object, is refused.
    def test_key_missing(self) -> None:
        paths = (
            _BOOL_PATHS
            + _INT_PATHS
            + _STR_PATHS
            + _LIST_PATHS
            + _TABLE_PATHS
            + _OBJECT_PATHS
        )
        for path in paths:
            bad = _wire_make()
            holder, name = _holder_find(bad, path)
            del holder[name]
            expected = _text_fill("settings_key_missing", path)
            self.check_fails(bad, expected, path)

    # A good object off the wire, its nested objects decoder objects, passes.
    def test_nested_objects(self) -> None:
        good = _wire_make()
        for path in _OBJECT_PATHS + _TABLE_PATHS:
            holder, name = _holder_find(good, path)
            self.assertIs(type(holder[name]), settings.jslb.Object, path)
        settings.settings_check(good)
        self.assertEqual(good, _GOOD_SETTINGS)

    # A value that is not an object is refused where an object belongs.
    def test_object_wrong(self) -> None:
        self.values_refuse(_OBJECT_PATHS, "dict", _NOT_OBJECT)


# Tests of the load on scratch files and on the checkout's file.
class TestLoad(unittest.TestCase):
    # Makes the scratch directory and the path of the settings file in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.file_path = os.path.join(scratch, "settings.json")

    # Asserts the load refuses the file with exactly the expected message.
    def load_fails(self, expected: str, note: str) -> None:
        with self.assertRaises(ValueError, msg=note) as context:
            settings.settings_load(self.file_path)
        self.assertEqual(str(context.exception), expected, note)

    # Writes the text to the scratch file.
    def text_write(self, text: str) -> None:
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(text)

    # A file that does not exist raises and nothing is defaulted.
    def test_file_absent(self) -> None:
        with self.assertRaises(FileNotFoundError):
            settings.settings_load(self.file_path)

    # The settings file at the top level of the checkout loads and checks.
    def test_file_real(self) -> None:
        loaded = settings.settings_load(_SETTINGS_PATH)
        settings.settings_check(loaded)

    # A file with an extra key is refused.
    def test_load_extra(self) -> None:
        bad = _good_make()
        bad["extra"] = 0
        self.text_write(json.dumps(bad))
        self.load_fails(_text_fill("settings_key_extra_extra"), "extra")

    # A good file loads to the object as read, with the order of its keys.
    def test_load_good(self) -> None:
        self.text_write(json.dumps(_GOOD_SETTINGS))
        loaded = settings.settings_load(self.file_path)
        self.assertEqual(loaded, _GOOD_SETTINGS)
        self.assertEqual(list(loaded), list(_GOOD_SETTINGS))
        for name in _OBJECT_PATHS:
            self.assertEqual(list(loaded[name]), list(_GOOD_SETTINGS[name]))

    # A file with a missing key is refused.
    def test_load_missing(self) -> None:
        bad = _good_make()
        del bad["provider"]["timeout_seconds"]
        self.text_write(json.dumps(bad))
        path = "provider.timeout_seconds"
        self.load_fails(_text_fill("settings_key_missing_timeout"), path)

    # A file whose JSON is not an object is refused naming the file.
    def test_load_object(self) -> None:
        for text in ("[]", '"text"', "null", "1"):
            self.text_write(text)
            expected = _text_fill("settings_not_object", self.file_path)
            self.load_fails(expected, text)

    # A file with a value of the wrong type is refused.
    def test_load_type(self) -> None:
        bad = _good_make()
        bad["debug"] = 1
        self.text_write(json.dumps(bad))
        expected = _text_fill("settings_type_wrong_debug")
        self.load_fails(expected, "debug")
