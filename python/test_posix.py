#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Checks the whitelisted files are UTF-8 with no non-ASCII outside
# _NON_ASCII_ALLOWED, checks the comments of those and the PowerShell files,
# including the TypeScript and JavaScript ones, proves the synchronization
# audit on probe files under build/, audits every ts/*.ts file other than the
# _SYNCHRONIZATION_MODULES for await, .then(, new Promise, Atomics and
# SharedArrayBuffer outside its comments and its string, template and regular
# expression literals, formats the whitelisted files with reformat.py, then
# lints the Python ones with ruff check. Below a file's header, the comment at
# its top, a comment must be one line, not be a <# #> comment, and outside its
# Doxygen `code` spans hold nothing but letters, digits, white space and
# _ENGLISH_PUNCT.

import argparse, glob, io, os, re, subprocess, sys, tempfile, tokenize
from typing import NamedTuple

_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# Bytecode of the modules main imports goes in build/.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")

# Probe code the audit must pass: each token in a literal or a comment.
_AUDIT_PASSED = (
    'const s = "await p.then( new Promise Atomics SharedArrayBuffer";\n',
    "const s = 'await p.then(';\n",
    "const t = `await p.then( ${n} new Promise`;\n",
    "const r = /await|\\.then\\(|Atomics/;\n",
    "// await p.then( new Promise\n",
    "/* Atomics SharedArrayBuffer */\n",
)

# Probe code the audit must refuse, one synchronization token in each.
_AUDIT_REFUSED = (
    "await x;\n",
    "p.then(f);\n",
    "p.then<T>(f);\n",
    "p.then (f);\n",
    "p.then\n  (f);\n",
    "new Promise(f);\n",
    "Atomics.wait(a, 0, 0);\n",
    "new SharedArrayBuffer(8);\n",
    "const t = `${await x}`;\n",
)

# A Doxygen code span, cut from a comment before its punctuation is checked.
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")

# The punctuation a comment below the header may hold outside a code span.
_ENGLISH_PUNCT = """.,"'?:!()/"""

# The comment header may have a doctype line before it.
_HEADER_BEFORE = re.compile(r"(?:<!DOCTYPE html>)?\s*", re.IGNORECASE)

# HTML comments, and the script and style elements, whose comments differ.
_HTML_REGION = re.compile(r"<!--|<(script|style)\b[^>]*>", re.IGNORECASE)

# What JavaScript can have before a regular expression literal.
_JAVASCRIPT_REGEX_AFTER = {
    *"(,=:[!&|?{};+-*%<>~^",
    "",
    "await",
    "case",
    "delete",
    "do",
    "else",
    "in",
    "instanceof",
    "new",
    "of",
    "return",
    "throw",
    "typeof",
    "void",
    "yield",
}

# A JavaScript name, keyword or number.
_JAVASCRIPT_WORD = re.compile(r"[\w$.]+")

# The characters beyond ASCII that the whitelisted files may hold.
_NON_ASCII_ALLOWED = {
    "\N{COPYRIGHT SIGN}",
    "\N{LATIN SMALL LETTER E WITH ACUTE}",
}

# A character a comment below the header may not hold.
_OUTSIDE_PUNCTUATION = re.compile(
    r"[^A-Za-z0-9\s" + re.escape(_ENGLISH_PUNCT) + r"]"
)

# The PowerShell files, found as the PowerShell lint finds them.
_POWERSHELL_GLOBS = ["**/*.ps1", "**/*.psm1", "**/*.psd1"]

# What PowerShell can have before a comment.
_POWERSHELL_TOKEN_BREAK = " \t\n;(){}|&,="

_RUFF_CACHE_PATH = os.path.join(_BUILD_PATH, "ruff_cache")

# The one ruff configuration, for files outside python/ too.
_RUFF_CONFIG_PATH = os.path.join(_ROOT_PATH, "python", "pyproject.toml")

# A shell here document's start: `<<`, `-` to strip tabs, a quote, its word.
_SHELL_HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)(\w+)\2")

# What the shell can have before a comment.
_SHELL_WORD_BREAK = " \t\n;&|()<>"

