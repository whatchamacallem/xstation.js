# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the settings check on a good object and on copies with a missing key,
# an extra key or a wrong type, the load from scratch files, and the real file.

import copy, json, os, settings, tempfile, unittest
from typing import Any

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
    "verbose_forward": True,
    "line_max": 1048576,
    "blob_max": 1073741824,
    "overflow_bytes": 131072,
    "chunk_bytes": 1048576,
    "srv_buf_size": 1048576,
    "media_db_bytes": 268435456,
    "files_browser_bytes": 1073741824,
    "turn_compact_tokens": 65536,
    "long_task_ms": 5,
    "provider": {
        "scripted": True,
        "base_url": "https://api.x.ai/v1",
        "chat_model": "grok-4",
        "image_model": "grok-2-image",
        "timeout_seconds": 120,
    },
}

# The paths of the values that are bools, nested names joined by `.`.
_BOOL_PATHS = (
    "debug",
    "queue_synchronous",
    "verbose_forward",
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
    "files_browser_bytes",
    "turn_compact_tokens",
    "long_task_ms",
    "provider.timeout_seconds",
)

# The paths of the values that are strings.
_STR_PATHS = (
    "provider.base_url",
    "provider.chat_model",
    "provider.image_model",
)

# The paths of the values that are objects.
_OBJECT_PATHS = ("provider",)

# Values that are not a bool. An int is not a bool.
_NOT_BOOL: tuple[Any, ...] = (None, 0, 1, 1.5, "true", [], {})

# Values that are not an int. A bool is not an int and nor is a float.
_NOT_INT: tuple[Any, ...] = (None, False, True, 1.0, 1.5, "1", [], {})

# Values that are not a string.
_NOT_STR: tuple[Any, ...] = (None, False, 0, 1.5, [], {})

# Values that are not an object.
_NOT_OBJECT: tuple[Any, ...] = (None, False, 0, 1.5, "text", [])


# Returns a copy of the good object, for a test to damage.
def _good_make() -> dict[str, Any]:
    return copy.deepcopy(_GOOD_SETTINGS)


# Returns the object that holds the path, and the last name of the path.
def _holder_find(
    value: dict[str, Any], path: str
) -> tuple[dict[str, Any], str]:
    names = path.split(".")
    for name in names[:-1]:
        value = value[name]
    return value, names[-1]


# Tests of the check on a good object and on damaged copies of it.
class TestCheck(unittest.TestCase):
    # Asserts the check refuses the object with an error naming the path.
    def check_fails(self, bad: dict[str, Any], path: str, note: str) -> None:
        with self.assertRaises(ValueError, msg=note) as context:
            settings.settings_check(bad)
        self.assertIn(path, str(context.exception), note)

    # Asserts each value, put in place of each path's value, is refused.
    def values_refuse(
        self, paths: tuple[str, ...], values: tuple[Any, ...]
    ) -> None:
        for path in paths:
            for value in values:
                bad = _good_make()
                holder, name = _holder_find(bad, path)
                holder[name] = value
                self.check_fails(bad, path, f"{path} {value!r}")

    # A value that is not a bool is refused where a bool belongs.
    def test_bool_wrong(self) -> None:
        self.values_refuse(_BOOL_PATHS, _NOT_BOOL)

    # A good object passes and the check leaves it as it was.
    def test_good_object(self) -> None:
        good = _good_make()
        settings.settings_check(good)
        self.assertEqual(good, _GOOD_SETTINGS)

    # A value that is not an int is refused where an int belongs.
    def test_int_wrong(self) -> None:
        self.values_refuse(_INT_PATHS, _NOT_INT)

    # An extra key at the top level or in the provider object is refused.
    def test_key_extra(self) -> None:
        for path in ("extra", "provider.extra"):
            bad = _good_make()
            holder, name = _holder_find(bad, path)
            holder[name] = 0
            self.check_fails(bad, path, path)

    # Each missing key, at the top level or in the provider object, is refused.
    def test_key_missing(self) -> None:
        paths = _BOOL_PATHS + _INT_PATHS + _STR_PATHS + _OBJECT_PATHS
        for path in paths:
            bad = _good_make()
            holder, name = _holder_find(bad, path)
            del holder[name]
            self.check_fails(bad, path, path)

    # A value that is not an object is refused where the provider belongs.
    def test_object_wrong(self) -> None:
        self.values_refuse(_OBJECT_PATHS, _NOT_OBJECT)

    # A value that is not a string is refused where a string belongs.
    def test_str_wrong(self) -> None:
        self.values_refuse(_STR_PATHS, _NOT_STR)


# Tests of the load on scratch files and on the checkout's file.
class TestLoad(unittest.TestCase):
    # Makes the scratch directory and the path of the settings file in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.file_path = os.path.join(scratch, "settings.json")

    # Asserts the load refuses the file with an error that names the needle.
    def load_fails(self, needle: str, note: str) -> None:
        with self.assertRaises(ValueError, msg=note) as context:
            settings.settings_load(self.file_path)
        self.assertIn(needle, str(context.exception), note)

    # Writes the text to the scratch file.
    def text_write(self, text: str) -> None:
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(text)

    # A file that does not exist raises and nothing is defaulted.
    def test_file_absent(self) -> None:
        with self.assertRaises(FileNotFoundError):
            settings.settings_load(self.file_path)

    # A file that is not JSON raises the decoder's error.
    def test_file_invalid(self) -> None:
        self.text_write("{")
        with self.assertRaises(json.JSONDecodeError):
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
        self.load_fails("extra", "extra")

    # A good file loads to the object as read, with the order of its keys.
    def test_load_good(self) -> None:
        self.text_write(json.dumps(_GOOD_SETTINGS))
        loaded = settings.settings_load(self.file_path)
        self.assertEqual(loaded, _GOOD_SETTINGS)
        self.assertEqual(list(loaded), list(_GOOD_SETTINGS))
        self.assertEqual(
            list(loaded["provider"]), list(_GOOD_SETTINGS["provider"])
        )

    # A file with a missing key is refused.
    def test_load_missing(self) -> None:
        bad = _good_make()
        del bad["provider"]["chat_model"]
        self.text_write(json.dumps(bad))
        self.load_fails("provider.chat_model", "provider.chat_model")

    # A file whose JSON is not an object is refused naming the file.
    def test_load_object(self) -> None:
        for text in ("[]", '"text"', "null", "1"):
            self.text_write(text)
            self.load_fails(self.file_path, text)

    # A file with a value of the wrong type is refused.
    def test_load_type(self) -> None:
        bad = _good_make()
        bad["debug"] = 1
        self.text_write(json.dumps(bad))
        self.load_fails("debug", "debug")
