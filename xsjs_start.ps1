# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Serves the engine on http://localhost:5768/ from the wslc container hype,
# made by hand or by powershell\test_wslc.ps1, which must publish port 5768
# on Windows' 127.0.0.1. Start makes hype's checkout a copy of this one by
# wslc_sync.sh, then runs python/xsjs_serve.py there in the background on the
# container's 0.0.0.0. That builds the page, makes the root ~/.cache/xsjs/root
# and serves it through ttyd, its log ~/.cache/xsjs/ttyd.log. Run it from any
# PowerShell:
#
#     .\xsjs_start.ps1 [--debug] [--verbose]
#
# --debug runs the page in debug mode, which the console role needs, and
# --verbose the console's shell at level 2 rather than 1. Run it again to
# serve this checkout anew. Stop it with xsjs_stop.ps1. Its `sh -c` scripts
# hold no double quote, as Windows PowerShell passes one to wslc unescaped.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# Read `$args`, not `param()`, as PowerShell takes `--debug` for a parameter.
$arguments_ = $args
# The switches start passes to the serve program, each given at most once.
$switch_names_ = 'debug', 'verbose'

# Returns the switches given, or throws usage at any other or a repeat.
function _xsjs_start_get_switches {
    $given_ = @()
    foreach ($argument_ in $arguments_) {
        $name_ = $switch_names_ | Where-Object { "$argument_" -ceq "--$_" }
        if (-not $name_ -or $given_ -ccontains "--$name_") {
            throw ($i18n_.start_usage -f $script_name_)
        }
        $given_ += "--$name_"
    }
    $given_
}

# Starts the container unless it runs, and returns it as inspected.
function _xsjs_start_step_start_container ([object]$found_) {
    xsjs_util_write_log_section ($i18n_.start_container -f $container_)
    if ($found_.State.Running) {
        xsjs_util_write_log ($i18n_.container_running -f $container_)
        return $found_
    }
    xsjs_util_invoke_native { wslc start $container_ }
    if ($LASTEXITCODE -ne 0) {
        throw ($i18n_.exit_code -f "wslc start $container_", $LASTEXITCODE)
    }
    xsjs_util_get_container
}

# Throws unless the container publishes the port on Windows' 127.0.0.1.
function _xsjs_start_step_check_publish ([object]$found_) {
    xsjs_util_write_log_section ($i18n_.check_publish -f $port_)
    $ports_ = $found_.Ports.PSObject.Properties |
        Where-Object Name -CEQ "$port_/tcp"
    $published_ = @(
        $ports_.Value | Where-Object {
            $_.HostIp -ceq $windows_address_ -and $_.HostPort -ceq "$port_"
        }
    )
    if (-not $published_) {
        $text_ = $i18n_.container_unpublished -f (
            $container_, $port_, $windows_address_)
        throw $text_
    }
    $text_ = $i18n_.container_published -f (
        $container_, $port_, $windows_address_)
    xsjs_util_write_log $text_
}

# Has the sync script, as the container's user, copy this checkout there.
function _xsjs_start_step_copy_checkout {
    xsjs_util_write_log_section ($i18n_.copy_checkout -f $container_root_)
    $sync_ = @(xsjs_util_get_sync_arguments)
    xsjs_util_invoke_native { wslc @sync_ }
    if ($LASTEXITCODE -ne 0) {
        $text_ = 'wslc ' + ($sync_ -join ' ')
        throw ($i18n_.exit_code -f $text_, $LASTEXITCODE)
    }
}

# Starts the serve program in the container's checkout and returns its PID.
function _xsjs_start_step_start_server ([string[]]$switches_) {
    xsjs_util_write_log_section ($i18n_.start_server -f $port_)
    # `sh` makes the log's folder and leaves the program running on its own.
    $script_ = (
        'set -e; log=$HOME/$1; shift; mkdir -p $(dirname $log); ' +
        'nohup $@ > $log 2>&1 < /dev/null & echo $!')
    # `-e` with a name alone passes on Windows' value, when there is one.
    $start_ = @(
        'exec', '-u', $container_user_, '-w', $container_root_
        '-e', $provider_key_name_, $container_, 'sh', '-c', $script_
        'sh', $serve_log_
    ) + @(xsjs_util_get_serve_command) + $switches_
    xsjs_util_write_log ('`wslc {0}`' -f ($start_ -join ' '))
    $id_ = [int](xsjs_util_get_wslc 0 $start_ | Select-Object -Last 1)
    xsjs_util_write_log ($i18n_.server_started -f $id_, $serve_log_)
    $id_
}

# Waits while the program lives for its address in its log, then fetches it.
function _xsjs_start_step_wait_server ([int]$id_) {
    xsjs_util_write_log_section $i18n_.wait_server
    $url_ = xsjs_util_get_local_url
    # `sh` exits 0 at the address, 1 while the program lives, 2 once it ended.
    $script_ = (
        'grep -Fqx $1 $HOME/$2 && exit 0; ' +
        'kill -0 $3 2> /dev/null && exit 1; exit 2')
    $check_ = @(
        'exec', '-u', $container_user_, $container_, 'sh', '-c', $script_
        'sh', $url_, $serve_log_, "$id_"
    )
    do {
        Start-Sleep -Milliseconds $poll_milliseconds_
        $null = xsjs_util_get_wslc 0, 1, 2 $check_
    } while ($LASTEXITCODE -eq 1)
    if ($LASTEXITCODE -eq 2) {
        $cat_ = @(
            'exec', '-u', $container_user_, $container_, 'sh', '-c'
            'cat $HOME/$1', 'sh', $serve_log_
        )
        $log_ = @(xsjs_util_get_wslc 0 $cat_)
        $ended_ = $i18n_.server_ended -f $id_, $serve_log_
        throw ((@($ended_) + $log_) -join "`n")
    }
    # wslc's listener on Windows' 127.0.0.1 reaches the program.
    $token_ = Invoke-WebRequest -Uri "${url_}token" -UseBasicParsing
    xsjs_util_write_log ($i18n_.server_listening -f $url_, $token_.StatusCode)
}

# Checks the container, copies this checkout into it and serves from there.
function _xsjs_start_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_start_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    $switches_ = @(_xsjs_start_get_switches)

    $found_ = xsjs_util_get_container
    xsjs_util_step_check_container $found_
    $found_ = _xsjs_start_step_start_container $found_
    _xsjs_start_step_check_publish $found_
    xsjs_util_step_stop_server $found_
    _xsjs_start_step_copy_checkout
    $id_ = _xsjs_start_step_start_server $switches_
    _xsjs_start_step_wait_server $id_

    xsjs_util_write_log_section $i18n_.done
    $url_ = xsjs_util_get_local_url
    xsjs_util_write_log ($i18n_.open_urls -f $url_, $container_)
    Write-Host ($i18n_.started_ok -f $url_) -ForegroundColor Green
}

_xsjs_start_main
