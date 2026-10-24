﻿# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
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

# The strings, read from `en-US`, the one strings file.
$i18n_arguments_ = @{
    BindingVariable = 'i18n_'
    BaseDirectory   = $PSScriptRoot
    FileName        = 'i18n.psd1'
    UICulture       = 'en-US'
}
Import-LocalizedData @i18n_arguments_

# Returns the JSON file parsed, with its path for the errors of its settings.
function xsjs_util_read_json ([string]$path_) {
    $value_ = [IO.File]::ReadAllText($path_) | ConvertFrom-Json
    [pscustomobject]@{ Path = $path_; Value = $value_ }
}

# Returns the setting of the id, its keys joined by `.`, or throws if none.
function xsjs_util_get_setting ([object]$file_, [string]$id_) {
    $value_ = $file_.Value
    foreach ($part_ in $id_.Split('.')) {
        $property_ = $value_.PSObject.Properties | Where-Object {
            $_.MemberType -eq 'NoteProperty' -and $_.Name -ceq $part_
        }
        # Windows PowerShell reads a missing property as `$null`, a default.
        if (-not $property_) {
            throw ($i18n_.setting_missing -f $file_.Path, $id_)
        }
        $value_ = $property_.Value
    }
    # The comma returns an array whole, a one item array too.
    ,$value_
}

# Not `$settings_`, the name of a local in two scripts, which callees see.
$settings_json_ = xsjs_util_read_json (
    Join-Path (Split-Path -Parent $PSScriptRoot) 'settings.json')
$port_ = xsjs_util_get_setting $settings_json_ 'powershell.windows_port'
# Linux ttyd's port on WSL's `bind_address`, which a port proxy forwards to.
$linux_port_ = xsjs_util_get_setting $settings_json_ 'powershell.linux_port'
$bind_address_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.bind_address')
$bootstrap_script_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.bootstrap_script')
# The page ttyd serves, which `page_build.py` writes into `build/`.
$engine_page_ = xsjs_util_get_setting $settings_json_ 'powershell.engine_page'
# Where install builds ttyd and the binary it makes, relative to the checkout.
$ttyd_build_path_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.ttyd_build')
$ttyd_binary_path_ = "$ttyd_build_path_/ttyd"
$terminal_type_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.terminal_type')
$srv_buf_size_ = xsjs_util_get_setting $settings_json_ 'srv_buf_size'
# Where start installs the server, below the Linux user's home.
$linux_folder_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.linux_folder')
$task_name_ = xsjs_util_get_setting $settings_json_ 'powershell.task_name'
$firewall_rule_name_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.firewall_rule')
# The TLS key and ttyd password live outside the repo, for this user only.
$state_path_ = Join-Path $env:LOCALAPPDATA (
    xsjs_util_get_setting $settings_json_ 'powershell.state_folder')
$certificate_path_ = Join-Path $state_path_ (
    xsjs_util_get_setting $settings_json_ 'powershell.certificate_file')
$key_path_ = Join-Path $state_path_ (
    xsjs_util_get_setting $settings_json_ 'powershell.key_file')
# How long a new TLS certificate lasts. Apple devices refuse longer ones.
$certificate_days_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.certificate_days')
$runner_path_ = Join-Path $state_path_ (
    xsjs_util_get_setting $settings_json_ 'powershell.runner_file')
$ttyd_log_path_ = Join-Path $state_path_ (
    xsjs_util_get_setting $settings_json_ 'powershell.ttyd_log_file')
# The tries of each poll, a default chosen by its writer.
$poll_tries_ = xsjs_util_get_setting $settings_json_ 'powershell.poll_tries'
# The wait before each try of a poll, a default chosen by its writer.
$poll_milliseconds_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.poll_milliseconds')
# The width of an object logged as text, a default chosen by its writer.
$output_width_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.output_width')

# Returns the command of the script block with its variables' values.
function xsjs_util_get_command_text {
    # Private, so a child scope's lookup of a command's variable skips them.
    [scriptblock]$private:command_ = $args[0]
    $private:type_ = [Management.Automation.Language.VariableExpressionAst]
    $private:pipeline_ = (
        $command_.Ast.EndBlock.Statements[0].PipelineElements[0])
    $private:elements_ = $pipeline_.CommandElements
    $private:words_ = foreach ($private:element_ in $elements_) {
        if ($element_ -is $type_) {
            $private:name_ = $element_.VariablePath.UserPath
            (& { Get-Variable $args[0] -ValueOnly } $name_) -join ' '
        } else {
            $element_.Extent.Text
        }
    }
    $words_ -join ' '
}

