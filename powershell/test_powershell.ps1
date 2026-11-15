# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Offline since 2026-10-30, kept, run by nothing, and to be brought back later.
#
# Formats and checks the scripts (test_lint.ps1), then runs the whole
# lifecycle, each script in its own PowerShell as a person would, with
# test_wslc.ps1 running test_posix.sh in the wslc container hype among them.
# Each step's output and log go to test_powershell.ps1.md. Any PowerShell
# runs it, as no step needs administrator:
#
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\powershell\test_powershell.ps1 [--test-normal|--test-all|--test-disabled]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured headings for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'xsjs_util.ps1')

# Read `$args`, not `param()`: PowerShell takes each level for a parameter.
$arguments_ = $args

# The project's top directory. Each Script is relative to it.
$root_path_ = Split-Path -Parent $PSScriptRoot
# Expect is the first line `xsjs_status.ps1` should print.
$lifecycle_ = @(
    @{ Script = 'xsjs_stop.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped }
    # Category: the step is given the category option too.
    @{ Script = 'powershell\test_wslc.ps1'; Category = $true }
    @{ Script = 'xsjs_start.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_running }
    @{ Script = 'xsjs_start.ps1'; Arguments = '--debug' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_running }
    @{ Script = 'xsjs_stop.ps1' }
    @{ Script = 'xsjs_status.ps1'; Expect = $i18n_.status_stopped }
)

# Returns the level's option as words, none if not given, or throws usage.
function _test_powershell_get_category {
    if ($arguments_.Count -eq 0) { return @() }
    $levels_ = @('--test-normal', '--test-all', '--test-disabled')
    if ($arguments_.Count -eq 1 -and $levels_ -ccontains $arguments_[0]) {
        return @($arguments_[0])
    }
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

# Runs one step in its own PowerShell and returns whether it passed.
function _test_powershell_test_step ([int]$number_, [hashtable]$step_) {
    # Shows and logs what it prints, then adds a script's own log.
    $ErrorActionPreference = 'Continue'
    $arguments_ = @($step_.Arguments | Where-Object { $_ })
    if ($step_.Category) { $arguments_ += $category_ }
    $command_ = (@(".\$($step_.Script)") + $arguments_) -join ' '
    Write-Host "`n> $command_" -ForegroundColor Cyan
    xsjs_util_write_log_section ('{0}. `{1}`' -f $number_, $command_)

    $path_ = Join-Path $root_path_ $step_.Script
    if (Test-Path "$path_.md") {
        Remove-Item "$path_.md" -ErrorAction Stop
    }
    $powershell_ = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $path_
    ) + $arguments_
    $lines_ = @(
        & powershell.exe @powershell_ |
            ForEach-Object { Write-Host $_; $_ }
    )
    $exit_code_ = $LASTEXITCODE
    xsjs_util_write_log ($i18n_.exit_code -f $command_, $exit_code_)
    $lines_ | xsjs_util_write_log_output
    if (Test-Path "$path_.md") {
        xsjs_util_write_log (_test_powershell_get_log_text "$path_.md")
    }

    $passed_ = $exit_code_ -eq 0
    if ($step_.Expect) {
        $expected_ = $step_.Expect -f (xsjs_util_get_local_url)
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
    $category_ = @(_test_powershell_get_category)

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
    $command_ = (@('./test_posix.sh') + $category_) -join ' '
    $message_ = $i18n_.test_passed -f $command_
    xsjs_util_write_log $message_
    Write-Host "`n$message_" -ForegroundColor Green
}

_test_powershell_main
