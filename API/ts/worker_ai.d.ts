// The AI worker once the boot has handed over its objects. At bring-up it
// sets this thread's settings, its switches and, in debug mode, the gold
// record from `tap.start`, builds the queue with its ports to the UI thread
// and to the server, sends `settings.set`, the settings, the switches and
// any gold, to the UI thread, answers `tap.start` with an
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
// The boot hands over the server's lane as a `queue.Port` and an end
// function: the ttyd page's wire, `wire.WirePort`, and its `wire_end`; the
// headless page's realm lane, a `queue.ThreadPort`, and a post of the line.
// The ttyd page's boot also hands over tty 0's port, a `wire.ConsolePort`
// at the page's address, which `tap_start` adds as the `console` owner's
// port, whose UI relays it registers by `console_register` with the port's
// `console_close`, and whose close it pushes to the UI as `console.exit`
// with the code; the headless page hands over none, as it has no ttyd.
//
// Faults: the worker registers its report function, which sends an `error`
// line with the cascade of the thrown value by `dispatch.cause_make` through
// the end function, whose callback runs once the server has the line: on
// the ttyd page once the server, having logged it, has ended the socket. A
// `fault` line of the UI thread is sent on the same way, its cascade as it
// came, and at that callback the worker closes itself. `tap_start` runs once
// per worker, so each of its pieces is a function of its own, for the unit
// suites.
//
// The overlay's note is a piece of the program the suites build toward and
// runs nowhere at bring-up.

declare namespace worker_ai {
  // Sends the line to the server, then calls `done` once the server has it.
  type ServerEnd = (line: lines.Line, done: () => void) => void;

  // What the boot hands over once `tap.start` is in.
  interface TapParts {
    first: lines.Line;
    server: queue.Port;
    end: ServerEnd;
    ui: MessagePort;
    console: wire.ConsolePort | undefined;
  }

  // The owner table of the AI thread.
  function owners_make(): queue.OwnerTable;

  // The port that logs each line it carries both ways, then passes it on.
  class WireTap implements queue.Port {
    constructor(inner: queue.Port, note: (text: string) => void);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Synchronous mode, from `queue_synchronous`, which needs debug mode.
  function synchronous_read(settings_get: (id: string) => unknown): boolean;

  // Relays the UI's `settings.put` to the server, `live` changed first.
  function settings_register(
    tasks: queue.TaskQueue,
    register: (type: string, version: number, fn: dispatch.Handler) => void,
    live: settings.Settings,
  ): void;

  // Adds tty 0's port as the `console` owner's, its relays and its exit push.
  function console_attach(
    tasks: queue.TaskQueue,
    port: wire.ConsolePort,
  ): void;

  // Relays the UI's `console.open` to tty 0, and its `console.close`.
  function console_register(
    tasks: queue.TaskQueue,
    register: (type: string, version: number, fn: dispatch.Handler) => void,
    close: () => void,
  ): void;

  // What takes each rendered line: an `overlay.line` of tty 1, then `log`.
  function note_make(
    tasks: queue.TaskQueue,
    log: (text: string) => void,
  ): (text: string) => void;

  // Sends the cascade as an `error` line by `end`, which calls `done`.
  function error_send(
    end: ServerEnd,
    cascade: lines.ErrorCause,
    done: () => void,
  ): void;

  // Registers the UI's `fault`: its cascade sent on, then `close` called.
  function fault_register(
    register: (type: string, version: number, fn: dispatch.Handler) => void,
    end: ServerEnd,
    close: () => void,
  ): void;

  // The bring up described above. `run` gets the queue for the suites.
  function tap_start(
    parts: TapParts,
    run: (tasks: queue.TaskQueue) => void,
  ): void;
}
