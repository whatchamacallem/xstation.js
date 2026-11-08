// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI worker once the boot has handed over its objects.
// API/ts/worker_ai.d.ts holds its rules. `tap_start` runs once per worker, so
// each of its pieces is a function of its own, for the unit suites.

namespace worker_ai {
  // The owners, settings, line types and numbers of the worker.
  const constants = Object.freeze({
    thread: "ai" as const,
    ui_owner: "ui" as const,
    server_owner: "server" as const,
    console_owner: "console" as const,
    synchronous_setting: "queue_synchronous",
    settings_type: "settings.set",
    put_type: "settings.put",
    open_type: "console.open",
    close_type: "console.close",
    exit_type: "console.exit",
    input_type: "console.input",
    write_type: "console.write",
    busy_type: "console.busy",
    idle_type: "console.idle",
    read_type: "console.read",
    output_type: "console.output",
    // The output kind byte of ttyd's messages, and the prompt of the dash.
    output_kind: 0x30,
    prompt_text: "$ ",
    second_ms: 1000,
    // The command byte of ttyd's input messages, and the end of a line.
    input_command: "0",
    line_end: "\n",
    tail_type: "audit.tail",
    tail_wake: "worker.tail_reply",
    error_type: "error",
    fault_type: "fault",
    opened_type: "worker.console_opened",
    put_wake: "worker.settings_put",
    handler_version: 0,
  });

  // Registers the handler of one line type and version, as dispatch does.
  export type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // Sends the line to the server, then calls `done` once the server has it.
  export type ServerEnd = (line: lines.Line, done: () => void) => void;

  // What the boot hands over once `tap.start` is in.
  export interface TapParts {
    first: lines.Line;
    server: queue.Port;
    end: ServerEnd;
    ui: MessagePort;
    console: wire.ConsolePort | undefined;
  }

  // What a relay's wake keeps: the request it owes the reply to.
  interface RelayState {
    request: lines.Line;
  }

  // A line of a type with its payload, in the name form this thread picks.
  function line_build(
    type: string,
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
  }

  // The owner table of the AI thread.
  export function owners_make(): queue.OwnerTable {
    return {
      "ai.": "ai",
      "tools.": "ai",
      "kv.": "ai",
      "doc.": "ai",
      "db.": "ai",
      "turn.": "ai",
      "sql.": "ai",
      "settings.put": "ai",
      "console.": "ai",
      "console.input": "console",
      "console.output": "ui",
      "console.exit": "ui",
      "console.busy": "ui",
      "console.idle": "ui",
      "audit.": "server",
      "audit.tail": "ai",
      "tap.": "server",
      fault: "ai",
    };
  }

  // How the AI's turn stands: none, waiting for tty 0, lapsed or on.
  type TurnPhase = "none" | "waiting" | "lapsed" | "on";

  // A read of the AI's that waits with its turn, and when its time ends.
  interface ReadWaiting {
    line: lines.Line;
    deadline: number;
    timer: number;
  }

  // tty 0's one writer: the AI's lines cut at newlines, the view's held.
  export class ConsoleWriter implements queue.Port {
    private readonly inner: queue.Port;
    private readonly notify_ui: (line: lines.Line) => void;
    // The AI's text after its last newline, which waits for the next write.
    private rest = "";
    // How the AI's turn stands, from its `console.busy` to its idle.
    private turn: TurnPhase = "none";
    // The view's lines that came during the turn, in order.
    private readonly held: lines.Line[] = [];
    // The AI's lines that wait with their turn, in order.
    private readonly waiting: lines.Line[] = [];
    // The AI's read that waits with its turn.
    private read: ReadWaiting | undefined = undefined;
    // Whether tty 0's output ends with the prompt since its last line.
    private concluded = false;
    // The end of tty 0's output since its last line, as long as the prompt.
    private tail = "";
    private receiver: ((line: lines.Line) => void) | undefined = undefined;

