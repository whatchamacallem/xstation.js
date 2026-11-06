// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The console view on the UI thread. API/ts/console_view.d.ts holds its rules.
// The terminal's rows are fitted to the height the container has above the
// band, the element after it, at each show and whenever the page or the band
// changes size while the view is shown, so every row is seen without
// scrolling.

// An xterm.js 5.5.0 marker of a buffer row, its line `-1` once disposed.
declare interface TerminalMarker {
  readonly line: number;
  dispose(): void;
}

// A cell of an xterm.js 5.5.0 buffer row: its text, width and attributes.
declare interface BufferCell {
  getChars(): string;
  getWidth(): number;
  getFgColorMode(): number;
  getBgColorMode(): number;
  getFgColor(): number;
  getBgColor(): number;
  isBold(): number;
  isDim(): number;
  isItalic(): number;
  isUnderline(): number;
  isBlink(): number;
  isInverse(): number;
  isInvisible(): number;
  isStrikethrough(): number;
  isOverline(): number;
}

// A row of an xterm.js 5.5.0 buffer.
declare interface BufferLine {
  getCell(column: number): BufferCell | undefined;
}

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
  // The cursor, base and rows of the active buffer, as xterm last parsed.
  readonly buffer: {
    readonly active: {
      readonly baseY: number;
      readonly cursorX: number;
      getLine(row: number): BufferLine | undefined;
    };
  };
  // Parses bytes of output as `UTF-8`, shows them, then calls the function.
  write(data: Uint8Array, parsed: () => void): void;
  // Marks the cursor's row of the active buffer, which xterm keeps current.
  registerMarker(): TerminalMarker;
  // Gives the terminal the keyboard focus.
  focus(): void;
  // Changes the size in character cells.
  resize(columns: number, rows: number): void;
  // Registers a listener for the text that keystrokes and pastes produce.
  readonly onData: (listener: (data: string) => void) => unknown;
}

namespace console_view {
  // The ttyd message kinds, line types, owner and terminal size.
  const constants = Object.freeze({
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    open_type: "console.open",
    close_type: "console.close",
    input_type: "console.input",
    wake_type: "ui.console_reply",
    closed_type: "ui.console_closed",
    owner: "ai" as const,
    // The keys of the held line: Enter, Backspace, Tab and the escape.
    enter: "\r",
    backspace: "\x7f",
    tab: "\t",
    escape: "\x1b",
    // The two characters that start a control or a single shift sequence.
    control_start: "[",
    shift_start: "O",
    // The range of the final character of a control sequence.
    final_first: 0x40,
    final_last: 0x7e,
    // The control characters, C0 below space, DEL and C1.
    space: 0x20,
    delete: 0x7f,
    c1_last: 0x9f,
    // The control sequence introducer, and its finals that place and erase.
    control: "\x1b[",
    place_final: "H",
    erase_below: "J",
    // The final of SGR, its reset and the codes of the cell's attributes.
    sgr_final: "m",
    sgr_reset: "0",
    bold_code: "1",
    dim_code: "2",
    italic_code: "3",
    underline_code: "4",
    blink_code: "5",
    inverse_code: "7",
    invisible_code: "8",
    strikethrough_code: "9",
    overline_code: "53",
    // xterm's colour modes: the default, 16 colours, 256 colours, RGB.
    mode_default: 0,
    mode_sixteen: 16777216,
    mode_palette: 33554432,
    // The SGR bases of the colours: normal and bright, then an index or RGB.
    foreground: { normal: 30, bright: 90, extended: 38 },
    background: { normal: 40, bright: 100, extended: 48 },
    palette_select: 5,
    rgb_select: 2,
    // The first bright colour of the 16, and a byte's mask.
    bright_first: 8,
    byte_mask: 255,
    // The text written for a cell whose text was erased.
    blank: " ",
    // The size when made, 120 by 40, its writer's, the rows fitted at a show.
    columns: 120,
    rows: 40,
    // The element of xterm.js that holds the rows, as tall as they are.
    screen_selector: ".xterm-screen",
  });

  // How far tty 0 has got: idle before and after it, opening, open, closing.
  type ViewPhase = "idle" | "opening" | "open" | "closing";

  // Where the echo starts: the marker of its row and the cursor's column.
  interface EchoStart {
    marker: TerminalMarker;
    column: number;
  }

  // The SGR bases of one colour, the foreground's or the background's.
  interface ColourBases {
    normal: number;
    bright: number;
    extended: number;
  }

