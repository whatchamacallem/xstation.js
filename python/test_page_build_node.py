# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the Node bundle of page_build.py with the real tsc and node, a split
# suite of page_build that waits on no program, both being approved, and on
# no archive. One bundle is built into a scratch directory under build/ and
# read by each test: the path returned, the strict line first, then
# test_vectors defined as the page defines it, from the vectors written anew
# into the scratch directory, then the bundle with the strings table in
# place once. node runs it on stdio: the first line, tap.start with i 101
# built as bootstrap.py builds it, is answered with an Empty reply, then the
# TAP stream of the block named comes in tap.line pushes, read by the TAP
# consumer, and node exits 0; a first line of another type exits 1, with
# nothing written back. A failed compile of a scratch project raises, tsc's
# output in its cause.

import base64, harness, jslb, json, os, page_build, shutil, subprocess
import tap_consumer, tempfile, unittest
from typing import NoReturn, cast

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The strings table, which takes the place of its identifier in the bundle.
_TABLE_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# Where the bundle goes in a build directory, as the config's `outFile` says.
_BUNDLE_PLACE = os.path.join("ts", "node.js")

# The folder of the build directory that holds the vectors.
_VECTORS_NAME = "vectors"

# The first line of the bundle, the strict line.
_STRICT_LINE = '"use strict";'

# The start of the second line, which defines the vectors.
_VECTORS_START = "var test_vectors = "

# The end of the second line.
_VECTORS_END = ";"

# The block the realm runs, whose tests read `test_vectors`.
_BLOCK = "test_utility"

# The type of the first line.
_FIRST_TYPE = "tap.start"

# The fixed id of the first line.
_FIRST_ID = 101

# A type the realm refuses as the first line.
_OTHER_TYPE = "echo"

# The type of each line of the stream the realm sends.
_LINE_TYPE = "tap.line"

# The language each line of the stream names.
_LANGUAGE = "typescript"

# What the realm writes to stderr when the first line is not `tap.start`.
_FIRST_REFUSED = b"Error: the first line is not tap.start with i 101"

# The one file of a scratch project that tsc refuses.
_BROKEN_NAME = "broken.ts"

# The configuration of that project.
_BROKEN_CONFIG = {
    "compilerOptions": {
        "module": "none",
        "noEmitOnError": True,
        "strict": True,
        "target": "ES2022",
    },
    "files": [_BROKEN_NAME],
}

# The text of that file, which sets a number to text.
_BROKEN_SOURCE = 'const count: number = "one";\n'

# The diagnostic tsc writes for that file.
_BROKEN_ERROR = (
    "broken.ts(1,7): error TS2322: Type 'string' is not assignable to type"
    " 'number'."
)


# Refuses a blob that streams, as the realm sends none that large.
def sink_refuse(header: jslb.Object) -> NoReturn:
    raise AssertionError(f"a blob came that streams: {header}")


# Returns the bytes of a first line as `bootstrap.py` writes it in debug mode.
def start_bytes(line_type: str) -> bytes:
    header = jslb.header_make(line_type, id=_FIRST_ID, full=True)
    tests = jslb.json_decode(json.dumps(harness.gold_copy()))
    line = jslb.line_make(
        header, [], settings=harness.settings_copy(), test_settings=tests
    )
    (piece,) = jslb.line_encode(line)
    return cast(bytes, piece)


# Runs node on the bundle and the block, the bytes on stdin, to its end.
def realm_run(path: str, data: bytes) -> subprocess.CompletedProcess[bytes]:
    node_path = shutil.which("node")
    if node_path is None:
        raise FileNotFoundError("node is not on PATH")
    return subprocess.run(
        [node_path, path, _BLOCK], input=data, capture_output=True, check=False
    )


