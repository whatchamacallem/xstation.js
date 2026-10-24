# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Tests the main loop file that never prepares: its loop_prepare runs in a
# forked child for the gold's running time until the hangup ttyd sends ends
# it, and its loop_run raises the gold's text with the root in it.

import harness, os, signal, stall_loop, sys, time, unittest

# The checkout's top directory, above this file's `python/`.
_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The root the functions are given, which neither of them reads.
_ROOT_GIVEN = os.path.join(_ROOT_PATH, "build", "stall_root")

# The id of this module's gold in `test_settings.json`.
_GOLD_ID = "python.test_stall_loop"


# A text of this module's gold.
def _text_get(name: str) -> str:
    text: str = harness.gold_get(f"{_GOLD_ID}.texts.{name}")
    return text


# Tests that `loop_prepare` never returns and that a hangup ends it.
class TestPrepare(unittest.TestCase):
    # The child still runs after the wait, and the hangup kills it.
    def test_prepare_endless(self) -> None:
        running: float = harness.gold_get(f"{_GOLD_ID}.running_seconds")
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            try:
                signal.signal(signal.SIGHUP, signal.SIG_DFL)
                stall_loop.loop_prepare(_ROOT_GIVEN)
            finally:
                os.kill(os.getpid(), signal.SIGKILL)
        time.sleep(running)
        self.assertEqual(os.waitpid(pid, os.WNOHANG), (0, 0))
        os.kill(pid, signal.SIGHUP)
        status = os.waitpid(pid, 0)[1]
        self.assertEqual(os.waitstatus_to_exitcode(status), -signal.SIGHUP)


# Tests that `loop_run`, which `bootstrap.py` never reaches, raises.
class TestRun(unittest.TestCase):
    # The call raises with the root in its message.
    def test_run_raises(self) -> None:
        with self.assertRaises(RuntimeError) as caught:
            stall_loop.loop_run(0, 1, _ROOT_GIVEN)
        text = _text_get("stall_loop_run_reached")
        message = text.replace("{0}", _ROOT_GIVEN)
        self.assertEqual(str(caught.exception), message)
