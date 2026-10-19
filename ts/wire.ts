// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The ports over ttyd's WebSocket: the wire to the server on tty 1, which
// carries JSLB, and the console on tty 0, which relays ttyd's own protocol.
// One of the four modules that turn platform events into lines.

namespace wire {
  // The paths, protocol bytes, codes, line types and waits of the ports.
  const constants = Object.freeze({
    token_path: "token",
    socket_path: "ws",
    console_path: "ws?arg=console",
    subprotocol: "tty",
    page_scheme: "http:",
    page_secure: "https:",
    socket_scheme: "ws:",
    socket_secure: "wss:",
    columns: 80,
    rows: 24,
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    close_normal: 1000,
    wait_seconds: 120,
    second_ms: 1000,
    poll_ms: 0,
    hello_type: "hello",
    error_type: "error",
    input_type: "console.input",
    output_type: "console.output",
    read_type: "console.read",
    debug_setting: "debug",
  });

  // A timer that throws, naming what was awaited, unless stopped in time.
  class WaitTimer {
    private readonly what: string;
    private id: number | undefined = undefined;

    // Takes the text that names what the wait is for.
    constructor(what: string) {
      this.what = what;
    }

    // Whether the timer runs.
    timer_running(): boolean {
      return this.id !== undefined;
    }

    // Starts the timer, which must not be running.
    timer_start(): void {
      if (this.id !== undefined) {
        throw new Error(i18n("wire.timer_twice", this.what));
      }
      this.id = setTimeout(
        () => this.timer_expire(),
        constants.wait_seconds * constants.second_ms
      );
    }

    // Stops the timer when it runs.
    timer_stop(): void {
      if (this.id !== undefined) {
        clearTimeout(this.id);
        this.id = undefined;
      }
    }

    // Fails the wait.
    private timer_expire(): void {
      this.id = undefined;
      throw new Error(
        i18n("wire.wait_expired", constants.wait_seconds, this.what)
      );
    }
  }

  // The bytes of a socket message, which ttyd sends as binary.
  function message_bytes(event: MessageEvent): Uint8Array {
    const data: unknown = event.data;
    if (!(data instanceof ArrayBuffer)) {
      throw new Error(i18n("wire.message_text"));
    }
    return new Uint8Array(data);
  }

  // The first byte of a message of ttyd's: output, title or preferences.
  function message_kind(message: Uint8Array): number {
    if (message.length === 0) {
      throw new Error(i18n("wire.message_empty"));
    }
    const kind = message[0];
    if (
      kind !== constants.output_kind &&
      kind !== constants.title_kind &&
      kind !== constants.preferences_kind
    ) {
      throw new Error(i18n("wire.kind_unknown", kind));
    }
    return kind;
  }

  // The socket address of a path beside the page, secure as the page is.
  function socket_address(base_url: string, path: string): string {
    const url = new URL(path, base_url);
    if (url.protocol === constants.page_scheme) {
      url.protocol = constants.socket_scheme;
    } else if (url.protocol === constants.page_secure) {
      url.protocol = constants.socket_secure;
    } else {
      throw new Error(i18n("wire.scheme_unknown", base_url));
    }
    return url.href;
  }

  // The socket, which must have been made.
  function socket_made(socket: WebSocket | undefined, url: string): WebSocket {
    if (socket === undefined) {
      throw new Error(i18n("wire.socket_missing", url));
    }
    return socket;
  }

  // The socket, which must be open.
  function socket_ready(
    socket: WebSocket | undefined,
    url: string
  ): WebSocket {
    const made = socket_made(socket, url);
    if (made.readyState !== WebSocket.OPEN) {
      throw new Error(i18n("wire.socket_closed", url));
    }
    return made;
  }

  // Throws when a receiver is set already, naming the call that sets it.
  function receiver_unset(fn: unknown, call: string): void {
    if (fn !== undefined) {
      throw new Error(i18n("wire.receiver_twice", call));
    }
  }

  // The receiver for a line of the type, which must be set.
  function receiver_known<T>(fn: T | undefined, type: unknown): T {
    if (fn === undefined) {
      throw new Error(i18n("wire.receiver_missing", type));
    }
    return fn;
  }

