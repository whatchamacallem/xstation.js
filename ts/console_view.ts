// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The console view on the UI thread: one xterm.js terminal in a hidden child
// of a container, speaking ttyd's client protocol to tty 0 as `console.input`
// and `console.output` lines, asking for tty 0 and its close, and asking for
// it again once it has ended. The terminal's rows are fitted to the height
// the container has above the band, the element after it, at each show and
// whenever the page or the band changes size while the view is shown, so
// every row is seen without scrolling.

// The xterm.js 5.5.0 members that the view uses, which no package declares.
declare class Terminal {
  // The width in character cells.
  readonly cols: number;
  // The height in character cells.
  readonly rows: number;
  // The live options, of which the view sets whether keystrokes are taken.
  readonly options: { disableStdin: boolean };
  // Makes a terminal of the size given, not yet in the page.
  constructor(options: { cols: number; rows: number; disableStdin: boolean });
  // Puts the terminal in the page, inside the element.
  open(parent: HTMLElement): void;
  // Parses bytes of output as `UTF-8` and shows them.
  write(data: Uint8Array): void;
  // Gives the terminal the keyboard focus.
  focus(): void;
  // Changes the size in character cells, a change reported to `onResize`.
  resize(columns: number, rows: number): void;
  // Registers a listener for the text that keystrokes and pastes produce.
  readonly onData: (listener: (data: string) => void) => unknown;
  // Registers a listener for a change of the size in character cells.
  readonly onResize: (
    listener: (size: { cols: number; rows: number }) => void,
  ) => unknown;
}

namespace console_view {
  // The ttyd message kinds, line types, owner, terminal size and name form.
  const constants = Object.freeze({
    input_kind: 0x30,
    output_kind: 0x30,
    resize_kind: 0x31,
    title_kind: 0x31,
    preferences_kind: 0x32,
    open_type: "console.open",
    close_type: "console.close",
    input_type: "console.input",
    wake_type: "ui.console_reply",
    closed_type: "ui.console_closed",
    owner: "ai" as const,
    // The size when made, 120 by 40, its writer's; the rows fitted at a show.
    columns: 120,
    rows: 40,
    names_full: true,
    // The element of xterm.js that holds the rows, as tall as they are.
    screen_selector: ".xterm-screen",
  });

  // How far tty 0 has got: idle before and after it, opening, open, closing.
  type ViewPhase = "idle" | "opening" | "open" | "closing";

  // A message of ttyd's client: the kind byte, then the body.
  function message_make(kind: number, body: Uint8Array): Uint8Array {
    const message = new Uint8Array(body.length + 1);
    message[0] = kind;
    message.set(body, 1);
    return message;
  }

  // The `console.input` line that carries one message as its blob.
  function input_line(message: Uint8Array): lines.Line {
    const header = jslb.header_make(constants.input_type, {
      full: constants.names_full,
    });
    return jslb.line_make(header, [jslb.blob_make(message)], {});
  }

  // The console view: one terminal in a hidden child of a container.
  export class ConsoleView {
    private readonly tasks: queue.TaskQueue;
    private readonly container: HTMLElement;
    private readonly child: HTMLElement;
    private readonly terminal: Terminal;
    private readonly observer: ResizeObserver;
    private phase: ViewPhase = "idle";
    private placed = false;
    // The height of one row in pixels, measured when the terminal is placed.
    private cell = 0;
    private open_id: number | undefined = undefined;
    private close_id: number | undefined = undefined;

    // Makes the hidden child and the terminal, which is not yet in the page.
    constructor(container: HTMLElement, tasks: queue.TaskQueue) {
      this.tasks = tasks;
      this.container = container;
      this.child = container.ownerDocument.createElement("div");
      this.child.hidden = true;
      container.append(this.child);
      this.terminal = new Terminal({
        cols: constants.columns,
        rows: constants.rows,
        disableStdin: true,
      });
      this.terminal.onData((data) => this.input_send(data));
      this.terminal.onResize((size) => this.resize_send(size.cols, size.rows));
      this.observer = new ResizeObserver(() => this.space_change());
    }

    // Shows the view, placing the terminal the first time, and fits its rows.
    view_show(): void {
      this.child.hidden = false;
      if (!this.placed) {
        this.terminal_place();
      }
      this.rows_fit();
      this.terminal.focus();
    }

    // Hides the view. The terminal keeps its screen, scrollback and colours.
    view_hide(): void {
      this.child.hidden = true;
    }

    // Shows the view when it is hidden and hides it when shown.
    view_toggle(): void {
      if (this.child.hidden) {
        this.view_show();
      } else {
        this.view_hide();
      }
    }

    // Whether the view is shown while tty 0 is idle, so that it is asked for.
    open_wanted(): boolean {
      return !this.child.hidden && this.phase === "idle";
    }

    // Asks the AI worker for tty 0 from a UI handler, which returns the sleep.
    open_request(): dispatch.Sleep {
      if (this.phase !== "idle") {
        throw new Error(i18n("console_view.open_phase", this.phase));
      }
      const header = jslb.header_make(constants.open_type, {
        full: constants.names_full,
      });
      const line = jslb.line_make(header, [], {});
      const id = this.tasks.task_submit(line, constants.owner);
      this.phase = "opening";
      this.open_id = id;
      return dispatch.task_sleep(null, [id], constants.wake_type);
    }

