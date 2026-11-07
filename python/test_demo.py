#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# The demo test, which proves the engine page is ready for a person to view.
# It makes a fresh debug root in build/test_demo-*/root and serves it through
# the functions of xsjs_serve.py, so that what it proves is what the maintainer
# runs, then drives chrome-headless-shell over DevTools as a person would:
# clicks and keys reach the page as input events, and every reading is of the
# page's elements. The analyst is the seed's scripted table, and no real AI
# provider is contacted. A person's error, an input the table does not hold,
# ends in her answer in the band, by the bad input rung. Each rung runs under
# a timer and is labelled smoke-test or test-all, and a mislabel fails the run.
# PNGs of the states go to build/test_demo/, which each run empties. The root
# goes once the run passes and stays after a failure, with a PNG of the failed
# rung. With --hold a failed rung leaves the page, keeps ttyd serving the root,
# prints the address and waits for ctrl C, so that a person opens the failed
# state in a browser, which a fresh load restores from the server. Its timers,
# window size, texts and log table are in its gold, python.test_demo.

import argparse, contextlib, os, shutil, signal, sqlite3, sys, tempfile, time
import types
from collections.abc import Callable
from typing import Any, TYPE_CHECKING, cast

# Only type checks import these here, as the bytecode's place is set below.
if TYPE_CHECKING:
    import devtools, xsjs_serve

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: the page, the run's root, the PNGs and bytecode.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The id of this driver's gold, in its own `test_setting_` file.
_GOLD_ID = "python.test_demo"

# The start of the name of the directory each run makes and keeps its root in.
_WORK_PREFIX = "test_demo-"

# The name of the root in that directory, and of the root in the label book.
_ROOT_NAME = "root"

# The directory the PNGs of the states go to, kept after the run.
_PICTURE_PATH = os.path.join(_BUILD_PATH, "test_demo")

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

