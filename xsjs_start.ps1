# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Serves bootstrap.py in a web terminal (ttyd, which serves xterm.js) on
# port 5768, now and whenever you sign in to Windows. Run
# xsjs_install.ps1 once first, then run this from an administrator
# PowerShell:
#
#     .\xsjs_start.ps1                    http://localhost:5768/
#     .\xsjs_start.ps1 username:password  https://<this PC>:5768/
#
# With a username and password, ttyd serves HTTPS on every network
# interface and asks for them, and a Windows Firewall rule lets other
# computers in. The TLS certificate is self-signed, so browsers warn about
# it the first time: check the fingerprint they show against the one this
# script prints.
#
# Run it again to change the settings. Stop it with xsjs_stop.ps1.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Read from $args, not param(), so a password that starts with "-" can't
# be mistaken for a parameter name.
$arguments_ = $args
# Where bootstrap.py is, and where ttyd runs it.
$python_path_ = Join-Path $PSScriptRoot 'python'

function _xsjs_start_step_check_installed {
    xsjs_util_write_log_section $i18n_.check_installed
    $script_path_ = Join-Path $python_path_ $bootstrap_script_
    if (-not (Test-Path $script_path_)) {
        throw ($i18n_.bootstrap_missing -f $script_path_)
    }
    xsjs_util_update_path
    if (-not (Get-Command ttyd -ErrorAction SilentlyContinue)) {
        throw ($i18n_.not_installed -f 'ttyd')
    }
    xsjs_util_invoke_native { ttyd --version }
    xsjs_util_invoke_native { wsl -e python3 --version }
    if ($LASTEXITCODE -ne 0) { throw ($i18n_.not_installed -f 'Python 3') }
    if ($credential_) {
        xsjs_util_invoke_native { wsl -e openssl version }
        if ($LASTEXITCODE -ne 0) { throw ($i18n_.not_installed -f 'OpenSSL') }
    }
}

function _xsjs_start_step_check_port {
    xsjs_util_write_log_section ($i18n_.check_port -f $port_)
    $owner_ = _xsjs_start_get_listener
    if ($owner_) {
        throw ($i18n_.port_in_use -f $port_, $owner_.ProcessName, $owner_.Id)
    }
    xsjs_util_write_log ($i18n_.port_free -f $port_)
}

function _xsjs_start_get_listener {
    $connection_ = @{
        LocalPort   = $port_
        State       = 'Listen'
        ErrorAction = 'SilentlyContinue'
    }
    $listener_ = Get-NetTCPConnection @connection_ | Select-Object -First 1
    if ($listener_) { Get-Process -Id $listener_.OwningProcess }
}

function _xsjs_start_step_make_certificate {
    xsjs_util_write_log_section $i18n_.make_certificate
    $null = New-Item -ItemType Directory -Force $state_path_
    $certificate_ = Split-Path -Leaf $certificate_path_
    $key_ = Split-Path -Leaf $key_path_
    $keep_ = $false
    if ((Test-Path $certificate_path_) -and (Test-Path $key_path_)) {
        # Keep it until it expires, so browsers that accepted it don't warn
        # again.
        $check_ = 'x509', '-checkend', '0', '-noout', '-in', $certificate_
        xsjs_util_invoke_native { wsl --cd $state_path_ -e openssl @check_ }
        $keep_ = $LASTEXITCODE -eq 0
    }
    if ($keep_) {
        xsjs_util_write_log ($i18n_.certificate_kept -f $state_path_)
    } else {
        $name_ = $env:COMPUTERNAME
        $request_ = @(
            'req', '-x509', '-newkey', 'rsa:2048', '-nodes'
            '-days', $certificate_days_
            '-subj', "/CN=$name_"
            '-addext', "subjectAltName=DNS:$name_,DNS:localhost,IP:127.0.0.1"
            '-keyout', $key_, '-out', $certificate_
        )
        xsjs_util_invoke_native { wsl --cd $state_path_ -e openssl @request_ }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.certificate_failed }
        xsjs_util_write_log ($i18n_.certificate_made -f $state_path_)
    }
    $show_ = 'x509', '-noout', '-fingerprint', '-sha256', '-in', $certificate_
    $fingerprint_ = wsl --cd $state_path_ -e openssl @show_
    if ($LASTEXITCODE -ne 0) { throw $i18n_.certificate_failed }
    $fingerprint_ = "$fingerprint_".Trim() -replace '^.*=', ''
    xsjs_util_write_log ($i18n_.certificate_fingerprint -f $fingerprint_)
    $fingerprint_
}

