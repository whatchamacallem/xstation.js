# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSUseDeclaredVarsMoreThanAssignments', '',
    Justification = 'The scripts that dot-source this file read these.')]
param()

$env:WSL_UTF8 = '1'
$ErrorActionPreference = 'Stop'
$progressPreference = 'silentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = (
    [Net.ServicePointManager]::SecurityProtocol -bor
    [Net.SecurityProtocolType]::Tls12
)

$i18n_arguments_ = @{
    BindingVariable = 'i18n_'
    BaseDirectory   = $PSScriptRoot
    FileName        = 'i18n.psd1'
}
try {
    Import-LocalizedData @i18n_arguments_
} catch {
    Import-LocalizedData @i18n_arguments_ -UICulture en-US
}

$port_ = 5768
$bootstrap_script_ = 'bootstrap.py'
$task_name_ = 'xstation.js'
$firewall_rule_name_ = 'xstation.js'
# The TLS key and the task's runner (which holds the ttyd password) live
# here, out of the repository, where only this Windows user can read them.
$state_path_ = Join-Path $env:LOCALAPPDATA 'xstation.js'
$certificate_path_ = Join-Path $state_path_ '_cached_cert.pem'
$key_path_ = Join-Path $state_path_ '_cached_key.pem'
# How long a new TLS certificate lasts. Apple devices refuse longer ones.
$certificate_days_ = 825
$runner_path_ = Join-Path $state_path_ 'serve.ps1'
$ttyd_log_path_ = Join-Path $state_path_ 'ttyd.log'

function xsjs_util_get_credential ([object[]]$arguments_) {
    if ($arguments_.Count -eq 0) { return $null }
    if ($arguments_.Count -eq 1 -and "$($arguments_[0])" -match '^[^:]+:.') {
        return "$($arguments_[0])"
    }
    throw ($i18n_.start_usage -f $script_name_)
}

function xsjs_util_get_fingerprint ([byte[]]$certificate_) {
    $sha256_ = [Security.Cryptography.SHA256]::Create()
    [BitConverter]::ToString($sha256_.ComputeHash($certificate_)).Replace(
        '-', ':')
}

function xsjs_util_get_local_url {
    if ($credential_) { return "https://localhost:$port_/" }
    "http://localhost:$port_/"
}

function xsjs_util_get_servers {
    Get-CimInstance Win32_Process -Filter "Name = 'ttyd.exe'" |
        Where-Object { $_.CommandLine -match "--port $port_(\s|$)" }
}

function xsjs_util_invoke_native ([scriptblock]$command_) {
    $ErrorActionPreference = 'Continue'
    $output_ = & $command_ 2>&1
    $exit_ = $i18n_.exit_code -f $command_.ToString().Trim(), $LASTEXITCODE
    xsjs_util_write_log $exit_
    $output_ | xsjs_util_write_log_output
}

function xsjs_util_open_log ([string]$script_path_) {
    $log_path_ = "$script_path_.md"
    try {
        $log_title_ = $i18n_.log_title -f (Split-Path -Leaf $script_path_)
        [IO.File]::WriteAllText($log_path_, "# $log_title_`r`n`r`n")
        Write-Host ($i18n_.log_path -f $log_path_)
    } catch {
        Write-Host ($i18n_.no_log -f $log_path_)
        return $null
    }
    $now_ = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    # Windows PowerShell leaves the update build revision out of the version.
    $version_ = [Environment]::OSVersion.Version
    $current_ = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    $revision_ = (Get-ItemProperty $current_ -ErrorAction SilentlyContinue).UBR
    if ($null -eq $revision_) { $revision_ = $version_.Revision }
    $os_ = 'Windows {0}.{1}' -f $version_.ToString(3), $revision_
    $started_ = $i18n_.started -f $now_, $os_, $PSVersionTable.PSVersion
    xsjs_util_write_log $started_
    $log_path_
}

