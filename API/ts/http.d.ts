// The port that answers `http.request` lines with `http.response`, or
// `error` on a non-2xx status, a failed fetch, or `timeout_seconds`
// expiring, a timer. One fetch per line. A JSON body is read by
// `jslb.json_decode`, the one door for bad numbers. One of the four modules
// allowed platform callbacks; any thread may own one.

declare namespace http {
  class HttpPort implements queue.Port {
    constructor(timeout_seconds: number);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }
}
