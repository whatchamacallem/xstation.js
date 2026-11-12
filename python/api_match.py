# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Proves the text of API/ against the code. API/python/api_match.pyi holds the
# contract. The text and the code are read, never imported, so that a module
# with a fault at import fails its own suite and not this one. text_match
# compiles only when a source of ts/ or API/ts/ is no older than the stamp
# the last passing TypeScript match left, by page_build.compile_timed.

import ast, copy, json, os, re, shutil, sys
from collections.abc import Iterable, Iterator
from typing import Any, NamedTuple, NoReturn

# The public names of this module, as its stub declares them.
__all__ = [
    "gold_match",
    "handlers_match",
    "members_read",
    "names_match",
    "payload_name",
    "python_match",
    "text_match",
    "typescript_match",
]

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bytecode of the modules imported here goes in build/.
sys.pycache_prefix = os.path.join(_ROOT_PATH, "build", "pycache")

# The paths of a checkout, under its top directory.
_API_CONFIG = os.path.join("ts", "tsconfig.api.json")
_CODE_CONFIG = os.path.join("ts", "tsconfig.test.json")
_MATCH_PATH = os.path.join("build", "api_match")
_API_PYTHON_PATH = os.path.join("API", "python")
_CODE_PYTHON_PATH = "python"
_LINES_PATH = os.path.join("API", "ts", "lines.d.ts")
_TOOLS_PATH = os.path.join("API", "mcp", "tools.json")
_SCHEMA_PATH = os.path.join("API", "sql", "substrate.sql")
_TOOLS_GOLD = os.path.join("ts", "test_setting_test_tools_browser.json")
_SCHEMA_GOLD = os.path.join("ts", "test_setting_test_substrate_store.json")

# The keys of the gold that repeat the text.
_TOOLS_KEY = "recorded_tools"
_SCHEMA_KEY = "schema_statements"

# The namespace the code's declarations move under.
_CODE_NAMESPACE = "code"

# The file of the check, which assigns each member both ways.
_CHECK_NAME = "check.ts"

# The stamp a passing TypeScript match leaves, dated to the match's start.
_PASSED_NAME = "passed"

# The lines of one pair in the check, and tsc's first error in it.
_PAIR_LINES = 4
_CHECK_ERROR = re.compile(r"check\.ts\((\d+),")

# What a difference of types says.
_TYPES_DIFFER = "the API text and the code differ, see the cause"

# The name of the file tsc emits the declarations beside.
_EMIT_NAME = "code.js"

# The file tsc emits.
_EMITTED_NAME = "code.d.ts"

# The configuration of the check.
_MATCH_CONFIG_NAME = "tsconfig.json"

# The file of the code's declarations under their namespace.
_WRAPPED_NAME = "wrapped.d.ts"

# A namespace with text and no code, as the code is typed by it.
_TEXT_ONLY = frozenset({"lines"})

# A namespace with code and no text: the block that fails by design.
_CODE_ONLY = frozenset({"failing_block"})

# The start of the name of a test's namespace or module, which has no text.
_TEST_PREFIX = "test_"

# The indent of a member of a namespace, in the text and as tsc emits it.
_TEXT_INDENT = 2
_EMIT_INDENT = 4

# The kinds of member that declare a type, and those that declare a value.
_TYPE_KINDS = frozenset({"class", "interface", "type"})
_VALUE_KINDS = frozenset({"class", "const", "function"})

# The options that make tsc emit the declarations alone, then the emitted file.
_EMIT_OPTIONS = (
    "--declaration",
    "--emitDeclarationOnly",
    "--removeComments",
    "--outFile",
)

# The start of a namespace, the line that ends it, and the scope outside them.
_NAMESPACE_START = re.compile(r"(?:declare )?namespace (\w+) \{")
_NAMESPACE_END = "}"
_TOP_SCOPE = ""

# The line by which a namespace says that only `export` members are public.
_EXPORTS_ONLY = "export {};"

# A private member as tsc emits it, which the text never declares.
_PRIVATE_MEMBER = re.compile(r"\s+(?:private (?:readonly )?\w+|#private);")

# The modifiers and keyword of a declaration, then its name.
_DECLARATION = re.compile(
    r"(export )?(?:declare )?(?:abstract )?"
    r"(class|const|function|interface|type) (\w+)"
)

