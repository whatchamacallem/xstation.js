// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The console view on the UI thread: one xterm.js terminal in a hidden child
// of a container, speaking ttyd's client protocol to tty 0 as `console.input`
// and `console.output` lines.

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
  // Registers a listener for the text that keystrokes and pastes produce.
  readonly onData: (listener: (data: string) => void) => unknown;
  // Registers a listener for a change of the size in character cells.
  readonly onResize: (
    listener: (size: { cols: number; rows: number }) => void
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
    input_type: "console.input",
    wake_type: "ui.console_reply",
    owner: "ai" as const,
    // The size of the terminal in characters, its columns and its rows.
    columns: 120,
    rows: 40,
    names_full: true,
  });

  // How far the console has got: idle, opening, open, or closed at its end.
  type Phase = "idle" | "opening" | "open" | "closed";

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
    private readonly child: HTMLElement;
    private readonly terminal: Terminal;
    private phase: Phase = "idle";
    private placed = false;
    private open_id: number | undefined = undefined;

    // Makes the hidden child and the terminal, which is not yet in the page.
    constructor(container: HTMLElement, tasks: queue.TaskQueue) {
      this.tasks = tasks;
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
    }

    // Shows the view, putting the terminal in the page the first time.
    view_show(): void {
      this.child.hidden = false;
      if (!this.placed) {
        this.terminal.open(this.child);
        this.placed = true;
      }
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
      const replies = jslb.payload_of(wake).replies as lines.Line[];
      const reply = replies[0];
      const type = jslb.field_get(reply[0], "type");
      if (type !== constants.open_type) {
        throw new Error(i18n("console_view.reply_type", type));
      }
      const id = jslb.field_get(reply[0], "reply");
      if (id !== this.open_id) {
        throw new Error(i18n("console_view.reply_id", id, this.open_id));
      }
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

    // Takes the end of tty 0: the screen stays, the terminal takes no input.
    exit_done(): void {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.exit_phase", this.phase));
      }
      this.phase = "closed";
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

    // Sends the new size of the terminal as one resize message.
    private resize_send(columns: number, rows: number): void {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.resize_phase", this.phase));
      }
      const body = utility.utf8_encode(utility.json_text({ columns, rows }));
      const message = message_make(constants.resize_kind, body);
      this.tasks.line_notify(input_line(message), constants.owner);
    }
  }
}

Object.freeze(console_view);
