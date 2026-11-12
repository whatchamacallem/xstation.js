#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The guide test of Dawa, Nobody Left Behind, one of the three tests of the
# end to end level: the engine page walked by python/guide_walk.py through his
# scripted table and model of the mountain's air in python/guides/dawa/, as
# its gold, python.test_guide_dawa, says.

import os, sys

# The guide's name: its directory in python/guides and its gold's id.
_GUIDE_NAME = "dawa"

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "build",
    "pycache",
)


# Runs the guide test with the arguments after the program's name.
def main(arguments: list[str]) -> int:
    import guide_walk

    return guide_walk.guide_main(arguments, _GUIDE_NAME)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
