# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests page_build.py with the real tsc, a later suite that waits only on the
# SQLite wasm and xterm.js archives, tsc being approved: a python3 child for
# each template, html/test.html and html/headless.html, builds its page from
# the real html/, ts/, i18n/en-US.json and the archives third_party_fetch.py
# places in third_party/, under a name of this run, removed after. Each child
# prints its page's SHA-256, and each page holds the bundle that tsc compiled
# by ts/tsconfig.test.json, the strings table in place, and the members it
# takes from the two archives the gold lists for the pins. Each page is its
# template with each marker replaced by its piece, the same pieces for both:
# that bundle, html/engine.css, the vectors written anew into build/vectors/,
# SQLite's glue and its wasm as base64, and xterm.js and its css.

import base64, harness, hashlib, json, os, page_build, subprocess, sys
import unittest, uuid
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the page is built.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The page templates.
_HTML_PATH = os.path.join(_ROOT_PATH, "html")

# The extension of a template and of the page built from it.
_PAGE_EXTENSION = ".html"

# The two templates, each built into a page of its own.
_TEMPLATES = ("test", "headless")

# The script the child runs, beside this file.
_SCRIPT_PATH = os.path.join(_ROOT_PATH, "python", "page_build.py")

# The configuration whose bundle the page carries, the test bundle.
_TEST_CONFIG = os.path.join(_ROOT_PATH, "ts", "tsconfig.test.json")

# The strings table, which takes the place of its identifier in the bundle.
_TABLE_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# The engine's style, which every page carries.
_ENGINE_CSS_PATH = os.path.join(_HTML_PATH, "engine.css")

# The vectors each build writes anew, which every page carries.
_VECTORS_PATH = os.path.join(_BUILD_PATH, "vectors")

# The archives `third_party_fetch.py` places.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The id of the gold's list of the archives the page reads, the pins' names.
_ARCHIVES_ID = "python.test_third_party_fetch.archives_read"

# SQLite's JavaScript glue, by the end of its path inside its archive.
_SQLITE_JS = "jswasm/sqlite3.js"

# SQLite's WebAssembly, by the end of its path inside its archive.
_SQLITE_WASM = "jswasm/sqlite3.wasm"

# The `xterm.js` script inside its package archive.
_XTERM_JS = "package/lib/xterm.js"

# The `xterm.js` style inside its package archive.
_XTERM_CSS = "package/css/xterm.css"


# Returns the path of the bundle that tsc compiles by the test config.
def bundle_named() -> str:
    with open(_TEST_CONFIG, encoding="utf-8") as config_file:
        config: dict[str, Any] = json.load(config_file)
    out_file: str = config["compilerOptions"]["outFile"]
    return os.path.join(os.path.dirname(_TEST_CONFIG), out_file)


# Returns the paths of the gold's two archives, the SQLite one first.
def archives_named() -> tuple[str, str]:
    names: list[str] = harness.gold_get(_ARCHIVES_ID)
    sqlite_name, xterm_name = names
    return (
        os.path.join(_THIRD_PARTY_PATH, sqlite_name),
        os.path.join(_THIRD_PARTY_PATH, xterm_name),
    )


# Returns each marker's piece, read from the files the builds read.
def pieces_read() -> dict[str, str]:
    sqlite_path, xterm_path = archives_named()
    glue, wasm = page_build.zip_read(sqlite_path, [_SQLITE_JS, _SQLITE_WASM])
    script, style = page_build.tar_read(xterm_path, [_XTERM_JS, _XTERM_CSS])
    bundle = page_build.text_read(bundle_named())
    table = page_build.text_read(_TABLE_PATH)
    return {
        "XSJS_BUILD_BUNDLE": page_build.table_substitute(bundle, table),
        "XSJS_BUILD_ENGINE_CSS": page_build.text_read(_ENGINE_CSS_PATH),
        "XSJS_BUILD_SQLITE3_JS": glue.decode("utf-8"),
        "XSJS_BUILD_SQLITE3_WASM": base64.b64encode(wasm).decode(),
        "XSJS_BUILD_TEST_VECTORS": page_build.vectors_json(_VECTORS_PATH),
        "XSJS_BUILD_XTERM_CSS": style.decode("utf-8"),
        "XSJS_BUILD_XTERM_JS": script.decode("utf-8"),
    }


# One page of each template built by a child with the real tsc.
class TestBuild(unittest.TestCase):
    # What each child printed, and the page it built, by template.
    printed: dict[str, bytes]
    page_paths: dict[str, str]

    # Builds each page in a child, under a name of this run, removed after.
    @classmethod
    def setUpClass(cls) -> None:
        cls.printed = {}
        cls.page_paths = {}
        run = uuid.uuid4().hex
        for template in _TEMPLATES:
            name = f"page_build_tsc-{template}-{run}"
            completed = subprocess.run(
                [sys.executable, _SCRIPT_PATH, template, name],
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"page_build.py {template} exited with"
                    f" {completed.returncode}: "
                    + completed.stderr.decode("utf-8", "replace")
                )
            page_path = os.path.join(_BUILD_PATH, name + _PAGE_EXTENSION)
            cls.addClassCleanup(os.remove, page_path)
            cls.page_paths[template] = page_path
            cls.printed[template] = completed.stdout

    # The template and the name build that page, and the child prints its hex.
    def test_command_printed(self) -> None:
        for template in _TEMPLATES:
            with open(self.page_paths[template], "rb") as file:
                digest = hashlib.sha256(file.read()).hexdigest()
            self.assertEqual(self.printed[template], (digest + "\n").encode())

    # Each page holds the bundle of the test config, the table in place.
    def test_bundle_test(self) -> None:
        bundle_path = bundle_named()
        bundle = page_build.text_read(bundle_path)
        table = page_build.text_read(_TABLE_PATH)
        piece = page_build.table_substitute(bundle, table)
        for template in _TEMPLATES:
            page = page_build.text_read(self.page_paths[template])
            # Checked by `in`, so that a failure prints no page of megabytes.
            self.assertTrue(piece in page, (template, bundle_path))

    # Each page holds the members of the gold's two archives.
    def test_archives_named(self) -> None:
        sqlite_path, xterm_path = archives_named()
        glue = page_build.zip_read(sqlite_path, [_SQLITE_JS])[0]
        script = page_build.tar_read(xterm_path, [_XTERM_JS])[0]
        for template in _TEMPLATES:
            page = page_build.text_read(self.page_paths[template])
            self.assertTrue(glue.decode("utf-8") in page, sqlite_path)
            self.assertTrue(script.decode("utf-8") in page, xterm_path)

    # Each page is its template filled from the same pieces, read here.
    def test_templates_filled(self) -> None:
        pieces = pieces_read()
        for template in _TEMPLATES:
            template_path = os.path.join(
                _HTML_PATH, template + _PAGE_EXTENSION
            )
            shell = page_build.text_read(template_path)
            filled = page_build.markers_fill(shell, pieces)
            page = page_build.text_read(self.page_paths[template])
            # Compared by `==`, so that a failure prints no page of megabytes.
            self.assertTrue(page == filled, template_path)
