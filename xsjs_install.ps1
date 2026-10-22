﻿# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The install command has to be run as admin:
#
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\xsjs_install.ps1
#
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'powershell\xsjs_util.ps1')

# The checkout, in which the ttyd source is unpacked, patched and built.
$checkout_path_ = $PSScriptRoot
# The pinned ttyd source release, which `third_party_fetch.py` fetches.
$ttyd_archive_path_ = 'third_party/ttyd-1.7.7.tar.gz'
# The patches to the ttyd source, applied in name order.
$patches_path_ = Join-Path $PSScriptRoot 'third_party\ttyd'
# The tools the ttyd build runs in Linux, each with its apt package.
$build_tools_ = [ordered]@{
    cmake = 'cmake'
    cc    = 'build-essential'
    make  = 'build-essential'
    patch = 'patch'
}
# The headers the ttyd build includes, each with its apt package.
$build_headers_ = [ordered]@{
    'uv.h'            = 'libuv1-dev'
    'json-c/json.h'   = 'libjson-c-dev'
    'zlib.h'          = 'zlib1g-dev'
    'libwebsockets.h' = 'libwebsockets-dev'
    'openssl/ssl.h'   = 'libssl-dev'
}

# `figlet -f bigmono9 xsjs`
$banner_ = @'
                  █


 █▒ ▒█  ▒███▒   ███   ▒███▒
 ░█ █░  █▒ ░█     █   █▒ ░█
  ▓█▓   █▒░       █   █▒░
  ░█░   ░███▒     █   ░███▒
  ███      ▒█     █      ▒█
 ░█ █░  █░ ▒█     █   █░ ▒█
 █▒ ▒█  ▒███▒     █   ▒███▒
                  █
                 ▒█
                ██▒

Cross-Station JS, a.k.a. xstation.js. © 2026 Adrian Johnston. Licensed under
the terms of the MIT license found in the LICENSE.md file.
'@

# Installs WSL and asks for a restart if it is missing, or else updates it.
function _xsjs_install_step_check_wsl {
    xsjs_util_write_log_section $i18n_.check_wsl
    xsjs_util_invoke_native { wsl --version }
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_notice $i18n_.wsl_missing
        xsjs_util_invoke_native { wsl --install --no-distribution }
        if ($LASTEXITCODE -ne 0) {
            throw ($i18n_.wsl_install_failed -f $LASTEXITCODE)
        }
        throw ($i18n_.restart_windows -f $script_name_)
    }
    xsjs_util_invoke_native { wsl --update }
    if ($LASTEXITCODE -ne 0) { throw $i18n_.wsl_update_failed }
}

# Installs Ubuntu if WSL runs no Linux, and throws if it still doesn't.
function _xsjs_install_step_check_linux {
    xsjs_util_write_log_section $i18n_.check_linux
    xsjs_util_invoke_native { wsl -e true }
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_notice $i18n_.linux_missing
        wsl --install -d Ubuntu
        xsjs_util_invoke_native { wsl -e true }
        if ($LASTEXITCODE -ne 0) {
            throw ($i18n_.ubuntu_not_working -f $script_name_)
        }
    }
}

# Installs Python 3 in Linux with apt if it is missing.
function _xsjs_install_step_check_python {
    xsjs_util_write_log_section $i18n_.check_python
    xsjs_util_invoke_native { wsl -e python3 --version }
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_log $i18n_.python_missing
        xsjs_util_invoke_native { wsl -u root -e apt-get update }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.python_install_failed }
        xsjs_util_invoke_native { wsl -u root -e apt-get install -y python3 }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.python_install_failed }
        xsjs_util_invoke_native { wsl -e python3 --version }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.python_install_failed }
    }
}

# Installs OpenSSL in Linux with apt if it is missing.
function _xsjs_install_step_check_openssl {
    xsjs_util_write_log_section $i18n_.check_openssl
    xsjs_util_invoke_native { wsl -e openssl version }
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_log $i18n_.openssl_missing
        xsjs_util_invoke_native { wsl -u root -e apt-get update }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.openssl_install_failed }
        xsjs_util_invoke_native { wsl -u root -e apt-get install -y openssl }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.openssl_install_failed }
        xsjs_util_invoke_native { wsl -e openssl version }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.openssl_install_failed }
    }
}

# Runs the command in Linux from the checkout, or throws the message.
function _xsjs_install_run_linux ([string[]]$arguments_, [string]$failure_) {
    xsjs_util_invoke_native { wsl --cd $checkout_path_ -e @arguments_ }
    if ($LASTEXITCODE -ne 0) { throw $failure_ }
}

