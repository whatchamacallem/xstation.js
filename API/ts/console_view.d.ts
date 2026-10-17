declare namespace console_view {
  // xterm.js in a hidden container on the UI thread. Output bytes from
  // the dash pty go to the terminal; the terminal's input goes to
  // `send`. ESC toggles the view when the console is enabled.
  class ConsoleView {
    constructor(
      container: HTMLElement,
      columns: number,
      rows: number,
      send: (data: Uint8Array) => void
    );
    view_show(): void;
    view_hide(): void;
    view_toggle(): void;
    visible(): boolean;
    output_write(data: Uint8Array): void;
    // Shows the exit line and stops taking input.
    exit_show(code: number): void;
  }
}
