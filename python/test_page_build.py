# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the parts of page_build.py that start no program but python3 and call
# into no project module but jslb.py, whose suite has passed: the strings
# table substitution, the archive member lookup by path suffix, the base64 of
# the vectors and the wasm, the gold's one line and its copy at another path
# with other gold, a suite's gold file of no object refused, the markers of
# the three templates, html/test.html, html/headless.html and
# html/engine.html, and the check of each piece, the headless template
# holding the head and the scripts of the test template in their order, its
# own entry last, and no pre for the TAP stream, the engine template holding
# those scripts with its own entry last, the body of the engine page's layout
# and no pre, a template html/ lacks refused with no page written, the
# command line refusing an option, or a name with no template, before
# anything is built, run as a python3 child, and the hash of the page written.
# Forked children, whose lines the count sees, run the script as the program
# and refuse a PATH with no tsc. The config of the API text lists exactly the
# files of API/ts and leaves their check on. No test starts tsc.

import base64, hashlib, html.parser, io, json, os, page_build, runpy, signal
import subprocess, sys, tarfile, tempfile, traceback, unittest, zipfile
from collections.abc import Callable
from typing import Any

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

# The markers of the page's pieces beside the vectors.
_PAGE_MARKERS = [
    "XSJS_BUILD_BUNDLE",
    "XSJS_BUILD_ENGINE_CSS",
    "XSJS_BUILD_SQLITE3_JS",
    "XSJS_BUILD_SQLITE3_WASM",
    "XSJS_BUILD_TEST_GOLD",
    "XSJS_BUILD_XTERM_CSS",
    "XSJS_BUILD_XTERM_JS",
]

# The marker of the vectors, which each template holds too.
_VECTORS_MARKER = "XSJS_BUILD_TEST_VECTORS"

# The extension of a template and of the page built from it.
_PAGE_EXTENSION = ".html"

# The template of the ttyd test page.
_TEST_TEMPLATE = "test"

# The template of the headless page of group B.
_HEADLESS_TEMPLATE = "headless"

# The template of the engine page.
_ENGINE_TEMPLATE = "engine"

# A template `html/` lacks.
_ABSENT_TEMPLATE = "page_build_absent"

# The last script of the test template, its entry on both threads.
_TEST_ENTRY = "test_all.suites_run();"

# The last script of the headless template, in place of the test entry.
_HEADLESS_ENTRY = "test_headless.realm_open();"

# The last script of the engine template, in place of the test entry.
_ENGINE_ENTRY = "engine.engine_start();"

# The start tag of the test template's element for the TAP stream.
_OUTPUT_TAG = ("pre", [("id", "tap_output")])

# The engine template's body before its scripts: each depth and start tag.
_ENGINE_BODY: list[tuple[int, tuple[str, list[tuple[str, str | None]]]]] = [
    (2, ("canvas", [("id", "image"), ("hidden", None)])),
    (2, ("div", [("id", "debug")])),
    (3, ("div", [("id", "overlays")])),
    (2, ("div", [("id", "band")])),
    (3, ("p", [("id", "subtitle")])),
    (3, ("form", [])),
    (4, ("input", [("id", "input"), ("disabled", None)])),
    (3, ("div", [("id", "permit")])),
]

# The start tag of a template's head.
_HEAD_START = "<head>"

# The end tag of a template's head.
_HEAD_END = "</head>"

# The script whose command line the tests give, beside this file.
_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "page_build.py"
)

# The name of the page a refused command line names, which is never built.
_REFUSED_NAME = "page_build_refused"

# The page of that name, which no test may leave written.
_REFUSED_PATH = os.path.join(_BUILD_PATH, _REFUSED_NAME + _PAGE_EXTENSION)

# What a forked child reports when its work returned.
_ENDING_RETURNED = "returned"

# The configuration a compile names, which a `PATH` with no tsc never reads.
_UNREAD_CONFIG = "tsconfig.json"

# The bundle a compile names, which a `PATH` with no tsc never writes.
_UNWRITTEN_NAME = "bundle.js"

