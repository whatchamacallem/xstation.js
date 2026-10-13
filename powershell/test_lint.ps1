# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Checks the project's PowerShell files have LF line endings and no <# #>
# comments below the top of the file, formats them, then checks them with
# PSScriptAnalyzer. Any PowerShell can run it; test_powershell.ps1 runs it
# first.
#
# Run it in a PowerShell of its own, as test_powershell.ps1 does:
# PSScriptAnalyzer loads the modules whose commands the scripts call, such
# as Microsoft.WinGet.Client, and Windows keeps their files locked until
# that PowerShell exits, so updating them fails until then.
#
#     powershell.exe -ExecutionPolicy Bypass -File .\powershell\test_lint.ps1
param()

$ErrorActionPreference = 'Stop'
$progressPreference = 'silentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = (
    [Net.ServicePointManager]::SecurityProtocol -bor
    [Net.SecurityProtocolType]::Tls12
)
$preset_ = 'CodeFormattingOTBS'
$globs_ = '*.ps1', '*.psm1', '*.psd1'
# The project's top directory, which holds the files to check.
$root_path_ = Split-Path -Parent $PSScriptRoot

function _test_lint_find_problems ([string]$path_) {
    # What PSScriptAnalyzer doesn't check. Fix these by hand: formatting a
    # file with CRLF would hide it.
    $text_ = [IO.File]::ReadAllText($path_)
    if ($text_.Contains("`r")) {
        return "${path_}: CRLF line endings. Use LF."
    }
    $tokens_ = $null
    $errors_ = $null
    $null = [Management.Automation.Language.Parser]::ParseInput(
        $text_, [ref]$tokens_, [ref]$errors_)
    foreach ($token_ in $tokens_) {
        $block_ = $token_.Kind -eq 'Comment' -and $token_.Text.StartsWith('<#')
        if ($block_ -and $token_.Extent.StartOffset -gt 0) {
            '{0}:{1}: <# #> comment below the top of the file. Use #.' -f (
                $path_, $token_.Extent.StartLineNumber)
        }
    }
}

function _test_lint_format_file ([string]$path_) {
    # Keep the file's BOM, or lack of one. The formatter inserts
    # Environment.NewLine, which is CRLF on Windows, so put back LF.
    $bytes_ = [IO.File]::ReadAllBytes($path_)
    $has_bom_ = $bytes_.Length -ge 3 -and (
        $bytes_[0] -eq 0xEF -and $bytes_[1] -eq 0xBB -and $bytes_[2] -eq 0xBF
    )
    $encoding_ = [Text.UTF8Encoding]::new($has_bom_)
    $text_ = [IO.File]::ReadAllText($path_, $encoding_)
    $formatted_ = Invoke-Formatter -ScriptDefinition $text_ -Settings $preset_
    $formatted_ = $formatted_.Replace("`r`n", "`n")
    if ($formatted_ -cne $text_) {
        [IO.File]::WriteAllText($path_, $formatted_, $encoding_)
        "Reformatted $path_"
    }
}

function _test_lint_get_lint_settings {
    # The OTBS preset only includes its own formatting rules. Drop that list so
    # the default rules run as well, with the formatting rules set up as OTBS.
    # Lines over 79 columns are reported but have to be wrapped by hand.
    $module_base_ = (Get-Module PSScriptAnalyzer).ModuleBase
    $preset_path_ = Join-Path $module_base_ "Settings\$preset_.psd1"
    $settings_ = Import-PowerShellDataFile $preset_path_
    $settings_.Remove('IncludeRules')
    $settings_.Rules.PSAvoidLongLines = @{
        Enable            = $true
        MaximumLineLength = 79
    }
    $settings_
}

function _test_lint_main {
    if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
        $module_ = @{
            Name       = 'PSScriptAnalyzer'
            Repository = 'PSGallery'
            Scope      = 'CurrentUser'
        }
        $null = Install-PackageProvider -Name NuGet -Force -Scope CurrentUser
        Install-Module @module_ -Force
    }
    Import-Module PSScriptAnalyzer

    $paths_ = @(
        Get-ChildItem -Path $root_path_ -Recurse -File -Include $globs_ |
            ForEach-Object FullName
    )
    $problems_ = @($paths_ | ForEach-Object { _test_lint_find_problems $_ })
    if ($problems_) {
        $problems_
        exit 1
    }
    $paths_ | ForEach-Object { _test_lint_format_file $_ }

    $analyzer_ = @{
        Path     = $root_path_
        Recurse  = $true
        Settings = _test_lint_get_lint_settings
    }
    $results_ = Invoke-ScriptAnalyzer @analyzer_
    if ($results_) {
        $results_ | Format-Table -AutoSize -Wrap | Out-String -Width 200
        exit 1
    }
    'PSScriptAnalyzer found nothing to fix.'
}

_test_lint_main
