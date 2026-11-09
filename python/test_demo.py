#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The demo test, which proves the engine page is ready for a person to view. It
# serves fresh debug roots in build/test_demo-*/ through the functions of
# xsjs_serve.py, as the maintainer serves one, and drives chrome-headless-shell
# over DevTools as a person would: clicks and keys are input events, and every
# reading is of the page's elements. The analyst is a scripted table, and no
# real AI provider is contacted. Each rung has a timer and a label, smoke-test
# or test-all, and a mislabel fails the run. One root must hold no unexpected
# failure, one outside debug mode must record nothing, and in a test-all run
# one calls every tool the AI is given in one conversation. Each audit must
# show the prompt and the log sent once per load or compaction, every other
# model call sending only what is new. build/test_demo/, emptied at each run,
# keeps PNGs of the states, server.txt, and the audits after a failed rung or
# under --debug. The roots go once the run passes. With --hold a failed rung
# leaves the page and keeps ttyd serving its root for a person, printing the
# address, until ctrl C. Its timers and texts are its gold, python.test_demo.

import argparse, contextlib, fnmatch, json, os, re, shutil, signal, sqlite3
import sys, tempfile, time, types
from collections.abc import Callable
from typing import Any, NamedTuple, TYPE_CHECKING, cast

# Only type checks import these here, as the bytecode's place is set below.
if TYPE_CHECKING:
    import devtools, xsjs_serve

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: the page, the run's roots, the PNGs and bytecode.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The id of this driver's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_demo"

# The start of the name of the directory each run makes and keeps its roots in.
_WORK_PREFIX = "test_demo-"

# The name of the root in that directory, and of the root in the label book.
_ROOT_NAME = "root"

# The name of the root outside debug mode there and in the label book.
_PLAIN_NAME = "plain"

# The name of the root of the gold's table of every tool.
_TOOLS_NAME = "tools"

# The directory of the PNGs of the states and the logs, kept after the run.
_PICTURE_PATH = os.path.join(_BUILD_PATH, "test_demo")

# The file the log of the plain rung's ttyd goes to, kept after the run.
_SERVER_PATH = os.path.join(_PICTURE_PATH, "server.txt")

# The start of the name of the PNG of a failed rung.
_FAILED_PREFIX = "failed_"

# The name `argparse` shows, as `sys.argv` may be empty.
_PROGRAM_NAME = "test_demo.py"

# The label of the important rungs that fit in 3 minutes.
_SMOKE_TEST = "smoke-test"

# The label of every other rung.
_TEST_ALL = "test-all"

# The exit code of a run with a failed check.
_EXIT_FAILED = 1

# The exit code of a run that `^C` ended.
_EXIT_INTERRUPTED = 130

# A shell's exit code for a signal is this plus the signal's number.
_SIGNAL_BASE = 128

# The signals `xsjs_serve.TtydServer` unblocks in ttyd, held while it starts.
_STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)

# The page the browser leaves the engine page for.
_BLANK_URL = "about:blank"

# The directory of the running processes.
_PROC_PATH = "/proc"

# The extension of a database file under the root.
_DB_EXTENSION = ".sqlite"

# The statement that reads a value held in a database file.
_NOTE_SELECT = "SELECT data FROM _kv WHERE key = ?"

# The DevTools method of a keyboard event.
_KEY_METHOD = "Input.dispatchKeyEvent"

# The DevTools method of a mouse event.
_MOUSE_METHOD = "Input.dispatchMouseEvent"

# The fields of the Enter key in a keyboard event.
_ENTER_KEY = {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13}

# The text the Enter key types.
_ENTER_TEXT = "\r"

# The bit of the ctrl key in a keyboard event's modifiers.
_CTRL_MODIFIER = 2

# The digit of ctrl that toggles the console view.
_CONSOLE_DIGIT = 0

# The digit of ctrl that toggles the overlay of tty 1, the audit's end.
_OVERLAY_DIGIT = 1

# The line of every other digit of ctrl, the one that never holds that digit.
_KEY_TYPE = "ui.control_key"

# The root's audit, and its copy beside the PNGs.
_AUDIT_NAME = "_audit.txt"
_AUDIT_COPY = os.path.join(_PICTURE_PATH, "audit.txt")

# The copy of the audit of the root of every tool, before its deliberate end.
_TOOLS_COPY = os.path.join(_PICTURE_PATH, "audit_tools.txt")

# The tools the AI is given, as `tools/list` returns them, by server.
_TOOLS_PATH = os.path.join(_CHECKOUT_PATH, "API", "mcp", "tools.json")

# The seed's system prompt, a document whose text the agent sends.
_PROMPT_PATH = os.path.join(_PYTHON_PATH, "seed", "prompt.json")

# The scripted table a root seeds its store with, under that root.
_TABLE_PATH = os.path.join("python", "seed", "provider_script.json")

# The node of the table of every tool that takes each person's input.
_MENU_NODE = "menu"

# The id of the call of a chain's tool of an index, as the table names it.
_CALL_ID = "call_{0}_{1}"

# What joins a server's prefix and a tool's name in the name the AI is given.
_PREFIX_MARK = "_"

# The field of a model call that holds its tool list.
_TOOLS_FIELD = "tools"

# The end of the URL of a model call, the Responses API's.
_MODEL_PATH = "/responses"

# The field of a model call that chains it to the response before it.
_CHAIN_FIELD = "previous_response_id"

# The roles of a system message, the person's, the model's reply, a result.
_SYSTEM_ROLE = "system"
_USER_ROLE = "user"
_REPLY_ROLE = "assistant"
_TOOL_ROLE = "tool"

# The types of the model's call of a function and of the output answering it.
_CALL_TYPE = "function_call"
_OUTPUT_TYPE = "function_call_output"

# The line that carries a stored turn to the server.
_TURN_TYPE = "turn.append"

# The lanes of the conversation: the model's calls, its replies, the commits.
_REQUEST_LANE = "ai to http"
_REPLY_LANE = "http to ai"
_COMMIT_LANE = "ai to server"
_CONVERSATION_LANES = (_REQUEST_LANE, _REPLY_LANE, _COMMIT_LANE)

# The commit that stores a conversation's system prompt.
_PROMPT_TYPE = "turn.prompt"

# A start heading of the engine, its process's id captured.
_START_PATTERN = re.compile(
    r"^==== engine started, .*, process (\d+) ====$", re.M
)

# The line of a database's dump that counts what it does not show, its turns.
_HIDDEN_PATTERN = re.compile(r"turns: (\d+),")

# The heading of each start of the engine role in the audit.
_ENGINE_START = "==== engine started, "

# The labels of the notes that only sleeps make, the page threads'.
_SLEEP_LABELS = ("note of ui", "note of ai")

# The text that follows a line's JSON in its entry when it carries blobs.
_BLOBS_PATTERN = re.compile(r"\n\[blobs omitted: \d+\]")

# A document listed in a dump: its database and id, then its version.
_DOCUMENT_PATTERN = re.compile(r"^      (/[^/\s]+/[^/\s]+)/\d+$", re.MULTILINE)