# The last line of the traceback of a `PATH` with no tsc.
_TSC_ABSENT = (
    "FileNotFoundError: tsc, the TypeScript compiler, is not on PATH\n"
)

# The line of a traceback that holds the frame of the command line's function.
_MAIN_FRAME = ", in main\n"

# A suite's gold file by its file name, in a scratch directory.
_SUITE_NAME = "test_setting_test_a.json"

# The configuration of the API text, which names each of its files.
_API_CONFIG_PATH = os.path.join(_ROOT_PATH, "ts", "tsconfig.api.json")

# The configuration that one extends, as that one names it.
_BASE_CONFIG_NAME = "./tsconfig.json"

# The configuration that one extends, by its place in the checkout.
_BASE_CONFIG_PATH = os.path.join(_ROOT_PATH, "ts", "tsconfig.json")

# The options of the API text's own configuration.
_API_OPTIONS = {"noEmit": True}

# The directory of the API text.
_API_TEXT_PATH = os.path.join(_ROOT_PATH, "API", "ts")

# The start of each file of the API text, as its configuration names it.
_API_FILE_START = "../API/ts/"

# The option that would leave every `.d.ts` file unchecked.
_SKIP_OPTION = "skipLibCheck"


# The start tags of a template in order, their depths, and each script's text.
class TemplateReader(html.parser.HTMLParser):
    # Reads the whole text of the template.
    def __init__(self, text: str) -> None:
        super().__init__()
        self.tags: list[tuple[str, list[tuple[str, str | None]]]] = []
        self.depths: list[int] = []
        self.scripts: list[str] = []
        self._inside = False
        self._open = 0
        self.feed(text)
        self.close()

    # Keeps each start tag with its attributes, and opens a script's text.
    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.tags.append((tag, attrs))
        self.depths.append(self._open)
        self._open += 1
        if tag == "script":
            self._inside = True
            self.scripts.append("")

    # Closes an element, and a script's text at its end tag.
    def handle_endtag(self, tag: str) -> None:
        self._open -= 1
        if tag == "script":
            self._inside = False

    # Adds the text inside a script to that script's text.
    def handle_data(self, data: str) -> None:
        if self._inside:
            self.scripts[-1] += data


# In the forked child: runs the work, writes how it ended, kills itself.
def child_end(work: Callable[[], None], write_fd: int) -> None:
    try:
        try:
            work()
            ending = _ENDING_RETURNED
        except BaseException:
            ending = traceback.format_exc()
        with os.fdopen(write_fd, "w", encoding="utf-8") as file:
            file.write(ending)
    finally:
        os.kill(os.getpid(), signal.SIGKILL)


# Runs the work in a forked child, whose lines count, returning how it ended.
def child_run(case: unittest.TestCase, work: Callable[[], None]) -> str:
    read_fd, write_fd = os.pipe()
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        child_end(work, write_fd)
    os.close(write_fd)
    with os.fdopen(read_fd, encoding="utf-8") as file:
        ending = file.read()
    status = os.waitpid(pid, 0)[1]
    case.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGKILL)
    return ending


# In a forked child: runs the script as the program, on the arguments given.
def script_run(arguments: list[str]) -> None:
    sys.argv = [_SCRIPT_PATH, *arguments]
    runpy.run_path(_SCRIPT_PATH, run_name="__main__")


# In a forked child: compiles with the folder alone on `PATH`.
def tsc_unfound(folder: str) -> None:
    os.environ["PATH"] = folder
    out_path = os.path.join(folder, _UNWRITTEN_NAME)
    page_build.bundle_compile(_UNREAD_CONFIG, out_path)


# In a forked child: checks the API text with the folder alone on `PATH`.
def api_unfound(folder: str) -> None:
    os.environ["PATH"] = folder
    page_build.api_check()


# Returns the object of the `tsc` configuration.
def config_read(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        config: dict[str, Any] = json.load(file)
    return config


# Runs the command line in a python3 child with the arguments, to its end.
def command_run(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, _SCRIPT_PATH, *arguments],
        capture_output=True,
        check=False,
    )


