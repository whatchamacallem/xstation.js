# SPDX-FileCopyrightText: © 2026 Adrian Johnston.
# SPDX-License-Identifier: MIT
# This file is licensed under the terms of the LICENSE.md file.
#
# Walks a guide test on the engine page, the work of the three programs
# test_guide_NAME.py, by the contract of API/python/guide_walk.pyi. table_build
# turns a guide's table.json into the scripted table the port takes: each node
# holding `ask` gains an `otherwise` of the table's `puzzled` then `ask`, and,
# with the table's `exit`, a reply of the exit's input and the three nodes
# NODE~exit, NODE~paused and NODE~resume, which pause there and resume there.
# guide_main serves a fresh debug root through the functions of xsjs_serve.py,
# as the maintainer serves one, its seed table the guide's, and drives
# chrome-headless-shell by keys alone, one step at a time: the line typed, its
# band waited for with the box enabled, then the picture and the rows of the
# server's databases the gold names. A step whose band the step before showed
# already is refused, as its wait could pass before its turn ran. It imports
# nothing of test_demo.py, and the modules beside it are imported inside the
# functions that use them, after their bytecode has been sent to build/.

import argparse, contextlib, copy, functools, json, os, shutil, signal, sqlite3
import sys, tempfile, time, types
from collections.abc import Callable
from typing import Any, TYPE_CHECKING, cast

# Only type checks import these here, as the bytecode's place is set below.
if TYPE_CHECKING:
    import devtools, xsjs_serve

# The public names of this module, as its stub declares them.
__all__ = ["CheckFailed", "guide_main", "table_build"]

# The checkout's `python` directory, which holds this file.
_PYTHON_PATH = os.path.dirname(os.path.abspath(__file__))

# The checkout, which holds the `python` directory.
_CHECKOUT_PATH = os.path.dirname(_PYTHON_PATH)

# The build directory: the page, each run's root, its failure and bytecode.
_BUILD_PATH = os.path.join(_CHECKOUT_PATH, "build")

# The directory of the guides, each in a directory of its own.
_GUIDES_PATH = os.path.join(_PYTHON_PATH, "guides")

# The file of a guide's directory that holds the source of its table.
_TABLE_NAME = "table.json"

# The one member of an object that stands for the text of a file of the guide.
_TEXT_KEY = "$text"

# The newline that ends each text file of a guide, which its text leaves out.
_TEXT_END = "\n"

# The member of a node that holds its question, and that of its other reply.
_ASK_KEY = "ask"
_OTHERWISE_KEY = "otherwise"

# The table's members of its words before a question asked again, its exit.
_PUZZLED_KEY = "puzzled"
_EXIT_KEY = "exit"

# The members of a node that hold one reply each, beside its `replies`.
_REPLY_KEYS = ("otherwise", "after_tools", "after_lacks")

# What joins a node's name and the end of the name of a node of its exit.
_EXIT_MARK = "~"

# The ends of the names of the nodes of an exit: left, paused, resumed.
_EXIT_ENDS = ("exit", "paused", "resume")

# The path of a script's `say` in the tool result a reply quotes.
_SAY_PATH = "value.say"

# The separators of the compact JSON text of a call's arguments.
_JSON_SEPARATORS = (",", ":")

# The language of the gold ids, and the start of each guide program's name.
_GOLD_LANGUAGE = "python"
_PROGRAM_PREFIX = "test_guide_"

# The name of the root in the work directory of a run.
_ROOT_NAME = "root"

# The scripted table a root seeds its store with, under that root.
_TABLE_PATH = os.path.join("python", "seed", "provider_script.json")

# The extension of a database file under the root.
_DB_EXTENSION = ".sqlite"

# The root's audit, and the name of its copy in the failure directory.
_AUDIT_NAME = "_audit.txt"
_AUDIT_COPY = "audit.txt"

# The heading of each start of the engine role in the audit.
_ENGINE_START = "==== engine started, "

# The start and the end of the name of the PNG of a failed rung.
_FAILED_PREFIX = "failed_"
_PICTURE_EXTENSION = ".png"

# The rung before the first, then the rungs every walk has around the gold's.
_FIRST_RUNG = "browser"
_SERVED_RUNG = "served"
_AUDIT_RUNG = "audit"
_LEFT_RUNG = "left"

