// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The UI thread: the page's elements, the AI worker made from the texts of
// the worker scripts and the channel to it, the task manager built on the
// settings the worker sends first, the DOM port of the player's text, clicks
// and keys and of the permit buttons, the media port, the console view, the
// overlays, and the handlers that paint renders, keep media, ask permits and
// carry the player's turns. The test page's UI thread runs its tests on the
// same queue.

namespace page {
  // The owners, ids, line types, settings and texts of the page.
  const constants = Object.freeze({
    thread: "ui" as const,
    ai_owner: "ai" as const,
    media_owner: "media" as const,
    dom_owner: "dom" as const,
    worker_name: "ai",
    worker_scripts: "script[data-worker]",
    strict_line: '"use strict";\n',
    script_join: "\n",
    script_media: "text/javascript",
    image_id: "image",
    subtitle_id: "subtitle",
    input_id: "input",
    permit_id: "permit",
    debug_id: "debug",
    settings_type: "settings.set",
    fault_type: "fault",
    put_type: "settings.put",
    say_type: "ai.say",
    click_type: "ai.click",
    input_type: "ui.input",
    key_type: "ui.control_key",
    turn_wake: "ui.turn_end",
    permit_wake: "ui.permit_reply",
    media_wake: "ui.media_reply",
    console_wake: "ui.console_reply",
    render_type: "render",
    store_type: "media.store",
    fetch_type: "media.fetch",
    permit_type: "permit.ask",
    choice_type: "dom.choice",
    output_type: "console.output",
    exit_type: "console.exit",
    overlay_type: "overlay.line",
    hello_type: "boot.hello",
    handler_version: 0,
    choices: Object.freeze(["accept", "deny", "always"]),
    // The state of a turn's sleep: the input, enabled again when it ends.
    turn_state: Object.freeze({ input: "enabled" }),
    key_digit: /^[0-9]$/,
    console_digit: 0,
    hello_level: 1,
    debug_setting: "debug",
    level_setting: "verbose_level",
    synchronous_setting: "queue_synchronous",
    media_setting: "media_db_bytes",
    timeout_setting: "provider.timeout_seconds",
    ring_setting: "verbose_ring",
  });

  // Registers the handler of one line type and version, as dispatch does.
  export type HandlerRegister = (
    type: string,
    version: number,
    fn: dispatch.Handler,
  ) => void;

  // The decoded images the page paints, by key, as the media port keeps them.
  export interface ImageSource {
    image_get(k: lines.KvRef): ImageBitmap | undefined;
  }

  // The console view as the handlers drive it.
  export interface ConsoleControl {
    view_toggle(): void;
    open_request(): dispatch.Sleep;
    open_done(wake: lines.Line): void;
    exit_done(): void;
    output_feed(data: Uint8Array): void;
  }

  // The overlays as the handlers drive them.
  export interface OverlayControl {
    line_add(tty: number, text: string): void;
    overlay_toggle(tty: number): void;
  }

  // What the UI handlers work with: the queue, the elements and the parts.
  export interface PageParts {
    tasks: queue.TaskQueue;
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    input: HTMLInputElement;
    permit: HTMLElement;
    images: ImageSource;
    view: ConsoleControl;
    overlays: OverlayControl;
    debug: boolean;
    full: boolean;
    log: (level: number, text: string) => void;
  }

  // The elements the page makes once.
  interface PageElements {
    canvas: HTMLCanvasElement;
    subtitle: HTMLElement;
    input: HTMLInputElement;
    permit: HTMLElement;
    debug: HTMLElement;
  }

  // What a relay's wake keeps: the request it owes the reply to.
  interface RelayState {
    request: lines.Line;
  }

  // What a permit's wake keeps: the request and the text that shows it.
  interface PermitState {
    request: lines.Line;
    text: HTMLElement;
  }

  // The owner table of the UI thread, with `tap.` on the test page.
  export function owners_make(test: boolean): queue.OwnerTable {
    const owners: queue.OwnerTable = {
      "ui.": "ui",
      "render": "ui",
      "media.": "ui",
      "permit.": "ui",
      "boot.": "ui",
      "overlay.": "ui",
      "console.": "ai",
      "console.output": "ui",
      "console.exit": "ui",
      "ai.": "ai",
      "settings.put": "ai",
      "verbose.": "ai",
      "kv.": "ai",
      "doc.": "ai",
      "db.": "ai",
      "turn.": "ai",
      "sql.": "ai",
      "dom.": "dom",
    };
    return test ? { ...owners, "tap.": "ai" } : owners;
  }

