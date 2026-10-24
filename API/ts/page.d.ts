// The UI thread: the AI worker made from the texts of the worker scripts and
// the channel to it, the queue built on the settings the worker sends first,
// and the pieces of the UI the test suites build toward: the DOM port of the
// player's text, clicks and control keys and of the permit buttons, the media
// port, the console view, the overlays, and the handlers that paint renders,
// keep media, ask permits, carry the player's turns and show the console.
//
// Every line the UI thread builds takes the form `settings.names_full()`
// picks, the DOM port's `ui.input` and `ui.control_key` and the page's own
// `fault` line included.
//
// `console.show`, a request of the AI worker, shows the console view as
// ctrl 0 does, then answers once tty 0 is open: at once when `open_is()`,
// else, when the shown view `open_wanted()`, through `open_request()`, whose
// sleep the handler takes over with the wake `ui.console_shown`, which runs
// `open_done` and replies Empty. A view that is opening or closing cannot
// answer and throws `page.console_busy`.
//
// A worker's `fault` line shows the fault screen, its stack followed by each
// cause's message and stack, then the page terminates the worker, which has
// already reported it to the server and seen the server end the wire. The
// page's own fault goes to the worker as a `fault` line, posted on the
// channel by the stop function, its cascade under `cause`.

declare namespace page {
  // Registers the handler of one line type and version, as dispatch does.
  type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // The decoded images the page paints, by key, as the media port keeps them.
  interface ImageSource {
    image_get(k: lines.KvRef): ImageBitmap | undefined;
  }

  // The console view as the handlers drive it.
  interface ConsoleControl {
    view_toggle(): void;
    view_show(): void;
    open_wanted(): boolean;
    open_is(): boolean;
    open_request(): dispatch.Sleep;
    open_done(wake: lines.Line): void;
    close_done(wake: lines.Line): void;
    exit_done(): void;
    output_feed(data: Uint8Array): void;
  }

  // The overlays as the handlers drive them.
  interface OverlayControl {
    line_add(tty: number, text: string): void;
    overlay_toggle(tty: number): void;
  }

  // What the UI handlers work with: the queue, the elements and the parts.
  interface PageParts {
    tasks: queue.TaskQueue;
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    input: HTMLInputElement;
    permit: HTMLElement;
    images: ImageSource;
    view: ConsoleControl;
    overlays: OverlayControl;
    debug: boolean;
  }

  // The owner table of the UI thread.
  function owners_make(): queue.OwnerTable;

  // The first line of the worker, which is `settings.set`, taken whole.
  function settings_take(data: unknown): lines.SettingsSet;

  // The fault a message of the worker carries, which must be a `fault` line.
  function fault_read(data: unknown): lines.Fault;

  // The DOM port: listeners post `ui.input` and `ui.control_key` lines.
  class DomPort implements queue.Port {
    constructor(container: HTMLElement);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Registers the handlers of the UI thread with the register given.
  function handlers_register(
    parts: PageParts,
    register: HandlerRegister,
  ): void;

  // The bring up of the UI thread, `run` getting its queue at `ui.tests`.
  function test_page(run: (tasks: queue.TaskQueue) => void): void;
}