  // A copy of the bytes in a buffer of their own, which a socket sends whole.
  function buffer_copy(bytes: Uint8Array): ArrayBuffer {
    const buffer = new ArrayBuffer(bytes.length);
    new Uint8Array(buffer).set(bytes);
    return buffer;
  }

  // Whether lines use full header names, which is debug mode.
  function names_full(): boolean {
    const debug = settings.settings_get(constants.debug_setting);
    if (typeof debug !== "boolean") {
      throw new Error(i18n("wire.debug_invalid", debug));
    }
    return debug;
  }

  // The body of ttyd's answer to the token request, which must succeed.
  function token_body(url: string, response: Response): Promise<ArrayBuffer> {
    if (!response.ok) {
      throw new Error(i18n("wire.token_status", url, response.status));
    }
    return response.arrayBuffer();
  }

  // The token in ttyd's JSON answer, read as strict `UTF-8`.
  function token_parse(url: string, body: ArrayBuffer): string {
    const text = utility.utf8_decode(new Uint8Array(body));
    const value: unknown = JSON.parse(text);
    const token =
      typeof value === "object" && value !== null && "token" in value
        ? value.token
        : undefined;
    if (typeof token !== "string") {
      throw new Error(i18n("wire.token_invalid", url, text));
    }
    return token;
  }

  // The first message of ttyd's client: the token and the terminal size.
  function start_message(token: string): ArrayBuffer {
    const text = utility.json_text({
      AuthToken: token,
      columns: constants.columns,
      rows: constants.rows,
    });
    return buffer_copy(utility.utf8_encode(text));
  }

  // The bytes of blob 1 of a `console.input` line, which must be in memory.
  function blob_bytes(line: lines.Line): Uint8Array {
    if (jslb.field_get(line[0], "blobs") !== 1) {
      throw new Error(i18n("wire.input_blob"));
    }
    const data = jslb.field_get(line[1] as lines.BlobHeader, "data");
    if (!(data instanceof Uint8Array)) {
      throw new Error(i18n("wire.input_bytes"));
    }
    return data;
  }

  // Encoded lines waiting to be sent, cut into the input frames of ttyd.
  export class FrameQueue {
    private readonly chunk_bytes: number;
    private readonly pieces: Uint8Array[] = [];
    private offset = 0;

    // Takes the most bytes a frame holds, its kind byte included.
    constructor(chunk_bytes: number) {
      if (!Number.isInteger(chunk_bytes) || chunk_bytes < 2) {
        throw new Error(i18n("wire.chunk_invalid", chunk_bytes));
      }
      this.chunk_bytes = chunk_bytes;
    }

    // Queues the pieces of one encoded line. A cache handle refuses it all.
    pieces_add(pieces: (Uint8Array | string)[]): void {
      const kept: Uint8Array[] = [];
      for (const piece of pieces) {
        if (typeof piece === "string") {
          throw new Error(i18n("wire.handle_unsent", piece));
        }
        if (piece.length > 0) {
          kept.push(piece);
        }
      }
      this.pieces.push(...kept);
    }

    // Whether a frame waits to be sent.
    frames_left(): boolean {
      return this.pieces.length > 0;
    }

    // The next frame: the input kind, then the next bytes of the first piece.
    frame_next(): ArrayBuffer {
      if (this.pieces.length === 0) {
        throw new Error(i18n("wire.frames_none"));
      }
      const piece = this.pieces[0];
      const size = Math.min(
        piece.length - this.offset,
        this.chunk_bytes - 1
      );
      const buffer = new ArrayBuffer(size + 1);
      const frame = new Uint8Array(buffer);
      frame[0] = constants.input_kind;
      frame.set(piece.subarray(this.offset, this.offset + size), 1);
      this.offset += size;
      if (this.offset === piece.length) {
        this.pieces.shift();
        this.offset = 0;
      }
      return buffer;
    }
  }

  // The console output as strict `UTF-8` text and the read waiting on it.
  export class ConsoleReader {
    private readonly decoder = new TextDecoder("utf-8", {
      fatal: true,
      ignoreBOM: true,
    });
    private until: string | undefined = undefined;
    private text = "";

    // Takes one message of ttyd's and answers the read once `until` shows.
    message_take(message: Uint8Array): lines.ConsoleReadReply | undefined {
      if (message_kind(message) !== constants.output_kind) {
        return undefined;
      }
      const text = this.decoder.decode(message.subarray(1), { stream: true });
      const until = this.until;
      if (until === undefined) {
        return undefined;
      }
      this.text += text;
      return this.text.includes(until) ? this.read_end(false) : undefined;
    }

