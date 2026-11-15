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

$ErrorActionPreference = 'Stop'
$progressPreference = 'silentlyContinue'

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
    , $value_
}

# This checkout, whose parent folder the container mounts.
$checkout_path_ = Split-Path -Parent $PSScriptRoot
# Not `$settings_`, the name of a local in two scripts, which callees see.
$settings_json_ = xsjs_util_read_json (
    Join-Path $checkout_path_ 'settings.json')
# The port the container serves on and publishes on Windows' 127.0.0.1.
$port_ = xsjs_util_get_setting $settings_json_ 'powershell.windows_port'
# The address of Windows that the container's port is published on.
$windows_address_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.windows_address')
# The wslc container that serves and runs the tests, made by hand.
$container_ = xsjs_util_get_setting $settings_json_ 'powershell.container'
# The container's user, who runs everything there, and that user's checkout.
$container_user_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.container_user')
$container_root_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.container_root')
# The container's address the serve program binds, which the publish reaches.
$container_interface_ = (
    xsjs_util_get_setting $settings_json_ 'powershell.container_interface')
# The script that makes the container's checkout a copy of this one.
$sync_script_ = xsjs_util_get_setting $settings_json_ 'powershell.sync_script'
# The serve program's log, from the home of the container's user.
$serve_log_ = '{0}/{1}' -f (
    (xsjs_util_get_setting $settings_json_ 'powershell.linux_folder'),
    (xsjs_util_get_setting $settings_json_ 'powershell.ttyd_log_file'))
# The user's environment variable that the serve program passes on.
$provider_key_name_ = xsjs_util_get_setting $settings_json_ 'provider.variable'
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

# Returns the container as wslc inspects it, or nothing when there is none.
function xsjs_util_get_container {
    $list_ = 'list', '--all', '--format', 'json'
    $names_ = xsjs_util_get_wslc 0 $list_ | Where-Object { $_ } |
        ForEach-Object { ($_ | ConvertFrom-Json).Names }
    if ($names_ -cnotcontains $container_) { return }
    $inspect_ = 'inspect', '--type', 'container', $container_
    $text_ = (xsjs_util_get_wslc 0 $inspect_) -join "`n"
    ($text_ | ConvertFrom-Json)[0]
}

