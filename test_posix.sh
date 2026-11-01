#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# One of the two official test targets of the project: runs
# python/test_all.py from the checkout with one category option and exits
# with its code. --smoke-test, the default, runs the smoke-test suites, and
# --normal-test runs those of both labels. The switches --anthropic, for
# Anthropic's cloud container, --debug and --verbose are passed on, each at
# most once:
#
#     ./test_posix.sh [--smoke-test | --normal-test] [--anthropic] [--debug]
#         [--verbose]

set -euo pipefail

# Prints the usage line and what the script runs.
usage_show() {
	cat <<'EOF2'
test_posix.sh [--smoke-test | --normal-test] [--anthropic] [--debug]
    [--verbose]
  Runs python3 python/test_all.py with the options, --smoke-test if none.
EOF2
}

# The category option passed on, `--smoke-test` when none is given.
_OPTION_=
# The switches passed on, in the order given, each at most once.
_SWITCHES_=()
for _ARGUMENT_ in "$@"; do
	case $_ARGUMENT_ in
	--smoke-test | --normal-test)
		if [ -n "$_OPTION_" ]; then
			usage_show >&2
			exit 2
		fi
		_OPTION_=$_ARGUMENT_
		;;
	--anthropic | --debug | --verbose)
		for _GIVEN_ in "${_SWITCHES_[@]}"; do
			if [ "$_GIVEN_" = "$_ARGUMENT_" ]; then
				usage_show >&2
				exit 2
			fi
		done
		_SWITCHES_+=("$_ARGUMENT_")
		;;
	*)
		usage_show >&2
		exit 2
		;;
	esac
done
if [ -z "$_OPTION_" ]; then
	_OPTION_=--smoke-test
fi

_SCRIPT_PATH_=$(readlink -f -- "$0")
cd -P -- "$(dirname -- "$_SCRIPT_PATH_")"

exec python3 python/test_all.py "$_OPTION_" "${_SWITCHES_[@]}"
