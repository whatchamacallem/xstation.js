# Builds ttyd from the pinned source archive and the project's patches by the
# steps of the install script's ttyd build, in the driver's bring up. The
# build directory is removed, the archive unpacked by `tarfile` into its
# `source/` with the first component of each path stripped, each `*.patch`
# of the patches' directory applied in name order by `patch -p1 -d SOURCE
# -i PATCH`, then `cmake -S SOURCE -B BUILD
# -DCMAKE_DISABLE_FIND_PACKAGE_Git=TRUE`, so that cmake starts no git, whose
# `git describe` would read the work tree around the source, `cmake --build
# BUILD` and `BUILD/ttyd --version` run, and last the record `inputs.json`
# written: the SHA-256 of the archive, then the name and SHA-256 of each
# patch in order. A build directory whose `ttyd` is present and whose
# record's bytes equal those the inputs give now is left alone, with no
# program started.
# Each program's stdin is `/dev/null`, and its stdout and stderr go to
# `build.log` in the build directory, never to stdout, the driver's TAP
# stream. A program that exits other than 0 raises naming its command line,
# its exit code and the log's path, the log's last lines in the `cause`.
# `checkout_build` reads `powershell.ttyd_archive`, `powershell.ttyd_patches`
# and `powershell.ttyd_build`, paths from the checkout's top, with
# `settings.settings_load`. The test driver calls it after the pins are
# fetched, before the first block and outside every time limit.

# Builds ttyd where `settings.json` says. Returns the path of its `ttyd`.
def checkout_build() -> str: ...

# Builds ttyd from the archive and the patches. Returns the path of `ttyd`.
def inputs_build(
    archive_path: str, patches_path: str, build_path: str
) -> str: ...
