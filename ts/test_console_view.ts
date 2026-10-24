// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the console view with a fake terminal on a container above a band
// in a frame of a fixed size, put in the page by each test and taken out after
// it, and a double of the task queue that keeps each line the view gives it
// and hands each submit the id the test picked. The requests, sleeps and
// input lines the view makes, the wakes the test gives it, ttyd's first
// messages and the texts of the view's refusals are the gold record's.
namespace test_console_view {
  // The owner, the ids the double hands out, the frame and the fake's cells.
  const constants = Object.freeze({
    // The thread the view gives its lines to.
    owner: "ai",
    // The ids the queue double hands the submits, in order, its writer's.
    request_ids: Object.freeze([11, 12, 13]),
    // The pixel sizes of the frame, band and cells, chosen by their writer.
    frame_width: 1000,
    frame_height: 400,
    band_height: 50,
    cell_width: 8,
    cell_height: 17,
  });

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

    // Records a resize and takes the new size, as xterm does.
    resize(cols: number, rows: number): void {
      this.resized.push([cols, rows]);
      this.cols = cols;
      this.rows = rows;
      this.screen_size();
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

    // Sizes the rows' element of a placed terminal at a fixed size per cell.
    private screen_size(): void {
      const screen = this.screen;
      if (screen !== undefined) {
        screen.style.width = `${this.cols * constants.cell_width}px`;
        screen.style.height = `${this.rows * constants.cell_height}px`;
      }
    }
  }

  // One line the view gave the queue double: by which call, for which owner.
  interface LineGiven {
    call: "task_submit" | "line_notify";
    line: lines.Line;
    owner: string;
  }

  // A double of the task queue, keeping each line the view gives it in order.
  class TasksDouble {
    readonly given: LineGiven[] = [];
    // The ids handed to the submits so far, in order.
    readonly handed: number[] = [];
    readonly #ids: number[];

    // Takes the ids the submits get, in order.
    constructor(ids: readonly number[]) {
      this.#ids = [...ids];
    }

    // Keeps a request and returns the next id the test picked.
    task_submit(line: lines.Line, owner: string): number {
      const id = this.#ids.shift();
      if (id === undefined) {
        throw new Error("The queue double was given no id for this submit.");
      }
      this.given.push({ call: "task_submit", line, owner });
      this.handed.push(id);
      return id;
    }

