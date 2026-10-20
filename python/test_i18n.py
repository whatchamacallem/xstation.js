# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the lookup and the placeholder rule of the strings module on a patched
# table, then the real strings file and the names the sources look up in it.

import glob, i18n, json, os, re, unittest, unittest.mock

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The strings file of the checkout.
_STRINGS_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# The dotted name of the strings table that the lookup tests patch.
_STRINGS_TARGET = "i18n._STRINGS"

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

    # A name the table lacks raises.
    def test_name_missing(self) -> None:
        with self.assertRaises(KeyError):
            i18n.i18n("t.absent")

    # Fewer arguments than placeholders raises.
    def test_arguments_few(self) -> None:
        with self.assertRaises(ValueError):
            i18n.i18n("t.two", "a")
        with self.assertRaises(ValueError):
            i18n.i18n("t.one")

    # More arguments than placeholders raises.
    def test_arguments_many(self) -> None:
        with self.assertRaises(ValueError):
            i18n.i18n("t.one", "a", "b")
        with self.assertRaises(ValueError):
            i18n.i18n("t.plain", "a")

    # A repeated index counts once and each argument is made into text.
    def test_index_repeat(self) -> None:
        self.assertEqual(i18n.i18n("t.repeat", 7, "b"), "7 and b and 7")
        with self.assertRaises(ValueError):
            i18n.i18n("t.repeat", 7, "b", "c")

    # An index gap raises even when the distinct count equals the arguments.
    def test_index_gap(self) -> None:
        with self.assertRaises(ValueError):
            i18n.i18n("t.gap", "a", "b")
        with self.assertRaises(ValueError):
            i18n.i18n("t.late", "a")

    # Braces that are not a placeholder pass through, also from an argument.
    def test_braces_literal(self) -> None:
        self.assertEqual(i18n.i18n("t.literal"), _TEST_STRINGS["t.literal"])
        self.assertEqual(i18n.i18n("t.mixed", "x"), "{a} x {}")
        self.assertEqual(i18n.i18n("t.two", "{1}", "b"), "{1} then b")


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
