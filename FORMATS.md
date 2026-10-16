# xstation.js formats

Version 1 of 2026-10-15: the formats, addresses and constants in use, and a plan for one settings file.

## 1 Conventions

1.1 MUST, MUST NOT, SHOULD and MAY are used as in BCP 14 (RFC 2119, RFC 8174) when in capitals.

1.2 An identifier is two full English words: `UPPER_SNAKE` in a table, `lower-hyphen` in ABNF.

1.3 `PROMPT_TEXT` and `prompt-text` are one identifier. Each is unique in this document.

1.4 Each identifier has one description of at most 100 characters, where it is defined.

1.5 An identifier is never renamed or reused. One that goes out of use stays, marked retired.

1.6 A format's version starts at 1. A change that a reader of the old version can't read raises it.

1.7 A `Fixed` format's version is its owner's: a standard's, or a program's release.

1.8 A reader MUST reject an unknown version, a missing field and a malformed value. It MUST NOT guess.

1.9 Grammars are ABNF (RFC 5234), with quoted text case sensitive as `%s` makes it (RFC 7405).

1.10 Text is UTF-8 (RFC 3629) unless a row says otherwise.

1.11 In a form, `<NAME>` stands for what `NAME` defines, and `<some words>` for what the row says.

1.12 Section 5 lists every constant. One defined with its format there says where.

1.13 Kind says who sets a constant:

1.13.1 `Setting`: a choice for running or testing, which section 6 moves into `settings.json`.

1.13.2 `Tool`: a choice kept in another program's own configuration file.

1.13.3 `Protocol`: part of a format here. Changing it needs a new version of that format.

1.13.4 `Layout`: a name in the checkout's own layout. Renaming the file changes it.

1.13.5 `Fixed`: set by a standard, another program or the system.

1.13.6 `Code`: private to the files that name it. Nothing else depends on it.

1.13.7 `Test`: a test's fixture or expected value.

1.14 Source names files by base name, each unique in the checkout, with the name the code uses.

1.15 Values were read from the code, from ttyd's source at `../ttyd` commit `2922cb8`, and from Linux.

1.16 To add a format or constant: choose an unused identifier, add its row here, then change the code.

## 2 Wire and process formats

### 2.1 Registry

| Identifier            | Version     | Kind       | Peers                             | Meaning                                                                                   |
| --------------------- | ----------- | ---------- | --------------------------------- | ----------------------------------------------------------------------------------------- |
| `WEB_SERVICE`         | ttyd 1.7.7  | `Fixed`    | page, tests; ttyd                 | HTTP/1.1 (RFC 9112) that ttyd answers: the page, its token and the WebSocket upgrade.     |
| `SOCKET_FRAMING`      | 13          | `Fixed`    | page, tests; ttyd, Chrome         | WebSocket framing (RFC 6455).                                                             |
| `TERMINAL_MESSAGES`   | ttyd 1.7.7  | `Fixed`    | page, `test_wire.py`; ttyd        | ttyd's messages in `BINARY_FRAME` frames: a type byte, then the payload.                  |
| `TERMINAL_DISCIPLINE` | Linux 6.18  | `Fixed`    | ttyd; bootstrapper                | The pseudo terminal ttyd makes with `forkpty`, in canonical mode, as measured on WSL.     |
| `COMMAND_SESSION`     | 1           | `Protocol` | page, user; bootstrapper          | The bootstrapper's lines on its standard streams, before the terminal echoes and adds CR. |
| `MODULE_INTERFACE`    | 1           | `Protocol` | bootstrapper; module              | What a module gets from the bootstrapper, which forks to run it.                          |
| `COMMAND_LINES`       | 1           | `Protocol` | scripts; ttyd, Windows            | The command lines the scripts build, some of which other scripts parse.                   |
| `TOOL_OUTPUTS`        | each tool's | `Fixed`    | other programs; scripts           | What the scripts read from other programs, and how.                                       |
| `DEBUGGING_PROTOCOL`  | Chrome      | `Fixed`    | `xsjs_screenshot.py`; Chrome      | Chrome DevTools Protocol: JSON in `TEXT_FRAME` frames.                                    |
| `WINDOWS_BRIDGE`      | 1           | `Protocol` | `xsjs_screenshot_wsl.py`; Windows | How the screenshot tool runs PowerShell and reaches Chrome from WSL.                      |

### 2.2 `WEB_SERVICE`

| Identifier            | Request                                                | Answer                                                       | Meaning                                                                    |
| --------------------- | ------------------------------------------------------ | ------------------------------------------------------------ | -------------------------------------------------------------------------- |
| `INDEX_REQUEST`       | `GET /`                                                | `<SUCCESS_STATUS>`, the `--index` file                       | The page. ttyd's base path is unset, so every path starts at `/`.          |
| `TOKEN_REQUEST`       | `GET <TOKEN_PATH>`                                     | `<SUCCESS_STATUS>`, `{"token": "<t>"}`                       | `t` is the credential in base64 (RFC 4648), or empty without a credential. |
| `SOCKET_UPGRADE`      | `GET <SOCKET_PATH>`                                    | `<SWITCHING_STATUS>`                                         | Opens `SOCKET_FRAMING`. With `-O`, ttyd checks `Origin` against `Host`.    |
| `BASIC_CHALLENGE`     | with a credential, any request without `Authorization` | `<CHALLENGE_STATUS>`, `WWW-Authenticate: Basic realm="ttyd"` | On `<SOCKET_PATH>`, ttyd ends the connection with no HTTP status instead.  |
| `BASIC_AUTHORIZATION` | `Authorization: <BASIC_SCHEME> <t>`                    | as without a credential                                      | RFC 7617, with the same `t` that `TOKEN_REQUEST` gives.                    |
| `UNKNOWN_PATH`        | `GET` of any other path                                | `<MISSING_STATUS>`                                           | Measured with `UNSERVED_PATH`.                                             |

### 2.3 `SOCKET_FRAMING`

| Identifier           | Form                                                                                                  | Meaning                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `OPENING_HANDSHAKE`  | `Sec-WebSocket-Key`: `NONCE_LENGTH` random bytes in base64; `Sec-WebSocket-Version: <SOCKET_VERSION>` | The answer's `Sec-WebSocket-Accept` MUST be base64 of SHA-1 of the key and `HANDSHAKE_SUFFIX`. |
| `SUBPROTOCOL_CHOICE` | `Sec-WebSocket-Protocol: <SUBPROTOCOL_NAME>`                                                          | The page and the tests ask for it. ttyd MUST choose it, or the client fails.                   |
| `FRAME_HEADER`       | `FINAL_FLAG` and an opcode in `OPERATION_BITS`; `MASK_FLAG` and a length in `LENGTH_BITS`             | Lengths below `MEDIUM_MARKER` fit; `MEDIUM_MARKER` adds 2 length bytes, `LONG_MARKER` 8.       |
| `CLIENT_MASKING`     | `MASK_LENGTH` random bytes after the length, XORed over the payload                                   | A client MUST mask every frame. ttyd and Chrome send theirs unmasked.                          |
| `MESSAGE_FRAGMENTS`  | frames without `FINAL_FLAG`, then continuation frames, opcode 0                                       | `test_wire.py` splits an `INPUT_MESSAGE` inside a UTF-8 character this way.                    |
| `CLOSE_PAYLOAD`      | a 2 byte big-endian code, then a UTF-8 reason                                                         | The page and the tests close with `NORMAL_CLOSURE`, and ttyd answers with it.                  |
| `HEARTBEAT_PING`     | `PING_FRAME` from ttyd every 5 s                                                                      | ttyd closes a client that hasn't answered with `PONG_FRAME` by 10 s.                           |

### 2.4 `TERMINAL_MESSAGES`

| Identifier            | Direction         | Bytes                                                                          | Meaning                                                                                          |
| --------------------- | ----------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `OPENING_MESSAGE`     | to ttyd, first    | `{"AuthToken": "<t>", "columns": <TERMINAL_COLUMNS>, "rows": <TERMINAL_ROWS>}` | JSON, so its first byte is `{`. ttyd checks `t` if it has a credential, then starts the program. |
| `INPUT_MESSAGE`       | to ttyd           | `INPUT_TYPE`, then bytes                                                       | ttyd writes the bytes to the terminal, as its `-W` allows.                                       |
| `RESIZE_MESSAGE`      | to ttyd           | `0x31`, then `{"columns": <c>, "rows": <r>}`                                   | Sets the terminal's size. Nothing sends it today.                                                |
| `PAUSE_MESSAGE`       | to ttyd           | `0x32`                                                                         | Asks ttyd to hold output. Linux ttyd ignores it. Nothing sends it.                               |
| `RESUME_MESSAGE`      | to ttyd           | `0x33`                                                                         | Ends a pause. Nothing sends it.                                                                  |
| `TITLE_MESSAGE`       | from ttyd, first  | `TITLE_TYPE`, then `<command> (<host name>)`                                   | Sent once the program starts. The command is ttyd's own, space separated.                        |
| `PREFERENCES_MESSAGE` | from ttyd, second | `PREFERENCES_TYPE`, then JSON of ttyd's `-t` options                           | `{ }` when there are none. The page keeps it as text.                                            |
| `OUTPUT_MESSAGE`      | from ttyd         | `OUTPUT_TYPE`, then terminal bytes                                             | A message may end inside a UTF-8 character, so a reader decodes them as one stream.              |
| `CLIENT_CLOSE`        | to ttyd           | `CLOSE_PAYLOAD` with `NORMAL_CLOSURE`                                          | ttyd sends SIGHUP to the program and answers with `NORMAL_CLOSURE`.                              |
| `PROGRAM_EXIT`        | from ttyd         | no close frame                                                                 | Linux ttyd ends TCP when the program exits; a browser reports `ABNORMAL_CLOSURE`.                |

### 2.5 `TERMINAL_DISCIPLINE`

| Identifier            | Value             | Meaning                                                                                     |
| --------------------- | ----------------- | ------------------------------------------------------------------------------------------- |
| `LINE_FEED`           | `0x0A`            | Ends a line. Only a whole line reaches the bootstrapper.                                    |
| `CARRIAGE_RETURN`     | `0x0D`            | Read as `LINE_FEED` (`ICRNL`). Written before each `LINE_FEED` (`OPOST`, `ONLCR`).          |
| `LINE_LIMIT`          | `4095`            | Bytes a line holds before its `LINE_FEED`. Linux drops the rest without an error.           |
| `INPUT_ECHO`          | `ECHO`, `ECHOCTL` | Input is echoed as it arrives, a control byte as `^` and a letter.                          |
| `INTERRUPT_CHARACTER` | `0x03`            | Echoed as `INTERRUPT_ECHO`. Flushes input and output, and sends SIGINT to the bootstrapper. |
| `INTERRUPT_ECHO`      | `^C`              | What the terminal shows for `INTERRUPT_CHARACTER`.                                          |
| `END_CHARACTER`       | `0x04`            | At a line's start, ends input. Elsewhere, passes the line on without `LINE_FEED`.           |
| `ERASE_CHARACTER`     | `0x7F`            | Erases one byte. `IUTF8` is off, so it can leave part of a character.                       |
| `KILL_CHARACTER`      | `0x15`            | Erases the line typed so far.                                                               |
| `WORD_ERASE`          | `0x17`            | Erases the last word typed (`IEXTEN`).                                                      |
| `LITERAL_NEXT`        | `0x16`            | Takes the next byte as data (`IEXTEN`).                                                     |
| `REPRINT_CHARACTER`   | `0x12`            | Echoes the line typed so far again (`IEXTEN`).                                              |
| `QUIT_CHARACTER`      | `0x1C`            | Sends SIGQUIT, which ends the bootstrapper and the session. Measured: exit -3.              |
| `SUSPEND_CHARACTER`   | `0x1A`            | Echoed. Linux discards SIGTSTP to the orphaned group, so the session goes on. Measured.     |
| `STOP_CHARACTER`      | `0x13`            | Holds output until `START_CHARACTER` (`IXON`). Measured.                                    |
| `START_CHARACTER`     | `0x11`            | Releases held output.                                                                       |

