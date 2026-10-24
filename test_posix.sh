#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# One of the two official test targets of the project: runs
# python/test_all.py from the checkout with one category option and exits
# with its code. --smoke-test, the default, runs the smoke-test suites, and
# --normal-test runs those of both labels:
#
#     ./test_posix.sh [--smoke-test | --normal-test]

set -euo pipefail

# Prints the usage line and what the script runs.
usage_show() {
	cat <<'EOF'
test_posix.sh [--smoke-test | --normal-test]
  Runs python3 python/test_all.py with the option, --smoke-test if none.
EOF
}

# The category option passed on, `--smoke-test` when none is given.
_OPTION_=--smoke-test
if [ $# -gt 1 ]; then
	usage_show >&2
	exit 2
fi
if [ $# = 1 ]; then
	case $1 in
	--smoke-test | --normal-test) _OPTION_=$1 ;;
	*)
		usage_show >&2
		exit 2
		;;
	esac
fi

_SCRIPT_PATH_=$(readlink -f -- "$0")
cd -P -- "$(dirname -- "$_SCRIPT_PATH_")"

exec python3 python/test_all.py "$_OPTION_"
