# tappy's producer, its names recalled from tappy's documentation: one TAP
# version 14 stream, a parent plan, and one indented block per test module,
# each with its own plan. Each line goes to the stream's writer the moment it
# is made, as `test_all.py` writes each to stdout. A realm's own stream of
# one block, as a TypeScript realm writes it, is relayed in as a block of
# this stream, a line at a time as each is fed: its indented lines unchanged,
# then the parent line with this stream's own number, `ok` only when the
# consumer reading this stream counted no failure in the block and the
# realm's parent line was `ok`, the two required to agree; a bail out from
# the realm ends the stream. No module or relay starts while a relay is
# open, and the stream does not end then.

import tap_consumer, unittest
from collections.abc import Callable

# Writes the lines of one level of a stream the moment each is added.
class Tracker:
    # `write` takes each line, without its newline.
    def __init__(self, write: Callable[[str], None]) -> None: ...
    # Writes the plan at once, before the points.
    def set_plan(self, total: int) -> None: ...
    def add_ok(
        self,
        class_name: str,
        description: str,
        directive: str = "",
        diagnostics: str | None = None,
    ) -> None: ...
    def add_not_ok(
        self,
        class_name: str,
        description: str,
        directive: str = "",
        diagnostics: str | None = None,
    ) -> None: ...
    def add_skip(
        self, class_name: str, description: str, reason: str
    ) -> None: ...
    # Writes the plan of the points added, for a level whose plan comes last.
    def generate_tap_reports(self) -> None: ...

# Turns unittest's outcomes into one point per test.
class TAPTestResult(unittest.TestResult):
    def __init__(self, tracker: Tracker) -> None: ...
    # Writes the point of the last test.
    def point_flush(self) -> None: ...

# tappy's `TAPTestRunner`, its results TAP, with no base, as TypeScript's.
class TAPTestRunner:
    # Whether the stream ends at the first failure, as unittest's does.
    failfast: bool
    # `failfast` ends the stream at the first failure, as unittest's does.
    def __init__(self, failfast: bool) -> None: ...
    # Sends each line to `write` as it is made, the version line first.
    def set_stream(self, write: Callable[[str], None]) -> None: ...
    # Runs the test as one block, its plan first, and returns its result.
    def run(
        self, test: unittest.TestSuite | unittest.TestCase
    ) -> TAPTestResult: ...
    # Loads and runs one module as a block. True when it passed.
    def module_run(
        self, module: str, load: Callable[[], unittest.TestSuite]
    ) -> bool: ...
    # Opens the relay of a realm's one block, graded by the stream's reader.
    def block_relay(
        self, module: str, reader: tap_consumer.StreamReader
    ) -> None: ...
    # Takes the next line of the realm's stream, without its newline.
    def relay_feed(self, text: str) -> None: ...
    # Ends the relay once the realm exited. True when its block passed.
    def relay_end(self) -> bool: ...
    # Writes the parent plan unless the stream bailed out. True if all passed.
    def run_end(self) -> bool: ...