### 2.6 `COMMAND_SESSION`

```abnf
; The first line of every session and of every `RESTART_COMMAND`.
banner-line    = banner-start banner-end line-feed
; The bootstrapper's absolute path, its file's SHA-256 and its process id.
banner-start   = %s"bootstrap " path-text %s" sha256 " digest-text %s" pid " decimal-number
; The Python version, then the modules folder's absolute path.
banner-end     = %s" python " version-text %s" modules " path-text
; Written while the bootstrapper waits for a command. No `LINE_FEED` follows it.
prompt-text    = %s"$ "
; Read from the terminal, then split as `COMMAND_WORDS` says.
command-line   = *line-byte line-feed
; Written after `PUT_COMMAND`: the file's name, its size in bytes and its SHA-256.
saved-line     = %s"saved " saved-name " " decimal-number %s" bytes sha256 " digest-text line-feed
; Written by `LIST_COMMAND` for each regular file: its size, SHA-256 and name.
listing-line   = decimal-number " " digest-text " " entry-name line-feed
; Written to standard error when a module exits with a code other than 0.
exit-line      = module-name %s": exit " signed-number line-feed
; Written to standard error when a command fails, as in 2.6.3.
error-line     = 1*line-byte line-feed
; Written when `INTERRUPT_CHARACTER` abandons a read, before the next prompt.
abandon-line   = line-feed
; An ASCII letter or underscore, then letters, digits or underscores, as `_MODULE_NAME` matches.
module-name    = name-start *name-rest
name-start     = %x41-5A / %x61-7A / %x5F
name-rest      = name-start / %x30-39
saved-name     = module-name %s".py"
; A SHA-256 in lower case hexadecimal.
digest-text    = 64digest-digit
digest-digit   = %x30-39 / %x61-66
decimal-number = 1*decimal-digit
; A negative code is minus the number of the signal that ended the module.
signed-number  = ["-"] decimal-number
decimal-digit  = %x30-39
path-text      = 1*line-byte
version-text   = 1*visible-byte
entry-name     = 1*line-byte
line-byte      = %x00-09 / %x0B-FF
visible-byte   = %x21-7E
line-feed      = %x0A
```

2.6.1 Commands. A builtin's name is checked before a module's.

| Identifier        | Words                      | Reply                                     | Meaning                                                                                   |
| ----------------- | -------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------- |
| `COMMAND_WORDS`   | any `command-line`         |                                           | Decoded as UTF-8, then split by Python's `shlex.split`: POSIX quoting, no expansion.      |
| `EMPTY_COMMAND`   | no words                   | nothing                                   | Does nothing.                                                                             |
| `PUT_COMMAND`     | `put <name>`               | `saved-line`                              | Reads to the end of input, then saves the bytes as `<name>.py`, replacing any file there. |
| `LIST_COMMAND`    | `ls`                       | `listing-line` for each                   | Lists the modules folder's regular files, not symbolic links, sorted by name.             |
| `RESTART_COMMAND` | `restart`                  | `banner-line`                             | Execs the interpreter on the bootstrapper's own command line: the same pid, new code.     |
| `MODULE_COMMAND`  | `<name> [<word> ...]`      | the module's output; `exit-line` unless 0 | Runs `<name>.py` as `MODULE_INTERFACE` says, with the other words, and waits for it.      |
| `SESSION_END`     | end of input at the prompt | none                                      | The bootstrapper exits 0, and ttyd ends the connection as `PROGRAM_EXIT` says.            |

2.6.2 Signals.

| Identifier        | Signal                      | Meaning                                                                               |
| ----------------- | --------------------------- | ------------------------------------------------------------------------------------- |
| `INTERRUPT_RELAY` | SIGINT while a module runs  | Sent on to the module's process group.                                                |
| `INPUT_ABANDONED` | SIGINT while no module runs | Abandons the read in progress, or else the next one: `abandon-line`, then the prompt. |
| `HANGUP_ENDING`   | SIGHUP or SIGTERM           | SIGKILL to the module's group, then the bootstrapper dies of the signal it got.       |

2.6.3 Errors, each an `error-line` on standard error.

| Identifier         | Text                                             | Meaning                                                          |
| ------------------ | ------------------------------------------------ | ---------------------------------------------------------------- |
| `ENCODING_ERROR`   | `not UTF-8: <message>`                           | The line isn't UTF-8. The message is Python's.                   |
| `QUOTING_ERROR`    | `<line>: <message>`                              | `shlex` couldn't split the line, as with `No closing quotation`. |
| `NAME_ERROR`       | `<word>: not a module name`                      | The first word isn't a `module-name`.                            |
| `MISSING_MODULE`   | `<name>: not found`                              | No `<name>.py` file is in the modules folder.                    |
| `USAGE_ERROR`      | `usage: put NAME`, `usage: ls`, `usage: restart` | A builtin got the wrong number of words.                         |
| `INTERNAL_FAILURE` | a Python traceback                               | Any other error ends the bootstrapper, and so the session.       |

### 2.7 `MODULE_INTERFACE`

| Identifier           | Value                                | Meaning                                                                            |
| -------------------- | ------------------------------------ | ---------------------------------------------------------------------------------- |
| `ARGUMENT_VECTOR`    | `sys.argv`                           | The module's path, then the words after its name.                                  |
| `MAIN_NAME`          | `__name__`                           | `"__main__"`, as `runpy.run_path` runs the file.                                   |
| `WORKING_FOLDER`     | `os.getcwd()`                        | The modules folder.                                                                |
| `IMPORT_PATH`        | `sys.path[0]`                        | The modules folder. A name the bootstrapper imported resolves to its module.       |
| `BOOTSTRAP_VARIABLE` | `XSJS_BOOTSTRAP`                     | An environment variable: the bootstrapper's absolute path.                         |
| `MODULES_VARIABLE`   | `XSJS_MODULES`                       | An environment variable: the modules folder's absolute path.                       |
| `STANDARD_STREAMS`   | descriptors 0, 1 and 2               | The terminal. Standard output and error write through, as under `python3 -u`.      |
| `OWN_SESSION`        | `os.setsid()`                        | A session and group of its own, with no controlling terminal, so `/dev/tty` fails. |
| `KEYBOARD_INTERRUPT` | SIGINT                               | Raises `KeyboardInterrupt`, as under `python3`.                                    |
| `EXIT_CODE`          | `sys.exit`, an exception or a signal | The bootstrapper reports any code but 0 in an `exit-line`.                         |
| `LEFTOVER_KILL`      | SIGKILL                              | Sent to the module's group when the module exits, ending what it started.          |
| `PROCESS_NAME`       | `/proc/<pid>/cmdline`                | The bootstrapper's command line, as the module is a fork of it.                    |

### 2.8 `COMMAND_LINES`

| Identifier             | Form                                                                                                                                                       | Meaning                                                                                  |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `BOOTSTRAP_COMMAND`    | `<INTERPRETER_NAME> <folder>/<SCRIPT_NAME> <folder>/<MODULES_FOLDER>`                                                                                      | What ttyd runs. Any other count of arguments prints a usage line and exits `USAGE_CODE`. |
| `SERVER_COMMAND`       | `<SERVER_NAME> -p <SERVICE_PORT> -i <LOOPBACK_ADDRESS> -W -O -T <TERMINAL_TYPE> --index <folder>/<PAGE_NAME> [<SECURE_OPTIONS>] <BOOTSTRAP_COMMAND>`       | Start runs it in WSL. Stop and status find ttyd by its start and end, with `pgrep`.      |
| `SECURE_OPTIONS`       | `--ssl --ssl-cert <state>/<CERTIFICATE_NAME> --ssl-key <state>/<KEY_NAME> -c <user>:<password>`                                                            | Added with a credential. `<state>` is the state folder's `WINDOWS_MOUNT` path.           |
| `WINDOWS_COMMAND`      | `-e <SERVER_COMMAND>`, each argument quoted as Windows programs split them                                                                                 | `wsl.exe`'s `ArgumentList` in `RUNNER_SCRIPT`.                                           |
| `TASK_ACTION`          | `<System32>\conhost.exe --headless "<powershell.exe>" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "<runner>"`                                 | What the scheduled task runs: the runner, in PowerShell, with no window.                 |
| `PROXY_COMMAND`        | `netsh interface portproxy add <PROXY_KIND> listenaddress=<address> listenport=<PUBLIC_PORT> connectaddress=<LOOPBACK_ADDRESS> connectport=<SERVICE_PORT>` | Forwards the public port to ttyd. `delete` takes the same listen address and port.       |
| `START_ARGUMENTS`      | `xsjs_start.ps1 [<user>:<password>]`                                                                                                                       | A user without `:`, then a password of at least one character, as `^[^:]+:.` matches.    |
| `STOP_ARGUMENTS`       | `xsjs_stop.ps1 [--softly \| -s]`                                                                                                                           | `--softly` keeps the task, port proxy, firewall rule and runner.                         |
| `SCREENSHOT_ARGUMENTS` | `xsjs_screenshot.py [--out <path>] [--typing <text>]`                                                                                                      | The text may hold no control byte and no `ERASE_CHARACTER`.                              |
| `ARCHIVE_ARGUMENTS`    | `archive.sh [<destination>]`                                                                                                                               | Without a destination, the archive goes to `BACKUP_FOLDER` if it exists, else home.      |
| `CLEAN_ARGUMENTS`      | `clean.sh [--help \| -h]`                                                                                                                                  | Removes what git ignores, except `LOG_FOLDER`.                                           |

### 2.9 `TOOL_OUTPUTS`