# The digit of ctrl that toggles the overlay of tty 1, the wire's.
_OVERLAY_DIGIT = 1

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
  };
})()
"""

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


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
    # Takes the browser, the log, the settings and the directory of the root.
    def __init__(
        self,
        browser: devtools.Browser,
        log: RungLog,
        values: dict[str, Any],
        work: str,
    ) -> None:
        self.browser = browser
        self.log = log
        self.values = values
        self.work = work
        self.root = os.path.join(work, _ROOT_NAME)
        script: str = values["powershell"]["bootstrap_script"]
        self.bootstrap = os.path.join(self.root, "python", script)
        self.ttyd: xsjs_serve.TtydServer | None = None

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
            lambda state: state["subtitle"] == text
            and not state["input"]["disabled"],
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

    # Saves the failed rung's PNG and, when asked, serves its root on.
    def failure_take(self, failure: Exception, hold: bool) -> None:
        log = self.log
        log.timer_renew()
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
            if (
                process_parent(pid) == ttyd_pid
                and bootstrap.encode() in cmdline_read(pid)
            ):
                pids.append(pid)
    return pids


# The note's value in the server's database file, None until its row comes.
def note_read(root: str) -> bytes | None:
    path = os.path.join(root, gold_value("note_db") + _DB_EXTENSION)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    with contextlib.closing(connection):
        row = connection.execute(
            _NOTE_SELECT, (gold_value("note_key"),)
        ).fetchone()
    return None if row is None else cast(bytes, row[0])


# Types a number and waits for the analyst's text of it in the band.
def choice_take(run: DemoRun, number: str) -> str:
    text: str = gold_value(f"choices.{number}")
    run.line_type(number)
    run.band_wait(text)
    return text


# The page builds, the root is made, ttyd answers and the first render shows.
def rung_served(run: DemoRun) -> str:
    import switches, xsjs_serve

    page = xsjs_serve.page_ready(run.values)
    parameters = {
        **switches.switches_get(),
        "debug": gold_value("root_debug"),
        "verbose": gold_value("root_verbose"),
    }
    xsjs_serve.root_make(run.values, page, run.root, parameters, True)
    # A stop signal waits until `run.ttyd` is set, so that the stop finds ttyd.
    held = signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
    try:
        run.ttyd = xsjs_serve.TtydServer(run.values, run.root, 0)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, held)
    address = run.ttyd.address_get()
    run.browser.page_open(address)
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
        lambda state: state["permit_texts"] == [permit]
        and [button["text"] for button in state["buttons"]] == labels,
    )
    # Accept comes first, as in the gold's buttons.
    accept: dict[str, Any] = state["buttons"][0]
    run.mouse_click(accept["x"], accept["y"])
    run.state_wait(
        "the console view shown", lambda state: state["console_shown"]
    )
    run.state_wait(
        f"dash's prompt {prompt!r} and the row {output!r}",
        lambda state: output in state["rows"]
        and any(row.startswith(prompt) for row in state["rows"]),
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
        lambda state: state["subtitle"] == text
        and not state["input"]["disabled"]
        and state["input"]["focused"],
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
    while (value := note_read(run.root)) is None:
        run.poll_sleep("the note's row in the server's database")
    if value != note.encode():
        raise CheckFailed(
            f"the server's database holds the note {value!r}, not {note!r}"
        )
    return (
        f"typing 2 ended with {text!r} in the band, and the server's database"
        f" file holds the note {note!r}"
    )


# ctrl 0 hides and shows the view, and a command typed in it runs.
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
    return (
        f"ctrl 0 hid the view and showed it again, and {command!r} typed in"
        f" its terminal showed the row {output!r}; PNG {png}"
    )


# ctrl 1 shows the wire overlay with a sent and a received line, then hides it.
def rung_overlay(run: DemoRun) -> str:
    sent: str = gold_value("overlay_sent")
    received: str = gold_value("overlay_received")
    run.control_press(_OVERLAY_DIGIT)
    state = run.state_wait(
        f"the wire overlay with lines starting {sent!r} and {received!r}",
        lambda state: any(
            line.startswith(sent) for line in state["overlay_lines"]
        )
        and any(line.startswith(received) for line in state["overlay_lines"]),
    )
    png = run.picture_save("overlay")
    run.control_press(_OVERLAY_DIGIT)
    run.state_wait(
        "the wire overlay hidden", lambda state: not state["overlay_lines"]
    )
    return (
        f"ctrl 1 showed the wire overlay, {len(state['overlay_lines'])} lines"
        f" with a sent and a received one, and hid it; PNG {png}"
    )


# The log tool's function reads each fragment of the gold's table.
def rung_log(run: DemoRun) -> str:
    import xsjs_log

    rows: list[dict[str, str]] = gold_value("log")
    for row in rows:
        thread, fragment, jslb = row["thread"], row["fragment"], row["jslb"]
        while not any(
            jslb in entry.text
            for entry in xsjs_log.lines_read(
                run.root, thread=thread, grep=fragment
            )
        ):
            run.poll_sleep(
                f"a line of thread {thread} in the log holding {fragment!r}"
                f" and {jslb!r}"
            )
    return f"the log holds the {len(rows)} fragments of the gold's table"


# Leaving the page ends the server, then ttyd stops and the root goes.
def rung_left(run: DemoRun) -> str:
    ttyd = cast("xsjs_serve.TtydServer", run.ttyd)
    programs = programs_find(ttyd.pid, run.bootstrap)
    if not programs:
        raise CheckFailed(f"no child of ttyd runs {run.bootstrap}")
    run.browser.page_open(_BLANK_URL)
    while programs_find(ttyd.pid, run.bootstrap):
        run.poll_sleep(f"the end of {run.bootstrap} under ttyd")
    run.ttyd = None
    code = ttyd.server_stop()
    due: int = gold_value("ttyd_code")
    if code != due:
        raise CheckFailed(f"ttyd stopped with code {code}, not {due}")
    shutil.rmtree(run.work)
    return (
        f"{_BLANK_URL} ended the page, the programs {programs} under ttyd"
        f" ended, ttyd stopped with code {code} and the root went"
    )


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
    log.rung_run("log", _SMOKE_TEST, lambda: rung_log(run))
    log.rung_run("left", _SMOKE_TEST, lambda: rung_left(run))
    log.book.root_leave()


# Runs the rungs in one browser, ttyd stopped whatever ended them.
def demo_run(log: RungLog, hold: bool) -> None:
    import devtools, harness

    # The directory holds this run's PNGs alone, so none misleads.
    if os.path.exists(_PICTURE_PATH):
        shutil.rmtree(_PICTURE_PATH)
    os.makedirs(_PICTURE_PATH)
    work = tempfile.mkdtemp(prefix=_WORK_PREFIX, dir=_BUILD_PATH)
    log.line_print(f"the root of this run is in {work} until it passes")
    width, height = gold_value("window_width"), gold_value("window_height")
    with devtools.Browser(width, height, devtools.LinuxPipe()) as browser:
        log.client_bind(browser.client_get())
        run = DemoRun(browser, log, harness.settings_copy(), work)
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
