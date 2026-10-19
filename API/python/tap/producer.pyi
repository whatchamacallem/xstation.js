import unittest
from collections.abc import Callable

# Writes TAP for a unittest run: one plan, one indented block per module.
class TapRunner:
    # `write` gets each TAP line as it is produced, with no buffering.
    def __init__(
        self, write: Callable[[str], None], failfast: bool
    ) -> None: ...
    # Runs one module's suite as a subtest block named `module`.
    def module_run(self, module: str, suite: unittest.TestSuite) -> bool: ...
    # Writes the parent plan. Returns whether every module passed.
    def run_end(self) -> bool: ...
