#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# `python3 python/page_build.py TEMPLATE NAME` builds build/NAME.html from
# the template html/TEMPLATE.html, read first, and prints the page's
# SHA-256, which page_build returns and never prints, since stdout is the
# driver's TAP stream when the driver builds the headless page. tsc compiles
# the test bundle by ts/tsconfig.test.json, the text of i18n/en-US.json
# takes the place of the bundle's strings table identifier, and the template
# receives html/engine.css, the bundle, every file of build/vectors/ as
# base64, written anew by vectors_make.py first, SQLite's JavaScript glue,
# its wasm as base64, and xterm.js and its css, read from the archives
# third_party_fetch.py places in third_party/. Each template takes the same
# pieces: html/test.html, the ttyd page, which the start script serves as
# hyperposition-engine.html, and html/headless.html, the headless page of
# group B, which the driver's HTTP server serves.
#
# node_build builds the Node bundle of group A in the build directory it is
# given: the vectors written anew into its vectors/ first, then tsc compiling
# ts/tsconfig.node.json into its ts/node.js, the place the config's outFile
# names in build/, which is rewritten as the strict line, then test_vectors
# defined as the page defines it, then the bundle with the strings table in
# place, and its path returned. tsc's output never reaches stdout: a failed
# compile raises, tsc's output in its cause.

import argparse, base64, hashlib, json, os, re, shutil, subprocess, sys
import tarfile, zipfile

# The public name of this module, as its stub declares it.
__all__ = ["node_build", "page_build"]

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the page is written, and the bundles in its `ts/`.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The page templates.
_HTML_PATH = os.path.join(_ROOT_PATH, "html")

# The extension of a template and of the page built from it.
_PAGE_EXTENSION = ".html"

# The engine's style, which every page carries.
_ENGINE_CSS_PATH = os.path.join(_HTML_PATH, "engine.css")

# The strings table, the same file the server reads.
_TABLE_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# The archives `third_party_fetch.py` places.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The TypeScript sources.
_TS_PATH = os.path.join(_ROOT_PATH, "ts")

# The `tsc` configuration of the test bundle, whose `outFile` the page takes.
_CONFIG_NAME = "tsconfig.test.json"

# The `tsc` configuration of the Node bundle, rewritten where its `outFile` is.
_NODE_CONFIG_NAME = "tsconfig.node.json"

# The start of the Node bundle: the strict line, then `test_vectors` defined.
_NODE_HEAD = '"use strict";\nvar test_vectors = {};\n'

# The folder of a build directory that the vectors are written into.
_VECTORS_NAME = "vectors"

# The vectors written for the page, which carries them as `test_vectors`.
_VECTORS_PATH = os.path.join(_BUILD_PATH, _VECTORS_NAME)

# The SQLite release archive, in its library's directory of `third_party`.
_SQLITE_ARCHIVE = os.path.join("sqlite", "sqlite-wasm-3460100.zip")

# SQLite's JavaScript glue, by the end of its path inside the archive.
_SQLITE_JS = "jswasm/sqlite3.js"

# SQLite's WebAssembly, by the end of its path inside the archive.
_SQLITE_WASM = "jswasm/sqlite3.wasm"

# The `xterm.js` package archive, in its library's directory of `third_party`.
_XTERM_ARCHIVE = os.path.join("xterm", "xterm-5.5.0.tgz")

# The `xterm.js` script inside its package archive.
_XTERM_JS = "package/lib/xterm.js"

# The `xterm.js` style inside its package archive.
_XTERM_CSS = "package/css/xterm.css"

# A build marker of a template: a word starting `XSJS_BUILD_`.
_MARKER = re.compile(r"(?<![\w$])XSJS_BUILD_\w+")

# Each build marker and the element whose raw text it stands in.
_MARKER_ELEMENTS = {
    "XSJS_BUILD_BUNDLE": "script",
    "XSJS_BUILD_ENGINE_CSS": "style",
    "XSJS_BUILD_SQLITE3_JS": "script",
    "XSJS_BUILD_SQLITE3_WASM": "script",
    "XSJS_BUILD_TEST_VECTORS": "script",
    "XSJS_BUILD_XTERM_CSS": "style",
    "XSJS_BUILD_XTERM_JS": "script",
}

