# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Prints a brief status of the web terminal: ttyd in Linux, the scheduled
# task that starts it when you sign in, ports 5768 and 5769, the Windows
# Firewall rule and any port proxies, WSL with the port ttyd listens on in
# Linux, and the processes serving it. It changes nothing, doesn't start
# WSL and doesn't write a log, so any PowerShell can run it:
#
#     .\xsjs_status.ps1
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Prints whether the server is running and whether it starts at sign in.
function _xsjs_status_show_summary {
    $running_ = $servers_.Count -gt 0
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

# Shows the scheduled task's state, mode, user and last result.
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

# Prints the text as a list item.
function _xsjs_status_show_item ([string]$text_) {
    Write-Host "- $text_"
}

# Returns HTTP, or HTTPS with the user name, from a ttyd command line.
function _xsjs_status_get_mode ([string]$command_line_) {
    # The command line holds the password, so only the user name leaves here.
    if ($command_line_ -notmatch '--ssl(\s|$)') { return 'HTTP' }
    $user_ = ''
    if ($command_line_ -match '(^|\s)(--credential|-c)\s+"?([^:"]+):') {
        $user_ = $Matches[3]
    }
    $i18n_.status_https -f $user_
}

# Shows each ttyd that start runs in Linux, with its mode and port.
function _xsjs_status_show_ttyd {
    foreach ($server_ in $servers_) {
        $text_ = $i18n_.status_ttyd -f (
            $server_.Id, (_xsjs_status_get_mode $server_.CommandLine),
            $linux_port_)
        _xsjs_status_show_item $text_
    }
    if (-not $servers_) { _xsjs_status_show_item $i18n_.status_ttyd_none }
}

# Shows what listens on the port in Windows and where connections come from.
function _xsjs_status_show_port ([int]$port_number_) {
    $query_ = @{ LocalPort = $port_number_; ErrorAction = 'SilentlyContinue' }
    $listeners_ = @(Get-NetTCPConnection @query_ -State Listen)
    foreach ($group_ in $listeners_ | Group-Object OwningProcess) {
        $owner_ = $processes_ | Where-Object ProcessId -EQ $group_.Name
        $addresses_ = ($group_.Group | ForEach-Object LocalAddress) -join ', '
        $text_ = $i18n_.status_listening -f (
            $port_number_, $owner_.Name, $group_.Name, $addresses_)
        _xsjs_status_show_item $text_
    }
    if (-not $listeners_) {
        _xsjs_status_show_item ($i18n_.status_port_closed -f $port_number_)
    }
    $clients_ = @(
        Get-NetTCPConnection @query_ -State Established |
            ForEach-Object RemoteAddress | Sort-Object -Unique
    )
    if ($clients_) {
        $text_ = $i18n_.status_connections -f (
            $port_number_, ($clients_ -join ', '))
        _xsjs_status_show_item $text_
    }
}

# Shows the firewall rule, if there is one.
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

# Shows every port proxy set up in Windows.
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

# Shows the default distribution and, if it runs, its port and bootstrappers.
function _xsjs_status_show_wsl {
    if (-not $distribution_) {
        _xsjs_status_show_item $i18n_.status_wsl_none
        return
    }
    $text_ = $i18n_.status_wsl -f $distribution_.Name, $distribution_.State
    _xsjs_status_show_item $text_
    if (-not $distribution_.Running) { return }
    $ss_ = '-e', 'ss', '-Hltnp', 'sport', '=', ":$linux_port_"
    $listeners_ = @(xsjs_util_get_wsl 0 $ss_)
    foreach ($listener_ in $listeners_) {
        # `ss` prints the state, queues, local and peer address, then users.
        $fields_ = $listener_ -split '\s+', 6
        $text_ = $i18n_.status_linux_listening -f (
            $linux_port_, $fields_[3], $fields_[5])
        _xsjs_status_show_item $text_
    }
    if (-not $listeners_) {
        _xsjs_status_show_item ($i18n_.status_linux_closed -f $linux_port_)
    }
    $command_ = xsjs_util_get_ttyd_command $linux_path_ |
        ForEach-Object { [regex]::Escape($_) }
    $pattern_ = '^' + ($command_ -join ' ') + '$'
    # `pgrep` exits 1 when no process matches.
    $found_ = @(xsjs_util_get_wsl 0, 1 '-e', 'pgrep', '-a', '-f', $pattern_)
    foreach ($line_ in $found_) {
        _xsjs_status_show_item ($i18n_.status_linux -f $line_)
    }
    if (-not $found_) {
        _xsjs_status_show_item ($i18n_.status_linux_none -f $bootstrap_script_)
    }
}

# Shows the tree of the runner's processes.
function _xsjs_status_show_processes {
    $runner_ = [regex]::Escape($runner_path_)
    $members_ = @(
        $processes_ | Where-Object { $_.CommandLine -match $runner_ }
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

# Prints the process, then the children it started, indented below it.
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

# Lists the files in the state folder.
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

# Shows the TLS certificate's expiry and fingerprint, if there is one.
function _xsjs_status_show_certificate {
    if (-not (Test-Path $certificate_path_)) { return }
    $x509_ = [Security.Cryptography.X509Certificates.X509Certificate2]
    $certificate_ = $x509_::new($certificate_path_)
    $fingerprint_ = xsjs_util_get_fingerprint $certificate_.RawData
    $text_ = $i18n_.status_certificate -f $certificate_.NotAfter, $fingerprint_
    _xsjs_status_show_item $text_
}

# Reads the processes, task and ttyd once, then shows each part of the status.
function _xsjs_status_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_status_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $processes_ = @(Get-CimInstance Win32_Process)
    $query_ = @{ TaskName = $task_name_; ErrorAction = 'SilentlyContinue' }
    $task_ = Get-ScheduledTask @query_
    $distribution_ = xsjs_util_get_distribution
    $servers_ = @()
    # Only look inside Linux when it already runs, so this doesn't start it.
    if ($distribution_ -and $distribution_.Running) {
        $linux_path_ = xsjs_util_get_linux_path
        $servers_ = @(xsjs_util_get_linux_servers $linux_path_)
    }

    _xsjs_status_show_summary
    _xsjs_status_show_task
    _xsjs_status_show_ttyd
    _xsjs_status_show_port $port_
    _xsjs_status_show_port $linux_port_
    _xsjs_status_show_firewall
    _xsjs_status_show_proxies
    _xsjs_status_show_wsl
    _xsjs_status_show_processes
    _xsjs_status_show_files
    _xsjs_status_show_certificate
}

_xsjs_status_main
