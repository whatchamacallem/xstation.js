declare namespace http {
  // The port that answers `http.request` lines with `http.response`, or
  // `error` on a non-2xx status, a failed fetch, or `timeout_seconds`
  // expiring, a timer. One fetch per line. One of the four modules
  // allowed platform callbacks; any thread may own one.
  class HttpPort implements queue.Port {
    constructor(timeout_seconds: number);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }
}