# The identifier the strings table stands for in the compiled bundle.
_TABLE_TOKEN = re.compile(r"(?<![\w$])I18N_TABLE_JSON(?![\w$])")

# The seconds tsc may run, a default chosen by its writer.
_TSC_SECONDS = 120.0

# Bytecode of `vectors_make` and of what it imports goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# Compiles the project of the `tsc` config into the path, returning its text.
def bundle_compile(config_path: str, out_path: str) -> str:
    tsc_path = shutil.which("tsc")
    if tsc_path is None:
        raise FileNotFoundError("tsc, the TypeScript compiler, is not on PATH")
    completed = subprocess.run(
        [tsc_path, "--project", config_path, "--outFile", out_path],
        capture_output=True,
        check=False,
        timeout=_TSC_SECONDS,
    )
    if completed.returncode != 0:
        output = completed.stdout + completed.stderr
        raise RuntimeError(
            f"tsc exited with {completed.returncode} compiling {config_path}"
        ) from RuntimeError(output.decode("utf-8", "replace"))
    return text_read(out_path)


# Returns the place the config's `outFile` names in `build`, in the directory.
def bundle_path(config_path: str, build_path: str) -> str:
    with open(config_path, encoding="utf-8") as config_file:
        out_file: str = json.load(config_file)["compilerOptions"]["outFile"]
    named = os.path.join(os.path.dirname(config_path), out_file)
    return os.path.join(build_path, os.path.relpath(named, _BUILD_PATH))


# Raises unless the text can be the raw text of the element, unchanged.
def embed_check(label: str, text: str, element: str) -> None:
    lower = text.lower()
    if "</" + element in lower:
        raise ValueError(f"{label}: holds </{element}, which ends the element")
    if element == "script" and "<!--" in lower and "<script" in lower:
        raise ValueError(
            f"{label}: holds <!-- and <script, which hide the end tag"
        )
    if "\0" in text:
        raise ValueError(f"{label}: holds NUL, which the HTML parser replaces")


# Returns the `SHA-256` hex of the file's bytes.
def file_hash(path: str) -> str:
    with open(path, "rb") as file:
        return hashlib.sha256(file.read()).hexdigest()


# Returns the template with each marker, found once, replaced in one pass.
def markers_fill(template: str, pieces: dict[str, str]) -> str:
    found = sorted(_MARKER.findall(template))
    if found != sorted(pieces):
        raise ValueError(f"template markers {found}, not {sorted(pieces)}")
    return _MARKER.sub(lambda match: pieces[match.group()], template)


# Returns the one name that is the suffix or ends in a slash and the suffix.
def member_find(names: list[str], suffix: str) -> str:
    matches = [
        name for name in names if name == suffix or name.endswith("/" + suffix)
    ]
    if len(matches) != 1:
        raise LookupError(f"{suffix}: archive members {matches}, not one")
    return matches[0]


# Builds the Node bundle in the build directory and returns its path.
def node_build(build_path: str) -> str:
    vectors = vectors_build(os.path.join(build_path, _VECTORS_NAME))
    config_path = os.path.join(_TS_PATH, _NODE_CONFIG_NAME)
    path = bundle_path(config_path, build_path)
    bundle = bundle_compile(config_path, path)
    text = _NODE_HEAD.format(vectors) + table_substitute(
        bundle, text_read(_TABLE_PATH)
    )
    with open(path, "wb") as file:
        file.write(text.encode("utf-8"))
    return path


