// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The ports over ttyd's WebSocket: the wire to the server on tty 1, which
// carries JSLB, and the console on tty 0, which relays ttyd's own protocol.
// One of the four modules that turn platform events into lines.

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
    columns: 80,
    rows: 24,
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
    // Hello once the socket opens: 120 s, a default kept from earlier code.
    hello_seconds: 120,
    // A drained socket buffer: 120 s, a default kept from the earlier code.
    drain_seconds: 120,
    // A poll of the socket buffer: 0 ms, a default chosen by its writer.
    poll_ms: 0,
    // The longest hello phase line: 10 MiB, the maintainer's size.
    hello_line_max: 10485760,
    // The largest hello phase blob: none, as hello carries no blob.
    hello_blob_max: 0,
    // The largest hello phase message: 10 MiB, the maintainer's size.
    hello_message_max: 10485760,
    // The hello phase blob bytes held in memory: none.
    hello_overflow_bytes: 0,
    hello_type: "hello",
    error_type: "error",
    open_type: "console.open",
    input_type: "console.input",
    output_type: "console.output",
    read_type: "console.read",
    debug_setting: "debug",
    chunk_setting: "chunk_bytes",
    line_setting: "line_max",
    blob_setting: "blob_max",
    message_setting: "message_max",
    overflow_setting: "overflow_bytes",
    queue_setting: "queue_max",
  });

  // Reads a cache file: `length` bytes from `offset`, fewer only at its end.
  type CacheRead = (
    handle: string,
    offset: number,
    length: number,
  ) => Uint8Array;

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

  // A cache file of an encoded line, whose ranges must be read whole.
  class CachePiece {
    readonly size: number;
    private readonly handle: string;
    private readonly read: CacheRead;

    // Takes the handle, the size its blob header gives, and the reader.
    constructor(handle: string, size: number, read: CacheRead) {
      this.handle = handle;
      this.size = size;
      this.read = read;
    }

    // The bytes of the range, which must number exactly its length.
    range_read(offset: number, length: number): Uint8Array {
      const bytes = this.read(this.handle, offset, length);
      if (bytes.length !== length) {
        throw new Error(
          i18n(
            "wire.handle_differs",
            this.handle,
            offset,
            length,
            bytes.length,
          ),
        );
      }
      return bytes;
    }
  }

  // The encoded piece `number` of a line, a cache handle read by `read`.
  function piece_make(
    line: lines.Line,
    number: number,
    data: Uint8Array | string,
    read: CacheRead | undefined,
  ): MemoryPiece | CachePiece {
    if (typeof data !== "string") {
      return new MemoryPiece(data);
    }
    if (read === undefined) {
      throw new Error(i18n("wire.handle_unsent", data));
    }
    const blob = line[number] as lines.BlobHeader;
    return new CachePiece(data, jslb.field_get(blob, "size") as number, read);
  }

  // Encoded lines waiting to go to ttyd as input frames, bounded in bytes.
  export class FrameQueue {
    private readonly chunk_bytes: number;
    private readonly message_max: number;
    private readonly queue_max: number;
    private readonly pieces: (MemoryPiece | CachePiece)[] = [];
    private offset = 0;
    // The bytes of the lines queued that no frame has taken yet.
    private held = 0;

    // Takes the bytes of a frame with its kind, of a message, of all held.
    constructor(chunk_bytes: number, message_max: number, queue_max: number) {
      if (!Number.isInteger(chunk_bytes) || chunk_bytes < 2) {
        throw new Error(i18n("wire.chunk_invalid", chunk_bytes));
      }
      this.chunk_bytes = chunk_bytes;
      this.message_max = message_max;
      this.queue_max = queue_max;
    }

    // Queues a line, refused whole over `message_max` or `queue_max`.
    line_add(line: lines.Line, read: CacheRead | undefined): void {
      const type = jslb.field_get(line[0], "type");
      const encoded = jslb.line_encode(line);
      const pieces: (MemoryPiece | CachePiece)[] = [];
      let bytes = 0;
      for (let number = 0; number < encoded.length; number += 1) {
        const piece = piece_make(line, number, encoded[number], read);
        bytes += piece.size;
        pieces.push(piece);
      }
      if (bytes > this.message_max) {
        throw new Error(
          i18n("wire.message_over", type, bytes, this.message_max),
        );
      }
      if (this.held + bytes > this.queue_max) {
        throw new Error(
          i18n("wire.queue_over", type, bytes, this.held, this.queue_max),
        );
      }
      // A piece of no bytes, an empty blob, sends no frame.
      this.pieces.push(...pieces.filter((piece) => piece.size > 0));
      this.held += bytes;
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
      const size = Math.min(piece.size - this.offset, this.chunk_bytes - 1);
      const buffer = new ArrayBuffer(size + 1);
      const frame = new Uint8Array(buffer);
      frame[0] = constants.input_kind;
      frame.set(piece.range_read(this.offset, size), 1);
      this.offset += size;
      this.held -= size;
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

  // The parts of the wire port that the settings size, built after hello.
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
    private readonly hello_timer: WaitTimer;
    private readonly drain_timer: WaitTimer;
    // The hello phase decoder until the settings size one, then that one.
    private decoder: jslb.LineDecoder;
    private parts: SettingsParts | undefined = undefined;
    private cache_read: CacheRead | undefined = undefined;
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

    // Takes the page's address, the sink of streamed blobs, the settings.
    constructor(
      base_url: string,
      sink: jslb.BlobSink,
      settings_get: (id: string) => unknown,
    ) {
      this.sink = sink;
      this.settings_get = settings_get;
      this.decoder = new jslb.LineDecoder(
        constants.hello_line_max,
        constants.hello_blob_max,
        constants.hello_message_max,
        constants.hello_overflow_bytes,
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
      this.hello_timer = new WaitTimer(
        i18n("wire.what_hello"),
        constants.hello_seconds,
      );
      this.drain_timer = new WaitTimer(
        i18n("wire.what_drain", this.socket_url),
        constants.drain_seconds,
      );
    }

    // Fetches the token, opens the socket and passes `hello` to `fn`.
    wire_open(fn: (hello: lines.Line) => void): void {
      this.hello_receive(fn);
      token_fetch(this.token_url, this.token_timer, (token) =>
        this.socket_start(token),
      );
    }

    // Closes the socket with the normal code, which ends the server.
    wire_close(): void {
      this.port_shut();
    }

    // Encodes the line and sends it as input frames, once `hello` is in.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      if (!this.hello_seen) {
        throw new Error(
          i18n("wire.post_early", jslb.field_get(line[0], "type")),
        );
      }
      this.parts_live().frames.line_add(line, this.cache_read);
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

    // Sets the one reader of cache files, which sends a blob held as a handle.
    cache_attach(read: CacheRead): void {
      receiver_unset(this.cache_read, "cache_attach");
      this.cache_read = read;
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
        this.output_take(body);
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
      // The error line is the fault, which the queue raises, so none is added.
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

    // Sends ttyd's first message once the socket is open, then awaits hello.
    private open_take(socket: WebSocket, token: string): void {
      this.open_timer.timer_stop();
      socket.send(start_message(token));
      this.hello_timer.timer_start();
    }

    // Takes a message of the socket, and closes the port when anything throws.
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

    // Decodes output, passes the lines on, then raises any fault held.
    private output_take(body: Uint8Array): void {
      const hello_phase = !this.hello_seen;
      // After hello the settings size the decoder, built here at the latest.
      if (!hello_phase) {
        this.parts_live();
      }
      const decoder = this.decoder;
      for (const line of decoder.bytes_feed(body)) {
        // Bytes after hello are the settings decoder's, so none may come yet.
        if (hello_phase && this.hello_seen) {
          throw new Error(i18n("wire.hello_trailing"));
        }
        this.line_take(line);
      }
      // Empty bytes finish no line and raise a fault met after the lines.
      decoder.bytes_feed(new Uint8Array(0));
      if (hello_phase && this.hello_seen && !decoder.idle()) {
        throw new Error(i18n("wire.hello_trailing"));
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
      } else if (type === constants.hello_type) {
        throw new Error(i18n("wire.hello_twice"));
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
      const message_max = this.setting_number(constants.message_setting);
      const frames = new FrameQueue(
        chunk_bytes,
        message_max,
        this.setting_number(constants.queue_setting),
      );
      this.decoder = new jslb.LineDecoder(
        this.setting_number(constants.line_setting),
        this.setting_number(constants.blob_setting),
        message_max,
        this.setting_number(constants.overflow_setting),
        this.sink,
      );
      const parts = { chunk_bytes, frames };
      this.parts = parts;
      return parts;
    }

    // A number of the settings, which the server checked before hello.
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
    private readonly settings_get: (id: string) => unknown;
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

    // Takes the page's address and the reader of the settings.
    constructor(base_url: string, settings_get: (id: string) => unknown) {
      this.settings_get = settings_get;
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
        full: this.names_full(),
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
      const fn = this.close_fn;
      if (fn !== undefined) {
        fn(code);
      }
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
        full: this.names_full(),
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
        !Number.isFinite(seconds) ||
        seconds < 0
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
      const id = this.read_id;
      if (id === undefined) {
        throw new Error(i18n("wire.read_none"));
      }
      this.read_id = undefined;
      const header = jslb.header_make(constants.read_type, {
        reply: id,
        full: this.names_full(),
      });
      const line = jslb.line_make(header, [], {
        text: reply.text,
        timed_out: reply.timed_out,
      });
      receiver_known(this.line_fn, constants.read_type)(line);
    }

    // Whether lines use full header names, which is debug mode.
    private names_full(): boolean {
      return this.settings_get(constants.debug_setting) as boolean;
    }
  }
}

Object.freeze(wire);