# The TypeScript modules that may hold a synchronization token.
_SYNCHRONIZATION_MODULES = ("queue.ts", "wire.ts", "http.ts", "media.ts")

# The tokens that only the synchronization modules may hold.
_SYNCHRONIZATION_TOKEN = re.compile(
    r"\bawait\b|\.then\s*(?:<[^()]*>)?\s*\(|\bnew Promise\b|\bAtomics\b"
    r"|\bSharedArrayBuffer\b"
)

# The TypeScript files the audit covers, from the top directory.
_TYPESCRIPT_GLOB = "ts/*.ts"


# A comment's offsets in its file's text, and the lengths of its markers.
class Comment(NamedTuple):
    start: int
    end: int
    opener: int
    closer: int


# Fails unless the audit refuses each probe token and passes each literal.
def audit_probe() -> None:
    os.makedirs(_BUILD_PATH, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
        path = os.path.join(scratch, "probe.ts")
        for code in _AUDIT_REFUSED:
            if not token_find(probe_write(path, code)):
                raise RuntimeError(f"the audit misses the token in {code!r}")
        for code in _AUDIT_PASSED:
            found = token_find(probe_write(path, code))
            if found:
                raise RuntimeError(
                    f"the audit finds {found.group()!r} in {code!r}"
                )


# Fails on the first comment below the header that breaks a comment rule.
def comments_check(path: str) -> None:
    with open(path, encoding="utf-8-sig") as file:
        text = file.read()
    groups: list[list[Comment]] = []
    for comment in comments_find(path, text):
        line_start = text.rfind("\n", 0, comment.start) + 1
        if (
            groups
            and not text[line_start : comment.start].strip()
            and offset_line(text, groups[-1][-1].end) + 1
            == offset_line(text, comment.start)
        ):
            groups[-1].append(comment)
        else:
            groups.append([comment])
    if groups and _HEADER_BEFORE.fullmatch(text, 0, groups[0][0].start):
        groups.pop(0)
    for group in groups:
        first_line = offset_line(text, group[0].start)
        for comment in group:
            if text.startswith("<#", comment.start):
                raise RuntimeError(
                    f"{path}:{offset_line(text, comment.start)}: <# #>"
                    " comment below the top of the file. Use #."
                )
        last_line = offset_line(text, group[-1].end)
        if last_line != first_line:
            raise RuntimeError(
                f"{path}:{first_line}: comment below the header runs to"
                f" line {last_line}. Make it one line."
            )
        comment = group[0]
        words = text[
            comment.start + comment.opener : comment.end - comment.closer
        ]
        match = _OUTSIDE_PUNCTUATION.search(_CODE_SPAN.sub("", words))
        if match:
            raise RuntimeError(
                f"{path}:{first_line}: comment holds {match.group()!r}"
                " outside _ENGLISH_PUNCT and code spans"
            )


# Returns the comments of the file's text, in order, by its extension.
def comments_find(path: str, text: str) -> list[Comment]:
    comments: list[Comment] = []
    match os.path.splitext(path)[1]:
        case ".md":
            pass
        case ".py" | ".pyi":
            comments = python_comments(text)
        case ".sh":
            shell_scan(path, text, 0, False, comments)
        case ".ps1" | ".psm1" | ".psd1":
            powershell_scan(path, text, 0, False, comments)
        case ".html":
            html_scan(path, text, comments)
        case ".ts" | ".js":
            javascript_scan(path, text, 0, len(text), False, comments, [])
        case extension:
            raise RuntimeError(f"{path}: no comment lexer for {extension!r}")
    return comments


# Adds the comments of CSS from the offset to the stop.
def css_scan(
    path: str, text: str, i: int, stop: int, comments: list[Comment]
) -> None:
    while i < stop:
        if text.startswith("/*", i):
            end = end_find(path, text, i + 2, "*/")
            comments.append(Comment(i, end, 2, 2))
            i = end
        elif text[i] in "'\"":
            i = javascript_string_scan(path, text, i)
        else:
            i += 1


# Returns the offset past the needle at or after the offset, failing if none.
def end_find(path: str, text: str, i: int, needle: str) -> int:
    end = text.find(needle, i)
    if end == -1:
        raise RuntimeError(
            f"{path}:{offset_line(text, i)}: no {needle!r} ends this"
        )
    return end + len(needle)


# Adds the comments of HTML and of its script and style elements.
def html_scan(path: str, text: str, comments: list[Comment]) -> None:
    lower = text.lower()
    i = 0
    while region := _HTML_REGION.search(text, i):
        if region.group() == "<!--":
            end = end_find(path, text, region.end(), "-->")
            comments.append(Comment(region.start(), end, 4, 3))
            i = end
            continue
        stop = lower.find(f"</{region.group(1).lower()}", region.end())
        if stop == -1:
            raise RuntimeError(
                f"{path}:{offset_line(text, region.start())}: no end tag"
            )
        if region.group(1).lower() == "script":
            javascript_scan(
                path, text, region.end(), stop, False, comments, []
            )
        else:
            css_scan(path, text, region.end(), stop, comments)
        i = stop


# Returns the offset past JavaScript to the stop, or past an unmatched brace.
def javascript_scan(
    path: str,
    text: str,
    i: int,
    stop: int,
    closer: bool,
    comments: list[Comment],
    literals: list[tuple[int, int]],
) -> int:
    depth = 0
    previous = ""
    while i < stop:
        character = text[i]
        if character.isspace():
            i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i, stop)
            end = stop if end == -1 else end
            comments.append(Comment(i, end, 2, 0))
            i = end
            continue
        if text.startswith("/*", i):
            end = end_find(path, text, i + 2, "*/")
            comments.append(Comment(i, end, 2, 2))
            i = end
            continue
        if character in "'\"":
            end = javascript_string_scan(path, text, i)
            literals.append((i, end))
            i = end
            character = "a"
        elif character == "`":
            i = javascript_template_scan(
                path, text, i, stop, comments, literals
            )
            character = "a"
        elif character == "/" and previous in _JAVASCRIPT_REGEX_AFTER:
            end = javascript_regex_scan(path, text, i)
            literals.append((i, end))
            i = end
            character = "a"
        elif word := _JAVASCRIPT_WORD.match(text, i):
            i = word.end()
            character = word.group()
        else:
            if character == "{":
                depth += 1
            elif character == "}":
                if closer and depth == 0:
                    return i + 1
                depth -= 1
            i += 1
        previous = character
    if closer:
        raise RuntimeError(f"{path}:{offset_line(text, i)}: no closing brace")
    return i


