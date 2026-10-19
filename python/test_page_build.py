# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of page_build.py that start no program: the strings table
# substitution, the archive member lookup by path suffix, the base64 of the
# vectors and the wasm, the template markers and the check of each piece, and
# the hash of the page written. No test starts tsc.

import base64, hashlib, io, json, os, page_build, tarfile, tempfile, unittest
import zipfile

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The page templates.
_HTML_PATH = os.path.join(_ROOT_PATH, "html")

# The hex digest of the bytes `abc`, the example of `FIPS 180-2`.
_ABC_SHA256 = (
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
)

# The markers both templates hold.
_PAGE_MARKERS = [
    "XSJS_BUILD_BUNDLE",
    "XSJS_BUILD_ENGINE_CSS",
    "XSJS_BUILD_SQLITE3_JS",
    "XSJS_BUILD_SQLITE3_WASM",
    "XSJS_BUILD_XTERM_CSS",
    "XSJS_BUILD_XTERM_JS",
]

# The marker only the test template holds.
_VECTORS_MARKER = "XSJS_BUILD_TEST_VECTORS"


# Writes a gzipped tar of each member, a name ending in a slash being a folder.
def tar_write(path: str, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            if name.endswith("/"):
                info.type = tarfile.DIRTYPE
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


# Writes a zip of each member, a name ending in a slash being a folder.
def zip_write(path: str, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)


# The strings table put in place of its one identifier, and the refusals.
class TestTable(unittest.TestCase):
    # The identifier is replaced by the JSON text, unmodified.
    def test_table_replaced(self) -> None:
        table = '{"page.title": "{0} of {1}"}\n'
        bundle = "ui_strings.table = Object.freeze(I18N_TABLE_JSON);\n"
        self.assertEqual(
            page_build.table_substitute(bundle, table),
            "ui_strings.table = Object.freeze(" + table + ");\n",
        )

    # Backslashes in the JSON text reach the bundle unchanged.
    def test_backslash_kept(self) -> None:
        table = r'{"a": "\\1 \\g<0>"}'
        self.assertEqual(
            page_build.table_substitute("x = I18N_TABLE_JSON;", table),
            "x = " + table + ";",
        )

    # A longer identifier holding the name is not the identifier.
    def test_identifier_whole(self) -> None:
        bundle = "I18N_TABLE_JSON_OLD; $I18N_TABLE_JSON; I18N_TABLE_JSON;"
        self.assertEqual(
            page_build.table_substitute(bundle, "{}"),
            "I18N_TABLE_JSON_OLD; $I18N_TABLE_JSON; {};",
        )

    # A bundle without the identifier is refused.
    def test_identifier_absent(self) -> None:
        with self.assertRaises(ValueError):
            page_build.table_substitute("x = 1;", "{}")

    # A bundle holding the identifier twice is refused.
    def test_identifier_twice(self) -> None:
        bundle = "I18N_TABLE_JSON; I18N_TABLE_JSON;"
        with self.assertRaises(ValueError):
            page_build.table_substitute(bundle, "{}")

    # A table that does not parse as JSON is refused.
    def test_table_invalid(self) -> None:
        with self.assertRaises(ValueError):
            page_build.table_substitute("I18N_TABLE_JSON;", '{"a": ')


# Archive members found by the end of their path, under a folder or not.
class TestMembers(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # Members under a leading folder are found, folders and the rest ignored.
    def test_zip_prefixed(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "sqlite.zip")
            zip_write(
                path,
                {
                    "sqlite-wasm-3460100/": b"",
                    "sqlite-wasm-3460100/jswasm/": b"",
                    "sqlite-wasm-3460100/jswasm/sqlite3.js": b"glue",
                    "sqlite-wasm-3460100/jswasm/sqlite3.mjs": b"module",
                    "sqlite-wasm-3460100/jswasm/sqlite3.wasm": b"\0asm",
                },
            )
            contents = page_build.zip_read(
                path, ["jswasm/sqlite3.js", "jswasm/sqlite3.wasm"]
            )
        self.assertEqual(contents, [b"glue", b"\0asm"])

    # A member at the top of the archive is found by its whole name.
    def test_zip_bare(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "sqlite.zip")
            zip_write(path, {"jswasm/sqlite3.js": b"glue"})
            contents = page_build.zip_read(path, ["jswasm/sqlite3.js"])
        self.assertEqual(contents, [b"glue"])

    # Two members ending in the suffix are refused.
    def test_zip_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "sqlite.zip")
            zip_write(
                path,
                {"a/jswasm/sqlite3.js": b"a", "b/jswasm/sqlite3.js": b"b"},
            )
            with self.assertRaises(LookupError):
                page_build.zip_read(path, ["jswasm/sqlite3.js"])

    # A suffix that starts inside a folder name is no match, and is refused.
    def test_zip_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "sqlite.zip")
            zip_write(path, {"xjswasm/sqlite3.js": b"x"})
            with self.assertRaises(LookupError):
                page_build.zip_read(path, ["jswasm/sqlite3.js"])

    # The package members of a gzipped tar are found, folders ignored.
    def test_tar_package(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "xterm.tgz")
            tar_write(
                path,
                {
                    "package/": b"",
                    "package/lib/": b"",
                    "package/lib/xterm.js": b"script",
                    "package/css/xterm.css": b"style",
                    "package/package.json": b"{}",
                },
            )
            contents = page_build.tar_read(
                path, ["package/lib/xterm.js", "package/css/xterm.css"]
            )
        self.assertEqual(contents, [b"script", b"style"])

    # A tar without the member is refused.
    def test_tar_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "xterm.tgz")
            tar_write(path, {"package/lib/xterm.mjs": b"module"})
            with self.assertRaises(LookupError):
                page_build.tar_read(path, ["package/lib/xterm.js"])


