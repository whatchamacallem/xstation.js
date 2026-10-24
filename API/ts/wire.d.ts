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

declare namespace wire {
  // Encoded lines waiting to go to ttyd as input frames, bounded in bytes.
  class FrameQueue {
    constructor(chunk_bytes: number, line_max: number, blob_max: number);
    // Queues a line, refused over `line_max` or with blobs over `blob_max`.
    line_add(line: lines.Line): void;
    // Whether a frame waits to be sent.
    frames_left(): boolean;
    // The next frame: the input kind, then the next bytes of the first piece.
    frame_next(): ArrayBuffer;
  }

  // The reads of the console output, each decoded from its own start.
  class ConsoleReader {
    // Takes a message of ttyd's, ignored unless a read waits that it may end.
    message_take(message: Uint8Array): lines.ConsoleReadReply | undefined;
    // Starts a read of the output from now on, until `until` shows in it.
    read_start(until: string): void;
    // Ends the waiting read when its timer expires or its socket closes.
    read_expire(): lines.ConsoleReadReply;
  }

  // The port to the server on tty 1.
  class WirePort implements queue.Port {
    constructor(
      base_url: string,
      sink: jslb.BlobSink,
      settings_get: (id: string) => unknown,
    );
    // Fetches the token, opens the socket, gives the first line to `fn`.
    wire_open(fn: (first: lines.Line) => void): void;
    // Closes with 1000, which ends the server.
    wire_close(): void;
    // Sends the line, awaits the server's end of the socket, calls `fn`.
    wire_end(line: lines.Line, fn: () => void): void;
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // Called once when the socket ends but by `wire_close` or `wire_end`.
    close_receive(fn: (code: number, had_error: boolean) => void): void;
    // Sets the one receiver of the first line, which `wire_open` does.
    first_receive(fn: (first: lines.Line) => void): void;
    // Takes one message of ttyd's: keeps a title or preferences, or decodes.
    message_take(message: Uint8Array): void;
    // The close: what `wire_end` awaits, else a fault without an error line.
    close_take(code: number): void;
    // ttyd's title and preferences.
    title: string;
    preferences: unknown;
  }

  // The port to the console on tty 0, no JSLB: one line per message.
  class ConsolePort implements queue.Port {
    constructor(base_url: string);
    // Ends tty 0, whose end the close function hears.
    console_close(): void;
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // Called once with the close code. The AI worker pushes `console.exit`.
    close_receive(fn: (code: number) => void): void;
    // Gives a message to the read, then relays it as `console.output`.
    message_take(message: Uint8Array): void;
    // Takes the close of the socket, after which `console.open` opens anew.
    close_take(code: number): void;
  }
}
