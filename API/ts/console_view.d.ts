// xterm.js in a hidden container on the UI thread, speaking ttyd's client
// protocol to tty 0 through the AI worker. Its lines are built in the form
// `settings.names_full()` picks. ttyd's client messages: the first one is
// JSON with `AuthToken`, `columns` and `rows`, the size of the terminal when
// tty 0 opens; then '0' and the typed bytes. The view sends no resize: the
// rows it fits to the page at a show are the size the first message gives,
// and a later fit changes only the terminal on the page, which is debug only.
// ttyd's server messages, each one `console.output` line: '0' output, '1'
// the title and '2' the preferences, the last two ignored. ctrl 0 toggles the
// view, which keeps its scrollback, colours and features while hidden. While
// the AI's command runs, from `console.busy` to `console.idle`, the view takes
// no keystrokes, and the person watches the command and its output.
//
// The person's line is held in the view: printable text and Tab join it,
// Backspace removes its last character, and Enter submits it whole with its
// carriage return as one `console.input`; every other control key and
// escape sequence is dropped. A paste is cut at its carriage returns, each
// whole line submitted in order and the rest held. The view echoes the held
// line at the cursor and erases that echo before it submits, before it
// writes output, which the echo then follows, and at `console.busy`; at
// `console.idle` the line is echoed again and the person goes on typing it.
// The view finds its echo by xterm's buffer, and saves no cursor of its own,
// so that a program's saved cursor stays the program's. Drawing the echo
// records its start: its row in the whole buffer, the viewport's base plus
// the cursor's row, held by an xterm marker that xterm moves when the
// scrollback drops its oldest rows, and the cursor's column. The erase moves
// the cursor to that row of the screen, the start's row less the base then,
// and that column, and erases below, so that an echo that scrolled the
// screen is erased from its own start. A start that has scrolled above the
// screen, a held line longer than the screen, is erased from the screen's
// top, and its part above stays in the scrollback, which no escape reaches.
// The view injects no newline: an echo that started at a pending wrap, the
// program's last character in the row's last column, is erased from the
// next row, then the filled row's last cell is written again from xterm's
// buffer, its character, a wide one from its first column, and its
// attributes as SGR, and then the attributes of the echo's first cell,
// the program's own, so that the wrap is pending again as the program left
// it and the program's next carriage return goes back to that row. An echo
// whose filled row has scrolled above the screen cannot have its wrap made
// pending again, and is erased from the screen's top.
// The view's writes go to the terminal one at a time, each once xterm has
// parsed the one before, so that the buffer it reads is the one its write
// meets.

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
    // Takes no keystrokes while the AI's command runs, at `console.busy`.
    input_hold(): void;
    // Takes keystrokes again while tty 0 is open, at `console.idle`.
    input_free(): void;
    output_feed(data: Uint8Array): void;
  }
}
