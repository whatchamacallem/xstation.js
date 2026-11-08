# The server's end of the TAP run, in debug mode alone, by the main loops that
# use it: each `tap.line`, a line of the TypeScript stream, the one that
# crosses the wire, is appended to `<root>/tap/typescript.tap` the moment it
# arrives, unbuffered, so a hang leaves every line before it on disk. Any other
# language is refused: the Python stream, the one `tap.run` runs, crosses the
# other way. When the browser fails, the main loop gives the message of its
# `error` line to `error_take`, which ends the TypeScript stream with a `Bail
# out!` line, so the TAP results are written out whole, before the main loop
# exits 1 without an answer. The stock main loop has recorded the whole line in
# the audit by then.

import jslb

# `tap.line`: appends the line to the file of its language.
def tap_line(line: jslb.Object, *, language: str, text: str) -> None: ...

# Appends `Bail out!` with the message of the browser's failure.
def error_take(message: str) -> None: ...

# Registers the handler, with the root that holds the `tap` directory.
def handlers_register(root: str) -> None: ...
