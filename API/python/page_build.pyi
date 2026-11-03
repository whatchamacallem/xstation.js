# `python3 python/page_build.py TEMPLATE NAME` builds `build/NAME.html` from
# the template `html/TEMPLATE.html` and prints its SHA-256. The templates are
# two of one build, each filled from the same pieces: `html/engine.css`, the
# test bundle that tsc compiles by `ts/tsconfig.test.json` with the strings
# table in place of `I18N_TABLE_JSON`, found once, the vectors written anew
# into `build/vectors/`, the gold, SQLite's glue and wasm, and xterm.js and
# its css, so each holds the same markers once each. The gold is the
# TypeScript suites' files `ts/test_setting_<suite>.json`, each read by
# `jslb.json_decode`, as `{"typescript": {suite: gold}}`, which the page
# defines as `test_gold` on a line of its own, `var test_gold = GOLD;`, in a
# `data-worker` script before the bundle, as it defines `test_vectors`, so
# that both threads read it; the harness reads it there.
# `ts/test_headless.ts` is a file of that bundle, as `ts/test_all.ts` is,
# and a template's last script, a worker script, picks the entry on both
# threads. `html/test.html`, the ttyd
# page, runs `test_all.suites_run()` and shows its TAP stream in
# `pre#tap_output`. The start script serves it as the page that
# `page_build.py test hyperposition-engine` builds, and the wire test and the
# browser test build it from `test` too. A test that gives a root's page
# other gold has `page_copy` write the built page into the root with that
# gold in place of its own, on the same line, and serves that copy.
# `html/headless.html`, the headless page of group B, holds the head and the
# scripts of `html/test.html` in their order, the last one
# `test_headless.realm_open()` in place of `test_all.suites_run()`, and no
# `pre#tap_output`, since its realm sends the stream to the driver. The
# driver builds `build/headless.html` at the start of the B phases with
# `page_build("headless", "headless")`, and its HTTP server serves it from
# `build/`. The template is read first, so a template `html/` lacks fails
# before tsc starts. `page_build` returns the digest and writes nothing to
# stdout, the driver's TAP stream; the command line prints it.
#
# `node_build` builds the Node bundle of group A, which `node` runs once for
# each block, `node node.js BLOCK [--failfast]`. In the build directory it
# is given it writes the vectors anew into `vectors/` first, then has tsc
# compile `ts/tsconfig.node.json` into `ts/node.js`, the place the config's
# `outFile` names in `build/`, and rewrites that file as `"use strict";` on
# a line of its own, then `var test_vectors = ...;`, the vectors as the page
# defines them, then `var test_gold = ...;`, the gold as the page defines it,
# then the bundle with the strings table in place of
# `I18N_TABLE_JSON`, found once. The strict line comes first as it does in
# the worker's source, since the bundle's own is no directive once the
# vectors precede it. The driver calls it with `build/` at the start of the
# TS phases and runs `node` on the path it returns. Both builds compile
# through one function, which keeps tsc's output off stdout, the driver's
# TAP stream: a failed compile raises, tsc's output in its cause.

from typing import Any

# Builds the Node bundle in the build directory. Returns the bundle's path.
def node_build(build_path: str) -> str: ...

# Builds the page from the template. Returns its `SHA-256` hex.
def page_build(template: str, name: str) -> str: ...

# Writes `build/<name>.html` at the path with the gold `{"typescript": ...}`.
def page_copy(name: str, path: str, gold: dict[str, Any]) -> str: ...