# The vectors as one JSON object of base64 text by file name.
class TestVectors(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # Every file is carried, sorted by name, and decodes to its bytes.
    def test_vectors_decoded(self) -> None:
        files = {"b.jslb": b'{"0":{"t":"x"}}\r\x00\xff', "a.json": b"{}"}
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            for name, data in files.items():
                with open(os.path.join(scratch, name), "wb") as file:
                    file.write(data)
            text = page_build.vectors_json(scratch)
        vectors: dict[str, str] = json.loads(text)
        self.assertEqual(list(vectors), ["a.json", "b.jslb"])
        for name, encoded in vectors.items():
            decoded = base64.b64decode(encoded, validate=True)
            self.assertEqual(decoded, files[name])

    # An empty folder gives an empty object.
    def test_vectors_empty(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            self.assertEqual(page_build.vectors_json(scratch), "{}")


# The build markers of the templates, each replaced once in one pass.
class TestMarkers(unittest.TestCase):
    # Each marker takes its piece, and a piece is not searched for markers.
    def test_markers_filled(self) -> None:
        template = (
            "<style>XSJS_BUILD_ENGINE_CSS</style>"
            "<script>XSJS_BUILD_BUNDLE</script>"
        )
        pieces = {
            "XSJS_BUILD_BUNDLE": "XSJS_BUILD_ENGINE_CSS;",
            "XSJS_BUILD_ENGINE_CSS": "body {}",
        }
        self.assertEqual(
            page_build.markers_fill(template, pieces),
            "<style>body {}</style><script>XSJS_BUILD_ENGINE_CSS;</script>",
        )

    # A marker the template lacks is refused.
    def test_marker_absent(self) -> None:
        pieces = {"XSJS_BUILD_BUNDLE": "", "XSJS_BUILD_XTERM_JS": ""}
        with self.assertRaises(ValueError):
            page_build.markers_fill("XSJS_BUILD_BUNDLE", pieces)

    # A marker the template holds twice is refused.
    def test_marker_twice(self) -> None:
        template = "XSJS_BUILD_BUNDLE XSJS_BUILD_BUNDLE"
        with self.assertRaises(ValueError):
            page_build.markers_fill(template, {"XSJS_BUILD_BUNDLE": ""})

    # A marker in the template that no piece names is refused.
    def test_marker_unknown(self) -> None:
        template = "XSJS_BUILD_BUNDLE XSJS_BUILD_OTHER"
        with self.assertRaises(ValueError):
            page_build.markers_fill(template, {"XSJS_BUILD_BUNDLE": ""})

    # The wasm bytes reach the page as base64 inside the string literal.
    def test_wasm_base64(self) -> None:
        wasm = bytes(range(256))
        template = 'var sqlite3_wasm_base64 = "XSJS_BUILD_SQLITE3_WASM";'
        piece = base64.b64encode(wasm).decode()
        page = page_build.page_merge(
            template, {"XSJS_BUILD_SQLITE3_WASM": piece}
        )
        self.assertEqual(
            base64.b64decode(page.split('"')[1], validate=True), wasm
        )

    # The marker decides which element a piece is checked against.
    def test_merge_checked(self) -> None:
        template = (
            "<style>XSJS_BUILD_XTERM_CSS</style>"
            "<script>XSJS_BUILD_XTERM_JS</script>"
        )
        page_build.page_merge(
            template,
            {"XSJS_BUILD_XTERM_CSS": "</script>", "XSJS_BUILD_XTERM_JS": ""},
        )
        with self.assertRaises(ValueError):
            page_build.page_merge(
                template,
                {
                    "XSJS_BUILD_XTERM_CSS": "",
                    "XSJS_BUILD_XTERM_JS": "</script>",
                },
            )

    # The engine template holds each page marker once.
    def test_template_engine(self) -> None:
        path = os.path.join(_HTML_PATH, "engine.html")
        pieces = {marker: "" for marker in _PAGE_MARKERS}
        page = page_build.markers_fill(page_build.text_read(path), pieces)
        self.assertNotIn("XSJS_BUILD_", page)

    # The test template holds each page marker and the vectors marker once.
    def test_template_tests(self) -> None:
        path = os.path.join(_HTML_PATH, "test.html")
        pieces = {marker: "" for marker in [*_PAGE_MARKERS, _VECTORS_MARKER]}
        page = page_build.markers_fill(page_build.text_read(path), pieces)
        self.assertNotIn("XSJS_BUILD_", page)


# Pieces that would change meaning as the raw text of their element.
class TestEmbed(unittest.TestCase):
    # A script piece holding its end tag, in any case, is refused.
    def test_script_end(self) -> None:
        with self.assertRaises(ValueError):
            page_build.embed_check("piece", 'x = "</SCRIPT >";', "script")

    # A style piece holding its end tag is refused, a script end tag is not.
    def test_style_end(self) -> None:
        page_build.embed_check("piece", 'a { content: "</script>"; }', "style")
        with self.assertRaises(ValueError):
            page_build.embed_check("piece", "a {} </Style>", "style")

    # A comment opener with a script start tag is refused, alone it is not.
    def test_comment_script(self) -> None:
        page_build.embed_check("piece", 'x = "<!--";', "script")
        with self.assertRaises(ValueError):
            page_build.embed_check("piece", 'x = "<!-- <script>";', "script")

    # A `NUL` character is refused.
    def test_nul_refused(self) -> None:
        with self.assertRaises(ValueError):
            page_build.embed_check("piece", 'x = "\0";', "script")


# The page written as `UTF-8` and the hex digest of the file.
class TestHash(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # The digest of `abc` is the example of `FIPS 180-2`.
    def test_hash_abc(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "page.html")
            digest = page_build.page_write(path, "abc")
            with open(path, "rb") as file:
                data = file.read()
        self.assertEqual(data, b"abc")
        self.assertEqual(digest, _ABC_SHA256)

    # A character beyond ASCII is written and hashed as `UTF-8`.
    def test_hash_utf8(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "page.html")
            digest = page_build.page_write(path, "caf" + chr(0xE9))
            with open(path, "rb") as file:
                data = file.read()
        self.assertEqual(data, b"caf\xc3\xa9")
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
