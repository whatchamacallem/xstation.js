// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the UI thread on the test page's document: the owner table, the
// reading of the worker's first line and faults, the DOM port's listeners
// and permit buttons, the handlers' checks that throw within the call that
// feeds them, the column the style lays the page out in, and the frozen
// module. Each check runs the page's handlers, registered at a version of
// its own, on a real queue in synchronous mode with the real console view,
// overlays and media port, the test's ends of linked local ports standing
// for the AI worker and the DOM port. The handlers' lines that are answered
// later are the page's line cases.

namespace test_page {
  // The text the band shows, the parts' sizes, the settings.
  const constants = Object.freeze({
    greeting: "How can I help you?",
    // The thread of the page's queue.
    thread: "ui" as const,
    // The lines each overlay keeps, its writer's choice.
    ring_lines: 3,
    // The media cache's budget and a download's seconds, their writer's.
    media_budget: 1000000,
    media_seconds: 10,
    // The pixel sizes of the console's frame and band, chosen by their writer.
    frame_width: 1000,
    frame_height: 400,
    band_height: 50,
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

  // The test's end of a lane: its linked local port and the lines that came.
  interface LaneEnd {
    port: queue.LocalPort;
    came: lines.Line[];
  }

  // Joins the queue to the thread by linked local ports, one end the test's.
  function lane_make(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
  ): LaneEnd {
    const near = new queue.LocalPort();
    const port = new queue.LocalPort(near);
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    tasks.port_add(thread, near);
    return { port, came };
  }

  // How many versions the page's handlers are registered at, each one new.
  let versions_made = 0;

  // Sets the version of a line's header in the header's own name form.
  function version_set(line: lines.Line, version: number): lines.Line {
    const header = line[0] as unknown as { [field: string]: unknown };
    header[Object.hasOwn(header, "type") ? "version" : "v"] = version;
    return line;
  }

  // The page's handlers at a version of their own, their queue and parts.
  interface PageRig {
    version: number;
    ai: LaneEnd;
    dom: LaneEnd;
    frame: HTMLElement;
    console: HTMLElement;
    overlays: HTMLElement;
    view: console_view.ConsoleView;
  }

  // Puts in the page a frame of a fixed size: the console above a band.
  function frame_make(): HTMLElement[] {
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
    const console_area = document.createElement("div");
    Object.assign(console_area.style, { minHeight: "0px", overflow: "auto" });
    const band = document.createElement("div");
    Object.assign(band.style, {
      flexShrink: "0",
      height: `${constants.band_height}px`,
    });
    frame.append(console_area, band);
    document.body.append(frame);
    return [frame, console_area];
  }

  // Registers the page's handlers on the elements at a new version.
  function rig_make(elements: FixtureElements, debug: boolean): PageRig {
    versions_made += 1;
    const version = versions_made;
    const tasks = new queue.TaskQueue(
      constants.thread,
      page.owners_make(),
      true,
    );
    const ai = lane_make(tasks, "ai");
    const dom = lane_make(tasks, "dom");
    const images = new media.MediaPort(
      constants.media_budget,
      constants.media_seconds,
    );
    tasks.port_add("media", images);
    const [frame, console_area] = frame_make();
    const overlays = document.createElement("div");
    elements.container.append(overlays);
    const view = new console_view.ConsoleView(console_area, tasks);
    page.handlers_register(
      {
        tasks,
        canvas: elements.canvas,
        subtitle: elements.subtitle,
        input: elements.input,
        permit: elements.permit,
        images,
        view,
        overlays: new overlay.Overlay(overlays, constants.ring_lines),
        debug,
      },
      (type, _version, fn) => dispatch.handler_register(type, version, fn),
    );
    return { version, ai, dom, frame, console: console_area, overlays, view };
  }

  // The checks of the handlers that throw or stay silent within the call.
  export class TestHandlerChecks extends ElementsCase {
    // The rigs of this test, whose frames `tearDown` takes out.
    #rigs: PageRig[] = [];

    // The page's handlers of a new rig, in debug mode or not.
    rig_new(debug: boolean): PageRig {
      const rig = rig_make(this.elements_get(), debug);
      this.#rigs.push(rig);
      return rig;
    }

    // Hidden first, a view fits nothing when the frame's removal is reported.
    override tearDown(): void {
      for (const rig of this.#rigs) {
        rig.view.view_hide();
        rig.frame.remove();
      }
      super.tearDown();
    }

    // A render of an image the media cache does not hold is a fault.
    test_image_missing(): void {
      const rig = this.rig_new(true);
      const render = version_set(gold_line("render_image"), rig.version);
      const error = thrown_get(() => rig.ai.port.line_post(render, []));
      this.assertEqual(error.message, gold_text("page_image_missing"));
      this.assertEqual(rig.ai.came.length, 0);
      this.assertFalse(this.elements_get().canvas.hidden);
    }

    // A console that is opening can neither answer nor be asked for again.
    test_show_busy(): void {
      const rig = this.rig_new(true);
      const show = version_set(gold_line("console_show_6"), rig.version);
      rig.ai.port.line_post(show, []);
      this.assertEqual(rig.ai.came, [gold_line("console_open_request")]);
      const second = version_set(gold_line("console_show_7"), rig.version);
      const error = thrown_get(() => rig.ai.port.line_post(second, []));
      this.assertEqual(error.message, gold_text("page_console_busy"));
      this.assertEqual(rig.ai.came.length, 1);
    }

    // Outside debug mode the keys toggle nothing and ask for nothing.
    test_keys_gated(): void {
      const rig = this.rig_new(false);
      for (const name of ["control_key_0", "control_key_1"]) {
        rig.dom.port.line_post(version_set(gold_line(name), rig.version), []);
      }
      this.assertEqual(rig.ai.came.length, 0);
      this.assertEqual(rig.dom.came.length, 0);
      const child = rig.console.firstElementChild as HTMLElement;
      this.assertTrue(child.hidden);
      this.assertEqual(child.childElementCount, 0);
      this.assertEqual(rig.overlays.childElementCount, 0);
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