# The exit code of a run with a failed check, and of one `^C` ended.
_EXIT_FAILED = 1
_EXIT_INTERRUPTED = 130

# A shell's exit code for a signal is this plus the signal's number.
_SIGNAL_BASE = 128

# The signals `xsjs_serve.TtydServer` unblocks in ttyd, held while it starts.
_STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)

# The page the browser leaves the engine page for.
_BLANK_URL = "about:blank"

# The directory of the running processes.
_PROC_PATH = "/proc"

# The DevTools method of a keyboard event.
_KEY_METHOD = "Input.dispatchKeyEvent"

# The fields of the Enter key in a keyboard event, and the text it types.
_ENTER_KEY = {"key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13}
_ENTER_TEXT = "\r"

# The page as a person sees it, or its fault screen alone, as one JSON value.
_STATE_SCRIPT = r"""(() => {
  const fault = document.querySelector("body > pre");
  if (fault !== null) {
    return { fault: fault.textContent };
  }
  const input = document.querySelector("#input");
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
    disabled: input.disabled,
    focused: document.activeElement === input,
    image_hidden: image.hidden,
    image_width: image.width,
    image_height: image.height,
    image_colours: [...colours],
  };
})()
"""

# Bytecode of the modules imported from the python directory goes in `build`.
sys.pycache_prefix = os.path.join(_BUILD_PATH, "pycache")


# A check of a walk that failed, with the measurement that failed it.
class CheckFailed(Exception):
    pass


# A rung's time limit, which fails loud once it has passed.
class _RungTimer:
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
class _RungLog:
    # Starts before the browser, the first timer of the gold's `rung_seconds`.
    def __init__(self, chosen: str, seconds: float) -> None:
        import category

        self.book = category.LabelBook(chosen)
        self.rung = _FIRST_RUNG
        self.seconds = seconds
        self.timer = _RungTimer(self.rung, seconds)
        self.started = time.monotonic()
        self.client: devtools.ProtocolClient | None = None

    # Has each rung's timer from now on bound the client's DevTools waits.
    def client_bind(self, client: devtools.ProtocolClient) -> None:
        self.client = client
        client.deadline_set(self.timer.end)

    # Starts a timer of the seconds for the rung that runs, bounding DevTools.
    def timer_start(self, seconds: float) -> None:
        self.timer = _RungTimer(self.rung, seconds)
        client = cast("devtools.ProtocolClient", self.client)
        client.deadline_set(self.timer.end)

    # Gives what follows a failed rung a timer, the rung's name kept.
    def timer_renew(self) -> None:
        self.timer_start(self.seconds)

    # Prints a line after the name of the rung that runs, under `--verbose`.
    def line_print(self, text: str) -> None:
        import switches

        if switches.verbose:
            print(f"{self.rung}: {text}", flush=True)

    # Runs a rung under a timer of the seconds, if the run takes its label.
    def rung_run(
        self, rung: str, label: str, check: Callable[[], str], seconds: float
    ) -> None:
        if not self.book.rung_enter(rung, label):
            return
        self.rung = rung
        self.started = time.monotonic()
        self.timer_start(seconds)
        summary = check()
        spent = time.monotonic() - self.started
        self.line_print(f"{summary} ({label}, {spent:.3f} s)")


# The browser, the root and the ttyd of a walk, and what a person does.
class _GuideRun:
    # Takes the browser, log, gold, settings, guide, work and failure folders.
    def __init__(
        self,
        browser: devtools.Browser,
        log: _RungLog,
        gold: dict[str, Any],
        values: dict[str, Any],
        name: str,
        work: str,
        failed: str,
    ) -> None:
        self.browser = browser
        self.log = log
        self.gold = gold
        self.values = values
        self.name = name
        self.failed = failed
        self.root = os.path.join(work, _ROOT_NAME)
        script: str = values["powershell"]["bootstrap_script"]
        # The root's `bootstrap.py`, which ttyd's children run.
        self.bootstrap = os.path.join(self.root, "python", script)
        self.ttyd: xsjs_serve.TtydServer | None = None
        # The band the first render or the last step showed, none before.
        self.band: str | None = None

    # Starts ttyd on the root, a stop signal waiting until `self.ttyd` is set.
    def server_start(self) -> xsjs_serve.TtydServer:
        import xsjs_serve

        held = signal.pthread_sigmask(signal.SIG_BLOCK, _STOP_SIGNALS)
        try:
            self.ttyd = xsjs_serve.TtydServer(
                self.values, self.root, 0, sys.stderr.fileno()
            )
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, held)
        return self.ttyd

    # Sleeps one poll, failing the rung once it has run out of its seconds.
    def poll_sleep(self, what: str) -> None:
        poll: float = self.gold["poll_seconds"]
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
            lambda state: state["subtitle"] == text and not state["disabled"],
        )

    # Presses and releases a key, `text` being what it types.
    def key_press(self, fields: dict[str, Any], text: str) -> None:
        client = self.browser.client_get()
        client.method_call(
            _KEY_METHOD, {**fields, "type": "keyDown", "text": text}
        )
        client.method_call(_KEY_METHOD, {**fields, "type": "keyUp"})

    # Types each character of the text, then Enter, at the focus.
    def line_type(self, text: str) -> None:
        for character in text:
            self.key_press({"key": character}, character)
        self.key_press(_ENTER_KEY, _ENTER_TEXT)

    # Checks the picture the gold names: hidden, or its size and colours.
    def picture_check(self, picture: dict[str, Any]) -> None:
        state = self.state_read()
        shown = (
            state["image_hidden"],
            state["image_width"],
            state["image_height"],
            sorted(state["image_colours"]),
        )
        hidden: bool = picture["hidden"]
        if hidden:
            if not state["image_hidden"]:
                raise CheckFailed(
                    "the picture's hidden, width, height and colours are"
                    f" {shown}, where it should be hidden"
                )
            return
        size: int = picture["size"]
        colours: list[str] = sorted(picture["colours"])
        if shown != (False, size, size, colours):
            raise CheckFailed(
                f"the picture's hidden, width, height and colours are {shown},"
                f" where it should show, {size} by {size}, all of {colours}"
            )

    # Polls the rows of a statement on a server's database until they are due.
    def rows_check(self, check: dict[str, Any]) -> None:
        path = os.path.join(self.root, check["db"] + _DB_EXTENSION)
        sql: str = check["sql"]
        params: list[Any] = check["params"]
        due: list[list[Any]] = check["rows"]
        while True:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            with contextlib.closing(connection):
                rows = [list(row) for row in connection.execute(sql, params)]
            if rows == due:
                return
            self.poll_sleep(
                f"the rows {due} of {sql!r} in {path}, the last read being"
                f" {rows}"
            )

    # Types a step's line and waits for its band, its picture and its rows.
    def step_take(self, step: dict[str, Any]) -> None:
        say: str = step["say"]
        band: str = step["band"]
        # A band shown already could be waited for before the turn ran.
        if band == self.band:
            raise CheckFailed(
                f"the step {say!r} waits for the band {band!r}, which the step"
                " before it showed already"
            )
        self.line_type(say)
        self.band_wait(band)
        self.band = band
        if "picture" in step:
            self.picture_check(step["picture"])
        if "rows" in step:
            for check in cast(list[dict[str, Any]], step["rows"]):
                self.rows_check(check)

    # Saves the failed rung's PNG and the audit in the failure directory.
    def failure_take(self) -> None:
        log = self.log
        log.timer_renew()
        audit = os.path.join(self.root, _AUDIT_NAME)
        # A run that failed before the server started has no audit to copy.
        if os.path.exists(audit):
            shutil.copyfile(audit, os.path.join(self.failed, _AUDIT_COPY))
        name = _FAILED_PREFIX + log.rung.replace(" ", "_") + _PICTURE_EXTENSION
        self.browser.screenshot_save(os.path.join(self.failed, name))

    # Stops ttyd when no rung has, as after a failure.
    def server_end(self) -> None:
        if self.ttyd is not None:
            self.ttyd.server_stop()


