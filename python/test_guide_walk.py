# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests guide_walk.table_build, by which a guide's table.json becomes the
# scripted table the port takes, on a scratch guide that each test writes in
# build/ from the gold's source and files, then on the three guides of
# python/guides/. The gold holds the scratch table's source and the whole table
# it must build, its exit expanded at the node that asks. guide_main serves a
# root and drives the page, so it runs in the guide programs alone, and this
# suite counts for no module.

import copy, guide_walk, harness, json, os, tempfile, unittest
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch guides go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The directory of the guides, each in a directory of its own.
_GUIDES_PATH = os.path.join(_ROOT_PATH, "python", "guides")

# The id of this module's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_guide_walk"

# The file of a guide that holds the source of its table.
_TABLE_NAME = "table.json"

# The newline that ends each text file of a guide.
_TEXT_END = "\n"

# The scratch guide's file of its question, and the member that names a file.
_ASK_FILE = "ask.txt"
_TEXT_KEY = "$text"

# The scratch guide's first node, its node that asks, and the one before it.
_START_NODE = "begin"
_ASKING_NODE = "choose"
_BUILT_NODE = "built"

# The input of the first node whose reply calls the script.
_BUILD_INPUT = "build"

# The name a node of the exit of the asking node takes.
_PAUSED_NODE = "choose~paused"


# A deep copy of a value of this module's gold, which a test may change.
def gold_value(name: str) -> Any:
    return copy.deepcopy(harness.gold_get(f"{_GOLD_ID}.{name}"))


# The table of a scratch guide, built from its source and files in `build/`.
class TestScratch(unittest.TestCase):
    # Makes the scratch directory and takes the gold's source and files.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.table: dict[str, Any] = gold_value("table")
        self.files: dict[str, str] = gold_value("files")

    # Writes the source and the files as a guide, then builds its table.
    def guide_build(self) -> dict[str, Any]:
        path = os.path.join(self.scratch, _TABLE_NAME)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.table, file)
        for name, text in self.files.items():
            path = os.path.join(self.scratch, name)
            with open(path, "w", encoding="utf-8", newline="") as file:
                file.write(text)
        return guide_walk.table_build(self.scratch)

    # The build is refused with a text that holds each fragment.
    def refusal_check(self, *fragments: str) -> None:
        with self.assertRaises(ValueError) as caught:
            self.guide_build()
        for fragment in fragments:
            self.assertIn(fragment, str(caught.exception))

    # The question's file, its text less the newline that ends it.
    def ask_text(self) -> str:
        return self.files[_ASK_FILE].removesuffix(_TEXT_END)

    # Each object of `$text` alone is its file's text, less the newline.
    def test_text_replaced(self) -> None:
        built = self.guide_build()
        content = built["nodes"][_BUILT_NODE]["after_tools"]["content"]
        self.assertEqual(content, self.ask_text())
        self.assertNotIn(_TEXT_KEY, json.dumps(built))

    # A file that does not end in a newline is refused.
    def test_newline_refused(self) -> None:
        self.files[_ASK_FILE] = self.ask_text()
        self.refusal_check(f"{_ASK_FILE} does not end in a newline")

    # An object of `$text` that holds another member too is refused.
    def test_member_refused(self) -> None:
        ask = {_TEXT_KEY: _ASK_FILE, "note": _ASK_FILE}
        self.table["nodes"][_ASKING_NODE]["ask"] = ask
        self.refusal_check(f"holds other members: {sorted(ask)}")

    # Each call's arguments become their compact JSON text.
    def test_arguments_text(self) -> None:
        built = self.guide_build()
        reply = built["nodes"][_START_NODE]["replies"][_BUILD_INPUT]
        arguments = reply["tool_calls"][0]["arguments"]
        self.assertEqual(arguments, gold_value("arguments_text"))

    # A node that asks takes `puzzled` then its question as its other reply.
    def test_otherwise_built(self) -> None:
        built = self.guide_build()
        content = f"{self.table['puzzled']} {self.ask_text()}"
        self.assertEqual(
            built["nodes"][_ASKING_NODE]["otherwise"],
            {"content": content, "next": _ASKING_NODE},
        )

    # A node that holds both a question and its own other reply is refused.
    def test_both_refused(self) -> None:
        nodes = self.table["nodes"]
        nodes[_ASKING_NODE]["otherwise"] = nodes[_START_NODE]["otherwise"]
        self.refusal_check(f"the node {_ASKING_NODE} of", "holds both")

    # A node with replies and neither a question nor another reply is refused.
    def test_neither_refused(self) -> None:
        del self.table["nodes"][_START_NODE]["otherwise"]
        self.refusal_check(f"the node {_START_NODE} of", "neither")

    # The exit is a reply of the node that asks and three nodes of its own.
    def test_exit_expanded(self) -> None:
        self.assertEqual(self.guide_build(), gold_value("built"))

    # A node that asks and holds the exit's input or resume is refused.
    def test_input_refused(self) -> None:
        for member in ("input", "resume"):
            with self.subTest(member=member):
                self.table = gold_value("table")
                node = self.table["nodes"][_ASKING_NODE]
                key: str = self.table["exit"][member]
                node["replies"][key] = node["replies"]["east"]
                self.refusal_check(f"the node {_ASKING_NODE} of", repr(key))

    # A node named as a node of an exit is refused where that exit is added.
    def test_name_refused(self) -> None:
        self.table["nodes"][_PAUSED_NODE] = {"replies": {}}
        self.refusal_check(f"the node {_PAUSED_NODE} of", "takes a name")

    # A table with no exit gains no reply and no node.
    def test_exit_absent(self) -> None:
        del self.table["exit"]
        built = self.guide_build()
        nodes: dict[str, Any] = self.table["nodes"]
        self.assertEqual(list(built["nodes"]), list(nodes))
        replies = built["nodes"][_ASKING_NODE]["replies"]
        self.assertEqual(list(replies), list(nodes[_ASKING_NODE]["replies"]))


# The table of each guide of python/guides/.
class TestGuides(unittest.TestCase):
    # Each guide's table builds, its start one of its nodes.
    def test_guides_built(self) -> None:
        names: list[str] = gold_value("guides")
        for name in names:
            with self.subTest(guide=name):
                directory = os.path.join(_GUIDES_PATH, name)
                built = guide_walk.table_build(directory)
                self.assertIn(built["start"], built["nodes"])