function xsjs_util_remove_firewall_rule {
    $rule_ = @{ Name = $firewall_rule_name_; ErrorAction = 'SilentlyContinue' }
    if (Get-NetFirewallRule @rule_) {
        Remove-NetFirewallRule -Name $firewall_rule_name_
        xsjs_util_write_log ($i18n_.firewall_closed -f $port_)
    } else {
        xsjs_util_write_log (
            $i18n_.status_firewall_none -f $firewall_rule_name_)
    }
}

function xsjs_util_step_check_administrator {
    xsjs_util_write_log_section $i18n_.check_administrator
    $identity_ = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal_ = [Security.Principal.WindowsPrincipal]$identity_
    $role_ = [Security.Principal.WindowsBuiltInRole]::Administrator
    if (-not $principal_.IsInRole($role_)) {
        throw ($i18n_.not_administrator -f $script_name_)
    }
    xsjs_util_write_log ($i18n_.administrator_ok -f $identity_.Name)
}

function xsjs_util_step_stop_server {
    xsjs_util_write_log_section ($i18n_.stop_server -f $port_)
    $task_ = @{ TaskName = $task_name_; ErrorAction = 'SilentlyContinue' }
    $running_ = (Get-ScheduledTask @task_).State -eq 'Running'
    if ($running_) {
        Stop-ScheduledTask -TaskName $task_name_
        xsjs_util_write_log ($i18n_.task_stopped -f $task_name_)
    }
    # Stopping the task may leave ttyd running, and ttyd may have been
    # started some other way, so stop any ttyd serving this port as well.
    $servers_ = @(xsjs_util_get_servers)
    foreach ($server_ in $servers_) {
        Stop-Process -Id $server_.ProcessId -Force
        xsjs_util_write_log ($i18n_.ttyd_stopped -f $server_.ProcessId)
    }
    if ($servers_) {
        Start-Sleep -Seconds 1
    } elseif (-not $running_) {
        xsjs_util_write_log $i18n_.server_not_running
    }
}

function xsjs_util_update_path {
    $machine_path_ = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user_path_ = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine_path_;$user_path_"
}

function xsjs_util_write_failure {
    param([Management.Automation.ErrorRecord]$record_)
    $message_ = $i18n_.failed_message -f $record_.Exception.Message
    Write-Host $message_ -ForegroundColor Red
    xsjs_util_write_log_section $i18n_.failed
    xsjs_util_write_log_alert CAUTION $record_.Exception.Message
    $record_.InvocationInfo.PositionMessage | xsjs_util_write_log_output
}

function xsjs_util_write_log ([string]$text_) {
    if ($log_path_) { [IO.File]::AppendAllText($log_path_, "$text_`r`n`r`n") }
}

function xsjs_util_write_log_alert ([string]$kind_, [string]$text_) {
    $lines_ = @("[!$kind_]") + ($text_.Trim() -split "`r?`n")
    xsjs_util_write_log (($lines_ | ForEach-Object { "> $_" }) -join "`r`n")
}

function xsjs_util_write_log_output {
    $lines_ = foreach ($item_ in $input) {
        if ($item_ -is [Management.Automation.WarningRecord]) {
            xsjs_util_write_problem $item_.Message
        } elseif ($item_ -is [Management.Automation.ErrorRecord]) {
            $item_.ToString()
        } elseif ($item_ -is [string]) {
            $item_
        } else {
            ($item_ | Out-String -Width 200).Trim()
        }
    }
    $text_ = ($lines_ -join "`r`n").Replace("`0", '').Trim()
    if ($text_) { xsjs_util_write_log ('```text', $text_, '```' -join "`r`n") }
}

function xsjs_util_write_log_section ([string]$text_) {
    xsjs_util_write_log "## $text_"
}

function xsjs_util_write_notice ([string]$text_) {
    Write-Host $text_
    xsjs_util_write_log_alert NOTE $text_
}

function xsjs_util_write_problem ([string]$text_) {
    Write-Warning $text_
    xsjs_util_write_log_alert WARNING $text_
}
