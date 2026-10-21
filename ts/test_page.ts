// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the UI thread on the test page's document: the owner table, the
// reading of the worker's first line and faults, the DOM port's listeners
// and permit buttons, the handlers on a synchronous queue with port, image,
// console and overlay doubles, and the column the style lays the page out in.

namespace test_page {
  // The types the page registers, routed by the tests, and the values used.
  const constants = Object.freeze({
    routed_types: Object.freeze([
      "render",
      "media.store",
      "media.fetch",
      "ui.media_reply",
      "permit.ask",
      "ui.permit_reply",
      "ui.input",
      "ui.turn_end",
      "ui.control_key",
      "console.output",
      "console.exit",
      "overlay.line",
      "boot.hello",
    ]),
    hyperposition: "/metaverse/hyperposition/1",
    greeting: "How can I help you?",
    scene: "/castle_gatehouse/scene/arrival/1",
    subtitle:
      "Mind the moat. The gatehouse keeper has been expecting someone," +
      " though not necessarily you.",
    image: "/_files/gatehouse/arrival.png",
    image_sha256:
      "90b3a753ed6b58ea1033aadd244b2b253bd45e9adb25962a52621120768bb8f0",
    bootstrap: "/home/t/.cache/xsjs/bootstrap.py",
    bootstrap_sha256:
      "ab30a921f2faeb729bc35cdbc0a4f5a8bb70c95624eb5bfc2ff778db2cb22f88",
    root: "/home/t/.cache/xsjs",
    pid: 4242,
    tool: "browser.console_run",
  });

  // An object of fields by name.
  type Fields = { [key: string]: unknown };

  // The header options the tests set.
  type HeaderOptions = { id?: number; reply?: number; full?: boolean };

  // The handlers the code under test registered, by line type.
  const routed = new Map<string, dispatch.Handler>();

  // Whether dispatch's registry routes the page's types to `routed`.
  let router_installed = false;

  // Routes the page's types from dispatch's registry, once per thread.
  function router_install(): void {
    if (router_installed) {
      return;
    }
    router_installed = true;
    for (const type of constants.routed_types) {
      dispatch.handler_register(type, 0, (line: lines.Line) => {
        const fn = routed.get(type);
        if (fn === undefined) {
          throw new Error(`No handler is routed for ${type}.`);
        }
        return fn(line);
      });
    }
  }

