// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The UI thread. API/ts/page.d.ts holds its rules. Every line it builds takes
// the form `settings.names_full()` picks, the DOM port's `ui.input` and
// `ui.control_key` and the page's own `fault` line included.

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
    line_break: "\n",
    image_id: "image",
    input_id: "input",
    permit_id: "permit",
    settings_type: "settings.set",
    fault_type: "fault",
    put_type: "settings.put",
    say_type: "ai.say",
    click_type: "ai.click",
    input_type: "ui.input",
    key_type: "ui.control_key",
    tests_type: "ui.tests",
    turn_wake: "ui.turn_end",
    permit_wake: "ui.permit_reply",
    media_wake: "ui.media_reply",
    console_wake: "ui.console_reply",
    closed_wake: "ui.console_closed",
    shown_wake: "ui.console_shown",
    render_type: "render",
    store_type: "media.store",
    fetch_type: "media.fetch",
    permit_type: "permit.ask",
    choice_type: "dom.choice",
    output_type: "console.output",
    exit_type: "console.exit",
    busy_type: "console.busy",
    idle_type: "console.idle",
    show_type: "console.show",
    tail_type: "audit.tail",
    tail_wake: "ui.audit_tail",
    dump_type: "db.dump",
    // The text that dumps both sides' databases before its turn, debug mode.
    dump_text: "0",
    audit_digit: 1,
    ring_setting: "verbose_ring",
    handler_version: 0,
    choices: Object.freeze(["accept", "deny", "always"]),
    // The state of a turn's sleep: the input, enabled again when it ends.
    turn_state: Object.freeze({ input: "enabled" }),
    key_digit: /^[0-9]$/,
    console_digit: 0,
    synchronous_setting: "queue_synchronous",
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
  export interface OverlayControl {
    text_show(tty: number, text: string): void;
    overlay_toggle(tty: number): boolean;
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

  // The owner table of the UI thread.
  export function owners_make(): queue.OwnerTable {
    return {
      "ui.": "ui",
      render: "ui",
      "media.": "ui",
      "permit.": "ui",
      "console.": "ai",
      "console.output": "ui",
      "console.exit": "ui",
      "console.busy": "ui",
      "console.idle": "ui",
      "console.show": "ui",
      "ai.": "ai",
      "settings.put": "ai",
      "audit.": "ai",
      "tap.": "ai",
      "kv.": "ai",
      "doc.": "ai",
      "db.": "ai",
      "turn.": "ai",
      "sql.": "ai",
      "dom.": "dom",
    };
  }

  // Whether a line uses full header names.
  function full_of(line: lines.Line): boolean {
    return Object.hasOwn(line[0], "type");
  }

  // A line of a type in the name form of this thread, with its payload.
  function line_build(
    type: string,
    payload: { [key: string]: unknown },
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    return jslb.line_make(header, [], payload);
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

  // The first line of the worker, which is settings.set, taken whole.
  export function settings_take(data: unknown): lines.SettingsSet {
    const line = data as lines.Line;
    const type = jslb.field_get(line[0], "type");
    if (type !== constants.settings_type) {
      throw new Error(i18n("page.settings_missing", String(type)));
    }
    return jslb.payload_of(line) as unknown as lines.SettingsSet;
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

    // Takes the text the player submits, empties the input and closes it.
    private text_take(event: SubmitEvent): void {
      event.preventDefault();
      const text = this.input.value;
      this.input.value = "";
      // Closed here, as a second Enter may come before the queue's next step.
      this.input.disabled = true;
      this.receiver_call(line_build(constants.input_type, { text }));
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
      this.input.disabled = true;
      this.receiver_call(line_build(constants.input_type, { x, y }));
    }

    // Takes control with a digit, which the page keeps from the browser.
    private key_take(event: KeyboardEvent): void {
      if (!event.ctrlKey || !constants.key_digit.test(event.key)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      const digit = Number(event.key);
      this.receiver_call(line_build(constants.key_type, { digit }));
    }

    // Answers a `dom.choice` with the choice clicked, in the request's form.
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
    // Whether the first render came, which opens the input.
    #ready = false;

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
      // The first render opens the input, after which the player may type.
      if (!this.#ready) {
        this.#ready = true;
        input.disabled = false;
        input.focus();
      }
      return dispatch.reply_make(line, {});
    }

    // Passes a media request to the media port and sleeps on its answer.
    media_take(line: lines.Line): dispatch.Sleep {
      const type = jslb.field_get(line[0], "type") as string;
      const header = jslb.header_make(type, { full: settings.names_full() });
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
      const { tasks, permit } = this.#parts;
      const ask = jslb.payload_of(line) as unknown as lines.PermitAsk;
      const text = permit.ownerDocument.createElement("p");
      const input = utility.json_text(ask.input);
      text.textContent = i18n("page.permit_text", ask.tool, input);
      permit.append(text);
      const choose = line_build(constants.choice_type, {
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

    // Starts a turn with the player's text or click, the text 0 dumping first.
    input_take(line: lines.Line): dispatch.Sleep {
      const { tasks, input, debug } = this.#parts;
      const said = jslb.payload_of(line) as unknown as lines.UiInput;
      if (debug && said.text === constants.dump_text) {
        tasks.line_notify(
          line_build(constants.dump_type, {}),
          constants.ai_owner,
        );
      }
      const turn =
        said.text === undefined
          ? line_build(constants.click_type, { x: said.x, y: said.y })
          : line_build(constants.say_type, { text: said.text });
      input.disabled = true;
      const id = tasks.task_submit(turn, constants.ai_owner);
      const state = constants.turn_state;
      return dispatch.task_sleep(state, [id], constants.turn_wake);
    }

    // Shows the turn's last subtitle, opens the input and gives it the focus.
    turn_done(wake: lines.Line): undefined {
      const { subtitle, input } = this.#parts;
      const [reply] = wake.replies as lines.Line[];
      const end = jslb.payload_of(reply) as unknown as lines.TurnEnd;
      subtitle.textContent = end.subtitle;
      input.disabled = false;
      input.focus();
      return undefined;
    }

    // In debug mode toggles an overlay, ctrl 1's asked of the server, or tty 0.
    key_take(line: lines.Line): dispatch.Sleep | undefined {
      const { debug, view, overlays, input, tasks } = this.#parts;
      const digit = jslb.payload_of(line).digit as number;
      // Outside debug mode the page gates the console and the overlays.
      if (!debug) {
        return undefined;
      }
      if (digit !== constants.console_digit) {
        const shown = overlays.overlay_toggle(digit);
        if (!shown || digit !== constants.audit_digit) {
          return undefined;
        }
        const count = settings.settings_get(constants.ring_setting);
        const tail = line_build(constants.tail_type, { count });
        const id = tasks.task_submit(tail, constants.ai_owner);
        return dispatch.task_sleep(null, [id], constants.tail_wake);
      }
      // A hidden console leaves the focus nowhere, so an open box takes it.
      if (!view.view_toggle() && !input.disabled) {
        input.focus();
      }
      // Shown and idle, at first or after its end, the view asks for tty 0.
      return view.open_wanted() ? view.open_request() : undefined;
    }

    // Shows the console, answered once it opens when idle, else at once.
    show_take(line: lines.Line): lines.Line | dispatch.Sleep {
      const { view } = this.#parts;
      view.view_show();
      // While ctrl 0 opens it, tty 0's writer holds the AI's lines for dash.
      if (!view.open_wanted()) {
        return dispatch.reply_make(line, {});
      }
      const sleep = view.open_request();
      const state: RelayState = { request: line };
      return dispatch.task_sleep(state, sleep.wait_ids, constants.shown_wake);
    }

    // Gives the view the answer to its opening, then answers the show.
    shown_take(wake: lines.Line): lines.Line {
      this.#parts.view.open_done(wake);
      const { request } = wake.state as RelayState;
      return dispatch.reply_make(request, {});
    }

    // Gives the view the answer to its opening.
    console_done(wake: lines.Line): undefined {
      this.#parts.view.open_done(wake);
      return undefined;
    }

    // Gives the view the answer to its close, after which its end arrives.
    closed_take(wake: lines.Line): undefined {
      this.#parts.view.close_done(wake);
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

    // Holds the view's keys while the AI's command runs.
    busy_take(): undefined {
      this.#parts.view.input_hold();
      return undefined;
    }

    // Frees the view's keys once the AI's command has ended.
    idle_take(): undefined {
      this.#parts.view.input_free();
      return undefined;
    }

    // Shows the end of the audit the server sent, while its overlay is shown.
    tail_done(wake: lines.Line): undefined {
      const [reply] = wake.replies as lines.Line[];
      const tail = jslb.payload_of(reply) as unknown as lines.AuditTailReply;
      this.#parts.overlays.text_show(constants.audit_digit, tail.text);
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
    register(constants.show_type, version, (line) => handlers.show_take(line));
    register(constants.shown_wake, version, (line) =>
      handlers.shown_take(line),
    );
    register(constants.console_wake, version, (line) =>
      handlers.console_done(line),
    );
    register(constants.closed_wake, version, (line) =>
      handlers.closed_take(line),
    );
    register(constants.output_type, version, (line) =>
      handlers.output_take(line),
    );
    register(constants.exit_type, version, () => handlers.exit_take());
    register(constants.busy_type, version, () => handlers.busy_take());
    register(constants.idle_type, version, () => handlers.idle_take());
    register(constants.tail_wake, version, (line) => handlers.tail_done(line));
  }

  // The stack of a fault followed by each cause's message and stack in turn.
  function fault_text(fault: lines.Fault): string {
    const parts = [fault.stack];
    let cause = fault.cause;
    while (cause !== undefined) {
      parts.push(cause.message, cause.stack);
      cause = cause.cause;
    }
    return parts.join(constants.line_break);
  }

  // The `fault` line of the UI thread, full names before the settings exist.
  function fault_make(thrown: unknown): lines.Line {
    const header = jslb.header_make(constants.fault_type, {
      full: settings.names_full(),
    });
    return jslb.line_make(header, [], {
      thread: constants.thread,
      ...dispatch.cause_make(thrown),
    });
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
    // The worker reported the fault and the server ended the wire before it.
    worker.onmessage = (event: MessageEvent<unknown>) => {
      const fault = fault_read(event.data);
      error_overlay.overlay_show(fault.message, fault_text(fault));
      worker.terminate();
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

  // Sets the switches and settings, then the queue, its sink, AI port, sender.
  function thread_open(
    port: MessagePort,
    set: lines.SettingsSet,
  ): queue.TaskQueue {
    switches.switches_set(set.switches);
    settings.settings_set(set.settings);
    const synchronous = settings.settings_get(
      constants.synchronous_setting,
    ) as boolean;
    const tasks = new queue.TaskQueue(
      constants.thread,
      owners_make(),
      synchronous,
    );
    tasks.limit_attach(settings.settings_get);
    tasks.port_add(constants.ai_owner, new queue.ThreadPort(port));
    if (switches.debug_on()) {
      tasks.audit_attach();
      tasks.audit_open();
    }
    settings.sender_register((put: lines.SettingsPut) => {
      const line = line_build(constants.put_type, { settings: put.settings });
      tasks.line_notify(line, constants.ai_owner);
    });
    return tasks;
  }

  // The bring up both pages share, `open` taking the queue at `settings.set`.
  function page_open(
    open: (tasks: queue.TaskQueue, set: lines.SettingsSet) => void,
  ): void {
    error_overlay.overlay_install();
    const worker = worker_make();
    const channel = new MessageChannel();
    error_overlay.stop_register((thrown) =>
      channel.port1.postMessage(fault_make(thrown)),
    );
    channel.port1.onmessage = (event: MessageEvent<unknown>) => {
      const set = settings_take(event.data);
      open(thread_open(channel.port1, set), set);
    };
    worker_post(worker, channel.port2);
  }

  // The bring up of the UI thread, `run` getting its queue at `ui.tests`.
  export function test_page(run: (tasks: queue.TaskQueue) => void): void {
    page_open((tasks, set) => {
      if (switches.debug_on()) {
        harness.values_set(set.settings);
      }
      dispatch.handler_register(
        constants.tests_type,
        constants.handler_version,
        () => {
          run(tasks);
          return undefined;
        },
      );
    });
  }

  // The engine page's bring up, `run` getting its queue at `settings.set`.
  export function engine_page(run: (tasks: queue.TaskQueue) => void): void {
    page_open(run);
  }
}

Object.freeze(page);
