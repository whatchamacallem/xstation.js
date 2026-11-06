# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests xsjs_screenshot.py as a program, as a person starts it, on the Linux
# browser of devtools.py, named by --browser so that the run is the same on WSL
# and off it. The program opens the whole page through the ttyd that
# ttyd_build.py built, and exits 0 only when both TAP documents pass, the page
# shows the last and the page's server ends when the page is left. It saves a
# PNG at least as large as its viewport, reports both documents, and leaves no
# root or profile in build/. A browser outside its list is refused, and no
# picture is saved.

import devtools, glob, os, re, struct, subprocess, sys, tempfile, unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the scratch directories go.
_BUILD_PATH = os.path.join(_ROOT_PATH, "build")

# The program under test.
_PROGRAM_PATH = os.path.join(_ROOT_PATH, "python", "xsjs_screenshot.py")

# The root and the profile of a run of the program, gone when it ends.
_LEFT_PATTERN = os.path.join(_BUILD_PATH, "xsjs_screenshot-*")

# The name the picture is saved under, in a scratch directory.
_SHOT_NAME = "shot.png"

# What the program prints after the picture's path.
_REPORT_PATTERN = re.compile(r": 2 TAP documents, pid \d+ gone, \d+\.\d s\n")

# A browser that the program's list does not hold.
_UNLISTED_NAME = "firefox"

# The exit code of a run that failed.
_FAILED_CODE = 1

# A PNG's signature, then its first chunk's length, type, width and height.
_PNG_HEAD = struct.Struct(">8sI4sII")

# The signature that starts every PNG.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# The type of the chunk that holds a PNG's size.
_PNG_SIZE_CHUNK = b"IHDR"

# The program's viewport, which it grows until no part of the page scrolls.
_VIEWPORT_WIDTH_PX = 1280
_VIEWPORT_HEIGHT_PX = 720


# Runs the program, whose cleanups are its own, so a stop asks it to end.
def program_run(arguments: list[str]) -> tuple[int, str, str]:
    with subprocess.Popen(
        [sys.executable, _PROGRAM_PATH, *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        try:
            output, errors = process.communicate()
        except BaseException:
            process.terminate()
            raise
    return process.returncode, output, errors


# The program on the Linux browser, each test in a scratch directory.
class TestProgram(unittest.TestCase):
    # Makes the scratch directory and names the picture in it.
    def setUp(self) -> None:
        os.makedirs(_BUILD_PATH, exist_ok=True)
        scratch = self.enterContext(
            tempfile.TemporaryDirectory(dir=_BUILD_PATH)
        )
        self.shot_path = os.path.join(scratch, _SHOT_NAME)

    # The page passes, its PNG is saved, and nothing is left in `build/`.
    def test_page_saved(self) -> None:
        before = set(glob.glob(_LEFT_PATTERN))
        browser_path = devtools.chrome_path()
        code, output, errors = program_run(
            ["--browser", browser_path, "--out", self.shot_path]
        )
        self.assertEqual(code, 0, errors)
        self.assertTrue(output.startswith(self.shot_path), output)
        report = output.removeprefix(self.shot_path)
        self.assertIsNotNone(_REPORT_PATTERN.fullmatch(report), output)
        with open(self.shot_path, "rb") as file:
            head = file.read(_PNG_HEAD.size)
        signature, _, chunk, width, height = _PNG_HEAD.unpack(head)
        self.assertEqual(signature, _PNG_SIGNATURE)
        self.assertEqual(chunk, _PNG_SIZE_CHUNK)
        self.assertGreaterEqual(width, _VIEWPORT_WIDTH_PX)
        self.assertGreaterEqual(height, _VIEWPORT_HEIGHT_PX)
        self.assertEqual(set(glob.glob(_LEFT_PATTERN)), before)

    # A browser outside the list fails the run, and no picture is saved.
    def test_browser_refused(self) -> None:
        code, output, errors = program_run(
            ["--browser", _UNLISTED_NAME, "--out", self.shot_path]
        )
        self.assertEqual(code, _FAILED_CODE, errors)
        self.assertEqual(output, "")
        self.assertTrue(errors.startswith(f"error: {_UNLISTED_NAME} is none"))
        self.assertFalse(os.path.exists(self.shot_path))