| Identifier          | Command                                                                   | Meaning                                                                                      |
| ------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `DISTRIBUTION_LIST` | `wsl.exe --list --verbose`                                                | NUL bytes and blank lines dropped; the line starting `*` gives the default's name and state. |
| `RUNNING_LIST`      | `wsl.exe --list --running --quiet`                                        | One name a line. Read because the state above is in the display language.                    |
| `HOME_QUERY`        | `wsl.exe -e printenv HOME`                                                | One line: the Linux user's home folder.                                                      |
| `PROCESS_LIST`      | `pgrep -a -x <SERVER_NAME>`, `pgrep -a -f <pattern>`                      | `<pid> <command line>` a line. The exit status is 1 when nothing matches.                    |
| `SOCKET_LIST`       | `ss -Hltnp sport = :<SERVICE_PORT>`                                       | Fields split on white space: state, two queues, local and peer address, then users.          |
| `FINGERPRINT_LINE`  | `openssl x509 -noout -fingerprint -sha256 -in <file>`                     | The text after the last `=`: hexadecimal pairs joined by `:`.                                |
| `EXPIRY_CHECK`      | `openssl x509 -checkend 0 -noout -in <file>`                              | Exit status 0 while the certificate is valid.                                                |
| `VERSION_CHECKS`    | `wsl --version`, `ttyd --version`, `python3 --version`, `openssl version` | Exit status 0 means installed. The output is logged, not parsed.                             |
| `BUILD_REVISION`    | `UBR` under `VERSION_KEY`                                                 | The update build revision, which `[Environment]::OSVersion` leaves out.                      |
| `NETWORK_ADDRESSES` | `Get-NetIPConfiguration`                                                  | This PC's IPv4 addresses on networks with a default gateway.                                 |

### 2.10 `DEBUGGING_PROTOCOL`

| Identifier       | Form                                                                                                                                                                                                                                                                                                      | Meaning                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `METHOD_REQUEST` | `{"id": <n>, "method": <m>, "params": <p>, "sessionId": <s>}`                                                                                                                                                                                                                                             | `n` counts from 1. `sessionId` goes with every method but `Browser.` and `Target.` ones. |
| `METHOD_REPLY`   | `{"id": <n>, "result": <r>}` or `{"id": <n>, "error": <e>}`                                                                                                                                                                                                                                               | Messages without the awaited `id`, such as events, are skipped.                          |
| `METHODS_USED`   | `Browser.close`, `Emulation.setDeviceMetricsOverride`, `Emulation.setFocusEmulationEnabled`, `Input.dispatchKeyEvent`, `Input.dispatchMouseEvent`, `Input.insertText`, `Page.captureScreenshot`, `Page.navigate`, `Runtime.evaluate`, `Target.attachToTarget`, `Target.createTarget`, `Target.getTargets` | Every method the screenshot tool calls.                                                  |

### 2.11 `WINDOWS_BRIDGE`

| Identifier           | Form                                                                                             | Meaning                                                                        |
| -------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `ENCODED_COMMAND`    | `<SHELL_NAME> -NoProfile -NonInteractive -EncodedCommand <base64 of the text in UTF-16LE>`       | Runs PowerShell text from WSL with no quoting in between.                      |
| `ENVIRONMENT_REPORT` | `{"LOCALAPPDATA": <s>, "ProgramFiles": <s>, "ProgramFiles(x86)": <s>, "TEMP": <s>}`              | One line of compressed JSON in UTF-8. A value is a string, or null when unset. |
| `BROWSER_START`      | `<browser> <BROWSER_OPTIONS> --user-data-dir=<TEMP>\<profile> --window-size=<w>,<h> about:blank` | Chrome or Edge, from `BROWSER_PATHS`. It picks its own DevTools port.          |
| `PORT_FILE`          | `<profile>\DevToolsActivePort`: a port line, then a path line                                    | Chrome writes it once DevTools listens. The tool reads both lines.             |
| `RELAY_UPLOAD`       | the relay's standard input to TCP                                                                | Carries bytes unchanged. Its end shuts down sending on the TCP connection.     |
| `RELAY_DOWNLOAD`     | TCP to the relay's standard output                                                               | Carries bytes unchanged, flushed after each read, until TCP ends.              |
| `BROWSER_STOP`       | `Stop-Process` of each `<browser>` whose command line holds `<profile>`                          | Windows Chrome outlives its WSL process, so the tool stops it by its profile.  |

## 3 File and record formats

### 3.1 Registry

| Identifier              | Version       | Kind       | Location                                                   | Meaning                                                                                      |
| ----------------------- | ------------- | ---------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `SOURCE_TEXT`           | 1             | `Protocol` | every text file in the checkout                            | Encoding, line ends, header and comments, as 3.2 says.                                       |
| `BOOTSTRAP_SCRIPT`      | 1             | `Protocol` | `python/<SCRIPT_NAME>`, copied to `LINUX_INSTALL`          | Python 3 source. The SHA-256 in `banner-line` names its exact bytes.                         |
| `BOOTSTRAP_PAGE`        | 1             | `Protocol` | `python/<PAGE_NAME>`, copied to `LINUX_INSTALL`            | One HTML5 file with inline style and script, served as ttyd's `--index`; 3.3 has its fields. |
| `MODULE_FILE`           | 1             | `Protocol` | `<LINUX_INSTALL>/<MODULES_FOLDER>/<name>.py`               | Exactly the bytes `PUT_COMMAND` read, run as Python 3 source.                                |
| `RUNNER_SCRIPT`         | 1             | `Protocol` | `<STATE_FOLDER>\<RUNNER_NAME>`                             | PowerShell, UTF-8 with `BYTE_ORDER`, CRLF; 3.4 has its lines. It holds the password.         |
| `SERVER_LOG`            | ttyd 1.7.7    | `Fixed`    | `<STATE_FOLDER>\<LOG_NAME>`; a pipe in the tests           | ttyd's standard error, replaced at each start; 3.5 has the lines read from it.               |
| `CERTIFICATE_FILE`      | 1             | `Protocol` | `<STATE_FOLDER>\<CERTIFICATE_NAME>`                        | A self-signed X.509 certificate in PEM; 3.6 has its fields. Kept until it expires.           |
| `PRIVATE_KEY`           | 1             | `Protocol` | `<STATE_FOLDER>\<KEY_NAME>`                                | The certificate's `KEY_ALGORITHM` key in PEM, unencrypted (`-nodes`).                        |
| `SCRIPT_LOG`            | 1             | `Protocol` | `<script>.ps1.md` beside each script but `xsjs_status.ps1` | Markdown that `mdformat --check` accepts; 3.7 has its blocks.                                |
| `TEXT_TABLE`            | 1             | `Protocol` | `powershell/<TEXT_CULTURE>/<TEXT_FILE>`                    | A PowerShell data file: one hashtable of names to .NET composite format strings.             |
| `REFORMAT_LIST`         | 1             | `Protocol` | `python/reformat_whitelist.txt`                            | One glob a line, from the top; top-level files by name. A glob matching nothing fails.       |
| `PROJECT_CONFIGURATION` | ruff, pyright | `Fixed`    | `python/pyproject.toml`                                    | TOML: `LINE_WIDTH` and `IGNORED_RULES` for ruff, `TYPE_CHECKING` for pyright.                |
| `EDITOR_SETTINGS`       | VS Code       | `Fixed`    | `.vscode/settings.json`                                    | Spelling words, a ruler at `LINE_WIDTH` and LF line ends.                                    |
| `ATTRIBUTE_LIST`        | git           | `Fixed`    | `.gitattributes`                                           | `* -text`: git converts no line ends.                                                        |
| `IGNORE_LIST`           | git           | `Fixed`    | `.gitignore`                                               | What git ignores: images, `BUILD_FOLDER`, `LOG_FOLDER` and the script logs.                  |
| `BUILD_LAYOUT`          | 1             | `Layout`   | `BUILD_FOLDER`                                             | Intermediates: `CACHE_FOLDER`, `LINT_CACHE`, and a folder for each test run.                 |
| `ARCHIVE_FILE`          | 1             | `Protocol` | `<destination>/<project>-<DATE_STAMP><ARCHIVE_SUFFIX>`     | An xz tar of `archive.sh` and `.git`. Run there alone, `archive.sh` restores the rest.       |
| `ENGINEERING_LOG`       | 1             | `Protocol` | `<LOG_FOLDER>/tasks_<day>_<HHMM>.md`                       | One a session: the requests verbatim, the order of operations, then the postmortem.          |
| `SCREENSHOT_IMAGE`      | 1             | `Protocol` | `python/<IMAGE_NAME>`                                      | A PNG of the whole page at `VIEWPORT_WIDTH` by `VIEWPORT_HEIGHT`.                            |
| `PROCESS_STATUS`        | Linux         | `Fixed`    | `/proc/<pid>/stat`                                         | `test_wire.py` reads fields after the last `)`: state, parent, group, session.               |
| `PROXY_REGISTRY`        | Windows       | `Fixed`    | registry `PROXY_KEY`                                       | A value a proxy: named `<listen address>/<port>`, holding `<connect address>/<port>`.        |
| `SCHEDULED_TASK`        | Windows       | `Fixed`    | Task Scheduler, `TASK_NAME`                                | `TASK_ACTION` at the sign in of the user who ran start, with the settings in 5.5.            |
| `FIREWALL_RULE`         | Windows       | `Fixed`    | Windows Firewall, `RULE_NAME`                              | Allows inbound TCP on `PUBLIC_PORT` for `FIREWALL_PROFILE`. Only made with a credential.     |
| `SETTINGS_FILE`         | 1             | `Protocol` | `settings.json` at the top                                 | Planned in section 6. It isn't in the checkout yet.                                          |

### 3.2 `SOURCE_TEXT`

| Identifier         | Form                                                                                 | Meaning                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| `TEXT_ENCODING`    | UTF-8; `.ps1` and `.psd1` start with `BYTE_ORDER`                                    | PowerShell 5.1 misreads non-ASCII without `BYTE_ORDER`.                                         |
| `LINE_ENDING`      | LF                                                                                   | `test_lint.ps1` fails on CR in a PowerShell file.                                               |
| `PLAIN_CHARACTERS` | ASCII and `ALLOWED_CHARACTERS`                                                       | What a file `REFORMAT_LIST` names may hold.                                                     |
| `LICENSE_HEADER`   | `SPDX-FileCopyrightText`, `SPDX-License-Identifier: MIT`, a line naming `LICENSE.md` | The top comment of each source file, in its language's comment syntax.                          |
| `COMMENT_RULES`    | below the header                                                                     | One line, not `<# #>`, with only letters, digits, space and `ENGLISH_PUNCTUATION` outside code. |
| `IMPORT_STYLE`     | `import a, b, c`                                                                     | Python, sorted, on the fewest lines; `from` only for `collections.abc` and `typing`.            |

### 3.3 `BOOTSTRAP_PAGE`

