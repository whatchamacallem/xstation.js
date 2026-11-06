# `python3 python/page_build.py TEMPLATE NAME` builds `build/NAME.html` from
# `html/TEMPLATE.html` and prints its SHA-256. `page_build` returns the digest
# and writes nothing to stdout, the driver's TAP stream. The templates are two
# of one build, filled from the same pieces, so each holds the same markers
# once each. `html/test.html` is the ttyd page. `html/headless.html`, the
# headless page of group B, holds the same head and scripts,
# `test_headless.realm_open()` last, and no `pre#tap_output`, since its realm
# sends the stream to the driver. The template is read first, so a template
# `html/` lacks fails before tsc starts.
#
# The gold is `{"typescript": {suite: gold}}` of the files
# `ts/test_setting_<suite>.json`, which the page defines as `test_gold` on a
# line of its own, in a `data-worker` script before the bundle, so that both
# threads read it. A test that gives a root's page other gold has `page_copy`
# write the built page into the root with that gold on the same line.
#
# `node_build` builds the Node bundle of group A. Its strict line comes first
# as it does in the worker's source, since the bundle's own is no directive
# once the vectors precede it.

from typing import Any

# Builds the Node bundle in the build directory. Returns the bundle's path.
def node_build(build_path: str) -> str: ...

# Builds the page from the template. Returns its `SHA-256` hex.
def page_build(template: str, name: str) -> str: ...

# Writes `build/<name>.html` at the path with the gold `{"typescript": ...}`.
def page_copy(name: str, path: str, gold: dict[str, Any]) -> str: ...