# One Node bundle built into a scratch directory, read by each test.
class TestBundle(unittest.TestCase):
    # The scratch directory, the bundle's path, and the bundle's text.
    scratch: str
    path: str
    text: str

    # Builds the bundle in a scratch directory under `build`, removed after.
    @classmethod
    def setUpClass(cls) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        cls.addClassCleanup(scratch.cleanup)
        cls.scratch = scratch.name
        cls.path = page_build.node_build(scratch.name)
        cls.text = page_build.text_read(cls.path)

    # The path returned is the bundle's place in the scratch directory.
    def test_path_returned(self) -> None:
        self.assertEqual(self.path, os.path.join(self.scratch, _BUNDLE_PLACE))
        self.assertTrue(os.path.isfile(self.path))

    # The strict line comes first, so the whole bundle is strict code.
    def test_strict_first(self) -> None:
        self.assertEqual(self.text.split("\n", 1)[0], _STRICT_LINE)

    # The second line defines the vectors written anew, each file as base64.
    def test_vectors_defined(self) -> None:
        line = self.text.split("\n", 2)[1]
        self.assertTrue(line.startswith(_VECTORS_START), line[:80])
        self.assertTrue(line.endswith(_VECTORS_END), line[-80:])
        text = line.removeprefix(_VECTORS_START).removesuffix(_VECTORS_END)
        vectors: dict[str, str] = json.loads(text)
        folder = os.path.join(self.scratch, _VECTORS_NAME)
        names = sorted(os.listdir(folder))
        self.assertTrue(names)
        self.assertEqual(list(vectors), names)
        for name, encoded in vectors.items():
            with open(os.path.join(folder, name), "rb") as file:
                data = file.read()
            decoded = base64.b64decode(encoded, validate=True)
            self.assertEqual(decoded, data, name)

    # The bundle after the two lines holds the table once, its identifier gone.
    def test_table_once(self) -> None:
        bundle = self.text.split("\n", 2)[2]
        table = page_build.text_read(_TABLE_PATH)
        self.assertEqual(bundle.count(table), 1)
        self.assertNotIn("I18N_TABLE_JSON", bundle)

    # The realm answers `tap.start`, sends the passing block, and exits 0.
    def test_block_run(self) -> None:
        completed = realm_run(self.path, start_bytes(_FIRST_TYPE))
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(completed.returncode, 0)
        decoder = jslb.LineDecoder(
            harness.setting_get("line_max"),
            harness.setting_get("blob_max"),
            harness.setting_get("overflow_bytes"),
            sink_refuse,
        )
        reply, *pushes = decoder.bytes_feed(completed.stdout)
        self.assertTrue(decoder.idle())
        answer = jslb.header_make(_FIRST_TYPE, reply=_FIRST_ID, full=True)
        self.assertEqual(reply, jslb.line_make(answer, []))
        texts: list[str] = []
        for push in pushes:
            self.assertEqual(push[0], jslb.header_make(_LINE_TYPE, full=True))
            payload = jslb.payload_of(push)
            self.assertEqual(payload["language"], _LANGUAGE)
            texts.append(payload["text"])
        stats = tap_consumer.document_stats("\n".join(texts) + "\n")
        self.assertTrue(stats.well_formed)
        self.assertEqual(stats.failed, 0)
        self.assertEqual(texts[-2:], [f"ok 1 - {_BLOCK}", "1..1"])

    # A first line of another type is refused: nothing back, and exit 1.
    def test_first_refused(self) -> None:
        completed = realm_run(self.path, start_bytes(_OTHER_TYPE))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, b"")
        self.assertIn(_FIRST_REFUSED, completed.stderr)


# A project tsc refuses, compiled into a scratch directory.
class TestCompile(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # The compile raises, tsc's exit code named and its output in the cause.
    def test_compile_failed(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            config_path = os.path.join(scratch, "tsconfig.json")
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(_BROKEN_CONFIG, file)
            source_path = os.path.join(scratch, _BROKEN_NAME)
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(_BROKEN_SOURCE)
            out_path = os.path.join(scratch, "broken.js")
            with self.assertRaises(RuntimeError) as caught:
                page_build.bundle_compile(config_path, out_path)
            self.assertFalse(os.path.exists(out_path))
        self.assertEqual(
            str(caught.exception),
            f"tsc exited with 1 compiling {config_path}",
        )
        cause = caught.exception.__cause__
        self.assertIsInstance(cause, RuntimeError)
        self.assertIn(_BROKEN_ERROR, str(cause))