# Returns the head of the text, from its start tag to its end tag.
def head_cut(text: str) -> str:
    return text[text.index(_HEAD_START) : text.index(_HEAD_END)]


# Returns the text of the template of `html/` by its name.
def template_text(name: str) -> str:
    return page_build.text_read(
        os.path.join(_HTML_PATH, name + _PAGE_EXTENSION)
    )


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
        with self.assertRaises(ValueError) as caught:
            page_build.table_substitute("x = 1;", "{}")
        self.assertEqual(
            str(caught.exception),
            "I18N_TABLE_JSON occurs 0 times in the bundle, not once",
        )

    # A bundle holding the identifier twice is refused.
    def test_identifier_twice(self) -> None:
        bundle = "I18N_TABLE_JSON; I18N_TABLE_JSON;"
        with self.assertRaises(ValueError) as caught:
            page_build.table_substitute(bundle, "{}")
        self.assertEqual(
            str(caught.exception),
            "I18N_TABLE_JSON occurs 2 times in the bundle, not once",
        )

    # A table that does not parse as JSON is refused.
    def test_table_invalid(self) -> None:
        with self.assertRaises(ValueError) as caught:
            page_build.table_substitute("I18N_TABLE_JSON;", '{"a": ')
        self.assertEqual(
            str(caught.exception), "Expecting value: line 1 column 7 (char 6)"
        )


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
            with self.assertRaises(LookupError) as caught:
                page_build.zip_read(path, ["jswasm/sqlite3.js"])
        self.assertEqual(
            str(caught.exception),
            "jswasm/sqlite3.js: archive members ['a/jswasm/sqlite3.js',"
            " 'b/jswasm/sqlite3.js'], not one",
        )

    # A suffix that starts inside a folder name is no match, and is refused.
    def test_zip_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "sqlite.zip")
            zip_write(path, {"xjswasm/sqlite3.js": b"x"})
            with self.assertRaises(LookupError) as caught:
                page_build.zip_read(path, ["jswasm/sqlite3.js"])
        self.assertEqual(
            str(caught.exception),
            "jswasm/sqlite3.js: archive members [], not one",
        )

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
            with self.assertRaises(LookupError) as caught:
                page_build.tar_read(path, ["package/lib/xterm.js"])
        self.assertEqual(
            str(caught.exception),
            "package/lib/xterm.js: archive members [], not one",
        )


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


