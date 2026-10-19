declare namespace console_view {
  // xterm.js in a hidden container on the UI thread, speaking ttyd's
  // client protocol: the first JSON message with columns and rows, '0'
  // input, '1' resize. Each message it sends is one `console.input`
  // line; each `console.output` line's blob is fed to it. ctrl-0
  // toggles the view, which keeps its scrollback, colours and features
  // while hidden.
  class ConsoleView {
    constructor(container: HTMLElement, tasks: queue.TaskQueue);
    view_show(): void;
    view_hide(): void;
    view_toggle(): void;
    output_feed(data: Uint8Array): void;
  }
}
