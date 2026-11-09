#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# One of the two official test targets of the project: runs
# python/test_all.py from the checkout and exits with its code. Without an
# option it runs at the end to end level, the wire, browser and demo tests
# alone. --test-normal raises the level to the smoke-test suites and the checks
# of test_posix.py too. --test-all raises it to the suites of both labels and
# the test-all rungs, and counts the lines each module's own suites run, by
# --coverage, which fails at a module's first line never run. --test-disabled
# raises it to everything disabled too, with no count. An option only raises
# the level, so giving two is the higher of them. The switches
# --anthropic, for Anthropic's cloud container, --debug and --verbose are
# passed on. Each option goes at most once:
#
#     ./test_posix.sh [--test-normal] [--test-all] [--test-disabled]
#         [--anthropic] [--debug] [--verbose]

set -euo pipefail

# Prints the usage line and what the script runs.
usage_show() {
	cat <<'EOF2'
test_posix.sh [--test-normal] [--test-all] [--test-disabled] [--anthropic]
    [--debug] [--verbose]
  Runs python3 python/test_all.py with the options, at the end to end level
  when no level is given, and --coverage with --test-all, unless
  --test-disabled is given too.
EOF2
}

# The options passed on, in the order given, each at most once.
_OPTIONS_=()
# The option that counts lines, for a run at the level `--test-all` gives.
_COVERAGE_=()
for _ARGUMENT_ in "$@"; do
	case $_ARGUMENT_ in
	--test-normal | --test-all | --test-disabled | --anthropic | --debug | --verbose)
		for _GIVEN_ in "${_OPTIONS_[@]}"; do
			if [ "$_GIVEN_" = "$_ARGUMENT_" ]; then
				usage_show >&2
				exit 2
			fi
		done
		_OPTIONS_+=("$_ARGUMENT_")
		;;
	*)
		usage_show >&2
		exit 2
		;;
	esac
done

case " ${_OPTIONS_[*]} " in
*" --test-disabled "*) ;;
*" --test-all "*) _COVERAGE_=(--coverage) ;;
esac

_SCRIPT_PATH_=$(readlink -f -- "$0")
cd -P -- "$(dirname -- "$_SCRIPT_PATH_")"

exec python3 python/test_all.py "${_OPTIONS_[@]}" "${_COVERAGE_[@]}"
