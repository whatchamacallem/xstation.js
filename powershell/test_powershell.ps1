﻿# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Formats and checks the scripts (test_lint.ps1), then runs the whole
# lifecycle, each script in its own PowerShell as a person would: serving
# localhost, starting again while running, stopping softly, then serving
# HTTPS with a throwaway password, which opens port 5768 to the network
# with a port proxy and a Windows Firewall rule until the last stop. Each
# step's output and log go to test_powershell.ps1.md. After the install it
# runs python/test_all.py in WSL from the checkout with the category option,
# which needs in WSL what that runner needs.
#
# The checkout must first hold what the scripts read and don't make:
# settings.json, i18n\en-US.json and the page build\hyperposition-engine.html.
# Make the page in WSL in the checkout: python3 python/third_party_fetch.py
# fetches the pinned archives over the network, then
# python3 python/page_build.py hyperposition-engine builds the page from
# them with tsc.
#
# The test command has to be run as admin:
#
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\powershell\test_powershell.ps1 [--smoke-test | --normal-test]
#
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured headings for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'xsjs_util.ps1')

# Read `$args`, not `param()`: PowerShell takes `--smoke-test` for a parameter.
$arguments_ = $args

# The project's top directory. Each Script is relative to it.
$root_path_ = Split-Path -Parent $PSScriptRoot
$test_user_ = 'xstation-test'
$test_credential_ = '{0}:{1}' -f $test_user_, [Guid]::NewGuid().ToString('N')
# Expect is the first line `xsjs_status.ps1` should print.
$lifecycle_ = @(
    @{ Script = 'xsjs_stop.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped }
    @{ Script = 'xsjs_install.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped }
    # Linux: a command run in WSL in the checkout, given the category option.
    @{ Linux = 'python3', 'python/test_all.py' }
    @{ Script = 'xsjs_start.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_running_signin }
    @{ Script = 'xsjs_start.ps1' }
    @{ Script = 'xsjs_stop.ps1'; Arguments = '--softly' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped_signin }
    @{ Script = 'xsjs_start.ps1'; Arguments = $test_credential_ }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_running_signin }
    @{ Script = 'xsjs_stop.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped }
)

# Returns the category option, `--smoke-test` if none, or throws usage.
function _test_powershell_get_category {
    if ($arguments_.Count -eq 0) { return '--smoke-test' }
    $known_ = $arguments_[0] -cin '--smoke-test', '--normal-test'
    if ($arguments_.Count -eq 1 -and $known_) { return $arguments_[0] }
    throw ($i18n_.test_usage -f $script_name_)
}

# Returns a script's own log without its title, for the step's section.
function _test_powershell_get_log_text ([string]$path_) {
    # Its headings go one level down so they sit under the step's.
    $fenced_ = $false
    $all_lines_ = [IO.File]::ReadAllLines($path_)
    $lines_ = foreach ($line_ in $all_lines_ | Select-Object -Skip 1) {
        if ($line_.StartsWith('```')) { $fenced_ = -not $fenced_ }
        if (-not $fenced_ -and $line_.StartsWith('#')) { $line_ = "#$line_" }
        $line_
    }
    ($lines_ -join "`n").Trim()
}

# Runs one step in its own PowerShell or in WSL and returns whether it passed.
function _test_powershell_test_step ([int]$number_, [hashtable]$step_) {
    # Shows and logs what it prints, then adds a script's own log.
    $ErrorActionPreference = 'Continue'
    if ($step_.Linux) {
        $linux_ = @($step_.Linux) + $category_
        $command_ = 'wsl --cd {0} -e {1}' -f $root_path_, ($linux_ -join ' ')
    } else {
        $arguments_ = @($step_.Arguments | Where-Object { $_ })
        $hidden_ = "${test_user_}:********"
        $shown_ = @(".\$($step_.Script)") + @(
            $arguments_ | ForEach-Object {
                if ($_ -ceq $test_credential_) { $hidden_ } else { $_ }
            }
        )
        $command_ = $shown_ -join ' '
    }
    Write-Host "`n> $command_" -ForegroundColor Cyan
    xsjs_util_write_log_section ('{0}. `{1}`' -f $number_, $command_)

    if ($step_.Linux) {
        # Each line as text, an error record's too, without the nulls of WSL.
        $lines_ = @(
            & wsl.exe --cd $root_path_ -e @linux_ 2>&1 |
                ForEach-Object { "$_".Replace("`0", '') } |
                ForEach-Object { Write-Host $_; $_ }
        )
    } else {
        $path_ = Join-Path $root_path_ $step_.Script
        Remove-Item "$path_.md" -ErrorAction SilentlyContinue
        $powershell_ = @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $path_
        ) + $arguments_
        $lines_ = @(
            & powershell.exe @powershell_ |
                ForEach-Object { Write-Host $_; $_ }
        )
    }
    $exit_code_ = $LASTEXITCODE
    xsjs_util_write_log ($i18n_.exit_code -f $command_, $exit_code_)
    $lines_ | xsjs_util_write_log_output
    if ($step_.Script -and (Test-Path "$path_.md")) {
        xsjs_util_write_log (_test_powershell_get_log_text "$path_.md")
    }

    $passed_ = $exit_code_ -eq 0
    if ($step_.Expect) {
        $expected_ = $step_.Expect -f $task_name_, $port_
        $first_ = "$($lines_ | Select-Object -First 1)".Trim()
        if ($first_ -cne $expected_) {
            $passed_ = $false
            $message_ = $i18n_.test_expected -f $expected_, $first_
            xsjs_util_write_log_alert CAUTION $message_
        }
    }
    if (-not $passed_) {
        Write-Host ($i18n_.test_step_failed -f $number_) -ForegroundColor Red
    }
    $passed_
}

# Lints, then runs the lifecycle, exiting 1 at the first step that fails.
function _test_powershell_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'Functions _test_powershell_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    $category_ = _test_powershell_get_category
    xsjs_util_step_check_administrator

    # Lint in a PowerShell of its own: see `test_lint.ps1`.
    $lint_ = @{ Script = 'powershell\test_lint.ps1' }
    if (-not (_test_powershell_test_step 1 $lint_)) {
        throw $i18n_.test_lint_failed
    }
    # A failed step ends the run, and the state it leaves is kept as it is.
    for ($index_ = 0; $index_ -lt $lifecycle_.Count; $index_++) {
        $number_ = $index_ + 2
        if (-not (_test_powershell_test_step $number_ $lifecycle_[$index_])) {
            throw ($i18n_.test_failed_step -f $number_, $log_path_)
        }
    }

    xsjs_util_write_log_section $i18n_.done
    $message_ = $i18n_.test_passed -f $category_
    xsjs_util_write_log $message_
    Write-Host "`n$message_" -ForegroundColor Green
}

_test_powershell_main
