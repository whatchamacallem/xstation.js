// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the console view with a fake terminal on a container above a band
// in a frame of a fixed size, put in the page by each test and taken out after
// it, and a real task queue of the UI thread in synchronous mode whose port to
// the AI worker is a double.
namespace test_console_view {
  // The test type prefix, the types, a token, the frame and the fake's cells.
  const constants = Object.freeze({
    type_prefix: "console_view_test.",
    wake_type: "ui.console_reply",
    closed_type: "ui.console_closed",
    open_type: "console.open",
    close_type: "console.close",
    input_type: "console.input",
    token: "dXNlcjpwYXNz",
    // The pixel sizes of the frame, band and cells, chosen by their writer.
    frame_width: 1000,
    frame_height: 400,
    band_height: 50,
    cell_width: 8,
    cell_height: 17,
  });

  // How many types the tests have made, so that each one is new.
  let types_made = 0;

  // Whether the wake handlers are registered, which happens once per bundle.
  let wake_registered = false;

  // The view of the last rig made, to which the wake handler passes wakes.
  let wake_view: console_view.ConsoleView | undefined = undefined;

  // The rigs made since the last `setUp`, whose frames `tearDown` takes out.
  let rigs_made: ViewRig[] = [];

  // The options a terminal is made with.
  interface TerminalOptions {
    cols: number;
    rows: number;
    disableStdin: boolean;
  }

  // A stand in for the xterm.js terminal that records what the view does.
  class FakeTerminal {
    // Every terminal made since the last `setUp`, in order.
    static made: FakeTerminal[] = [];
    cols: number;
    rows: number;
    options: { disableStdin: boolean };
    focused = 0;
    opened: HTMLElement[] = [];
    written: Uint8Array[] = [];
    resized: [number, number][] = [];
    screen: HTMLElement | undefined = undefined;
    data_listener: ((data: string) => void) | undefined = undefined;
    resize_listener:
      ((size: { cols: number; rows: number }) => void) | undefined = undefined;

    // Records the terminal as made, with its size and its input option.
    constructor(options: TerminalOptions) {
      this.cols = options.cols;
      this.rows = options.rows;
      this.options = { disableStdin: options.disableStdin };
      FakeTerminal.made.push(this);
    }

    // Records the element the terminal was opened in and puts its rows there.
    open(parent: HTMLElement): void {
      this.opened.push(parent);
      const document_of = parent.ownerDocument;
      const element = document_of.createElement("div");
      const screen = document_of.createElement("div");
      screen.className = "xterm-screen";
      element.append(screen);
      parent.append(element);
      this.screen = screen;
      this.screen_size();
    }

    // Records a resize and reports a change of size, as xterm does.
    resize(cols: number, rows: number): void {
      this.resized.push([cols, rows]);
      if (cols !== this.cols || rows !== this.rows) {
        this.size_change(cols, rows);
      }
    }

    // Records the bytes written to the terminal.
    write(data: Uint8Array): void {
      this.written.push(data);
    }

    // Counts a request for the keyboard focus.
    focus(): void {
      this.focused += 1;
    }

    // Keeps the listener of the text events.
    onData = (listener: (data: string) => void): void => {
      this.data_listener = listener;
    };

    // Keeps the listener of the resize events.
    onResize = (
      listener: (size: { cols: number; rows: number }) => void,
    ): void => {
      this.resize_listener = listener;
    };

    // Types text, which reaches the view only while input is on, as in xterm.
    text_type(text: string): void {
      if (!this.options.disableStdin) {
        this.text_force(text);
      }
    }

    // Gives text to the listener of the view whether input is on or off.
    text_force(text: string): void {
      (this.data_listener as (data: string) => void)(text);
    }

    // Resizes the terminal and makes it report the new size.
    size_change(cols: number, rows: number): void {
      const listener = this.resize_listener as (size: {
        cols: number;
        rows: number;
      }) => void;
      this.cols = cols;
      this.rows = rows;
      this.screen_size();
      listener({ cols, rows });
    }

    // Sizes the rows' element of a placed terminal at a fixed size per cell.
    private screen_size(): void {
      const screen = this.screen;
      if (screen !== undefined) {
        screen.style.width = `${this.cols * constants.cell_width}px`;
        screen.style.height = `${this.rows * constants.cell_height}px`;
      }
    }
  }