# The text of a file of the guide's directory, less the newline that ends it.
def _text_read(directory: str, name: str) -> str:
    path = os.path.join(directory, name)
    with open(path, encoding="utf-8", newline="") as file:
        text = file.read()
    if not text.endswith(_TEXT_END):
        raise ValueError(f"the guide's file {path} does not end in a newline")
    return text.removesuffix(_TEXT_END)


# The value with each object of `$text` alone replaced by its file's text.
def _texts_replace(value: Any, directory: str) -> Any:
    if isinstance(value, list):
        items = cast(list[Any], value)
        return [_texts_replace(item, directory) for item in items]
    if not isinstance(value, dict):
        return value
    fields = cast(dict[str, Any], value)
    if _TEXT_KEY not in fields:
        return {
            key: _texts_replace(item, directory)
            for key, item in fields.items()
        }
    if len(fields) != 1:
        raise ValueError(
            f"an object of {_TEXT_KEY} in {directory} holds other members:"
            f" {sorted(fields)}"
        )
    return _text_read(directory, fields[_TEXT_KEY])


# Adds the exit to the node that asks: a reply, and three nodes of its own.
def _exit_add(
    nodes: dict[str, Any],
    name: str,
    ask: str,
    way_out: dict[str, Any],
    path: str,
) -> None:
    replies: dict[str, Any] = nodes[name]["replies"]
    for key in (way_out["input"], way_out["resume"]):
        if key in replies:
            raise ValueError(
                f"the node {name} of {path} holds the exit's reply {key!r}"
                " already"
            )
    left, paused, resumed = [name + _EXIT_MARK + end for end in _EXIT_ENDS]
    for made in (left, paused, resumed):
        if made in nodes:
            raise ValueError(
                f"the node {made} of {path} takes a name of the exit of"
                f" {name}"
            )
    # Each reply holds a call of its own, as each call's arguments become text.
    replies[way_out["input"]] = {
        "content": None,
        "tool_calls": [copy.deepcopy(way_out["call"])],
        "next": left,
    }
    nodes[left] = {
        "replies": {},
        "after_tools": {
            "content": way_out["after"],
            "quote": _SAY_PATH,
            "next": paused,
        },
    }
    nodes[paused] = {
        "replies": {
            way_out["resume"]: {
                "content": None,
                "tool_calls": [copy.deepcopy(way_out["resume_call"])],
                "next": resumed,
            }
        },
        "otherwise": {"content": way_out["paused"], "next": paused},
    }
    nodes[resumed] = {
        "replies": {},
        "after_tools": {"content": ask, "quote": _SAY_PATH, "next": name},
    }


