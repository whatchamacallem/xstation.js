# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Talking HTTP to ttyd, for the tests. Dot-source it after
# xsjs_util.ps1.

function test_util_connect_server {
    # Connects to ttyd on this PC. With a password it serves HTTPS, so speak
    # TLS and accept only the certificate in $certificate_path_.
    $client_ = [Net.Sockets.TcpClient]::new('127.0.0.1', $port_)
    $client_.ReceiveTimeout = 30000
    $client_.SendTimeout = 30000
    $stream_ = $client_.GetStream()
    if (-not $credential_) { return $stream_ }
    $x509_ = [Security.Cryptography.X509Certificates.X509Certificate2]
    $certificate_ = $x509_::new($certificate_path_)
    $expected_ = xsjs_util_get_fingerprint $certificate_.RawData
    $check_ = {
        $sha256_ = [Security.Cryptography.SHA256]::Create()
        $hash_ = $sha256_.ComputeHash($args[1].GetRawCertData())
        [BitConverter]::ToString($hash_).Replace('-', ':') -eq $expected_
    }.GetNewClosure()
    $tls_ = [Net.Security.SslStream]::new($stream_, $false, $check_)
    $tls_.AuthenticateAsClient('localhost')
    $tls_
}

function test_util_get_request ([string]$request_line_) {
    # The start of a request to ttyd, with the password if it has one.
    "$request_line_ HTTP/1.1"
    "Host: localhost:$port_"
    if ($credential_) {
        $bytes_ = [Text.Encoding]::UTF8.GetBytes($credential_)
        'Authorization: Basic ' + [Convert]::ToBase64String($bytes_)
    }
}

function test_util_read_status ($stream_) {
    # Reads an HTTP response's status line and headers a byte at a time, so
    # whatever follows them stays in the stream, and returns the status.
    $head_ = [Text.StringBuilder]::new()
    while (-not $head_.ToString().EndsWith("`r`n`r`n")) {
        $byte_ = $stream_.ReadByte()
        if ($byte_ -lt 0) { break }
        $null = $head_.Append([char]$byte_)
    }
    $status_ = ($head_.ToString() -split "`r`n")[0]
    if (-not $status_) { $status_ = $i18n_.no_answer }
    $status_
}

function test_util_send_request ($stream_, [string[]]$lines_) {
    $bytes_ = [Text.Encoding]::ASCII.GetBytes(
        ($lines_ + @('', '')) -join "`r`n")
    $stream_.Write($bytes_, 0, $bytes_.Length)
}
