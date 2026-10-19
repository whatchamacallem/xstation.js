declare namespace boot {
  // The one bundle runs on two threads. `boot_run` reads `self.name`:
  // undefined on the main thread, "ai" in the worker.
  function boot_run(): void;

  // UI: error_overlay installed first; builds the DOM, creates the AI
  // worker from the bundle's Blob URL, owns the UI queue with its media
  // port and its DOM port, routes input, paints renders, hosts the
  // console view and the overlays, shows permission requests.
  function page_main(): void;

  // The DOM port of the UI thread: its listeners post `ui.input` as
  // notifications, and it answers `dom.choice` when a button of the
  // permission request is clicked. Listeners are events, not promises.
  class DomPort implements queue.Port {
    constructor(container: HTMLElement);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // AI: the owner table, the store, the wire and console ports, the
  // HTTP or scripted port, the MCP servers and clients, the agent, the
  // forwarding of replication.
  function worker_ai_main(): void;
}