    // Takes the wake of that sleep, sends ttyd's first message, takes input.
    open_done(wake: lines.Line): void {
      if (this.phase !== "opening") {
        throw new Error(i18n("console_view.reply_phase", this.phase));
      }
      const reply = this.reply_take(wake, constants.open_type, this.open_id);
      const token = jslb.payload_of(reply).token;
      if (typeof token !== "string") {
        throw new Error(i18n("console_view.token_invalid", typeof token));
      }
      const text = utility.json_text({
        AuthToken: token,
        columns: this.terminal.cols,
        rows: this.terminal.rows,
      });
      const message = utility.utf8_encode(text);
      this.tasks.line_notify(input_line(message), constants.owner);
      this.phase = "open";
      this.terminal.options.disableStdin = false;
    }

    // Asks the AI worker to close tty 0, from a UI handler that sleeps on it.
    close_request(): dispatch.Sleep {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.close_phase", this.phase));
      }
      const header = jslb.header_make(constants.close_type, {
        full: constants.names_full,
      });
      const line = jslb.line_make(header, [], {});
      const id = this.tasks.task_submit(line, constants.owner);
      this.phase = "closing";
      this.close_id = id;
      this.terminal.options.disableStdin = true;
      return dispatch.task_sleep(null, [id], constants.closed_type);
    }

    // Takes the wake of that sleep. The end of tty 0 follows as its exit.
    close_done(wake: lines.Line): void {
      if (this.phase !== "closing") {
        throw new Error(i18n("console_view.closed_phase", this.phase));
      }
      this.reply_take(wake, constants.close_type, this.close_id);
    }

    // Ends tty 0: the screen stays, input is off, and a later show opens it.
    exit_done(): void {
      if (this.phase !== "open" && this.phase !== "closing") {
        throw new Error(i18n("console_view.exit_phase", this.phase));
      }
      this.phase = "idle";
      this.terminal.options.disableStdin = true;
    }

    // Writes a ttyd output message and ignores the title and preferences.
    output_feed(data: Uint8Array): void {
      if (data.length === 0) {
        throw new Error(i18n("console_view.message_empty"));
      }
      const kind = data[0];
      if (kind === constants.output_kind) {
        this.terminal.write(data.subarray(1));
        return;
      }
      if (
        kind === constants.title_kind ||
        kind === constants.preferences_kind
      ) {
        return;
      }
      throw new Error(i18n("console_view.kind_unknown", kind));
    }

    // Sends typed text. The terminal takes no keystrokes unless it is open.
    private input_send(data: string): void {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.input_phase", this.phase));
      }
      const body = utility.utf8_encode(data);
      const message = message_make(constants.input_kind, body);
      this.tasks.line_notify(input_line(message), constants.owner);
    }

    // Sends the new size of an open terminal as one resize message.
    private resize_send(columns: number, rows: number): void {
      // Unless tty 0 is open, the first message of its next opening has it.
      if (this.phase !== "open") {
        return;
      }
      const body = utility.utf8_encode(utility.json_text({ columns, rows }));
      const message = message_make(constants.resize_kind, body);
      this.tasks.line_notify(input_line(message), constants.owner);
    }

    // Opens the terminal in the child, measures a row, watches the space.
    private terminal_place(): void {
      this.terminal.open(this.child);
      this.placed = true;
      const screen = this.child.querySelector<HTMLElement>(
        constants.screen_selector,
      ) as HTMLElement;
      this.cell = screen.getBoundingClientRect().height / this.terminal.rows;
      const band = this.band_get();
      this.observer.observe(band.parentElement as HTMLElement);
      this.observer.observe(band);
    }

    // Sizes the rows to the height the container has above the band.
    private rows_fit(): void {
      const container = this.container;
      const top = container.getBoundingClientRect().top;
      const bars = container.offsetHeight - container.clientHeight;
      const space = this.band_get().getBoundingClientRect().top - top - bars;
      const rows = Math.floor(space / this.cell);
      if (!Number.isInteger(rows) || rows < 1) {
        throw new Error(i18n("console_view.rows_unfit", space, this.cell));
      }
      this.terminal.resize(this.terminal.cols, rows);
    }

    // Fits the rows again when the page or the band changed size.
    private space_change(): void {
      // A hidden terminal cannot be measured, and its next show fits it.
      if (!this.child.hidden) {
        this.rows_fit();
      }
    }

    // The band the rows stay above, which is the element after the container.
    private band_get(): HTMLElement {
      return this.container.nextElementSibling as HTMLElement;
    }

    // The one reply of a wake, which must answer the request of the id given.
    private reply_take(
      wake: lines.Line,
      type: string,
      id: number | undefined,
    ): lines.Line {
      const replies = jslb.payload_of(wake).replies as lines.Line[];
      const reply = replies[0];
      const found = jslb.field_get(reply[0], "type");
      if (found !== type) {
        throw new Error(i18n("console_view.reply_type", found, type));
      }
      const answered = jslb.field_get(reply[0], "reply");
      if (answered !== id) {
        throw new Error(i18n("console_view.reply_id", answered, id));
      }
      return reply;
    }
  }
}

Object.freeze(console_view);