| Identifier         | Name                                 | Meaning                                                                                            |
| ------------------ | ------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `PAGE_STATE`       | `window.boot`                        | The object a driver reads: the fields below, updated as messages come.                             |
| `TITLE_TEXT`       | `boot.ttyd.title`                    | `TITLE_MESSAGE`'s payload as text, or null before it comes.                                        |
| `PREFERENCES_TEXT` | `boot.ttyd.preferences`              | `PREFERENCES_MESSAGE`'s payload as text, not parsed, or null before it comes.                      |
| `OUTPUT_TEXT`      | `boot.output`                        | Every `OUTPUT_MESSAGE` decoded as one UTF-8 stream, with each `CARRIAGE_RETURN` removed.           |
| `CLOSE_RECORD`     | `boot.closed`                        | `{code, reason, wasClean}` from the close event, or null while open.                               |
| `FAILURE_TEXT`     | `boot.failure`                       | The first failure only, or null. A failure closes with `NORMAL_CLOSURE` and `FAILURE_REASON`.      |
| `PAGE_CONTROLS`    | `input`, `interrupt`, `eof`, `close` | Enter sends the input and `LINE_FEED`. The buttons: `INTERRUPT_CHARACTER`, `END_CHARACTER`, close. |
| `STATUS_LINES`     | `status`                             | `socket` and its state with any close, `ttyd title`, `ttyd preferences`, then any `failure`.       |
| `LONG_LINE`        | a line over `LINE_LIMIT` bytes       | Sends nothing and records a failure, as the terminal would cut the line short.                     |

### 3.4 `RUNNER_SCRIPT`

| Identifier         | Line                                     | Meaning                                                                              |
| ------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------ |
| `RUNNER_COMMENT`   | `# <runner_comment>`                     | From `TEXT_TABLE`: which task runs it, and that it may hold the password.            |
| `SERVER_ARGUMENTS` | `$server_ = @{...}`                      | `wsl.exe`'s path, `WINDOWS_COMMAND`, the state folder and `SERVER_LOG`, to wait for. |
| `RUNNER_EXIT`      | `exit (Start-Process @server_).ExitCode` | Exits with `wsl.exe`'s code, which the task shows as its last result.                |

### 3.5 `SERVER_LOG`

| Identifier       | Pattern                                                             | Meaning                                                               |
| ---------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `VERSION_LINE`   | ` N: (ttyd \S+ \(libwebsockets \S+\))$`                             | ttyd's first line: its version and that of libwebsockets.             |
| `LISTENING_LINE` | ` Listening on port: (\d+)$`                                        | The port ttyd took for `--port 0`.                                    |
| `PROGRAM_ENDED`  | `process (killed with signal\|exited with code) (\d+), pid: <pid>$` | How the program ended: SIGHUP after `CLIENT_CLOSE`, or its exit code. |

### 3.6 `CERTIFICATE_FILE`

| Identifier          | Value                                                                              | Meaning                                                                     |
| ------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `SUBJECT_NAME`      | `/CN=<computer name>`                                                              | The Windows computer's name.                                                |
| `ALTERNATIVE_NAMES` | `DNS:<computer name>`, `DNS:<LOCAL_HOST>`, `IP:<LOOPBACK_ADDRESS>`, `IP:<address>` | One `IP:` for each of `NETWORK_ADDRESSES` when the certificate was made.    |
| `VALIDITY_PERIOD`   | `CERTIFICATE_LIFETIME` days from its making                                        | Start makes a new one once `EXPIRY_CHECK` fails.                            |
| `FINGERPRINT_TEXT`  | SHA-256 of the DER bytes, upper case hexadecimal pairs joined by `:`               | Start prints it and status shows it, to check against what a browser shows. |

### 3.7 `SCRIPT_LOG`

| Identifier        | Form                                                                          | Meaning                                                                                     |
| ----------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `LOG_TITLE`       | `# <script> log`                                                              | The first line, written whole when the script starts.                                       |
| `STARTED_LINE`    | `Started <DATE_FORMAT> on Windows <version>.<revision>, PowerShell <version>` | The second block. The revision is `BUILD_REVISION`.                                         |
| `SECTION_HEADING` | `## <step>`                                                                   | One a step.                                                                                 |
| `OUTPUT_BLOCK`    | a fenced block of type `text`                                                 | A command's output or a failure's position, CRLF made LF and NUL removed.                   |
| `ALERT_BLOCK`     | `> [!NOTE]`, `> [!WARNING]` or `> [!CAUTION]`, then `> ` lines                | A notice, a problem or the failure.                                                         |
| `PLAIN_BLOCK`     | a paragraph                                                                   | Each block starts with a blank line and the file ends with one LF. Backslashes are doubled. |

## 4 URL and path formats

| Identifier           | Form                                                    | Used by                  | Meaning                                                                        |
| -------------------- | ------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------ |
| `LOCAL_ADDRESS`      | `http://<LOCAL_HOST>:<PUBLIC_PORT>/`                    | start, plan              | The page when start has no credential.                                         |
| `SECURE_LOCAL`       | `https://<LOCAL_HOST>:<PUBLIC_PORT>/`                   | start                    | The page on this PC when start has a credential.                               |
| `HOST_ADDRESS`       | `https://<computer name in lower case>:<PUBLIC_PORT>/`  | start                    | The first address start prints with a credential.                              |
| `NETWORK_ADDRESS`    | `https://<IPv4 address>:<PUBLIC_PORT>/`                 | start                    | One for each of `NETWORK_ADDRESSES`.                                           |
| `TOKEN_ADDRESS`      | `<page scheme>//<page host><page path><TOKEN_PATH>`     | page                     | The page path loses any trailing `/` first.                                    |
| `SOCKET_ADDRESS`     | `<ws: or wss:>//<page host><page path><SOCKET_PATH>`    | page                     | `wss:` when the page came over `https:`.                                       |
| `TEST_ADDRESS`       | `http://<LOOPBACK_ADDRESS>:<port>/`                     | `test_wire.py`           | The port is `LISTENING_LINE`'s. Without its `/`, it is the `Origin` too.       |
| `SCREENSHOT_ADDRESS` | `http://<LOCAL_HOST>:<SCREENSHOT_PORT>/`                | `xsjs_screenshot.py`     | Windows Chrome reaches WSL's port by localhost forwarding.                     |
| `DEBUGGING_ADDRESS`  | `ws://<LOOPBACK_ADDRESS>:<port><path>`                  | `xsjs_screenshot.py`     | Both from `PORT_FILE`. The bytes go by `RELAY_UPLOAD` and `RELAY_DOWNLOAD`.    |
| `BLANK_PAGE`         | `about:blank`                                           | `xsjs_screenshot_wsl.py` | Chrome's first page and a new target's, before the page loads.                 |
| `REPOSITORY_ADDRESS` | `https://github.com/tsl0922/ttyd.git`                   | `xsjs_screenshot.py`     | ttyd's source, cloned to `SERVER_CHECKOUT` when missing and never updated.     |
| `LINUX_INSTALL`      | `$HOME/<INSTALL_FOLDER>`                                | start, stop, status      | `$HOME` is `HOME_QUERY`'s.                                                     |
| `STATE_FOLDER`       | `%LOCALAPPDATA%\<STATE_NAME>`                           | start, stop, status      | Only the user who ran start can read it.                                       |
| `LINUX_SHARE`        | `\\wsl.localhost\<distribution>\home\<user>\<checkout>` | a person                 | A Linux checkout as Windows sees it. The scripts run from there with `Bypass`. |
| `WINDOWS_CHECKOUT`   | `C:\src\xstation.js`                                    | `README.md`              | The supported checkout for Windows users.                                      |
| `WINDOWS_MOUNT`      | `/mnt/<drive>/<path>`                                   | start, screenshot        | A Windows path as `wslpath -u` maps it.                                        |

## 5 Constants

Every constant in use but 0 and false. Values are the code's, in the unit the Value column gives.

### 5.1 Network

| Identifier         | Value       | Kind      | Source                                                                                            | Meaning                                                                            |
| ------------------ | ----------- | --------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `PUBLIC_PORT`      | `5768`      | `Setting` | `xsjs_util.ps1` `$port_`                                                                          | The Windows port the browser opens. The port proxy listens on it.                  |
| `SERVICE_PORT`     | `5769`      | `Setting` | `xsjs_util.ps1` `$linux_port_`                                                                    | Linux ttyd's port on WSL's loopback, which the port proxy forwards to.             |
| `SCREENSHOT_PORT`  | `7681`      | `Setting` | `xsjs_screenshot.py` `_TTYD_PORT`                                                                 | ttyd's port for a screenshot run, which must be free.                              |
| `LOOPBACK_ADDRESS` | `127.0.0.1` | `Fixed`   | `xsjs_util.ps1`; `xsjs_start.ps1`; `test_wire.py`; `xsjs_screenshot.py`; `xsjs_screenshot_wsl.py` | Where ttyd binds, where the local proxy listens, and where Chrome serves DevTools. |
| `WILDCARD_ADDRESS` | `0.0.0.0`   | `Fixed`   | `xsjs_start.ps1` `$address_`                                                                      | Every IPv4 interface: where the proxy listens when start has a credential.         |
| `LOCAL_HOST`       | `localhost` | `Fixed`   | `xsjs_util.ps1`; `xsjs_start.ps1`; `xsjs_screenshot.py`                                           | The host name in local addresses and in the certificate.                           |
| `PROXY_KIND`       | `v4tov4`    | `Fixed`   | `xsjs_util.ps1`; `xsjs_start.ps1`                                                                 | The `netsh` port proxy kind: IPv4 to IPv4.                                         |

### 5.2 Names and folders