    // Keeps a notification.
    line_notify(line: lines.Line, owner: string): void {
      this.given.push({ call: "line_notify", line, owner });
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

  // A view in its frame with its terminal and its queue double.
  interface ViewRig {
    frame: HTMLElement;
    container: HTMLElement;
    band: HTMLElement;
    tasks: TasksDouble;
    terminal: FakeTerminal;
    view: console_view.ConsoleView;
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_console_view.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_console_view.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A ttyd first message of the gold, the text the view sends as bytes.
  function first_message(name: string): string {
    return gold_value(`first_messages.${name}`) as string;
  }

  // A wake of the gold whose one reply answers the request of the id.
  function wake_make(name: string, id: number): lines.Line {
    const wake = gold_line(name);
    const replies = wake.replies as lines.Line[];
    Object.assign(replies[0][0], { reply: id });
    return wake;
  }

  // A sleep of the gold that waits for the request of the id.
  function sleep_make(name: string, id: number): dispatch.Sleep {
    const sleep = gold_value(`lines.${name}`) as dispatch.Sleep;
    sleep.wait_ids = [id];
    return sleep;
  }

  // The text of the refusal of a reply to one request while another waits.
  function reply_id_text(answered: number, waited: number): string {
    return gold_text("console_view_reply_id")
      .replaceAll("{0}", String(answered))
      .replaceAll("{1}", String(waited));
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

  // Makes a view on a queue double that hands out the test's ids.
  function rig_make(): ViewRig {
    const frame = frame_make();
    const container = document.createElement("div");
    Object.assign(container.style, { minHeight: "0px", overflow: "auto" });
    const band = document.createElement("div");
    Object.assign(band.style, {
      flexShrink: "0",
      height: `${constants.band_height}px`,
    });
    frame.append(container, band);
    const tasks = new TasksDouble(constants.request_ids);
    const view = new console_view.ConsoleView(
      container,
      tasks as unknown as queue.TaskQueue,
    );
    const terminal = FakeTerminal.made[FakeTerminal.made.length - 1];
    const rig: ViewRig = { frame, container, band, tasks, terminal, view };
    rigs_made.push(rig);
    return rig;
  }

  // The id the queue double handed to the last submit.
  function id_last(rig: ViewRig): number {
    return rig.tasks.handed[rig.tasks.handed.length - 1];
  }

  // Gives the view the wake of the gold that answers its last request.
  function open_answer(rig: ViewRig, name: string): void {
    rig.view.open_done(wake_make(name, id_last(rig)));
  }

  // Gives the view the wake of its last request, the close, as the AI does.
  function close_answer(rig: ViewRig): void {
    rig.view.close_done(wake_make("close_wake", id_last(rig)));
  }

  // Asks for the console and answers with the token, so that it is open.
  function rig_start(rig: ViewRig): void {
    rig.view.open_request();
    open_answer(rig, "open_wake");
  }

  // The lines the view submitted to the queue double, in order.
  function submits_of(rig: ViewRig): lines.Line[] {
    return rig.tasks.given
      .filter((given) => given.call === "task_submit")
      .map((given) => given.line);
  }

  // The `console.input` lines the view notified to the queue double.
  function inputs_of(rig: ViewRig): lines.Line[] {
    return rig.tasks.given
      .filter((given) => given.call === "line_notify")
      .map((given) => given.line);
  }

  // The `console.input` line of the gold that carries one message as blob 1.
  function input_expected(message: Uint8Array): lines.Line {
    const line = gold_line("input");
    line[1] = { size: message.length, d: message };
    return line;
  }

  // A request of the gold as the view submits it for the AI worker.
  function submit_expected(name: string): LineGiven {
    const line = gold_line(name);
    return { call: "task_submit", line, owner: constants.owner };
  }

  // A message of ttyd as the view notifies it for the AI worker.
  function notify_expected(message: Uint8Array): LineGiven {
    const line = input_expected(message);
    return { call: "line_notify", line, owner: constants.owner };
  }

  // The one child element the view made in a container.
  function child_find(container: HTMLElement): HTMLElement {
    return container.firstElementChild as HTMLElement;
  }

  // The bytes of blob 1 of a line.
  function blob_bytes(line: lines.Line): Uint8Array {
    return (line[1] as lines.BlobHeader).d as Uint8Array;
  }

  // The text of bytes read as strict `UTF-8`.
  function text_decode(data: Uint8Array): string {
    return new TextDecoder("utf-8", { fatal: true }).decode(data);
  }

  // The bytes of a message: the kind byte, then the text as `UTF-8`.
  function message_bytes(kind: number, text: string): Uint8Array {
    const body = new TextEncoder().encode(text);
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
      this.assertEqual(rig.tasks.given.length, 0);
    }

    // Two views on one queue can be made, as a view registers no handler.
    test_made_twice(): void {
      const tasks = new TasksDouble([]);
      for (let count = 0; count < 2; count += 1) {
        new console_view.ConsoleView(
          document.createElement("div"),
          tasks as unknown as queue.TaskQueue,
        );
      }
      this.assertEqual(FakeTerminal.made.length, 2);
      this.assertEqual(tasks.given.length, 0);
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
      this.assertEqual(rig.tasks.given.length, 0);
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
      this.assertEqual(rig.tasks.given.length, 0);
    }

    // A hide hides the child and does nothing to the terminal.
    test_hide_shown(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      this.assertTrue(child_find(rig.container).hidden);
      this.assertEqual(rig.terminal.opened.length, 1);
      this.assertEqual(FakeTerminal.made.length, 1);
      this.assertEqual(rig.tasks.given.length, 0);
    }

    // A hide before any show leaves the terminal out of the page.
    test_hide_idle(): void {
      const rig = rig_make();
      rig.view.view_hide();
      this.assertTrue(child_find(rig.container).hidden);
      this.assertEqual(rig.terminal.opened.length, 0);
      this.assertEqual(rig.tasks.given.length, 0);
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
      this.assertEqual(rig.tasks.given.length, 0);
    }

    // Showing an open console fits its rows and sends no resize to tty 0.
    test_toggle_open(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.view_toggle();
      rig.view.view_toggle();
      this.assertEqual(rig.terminal.rows, 20);
      this.assertEqual(rig.tasks.given.length, 2);
      this.assertFalse(rig.terminal.options.disableStdin);
    }

    // The view wants tty 0 when shown while idle, at first and after its end.
    test_open_wanted(): void {
      const rig = rig_make();
      this.assertFalse(rig.view.open_wanted());
      rig.view.view_show();
      this.assertTrue(rig.view.open_wanted());
      rig.view.open_request();
      this.assertFalse(rig.view.open_wanted());
      open_answer(rig, "open_wake");
      this.assertFalse(rig.view.open_wanted());
      rig.view.exit_done();
      this.assertTrue(rig.view.open_wanted());
      rig.view.view_hide();
      this.assertFalse(rig.view.open_wanted());
      this.assertEqual(rig.tasks.given.length, 2);
    }

    // The view is open only while tty 0 is open: not idle, opening, closing.
    test_open_is(): void {
      const rig = rig_make();
      this.assertFalse(rig.view.open_is());
      rig.view.open_request();
      this.assertFalse(rig.view.open_is());
      open_answer(rig, "open_wake");
      this.assertTrue(rig.view.open_is());
      rig.view.close_request();
      this.assertFalse(rig.view.open_is());
      close_answer(rig);
      this.assertFalse(rig.view.open_is());
      rig.view.exit_done();
      this.assertFalse(rig.view.open_is());
    }
  }

  // The request for tty 0, its wake and ttyd's first message.
  export class TestOpening extends TerminalCase {
    // A request gives the queue one `console.open` for the AI worker.
    test_open_request(): void {
      const rig = rig_make();
      rig.view.open_request();
      this.assertEqual(rig.tasks.given, [submit_expected("open_request")]);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // The request returns a sleep on the id it got that wakes with its type.
    test_sleep_returned(): void {
      const rig = rig_make();
      const sleep = rig.view.open_request();
      this.assertEqual(
        sleep,
        sleep_make("open_sleep", constants.request_ids[0]),
      );
    }

    // Lines take the name form the settings pick, full exactly in debug mode.
    test_full_names(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.close_request();
      const full = harness.setting_get("debug") === true;
      this.assertEqual(rig.tasks.given.length, 3);
      for (const given of rig.tasks.given) {
        this.assertEqual("type" in given.line[0], full);
        this.assertEqual("t" in given.line[0], !full);
      }
    }

    // A second request while opening or open is refused and gives nothing.
    test_open_twice(): void {
      const opening = rig_make();
      opening.view.open_request();
      const early = thrown_get(() => opening.view.open_request());
      this.assertEqual(
        early.message,
        gold_text("console_view_open_phase_opening"),
      );
      this.assertEqual(opening.tasks.given.length, 1);
      const open = rig_make();
      rig_start(open);
      const late = thrown_get(() => open.view.open_request());
      this.assertEqual(
        late.message,
        gold_text("console_view_open_phase_open"),
      );
      this.assertEqual(open.tasks.given.length, 2);
    }

    // The wake gives ttyd's first message, the one for an empty token.
    test_first_message(): void {
      const rig = rig_make();
      rig.view.open_request();
      open_answer(rig, "open_wake_empty");
      const message = new TextEncoder().encode(first_message("empty"));
      this.assertEqual(rig.tasks.given.slice(1), [notify_expected(message)]);
      this.assertFalse(rig.terminal.options.disableStdin);
    }

    // The first message carries the token of the reply.
    test_first_token(): void {
      const rig = rig_make();
      rig_start(rig);
      this.assertEqual(
        text_decode(blob_bytes(inputs_of(rig)[0])),
        first_message("token"),
      );
    }

    // The first message has no kind byte and the size the terminal has.
    test_first_size(): void {
      const rig = rig_make();
      rig.view.open_request();
      rig.terminal.cols = 100;
      rig.terminal.rows = 30;
      open_answer(rig, "open_wake_empty");
      const bytes = blob_bytes(inputs_of(rig)[0]);
      this.assertEqual(bytes[0], 0x7b);
      this.assertEqual(text_decode(bytes), first_message("sized"));
    }

    // A wake before any request is refused and sends nothing.
    test_reply_idle(): void {
      const rig = rig_make();
      const wake = wake_make("open_wake", constants.request_ids[0]);
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(
        error.message,
        gold_text("console_view_reply_phase_idle"),
      );
      this.assertEqual(rig.tasks.given.length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // A second wake is refused and sends nothing more.
    test_reply_twice(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_make("open_wake", constants.request_ids[0]);
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(
        error.message,
        gold_text("console_view_reply_phase_open"),
      );
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A reply of another type to the request is refused and sends nothing.
    test_reply_type(): void {
      const rig = rig_make();
      rig.view.open_request();
      const error = thrown_get(() =>
        open_answer(rig, "open_wake_close_reply"),
      );
      this.assertEqual(
        error.message,
        gold_text("console_view_reply_type_close"),
      );
      this.assertEqual(inputs_of(rig).length, 0);
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // A wake with the reply to another request is refused, the right one not.
    test_reply_id(): void {
      const rig = rig_make();
      rig.view.open_request();
      const [asked, other] = constants.request_ids;
      const wake = wake_make("open_wake", other);
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(error.message, reply_id_text(other, asked));
      this.assertEqual(inputs_of(rig).length, 0);
      open_answer(rig, "open_wake");
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A reply without a token is refused and sends nothing.
    test_token_missing(): void {
      const rig = rig_make();
      rig.view.open_request();
      const error = thrown_get(() => open_answer(rig, "open_wake_bare"));
      this.assertEqual(error.message, gold_text("console_view_token_invalid"));
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
      this.assertEqual(inputs_of(rig).length, 2);
      this.assertEqual(rig.tasks.given.slice(2), [
        notify_expected(Uint8Array.of(0x30, 0x6c, 0x73, 0x0d)),
      ]);
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
        gold_text("console_view_input_phase_idle"),
      );
      this.assertEqual(rig.tasks.given.length, 0);
    }

    // Before ttyd's first message the terminal takes no input either.
    test_input_opening(): void {
      const rig = rig_make();
      rig.view.open_request();
      rig.terminal.text_type("x");
      this.assertTrue(rig.terminal.options.disableStdin);
      const error = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        error.message,
        gold_text("console_view_input_phase_opening"),
      );
      this.assertEqual(inputs_of(rig).length, 0);
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
      this.assertEqual(rig.tasks.given.length, 0);
      rig_start(rig);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      this.assertEqual(
        text_decode(blob_bytes(inputs[0])),
        first_message("fitted"),
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
      this.assertEqual(rig.tasks.given.length, 0);
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
      this.assertEqual(error.message, gold_text("console_view_rows_unfit"));
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
      const encoder = new TextEncoder();
      this.assertEqual(rig.terminal.written.length, 2);
      this.assertEqual(rig.terminal.written[0], encoder.encode("$ "));
      this.assertEqual(rig.terminal.written[1], encoder.encode("hi\r\n"));
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
          gold_text(`console_view_kind_unknown_${kind}`),
        );
      }
      this.assertEqual(rig.terminal.written.length, 0);
    }

    // A message with no bytes has no kind and is refused.
    test_message_empty(): void {
      const rig = rig_make();
      rig_start(rig);
      const error = thrown_get(() => rig.view.output_feed(new Uint8Array(0)));
      this.assertEqual(error.message, gold_text("console_view_message_empty"));
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
      this.assertEqual(
        rig.terminal.written[0],
        new TextEncoder().encode("kept"),
      );
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
    // A request gives the queue one `console.close` and turns input off.
    test_close_request(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.close_request();
      this.assertEqual(rig.tasks.given.length, 3);
      this.assertEqual(rig.tasks.given[2], submit_expected("close_request"));
      this.assertTrue(rig.terminal.options.disableStdin);
    }

    // The request returns a sleep on the id it got that wakes with its type.
    test_close_sleep(): void {
      const rig = rig_make();
      rig_start(rig);
      const sleep = rig.view.close_request();
      this.assertEqual(
        sleep,
        sleep_make("close_sleep", constants.request_ids[1]),
      );
    }

    // The reply leaves the console closing, taking no input and no opening.
    test_close_reply(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.close_request();
      close_answer(rig);
      this.assertTrue(rig.terminal.options.disableStdin);
      const typed = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        typed.message,
        gold_text("console_view_input_phase_closing"),
      );
      const again = thrown_get(() => rig.view.open_request());
      this.assertEqual(
        again.message,
        gold_text("console_view_open_phase_closing"),
      );
      this.assertEqual(rig.tasks.given.length, 3);
    }

    // A close while idle, opening or closing is refused and gives nothing.
    test_close_phase(): void {
      const idle = rig_make();
      const first = thrown_get(() => idle.view.close_request());
      this.assertEqual(
        first.message,
        gold_text("console_view_close_phase_idle"),
      );
      this.assertEqual(idle.tasks.given.length, 0);
      const opening = rig_make();
      opening.view.open_request();
      const early = thrown_get(() => opening.view.close_request());
      this.assertEqual(
        early.message,
        gold_text("console_view_close_phase_opening"),
      );
      this.assertEqual(opening.tasks.given.length, 1);
      const closing = rig_make();
      rig_start(closing);
      closing.view.close_request();
      const twice = thrown_get(() => closing.view.close_request());
      this.assertEqual(
        twice.message,
        gold_text("console_view_close_phase_closing"),
      );
      this.assertEqual(closing.tasks.given.length, 3);
    }

    // A wake of the close before any close is asked for is refused.
    test_closed_early(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_make("close_wake", constants.request_ids[1]);
      const error = thrown_get(() => rig.view.close_done(wake));
      this.assertEqual(error.message, gold_text("console_view_closed_phase"));
    }

    // A reply of another type or to another request is refused.
    test_closed_checked(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.close_request();
      const [opened, closed] = constants.request_ids;
      const other = wake_make("close_wake_open_reply", closed);
      const typed = thrown_get(() => rig.view.close_done(other));
      this.assertEqual(
        typed.message,
        gold_text("console_view_reply_type_open"),
      );
      const stray = wake_make("close_wake", opened);
      const wrong = thrown_get(() => rig.view.close_done(stray));
      this.assertEqual(wrong.message, reply_id_text(opened, closed));
      close_answer(rig);
    }

    // The end after a close leaves the console idle, and it opens again.
    test_close_reopen(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.close_request();
      close_answer(rig);
      rig.view.exit_done();
      rig.view.open_request();
      this.assertEqual(submits_of(rig), [
        gold_line("open_request"),
        gold_line("close_request"),
        gold_line("open_request"),
      ]);
      open_answer(rig, "open_wake");
      this.assertEqual(inputs_of(rig).length, 2);
      this.assertFalse(rig.terminal.options.disableStdin);
      rig.terminal.text_type("a");
      this.assertEqual(inputs_of(rig).length, 3);
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
      this.assertEqual(
        idle.message,
        gold_text("console_view_exit_phase_idle"),
      );
      rig.view.open_request();
      const opening = thrown_get(() => rig.view.exit_done());
      this.assertEqual(
        opening.message,
        gold_text("console_view_exit_phase_opening"),
      );
    }

    // A second end is refused, as the console is idle again.
    test_exit_twice(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      const error = thrown_get(() => rig.view.exit_done());
      this.assertEqual(
        error.message,
        gold_text("console_view_exit_phase_idle"),
      );
    }

    // Text that reaches the view after the end is refused and sends nothing.
    test_input_closed(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      const error = thrown_get(() => rig.terminal.text_force("x"));
      this.assertEqual(
        error.message,
        gold_text("console_view_input_phase_idle"),
      );
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A request after the end asks for tty 0 again and sends a first message.
    test_open_again(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.exit_done();
      rig.view.open_request();
      this.assertEqual(rig.tasks.given.length, 3);
      this.assertEqual(rig.tasks.given[2], submit_expected("open_request"));
      this.assertTrue(rig.terminal.options.disableStdin);
      open_answer(rig, "open_wake");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(
        text_decode(blob_bytes(inputs[1])),
        first_message("token"),
      );
      this.assertFalse(rig.terminal.options.disableStdin);
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
