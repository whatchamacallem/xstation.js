// The port that answers `http.request` lines with an `http.request` reply
// holding `lines.HttpResponse`, or `error` on a non-2xx status, a failed
// fetch, or `timeout_seconds` expiring, a timer. One fetch per line. A JSON
// body is read by `jslb.json_decode`, the one door for bad numbers. One of
// the four modules allowed platform callbacks; any thread may own one.

declare namespace http {
  // What one fetch needs: the url and its options.
  interface FetchArguments {
    url: string;
    init: RequestInit;
  }

  // A response read to its end: status, header values and body text.
  interface HttpAnswer {
    status: number;
    headers: lines.HttpRequest["headers"];
    text: string;
  }

  // The steps from one request line to its fetch and to its reply lines.
  class HttpExchange {
    // Takes an `http.request` line that has an id, no blobs and valid fields.
    constructor(line: lines.Line);
    // The arguments of the one fetch: `json` as the body, else `body` as is.
    arguments_make(): FetchArguments;
    // The reply to a response: its lines, or an error for a failed status.
    answer_reply(answer: HttpAnswer): lines.Line;
    // The error reply to a fetch or a body read that rejected.
    failure_reply(cause: unknown): lines.Line;
    // The error reply to a request that outlived its timer.
    timeout_reply(timeout_seconds: number): lines.Line;
  }

  class HttpPort implements queue.Port {
    constructor(timeout_seconds: number);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }
}
