import jslb

# `tap.line`: appends the line to `<root>/tap/<language>.tap`, unbuffered.
def tap_line(line: jslb.Object, *, language: str, text: str) -> None: ...