  // Whether the lines this thread builds use full names, which is debug mode.
  function names_full(): boolean {
    return settings.settings_get(constants.debug_setting) as boolean;
  }

  // Whether a line uses full header names.
  function full_of(line: lines.Line): boolean {
    return Object.hasOwn(line[0], "type");
  }

  // A line of a type in the name form given, with its payload.
  function line_build(
    type: string,
    full: boolean,
    payload: { [key: string]: unknown },
  ): lines.Line {
    return jslb.line_make(jslb.header_make(type, { full }), [], payload);
  }

  // The element of a container with the id given, which must be there.
  function element_find(container: HTMLElement, id: string): HTMLElement {
    const element = container.querySelector<HTMLElement>(`#${id}`);
    if (element === null) {
      throw new Error(i18n("page.element_missing", id));
    }
    return element;
  }

  // The text of a button for a choice of a permit request.
  function choice_label(choice: string): string {
    const labels: { [choice: string]: string } = {
      accept: i18n("page.choice_accept"),
      deny: i18n("page.choice_deny"),
      always: i18n("page.choice_always"),
    };
    if (!Object.hasOwn(labels, choice)) {
      throw new Error(i18n("page.choice_unknown", choice));
    }
    return labels[choice];
  }

  // The settings the first line of the worker carries, which is settings.set.
  export function settings_take(data: unknown): settings.Settings {
    const line = data as lines.Line;
    const type = jslb.field_get(line[0], "type");
    if (type !== constants.settings_type) {
      throw new Error(i18n("page.settings_missing", String(type)));
    }
    return (jslb.payload_of(line) as unknown as lines.SettingsSet).settings;
  }

  // The fault a message of the worker carries, which must be a fault line.
  export function fault_read(data: unknown): lines.Fault {
    const line = data as lines.Line;
    const type = jslb.field_get(line[0], "type");
    if (type !== constants.fault_type) {
      throw new Error(i18n("page.message_unknown", String(type)));
    }
    return jslb.payload_of(line) as unknown as lines.Fault;
  }

  // The DOM port: the player's text, clicks and keys, and the permit buttons.
  export class DomPort implements queue.Port {
    private readonly canvas: HTMLCanvasElement;
    private readonly input: HTMLInputElement;
    private readonly permit: HTMLElement;
    private receiver: ((line: lines.Line) => void) | undefined = undefined;

    // Finds the image, the input and the permit area, and listens to them.
    constructor(container: HTMLElement) {
      this.canvas = element_find(
        container,
        constants.image_id,
      ) as HTMLCanvasElement;
      this.input = element_find(
        container,
        constants.input_id,
      ) as HTMLInputElement;
      this.permit = element_find(container, constants.permit_id);
      container.addEventListener("submit", (event: SubmitEvent) =>
        this.text_take(event),
      );
      this.canvas.addEventListener("click", (event: MouseEvent) =>
        this.click_take(event),
      );
      container.addEventListener(
        "keydown",
        (event: KeyboardEvent) => this.key_take(event),
        true,
      );
    }

    // Shows a button for each choice of a `dom.choice`, answered when clicked.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const header = line[0];
      const type = jslb.field_get(header, "type");
      if (type !== constants.choice_type) {
        throw new Error(i18n("page.dom_type", String(type)));
      }
      const id = jslb.field_get(header, "id");
      if (typeof id !== "number") {
        throw new Error(i18n("page.id_missing", type));
      }
      const choices = jslb.payload_of(line).choices as string[];
      const labels = choices.map((choice) => choice_label(choice));
      const document_of = this.permit.ownerDocument;
      const block = document_of.createElement("div");
      for (let index = 0; index < choices.length; index += 1) {
        const choice = choices[index];
        const button = document_of.createElement("button");
        button.type = "button";
        button.textContent = labels[index];
        button.addEventListener("click", () => {
          block.remove();
          this.choice_answer(full_of(line), id, choice);
        });
        block.append(button);
      }
      this.permit.append(block);
    }

    // Sets the one receiver of the lines of the listeners and the answers.
    line_receive(fn: (line: lines.Line) => void): void {
      if (this.receiver !== undefined) {
        throw new Error(i18n("page.receiver_twice"));
      }
      this.receiver = fn;
    }

    // Takes the text the player submits and empties the input.
    private text_take(event: SubmitEvent): void {
      event.preventDefault();
      const text = this.input.value;
      this.input.value = "";
      this.receiver_call(line_build(constants.input_type, false, { text }));
    }