# The gold as one line of JSON, and a built page copied with other gold.
class TestGold(unittest.TestCase):
    # Makes the checkout's `build/` for the pages.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # Writes a page into `build/` and returns its name, removed after.
    def page_make(self, page: str) -> str:
        with tempfile.NamedTemporaryFile(
            "w", suffix=_PAGE_EXTENSION, dir=_BUILD_PATH, delete=False
        ) as file:
            file.write(page)
        self.addCleanup(os.remove, file.name)
        return os.path.basename(file.name).removesuffix(_PAGE_EXTENSION)

    # The gold is one line of JSON with no space between its tokens.
    def test_gold_line(self) -> None:
        gold = {"typescript": {"test_a": {"text": "a\nb", "n": [1, 2]}}}
        text = page_build.gold_json(gold)
        self.assertNotIn("\n", text)
        self.assertEqual(json.loads(text), gold)
        self.assertEqual(text, json.dumps(gold, separators=(",", ":")))

    # Gold with a key but the TypeScript language's is refused.
    def test_gold_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            page_build.gold_json({"typescript": {}, "python": {}})
        self.assertEqual(
            str(caught.exception),
            "the gold's keys ['typescript', 'python'], not typescript",
        )

    # A suite's gold file that holds no JSON object is refused by its path.
    def test_suite_refused(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, _SUITE_NAME)
            with open(path, "w", encoding="utf-8") as file:
                file.write("[]")
            with self.assertRaises(ValueError) as caught:
                page_build.gold_read(scratch)
        self.assertEqual(
            str(caught.exception), f"{path}: holds no JSON object"
        )

    # The copy is the page with the other gold on its one gold line.
    def test_page_copied(self) -> None:
        head = "<script data-worker>\n"
        tail = "\n</script>\n<script>var other = {};</script>\n"
        name = self.page_make(
            head + '  var test_gold = {"typescript":{}};' + tail
        )
        gold = {"typescript": {"test_a": {"k": 1}}}
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            path = os.path.join(scratch, "copy.html")
            digest = page_build.page_copy(name, path, gold)
            with open(path, "rb") as file:
                data = file.read()
        line = "  var test_gold = " + page_build.gold_json(gold) + ";"
        self.assertEqual(data.decode("utf-8"), head + line + tail)
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    # A page with no gold line, or with two, is refused, and nothing written.
    def test_copy_refused(self) -> None:
        line = "var test_gold = {};\n"
        for count in (0, 2):
            name = self.page_make(line * count)
            with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
                path = os.path.join(scratch, "copy.html")
                with self.assertRaises(ValueError) as caught:
                    page_build.page_copy(name, path, {"typescript": {}})
                self.assertFalse(os.path.exists(path))
            self.assertEqual(
                str(caught.exception),
                f"{name}: {count} lines define test_gold, not one",
            )


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
        with self.assertRaises(ValueError) as caught:
            page_build.markers_fill("XSJS_BUILD_BUNDLE", pieces)
        self.assertEqual(
            str(caught.exception),
            "template markers ['XSJS_BUILD_BUNDLE'], not"
            " ['XSJS_BUILD_BUNDLE', 'XSJS_BUILD_XTERM_JS']",
        )

    # A marker the template holds twice is refused.
    def test_marker_twice(self) -> None:
        template = "XSJS_BUILD_BUNDLE XSJS_BUILD_BUNDLE"
        with self.assertRaises(ValueError) as caught:
            page_build.markers_fill(template, {"XSJS_BUILD_BUNDLE": ""})
        self.assertEqual(
            str(caught.exception),
            "template markers ['XSJS_BUILD_BUNDLE', 'XSJS_BUILD_BUNDLE'], not"
            " ['XSJS_BUILD_BUNDLE']",
        )

    # A marker in the template that no piece names is refused.
    def test_marker_unknown(self) -> None:
        template = "XSJS_BUILD_BUNDLE XSJS_BUILD_OTHER"
        with self.assertRaises(ValueError) as caught:
            page_build.markers_fill(template, {"XSJS_BUILD_BUNDLE": ""})
        self.assertEqual(
            str(caught.exception),
            "template markers ['XSJS_BUILD_BUNDLE', 'XSJS_BUILD_OTHER'], not"
            " ['XSJS_BUILD_BUNDLE']",
        )

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
        with self.assertRaises(ValueError) as caught:
            page_build.page_merge(
                template,
                {
                    "XSJS_BUILD_XTERM_CSS": "",
                    "XSJS_BUILD_XTERM_JS": "</script>",
                },
            )
        self.assertEqual(
            str(caught.exception),
            "XSJS_BUILD_XTERM_JS: holds </script, which ends the element",
        )

    # The test template holds each page marker and the vectors marker once.
    def test_template_tests(self) -> None:
        path = os.path.join(_HTML_PATH, "test.html")
        pieces = {marker: "" for marker in [*_PAGE_MARKERS, _VECTORS_MARKER]}
        page = page_build.markers_fill(page_build.text_read(path), pieces)
        self.assertNotIn("XSJS_BUILD_", page)

    # The headless template holds the same markers once, from the same pieces.
    def test_template_headless(self) -> None:
        pieces = {marker: "" for marker in [*_PAGE_MARKERS, _VECTORS_MARKER]}
        template = template_text(_HEADLESS_TEMPLATE)
        page = page_build.markers_fill(template, pieces)
        self.assertNotIn("XSJS_BUILD_", page)

    # The engine template holds the same markers once, from the same pieces.
    def test_template_engine(self) -> None:
        pieces = {marker: "" for marker in [*_PAGE_MARKERS, _VECTORS_MARKER]}
        template = template_text(_ENGINE_TEMPLATE)
        page = page_build.markers_fill(template, pieces)
        self.assertNotIn("XSJS_BUILD_", page)