  // A register that keeps each handler in `routed`.
  function register_route(
    type: string,
    _version: number,
    fn: dispatch.Handler,
  ): void {
    routed.set(type, fn);
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

  // A port double: it keeps what the queue posts and hands it lines.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    private receiver: ((line: lines.Line) => void) | undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver, which is the queue.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the queue as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
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
    private readonly tasks: queue.TaskQueue;
    // Whether the double is shown, which each toggle changes.
    private shown = false;
    // Whether tty 0 was asked for and has not ended since.
    private asked = false;

    // Takes the queue the opening is submitted on.
    constructor(tasks: queue.TaskQueue) {
      this.tasks = tasks;
    }

    // Records a toggle and shows or hides the double.
    view_toggle(): void {
      this.calls.push("toggle");
      this.shown = !this.shown;
    }

    // Whether the double is shown and tty 0 is not asked for.
    open_wanted(): boolean {
      return this.shown && !this.asked;
    }

    // Submits `console.open` to the AI worker and returns the sleep on it.
    open_request(): dispatch.Sleep {
      this.calls.push("open");
      this.asked = true;
      const line = jslb.line_make(jslb.header_make("console.open"), [], {});
      const id = this.tasks.task_submit(line, "ai");
      return dispatch.task_sleep(null, [id], "ui.console_reply");
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
  interface Elements {
    container: HTMLElement;
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    form: HTMLFormElement;
    input: HTMLInputElement;
    permit: HTMLElement;
  }

  // Makes the elements in a container and puts it in the document's body.
  function elements_make(document_of: Document): Elements {
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

  // A synchronous UI queue, its port doubles and the doubles of its parts.
  interface Bench {
    tasks: queue.TaskQueue;
    ai: PortDouble;
    media: PortDouble;
    dom: PortDouble;
    images: ImageDouble;
    view: ViewDouble;
    overlays: OverlayDouble;
    logs: string[];
  }

  // Makes a bench whose handlers work on the elements, in debug mode or not.
  function bench_make(elements: Elements, debug: boolean): Bench {
    router_install();
    routed.clear();
    const tasks = new queue.TaskQueue("ui", page.owners_make(false), true);
    const bench: Bench = {
      tasks,
      ai: new PortDouble(),
      media: new PortDouble(),
      dom: new PortDouble(),
      images: new ImageDouble(),
      view: new ViewDouble(tasks),
      overlays: new OverlayDouble(),
      logs: [],
    };
    tasks.port_add("ai", bench.ai);
    tasks.port_add("media", bench.media);
    tasks.port_add("dom", bench.dom);
    page.handlers_register(
      {
        tasks,
        canvas: elements.canvas,
        subtitle: elements.subtitle,
        input: elements.input,
        permit: elements.permit,
        images: bench.images,
        view: bench.view,
        overlays: bench.overlays,
        debug,
        full: false,
        log: (text: string) => {
          bench.logs.push(text);
        },
      },
      register_route,
    );
    return bench;
  }

  // The type of a line.
  function type_of(line: lines.Line): unknown {
    return jslb.field_get(line[0], "type");
  }

  // A line in short names from its type, payload, header options and blobs.
  function line_short(
    type: string,
    payload: Fields = {},
    options: HeaderOptions = {},
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, options), blobs, payload);
  }

  // The reply to a request a double received, with its payload and blobs.
  function reply_to(
    request: lines.Line,
    payload: Fields,
    blobs: lines.BlobHeader[] = [],
  ): lines.Line {
    const header = jslb.header_make(type_of(request) as string, {
      reply: jslb.field_get(request[0], "id") as number,
      full: Object.hasOwn(request[0], "type"),
    });
    return jslb.line_make(header, blobs, payload);
  }

  // A decoded image of the size given, made at once.
  function bitmap_make(width: number, height: number): ImageBitmap {
    return new OffscreenCanvas(width, height).transferToImageBitmap();
  }

  // The settings of `settings.json`, every key with its value.
  function settings_make(): settings.Settings {
    return {
      debug: true,
      queue_synchronous: false,
      verbose_level: 1,
      verbose_ring: 1000,
      line_max: 1048576,
      blob_max: 2147483391,
      overflow_bytes: 131072,
      chunk_bytes: 1048576,
      srv_buf_size: 1048576,
      media_db_bytes: 268435456,
      files_browser_bytes: 1073741824,
      db_soft_bytes: 1073741824,
      turn_compact_turns: 64,
      long_task_ms: 5,
      provider: {
        scripted: true,
        timeout_seconds: 120,
      },
    };
  }

  // A test on elements put in the document in `setUp` and removed after.
  class ElementsCase extends unittest.TestCase {
    // The elements, made from the document in `setUp`.
    #elements: Elements | undefined = undefined;

    // Makes the elements in the test page's document.
    setUp(): void {
      this.#elements = elements_make(document);
    }

    // Takes the elements out of the document.
    tearDown(): void {
      this.elements_get().container.remove();
    }

    // The elements of this test.
    elements_get(): Elements {
      return this.#elements as Elements;
    }
  }

  // The owner table of the UI thread and the test page's.
  export class TestOwnerTable extends unittest.TestCase {
    // The console goes to the worker but for its output and its end.
    test_console_routes(): void {
      const owners = page.owners_make(false);
      this.assertEqual(owners["console."], "ai");
      this.assertEqual(owners["console.output"], "ui");
      this.assertEqual(owners["console.exit"], "ui");
      this.assertEqual(owners["media."], "ui");
      this.assertEqual(owners["render"], "ui");
      this.assertEqual(owners["ui."], "ui");
      this.assertEqual(owners["dom."], "dom");
      this.assertEqual(owners["verbose."], "ai");
      this.assertFalse(Object.hasOwn(owners, "tap."));
    }

    // The test page's table sends `tap.` lines to the worker.
    test_tap_route(): void {
      this.assertEqual(page.owners_make(true)["tap."], "ai");
    }
  }

  // The first line of the worker and the messages of its faults.
  export class TestWorkerLines extends unittest.TestCase {
    // The first line must be `settings.set`, whose settings are taken.
    test_settings_taken(): void {
      const value = settings_make();
      const set = line_short("settings.set", { settings: value });
      this.assertEqual(page.settings_take(set), value);
      const other = line_short("boot.hello", {});
      const error = thrown_get(() => page.settings_take(other));
      this.assertEqual(
        error.message,
        i18n("page.settings_missing", "boot.hello"),
      );
    }

    // A message of the worker must be a fault line.
    test_fault_read(): void {
      const fields = { thread: "ai", message: "Broken.", stack: "at x" };
      const fault = line_short("fault", fields);
      this.assertEqual(page.fault_read(fault), fields);
      const error = thrown_get(() => page.fault_read(line_short("render")));
      this.assertEqual(error.message, i18n("page.message_unknown", "render"));
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
      this.assertEqual(received.length, 1);
      this.assertEqual(type_of(received[0]), "ui.input");
      this.assertEqual(jslb.payload_of(received[0]), { text: "1" });
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
      this.assertEqual(received.length, 1);
      this.assertEqual(jslb.payload_of(received[0]), { x: 1, y: 0 });
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
      this.assertEqual(received.length, 1);
      this.assertEqual(type_of(received[0]), "ui.control_key");
      this.assertEqual(jslb.payload_of(received[0]), { digit: 3 });
    }

    // A `dom.choice` shows its buttons and answers with the one clicked.
    test_choice_answered(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const received: lines.Line[] = [];
      port.line_receive((line) => {
        received.push(line);
      });
      const choices = ["accept", "deny", "always"];
      const ask = line_short("dom.choice", { permit: 1, choices }, { id: 4 });
      port.line_post(ask, []);
      const buttons = Array.from(elements.permit.querySelectorAll("button"));
      this.assertEqual(
        buttons.map((button) => button.textContent),
        [
          i18n("page.choice_accept"),
          i18n("page.choice_deny"),
          i18n("page.choice_always"),
        ],
      );
      buttons[1].click();
      this.assertEqual(elements.permit.children.length, 0);
      this.assertEqual(received.length, 1);
      this.assertEqual(jslb.field_get(received[0][0], "reply"), 4);
      this.assertEqual(jslb.payload_of(received[0]), { choice: "deny" });
    }

    // Another type, a missing id and an unknown choice are refused.
    test_post_refused(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      const other = line_short("dom.other", {}, { id: 1 });
      let error = thrown_get(() => port.line_post(other, []));
      this.assertEqual(error.message, i18n("page.dom_type", "dom.other"));
      const unasked = line_short("dom.choice", { permit: 1, choices: [] });
      error = thrown_get(() => port.line_post(unasked, []));
      this.assertEqual(error.message, i18n("page.id_missing", "dom.choice"));
      const unknown = line_short(
        "dom.choice",
        { permit: 1, choices: ["maybe"] },
        { id: 2 },
      );
      error = thrown_get(() => port.line_post(unknown, []));
      this.assertEqual(error.message, i18n("page.choice_unknown", "maybe"));
      this.assertEqual(elements.permit.children.length, 0);
    }

    // A second receiver and a container without the elements are refused.
    test_port_refused(): void {
      const elements = this.elements_get();
      const port = new page.DomPort(elements.container);
      port.line_receive(() => {});
      const twice = thrown_get(() => port.line_receive(() => {}));
      this.assertEqual(twice.message, i18n("page.receiver_twice"));
      const empty = elements.container.ownerDocument.createElement("div");
      const missing = thrown_get(() => new page.DomPort(empty));
      this.assertEqual(missing.message, i18n("page.element_missing", "image"));
    }
  }

  // The handlers of the UI thread on a synchronous queue.
  export class TestPageHandlers extends ElementsCase {
    // A render paints its image, shows its subtitle and opens the input.
    test_render_image(): void {
      const elements = this.elements_get();
      elements.input.disabled = true;
      const bench = bench_make(elements, true);
      bench.images.images.set(constants.image, bitmap_make(3, 2));
      const render = line_short(
        "render",
        {
          scene: constants.scene,
          subtitle: constants.subtitle,
          image: constants.image,
        },
        { id: 2 },
      );
      bench.ai.line_send(render);
      const reply = bench.ai.posted[0];
      this.assertEqual(type_of(reply), "render");
      this.assertEqual(jslb.field_get(reply[0], "reply"), 2);
      this.assertEqual(jslb.payload_of(reply), {});
      const canvas = elements.canvas;
      this.assertEqual([canvas.width, canvas.height], [3, 2]);
      this.assertFalse(elements.canvas.hidden);
      this.assertEqual(elements.subtitle.textContent, constants.subtitle);
      this.assertFalse(elements.input.disabled);
    }

    // A render with no image shows black, which hides the image.
    test_render_black(): void {
      const elements = this.elements_get();
      const bench = bench_make(elements, true);
      const render = line_short(
        "render",
        { scene: constants.hyperposition, subtitle: constants.greeting },
        { id: 1 },
      );
      bench.ai.line_send(render);
      this.assertTrue(elements.canvas.hidden);
      this.assertEqual(elements.subtitle.textContent, constants.greeting);
    }

    // A render of an image the cache does not hold is a fault.
    test_image_missing(): void {
      const bench = bench_make(this.elements_get(), true);
      const render = line_short(
        "render",
        {
          scene: constants.scene,
          subtitle: constants.subtitle,
          image: constants.image,
        },
        { id: 1 },
      );
      const error = thrown_get(() => bench.ai.line_send(render));
      this.assertEqual(
        error.message,
        i18n("page.image_missing", constants.scene, constants.image),
      );
    }

    // An image to keep goes to the media port, whose answer goes back.
    test_media_stored(): void {
      const bench = bench_make(this.elements_get(), true);
      const blob = jslb.blob_make(new Uint8Array([1, 2, 3]));
      const store = line_short(
        "media.store",
        { k: constants.image },
        { id: 1 },
        [blob],
      );
      bench.ai.line_send(store);
      const copy = bench.media.posted[0];
      this.assertEqual(type_of(copy), "media.store");
      this.assertTrue(copy !== store);
      this.assertEqual(copy.k, constants.image);
      const kept = { k: constants.image, size: 3, sha256: "" };
      bench.media.line_send(reply_to(copy, kept));
      const reply = bench.ai.posted[0];
      this.assertEqual(jslb.field_get(reply[0], "reply"), 1);
      this.assertEqual(jslb.payload_of(reply), kept);
      this.assertEqual(jslb.headers_of(reply).length, 1);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // A download's answer goes back with the bytes as its blob.
    test_media_fetched(): void {
      const bench = bench_make(this.elements_get(), true);
      const fetch_line = line_short(
        "media.fetch",
        { url: "https://example.invalid/a.png", k: constants.image },
        { id: 5 },
      );
      bench.ai.line_send(fetch_line);
      const copy = bench.media.posted[0];
      this.assertEqual(type_of(copy), "media.fetch");
      const kept = {
        k: constants.image,
        size: 2,
        sha256: constants.image_sha256,
      };
      const blob = jslb.blob_make(new Uint8Array([8, 9]));
      bench.media.line_send(reply_to(copy, kept, [blob]));
      const reply = bench.ai.posted[0];
      this.assertEqual(jslb.field_get(reply[0], "reply"), 5);
      this.assertEqual(jslb.payload_of(reply), kept);
      const data = jslb.field_get(reply[1] as lines.BlobHeader, "data");
      this.assertEqual(data, new Uint8Array([8, 9]));
    }

    // A permit shows its request, asks the DOM port, answers its choice.
    test_permit_answered(): void {
      const elements = this.elements_get();
      const bench = bench_make(elements, true);
      const input = { text: "ls", timeout_seconds: 5 };
      const ask = line_short(
        "permit.ask",
        { permit: 1, tool: constants.tool, input },
        { id: 3 },
      );
      bench.ai.line_send(ask);
      this.assertEqual(
        elements.permit.textContent,
        i18n("page.permit_text", constants.tool, utility.json_text(input)),
      );
      const choose = bench.dom.posted[0];
      this.assertEqual(type_of(choose), "dom.choice");
      this.assertEqual(jslb.payload_of(choose), {
        permit: 1,
        choices: ["accept", "deny", "always"],
      });
      bench.dom.line_send(reply_to(choose, { choice: "always" }));
      const reply = bench.ai.posted[0];
      this.assertEqual(jslb.field_get(reply[0], "reply"), 3);
      this.assertEqual(jslb.payload_of(reply), {
        permit: 1,
        choice: "always",
      });
      this.assertEqual(elements.permit.children.length, 0);
    }

    // The player's text starts a turn, whose end shows the subtitle.
    test_turn_said(): void {
      const elements = this.elements_get();
      const bench = bench_make(elements, true);
      bench.dom.line_send(line_short("ui.input", { text: "1" }));
      const say = bench.ai.posted[0];
      this.assertEqual(type_of(say), "ai.say");
      this.assertEqual(jslb.payload_of(say), { text: "1" });
      this.assertTrue(elements.input.disabled);
      const end = { turn: 7, scene: constants.scene, subtitle: "Fog." };
      bench.ai.line_send(reply_to(say, end));
      this.assertEqual(elements.subtitle.textContent, "Fog.");
      this.assertFalse(elements.input.disabled);
      this.assertEqual(bench.tasks.depth(), 0);
    }

    // The player's click starts a turn with its point.
    test_turn_clicked(): void {
      const bench = bench_make(this.elements_get(), true);
      bench.dom.line_send(line_short("ui.input", { x: 3, y: 4 }));
      const click = bench.ai.posted[0];
      this.assertEqual(type_of(click), "ai.click");
      this.assertEqual(jslb.payload_of(click), { x: 3, y: 4 });
    }

    // Control 0 toggles the console and asks for tty 0, 2 toggles its overlay.
    test_keys_debug(): void {
      const bench = bench_make(this.elements_get(), true);
      for (const digit of [0, 0, 2]) {
        bench.dom.line_send(line_short("ui.control_key", { digit }));
      }
      this.assertEqual(bench.view.calls, ["toggle", "open", "toggle"]);
      this.assertEqual(bench.overlays.calls, ["toggle 2"]);
      this.assertEqual(bench.ai.posted.length, 1);
      this.assertEqual(type_of(bench.ai.posted[0]), "console.open");
    }

    // After the end of tty 0, the next show by control 0 asks for it again.
    test_keys_reopen(): void {
      const bench = bench_make(this.elements_get(), true);
      bench.dom.line_send(line_short("ui.control_key", { digit: 0 }));
      bench.ai.line_send(line_short("console.exit", { code: 0 }));
      for (let count = 0; count < 2; count += 1) {
        bench.dom.line_send(line_short("ui.control_key", { digit: 0 }));
      }
      this.assertEqual(bench.view.calls, [
        "toggle",
        "open",
        "exit",
        "toggle",
        "toggle",
        "open",
      ]);
      const opened = bench.ai.posted.filter(
        (line) => type_of(line) === "console.open",
      );
      this.assertEqual(opened.length, 2);
      this.assertEqual(jslb.field_get(opened[1][0], "id"), 2);
    }

    // Outside debug mode the keys toggle nothing.
    test_keys_gated(): void {
      const bench = bench_make(this.elements_get(), false);
      for (const digit of [0, 1]) {
        bench.dom.line_send(line_short("ui.control_key", { digit }));
      }
      this.assertEqual(bench.view.calls, []);
      this.assertEqual(bench.overlays.calls, []);
      this.assertEqual(bench.ai.posted.length, 0);
    }

    // The console's output, end, opening and close, and overlay lines arrive.
    test_debug_lines(): void {
      const bench = bench_make(this.elements_get(), true);
      const bytes = new Uint8Array([0x30, 0x24]);
      const output = line_short("console.output", {}, {}, [
        jslb.blob_make(bytes),
      ]);
      bench.ai.line_send(output);
      this.assertEqual(bench.view.fed, [new Uint8Array([0x30, 0x24])]);
      bench.ai.line_send(line_short("console.exit", { code: 0 }));
      bench.ai.line_send(line_short("overlay.line", { tty: 1, text: "> x" }));
      const woken = { state: null, replies: [] };
      const wake = line_short("ui.console_reply", woken);
      const done = routed.get("ui.console_reply") as dispatch.Handler;
      this.assertEqual(done(wake), undefined);
      const closed = line_short("ui.console_closed", woken);
      const close = routed.get("ui.console_closed") as dispatch.Handler;
      this.assertEqual(close(closed), undefined);
      this.assertEqual(bench.view.calls, ["exit", "done", "closed"]);
      this.assertTrue(bench.view.wakes[0] === wake);
      this.assertTrue(bench.view.wakes[1] === closed);
      this.assertEqual(bench.overlays.calls, ["line 1 > x"]);
    }

    // What the hello says of the server is written as a verbose line.
    test_hello_logged(): void {
      const bench = bench_make(this.elements_get(), true);
      const hello = {
        bootstrap: constants.bootstrap,
        sha256: constants.bootstrap_sha256,
        pid: constants.pid,
        root: constants.root,
      };
      bench.ai.line_send(line_short("boot.hello", hello));
      const text = i18n(
        "page.hello_shown",
        constants.bootstrap,
        constants.bootstrap_sha256,
        constants.pid,
        constants.root,
      );
      this.assertEqual(bench.logs, [text]);
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
      button.textContent = i18n("page.choice_accept");
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
}

Object.freeze(test_page);