# Returns the offset past the regular expression literal at the offset.
def javascript_regex_scan(path: str, text: str, i: int) -> int:
    start = i
    in_class = False
    i += 1
    while i < len(text) and text[i] != "\n":
        character = text[i]
        if character == "\\":
            i += 1
        elif character == "[":
            in_class = True
        elif character == "]":
            in_class = False
        elif character == "/" and not in_class:
            i += 1
            while i < len(text) and text[i].isalpha():
                i += 1
            return i
        i += 1
    raise RuntimeError(
        f"{path}:{offset_line(text, start)}: unterminated regular expression"
    )


# Returns the offset past the quoted string at the offset.
def javascript_string_scan(path: str, text: str, i: int) -> int:
    start = i
    quote = text[i]
    i += 1
    while i < len(text) and text[i] != "\n":
        if text[i] == "\\":
            i += 2
        elif text[i] == quote:
            return i + 1
        else:
            i += 1
    raise RuntimeError(
        f"{path}:{offset_line(text, start)}: unterminated string"
    )


# Returns the offset past the template literal, adding its text spans.
def javascript_template_scan(
    path: str,
    text: str,
    i: int,
    stop: int,
    comments: list[Comment],
    literals: list[tuple[int, int]],
) -> int:
    start = i
    span_start = i
    i += 1
    while i < stop:
        if text[i] == "\\":
            i += 2
        elif text[i] == "`":
            literals.append((span_start, i + 1))
            return i + 1
        elif text.startswith("${", i):
            literals.append((span_start, i))
            i = javascript_scan(
                path, text, i + 2, stop, True, comments, literals
            )
            span_start = i
        else:
            i += 1
    raise RuntimeError(
        f"{path}:{offset_line(text, start)}: unterminated template literal"
    )


