declare namespace wire {
  // The port to the server over ttyd's WebSocket. Fetches `/token`, opens
  // `/ws` with subprotocol `tty`, sends ttyd's first JSON message, skips
  // the title and preferences, strips and adds the `'0'`, feeds the
  // decoder, and on upload waits for `bufferedAmount` under one chunk.
  class WirePort implements queue.Port {
    constructor(
      base_url: string,
      chunk_bytes: number,
      decoder: jslb.LineDecoder
    );
    // Resolves with `hello` once it arrives. Rejects on any failure.
    wire_open(): Promise<lines.Line>;
    // Closes with 1000. Resolves once the socket reports closed.
    wire_close(): Promise<void>;
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
    // Called once, with the close code and reason, when the socket ends
    // for any reason other than `wire_close`.
    close_receive(fn: (code: number, reason: string) => void): void;
    // ttyd's title and preferences, kept for the page to show.
    title: string;
    preferences: unknown;
  }
}
