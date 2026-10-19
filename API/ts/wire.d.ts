declare namespace wire {
  // The port to the server over ttyd's WebSocket on tty 1. Fetches
  // `/token`, opens `/ws` with subprotocol `tty`, sends ttyd's first JSON
  // message, skips the title and preferences, strips and adds the '0',
  // feeds the decoder, and on upload waits for `bufferedAmount` under
  // one chunk. One of the four modules allowed platform callbacks.
  class WirePort implements queue.Port {
    constructor(
      base_url: string,
      chunk_bytes: number,
      decoder: jslb.LineDecoder
    );
    // Opens the socket; `fn` gets `hello` once it arrives.
    wire_open(fn: (hello: lines.Line) => void): void;
    // Closes with 1000.
    wire_close(): void;
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // Called once when the socket ends for any reason other than
    // `wire_close`, with the close code and whether an `error` line was
    // received before it; without one the fault names the code.
    close_receive(fn: (code: number, had_error: boolean) => void): void;
    // ttyd's title and preferences, kept for the overlay.
    title: string;
    preferences: unknown;
  }

  // The port to the console on tty 0: `/ws?arg=console`, no JSLB. Each
  // message of ttyd's protocol received becomes one `console.output`
  // line with the bytes as blob "1"; each `console.input` line posted
  // sends its blob as one message; a `console.read` line is answered
  // once `until` appears in the output or its timer expires.
  class ConsolePort implements queue.Port {
    constructor(base_url: string);
    console_open(fn: () => void): void;
    console_close(): void;
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // Called once with the close code; the AI worker pushes
    // `console.exit`.
    close_receive(fn: (code: number) => void): void;
  }
}