# The modules with no stub: the programs the rules name and the test fixture.
_STUB_ABSENT = frozenset(
    {
        "echo_loop",
        "failing_suite",
        "reformat",
        "stall_loop",
        "tap_loop",
        "vectors_make",
        "xsjs_screenshot",
        "xsjs_screenshot_posix",
        "xsjs_screenshot_wsl",
    }
)

# What a difference of names says.
_TEXT_ALONE = "the API text holds it and the code lacks it"
_CODE_ALONE = "the code holds it and the API text lacks it"

# The name of a module's list of its public names.
_EXPORTS_NAME = "__all__"

# The extension of a stub and that of a module.
_STUB_EXTENSION = ".pyi"
_MODULE_EXTENSION = ".py"

# The first parameter of a method, whose attributes the class holds.
_SELF_NAME = "self"

# The annotation of an alias, whose value is compared too.
_ALIAS_ANNOTATION = "TypeAlias"

# The payload of a line type its name does not spell.
_PAYLOAD_NAMES = {"db.create": "DbName", "db.drop": "DbName"}

# The start of the name of a module of handlers.
_HANDLER_PREFIX = "engine_"

# The function of `dispatch` that registers a handler.
_REGISTER_NAME = "handler_register"

# An interface of the line types and its body, empty for `{}`.
_INTERFACE = re.compile(
    r"^  interface (\w+) \{(?:\}|(.*?)^  \})$", re.MULTILINE | re.DOTALL
)

# A field of an interface, and whether it may be left out.
_FIELD = re.compile(r"^    (\w+)(\?)?:", re.MULTILINE)

# A comment of SQL text.
_SQL_COMMENT = re.compile(r"--[^\n]*")

# The key of the browser's tools in the text of the tools.
_BROWSER_KEY = "browser"

# What cuts a line type into the words of its payload's name.
_TYPE_WORD = re.compile(r"[._]")


# One member of a namespace: its keyword, and whether it says `export`.
class Member(NamedTuple):
    kind: str
    exported: bool


# One check: the member it proves, the code's type and the API text's.
class Pair(NamedTuple):
    path: str
    code: str
    text: str


# Raises the difference, naming where it is.
def difference_raise(where: str, what: str) -> NoReturn:
    raise RuntimeError(f"{where}: {what}")


