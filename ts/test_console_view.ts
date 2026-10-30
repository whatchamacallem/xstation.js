// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the console view on the real xterm.js terminal, on a container
// above a band in a frame of a fixed size, put in the page by each test and
// taken out after it. Each view has a real task queue of its own in
// synchronous mode, whose lane to the AI worker is one of a linked pair of
// local ports, the test's end keeping every line the view sends. The
// requests run in handlers of types each view registers, which take over
// the view's sleep with a wake of their own and hand the view its wake, as
// the page's handlers do. Keystrokes and text reach the terminal as DOM
// events sent to its input. The rows the terminal shows are read from its
// rows element, and the first message is compared with the gold's text
// with those rows filled in. The lines, sleeps, wakes and texts of the
// refusals are the gold record's. What the terminal does with output comes
// after the call that feeds it, so it is tested by the view's line cases.
namespace test_console_view {
  // The threads, the type prefix, the frame and the elements of xterm.js.
  const constants = Object.freeze({
    // The thread the view gives its lines to, and the view's own thread.
    owner: "ai" as const,
    thread: "ui" as const,
    // The prefix of the types the views register, each one new.
    type_prefix: "console_test.",
    // The pixel sizes of the frame and the band, chosen by their writer.
    frame_width: 1000,
    frame_height: 400,
    band_height: 50,
    // The height of the frame that leaves fewer rows, its writer's choice.
    frame_lower: 300,
    // The width of the frame under the terminal's columns, its writer's.
    frame_narrow: 500,
    // The elements xterm.js makes: the terminal, its rows and its input.
    terminal_selector: ".xterm",
    screen_selector: ".xterm-screen",
    rows_selector: ".xterm-rows",
    input_selector: ".xterm-helper-textarea",
    // The first byte of ttyd's first message, the brace of its JSON.
    brace: 0x7b,
  });

  // The rigs made since the last `setUp`, whose frames `tearDown` takes out.
  let rigs_made: ViewRig[] = [];

  // How many types the views have registered, so that each one is new.
  let types_made = 0;

  // A view in its frame on its queue, and the test's end of its AI lane.
  interface ViewRig {
    frame: HTMLElement;
    container: HTMLElement;
    band: HTMLElement;
    view: console_view.ConsoleView;
    // The test's end of the lane to the AI worker, and every line it got.
    lane: queue.LocalPort;
    came: lines.Line[];
    // The types whose handlers ask for tty 0 and for its close.
    open_type: string;
    close_type: string;
    // The sleeps the view returned to those handlers, in order.
    sleeps: dispatch.Sleep[];
  }

  // A test case that takes out the frames of its views, each hidden first.
  class ViewCase extends unittest.TestCase {
    // Starts with no rig made.
    setUp(): void {
      rigs_made = [];
    }

    // Hidden, a view fits nothing when the frame's removal is reported.
    tearDown(): void {
      for (const rig of rigs_made) {
        rig.view.view_hide();
        rig.frame.remove();
      }
      rigs_made = [];
    }
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

  // A gold text with each run time placeholder `{n}` replaced by its value.
  function text_fill(text: string, values: readonly unknown[]): string {
    let filled = text;
    for (const [index, value] of values.entries()) {
      filled = filled.replaceAll(`{${index}}`, String(value));
    }
    return filled;
  }

  // A ttyd first message of the gold, its rows filled in when it has none.
  function first_message(name: string, rows?: number): string {
    const text = gold_value(`first_messages.${name}`) as string;
    return text_fill(text, [rows]);
  }

  // Sets a field of a line's header in the header's own name form.
  function field_set(
    line: lines.Line,
    full: string,
    short: string,
    value: number,
  ): lines.Line {
    const header = line[0] as unknown as { [field: string]: unknown };
    header[Object.hasOwn(header, "type") ? full : short] = value;
    return line;
  }

  // A wake of the gold whose one reply answers the request of the id.
  function wake_make(name: string, id: number): lines.Line {
    const wake = gold_line(name);
    const replies = wake.replies as lines.Line[];
    field_set(replies[0], "reply", "r", id);
    return wake;
  }

  // A sleep of the gold that waits for the request of the id.
  function sleep_make(name: string, id: number): dispatch.Sleep {
    const sleep = gold_value(`lines.${name}`) as dispatch.Sleep;
    sleep.wait_ids = [id];
    return sleep;
  }

