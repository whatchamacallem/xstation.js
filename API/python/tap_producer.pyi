import unittest

# tappy's `Tracker`, its names recalled from tappy's documentation.
class Tracker:
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
    # Sets the number of points the plan line announces.
    def set_plan(self, total: int) -> None: ...
    # Writes the points collected so far as TAP.
    def generate_tap_reports(self) -> None: ...

# tappy's `TAPTestRunner`: a `unittest.TextTestRunner` whose results are TAP.
class TAPTestRunner(unittest.TextTestRunner):
    # Streams each TAP line as it is produced, in place of the runner's text.
    def set_stream(self, streaming: bool) -> None: ...
