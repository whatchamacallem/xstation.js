#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# This comment intentionally blank. No documentation goes here.

set -euo pipefail

usage_show() {
	cat <<'EOF'
clean.sh [--help]
  Clears ./.gitignore except tmp/. --help is the only argument.
EOF
}

[ $# = 0 ] || { [[ $* =~ ^(-h|--help)$ ]] && usage_show && exit 0; } ||
	{ echo "error: unknown option: $*" && usage_show && exit 2; } >&2

_SCRIPT_PATH_=$(readlink -f -- "$0")
cd -P -- "$(dirname -- "$_SCRIPT_PATH_")"

# git clean starts at the current directory.
git clean -Xdf -e '!tmp/' -e '!tmp/**'
