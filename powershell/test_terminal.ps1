# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Checks the web terminal end to end as a browser would: asks for the
# page, connects to ttyd's WebSocket, waits for bootstrap.py's CHALLENGE,
# answers it and checks bootstrap.py echoes the answer back. Run it after
# xsjs_start.ps1, with the same username:password if it has one. Any
# PowerShell can run it; test_powershell.ps1 runs it after each start.
#
#     .\powershell\test_terminal.ps1
#     .\powershell\test_terminal.ps1 username:password
[Diagnostics.CodeAnalysis.SuppressMessageAttribute(
    'PSAvoidUsingWriteHost', '',
    Justification = 'Coloured status for the person running it.')]
param()

. (Join-Path $PSScriptRoot 'xsjs_util.ps1')
. (Join-Path $PSScriptRoot 'test_util.ps1')

# Read from $args, not param(), so a password that starts with "-" can't
# be mistaken for a parameter name.
$arguments_ = $args
$timeout_seconds_ = 60
# The first byte of each ttyd message says what it is.
$input_type_ = '0'
$output_type_ = [byte][char]'0'

function _test_terminal_send_frame ([byte[]]$payload_, [int]$opcode_ = 2) {
    # A WebSocket frame, binary unless told otherwise, masked as a client's
    # must be.
    $frame_ = [Collections.Generic.List[byte]]::new()
    $frame_.Add(0x80 -bor $opcode_)
    if ($payload_.Length -lt 126) {
        $frame_.Add(0x80 -bor $payload_.Length)
    } else {
        $frame_.Add(0x80 -bor 126)
        $frame_.Add(($payload_.Length -shr 8) -band 0xFF)
        $frame_.Add($payload_.Length -band 0xFF)
    }
    $mask_ = [byte[]]::new(4)
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($mask_)
    $frame_.AddRange($mask_)
    for ($index_ = 0; $index_ -lt $payload_.Length; $index_++) {
        $frame_.Add($payload_[$index_] -bxor $mask_[$index_ % 4])
    }
    $stream_.Write($frame_.ToArray(), 0, $frame_.Count)
}

function _test_terminal_send_input ([string]$text_) {
    $bytes_ = [Text.Encoding]::UTF8.GetBytes($input_type_ + $text_)
    _test_terminal_send_frame $bytes_
}

function _test_terminal_read_bytes ([int]$count_) {
    $buffer_ = [byte[]]::new($count_)
    $done_ = 0
    while ($done_ -lt $count_) {
        $read_ = $stream_.Read($buffer_, $done_, $count_ - $done_)
        if ($read_ -le 0) { return $null }
        $done_ += $read_
    }
    , $buffer_
}

function _test_terminal_read_message {
    # Returns the next WebSocket message, answering pings on the way, or
    # $null once ttyd closes the connection.
    $message_ = [Collections.Generic.List[byte]]::new()
    while ($true) {
        $head_ = _test_terminal_read_bytes 2
        if ($null -eq $head_) { return $null }
        $final_ = ($head_[0] -band 0x80) -ne 0
        $opcode_ = $head_[0] -band 0x0F
        $length_ = $head_[1] -band 0x7F
        if ($length_ -ge 126) {
            $size_ = if ($length_ -eq 126) { 2 } else { 8 }
            $length_ = 0
            foreach ($byte_ in _test_terminal_read_bytes $size_) {
                $length_ = $length_ * 256 + $byte_
            }
        }
        $payload_ = _test_terminal_read_bytes $length_
        if ($null -eq $payload_) { return $null }
        switch ($opcode_) {
            8 { return $null }
            9 { _test_terminal_send_frame $payload_ 10 }
            10 {}
            default {
                $message_.AddRange($payload_)
                if ($final_) { return , $message_.ToArray() }
            }
        }
    }
}

function _test_terminal_get_plain_text ([string]$text_) {
    # Drops the terminal's escape sequences: titles, colours, cursor moves.
    $title_ = '\x1b\][^\x07\x1b]*(\x07|\x1b\\)'
    $control_ = '\x1b\[[0-?]*[ -/]*[@-~]'
    $text_ -replace $title_, '' -replace $control_, '' -replace '\x1b.', ''
}

function _test_terminal_step_check_page {
    # Asks for the page, over TLS and with the password when there is one.
    $url_ = xsjs_util_get_local_url
    xsjs_util_write_log_section ($i18n_.check_page -f $url_)
    $stream_ = test_util_connect_server
    try {
        $request_ = @(test_util_get_request 'GET /') + 'Connection: close'
        test_util_send_request $stream_ $request_
        $status_ = test_util_read_status $stream_
    } finally {
        $stream_.Dispose()
    }
    if ($status_ -notmatch '^HTTP/1\.[01] 200 ') {
        throw ($i18n_.unexpected_answer -f $url_, $status_, '200 OK')
    }
    xsjs_util_write_log ($i18n_.page_answered -f $url_, $status_)
}