    // Takes a click on the image as a point of the image's own pixels.
    private click_take(event: MouseEvent): void {
      // While the input is closed, as during a turn, a click is not taken.
      if (this.input.disabled) {
        return;
      }
      const canvas = this.canvas;
      const box = canvas.getBoundingClientRect();
      const scale = Math.min(
        box.width / canvas.width,
        box.height / canvas.height,
      );
      const left = (box.width - canvas.width * scale) / 2;
      const top = (box.height - canvas.height * scale) / 2;
      const x = Math.floor((event.clientX - box.left - left) / scale);
      const y = Math.floor((event.clientY - box.top - top) / scale);
      this.receiver_call(line_build(constants.input_type, false, { x, y }));
    }

    // Takes control with a digit, which the page keeps from the browser.
    private key_take(event: KeyboardEvent): void {
      if (!event.ctrlKey || !constants.key_digit.test(event.key)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const digit = Number(event.key);
      this.receiver_call(line_build(constants.key_type, false, { digit }));
    }

    // Answers a `dom.choice` with the choice clicked.
    private choice_answer(full: boolean, id: number, choice: string): void {
      const header = jslb.header_make(constants.choice_type, {
        reply: id,
        full,
      });
      this.receiver_call(jslb.line_make(header, [], { choice }));
    }

    // Gives a line to the receiver, which the queue set when it took the port.
    private receiver_call(line: lines.Line): void {
      (this.receiver as (line: lines.Line) => void)(line);
    }
  }

  // The handlers of the UI thread and the state they share.
  class PageHandlers {
    readonly #parts: PageParts;
    // Whether the first render came, which ends the start.
    #ready = false;
    // Whether the console was asked for, which happens once a page load.
    #console_asked = false;

    // Takes what the handlers work with.
    constructor(parts: PageParts) {
      this.#parts = parts;
    }

    // Paints the image the render names, or black, and shows its subtitle.
    render_take(line: lines.Line): lines.Line {
      const { canvas, images, subtitle, input } = this.#parts;
      const render = jslb.payload_of(line) as unknown as lines.Render;
      const image = render.image;
      if (image === undefined) {
        canvas.hidden = true;
      } else {
        const bitmap = images.image_get(image);
        if (bitmap === undefined) {
          throw new Error(i18n("page.image_missing", render.scene, image));
        }
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const context = canvas.getContext("2d") as CanvasRenderingContext2D;
        context.drawImage(bitmap, 0, 0);
        canvas.hidden = false;
      }
      subtitle.textContent = render.subtitle;
      // The first render ends the start, after which the player may type.
      if (!this.#ready) {
        this.#ready = true;
        input.disabled = false;
      }
      return dispatch.reply_make(line, {});
    }

    // Passes a media request to the media port and sleeps on its answer.
    media_take(line: lines.Line): dispatch.Sleep {
      const type = jslb.field_get(line[0], "type") as string;
      const header = jslb.header_make(type, { full: full_of(line) });
      const blobs = jslb.headers_of(line).slice(1) as lines.BlobHeader[];
      const copy = jslb.line_make(header, blobs, jslb.payload_of(line));
      const id = this.#parts.tasks.task_submit(copy, constants.media_owner);
      const state: RelayState = { request: line };
      return dispatch.task_sleep(state, [id], constants.media_wake);
    }

    // Answers the media request with the media port's answer and its blobs.
    media_done(wake: lines.Line): lines.Line {
      const { request } = wake.state as RelayState;
      const [reply] = wake.replies as lines.Line[];
      const blobs = jslb.headers_of(reply).slice(1) as lines.BlobHeader[];
      return dispatch.reply_make(request, jslb.payload_of(reply), blobs);
    }

    // Shows the permit request, asks the DOM port for a choice, and sleeps.
    permit_take(line: lines.Line): dispatch.Sleep {
      const { tasks, permit, full } = this.#parts;
      const ask = jslb.payload_of(line) as unknown as lines.PermitAsk;
      const text = permit.ownerDocument.createElement("p");
      const input = utility.json_text(ask.input);
      text.textContent = i18n("page.permit_text", ask.tool, input);
      permit.append(text);
      const choose = line_build(constants.choice_type, full, {
        permit: ask.permit,
        choices: [...constants.choices],
      });
      const id = tasks.task_submit(choose, constants.dom_owner);
      const state: PermitState = { request: line, text };
      return dispatch.task_sleep(state, [id], constants.permit_wake);
    }

    // Removes the request's text and answers it with the choice made.
    permit_done(wake: lines.Line): lines.Line {
      const { request, text } = wake.state as PermitState;
      const [reply] = wake.replies as lines.Line[];
      text.remove();
      return dispatch.reply_make(request, {
        permit: jslb.payload_of(request).permit,
        choice: jslb.payload_of(reply).choice,
      });
    }

