# `python3 python/page_build.py NAME` builds `build/NAME.html`, the one page
# there is, the bring up: `html/test.html` with `html/engine.css`, the test
# bundle that tsc compiles by `ts/tsconfig.test.json`, the strings table, the
# vectors written anew into `build/vectors/`, SQLite's glue and wasm, and
# xterm.js and its css. The start script serves it as
# `hyperposition-engine.html`.

# Builds the page. Returns its `SHA-256` hex.
def page_build(name: str) -> str: ...
