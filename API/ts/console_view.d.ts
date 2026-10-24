// xterm.js in a hidden container on the UI thread, speaking ttyd's client
// protocol to tty 0 through the AI worker. Its lines are built in the form
// `settings.names_full()` picks. ttyd's client messages: the first one is
// JSON with `AuthToken`, `columns` and `rows`, the size of the terminal when
// tty 0 opens; then '0' and the typed bytes. The view sends no resize: the
// rows it fits to the page at a show are the size the first message gives,
// and a later fit changes only the terminal on the page, which is debug only.
// ttyd's server messages, each one `console.output` line: '0' output, '1'
// the title and '2' the preferences, the last two ignored. ctrl 0 toggles the
// view, which keeps its scrollback, colours and features while hidden.

declare namespace console_view {
  class ConsoleView {
    constructor(container: HTMLElement, tasks: queue.TaskQueue);
    view_show(): void;
    view_hide(): void;
    view_toggle(): void;
    // Whether the view is shown while tty 0 is idle, so that it is asked for.
    open_wanted(): boolean;
    // Whether tty 0 is open: its first message sent and input taken.
    open_is(): boolean;
    // Asks the AI worker for tty 0 from a UI handler, which returns the sleep.
    open_request(): dispatch.Sleep;
    // Takes the wake of that sleep, sends the first message, takes input.
    open_done(wake: lines.Line): void;
    // Asks the AI worker to close tty 0, from a UI handler that sleeps.
    close_request(): dispatch.Sleep;
    close_done(wake: lines.Line): void;
    // Ends tty 0: the screen stays, input is off, a later show opens it.
    exit_done(): void;
    output_feed(data: Uint8Array): void;
  }
}
