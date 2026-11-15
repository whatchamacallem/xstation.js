# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Prints a brief status of the server: whether the serve program that
# xsjs_start.ps1 runs in the wslc container hype runs, hype's state and the
# ports it publishes, and what listens on port 5768 in Windows. It changes
# nothing and writes no log, so any PowerShell can run it:
#
#     .\xsjs_status.ps1
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Prints whether the serve program runs, and its address when it does.
function _xsjs_status_show_summary {
    if ($servers_) {
        $text_ = $i18n_.status_running -f (xsjs_util_get_local_url)
        Write-Host $text_ -ForegroundColor Green
    } else {
        Write-Host $i18n_.status_stopped -ForegroundColor Gray
    }
}

# Prints the text as a list item.
function _xsjs_status_show_item ([string]$text_) {
    Write-Host "- $text_"
}

# Shows the container's state and each port it publishes.
function _xsjs_status_show_container {
    if (-not $found_) {
        _xsjs_status_show_item ($i18n_.status_container_none -f $container_)
        return
    }
    $text_ = $i18n_.status_container -f $container_, $found_.State.Status
    _xsjs_status_show_item $text_
    $ports_ = @($found_.Ports.PSObject.Properties)
    foreach ($port_property_ in $ports_) {
        foreach ($binding_ in $port_property_.Value) {
            $text_ = $i18n_.status_published -f (
                $port_property_.Name, $binding_.HostIp, $binding_.HostPort)
            _xsjs_status_show_item $text_
        }
    }
    if (-not $ports_) {
        _xsjs_status_show_item ($i18n_.status_unpublished -f $container_)
    }
}

# Shows each serve program that start runs in the container.
function _xsjs_status_show_servers {
    foreach ($server_ in $servers_) {
        $text_ = $i18n_.status_server -f $server_.Id, $server_.CommandLine
        _xsjs_status_show_item $text_
    }
    if (-not $servers_) {
        _xsjs_status_show_item $i18n_.status_server_none
    }
}

# Shows what listens on the port in Windows and where connections come from.
function _xsjs_status_show_port {
    $connections_ = @(Get-NetTCPConnection | Where-Object LocalPort -EQ $port_)
    $listeners_ = @($connections_ | Where-Object State -EQ 'Listen')
    foreach ($group_ in $listeners_ | Group-Object OwningProcess) {
        $owner_ = Get-Process -Id $group_.Name
        $addresses_ = ($group_.Group | ForEach-Object LocalAddress) -join ', '
        $text_ = $i18n_.status_listening -f (
            $port_, $owner_.ProcessName, $group_.Name, $addresses_)
        _xsjs_status_show_item $text_
    }
    if (-not $listeners_) {
        _xsjs_status_show_item ($i18n_.status_port_closed -f $port_)
    }
    $clients_ = @(
        $connections_ | Where-Object State -EQ 'Established' |
            ForEach-Object RemoteAddress | Sort-Object -Unique
    )
    if ($clients_) {
        $text_ = $i18n_.status_connections -f $port_, ($clients_ -join ', ')
        _xsjs_status_show_item $text_
    }
}

# Reads the container and its serve programs once, then shows each part.
function _xsjs_status_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_status_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $found_ = xsjs_util_get_container
    $servers_ = @(xsjs_util_get_servers $found_)

    _xsjs_status_show_summary
    _xsjs_status_show_container
    _xsjs_status_show_servers
    _xsjs_status_show_port
}

_xsjs_status_main
