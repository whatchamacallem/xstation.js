// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The AI worker once the boot has handed over its objects. At bring up it
// sets this thread's settings and, in debug mode, the gold record from
// `tap.start`, builds the queue with its ports to the UI thread and to the
// server, sends `settings.set` to the UI thread, answers `tap.start` with an
// Empty reply, and in debug mode notifies itself `worker.tests`, whose task
// runs the worker's suites by `run`, which sends `ui.tests` when its stream
// ends. Outside debug mode no gold arrives, so no suite runs and nothing
// else does. Every line the worker builds takes the form
// `settings.names_full()` picks.
//
// In debug mode the server's port is a `WireTap`: each line it carries is
// logged with `verbose.log` as its rendering by `jslb.line_render`, unless
// that text would not fit one `verbose.put` below `line_max`, by
// `queue.entry_fits`; such a line is logged as its header and the sizes of
// its payload and blobs only. A `verbose.put` it sends is not logged.
//
// Faults: the worker registers its report function, which sends an `error`
// line with the cascade of the thrown value by `dispatch.cause_make` through
// `wire.WirePort.wire_end`, whose callback runs once the server, having
// logged it, has ended the socket. A `fault` line of the UI thread is sent
// on the same way, its cascade as it came, and at that callback the worker
// closes itself. `tap_start` runs once per worker, so each of its pieces is
// a function of its own, for the unit suites.
//
// The relays of the console and the overlay's note are pieces of the program
// the suites build toward and run nowhere at bring up.

namespace worker_ai {
  // The owners, settings, line types and numbers of the worker.
  const constants = Object.freeze({
    thread: "ai" as const,
    ui_owner: "ui" as const,
    server_owner: "server" as const,
    console_owner: "console" as const,
    debug_setting: "debug",
    synchronous_setting: "queue_synchronous",
    line_setting: "line_max",
    settings_type: "settings.set",
    put_type: "settings.put",
    open_type: "console.open",
    close_type: "console.close",
    overlay_type: "overlay.line",
    verbose_type: "verbose.put",
    error_type: "error",
    fault_type: "fault",
    opened_type: "worker.console_opened",
    put_wake: "worker.settings_put",
    tests_type: "worker.tests",
    handler_version: 0,
    wire_tty: 1,
  });

  // Registers the handler of one line type and version, as dispatch does.
  export type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // What the boot hands over once `tap.start` is in.
  export interface TapParts {
    first: lines.Line;
    wire: wire.WirePort;
    ui: MessagePort;
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

  // The note of a line: its rendering if it fits a verbose entry, else sizes.
  function note_text(
    line: lines.Line,
    rendered: string,
    sized: string,
  ): string {
    const text = i18n(rendered, jslb.line_render(line));
    const line_max = settings.settings_get(constants.line_setting) as number;
    if (queue.entry_fits(constants.thread, text, line_max)) {
      return text;
    }
    const header = utility.json_text(line[0]);
    const payload = utility.json_text(jslb.payload_of(line));
    const blobs = jslb.headers_of(line).slice(1) as lines.BlobHeader[];
    const sizes = blobs.map((blob) => jslb.field_get(blob, "size"));
    return i18n(
      sized,
      header,
      utility.utf8_encode(payload).length,
      utility.json_text(sizes),
    );
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
      "verbose.": "server",
      "tap.": "server",
      fault: "ai",
    };
  }

  // A port that logs each line it carries both ways, then passes it on.
  export class WireTap implements queue.Port {
    private readonly inner: queue.Port;
    private readonly note: (text: string) => void;

    // Takes the port it wraps and what takes the text of each line.
    constructor(inner: queue.Port, note: (text: string) => void) {
      this.inner = inner;
      this.note = note;
    }

    // Notes the line as sent unless it forwards the log, then posts it.
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void {
      // Noted, a `verbose.put` would be forwarded and noted again, forever.
      if (jslb.field_get(line[0], "type") !== constants.verbose_type) {
        this.note(
          note_text(
            line,
            "worker_ai.overlay_sent",
            "worker_ai.overlay_sent_sized",
          ),
        );
      }
      this.inner.line_post(line, transfer);
    }

