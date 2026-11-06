# Builds ttyd from the pinned source archive and the project's patches by the
# steps of the install script's ttyd build, with the switch
# `switches.anthropic` from the package manager's archive of the same tree.
# `patch --batch` asks nothing even under `POSIXLY_CORRECT`, and cmake runs
# with Git's package disabled, so that it starts no git, whose `git describe`
# would read the work tree around the source.
#
# The record `inputs.json`, the SHA-256 of the archive, then the name and
# SHA-256 of each patch in order, is written last, so that a failed build
# leaves none. A build directory whose `ttyd` is present and whose record's
# bytes equal those the inputs give now is left alone, with no program started.
#
# Each program's stdout and stderr go to `build.log`, never to stdout, the
# driver's TAP stream. A program that exits other than 0 raises naming its
# command line, its exit code and the log's path, the log's last lines in the
# `cause`. The test driver calls `checkout_build` after the pins are fetched,
# before the first block and outside every time limit.

# Builds ttyd where `settings.json` says. Returns the path of its `ttyd`.
def checkout_build() -> str: ...

# Builds ttyd from the archive and the patches. Returns the path of `ttyd`.
def inputs_build(
    archive_path: str, patches_path: str, build_path: str
) -> str: ...
