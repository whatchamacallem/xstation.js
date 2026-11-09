# Proves the text of `API/` against the code, so that neither moves alone.
# `text_match` runs every match on a checkout, and `test_posix.py` calls it
# last, as a source check, so the cloud run skips it. Each function raises at
# the first difference, naming it.
#
# `typescript_match` compiles the declarations tsc emits from `ts/` beside the
# API text, with a check that assigns each member to its twin both ways, so
# that the two agree by the compiler's own rules. `python_match` compares each
# stub with its module by `ast`. `handlers_match` compares each handler of
# `python/engine_*.py` with its payload in `API/ts/lines.d.ts`. `gold_match`
# compares `API/mcp/tools.json` and `API/sql/substrate.sql` with the gold the
# browser's suites hold the real tools and tables to. What each compares and
# what none can see is the section api_match of the rules.

# Returns each namespace's public members by keyword, `""` for no namespace.
def members_read(text: str, indent: int) -> dict[str, dict[str, str]]: ...

# Refuses a name the text or the code lacks, and a member changing kind.
def names_match(
    text: dict[str, dict[str, str]], code: dict[str, dict[str, str]]
) -> None: ...

# Proves `API/ts` against `ts/`, by the two tsc configurations given.
def typescript_match(
    api_config: str, code_config: str, build_path: str
) -> None: ...

# Proves the stubs of the first directory against the modules of the second.
def python_match(api_path: str, code_path: str) -> None: ...

# Returns the name of the payload of a line type.
def payload_name(line_type: str) -> str: ...

# Proves the handlers of the directory against the file of the line types.
def handlers_match(lines_path: str, code_path: str) -> None: ...

# Proves the gold of the TypeScript suites against the text of the checkout.
def gold_match(root: str) -> None: ...

# Runs every match on the checkout, `typescript_match` by `compile_timed`.
def text_match(root: str) -> None: ...