# Returns the user and password argument, `$null` if none, or throws usage.
function xsjs_util_get_credential ([object[]]$arguments_) {
    if ($arguments_.Count -eq 0) { return $null }
    if ($arguments_.Count -eq 1 -and "$($arguments_[0])" -match '^[^:]+:.') {
        return "$($arguments_[0])"
    }
    throw ($i18n_.start_usage -f $script_name_)
}

# Returns WSL's default distribution's name and state, or nothing if none.
function xsjs_util_get_distribution {
    foreach ($line_ in xsjs_util_get_wsl 0 '--list', '--verbose') {
        if ($line_ -match '^\*\s*(\S+)\s+(\S+)') {
            $name_ = $Matches[1]
            $state_ = $Matches[2]
            # The state is in the display language, so ask which ones run.
            $list_ = '--list', '--running', '--quiet'
            return [pscustomobject]@{
                Name    = $name_
                State   = $state_
                Running = $name_ -in @(xsjs_util_get_wsl 0 $list_)
            }
        }
    }
}

# Returns the SHA256 fingerprint of the certificate's bytes, colon separated.
function xsjs_util_get_fingerprint ([byte[]]$certificate_) {
    $sha256_ = [Security.Cryptography.SHA256]::Create()
    [BitConverter]::ToString($sha256_.ComputeHash($certificate_)).Replace(
        '-', ':')
}

# Returns the folder in Linux, the server root, that holds ttyd and the engine.
function xsjs_util_get_linux_path {
    $home_ = xsjs_util_get_wsl 0 '-e', 'printenv', 'HOME'
    "$home_/$linux_folder_"
}

# Returns the PID and command line of each ttyd that start runs in Linux.
function xsjs_util_get_linux_servers ([string]$linux_path_) {
    # `pgrep` exits 1 when no process matches.
    $lines_ = xsjs_util_get_wsl 0, 1 '-e', 'pgrep', '-a', '-x', 'ttyd'
    # Only ttyd with start's options and command, whatever TLS options between.
    $options_ = (xsjs_util_get_ttyd_options $linux_path_) -join ' '
    $command_ = (xsjs_util_get_ttyd_command $linux_path_) -join ' '
    $ordinal_ = [StringComparison]::Ordinal
    foreach ($line_ in $lines_) {
        $id_, $command_line_ = $line_ -split ' ', 2
        if ($command_line_.StartsWith("$options_ ", $ordinal_) -and
            $command_line_.EndsWith(" $command_", $ordinal_)) {
            [pscustomobject]@{ Id = [int]$id_; CommandLine = $command_line_ }
        }
    }
}

# Returns the localhost address, HTTPS when there is a credential.
function xsjs_util_get_local_url {
    if ($credential_) { return "https://localhost:$port_/" }
    "http://localhost:$port_/"
}