function _xsjs_start_step_open_firewall {
    xsjs_util_write_log_section ($i18n_.open_firewall -f $port_)
    xsjs_util_remove_firewall_rule
    $rule_ = @{
        Name        = $firewall_rule_name_
        DisplayName = $i18n_.firewall_display_name -f $port_
        Description = $i18n_.firewall_description
        Direction   = 'Inbound'
        Protocol    = 'TCP'
        LocalPort   = $port_
        Action      = 'Allow'
        Profile     = 'Any'
    }
    $null = New-NetFirewallRule @rule_
    xsjs_util_write_log ($i18n_.firewall_opened -f $port_)
}

function _xsjs_start_step_close_firewall {
    xsjs_util_write_log_section ($i18n_.close_firewall -f $port_)
    xsjs_util_remove_firewall_rule
}

function _xsjs_start_step_write_runner {
    xsjs_util_write_log_section $i18n_.write_runner
    $ttyd_path_ = (Get-Command ttyd).Source
    $ttyd_arguments_ = @(
        '--port', $port_
        '--cwd', $python_path_
        '--writable'
        '--check-origin'
    )
    if ($credential_) {
        $ttyd_arguments_ += @(
            '--ssl'
            '--ssl-cert', $certificate_path_
            '--ssl-key', $key_path_
            '--credential', $credential_
        )
    } else {
        $ttyd_arguments_ += '--interface', '127.0.0.1'
    }
    # ttyd for Windows copies the command into a 256-byte buffer, so keep
    # it short and let --cwd say where bootstrap.py is.
    $ttyd_arguments_ += 'wsl.exe', '-e', 'python3', $bootstrap_script_
    $command_line_ = @(
        $ttyd_arguments_ | ForEach-Object { _xsjs_start_quote_argument $_ }
    ) -join ' '
    $shown_ = @(
        $ttyd_arguments_ | ForEach-Object {
            if ($credential_ -and $_ -ceq $credential_) {
                $i18n_.credential_hidden
            } else {
                _xsjs_start_quote_argument $_
            }
        }
    ) -join ' '
    xsjs_util_write_log ('`{0} {1}`' -f $ttyd_path_, $shown_)

    $runner_ = @(
        '# ' + ($i18n_.runner_comment -f $task_name_)
        '$server_ = @{'
        '    FilePath              = ' +
        (_xsjs_start_quote_literal $ttyd_path_)
        '    ArgumentList          = ' +
        (_xsjs_start_quote_literal $command_line_)
        '    WorkingDirectory      = ' +
        (_xsjs_start_quote_literal $state_path_)
        '    RedirectStandardError = ' +
        (_xsjs_start_quote_literal $ttyd_log_path_)
        '    NoNewWindow           = $true'
        '    PassThru              = $true'
        '    Wait                  = $true'
        '}'
        'exit (Start-Process @server_).ExitCode'
        ''
    ) -join "`r`n"
    $null = New-Item -ItemType Directory -Force $state_path_
    $utf8_bom_ = [Text.UTF8Encoding]::new($true)
    [IO.File]::WriteAllText($runner_path_, $runner_, $utf8_bom_)
    xsjs_util_write_log ($i18n_.runner_written -f $runner_path_)
}

function _xsjs_start_quote_argument ([string]$text_) {
    if ($text_ -and $text_ -notmatch '[\s"]') { return $text_ }
    $text_ = $text_ -replace '(\\*)"', '$1$1\"'
    '"{0}"' -f ($text_ -replace '(\\+)$', '$1$1')
}

function _xsjs_start_quote_literal ([string]$text_) {
    $escape_ = [Management.Automation.Language.CodeGeneration]
    "'{0}'" -f $escape_::EscapeSingleQuotedStringContent($text_)
}