| Identifier           | Value                        | Kind      | Source                                                                                                         | Meaning                                                                         |
| -------------------- | ---------------------------- | --------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `TASK_NAME`          | `xstation.js`                | `Setting` | `xsjs_util.ps1` `$task_name_`                                                                                  | The scheduled task's name, by which start, stop and status find it.             |
| `RULE_NAME`          | `xstation.js`                | `Setting` | `xsjs_util.ps1` `$firewall_rule_name_`                                                                         | The Windows Firewall rule's name.                                               |
| `STATE_NAME`         | `xstation.js`                | `Setting` | `xsjs_util.ps1` `$state_path_`                                                                                 | The folder under `%LOCALAPPDATA%` for the runner, log, certificate and key.     |
| `RUNNER_NAME`        | `serve.ps1`                  | `Setting` | `xsjs_util.ps1` `$runner_path_`                                                                                | `RUNNER_SCRIPT`'s file name.                                                    |
| `LOG_NAME`           | `ttyd.log`                   | `Setting` | `xsjs_util.ps1` `$ttyd_log_path_`                                                                              | `SERVER_LOG`'s file name.                                                       |
| `CERTIFICATE_NAME`   | `_cached_cert.pem`           | `Setting` | `xsjs_util.ps1` `$certificate_path_`                                                                           | `CERTIFICATE_FILE`'s file name.                                                 |
| `KEY_NAME`           | `_cached_key.pem`            | `Setting` | `xsjs_util.ps1` `$key_path_`                                                                                   | `PRIVATE_KEY`'s file name.                                                      |
| `INSTALL_FOLDER`     | `.cache/xsjs`                | `Setting` | `xsjs_util.ps1` `$linux_folder_`                                                                               | The folder below the Linux home that start copies the script and page into.     |
| `MODULES_FOLDER`     | `modules`                    | `Setting` | `xsjs_util.ps1`; `xsjs_start.ps1`; `test_wire.py`; `xsjs_screenshot.py`                                        | The modules folder, inside `LINUX_INSTALL` or a test's run folder.              |
| `INTERPRETER_NAME`   | `python3`                    | `Setting` | `xsjs_util.ps1`; `test_wire.py`; `xsjs_screenshot.py`                                                          | The program ttyd runs the bootstrapper with, found on Linux's `PATH`.           |
| `LINUX_DISTRIBUTION` | `Ubuntu`                     | `Setting` | `xsjs_install.ps1`                                                                                             | The distribution install installs when WSL runs none.                           |
| `LINUX_PACKAGES`     | `python3`, `openssl`, `ttyd` | `Fixed`   | `xsjs_install.ps1`                                                                                             | The apt packages install installs when their commands are missing.              |
| `SERVER_NAME`        | `ttyd`                       | `Fixed`   | `xsjs_util.ps1`                                                                                                | The process name stop and status look for with `pgrep -x`.                      |
| `SCRIPT_NAME`        | `bootstrap.py`               | `Layout`  | `xsjs_util.ps1` `$bootstrap_script_`; `test_wire.py` `_BOOTSTRAP_PATH`; `xsjs_screenshot.py` `_BOOTSTRAP_PATH` | `BOOTSTRAP_SCRIPT`'s file name, in `python/` and in `LINUX_INSTALL`.            |
| `PAGE_NAME`          | `bootstrap.html`             | `Layout`  | `xsjs_util.ps1` `$bootstrap_page_`; `test_wire.py` `_INDEX_PATH`; `xsjs_screenshot.py` `_BOOTSTRAP_PAGE_PATH`  | `BOOTSTRAP_PAGE`'s file name, in `python/` and in `LINUX_INSTALL`.              |
| `TEXT_FILE`          | `i18n.psd1`                  | `Layout`  | `xsjs_util.ps1`                                                                                                | `TEXT_TABLE`'s file name.                                                       |
| `TEXT_CULTURE`       | `en-US`                      | `Layout`  | `xsjs_util.ps1`                                                                                                | The text table loaded when Windows' display language has none.                  |
| `BUILD_FOLDER`       | `build`                      | `Layout`  | `reformat.py`; `test_posix.py`; `test_wire.py`; `xsjs_screenshot.py`; `.gitignore`                             | Where intermediates go. Git ignores it.                                         |
| `CACHE_FOLDER`       | `build/pycache`              | `Layout`  | `test_posix.py`; `xsjs_screenshot.py`                                                                          | `sys.pycache_prefix`: the bytecode of imported sibling modules.                 |
| `LINT_CACHE`         | `build/ruff_cache`           | `Layout`  | `reformat.py`; `test_posix.py`                                                                                 | ruff's `--cache-dir`.                                                           |
| `LOG_FOLDER`         | `tmp`                        | `Layout`  | `clean.sh`; `.gitignore`                                                                                       | Where `ENGINEERING_LOG` files go. `clean.sh` keeps it.                          |
| `SERVER_CHECKOUT`    | `../ttyd`                    | `Setting` | `test_wire.py` `_TTYD_PATH`; `xsjs_screenshot.py` `_TTYD_PATH`                                                 | ttyd's checkout beside the project. The tests run its `build/ttyd`.             |
| `WIRE_PREFIX`        | `test_wire-`                 | `Code`    | `test_wire.py`                                                                                                 | The start of each wire test run's folder name in `BUILD_FOLDER`.                |
| `PROFILE_PREFIX`     | `xsjs_screenshot-`           | `Code`    | `xsjs_screenshot.py`; `xsjs_screenshot_wsl.py` `_PROFILE_PREFIX`                                               | The start of each screenshot run's folder name and Chrome profile name.         |
| `IMAGE_NAME`         | `xsjs_screenshot.png`        | `Setting` | `xsjs_screenshot.py` `_IMAGE_NAME`                                                                             | `SCREENSHOT_IMAGE`'s file name in `python/`, unless `--out` gives another path. |
| `PORT_FILE`          | `DevToolsActivePort`         | `Fixed`   | `xsjs_screenshot_wsl.py` `_DEVTOOLS_PORT_FILE_NAME`                                                            | Defined in 2.11.                                                                |

### 5.3 Terminal and session

| Identifier            | Value                    | Kind       | Source                                                                                | Meaning                                                             |
| --------------------- | ------------------------ | ---------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `TERMINAL_TYPE`       | `dumb`                   | `Setting`  | `xsjs_util.ps1`; `test_wire.py` `_TTYD_OPTIONS`; `xsjs_screenshot.py`                 | ttyd's `-T`: the program's `TERM`, so Python writes no colour.      |
| `TERMINAL_COLUMNS`    | `80`                     | `Setting`  | `bootstrap.html` `onOpen`; `test_wire.py` `_COLUMNS`                                  | Columns in `OPENING_MESSAGE`, the same as ttyd's own default.       |
| `TERMINAL_ROWS`       | `24`                     | `Setting`  | `bootstrap.html` `onOpen`; `test_wire.py` `_ROWS`                                     | Rows in `OPENING_MESSAGE`, the same as ttyd's own default.          |
| `LINE_LIMIT`          | `4095`                   | `Fixed`    | `bootstrap.html` `LINE_BYTES_MAX`; `test_wire.py` `_LINE_BYTES`                       | Defined in 2.5.                                                     |
| `LINE_FEED`           | `0x0A`                   | `Fixed`    | `bootstrap.py`; `bootstrap.html`                                                      | Defined in 2.5.                                                     |
| `CARRIAGE_RETURN`     | `0x0D`                   | `Fixed`    | `bootstrap.html` `onMessage`                                                          | Defined in 2.5.                                                     |
| `INTERRUPT_CHARACTER` | `0x03`                   | `Fixed`    | `bootstrap.html` `INTERRUPT_TEXT`; `test_wire.py` `_INTERRUPT`                        | Defined in 2.5.                                                     |
| `INTERRUPT_ECHO`      | `^C`                     | `Fixed`    | `test_wire.py` `_INTERRUPT_ECHO`                                                      | Defined in 2.5.                                                     |
| `END_CHARACTER`       | `0x04`                   | `Fixed`    | `bootstrap.html` `END_OF_INPUT_TEXT`; `test_wire.py` `_EOF`                           | Defined in 2.5.                                                     |
| `ERASE_CHARACTER`     | `0x7F`                   | `Fixed`    | `xsjs_screenshot.py` `main`                                                           | Defined in 2.5.                                                     |
| `PROMPT_TEXT`         | `$ `                     | `Protocol` | `bootstrap.py` `_PROMPT`; `test_wire.py` `_PROMPT`; `xsjs_screenshot.py` `_PROMPT`    | Defined in 2.6 as `prompt-text`.                                    |
| `MODULE_NAME`         | `[A-Za-z_][A-Za-z0-9_]*` | `Protocol` | `bootstrap.py` `_MODULE_NAME`                                                         | Defined in 2.6 as `module-name`.                                    |
| `BANNER_LINE`         | 2.6 `banner-line`        | `Protocol` | `test_wire.py` `_BANNER_PATTERN`; `xsjs_screenshot.py` `_BANNER_PATTERN`              | Defined in 2.6 as `banner-line`.                                    |
| `BOOTSTRAP_VARIABLE`  | `XSJS_BOOTSTRAP`         | `Protocol` | `bootstrap.py` `module_run`                                                           | Defined in 2.7.                                                     |
| `MODULES_VARIABLE`    | `XSJS_MODULES`           | `Protocol` | `bootstrap.py` `module_run`                                                           | Defined in 2.7.                                                     |
| `READ_SIZE`           | `65536` bytes            | `Code`     | `bootstrap.py` `_READ_SIZE`; `test_wire.py`; `xsjs_screenshot_wsl.py` `_RELAY_SCRIPT` | The most bytes taken in one read of a descriptor, socket or stream. |
| `SOCKET_READ`         | `1048576` bytes          | `Code`     | `test_wire.py` `socket_read`                                                          | The most bytes the wire test takes in one read of its WebSocket.    |
| `OUTPUT_ENCODING`     | `WSL_UTF8=1`             | `Fixed`    | `xsjs_util.ps1`                                                                       | Makes `wsl.exe` write its own messages in UTF-8, not UTF-16.        |

### 5.4 HTTP and WebSocket

