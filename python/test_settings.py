# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the settings check on good objects, plain and read off the wire, and
# on copies with a missing key, an extra key or a wrong type, the load from
# scratch files, and the real file.

import copy, jslb, json, os, settings, tempfile, unittest
from i18n import i18n
from typing import Any, NoReturn, cast

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
    "blob_max": 10485760,
    "message_max": 10485760,
    "queue_max": 104857600,
    "overflow_bytes": 131072,
    "chunk_bytes": 1048576,
    "srv_buf_size": 1048576,
    "media_db_bytes": 268435456,
    "files_browser_bytes": 1073741824,
    "db_soft_bytes": 1073741824,
    "turn_compact_tokens": 65536,
    "long_task_ms": 5,
    "provider": {
        "scripted": True,
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
    "message_max",
    "queue_max",
    "overflow_bytes",
    "chunk_bytes",
    "srv_buf_size",
    "media_db_bytes",
    "files_browser_bytes",
    "db_soft_bytes",
    "turn_compact_tokens",
    "long_task_ms",
    "provider.timeout_seconds",
)

# The paths of the provider values that the provider file holds instead.
_MOVED_PATHS = (
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

# Values that are not an object.
_NOT_OBJECT: tuple[Any, ...] = (None, False, 0, 1.5, "text", [])

# The id of the `settings.put` request the tests read off the wire.
_REQUEST_ID = 1


# Returns a copy of the good object, for a test to damage.
def _good_make() -> dict[str, Any]:
    return copy.deepcopy(_GOOD_SETTINGS)


# Refuses a streamed blob, which the line of these tests does not carry.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError("a blob was streamed")


# Returns the good object as `settings.put` carries it, read off the wire.
def _wire_make() -> dict[str, Any]:
    header = jslb.header_make("settings.put", id=_REQUEST_ID)
    line = jslb.line_make(header, [], settings=_GOOD_SETTINGS)
    (piece,) = jslb.line_encode(line)
    decoder = jslb.LineDecoder(
        _GOOD_SETTINGS["line_max"],
        _GOOD_SETTINGS["blob_max"],
        _GOOD_SETTINGS["message_max"],
        _GOOD_SETTINGS["overflow_bytes"],
        _sink_refuse,
    )
    (decoded,) = decoder.bytes_feed(cast(bytes, piece))
    return decoded["settings"]


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
                expected = i18n("settings.type_wrong", path, wanted, found)
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

    # An extra key, the provider file's keys among them, is refused.
    def test_key_extra(self) -> None:
        for path in ("extra", "provider.extra") + _MOVED_PATHS:
            bad = _wire_make()
            holder, name = _holder_find(bad, path)
            holder[name] = 0
            expected = i18n("settings.key_extra", path)
            self.check_fails(bad, expected, path)

    # Each missing key, at the top level or in the provider object, is refused.
    def test_key_missing(self) -> None:
        paths = _BOOL_PATHS + _INT_PATHS + _OBJECT_PATHS
        for path in paths:
            bad = _wire_make()
            holder, name = _holder_find(bad, path)
            del holder[name]
            expected = i18n("settings.key_missing", path)
            self.check_fails(bad, expected, path)

    # A good object off the wire, whose provider is a nested `Object`, passes.
    def test_nested_provider(self) -> None:
        good = _wire_make()
        self.assertIs(type(good["provider"]), jslb.Object)
        settings.settings_check(good)
        self.assertEqual(good, _GOOD_SETTINGS)

    # A value that is not an object is refused where the provider belongs.
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
        self.load_fails(i18n("settings.key_extra", "extra"), "extra")

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
        del bad["provider"]["timeout_seconds"]
        self.text_write(json.dumps(bad))
        path = "provider.timeout_seconds"
        self.load_fails(i18n("settings.key_missing", path), path)

    # A file whose JSON is not an object is refused naming the file.
    def test_load_object(self) -> None:
        for text in ("[]", '"text"', "null", "1"):
            self.text_write(text)
            expected = i18n("settings.not_object", self.file_path)
            self.load_fails(expected, text)

    # A file with a value of the wrong type is refused.
    def test_load_type(self) -> None:
        bad = _good_make()
        bad["debug"] = 1
        self.text_write(json.dumps(bad))
        expected = i18n("settings.type_wrong", "debug", "bool", "int")
        self.load_fails(expected, "debug")
