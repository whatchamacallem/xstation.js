# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests page_build.py with the real tsc, a later suite that waits on tsc: a
# python3 child builds one page from the real html/, ts/, i18n/en-US.json
# and the archives third_party_fetch.py places in third_party/, under a name
# of this run, removed after. The child prints the page's SHA-256, and the
# page holds the bundle that tsc compiled by ts/tsconfig.test.json, the
# strings table in place, and the members it takes from the two archives the
# gold lists for the pins.

import hashlib, harness, json, os, page_build, subprocess, sys, unittest, uuid
from typing import Any

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the page is built.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The script the child runs, beside this file.
_SCRIPT_PATH = os.path.join(_ROOT_PATH, "python", "page_build.py")

# The configuration whose bundle the page carries, the test bundle.
_TEST_CONFIG = os.path.join(_ROOT_PATH, "ts", "tsconfig.test.json")

# The strings table, which takes the place of its identifier in the bundle.
_TABLE_PATH = os.path.join(_ROOT_PATH, "i18n", "en-US.json")

# The archives `third_party_fetch.py` places.
_THIRD_PARTY_PATH = os.path.join(_ROOT_PATH, "third_party")

# The id of the gold's list of the archives the page reads, the pins' names.
_ARCHIVES_ID = "python.test_third_party_fetch.archives_read"

# SQLite's JavaScript glue, by the end of its path inside its archive.
_SQLITE_JS = "jswasm/sqlite3.js"

# The `xterm.js` script inside its package archive.
_XTERM_JS = "package/lib/xterm.js"


# One page built by a child with the real tsc, read by each test.
class TestBuild(unittest.TestCase):
    # What the child printed, and the page it built.
    printed: bytes
    page_path: str

    # Builds the page in a child, under a name of this run, removed after.
    @classmethod
    def setUpClass(cls) -> None:
        name = "page_build_tsc-" + uuid.uuid4().hex
        completed = subprocess.run(
            [sys.executable, _SCRIPT_PATH, name],
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"page_build.py exited with {completed.returncode}: "
                + completed.stderr.decode("utf-8", "replace")
            )
        cls.page_path = os.path.join(_BUILD_PATH, name + ".html")
        cls.addClassCleanup(os.remove, cls.page_path)
        cls.printed = completed.stdout

    # The name alone builds that page, and the child prints its `SHA-256`.
    def test_command_name(self) -> None:
        with open(self.page_path, "rb") as file:
            digest = hashlib.sha256(file.read()).hexdigest()
        self.assertEqual(self.printed, (digest + "\n").encode())

    # The bundle is that of `ts/tsconfig.test.json`, the table in place.
    def test_bundle_test(self) -> None:
        with open(_TEST_CONFIG, encoding="utf-8") as config_file:
            config: dict[str, Any] = json.load(config_file)
        out_file: str = config["compilerOptions"]["outFile"]
        bundle_path = os.path.join(os.path.dirname(_TEST_CONFIG), out_file)
        bundle = page_build.text_read(bundle_path)
        table = page_build.text_read(_TABLE_PATH)
        piece = page_build.table_substitute(bundle, table)
        page = page_build.text_read(self.page_path)
        # Checked by `in`, so that a failure prints no page of megabytes.
        self.assertTrue(piece in page, bundle_path)

    # The page holds the members of the gold's two archives, in order.
    def test_archives_named(self) -> None:
        names: list[str] = harness.gold_get(_ARCHIVES_ID)
        sqlite_name, xterm_name = names
        sqlite_path = os.path.join(_THIRD_PARTY_PATH, sqlite_name)
        xterm_path = os.path.join(_THIRD_PARTY_PATH, xterm_name)
        glue = page_build.zip_read(sqlite_path, [_SQLITE_JS])[0]
        script = page_build.tar_read(xterm_path, [_XTERM_JS])[0]
        page = page_build.text_read(self.page_path)
        self.assertTrue(glue.decode("utf-8") in page, sqlite_path)
        self.assertTrue(script.decode("utf-8") in page, xterm_path)