# The other templates beside the test template, and a template `html/` lacks.
class TestTemplates(unittest.TestCase):
    # The head of the headless template is that of the test template.
    def test_head_same(self) -> None:
        tests = head_cut(template_text(_TEST_TEMPLATE))
        headless = head_cut(template_text(_HEADLESS_TEMPLATE))
        self.assertEqual(headless, tests)

    # Its elements are those of the test template, but the TAP stream's `pre`.
    def test_elements_same(self) -> None:
        tests = TemplateReader(template_text(_TEST_TEMPLATE)).tags
        headless = TemplateReader(template_text(_HEADLESS_TEMPLATE)).tags
        self.assertIn(_OUTPUT_TAG, tests)
        self.assertEqual(
            headless, [tag for tag in tests if tag != _OUTPUT_TAG]
        )

    # Its scripts are those of the test template in order, its own entry last.
    def test_scripts_same(self) -> None:
        reader = TemplateReader(template_text(_TEST_TEMPLATE))
        tests = [script.strip() for script in reader.scripts]
        reader = TemplateReader(template_text(_HEADLESS_TEMPLATE))
        headless = [script.strip() for script in reader.scripts]
        self.assertEqual(tests[-1], _TEST_ENTRY)
        self.assertEqual(headless, [*tests[:-1], _HEADLESS_ENTRY])

    # The engine template's scripts are the test template's, its entry last.
    def test_engine_scripts(self) -> None:
        reader = TemplateReader(template_text(_TEST_TEMPLATE))
        tests = [script.strip() for script in reader.scripts]
        tags = [tag for tag in reader.tags if tag[0] == "script"]
        reader = TemplateReader(template_text(_ENGINE_TEMPLATE))
        engine = [script.strip() for script in reader.scripts]
        self.assertEqual(engine, [*tests[:-1], _ENGINE_ENTRY])
        self.assertEqual(
            [tag for tag in reader.tags if tag[0] == "script"], tags
        )

    # The engine template's body is the page's layout, its scripts after it.
    def test_engine_body(self) -> None:
        reader = TemplateReader(template_text(_ENGINE_TEMPLATE))
        names = [tag[0] for tag in reader.tags]
        first = names.index("body") + 1
        last = names.index("script")
        self.assertEqual(
            list(zip(reader.depths[first:last], reader.tags[first:last])),
            _ENGINE_BODY,
        )

    # The engine template holds no `pre`, as it shows no TAP stream.
    def test_engine_output(self) -> None:
        tags = TemplateReader(template_text(_ENGINE_TEMPLATE)).tags
        self.assertNotIn("pre", [tag[0] for tag in tags])

    # A template `html/` lacks is refused by name, and no page is written.
    def test_template_absent(self) -> None:
        with self.assertRaises(FileNotFoundError) as caught:
            page_build.page_build(_ABSENT_TEMPLATE, _REFUSED_NAME)
        self.assertEqual(
            caught.exception.filename,
            os.path.join(_HTML_PATH, _ABSENT_TEMPLATE + _PAGE_EXTENSION),
        )
        self.assertFalse(os.path.exists(_REFUSED_PATH))


