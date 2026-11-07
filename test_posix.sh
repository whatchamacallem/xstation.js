#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# One of the two official test targets of the project: runs
# python/test_all.py from the checkout and exits with its code. Without an
# option it runs the smoke-test suites, and --test-all runs those of both
# labels and counts the lines each module's own suites run, by --coverage,
# which fails at a module's first line never run. The switches --anthropic,
# for Anthropic's cloud container, --debug and --verbose are passed on, each
# at most once:
#
#     ./test_posix.sh [--test-all] [--anthropic] [--debug] [--verbose]

set -euo pipefail

# Prints the usage line and what the script runs.
usage_show() {
	cat <<'EOF2'
test_posix.sh [--test-all] [--anthropic] [--debug] [--verbose]
  Runs python3 python/test_all.py with the options, and --coverage with
  --test-all.
EOF2
}

# The category option passed on, none when the `smoke-test` suites run.
_OPTION_=()
# The switches passed on, in the order given, each at most once.
_SWITCHES_=()
for _ARGUMENT_ in "$@"; do
	case $_ARGUMENT_ in
	--test-all)
		if [ ${#_OPTION_[@]} -ne 0 ]; then
			usage_show >&2
			exit 2
		fi
		_OPTION_=("$_ARGUMENT_" --coverage)
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

_SCRIPT_PATH_=$(readlink -f -- "$0")
cd -P -- "$(dirname -- "$_SCRIPT_PATH_")"

exec python3 python/test_all.py "${_OPTION_[@]}" "${_SWITCHES_[@]}"
