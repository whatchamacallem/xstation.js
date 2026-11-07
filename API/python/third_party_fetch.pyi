# Fetches the pinned third party files with urllib, each to its path in
# `third_party/`, `<library>/<file>`, one directory per library, made when
# missing. The sha256 hex of each download is checked before the file is
# moved into place, and a file there with its pinned hex is left alone,
# with no fetch. The test driver fetches every pin before each run. With
# the switch `switches.anthropic`, in Anthropic's cloud container, ttyd's
# pin is replaced by `ttyd/ttyd_1.7.7.orig.tar.xz`, the upstream archive of
# Ubuntu's source package ttyd 1.7.7-4build1, whose tree is the pin's: the
# package manager places it, `apt-get source --download-only
# ttyd=1.7.7-4build1` in `third_party/ttyd/`, and it is checked by its own
# digest and never fetched. Python runs no package manager.

# Fetches the URL to the name's path in `third_party/`. Returns the path.
def file_fetch(url: str, sha256: str, name: str) -> str: ...

# Returns the path of the package manager's file, checked by its digest.
def package_check(name: str, command: str, sha256: str) -> str: ...

# The path of ttyd's archive from the package manager.
def package_path() -> str: ...

# Fetches each pinned file in pin order, to the first failure. Returns paths.
def pins_fetch() -> list[str]: ...

# Fetches every pinned file from the command line, printing nothing.
def main() -> None: ...
