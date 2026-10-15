# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
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
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_problem $i18n_.wsl_update_failed
    }
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
        xsjs_util_invoke_native { wsl -u root -e apt-get install -y python3 }
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
        xsjs_util_invoke_native { wsl -u root -e apt-get install -y openssl }
        xsjs_util_invoke_native { wsl -e openssl version }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.openssl_install_failed }
    }
}

# Installs ttyd in Linux with apt if it is missing.
function _xsjs_install_step_check_ttyd {
    xsjs_util_write_log_section $i18n_.check_ttyd
    xsjs_util_invoke_native { wsl -e ttyd --version }
    if ($LASTEXITCODE -ne 0) {
        xsjs_util_write_log $i18n_.ttyd_missing
        xsjs_util_invoke_native { wsl -u root -e apt-get update }
        xsjs_util_invoke_native { wsl -u root -e apt-get install -y ttyd }
        xsjs_util_invoke_native { wsl -e ttyd --version }
        if ($LASTEXITCODE -ne 0) { throw $i18n_.ttyd_install_failed }
    }
}

# Reports a ttyd for Windows from an earlier install, which stays installed.
function _xsjs_install_step_check_windows_ttyd {
    xsjs_util_write_log_section $i18n_.check_windows_ttyd
    xsjs_util_update_path
    $ttyd_ = Get-Command ttyd.exe -ErrorAction SilentlyContinue
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
    _xsjs_install_step_check_ttyd
    _xsjs_install_step_check_windows_ttyd

    xsjs_util_write_log_section $i18n_.done
    xsjs_util_write_log $i18n_.installed
    Write-Host $i18n_.installed -ForegroundColor Green
}

_xsjs_install_main