# Turns the `arguments` of each call of the node into its compact JSON text.
def _arguments_encode(node: dict[str, Any], name: str, path: str) -> None:
    replies: dict[str, Any] = node["replies"]
    held = [
        *replies.values(),
        *(node[key] for key in _REPLY_KEYS if key in node),
    ]
    for reply in held:
        if "tool_calls" not in reply:
            continue
        for call in reply["tool_calls"]:
            arguments = call["arguments"]
            if not isinstance(arguments, dict):
                raise ValueError(
                    f"a call of the node {name} of {path} has arguments that"
                    f" are no object: {arguments!r}"
                )
            call["arguments"] = json.dumps(
                cast(dict[str, Any], arguments),
                ensure_ascii=False,
                separators=_JSON_SEPARATORS,
            )


# The scripted table of the guide in `directory`, a `provider_script.Script`.
def table_build(directory: str) -> dict[str, Any]:
    path = os.path.join(directory, _TABLE_NAME)
    with open(path, encoding="utf-8") as file:
        loaded: object = json.load(file)
    source = cast(dict[str, Any], _texts_replace(loaded, directory))
    nodes: dict[str, Any] = source["nodes"]
    # The source's nodes alone, as an exit adds nodes of its own.
    for name in list(nodes):
        node: dict[str, Any] = nodes[name]
        if _ASK_KEY not in node:
            continue
        if _OTHERWISE_KEY in node:
            raise ValueError(
                f"the node {name} of {path} holds both {_ASK_KEY} and"
                f" {_OTHERWISE_KEY}"
            )
        ask: str = node.pop(_ASK_KEY)
        puzzled: str = source[_PUZZLED_KEY]
        node[_OTHERWISE_KEY] = {"content": f"{puzzled} {ask}", "next": name}
        if _EXIT_KEY in source:
            _exit_add(nodes, name, ask, source[_EXIT_KEY], path)
    for name, node in nodes.items():
        if node["replies"] and _OTHERWISE_KEY not in node:
            raise ValueError(
                f"the node {name} of {path} has replies and neither"
                f" {_ASK_KEY} nor {_OTHERWISE_KEY}"
            )
        _arguments_encode(node, name, path)
    return {"start": source["start"], "nodes": nodes}


