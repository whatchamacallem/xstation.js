// The AI worker once the boot has handed over its objects. `tap_start` calls
// `run` in every mode, at once after the Empty reply and outside any task, so
// it may notify but not submit. In debug mode the server's port is a
// `WireTap`, which logs each line it carries but a `verbose.put`.
//
// The `ConsoleWriter` is tty 0's one writer, one command line at a time. It
// knows tty 0 concluded when its output ends with the prompt `$ `, and running
// from a line's submission until then. The AI's `console.busy` starts its turn
// on a concluded tty 0 only: on a running one the AI's lines and its
// `console.read` wait, while the view's lines go at once, as input to the
// person's own command. From the busy to the AI's `console.idle` the view's
// lines wait, so a view's line is never joined to the AI's. A waiting read
// whose timeout passes is answered as timed out and its turn lapses, starting
// again only at the AI's next write or read. An idle on a waiting or lapsed
// turn posts nothing and drops the AI's waiting lines.
//
// Faults: the report function sends an `error` line through the end function,
// whose callback runs once the server has the line: on the ttyd page once the
// server, having logged it, has ended the socket. A `fault` line of the UI
// thread goes the same way, and at that callback the worker closes itself.

declare namespace worker_ai {
  // Registers the handler of one line type and version, as dispatch does.
  type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // Sends the line to the server, then calls `done` once the server has it.
  type ServerEnd = (line: lines.Line, done: () => void) => void;

  // What the boot hands over once `tap.start` is in.
  interface TapParts {
    first: lines.Line;
    server: queue.Port;
    end: ServerEnd;
    ui: MessagePort;
    console: wire.ConsolePort | undefined;
    // Whether the `WireTap` notes through `note_make`: the engine page alone.
    overlay: boolean;
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
  function synchronous_read(
    settings_get: (id: string) => unknown,
    debug_on: () => boolean,
  ): boolean;

  // Relays the UI's `settings.put` to the server, `live` changed first.
  function settings_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
    live: settings.Settings,
  ): void;

  // tty 0's one writer: the AI's lines cut at newlines, the view's held.
  class ConsoleWriter implements queue.Port {
    // Takes tty 0's port and what posts the turn's busy and idle to the UI.
    constructor(inner: queue.Port, notify_ui: (line: lines.Line) => void);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Adds tty 0's port in a writer as the `console` owner's, relays, exit push.
  function console_attach(
    tasks: queue.TaskQueue,
    port: wire.ConsolePort,
  ): void;

  // Relays the UI's `console.open` to tty 0, and its `console.close`.
  function console_register(
    tasks: queue.TaskQueue,
    register: HandlerRegister,
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
    register: HandlerRegister,
    end: ServerEnd,
    close: () => void,
  ): void;

  // The bring up above, `run` the worker's program or a test page's entry.
  function tap_start(
    parts: TapParts,
    run: (tasks: queue.TaskQueue) => void,
  ): void;
}