# Fails on the first character beyond ASCII that the file may not hold.
def non_ascii_check(path: str) -> None:
    with open(path, "rb") as file:
        data = file.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"{path}: not UTF-8: {error}") from error
    for line_number, line in enumerate(text.split("\n"), 1):
        for column, character in enumerate(line, 1):
            if character.isascii() or character in _NON_ASCII_ALLOWED:
                continue
            raise RuntimeError(
                f"{path}:{line_number}:{column}: U+{ord(character):04X}"
                f" {character!r} isn't in _NON_ASCII_ALLOWED"
            )


# Returns the line the offset is on, counting from 1.
def offset_line(text: str, i: int) -> int:
    return text.count("\n", 0, i) + 1


# Returns the offset past the double quoted PowerShell string at the offset.
def powershell_double_scan(
    path: str, text: str, i: int, comments: list[Comment]
) -> int:
    start = i
    i += 1
    while i < len(text):
        if text[i] == "`" or text.startswith('""', i):
            i += 2
        elif text[i] == '"':
            return i + 1
        elif text.startswith("$(", i):
            i = powershell_scan(path, text, i + 2, True, comments)
        else:
            i += 1
    raise RuntimeError(
        f"{path}:{offset_line(text, start)}: unterminated string"
    )


# Returns the PowerShell files under the top directory, sorted.
def powershell_paths() -> list[str]:
    paths: list[str] = []
    for pattern in _POWERSHELL_GLOBS:
        matched = glob.glob(pattern, root_dir=_ROOT_PATH, recursive=True)
        paths += [os.path.join(_ROOT_PATH, path) for path in matched]
    return sorted(paths)


# Returns the offset past PowerShell to the end, or past an unmatched paren.
def powershell_scan(
    path: str, text: str, i: int, closer: bool, comments: list[Comment]
) -> int:
    depth = 0
    while i < len(text):
        character = text[i]
        if text.startswith("<#", i):
            end = end_find(path, text, i + 2, "#>")
            comments.append(Comment(i, end, 2, 2))
            i = end
        elif character == "#" and (
            i == 0 or text[i - 1] in _POWERSHELL_TOKEN_BREAK
        ):
            end = text.find("\n", i)
            end = len(text) if end == -1 else end
            comments.append(Comment(i, end, 1, 0))
            i = end
        elif character == "`":
            i += 2
        elif text.startswith("@'\n", i):
            i = end_find(path, text, i + 2, "\n'@")
        elif text.startswith('@"\n', i):
            i = end_find(path, text, i + 2, '\n"@')
        elif character == "'":
            i = end_find(path, text, i + 1, "'")
            while text.startswith("'", i):
                i = end_find(path, text, i + 1, "'")
        elif character == '"':
            i = powershell_double_scan(path, text, i, comments)
        elif character == ")" and closer and depth == 0:
            return i + 1
        else:
            depth += {"(": 1, ")": -1}.get(character, 0)
            i += 1
    if closer:
        raise RuntimeError(f"{path}:{offset_line(text, i)}: no closing paren")
    return i


# Writes the code to the probe file and returns its path.
def probe_write(path: str, code: str) -> str:
    with open(path, "w", encoding="utf-8") as file:
        file.write(code)
    return path


# Returns the comments Python's tokenizer finds in the text.
def python_comments(text: str) -> list[Comment]:
    line_starts = [0]
    line_starts += [i + 1 for i, c in enumerate(text) if c == "\n"]
    comments: list[Comment] = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            start = line_starts[token.start[0] - 1] + token.start[1]
            comments.append(Comment(start, start + len(token.string), 1, 0))
    return comments


# Returns the offset past the double quoted shell string at the offset.
def shell_double_scan(
    path: str, text: str, i: int, comments: list[Comment]
) -> int:
    start = i
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
        elif text[i] == '"':
            return i + 1
        elif text.startswith("$(", i):
            i = shell_scan(path, text, i + 2, True, comments)
        elif text[i] == "`":
            i = end_find(path, text, i + 1, "`")
        else:
            i += 1
    raise RuntimeError(
        f"{path}:{offset_line(text, start)}: unterminated string"
    )


