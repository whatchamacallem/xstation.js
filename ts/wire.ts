// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The ports over ttyd's WebSocket: the wire to the server on tty 1, which
// carries JSLB, and the console on tty 0, which relays ttyd's own protocol.
// One of the four modules that turn platform events into lines. Every line
// they build takes the form `settings.names_full()` picks.
//
// ttyd 1.7.7's protocol, the same on both ttys. The client fetches `/token`,
// opens `/ws`, or `/ws?arg=console` for tty 0, with the subprotocol `tty`,
// and sends one first message of JSON text: on tty 1 only `AuthToken`, on
// tty 0 also `columns` and `rows`, the console view's. That ttyd 1.7.7
// accepts a first message without a size is from memory, owed to testing.
// After it, each client message is one kind byte and its body: '0' input,
// '1' a resize, which the page never sends. Each server message is one kind
// byte and its body: '0' output, '1' the window title, '2' the preferences
// as JSON. ttyd runs the command once the first message is in, and ends the
// socket when the command exits.
//
// tty 1 carries JSLB in the bodies of '0' messages both ways, split into
// input frames of `chunk_bytes`, each sent once `bufferedAmount` is under
// one chunk. Every blob it sends is bytes in memory, never a cache handle.
// The first line, `tap.start`, is read before the settings exist, under
// fixed bounds: `first_line_max` 10 MiB, no blob. The settings then size the
// decoder. A second `tap.start`, as `system.restart` makes, throws
// `wire.start_twice`: only a reload of the page takes a new first line. The
// JSON of ttyd's token answer and of its preferences is read by
// `jslb.json_decode`.
//
// A fault while the port takes a message stops it taking more but leaves the
// socket open, so that the worker's report can still send the `error` line
// by `wire_end`. `wire_end` never closes the socket: the server ends it by
// its exit once it has logged the failure, and `fn` runs at that close, or
// at once on a socket already closed. Its wait runs under the drain timer,
// whose expiry is a fault met while a fault is reported.

namespace wire {
  // The paths, protocol bytes, codes, line types, setting ids and limits.
  const constants = Object.freeze({
    token_path: "token",
    socket_path: "ws",
    console_path: "ws?arg=console",
    subprotocol: "tty",
    page_scheme: "http:",
    page_secure: "https:",
    socket_scheme: "ws:",
    socket_secure: "wss:",
    input_kind: 0x30,
    output_kind: 0x30,
    title_kind: 0x31,
    preferences_kind: 0x32,
    close_normal: 1000,
    second_ms: 1000,
    // The wait for ttyd's token: 120 s, a default kept from the earlier code.
    token_seconds: 120,
    // A socket opening: 120 s, a default kept from the earlier code.
    open_seconds: 120,
    // The first line once the socket opens: 120 s, kept from earlier code.
    first_seconds: 120,
    // A drained socket buffer: 120 s, a default kept from the earlier code.
    drain_seconds: 120,
    // A poll of the socket buffer: 0 ms, a default chosen by its writer.
    poll_ms: 0,
    // The longest delay a timer holds: `2^31 - 1` ms, the platform's limit.
    timer_max_ms: 2 ** 31 - 1,
    // The longest first line: 10 MiB, a default kept from earlier code.
    first_line_max: 10485760,
    // The first phase blob bytes of a message: none, as the first has none.
    first_blob_max: 0,
    // The first phase blob bytes held in memory: none.
    first_overflow_bytes: 0,
    first_type: "tap.start",
    error_type: "error",
    open_type: "console.open",
    input_type: "console.input",
    output_type: "console.output",
    read_type: "console.read",
    chunk_setting: "chunk_bytes",
    line_setting: "line_max",
    blob_setting: "blob_max",
    overflow_setting: "overflow_bytes",
  });

  // A timer that throws, naming what was awaited, unless stopped in time.
  class WaitTimer {
    private readonly what: string;
    private readonly seconds: number;
    private id: number | undefined = undefined;

    // Takes the text that names what the wait is for, and its seconds.
    constructor(what: string, seconds: number) {
      this.what = what;
      this.seconds = seconds;
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
        this.seconds * constants.second_ms,
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
      throw new Error(i18n("wire.wait_expired", this.seconds, this.what));
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
    url: string,
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
    const value: unknown = jslb.json_decode(text);
    const token =
      typeof value === "object" && value !== null && "token" in value
        ? value.token
        : undefined;
    if (typeof token !== "string") {
      throw new Error(i18n("wire.token_invalid", url, text));
    }
    return token;
  }