# Returns the parent's pid, the second field after the name in brackets.
def _process_parent(pid: int) -> int:
    with open(f"{_PROC_PATH}/{pid}/stat", "rb") as file:
        stat = file.read()
    return int(stat[stat.rindex(b")") + 2 :].split()[1])


# The words of a process's command line.
def _command_read(pid: int) -> list[bytes]:
    with open(f"{_PROC_PATH}/{pid}/cmdline", "rb") as file:
        return file.read().split(b"\0")[:-1]


# The pids of ttyd's children that run the root's `bootstrap.py`.
def _programs_find(ttyd_pid: int, bootstrap: str) -> list[int]:
    pids: list[int] = []
    for name in os.listdir(_PROC_PATH):
        if not name.isdigit():
            continue
        pid = int(name)
        # A process can end between the listing and the reads.
        with contextlib.suppress(FileNotFoundError, ProcessLookupError):
            if _process_parent(
                pid
            ) == ttyd_pid and bootstrap.encode() in _command_read(pid):
                pids.append(pid)
    return pids


# The parameters of the root, its debug mode and verbose level the gold's.
def _parameters_make(gold: dict[str, Any]) -> dict[str, bool]:
    import switches

    return {
        **switches.switches_get(),
        "debug": gold["root_debug"],
        "verbose": gold["root_verbose"],
    }


# The page builds, the root serves the guide's table, the first render shows.
def _rung_served(run: _GuideRun) -> str:
    import xsjs_serve

    page = xsjs_serve.page_ready(run.values)
    parameters = _parameters_make(run.gold)
    xsjs_serve.root_make(run.values, page, run.root, parameters, True)
    table = table_build(os.path.join(_GUIDES_PATH, run.name))
    table_path = os.path.join(run.root, _TABLE_PATH)
    # Written before ttyd starts, as the engine seeds its store from it.
    with open(table_path, "w", encoding="utf-8") as file:
        json.dump(table, file)
    ttyd = run.server_start()
    address = ttyd.address_get()
    run.browser.page_open(address)
    served: dict[str, Any] = run.gold["served"]
    band: str = served["band"]
    run.band_wait(band)
    run.band = band
    run.picture_check(served["picture"])
    return (
        f"{address} loaded, its seed the {len(table['nodes'])} nodes of the"
        f" guide's table, and its first render shows {band!r} in the band,"
        " the box enabled and the picture the gold names"
    )


# Each step of a rung of the gold, in order.
def _rung_steps(run: _GuideRun, steps: list[dict[str, Any]]) -> str:
    for step in steps:
        run.step_take(step)
    says = [step["say"] for step in steps]
    return (
        f"typing each of {says} ended with its band, the box enabled, and the"
        " pictures and rows the gold names"
    )


# The audit holds no unexpected failure and one start of the engine.
def _rung_audit(run: _GuideRun) -> str:
    import audit_read, switches

    path = os.path.join(run.root, _AUDIT_NAME)
    while True:
        entries = audit_read.entries_parse(audit_read.document_read(path))
        opened = audit_read.requests_open(entries)
        if not opened:
            break
        run.poll_sleep(f"the replies of the audit's requests: {opened}")
    try:
        audit_read.failure_check(entries)
    except audit_read.AuditFailed as failure:
        raise CheckFailed(f"the audit of {run.root}: {failure}") from failure
    with open(path, encoding="utf-8") as file:
        starts = sum(
            line.startswith(_ENGINE_START) for line in file.read().split("\n")
        )
    if starts != 1:
        raise CheckFailed(
            f"the audit holds {starts} starts of the engine for the one load"
        )
    if switches.debug:
        shutil.copyfile(path, os.path.join(run.failed, _AUDIT_COPY))
    return (
        f"the audit's {len(entries)} entries hold no unexpected failure and"
        " one start of the engine"
    )


