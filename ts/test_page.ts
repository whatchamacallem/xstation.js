// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the UI thread on the test page's document: the owner table, the
// reading of the worker's first line and faults, the DOM port's listeners
// and permit buttons, the handlers called through a register double with
// queue, image, console and overlay doubles, each line, sleep and text
// compared to the gold, the column the style lays the page out in, and the
// frozen module.

namespace test_page {
  // The text the band shows, the ids the queue double answers, the settings.
  const constants = Object.freeze({
    greeting: "How can I help you?",
    submit_ids: Object.freeze([21, 22]),
    // The members of `settings.json`, each read by the harness.
    settings_names: Object.freeze([
      "debug",
      "queue_synchronous",
      "verbose_level",
      "verbose_ring",
      "line_max",
      "blob_max",
      "overflow_bytes",
      "chunk_bytes",
      "srv_buf_size",
      "media_db_bytes",
      "turn_compact_turns",
      "provider",
      "powershell",
    ]),
  });

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`typescript.test_page.${name}`));
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(`typescript.test_page.texts.${name}`) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A copy of a sleep of this module's gold, its run time parts set on it.
  function gold_sleep(name: string): dispatch.Sleep {
    return gold_value(`lines.${name}`) as dispatch.Sleep;
  }

  // Sets the reply field of a line's header in the header's own name form.
  function reply_set(line: lines.Line, id: number): lines.Line {
    const header = line[0] as unknown as { [field: string]: unknown };
    header[Object.hasOwn(header, "type") ? "reply" : "r"] = id;
    return line;
  }

  // Sets the bytes of a line's blob 1, which its gold header gives the size.
  function blob_set(line: lines.Line, data: Uint8Array): lines.Line {
    (line[1] as lines.BlobHeader).d = data;
    return line;
  }

  // A wake of the gold with the sleep's state and the replies it waited for.
  function wake_make(
    name: string,
    sleep: dispatch.Sleep,
    replies: lines.Line[],
  ): lines.Line {
    const wake = gold_line(name);
    wake.state = sleep.state;
    wake.replies = replies;
    return wake;
  }

  // The settings of `settings.json` as the harness reads them, a copy.
  function settings_copy(): settings.Settings {
    const entries = constants.settings_names.map((name) => [
      name,
      structuredClone(harness.setting_get(name)),
    ]);
    return Object.fromEntries(entries) as settings.Settings;
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A queue double: it keeps each line submitted and answers the test's ids.
  class TasksDouble {
    // Each line submitted and its owner, in order.
    readonly submitted: [lines.Line, string | undefined][] = [];
    // The ids still to answer, in order.
    readonly #ids: number[];

    // Takes the ids the double answers, in order.
    constructor(ids: readonly number[]) {
      this.#ids = [...ids];
    }

    // Keeps the line and its owner and answers the next id.
    task_submit(line: lines.Line, owner?: string): number {
      const id = this.#ids.shift();
      if (id === undefined) {
        throw new Error("The queue double has no id left to answer.");
      }
      this.submitted.push([line, owner]);
      return id;
    }
  }

  // An image double: decoded images by key.
  class ImageDouble implements page.ImageSource {
    readonly images = new Map<string, ImageBitmap>();

    // The image of a key, if the double holds one.
    image_get(k: lines.KvRef): ImageBitmap | undefined {
      return this.images.get(k);
    }
  }

  // A console view double: it records each call and submits its opening.
  class ViewDouble implements page.ConsoleControl {
    readonly calls: string[] = [];
    readonly fed: Uint8Array[] = [];
    readonly wakes: lines.Line[] = [];
    // Whether tty 0 is open, which the tests set.
    open = false;
    // Whether tty 0 was asked for and has not ended since.
    asked = false;
    private readonly tasks: TasksDouble;
    // Whether the double is shown, which each toggle changes.
    private shown = false;

    // Takes the queue double the opening is submitted on.
    constructor(tasks: TasksDouble) {
      this.tasks = tasks;
    }

    // Records a toggle and shows or hides the double.
    view_toggle(): void {
      this.calls.push("toggle");
      this.shown = !this.shown;
    }

    // Records a show and shows the double.
    view_show(): void {
      this.calls.push("show");
      this.shown = true;
    }

    // Whether the double is shown and tty 0 is not asked for.
    open_wanted(): boolean {
      return this.shown && !this.asked;
    }

    // Whether the tests set tty 0 open.
    open_is(): boolean {
      return this.open;
    }

    // Submits `console.open` to the AI worker and returns the sleep on it.
    open_request(): dispatch.Sleep {
      this.calls.push("open");
      this.asked = true;
      const id = this.tasks.task_submit(gold_line("console_open"), "ai");
      const sleep = gold_sleep("sleep_console");
      sleep.wait_ids = [id];
      return sleep;
    }

    // Records the wake of the opening.
    open_done(wake: lines.Line): void {
      this.calls.push("done");
      this.wakes.push(wake);
    }

    // Records the wake of the close.
    close_done(wake: lines.Line): void {
      this.calls.push("closed");
      this.wakes.push(wake);
    }

    // Records the end of tty 0, after which it can be asked for again.
    exit_done(): void {
      this.calls.push("exit");
      this.asked = false;
    }

    // Keeps the bytes fed.
    output_feed(data: Uint8Array): void {
      this.fed.push(data);
    }
  }

  // An overlay double: it records each call.
  class OverlayDouble implements page.OverlayControl {
    readonly calls: string[] = [];

    // Records a line added to a tty.
    line_add(tty: number, text: string): void {
      this.calls.push(`line ${tty} ${text}`);
    }

    // Records a toggle of a tty.
    overlay_toggle(tty: number): void {
      this.calls.push(`toggle ${tty}`);
    }
  }

  // The elements the page's code finds, in a container in the document.
  interface FixtureElements {
    container: HTMLElement;
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    form: HTMLFormElement;
    input: HTMLInputElement;
    permit: HTMLElement;
  }

  // Makes the elements in a container and puts it in the document's body.
  function elements_make(document_of: Document): FixtureElements {
    const container = document_of.createElement("div");
    const canvas = document_of.createElement("canvas");
    canvas.id = "image";
    const subtitle = document_of.createElement("p");
    const form = document_of.createElement("form");
    const input = document_of.createElement("input");
    input.id = "input";
    form.append(input);
    const permit = document_of.createElement("div");
    permit.id = "permit";
    container.append(canvas, subtitle, form, permit);
    document_of.body.append(container);
    return { container, canvas, subtitle, form, input, permit };
  }

  // The page's handlers on the elements, with doubles of the queue and parts.
  class HandlerBench {
    readonly tasks = new TasksDouble(constants.submit_ids);
    readonly images = new ImageDouble();
    readonly view = new ViewDouble(this.tasks);
    readonly overlays = new OverlayDouble();
    // The handlers the page registered, by line type.
    readonly #handlers = new Map<string, dispatch.Handler>();

    // Registers the page's handlers on the elements, in debug mode or not.
    constructor(elements: FixtureElements, debug: boolean) {
      page.handlers_register(
        {
          tasks: this.tasks as unknown as queue.TaskQueue,
          canvas: elements.canvas,
          subtitle: elements.subtitle,
          input: elements.input,
          permit: elements.permit,
          images: this.images,
          view: this.view,
          overlays: this.overlays,
          debug,
        },
        (type, _version, fn) => this.handler_keep(type, fn),
      );
    }

    // Keeps a handler the page registered, once per type as dispatch does.
    private handler_keep(type: string, fn: dispatch.Handler): void {
      if (this.#handlers.has(type)) {
        throw new Error(`The page registered ${type} twice.`);
      }
      this.#handlers.set(type, fn);
    }

    // Runs the handler of the type on the line, as the queue would.
    line_run(type: string, line: lines.Line): unknown {
      const fn = this.#handlers.get(type);
      if (fn === undefined) {
        throw new Error(`The page registered no handler for ${type}.`);
      }
      return fn(line);
    }
  }

  // A decoded image of the size given, made at once.
  function bitmap_make(width: number, height: number): ImageBitmap {
    return new OffscreenCanvas(width, height).transferToImageBitmap();
  }

  // A test on elements put in the document in `setUp` and removed after.
  class ElementsCase extends unittest.TestCase {
    // The elements, made from the document in `setUp`.
    #elements: FixtureElements | undefined = undefined;

    // Makes the elements in the test page's document.
    setUp(): void {
      this.#elements = elements_make(document);
    }

    // Takes the elements out of the document.
    tearDown(): void {
      this.elements_get().container.remove();
    }

    // The elements of this test.
    elements_get(): FixtureElements {
      return this.#elements as FixtureElements;
    }
  }

  // The owner table of the UI thread.
  export class TestOwnerTable extends unittest.TestCase {
    // The console goes to the worker but for its output, end and show.
    test_console_routes(): void {
      const owners = page.owners_make();
      this.assertEqual(owners["console."], "ai");
      this.assertEqual(owners["console.output"], "ui");
      this.assertEqual(owners["console.exit"], "ui");
      this.assertEqual(owners["console.show"], "ui");
      this.assertEqual(owners["media."], "ui");
      this.assertEqual(owners["render"], "ui");
      this.assertEqual(owners["ui."], "ui");
      this.assertEqual(owners["dom."], "dom");
      this.assertEqual(owners["verbose."], "ai");
      this.assertFalse(Object.hasOwn(owners, "boot."));
    }

    // The table sends `tap.` lines to the worker.
    test_tap_route(): void {
      this.assertEqual(page.owners_make()["tap."], "ai");
    }
  }

  // The first line of the worker and the messages of its faults.
  export class TestWorkerLines extends unittest.TestCase {
    // The first line must be `settings.set`, which is taken whole.
    test_settings_taken(): void {
      const value = settings_copy();
      const set = gold_line("settings_set");
      set.settings = value;
      this.assertEqual(page.settings_take(set), { settings: value });
      const other = gold_line("ui_tests");
      const error = thrown_get(() => page.settings_take(other));
      this.assertEqual(error.message, gold_text("page_settings_missing"));
    }

    // The gold record that comes with the settings is taken with them.
    test_test_settings(): void {
      const value = settings_copy();
      const set = gold_line("settings_set_gold");
      const gold = structuredClone(set.test_settings);
      set.settings = value;
      this.assertEqual(page.settings_take(set), {
        settings: value,
        test_settings: gold,
      });
    }

    // A message of the worker must be a fault line.
    test_fault_read(): void {
      const { 0: header, ...fields } = gold_line("fault");
      this.assertEqual(page.fault_read({ 0: header, ...fields }), fields);
      const render = gold_line("render_bare");
      const error = thrown_get(() => page.fault_read(render));
      this.assertEqual(error.message, gold_text("page_message_unknown"));
    }
  }

  // The DOM port: the player's text, clicks and keys, the permit buttons.
  export class TestDomPort extends ElementsCase {
    // A submitted text is posted as `ui.input` and the input emptied.
    test_text_submitted(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      elements.input.value = "1";
      const submit = new SubmitEvent("submit", {
        bubbles: true,
        cancelable: true,
      });
      elements.form.dispatchEvent(submit);
      this.assertTrue(submit.defaultPrevented);
      this.assertEqual(received, [gold_line("ui_input_text")]);
      this.assertEqual(elements.input.value, "");
    }

    // A click is posted as the point of the image's pixels it falls on.
    test_click_mapped(): void {
      const elements = this.elements_get();
      const canvas = elements.canvas;
      canvas.width = 4;
      canvas.height = 2;
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      const box = canvas.getBoundingClientRect();
      const scale = Math.min(box.width / 4, box.height / 2);
      const left = (box.width - 4 * scale) / 2;
      const top = (box.height - 2 * scale) / 2;
      const click = new MouseEvent("click", {
        clientX: box.left + left + 1.5 * scale,
        clientY: box.top + top + 0.5 * scale,
        bubbles: true,
      });
      canvas.dispatchEvent(click);
      this.assertEqual(received, [gold_line("ui_input_click")]);
    }

    // A click while the input is closed is not taken.
    test_click_closed(): void {
      const elements = this.elements_get();
      elements.input.disabled = true;
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      const click = new MouseEvent("click", { bubbles: true });
      elements.canvas.dispatchEvent(click);
      this.assertEqual(received.length, 0);
    }

    // Control with a digit is posted and kept from the browser.
    test_control_key(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      const key = new KeyboardEvent("keydown", {
        key: "3",
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      });
      elements.input.dispatchEvent(key);
      this.assertTrue(key.defaultPrevented);
      const plain = new KeyboardEvent("keydown", { key: "3", bubbles: true });
      elements.input.dispatchEvent(plain);
      this.assertEqual(received, [gold_line("ui_control_key_3")]);
    }

    // A `dom.choice` shows its buttons and answers with the one clicked.
    test_choice_answered(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      port.line_post(gold_line("dom_choice"), []);
      const buttons = Array.from(elements.permit.querySelectorAll("button"));
      this.assertEqual(
        buttons.map((button) => button.textContent),
        [
          gold_text("page_choice_accept"),
          gold_text("page_choice_deny"),
          gold_text("page_choice_always"),
        ],
      );
      buttons[1].click();
      this.assertEqual(elements.permit.children.length, 0);
      // The answer keeps the form of the line it answers.
      this.assertEqual(received, [gold_line("dom_choice_answer")]);
    }

    // Another type, a missing id and an unknown choice are refused.
    test_post_refused(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const other = gold_line("dom_other");
      let error = thrown_get(() => port.line_post(other, []));
      this.assertEqual(error.message, gold_text("page_dom_type"));
      const unasked = gold_line("dom_choice_unasked");
      error = thrown_get(() => port.line_post(unasked, []));
      this.assertEqual(error.message, gold_text("page_id_missing"));
      const unknown = gold_line("dom_choice_unknown");
      error = thrown_get(() => port.line_post(unknown, []));
      this.assertEqual(error.message, gold_text("page_choice_unknown"));
      this.assertEqual(elements.permit.children.length, 0);
    }

    // A second receiver and a container without the elements are refused.
    test_port_refused(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, gold_text("page_receiver_twice"));
      const empty = elements.container.ownerDocument.createElement("div");
      const missing = thrown_get(() => new page.DomPort(empty));
      this.assertEqual(missing.message, gold_text("page_element_missing"));
    }
  }

  // The handlers of the UI thread, called as the queue would call them.
  export class TestPageHandlers extends ElementsCase {
    // A render paints its image, shows its subtitle and opens the input.
    test_render_image(): void {
      const elements = this.elements_get();
      elements.input.disabled = true;
      const bench = new HandlerBench(elements, true);
      const render = gold_line("render_image");
      bench.images.images.set(render.image as string, bitmap_make(3, 2));
      const reply = bench.line_run("render", render);
      this.assertEqual(reply, gold_line("render_reply"));
      const canvas = elements.canvas;
      this.assertEqual([canvas.width, canvas.height], [3, 2]);
      this.assertFalse(elements.canvas.hidden);
      this.assertEqual(elements.subtitle.textContent, render.subtitle);
      this.assertFalse(elements.input.disabled);
    }

    // A render with no image shows black, which hides the image.
    test_render_black(): void {
      const elements = this.elements_get();
      const bench = new HandlerBench(elements, true);
      const render = gold_line("render_black");
      bench.line_run("render", render);
      this.assertTrue(elements.canvas.hidden);
      this.assertEqual(elements.subtitle.textContent, render.subtitle);
    }

    // A render of an image the cache does not hold is a fault.
    test_image_missing(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      const render = gold_line("render_image");
      const error = thrown_get(() => bench.line_run("render", render));
      this.assertEqual(error.message, gold_text("page_image_missing"));
    }

    // An image to keep goes to the media port, whose answer goes back.
    test_media_stored(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      const bytes = new Uint8Array([1, 2, 3]);
      const store = blob_set(gold_line("media_store"), bytes);
      const sleep = bench.line_run("media.store", store);
      const copy = blob_set(gold_line("media_store_copy"), bytes);
      this.assertEqual(bench.tasks.submitted, [[copy, "media"]]);
      this.assertTrue(bench.tasks.submitted[0][0] !== store);
      const id = constants.submit_ids[0];
      const expected = gold_sleep("sleep_media");
      expected.state = { request: store };
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const answer = reply_set(gold_line("media_store_answer"), id);
      const wake = wake_make("wake_media", expected, [answer]);
      const reply = bench.line_run("ui.media_reply", wake);
      this.assertEqual(reply, gold_line("media_store_reply"));
    }

    // A download's answer goes back with the bytes as its blob.
    test_media_fetched(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      const fetch_line = gold_line("media_fetch");
      const sleep = bench.line_run("media.fetch", fetch_line);
      const copy = gold_line("media_fetch_copy");
      this.assertEqual(bench.tasks.submitted, [[copy, "media"]]);
      const id = constants.submit_ids[0];
      const expected = gold_sleep("sleep_media");
      expected.state = { request: fetch_line };
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const bytes = new Uint8Array([8, 9]);
      const answer = blob_set(gold_line("media_fetch_answer"), bytes);
      const wake = wake_make("wake_media", expected, [reply_set(answer, id)]);
      const reply = bench.line_run("ui.media_reply", wake);
      this.assertEqual(reply, blob_set(gold_line("media_fetch_reply"), bytes));
    }

    // A permit shows its request, asks the DOM port, answers its choice.
    test_permit_answered(): void {
      const elements = this.elements_get();
      const bench = new HandlerBench(elements, true);
      const ask = gold_line("permit_ask");
      const sleep = bench.line_run("permit.ask", ask);
      this.assertEqual(
        elements.permit.textContent,
        gold_text("page_permit_text"),
      );
      const choose = gold_line("dom_choice_permit");
      this.assertEqual(bench.tasks.submitted, [[choose, "dom"]]);
      const id = constants.submit_ids[0];
      const expected = gold_sleep("sleep_permit");
      expected.state = { request: ask, text: elements.permit.firstChild };
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const answer = reply_set(gold_line("dom_choice_always"), id);
      const wake = wake_make("wake_permit", expected, [answer]);
      const reply = bench.line_run("ui.permit_reply", wake);
      this.assertEqual(reply, gold_line("permit_reply"));
      this.assertEqual(elements.permit.children.length, 0);
    }

    // The player's text starts a turn, whose end shows the subtitle.
    test_turn_said(): void {
      const elements = this.elements_get();
      const bench = new HandlerBench(elements, true);
      const sleep = bench.line_run("ui.input", gold_line("ui_input_said"));
      this.assertEqual(bench.tasks.submitted, [[gold_line("ai_say"), "ai"]]);
      this.assertTrue(elements.input.disabled);
      const id = constants.submit_ids[0];
      const expected = gold_sleep("sleep_turn");
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const end = reply_set(gold_line("ai_say_end"), id);
      const wake = wake_make("wake_turn", expected, [end]);
      this.assertEqual(bench.line_run("ui.turn_end", wake), undefined);
      this.assertEqual(elements.subtitle.textContent, end.subtitle);
      this.assertFalse(elements.input.disabled);
    }

    // The player's click starts a turn with its point.
    test_turn_clicked(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      bench.line_run("ui.input", gold_line("ui_input_clicked"));
      const click = gold_line("ai_click");
      this.assertEqual(bench.tasks.submitted, [[click, "ai"]]);
    }

    // Control 0 toggles the console and asks for tty 0, 2 toggles its overlay.
    test_keys_debug(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      for (const name of ["control_key_0", "control_key_0", "control_key_2"]) {
        bench.line_run("ui.control_key", gold_line(name));
      }
      this.assertEqual(bench.view.calls, ["toggle", "open", "toggle"]);
      this.assertEqual(bench.overlays.calls, ["toggle 2"]);
      const open = gold_line("console_open");
      this.assertEqual(bench.tasks.submitted, [[open, "ai"]]);
    }

    // After the end of tty 0, the next show by control 0 asks for it again.
    test_keys_reopen(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      bench.line_run("ui.control_key", gold_line("control_key_0"));
      bench.line_run("console.exit", gold_line("console_exit"));
      let sleep: unknown = undefined;
      for (let count = 0; count < 2; count += 1) {
        sleep = bench.line_run("ui.control_key", gold_line("control_key_0"));
      }
      this.assertEqual(bench.view.calls, [
        "toggle",
        "open",
        "exit",
        "toggle",
        "toggle",
        "open",
      ]);
      const open = gold_line("console_open");
      this.assertEqual(bench.tasks.submitted, [
        [open, "ai"],
        [open, "ai"],
      ]);
      const expected = gold_sleep("sleep_console");
      expected.wait_ids = [constants.submit_ids[1]];
      this.assertEqual(sleep, expected);
    }

    // Outside debug mode the keys toggle nothing.
    test_keys_gated(): void {
      const bench = new HandlerBench(this.elements_get(), false);
      for (const name of ["control_key_0", "control_key_1"]) {
        bench.line_run("ui.control_key", gold_line(name));
      }
      this.assertEqual(bench.view.calls, []);
      this.assertEqual(bench.overlays.calls, []);
      this.assertEqual(bench.tasks.submitted.length, 0);
    }

    // The console's output, end, opening and close, and overlay lines arrive.
    test_debug_lines(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      const bytes = new Uint8Array([0x30, 0x24]);
      const output = blob_set(gold_line("console_output"), bytes);
      bench.line_run("console.output", output);
      this.assertEqual(bench.view.fed, [new Uint8Array([0x30, 0x24])]);
      bench.line_run("console.exit", gold_line("console_exit"));
      bench.line_run("overlay.line", gold_line("overlay_line"));
      const wake = gold_line("wake_console_reply");
      this.assertEqual(bench.line_run("ui.console_reply", wake), undefined);
      const closed = gold_line("wake_console_closed");
      this.assertEqual(bench.line_run("ui.console_closed", closed), undefined);
      this.assertEqual(bench.view.calls, ["exit", "done", "closed"]);
      this.assertTrue(bench.view.wakes[0] === wake);
      this.assertTrue(bench.view.wakes[1] === closed);
      this.assertEqual(bench.overlays.calls, ["line 1 > x"]);
    }

    // `console.show` shows an open console and answers at once.
    test_show_open(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      bench.view.open = true;
      const show = gold_line("console_show_6");
      const reply = bench.line_run("console.show", show);
      this.assertEqual(bench.view.calls, ["show"]);
      this.assertEqual(reply, gold_line("console_show_reply"));
      this.assertEqual(bench.tasks.submitted.length, 0);
    }

    // An idle console is asked for, and the show is answered once it opens.
    test_show_idle(): void {
      const bench = new HandlerBench(this.elements_get(), true);
      const show = gold_line("console_show_6");
      const sleep = bench.line_run("console.show", show);
      this.assertEqual(bench.view.calls, ["show", "open"]);
      const open = gold_line("console_open");
      this.assertEqual(bench.tasks.submitted, [[open, "ai"]]);
      const id = constants.submit_ids[0];
      const expected = gold_sleep("sleep_shown");
      expected.state = { request: show };
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const state = (sleep as dispatch.Sleep).state as { request: unknown };
      this.assertTrue(state.request === show);
      const answer = reply_set(gold_line("console_open_answer"), id);
      const wake = wake_make("wake_console_shown", expected, [answer]);
      const reply = bench.line_run("ui.console_shown", wake);
      this.assertEqual(bench.view.calls, ["show", "open", "done"]);
      this.assertTrue(bench.view.wakes[0] === wake);
      this.assertEqual(reply, gold_line("console_show_reply"));
    }

    // A console opening or closing can neither answer nor be asked for.
    test_show_busy(): void {
      const opening = new HandlerBench(this.elements_get(), true);
      opening.line_run("console.show", gold_line("console_show_6"));
      const second = gold_line("console_show_7");
      const early = thrown_get(() => opening.line_run("console.show", second));
      this.assertEqual(early.message, gold_text("page_console_busy"));
      this.assertEqual(opening.tasks.submitted.length, 1);
      const closing = new HandlerBench(this.elements_get(), true);
      closing.view.asked = true;
      const show = gold_line("console_show_8");
      const late = thrown_get(() => closing.line_run("console.show", show));
      this.assertEqual(late.message, gold_text("page_console_busy"));
      this.assertEqual(closing.tasks.submitted.length, 0);
    }
  }

  // The page's column of the style: the debug views never cover the band.
  export class TestLayout extends unittest.TestCase {
    // The debug area and the subtitle band, made in `setUp`.
    #parts: HTMLElement[] = [];

    // Puts a debug area twice the viewport's height above a subtitle band.
    setUp(): void {
      const debug = document.createElement("div");
      debug.id = "debug";
      const tall = document.createElement("div");
      tall.style.height = `${2 * innerHeight}px`;
      debug.append(tall);
      const area = document.createElement("div");
      area.id = "subtitle";
      const text = document.createElement("p");
      text.textContent = constants.greeting;
      const permit = document.createElement("div");
      permit.id = "permit";
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = gold_text("page_choice_accept");
      permit.append(button);
      const form = document.createElement("form");
      const input = document.createElement("input");
      input.id = "input";
      form.append(input);
      area.append(text, permit, form);
      document.body.append(debug, area);
      this.#parts = [debug, area, text, button, input];
    }

    // Takes the debug area and the band out of the document.
    tearDown(): void {
      this.#parts[0].remove();
      this.#parts[1].remove();
    }

    // A tall debug view covers no part of the band: text, button, input.
    test_band_uncovered(): void {
      const [debug, area, ...shown] = this.#parts;
      const debug_box = debug.getBoundingClientRect();
      const area_box = area.getBoundingClientRect();
      this.assertTrue(
        debug_box.bottom <= area_box.top,
        `#debug ends at ${debug_box.bottom}, the band at ${area_box.top}`,
      );
      this.assertTrue(debug.scrollHeight > debug.clientHeight);
      for (const element of shown) {
        const box = element.getBoundingClientRect();
        const x = box.left + box.width / 2;
        const y = box.top + box.height / 2;
        this.assertTrue(
          document.elementFromPoint(x, y) === element,
          `the ${element.localName} at ${x}, ${y} is covered or unseen`,
        );
      }
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module object is frozen.
    test_module_frozen(): void {
      this.assertTrue(Object.isFrozen(page));
    }
  }
}

Object.freeze(test_page);