function _test_terminal_step_connect {
    $url_ = (xsjs_util_get_local_url) -replace '^http', 'ws'
    xsjs_util_write_log_section ($i18n_.test_connect -f "${url_}ws")
    $key_ = [byte[]]::new(16)
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($key_)
    # Without an Origin that matches Host, --check-origin refuses it.
    $request_ = @(
        test_util_get_request 'GET /ws'
        "Origin: $((xsjs_util_get_local_url).TrimEnd('/'))"
        'Upgrade: websocket'
        'Connection: Upgrade'
        'Sec-WebSocket-Key: ' + [Convert]::ToBase64String($key_)
        'Sec-WebSocket-Version: 13'
        'Sec-WebSocket-Protocol: tty'
    )
    test_util_send_request $stream_ $request_
    $status_ = test_util_read_status $stream_
    if ($status_ -notmatch '^HTTP/1\.1 101 ') {
        throw ($i18n_.unexpected_answer -f "${url_}ws", $status_, '101')
    }
    xsjs_util_write_log ($i18n_.page_answered -f "${url_}ws", $status_)
    # ttyd starts bootstrap.py once it has the terminal's size and, if it
    # has a password, the password.
    $token_ = ''
    if ($credential_) {
        $bytes_ = [Text.Encoding]::UTF8.GetBytes($credential_)
        $token_ = [Convert]::ToBase64String($bytes_)
    }
    $hello_ = @{ AuthToken = $token_; columns = 80; rows = 24 }
    $json_ = ConvertTo-Json $hello_ -Compress
    _test_terminal_send_frame ([Text.Encoding]::UTF8.GetBytes($json_))
}

function _test_terminal_step_answer_challenge {
    xsjs_util_write_log_section ($i18n_.test_answer -f $bootstrap_script_)
    $answer_ = 'xstation-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
    $response_ = 'RESPONSE:\s*' + [regex]::Escape($answer_)
    $cursor_query_ = "$([char]27)[6n"
    $output_ = [Text.StringBuilder]::new()
    $plain_ = ''
    $asked_ = $false
    $reason_ = $i18n_.test_timed_out
    $deadline_ = [DateTime]::UtcNow.AddSeconds($timeout_seconds_)
    while ([DateTime]::UtcNow -lt $deadline_) {
        $left_ = ($deadline_ - [DateTime]::UtcNow).TotalMilliseconds
        $stream_.ReadTimeout = [Math]::Max(1, [int]$left_)
        try {
            $message_ = _test_terminal_read_message
        } catch {
            $reason_ = $_.Exception.Message
            break
        }
        if ($null -eq $message_) {
            $reason_ = $i18n_.test_closed
            break
        }
        if ($message_.Length -eq 0 -or $message_[0] -ne $output_type_) {
            continue
        }
        $text_ = [Text.Encoding]::UTF8.GetString(
            $message_, 1, $message_.Length - 1)
        # Windows' pseudoconsole may ask where the cursor is before it
        # shows anything.
        if ($text_.Contains($cursor_query_)) {
            _test_terminal_send_input "$([char]27)[1;1R"
        }
        $null = $output_.Append($text_)
        $plain_ = _test_terminal_get_plain_text $output_.ToString()
        if (-not $asked_ -and $plain_ -match 'CHALLENGE:') {
            _test_terminal_send_input "$answer_`r"
            $asked_ = $true
            xsjs_util_write_log ($i18n_.test_answered -f $answer_)
        } elseif ($asked_ -and $plain_ -match $response_) {
            xsjs_util_write_log (
                $i18n_.test_response -f $bootstrap_script_, $answer_)
            $plain_ | xsjs_util_write_log_output
            _test_terminal_send_frame ([byte[]]@()) 8
            return
        }
    }
    $message_ = $i18n_.test_no_response -f (
        $answer_, $bootstrap_script_, $timeout_seconds_, $reason_)
    throw "$message_`r`n$plain_"
}

function _test_terminal_main {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute(
        'PSUseDeclaredVarsMoreThanAssignments', '',
        Justification = 'The functions _test_terminal_main calls read these.')]
    param()
    trap { xsjs_util_write_failure $_; exit 1 }

    $script_name_ = Split-Path -Leaf $PSCommandPath
    $log_path_ = xsjs_util_open_log $PSCommandPath
    $credential_ = xsjs_util_get_credential $arguments_

    _test_terminal_step_check_page
    $stream_ = test_util_connect_server
    try {
        _test_terminal_step_connect
        _test_terminal_step_answer_challenge
    } finally {
        $stream_.Dispose()
    }

    xsjs_util_write_log_section $i18n_.done
    $message_ = $i18n_.test_terminal_ok -f (
        (xsjs_util_get_local_url), $bootstrap_script_)
    xsjs_util_write_log $message_
    Write-Host $message_ -ForegroundColor Green
}

_test_terminal_main
