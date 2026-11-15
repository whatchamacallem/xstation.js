# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
@{
    check_container       = 'Checking the wslc container {0}'
    check_publish         = 'Checking that port {0} is published'
    container_checked     = (
        'The wslc container {0} adds no capability and mounts the checkout.'
    )
    container_missing     = (
        'There is no wslc container {0}. Run .\powershell\test_wslc.ps1, ' +
        'which makes it.'
    )
    container_published   = (
        'The wslc container {0} publishes port {1} on {2}.'
    )
    container_running     = 'The wslc container {0} runs.'
    container_unpublished = (
        'The wslc container {0} publishes no port {1} on {2}, by ' +
        'which Windows reaches it, and wslc publishes only when it makes ' +
        'a container. Remove it by `wslc remove --force {0}` and run ' +
        '.\powershell\test_wslc.ps1 to make it again.'
    )
    copy_checkout         = 'Copying this checkout into `{0}`'
    done                  = 'Done'
    exit_code             = '`{0}` exited {1}'
    failed                = 'Failed'
    failed_message        = 'FAILED: {0}'
    log_path              = 'Log: {0}'
    log_title             = '{0} log'
    open_urls             = 'Open {0}, served from the wslc container {1}.'
    server_ended          = (
        'The serve program (PID {0}) ended before it served. ' +
        'Its log, `~/{1}`:'
    )
    server_listening      = '{0} answers {1} through the published port.'
    server_not_running    = 'The serve program was not running.'
    server_not_stopped    = (
        'The serve program (PID {0}) still runs {1} s after SIGTERM.'
    )
    server_started        = (
        'The serve program runs as PID {0}, its log `~/{1}`.'
    )
    server_stopped        = 'Stopped the serve program (PID {0}).'
    setting_missing       = '`{0}` has no value with id `{1}`.'
    start_container       = 'Starting the wslc container {0}'
    start_server          = 'Starting the serve program on port {0}'
    start_usage           = 'Usage: {0} [--debug] [--verbose]'
    started               = 'Started {0} on {1}, PowerShell {2}'
    started_ok            = 'OK: {0} (stop: xsjs_stop.ps1)'
    status_connections    = 'Port {0}: connected from {1}.'
    status_container      = 'wslc container {0}: {1}.'
    status_container_none = 'No wslc container {0}.'
    status_listening      = 'Port {0}: {1} (PID {2}) listens on {3}.'
    status_port_closed    = 'Port {0}: not listening.'
    status_published      = 'Port {0} published on {1}:{2}.'
    status_running        = 'Running: {0}'
    status_server         = 'Serve program (PID {0}): {1}'
    status_server_none    = 'No serve program.'
    status_stopped        = 'Stopped.'
    status_unpublished    = 'The wslc container {0} publishes no port.'
    stop_server           = 'Stopping the serve program on port {0}'
    stop_usage            = 'Usage: {0}'
    stopped               = 'Stopped.'
    test_expected         = 'Expected "{0}", got "{1}".'
    test_failed_step      = 'Step {0} failed. Log: `{1}`'
    test_lint_failed      = 'Fix what test_lint.ps1 found, then rerun.'
    test_passed           = (
        'The lint, the lifecycle and `{0}` ran without failures.'
    )
    test_step_failed      = 'Step {0} failed.'
    test_usage            = (
        'Usage: {0} [--test-normal | --test-all | --test-disabled]'
    )
    wait_server           = 'Waiting for the serve program to listen'
    wslc_capability_added = (
        'The wslc container {0} holds the added capability {1}, where it ' +
        'should add none. Remove it by `wslc remove --force {0}` and run ' +
        '.\powershell\test_wslc.ps1 to make it again.'
    )
    wslc_drive_missing    = (
        '`{0}` is on no drive letter, so WSL has no path for it.'
    )
    wslc_mount_missing    = (
        'The wslc container {0} does not mount `{1}` at `{2}`. Remove it ' +
        'by `wslc remove --force {0}` and run .\powershell\test_wslc.ps1 ' +
        'to make it again.'
    )
}
