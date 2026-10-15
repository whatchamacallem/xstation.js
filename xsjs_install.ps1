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

$ttyd_package_ = @{ Id = 'tsl0922.ttyd'; MatchOption = 'Equals' }

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

# Installs the WinGet module if missing, then repairs WinGet if it needs it.
function _xsjs_install_step_check_winget {
    xsjs_util_write_log_section $i18n_.check_winget_module
    $module_ = @{
        Name       = 'Microsoft.WinGet.Client'
        Repository = 'PSGallery'
        Scope      = 'CurrentUser'
    }
    # Install only if missing: a reinstall fails while the lint has it loaded.
    $installed_ = Get-Module -ListAvailable -Name $module_.Name |
        Sort-Object Version -Descending | Select-Object -First 1
    if ($installed_) {
        xsjs_util_write_log ($i18n_.winget_module_ok -f $installed_.Version)
    } else {
        xsjs_util_write_log $i18n_.winget_module_missing
        $null = Install-PackageProvider -Name NuGet -Force -Scope CurrentUser
        Install-Module @module_ -Force 3>&1 | xsjs_util_write_log_output
    }
    Import-Module $module_.Name

    xsjs_util_write_log_section $i18n_.check_winget
    try {
        Assert-WinGetPackageManager -Latest
        xsjs_util_write_log $i18n_.winget_ok
    } catch {
        $message_ = xsjs_util_get_markdown_text $_.Exception.Message
        xsjs_util_write_log ($i18n_.winget_needs_fixing -f $message_)
        Repair-WinGetPackageManager -Latest -Force 3>&1 |
            xsjs_util_write_log_output
        Assert-WinGetPackageManager -Latest
        xsjs_util_write_log $i18n_.winget_ok_now
    }
}

# Stops the scheduled task and every ttyd process.
function _xsjs_install_stop_ttyd {
    # WinGet can't replace ttyd.exe while any copy of it runs.
    $task_ = @{ TaskName = $task_name_; ErrorAction = 'SilentlyContinue' }
    if ((Get-ScheduledTask @task_).State -eq 'Running') {
        Stop-ScheduledTask -TaskName $task_name_
        xsjs_util_write_log ($i18n_.task_stopped -f $task_name_)
    }
    $processes_ = @(Get-Process -Name ttyd -ErrorAction SilentlyContinue)
    foreach ($process_ in $processes_) {
        Stop-Process -Id $process_.Id -Force
        xsjs_util_write_log ($i18n_.ttyd_stopped -f $process_.Id)
    }
    if ($processes_) { Start-Sleep -Seconds 1 }
}

# Installs ttyd with WinGet, or updates it when WinGet has a newer one.
function _xsjs_install_step_check_ttyd_installed {
    xsjs_util_write_log_section $i18n_.check_ttyd_installed
    $ttyd_ = Get-WinGetPackage @ttyd_package_
    if ($null -eq $ttyd_) {
        xsjs_util_write_log $i18n_.ttyd_missing
        $result_ = Install-WinGetPackage @ttyd_package_ -Source winget
        $result_ | xsjs_util_write_log_output
        if (-not $result_.Succeeded()) {
            throw ($i18n_.ttyd_install_failed -f $result_.ErrorMessage())
        }
    } elseif ($ttyd_.IsUpdateAvailable) {
        xsjs_util_write_log (
            $i18n_.ttyd_out_of_date -f $ttyd_.InstalledVersion)
        _xsjs_install_stop_ttyd
        $result_ = Update-WinGetPackage @ttyd_package_ -Source winget
        $result_ | xsjs_util_write_log_output
        if (-not $result_.Succeeded()) {
            throw ($i18n_.ttyd_update_failed -f $result_.ErrorMessage())
        }
    } else {
        xsjs_util_write_log ($i18n_.ttyd_up_to_date -f $ttyd_.InstalledVersion)
    }
}

# Reinstalls ttyd if it doesn't run, and throws if it still doesn't.
function _xsjs_install_step_check_ttyd_works {
    xsjs_util_write_log_section $i18n_.check_ttyd_works
    if (-not (_xsjs_install_test_ttyd)) {
        xsjs_util_write_log $i18n_.ttyd_broken
        _xsjs_install_stop_ttyd
        Uninstall-WinGetPackage @ttyd_package_ -Force |
            xsjs_util_write_log_output
        $result_ = Install-WinGetPackage @ttyd_package_ -Source winget
        $result_ | xsjs_util_write_log_output
        if (-not $result_.Succeeded()) {
            throw ($i18n_.ttyd_reinstall_failed -f $result_.ErrorMessage())
        }
        if (-not (_xsjs_install_test_ttyd)) { throw $i18n_.ttyd_still_broken }
    }
}

# Returns whether ttyd is on the path and runs, logging its version.
function _xsjs_install_test_ttyd {
    xsjs_util_update_path
    if (-not (Get-Command ttyd -ErrorAction SilentlyContinue)) {
        xsjs_util_write_log $i18n_.ttyd_not_on_path
        return $false
    }
    xsjs_util_invoke_native { ttyd --version }
    return $LASTEXITCODE -eq 0
}

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

    _xsjs_install_step_check_winget
    _xsjs_install_step_check_ttyd_installed
    _xsjs_install_step_check_ttyd_works
    _xsjs_install_step_check_wsl
    _xsjs_install_step_check_linux
    _xsjs_install_step_check_python
    _xsjs_install_step_check_openssl

    xsjs_util_write_log_section $i18n_.done
    xsjs_util_write_log $i18n_.installed
    Write-Host $i18n_.installed -ForegroundColor Green
}

_xsjs_install_main
