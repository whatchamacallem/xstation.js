# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the lookup and the placeholder rule of the strings module on the
# texts of the real strings file, each found by its placeholders, then the
# real strings file and the names the sources look up in it, then the read at
# import, in scratch checkouts under build/ that hold the module as a link, so
# that its lines count as the module's own.

import glob, json, os, re, runpy, tempfile, unittest
from collections.abc import Callable
from internationalization import i18n
from typing import Any, cast

# The root of the checkout.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The file name of the strings module and its file in the checkout.
_MODULE_NAME = "internationalization.py"
_MODULE_PATH = os.path.join(_ROOT_PATH, "python", _MODULE_NAME)

# The strings file of the checkout.
_STRINGS_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# A call to `i18n` with a literal name, which the pattern captures.
_CALL_NAME = re.compile(r'\bi18n\(\s*"([^"]+)"')

# A placeholder, a decimal index with no leading zero in braces.
_PLACEHOLDER = re.compile(r"\{(0|[1-9][0-9]*)\}")

# A name the strings file lacks, under the strings module's own prefix.
_NAME_ABSENT = "internationalization.absent"


# Reads the real strings file, a JSON object.
def _strings_read() -> dict[str, object]:
    with open(_STRINGS_PATH, encoding="utf-8") as file:
        strings: dict[str, object] = json.load(file)
    return strings


# The indices of a text's placeholders, in the order they appear.
def _indices_list(text: str) -> list[int]:
    return [int(index) for index in _PLACEHOLDER.findall(text)]


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
    # The first name of the file whose text's indices pass the check, by name.
    def text_find(self, check: Callable[[list[int]], bool]) -> tuple[str, str]:
        for name, value in sorted(_strings_read().items()):
            text = cast(str, value)
            if check(_indices_list(text)):
                return name, text
        self.fail("no text of the strings file has the placeholders")

    # A name the table lacks raises, naming it.
    def test_name_missing(self) -> None:
        self.assertNotIn(_NAME_ABSENT, _strings_read())
        with self.assertRaises(KeyError) as caught:
            i18n(_NAME_ABSENT)
        self.assertEqual(caught.exception.args, (_NAME_ABSENT,))

    # Fewer arguments than placeholders raises.
    def test_arguments_few(self) -> None:
        name, _ = self.text_find(lambda found: sorted(found) == [0, 1])
        with self.assertRaises(ValueError) as caught:
            i18n(name, "a")
        message = f"{name}: placeholders [0, 1], arguments 1"
        self.assertEqual(caught.exception.args, (message,))
        name, _ = self.text_find(lambda found: found == [0])
        with self.assertRaises(ValueError) as caught:
            i18n(name)
        message = f"{name}: placeholders [0], arguments 0"
        self.assertEqual(caught.exception.args, (message,))

    # More arguments than placeholders raises.
    def test_arguments_many(self) -> None:
        name, _ = self.text_find(lambda found: found == [0])
        with self.assertRaises(ValueError) as caught:
            i18n(name, "a", "b")
        message = f"{name}: placeholders [0], arguments 2"
        self.assertEqual(caught.exception.args, (message,))
        name, _ = self.text_find(lambda found: not found)
        with self.assertRaises(ValueError) as caught:
            i18n(name, "a")
        message = f"{name}: placeholders [], arguments 1"
        self.assertEqual(caught.exception.args, (message,))

    # A repeated index counts once and each argument is made into text.
    def test_index_repeat(self) -> None:
        name, text = self.text_find(lambda found: len(found) > len(set(found)))
        count = len(set(_indices_list(text)))
        values = [7 * (index + 1) for index in range(count)]
        expected = text
        for index, value in enumerate(values):
            expected = expected.replace(f"{{{index}}}", str(value))
        self.assertEqual(i18n(name, *values), expected)
        with self.assertRaises(ValueError) as caught:
            i18n(name, *values, "c")
        message = (
            f"{name}: placeholders {list(range(count))}, arguments {count + 1}"
        )
        self.assertEqual(caught.exception.args, (message,))

    # Braces an argument holds pass through, not read as a placeholder.
    def test_braces_argument(self) -> None:
        name, text = self.text_find(lambda found: sorted(found) == [0, 1])
        expected = text.replace("{1}", "b").replace("{0}", "{1}")
        self.assertEqual(i18n(name, "{1}", "b"), expected)


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


# Tests the read at import, in a scratch checkout the module is linked into.
class TestImport(unittest.TestCase):
    # Makes the scratch checkout, which has the strings module as a link.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        os.mkdir(os.path.join(scratch, "i18n"))
        os.mkdir(os.path.join(scratch, "python"))
        self.strings_path = os.path.join(scratch, "i18n", "en-US.json")
        self.link_path = os.path.join(scratch, "python", _MODULE_NAME)
        os.symlink(_MODULE_PATH, self.link_path)

    # Writes the value as the strings file, then imports the module anew.
    def module_import(self, value: object) -> dict[str, Any]:
        with open(self.strings_path, "w", encoding="utf-8") as file:
            json.dump(value, file)
        return runpy.run_path(self.link_path)

    # Asserts the import refuses the value, naming the file and the reason.
    def import_fails(self, value: object, reason: str) -> None:
        with self.assertRaises(ValueError) as caught:
            self.module_import(value)
        message = f"{self.strings_path}: {reason}"
        self.assertEqual(caught.exception.args, (message,))

    # The file of the `i18n` directory beside the module's own is the one read.
    def test_file_beside(self) -> None:
        self.assertNotIn(_NAME_ABSENT, _strings_read())
        module = self.module_import({_NAME_ABSENT: "a {0}"})
        self.assertEqual(module["i18n"](_NAME_ABSENT, "b"), "a b")

    # A file that is not a JSON object is refused.
    def test_file_list(self) -> None:
        self.import_fails([_NAME_ABSENT], "not a JSON object")

    # A value that is not a string is refused, by its name.
    def test_value_number(self) -> None:
        self.import_fails(
            {_NAME_ABSENT: 1}, f"{_NAME_ABSENT!r} is not a string"
        )
