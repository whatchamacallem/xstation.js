# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Serves the engine, python\bootstrap.py with its page,
# build\hyperposition-engine.html, through ttyd in WSL on port 5768, now and
# whenever you sign in to Windows. Run xsjs_install.ps1 once first, build the
# page in WSL with python3 python/page_build.py hyperposition-engine, then
# run this from an administrator PowerShell:
#
#     .\xsjs_start.ps1                    http://localhost:5768/
#     .\xsjs_start.ps1 username:password  https://<this PC>:5768/
#
# Each run copies the ttyd that xsjs_install.ps1 built, the engine's modules
# and seeds from python\, i18n\en-US.json, settings.json, test_settings.json,
# provider.json and the page into ~/.cache/xsjs in Linux, and ttyd runs that
# copy on port 5769 of WSL's 127.0.0.1. A Windows port proxy forwards port
# 5768 to it. The environment variable XSJS_PROVIDER_KEY of your user
# account, when set, is passed on to ttyd.
#
# With a username and password, ttyd serves HTTPS and asks for them, the
# port proxy listens on every network interface, and a Windows Firewall
# rule lets other computers in. Without, the port proxy listens on
# 127.0.0.1 only. The TLS certificate is self-signed, so browsers warn
# about it the first time: check the fingerprint they show against the one
# this script prints.
#
# Run it again to change the settings. Stop it with xsjs_stop.ps1.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Read `$args`, not `param()`, so a password may start with `-`.
$arguments_ = $args
# The checkout, where the server's files are copied from.
$checkout_path_ = $PSScriptRoot
# Where the engine's Python modules and seeds are copied from.
$python_path_ = Join-Path $PSScriptRoot 'python'
# The modules the server runs, by name in `python`, which start copies.
$runtime_modules_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.runtime_modules')
# The user's environment variable that ttyd passes on as the provider key.
$provider_key_name_ = xsjs_util_get_setting $settings_json_ 'provider.variable'
# The checkout's files that every root holds, beside ttyd and the page.
$root_files_ = xsjs_util_get_setting $settings_json_ 'powershell.root_files'

# Throws unless the files, ttyd, Python 3 and, for HTTPS, OpenSSL are present.
function _xsjs_start_step_check_installed {
    xsjs_util_write_log_section $i18n_.check_installed
    $path_ = Join-Path $python_path_ $bootstrap_script_
    if (-not (Test-Path $path_)) { throw ($i18n_.bootstrap_missing -f $path_) }
    $path_ = Join-Path $checkout_path_ "build\$engine_page_"
    if (-not (Test-Path $path_)) {
        $page_name_ = [IO.Path]::GetFileNameWithoutExtension($engine_page_)
        throw ($i18n_.page_missing -f $path_, $page_name_)
    }
    $version_ = '-e', $ttyd_binary_path_, '--version'
    xsjs_util_invoke_native { wsl --cd $checkout_path_ @version_ }
    if ($LASTEXITCODE -ne 0) { throw ($i18n_.not_installed -f 'ttyd') }
    xsjs_util_invoke_native { wsl -e python3 --version }
    if ($LASTEXITCODE -ne 0) { throw ($i18n_.not_installed -f 'Python 3') }
    if ($credential_) {
        xsjs_util_invoke_native { wsl -e openssl version }
        if ($LASTEXITCODE -ne 0) { throw ($i18n_.not_installed -f 'OpenSSL') }
    }
}

# Removes the port proxy, then throws if a process keeps either port.
function _xsjs_start_step_check_port {
    xsjs_util_write_log_section ($i18n_.check_port -f $port_, $linux_port_)
    xsjs_util_remove_proxy
    foreach ($port_number_ in $port_, $linux_port_) {
        # A closed port proxy or `wslrelay` frees its port a moment later.
        $owner_ = _xsjs_start_get_listener $port_number_
        for ($try_ = 0; $owner_ -and $try_ -lt $poll_tries_; $try_++) {
            Start-Sleep -Milliseconds $poll_milliseconds_
            $owner_ = _xsjs_start_get_listener $port_number_
        }
        if ($owner_) {
            $in_use_ = $i18n_.port_in_use -f (
                $port_number_, $owner_.ProcessName, $owner_.Id)
            throw $in_use_
        }
        xsjs_util_write_log ($i18n_.port_free -f $port_number_)
    }
}

# Returns the process listening on the port in Windows, if any.
function _xsjs_start_get_listener ([int]$port_number_) {
    $listener_ = Get-NetTCPConnection | Where-Object {
        $_.State -eq 'Listen' -and $_.LocalPort -eq $port_number_
    } | Select-Object -First 1
    if ($listener_) { Get-Process -Id $listener_.OwningProcess }
}

# Copies the files and folders, named from the checkout, into the Linux folder.
function _xsjs_start_copy_files ([string[]]$sources_, [string]$target_) {
    $copy_ = @('cp', '-r') + $sources_ + $target_
    xsjs_util_invoke_native { wsl --cd $checkout_path_ -e @copy_ }
    if ($LASTEXITCODE -ne 0) {
        throw ($i18n_.bootstrap_not_installed -f $target_)
    }
}