  // A double of the port to the AI worker: it keeps posts and hands in lines.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    private receiver: ((line: lines.Line) => void) | undefined = undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the queue as if the AI worker sent it.
    line_send(line: lines.Line): void {
      (this.receiver as (line: lines.Line) => void)(line);
    }
  }

  // A test case that stands the fake terminal in for the global `Terminal`.
  class TerminalCase extends unittest.TestCase {
    private had = false;
    private saved: unknown = undefined;

    // Puts the fake terminal in the global scope, keeping what was there.
    setUp(): void {
      this.had = Object.hasOwn(globalThis, "Terminal");
      this.saved = Reflect.get(globalThis, "Terminal");
      FakeTerminal.made = [];
      rigs_made = [];
      Reflect.set(globalThis, "Terminal", FakeTerminal);
    }

    // Takes the frames out, each view hidden first, and puts the scope back.
    tearDown(): void {
      // Hidden, a view fits nothing when the frame's removal is reported.
      for (const rig of rigs_made) {
        rig.view.view_hide();
        rig.frame.remove();
      }
      rigs_made = [];
      if (this.had) {
        Reflect.set(globalThis, "Terminal", this.saved);
      } else {
        Reflect.deleteProperty(globalThis, "Terminal");
      }
    }
  }

  // A view in its frame with its terminal, queue, port double and two types.
  interface ViewRig {
    frame: HTMLElement;
    container: HTMLElement;
    band: HTMLElement;
    tasks: queue.TaskQueue;
    ai: PortDouble;
    terminal: FakeTerminal;
    view: console_view.ConsoleView;
    start: string;
    stop: string;
  }

  // A type that no other test registers.
  function type_fresh(): string {
    types_made += 1;
    return `${constants.type_prefix}${types_made}`;
  }

  // Registers a handler for a new type and returns that type.
  function handler_fresh(fn: dispatch.Handler): string {
    const type = type_fresh();
    dispatch.handler_register(type, 0, fn);
    return type;
  }

  // Registers the wake handlers once, which pass each wake to the last view.
  function wake_register(): void {
    if (wake_registered) {
      return;
    }
    wake_registered = true;
    dispatch.handler_register(constants.wake_type, 0, (line) => {
      (wake_view as console_view.ConsoleView).open_done(line);
      return undefined;
    });
    dispatch.handler_register(constants.closed_type, 0, (line) => {
      (wake_view as console_view.ConsoleView).close_done(line);
      return undefined;
    });
  }

  // Builds a line with no blobs and no payload from its type.
  function line_build(type: string): lines.Line {
    return jslb.line_make(jslb.header_make(type), [], {});
  }

  // Puts in the page a frame of a fixed size, a column laid out as the page.
  function frame_make(): HTMLElement {
    const frame = document.createElement("div");
    Object.assign(frame.style, {
      position: "fixed",
      top: "0px",
      left: "0px",
      width: `${constants.frame_width}px`,
      height: `${constants.frame_height}px`,
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    });
    document.body.append(frame);
    return frame;
  }

  // Makes a view on a UI queue whose owner table leaves out the console.
  function rig_make(): ViewRig {
    wake_register();
    const frame = frame_make();
    const container = document.createElement("div");
    Object.assign(container.style, { minHeight: "0px", overflow: "auto" });
    const band = document.createElement("div");
    Object.assign(band.style, {
      flexShrink: "0",
      height: `${constants.band_height}px`,
    });
    frame.append(container, band);
    const owners: queue.OwnerTable = { [constants.type_prefix]: "ui" };
    const tasks = new queue.TaskQueue("ui", owners, true);
    const ai = new PortDouble();
    tasks.port_add("ai", ai);
    const view = new console_view.ConsoleView(container, tasks);
    wake_view = view;
    const start = handler_fresh(() => view.open_request());
    const stop = handler_fresh(() => view.close_request());
    const terminal = FakeTerminal.made[FakeTerminal.made.length - 1];
    const rig: ViewRig = {
      frame,
      container,
      band,
      tasks,
      ai,
      terminal,
      view,
      start,
      stop,
    };
    rigs_made.push(rig);
    return rig;
  }

  // Runs the handler that asks for the console, as the `ctrl-0` handler does.
  function start_run(rig: ViewRig): void {
    rig.tasks.line_notify(line_build(rig.start));
  }

  // Runs a handler that asks for the close of the console.
  function stop_run(rig: ViewRig): void {
    rig.tasks.line_notify(line_build(rig.stop));
  }

  // The lines of a type the view posted to the AI worker, in order.
  function posted_of(rig: ViewRig, type: string): lines.Line[] {
    return rig.ai.posted.filter(
      (line) => jslb.field_get(line[0], "type") === type,
    );
  }

  // Answers the last request for the console with the token, as the AI does.
  function reply_send(rig: ViewRig, token: string): void {
    const requests = posted_of(rig, constants.open_type);
    const request = requests[requests.length - 1];
    rig.ai.line_send(dispatch.reply_make(request, { token }));
  }

  // Answers the last request for the close with no payload, as the AI does.
  function close_send(rig: ViewRig): void {
    const requests = posted_of(rig, constants.close_type);
    const request = requests[requests.length - 1];
    rig.ai.line_send(dispatch.reply_make(request, {}));
  }

  // Asks for the console and answers, so that the console is open.
  function rig_start(rig: ViewRig): void {
    start_run(rig);
    reply_send(rig, constants.token);
  }

  // A reply of the type to the request id, carrying the token.
  function reply_build(type: string, id: number): lines.Line {
    const header = jslb.header_make(type, { reply: id, full: true });
    return jslb.line_make(header, [], { token: constants.token });
  }

  // A wake as the queue makes it, holding the one reply.
  function wake_build(reply: lines.Line): lines.Line {
    const header = jslb.header_make(constants.wake_type);
    return jslb.line_make(header, [], { state: null, replies: [reply] });
  }

  // The `console.input` lines the view posted to the AI worker, in order.
  function inputs_of(rig: ViewRig): lines.Line[] {
    return posted_of(rig, constants.input_type);
  }

  // The one child element the view made in a container.
  function child_find(container: HTMLElement): HTMLElement {
    return container.firstElementChild as HTMLElement;
  }

  // The bytes of blob 1 of a line.
  function blob_bytes(line: lines.Line): Uint8Array {
    return jslb.field_get(line[1] as lines.BlobHeader, "data") as Uint8Array;
  }

  // The bytes of a message: the kind byte, then the text as `UTF-8`.
  function message_bytes(kind: number, text: string): Uint8Array {
    const body = utility.utf8_encode(text);
    const message = new Uint8Array(body.length + 1);
    message[0] = kind;
    message.set(body, 1);
    return message;
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      return error as Error;
    }
    throw new Error("Nothing was thrown.");
  }

  // Making, showing, hiding and toggling the view.
  export class TestVisibility extends TerminalCase {
    // The view makes one hidden child and a terminal not opened, input off.
    test_made_hidden(): void {
      const rig = rig_make();
      const child = child_find(rig.container);
      this.assertEqual(rig.container.childElementCount, 1);
      this.assertEqual(child.tagName, "DIV");
      this.assertTrue(child.hidden);
      this.assertEqual(FakeTerminal.made.length, 1);
      this.assertEqual(rig.terminal.opened.length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
      this.assertEqual(rig.ai.posted.length, 0);
      this.assertEqual(rig.tasks.depth(), 0);
    }

    // Two views on one queue can be made, as a view registers no handler.
    test_made_twice(): void {
      const tasks = new queue.TaskQueue("ui", {}, true);
      for (let count = 0; count < 2; count += 1) {
        new console_view.ConsoleView(document.createElement("div"), tasks);
      }
      this.assertEqual(FakeTerminal.made.length, 2);
    }

    // The terminal is made 120 columns wide and 40 rows high.
    test_made_size(): void {
      const rig = rig_make();
      this.assertEqual(rig.terminal.cols, 120);
      this.assertEqual(rig.terminal.rows, 40);
    }

    // The first show reveals the child, opens the terminal in it, focuses it.
    test_first_show(): void {
      const rig = rig_make();
      rig.view.view_show();
      const child = child_find(rig.container);
      this.assertFalse(child.hidden);
      this.assertEqual(rig.terminal.opened.length, 1);
      this.assertTrue(rig.terminal.opened[0] === child);
      this.assertEqual(rig.terminal.focused, 1);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // Later shows reveal the child and focus again, and ask for nothing.
    test_later_show(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      rig.view.view_show();
      this.assertFalse(child_find(rig.container).hidden);
      this.assertEqual(rig.terminal.opened.length, 1);
      this.assertEqual(rig.terminal.focused, 2);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // A hide hides the child and does nothing to the terminal.
    test_hide_shown(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      this.assertTrue(child_find(rig.container).hidden);
      this.assertEqual(rig.terminal.opened.length, 1);
      this.assertEqual(FakeTerminal.made.length, 1);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // A hide before any show leaves the terminal out of the page.
    test_hide_idle(): void {
      const rig = rig_make();
      rig.view.view_hide();
      this.assertTrue(child_find(rig.container).hidden);
      this.assertEqual(rig.terminal.opened.length, 0);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // A toggle shows a hidden view and the next toggle hides it again.
    test_toggle_twice(): void {
      const rig = rig_make();
      const child = child_find(rig.container);
      rig.view.view_toggle();
      this.assertFalse(child.hidden);
      rig.view.view_toggle();
      this.assertTrue(child.hidden);
      rig.view.view_toggle();
      this.assertFalse(child.hidden);
      this.assertEqual(rig.terminal.opened.length, 1);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // Showing an open console sends its fitted size, hiding sends nothing.
    test_toggle_open(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.view_toggle();
      rig.view.view_toggle();
      this.assertEqual(rig.ai.posted.length, 3);
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        message_bytes(0x31, '{"columns":120,"rows":20}'),
      );
      this.assertFalse(rig.terminal.options.disableStdin);
    }

    // The view wants tty 0 when shown while idle, at first and after its end.
    test_open_wanted(): void {
      const rig = rig_make();
      this.assertFalse(rig.view.open_wanted());
      rig.view.view_show();
      this.assertTrue(rig.view.open_wanted());
      start_run(rig);
      this.assertFalse(rig.view.open_wanted());
      reply_send(rig, constants.token);
      this.assertFalse(rig.view.open_wanted());
      rig.view.exit_done();
      this.assertTrue(rig.view.open_wanted());
      rig.view.view_hide();
      this.assertFalse(rig.view.open_wanted());
      this.assertEqual(rig.ai.posted.length, 2);
    }
  }

  // The request for tty 0, its wake and ttyd's first message.
  export class TestOpening extends TerminalCase {
    // A handler run posts one `console.open` request to the AI worker.
    test_open_request(): void {
      const rig = rig_make();
      start_run(rig);
      this.assertEqual(rig.ai.posted.length, 1);
      const line = rig.ai.posted[0];
      this.assertEqual(jslb.field_get(line[0], "type"), constants.open_type);
      this.assertEqual(jslb.field_get(line[0], "id"), 1);
      this.assertEqual(jslb.field_get(line[0], "blobs"), 0);
      this.assertEqual(rig.tasks.depth(), 1);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // The request returns a sleep on its id that wakes with the wake type.
    test_sleep_returned(): void {
      const rig = rig_make();
      const sleeps: dispatch.Sleep[] = [];
      const keep = handler_fresh(() => {
        const sleep = rig.view.open_request();
        sleeps.push(sleep);
        return sleep;
      });
      rig.tasks.line_notify(line_build(keep));
      this.assertEqual(sleeps.length, 1);
      this.assertEqual(sleeps[0].wait_ids, [1]);
      this.assertEqual(sleeps[0].then_type, constants.wake_type);
      this.assertEqual(sleeps[0].state, null);
    }

    // Lines use full header names, as the console exists in debug mode only.
    test_full_names(): void {
      const rig = rig_make();
      rig_start(rig);
      for (const line of [rig.ai.posted[0], rig.ai.posted[1]]) {
        this.assertTrue("type" in line[0]);
        this.assertFalse("t" in line[0]);
      }
    }

    // A request outside a handler is refused by the queue and leaves it idle.
    test_open_outside(): void {
      const rig = rig_make();
      const error = thrown_get(() => rig.view.open_request());
      this.assertEqual(
        error.message,
        i18n("queue.submit_outside", "ui", constants.open_type),
      );
      this.assertEqual(rig.ai.posted.length, 0);
      start_run(rig);
      this.assertEqual(rig.ai.posted.length, 1);
      this.assertEqual(jslb.field_get(rig.ai.posted[0][0], "id"), 1);
    }

    // A handler that drops the sleep of its request is refused by the queue.
    test_sleep_dropped(): void {
      const rig = rig_make();
      const drop = handler_fresh(() => {
        rig.view.open_request();
        return undefined;
      });
      const error = thrown_get(() => rig.tasks.line_notify(line_build(drop)));
      this.assertEqual(
        error.message,
        i18n("queue.wait_missing", drop, "ui", 1),
      );
    }

    // A second request while opening or open is refused and posts nothing.
    test_open_twice(): void {
      const opening = rig_make();
      start_run(opening);
      const early = thrown_get(() => start_run(opening));
      this.assertEqual(
        early.message,
        i18n("console_view.open_phase", "opening"),
      );
      this.assertEqual(opening.ai.posted.length, 1);
      const open = rig_make();
      rig_start(open);
      const late = thrown_get(() => start_run(open));
      this.assertEqual(late.message, i18n("console_view.open_phase", "open"));
      this.assertEqual(open.ai.posted.length, 2);
    }

    // The wake sends ttyd's first message, the one for an empty token.
    test_first_message(): void {
      const rig = rig_make();
      start_run(rig);
      reply_send(rig, "");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      const line = inputs[0];
      this.assertEqual(jslb.field_get(line[0], "blobs"), 1);
      const bytes = blob_bytes(line);
      this.assertEqual(bytes.length, 40);
      this.assertEqual(
        utility.utf8_decode(bytes),
        '{"AuthToken":"","columns":120,"rows":40}',
      );
      this.assertFalse(rig.terminal.options.disableStdin);
      this.assertEqual(rig.tasks.depth(), 0);
    }

    // The first message carries the token of the reply.
    test_first_token(): void {
      const rig = rig_make();
      rig_start(rig);
      this.assertEqual(
        utility.utf8_decode(blob_bytes(inputs_of(rig)[0])),
        '{"AuthToken":"dXNlcjpwYXNz","columns":120,"rows":40}',
      );
    }

    // The first message has no kind byte and the size the terminal has.
    test_first_size(): void {
      const rig = rig_make();
      start_run(rig);
      rig.terminal.cols = 100;
      rig.terminal.rows = 30;
      reply_send(rig, "");
      const bytes = blob_bytes(inputs_of(rig)[0]);
      this.assertEqual(bytes[0], 0x7b);
      this.assertEqual(
        utility.utf8_decode(bytes),
        '{"AuthToken":"","columns":100,"rows":30}',
      );
    }

    // A wake before any request is refused and sends nothing.
    test_reply_idle(): void {
      const rig = rig_make();
      const wake = wake_build(reply_build(constants.open_type, 1));
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(
        error.message,
        i18n("console_view.reply_phase", "idle"),
      );
      this.assertEqual(rig.ai.posted.length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // A second wake is refused and sends nothing more.
    test_reply_twice(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_build(reply_build(constants.open_type, 1));
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(
        error.message,
        i18n("console_view.reply_phase", "open"),
      );
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A reply of another type to the request is refused and sends nothing.
    test_reply_type(): void {
      const rig = rig_make();
      start_run(rig);
      const reply = reply_build("console.close", 1);
      const error = thrown_get(() => rig.ai.line_send(reply));
      this.assertEqual(
        error.message,
        i18n("console_view.reply_type", "console.close", "console.open"),
      );
      this.assertEqual(inputs_of(rig).length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // A wake with the reply to another request is refused, the right one not.
    test_reply_id(): void {
      const rig = rig_make();
      start_run(rig);
      const wake = wake_build(reply_build(constants.open_type, 2));
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(error.message, i18n("console_view.reply_id", 2, 1));
      this.assertEqual(inputs_of(rig).length, 0);
      reply_send(rig, constants.token);
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A reply without a token is refused and sends nothing.
    test_token_missing(): void {
      const rig = rig_make();
      start_run(rig);
      const reply = dispatch.reply_make(rig.ai.posted[0], {});
      const error = thrown_get(() => rig.ai.line_send(reply));
      this.assertEqual(
        error.message,
        i18n("console_view.token_invalid", "undefined"),
      );
      this.assertEqual(inputs_of(rig).length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
    }
  }

  // The keystrokes the terminal emits, as ttyd's input messages.
  export class TestInput extends TerminalCase {
    // A batch of text is one line whose blob is a zero and the text.
    test_ascii_batch(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type("ls\r");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(jslb.field_get(inputs[1][0], "blobs"), 1);
      this.assertEqual(
        blob_bytes(inputs[1]),
        Uint8Array.of(0x30, 0x6c, 0x73, 0x0d),
      );
    }

    // Each batch is its own line, in the order the terminal emitted them.
    test_each_batch(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type("a");
      rig.terminal.text_type("b");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 3);
      this.assertEqual(blob_bytes(inputs[1]), message_bytes(0x30, "a"));
      this.assertEqual(blob_bytes(inputs[2]), message_bytes(0x30, "b"));
    }

    // A character of two bytes is sent as its two `UTF-8` bytes.
    test_two_bytes(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type(String.fromCodePoint(0xe9));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xc3, 0xa9),
      );
    }

    // A character of three bytes is sent as its three `UTF-8` bytes.
    test_three_bytes(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type(String.fromCodePoint(0x4e2d));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xe4, 0xb8, 0xad),
      );
    }

    // A character of four bytes, two `UTF-16` units, is sent as four bytes.
    test_four_bytes(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type(String.fromCodePoint(0x1f600));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xf0, 0x9f, 0x98, 0x80),
      );
    }

    // A batch of mixed characters is one line with the bytes in order.
    test_mixed_batch(): void {
      const rig = rig_make();
      rig_start(rig);
      const text =
        "a" +
        String.fromCodePoint(0xe9) +
        String.fromCodePoint(0x4e2d) +
        String.fromCodePoint(0x1f600);
      rig.terminal.text_type(text);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(
        blob_bytes(inputs[1]),
        Uint8Array.of(
          0x30,
          0x61,
          0xc3,
          0xa9,
          0xe4,
          0xb8,
          0xad,
          0xf0,
          0x9f,
          0x98,
          0x80,
        ),
      );
    }

    // A control character is sent as its own byte after the zero.
    test_control_byte(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type(String.fromCharCode(0x03));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0x03),
      );
    }

    // Before any request the terminal takes no input, and the view refuses.
    test_input_idle(): void {
      const rig = rig_make();
      rig.terminal.text_type("x");
      this.assertTrue(rig.terminal.options.disableStdin);
      const error = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        error.message,
        i18n("console_view.input_phase", "idle"),
      );
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // Before ttyd's first message the terminal takes no input either.
    test_input_opening(): void {
      const rig = rig_make();
      start_run(rig);
      rig.terminal.text_type("x");
      this.assertTrue(rig.terminal.options.disableStdin);
      const error = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        error.message,
        i18n("console_view.input_phase", "opening"),
      );
      this.assertEqual(inputs_of(rig).length, 0);
    }
  }

  // The resizes the terminal reports, as ttyd's resize messages.
  export class TestResize extends TerminalCase {
    // A resize is one line whose blob is a one and the JSON of the size.
    test_resize_message(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.size_change(100, 30);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(jslb.field_get(inputs[1][0], "blobs"), 1);
      this.assertEqual(
        blob_bytes(inputs[1]),
        message_bytes(0x31, '{"columns":100,"rows":30}'),
      );
    }

    // Input and resizes are lines in the order they happened.
    test_order_kept(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.terminal.text_type("a");
      rig.terminal.size_change(90, 20);
      rig.terminal.text_type("b");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 4);
      this.assertEqual(blob_bytes(inputs[1]), message_bytes(0x30, "a"));
      this.assertEqual(
        blob_bytes(inputs[2]),
        message_bytes(0x31, '{"columns":90,"rows":20}'),
      );
      this.assertEqual(blob_bytes(inputs[3]), message_bytes(0x30, "b"));
    }

    // A resize before any request sends nothing, and the first message has it.
    test_resize_idle(): void {
      const rig = rig_make();
      rig.terminal.size_change(100, 30);
      this.assertEqual(rig.ai.posted.length, 0);
      rig_start(rig);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      this.assertEqual(
        utility.utf8_decode(blob_bytes(inputs[0])),
        '{"AuthToken":"dXNlcjpwYXNz","columns":100,"rows":30}',
      );
    }

    // A resize while opening sends nothing, and the first message has it.
    test_resize_opening(): void {
      const rig = rig_make();
      start_run(rig);
      rig.terminal.size_change(100, 30);
      this.assertEqual(rig.ai.posted.length, 1);
      reply_send(rig, "");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      this.assertEqual(
        utility.utf8_decode(blob_bytes(inputs[0])),
        '{"AuthToken":"","columns":100,"rows":30}',
      );
    }

    // A resize while closing or after the end sends nothing.
    test_resize_closed(): void {
      const rig = rig_make();
      rig_start(rig);
      stop_run(rig);
      rig.terminal.size_change(100, 30);
      this.assertEqual(rig.ai.posted.length, 3);
      close_send(rig);
      rig.view.exit_done();
      rig.terminal.size_change(90, 20);
      this.assertEqual(rig.ai.posted.length, 3);
    }
  }

  // The rows fitted to the height the container has above the band.
  export class TestFit extends TerminalCase {
    // A show fits the rows to the space above the band, so none is scrolled.
    test_rows_fitted(): void {
      const rig = rig_make();
      rig.view.view_show();
      this.assertEqual(rig.terminal.cols, 120);
      this.assertEqual(rig.terminal.rows, 20);
      this.assertEqual(rig.terminal.resized, [[120, 20]]);
      const container = rig.container;
      this.assertTrue(
        container.scrollHeight <= container.clientHeight,
        `${container.scrollHeight} px of rows in ${container.clientHeight} px`,
      );
      const placed = rig.terminal.screen as HTMLElement;
      const screen = placed.getBoundingClientRect();
      const band = rig.band.getBoundingClientRect();
      this.assertTrue(
        screen.bottom <= band.top,
        `rows end at ${screen.bottom}, the band at ${band.top}`,
      );
    }

    // A fit while idle sends nothing, and the first message has the rows.
    test_fitted_first(): void {
      const rig = rig_make();
      rig.view.view_show();
      this.assertEqual(rig.ai.posted.length, 0);
      rig_start(rig);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      this.assertEqual(
        utility.utf8_decode(blob_bytes(inputs[0])),
        '{"AuthToken":"dXNlcjpwYXNz","columns":120,"rows":20}',
      );
    }

    // A later show fits the rows again, to the space the frame has then.
    test_space_changed(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      rig.frame.style.height = "300px";
      rig.view.view_show();
      this.assertEqual(rig.terminal.rows, 14);
      this.assertEqual(rig.terminal.resized, [
        [120, 20],
        [120, 14],
      ]);
      this.assertEqual(rig.ai.posted.length, 0);
    }

    // A scroll bar under wide columns is left out of the space.
    test_narrow_frame(): void {
      const rig = rig_make();
      rig.frame.style.width = "500px";
      rig.view.view_show();
      const container = rig.container;
      this.assertTrue(container.scrollWidth > container.clientWidth);
      this.assertTrue(
        container.scrollHeight <= container.clientHeight,
        `${container.scrollHeight} px of rows in ${container.clientHeight} px`,
      );
    }

    // A band that leaves no room for one row is refused.
    test_rows_unfit(): void {
      const rig = rig_make();
      rig.band.style.height = `${constants.frame_height}px`;
      const error = thrown_get(() => rig.view.view_show());
      this.assertEqual(
        error.message,
        i18n("console_view.rows_unfit", 0, constants.cell_height),
      );
      this.assertEqual(rig.terminal.rows, 40);
    }
  }

  // The messages of ttyd that `output_feed` takes.
  export class TestOutput extends TerminalCase {
    // Output is written to the terminal without its kind byte.
    test_output_written(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(Uint8Array.of(0x30, 0x68, 0x69));
      this.assertEqual(rig.terminal.written.length, 1);
      this.assertEqual(rig.terminal.written[0], Uint8Array.of(0x68, 0x69));
    }

    // Each output message is a separate write, in order.
    test_writes_ordered(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(message_bytes(0x30, "$ "));
      rig.view.output_feed(message_bytes(0x30, "hi\r\n"));
      this.assertEqual(rig.terminal.written.length, 2);
      this.assertEqual(rig.terminal.written[0], utility.utf8_encode("$ "));
      this.assertEqual(rig.terminal.written[1], utility.utf8_encode("hi\r\n"));
    }

    // A title message is ignored.
    test_title_ignored(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(message_bytes(0x31, "python3 bootstrap.py"));
      this.assertEqual(rig.terminal.written.length, 0);
    }

    // A preferences message is ignored.
    test_preferences_ignored(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(message_bytes(0x32, "{}"));
      this.assertEqual(rig.terminal.written.length, 0);
    }

    // A kind byte that is not output, title or preferences is refused.
    test_kind_unknown(): void {
      const rig = rig_make();
      rig_start(rig);
      for (const kind of [0x2f, 0x33, 0x7b, 0x00, 0xff]) {
        const error = thrown_get(() =>
          rig.view.output_feed(message_bytes(kind, "x")),
        );
        this.assertEqual(
          error.message,
          i18n("console_view.kind_unknown", kind),
        );
      }
      this.assertEqual(rig.terminal.written.length, 0);
    }

    // A message with no bytes has no kind and is refused.
    test_message_empty(): void {
      const rig = rig_make();
      rig_start(rig);
      const error = thrown_get(() => rig.view.output_feed(new Uint8Array(0)));
      this.assertEqual(error.message, i18n("console_view.message_empty"));
      this.assertEqual(rig.terminal.written.length, 0);
    }

    // An output message with no text is a write of no bytes.
    test_output_bare(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(Uint8Array.of(0x30));
      this.assertEqual(rig.terminal.written.length, 1);
      this.assertEqual(rig.terminal.written[0].length, 0);
    }

    // Output fed while the view is hidden still goes to the terminal.
    test_output_hidden(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      rig.view.view_hide();
      rig.view.output_feed(message_bytes(0x30, "kept"));
      this.assertEqual(rig.terminal.written.length, 1);
      this.assertEqual(rig.terminal.written[0], utility.utf8_encode("kept"));
      this.assertEqual(rig.terminal.opened.length, 1);
    }

    // Bytes of one character split over two messages are passed as they are.
    test_output_split(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(Uint8Array.of(0x30, 0xe4, 0xb8));
      rig.view.output_feed(Uint8Array.of(0x30, 0xad));
      this.assertEqual(rig.terminal.written.length, 2);
      this.assertEqual(rig.terminal.written[0], Uint8Array.of(0xe4, 0xb8));
      this.assertEqual(rig.terminal.written[1], Uint8Array.of(0xad));
    }

    // Invalid `UTF-8` is passed on, as the terminal decodes its own input.
    test_output_invalid(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.output_feed(Uint8Array.of(0x30, 0xff, 0xfe));
      this.assertEqual(rig.terminal.written[0], Uint8Array.of(0xff, 0xfe));
    }
  }

  // The request to close tty 0, its wake, and the end that follows it.
  export class TestClosing extends TerminalCase {
    // A handler run posts one `console.close` request and turns input off.
    test_close_request(): void {
      const rig = rig_make();
      rig_start(rig);
      stop_run(rig);
      this.assertEqual(rig.ai.posted.length, 3);
      const line = rig.ai.posted[2];
      this.assertEqual(jslb.field_get(line[0], "type"), constants.close_type);
      this.assertEqual(jslb.field_get(line[0], "id"), 2);
      this.assertTrue("type" in line[0]);
      this.assertEqual(jslb.payload_of(line), {});
      this.assertEqual(rig.tasks.depth(), 1);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // The request returns a sleep on its id that wakes with its own type.
    test_close_sleep(): void {
      const rig = rig_make();
      rig_start(rig);
      const sleeps: dispatch.Sleep[] = [];
      const keep = handler_fresh(() => {
        const sleep = rig.view.close_request();
        sleeps.push(sleep);
        return sleep;
      });
      rig.tasks.line_notify(line_build(keep));
      this.assertEqual(sleeps.length, 1);
      this.assertEqual(sleeps[0].wait_ids, [2]);
      this.assertEqual(sleeps[0].then_type, constants.closed_type);
      this.assertEqual(sleeps[0].state, null);
    }

    // The reply leaves the console closing, taking no input and no opening.
    test_close_reply(): void {
      const rig = rig_make();
      rig_start(rig);
      stop_run(rig);
      close_send(rig);
      this.assertEqual(rig.tasks.depth(), 0);
      this.assertTrue(rig.terminal.options.disableStdin);
      const typed = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        typed.message,
        i18n("console_view.input_phase", "closing"),
      );
      const again = thrown_get(() => start_run(rig));
      this.assertEqual(
        again.message,
        i18n("console_view.open_phase", "closing"),
      );
      this.assertEqual(rig.ai.posted.length, 3);
    }

    // A close while idle, opening or closing is refused and posts nothing.
    test_close_phase(): void {
      const idle = rig_make();
      const first = thrown_get(() => stop_run(idle));
      this.assertEqual(
        first.message,
        i18n("console_view.close_phase", "idle"),
      );
      this.assertEqual(idle.ai.posted.length, 0);
      const opening = rig_make();
      start_run(opening);
      const early = thrown_get(() => stop_run(opening));
      this.assertEqual(
        early.message,
        i18n("console_view.close_phase", "opening"),
      );
      this.assertEqual(opening.ai.posted.length, 1);
      const closing = rig_make();
      rig_start(closing);
      stop_run(closing);
      const twice = thrown_get(() => stop_run(closing));
      this.assertEqual(
        twice.message,
        i18n("console_view.close_phase", "closing"),
      );
      this.assertEqual(closing.ai.posted.length, 3);
    }

    // A wake of the close before any close is asked for is refused.
    test_closed_early(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_build(reply_build(constants.close_type, 2));
      const error = thrown_get(() => rig.view.close_done(wake));
      this.assertEqual(
        error.message,
        i18n("console_view.closed_phase", "open"),
      );
    }

    // A reply of another type or to another request is refused.
    test_closed_checked(): void {
      const rig = rig_make();
      rig_start(rig);
      stop_run(rig);
      const other = wake_build(reply_build(constants.open_type, 2));
      const typed = thrown_get(() => rig.view.close_done(other));
      this.assertEqual(
        typed.message,
        i18n(
          "console_view.reply_type",
          constants.open_type,
          constants.close_type,
        ),
      );
      const stray = wake_build(reply_build(constants.close_type, 1));
      const wrong = thrown_get(() => rig.view.close_done(stray));
      this.assertEqual(wrong.message, i18n("console_view.reply_id", 1, 2));
      close_send(rig);
      this.assertEqual(rig.tasks.depth(), 0);
    }

    // The end after a close leaves the console idle, and it opens again.
    test_close_reopen(): void {
      const rig = rig_make();
      rig_start(rig);
      stop_run(rig);
      close_send(rig);
      rig.view.exit_done();
      start_run(rig);
      const opened = posted_of(rig, constants.open_type);
      this.assertEqual(opened.length, 2);
      this.assertEqual(jslb.field_get(opened[1][0], "id"), 3);
      reply_send(rig, constants.token);
      this.assertEqual(inputs_of(rig).length, 2);
      this.assertFalse(rig.terminal.options.disableStdin);
      rig.terminal.text_type("a");
      this.assertEqual(inputs_of(rig).length, 3);
      this.assertEqual(rig.tasks.depth(), 0);
    }
  }

  // The end of tty 0, after which the console can be asked for again.
  export class TestExit extends TerminalCase {
    // The end turns input off, so typing sends nothing more.
    test_exit_open(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      this.assertTrue(rig.terminal.options.disableStdin);
      rig.terminal.text_type("x");
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // An end before the console is open is refused.
    test_exit_early(): void {
      const rig = rig_make();
      const idle = thrown_get(() => rig.view.exit_done());
      this.assertEqual(idle.message, i18n("console_view.exit_phase", "idle"));
      start_run(rig);
      const opening = thrown_get(() => rig.view.exit_done());
      this.assertEqual(
        opening.message,
        i18n("console_view.exit_phase", "opening"),
      );
    }

    // A second end is refused, as the console is idle again.
    test_exit_twice(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      const error = thrown_get(() => rig.view.exit_done());
      this.assertEqual(error.message, i18n("console_view.exit_phase", "idle"));
    }

    // Text that reaches the view after the end is refused and sends nothing.
    test_input_closed(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      const error = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        error.message,
        i18n("console_view.input_phase", "idle"),
      );
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A request after the end asks for tty 0 again and sends a first message.
    test_open_again(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      start_run(rig);
      this.assertEqual(rig.ai.posted.length, 3);
      const line = rig.ai.posted[2];
      this.assertEqual(jslb.field_get(line[0], "type"), constants.open_type);
      this.assertEqual(jslb.field_get(line[0], "id"), 2);
      this.assertTrue(rig.terminal.options.disableStdin);
      reply_send(rig, constants.token);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(
        utility.utf8_decode(blob_bytes(inputs[1])),
        '{"AuthToken":"dXNlcjpwYXNz","columns":120,"rows":40}',
      );
      this.assertFalse(rig.terminal.options.disableStdin);
      this.assertEqual(rig.tasks.depth(), 0);
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the one class of its declaration.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(console_view));
      this.assertEqual(Object.keys(console_view).join(","), "ConsoleView");
    }
  }
}
Object.freeze(test_console_view);