# Returns the offset past shell code to the end, or past an unmatched paren.
def shell_scan(
    path: str, text: str, i: int, closer: bool, comments: list[Comment]
) -> int:
    depth = 0
    heredocs: list[re.Match[str]] = []
    while i < len(text):
        character = text[i]
        if character == "\\":
            i += 2
        elif character == "'":
            i = end_find(path, text, i + 1, "'")
        elif character == '"':
            i = shell_double_scan(path, text, i, comments)
        elif character == "#" and (i == 0 or text[i - 1] in _SHELL_WORD_BREAK):
            end = text.find("\n", i)
            end = len(text) if end == -1 else end
            comments.append(Comment(i, end, 1, 0))
            i = end
        elif text.startswith("<<<", i):
            i += 3
        elif heredoc := _SHELL_HEREDOC.match(text, i):
            heredocs.append(heredoc)
            i = heredoc.end()
        elif character == "\n" and heredocs:
            for heredoc in heredocs:
                tabs = "\t*" if heredoc.group(1) else ""
                word = re.escape(heredoc.group(3))
                body = re.compile(f"^{tabs}{word}$", re.MULTILINE)
                end = body.search(text, i + 1)
                if not end:
                    raise RuntimeError(
                        f"{path}:{offset_line(text, heredoc.start())}: no"
                        f" line ends the here document {word!r}"
                    )
                i = end.end()
            heredocs.clear()
        elif character == ")" and closer and depth == 0:
            return i + 1
        else:
            depth += {"(": 1, ")": -1}.get(character, 0)
            i += 1
    if closer or heredocs:
        raise RuntimeError(f"{path}:{offset_line(text, i)}: unterminated")
    return i


# Fails on the first synchronization token in a file's code.
def synchronization_check(path: str) -> None:
    if os.path.basename(path) in _SYNCHRONIZATION_MODULES:
        return
    match = token_find(path)
    if match:
        raise RuntimeError(
            f"{path}:{offset_line(match.string, match.start())}:"
            f" {match.group()} outside the four modules"
        )


# Returns the first synchronization token, comments and literals blanked.
def token_find(path: str) -> re.Match[str] | None:
    with open(path, encoding="utf-8-sig") as file:
        text = file.read()
    comments: list[Comment] = []
    literals: list[tuple[int, int]] = []
    javascript_scan(path, text, 0, len(text), False, comments, literals)
    spans = [(comment.start, comment.end) for comment in comments]
    code = list(text)
    for start, end in spans + literals:
        for i in range(start, end):
            if code[i] != "\n":
                code[i] = " "
    return _SYNCHRONIZATION_TOKEN.search("".join(code))


# Returns the TypeScript files under the top directory, failing on none.
def typescript_paths() -> list[str]:
    matched = glob.glob(_TYPESCRIPT_GLOB, root_dir=_ROOT_PATH)
    if not matched:
        raise RuntimeError(
            f"{_TYPESCRIPT_GLOB} matches no file under {_ROOT_PATH}"
        )
    return sorted(os.path.join(_ROOT_PATH, path) for path in matched)


# Checks and audits the files, then formats and lints the whitelisted ones.
def main() -> None:
    import reformat

    argparse.ArgumentParser(
        description="Check, format and lint the files"
        " reformat_whitelist.txt lists, check the comments of those and the"
        " PowerShell files, and audit the ts/*.ts files for synchronization"
        " tokens."
    ).parse_args()
    paths = reformat.whitelist_paths()
    for path in paths:
        non_ascii_check(path)
    for path in paths + powershell_paths():
        comments_check(path)
    audit_probe()
    for path in typescript_paths():
        synchronization_check(path)
    reformat.reformat(paths)
    python_paths = [path for path in paths if path.endswith((".py", ".pyi"))]
    # With no files, ruff checks the directory.
    if python_paths:
        subprocess.run(
            [
                "ruff",
                "check",
                "--config",
                _RUFF_CONFIG_PATH,
                "--cache-dir",
                _RUFF_CACHE_PATH,
                *python_paths,
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
