# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Prints a brief status of the web terminal: ttyd, the scheduled task that
# starts it when you sign in, its port, Windows Firewall rule and any port
# proxies, WSL, and the processes serving it. It changes nothing, doesn't
# start WSL and doesn't write a log, so any PowerShell can run it:
#
#     .\xsjs_status.ps1
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

function _xsjs_status_show_summary {
    $running_ = @(xsjs_util_get_servers).Count -gt 0
    $signin_ = $task_ -and $task_.State -ne 'Disabled'
    if ($running_ -and $signin_) {
        $text_ = $i18n_.status_running_signin
    } elseif ($running_) {
        $text_ = $i18n_.status_running
    } elseif ($signin_) {
        $text_ = $i18n_.status_stopped_signin
    } else {
        $text_ = $i18n_.status_stopped
    }
    $color_ = 'Gray'
    if ($running_) { $color_ = 'Green' }
    Write-Host ($text_ -f $task_name_, $port_) -ForegroundColor $color_
}

function _xsjs_status_show_task {
    if (-not $task_) {
        _xsjs_status_show_item ($i18n_.status_task_none -f $task_name_)
        return
    }
    $mode_ = $i18n_.status_no_runner -f $runner_path_
    if (Test-Path $runner_path_) {
        $mode_ = _xsjs_status_get_mode (Get-Content $runner_path_ -Raw)
    }
    $query_ = @{ TaskName = $task_name_; ErrorAction = 'SilentlyContinue' }
    $info_ = Get-ScheduledTaskInfo @query_
    $text_ = $i18n_.status_task -f (
        $task_name_, $task_.State, $mode_, $task_.Principal.UserId,
        $info_.LastTaskResult)
    _xsjs_status_show_item $text_
}

function _xsjs_status_show_item ([string]$text_) {
    Write-Host "- $text_"
}

function _xsjs_status_get_mode ([string]$command_line_) {
    # ttyd's command line holds the password, so only the user name
    # leaves here.
    if ($command_line_ -notmatch '--ssl(\s|$)') { return 'HTTP' }
    $user_ = ''
    if ($command_line_ -match '--credential\s+"?([^:"]+):') {
        $user_ = $Matches[1]
    }
    $i18n_.status_https -f $user_
}

function _xsjs_status_show_ttyd {
    $servers_ = @($processes_ | Where-Object Name -EQ 'ttyd.exe')
    foreach ($server_ in $servers_) {
        # 7681 is ttyd's default port.
        $server_port_ = 7681
        if ($server_.CommandLine -match '(--port|-p)\s+(\d+)') {
            $server_port_ = $Matches[2]
        }
        $text_ = $i18n_.status_ttyd -f (
            $server_.ProcessId, (_xsjs_status_get_mode $server_.CommandLine),
            $server_port_, $server_.CreationDate)
        _xsjs_status_show_item $text_
    }
    if (-not $servers_) { _xsjs_status_show_item $i18n_.status_ttyd_none }
}

function _xsjs_status_show_port {
    $query_ = @{ LocalPort = $port_; ErrorAction = 'SilentlyContinue' }
    $listeners_ = @(Get-NetTCPConnection @query_ -State Listen)
    foreach ($group_ in $listeners_ | Group-Object OwningProcess) {
        $owner_ = $processes_ | Where-Object ProcessId -EQ $group_.Name
        $addresses_ = ($group_.Group | ForEach-Object LocalAddress) -join ', '
        $text_ = $i18n_.status_listening -f (
            $port_, $owner_.Name, $group_.Name, $addresses_)
        _xsjs_status_show_item $text_
    }
    if (-not $listeners_) {
        _xsjs_status_show_item ($i18n_.status_port_closed -f $port_)
    }
    $clients_ = @(
        Get-NetTCPConnection @query_ -State Established |
            ForEach-Object RemoteAddress | Sort-Object -Unique
    )
    if ($clients_) {
        $text_ = $i18n_.status_connections -f $port_, ($clients_ -join ', ')
        _xsjs_status_show_item $text_
    }
}

function _xsjs_status_show_firewall {
    $rule_ = @{ Name = $firewall_rule_name_; ErrorAction = 'SilentlyContinue' }
    $found_ = Get-NetFirewallRule @rule_
    if (-not $found_) {
        $text_ = $i18n_.status_firewall_none -f $firewall_rule_name_
        _xsjs_status_show_item $text_
        return
    }
    $text_ = $i18n_.status_firewall -f (
        $firewall_rule_name_, $port_, $found_.Enabled, $found_.Profile)
    _xsjs_status_show_item $text_
}