# Throws, naming the apt package to request, unless ttyd can be built.
function _xsjs_install_step_check_build {
    xsjs_util_write_log_section $i18n_.check_build
    foreach ($tool_ in $build_tools_.Keys) {
        xsjs_util_invoke_native { wsl -e which $tool_ }
        if ($LASTEXITCODE -ne 0) {
            throw ($i18n_.build_tool_missing -f $tool_, $build_tools_[$tool_])
        }
    }
    foreach ($header_ in $build_headers_.Keys) {
        # The compiler preprocesses an empty file that includes the header.
        $include_ = @(
            'cc', '-E', '-x', 'c', '-include', $header_
            '-o', '/dev/null', '/dev/null'
        )
        xsjs_util_invoke_native { wsl -e @include_ }
        if ($LASTEXITCODE -ne 0) {
            $missing_ = $i18n_.build_header_missing -f (
                $header_, $build_headers_[$header_])
            throw $missing_
        }
    }
}

# Builds ttyd in the checkout from the pinned source release and its patches.
function _xsjs_install_step_build_ttyd {
    xsjs_util_write_log_section $i18n_.build_ttyd
    $source_path_ = "$ttyd_build_path_/source"
    $fetch_ = 'python3', 'python/third_party_fetch.py'
    _xsjs_install_run_linux $fetch_ $i18n_.ttyd_fetch_failed
    # Every build starts from the archive, as a patch applies only once.
    $unpack_failed_ = $i18n_.ttyd_unpack_failed
    _xsjs_install_run_linux ('rm', '-rf', $ttyd_build_path_) $unpack_failed_
    _xsjs_install_run_linux ('mkdir', '-p', $source_path_) $unpack_failed_
    $unpack_ = @(
        'tar', '-xzf', $ttyd_archive_path_, '-C', $source_path_
        '--strip-components=1'
    )
    _xsjs_install_run_linux $unpack_ $unpack_failed_
    $wslpath_ = '-e', 'wslpath', '-u', $checkout_path_
    $checkout_linux_ = xsjs_util_get_wsl 0 $wslpath_
    $patches_ = Get-ChildItem $patches_path_ -Filter '*.patch' |
        Sort-Object Name
    foreach ($patch_ in $patches_) {
        $apply_ = @(
            'patch', '-p1', '-d', $source_path_
            '-i', "$checkout_linux_/third_party/ttyd/$($patch_.Name)"
        )
        $apply_failed_ = $i18n_.ttyd_patch_failed -f $patch_.Name
        _xsjs_install_run_linux $apply_ $apply_failed_
    }
    $configure_ = 'cmake', '-S', $source_path_, '-B', $ttyd_build_path_
    _xsjs_install_run_linux $configure_ $i18n_.ttyd_configure_failed
    $build_ = 'cmake', '--build', $ttyd_build_path_
    _xsjs_install_run_linux $build_ $i18n_.ttyd_build_failed
    $version_ = $ttyd_binary_path_, '--version'
    _xsjs_install_run_linux $version_ $i18n_.ttyd_build_failed
}

# Reports a ttyd for Windows from an earlier install, which stays installed.
function _xsjs_install_step_check_windows_ttyd {
    xsjs_util_write_log_section $i18n_.check_windows_ttyd
    xsjs_util_update_path
    $ttyd_ = Get-Command -CommandType Application |
        Where-Object Name -EQ 'ttyd.exe' | Select-Object -First 1
    if ($ttyd_) {
        xsjs_util_write_notice ($i18n_.windows_ttyd_left -f $ttyd_.Source)
    } else {
        xsjs_util_write_log $i18n_.windows_ttyd_none
    }
}

# Shows the banner, then checks and installs each requirement in turn.
function _xsjs_install_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _xsjs_install_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    Write-Host "$banner_`n"
    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath

    _xsjs_install_step_check_wsl
    _xsjs_install_step_check_linux
    _xsjs_install_step_check_python
    _xsjs_install_step_check_openssl
    _xsjs_install_step_check_build
    _xsjs_install_step_build_ttyd
    _xsjs_install_step_check_windows_ttyd

    xsjs_util_write_log_section $i18n_.done
    xsjs_util_write_log $i18n_.installed
    Write-Host $i18n_.installed -ForegroundColor Green
}

_xsjs_install_main