    // Starts a read of the output from now on, until `until` shows in it.
    read_start(until: string): void {
      if (this.until !== undefined) {
        throw new Error(i18n("wire.read_twice", this.until));
      }
      this.until = until;
    }

    // Ends the waiting read when its timer expires.
    read_expire(): lines.ConsoleReadReply {
      if (this.until === undefined) {
        throw new Error(i18n("wire.read_none"));
      }
      return this.read_end(true);
    }

    // The reply of the waiting read, which ends it.
    private read_end(timed_out: boolean): lines.ConsoleReadReply {
      const reply = { text: this.text, timed_out };
      this.until = undefined;
      this.text = "";
      return reply;
    }
  }

  // The port to the server over ttyd's WebSocket on tty 1, carrying JSLB.
  export class WirePort implements queue.Port {
    // ttyd's title and preferences, kept for the overlay.
    title = "";
    preferences: unknown = undefined;
    private readonly chunk_bytes: number;
    private readonly decoder: jslb.LineDecoder;
    private readonly frames: FrameQueue;
    private readonly token_url: string;
    private readonly socket_url: string;
    private readonly token_timer: WaitTimer;
    private readonly open_timer: WaitTimer;
    private readonly hello_timer: WaitTimer;
    private readonly drain_timer: WaitTimer;
    private socket: WebSocket | undefined = undefined;
    private poll_id: number | undefined = undefined;
    private hello_fn: ((hello: lines.Line) => void) | undefined = undefined;
    private line_fn: ((line: lines.Line) => void) | undefined = undefined;
    private close_fn:
      | ((code: number, had_error: boolean) => void)
      | undefined = undefined;
    private hello_seen = false;
    private error_seen = false;
    // Set once this side closes the socket, on request or on a fault.
    private shut = false;

    // Takes the page's address, the most bytes a frame holds, the decoder.
    constructor(
      base_url: string,
      chunk_bytes: number,
      decoder: jslb.LineDecoder
    ) {
      this.chunk_bytes = chunk_bytes;
      this.decoder = decoder;
      this.frames = new FrameQueue(chunk_bytes);
      this.token_url = new URL(constants.token_path, base_url).href;
      this.socket_url = socket_address(base_url, constants.socket_path);
      this.token_timer = new WaitTimer(
        i18n("wire.what_token", this.token_url)
      );
      this.open_timer = new WaitTimer(i18n("wire.what_open", this.socket_url));
      this.hello_timer = new WaitTimer(i18n("wire.what_hello"));
      this.drain_timer = new WaitTimer(
        i18n("wire.what_drain", this.socket_url)
      );
    }

    // Fetches the token, opens the socket and passes `hello` to `fn`.
    wire_open(fn: (hello: lines.Line) => void): void {
      this.hello_receive(fn);
      this.token_timer.timer_start();
      fetch(this.token_url)
        .then((response) => token_body(this.token_url, response))
        .finally(() => this.token_timer.timer_stop())
        .then((body) => this.socket_start(token_parse(this.token_url, body)));
    }

    // Closes the socket with the normal code, which ends the server.
    wire_close(): void {
      this.port_shut();
    }

