# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests guide_walk.table_build, by which a guide's table.json becomes the
# scripted table the port takes, on a scratch guide that each test writes in
# build/ from the gold's source and files, the core's files in `ecs` beside
# it, then on the three guides of python/guides/. The gold holds the scratch
# table's source and the whole table it must build: its `$text` and `$ecs`
# objects the texts of their files, and its exit's lists of calls expanded at
# the node that asks. Each source the builder refuses is tested by the text of
# its refusal. guide_main serves a root and drives the page, so it runs in the
# guide programs alone, and this suite counts for no module.

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

# The scratch guide's directory, and that of the core's files beside it.
_GUIDE_NAME = "scratch"
_ECS_NAME = "ecs"

# The scratch guide's file of its question, and the member that names a file.
_ASK_FILE = "ask.txt"
_TEXT_KEY = "$text"

# The core's file of the step, and the member that names a file of the core.
_STEP_FILE = "step.js"
_ECS_KEY = "$ecs"

# The scratch guide's first node, its node that asks, and the one before it.
_START_NODE = "begin"
_ASKING_NODE = "choose"
_BUILT_NODE = "built"

# The input of the first node, whose reply puts the scripts and spawns.
_BUILD_INPUT = "build"

# The name a node of the exit of the asking node takes.
_PAUSED_NODE = "choose~paused"

# A second node that asks, made as a copy of the first.
_SECOND_NODE = "again"

# The members of the exit that list calls.
_EXIT_CALLS = ("calls", "resume_calls")


# A deep copy of a value of this module's gold, which a test may change.
def gold_value(name: str) -> Any:
    return copy.deepcopy(harness.gold_get(f"{_GOLD_ID}.{name}"))


# The table of a scratch guide, built from its source and files in `build/`.
class TestScratch(unittest.TestCase):
    # Makes the scratch directory and takes the gold's source and files.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.guide = os.path.join(scratch, _GUIDE_NAME)
        self.core = os.path.join(scratch, _ECS_NAME)
        self.table: dict[str, Any] = gold_value("table")
        self.files: dict[str, str] = gold_value("files")
        self.ecs_files: dict[str, str] = gold_value("ecs_files")

    # Writes the source and the files as a guide and its core, then builds.
    def guide_build(self) -> dict[str, Any]:
        os.makedirs(self.guide, exist_ok=True)
        path = os.path.join(self.guide, _TABLE_NAME)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.table, file)
        held = ((self.guide, self.files), (self.core, self.ecs_files))
        for folder, files in held:
            os.makedirs(folder, exist_ok=True)
            for name, text in files.items():
                path = os.path.join(folder, name)
                with open(path, "w", encoding="utf-8", newline="") as file:
                    file.write(text)
        return guide_walk.table_build(self.guide)

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

    # Each object of `$ecs` alone is its core file's text, less the newline.
    def test_ecs_replaced(self) -> None:
        built = self.guide_build()
        reply = built["nodes"][_START_NODE]["replies"][_BUILD_INPUT]
        arguments = json.loads(reply["tool_calls"][0]["arguments"])
        text = self.ecs_files[_STEP_FILE].removesuffix(_TEXT_END)
        self.assertEqual(arguments["text"], text)
        self.assertNotIn(_ECS_KEY, json.dumps(built))

    # A file of the guide that does not end in a newline is refused.
    def test_newline_refused(self) -> None:
        self.files[_ASK_FILE] = self.ask_text()
        path = os.path.join(self.guide, _ASK_FILE)
        self.refusal_check(f"the file {path} does not end in a newline")

    # A file of the core that does not end in a newline is refused.
    def test_ecs_newline_refused(self) -> None:
        text = self.ecs_files[_STEP_FILE]
        self.ecs_files[_STEP_FILE] = text.removesuffix(_TEXT_END)
        path = os.path.join(self.core, _STEP_FILE)
        self.refusal_check(f"the file {path} does not end in a newline")

    # An object of `$text` or `$ecs` that holds another member too is refused.
    def test_member_refused(self) -> None:
        folders = {_TEXT_KEY: self.guide, _ECS_KEY: self.core}
        objects = (
            (_TEXT_KEY, {_TEXT_KEY: _ASK_FILE, "note": _ASK_FILE}),
            (_ECS_KEY, {_ECS_KEY: _STEP_FILE, "note": _STEP_FILE}),
            (_TEXT_KEY, {_TEXT_KEY: _ASK_FILE, _ECS_KEY: _STEP_FILE}),
        )
        for key, ask in objects:
            with self.subTest(ask=ask):
                self.table = gold_value("table")
                self.table["nodes"][_ASKING_NODE]["ask"] = ask
                self.refusal_check(
                    f"an object of {key} in {folders[key]} holds other"
                    f" members: {sorted(ask)}"
                )

    # Each call's arguments become their compact JSON text.
    def test_arguments_text(self) -> None:
        built = self.guide_build()
        reply = built["nodes"][_START_NODE]["replies"][_BUILD_INPUT]
        arguments = reply["tool_calls"][-1]["arguments"]
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

    # Each node that asks calls its own copies of the exit's lists of calls.
    def test_exit_copied(self) -> None:
        nodes = self.table["nodes"]
        nodes[_SECOND_NODE] = copy.deepcopy(nodes[_ASKING_NODE])
        built = self.guide_build()["nodes"]
        due = gold_value("built")["nodes"]
        entry: str = self.table["exit"]["input"]
        back: str = self.table["exit"]["resume"]
        calls = due[_ASKING_NODE]["replies"][entry]["tool_calls"]
        resume_calls = due[_PAUSED_NODE]["replies"][back]["tool_calls"]
        for name in (_ASKING_NODE, _SECOND_NODE):
            with self.subTest(node=name):
                replies = built[name]["replies"]
                self.assertEqual(replies[entry]["tool_calls"], calls)
                paused = built[f"{name}~paused"]["replies"]
                self.assertEqual(paused[back]["tool_calls"], resume_calls)

    # An exit of the old form, a call in place of each list, is refused.
    def test_exit_old_refused(self) -> None:
        for member in _EXIT_CALLS:
            with self.subTest(member=member):
                self.table = gold_value("table")
                way_out: dict[str, Any] = self.table["exit"]
                way_out[member.removesuffix("s")] = way_out.pop(member)[0]
                self.refusal_check(
                    "the exit of", f"holds the members {sorted(way_out)}"
                )

    # An exit whose calls or resume calls are no list of calls is refused.
    def test_calls_refused(self) -> None:
        for member in _EXIT_CALLS:
            first = gold_value("table")["exit"][member][0]
            values: list[Any] = [[], first]
            for broken in values:
                with self.subTest(member=member, broken=broken):
                    self.table = gold_value("table")
                    self.table["exit"][member] = broken
                    self.refusal_check(
                        f"the exit's {member} of",
                        f"is {broken!r}, where it lists one call or more",
                    )

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
