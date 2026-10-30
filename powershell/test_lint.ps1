# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Offline since 2026-10-30, kept, run by nothing, and to be brought back later.
#
# Checks that the PowerShell files python/reformat_whitelist.txt lists have
# LF line endings, formats them, then checks them with PSScriptAnalyzer,
# stopping at the first file with a fault. It matches the whitelist's lines
# as python/reformat.py does. Any PowerShell can run it; test_powershell.ps1
# runs it first. python/test_posix.py checks their comments and characters in
# WSL, where python/reformat.py formats the other whitelisted files.
#
# Run it in a PowerShell of its own, as test_powershell.ps1 does:
# PSScriptAnalyzer loads the modules whose commands the scripts call, and
# Windows keeps their files locked until that PowerShell exits, so updating
# them fails until then.
#
#     powershell.exe -ExecutionPolicy Bypass -File .\powershell\test_lint.ps1
param()

. (Join-Path $PSScriptRoot 'xsjs_util.ps1')

# The project's top directory, which holds the files to check.
$root_path_ = Split-Path -Parent $PSScriptRoot
$test_settings_json_ = xsjs_util_read_json (
    Join-Path $root_path_ 'test_settings.json')
$lint_module_ = (
    xsjs_util_get_setting $test_settings_json_ 'powershell.lint_module')
$preset_ = xsjs_util_get_setting $test_settings_json_ 'powershell.lint_preset'
# The extensions of the `windows` rows of `reformat_table.json`.
$extensions_ = (
    xsjs_util_get_setting $test_settings_json_ 'powershell.lint_extensions')
$line_length_ = (
    xsjs_util_get_setting $test_settings_json_ 'powershell.lint_line_length')
# The whitelist that `reformat.py` reads too.
$whitelist_path_ = Join-Path $root_path_ 'python\reformat_whitelist.txt'
# A whitelist line: a path from the top, with `*` or `?` in its last part only.
$whitelist_line_ = '^(?:[^*?\[\]`/]+/)*[^\[\]`/]+\z'

# Returns the file's CRLF fault, which PSScriptAnalyzer doesn't check.
function _test_lint_find_problems ([string]$path_) {
    # Fix it by hand: formatting a file with CRLF would hide it.
    $text_ = [IO.File]::ReadAllText($path_)
    if ($text_.Contains("`r")) {
        return "${path_}: CRLF line endings. Use LF."
    }
}

# Formats the file in place with the OTBS preset, keeping its encoding and LF.
function _test_lint_format_file ([string]$path_) {
    # Keep the file's BOM, or lack of one.
    $bytes_ = [IO.File]::ReadAllBytes($path_)
    $has_bom_ = $bytes_.Length -ge 3 -and (
        $bytes_[0] -eq 0xEF -and $bytes_[1] -eq 0xBB -and $bytes_[2] -eq 0xBF
    )
    $encoding_ = [Text.UTF8Encoding]::new($has_bom_)
    $text_ = [IO.File]::ReadAllText($path_, $encoding_)
    $formatted_ = Invoke-Formatter -ScriptDefinition $text_ -Settings $preset_
    # The formatter inserts Environment.NewLine, which is CRLF on Windows.
    $formatted_ = $formatted_.Replace("`r`n", "`n")
    if ($formatted_ -cne $text_) {
        [IO.File]::WriteAllText($path_, $formatted_, $encoding_)
        "Reformatted $path_"
    }
}

# Returns the OTBS preset's settings with the default rules and line length.
function _test_lint_get_lint_settings {
    $module_base_ = (Get-Module $lint_module_).ModuleBase
    $preset_path_ = Join-Path $module_base_ "Settings\$preset_.psd1"
    $settings_ = Import-PowerShellDataFile $preset_path_
    # Dropping the preset's list of its own rules runs the default rules too.
    $settings_.Remove('IncludeRules')
    # Longer lines are reported but have to be wrapped by hand.
    $settings_.Rules.PSAvoidLongLines = @{
        Enable            = $true
        MaximumLineLength = $line_length_
    }
    $settings_
}

# Returns the whitelisted PowerShell files, matched as `reformat.py` does.
function _test_lint_get_paths {
    # Each file once, sorted by its path from the top in ordinal order.
    $matched_ = [Collections.Generic.SortedSet[string]]::new(
        [StringComparer]::Ordinal
    )
    foreach ($pattern_ in [IO.File]::ReadAllLines($whitelist_path_)) {
        if ($pattern_ -cnotmatch $whitelist_line_) {
            $message_ = (
                "whitelist line '{0}' is not a path with * or ? in its" +
                ' last part only'
            ) -f $pattern_
            throw $message_
        }
        $slash_ = $pattern_.LastIndexOf('/')
        $directory_ = $pattern_.Substring(0, $slash_ + 1)
        $leaf_ = $pattern_.Substring($slash_ + 1)
        $directory_path_ = [IO.Path]::Combine($root_path_, $directory_)
        $names_ = [string[]]@()
        if (Test-Path -LiteralPath $directory_path_ -PathType Container) {
            $names_ = [string[]]@(
                Get-ChildItem -LiteralPath $directory_path_ -Force |
                    ForEach-Object Name
            )
        }
        [Array]::Sort($names_, [StringComparer]::Ordinal)
        $found_ = $false
        foreach ($name_ in $names_) {
            if ($name_ -cnotlike $leaf_) {
                continue
            }
            if ($name_.StartsWith('.') -and -not $leaf_.StartsWith('.')) {
                continue
            }
            $relative_ = $directory_ + $name_
            $path_ = [IO.Path]::Combine($root_path_, $relative_)
            if (-not (Test-Path -LiteralPath $path_ -PathType Leaf)) {
                $message_ = (
                    "whitelist line '{0}' matches '{1}', which is not a file"
                ) -f $pattern_, $relative_
                throw $message_
            }
            $null = $matched_.Add($relative_)
            $found_ = $true
        }
        if (-not $found_) {
            $message_ = (
                "whitelist line '{0}' matches nothing under {1}"
            ) -f $pattern_, $root_path_
            throw $message_
        }
    }
    foreach ($relative_ in $matched_) {
        if ([IO.Path]::GetExtension($relative_) -cin $extensions_) {
            $path_ = [IO.Path]::Combine($root_path_, $relative_)
            [IO.Path]::GetFullPath($path_)
        }
    }
}

# Installs PSScriptAnalyzer if missing, then checks, formats and lints.
function _test_lint_main {
    if (-not (Get-Module -ListAvailable -Name $lint_module_)) {
        $module_ = @{
            Name       = $lint_module_
            Repository = 'PSGallery'
            Scope      = 'CurrentUser'
        }
        $null = Install-PackageProvider -Name NuGet -Force -Scope CurrentUser
        Install-Module @module_ -Force
    }
    Import-Module $lint_module_

    $paths_ = @(_test_lint_get_paths)
    foreach ($path_ in $paths_) {
        $problem_ = _test_lint_find_problems $path_
        if ($problem_) {
            $problem_
            exit 1
        }
    }
    $paths_ | ForEach-Object { _test_lint_format_file $_ }

    $settings_ = _test_lint_get_lint_settings
    foreach ($path_ in $paths_) {
        $results_ = Invoke-ScriptAnalyzer -Path $path_ -Settings $settings_
        if ($results_) {
            $results_ | Format-Table -AutoSize -Wrap |
                Out-String -Width $output_width_
            exit 1
        }
    }
    '{0} found nothing to fix.' -f $lint_module_
}

_test_lint_main