  // Fetches ttyd's token while the timer runs and passes it to `fn`.
  function token_fetch(
    url: string,
    timer: WaitTimer,
    fn: (token: string) => void,
  ): void {
    timer.timer_start();
    fetch(url)
      .then((response) => token_body(url, response))
      .finally(() => timer.timer_stop())
      .then((body) => fn(token_parse(url, body)));
  }

  // The first message of ttyd's client: the token.
  function start_message(token: string): ArrayBuffer {
    const text = utility.json_text({ AuthToken: token });
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

  // The id of a request to the console port, which must have one.
  function request_id(line: lines.Line, type: string): number {
    const id = jslb.field_get(line[0], "id");
    if (typeof id !== "number") {
      throw new Error(i18n("wire.id_missing", type));
    }
    return id;
  }

  // Bytes of an encoded line in memory, read as views with no copy.
  class MemoryPiece {
    readonly size: number;
    private readonly bytes: Uint8Array;

    // Takes the bytes.
    constructor(bytes: Uint8Array) {
      this.bytes = bytes;
      this.size = bytes.length;
    }

    // A view of the bytes of the range.
    range_read(offset: number, length: number): Uint8Array {
      return this.bytes.subarray(offset, offset + length);
    }
  }

  // An encoded piece of a line, which must be bytes: no cache handle is sent.
  function piece_make(data: Uint8Array | string): MemoryPiece {
    if (typeof data === "string") {
      throw new Error(i18n("wire.handle_unsent", data));
    }
    return new MemoryPiece(data);
  }

  // A piece waiting in the frame queue, and whether it is a blob's bytes.
  interface QueuedPiece {
    piece: MemoryPiece;
    blob: boolean;
  }

  // Encoded lines waiting to go to ttyd as input frames, bounded in bytes.
  export class FrameQueue {
    private readonly chunk_bytes: number;
    private readonly line_max: number;
    private readonly blob_max: number;
    private readonly pieces: QueuedPiece[] = [];
    private offset = 0;
    // The blob bytes of the lines queued that no frame has taken yet.
    private held = 0;

    // Takes the bytes of a frame with its kind, of a line, of all blobs held.
    constructor(chunk_bytes: number, line_max: number, blob_max: number) {
      if (!Number.isInteger(chunk_bytes) || chunk_bytes < 2) {
        throw new Error(i18n("wire.chunk_invalid", chunk_bytes));
      }
      this.chunk_bytes = chunk_bytes;
      this.line_max = line_max;
      this.blob_max = blob_max;
    }

    // Queues a line, refused over `line_max` or with blobs over `blob_max`.
    line_add(line: lines.Line): void {
      const type = jslb.field_get(line[0], "type");
      const encoded = jslb.line_encode(line);
      const pieces: QueuedPiece[] = [];
      for (let number = 0; number < encoded.length; number += 1) {
        const piece = piece_make(encoded[number]);
        pieces.push({ piece, blob: number > 0 });
      }
      const bytes = pieces[0].piece.size;
      if (bytes > this.line_max) {
        throw new Error(i18n("wire.line_over", type, bytes, this.line_max));
      }
      let total = 0;
      for (const queued of pieces.slice(1)) {
        total += queued.piece.size;
      }
      if (total > this.blob_max) {
        throw new Error(i18n("wire.blobs_over", type, total, this.blob_max));
      }
      if (this.held + total > this.blob_max) {
        throw new Error(
          i18n("wire.queue_over", type, total, this.held, this.blob_max),
        );
      }
      // A piece of no bytes, an empty blob, sends no frame.
      this.pieces.push(...pieces.filter((queued) => queued.piece.size > 0));
      this.held += total;
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
      const { piece, blob } = this.pieces[0];
      const size = Math.min(piece.size - this.offset, this.chunk_bytes - 1);
      const buffer = new ArrayBuffer(size + 1);
      const frame = new Uint8Array(buffer);
      frame[0] = constants.input_kind;
      frame.set(piece.range_read(this.offset, size), 1);
      this.offset += size;
      if (blob) {
        this.held -= size;
      }
      if (this.offset === piece.size) {
        this.pieces.shift();
        this.offset = 0;
      }
      return buffer;
    }
  }

  // A read waiting on the console output: `until`, its decoder, its text.
  interface ReadState {
    until: string;
    decoder: TextDecoder;
    text: string;
  }

  // Decodes output for a read as strict `UTF-8`, a split sequence kept whole.
  function output_decode(read: ReadState, bytes: Uint8Array): string {
    try {
      return read.decoder.decode(bytes, { stream: true });
    } catch (error) {
      throw utility.error_wrap(i18n("wire.output_invalid", read.until), error);
    }
  }

  // The reads of the console output, each decoded from its own start.
  export class ConsoleReader {
    private read: ReadState | undefined = undefined;

    // Takes a message of ttyd's, ignored unless a read waits that it may end.
    message_take(message: Uint8Array): lines.ConsoleReadReply | undefined {
      const kind = message_kind(message);
      const read = this.read;
      if (kind !== constants.output_kind || read === undefined) {
        return undefined;
      }
      read.text += output_decode(read, message.subarray(1));
      if (!read.text.includes(read.until)) {
        return undefined;
      }
      return this.read_end(read, false);
    }

    // Starts a read of the output from now on, until `until` shows in it.
    read_start(until: string): void {
      const read = this.read;
      if (read !== undefined) {
        throw new Error(i18n("wire.read_twice", read.until));
      }
      this.read = {
        until,
        decoder: new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }),
        text: "",
      };
    }