# Returns the text escaped for plain Markdown text in the log.
function xsjs_util_get_markdown_text ([string]$text_) {
    # mdformat writes every backslash in plain text as two.
    $text_.Replace('\', '\\')
}

# Returns the command ttyd runs for each connection, after its options.
function xsjs_util_get_ttyd_command ([string]$linux_path_) {
    'python3', "$linux_path_/python/$bootstrap_script_", '--root', $linux_path_
}

# Returns ttyd and its options in Linux, before any for TLS.
function xsjs_util_get_ttyd_options ([string]$linux_path_) {
    "$linux_path_/ttyd"
    # `-W` lets input in, `-O` checks Origin. `-i lo` binds 10.255.255.254.
    '-p', "$linux_port_", '-i', $bind_address_, '-W', '-O'
    # `-T dumb` reports a terminal that shows lines, not escape sequences.
    '-T', $terminal_type_, '--index', "$linux_path_/$engine_page_"
    # `--url-arg` lets the page append a role to the command.
    '--url-arg'
    # `--srv-buf-size`: the receive chunk, `srv_buf_size`, that a patch adds.
    '--srv-buf-size', "$srv_buf_size_"
}

# Returns the lines WSL prints, throwing unless it exits with one of the codes.
function xsjs_util_get_wsl ([int[]]$exit_codes_, [string[]]$wsl_arguments_) {
    $lines_ = @(xsjs_util_get_wsl_lines $wsl_arguments_)
    if ($LASTEXITCODE -notin $exit_codes_) {
        $command_ = 'wsl ' + ($wsl_arguments_ -join ' ')
        $message_ = $i18n_.exit_code -f $command_, $LASTEXITCODE
        throw ((@($message_) + $lines_) -join "`n")
    }
    $lines_
}

# Returns the lines WSL prints for the arguments, cleaned and without blanks.
function xsjs_util_get_wsl_lines ([string[]]$wsl_arguments_) {
    $ErrorActionPreference = 'Continue'
    & wsl.exe @wsl_arguments_ 2>&1 |
        ForEach-Object { "$_".Replace("`0", '').Trim() } |
        Where-Object { $_ }
}

# Runs a native command and logs it expanded, then its exit code and output.
function xsjs_util_invoke_native {
    # Private, so the expansion and the run of a command look past it.
    [scriptblock]$private:command_ = $args[0]
    xsjs_util_write_log ('`{0}`' -f (xsjs_util_get_command_text $command_))
    $ErrorActionPreference = 'Continue'
    $output_ = & $command_ 2>&1
    $exit_ = $i18n_.exit_code -f $command_.ToString().Trim(), $LASTEXITCODE
    xsjs_util_write_log $exit_
    $output_ | xsjs_util_write_log_output
}

# Starts a log beside the script and returns its path.
function xsjs_util_open_log ([string]$script_path_) {
    $log_path_ = "$script_path_.md"
    $log_title_ = $i18n_.log_title -f (Split-Path -Leaf $script_path_)
    [IO.File]::WriteAllText($log_path_, "# $log_title_`n")
    Write-Host ($i18n_.log_path -f $log_path_)
    $now_ = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    # Windows PowerShell leaves the update build revision out of the version.
    $version_ = [Environment]::OSVersion.Version
    $current_ = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
    $revision_ = Get-ItemPropertyValue $current_ -Name UBR
    $os_ = 'Windows {0}.{1}' -f $version_.ToString(3), $revision_
    $started_ = $i18n_.started -f $now_, $os_, $PSVersionTable.PSVersion
    xsjs_util_write_log $started_
    $log_path_
}

# Removes the firewall rule if there is one, logging either way.
function xsjs_util_remove_firewall_rule {
    $rule_ = Get-NetFirewallRule | Where-Object Name -EQ $firewall_rule_name_
    if ($rule_) {
        Remove-NetFirewallRule -Name $firewall_rule_name_
        xsjs_util_write_log ($i18n_.firewall_closed -f $port_)
    } else {
        xsjs_util_write_log (
            $i18n_.status_firewall_none -f $firewall_rule_name_)
    }
}

# Removes each port proxy from the port to Linux ttyd, logging either way.
function xsjs_util_remove_proxy {
    $path_ = 'HKLM:\SYSTEM\CurrentControlSet\Services\PortProxy\v4tov4\tcp'
    $names_ = @()
    if (Test-Path $path_) {
        $key_ = Get-Item $path_
        # A value's name is where it listens, its data where it connects.
        $names_ = @(
            $key_.GetValueNames() | Where-Object {
                $_ -like "*/$port_" -and
                $key_.GetValue($_) -eq "$bind_address_/$linux_port_"
            }
        )
    }
    foreach ($name_ in $names_) {
        $address_ = ($name_ -split '/')[0]
        $delete_ = @(
            'interface', 'portproxy', 'delete', 'v4tov4'
            "listenaddress=$address_", "listenport=$port_"
        )
        xsjs_util_invoke_native { netsh @delete_ }
        if ($LASTEXITCODE -ne 0) {
            throw ($i18n_.proxy_remove_failed -f $address_, $port_)
        }
        xsjs_util_write_log ($i18n_.proxy_removed -f $address_, $port_)
    }
    if (-not $names_) { xsjs_util_write_log ($i18n_.proxy_none -f $port_) }
}

# Throws unless this PowerShell runs as administrator.
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

# Stops the ttyd that the task runs in Linux, then the task.
function xsjs_util_step_stop_server {
    xsjs_util_write_log_section ($i18n_.stop_server -f $port_)
    $ids_ = @()
    $distribution_ = xsjs_util_get_distribution
    # Linux runs no ttyd while its default distribution is stopped.
    if ($distribution_ -and $distribution_.Running) {
        $path_ = xsjs_util_get_linux_path
        $ids_ = @(xsjs_util_get_linux_servers $path_ | ForEach-Object Id)
    }
    if ($ids_) {
        # Ending `wsl.exe` need not end ttyd in Linux, so signal ttyd itself.
        xsjs_util_invoke_native { wsl -e kill -TERM @ids_ }
        if ($LASTEXITCODE -ne 0) {
            throw ($i18n_.ttyd_stop_failed -f ($ids_ -join ', '))
        }
        $left_ = $ids_
        for ($try_ = 0; $left_ -and $try_ -lt $poll_tries_; $try_++) {
            Start-Sleep -Milliseconds $poll_milliseconds_
            $left_ = @(xsjs_util_get_linux_servers $path_)
        }
        if ($left_) {
            $seconds_ = $poll_tries_ * $poll_milliseconds_ / 1000
            throw ($i18n_.ttyd_not_stopped -f ($ids_ -join ', '), $seconds_)
        }
        xsjs_util_write_log ($i18n_.ttyd_stopped -f ($ids_ -join ', '))
    }
    $task_ = Get-ScheduledTask | Where-Object TaskName -EQ $task_name_
    $running_ = $task_.State -eq 'Running'
    if ($running_) {
        Stop-ScheduledTask -TaskName $task_name_
        xsjs_util_write_log ($i18n_.task_stopped -f $task_name_)
    }
    if (-not $ids_ -and -not $running_) {
        xsjs_util_write_log $i18n_.server_not_running
    }
}

# Reloads `$env:Path` from the machine and user, to find new installs.
function xsjs_util_update_path {
    $machine_path_ = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user_path_ = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine_path_;$user_path_"
}

# Shows the error in red and logs its message, output and position.
function xsjs_util_write_failure {
    param([Management.Automation.ErrorRecord]$record_)
    $message_ = $i18n_.failed_message -f $record_.Exception.Message
    Write-Host $message_ -ForegroundColor Red
    xsjs_util_write_log_section $i18n_.failed
    # The first line is the message. Any more is output, so it gets a block.
    $lines_ = $record_.Exception.Message.Trim() -split "`r?`n", 2
    $text_ = xsjs_util_get_markdown_text $lines_[0]
    xsjs_util_write_log_alert CAUTION $text_
    if ($lines_.Count -gt 1) { $lines_[1] | xsjs_util_write_log_output }
    $record_.InvocationInfo.PositionMessage | xsjs_util_write_log_output
}

# Appends the text to the log as a block, when there is a log.
function xsjs_util_write_log ([string]$text_) {
    # Blocks start blank so the file ends in one line feed, as mdformat wants.
    if ($log_path_) { [IO.File]::AppendAllText($log_path_, "`n$text_`n") }
}

# Logs the text as a Markdown alert of the given kind.
function xsjs_util_write_log_alert ([string]$kind_, [string]$text_) {
    $lines_ = @("[!$kind_]") + ($text_.Trim() -split "`r?`n")
    $quoted_ = $lines_ | ForEach-Object { "> $_".TrimEnd() }
    xsjs_util_write_log ($quoted_ -join "`n")
}

# Logs its pipeline input as one fenced text block, and warnings as problems.
function xsjs_util_write_log_output {
    $lines_ = foreach ($item_ in $input) {
        if ($item_ -is [Management.Automation.WarningRecord]) {
            xsjs_util_write_problem $item_.Message
        } elseif ($item_ -is [Management.Automation.ErrorRecord]) {
            $item_.ToString()
        } elseif ($item_ -is [string]) {
            $item_
        } else {
            ($item_ | Out-String -Width $output_width_).Trim()
        }
    }
    $text_ = ($lines_ -join "`n").Replace("`0", '').Trim()
    $text_ = $text_.Replace("`r`n", "`n")
    if ($text_) { xsjs_util_write_log ('```text', $text_, '```' -join "`n") }
}

# Logs the text as a section heading.
function xsjs_util_write_log_section ([string]$text_) {
    xsjs_util_write_log "## $text_"
}

# Shows the text and logs it as a note.
function xsjs_util_write_notice ([string]$text_) {
    Write-Host $text_
    xsjs_util_write_log_alert NOTE $text_
}

# Shows the text as a warning and logs it as one.
function xsjs_util_write_problem ([string]$text_) {
    Write-Warning $text_
    xsjs_util_write_log_alert WARNING (xsjs_util_get_markdown_text $text_)
}