    // Notes each line received before the receiver takes it.
    line_receive(fn: (line: lines.Line) => void): void {
      this.inner.line_receive((line: lines.Line) => {
        this.note(
          note_text(
            line,
            "worker_ai.overlay_received",
            "worker_ai.overlay_received_sized",
          ),
        );
        fn(line);
      });
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

  // What takes each rendered line of the wire: tty 1's overlay, then `log`.
  export function note_make(
    tasks: queue.TaskQueue,
    log: (text: string) => void,
  ): (text: string) => void {
    return (text: string) => {
      const line = line_build(constants.overlay_type, {
        tty: constants.wire_tty,
        text,
      });
      tasks.line_notify(line, constants.ui_owner);
      log(text);
    };
  }

  // Synchronous mode, from `queue_synchronous`, which needs debug mode.
  export function synchronous_read(
    settings_get: (id: string) => unknown,
  ): boolean {
    const synchronous = settings_get(constants.synchronous_setting) === true;
    if (synchronous && settings_get(constants.debug_setting) !== true) {
      throw new Error(i18n("worker_ai.synchronous_release"));
    }
    return synchronous;
  }

  // Sends the cascade as an `error` line by `wire_end`, then calls `done`.
  export function error_send(
    port: wire.WirePort,
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
    port.wire_end(line_build(constants.error_type, payload), done);
  }

  // Registers the UI's `fault`: its cascade sent on, then `close` called.
  export function fault_register(
    register: HandlerRegister,
    port: wire.WirePort,
    close: () => void,
  ): void {
    register(constants.fault_type, constants.handler_version, (line) => {
      const fault = jslb.payload_of(line) as unknown as lines.Fault;
      const { message, stack, cause } = fault;
      error_send(port, { message, stack, cause }, close);
      return undefined;
    });
  }

  // The bring up described above. `run` gets the queue for the suites.
  export function tap_start(
    parts: TapParts,
    run: (tasks: queue.TaskQueue) => void,
  ): void {
    const payload = jslb.payload_of(parts.first) as unknown as lines.TapStart;
    settings.settings_set(payload.settings);
    const gold = payload.test_settings;
    if (gold !== undefined) {
      harness.values_set(payload.settings, gold);
    }
    const tasks = new queue.TaskQueue(
      constants.thread,
      owners_make(),
      synchronous_read(settings.settings_get),
    );
    tasks.sink_attach(verbose.sink_set, settings.settings_get);
    tasks.port_add(constants.ui_owner, new queue.ThreadPort(parts.ui));
    const debug = settings.settings_get(constants.debug_setting) === true;
    const server: queue.Port = debug
      ? new WireTap(parts.wire, verbose.log)
      : parts.wire;
    tasks.port_add(constants.server_owner, server);
    settings_register(tasks, dispatch.handler_register, payload.settings);
    settings.sender_register((put: lines.SettingsPut) => {
      const line = line_build(constants.put_type, { settings: put.settings });
      tasks.line_notify(line, constants.thread);
    });
    error_overlay.report_register((thrown, done) =>
      error_send(parts.wire, dispatch.cause_make(thrown), done),
    );
    fault_register(dispatch.handler_register, parts.wire, () => self.close());
    const notice: { [key: string]: unknown } = { settings: payload.settings };
    if (gold !== undefined) {
      notice.test_settings = gold;
    }
    const set = line_build(constants.settings_type, notice);
    tasks.line_notify(set, constants.ui_owner);
    server.line_post(dispatch.reply_make(parts.first, {}), []);
    if (debug) {
      dispatch.handler_register(
        constants.tests_type,
        constants.handler_version,
        () => {
          run(tasks);
          return undefined;
        },
      );
      const tests = line_build(constants.tests_type, {});
      tasks.line_notify(tests, constants.thread);
    }
  }
}

Object.freeze(worker_ai);