| Identifier         | Value                                     | Kind       | Source                                                                                                                 | Meaning                                                                    |
| ------------------ | ----------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `TOKEN_PATH`       | `/token`                                  | `Fixed`    | `bootstrap.html` `start`; `test_wire.py`                                                                               | The path of `TOKEN_REQUEST`.                                               |
| `SOCKET_PATH`      | `/ws`                                     | `Fixed`    | `bootstrap.html` `start`; `test_wire.py`                                                                               | The path of `SOCKET_UPGRADE`.                                              |
| `SUCCESS_STATUS`   | `200`                                     | `Fixed`    | `test_wire.py`                                                                                                         | The status of `INDEX_REQUEST` and `TOKEN_REQUEST`.                         |
| `SWITCHING_STATUS` | `101`                                     | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | The status of an accepted WebSocket upgrade.                               |
| `CHALLENGE_STATUS` | `401`                                     | `Fixed`    | `test_wire.py`                                                                                                         | The status of `BASIC_CHALLENGE`.                                           |
| `MISSING_STATUS`   | `404`                                     | `Fixed`    | `test_wire.py`                                                                                                         | The status of `UNKNOWN_PATH`.                                              |
| `BASIC_SCHEME`     | `Basic`                                   | `Fixed`    | `test_wire.py`                                                                                                         | The `Authorization` scheme ttyd takes.                                     |
| `SUBPROTOCOL_NAME` | `tty`                                     | `Fixed`    | `bootstrap.html` `start`; `test_wire.py`                                                                               | The WebSocket subprotocol ttyd speaks.                                     |
| `SOCKET_VERSION`   | `13`                                      | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | `Sec-WebSocket-Version`, the only one RFC 6455 defines.                    |
| `HANDSHAKE_SUFFIX` | `258EAFA5-E914-47DA-95CA-C5AB0DC85B11`    | `Fixed`    | `test_wire.py` `_WEBSOCKET_GUID`; `xsjs_screenshot.py` `_WEBSOCKET_GUID`                                               | What RFC 6455 appends to the key before SHA-1, to make the accept value.   |
| `NONCE_LENGTH`     | `16` bytes                                | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | Random bytes in `Sec-WebSocket-Key`, before base64.                        |
| `MASK_LENGTH`      | `4` bytes                                 | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | A client frame's masking key.                                              |
| `FINAL_FLAG`       | `0x80`                                    | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | The first header byte's bit for a message's last frame.                    |
| `MASK_FLAG`        | `0x80`                                    | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | The second header byte's bit for a masked payload.                         |
| `OPERATION_BITS`   | `0x0F`                                    | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | The first header byte's opcode bits.                                       |
| `LENGTH_BITS`      | `0x7F`                                    | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | The second header byte's length bits.                                      |
| `MEDIUM_MARKER`    | `126`                                     | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | A length that says a 2 byte length follows.                                |
| `LONG_MARKER`      | `127`                                     | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | A length that says an 8 byte length follows.                               |
| `MEDIUM_LIMIT`     | `65536` bytes                             | `Fixed`    | `test_wire.py`; `xsjs_screenshot.py`                                                                                   | Payloads shorter than this take the 2 byte length.                         |
| `TEXT_FRAME`       | `0x1`                                     | `Fixed`    | `xsjs_screenshot.py` `_WEBSOCKET_OPCODE_TEXT`                                                                          | The opcode of a text frame, which `DEBUGGING_PROTOCOL` uses.               |
| `BINARY_FRAME`     | `0x2`                                     | `Fixed`    | `test_wire.py` `_WEBSOCKET_OPCODE_BINARY`                                                                              | The opcode of a binary frame, which `TERMINAL_MESSAGES` uses.              |
| `CLOSE_FRAME`      | `0x8`                                     | `Fixed`    | `test_wire.py` `_WEBSOCKET_OPCODE_CLOSE`; `xsjs_screenshot.py` `_WEBSOCKET_OPCODE_CLOSE`                               | The opcode of a close frame.                                               |
| `PING_FRAME`       | `0x9`                                     | `Fixed`    | `test_wire.py` `_WEBSOCKET_OPCODE_PING`; `xsjs_screenshot.py` `_WEBSOCKET_OPCODE_PING`                                 | The opcode of a ping, which a pong must answer.                            |
| `PONG_FRAME`       | `0xA`                                     | `Fixed`    | `test_wire.py` `_WEBSOCKET_OPCODE_PONG`; `xsjs_screenshot.py` `_WEBSOCKET_OPCODE_PONG`                                 | The opcode of a pong.                                                      |
| `NORMAL_CLOSURE`   | `1000`                                    | `Fixed`    | `bootstrap.html` `onClosePressed`; `test_wire.py` `_WEBSOCKET_CLOSE_NORMAL`; `xsjs_screenshot.py` `_CLOSE_CODE_NORMAL` | The close code for a finished connection.                                  |
| `ABNORMAL_CLOSURE` | `1006`                                    | `Fixed`    | `test_wire.py`; `PLAN_OF_RECIORD.md`                                                                                   | What a browser reports when TCP ends with no close frame. Nobody sends it. |
| `FAILURE_REASON`   | `failure`                                 | `Protocol` | `bootstrap.html` `record`                                                                                              | The close reason the page sends with `NORMAL_CLOSURE` after a failure.     |
| `INPUT_TYPE`       | `0x30`                                    | `Fixed`    | `bootstrap.html` `TTYD_INPUT_TYPE`; `test_wire.py`                                                                     | `INPUT_MESSAGE`'s type byte, `0`.                                          |
| `OUTPUT_TYPE`      | `0x30`                                    | `Fixed`    | `bootstrap.html` `TTYD_OUTPUT_TYPE`; `test_wire.py`                                                                    | `OUTPUT_MESSAGE`'s type byte, `0`.                                         |
| `TITLE_TYPE`       | `0x31`                                    | `Fixed`    | `bootstrap.html` `TTYD_FIRST_TYPES`; `test_wire.py`                                                                    | `TITLE_MESSAGE`'s type byte, `1`.                                          |
| `PREFERENCES_TYPE` | `0x32`                                    | `Fixed`    | `bootstrap.html` `TTYD_FIRST_TYPES`; `test_wire.py`                                                                    | `PREFERENCES_MESSAGE`'s type byte, `2`.                                    |
| `READY_STATES`     | `connecting`, `open`, `closing`, `closed` | `Fixed`    | `bootstrap.html` `READY_STATES`                                                                                        | WebSocket's `readyState` names, in order, for `STATUS_LINES`.              |

### 5.5 Windows

| Identifier           | Value                                                                                                            | Kind       | Source                                                             | Meaning                                                                            |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `TASK_TRIGGER`       | `-AtLogOn`                                                                                                       | `Code`     | `xsjs_start.ps1`                                                   | The task starts at sign in, not boot: WSL is unreliable while nobody is signed in. |
| `LOGON_TYPE`         | `Interactive`                                                                                                    | `Setting`  | `xsjs_start.ps1`                                                   | The task runs only in the session of the user who ran start.                       |
| `RUN_LEVEL`          | `Limited`                                                                                                        | `Setting`  | `xsjs_start.ps1`                                                   | The task runs without administrator rights.                                        |
| `BATTERY_START`      | `$true`                                                                                                          | `Setting`  | `xsjs_start.ps1` `AllowStartIfOnBatteries`                         | The task starts on battery power.                                                  |
| `BATTERY_CONTINUE`   | `$true`                                                                                                          | `Setting`  | `xsjs_start.ps1` `DontStopIfGoingOnBatteries`                      | The task keeps running when power changes to battery.                              |
| `INSTANCE_POLICY`    | `IgnoreNew`                                                                                                      | `Setting`  | `xsjs_start.ps1` `MultipleInstances`                               | Starting the task while it runs does nothing.                                      |
| `HEADLESS_CONSOLE`   | `conhost.exe --headless`                                                                                         | `Code`     | `xsjs_start.ps1`                                                   | Runs PowerShell, and so `wsl.exe`, with no window.                                 |
| `FIREWALL_PROFILE`   | `Any`                                                                                                            | `Setting`  | `xsjs_start.ps1`                                                   | The network profiles the firewall rule applies to.                                 |
| `ERROR_ACTION`       | `Stop`                                                                                                           | `Code`     | `xsjs_util.ps1`; `test_lint.ps1`                                   | Every PowerShell error terminates, so the `trap` in `_main` logs it.               |
| `PROGRESS_DISPLAY`   | `SilentlyContinue`                                                                                               | `Code`     | `xsjs_util.ps1`; `test_lint.ps1`; `xsjs_screenshot_wsl.py`         | Hides PowerShell's progress bars.                                                  |
| `TRANSPORT_SECURITY` | `Tls12`                                                                                                          | `Code`     | `xsjs_util.ps1`; `test_lint.ps1`                                   | Adds TLS 1.2 to what .NET offers for PowerShell's own HTTPS requests.              |
| `OUTPUT_WIDTH`       | `200` columns                                                                                                    | `Code`     | `xsjs_util.ps1`; `test_lint.ps1`                                   | How wide PowerShell formats objects before they are logged or shown.               |
| `TREE_INDENT`        | `4` spaces, and `2` more a level                                                                                 | `Code`     | `xsjs_status.ps1`                                                  | How status indents the task's process tree.                                        |
| `BYTE_ORDER`         | `EF BB BF`                                                                                                       | `Fixed`    | `test_lint.ps1`; `xsjs_start.ps1`                                  | The UTF-8 byte order mark.                                                         |
| `PROXY_KEY`          | `HKLM:\SYSTEM\CurrentControlSet\Services\PortProxy\v4tov4\tcp`                                                   | `Fixed`    | `xsjs_util.ps1`; `xsjs_status.ps1`                                 | Where Windows keeps `PROXY_REGISTRY`. Status lists every kind under `PortProxy`.   |
| `VERSION_KEY`        | `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion`                                                             | `Fixed`    | `xsjs_util.ps1`                                                    | Holds `UBR`, which `BUILD_REVISION` reads.                                         |
| `SHELL_NAME`         | `powershell.exe`                                                                                                 | `Fixed`    | `xsjs_screenshot_wsl.py` `_POWERSHELL_NAME`; `test_powershell.ps1` | Windows PowerShell 5.1, not `pwsh`.                                                |
| `SHELL_LOCATION`     | `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`                                                  | `Fixed`    | `xsjs_screenshot_wsl.py` `_POWERSHELL_PATH`                        | Used when `SHELL_NAME` isn't on WSL's `PATH`.                                      |
| `BROWSER_PATHS`      | Chrome under `ProgramFiles`, `ProgramFiles(x86)`, `LOCALAPPDATA`; Edge under `ProgramFiles(x86)`, `ProgramFiles` | `Fixed`    | `xsjs_screenshot_wsl.py` `_BROWSER_LOCATIONS`                      | Where the screenshot tool looks for a browser, in order. The first found is used.  |
| `ANALYZER_SOURCE`    | `PSGallery`                                                                                                      | `Fixed`    | `test_lint.ps1`                                                    | Where `test_lint.ps1` installs PSScriptAnalyzer from, for the current user.        |
| `PACKAGE_PROVIDER`   | `NuGet`                                                                                                          | `Fixed`    | `test_lint.ps1`                                                    | The package provider PSScriptAnalyzer's install needs.                             |
| `HIDDEN_CREDENTIAL`  | `USERNAME:PASSWORD`                                                                                              | `Protocol` | `i18n.psd1` `credential_hidden`                                    | What start's log shows in place of the credential.                                 |
| `DATE_FORMAT`        | `yyyy-MM-dd HH:mm:ss`                                                                                            | `Protocol` | `xsjs_util.ps1`                                                    | The time in `STARTED_LINE`.                                                        |
| `INSTALL_BANNER`     | `figlet -f bigmono9 xsjs`, then the copyright                                                                    | `Code`     | `xsjs_install.ps1` `$banner_`                                      | What install shows first.                                                          |

### 5.6 Certificates

| Identifier             | Value      | Kind       | Source                               | Meaning                                                             |
| ---------------------- | ---------- | ---------- | ------------------------------------ | ------------------------------------------------------------------- |
| `CERTIFICATE_LIFETIME` | `825` days | `Setting`  | `xsjs_util.ps1` `$certificate_days_` | How long a new certificate lasts. Apple devices refuse longer ones. |
| `KEY_ALGORITHM`        | `rsa:2048` | `Setting`  | `xsjs_start.ps1`                     | The key `openssl req -newkey` makes.                                |
| `FINGERPRINT_HASH`     | `sha256`   | `Protocol` | `xsjs_start.ps1`; `xsjs_util.ps1`    | The hash of `FINGERPRINT_TEXT`.                                     |

### 5.7 Timing