# Copies ttyd, engine, seeds, strings, settings, provider and page to Linux.
function _xsjs_start_step_install_server {
    xsjs_util_write_log_section $i18n_.install_server
    $folders_ = "$linux_path_/python", "$linux_path_/i18n"
    # The copies of earlier runs go, so the root holds this checkout's only.
    xsjs_util_invoke_native { wsl -e rm -rf @folders_ }
    if ($LASTEXITCODE -ne 0) {
        throw ($i18n_.bootstrap_not_installed -f $linux_path_)
    }
    xsjs_util_invoke_native { wsl -e mkdir -p @folders_ }
    if ($LASTEXITCODE -ne 0) {
        throw ($i18n_.bootstrap_not_installed -f $linux_path_)
    }
    $modules_ = @($runtime_modules_ | ForEach-Object { "python/$_.py" })
    $files_ = @($ttyd_binary_path_) + $root_files_ + "build/$engine_page_"
    _xsjs_start_copy_files $files_ $linux_path_
    _xsjs_start_copy_files ($modules_ + 'python/seed') "$linux_path_/python"
    _xsjs_start_copy_files 'i18n/en-US.json' "$linux_path_/i18n"
    xsjs_util_write_log ($i18n_.server_installed -f $linux_path_)
}

# Keeps or makes the TLS certificate and returns its fingerprint.
function _xsjs_start_step_make_certificate {
    xsjs_util_write_log_section $i18n_.make_certificate
    $null = New-Item -ItemType Directory -Force $state_path_
    $certificate_ = Split-Path -Leaf $certificate_path_
    $key_ = Split-Path -Leaf $key_path_
    $keep_ = $false
    if ((Test-Path $certificate_path_) -and (Test-Path $key_path_)) {
        # Keep it until it expires, so browsers that accepted it don't warn.
        $check_ = 'x509', '-checkend', '0', '-noout', '-in', $certificate_
        xsjs_util_invoke_native { wsl --cd $state_path_ -e openssl @check_ }
        $keep_ = $LASTEXITCODE -eq 0
    }
    if ($keep_) {
        xsjs_util_write_log ($i18n_.certificate_kept -f $state_path_)
    } else {
        $name_ = $env:COMPUTERNAME
        $names_ = @("DNS:$name_", 'DNS:localhost', 'IP:127.0.0.1') + @(
            _xsjs_start_get_addresses | ForEach-Object { "IP:$_" }
        )
        $request_ = @(
            'req', '-x509', '-newkey', 'rsa:2048', '-nodes'
            '-days', $certificate_days_
            '-subj', "/CN=$name_"
            '-addext', ('subjectAltName=' + ($names_ -join ','))
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

# Returns the addresses other computers can reach this PC on.
function _xsjs_start_get_addresses {
    # This PC's IPv4 addresses on networks with a default gateway.
    Get-NetIPConfiguration | Where-Object IPv4DefaultGateway |
        ForEach-Object { $_.IPv4Address.IPAddress }
}

# Replaces the firewall rule that lets other computers reach the port.
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

# Removes the firewall rule, as serving localhost needs none.
function _xsjs_start_step_close_firewall {
    xsjs_util_write_log_section ($i18n_.close_firewall -f $port_)
    xsjs_util_remove_firewall_rule
}

# Forwards the port to Linux ttyd, from other computers only for HTTPS.
function _xsjs_start_step_add_proxy {
    xsjs_util_write_log_section ($i18n_.add_proxy -f $port_, $linux_port_)
    $address_ = '127.0.0.1'
    if ($credential_) { $address_ = '0.0.0.0' }
    # Windows' 127.0.0.1 reaches WSL's through `wslrelay`.
    $add_ = @(
        'interface', 'portproxy', 'add', 'v4tov4'
        "listenaddress=$address_", "listenport=$port_"
        "connectaddress=$bind_address_", "connectport=$linux_port_"
    )
    xsjs_util_invoke_native { netsh @add_ }
    if ($LASTEXITCODE -ne 0) { throw $i18n_.proxy_failed }
    $added_ = $i18n_.proxy_added -f (
        $address_, $port_, $linux_port_, $bind_address_)
    xsjs_util_write_log $added_
}

# Writes the runner, the script the task runs to start ttyd with the settings.
function _xsjs_start_step_write_runner {
    xsjs_util_write_log_section $i18n_.write_runner
    $wsl_path_ = (Get-Command wsl.exe).Source
    $tls_ = @()
    if ($credential_) {
        # ttyd in Linux reads the certificate and key from Windows' drive.
        $state_ = xsjs_util_get_wsl 0 '-e', 'wslpath', '-u', $state_path_
        $tls_ = @(
            '--ssl'
            '--ssl-cert', "$state_/$(Split-Path -Leaf $certificate_path_)"
            '--ssl-key', "$state_/$(Split-Path -Leaf $key_path_)"
            '-c', $credential_
        )
    }
    $wsl_arguments_ = @(
        '-e'
        xsjs_util_get_ttyd_options $linux_path_
        $tls_
        xsjs_util_get_ttyd_command $linux_path_
    )
    $command_line_ = @(
        $wsl_arguments_ | ForEach-Object { _xsjs_start_quote_argument $_ }
    ) -join ' '
    $shown_ = @(
        $wsl_arguments_ | ForEach-Object {
            if ($credential_ -and $_ -ceq $credential_) {
                $i18n_.credential_hidden
            } else {
                _xsjs_start_quote_argument $_
            }
        }
    ) -join ' '
    xsjs_util_write_log ('`{0} {1}`' -f $wsl_path_, $shown_)

    $runner_ = @(
        '# ' + ($i18n_.runner_comment -f $task_name_)
        '$env:WSLENV = (@($env:WSLENV, ' +
        (_xsjs_start_quote_literal $provider_key_name_) +
        ') -ne $null) -join '':'''
        '$server_ = @{'
        '    FilePath              = ' +
        (_xsjs_start_quote_literal $wsl_path_)
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

# Returns the text quoted as one Windows command line argument when needed.
function _xsjs_start_quote_argument ([string]$text_) {
    if ($text_ -and $text_ -notmatch '[\s"]') { return $text_ }
    $text_ = $text_ -replace '(\\*)"', '$1$1\"'
    '"{0}"' -f ($text_ -replace '(\\+)$', '$1$1')
}

# Returns the text as a single quoted PowerShell string.
function _xsjs_start_quote_literal ([string]$text_) {
    $escape_ = [Management.Automation.Language.CodeGeneration]
    "'{0}'" -f $escape_::EscapeSingleQuotedStringContent($text_)
}

# Registers the task that runs the runner without a window at sign in.
function _xsjs_start_step_register_task {
    xsjs_util_write_log_section $i18n_.register_task
    $user_ = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $system_ = Join-Path $env:SystemRoot 'System32'
    $powershell_ = Join-Path $system_ 'WindowsPowerShell\v1.0\powershell.exe'
    # `conhost --headless` runs PowerShell, and so `wsl.exe`, without a window.
    $action_ = @{
        Execute  = Join-Path $system_ 'conhost.exe'
        Argument = (
            '--headless "{0}" -NoProfile -NonInteractive ' +
            '-ExecutionPolicy Bypass -File "{1}"'
        ) -f $powershell_, $runner_path_
    }
    # Start at sign in, not boot: WSL is unreliable while nobody is signed in.
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
        Description = $i18n_.task_description -f $port_, $bootstrap_script_
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

# Starts the task and throws with ttyd's log unless it listens within a poll.
function _xsjs_start_step_start_task {
    xsjs_util_write_log_section ($i18n_.start_server -f $port_)
    if (Test-Path $ttyd_log_path_) { Remove-Item $ttyd_log_path_ }
    Start-ScheduledTask -TaskName $task_name_
    # `wslrelay` listens in Windows once ttyd listens in Linux.
    $relay_ = $null
    for ($try_ = 0; -not $relay_ -and $try_ -lt $poll_tries_; $try_++) {
        Start-Sleep -Milliseconds $poll_milliseconds_
        $relay_ = _xsjs_start_get_listener $linux_port_
    }
    if (-not $relay_) {
        $result_ = (Get-ScheduledTaskInfo -TaskName $task_name_).LastTaskResult
        $log_text_ = ''
        if (Test-Path $ttyd_log_path_) {
            $log_text_ = Get-Content $ttyd_log_path_ -Raw
        }
        $message_ = $i18n_.server_not_listening -f (
            $linux_port_, $result_, $ttyd_log_path_)
        throw "$message_`r`n$log_text_"
    }
    $ids_ = @(xsjs_util_get_linux_servers $linux_path_ | ForEach-Object Id)
    $listening_ = $i18n_.server_listening -f (
        $linux_port_, ($ids_ -join ', '), $relay_.ProcessName, $relay_.Id,
        $ttyd_log_path_)
    xsjs_util_write_log $listening_
    $proxy_ = _xsjs_start_get_listener $port_
    if (-not $proxy_) { throw ($i18n_.proxy_not_listening -f $port_) }
    $forwarding_ = $i18n_.proxy_listening -f (
        $port_, $proxy_.ProcessName, $proxy_.Id)
    xsjs_util_write_log $forwarding_
}

# Returns the addresses to open: localhost, or this PC's name and addresses.
function _xsjs_start_get_urls {
    if (-not $credential_) { return xsjs_util_get_local_url }
    "https://$($env:COMPUTERNAME.ToLower()):$port_/"
    _xsjs_start_get_addresses | ForEach-Object { "https://${_}:$port_/" }
}

# Sets up the server for any given credential, starts it and prints its URLs.
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
    $linux_path_ = xsjs_util_get_linux_path
    xsjs_util_step_stop_server
    _xsjs_start_step_check_port
    _xsjs_start_step_install_server
    $fingerprint_ = $null
    if ($credential_) {
        $fingerprint_ = _xsjs_start_step_make_certificate
        _xsjs_start_step_open_firewall
    } else {
        _xsjs_start_step_close_firewall
    }
    _xsjs_start_step_add_proxy
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