# The page as a person sees it, or its fault screen alone, as one JSON value.
_STATE_SCRIPT = r"""(() => {
  const fault = document.querySelector("body > pre");
  if (fault !== null) {
    return { fault: fault.textContent };
  }
  const place = (element) => {
    const box = element.getBoundingClientRect();
    return {
      x: box.left + box.width / 2,
      y: box.top + box.height / 2,
      shown: box.width > 0 && box.height > 0,
    };
  };
  const input = document.querySelector("#input");
  const permit = document.querySelector("#permit");
  const terminal = document.querySelector("#debug .xterm");
  const rows = document.querySelector("#debug .xterm-rows");
  const overlay = document.querySelector("#overlays pre");
  const image = document.querySelector("#image");
  const pixels = image
    .getContext("2d")
    .getImageData(0, 0, image.width, image.height).data;
  const colours = new Set();
  for (let at = 0; at < pixels.length; at += 4) {
    colours.add(pixels.subarray(at, at + 4).join(" "));
  }
  return {
    fault: null,
    subtitle: document.querySelector("#subtitle").textContent,
    image_hidden: image.hidden,
    image_width: image.width,
    image_height: image.height,
    image_colours: [...colours],
    input: {
      ...place(input),
      disabled: input.disabled,
      focused: document.activeElement === input,
    },
    permit_texts: Array.from(
      permit.querySelectorAll("p"),
      (text) => text.textContent,
    ),
    buttons: Array.from(permit.querySelectorAll("button"), (button) => ({
      ...place(button),
      text: button.textContent,
    })),
    console_shown: terminal !== null && place(terminal).shown,
    rows:
      rows === null
        ? []
        : Array.from(rows.children, (row) => row.textContent.trimEnd()),
    overlay_lines:
      overlay !== null && place(overlay).shown
        ? overlay.textContent.split("\n")
        : [],
    overlay_text: overlay === null ? "" : overlay.textContent,
  };
})()
"""

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


# A model call of an audit: its start, its line, its body and its reply's body.
class ModelCall(NamedTuple):
    start: int
    number: int
    body: dict[str, Any]
    reply: dict[str, Any] | None


# A rung's time limit, which fails loud once it has passed.
class RungTimer:
    # Starts the rung's time.
    def __init__(self, rung: str, seconds: float) -> None:
        self.rung = rung
        self.seconds = seconds
        self.end = time.monotonic() + seconds

    # Returns the seconds left, failing the rung once there are none.
    def seconds_left(self, what: str) -> float:
        left = self.end - time.monotonic()
        if left <= 0:
            raise CheckFailed(
                f"the rung {self.rung} ran out of its {self.seconds:g} s"
                f" waiting for {what}"
            )
        return left


# The rung that runs, its timer and start, the labels, and each rung's line.
class RungLog:
    # Starts on the browser, before any rung, checking the category's labels.
    def __init__(self, chosen: str) -> None:
        import category

        self.book = category.LabelBook(chosen)
        self.rung = "browser"
        self.timer = RungTimer(self.rung, gold_value("rung_seconds"))
        self.started = time.monotonic()
        self.client: devtools.ProtocolClient | None = None

    # Has each rung's timer from now on bound the client's DevTools waits.
    def client_bind(self, client: devtools.ProtocolClient) -> None:
        self.client = client
        client.deadline_set(self.timer.end)

    # Starts a timer of the seconds for the rung named, bounding DevTools too.
    def timer_start(self, seconds: float) -> None:
        self.timer = RungTimer(self.rung, seconds)
        client = cast("devtools.ProtocolClient", self.client)
        client.deadline_set(self.timer.end)

    # Gives what follows a failed rung a timer, the rung's name kept.
    def timer_renew(self) -> None:
        self.timer_start(gold_value("rung_seconds"))

    # Prints a line after the name of the rung that runs, under `--verbose`.
    def line_print(self, text: str) -> None:
        import switches

        if switches.verbose:
            print(f"{self.rung}: {text}", flush=True)

    # Runs a rung under its timer, the gold's `rung_seconds` unless given.
    def rung_run(
        self,
        rung: str,
        label: str,
        check: Callable[[], str],
        seconds: float | None = None,
    ) -> None:
        if not self.book.rung_enter(rung, label):
            return
        self.rung = rung
        self.started = time.monotonic()
        self.timer_start(
            gold_value("rung_seconds") if seconds is None else seconds
        )
        summary = check()
        seconds = time.monotonic() - self.started
        self.line_print(f"{summary} ({label}, {seconds:.3f} s)")


# The browser, the root and the ttyd of the run, and what a person does.
class DemoRun:
    # Takes the browser, log, settings, roots' directory and plain rung's log.
    def __init__(
        self,
        browser: devtools.Browser,
        log: RungLog,
        values: dict[str, Any],
        work: str,
        server_fd: int,
    ) -> None:
        self.browser = browser
        self.log = log
        self.values = values
        self.work = work
        self.server_fd = server_fd
        self.root = os.path.join(work, _ROOT_NAME)
        self.bootstrap = self.bootstrap_path(self.root)
        # Where a failure copies the audit of the root that runs.
        self.audit_path = _AUDIT_COPY
        # The built page, which both roots copy, once the served rung built it.
        self.page: str | None = None
        self.ttyd: xsjs_serve.TtydServer | None = None
        # The loads of the page, each a start of the engine in the audit.
        self.loads = 0

    # The `bootstrap.py` of a root, which ttyd's children run.
    def bootstrap_path(self, root: str) -> str:
        script: str = self.values["powershell"]["bootstrap_script"]
        return os.path.join(root, "python", script)

    # Starts ttyd on a root, a stop signal waiting until `self.ttyd` is set.
    def server_start(self, root: str, log_fd: int) -> xsjs_serve.TtydServer:
        import xsjs_serve

        held = signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
        try:
            self.ttyd = xsjs_serve.TtydServer(self.values, root, 0, log_fd)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, held)
        return self.ttyd

    # Sleeps one poll, failing the rung once it has run out of its seconds.
    def poll_sleep(self, what: str) -> None:
        poll: float = gold_value("poll_seconds")
        time.sleep(min(poll, self.log.timer.seconds_left(what)))

    # Reads the page, failing at once on its fault screen.
    def state_read(self) -> dict[str, Any]:
        state = cast(
            dict[str, Any], self.browser.script_evaluate(_STATE_SCRIPT)
        )
        if state["fault"] is not None:
            raise CheckFailed(f"the page faulted: {state['fault']}")
        return state

    # Returns the page's state once `test` holds of it.
    def state_wait(
        self, what: str, test: Callable[[dict[str, Any]], bool]
    ) -> dict[str, Any]:
        while True:
            state = self.state_read()
            if test(state):
                return state
            self.poll_sleep(f"{what}, the page being {state}")

    # Waits for the text in the band with the box enabled.
    def band_wait(self, text: str) -> None:
        self.state_wait(
            f"{text!r} in the band with the box enabled",
            lambda state: (
                state["subtitle"] == text and not state["input"]["disabled"]
            ),
        )

    # Presses and releases a key, `text` being what it types, if anything.
    def key_press(self, fields: dict[str, Any], text: str) -> None:
        client = self.browser.client_get()
        down = {"type": "keyDown", "text": text} if text else {}
        client.method_call(
            _KEY_METHOD, {"type": "rawKeyDown", **fields, **down}
        )
        client.method_call(_KEY_METHOD, {**fields, "type": "keyUp"})

    # Types each character of the text, then Enter, at the focus.
    def line_type(self, text: str) -> None:
        for character in text:
            self.key_press({"key": character}, character)
        self.key_press(_ENTER_KEY, _ENTER_TEXT)

    # Presses ctrl and a digit.
    def control_press(self, digit: int) -> None:
        character = str(digit)
        fields = {
            "key": character,
            "code": f"Digit{digit}",
            "windowsVirtualKeyCode": ord(character),
            "modifiers": _CTRL_MODIFIER,
        }
        self.key_press(fields, "")

    # Clicks the left button at a point of the viewport.
    def mouse_click(self, x: float, y: float) -> None:
        client = self.browser.client_get()
        for kind in ("mousePressed", "mouseReleased"):
            client.method_call(
                _MOUSE_METHOD,
                {
                    "type": kind,
                    "x": x,
                    "y": y,
                    "button": "left",
                    "clickCount": 1,
                },
            )

    # Clicks the box once in a run, as each turn's end gives it the focus back.
    def box_click(self) -> None:
        box: dict[str, Any] = self.state_read()["input"]
        self.mouse_click(box["x"], box["y"])

    # Saves a PNG of the page under the name and returns its path.
    def picture_save(self, name: str) -> str:
        path = os.path.join(_PICTURE_PATH, name + ".png")
        self.browser.screenshot_save(path)
        return path

    # Saves the failed rung's PNG and audit, and when asked serves the root.
    def failure_take(self, failure: Exception, hold: bool) -> None:
        log = self.log
        log.timer_renew()
        # A run that failed before the server started has no audit to copy.
        if os.path.exists(os.path.join(self.root, _AUDIT_NAME)):
            audit_copy(self.root, self.audit_path)
        self.picture_save(_FAILED_PREFIX + log.rung.replace(" ", "_"))
        if hold and self.ttyd is not None:
            print(f"error: {log.rung}: {failure}", file=sys.stderr, flush=True)
            self.browser.page_open(_BLANK_URL)
            print(self.ttyd.address_get(), flush=True)
            self.ttyd.signal_wait()

    # Stops ttyd when no rung has, as after a failure.
    def server_end(self) -> None:
        if self.ttyd is not None:
            self.ttyd.server_stop()


