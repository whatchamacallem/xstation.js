#!/usr/bin/env bash
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Makes the checkout DESTINATION, inside the wslc container hype, a copy of
# the working tree of the checkout SOURCE, the Windows checkout as hype mounts
# it, and writes nothing under SOURCE. It clones SOURCE when DESTINATION is
# absent, takes SOURCE's new commits by moving DESTINATION's branch, refusing
# when DESTINATION holds a commit SOURCE lacks, then copies each file that
# differs and removes each that SOURCE removed. Ignored files, build/ and the
# archives of third_party/ among them, stay as they are. A copied file keeps
# its mode and a new one gets the umask's. powershell/test_wslc.ps1 runs it
# as t before each run, and a person in hype runs it as:
#
#     bash wslc_sync.sh /mnt/c/Users/ajohn/Downloads/xstation.js ~/xstation.js

set -euo pipefail

# Prints the usage line.
usage_show() {
	echo 'wslc_sync.sh SOURCE DESTINATION'
}

if [ $# -ne 2 ]; then
	usage_show >&2
	exit 2
fi
_SOURCE_=$1
_DESTINATION_=$2

# Runs git trusting SOURCE for one command, as the mount shows root owning it.
trusted_git() {
	git -c safe.directory="$_SOURCE_" "$@"
}

# Runs git on SOURCE.
source_git() {
	trusted_git -C "$_SOURCE_" "$@"
}

# Runs git on DESTINATION, which reads SOURCE in a clone or a fetch.
destination_git() {
	trusted_git -C "$_DESTINATION_" "$@"
}

if [ ! -e "$_DESTINATION_" ]; then
	trusted_git clone --quiet "$_SOURCE_" "$_DESTINATION_"
fi
destination_git fetch --quiet "$_SOURCE_" HEAD
_HEAD_=$(destination_git rev-parse HEAD)
if [ "$_HEAD_" != "$(destination_git rev-parse FETCH_HEAD)" ]; then
	if ! destination_git merge-base --is-ancestor HEAD FETCH_HEAD; then
		echo "wslc_sync.sh: $_DESTINATION_ holds a commit $_SOURCE_ lacks" >&2
		exit 1
	fi
	# A mixed reset moves the branch and the index and leaves every file as it is.
	destination_git reset --quiet FETCH_HEAD
fi

# Each path that differs from the commit on either side, once, NUL ended.
{
	# Plumbing, as `git diff` writes the index of SOURCE when a stat is stale.
	source_git diff-index --name-only -z HEAD
	source_git ls-files -z --others --exclude-standard
	destination_git diff --name-only -z HEAD
	destination_git ls-files -z --others --exclude-standard
} | sort -zu | while IFS= read -r -d '' _PATH_; do
	if [ -e "$_SOURCE_/$_PATH_" ]; then
		if ! cmp -s "$_SOURCE_/$_PATH_" "$_DESTINATION_/$_PATH_"; then
			mkdir -p "$(dirname "$_DESTINATION_/$_PATH_")"
			cat "$_SOURCE_/$_PATH_" >"$_DESTINATION_/$_PATH_"
			echo "copied $_PATH_"
		fi
	elif [ -e "$_DESTINATION_/$_PATH_" ]; then
		rm -- "$_DESTINATION_/$_PATH_"
		echo "removed $_PATH_"
	fi
done