    // Starts a turn with the player's text or click and closes the input.
    input_take(line: lines.Line): dispatch.Sleep {
      const { tasks, input, full } = this.#parts;
      const said = jslb.payload_of(line) as unknown as lines.UiInput;
      const turn =
        said.text === undefined
          ? line_build(constants.click_type, full, { x: said.x, y: said.y })
          : line_build(constants.say_type, full, { text: said.text });
      input.disabled = true;
      const id = tasks.task_submit(turn, constants.ai_owner);
      const state = constants.turn_state;
      return dispatch.task_sleep(state, [id], constants.turn_wake);
    }

    // Shows the subtitle the turn ended with and opens the input again.
    turn_done(wake: lines.Line): undefined {
      const [reply] = wake.replies as lines.Line[];
      const end = jslb.payload_of(reply) as unknown as lines.TurnEnd;
      this.#parts.subtitle.textContent = end.subtitle;
      this.#parts.input.disabled = false;
      return undefined;
    }

    // In debug mode toggles the console or an overlay, asking for tty 0 once.
    key_take(line: lines.Line): dispatch.Sleep | undefined {
      const { debug, view, overlays } = this.#parts;
      const digit = jslb.payload_of(line).digit as number;
      // Outside debug mode the page gates the console and the overlays.
      if (!debug) {
        return undefined;
      }
      if (digit !== constants.console_digit) {
        overlays.overlay_toggle(digit);
        return undefined;
      }
      view.view_toggle();
      if (this.#console_asked) {
        return undefined;
      }
      this.#console_asked = true;
      return view.open_request();
    }

    // Gives the view the answer to its opening.
    console_done(wake: lines.Line): undefined {
      this.#parts.view.open_done(wake);
      return undefined;
    }

    // Feeds the view one message of tty 0.
    output_take(line: lines.Line): undefined {
      const blob = line[1] as lines.BlobHeader;
      this.#parts.view.output_feed(jslb.field_get(blob, "data") as Uint8Array);
      return undefined;
    }

    // Tells the view that tty 0 ended.
    exit_take(): undefined {
      this.#parts.view.exit_done();
      return undefined;
    }

    // Adds a rendered line to the overlay of its tty.
    overlay_take(line: lines.Line): undefined {
      const shown = jslb.payload_of(line) as unknown as lines.OverlayLine;
      this.#parts.overlays.line_add(shown.tty, shown.text);
      return undefined;
    }

    // Writes what the hello says of the server as a line of progress.
    hello_take(line: lines.Line): undefined {
      const hello = jslb.payload_of(line) as unknown as lines.BootHello;
      const { bootstrap, sha256, pid, root } = hello;
      const text = i18n("page.hello_shown", bootstrap, sha256, pid, root);
      this.#parts.log(constants.hello_level, text);
      return undefined;
    }
  }

  // Registers the handlers of the UI thread with the register given.
  export function handlers_register(
    parts: PageParts,
    register: HandlerRegister,
  ): void {
    const handlers = new PageHandlers(parts);
    const version = constants.handler_version;
    register(constants.render_type, version, (line) =>
      handlers.render_take(line),
    );
    register(constants.store_type, version, (line) =>
      handlers.media_take(line),
    );
    register(constants.fetch_type, version, (line) =>
      handlers.media_take(line),
    );
    register(constants.media_wake, version, (line) =>
      handlers.media_done(line),
    );
    register(constants.permit_type, version, (line) =>
      handlers.permit_take(line),
    );
    register(constants.permit_wake, version, (line) =>
      handlers.permit_done(line),
    );
    register(constants.input_type, version, (line) =>
      handlers.input_take(line),
    );
    register(constants.turn_wake, version, (line) => handlers.turn_done(line));
    register(constants.key_type, version, (line) => handlers.key_take(line));
    register(constants.console_wake, version, (line) =>
      handlers.console_done(line),
    );
    register(constants.output_type, version, (line) =>
      handlers.output_take(line),
    );
    register(constants.exit_type, version, () => handlers.exit_take());
    register(constants.overlay_type, version, (line) =>
      handlers.overlay_take(line),
    );
    register(constants.hello_type, version, (line) =>
      handlers.hello_take(line),
    );
  }

  // Makes the page's elements in the body, the input closed until the start.
  function page_build(body: HTMLElement): PageElements {
    const document_of = body.ownerDocument;
    const canvas = document_of.createElement("canvas");
    canvas.id = constants.image_id;
    canvas.hidden = true;
    const area = document_of.createElement("div");
    area.id = constants.subtitle_id;
    const subtitle = document_of.createElement("p");
    const permit = document_of.createElement("div");
    permit.id = constants.permit_id;
    const form = document_of.createElement("form");
    const input = document_of.createElement("input");
    input.id = constants.input_id;
    input.disabled = true;
    form.append(input);
    area.append(subtitle, permit, form);
    const debug = document_of.createElement("div");
    debug.id = constants.debug_id;
    body.append(canvas, area, debug);
    return { canvas, subtitle, input, permit, debug };
  }

