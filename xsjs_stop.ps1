# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Stops the serve program that xsjs_start.ps1 runs in the wslc container
# hype, which stops its ttyd. hype keeps running, and so do other programs in
# it. Run it from any PowerShell:
#
#     .\xsjs_stop.ps1
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Read `$args`, not `param()`, so that any argument is refused as usage.
$arguments_ = $args

# Stops the serve program, if one runs.
function _xsjs_stop_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_stop_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    if ($arguments_.Count -ne 0) { throw ($i18n_.stop_usage -f $script_name_) }

    xsjs_util_step_stop_server (xsjs_util_get_container)

    xsjs_util_write_log_section $i18n_.done
    xsjs_util_write_log $i18n_.stopped
    Write-Host $i18n_.stopped -ForegroundColor Green
}

_xsjs_stop_main