# Returns the path WSL gives a folder of a Windows drive, as /mnt/c/Users.
function xsjs_util_get_linux_path ([string]$path_) {
    if (-not ($path_ -match '^([A-Za-z]):\\(.*)$')) {
        throw ($i18n_.wslc_drive_missing -f $path_)
    }
    $folder_ = $Matches[2].TrimEnd('\').Replace('\', '/')
    '/mnt/{0}/{1}' -f $Matches[1].ToLowerInvariant(), $folder_
}

# Returns the localhost address.
function xsjs_util_get_local_url {
    "http://localhost:$port_/"
}

# Returns the text escaped for plain Markdown text in the log.
function xsjs_util_get_markdown_text ([string]$text_) {
    # mdformat writes every backslash in plain text as two.
    $text_.Replace('\', '\\')
}

# Returns the serve program's command in the container, before any switch.
function xsjs_util_get_serve_command {
    # The published port reaches the container's 0.0.0.0, not its 127.0.0.1.
    'python3', 'python/xsjs_serve.py', '--port', "$port_"
    '--interface', $container_interface_
}

# Returns the PID and command line of each serve program that start runs.
function xsjs_util_get_servers ([object]$found_) {
    # A container that is missing or stopped runs nothing.
    if (-not $found_ -or -not $found_.State.Running) { return }
    # `pgrep` exits 1 when no process matches.
    $pgrep_ = @(
        'exec', '-u', $container_user_, $container_
        'pgrep', '-a', '-u', $container_user_, '-x', 'python3'
    )
    $command_ = (xsjs_util_get_serve_command) -join ' '
    $ordinal_ = [StringComparison]::Ordinal
    foreach ($line_ in xsjs_util_get_wslc 0, 1 $pgrep_) {
        $id_, $command_line_ = "$line_" -split ' ', 2
        $switched_ = $command_line_.StartsWith("$command_ ", $ordinal_)
        if ($command_line_ -ceq $command_ -or $switched_) {
            [pscustomobject]@{ Id = [int]$id_; CommandLine = $command_line_ }
        }
    }
}

# Returns the arguments of wslc that make the container's checkout a copy.
function xsjs_util_get_sync_arguments {
    $source_ = xsjs_util_get_linux_path (Split-Path -Parent $checkout_path_)
    $checkout_ = '{0}/{1}' -f $source_, (Split-Path -Leaf $checkout_path_)
    'exec', '-u', $container_user_, $container_, 'bash'
    "$checkout_/$sync_script_", $checkout_, $container_root_
}

# Returns the lines wslc prints, throwing unless it exits with one of these.
function xsjs_util_get_wslc ([int[]]$exit_codes_, [string[]]$wslc_arguments_) {
    $lines_ = @(& wslc.exe @wslc_arguments_)
    if ($LASTEXITCODE -notin $exit_codes_) {
        $command_ = 'wslc ' + ($wslc_arguments_ -join ' ')
        throw ($i18n_.exit_code -f $command_, $LASTEXITCODE)
    }
    $lines_
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

# Throws unless the container adds no capability and mounts as WSL does.
function xsjs_util_step_check_container ([object]$found_) {
    xsjs_util_write_log_section ($i18n_.check_container -f $container_)
    if (-not $found_) { throw ($i18n_.container_missing -f $container_) }
    $added_ = $found_.HostConfig.CapAdd
    if ($added_) {
        $text_ = $i18n_.wslc_capability_added -f (
            $container_, ($added_ -join ', '))
        throw $text_
    }
    $source_ = Split-Path -Parent $checkout_path_
    $destination_ = xsjs_util_get_linux_path $source_
    # A Windows path matches in any case, as Windows reads it so.
    $mounts_ = @(
        $found_.Mounts | Where-Object {
            $_.Type -ceq 'bind' -and $_.Source -eq $source_ -and
            $_.Destination -ceq $destination_
        }
    )
    if (-not $mounts_) {
        $text_ = $i18n_.wslc_mount_missing -f (
            $container_, $source_, $destination_)
        throw $text_
    }
    xsjs_util_write_log ($i18n_.container_checked -f $container_)
}

# Stops each serve program that start runs, waiting for its end.
function xsjs_util_step_stop_server ([object]$found_) {
    xsjs_util_write_log_section ($i18n_.stop_server -f $port_)
    $ids_ = @(xsjs_util_get_servers $found_ | ForEach-Object Id)
    if (-not $ids_) {
        xsjs_util_write_log $i18n_.server_not_running
        return
    }
    # The program stops its ttyd's group at SIGTERM, then exits.
    $kill_ = @(
        'exec', '-u', $container_user_, $container_, 'kill', '-TERM'
    ) + @($ids_ | ForEach-Object { "$_" })
    xsjs_util_write_log ('`wslc {0}`' -f ($kill_ -join ' '))
    $null = xsjs_util_get_wslc 0 $kill_
    $left_ = $ids_
    for ($try_ = 0; $left_ -and $try_ -lt $poll_tries_; $try_++) {
        Start-Sleep -Milliseconds $poll_milliseconds_
        $left_ = @(xsjs_util_get_servers $found_)
    }
    if ($left_) {
        $seconds_ = $poll_tries_ * $poll_milliseconds_ / 1000
        throw ($i18n_.server_not_stopped -f ($ids_ -join ', '), $seconds_)
    }
    xsjs_util_write_log ($i18n_.server_stopped -f ($ids_ -join ', '))
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

# Shows the text as a warning and logs it as one.
function xsjs_util_write_problem ([string]$text_) {
    Write-Warning $text_
    xsjs_util_write_log_alert WARNING (xsjs_util_get_markdown_text $text_)
}
