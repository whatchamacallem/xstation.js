# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the lookup and the placeholder rule of the strings module on a patched
# table, the loader's refusals of a strings file of the wrong shape, then the
# real strings file and the names the sources look up in it.

import glob, internationalization, json, os, re, tempfile, unittest
import unittest.mock
from collections.abc import Callable
from internationalization import i18n

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The checkout's build directory, where a test makes its scratch directory.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The strings file of the checkout.
_STRINGS_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# The dotted name of the strings table that the lookup tests patch.
_STRINGS_TARGET = "internationalization._STRINGS"

# A call to `i18n` with a literal name, which the pattern captures.
_CALL_NAME = re.compile(r'\bi18n\(\s*"([^"]+)"')

# A placeholder, a decimal index with no leading zero in braces.
_PLACEHOLDER = re.compile(r"\{(0|[1-9][0-9]*)\}")

# The strings the lookup tests patch in.
_TEST_STRINGS = {
    "t.gap": "{0} and {2}",
    "t.late": "{1}",
    "t.literal": "{} {a} {-1} { 0 } {0 {01} } {1.5}",
    "t.mixed": "{a} {0} {}",
    "t.one": "one {0}",
    "t.plain": "plain",
    "t.repeat": "{0} and {1} and {0}",
    "t.two": "{0} then {1}",
}


# Reads the real strings file, a JSON object.
def _strings_read() -> dict[str, object]:
    with open(_STRINGS_PATH, encoding="utf-8") as file:
        strings: dict[str, object] = json.load(file)
    return strings


# Finds the source files that are not tests, in `python` and `ts`.
def _sources_find() -> list[str]:
    paths = glob.glob(os.path.join(_ROOT_PATH, "python", "*.py"))
    paths += glob.glob(os.path.join(_ROOT_PATH, "ts", "*.ts"))
    return sorted(
        path
        for path in paths
        if not os.path.basename(path).startswith("test_")
    )


# Tests the lookup, the placeholder rule and the argument checks.
class TestLookup(unittest.TestCase):
    # Patches the strings table to the test strings until the test ends.
    def setUp(self) -> None:
        patcher = unittest.mock.patch.dict(
            _STRINGS_TARGET, _TEST_STRINGS, clear=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # A name the table lacks raises, naming it.
    def test_name_missing(self) -> None:
        with self.assertRaises(KeyError) as caught:
            i18n("t.absent")
        self.assertEqual(caught.exception.args, ("t.absent",))

    # Fewer arguments than placeholders raises.
    def test_arguments_few(self) -> None:
        with self.assertRaises(ValueError) as caught:
            i18n("t.two", "a")
        message = "t.two: placeholders [0, 1], arguments 1"
        self.assertEqual(caught.exception.args, (message,))
        with self.assertRaises(ValueError) as caught:
            i18n("t.one")
        message = "t.one: placeholders [0], arguments 0"
        self.assertEqual(caught.exception.args, (message,))

    # More arguments than placeholders raises.
    def test_arguments_many(self) -> None:
        with self.assertRaises(ValueError) as caught:
            i18n("t.one", "a", "b")
        message = "t.one: placeholders [0], arguments 2"
        self.assertEqual(caught.exception.args, (message,))
        with self.assertRaises(ValueError) as caught:
            i18n("t.plain", "a")
        message = "t.plain: placeholders [], arguments 1"
        self.assertEqual(caught.exception.args, (message,))

    # A repeated index counts once and each argument is made into text.
    def test_index_repeat(self) -> None:
        self.assertEqual(i18n("t.repeat", 7, "b"), "7 and b and 7")
        with self.assertRaises(ValueError) as caught:
            i18n("t.repeat", 7, "b", "c")
        message = "t.repeat: placeholders [0, 1], arguments 3"
        self.assertEqual(caught.exception.args, (message,))

    # An index gap raises even when the distinct count equals the arguments.
    def test_index_gap(self) -> None:
        with self.assertRaises(ValueError) as caught:
            i18n("t.gap", "a", "b")
        message = "t.gap: placeholders [0, 2], arguments 2"
        self.assertEqual(caught.exception.args, (message,))
        with self.assertRaises(ValueError) as caught:
            i18n("t.late", "a")
        message = "t.late: placeholders [1], arguments 1"
        self.assertEqual(caught.exception.args, (message,))

    # Braces that are not a placeholder pass through, also from an argument.
    def test_braces_literal(self) -> None:
        self.assertEqual(i18n("t.literal"), _TEST_STRINGS["t.literal"])
        self.assertEqual(i18n("t.mixed", "x"), "{a} x {}")
        self.assertEqual(i18n("t.two", "{1}", "b"), "{1} then b")


# Tests the loader's refusals of a strings file of the wrong shape.
class TestLoading(unittest.TestCase):
    # Writes the text as a strings file in a scratch directory under `build/`.
    def file_write(self, text: str) -> str:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        path = os.path.join(scratch, "en-US.json")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    # A document that is not one JSON object raises, naming the file.
    def test_document_refused(self) -> None:
        path = self.file_write('["text"]')
        load: Callable[[str], dict[str, str]] = getattr(
            internationalization, "_strings_load"
        )
        with self.assertRaises(ValueError) as caught:
            load(path)
        message = f"{path}: not a JSON object"
        self.assertEqual(caught.exception.args, (message,))

    # A value that is not a string raises, naming the file and the name.
    def test_value_refused(self) -> None:
        path = self.file_write('{"t.one": "one", "t.two": 2}')
        load: Callable[[str], dict[str, str]] = getattr(
            internationalization, "_strings_load"
        )
        with self.assertRaises(ValueError) as caught:
            load(path)
        message = f"{path}: 't.two' is not a string"
        self.assertEqual(caught.exception.args, (message,))


# Tests the real strings file and the names the sources look up in it.
class TestStrings(unittest.TestCase):
    # Every value of the file is a string with gapless placeholders.
    def test_file_values(self) -> None:
        for name, text in _strings_read().items():
            if not isinstance(text, str):
                self.fail(f"{name} is not a string")
            indices = {int(index) for index in _PLACEHOLDER.findall(text)}
            self.assertEqual(indices, set(range(len(indices))), name)

    # Every literal name the sources pass to `i18n` is in the file.
    def test_file_names(self) -> None:
        strings = _strings_read()
        for path in _sources_find():
            with open(path, encoding="utf-8") as file:
                text = file.read()
            for name in _CALL_NAME.findall(text):
                self.assertTrue(name in strings, f"{path}: {name}")