function _xsjs_start_step_register_task {
    xsjs_util_write_log_section $i18n_.register_task
    $user_ = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $system_ = Join-Path $env:SystemRoot 'System32'
    $powershell_ = Join-Path $system_ 'WindowsPowerShell\v1.0\powershell.exe'
    # conhost --headless runs PowerShell, and so ttyd, without a window.
    $action_ = @{
        Execute  = Join-Path $system_ 'conhost.exe'
        Argument = (
            '--headless "{0}" -NoProfile -NonInteractive ' +
            '-ExecutionPolicy Bypass -File "{1}"'
        ) -f $powershell_, $runner_path_
    }
    # Start at sign-in rather than at boot: WSL is unreliable in a task
    # that runs while nobody is signed in.
    $principal_ = @{
        UserId    = $user_
        LogonType = 'Interactive'
        RunLevel  = 'Limited'
    }
    $settings_ = @{
        AllowStartIfOnBatteries    = $true
        DontStopIfGoingOnBatteries = $true
        ExecutionTimeLimit         = [TimeSpan]::Zero
        MultipleInstances          = 'IgnoreNew'
    }
    $task_ = @{
        TaskName    = $task_name_
        Description = $i18n_.task_description -f $port_
        Action      = New-ScheduledTaskAction @action_
        Trigger     = New-ScheduledTaskTrigger -AtLogOn -User $user_
        Principal   = New-ScheduledTaskPrincipal @principal_
        Settings    = New-ScheduledTaskSettingsSet @settings_
        Force       = $true
    }
    $null = Register-ScheduledTask @task_
    $registered_ = $i18n_.task_registered -f (
        $task_name_, $runner_path_, $user_)
    xsjs_util_write_log $registered_
}

function _xsjs_start_step_start_task {
    xsjs_util_write_log_section ($i18n_.start_server -f $port_)
    Remove-Item $ttyd_log_path_ -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName $task_name_
    $listener_ = $null
    for ($try_ = 0; -not $listener_ -and $try_ -lt 30; $try_++) {
        Start-Sleep -Milliseconds 500
        $listener_ = _xsjs_start_get_listener
    }
    if (-not $listener_) {
        $result_ = (Get-ScheduledTaskInfo -TaskName $task_name_).LastTaskResult
        $log_text_ = ''
        if (Test-Path $ttyd_log_path_) {
            $log_text_ = Get-Content $ttyd_log_path_ -Raw
        }
        $message_ = $i18n_.server_not_listening -f (
            $port_, $result_, $ttyd_log_path_)
        throw "$message_`r`n$log_text_"
    }
    $listening_ = $i18n_.server_listening -f (
        $port_, $listener_.Id, $ttyd_log_path_)
    xsjs_util_write_log $listening_
}

function _xsjs_start_get_urls {
    if (-not $credential_) { return xsjs_util_get_local_url }
    "https://$($env:COMPUTERNAME.ToLower()):$port_/"
    Get-NetIPConfiguration | Where-Object IPv4DefaultGateway |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        ForEach-Object { "https://${_}:$port_/" }
}

function _xsjs_start_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_start_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    $credential_ = xsjs_util_get_credential $arguments_
    if ($credential_) {
        xsjs_util_write_log ($i18n_.https_mode -f ($credential_ -split ':')[0])
    } else {
        xsjs_util_write_log $i18n_.localhost_mode
    }

    xsjs_util_step_check_administrator
    _xsjs_start_step_check_installed
    xsjs_util_step_stop_server
    _xsjs_start_step_check_port
    $fingerprint_ = $null
    if ($credential_) {
        $fingerprint_ = _xsjs_start_step_make_certificate
        _xsjs_start_step_open_firewall
    } else {
        _xsjs_start_step_close_firewall
    }
    _xsjs_start_step_write_runner
    _xsjs_start_step_register_task
    _xsjs_start_step_start_task

    xsjs_util_write_log_section $i18n_.done
    $urls_ = @(_xsjs_start_get_urls)
    $open_ = $i18n_.open_urls -f ($urls_ -join ' '), $bootstrap_script_
    xsjs_util_write_log $open_
    Write-Host ($i18n_.started_ok -f ($urls_ -join ' ')) -ForegroundColor Green
    if ($fingerprint_) {
        Write-Host ($i18n_.certificate_fingerprint -f $fingerprint_)
    }
}

_xsjs_start_main
