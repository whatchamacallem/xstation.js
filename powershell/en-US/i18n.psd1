﻿# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
@{
    add_proxy               = 'Forwarding port {0} to port {1}'
    administrator_ok        = 'Administrator: `{0}`.'
    bootstrap_missing       = '{0} is missing.'
    bootstrap_not_installed = 'Copying into `{0}` failed.'
    build_header_missing    = (
        'The header `{0}` is missing or does not compile in Linux. ' +
        'Ask the maintainer to install the apt package `{1}`.'
    )
    build_tool_missing      = (
        '`{0}` is missing in Linux. ' +
        'Ask the maintainer to install the apt package `{1}`.'
    )
    build_ttyd              = 'Building ttyd from the pinned source release'
    certificate_failed      = 'Making the TLS certificate failed.'
    certificate_fingerprint = 'TLS fingerprint (SHA-256): {0}'
    certificate_kept        = 'Kept the TLS certificate in `{0}`.'
    certificate_made        = 'Made a self-signed TLS certificate in `{0}`.'
    check_administrator     = 'Checking for administrator'
    check_build             = 'Checking the tools that build ttyd'
    check_installed         = 'Checking installation'
    check_linux             = 'Checking Linux in WSL'
    check_openssl           = 'Checking OpenSSL'
    check_port              = 'Checking ports {0} and {1}'
    check_python            = 'Checking Python 3'
    check_windows_ttyd      = 'Checking for ttyd for Windows'
    check_wsl               = 'Checking WSL'
    close_firewall          = 'Closing port {0} (localhost only)'
    credential_hidden       = 'USERNAME:PASSWORD'
    done                    = 'Done'
    exit_code               = '`{0}` exited {1}'
    failed                  = 'Failed'
    failed_message          = 'FAILED: {0}'
    firewall_closed         = 'Removed the firewall rule for port {0}.'
    firewall_description    = (
        'Remote access to the xstation web terminal. ' +
        'Remove with xsjs_stop.ps1.'
    )
    firewall_display_name   = 'xstation web terminal (TCP {0})'
    firewall_opened         = 'Opened TCP port {0} in Windows Firewall.'
    full_stop_mode          = 'Stopping ttyd and its sign-in start.'
    https_mode              = 'Serving HTTPS to other computers. User: {0}'
    install_server          = 'Installing the server in Linux'
    installed               = (
        'Installed. Next, run xsjs_start.ps1 as administrator.'
    )
    linux_missing           = (
        'Installing Ubuntu. When asked, choose a Linux user name and ' +
        'password. At a Linux prompt, type: exit'
    )
    localhost_mode          = 'No credentials: serving http://localhost only.'
    log_path                = 'Log: {0}'
    log_title               = '{0} log'
    make_certificate        = 'Checking the TLS certificate'
    no_log                  = "No log: can't write {0}"
    not_administrator       = 'Run {0} as administrator.'
    not_installed           = '{0} missing. Run xsjs_install.ps1 first.'
    open_firewall           = 'Opening firewall port {0}'
    open_urls               = 'Open {0} to use `{1}`.'
    openssl_install_failed  = 'Installing OpenSSL failed.'
    openssl_missing         = 'Installing OpenSSL with apt-get...'
    page_missing            = (
        '{0} is missing. In WSL, in the checkout, run ' +
        '`python3 python/page_build.py hyperposition-engine`.'
    )
    port_free               = 'Port {0} is free.'
    port_in_use             = (
        'Port {0} is used by {1} (PID {2}). Stop it and retry.'
    )
    proxy_added             = (
        'Port {1} on `{0}` now forwards to port {2} on `127.0.0.1`.'
    )
    proxy_failed            = 'Adding the port proxy failed.'
    proxy_listening         = (
        '{1} (PID {2}) listens on port {0} for the port proxy.'
    )
    proxy_none              = 'No port proxy from port {0} to ttyd.'
    proxy_not_listening     = (
        'Nothing listens on port {0}: the port proxy needs the IP Helper ' +
        'service.'
    )
    proxy_remove_failed     = (
        'Removing the port proxy from port {1} on `{0}` failed.'
    )
    proxy_removed           = 'Removed the port proxy from port {1} on `{0}`.'
    python_install_failed   = 'Installing Python 3 failed.'
    python_missing          = 'Installing Python 3 with apt-get...'
    register_task           = 'Setting ttyd to start at sign-in'
    remove_autostart        = 'Removing the sign-in start'
    restart_windows         = 'Restart Windows, then rerun {0}.'
    runner_comment          = (
        'From xsjs_start.ps1; task {0} runs it at sign-in. ' +
        'May hold the ttyd password: keep private.'
    )
    runner_removed          = 'Deleted `{0}`.'
    runner_written          = 'Wrote `{0}`.'
    server_installed        = 'Copied ttyd, the engine and page into `{0}`.'
    server_listening        = (
        'ttyd (Linux PID {1}) listening on port {0}, relayed by {2} ' +
        '(PID {3}). Log: `{4}`'
    )
    server_not_listening    = (
        'ttyd not listening on port {0}. Task result: {1}. Log (`{2}`):'
    )
    server_not_running      = 'ttyd was not running.'
    soft_stop_mode          = 'Stopping ttyd until next sign-in (--softly).'
    start_server            = 'Starting ttyd on port {0}'
    start_usage             = 'Usage: {0} [username:password]'
    started                 = 'Started {0} on {1}, PowerShell {2}'
    started_ok              = 'OK: {0} (stop: xsjs_stop.ps1)'
    status_certificate      = (
        'TLS certificate expires {0:yyyy-MM-dd}, SHA-256 {1}'
    )
    status_connections      = 'Port {0}: connected from {1}.'
    status_files            = 'Files in {0}: {1}'
    status_files_none       = 'No files in {0}.'
    status_firewall         = (
        'Firewall rule {0}: TCP {1} in, enabled {2}, profile {3}.'
    )
    status_firewall_none    = 'No firewall rule {0}.'
    status_https            = 'HTTPS, user {0}'
    status_linux            = 'Linux: {0}'
    status_linux_closed     = 'Linux port {0}: not listening.'
    status_linux_listening  = 'Linux port {0}: listening on {1} {2}'
    status_linux_none       = '{0} not running in Linux.'
    status_listening        = 'Port {0}: {1} (PID {2}) listens on {3}.'
    status_no_runner        = 'nothing ({0} missing)'
    status_port_closed      = 'Port {0}: not listening.'
    status_processes        = 'Task processes:'
    status_processes_none   = 'No task processes.'
    status_proxy            = 'Port proxy ({0}): {1} -> {2}'
    status_proxy_none       = 'No port proxies.'
    status_running          = '{0}: running on port {1}; no sign-in start.'
    status_running_signin   = '{0}: running on port {1}; starts at sign-in.'
    status_stopped          = '{0}: stopped; no sign-in start.'
    status_stopped_signin   = '{0}: stopped until next sign-in.'
    status_task             = (
        'Scheduled task {0}: {1}, serves {2} when {3} signs in, ' +
        'last result 0x{4:X}.'
    )
    status_task_none        = 'No scheduled task {0}.'
    status_ttyd             = 'ttyd in Linux (PID {0}): {1} on port {2}.'
    status_ttyd_none        = 'ttyd not running.'
    status_wsl              = 'WSL: {0} (default) is {1}.'
    status_wsl_none         = 'WSL: no default distribution.'
    stop_server             = 'Stopping ttyd on port {0}'
    stop_usage              = 'Usage: {0} [--softly][-s]'
    stopped                 = 'Stopped. No longer starts at sign-in.'
    stopped_softly          = (
        'Stopped until next sign-in. Restart now: Start-ScheduledTask {0}'
    )
    task_description        = (
        'Serves bootstrap.py with ttyd on port {0}. ' +
        'Remove with xsjs_stop.ps1.'
    )
    task_registered         = (
        'Scheduled task {0} runs `{1}` when `{2}` signs in.'
    )
    task_removed            = 'Removed scheduled task {0}.'
    task_stopped            = 'Stopped scheduled task {0}.'
    test_expected           = 'Expected "{0}", got "{1}".'
    test_failed_steps       = 'Failed steps: {0}. Log: `{1}`'
    test_lint_failed        = 'Fix what test_lint.ps1 found, then rerun.'
    test_passed             = 'The lifecycle ran without failures.'
    test_step_failed        = 'Step {0} failed.'
    ttyd_build_failed       = 'Building ttyd failed.'
    ttyd_configure_failed   = 'Configuring the ttyd build failed.'
    ttyd_fetch_failed       = 'Fetching the third party files failed.'
    ttyd_not_stopped        = (
        'ttyd (Linux PID {0}) still runs 15 s after SIGTERM.'
    )
    ttyd_patch_failed       = 'Applying the patch `{0}` to ttyd failed.'
    ttyd_stop_failed        = 'Stopping ttyd (Linux PID {0}) failed.'
    ttyd_stopped            = 'Stopped ttyd (Linux PID {0}).'
    ttyd_unpack_failed      = 'Unpacking the ttyd source failed.'
    ubuntu_not_working      = 'Ubuntu not ready. Restart Windows, rerun {0}.'
    windows_ttyd_left       = (
        'ttyd for Windows is no longer used and stays installed: `{0}`'
    )
    windows_ttyd_none       = 'No ttyd for Windows.'
    write_runner            = 'Writing the task script'
    wsl_install_failed      = 'Installing WSL failed (exit code {0}).'
    wsl_missing             = 'Installing WSL; approve the Windows prompt.'
    wsl_update_failed       = 'Updating WSL failed. Continuing anyway.'
}
