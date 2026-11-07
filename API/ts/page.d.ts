// The UI thread: the AI worker made from the texts of the worker scripts and
// the channel to it, the queue built on the settings the worker sends first,
// and the pieces of the UI, which the engine page's program builds. The test
// page waits for `ui.tests`; `engine_page` runs its function at `settings.set`
// itself, in every mode and outside any task, so it may notify but not submit.
// The box takes the focus each time it opens: at the first render and at each
// turn's end, as a disabled box loses the focus. An open box takes it too when
// ctrl 0 hides the console.
//
// `console.show`, a request of the AI worker, shows the console view as ctrl 0
// does. An idle view asks for tty 0 and answers once it opens; any other view
// answers at once, as tty 0's writer holds the AI's lines until dash's prompt.
// `console.busy` and `console.idle`, pushes of the AI worker around its
// command, hold and free the view's keys.
//
// A worker's `fault` line shows the fault screen, its stack followed by each
// cause's message and stack, then the page terminates the worker, which has
// already reported it to the server and seen the server end the wire. The
// page's own fault goes to the worker as a `fault` line, its cascade under
// `cause`.

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
    view_toggle(): boolean;
    view_show(): void;
    open_wanted(): boolean;
    open_request(): dispatch.Sleep;
    open_done(wake: lines.Line): void;
    close_done(wake: lines.Line): void;
    exit_done(): void;
    output_feed(data: Uint8Array): void;
    input_hold(): void;
    input_free(): void;
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

  // The engine page's bring up, `run` getting its queue at `settings.set`.
  function engine_page(run: (tasks: queue.TaskQueue) => void): void;
}