# Builds `build/<name>.html` from `html/<template>.html`, its hex returned.
def page_build(template: str, name: str) -> str:
    # Read first, so a template `html/` lacks fails before `tsc` starts.
    shell = text_read(os.path.join(_HTML_PATH, template + _PAGE_EXTENSION))
    config_path = os.path.join(_TS_PATH, _CONFIG_NAME)
    bundle = bundle_compile(config_path, bundle_path(config_path, _BUILD_PATH))
    sqlite_js, sqlite_wasm = zip_read(
        os.path.join(_THIRD_PARTY_PATH, _SQLITE_ARCHIVE),
        [_SQLITE_JS, _SQLITE_WASM],
    )
    xterm_js, xterm_css = tar_read(
        os.path.join(_THIRD_PARTY_PATH, _XTERM_ARCHIVE),
        [_XTERM_JS, _XTERM_CSS],
    )
    # The worker joins `data-worker` texts by `"\n"` after `"use strict";\n`.
    pieces = {
        "XSJS_BUILD_BUNDLE": table_substitute(bundle, text_read(_TABLE_PATH)),
        "XSJS_BUILD_ENGINE_CSS": text_read(_ENGINE_CSS_PATH),
        "XSJS_BUILD_SQLITE3_JS": sqlite_js.decode("utf-8"),
        "XSJS_BUILD_SQLITE3_WASM": base64.b64encode(sqlite_wasm).decode(),
        "XSJS_BUILD_TEST_VECTORS": vectors_build(_VECTORS_PATH),
        "XSJS_BUILD_XTERM_CSS": xterm_css.decode("utf-8"),
        "XSJS_BUILD_XTERM_JS": xterm_js.decode("utf-8"),
    }
    page = page_merge(shell, pieces)
    return page_write(os.path.join(_BUILD_PATH, name + _PAGE_EXTENSION), page)


# Returns the template with its markers replaced by the pieces, each checked.
def page_merge(template: str, pieces: dict[str, str]) -> str:
    for marker, text in pieces.items():
        embed_check(marker, text, _MARKER_ELEMENTS[marker])
    return markers_fill(template, pieces)


# Writes the page as `UTF-8` and returns the `SHA-256` hex of the file.
def page_write(path: str, page: str) -> str:
    with open(path, "wb") as file:
        file.write(page.encode("utf-8"))
    return file_hash(path)


# Returns the bundle with its one table identifier replaced by the JSON text.
def table_substitute(bundle: str, table_json: str) -> str:
    json.loads(table_json)
    count = len(_TABLE_TOKEN.findall(bundle))
    if count != 1:
        raise ValueError(
            f"I18N_TABLE_JSON occurs {count} times in the bundle, not once"
        )
    return _TABLE_TOKEN.sub(lambda _match: table_json, bundle)


# Returns the bytes of the members of the gzipped tar the suffixes name.
def tar_read(path: str, suffixes: list[str]) -> list[bytes]:
    with tarfile.open(path, "r:gz") as archive:
        members = [
            member for member in archive.getmembers() if member.isfile()
        ]
        names = [member.name for member in members]
        contents: list[bytes] = []
        for suffix in suffixes:
            name = member_find(names, suffix)
            file = archive.extractfile(members[names.index(name)])
            if file is None:
                raise LookupError(f"{path}: {name} gives no file to read")
            contents.append(file.read())
        return contents


# Returns the file's text, decoded as strict `UTF-8`, its newlines unchanged.
def text_read(path: str) -> str:
    with open(path, "rb") as file:
        return file.read().decode("utf-8")


# Writes the vectors into the folder anew, then returns them as base64 JSON.
def vectors_build(path: str) -> str:
    # Imported here so its bytecode goes under the prefix set above.
    import vectors_make

    vectors_make.vectors_write(path)
    return vectors_json(path)


# Returns a JSON object of each file in the folder, by name, as base64.
def vectors_json(path: str) -> str:
    vectors: dict[str, str] = {}
    for name in sorted(os.listdir(path)):
        with open(os.path.join(path, name), "rb") as file:
            vectors[name] = base64.b64encode(file.read()).decode()
    return json.dumps(vectors)


# Returns the bytes of the members of the zip archive the suffixes name.
def zip_read(path: str, suffixes: list[str]) -> list[bytes]:
    with zipfile.ZipFile(path) as archive:
        names = [
            info.filename for info in archive.infolist() if not info.is_dir()
        ]
        return [
            archive.read(member_find(names, suffix)) for suffix in suffixes
        ]


# Builds the page the command line names from its template, printing its hex.
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build build/NAME.html from the template"
        " html/TEMPLATE.html, the test bundle tsc compiles from ts/, the"
        " vectors, written anew into build/vectors/, and the archives of"
        " third_party/, and print its SHA-256."
    )
    parser.add_argument(
        "template", help="the template's file name in html/ without .html"
    )
    parser.add_argument(
        "name", help="the page's file name in build/ without .html"
    )
    arguments = parser.parse_args()
    print(page_build(arguments.template, arguments.name))


if __name__ == "__main__":
    main()
