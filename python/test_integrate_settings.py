# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the settings joined to the codec of `jslb`: the checkout's settings
# carried by a `settings.put` line, written by the real encoder and read
# back by the real decoder, whose objects the check takes whole, and with a
# value damaged, at the top level and inside a nested object; and the load
# of scratch files that the decoders refuse at read, as the single door for
# bad numbers, a text that is not JSON and a number that overflows a double.
# The expected texts are the gold's.

import harness, jslb, json, os, settings, tempfile, unittest
from typing import Any, NoReturn, cast

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where each test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_integrate_settings"

# The type of the line that carries the settings.
_PUT_TYPE = "settings.put"

# The id of the `settings.put` line, the first a port counts after 101.
_PUT_ID = 102

# A number token that overflows a double, which the decoders refuse.
_OVERFLOW_TOKEN = "1e400"


# A text of this module's gold, each `{n}` replaced by the value `n`.
def _text_fill(name: str, *values: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    for index, value in enumerate(values):
        text = text.replace("{" + str(index) + "}", value)
    return text


# Refuses a blob, which no `settings.put` line carries.
def _sink_refuse(header: jslb.Object) -> NoReturn:
    raise RuntimeError("internal error")


# The settings of a `settings.put` line, written and read back as the
# server reads them, by a decoder of the checkout's limits.
def _settings_carried(values: dict[str, Any]) -> Any:
    header = jslb.header_make(_PUT_TYPE, id=_PUT_ID)
    line = jslb.line_make(header, [], settings=values)
    (piece,) = jslb.line_encode(line)
    if not isinstance(piece, bytes):
        raise AssertionError(f"{piece} is no line")
    decoder = jslb.LineDecoder(
        harness.setting_get("line_max"),
        harness.setting_get("blob_max"),
        harness.setting_get("overflow_bytes"),
        _sink_refuse,
    )
    (read,) = decoder.bytes_feed(piece)
    return jslb.payload_of(read)["settings"]


# Tests of the check on the settings a `settings.put` line carried.
class TestCarried(unittest.TestCase):
    # Asserts the check refuses the settings with exactly the text given.
    def check_fails(self, carried: Any, expected: str) -> None:
        with self.assertRaises(ValueError) as context:
            settings.settings_check(carried)
        self.assertEqual(str(context.exception), expected)

    # The checkout's settings pass the check as the decoder's objects.
    def test_settings_carried(self) -> None:
        values = harness.settings_copy()
        carried = _settings_carried(values)
        for value in (carried, carried["provider"], carried["powershell"]):
            self.assertIs(type(value), jslb.Object)
        settings.settings_check(carried)
        self.assertEqual(carried, values)

    # A value of the wrong type at the top level is refused.
    def test_debug_damaged(self) -> None:
        values = harness.settings_copy()
        values["debug"] = 1
        expected = _text_fill("settings_type_wrong_debug")
        self.check_fails(_settings_carried(values), expected)

    # A list with an item of the wrong type in a nested object is refused.
    def test_list_damaged(self) -> None:
        values = harness.settings_copy()
        values["powershell"]["root_files"] = ["settings.json", 1]
        expected = _text_fill("settings_type_wrong_root_files")
        self.check_fails(_settings_carried(values), expected)


# Tests of the load of files that the decoders refuse at read.
class TestDoor(unittest.TestCase):
    # Makes the scratch directory and the path of the settings file in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.file_path = os.path.join(scratch, "settings.json")

    # Writes the text to the scratch file.
    def text_write(self, text: str) -> None:
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(text)

    # Loads the scratch file and returns the decoders' refusal it raises.
    def wire_refused(self) -> jslb.WireError:
        with self.assertRaises(jslb.WireError) as context:
            settings.settings_load(self.file_path)
        return context.exception

    # A file that is not JSON raises the decoders' `jslb.text_not_json`.
    def test_file_invalid(self) -> None:
        self.text_write("{")
        error = self.wire_refused()
        cause = error.__cause__
        self.assertIsInstance(cause, json.JSONDecodeError)
        reason = cast(json.JSONDecodeError, cause).msg
        expected = _text_fill("jslb_text_not_json", reason)
        self.assertEqual(str(error), expected)

    # A number that overflows a double is refused at read, by the decoders.
    def test_number_overflow(self) -> None:
        self.text_write('{"verbose_ring": ' + _OVERFLOW_TOKEN + "}")
        error = self.wire_refused()
        self.assertEqual(str(error), _text_fill("jslb_number_overflow"))