# Leaving the page ends the server, and ttyd stops with the gold's code.
def _rung_left(run: _GuideRun) -> str:
    ttyd = cast("xsjs_serve.TtydServer", run.ttyd)
    programs = _programs_find(ttyd.pid, run.bootstrap)
    if not programs:
        raise CheckFailed(f"no child of ttyd runs {run.bootstrap}")
    run.browser.page_open(_BLANK_URL)
    while _programs_find(ttyd.pid, run.bootstrap):
        run.poll_sleep(f"the end of {run.bootstrap} under ttyd")
    # Stopped here alone, so that no failure stops it again.
    run.ttyd = None
    code = ttyd.server_stop()
    due: int = run.gold["ttyd_code"]
    if code != due:
        raise CheckFailed(f"ttyd stopped with code {code}, not {due}")
    return (
        f"{_BLANK_URL} ended the page, the programs {programs} under ttyd"
        f" ended and ttyd stopped with code {code}"
    )


# Runs the rungs in order, each by its label, the gold's between the fixed.
def _rungs_climb(run: _GuideRun) -> None:
    log = run.log
    gold = run.gold
    label: str = gold["root_label"]
    rung_seconds: float = gold["rung_seconds"]
    if not log.book.root_enter(run.name, label):
        return
    log.rung_run(
        _SERVED_RUNG,
        label,
        functools.partial(_rung_served, run),
        gold["served_seconds"],
    )
    for rung in cast(list[dict[str, Any]], gold["rungs"]):
        log.rung_run(
            rung["rung"],
            rung["label"],
            functools.partial(_rung_steps, run, rung["steps"]),
            rung_seconds,
        )
    log.rung_run(
        _AUDIT_RUNG, label, functools.partial(_rung_audit, run), rung_seconds
    )
    log.rung_run(
        _LEFT_RUNG, label, functools.partial(_rung_left, run), rung_seconds
    )
    log.book.root_leave()


# Walks the guide in one browser, ttyd stopped whatever ended the walk.
def _walk_run(log: _RungLog, gold: dict[str, Any], name: str) -> None:
    import devtools, harness

    failed = os.path.join(_BUILD_PATH, _PROGRAM_PREFIX + name)
    # The directory holds this run's failure alone, so none misleads.
    if os.path.exists(failed):
        shutil.rmtree(failed)
    os.makedirs(failed)
    prefix = f"{_PROGRAM_PREFIX}{name}-"
    work = tempfile.mkdtemp(prefix=prefix, dir=_BUILD_PATH)
    log.line_print(f"the root of this run is in {work} until it passes")
    width: int = gold["window_width"]
    height: int = gold["window_height"]
    with devtools.Browser(width, height, devtools.LinuxPipe()) as browser:
        log.client_bind(browser.client_get())
        values = harness.settings_copy()
        run = _GuideRun(browser, log, gold, values, name, work, failed)
        try:
            _rungs_climb(run)
        except Exception:
            run.failure_take()
            raise
        finally:
            run.server_end()
    shutil.rmtree(work)


# Exits with 128 plus the signal's number, so that the walk stops ttyd.
def _signal_exit(number: int, frame: types.FrameType | None) -> None:
    sys.exit(_SIGNAL_BASE + number)


# Runs the guide test `name` with its program's arguments. The exit code.
def guide_main(arguments: list[str], name: str) -> int:
    import category, harness, switches

    parser = argparse.ArgumentParser(
        prog=f"{_PROGRAM_PREFIX}{name}.py",
        description=f"Run the guide test of python/guides/{name}/: the engine"
        " page served as xsjs_serve.py serves it, from a fresh debug root"
        " under build/ seeded with the guide's scripted table, walked step by"
        " step in chrome-headless-shell as its gold says. A failed rung keeps"
        f" its PNG and the audit in build/{_PROGRAM_PREFIX}{name}/.",
        allow_abbrev=False,
    )
    category.options_add(parser)
    switches.options_add(parser)
    parsed = parser.parse_args(arguments)
    chosen: str = parsed.category
    switches.switches_set(parsed)
    for number in (signal.SIGHUP, signal.SIGTERM):
        signal.signal(number, _signal_exit)
    gold_id = f"{_GOLD_LANGUAGE}.{_PROGRAM_PREFIX}{name}"
    gold = cast(dict[str, Any], harness.gold_get(gold_id))
    log = _RungLog(chosen, gold["rung_seconds"])
    try:
        _walk_run(log, gold, name)
    except CheckFailed as failure:
        print(f"error: {log.rung}: {failure}", file=sys.stderr)
        return _EXIT_FAILED
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    except Exception as failure:
        failure.add_note(f"the rung that ran: {log.rung}")
        raise
    return 0
