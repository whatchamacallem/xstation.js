// xterm.js in a hidden container on the UI thread, speaking ttyd's client
// protocol to tty 0 through the AI worker. The view sends no resize: the rows
// it fits at a show are the size the first message gives, and a later fit
// changes only the terminal on the page, which is debug only. ctrl 0 toggles
// the view, which keeps its state while hidden.
//
// The person's line is held in the view until Enter submits it whole, and
// every control key and escape sequence but Tab and Backspace is dropped. The
// view echoes the held line and erases that echo before it submits, before it
// writes output and at `console.busy`. It finds its echo by xterm's buffer and
// saves no cursor of its own, so that a program's saved cursor stays the
// program's. An xterm marker holds the echo's start row, as xterm moves it
// when the scrollback drops rows. A start above the screen is erased from the
// screen's top, its part above staying in the scrollback, which no escape
// reaches. The view injects no newline: an echo that started at a pending wrap
// is erased from the next row, then the filled row's last cell is written
// again with its attributes, so that the wrap is pending again as the program
// left it. Writes go to the terminal one at a time, each once xterm has parsed
// the one before, so that the buffer the view reads is the one its write
// meets.

declare namespace console_view {
  class ConsoleView {
    constructor(container: HTMLElement, tasks: queue.TaskQueue);
    view_show(): void;
    view_hide(): void;
    // Shows a hidden view, hides a shown one, and says whether it now shows.
    view_toggle(): boolean;
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