    // Ends the waiting read when its timer expires or its socket closes.
    read_expire(): lines.ConsoleReadReply {
      const read = this.read;
      if (read === undefined) {
        throw new Error(i18n("wire.read_none"));
      }
      return this.read_end(read, true);
    }

    // The reply of the waiting read, which ends it.
    private read_end(
      read: ReadState,
      timed_out: boolean,
    ): lines.ConsoleReadReply {
      this.read = undefined;
      return { text: read.text, timed_out };
    }
  }

  // The parts of the wire port that the settings size, built after the first.
  interface SettingsParts {
    chunk_bytes: number;
    frames: FrameQueue;
  }

  // The port to the server over ttyd's WebSocket on tty 1, carrying JSLB.
  export class WirePort implements queue.Port {
    // ttyd's title and preferences, kept for the overlay.
    title = "";
    preferences: unknown = undefined;
    private readonly sink: jslb.BlobSink;
    private readonly settings_get: (id: string) => unknown;
    private readonly token_url: string;
    private readonly socket_url: string;
    private readonly token_timer: WaitTimer;
    private readonly open_timer: WaitTimer;
    private readonly first_timer: WaitTimer;
    private readonly drain_timer: WaitTimer;
    // The first phase decoder until the settings size one, then that one.
    private decoder: jslb.LineDecoder;
    private parts: SettingsParts | undefined = undefined;
    private socket: WebSocket | undefined = undefined;
    private poll_id: number | undefined = undefined;
    private first_fn: ((first: lines.Line) => void) | undefined = undefined;
    private line_fn: ((line: lines.Line) => void) | undefined = undefined;
    private close_fn:
      ((code: number, had_error: boolean) => void) | undefined = undefined;
    // What `wire_end` calls at the server's close, set by its call.
    private end_fn: (() => void) | undefined = undefined;
    private first_seen = false;
    private error_seen = false;
    // Set once the socket is done with: closed by either side or ended.
    private shut = false;
    // Cleared by a fault in a message, after which no message is taken.
    private taking = true;

    // Takes the page's address, the sink of streamed blobs, the settings.
    constructor(
      base_url: string,
      sink: jslb.BlobSink,
      settings_get: (id: string) => unknown,
    ) {
      this.sink = sink;
      this.settings_get = settings_get;
      this.decoder = new jslb.LineDecoder(
        constants.first_line_max,
        constants.first_blob_max,
        constants.first_overflow_bytes,
        sink,
      );
      this.token_url = new URL(constants.token_path, base_url).href;
      this.socket_url = socket_address(base_url, constants.socket_path);
      this.token_timer = new WaitTimer(
        i18n("wire.what_token", this.token_url),
        constants.token_seconds,
      );
      this.open_timer = new WaitTimer(
        i18n("wire.what_open", this.socket_url),
        constants.open_seconds,
      );
      this.first_timer = new WaitTimer(
        i18n("wire.what_first"),
        constants.first_seconds,
      );
      this.drain_timer = new WaitTimer(
        i18n("wire.what_drain", this.socket_url),
        constants.drain_seconds,
      );
    }