# A value of this driver's gold, `python.test_demo` of the test settings.
def gold_value(name: str) -> Any:
    import harness

    return harness.gold_get(f"{_GOLD_ID}.{name}")


# Returns the parent's pid, the second field after the name in brackets.
def process_parent(pid: int) -> int:
    with open(f"{_PROC_PATH}/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# The words of a process's command line, none once it has ended.
def cmdline_read(pid: int) -> list[bytes]:
    with open(f"{_PROC_PATH}/{pid}/cmdline", "rb") as file:
        return file.read().split(b"\0")[:-1]


# The pids of ttyd's children that run the root's `bootstrap.py`.
def programs_find(ttyd_pid: int, bootstrap: str) -> list[int]:
    pids: list[int] = []
    for name in os.listdir(_PROC_PATH):
        if not name.isdigit():
            continue
        pid = int(name)
        # A process can end between the listing and the reads.
        with contextlib.suppress(FileNotFoundError, ProcessLookupError):
            if process_parent(
                pid
            ) == ttyd_pid and bootstrap.encode() in cmdline_read(pid):
                pids.append(pid)
    return pids


# A value in the server's database file, None until its row comes.
def value_read(root: str, db: str, key: str) -> bytes | None:
    path = os.path.join(root, db + _DB_EXTENSION)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    with contextlib.closing(connection):
        row = connection.execute(_NOTE_SELECT, (key,)).fetchone()
    return None if row is None else cast(bytes, row[0])


# Copies the root's audit beside the PNGs, to the path given.
def audit_copy(root: str, path: str) -> None:
    shutil.copyfile(os.path.join(root, _AUDIT_NAME), path)


# The entries of a root's audit, each line made whole by `audit_read`.
def entries_whole(root: str) -> list[Any]:
    import audit_read

    return audit_read.entries_parse(
        audit_read.document_read(os.path.join(root, _AUDIT_NAME))
    )


# Waits for each request of the root's audit to be answered, then checks it.
def failures_check(run: DemoRun, root: str) -> int:
    import audit_read

    while True:
        entries = entries_whole(root)
        opened = audit_read.requests_open(entries)
        if not opened:
            break
        run.poll_sleep(f"the replies of the audit's requests: {opened}")
    try:
        audit_read.failure_check(entries)
    except audit_read.AuditFailed as failure:
        raise CheckFailed(f"the audit of {root}: {failure}") from failure
    return len(entries)


# The parameters of a root of this run, its debug mode as given.
def parameters_make(debug: bool) -> dict[str, bool]:
    import switches

    return {
        **switches.switches_get(),
        "debug": debug,
        "verbose": gold_value("root_verbose"),
    }


# Leaves the page, waits for the end of the programs under ttyd, returns them.
def page_leave(
    run: DemoRun, ttyd: xsjs_serve.TtydServer, bootstrap: str
) -> list[int]:
    programs = programs_find(ttyd.pid, bootstrap)
    if not programs:
        raise CheckFailed(f"no child of ttyd runs {bootstrap}")
    run.browser.page_open(_BLANK_URL)
    while programs_find(ttyd.pid, bootstrap):
        run.poll_sleep(f"the end of {bootstrap} under ttyd")
    return programs


# Stops ttyd, leaving no failure to stop it again, and checks its exit code.
def server_finish(run: DemoRun, ttyd: xsjs_serve.TtydServer) -> int:
    run.ttyd = None
    code = ttyd.server_stop()
    due: int = gold_value("ttyd_code")
    if code != due:
        raise CheckFailed(f"ttyd stopped with code {code}, not {due}")
    return code


# Waits for each fragment in the log of the plain rung's ttyd, in any order.
def fragments_wait(run: DemoRun, fragments: list[str]) -> None:
    while True:
        with open(_SERVER_PATH, "rb") as file:
            text = file.read()
        missing = [
            fragment for fragment in fragments if fragment.encode() not in text
        ]
        if not missing:
            return
        run.poll_sleep(f"{missing} in {_SERVER_PATH}, holding {text!r}")


# The line of a line entry's body, which is its JSON, then its blobs counted.
def body_line(entry: Any) -> dict[str, Any]:
    try:
        line, end = json.JSONDecoder().raw_decode(entry.body)
    except json.JSONDecodeError as error:
        raise CheckFailed(
            f"the entry {entry.label} at {entry.time} holds no JSON:"
            f" {entry.body!r}"
        ) from error
    rest = entry.body[end:]
    if rest and _BLOBS_PATTERN.fullmatch(rest) is None:
        raise CheckFailed(
            f"the entry {entry.label} at {entry.time} ends {rest!r}"
        )
    return cast(dict[str, Any], line)


# Whether an entry fits a row of the gold: its label, type or words, fragment.
def entry_fits(entry: Any, row: dict[str, str]) -> bool:
    if entry.label != row["label"]:
        return False
    if "type" in row and body_line(entry)["0"].get("type") != row["type"]:
        return False
    if "words" in row and row["words"] not in entry.body:
        return False
    return row.get("fragment", "") in entry.body


# The bodies of the entries that fit the rows in their order, else None.
def entries_ordered(root: str, rows: list[dict[str, str]]) -> list[str] | None:
    import audit

    bodies: list[str] = []
    entries = iter(audit.entries_read(root))
    for row in rows:
        fitting = (entry for entry in entries if entry_fits(entry, row))
        entry = next(fitting, None)
        if entry is None:
            return None
        bodies.append(entry.body)
    return bodies


# Types a number and waits for the analyst's text of it in the band.
def choice_take(run: DemoRun, number: str) -> str:
    text: str = gold_value(f"choices.{number}")
    run.line_type(number)
    run.band_wait(text)
    return text


# The page builds, the root is made, ttyd answers and the first render shows.
def rung_served(run: DemoRun) -> str:
    import xsjs_serve

    run.page = xsjs_serve.page_ready(run.values)
    parameters = parameters_make(gold_value("root_debug"))
    xsjs_serve.root_make(run.values, run.page, run.root, parameters, True)
    ttyd = run.server_start(run.root, sys.stderr.fileno())
    address = ttyd.address_get()
    run.browser.page_open(address)
    run.loads += 1
    remark: str = gold_value("remark")
    run.band_wait(remark)
    size: int = gold_value("picture_size")
    colours: list[str] = gold_value("picture_colours")
    state = run.state_read()
    picture = (
        state["image_hidden"],
        state["image_width"],
        state["image_height"],
        state["image_colours"],
    )
    if picture != (False, size, size, colours):
        raise CheckFailed(
            f"the picture's hidden, width, height and colours are {picture},"
            f" where it should show, {size} by {size}, all of {colours}"
        )
    png = run.picture_save("served")
    return (
        f"{address} loaded and its first render shows {remark!r} in the band,"
        f" the box enabled and the picture shown, {size} by {size}, all of"
        f" {colours}; PNG {png}"
    )


# A second load at once comes up on the files the first load's worker held.
def rung_reload(run: DemoRun) -> str:
    address = cast("xsjs_serve.TtydServer", run.ttyd).address_get()
    remark: str = gold_value("remark")
    run.browser.page_open(address)
    run.loads += 1
    run.band_wait(remark)
    return (
        f"{address} loaded again at once and its first render shows"
        f" {remark!r} in the band, the box enabled"
    )


# Clicks the box, and typing 1 ends with the analyst's first text in the band.
def rung_choice_render(run: DemoRun) -> str:
    run.box_click()
    text = choice_take(run, "1")
    # The table's render names no image, so the first one hides the picture.
    if not run.state_read()["image_hidden"]:
        raise CheckFailed("the picture shows after a render that names none")
    png = run.picture_save("choice_1")
    return (
        f"typing 1 ended with {text!r} in the band, the picture hidden;"
        f" PNG {png}"
    )


# Typing 3 asks the permit, and Accept runs the command in dash in view.
def rung_choice_console(run: DemoRun) -> str:
    permit: str = gold_value("permit_text")
    labels: list[str] = gold_value("buttons")
    prompt: str = gold_value("console_prompt")
    output: str = gold_value("console_output")
    text: str = gold_value("choices.3")
    run.line_type("3")
    state = run.state_wait(
        f"the permit text {permit!r} and the buttons {labels}",
        lambda state: (
            state["permit_texts"] == [permit]
            and [button["text"] for button in state["buttons"]] == labels
        ),
    )
    # Accept comes first, as in the gold's buttons.
    accept: dict[str, Any] = state["buttons"][0]
    run.mouse_click(accept["x"], accept["y"])
    run.state_wait(
        "the console view shown", lambda state: state["console_shown"]
    )
    run.state_wait(
        f"dash's prompt {prompt!r} and the row {output!r}",
        lambda state: (
            output in state["rows"]
            and any(row.startswith(prompt) for row in state["rows"])
        ),
    )
    run.band_wait(text)
    png = run.picture_save("choice_3")
    return (
        f"typing 3 showed {permit!r} with the buttons {labels}; Accept showed"
        f" the console view, whose rows hold {prompt!r} and {output!r}, and"
        f" {text!r} ended in the band; PNG {png}"
    )


# Types what the table does not hold and waits for the box to come back.
def input_refuse(run: DemoRun, line: str) -> None:
    text: str = gold_value("otherwise")
    run.line_type(line)
    run.state_wait(
        f"{text!r} in the band after {line!r}, the box enabled and focused",
        lambda state: (
            state["subtitle"] == text
            and not state["input"]["disabled"]
            and state["input"]["focused"]
        ),
    )


# Each input the table does not hold is answered, and a choice then still is.
def rung_refused(run: DemoRun) -> str:
    inputs: list[str] = gold_value("bad_inputs")
    for line in inputs:
        input_refuse(run, line)
    # Not choice 2, whose rung would then find its text in the band at once.
    text = choice_take(run, "1")
    return (
        f"typing each of {inputs} ended with the analyst's answer in the"
        " band, the box enabled and focused, and typing 1 then ended with"
        f" {text!r}"
    )


# Typing 2 ends with its text, and the server's database holds the note.
def rung_choice_note(run: DemoRun) -> str:
    text = choice_take(run, "2")
    note: str = gold_value("note_text")
    db, key = gold_value("note_db"), gold_value("note_key")
    while (value := value_read(run.root, db, key)) is None:
        run.poll_sleep("the note's row in the server's database")
    if value != note.encode():
        raise CheckFailed(
            f"the server's database holds the note {value!r}, not {note!r}"
        )
    return (
        f"typing 2 ended with {text!r} in the band, and the server's database"
        f" file holds the note {note!r}"
    )


# ctrl 0 hides and shows the view, a command runs in it, ctrl 0 hides it again.
def rung_console(run: DemoRun) -> str:
    command: str = gold_value("hello_command")
    output: str = gold_value("hello_output")
    run.control_press(_CONSOLE_DIGIT)
    run.state_wait(
        "the console view hidden", lambda state: not state["console_shown"]
    )
    run.control_press(_CONSOLE_DIGIT)
    run.state_wait(
        "the console view shown again", lambda state: state["console_shown"]
    )
    run.line_type(command)
    run.state_wait(
        f"the row {output!r}", lambda state: output in state["rows"]
    )
    png = run.picture_save("console")
    run.control_press(_CONSOLE_DIGIT)
    run.state_wait(
        "the console view hidden and the box focused",
        lambda state: not state["console_shown"] and state["input"]["focused"],
    )
    return (
        f"ctrl 0 hid the view and showed it again, {command!r} typed in its"
        f" terminal showed the row {output!r}, and ctrl 0 hid it, the box"
        f" taking the focus; PNG {png}"
    )


# ctrl 1 shows the audit's end with the last turn, then hides and empties it.
def rung_overlay(run: DemoRun) -> str:
    fragments: list[str] = gold_value("overlay_fragments")
    run.control_press(_OVERLAY_DIGIT)
    state = run.state_wait(
        f"the audit's end on the overlay, holding {fragments}",
        lambda state: all(
            any(fragment in line for line in state["overlay_lines"])
            for fragment in fragments
        ),
    )
    png = run.picture_save("overlay")
    run.control_press(_OVERLAY_DIGIT)
    run.state_wait(
        "the overlay hidden and holding no text",
        lambda state: (
            not state["overlay_lines"] and state["overlay_text"] == ""
        ),
    )
    return (
        f"ctrl 1 showed the audit's end, {len(state['overlay_lines'])} lines"
        f" holding {fragments}, and hid it, its text gone; PNG {png}"
    )


# After a load the prompt is not stored again, and goes once with the log.
def rung_prompt_kept(run: DemoRun) -> str:
    load = entries_whole(run.root)[-1].start
    rung_reload(run)
    line: str = gold_value("bad_inputs")[0]
    input_refuse(run, line)
    entries, calls = calls_wait(run, load)
    started, chained = conversation_check(entries, calls)
    return (
        f"a new load answered {line!r} with the log restored: one commit"
        f" stored the prompt before the first of the {len(calls)} model"
        f" calls, each listing every tool, the {started} chains' first calls"
        f" sent it once, as their first item, the {chained} chained calls"
        " only their new items, each reply finding its context cached, and"
        " the lanes wrote the prompt once"
    )


# Typing 0 ends with its answer, and the audit holds both sides' dumps.
def rung_dump(run: DemoRun) -> str:
    text: str = gold_value("choices.0")
    run.line_type("0")
    run.state_wait(
        f"{text!r} in the band, the box enabled and focused",
        lambda state: (
            state["subtitle"] == text
            and not state["input"]["disabled"]
            and state["input"]["focused"]
        ),
    )
    rows: list[dict[str, str]] = gold_value("dump_entries")
    while (bodies := entries_ordered(run.root, rows)) is None:
        run.poll_sleep(f"the audit's entries {rows} of the input 0")
    browser, server = bodies[0], bodies[1]
    if browser != server:
        raise CheckFailed(
            f"the browser's dump {browser!r} differs from the server's"
            f" {server!r}"
        )
    fragments: list[str] = gold_value("dump_fragments")
    missing = [fragment for fragment in fragments if fragment not in browser]
    if missing:
        raise CheckFailed(f"the dumps lack {missing}: {browser!r}")
    documents = _DOCUMENT_PATTERN.findall(browser)
    if len(documents) != len(set(documents)):
        raise CheckFailed(f"the dumps list an older version: {documents}")
    return (
        f"typing 0 ended with {text!r} in the band, the box enabled and"
        f" focused, and the audit holds the input's {len(rows)} entries in"
        f" order, the two dumps the same text, holding {fragments}, and"
        f" {len(documents)} documents each of its current version alone"
    )


# The audit holds the gold's table, no line of its own and notes of sleeps.
def rung_audit(run: DemoRun) -> str:
    import audit

    rows: list[dict[str, str]] = gold_value("audit")
    while missing := [
        row
        for row in rows
        if not any(
            entry_fits(entry, row) for entry in audit.entries_read(run.root)
        )
    ]:
        run.poll_sleep(f"the audit's entries of {missing}")
    entries = audit.entries_read(run.root)
    sleep: str = gold_value("sleep_note")
    own_wake: str = gold_value("audit_wake_note")
    for entry in entries:
        if entry.label in _SLEEP_LABELS:
            if not entry.body.startswith(sleep):
                raise CheckFailed(f"a note is not of a sleep: {entry}")
            if own_wake in entry.body:
                raise CheckFailed(f"a note is of the audit's own: {entry}")
        elif entry.label.startswith("note of ") or " to " not in entry.label:
            continue
        else:
            line = body_line(entry)
            line_type = str(line["0"].get("type"))
            if line_type.startswith("audit."):
                raise CheckFailed(f"the audit records its own line: {entry}")
            if line_type == _KEY_TYPE and line.get("digit") == _OVERLAY_DIGIT:
                raise CheckFailed(f"the audit records ctrl 1: {entry}")
    with open(os.path.join(run.root, _AUDIT_NAME), encoding="utf-8") as file:
        starts = sum(
            line.startswith(_ENGINE_START) for line in file.read().split("\n")
        )
    if starts != run.loads:
        raise CheckFailed(
            f"the audit holds {starts} starts of the engine for"
            f" {run.loads} loads"
        )
    failures_check(run, run.root)
    return (
        f"the audit's {len(entries)} entries hold the {len(rows)} rows of the"
        f" gold's table, every line's body JSON, no line of the audit's own,"
        f" each note of a page thread a sleep on no wake of the audit's own,"
        f" {starts} starts of the engine, one per load, and no unexpected"
        " failure"
    )


# Leaving the page ends the server and ttyd stops, `--debug` keeping the audit.
def rung_left(run: DemoRun) -> str:
    import switches

    if switches.debug:
        audit_copy(run.root, _AUDIT_COPY)
    ttyd = cast("xsjs_serve.TtydServer", run.ttyd)
    programs = page_leave(run, ttyd, run.bootstrap)
    code = server_finish(run, ttyd)
    return (
        f"{_BLANK_URL} ended the page, the programs {programs} under ttyd"
        f" ended and ttyd stopped with code {code}"
    )


# A root outside debug mode serves two turns and ends up holding no record.
def rung_plain(run: DemoRun) -> str:
    import xsjs_serve

    root = os.path.join(run.work, _PLAIN_NAME)
    parameters = parameters_make(gold_value("plain_debug"))
    page = cast(str, run.page)
    xsjs_serve.root_make(run.values, page, root, parameters, True)
    ttyd = run.server_start(root, run.server_fd)
    run.browser.page_open(ttyd.address_get())
    run.band_wait(gold_value("remark"))
    # The first render gives the box the focus, so no click comes first.
    choices = [choice_take(run, "1"), choice_take(run, "0")]
    programs = page_leave(run, ttyd, run.bootstrap_path(root))
    # Wanted before the stop, as ttyd exits with no line of a program's end.
    fragments: list[str] = [
        gold_value("plain_port").format(ttyd.port),
        *gold_value("plain_fragments"),
    ]
    fragments_wait(run, fragments)
    code = server_finish(run, ttyd)
    names = os.listdir(root)
    patterns: list[str] = gold_value("plain_absent")
    records = [
        name
        for name in names
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
    ]
    if records:
        raise CheckFailed(f"the root outside debug mode holds {records}")
    shutil.rmtree(root)
    return (
        f"debug false served {choices}, the programs {programs} ended, ttyd"
        f" stopped with code {code}, {_SERVER_PATH} holds {fragments} and the"
        f" root held none of {patterns} among {sorted(names)}, then went"
    )


# A value of the gold of the root of every tool.
def tools_value(name: str) -> Any:
    return gold_value(f"tools.{name}")


# The prefixed name of every tool the AI is given.
def tools_listed() -> list[str]:
    with open(_TOOLS_PATH, encoding="utf-8") as file:
        listed: dict[str, Any] = json.load(file)
    return [
        f"{side}{_PREFIX_MARK}{tool['name']}"
        for side, reply in listed.items()
        for tool in reply["result"]["tools"]
    ]


# The reply that calls a chain's tool of the index, its results ending there.
def call_reply(chain: str, index: int, call: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": None,
        "next": f"{chain}_{index}",
        "tool_calls": [
            {
                "call_id": _CALL_ID.format(chain, index),
                "name": call["name"],
                "arguments": json.dumps(call["arguments"]),
            }
        ],
    }


# Adds a chain's nodes to the table and returns the reply that starts it.
def chain_add(
    nodes: dict[str, Any], row: dict[str, str], calls: list[dict[str, Any]]
) -> dict[str, Any]:
    chain = row["chain"]
    last = {"content": row["answer"], "next": _MENU_NODE}
    for index in range(len(calls)):
        after = last
        if index + 1 < len(calls):
            after = call_reply(chain, index + 1, calls[index + 1])
        nodes[f"{chain}_{index}"] = {"replies": {}, "after_tools": after}
    return call_reply(chain, 0, calls[0])


# The scripted table of every tool, refusing a tool the gold's chains omit.
def table_make() -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    replies: dict[str, Any] = {
        "0": {"content": tools_value("rest_answer"), "next": _MENU_NODE}
    }
    called: set[str] = set()
    for row in cast(list[dict[str, str]], tools_value("chains")):
        calls: list[dict[str, Any]] = tools_value(row["calls"])
        replies[row["input"]] = chain_add(nodes, row, calls)
        called.update(call["name"] for call in calls)
    missing = [name for name in tools_listed() if name not in called]
    if missing:
        raise CheckFailed(f"the gold's chains call none of {missing}")
    nodes[_MENU_NODE] = {
        "replies": replies,
        "otherwise": {"content": tools_value("otherwise"), "next": _MENU_NODE},
    }
    return {"start": _MENU_NODE, "nodes": nodes}


# Types a chain's input, answers the permits it asks, waits for its answer.
def chain_take(run: DemoRun, number: int) -> str:
    row: dict[str, str] = tools_value("chains")[number]
    permits: dict[str, list[list[str]]] = tools_value("permits")
    run.line_type(row["input"])
    words: str = tools_value("permit_words")
    for tool, label in permits.get(row["chain"], []):
        shown = tool + words
        state = run.state_wait(
            f"the permit of {tool}",
            lambda state: (
                len(state["permit_texts"]) == 1
                and state["permit_texts"][0].startswith(shown)
            ),
        )
        button = next(
            button for button in state["buttons"] if button["text"] == label
        )
        run.mouse_click(button["x"], button["y"])
    run.band_wait(row["answer"])
    return row["answer"]


# A root whose table calls every tool serves, and its first render shows.
def rung_tools_served(run: DemoRun) -> str:
    import xsjs_serve

    table = table_make()
    root = os.path.join(run.work, _TOOLS_NAME)
    run.root = root
    run.bootstrap = run.bootstrap_path(root)
    run.audit_path = _TOOLS_COPY
    parameters = parameters_make(gold_value("root_debug"))
    page = cast(str, run.page)
    xsjs_serve.root_make(run.values, page, root, parameters, True)
    with open(os.path.join(root, _TABLE_PATH), "w", encoding="utf-8") as file:
        json.dump(table, file)
    ttyd = run.server_start(root, sys.stderr.fileno())
    run.browser.page_open(ttyd.address_get())
    remark: str = gold_value("remark")
    run.band_wait(remark)
    return (
        f"the table of {len(table['nodes'])} nodes, which calls all"
        f" {len(tools_listed())} tools the AI is given, serves {remark!r}"
    )


# Typing 1 runs every data tool, and the picture they render shows.
def rung_tools_data(run: DemoRun) -> str:
    text = chain_take(run, 0)
    size: int = tools_value("picture_size")
    colours: list[str] = tools_value("picture_colours")
    state = run.state_read()
    picture = (
        state["image_hidden"],
        state["image_width"],
        state["image_height"],
        state["image_colours"],
    )
    if picture != (False, size, size, colours):
        raise CheckFailed(
            f"the picture's hidden, width, height and colours are {picture},"
            f" where it should show, {size} by {size}, all of {colours}"
        )
    png = run.picture_save("tools_data")
    return (
        f"typing 1 ended with {text!r}, the made picture shown, {size} by"
        f" {size}, of {colours}; PNG {png}"
    )


# Typing 2 runs every console tool, each permit answered by a click.
def rung_tools_console(run: DemoRun) -> str:
    text = chain_take(run, 1)
    png = run.picture_save("tools_console")
    return f"typing 2 answered its permits and ended with {text!r}; PNG {png}"


# Each tool again: 3 past the turns that compact, 4 compacting them first.
def rung_tools_again(run: DemoRun) -> str:
    texts = [chain_take(run, 2), chain_take(run, 3)]
    return f"typing 3 and 4 ended with {texts}"


# Typing 0 dumps both sides, the server holding the turns the browser dropped.
def rung_tools_dump(run: DemoRun) -> str:
    text: str = tools_value("rest_answer")
    run.line_type("0")
    run.band_wait(text)
    rows: list[dict[str, str]] = gold_value("dump_entries")
    while (bodies := entries_ordered(run.root, rows)) is None:
        run.poll_sleep(f"the audit's entries {rows} of the input 0")
    turns: dict[str, int] = tools_value("dump_turns")
    held = {
        "browser": [int(n) for n in _HIDDEN_PATTERN.findall(bodies[0])],
        "server": [int(n) for n in _HIDDEN_PATTERN.findall(bodies[1])],
    }
    for side, counts in held.items():
        if max(counts) != turns[side]:
            raise CheckFailed(
                f"the {side}'s dump counts {counts} turns, not {turns[side]}"
            )
    browser = _HIDDEN_PATTERN.sub("", bodies[0])
    server = _HIDDEN_PATTERN.sub("", bodies[1])
    if browser != server:
        raise CheckFailed(
            f"the dumps differ past their turns: {browser!r}, {server!r}"
        )
    return (
        f"typing 0 ended with {text!r}, and the dumps differ in nothing but"
        f" their turns: {turns}"
    )


# The model calls of an audit's whole entries, each with its reply's body.
def calls_read(entries: list[Any]) -> list[ModelCall]:
    answers: dict[tuple[int, object], dict[str, Any]] = {
        (entry.start, entry.line["0"].get("reply")): entry.line
        for entry in entries
        if entry.label == _REPLY_LANE
    }
    calls: list[ModelCall] = []
    for entry in entries:
        line = entry.line
        if entry.label == _REQUEST_LANE and line["url"].endswith(_MODEL_PATH):
            answer = answers.get((entry.start, line["0"].get("id")))
            reply = None if answer is None else answer["json"]
            calls.append(
                ModelCall(entry.start, entry.number, line["json"], reply)
            )
    return calls


# The whole entries and model calls once a call after the load is answered.
def calls_wait(run: DemoRun, load: int) -> tuple[list[Any], list[ModelCall]]:
    while True:
        entries = entries_whole(run.root)
        calls = calls_read(entries)
        answered = all(call.reply is not None for call in calls)
        if calls and calls[-1].start > load and answered:
            return entries, calls
        run.poll_sleep(
            f"a model call of an engine start after {load} in the audit,"
            " each call with its reply"
        )


# The seed's system prompt, the text of the document the agent sends.
def prompt_read() -> str:
    with open(_PROMPT_PATH, encoding="utf-8") as file:
        prompt: str = json.load(file)["text"]
    return prompt


# How many of the items hold the text, escaped as their JSON writes it.
def text_holders(items: list[dict[str, Any]], text: str) -> int:
    escaped = json.dumps(text, ensure_ascii=False)[1:-1]
    return sum(
        escaped in json.dumps(item, ensure_ascii=False) for item in items
    )


# The kind of an input item: its type, or the role of a message with none.
def item_kind(item: dict[str, Any]) -> str:
    return str(item["type"] if "type" in item else item["role"])


# One commit stored the conversation's prompt, before the first model call.
def prompt_stored_check(
    entries: list[Any], calls: list[ModelCall], prompt: str
) -> None:
    stored = [
        entry
        for entry in entries
        if entry.label == _COMMIT_LANE
        and entry.line["0"].get("type") == _PROMPT_TYPE
    ]
    if len(stored) != 1:
        numbers = [entry.number for entry in stored]
        raise CheckFailed(
            f"{len(stored)} prompts were stored, at the lines {numbers}"
        )
    entry = stored[0]
    messages: list[dict[str, Any]] = entry.line["messages"]
    first = calls[0].number
    message = {"role": _SYSTEM_ROLE, "content": prompt}
    if entry.number > first or messages[:1] != [message]:
        raise CheckFailed(
            f"the prompt stored at line {entry.number}, the first model call"
            f" being at line {first}, holds {messages}"
        )


# A chained call sends no system message and only the items its reply left.
def chained_check(
    call: ModelCall, output: list[dict[str, Any]] | None
) -> None:
    items: list[dict[str, Any]] = call.body["input"]
    if output is None:
        raise CheckFailed(
            f"the model call at line {call.number} chains from"
            f" {call.body[_CHAIN_FIELD]}, which no reply of its load holds"
        )
    if any(item.get("role") == _SYSTEM_ROLE for item in items):
        raise CheckFailed(
            f"the chained model call at line {call.number} sends a system"
            " message"
        )
    asked = [item["call_id"] for item in output if item["type"] == _CALL_TYPE]
    due: list[tuple[str, object]] = [(_OUTPUT_TYPE, ident) for ident in asked]
    if not asked:
        due = [(_USER_ROLE, None)]
    sent = [(item_kind(item), item.get("call_id")) for item in items]
    if sent != due:
        raise CheckFailed(
            f"the chained model call at line {call.number} sends {sent}, not"
            f" only the new items {due}"
        )
    usage = cast(dict[str, Any], call.reply)["usage"]
    if usage["input_tokens_details"]["cached_tokens"] == 0:
        raise CheckFailed(
            f"the reply to the chained model call at line {call.number}"
            f" found nothing cached: {usage}"
        )


# A chain starts at a load or a compaction, the prompt once and first.
def chains_check(calls: list[ModelCall], prompt: str) -> tuple[int, int]:
    message = {"role": _SYSTEM_ROLE, "content": prompt}
    outputs: dict[tuple[int, object], list[dict[str, Any]]] = {}
    started = 0
    for index, call in enumerate(calls):
        if _CHAIN_FIELD in call.body:
            output = outputs.get((call.start, call.body[_CHAIN_FIELD]))
            chained_check(call, output)
        else:
            items: list[dict[str, Any]] = call.body["input"]
            first = index == 0 or calls[index - 1].start != call.start
            kinds = [item_kind(item) for item in items[:2]]
            if not first and kinds != [_SYSTEM_ROLE, _SYSTEM_ROLE]:
                raise CheckFailed(
                    f"the model call at line {call.number} starts a chain"
                    " within its load and after no compaction"
                )
            if items[0] != message or text_holders(items, prompt) != 1:
                raise CheckFailed(
                    f"the model call at line {call.number} starts a chain"
                    " without the prompt once, as its first item"
                )
            started += 1
        reply = cast(dict[str, Any], call.reply)
        outputs[(call.start, reply["id"])] = reply["output"]
    return started, len(calls) - started


# Each model call of a debug root sends the omission's text, no tool list.
def tools_check(calls: list[ModelCall]) -> None:
    omitted: str = gold_value("tools_omitted")
    for call in calls:
        tools = call.body.get(_TOOLS_FIELD)
        if tools != omitted:
            raise CheckFailed(
                f"the model call at line {call.number} sends {tools!r} as its"
                f" tools, not {omitted!r}"
            )


# The three lanes of the conversation write the prompt once.
def prompt_once_check(entries: list[Any], prompt: str) -> None:
    text = json.dumps(prompt, ensure_ascii=False)
    count = sum(
        entry.body.count(text)
        for entry in entries
        if entry.label in _CONVERSATION_LANES
    )
    if count != 1:
        raise CheckFailed(
            f"the conversation's three lanes write the prompt {count} times"
        )


# The prompt stored, sent once per chain and written once, and no tool list.
def conversation_check(
    entries: list[Any], calls: list[ModelCall]
) -> tuple[int, int]:
    prompt = prompt_read()
    prompt_stored_check(entries, calls, prompt)
    counts = chains_check(calls, prompt)
    tools_check(calls)
    prompt_once_check(entries, prompt)
    return counts


# The stored turns the browser sent, none of the system or holding the prompt.
def turns_read(entries: list[Any], prompt: str) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for entry in entries:
        line = entry.line
        if entry.label == _COMMIT_LANE and line["0"].get("type") == _TURN_TYPE:
            if text_holders(line["content"], prompt):
                raise CheckFailed(
                    f"the turn stored at line {entry.number} holds the prompt"
                )
            if line["role"] == _SYSTEM_ROLE:
                raise CheckFailed(
                    f"a system turn was stored at line {entry.number}"
                )
            turns.append(line)
    return turns


# Each result is stored under its own call's id and holds the gold's text.
def results_check(turns: list[dict[str, Any]]) -> int:
    named: dict[str, str] = {}
    results: dict[str, str] = {}
    for turn in turns:
        for item in turn["content"]:
            if turn["role"] == _REPLY_ROLE and item["type"] == _CALL_TYPE:
                named[item["call_id"]] = item["name"]
            elif turn["role"] == _TOOL_ROLE:
                key = item["call_id"]
                if key in results:
                    raise CheckFailed(f"the tool call id {key} comes twice")
                results[key] = item["output"]
    for row in cast(list[dict[str, str]], tools_value("chains")):
        if row["chain"] == "restart":
            continue
        calls: list[dict[str, Any]] = tools_value(row["calls"])
        for index, call in enumerate(calls):
            ident = _CALL_ID.format(row["chain"], index)
            found = results.get(ident)
            if (
                named.get(ident) != call["name"]
                or found is None
                or call["holds"] not in found
            ):
                raise CheckFailed(
                    f"the call {ident} named {named.get(ident)!r}, not"
                    f" {call['name']!r}, or returned {found!r}, which lacks"
                    f" {call['holds']!r}"
                )
    return len(results)


# The first call to show the compaction starts a chain, its summary second.
def compaction_check(calls: list[ModelCall]) -> int:
    summary: str = tools_value("compact_summary")
    for call in calls:
        items: list[dict[str, Any]] = call.body["input"]
        if text_holders(items, summary):
            kinds = [item_kind(item) for item in items]
            if (
                _CHAIN_FIELD in call.body
                or kinds != [_SYSTEM_ROLE, _SYSTEM_ROLE, _USER_ROLE]
                or not text_holders(items[1:2], summary)
            ):
                raise CheckFailed(
                    "the first model call to show the compaction, at line"
                    f" {call.number}, sends {kinds}, not a new chain of the"
                    f" prompt, the summary {summary!r} and the person's text"
                )
            return call.number
    raise CheckFailed(f"no model call shows the compaction: {summary!r}")


# What the server holds of the tour: the kept row, the file, no dropped file.
def server_check(root: str) -> None:
    text: str = tools_value("kept_text")
    value = value_read(root, tools_value("kept_db"), tools_value("kept_key"))
    if value != text.encode():
        raise CheckFailed(f"the server holds {value!r}, not {text!r}")
    dropped = os.path.join(root, tools_value("dropped_db") + _DB_EXTENSION)
    if os.path.exists(dropped):
        raise CheckFailed(f"the dropped database {dropped} is still there")
    path = os.path.join(root, "main_loop", tools_value("loop_name"))
    with open(path, encoding="utf-8") as file:
        written = file.read()
    if written != tools_value("loop_text"):
        raise CheckFailed(f"the server's main loop file holds {written!r}")


# The audit shows the prompt once per chain, every tool's result and commit.
def rung_tools_record(run: DemoRun) -> str:
    import audit, switches

    count = failures_check(run, run.root)
    entries = entries_whole(run.root)
    calls = calls_read(entries)
    started, chained = conversation_check(entries, calls)
    compacted = compaction_check(calls)
    turns = turns_read(entries, prompt_read())
    due: int = tools_value("turns_sent")
    if len(turns) != due:
        raise CheckFailed(f"the browser sent {len(turns)} turns, not {due}")
    results = results_check(turns)
    rows: list[dict[str, str]] = tools_value("commits")
    written = audit.entries_read(run.root)
    missing = [
        row
        for row in rows
        if not any(entry_fits(entry, row) for entry in written)
    ]
    if missing:
        raise CheckFailed(f"the audit lacks {missing}")
    server_check(run.root)
    if switches.debug:
        audit_copy(run.root, _TOOLS_COPY)
    return (
        f"the audit's {count} entries hold no unexpected failure; one commit"
        f" stored the prompt, the {started} chains' first calls sent it once,"
        f" as their first item, the one at line {compacted} after the"
        f" compaction with its summary next, the {chained} chained calls"
        " only their new items, each reply finding its context cached, all"
        f" {len(calls)} calls listing every tool, and none of the"
        f" {len(turns)} stored turns holds it; {results} tool results hold"
        " the gold's texts under their own calls' ids, and the server holds"
        " their commits"
    )


# Typing 5 restarts the server in place, which the page refuses by its fault.
def rung_tools_restart(run: DemoRun) -> str:
    text: str = tools_value("restart_fault")
    run.line_type(tools_value("chains")[4]["input"])
    while True:
        state = cast(
            dict[str, Any], run.browser.script_evaluate(_STATE_SCRIPT)
        )
        if state["fault"] is not None:
            break
        run.poll_sleep(f"the fault screen holding {text!r}")
    if text not in state["fault"]:
        raise CheckFailed(f"the fault screen holds {state['fault']!r}")
    png = run.picture_save("tools_restart")
    with open(os.path.join(run.root, _AUDIT_NAME), encoding="utf-8") as file:
        pids = _START_PATTERN.findall(file.read())
    if len(pids) != 2 or pids[0] != pids[1]:
        raise CheckFailed(f"the audit's engine starts are of the pids {pids}")
    run.browser.page_open(_BLANK_URL)
    code = server_finish(run, cast("xsjs_serve.TtydServer", run.ttyd))
    return (
        f"typing 5 restarted the server in place, the pid {pids[0]} kept, the"
        f" page refused it with {text!r}, and ttyd stopped with code {code};"
        f" PNG {png}"
    )


# The run passed: `--debug` has left the audit, and the roots go.
def run_finish(run: DemoRun) -> None:
    import switches

    if switches.debug and not (
        os.path.isfile(_AUDIT_COPY) and os.path.getsize(_AUDIT_COPY) > 0
    ):
        raise CheckFailed(f"--debug left no audit at {_AUDIT_COPY}")
    shutil.rmtree(run.work)


# Runs the rungs in the order of the plan, each by its label.
def rungs_climb(run: DemoRun) -> None:
    log = run.log
    log.book.root_enter(_ROOT_NAME, _SMOKE_TEST)
    log.rung_run(
        "served",
        _SMOKE_TEST,
        lambda: rung_served(run),
        gold_value("served_seconds"),
    )
    log.rung_run("reload", _TEST_ALL, lambda: rung_reload(run))
    log.rung_run("choice 1", _SMOKE_TEST, lambda: rung_choice_render(run))
    log.rung_run("choice 3", _SMOKE_TEST, lambda: rung_choice_console(run))
    log.rung_run("bad input", _SMOKE_TEST, lambda: rung_refused(run))
    log.rung_run("choice 2", _TEST_ALL, lambda: rung_choice_note(run))
    log.rung_run("console", _TEST_ALL, lambda: rung_console(run))
    log.rung_run("overlay", _TEST_ALL, lambda: rung_overlay(run))
    log.rung_run("prompt kept", _SMOKE_TEST, lambda: rung_prompt_kept(run))
    log.rung_run("dump", _SMOKE_TEST, lambda: rung_dump(run))
    log.rung_run("audit", _SMOKE_TEST, lambda: rung_audit(run))
    log.rung_run("left", _SMOKE_TEST, lambda: rung_left(run))
    log.book.root_leave()
    log.book.root_enter(_PLAIN_NAME, _SMOKE_TEST)
    log.rung_run("plain", _SMOKE_TEST, lambda: rung_plain(run))
    log.book.root_leave()
    if log.book.root_enter(_TOOLS_NAME, _TEST_ALL):
        log.rung_run("tools served", _TEST_ALL, lambda: rung_tools_served(run))
        log.rung_run("tools data", _TEST_ALL, lambda: rung_tools_data(run))
        log.rung_run(
            "tools console", _TEST_ALL, lambda: rung_tools_console(run)
        )
        log.rung_run("tools again", _TEST_ALL, lambda: rung_tools_again(run))
        log.rung_run("tools dump", _TEST_ALL, lambda: rung_tools_dump(run))
        log.rung_run("tools record", _TEST_ALL, lambda: rung_tools_record(run))
        log.rung_run(
            "tools restart", _TEST_ALL, lambda: rung_tools_restart(run)
        )
        log.book.root_leave()
    run_finish(run)


# Runs the rungs in one browser, ttyd stopped whatever ended them.
def demo_run(log: RungLog, hold: bool) -> None:
    import devtools, harness

    # The directory holds this run's PNGs alone, so none misleads.
    if os.path.exists(_PICTURE_PATH):
        shutil.rmtree(_PICTURE_PATH)
    os.makedirs(_PICTURE_PATH)
    work = tempfile.mkdtemp(prefix=_WORK_PREFIX, dir=_BUILD_PATH)
    log.line_print(f"the roots of this run are in {work} until it passes")
    width, height = gold_value("window_width"), gold_value("window_height")
    with (
        devtools.Browser(width, height, devtools.LinuxPipe()) as browser,
        open(_SERVER_PATH, "wb", buffering=0) as server_log,
    ):
        log.client_bind(browser.client_get())
        run = DemoRun(
            browser, log, harness.settings_copy(), work, server_log.fileno()
        )
        try:
            rungs_climb(run)
        except Exception as failure:
            run.failure_take(failure, hold)
            raise
        finally:
            run.server_end()


# Exits with 128 plus the signal's number, so the blocks stop what they run.
def signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the rungs of the chosen category in order and returns the exit code.
def main(arguments: list[str]) -> int:
    import category, switches

    parser = argparse.ArgumentParser(
        prog=_PROGRAM_NAME,
        description="Run the demo test: the engine page served as"
        " xsjs_serve.py serves it, from a fresh root under build/, driven"
        " rung by rung in chrome-headless-shell, each state's PNG saved to"
        " build/test_demo/.",
    )
    parser.add_argument(
        "--hold",
        action="store_true",
        help="after a failed rung leave the page, keep ttyd serving the root,"
        " print its address and wait for ctrl C",
    )
    category.options_add(parser)
    switches.options_add(parser)
    parsed = parser.parse_args(arguments)
    chosen: str = parsed.category
    hold: bool = parsed.hold
    switches.switches_set(parsed)
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, signal_exit)
    log = RungLog(chosen)
    try:
        demo_run(log, hold)
    except CheckFailed as failure:
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    except Exception as failure:
        failure.add_note(f"the rung that ran: {log.rung}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