function _xsjs_status_show_proxies {
    $path_ = 'HKLM:\SYSTEM\CurrentControlSet\Services\PortProxy'
    $proxies_ = @(
        Get-ChildItem $path_ -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object {
                $key_ = $_
                $kind_ = Split-Path -Leaf $key_.PSParentPath
                foreach ($name_ in $key_.GetValueNames()) {
                    $to_ = $key_.GetValue($name_)
                    $i18n_.status_proxy -f $kind_, $name_, $to_
                }
            }
    )
    if (-not $proxies_) { $proxies_ = @($i18n_.status_proxy_none) }
    $proxies_ | ForEach-Object { _xsjs_status_show_item $_ }
}

function _xsjs_status_get_wsl ([string[]]$wsl_arguments_) {
    $ErrorActionPreference = 'Continue'
    & wsl.exe @wsl_arguments_ 2>&1 |
        ForEach-Object { "$_".Replace("`0", '').Trim() } |
        Where-Object { $_ }
}

function _xsjs_status_show_wsl {
    $name_ = $null
    foreach ($line_ in _xsjs_status_get_wsl '--list', '--verbose') {
        if ($line_ -match '^\*\s*(\S+)\s+(\S+)') {
            $name_ = $Matches[1]
            $state_ = $Matches[2]
        }
    }
    if (-not $name_) {
        _xsjs_status_show_item $i18n_.status_wsl_none
        return
    }
    _xsjs_status_show_item ($i18n_.status_wsl -f $name_, $state_)
    # Only look inside Linux if it is already running, so this doesn't
    # start it.
    $running_ = _xsjs_status_get_wsl '--list', '--running', '--quiet'
    if ($name_ -notin $running_) { return }
    $pattern_ = '^python3 ' + [regex]::Escape($bootstrap_script_)
    $pgrep_ = '-e', 'pgrep', '-a', '-f', $pattern_
    $found_ = @(_xsjs_status_get_wsl $pgrep_) -match '^\d+ '
    foreach ($line_ in $found_) {
        _xsjs_status_show_item ($i18n_.status_linux -f $line_)
    }
    if (-not $found_) {
        _xsjs_status_show_item ($i18n_.status_linux_none -f $bootstrap_script_)
    }
}

function _xsjs_status_show_processes {
    $runner_ = [regex]::Escape($runner_path_)
    $members_ = @(
        $processes_ | Where-Object {
            $_.Name -eq 'ttyd.exe' -or $_.CommandLine -match $runner_
        }
    )
    if (-not $members_) {
        _xsjs_status_show_item $i18n_.status_processes_none
        return
    }
    _xsjs_status_show_item $i18n_.status_processes
    $ids_ = $members_ | ForEach-Object ProcessId
    foreach ($member_ in $members_) {
        if ($member_.ParentProcessId -notin $ids_) {
            _xsjs_status_show_process_tree $member_ '    '
        }
    }
}

function _xsjs_status_show_process_tree ($process_, [string]$indent_) {
    Write-Host ('{0}{1} {2}' -f $indent_, $process_.Name, $process_.ProcessId)
    $children_ = $processes_ | Where-Object {
        $_.ParentProcessId -eq $process_.ProcessId -and
        $_.CreationDate -ge $process_.CreationDate
    }
    foreach ($child_ in $children_) {
        _xsjs_status_show_process_tree $child_ "  $indent_"
    }
}

function _xsjs_status_show_files {
    $names_ = @(
        Get-ChildItem $state_path_ -File -ErrorAction SilentlyContinue |
            ForEach-Object Name
    )
    if ($names_) {
        $text_ = $i18n_.status_files -f $state_path_, ($names_ -join ', ')
        _xsjs_status_show_item $text_
    } else {
        _xsjs_status_show_item ($i18n_.status_files_none -f $state_path_)
    }
}

function _xsjs_status_show_certificate {
    if (-not (Test-Path $certificate_path_)) { return }
    $x509_ = [Security.Cryptography.X509Certificates.X509Certificate2]
    $certificate_ = $x509_::new($certificate_path_)
    $fingerprint_ = xsjs_util_get_fingerprint $certificate_.RawData
    $text_ = $i18n_.status_certificate -f $certificate_.NotAfter, $fingerprint_
    _xsjs_status_show_item $text_
}

function _xsjs_status_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_status_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $processes_ = @(Get-CimInstance Win32_Process)
    $query_ = @{ TaskName = $task_name_; ErrorAction = 'SilentlyContinue' }
    $task_ = Get-ScheduledTask @query_

    _xsjs_status_show_summary
    _xsjs_status_show_task
    _xsjs_status_show_ttyd
    _xsjs_status_show_port
    _xsjs_status_show_firewall
    _xsjs_status_show_proxies
    _xsjs_status_show_wsl
    _xsjs_status_show_processes
    _xsjs_status_show_files
    _xsjs_status_show_certificate
}

_xsjs_status_main