    // Fetches the token, opens the socket, gives the first line to `fn`, once.
    wire_open(fn: (first: lines.Line) => void): void {
      if (this.first_fn !== undefined) {
        throw new Error(i18n("wire.open_twice", this.socket_url));
      }
      this.first_receive(fn);
      token_fetch(this.token_url, this.token_timer, (token) =>
        this.socket_start(token),
      );
    }

    // Closes the socket with the normal code, which ends the server.
    wire_close(): void {
      this.port_shut();
    }

    // Sends the line, awaits the server's end of the socket, calls `fn`.
    wire_end(line: lines.Line, fn: () => void): void {
      receiver_unset(this.end_fn, "wire_end");
      this.end_fn = fn;
      const socket = this.socket;
      if (
        this.shut ||
        socket === undefined ||
        socket.readyState !== WebSocket.OPEN
      ) {
        this.shut = true;
        this.timers_stop();
        fn();
        return;
      }
      // The drain timer starts once the last frame is sent, in `frames_send`.
      this.line_post(line, []);
    }

    // Encodes the line and sends it as input frames, once the first is in.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      if (!this.first_seen) {
        throw new Error(
          i18n("wire.post_early", jslb.field_get(line[0], "type")),
        );
      }
      this.parts_live().frames.line_add(line);
      this.frames_send();
    }

    // Sets the one receiver of the lines after the first.
    line_receive(fn: (line: lines.Line) => void): void {
      receiver_unset(this.line_fn, "line_receive");
      this.line_fn = fn;
    }

    // Sets the one receiver of a close that this side did not make.
    close_receive(fn: (code: number, had_error: boolean) => void): void {
      receiver_unset(this.close_fn, "close_receive");
      this.close_fn = fn;
    }

    // Sets the one receiver of the first line, which `wire_open` does.
    first_receive(fn: (first: lines.Line) => void): void {
      receiver_unset(this.first_fn, "first_receive");
      this.first_fn = fn;
    }

    // Takes one message of ttyd's: keeps a title or preferences, or decodes.
    message_take(message: Uint8Array): void {
      const kind = message_kind(message);
      const body = message.subarray(1);
      if (kind === constants.title_kind) {
        this.title = utility.utf8_decode(body);
      } else if (kind === constants.preferences_kind) {
        this.preferences = jslb.json_decode(utility.utf8_decode(body));
      } else {
        this.output_take(body);
      }
    }

    // The close: what `wire_end` awaits, else a fault without an error line.
    close_take(code: number): void {
      this.timers_stop();
      if (this.shut) {
        return;
      }
      this.shut = true;
      const end = this.end_fn;
      if (end !== undefined) {
        end();
        return;
      }
      const fn = this.close_fn;
      if (fn !== undefined) {
        fn(code, this.error_seen);
      }
      // The error line is the fault, which the queue or this port raised.
      if (this.error_seen) {
        return;
      }
      if (!this.decoder.idle()) {
        throw new Error(i18n("wire.close_partial", code));
      }
      throw new Error(i18n("wire.close_silent", code));
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

    // Sends ttyd's first message once the socket is open, then awaits ours.
    private open_take(socket: WebSocket, token: string): void {
      this.open_timer.timer_stop();
      socket.send(start_message(token));
      this.first_timer.timer_start();
    }

    // Takes a socket message: a fault stops the taking but not the socket.
    private message_event(event: MessageEvent): void {
      // A port done with its socket, or after a fault, takes nothing more.
      if (this.shut || !this.taking) {
        return;
      }
      try {
        this.message_take(message_bytes(event));
      } catch (error) {
        this.taking = false;
        this.timers_stop();
        throw error;
      }
    }

    // Decodes output, passes the lines on, then raises any fault held.
    private output_take(body: Uint8Array): void {
      const first_phase = !this.first_seen;
      // After the first the settings size the decoder, built here at latest.
      if (!first_phase) {
        this.parts_live();
      }
      const decoder = this.decoder;
      for (const line of decoder.bytes_feed(body)) {
        // Bytes after the first are the settings decoder's, so none come yet.
        if (first_phase && this.first_seen) {
          throw new Error(i18n("wire.start_trailing"));
        }
        this.line_take(line);
      }
      // Empty bytes finish no line and raise a fault met after the lines.
      decoder.bytes_feed(new Uint8Array(0));
      if (first_phase && this.first_seen && !decoder.idle()) {
        throw new Error(i18n("wire.start_trailing"));
      }
    }

    // The first line to its receiver, the rest on, and an early error thrown.
    private line_take(line: lines.Line): void {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.error_type) {
        this.error_seen = true;
        // Before the first no queue reads lines, so the port raises it.
        if (!this.first_seen) {
          const payload = jslb.payload_of(line);
          throw new Error(
            i18n("wire.error_first", payload.message, payload.stack),
          );
        }
      } else if (!this.first_seen) {
        if (type !== constants.first_type) {
          throw new Error(i18n("wire.start_missing", type));
        }
        this.first_seen = true;
        this.first_timer.timer_stop();
        receiver_known(this.first_fn, type)(line);
        return;
      } else if (type === constants.first_type) {
        throw new Error(i18n("wire.start_twice"));
      }
      receiver_known(this.line_fn, type)(line);
    }

    // The frame queue and decoder the settings size, built at first need.
    private parts_live(): SettingsParts {
      const built = this.parts;
      if (built !== undefined) {
        return built;
      }
      const chunk_bytes = this.setting_number(constants.chunk_setting);
      const line_max = this.setting_number(constants.line_setting);
      const blob_max = this.setting_number(constants.blob_setting);
      const frames = new FrameQueue(chunk_bytes, line_max, blob_max);
      this.decoder = new jslb.LineDecoder(
        line_max,
        blob_max,
        this.setting_number(constants.overflow_setting),
        this.sink,
      );
      const parts = { chunk_bytes, frames };
      this.parts = parts;
      return parts;
    }

    // A number of the settings, which the server checked before the first.
    private setting_number(id: string): number {
      return this.settings_get(id) as number;
    }

    // Sends frames while the socket buffers less than one chunk, then polls.
    private frames_send(): void {
      const parts = this.parts_live();
      const socket = socket_ready(this.socket, this.socket_url);
      while (parts.frames.frames_left()) {
        if (socket.bufferedAmount >= parts.chunk_bytes) {
          this.drain_wait();
          return;
        }
        socket.send(parts.frames.frame_next());
        this.drain_timer.timer_stop();
      }
      // All is sent, so a `wire_end` waits for the close under the timer.
      if (this.end_fn !== undefined) {
        this.drain_timer.timer_start();
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
      this.first_timer.timer_stop();
      this.drain_timer.timer_stop();
      if (this.poll_id !== undefined) {
        clearTimeout(this.poll_id);
        this.poll_id = undefined;
      }
    }
  }

  // The port to the console on tty 0, relaying ttyd's own protocol as lines.
  export class ConsolePort implements queue.Port {
    private readonly token_url: string;
    private readonly socket_url: string;
    private readonly token_timer: WaitTimer;
    private readonly open_timer: WaitTimer;
    private readonly reader = new ConsoleReader();
    private socket: WebSocket | undefined = undefined;
    // The id of the `console.open` that waits for the socket, while one does.
    private open_id: number | undefined = undefined;
    private line_fn: ((line: lines.Line) => void) | undefined = undefined;
    private close_fn: ((code: number) => void) | undefined = undefined;
    private read_id: number | undefined = undefined;
    private read_timer: number | undefined = undefined;

    // Takes the page's address.
    constructor(base_url: string) {
      this.token_url = new URL(constants.token_path, base_url).href;
      this.socket_url = socket_address(base_url, constants.console_path);
      this.token_timer = new WaitTimer(
        i18n("wire.what_token", this.token_url),
        constants.token_seconds,
      );
      this.open_timer = new WaitTimer(
        i18n("wire.what_open", this.socket_url),
        constants.open_seconds,
      );
    }

    // Closes the console socket with the normal code.
    console_close(): void {
      socket_made(this.socket, this.socket_url).close(constants.close_normal);
    }

    // Opens tty 0, sends one `console.input` message, or starts a read.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      const type = jslb.field_get(line[0], "type");
      if (type === constants.open_type) {
        this.open_start(line);
      } else if (type === constants.input_type) {
        const socket = socket_ready(this.socket, this.socket_url);
        socket.send(buffer_copy(blob_bytes(line)));
      } else if (type === constants.read_type) {
        this.read_start(line);
      } else {
        throw new Error(i18n("wire.console_type", type));
      }
    }

    // Sets the one receiver of `console.output` and of the replies.
    line_receive(fn: (line: lines.Line) => void): void {
      receiver_unset(this.line_fn, "line_receive");
      this.line_fn = fn;
    }

    // Sets the one receiver of the close of the console socket.
    close_receive(fn: (code: number) => void): void {
      receiver_unset(this.close_fn, "close_receive");
      this.close_fn = fn;
    }

    // Gives a message to the read, then relays it, which may move its buffer.
    message_take(message: Uint8Array): void {
      const reply = this.reader.message_take(message);
      const header = jslb.header_make(constants.output_type, {
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [jslb.blob_make(message)], {});
      receiver_known(this.line_fn, constants.output_type)(line);
      if (reply !== undefined) {
        this.read_answer(reply);
      }
    }

    // Takes the close of the socket, after which `console.open` opens anew.
    close_take(code: number): void {
      this.open_timer.timer_stop();
      this.socket = undefined;
      if (this.open_id !== undefined) {
        this.open_id = undefined;
        throw new Error(i18n("wire.open_closed", this.socket_url, code));
      }
      // A read still waiting is answered as timed out, so its sleep wakes.
      if (this.read_id !== undefined) {
        this.read_answer(this.reader.read_expire());
      }
      receiver_known(this.close_fn, "close")(code);
    }

    // Fetches the token and opens tty 0, answering `console.open` once open.
    private open_start(line: lines.Line): void {
      const id = request_id(line, constants.open_type);
      if (this.socket !== undefined || this.open_id !== undefined) {
        throw new Error(i18n("wire.open_twice", this.socket_url));
      }
      this.open_id = id;
      token_fetch(this.token_url, this.token_timer, (token) =>
        this.socket_start(id, token),
      );
    }

    // Opens the console socket with ttyd's subprotocol and listens to it.
    private socket_start(id: number, token: string): void {
      const socket = new WebSocket(this.socket_url, constants.subprotocol);
      socket.binaryType = "arraybuffer";
      socket.addEventListener("open", () => this.open_take(id, token));
      socket.addEventListener("message", (event) =>
        this.message_take(message_bytes(event)),
      );
      socket.addEventListener("close", (event) => this.close_take(event.code));
      this.open_timer.timer_start();
      this.socket = socket;
    }

    // Answers the `console.open` with the token once the socket is open.
    private open_take(id: number, token: string): void {
      this.open_timer.timer_stop();
      this.open_id = undefined;
      const header = jslb.header_make(constants.open_type, {
        reply: id,
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [], { token });
      receiver_known(this.line_fn, constants.open_type)(line);
    }

    // Starts a `console.read`, answered when `until` shows or its timer ends.
    private read_start(line: lines.Line): void {
      const id = request_id(line, constants.read_type);
      const payload = jslb.payload_of(line);
      const until = payload["until"];
      const seconds = payload["timeout_seconds"];
      if (typeof until !== "string") {
        throw new Error(i18n("wire.read_until"));
      }
      if (
        typeof seconds !== "number" ||
        seconds < 0 ||
        seconds * constants.second_ms > constants.timer_max_ms
      ) {
        throw new Error(i18n("wire.read_seconds", seconds));
      }
      this.reader.read_start(until);
      this.read_id = id;
      this.read_timer = setTimeout(
        () => this.read_expire(),
        seconds * constants.second_ms,
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
      const id = this.read_id as number;
      this.read_id = undefined;
      const header = jslb.header_make(constants.read_type, {
        reply: id,
        full: settings.names_full(),
      });
      const line = jslb.line_make(header, [], {
        text: reply.text,
        timed_out: reply.timed_out,
      });
      receiver_known(this.line_fn, constants.read_type)(line);
    }
  }
}

Object.freeze(wire);