  // A request of the gold as the view submits it, with the id it got.
  function request_expected(name: string, id: number): lines.Line {
    return field_set(gold_line(name), "id", "i", id);
  }

  // The `console.input` line of the gold that carries one message as blob 1.
  function input_expected(message: Uint8Array): lines.Line {
    const line = gold_line("input");
    line[1] = { size: message.length, d: message };
    return line;
  }

  // The text of the refusal of a reply to one request while another waits.
  function reply_id_text(answered: number, waited: number): string {
    return text_fill(gold_text("console_view_reply_id"), [answered, waited]);
  }

  // A type that no other view registers, with its handler.
  function handler_fresh(fn: dispatch.Handler): string {
    types_made += 1;
    const type = `${constants.type_prefix}${types_made}`;
    dispatch.handler_register(type, 0, fn);
    return type;
  }

  // A line of a type, with no payload, in the name form the settings pick.
  function line_typed(type: string): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], {});
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

  // A queue of the view's thread whose lane to the AI worker is the test's.
  function lane_make(): {
    tasks: queue.TaskQueue;
    lane: queue.LocalPort;
    came: lines.Line[];
  } {
    const owners = { [constants.type_prefix]: constants.thread };
    const tasks = new queue.TaskQueue(constants.thread, owners, true);
    const near = new queue.LocalPort();
    const lane = new queue.LocalPort(near);
    const came: lines.Line[] = [];
    lane.line_receive((line) => {
      came.push(line);
    });
    tasks.port_add(constants.owner, near);
    return { tasks, lane, came };
  }

  // Makes a view in a frame on a queue of its own, its handlers registered.
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
    const { tasks, lane, came } = lane_make();
    const view = new console_view.ConsoleView(container, tasks);
    const sleeps: dispatch.Sleep[] = [];
    // The request's sleep, taken over with the wake of the test's type.
    const asked = (sleep: dispatch.Sleep, then: string): dispatch.Sleep => {
      sleeps.push(sleep);
      return dispatch.task_sleep(null, sleep.wait_ids, then);
    };
    const opened = handler_fresh((wake) => {
      view.open_done(wake);
      return undefined;
    });
    const closed = handler_fresh((wake) => {
      view.close_done(wake);
      return undefined;
    });
    const open_type = handler_fresh(() => asked(view.open_request(), opened));
    const close_type = handler_fresh(() =>
      asked(view.close_request(), closed),
    );
    const rig: ViewRig = {
      frame,
      container,
      band,
      view,
      lane,
      came,
      open_type,
      close_type,
      sleeps,
    };
    rigs_made.push(rig);
    return rig;
  }

  // The id of the last request the view sent, as its line came.
  function id_last(rig: ViewRig): number {
    const requests = rig.came.filter(
      (line) => jslb.field_get(line[0], "id") !== undefined,
    );
    const last = requests[requests.length - 1];
    return jslb.field_get(last[0], "id") as number;
  }

  // Asks for tty 0 from a handler of the view's queue, as ctrl 0 does.
  function open_ask(rig: ViewRig): void {
    rig.lane.line_post(line_typed(rig.open_type), []);
  }

  // Asks to close tty 0 from a handler of the view's queue.
  function close_ask(rig: ViewRig): void {
    rig.lane.line_post(line_typed(rig.close_type), []);
  }

  // Answers the view's last request with a reply of the gold, as the AI does.
  function request_answer(rig: ViewRig, name: string): void {
    const reply = field_set(gold_line(name), "reply", "r", id_last(rig));
    rig.lane.line_post(reply, []);
  }

  // Asks for the console and answers with the token, so that it is open.
  function rig_start(rig: ViewRig): void {
    open_ask(rig);
    request_answer(rig, "open_reply");
  }

  // The `console.input` lines the view sent, in order.
  function inputs_of(rig: ViewRig): lines.Line[] {
    return rig.came.filter(
      (line) => jslb.field_get(line[0], "type") === "console.input",
    );
  }

  // The one child element the view made in a container.
  function child_find(container: HTMLElement): HTMLElement {
    return container.firstElementChild as HTMLElement;
  }

  // The element of the view's terminal that xterm.js names, which is there.
  function part_find(rig: ViewRig, selector: string): HTMLElement {
    const part = rig.container.querySelector<HTMLElement>(selector);
    if (part === null) {
      throw new Error(`The terminal has no element ${selector} yet.`);
    }
    return part;
  }

  // How many rows the terminal on the page has.
  function rows_count(rig: ViewRig): number {
    return part_find(rig, constants.rows_selector).childElementCount;
  }

  // Types text into the terminal, as an input method gives it.
  function text_type(rig: ViewRig, text: string): void {
    const input = part_find(rig, constants.input_selector);
    input.dispatchEvent(
      new InputEvent("input", { data: text, inputType: "insertText" }),
    );
  }

  // Presses a key in the terminal, with control or without.
  function key_press(
    rig: ViewRig,
    key: string,
    code: number,
    control: boolean,
  ): void {
    const input = part_find(rig, constants.input_selector);
    input.dispatchEvent(
      new KeyboardEvent("keydown", {
        key,
        keyCode: code,
        ctrlKey: control,
        bubbles: true,
        cancelable: true,
      }),
    );
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

  // Asserts that the rows fill the space above the band, every one whole.
  function fit_assert(test: unittest.TestCase, rig: ViewRig): void {
    const { container, band } = rig;
    const screen = part_find(rig, constants.screen_selector);
    const height = screen.getBoundingClientRect().height;
    const cell = height / rows_count(rig);
    const top = container.getBoundingClientRect().top;
    const bars = container.offsetHeight - container.clientHeight;
    const space = band.getBoundingClientRect().top - top - bars;
    test.assertTrue(
      height <= space && space < height + cell,
      `${height} px of rows of ${cell} px in ${space} px`,
    );
    test.assertTrue(
      container.scrollHeight <= container.clientHeight,
      `${container.scrollHeight} px of rows in ${container.clientHeight} px`,
    );
    test.assertTrue(
      screen.getBoundingClientRect().bottom <=
        band.getBoundingClientRect().top,
      "the rows end below the top of the band",
    );
  }

  // Making, showing, hiding and toggling the view.
  export class TestVisibility extends ViewCase {
    // The view makes one hidden child and no terminal in it, and sends none.
    test_made_hidden(): void {
      const rig = rig_make();
      const child = child_find(rig.container);
      this.assertEqual(rig.container.childElementCount, 1);
      this.assertEqual(child.tagName, "DIV");
      this.assertTrue(child.hidden);
      this.assertEqual(child.childElementCount, 0);
      this.assertEqual(rig.came.length, 0);
    }

    // Two views on one queue can be made, as a view registers no handler.
    test_made_twice(): void {
      const { tasks, came } = lane_make();
      const containers = [0, 1].map(() => document.createElement("div"));
      for (const container of containers) {
        new console_view.ConsoleView(container, tasks);
      }
      for (const container of containers) {
        this.assertEqual(container.childElementCount, 1);
        this.assertTrue(child_find(container).hidden);
      }
      this.assertEqual(came.length, 0);
    }

    // The terminal is made 120 columns wide and 40 rows high.
    test_made_size(): void {
      const rig = rig_make();
      rig_start(rig);
      const message = JSON.parse(text_decode(blob_bytes(inputs_of(rig)[0])));
      this.assertEqual([message.columns, message.rows], [120, 40]);
    }

    // The first show reveals the child, opens the terminal in it, focuses it.
    test_first_show(): void {
      const rig = rig_make();
      rig.view.view_show();
      const child = child_find(rig.container);
      this.assertFalse(child.hidden);
      const terminals = child.querySelectorAll(constants.terminal_selector);
      this.assertEqual(terminals.length, 1);
      this.assertTrue(terminals[0].parentElement === child);
      this.assertTrue(
        document.activeElement === part_find(rig, constants.input_selector),
      );
      this.assertEqual(rig.came.length, 0);
    }

    // Later shows reveal the child and focus again, and ask for nothing.
    test_later_show(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      part_find(rig, constants.input_selector).blur();
      rig.view.view_show();
      const child = child_find(rig.container);
      this.assertFalse(child.hidden);
      this.assertEqual(
        child.querySelectorAll(constants.terminal_selector).length,
        1,
      );
      this.assertTrue(
        document.activeElement === part_find(rig, constants.input_selector),
      );
      this.assertEqual(rig.came.length, 0);
    }

    // A hide hides the child and leaves the terminal in it.
    test_hide_shown(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig.view.view_hide();
      const child = child_find(rig.container);
      this.assertTrue(child.hidden);
      this.assertEqual(
        child.querySelectorAll(constants.terminal_selector).length,
        1,
      );
      this.assertEqual(rig.came.length, 0);
    }

    // A hide before any show leaves the terminal out of the page.
    test_hide_idle(): void {
      const rig = rig_make();
      rig.view.view_hide();
      const child = child_find(rig.container);
      this.assertTrue(child.hidden);
      this.assertEqual(child.childElementCount, 0);
      this.assertEqual(rig.came.length, 0);
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
      this.assertEqual(
        child.querySelectorAll(constants.terminal_selector).length,
        1,
      );
      this.assertEqual(rig.came.length, 0);
    }

    // Showing an open console fits its rows and sends no resize to tty 0.
    test_toggle_open(): void {
      const rig = rig_make();
      rig_start(rig);
      rig.view.view_toggle();
      fit_assert(this, rig);
      rig.view.view_toggle();
      this.assertEqual(rig.came.length, 2);
      text_type(rig, "a");
      this.assertEqual(inputs_of(rig).length, 2);
    }

    // The view wants tty 0 when shown while idle, at first and after its end.
    test_open_wanted(): void {
      const rig = rig_make();
      this.assertFalse(rig.view.open_wanted());
      rig.view.view_show();
      this.assertTrue(rig.view.open_wanted());
      open_ask(rig);
      this.assertFalse(rig.view.open_wanted());
      request_answer(rig, "open_reply");
      this.assertFalse(rig.view.open_wanted());
      rig.view.exit_done();
      this.assertTrue(rig.view.open_wanted());
      rig.view.view_hide();
      this.assertFalse(rig.view.open_wanted());
      this.assertEqual(rig.came.length, 2);
    }

    // The view is open only while tty 0 is open: not idle, opening, closing.
    test_open_is(): void {
      const rig = rig_make();
      this.assertFalse(rig.view.open_is());
      open_ask(rig);
      this.assertFalse(rig.view.open_is());
      request_answer(rig, "open_reply");
      this.assertTrue(rig.view.open_is());
      close_ask(rig);
      this.assertFalse(rig.view.open_is());
      request_answer(rig, "close_reply");
      this.assertFalse(rig.view.open_is());
      rig.view.exit_done();
      this.assertFalse(rig.view.open_is());
    }
  }

  // The request for tty 0, its wake and ttyd's first message.
  export class TestOpening extends ViewCase {
    // A request gives the AI worker one `console.open`, and input stays off.
    test_open_request(): void {
      const rig = rig_make();
      rig.view.view_show();
      open_ask(rig);
      this.assertEqual(rig.came, [request_expected("open_request", 1)]);
      text_type(rig, "x");
      this.assertEqual(rig.came.length, 1);
    }

    // The request returns a sleep on the id it got that wakes with its type.
    test_sleep_returned(): void {
      const rig = rig_make();
      open_ask(rig);
      this.assertEqual(rig.sleeps, [sleep_make("open_sleep", id_last(rig))]);
    }

    // Lines take the name form the settings pick, full exactly in debug mode.
    test_full_names(): void {
      const rig = rig_make();
      rig_start(rig);
      close_ask(rig);
      const full = harness.setting_get("debug") === true;
      this.assertEqual(rig.came.length, 3);
      for (const line of rig.came) {
        this.assertEqual("type" in line[0], full);
        this.assertEqual("t" in line[0], !full);
      }
    }

    // A second request while opening or open is refused and gives nothing.
    test_open_twice(): void {
      const opening = rig_make();
      open_ask(opening);
      const early = thrown_get(() => opening.view.open_request());
      this.assertEqual(
        early.message,
        gold_text("console_view_open_phase_opening"),
      );
      this.assertEqual(opening.came.length, 1);
      const open = rig_make();
      rig_start(open);
      const late = thrown_get(() => open.view.open_request());
      this.assertEqual(
        late.message,
        gold_text("console_view_open_phase_open"),
      );
      this.assertEqual(open.came.length, 2);
    }

    // The wake gives ttyd's first message, the one for an empty token.
    test_first_message(): void {
      const rig = rig_make();
      open_ask(rig);
      request_answer(rig, "open_reply_empty");
      const message = new TextEncoder().encode(first_message("empty"));
      this.assertEqual(rig.came.slice(1), [input_expected(message)]);
      rig.view.view_show();
      text_type(rig, "x");
      this.assertEqual(inputs_of(rig).length, 2);
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
      rig.frame.style.height = `${constants.frame_lower}px`;
      rig.view.view_show();
      rig.view.view_hide();
      open_ask(rig);
      request_answer(rig, "open_reply_empty");
      const bytes = blob_bytes(inputs_of(rig)[0]);
      this.assertEqual(bytes[0], constants.brace);
      this.assertEqual(
        text_decode(bytes),
        first_message("sized", rows_count(rig)),
      );
    }

    // A wake before any request is refused and sends nothing.
    test_reply_idle(): void {
      const rig = rig_make();
      rig.view.view_show();
      const error = thrown_get(() =>
        rig.view.open_done(wake_make("open_wake", 1)),
      );
      this.assertEqual(
        error.message,
        gold_text("console_view_reply_phase_idle"),
      );
      text_type(rig, "x");
      this.assertEqual(rig.came.length, 0);
    }

    // A second wake is refused and sends nothing more.
    test_reply_twice(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_make("open_wake", id_last(rig));
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
      rig.view.view_show();
      open_ask(rig);
      const wake = wake_make("open_wake_close_reply", id_last(rig));
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(
        error.message,
        gold_text("console_view_reply_type_close"),
      );
      text_type(rig, "x");
      this.assertEqual(inputs_of(rig).length, 0);
    }

    // A wake with the reply to another request is refused, the right one not.
    test_reply_id(): void {
      const rig = rig_make();
      open_ask(rig);
      const asked = id_last(rig);
      const other = asked + 1;
      const wake = wake_make("open_wake", other);
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(error.message, reply_id_text(other, asked));
      this.assertEqual(inputs_of(rig).length, 0);
      request_answer(rig, "open_reply");
      this.assertEqual(inputs_of(rig).length, 1);
    }

    // A reply without a token is refused and sends nothing.
    test_token_missing(): void {
      const rig = rig_make();
      rig.view.view_show();
      open_ask(rig);
      const wake = wake_make("open_wake_bare", id_last(rig));
      const error = thrown_get(() => rig.view.open_done(wake));
      this.assertEqual(error.message, gold_text("console_view_token_invalid"));
      text_type(rig, "x");
      this.assertEqual(inputs_of(rig).length, 0);
    }
  }

  // The keystrokes and text the terminal emits, as ttyd's input messages.
  export class TestInput extends ViewCase {
    // Shows the view of a new rig and opens tty 0, so that input is taken.
    rig_typing(): ViewRig {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      return rig;
    }

    // A batch of text is one line whose blob is a zero and the text.
    test_ascii_batch(): void {
      const rig = this.rig_typing();
      text_type(rig, "ls\r");
      this.assertEqual(inputs_of(rig).length, 2);
      this.assertEqual(rig.came.slice(2), [
        input_expected(Uint8Array.of(0x30, 0x6c, 0x73, 0x0d)),
      ]);
    }

    // Each batch is its own line, in the order the terminal emitted them.
    test_each_batch(): void {
      const rig = this.rig_typing();
      text_type(rig, "a");
      text_type(rig, "b");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 3);
      this.assertEqual(blob_bytes(inputs[1]), message_bytes(0x30, "a"));
      this.assertEqual(blob_bytes(inputs[2]), message_bytes(0x30, "b"));
    }

    // Each key pressed is its own line, the key's text after the zero.
    test_keys_pressed(): void {
      const rig = this.rig_typing();
      key_press(rig, "l", 0x4c, false);
      key_press(rig, "Enter", 0x0d, false);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 3);
      this.assertEqual(blob_bytes(inputs[1]), message_bytes(0x30, "l"));
      this.assertEqual(blob_bytes(inputs[2]), Uint8Array.of(0x30, 0x0d));
    }

    // A character of two bytes is sent as its two `UTF-8` bytes.
    test_two_bytes(): void {
      const rig = this.rig_typing();
      text_type(rig, String.fromCodePoint(0xe9));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xc3, 0xa9),
      );
    }

    // A character of three bytes is sent as its three `UTF-8` bytes.
    test_three_bytes(): void {
      const rig = this.rig_typing();
      text_type(rig, String.fromCodePoint(0x4e2d));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xe4, 0xb8, 0xad),
      );
    }

    // A character of four bytes, two `UTF-16` units, is sent as four bytes.
    test_four_bytes(): void {
      const rig = this.rig_typing();
      text_type(rig, String.fromCodePoint(0x1f600));
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0xf0, 0x9f, 0x98, 0x80),
      );
    }

    // A batch of mixed characters is one line with the bytes in order.
    test_mixed_batch(): void {
      const rig = this.rig_typing();
      const text =
        "a" +
        String.fromCodePoint(0xe9) +
        String.fromCodePoint(0x4e2d) +
        String.fromCodePoint(0x1f600);
      text_type(rig, text);
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

    // Control with a letter is sent as its control byte after the zero.
    test_control_byte(): void {
      const rig = this.rig_typing();
      key_press(rig, "c", 0x43, true);
      this.assertEqual(
        blob_bytes(inputs_of(rig)[1]),
        Uint8Array.of(0x30, 0x03),
      );
    }

    // Before any request the terminal takes no input, so nothing is sent.
    test_input_idle(): void {
      const rig = rig_make();
      rig.view.view_show();
      text_type(rig, "x");
      key_press(rig, "c", 0x43, true);
      this.assertEqual(rig.came.length, 0);
    }

    // Before ttyd's first message the terminal takes no input either.
    test_input_opening(): void {
      const rig = rig_make();
      rig.view.view_show();
      open_ask(rig);
      text_type(rig, "x");
      this.assertEqual(rig.came.length, 1);
      this.assertEqual(inputs_of(rig).length, 0);
    }
  }

  // The rows fitted to the height the container has above the band.
  export class TestFit extends ViewCase {
    // A show fits the rows to the space above the band, so none is scrolled.
    test_rows_fitted(): void {
      const rig = rig_make();
      rig.view.view_show();
      fit_assert(this, rig);
      this.assertEqual(rig.came.length, 0);
    }

    // A fit while idle sends nothing, and the first message has the rows.
    test_fitted_first(): void {
      const rig = rig_make();
      rig.view.view_show();
      this.assertEqual(rig.came.length, 0);
      rig_start(rig);
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 1);
      this.assertEqual(
        text_decode(blob_bytes(inputs[0])),
        first_message("fitted", rows_count(rig)),
      );
    }

    // A later show fits the rows again, to the space the frame has then.
    test_space_changed(): void {
      const rig = rig_make();
      rig.view.view_show();
      const before = rows_count(rig);
      rig.view.view_hide();
      rig.frame.style.height = `${constants.frame_lower}px`;
      rig.view.view_show();
      fit_assert(this, rig);
      this.assertTrue(rows_count(rig) < before);
      this.assertEqual(rig.came.length, 0);
    }

    // A scroll bar under wide columns is left out of the space.
    test_narrow_frame(): void {
      const rig = rig_make();
      rig.frame.style.width = `${constants.frame_narrow}px`;
      rig.view.view_show();
      const container = rig.container;
      this.assertTrue(container.scrollWidth > container.clientWidth);
      this.assertTrue(container.offsetHeight > container.clientHeight);
      fit_assert(this, rig);
    }

    // A band that leaves no room for one row is refused.
    test_rows_unfit(): void {
      const rig = rig_make();
      rig.band.style.height = `${constants.frame_height}px`;
      const error = thrown_get(() => rig.view.view_show());
      const { container, band } = rig;
      const screen = part_find(rig, constants.screen_selector);
      const cell = screen.getBoundingClientRect().height / rows_count(rig);
      const top = container.getBoundingClientRect().top;
      const bars = container.offsetHeight - container.clientHeight;
      const space = band.getBoundingClientRect().top - top - bars;
      this.assertEqual(
        error.message,
        text_fill(gold_text("console_view_rows_unfit"), [space, cell]),
      );
      this.assertEqual(rows_count(rig), 40);
    }
  }

  // The messages of ttyd that `output_feed` refuses before writing.
  export class TestOutput extends ViewCase {
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
    }

    // A message with no bytes has no kind and is refused.
    test_message_empty(): void {
      const rig = rig_make();
      rig_start(rig);
      const error = thrown_get(() => rig.view.output_feed(new Uint8Array(0)));
      this.assertEqual(error.message, gold_text("console_view_message_empty"));
    }
  }

  // The request to close tty 0, its wake, and the end that follows it.
  export class TestClosing extends ViewCase {
    // A request gives the AI worker one `console.close` and turns input off.
    test_close_request(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      close_ask(rig);
      this.assertEqual(rig.came.length, 3);
      this.assertEqual(rig.came[2], request_expected("close_request", 2));
      text_type(rig, "x");
      this.assertEqual(rig.came.length, 3);
    }

    // The request returns a sleep on the id it got that wakes with its type.
    test_close_sleep(): void {
      const rig = rig_make();
      rig_start(rig);
      close_ask(rig);
      this.assertEqual(rig.sleeps.length, 2);
      this.assertEqual(rig.sleeps[1], sleep_make("close_sleep", id_last(rig)));
    }

    // The reply leaves the console closing, taking no input and no opening.
    test_close_reply(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      close_ask(rig);
      request_answer(rig, "close_reply");
      text_type(rig, "x");
      const again = thrown_get(() => rig.view.open_request());
      this.assertEqual(
        again.message,
        gold_text("console_view_open_phase_closing"),
      );
      this.assertEqual(rig.came.length, 3);
    }

    // A close while idle, opening or closing is refused and gives nothing.
    test_close_phase(): void {
      const idle = rig_make();
      const first = thrown_get(() => idle.view.close_request());
      this.assertEqual(
        first.message,
        gold_text("console_view_close_phase_idle"),
      );
      this.assertEqual(idle.came.length, 0);
      const opening = rig_make();
      open_ask(opening);
      const early = thrown_get(() => opening.view.close_request());
      this.assertEqual(
        early.message,
        gold_text("console_view_close_phase_opening"),
      );
      this.assertEqual(opening.came.length, 1);
      const closing = rig_make();
      rig_start(closing);
      close_ask(closing);
      const twice = thrown_get(() => closing.view.close_request());
      this.assertEqual(
        twice.message,
        gold_text("console_view_close_phase_closing"),
      );
      this.assertEqual(closing.came.length, 3);
    }

    // A wake of the close before any close is asked for is refused.
    test_closed_early(): void {
      const rig = rig_make();
      rig_start(rig);
      const wake = wake_make("close_wake", id_last(rig) + 1);
      const error = thrown_get(() => rig.view.close_done(wake));
      this.assertEqual(error.message, gold_text("console_view_closed_phase"));
    }

    // A reply of another type or to another request is refused.
    test_closed_checked(): void {
      const rig = rig_make();
      rig_start(rig);
      const opened = id_last(rig);
      close_ask(rig);
      const closed = id_last(rig);
      const other = wake_make("close_wake_open_reply", closed);
      const typed = thrown_get(() => rig.view.close_done(other));
      this.assertEqual(
        typed.message,
        gold_text("console_view_reply_type_open"),
      );
      const stray = wake_make("close_wake", opened);
      const wrong = thrown_get(() => rig.view.close_done(stray));
      this.assertEqual(wrong.message, reply_id_text(opened, closed));
      request_answer(rig, "close_reply");
    }

    // The end after a close leaves the console idle, and it opens again.
    test_close_reopen(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      close_ask(rig);
      request_answer(rig, "close_reply");
      rig.view.exit_done();
      open_ask(rig);
      const requests = rig.came.filter(
        (line) => jslb.field_get(line[0], "id") !== undefined,
      );
      this.assertEqual(requests, [
        request_expected("open_request", 1),
        request_expected("close_request", 2),
        request_expected("open_request", 3),
      ]);
      request_answer(rig, "open_reply");
      this.assertEqual(inputs_of(rig).length, 2);
      text_type(rig, "a");
      this.assertEqual(inputs_of(rig).length, 3);
    }
  }

  // The end of tty 0, after which the console can be asked for again.
  export class TestExit extends ViewCase {
    // The end turns input off, so typing sends nothing more.
    test_exit_open(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      rig.view.exit_done();
      text_type(rig, "x");
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
      open_ask(rig);
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

    // A request after the end asks for tty 0 again and sends a first message.
    test_open_again(): void {
      const rig = rig_make();
      rig.view.view_show();
      rig_start(rig);
      rig.view.exit_done();
      open_ask(rig);
      this.assertEqual(rig.came.length, 3);
      this.assertEqual(rig.came[2], request_expected("open_request", 2));
      text_type(rig, "x");
      this.assertEqual(rig.came.length, 3);
      request_answer(rig, "open_reply");
      const inputs = inputs_of(rig);
      this.assertEqual(inputs.length, 2);
      this.assertEqual(
        text_decode(blob_bytes(inputs[1])),
        first_message("fitted", rows_count(rig)),
      );
      text_type(rig, "x");
      this.assertEqual(inputs_of(rig).length, 3);
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
