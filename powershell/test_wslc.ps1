# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Runs test_posix.sh in the wslc container hype as its user t, from any
# PowerShell, as no step needs administrator. It makes hype from its image
# when there is none, adding no capability: the checkout's parent folder
# mounted where WSL mounts it, port 5768 published on Windows' 127.0.0.1 for
# xsjs_start.ps1, the PATH the image lost and an init that waits. It refuses
# a hype made with an added capability or without the mount, starts hype when
# it is stopped, has wslc_sync.sh make hype's checkout a copy of this one,
# then runs test_posix.sh there with the arguments given and exits with its
# code:
#
#     .\powershell\test_wslc.ps1 [--test-normal] [--test-all]
#         [--test-disabled] [--anthropic] [--debug] [--verbose]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured commands for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'xsjs_util.ps1')

# Read `$args`, not `param()`: PowerShell takes each option for a parameter.
$arguments_ = $args

# What makes hype, in this script's own file beside it.
$gold_json_ = xsjs_util_read_json (
    Join-Path $PSScriptRoot 'test_setting_test_wslc.json')
$image_ = xsjs_util_get_setting $gold_json_ 'image'
$environment_ = xsjs_util_get_setting $gold_json_ 'environment'
$command_ = xsjs_util_get_setting $gold_json_ 'command'
$restart_ = xsjs_util_get_setting $gold_json_ 'restart'

# Shows the wslc command, runs it with its output shown, returns its code.
function _test_wslc_run_shown_command ([string[]]$wslc_arguments_) {
    Write-Host "`n> wslc $($wslc_arguments_ -join ' ')" -ForegroundColor Cyan
    & wslc.exe @wslc_arguments_ | Out-Host
    $LASTEXITCODE
}

# Runs the wslc command with its output shown, and throws unless it exits 0.
function _test_wslc_run_checked_command ([string[]]$wslc_arguments_) {
    $exit_code_ = _test_wslc_run_shown_command $wslc_arguments_
    if ($exit_code_ -ne 0) {
        $text_ = 'wslc ' + ($wslc_arguments_ -join ' ')
        throw ($i18n_.exit_code -f $text_, $exit_code_)
    }
}

# Makes hype from its image with the environment, mount, port and init.
function _test_wslc_create_container {
    $source_ = Split-Path -Parent $checkout_path_
    $destination_ = xsjs_util_get_linux_path $source_
    $create_ = @(
        'create', '--name', $container_, '--restart', $restart_,
        '--pull', 'never'
    )
    foreach ($variable_ in $environment_) { $create_ += '--env', $variable_ }
    $create_ += '--volume', "${source_}:$destination_"
    $create_ += '--publish', "${windows_address_}:${port_}:$port_", $image_
    _test_wslc_run_checked_command ($create_ + $command_)
}

# Checks hype, or makes it when there is none, and returns it as inspected.
function _test_wslc_step_prepare_container {
    $found_ = xsjs_util_get_container
    if ($found_) {
        xsjs_util_step_check_container $found_
        return $found_
    }
    _test_wslc_create_container
    xsjs_util_get_container
}

# Starts hype unless it is running.
function _test_wslc_step_start_container ([object]$found_) {
    if (-not $found_.State.Running) {
        _test_wslc_run_checked_command 'start', $container_
    }
}

# Has `wslc_sync.sh`, as hype's user, make hype's checkout a copy of this one.
function _test_wslc_step_copy_checkout {
    _test_wslc_run_checked_command @(xsjs_util_get_sync_arguments)
}

# Runs `test_posix.sh` with the arguments in hype's checkout, giving its code.
function _test_wslc_step_run_tests {
    $run_ = @(
        'exec', '-u', $container_user_, '-w', $container_root_, $container_,
        './test_posix.sh'
    ) + $arguments_
    _test_wslc_run_shown_command $run_
}

# Makes or checks hype, starts it, copies its checkout, then runs the tests.
function _test_wslc_main {
    trap { xsjs_util_write_failure $_; exit 1 }

    $found_ = _test_wslc_step_prepare_container
    _test_wslc_step_start_container $found_
    _test_wslc_step_copy_checkout
    exit (_test_wslc_step_run_tests)
}

_test_wslc_main