# Reads a text file.
def text_read(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


# Reads a JSON file by the decoders' door for bad numbers.
def json_read(path: str) -> Any:
    # Imported here so its bytecode goes under the prefix set above.
    import jslb

    return jslb.json_decode(text_read(path))


# Returns the public members of each scope, each name by its keyword.
def members_read(text: str, indent: int) -> dict[str, dict[str, str]]:
    scopes: dict[str, dict[str, Member]] = {_TOP_SCOPE: {}}
    explicit: set[str] = set()
    scope = _TOP_SCOPE
    for line in text.splitlines():
        started = _NAMESPACE_START.match(line)
        if started is not None:
            scope = started.group(1)
            scopes.setdefault(scope, {})
        elif line == _NAMESPACE_END:
            scope = _TOP_SCOPE
        elif line.strip() == _EXPORTS_ONLY:
            explicit.add(scope)
        else:
            depth = indent if scope else 0
            found = _DECLARATION.match(line, depth)
            if found is not None and not line[:depth].strip():
                scopes[scope][found.group(3)] = Member(
                    found.group(2), found.group(1) is not None
                )
    return {
        scope: {
            name: member.kind
            for name, member in members.items()
            if member.exported or scope not in explicit
        }
        for scope, members in scopes.items()
    }


# Refuses a name one side lacks, and a member that changes its kind.
def names_match(
    text: dict[str, dict[str, str]], code: dict[str, dict[str, str]]
) -> None:
    for scope, members in sorted(text.items()):
        if scope in _TEXT_ONLY:
            continue
        if scope not in code:
            difference_raise(scope, _TEXT_ALONE)
        for name, kind in sorted(members.items()):
            where = f"{scope}.{name}"
            if name not in code[scope]:
                difference_raise(where, _TEXT_ALONE)
            other = code[scope][name]
            if (kind in _TYPE_KINDS, kind in _VALUE_KINDS) != (
                other in _TYPE_KINDS,
                other in _VALUE_KINDS,
            ):
                difference_raise(
                    where, f"{kind} in the API text, {other} in the code"
                )
    for scope, members in sorted(code.items()):
        if scope == _TOP_SCOPE or scope in _CODE_ONLY:
            continue
        if scope.startswith(_TEST_PREFIX) and scope not in text:
            continue
        if scope not in text:
            difference_raise(scope, _CODE_ALONE)
        for name in sorted(members):
            if name not in text[scope]:
                difference_raise(f"{scope}.{name}", _CODE_ALONE)


# Returns the `_PAIR_LINES` lines that assign the two types to each other.
def pair_text(index: int, pair: Pair) -> str:
    return (
        f"declare const code_{index}: {pair.code};\n"
        f"const text_{index}: {pair.text} = code_{index};\n"
        f"declare const other_{index}: {pair.text};\n"
        f"const back_{index}: {pair.code} = other_{index};\n"
    )


# Returns the pairs of every member the API text holds.
def pairs_make(text: dict[str, dict[str, str]]) -> list[Pair]:
    pairs: list[Pair] = []
    for scope, members in sorted(text.items()):
        if scope in _TEXT_ONLY:
            continue
        for name, kind in sorted(members.items()):
            path = f"{scope}.{name}" if scope else name
            owned = f"{_CODE_NAMESPACE}.{path}"
            if kind in _TYPE_KINDS:
                pairs.append(Pair(path, owned, path))
            if kind in _VALUE_KINDS:
                pairs.append(Pair(path, f"typeof {owned}", f"typeof {path}"))
    return pairs


# Returns the emitted declarations under one namespace, private members cut.
def code_wrap(text: str) -> str:
    lines = [
        line.removeprefix("declare ")
        for line in text.splitlines()
        if _PRIVATE_MEMBER.fullmatch(line) is None
    ]
    return "\n".join(
        [f"declare namespace {_CODE_NAMESPACE} {{", *lines, "}\n"]
    )


# Writes a text file.
def text_write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


# Proves `API/ts` against `ts/`, by the two tsc configurations given.
def typescript_match(
    api_config: str, code_config: str, build_path: str
) -> None:
    # Imported here so its bytecode goes under the prefix set above.
    import page_build

    if os.path.exists(build_path):
        shutil.rmtree(build_path)
    os.makedirs(build_path)
    emit_path = os.path.join(build_path, _EMIT_NAME)
    page_build.tsc_run(code_config, *_EMIT_OPTIONS, emit_path)
    emitted = text_read(os.path.join(build_path, _EMITTED_NAME))
    config = json_read(api_config)
    folder = os.path.dirname(api_config)
    paths = [
        os.path.normpath(os.path.join(folder, name))
        for name in config["files"]
    ]
    written = "\n".join(text_read(path) for path in paths)
    text = members_read(written, _TEXT_INDENT)
    names_match(text, members_read(emitted, _EMIT_INDENT))
    text_write(os.path.join(build_path, _WRAPPED_NAME), code_wrap(emitted))
    pairs = pairs_make(text)
    check = "".join(pair_text(*numbered) for numbered in enumerate(pairs))
    text_write(os.path.join(build_path, _CHECK_NAME), check)
    project = {
        "extends": api_config,
        "files": [*paths, _WRAPPED_NAME, _CHECK_NAME],
    }
    config_path = os.path.join(build_path, _MATCH_CONFIG_NAME)
    text_write(config_path, json.dumps(project))
    try:
        page_build.tsc_run(config_path)
    except RuntimeError as failed:
        found = _CHECK_ERROR.search(str(failed.__cause__))
        if found is None:
            raise
        pair = pairs[(int(found.group(1)) - 1) // _PAIR_LINES]
        raise RuntimeError(f"{pair.path}: {_TYPES_DIFFER}") from failed


# Whether a name is public: no `_` first, or a method Python itself names.
def public_is(name: str) -> bool:
    return name != _EXPORTS_NAME and (
        not name.startswith("_")
        or (name.startswith("__") and name.endswith("__"))
    )


# Returns the names a body defines, each by the statement that does.
def scope_read(body: list[ast.stmt]) -> dict[str, ast.stmt]:
    scope: dict[str, ast.stmt] = {}
    for statement in body:
        if isinstance(
            statement, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            scope[statement.name] = statement
        elif isinstance(statement, ast.AnnAssign):
            if isinstance(statement.target, ast.Name):
                scope[statement.target.id] = statement
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    scope[target.id] = statement
    return scope


# Yields the attributes of `self` the body assigns, with what assigns them.
def attributes_read(
    body: list[ast.stmt],
) -> Iterator[tuple[str, ast.stmt]]:
    for parent in body:
        for statement in ast.walk(parent):
            if isinstance(statement, ast.Assign):
                targets = statement.targets
            elif isinstance(statement, ast.AnnAssign):
                targets = [statement.target]
            else:
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == _SELF_NAME
                ):
                    yield target.attr, statement


# Returns the names of a class, its instance attributes among them.
def class_read(statement: ast.ClassDef) -> dict[str, ast.stmt]:
    scope = scope_read(statement.body)
    for name, assigner in attributes_read(statement.body):
        if name not in scope or isinstance(assigner, ast.AnnAssign):
            scope[name] = assigner
    return scope


# Returns what must agree of a definition, empty when a line states nothing.
def definition_text(statement: ast.stmt) -> str:
    if isinstance(statement, ast.Assign):
        return ""
    if isinstance(statement, ast.AnnAssign):
        annotation = ast.unparse(statement.annotation)
        if annotation == _ALIAS_ANNOTATION:
            return ast.unparse(statement)
        return annotation
    shown = copy.deepcopy(statement)
    assert isinstance(
        shown, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    )
    shown.body = [ast.Expr(ast.Constant(...))]
    if not isinstance(shown, ast.ClassDef):
        marks = ast.Constant(...)
        shown.args.defaults = [marks for _ in shown.args.defaults]
        shown.args.kw_defaults = [
            default and marks for default in shown.args.kw_defaults
        ]
    return ast.unparse(shown)


# Whether a stub's class is written as `class Name: ...`, its members its own.
def opaque_is(statement: ast.ClassDef) -> bool:
    return len(statement.body) == 1 and isinstance(statement.body[0], ast.Expr)


# Refuses the first difference of the named members of two scopes.
def scope_match(
    where: str,
    names: Iterable[str],
    text: dict[str, ast.stmt],
    code: dict[str, ast.stmt],
) -> None:
    for name in sorted(names):
        place = f"{where}.{name}"
        if name not in code:
            difference_raise(place, _TEXT_ALONE)
        if name not in text:
            difference_raise(place, _CODE_ALONE)
        stated = definition_text(text[name])
        written = definition_text(code[name])
        if stated and written and stated != written:
            difference_raise(place, f"{stated!r} against {written!r}")
        declared = text[name]
        defined = code[name]
        if (
            isinstance(declared, ast.ClassDef)
            and isinstance(defined, ast.ClassDef)
            and not opaque_is(declared)
        ):
            scope_match(
                place,
                filter(
                    public_is,
                    scope_read(declared.body).keys()
                    | scope_read(defined.body).keys(),
                ),
                scope_read(declared.body),
                class_read(defined),
            )


# Returns the names a module's `__all__` lists, None when it has none.
def exports_read(code: dict[str, ast.stmt]) -> set[str] | None:
    if _EXPORTS_NAME not in code:
        return None
    statement = code[_EXPORTS_NAME]
    assert isinstance(statement, ast.Assign)
    listed = ast.literal_eval(statement.value)
    return set(listed)


# Refuses the first difference of a stub's text and its module's.
def module_match(name: str, stub: str, module: str) -> None:
    text = scope_read(ast.parse(stub).body)
    code = scope_read(ast.parse(module).body)
    public = set(filter(public_is, text))
    exports = exports_read(code)
    if exports is None:
        public |= set(filter(public_is, code))
    else:
        public |= exports
    scope_match(name, public, text, code)


# Proves the stubs of the first directory against the modules of the second.
def python_match(api_path: str, code_path: str) -> None:
    stubs = {
        name.removesuffix(_STUB_EXTENSION)
        for name in os.listdir(api_path)
        if name.endswith(_STUB_EXTENSION)
    }
    modules = {
        name.removesuffix(_MODULE_EXTENSION)
        for name in os.listdir(code_path)
        if name.endswith(_MODULE_EXTENSION)
        and not name.startswith(_TEST_PREFIX)
    }
    for name in sorted(stubs - modules):
        difference_raise(name, _TEXT_ALONE)
    for name in sorted(modules - stubs - _STUB_ABSENT):
        difference_raise(name, _CODE_ALONE)
    for name in sorted(stubs):
        module_match(
            name,
            text_read(os.path.join(api_path, name + _STUB_EXTENSION)),
            text_read(os.path.join(code_path, name + _MODULE_EXTENSION)),
        )


# Returns each payload of the line types, each field by whether it may go.
def payloads_read(text: str) -> dict[str, dict[str, bool]]:
    return {
        found.group(1): {
            field.group(1): field.group(2) is not None
            for field in _FIELD.finditer(found.group(2) or "")
        }
        for found in _INTERFACE.finditer(text)
    }


# Returns the name of the payload of a line type.
def payload_name(line_type: str) -> str:
    if line_type in _PAYLOAD_NAMES:
        return _PAYLOAD_NAMES[line_type]
    words = _TYPE_WORD.split(line_type)
    return "".join(word.capitalize() for word in words)


# Returns the keywords of a handler, each by whether it has a default.
def keywords_read(function: ast.FunctionDef) -> dict[str, bool]:
    return {
        keyword.arg: default is not None
        for keyword, default in zip(
            function.args.kwonlyargs, function.args.kw_defaults, strict=True
        )
    }


# Proves the handlers of the directory against the file of the line types.
def handlers_match(lines_path: str, code_path: str) -> None:
    payloads = payloads_read(text_read(lines_path))
    for name in sorted(os.listdir(code_path)):
        if not (
            name.startswith(_HANDLER_PREFIX)
            and name.endswith(_MODULE_EXTENSION)
        ):
            continue
        tree = ast.parse(text_read(os.path.join(code_path, name)))
        scope = scope_read(tree.body)
        for call in ast.walk(tree):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == _REGISTER_NAME
            ):
                continue
            type_node, _, function_node = call.args
            assert isinstance(type_node, ast.Constant)
            assert isinstance(function_node, ast.Name)
            function = scope[function_node.id]
            assert isinstance(function, ast.FunctionDef)
            assert isinstance(type_node.value, str)
            line_type = type_node.value
            if function.args.kwarg is not None:
                continue
            payload = payload_name(line_type)
            if payload not in payloads:
                difference_raise(line_type, f"the API text has no {payload}")
            keywords = keywords_read(function)
            if keywords != payloads[payload]:
                difference_raise(
                    line_type,
                    f"{payloads[payload]} in the API text,"
                    f" {keywords} in {name}",
                )


# Returns the statements of SQL text, comments cut and white space folded.
def statements_read(text: str) -> list[str]:
    bare = _SQL_COMMENT.sub("", text)
    words = (" ".join(part.split()) for part in bare.split(";"))
    return [statement for statement in words if statement]


# Proves the gold of the TypeScript suites against the text of the checkout.
def gold_match(root: str) -> None:
    tools = json_read(os.path.join(root, _TOOLS_PATH))
    gold = json_read(os.path.join(root, _TOOLS_GOLD))
    if gold[_TOOLS_KEY] != tools[_BROWSER_KEY]["result"]["tools"]:
        difference_raise(
            _TOOLS_GOLD, f"{_TOOLS_KEY} differs from {_TOOLS_PATH}"
        )
    gold = json_read(os.path.join(root, _SCHEMA_GOLD))
    schema = statements_read(text_read(os.path.join(root, _SCHEMA_PATH)))
    if gold[_SCHEMA_KEY] != schema:
        difference_raise(
            _SCHEMA_GOLD, f"{_SCHEMA_KEY} differs from {_SCHEMA_PATH}"
        )


# Runs every match on the checkout, the compiles unless its stamp is newer.
def text_match(root: str) -> None:
    # Imported here so its bytecode goes under the prefix set above.
    import page_build

    match_path = os.path.join(root, _MATCH_PATH)
    page_build.compile_timed(
        os.path.join(match_path, _PASSED_NAME),
        lambda: typescript_match(
            os.path.join(root, _API_CONFIG),
            os.path.join(root, _CODE_CONFIG),
            match_path,
        ),
        root,
    )
    code_path = os.path.join(root, _CODE_PYTHON_PATH)
    python_match(os.path.join(root, _API_PYTHON_PATH), code_path)
    handlers_match(os.path.join(root, _LINES_PATH), code_path)
    gold_match(root)