    // Takes tty 0's port and what posts the turn's busy and idle to the UI.
    constructor(inner: queue.Port, notify_ui: (line: lines.Line) => void) {
      this.inner = inner;
      this.notify_ui = notify_ui;
    }

    // Types the AI's lines, holds or passes the view's, passes the rest on.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.write_type) {
        this.text_write(jslb.payload_of(line).text as string);
      } else if (type === constants.input_type) {
        this.view_take(line);
      } else if (type === constants.read_type) {
        this.read_take(line);
      } else if (type === constants.busy_type) {
        this.busy_take();
      } else if (type === constants.idle_type) {
        this.idle_take();
      } else if (type === constants.open_type) {
        // A tty 0 that opens anew has shown no prompt yet.
        this.concluded = false;
        this.tail = "";
        this.inner.line_post(line, transfer);
      } else {
        this.inner.line_post(line, transfer);
      }
    }

    // Passes on what the port sends back, then follows tty 0's output.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
      this.inner.line_receive((line) => {
        fn(line);
        this.output_take(line);
      });
    }

    // Sends a line to tty 0, which runs until its output ends with the prompt.
    private input_send(line: lines.Line): void {
      this.concluded = false;
      this.tail = "";
      this.inner.line_post(line, []);
    }

    // Sends the view's line, held from the AI's turn's start to its end.
    private view_take(line: lines.Line): void {
      if (this.turn === "on") {
        this.held.push(line);
        return;
      }
      this.input_send(line);
    }

    // Sends each line a newline ends as one message and keeps the rest.
    private text_write(text: string): void {
      const pieces = (this.rest + text).split(constants.line_end);
      this.rest = pieces.pop() as string;
      for (const piece of pieces) {
        const typed = constants.input_command + piece + constants.line_end;
        const header = jslb.header_make(constants.input_type, {
          full: settings.names_full(),
        });
        const blob = jslb.blob_make(utility.utf8_encode(typed));
        const line = jslb.line_make(header, [blob], {});
        if (this.turn === "waiting" || this.turn === "lapsed") {
          this.waiting.push(line);
        } else {
          this.input_send(line);
        }
      }
      this.turn_wake();
    }

    // Holds the AI's read while its turn waits, its time counted, else sends.
    private read_take(line: lines.Line): void {
      if (this.turn !== "waiting" && this.turn !== "lapsed") {
        this.inner.line_post(line, []);
        return;
      }
      const seconds = jslb.payload_of(line).timeout_seconds as number;
      this.read = {
        line,
        deadline: Date.now() + seconds * constants.second_ms,
        timer: setTimeout(
          () => this.read_expire(),
          seconds * constants.second_ms,
        ),
      };
      this.turn_wake();
    }

    // Answers the waiting read as timed out with no text, its turn lapsed.
    private read_expire(): void {
      const read = this.read as ReadWaiting;
      this.read = undefined;
      const header = jslb.header_make(constants.read_type, {
        reply: jslb.field_get(read.line[0], "id") as number,
        full: settings.names_full(),
      });
      const reply = jslb.line_make(header, [], { text: "", timed_out: true });
      this.turn = "lapsed";
      (this.receiver as (line: lines.Line) => void)(reply);
    }

    // Starts the AI's turn on a concluded tty 0, else lets it wait.
    private busy_take(): void {
      if (this.turn !== "none") {
        throw new Error(i18n("worker_ai.busy_twice"));
      }
      this.turn = "waiting";
      this.turn_wake();
    }

    // Ends the turn: started, its idle posted and the view's lines sent.
    private idle_take(): void {
      const turn = this.turn;
      if (turn === "none") {
        throw new Error(i18n("worker_ai.idle_unheld"));
      }
      this.turn = "none";
      if (turn !== "on") {
        // A turn that never started sent nothing, and its lines are dropped.
        this.waiting.splice(0);
        return;
      }
      this.inner.line_post(line_build(constants.idle_type, {}), []);
      this.notify_ui(line_build(constants.idle_type, {}));
      for (const line of this.held.splice(0)) {
        this.input_send(line);
      }
    }

    // A lapsed turn waits again at the AI's next act, and starts if it can.
    private turn_wake(): void {
      if (this.turn === "lapsed") {
        this.turn = "waiting";
      }
      if (this.turn === "waiting" && this.concluded) {
        this.turn_begin();
      }
    }

    // Starts the turn: the busy to tty 0 and the UI, the AI's lines, its read.
    private turn_begin(): void {
      this.turn = "on";
      this.inner.line_post(line_build(constants.busy_type, {}), []);
      this.notify_ui(line_build(constants.busy_type, {}));
      for (const line of this.waiting.splice(0)) {
        this.input_send(line);
      }
      const read = this.read;
      if (read === undefined) {
        return;
      }
      this.read = undefined;
      clearTimeout(read.timer);
      const left = Math.max(0, read.deadline - Date.now());
      const payload = {
        ...jslb.payload_of(read.line),
        timeout_seconds: left / constants.second_ms,
      };
      this.inner.line_post(jslb.line_make(read.line[0], [], payload), []);
    }

    // Follows tty 0's output to its prompt, which starts a waiting turn.
    private output_take(line: lines.Line): void {
      if (jslb.field_get(line[0], "type") !== constants.output_type) {
        return;
      }
      const blob = line[1] as lines.BlobHeader;
      const data = jslb.field_get(blob, "data") as Uint8Array;
      if (data[0] !== constants.output_kind) {
        return;
      }
      const prompt = constants.prompt_text;
      const ending = data.subarray(Math.max(1, data.length - prompt.length));
      this.tail = (this.tail + String.fromCharCode(...ending)).slice(
        -prompt.length,
      );
      this.concluded = this.tail === prompt;
      if (this.turn === "waiting" && this.concluded) {
        this.turn_begin();
      }
    }
  }

  // Registers the relays of the UI's `console.open` and `console.close`.
  export function console_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
    close: () => void,
  ): void {
    const version = constants.handler_version;
    // Opens tty 0 through the console port and sleeps until it is open.
    register(constants.open_type, version, (line) => {
      const copy = line_build(constants.open_type, {});
      const id = tasks.task_submit(copy, constants.console_owner);
      const state: RelayState = { request: line };
      return dispatch.task_sleep(state, [id], constants.opened_type);
    });
    // Answers the UI with the token the console port fetched.
    register(constants.opened_type, version, (line) => {
      const { request } = line.state as RelayState;
      const replies = line.replies as lines.Line[];
      const token = jslb.payload_of(replies[0]).token;
      return dispatch.reply_make(request, { token });
    });
    // Closes tty 0 through the console port, whose end follows as the exit.
    register(constants.close_type, version, (line) => {
      close();
      return dispatch.reply_make(line, {});
    });
  }

  // Adds tty 0's port in a writer as the console's owner, relays, exit push.
  export function console_attach(
    tasks: queue.TaskQueue,
    port: wire.ConsolePort,
  ): void {
    const notify_ui = (line: lines.Line): void =>
      tasks.line_notify(line, constants.ui_owner);
    tasks.port_add(
      constants.console_owner,
      new ConsoleWriter(port, notify_ui),
    );
    console_register(tasks, dispatch.handler_register, () =>
      port.console_close(),
    );
    port.close_receive((code) => {
      const exit = line_build(constants.exit_type, { code });
      tasks.line_notify(exit, constants.ui_owner);
    });
  }

  // Registers the relay of a `settings.put` notice to the server as a request.
  export function settings_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
    live: settings.Settings,
  ): void {
    const version = constants.handler_version;
    // Changes this thread's live settings, then submits them to the server.
    register(constants.put_type, version, (line) => {
      const payload = jslb.payload_of(line);
      // A copy, so a later change of the live value cannot alter the line.
      Object.assign(live, JSON.parse(utility.json_text(payload.settings)));
      const copy = line_build(constants.put_type, payload);
      const id = tasks.task_submit(copy, constants.server_owner);
      return dispatch.task_sleep(null, [id], constants.put_wake);
    });
    register(constants.put_wake, version, () => undefined);
  }

  // Relays the UI's `audit.tail` to the server and its reply back.
  export function tail_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
  ): void {
    const version = constants.handler_version;
    // Asks the server for the end of the audit and sleeps on it.
    register(constants.tail_type, version, (line) => {
      const copy = line_build(constants.tail_type, jslb.payload_of(line));
      const id = tasks.task_submit(copy, constants.server_owner);
      const state: RelayState = { request: line };
      return dispatch.task_sleep(state, [id], constants.tail_wake);
    });
    // Answers the UI with the server's text.
    register(constants.tail_wake, version, (line) => {
      const { request } = line.state as RelayState;
      const replies = line.replies as lines.Line[];
      return dispatch.reply_make(request, jslb.payload_of(replies[0]));
    });
  }

  // Synchronous mode, from `queue_synchronous`, which needs debug mode.
  export function synchronous_read(
    settings_get: (id: string) => unknown,
    debug_on: () => boolean,
  ): boolean {
    const synchronous = settings_get(constants.synchronous_setting) === true;
    if (synchronous && !debug_on()) {
      throw new Error(i18n("worker_ai.synchronous_release"));
    }
    return synchronous;
  }

  // Sends the cascade as an `error` line by `end`, which calls `done`.
  export function error_send(
    end: ServerEnd,
    cascade: lines.ErrorCause,
    done: () => void,
  ): void {
    const payload: { [key: string]: unknown } = {
      message: cascade.message,
      stack: cascade.stack,
    };
    if (cascade.cause !== undefined) {
      payload.cause = cascade.cause;
    }
    end(line_build(constants.error_type, payload), done);
  }

  // Registers the UI's `fault`: its cascade sent on, then `close` called.
  export function fault_register(
    register: HandlerRegister,
    end: ServerEnd,
    close: () => void,
  ): void {
    register(constants.fault_type, constants.handler_version, (line) => {
      const fault = jslb.payload_of(line) as unknown as lines.Fault;
      const { message, stack, cause } = fault;
      error_send(end, { message, stack, cause }, close);
      return undefined;
    });
  }

  // The bring up above, `run` the worker's program or a test page's entry.
  export function tap_start(
    parts: TapParts,
    run: (tasks: queue.TaskQueue) => void,
  ): void {
    const payload = jslb.payload_of(parts.first) as unknown as lines.TapStart;
    switches.switches_set(payload.switches);
    settings.settings_set(payload.settings);
    if (switches.debug_on()) {
      harness.values_set(payload.settings);
    }
    const tasks = new queue.TaskQueue(
      constants.thread,
      owners_make(),
      synchronous_read(settings.settings_get, switches.debug_on),
    );
    tasks.limit_attach(settings.settings_get);
    if (switches.debug_on()) {
      tasks.audit_attach();
    }
    tasks.port_add(constants.ui_owner, new queue.ThreadPort(parts.ui));
    tasks.port_add(constants.server_owner, parts.server);
    settings_register(tasks, dispatch.handler_register, payload.settings);
    tail_register(tasks, dispatch.handler_register);
    settings.sender_register((put: lines.SettingsPut) => {
      const line = line_build(constants.put_type, { settings: put.settings });
      tasks.line_notify(line, constants.thread);
    });
    error_overlay.report_register((thrown, done) =>
      error_send(parts.end, dispatch.cause_make(thrown), done),
    );
    fault_register(dispatch.handler_register, parts.end, () => self.close());
    if (parts.console !== undefined) {
      console_attach(tasks, parts.console);
    }
    const notice: { [key: string]: unknown } = {
      settings: payload.settings,
      switches: payload.switches,
    };
    const set = line_build(constants.settings_type, notice);
    tasks.line_notify(set, constants.ui_owner);
    parts.server.line_post(dispatch.reply_make(parts.first, {}), []);
    // The engine role reads the Empty reply first and alone.
    if (switches.debug_on()) {
      tasks.audit_open();
    }
    run(tasks);
  }
}

Object.freeze(worker_ai);
