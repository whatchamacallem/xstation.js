# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the matches of the API text against the code on scratch checkouts in
# `build/`, by the real tsc: a whole checkout that agrees passes, and each kind
# of difference, written into a copy of it, raises and names its member. The
# real checkout is matched by `test_posix.py`.

import api_match, category, json, os, tempfile, unittest
from typing import cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch checkouts go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The base configuration of a scratch checkout's two projects.
_BASE_CONFIG = {
    "compilerOptions": {
        "module": "none",
        "noEmitOnError": True,
        "strict": True,
        "target": "ES2022",
    }
}

# The scratch API text of TypeScript.
_TYPESCRIPT_TEXT = """declare namespace shapes {
  interface Corner {
    x: number;
  }
  type Name = string;
  const limit: number;
  class Square {
    constructor(side: number);
    area_get(): number;
    side_get(): number;
  }
  function corner_make(x: number): Corner;
}
declare function shape_count(name: string): number;
"""

# The scratch code of that text, a private member and a private helper in it.
_TYPESCRIPT_CODE = """namespace shapes {
  export interface Corner {
    x: number;
  }
  export type Name = string;
  type Hidden = number;
  export const limit: number = 4;
  export class Square {
    private readonly side: number;
    #area: number;
    constructor(side: number) {
      this.side = side;
      this.#area = side * side;
    }
    area_get(): number {
      return this.#area;
    }
    side_get(): number {
      return this.side;
    }
  }
  export function corner_make(x: Hidden): Corner {
    return { x };
  }
}
function shape_count(name: string): number {
  return name.length;
}
"""

# The line types of a scratch checkout.
_LINES_TEXT = """declare namespace lines {
  interface RowPut {
    db: string;
    size?: number;
  }
  interface DbName {
    db: string;
  }
  interface RowDrop {}
}
"""

# The scratch stub of a module of handlers.
_STUB_TEXT = """from collections.abc import Callable
from typing import TypeAlias

import jslb

Reader: TypeAlias = Callable[[str], int]

class Point:
    x: int
    def __init__(self, x: int) -> None: ...
    def x_get(self) -> int: ...

def row_put(line: jslb.Object, *, db: str, size: int = ...) -> None: ...
def db_create(line: jslb.Object, *, db: str) -> None: ...
def row_drop(line: jslb.Object) -> None: ...
def row_any(line: jslb.Object, **message: object) -> None: ...
def handlers_register() -> None: ...
"""

# The module of that stub.
_MODULE_TEXT = """import dispatch, jslb
from collections.abc import Callable
from typing import TypeAlias

_LIMIT = 4

Reader: TypeAlias = Callable[[str], int]

class Point:
    def __init__(self, x: int) -> None:
        self.x = x
        self._y = x

    def x_get(self) -> int:
        return self.x

def row_put(line: jslb.Object, *, db: str, size: int = 0) -> None:
    pass

def db_create(line: jslb.Object, *, db: str) -> None:
    pass

def row_drop(line: jslb.Object) -> None:
    pass

def row_any(line: jslb.Object, **message: object) -> None:
    pass

def _row_helper() -> None:
    pass

def handlers_register() -> None:
    dispatch.handler_register("row.put", 0, row_put)
    dispatch.handler_register("db.create", 0, db_create)
    dispatch.handler_register("row.drop", 0, row_drop)
    dispatch.handler_register("row.any", 0, row_any)
"""

# The name of the scratch module, a module of handlers.
_MODULE_NAME = "engine_rows"

# What a difference of names says.
_TEXT_ALONE = "the API text holds it and the code lacks it"
_CODE_ALONE = "the code holds it and the API text lacks it"

# The errors of a check where every member differs: seven pairs, both ways.
_TYPE_ERRORS = 14

# Changes of the stub that each make one signature differ from the module.
_SIGNATURE_EDITS = (
    ("def x_get(self) -> int", "def x_get(self) -> str"),
    ("row_drop(line: jslb.Object)", "row_drop(other: jslb.Object)"),
    ("size: int = ...", "size: str = ..."),
    ("size: int = ...", "size: int"),
    ("*, db: str, size", "db: str, size"),
    ("    def x_get", "    @staticmethod\n    def x_get"),
)

# The list of a module's public names, its helpers left out.
_ALL_TEXT = """__all__ = [
    "Point",
    "Reader",
    "db_create",
    "handlers_register",
    "row_any",
    "row_drop",
    "row_put",
]
"""

# The tools of a scratch checkout, as `tools/list` returns them.
_TOOLS = [{"name": "row_read", "description": "Reads a row."}]