  // Makes the AI worker from the worker scripts' texts and shows its faults.
  function worker_make(): Worker {
    const scripts = document.querySelectorAll<HTMLScriptElement>(
      constants.worker_scripts,
    );
    const texts = Array.from(scripts, (script) => script.text);
    const source = constants.strict_line + texts.join(constants.script_join);
    const blob = new Blob([source], { type: constants.script_media });
    const worker = new Worker(URL.createObjectURL(blob), {
      name: constants.worker_name,
    });
    worker.onmessage = (event: MessageEvent<unknown>) => {
      const fault = fault_read(event.data);
      error_overlay.overlay_show(fault.message, fault.stack);
    };
    worker.onerror = (event: ErrorEvent) => {
      const { filename, lineno, colno } = event;
      const where = i18n("page.worker_where", filename, lineno, colno);
      error_overlay.overlay_show(event.message, where);
    };
    worker.onmessageerror = () => {
      const error = new Error(i18n("page.message_error"));
      error_overlay.overlay_show(error.message, error.stack as string);
    };
    return worker;
  }

  // Gives the worker its end of the channel and the page's address.
  function worker_post(worker: Worker, port: MessagePort): void {
    worker.postMessage({ port, base_url: location.href }, [port]);
  }

  // Sets the settings, then the queue, its sink, its AI port and its sender.
  function thread_open(
    port: MessagePort,
    value: settings.Settings,
    test: boolean,
  ): queue.TaskQueue {
    settings.settings_set(value);
    const level = settings.settings_get(constants.level_setting) as number;
    verbose.level_set(level);
    const synchronous = settings.settings_get(
      constants.synchronous_setting,
    ) as boolean;
    const tasks = new queue.TaskQueue(
      constants.thread,
      owners_make(test),
      synchronous,
    );
    tasks.sink_attach(verbose.sink_set, settings.settings_get);
    tasks.port_add(constants.ai_owner, new queue.ThreadPort(port));
    settings.sender_register((put: lines.SettingsPut) => {
      const line = line_build(constants.put_type, names_full(), {
        settings: put.settings,
      });
      tasks.line_notify(line, constants.ai_owner);
    });
    return tasks;
  }

  // Builds the engine's UI thread on the settings the worker sent.
  function engine_open(
    body: HTMLElement,
    elements: PageElements,
    port: MessagePort,
    value: settings.Settings,
  ): void {
    const tasks = thread_open(port, value, false);
    const images = new media.MediaPort(
      settings.settings_get(constants.media_setting) as number,
      settings.settings_get(constants.timeout_setting) as number,
    );
    tasks.port_add(constants.dom_owner, new DomPort(body));
    tasks.port_add(constants.media_owner, images);
    const ring = settings.settings_get(constants.ring_setting) as number;
    handlers_register(
      {
        tasks,
        canvas: elements.canvas,
        subtitle: elements.subtitle,
        input: elements.input,
        permit: elements.permit,
        images,
        view: new console_view.ConsoleView(elements.debug, tasks),
        overlays: new overlay.Overlay(elements.debug, ring),
        debug: settings.settings_get(constants.debug_setting) === true,
        full: names_full(),
        log: (level: number, text: string) => verbose.log(level, text),
      },
      dispatch.handler_register,
    );
  }

  // The UI thread of the engine page: the elements, the worker, the channel.
  export function page_main(): void {
    error_overlay.overlay_install();
    const body = document.body;
    const elements = page_build(body);
    const worker = worker_make();
    error_overlay.stop_register(() => worker.terminate());
    const channel = new MessageChannel();
    channel.port1.onmessage = (event: MessageEvent<unknown>) => {
      engine_open(body, elements, channel.port1, settings_take(event.data));
    };
    worker_post(worker, channel.port2);
  }

  // The UI thread of the test page: the worker, then the tests on the queue.
  export function test_page(run: (tasks: queue.TaskQueue) => void): void {
    error_overlay.overlay_install();
    const worker = worker_make();
    const channel = new MessageChannel();
    channel.port1.onmessage = (event: MessageEvent<unknown>) => {
      run(thread_open(channel.port1, settings_take(event.data), true));
    };
    worker_post(worker, channel.port2);
  }
}

Object.freeze(page);