    // Encodes the line and sends it as input frames, once `hello` is in.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      if (!this.hello_seen) {
        throw new Error(
          i18n("wire.post_early", jslb.field_get(line[0], "type"))
        );
      }
      this.frames.pieces_add(jslb.line_encode(line));
      this.frames_send();
    }

    // Sets the one receiver of the lines after `hello`.
    line_receive(fn: (line: lines.Line) => void): void {
      receiver_unset(this.line_fn, "line_receive");
      this.line_fn = fn;
    }

    // Sets the one receiver of a close that this side did not make.
    close_receive(fn: (code: number, had_error: boolean) => void): void {
      receiver_unset(this.close_fn, "close_receive");
      this.close_fn = fn;
    }

    // Sets the one receiver of `hello`, which `wire_open` does.
    hello_receive(fn: (hello: lines.Line) => void): void {
      receiver_unset(this.hello_fn, "hello_receive");
      this.hello_fn = fn;
    }

    // Takes one message of ttyd's: keeps a title or preferences, or decodes.
    message_take(message: Uint8Array): void {
      const kind = message_kind(message);
      const body = message.subarray(1);
      if (kind === constants.title_kind) {
        this.title = utility.utf8_decode(body);
      } else if (kind === constants.preferences_kind) {
        this.preferences = JSON.parse(utility.utf8_decode(body));
      } else {
        for (const line of this.decoder.bytes_feed(body)) {
          this.line_take(line);
        }
      }
    }

    // Takes the close of the socket, a fault unless an error line came first.
    close_take(code: number): void {
      this.timers_stop();
      if (this.shut) {
        return;
      }
      this.shut = true;
      const fn = this.close_fn;
      if (fn !== undefined) {
        fn(code, this.error_seen);
      }
      if (!this.error_seen) {
        throw new Error(i18n("wire.close_silent", code));
      }
    }

    // Opens the socket with ttyd's subprotocol and listens to it.
    private socket_start(token: string): void {
      const socket = new WebSocket(this.socket_url, constants.subprotocol);
      socket.binaryType = "arraybuffer";
      socket.addEventListener("open", () => this.open_take(socket, token));
      socket.addEventListener("message", (event) => this.message_event(event));
      socket.addEventListener("close", (event) => this.close_take(event.code));
      this.open_timer.timer_start();
      this.socket = socket;
    }

    // Sends ttyd's first message once the socket is open, then awaits hello.
    private open_take(socket: WebSocket, token: string): void {
      this.open_timer.timer_stop();
      socket.send(start_message(token));
      this.hello_timer.timer_start();
    }

    // Takes a message of the socket, and closes the port when that throws.
    private message_event(event: MessageEvent): void {
      // A port that closed itself takes nothing more.
      if (this.shut) {
        return;
      }
      try {
        this.message_take(message_bytes(event));
      } catch (error) {
        this.port_shut();
        throw error;
      }
    }

    // Passes the first line to the hello receiver and the rest on.
    private line_take(line: lines.Line): void {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.error_type) {
        this.error_seen = true;
      } else if (!this.hello_seen) {
        if (type !== constants.hello_type) {
          throw new Error(i18n("wire.hello_missing", type));
        }
        this.hello_seen = true;
        this.hello_timer.timer_stop();
        receiver_known(this.hello_fn, type)(line);
        return;
      }
      receiver_known(this.line_fn, type)(line);
    }

    // Sends frames while the socket buffers less than one chunk, then polls.
    private frames_send(): void {
      const socket = socket_ready(this.socket, this.socket_url);
      while (this.frames.frames_left()) {
        if (socket.bufferedAmount >= this.chunk_bytes) {
          this.drain_wait();
          return;
        }
        socket.send(this.frames.frame_next());
        this.drain_timer.timer_stop();
      }
    }

    // Polls at the next turn, as a socket has no event for a drained buffer.
    private drain_wait(): void {
      if (this.poll_id !== undefined) {
        return;
      }
      if (!this.drain_timer.timer_running()) {
        this.drain_timer.timer_start();
      }
      this.poll_id = setTimeout(() => this.poll_take(), constants.poll_ms);
    }

    // Takes the poll and sends what the socket can take now.
    private poll_take(): void {
      this.poll_id = undefined;
      this.frames_send();
    }

    // Closes the socket from this side, after which no close is reported.
    private port_shut(): void {
      const socket = socket_made(this.socket, this.socket_url);
      this.shut = true;
      this.timers_stop();
      socket.close(constants.close_normal);
    }

    // Stops every wait and the poll.
    private timers_stop(): void {
      this.token_timer.timer_stop();
      this.open_timer.timer_stop();
      this.hello_timer.timer_stop();
      this.drain_timer.timer_stop();
      if (this.poll_id !== undefined) {
        clearTimeout(this.poll_id);
        this.poll_id = undefined;
      }
    }
  }

  // The port to the console on tty 0, relaying ttyd's own protocol as lines.
  export class ConsolePort implements queue.Port {
    private readonly socket_url: string;
    private readonly open_timer: WaitTimer;
    private readonly reader = new ConsoleReader();
    private socket: WebSocket | undefined = undefined;
    private line_fn: ((line: lines.Line) => void) | undefined = undefined;
    private close_fn: ((code: number) => void) | undefined = undefined;
    private read_id: number | undefined = undefined;
    private read_timer: number | undefined = undefined;

    // Takes the page's address.
    constructor(base_url: string) {
      this.socket_url = socket_address(base_url, constants.console_path);
      this.open_timer = new WaitTimer(i18n("wire.what_open", this.socket_url));
    }

    // Opens the console socket and calls `fn` once it is open.
    console_open(fn: () => void): void {
      if (this.socket !== undefined) {
        throw new Error(i18n("wire.open_twice", this.socket_url));
      }
      const socket = new WebSocket(this.socket_url, constants.subprotocol);
      socket.binaryType = "arraybuffer";
      socket.addEventListener("open", () => {
        this.open_timer.timer_stop();
        fn();
      });
      socket.addEventListener("message", (event) => this.message_event(event));
      socket.addEventListener("close", (event) =>
        this.close_event(event.code)
      );
      this.open_timer.timer_start();
      this.socket = socket;
    }

    // Closes the console socket with the normal code.
    console_close(): void {
      socket_made(this.socket, this.socket_url).close(constants.close_normal);
    }

    // Sends a `console.input` blob as one message or starts a `console.read`.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.input_type) {
        const socket = socket_ready(this.socket, this.socket_url);
        socket.send(buffer_copy(blob_bytes(line)));
      } else if (type === constants.read_type) {
        this.read_start(line);
      } else {
        throw new Error(i18n("wire.console_type", type));
      }
    }

    // Sets the one receiver of `console.output` and of the read replies.
    line_receive(fn: (line: lines.Line) => void): void {
      receiver_unset(this.line_fn, "line_receive");
      this.line_fn = fn;
    }

    // Sets the one receiver of the close of the console socket.
    close_receive(fn: (code: number) => void): void {
      receiver_unset(this.close_fn, "close_receive");
      this.close_fn = fn;
    }

    // Relays one message as `console.output`, then answers a read it ends.
    private message_event(event: MessageEvent): void {
      const message = message_bytes(event);
      const header = jslb.header_make(constants.output_type, {
        full: names_full(),
      });
      const line = jslb.line_make(header, [jslb.blob_make(message)], {});
      receiver_known(this.line_fn, constants.output_type)(line);
      const reply = this.reader.message_take(message);
      if (reply !== undefined) {
        this.read_answer(reply);
      }
    }

    // Starts a `console.read`, answered when `until` shows or its timer ends.
    private read_start(line: lines.Line): void {
      const id = jslb.field_get(line[0], "id");
      const payload = jslb.payload_of(line);
      const until = payload["until"];
      const seconds = payload["timeout_seconds"];
      if (typeof id !== "number") {
        throw new Error(i18n("wire.read_id"));
      }
      if (typeof until !== "string") {
        throw new Error(i18n("wire.read_until"));
      }
      if (
        typeof seconds !== "number" ||
        !Number.isFinite(seconds) ||
        seconds < 0
      ) {
        throw new Error(i18n("wire.read_seconds", seconds));
      }
      this.reader.read_start(until);
      this.read_id = id;
      this.read_timer = setTimeout(
        () => this.read_expire(),
        seconds * constants.second_ms
      );
    }

    // Answers the waiting read when its timer ends.
    private read_expire(): void {
      this.read_timer = undefined;
      this.read_answer(this.reader.read_expire());
    }

    // Posts the reply of the read that ended to the line receiver.
    private read_answer(reply: lines.ConsoleReadReply): void {
      if (this.read_timer !== undefined) {
        clearTimeout(this.read_timer);
        this.read_timer = undefined;
      }
      const id = this.read_id;
      if (id === undefined) {
        throw new Error(i18n("wire.read_none"));
      }
      this.read_id = undefined;
      const header = jslb.header_make(constants.read_type, {
        reply: id,
        full: names_full(),
      });
      const line = jslb.line_make(header, [], {
        text: reply.text,
        timed_out: reply.timed_out,
      });
      receiver_known(this.line_fn, constants.read_type)(line);
    }

    // Reports the close of the console socket with its code.
    private close_event(code: number): void {
      this.open_timer.timer_stop();
      const fn = this.close_fn;
      if (fn !== undefined) {
        fn(code);
      }
    }
  }
}

Object.freeze(wire);