# The command line, which names the template and the page, in a child.
class TestCommand(unittest.TestCase):
    # The old `--test` option is refused with the usage code 2, unbuilt.
    def test_option_refused(self) -> None:
        completed = command_run([_TEST_TEMPLATE, _REFUSED_NAME, "--test"])
        self.assertEqual(completed.returncode, 2)
        self.assertIn(b"unrecognized arguments: --test", completed.stderr)
        self.assertEqual(completed.stdout, b"")
        self.assertFalse(os.path.exists(_REFUSED_PATH))

    # A name with no template, the command line before the templates, unbuilt.
    def test_name_alone(self) -> None:
        completed = command_run([_REFUSED_NAME])
        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            b"the following arguments are required: name", completed.stderr
        )
        self.assertEqual(completed.stdout, b"")
        self.assertFalse(os.path.exists(_REFUSED_PATH))

    # As the program, the file's last line reaches the build through `main`.
    def test_script_forked(self) -> None:
        arguments = [_ABSENT_TEMPLATE, _REFUSED_NAME]
        ending = child_run(self, lambda: script_run(arguments))
        path = os.path.join(_HTML_PATH, _ABSENT_TEMPLATE + _PAGE_EXTENSION)
        self.assertIn(_MAIN_FRAME, ending)
        self.assertTrue(ending.endswith(f"directory: {path!r}\n"), ending)
        self.assertFalse(os.path.exists(_REFUSED_PATH))


# The compiler looked for on `PATH`, in a forked child that changes its own.
class TestCompiler(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # A `PATH` with no tsc is refused by name, and nothing is written.
    def test_tsc_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            ending = child_run(self, lambda: tsc_unfound(scratch))
            self.assertEqual(os.listdir(scratch), [])
        self.assertTrue(ending.endswith(_TSC_ABSENT), ending)

    # The check of the API text is refused the same way.
    def test_api_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            ending = child_run(self, lambda: api_unfound(scratch))
        self.assertTrue(ending.endswith(_TSC_ABSENT), ending)


# The configuration `page_build.api_check` compiles, read and never compiled.
class TestApiConfig(unittest.TestCase):
    # It lists exactly the files of `API/ts`, each once.
    def test_files_listed(self) -> None:
        listed: list[str] = config_read(_API_CONFIG_PATH)["files"]
        names = os.listdir(_API_TEXT_PATH)
        expected = [_API_FILE_START + name for name in names]
        self.assertEqual(sorted(listed), sorted(expected))

    # It extends the base and emits nothing, its only option.
    def test_options_own(self) -> None:
        config = config_read(_API_CONFIG_PATH)
        self.assertEqual(config["extends"], _BASE_CONFIG_NAME)
        self.assertEqual(config["compilerOptions"], _API_OPTIONS)

    # The base leaves the `.d.ts` files checked, or nothing would be.
    def test_text_checked(self) -> None:
        base = config_read(_BASE_CONFIG_PATH)
        self.assertNotIn(_SKIP_OPTION, base["compilerOptions"])


# Pieces that would change meaning as the raw text of their element.
class TestEmbed(unittest.TestCase):
    # A script piece holding its end tag, in any case, is refused.
    def test_script_end(self) -> None:
        with self.assertRaises(ValueError) as caught:
            page_build.embed_check("piece", 'x = "</SCRIPT >";', "script")
        self.assertEqual(
            str(caught.exception),
            "piece: holds </script, which ends the element",
        )

    # A style piece holding its end tag is refused, a script end tag is not.
    def test_style_end(self) -> None:
        page_build.embed_check("piece", 'a { content: "</script>"; }', "style")
        with self.assertRaises(ValueError) as caught:
            page_build.embed_check("piece", "a {} </Style>", "style")
        self.assertEqual(
            str(caught.exception),
            "piece: holds </style, which ends the element",
        )

    # A comment opener with a script start tag is refused, alone it is not.
    def test_comment_script(self) -> None:
        page_build.embed_check("piece", 'x = "<!--";', "script")
        with self.assertRaises(ValueError) as caught:
            page_build.embed_check("piece", 'x = "<!-- <script>";', "script")
        self.assertEqual(
            str(caught.exception),
            "piece: holds <!-- and <script, which hide the end tag",
        )

    # A `NUL` character is refused.
    def test_nul_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            page_build.embed_check("piece", 'x = "\0";', "script")
        self.assertEqual(
            str(caught.exception),
            "piece: holds NUL, which the HTML parser replaces",
        )


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