# The text of a scratch checkout's schema.
_SCHEMA_TEXT = """-- The rows.
CREATE TABLE _row (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL -- what it holds
) STRICT;

-- The tags.
CREATE TABLE _tag (
    name TEXT
);
"""

# Those statements, as the gold holds them.
_SCHEMA_GOLD = [
    "CREATE TABLE _row ( key TEXT PRIMARY KEY, value TEXT NOT NULL ) STRICT",
    "CREATE TABLE _tag ( name TEXT )",
]


# The gold of a scratch checkout, which repeats its tools and its schema.
_TOOLS_GOLD = "ts/test_setting_test_tools_browser.json"
_SCHEMA_GOLD_NAME = "ts/test_setting_test_substrate_store.json"


# Writes a file of a scratch checkout, its folders with it.
def file_write(root: str, name: str, text: str) -> None:
    path = os.path.join(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


# Writes a whole scratch checkout, the texts given.
def checkout_write(
    root: str,
    typescript_text: str = _TYPESCRIPT_TEXT,
    typescript_code: str = _TYPESCRIPT_CODE,
    stub: str = _STUB_TEXT,
    module: str = _MODULE_TEXT,
    lines: str = _LINES_TEXT,
) -> None:
    file_write(root, "ts/tsconfig.json", json.dumps(_BASE_CONFIG))
    api_config = {
        "extends": "./tsconfig.json",
        "compilerOptions": {"noEmit": True},
        "files": ["../API/ts/lines.d.ts", "../API/ts/shapes.d.ts"],
    }
    file_write(root, "ts/tsconfig.api.json", json.dumps(api_config))
    code_config = {
        "extends": "./tsconfig.json",
        "compilerOptions": {"outFile": "../build/ts/test.js"},
        "files": ["../API/ts/lines.d.ts", "shapes.ts"],
    }
    file_write(root, "ts/tsconfig.test.json", json.dumps(code_config))
    file_write(root, "API/ts/lines.d.ts", lines)
    file_write(root, "API/ts/shapes.d.ts", typescript_text)
    file_write(root, "ts/shapes.ts", typescript_code)
    file_write(root, f"API/python/{_MODULE_NAME}.pyi", stub)
    file_write(root, f"python/{_MODULE_NAME}.py", module)
    file_write(root, "python/test_rows.py", "")
    tools = {"browser": {"result": {"tools": _TOOLS}}}
    file_write(root, "API/mcp/tools.json", json.dumps(tools))
    file_write(root, "API/sql/substrate.sql", _SCHEMA_TEXT)
    file_write(root, _TOOLS_GOLD, json.dumps({"recorded_tools": _TOOLS}))
    gold = {"schema_statements": _SCHEMA_GOLD}
    file_write(root, _SCHEMA_GOLD_NAME, json.dumps(gold))


class ScratchCase(unittest.TestCase):
    # Makes a scratch directory in the checkout's `build/`.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        self.root = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )

    # Checks that the match of the stub and the module raises the text.
    def stub_refused(self, stub: str, module: str, text: str) -> None:
        checkout_write(self.root, stub=stub, module=module)
        with self.assertRaises(RuntimeError) as caught:
            api_match.python_match(
                os.path.join(self.root, "API", "python"),
                os.path.join(self.root, "python"),
            )
        self.assertIn(text, str(caught.exception))


# A whole checkout.
@unittest.skipUnless(
    category.disabled_taken(),
    "disabled: two real compiler runs each, 1.6 s to 1.9 s",
)
class TestCheckout(ScratchCase):
    # A checkout whose text and code agree passes, its old intermediates gone.
    def test_checkout_passed(self) -> None:
        checkout_write(self.root)
        file_write(self.root, "build/api_match/stale.d.ts", "")
        stale = os.path.join(self.root, "build", "api_match", "stale.d.ts")
        api_match.text_match(self.root)
        self.assertFalse(os.path.exists(stale))

    # A type the text and the code disagree on fails the compile, each named.
    def test_types_refused(self) -> None:
        text = (
            _TYPESCRIPT_TEXT.replace("x: number;", "x: string;")
            .replace("side_get(): number", "side_get(): string")
            .replace("Name = string", "Name = number")
            .replace("limit: number", "limit: string")
            .replace("corner_make(x: number)", "corner_make(x: string)")
            .replace("shape_count(name: string)", "shape_count(name: number)")
        )
        checkout_write(self.root, typescript_text=text)
        with self.assertRaises(RuntimeError) as caught:
            api_match.text_match(self.root)
        self.assertIn("shape_count: ", str(caught.exception))
        cause = caught.exception.__cause__
        self.assertIsInstance(cause, RuntimeError)
        output = str(cast(RuntimeError, cause).__cause__)
        self.assertEqual(output.count("check.ts("), _TYPE_ERRORS)

    # A fault of the text itself keeps tsc's own failure.
    def test_text_broken(self) -> None:
        text = _TYPESCRIPT_TEXT.replace("Name = string", "Name = Absent")
        checkout_write(self.root, typescript_text=text)
        with self.assertRaises(RuntimeError) as caught:
            api_match.text_match(self.root)
        self.assertIn("tsc exited", str(caught.exception))
        self.assertIn("Absent", str(caught.exception.__cause__))

    # A stub that differs from its module stops the whole match.
    def test_stub_refused(self) -> None:
        stub = _STUB_TEXT.replace("def x_get", "def y_get")
        checkout_write(self.root, stub=stub)
        with self.assertRaises(RuntimeError) as caught:
            api_match.text_match(self.root)
        self.assertIn(f"{_MODULE_NAME}.Point.x_get", str(caught.exception))

    # A handler that differs from its payload stops the whole match.
    def test_handler_refused(self) -> None:
        lines = _LINES_TEXT.replace("    db: string;\n    size", "    size")
        checkout_write(self.root, lines=lines)
        with self.assertRaises(RuntimeError) as caught:
            api_match.text_match(self.root)
        self.assertIn("row.put", str(caught.exception))


# The members of a text and of what tsc emits.
class TestMembers(unittest.TestCase):
    # Each kind of member of a namespace, and a function outside any.
    def test_members_read(self) -> None:
        self.assertEqual(
            api_match.members_read(_TYPESCRIPT_TEXT, 2),
            {
                "": {"shape_count": "function"},
                "shapes": {
                    "Corner": "interface",
                    "Name": "type",
                    "Square": "class",
                    "corner_make": "function",
                    "limit": "const",
                },
            },
        )

    # A namespace with `export {};` holds only what says `export`.
    def test_exports_only(self) -> None:
        text = (
            "declare namespace one {\n"
            "    type Hidden = string;\n"
            "    export function shown_get(): Hidden;\n"
            "    export {};\n"
            "}\n"
        )
        self.assertEqual(
            api_match.members_read(text, 4),
            {"": {}, "one": {"shown_get": "function"}},
        )

    # A member's own fields are not members.
    def test_nested_skipped(self) -> None:
        text = (
            "declare namespace one {\n"
            "  interface Outer {\n"
            "    type: string;\n"
            "    const: number;\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            api_match.members_read(text, 2),
            {"": {}, "one": {"Outer": "interface"}},
        )


# The names of the two sides.
class TestNames(unittest.TestCase):
    # Checks that the two sides raise the text.
    def names_refused(
        self,
        text: dict[str, dict[str, str]],
        code: dict[str, dict[str, str]],
        expected: str,
    ) -> None:
        with self.assertRaises(RuntimeError) as caught:
            api_match.names_match(text, code)
        self.assertEqual(str(caught.exception), expected)

    # Equal names pass, `function` and `const` being both a value.
    def test_names_passed(self) -> None:
        api_match.names_match(
            {"one": {"a_make": "function"}},
            {"one": {"a_make": "const"}},
        )

    # Namespaces with one side by design pass.
    def test_sides_passed(self) -> None:
        api_match.names_match(
            {"": {}, "lines": {"Line": "interface"}},
            {
                "": {"Terminal": "class"},
                "failing_block": {"a_make": "function"},
                "test_one": {"Case": "class"},
            },
        )

    # A namespace the text holds and the code lacks.
    def test_namespace_text(self) -> None:
        self.names_refused({"one": {}}, {}, f"one: {_TEXT_ALONE}")

    # A namespace the code holds and the text lacks.
    def test_namespace_code(self) -> None:
        self.names_refused({}, {"one": {}}, f"one: {_CODE_ALONE}")

    # A member the text holds and the code lacks.
    def test_member_text(self) -> None:
        self.names_refused(
            {"one": {"a_make": "function"}},
            {"one": {}},
            f"one.a_make: {_TEXT_ALONE}",
        )

    # A member the code exports and the text lacks.
    def test_member_code(self) -> None:
        self.names_refused(
            {"one": {}},
            {"one": {"a_make": "function"}},
            f"one.a_make: {_CODE_ALONE}",
        )

    # A class in the code is no interface in the text.
    def test_kind_refused(self) -> None:
        self.names_refused(
            {"one": {"Thing": "interface"}},
            {"one": {"Thing": "class"}},
            "one.Thing: interface in the API text, class in the code",
        )


# The stubs of a directory against its modules.
class TestStubs(ScratchCase):
    # Checks that the stub and the module pass.
    def stub_passed(self, stub: str, module: str) -> None:
        checkout_write(self.root, stub=stub, module=module)
        api_match.python_match(
            os.path.join(self.root, "API", "python"),
            os.path.join(self.root, "python"),
        )

    # A stub with no module.
    def test_stub_alone(self) -> None:
        checkout_write(self.root)
        file_write(self.root, "API/python/other_one.pyi", "")
        with self.assertRaises(RuntimeError) as caught:
            api_match.python_match(
                os.path.join(self.root, "API", "python"),
                os.path.join(self.root, "python"),
            )
        self.assertEqual(str(caught.exception), f"other_one: {_TEXT_ALONE}")

    # A module with no stub.
    def test_module_alone(self) -> None:
        checkout_write(self.root)
        file_write(self.root, "python/other_one.py", "")
        with self.assertRaises(RuntimeError) as caught:
            api_match.python_match(
                os.path.join(self.root, "API", "python"),
                os.path.join(self.root, "python"),
            )
        self.assertEqual(str(caught.exception), f"other_one: {_CODE_ALONE}")

    # The programs with no stub and the test modules pass.
    def test_absent_passed(self) -> None:
        checkout_write(self.root)
        file_write(self.root, "python/echo_loop.py", "")
        file_write(self.root, "python/test_rows.py", "")
        file_write(self.root, "python/notes.txt", "")
        file_write(self.root, "API/python/notes.txt", "")
        api_match.python_match(
            os.path.join(self.root, "API", "python"),
            os.path.join(self.root, "python"),
        )

    # A public function the stub holds and the module lacks.
    def test_function_text(self) -> None:
        self.stub_refused(
            _STUB_TEXT + "def row_gone() -> None: ...\n",
            _MODULE_TEXT,
            f"{_MODULE_NAME}.row_gone: {_TEXT_ALONE}",
        )

    # A public function the module holds and the stub lacks.
    def test_function_code(self) -> None:
        self.stub_refused(
            _STUB_TEXT,
            _MODULE_TEXT + "def row_new() -> None:\n    pass\n",
            f"{_MODULE_NAME}.row_new: {_CODE_ALONE}",
        )

    # The name, annotation, return, default and decorator of a function.
    def test_signature_refused(self) -> None:
        for old, new in _SIGNATURE_EDITS:
            with self.subTest(new):
                self.stub_refused(
                    _STUB_TEXT.replace(old, new),
                    _MODULE_TEXT,
                    "against",
                )

    # Two default values are the same statement, as a stub writes `...`.
    def test_default_passed(self) -> None:
        self.stub_passed(
            _STUB_TEXT.replace("size: int = ...", "size: int = 7"),
            _MODULE_TEXT,
        )

    # A method and a class field are compared both ways.
    def test_class_refused(self) -> None:
        self.stub_refused(
            _STUB_TEXT,
            _MODULE_TEXT.replace(
                "    def x_get(self)",
                "    def x_set(self) -> None:\n        pass\n\n"
                "    def x_get(self)",
            ),
            f"{_MODULE_NAME}.Point.x_set: {_CODE_ALONE}",
        )

    # A stub's `class Name: ...` leaves the class's members to the module.
    def test_opaque_passed(self) -> None:
        self.stub_passed(
            _STUB_TEXT + "class Inner: ...\n",
            _MODULE_TEXT + "class Inner:\n    def x_get(self) -> int:\n"
            "        return 1\n",
        )

    # An attribute the stub names must be assigned.
    def test_attribute_text(self) -> None:
        self.stub_refused(
            _STUB_TEXT.replace("    x: int\n", "    x: int\n    y: int\n"),
            _MODULE_TEXT,
            f"{_MODULE_NAME}.Point.y: {_TEXT_ALONE}",
        )

    # An attribute the module assigns need not be in the stub.
    def test_attribute_code(self) -> None:
        self.stub_passed(_STUB_TEXT.replace("    x: int\n", ""), _MODULE_TEXT)

    # An annotation of an attribute must agree.
    def test_attribute_annotated(self) -> None:
        self.stub_refused(
            _STUB_TEXT,
            _MODULE_TEXT.replace("self.x = x", "self.x: str = x"),
            f"{_MODULE_NAME}.Point.x: 'int' against 'str'",
        )

    # The bases of a class must agree.
    def test_bases_refused(self) -> None:
        self.stub_refused(
            _STUB_TEXT.replace("class Point:", "class Point(int):"),
            _MODULE_TEXT,
            "against",
        )

    # An alias's value must agree.
    def test_alias_refused(self) -> None:
        self.stub_refused(
            _STUB_TEXT.replace("[[str], int]", "[[str], str]"),
            _MODULE_TEXT,
            f"{_MODULE_NAME}.Reader",
        )

    # A name a line assigns with no annotation states nothing.
    def test_assigned_passed(self) -> None:
        self.stub_passed(
            _STUB_TEXT + "LIMIT: int\n",
            _MODULE_TEXT + "LIMIT = 4\n",
        )

    # A module's `__all__` is its public names, and a helper may stay out.
    def test_exports_passed(self) -> None:
        self.stub_passed(
            _STUB_TEXT,
            _MODULE_TEXT + "def row_helper() -> None:\n    pass\n" + _ALL_TEXT,
        )

    # A name of `__all__` the stub lacks fails.
    def test_exports_refused(self) -> None:
        self.stub_refused(
            _STUB_TEXT.replace("def row_any", "def row_many"),
            _MODULE_TEXT + _ALL_TEXT,
            f"{_MODULE_NAME}.row_any: {_CODE_ALONE}",
        )


# The handlers of a directory against the line types.
class TestHandlers(ScratchCase):
    # Checks that the line types and the module raise the text.
    def handlers_refused(self, lines: str, module: str, text: str) -> None:
        file_write(self.root, "API/ts/lines.d.ts", lines)
        file_write(self.root, f"python/{_MODULE_NAME}.py", module)
        file_write(self.root, "python/page_other.py", "")
        with self.assertRaises(RuntimeError) as caught:
            api_match.handlers_match(
                os.path.join(self.root, "API", "ts", "lines.d.ts"),
                os.path.join(self.root, "python"),
            )
        self.assertIn(text, str(caught.exception))

    # A payload field the handler does not take.
    def test_field_text(self) -> None:
        self.handlers_refused(
            _LINES_TEXT.replace("size?:", "weight: number;\n    size?:"),
            _MODULE_TEXT,
            "row.put",
        )

    # A keyword that is no field of the payload.
    def test_field_code(self) -> None:
        self.handlers_refused(
            _LINES_TEXT,
            _MODULE_TEXT.replace(
                "def row_drop(line: jslb.Object)",
                "def row_drop(line: jslb.Object, *, db: str)",
            ),
            "row.drop",
        )

    # A field that may be left out takes a default.
    def test_default_refused(self) -> None:
        self.handlers_refused(
            _LINES_TEXT.replace("size?:", "size:"),
            _MODULE_TEXT,
            "row.put",
        )

    # A line type with no payload in the text.
    def test_payload_absent(self) -> None:
        self.handlers_refused(
            _LINES_TEXT.replace("RowDrop", "RowGone"),
            _MODULE_TEXT,
            "the API text has no RowDrop",
        )

    # The spelled name of a payload, its exceptions and its word marks.
    def test_payload_named(self) -> None:
        self.assertEqual(api_match.payload_name("kv.put"), "KvPut")
        self.assertEqual(api_match.payload_name("db.drop"), "DbName")
        self.assertEqual(api_match.payload_name("a.b_c"), "ABC")


# The gold of the browser's suites against the text.
class TestGold(ScratchCase):
    # Checks that the gold file holding the value raises the text.
    def gold_refused(self, name: str, value: object, text: str) -> None:
        checkout_write(self.root)
        file_write(self.root, name, json.dumps(value))
        with self.assertRaises(RuntimeError) as caught:
            api_match.gold_match(self.root)
        self.assertIn(text, str(caught.exception))

    # A gold equal to the text passes, comments and white space aside.
    def test_gold_passed(self) -> None:
        checkout_write(self.root)
        api_match.gold_match(self.root)

    # Tools the text does not hold.
    def test_tools_refused(self) -> None:
        self.gold_refused(
            _TOOLS_GOLD, {"recorded_tools": []}, "recorded_tools"
        )

    # Statements the text does not hold.
    def test_schema_refused(self) -> None:
        self.gold_refused(
            _SCHEMA_GOLD_NAME,
            {"schema_statements": _SCHEMA_GOLD[:1]},
            "schema_statements",
        )