| Identifier           | Value          | Kind      | Source                                                                                                                        | Meaning                                                                             |
| -------------------- | -------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `WAIT_INTERVAL`      | `500` ms       | `Setting` | `xsjs_util.ps1`; `xsjs_start.ps1`                                                                                             | The pause between checks while a port frees, ttyd listens or ttyd stops.            |
| `WAIT_ATTEMPTS`      | `30`           | `Setting` | `xsjs_util.ps1`; `xsjs_start.ps1`                                                                                             | Checks before giving up: 15 s with `WAIT_INTERVAL`, as `ttyd_not_stopped` says.     |
| `WIRE_POLL`          | `0.05` s       | `Setting` | `test_wire.py` `_POLL_SECONDS`                                                                                                | The wire test's pause between looks for processes that should have ended.           |
| `WIRE_TIMEOUT`       | `120` s        | `Setting` | `test_wire.py` `_RUN_TIMEOUT_SECONDS`                                                                                         | The whole wire test's deadline.                                                     |
| `SCREENSHOT_POLL`    | `0.1` s        | `Setting` | `xsjs_screenshot.py` `_POLL_SECONDS`                                                                                          | The screenshot tool's pause between looks at the page or the port.                  |
| `SCREENSHOT_TIMEOUT` | `180` s        | `Setting` | `xsjs_screenshot.py` `_RUN_TIMEOUT_SECONDS`                                                                                   | A screenshot run's deadline once ttyd is built, covering Chrome's slow first start. |
| `SERVER_WAIT`        | `60` s         | `Setting` | `xsjs_screenshot.py` `_SERVER_WAIT_SECONDS`                                                                                   | How long the screenshot tool waits for ttyd, while Chrome gets `REFUSED_ERROR`.     |
| `STOP_WAIT`          | `5` s          | `Setting` | `test_wire.py` `_STOP_WAIT_SECONDS`; `xsjs_screenshot.py` `_STOP_WAIT_SECONDS`; `xsjs_screenshot_wsl.py` `_STOP_WAIT_SECONDS` | How long a tool waits for a process it ends before it kills it.                     |
| `BROWSER_POLL`       | `0.1` s        | `Setting` | `xsjs_screenshot_wsl.py` `_POLL_SECONDS`                                                                                      | The pause between looks for `PORT_FILE` and tries to remove the profile.            |
| `DEBUGGER_WAIT`      | `60` s         | `Setting` | `xsjs_screenshot_wsl.py` `_DEVTOOLS_WAIT_SECONDS`                                                                             | How long the tool waits for `PORT_FILE`. A new profile can take over 10 s.          |
| `REMOVAL_WAIT`       | `10` s         | `Setting` | `xsjs_screenshot_wsl.py` `_PROFILE_REMOVE_SECONDS`                                                                            | How long the tool retries removing the profile while Chrome's helpers exit.         |
| `HISTORY_EXPIRY`     | `24.hours.ago` | `Setting` | `archive.sh`                                                                                                                  | Reflog entries older than this go before `git gc` packs the archive.                |

### 5.8 Exit codes

| Identifier       | Value | Kind       | Source                                                           | Meaning                                                                     |
| ---------------- | ----- | ---------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `FAILURE_CODE`   | `1`   | `Protocol` | `xsjs_start.ps1` `trap`; `test_wire.py` `main`                   | A failure. A PowerShell script's `trap` logs it first.                      |
| `USAGE_CODE`     | `2`   | `Protocol` | `bootstrap.py`; `archive.sh`; `clean.sh`; `xsjs_screenshot.py`   | Wrong arguments, or no browser module for the platform.                     |
| `SIGNAL_BASE`    | `128` | `Protocol` | `test_wire.py` `signal_exit`; `xsjs_screenshot.py` `signal_exit` | A tool ended by SIGHUP or SIGTERM exits with this plus the signal's number. |
| `INTERRUPT_CODE` | `130` | `Protocol` | `test_wire.py` `main`; `xsjs_screenshot.py` `main`               | A tool ended by `^C` exits with `SIGNAL_BASE` plus SIGINT's 2.              |

### 5.9 Checks and style

| Identifier            | Value                                                     | Kind      | Source                                                                                               | Meaning                                                                      |
| --------------------- | --------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `LINE_WIDTH`          | `79` columns                                              | `Setting` | `pyproject.toml` `line-length`; `test_lint.ps1` `MaximumLineLength`; `settings.json` `editor.rulers` | The longest line for Python and PowerShell, and the editor's ruler.          |
| `FORMAT_PRESET`       | `CodeFormattingOTBS`                                      | `Setting` | `test_lint.ps1` `$preset_`                                                                           | PSScriptAnalyzer's formatting preset: the one true brace style.              |
| `LINT_GLOBS`          | `*.ps1`, `*.psm1`, `*.psd1`                               | `Layout`  | `test_lint.ps1` `$globs_`; `test_posix.py` `_POWERSHELL_GLOBS`                                       | The PowerShell files, under the top folder.                                  |
| `ENGLISH_PUNCTUATION` | `.,"'?:!()/`                                              | `Setting` | `test_posix.py` `_ENGLISH_PUNCT`                                                                     | What a comment below the header may hold, besides letters, digits and space. |
| `ALLOWED_CHARACTERS`  | U+00A9, U+00E9                                            | `Setting` | `test_posix.py` `_NON_ASCII_ALLOWED`                                                                 | The only characters beyond ASCII a file `REFORMAT_LIST` names may hold.      |
| `IGNORED_RULES`       | `E401`, `I001`                                            | `Tool`    | `pyproject.toml`                                                                                     | ruff rules turned off, as they reject `import a, b`.                         |
| `TYPE_CHECKING`       | `strict`                                                  | `Tool`    | `pyproject.toml`                                                                                     | pyright's mode.                                                              |
| `FORMATTER_COMMANDS`  | `mdformat --check`, `ruff format`, `shfmt --list --write` | `Code`    | `reformat.py` `_FORMATTERS`                                                                          | The formatter for `.md`, `.py` and `.sh` files. Markdown is only checked.    |

### 5.10 Page

| Identifier       | Value         | Kind   | Source                                      | Meaning                                                                    |
| ---------------- | ------------- | ------ | ------------------------------------------- | -------------------------------------------------------------------------- |
| `PAGE_TITLE`     | `xstation.js` | `Code` | `bootstrap.html`                            | The page's `title` element.                                                |
| `FONT_SIZE`      | `12px`        | `Code` | `bootstrap.html`                            | The page's one font size, in a monospace font.                             |
| `PAGE_SPACING`   | `8px`         | `Code` | `bootstrap.html`                            | The margins and gaps between the page's parts.                             |
| `INPUT_ROWS`     | `4`           | `Code` | `bootstrap.html`                            | The input's height in lines.                                               |
| `PREVIEW_LENGTH` | `40`          | `Code` | `bootstrap.html` `sendText`; `test_wire.py` | Characters of a refused line, or bytes sent, that a failure message shows. |

### 5.11 Screenshot

| Identifier          | Value                                                                                                  | Kind      | Source                                     | Meaning                                                                      |
| ------------------- | ------------------------------------------------------------------------------------------------------ | --------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| `VIEWPORT_WIDTH`    | `1280` px                                                                                              | `Setting` | `xsjs_screenshot.py` `_VIEWPORT_WIDTH_PX`  | The browser window's and the page's width.                                   |
| `VIEWPORT_HEIGHT`   | `720` px                                                                                               | `Setting` | `xsjs_screenshot.py` `_VIEWPORT_HEIGHT_PX` | The browser window's and the page's height.                                  |
| `SCALE_FACTOR`      | `1`                                                                                                    | `Setting` | `xsjs_screenshot.py` `viewport_set`        | Device pixels for each CSS pixel in the screenshot.                          |
| `ENTER_CODE`        | `13`                                                                                                   | `Fixed`   | `xsjs_screenshot.py` `_ENTER_KEY`          | The Windows virtual key code of Enter, which the tool presses.               |
| `REFUSED_ERROR`     | `net::ERR_CONNECTION_REFUSED`                                                                          | `Fixed`   | `xsjs_screenshot.py` `_REFUSED_ERROR_TEXT` | Chrome's error while ttyd isn't reachable yet. The tool retries on it alone. |
| `BROWSER_OPTIONS`   | `--headless=new --hide-scrollbars --no-default-browser-check --no-first-run --remote-debugging-port=0` | `Code`    | `xsjs_screenshot_wsl.py` `start`           | Chrome's options besides the profile, window size and first page.            |
| `TYPING_TEXT`       | `h\u00e9llo w\u00f6rld \u00a9 2026`                                                                    | `Test`    | `xsjs_screenshot.py` `_TYPING_DEFAULT`     | The line typed to the module's input unless `--typing` gives one.            |
| `SCREENSHOT_MODULE` | `update`                                                                                               | `Test`    | `xsjs_screenshot.py` `_MODULE_NAME`        | The module the tool puts and runs.                                           |
| `MODULE_ARGUMENTS`  | `--who demo 42`                                                                                        | `Test`    | `xsjs_screenshot.py` `_MODULE_ARGS`        | The words after the module's name.                                           |

### 5.12 Tests

| Identifier        | Value                                                       | Kind   | Source                                                 | Meaning                                                                                   |
| ----------------- | ----------------------------------------------------------- | ------ | ------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| `TEST_CREDENTIAL` | `user:pass`                                                 | `Test` | `test_wire.py` `_CREDENTIAL`                           | The credential the serve rung's second ttyd takes.                                        |
| `UNSERVED_PATH`   | `/other.js`                                                 | `Test` | `test_wire.py` `_MADE_UP_PATH`                         | A path ttyd doesn't serve, for `UNKNOWN_PATH`.                                            |
| `SAMPLE_TEXT`     | `na\u00efve \u65e5\u672c\u8a9e \U0001f600 \u00e9t\u00e9`    | `Test` | `test_wire.py` `_NON_ASCII_TEXT`                       | Characters of 2, 3 and 4 bytes, for arguments, output and errors.                         |
| `SPLIT_CHARACTER` | `\U0001f600`                                                | `Test` | `test_wire.py` `_NON_ASCII_SPLIT_CHARACTER`            | The character an `INPUT_MESSAGE` is split inside, 2 bytes in.                             |
| `BIG_LINES`       | `256`                                                       | `Test` | `test_wire.py` `_BIG_LINES`                            | Lines of `LINE_LIMIT` bytes in the big put: 1 MiB with their `LINE_FEED`.                 |
| `UNIT_LETTERS`    | `23`                                                        | `Test` | `test_wire.py` `_BIG_ASCII_PER_UNIT`                   | Random ASCII characters in each unit of the big put, before `WIDE_TEXT`.                  |
| `WIDE_TEXT`       | `\u00e9\u4e2d\U0001f600`                                    | `Test` | `test_wire.py` `_BIG_WIDE_TEXT`                        | The characters of 2, 3 and 4 bytes that end each unit.                                    |
| `LINE_COUNT`      | `100000`                                                    | `Test` | `test_wire.py` `_LINES_COUNT`                          | How many lines `lines.py` prints, from 1.                                                 |
| `CONTEXT_BYTES`   | `200`                                                       | `Test` | `test_wire.py` `_SHOWN_BYTES`                          | Bytes shown each side of where a transcript first differs.                                |
| `RUN_ARGUMENTS`   | `--who`, `two words`, `SAMPLE_TEXT`                         | `Test` | `test_wire.py` `_RUN_ARGS`                             | The arguments `report.py` runs with.                                                      |
| `ERROR_CASES`     | seven commands, each with its `error-line`                  | `Test` | `test_wire.py` `_ERRORS`                               | What the errors rung sends, and the error due for each.                                   |
| `UPDATE_LINE`     | `# updated by update.py`, then `LINE_FEED`                  | `Test` | `test_wire.py` `_UPDATE_LINE`                          | What `update.py` appends to the bootstrapper before `restart`.                            |
| `EXIT_EXAMPLE`    | `3`                                                         | `Test` | `test_wire.py`; `PLAN_OF_RECIORD.md`                   | The code the exit module exits with.                                                      |
| `SLEEP_SECONDS`   | `600` s                                                     | `Test` | `test_wire.py` `_SLEEPER_SOURCE`; `PLAN_OF_RECIORD.md` | How long a sleep module sleeps unless interrupted.                                        |
| `MODULE_SOURCES`  | exit, raise, report, sleep, input, update and lines modules | `Test` | `test_wire.py`                                         | The modules the rungs put, as Python source in `test_wire.py`.                            |
| `DIGEST_PREVIEW`  | `12`                                                        | `Code` | `test_wire.py`                                         | Hexadecimal digits of a SHA-256 that a rung's summary shows.                              |
| `MESSAGE_PREVIEW` | `60`                                                        | `Code` | `test_wire.py`                                         | Bytes of an unexpected ttyd message that a failure shows.                                 |
| `TEST_USER`       | `xstation-test`                                             | `Test` | `test_powershell.ps1` `$test_user_`                    | The user of the credential `test_powershell.ps1` starts HTTPS with.                       |
| `TEST_PASSWORD`   | a new GUID, 32 hexadecimal digits                           | `Test` | `test_powershell.ps1` `$test_credential_`              | The throwaway password of that credential.                                                |
| `LIFECYCLE_STEPS` | 13 steps after the lint                                     | `Test` | `test_powershell.ps1` `$lifecycle_`                    | Stop, install, start twice, soft stop, HTTPS start and full stop, each checked by status. |

