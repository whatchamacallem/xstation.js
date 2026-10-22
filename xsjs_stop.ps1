# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Stops the web terminal that xsjs_start.ps1 started: the ttyd it runs in
# Linux, found by its command line, and the scheduled task. Other ttyd
# processes are left alone. Run it from an administrator PowerShell:
#
#     .\xsjs_stop.ps1            stop it, and don't start it at sign-in
#     .\xsjs_stop.ps1 --softly   stop it until you next sign in
#
# Without --softly it also removes the scheduled task, the port proxy, the
# Windows Firewall rule and the task's runner script (which holds the ttyd
# password). The TLS certificate stays, so browsers that accepted it don't
# warn again, and so does the copy of bootstrap.py in Linux with its
# modules.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Read `$args`, not `param()`, as PowerShell takes `--softly` for a parameter.
$arguments_ = $args

# Returns whether `--softly` or `-s` was given, and throws on anything else.
function _xsjs_stop_get_softly {
    if ($arguments_.Count -eq 0) { return $false }
    $softly_ = $arguments_[0] -in '--softly', '-s'
    if ($arguments_.Count -eq 1 -and $softly_) { return $true }
    throw ($i18n_.stop_usage -f $script_name_)
}

# Removes the task, port proxy, firewall rule and the runner with its password.
function _xsjs_stop_step_remove_autostart {
    xsjs_util_write_log_section $i18n_.remove_autostart
    $task_ = Get-ScheduledTask | Where-Object TaskName -EQ $task_name_
    if ($task_) {
        Unregister-ScheduledTask -TaskName $task_name_ -Confirm:$false
        xsjs_util_write_log ($i18n_.task_removed -f $task_name_)
    } else {
        xsjs_util_write_log ($i18n_.status_task_none -f $task_name_)
    }
    xsjs_util_remove_proxy
    xsjs_util_remove_firewall_rule
    if (Test-Path $runner_path_) {
        Remove-Item $runner_path_
        xsjs_util_write_log ($i18n_.runner_removed -f $runner_path_)
    }
}

# Stops the server and, unless `--softly`, removes what starts it at sign in.
function _xsjs_stop_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_stop_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    $softly_ = _xsjs_stop_get_softly
    if ($softly_) {
        xsjs_util_write_log $i18n_.soft_stop_mode
    } else {
        xsjs_util_write_log $i18n_.full_stop_mode
    }

    xsjs_util_step_check_administrator
    xsjs_util_step_stop_server
    if (-not $softly_) { _xsjs_stop_step_remove_autostart }

    xsjs_util_write_log_section $i18n_.done
    $message_ = $i18n_.stopped
    if ($softly_) { $message_ = $i18n_.stopped_softly -f $task_name_ }
    xsjs_util_write_log $message_
    Write-Host $message_ -ForegroundColor Green
}

_xsjs_stop_main