  // The SGR codes of a colour of a mode, none for the default.
  function colour_codes(
    mode: number,
    colour: number,
    bases: ColourBases,
  ): string[] {
    if (mode === constants.mode_default) {
      return [];
    }
    if (mode === constants.mode_sixteen) {
      const bright = colour >= constants.bright_first;
      const code = bright
        ? bases.bright + colour - constants.bright_first
        : bases.normal + colour;
      return [String(code)];
    }
    if (mode === constants.mode_palette) {
      return [
        String(bases.extended),
        String(constants.palette_select),
        String(colour),
      ];
    }
    // The last value of the mode's two bits, RGB, as 0xRRGGBB.
    const mask = constants.byte_mask;
    return [
      String(bases.extended),
      String(constants.rgb_select),
      String((colour >> 16) & mask),
      String((colour >> 8) & mask),
      String(colour & mask),
    ];
  }

  // The SGR sequence that gives a cell's attributes from none.
  function sgr_make(cell: BufferCell): string {
    const codes: string[] = [constants.sgr_reset];
    const flags: [number, string][] = [
      [cell.isBold(), constants.bold_code],
      [cell.isDim(), constants.dim_code],
      [cell.isItalic(), constants.italic_code],
      [cell.isUnderline(), constants.underline_code],
      [cell.isBlink(), constants.blink_code],
      [cell.isInverse(), constants.inverse_code],
      [cell.isInvisible(), constants.invisible_code],
      [cell.isStrikethrough(), constants.strikethrough_code],
      [cell.isOverline(), constants.overline_code],
    ];
    for (const [set, code] of flags) {
      if (set !== 0) {
        codes.push(code);
      }
    }
    codes.push(
      ...colour_codes(
        cell.getFgColorMode(),
        cell.getFgColor(),
        constants.foreground,
      ),
      ...colour_codes(
        cell.getBgColorMode(),
        cell.getBgColor(),
        constants.background,
      ),
    );
    return constants.control + codes.join(";") + constants.sgr_final;
  }

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
      full: settings.names_full(),
    });
    return jslb.line_make(header, [jslb.blob_make(message)], {});
  }

  // Whether a character joins the held line: no C0, DEL or C1 control.
  function printable_is(character: string): boolean {
    const code = character.codePointAt(0) as number;
    return (
      code >= constants.space &&
      code !== constants.delete &&
      (code < constants.delete || code > constants.c1_last)
    );
  }

  // The index after the escape sequence that starts at the index given.
  function escape_end(characters: string[], index: number): number {
    const next = characters[index + 1];
    if (next === constants.shift_start) {
      return index + 3;
    }
    if (next !== constants.control_start) {
      return index + 2;
    }
    let end = index + 2;
    while (end < characters.length) {
      const code = characters[end].codePointAt(0) as number;
      end += 1;
      if (code >= constants.final_first && code <= constants.final_last) {
        break;
      }
    }
    return end;
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
    // Whether the AI's command runs, so that no keystroke is taken.
    private held = false;
    // The person's line since the last submission, held until Enter.
    private line = "";
    // Whether the held line's echo is on the screen.
    private echoed = false;
    // The echo's start, recorded once xterm has parsed what is before it.
    private start: EchoStart | undefined = undefined;
    // The writes that wait for xterm to parse the one before them.
    private readonly writes: (() => Uint8Array)[] = [];
    // Whether a write is with xterm and not yet parsed.
    private writing = false;

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

    // Whether tty 0 is open: its first message sent and input taken.
    open_is(): boolean {
      return this.phase === "open";
    }

    // Asks the AI worker for tty 0 from a UI handler, which returns the sleep.
    open_request(): dispatch.Sleep {
      if (this.phase !== "idle") {
        throw new Error(i18n("console_view.open_phase", this.phase));
      }
      const header = jslb.header_make(constants.open_type, {
        full: settings.names_full(),
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
      this.terminal.options.disableStdin = this.held;
    }

    // Asks the AI worker to close tty 0, from a UI handler that sleeps on it.
    close_request(): dispatch.Sleep {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.close_phase", this.phase));
      }
      const header = jslb.header_make(constants.close_type, {
        full: settings.names_full(),
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

    // Takes no keystrokes while the AI's command runs, the echo erased.
    input_hold(): void {
      this.held = true;
      this.terminal.options.disableStdin = true;
      this.echo_erase();
    }

    // Takes keystrokes again once the AI's command ends, the line echoed.
    input_free(): void {
      this.held = false;
      this.terminal.options.disableStdin = this.phase !== "open";
      this.echo_write();
    }

    // Writes a ttyd output message and ignores the title and preferences.
    output_feed(data: Uint8Array): void {
      if (data.length === 0) {
        throw new Error(i18n("console_view.message_empty"));
      }
      const kind = data[0];
      if (kind === constants.output_kind) {
        this.echo_erase();
        const output = data.subarray(1);
        this.write_queue(() => output);
        this.echo_write();
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

    // Edits the held line with typed text, submitting it at each Enter.
    private input_send(data: string): void {
      if (this.phase !== "open") {
        throw new Error(i18n("console_view.input_phase", this.phase));
      }
      if (this.held) {
        throw new Error(i18n("console_view.input_held"));
      }
      this.echo_erase();
      const characters = Array.from(data);
      let index = 0;
      while (index < characters.length) {
        const character = characters[index];
        if (character === constants.escape) {
          index = escape_end(characters, index);
          continue;
        }
        if (character === constants.enter) {
          this.line_submit();
        } else if (character === constants.backspace) {
          this.line = Array.from(this.line).slice(0, -1).join("");
        } else if (character === constants.tab || printable_is(character)) {
          this.line += character;
        }
        index += 1;
      }
      this.echo_write();
    }

    // Sends the held line with its carriage return as one message.
    private line_submit(): void {
      const body = utility.utf8_encode(this.line + constants.enter);
      const message = message_make(constants.input_kind, body);
      this.tasks.line_notify(input_line(message), constants.owner);
      this.line = "";
    }

    // Erases the held line's echo when it is on the screen.
    private echo_erase(): void {
      if (this.echoed) {
        this.write_queue(() => utility.utf8_encode(this.erase_make()));
        this.echoed = false;
      }
    }

    // Echoes the held line at the cursor while tty 0 is open and not held.
    private echo_write(): void {
      if (this.phase === "open" && !this.held && this.line !== "") {
        const echo = utility.utf8_encode(this.line);
        this.write_queue(() => {
          this.start = {
            marker: this.terminal.registerMarker(),
            column: this.terminal.buffer.active.cursorX,
          };
          return echo;
        });
        this.echoed = true;
      }
    }

    // The sequence that places the cursor at the echo's start and erases.
    private erase_make(): string {
      const start = this.start as EchoStart;
      this.start = undefined;
      const columns = this.terminal.cols;
      // A start past the last column is the next row's, as the echo wrapped.
      const wrapped = start.column === columns;
      const buffer = this.terminal.buffer.active;
      const base = buffer.baseY;
      const filled = start.marker.line;
      const row = filled - base + (wrapped ? 1 : 0);
      // A marker xterm disposed has a row that the scrollback dropped.
      const above = filled < 0 || row < 0;
      // The wrap is pending again only on a filled row still on the screen.
      const pending = wrapped && !above && row > 0;
      const restore = pending ? this.wrap_make(filled, row) : "";
      start.marker.dispose();
      const place_row = above ? 1 : row + 1;
      const place_column = above || wrapped ? 1 : start.column + 1;
      const place = `${place_row};${place_column}${constants.place_final}`;
      return (
        constants.control +
        place +
        constants.control +
        constants.erase_below +
        restore
      );
    }

    // Writes the filled row's last cell again, so its wrap is pending again.
    private wrap_make(filled: number, screen_row: number): string {
      const buffer = this.terminal.buffer.active;
      const columns = this.terminal.cols;
      const line = buffer.getLine(filled) as BufferLine;
      const last = line.getCell(columns - 1) as BufferCell;
      // The last cell of a wide character is its second half, of no width.
      const column = last.getWidth() === 0 ? columns - 2 : columns - 1;
      const cell = line.getCell(column) as BufferCell;
      const echo_row = buffer.getLine(filled + 1) as BufferLine;
      const program = echo_row.getCell(0) as BufferCell;
      // An erased cell shows as a blank, which writing a blank keeps.
      const chars = cell.getChars() === "" ? constants.blank : cell.getChars();
      const place = `${screen_row};${column + 1}${constants.place_final}`;
      return (
        constants.control + place + sgr_make(cell) + chars + sgr_make(program)
      );
    }

    // Queues a write, made once xterm has parsed every write before it.
    private write_queue(make: () => Uint8Array): void {
      this.writes.push(make);
      if (!this.writing) {
        this.write_next();
      }
    }

    // Makes and writes the next queued write, the next once it is parsed.
    private write_next(): void {
      const make = this.writes.shift();
      if (make === undefined) {
        this.writing = false;
        return;
      }
      this.writing = true;
      this.terminal.write(make(), () => this.write_next());
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