### 5.13 Archive

| Identifier       | Value                     | Kind       | Source       | Meaning                                                                               |
| ---------------- | ------------------------- | ---------- | ------------ | ------------------------------------------------------------------------------------- |
| `BACKUP_FOLDER`  | `Backups`                 | `Setting`  | `archive.sh` | The folder in the home folder an archive goes to without a destination, if it exists. |
| `ARCHIVE_SUFFIX` | `.git.txz`                | `Protocol` | `archive.sh` | The end of `ARCHIVE_FILE`'s name.                                                     |
| `DATE_STAMP`     | `%Y-%m-%d`                | `Protocol` | `archive.sh` | The date in `ARCHIVE_FILE`'s name.                                                    |
| `DRIVE_TYPES`    | `v9fs`, `fuseblk`, `ntfs` | `Fixed`    | `archive.sh` | File systems taken for a Windows drive, where a restore sets `core.fileMode false`.   |

## 6 Settings file plan

6.1 Goal: `settings.json` at the top of the checkout holds every constant section 5 marks `Setting`.

6.1.1 PowerShell, Python, JavaScript and shell read it. No source keeps its own copy of a `Setting`.

6.2 `SETTINGS_FILE` version 1:

6.2.1 JSON (RFC 8259): one object, one member a line, sorted by key, indented by two spaces.

6.2.2 ASCII, so with no byte order mark, with LF line ends and a final LF.

6.2.3 Keys are section 5 identifiers, verbatim, so one spelling finds a setting in every language.

6.2.4 A value is a string, number, boolean or array of strings, in the unit section 5 gives.

6.2.5 A setting's unit never changes. A new unit needs a new identifier.

6.2.6 `SETTINGS_VERSION` holds the version. JSON allows no comments, so section 5 is the schema.

6.3 Reading:

6.3.1 A reader fails at once, naming the file and key, on a missing file, key or version, or a wrong type.

6.3.2 A reader takes only the keys it uses, by exact name. There are no defaults in code.

6.3.3 A change takes effect at the next run of each reader. `RUNNER_SCRIPT` keeps what start wrote.

6.3.4 Stop before changing a name, port or folder start gives Windows or Linux, or stop can't find it.

6.4 Each language:

6.4.1 PowerShell: `xsjs_util.ps1` parses `..\settings.json` with `ConvertFrom-Json`.

6.4.2 PowerShell: `xsjs_util_get_setting` throws on a missing key. `$port_` and the rest come from it.

6.4.3 PowerShell: `test_lint.ps1` reads `LINE_WIDTH` and `FORMAT_PRESET` in the same way.

6.4.4 Python: each tool sets its constants from `json.load` of the top's `settings.json`, after imports.

6.4.5 Python: `bootstrap.py` reads none, as none of its constants is a `Setting`. It stays standalone.

6.4.6 JavaScript: ttyd serves only the page, so start gives ttyd `-t TERMINAL_COLUMNS=80` and the like.

6.4.7 JavaScript: the page reads them from `PREFERENCES_MESSAGE` and sends `RESIZE_MESSAGE`.

6.4.8 JavaScript: `OPENING_MESSAGE` drops the size, and ttyd starts at its own default of 80 by 24.

6.4.9 The Python tests pass the same `-t` options to their ttyd, so the page runs as deployed.

6.4.10 Shell: `archive.sh` reads `BACKUP_FOLDER` and `HISTORY_EXPIRY` with `python3 -I -c` and `json`.

6.4.11 Shell: `jq` would be an apt package, which needs the maintainer's approval. `clean.sh` reads none.

6.5 What stays out:

6.5.1 Constants of every other kind: changing one changes a format, a layout, or a peer's behaviour.

6.5.2 `Tool` values, and copies other programs read in `pyproject.toml` and `.vscode/settings.json`.

6.5.3 A check compares each copy of `LINE_WIDTH` in those files with `settings.json`.

6.5.4 Text in `TEXT_TABLE`. The `15 s` in `ttyd_not_stopped` becomes a placeholder start fills.

6.6 Checks:

6.6.1 `test_posix.py` fails on a key that no source reads.

6.6.2 `comments_find` in `test_posix.py` needs a `.json` case, as it fails on an unknown extension.

6.6.3 Adding `settings.json` to `REFORMAT_LIST` needs the maintainer's permission.

6.7 Order of work. Each step leaves every test passing:

6.7.1 Add `settings.json` with the PowerShell settings; `xsjs_util.ps1` and `test_lint.ps1` read them.

6.7.2 Run `test_lint.ps1`. The maintainer runs `test_powershell.ps1` and `PLAN_OF_RECIORD.md`.

6.7.3 Move the Python settings. Run `test_posix.py`, pyright, `test_wire.py`, `xsjs_screenshot.py`.

6.7.4 Move the terminal size to ttyd's `-t` options and the page. Run both Python tests again.

6.7.5 Move `archive.sh`'s settings, then archive once into a scratch folder.

6.7.6 Add the checks in 6.6, and update the Lookup Accelerator.

6.8 Decisions for the maintainer:

6.8.1 Keys as the identifiers verbatim, as planned, or in camel case.

6.8.2 Whether test timeouts and sizes count as settings, as planned, or stay in each test.

6.8.3 Whether `archive.sh` may call `python3`. Its restore mode reads no settings and needs none.

6.8.4 Whether the page's size moves to `-t`, which adds a `RESIZE_MESSAGE` to each connection.

6.8.5 Whether `REFORMAT_LIST` folds into `settings.json` as an array of globs.

6.9 Risks:

6.9.1 A setting changed while running strands what start made, as stop looks it up by the new value.

6.9.2 The `-t` options lengthen `SERVER_COMMAND`, by which stop and status find ttyd.

6.10 The planned file, generated from section 5:

```json
{
  "ALLOWED_CHARACTERS": [
    "\u00a9",
    "\u00e9"
  ],
  "BACKUP_FOLDER": "Backups",
  "BATTERY_CONTINUE": true,
  "BATTERY_START": true,
  "BROWSER_POLL": 0.1,
  "CERTIFICATE_LIFETIME": 825,
  "CERTIFICATE_NAME": "_cached_cert.pem",
  "DEBUGGER_WAIT": 60,
  "ENGLISH_PUNCTUATION": ".,\"'?:!()/",
  "FIREWALL_PROFILE": "Any",
  "FORMAT_PRESET": "CodeFormattingOTBS",
  "HISTORY_EXPIRY": "24.hours.ago",
  "IMAGE_NAME": "xsjs_screenshot.png",
  "INSTALL_FOLDER": ".cache/xsjs",
  "INSTANCE_POLICY": "IgnoreNew",
  "INTERPRETER_NAME": "python3",
  "KEY_ALGORITHM": "rsa:2048",
  "KEY_NAME": "_cached_key.pem",
  "LINE_WIDTH": 79,
  "LINUX_DISTRIBUTION": "Ubuntu",
  "LOGON_TYPE": "Interactive",
  "LOG_NAME": "ttyd.log",
  "MODULES_FOLDER": "modules",
  "PUBLIC_PORT": 5768,
  "REMOVAL_WAIT": 10,
  "RULE_NAME": "xstation.js",
  "RUNNER_NAME": "serve.ps1",
  "RUN_LEVEL": "Limited",
  "SCALE_FACTOR": 1,
  "SCREENSHOT_POLL": 0.1,
  "SCREENSHOT_PORT": 7681,
  "SCREENSHOT_TIMEOUT": 180,
  "SERVER_CHECKOUT": "../ttyd",
  "SERVER_WAIT": 60,
  "SERVICE_PORT": 5769,
  "SETTINGS_VERSION": 1,
  "STATE_NAME": "xstation.js",
  "STOP_WAIT": 5,
  "TASK_NAME": "xstation.js",
  "TERMINAL_COLUMNS": 80,
  "TERMINAL_ROWS": 24,
  "TERMINAL_TYPE": "dumb",
  "VIEWPORT_HEIGHT": 720,
  "VIEWPORT_WIDTH": 1280,
  "WAIT_ATTEMPTS": 30,
  "WAIT_INTERVAL": 500,
  "WIRE_POLL": 0.05,
  "WIRE_TIMEOUT": 120
}
```

## 7 Open items

7.1 `COMMAND_SESSION` carries no version. A version word in `banner-line` would let a page check it.

7.2 `banner-line`'s paths are unquoted, so a path holding a space and `sha256` can read two ways.

7.3 The page sends typed or pasted control bytes as they are. `QUIT_CHARACTER` ends the session.

7.4 The page's `END_CHARACTER` button leaves the text in the input unsent.

7.5 Deployment runs Ubuntu's ttyd 1.7.7. The tests run `../ttyd`, built from its newer source.

## 8 References

8.1 BCP 14: RFC 2119 and RFC 8174, the requirement key words.

8.2 RFC 3629, UTF-8. RFC 4648, base64. RFC 8259, JSON.

8.3 RFC 5234, ABNF. RFC 7405, case sensitive strings in ABNF.

8.4 RFC 6455, the WebSocket protocol. RFC 7617, the Basic HTTP authentication scheme.

8.5 RFC 9112, HTTP/1.1. RFC 3986, URI syntax.

8.6 POSIX.1-2024, the General Terminal Interface, for `TERMINAL_DISCIPLINE`.

8.7 ttyd's source, `https://github.com/tsl0922/ttyd`: `server.h`, `protocol.c`, `http.c`, `pty.c`.

8.8 Chrome DevTools Protocol, `https://chromedevtools.github.io/devtools-protocol/`.
