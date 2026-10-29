# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests page_build.py with its one project callee, vectors_make.py, whose
# suite has passed: the piece of the page's vectors, which vectors_make.py
# writes anew into a scratch directory under build/, carries every file
# written there and none that was left there before.

import json, os, page_build, tempfile, unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")


# The vectors of the page, written anew by the real `vectors_make`.
class TestVectors(unittest.TestCase):
    # Makes the checkout's `build/` for the scratch directories.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)

    # The piece carries the vectors written anew, not a file left before.
    def test_vectors_built(self) -> None:
        with tempfile.TemporaryDirectory(dir=_BUILD_PATH) as scratch:
            with open(os.path.join(scratch, "stale.jslb"), "wb") as file:
                file.write(b'{"0":{"t":"x"}}\r')
            text = page_build.vectors_build(scratch)
            names = sorted(os.listdir(scratch))
        vectors: dict[str, str] = json.loads(text)
        self.assertTrue(names)
        self.assertEqual(list(vectors), names)
        self.assertNotIn("stale.jslb", vectors)
