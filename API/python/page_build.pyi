# Writes one HTML file: `html/<page>.html` with `html/<page>.css` inlined,
# the tsc bundle `build/js/<bundle>.js` inlined once as a script and once
# as the workers' source, `third_party/sqlite-wasm/sqlite3.wasm` as base64,
# and xterm.js. Returns the output's SHA-256, which `hello` reports.
def page_build(page: str, bundle: str, output: str) -> str: ...
