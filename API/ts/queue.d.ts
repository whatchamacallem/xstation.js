// The task manager of one thread, the one synchronization tool: one line
// dispatched at a time, a handler run to completion, sleeping tasks woken by a
// line of their `then_type` once every awaited reply is in. The lines of each
// input run in the order they come, in both modes, and a wake runs in its last
// reply's place, before every line that came after that reply.
//
// A handler's `dispatch.Failure` is answered first: its reply is posted, then
// the queue fails with its error. A handler that submitted requests it does
// not sleep on fails with `queue.wait_missing`, that error its `cause`, so its
// own message is kept. An `error` line stops a queue with `queue.error_line`,
// the line's `cause` entries rebuilt as Errors: the sender's whole cascade.
//
// The audit, attached in debug mode alone: before each line it sends but to
// the server, and each it receives from a port that is no queue, `http`,
// `media`, `console` or `dom`, it posts an `audit.line` to the owner of
// `audit.`, its blob the line's `jslb.line_json` with the `Authorization` of
// `http.request` and the `token` of a `console.open` reply masked; at each
// sleep an `audit.note` of the replies' ids and the wake's type. Neither is
// posted before `audit_open`. A type under `audit.` is the audit's own: such
// a line is never recorded, and a sleep with such a wake is never noted.

declare namespace queue {
  // The owners a line can have: the threads, the server and the ports.
  type ThreadName =
    "ui" | "ai" | "server" | "http" | "media" | "console" | "dom";

  // A port carries lines one way each direction, in order.
  interface Port {
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Same thread: `line_post` hands the line to the receiver of the far end.
  class LocalPort implements Port {
    // Links the far end given back to this port, else the port is its own.
    constructor(far?: LocalPort);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // A MessagePort with the blob buffers in the transfer list.
  class ThreadPort implements Port {
    constructor(port: MessagePort);
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Type prefix to owner, where the longest prefix that matches wins.
  type OwnerTable = { [prefix: string]: ThreadName };

  // The blob bytes a held line counts: its blobs whose `d` is bytes.
  function line_bytes(line: lines.Line): number;

  class TaskQueue {
    // `synchronous` runs every task held before the next input is read.
    constructor(thread: ThreadName, owners: OwnerTable, synchronous: boolean);
    // Connects the port that reaches the named thread and receives from it.
    port_add(thread: ThreadName, port: Port): void;
    // Submits a request to `owner`, else the table's. Returns its `i`.
    task_submit(line: lines.Line, owner?: ThreadName): number;
    // Posts a notification to `owner`, else the table's.
    line_notify(line: lines.Line, owner?: ThreadName): void;
    // Passes a line another thread owns to that owner's port unchanged.
    line_forward(line: lines.Line): void;
    // The number of tasks waiting, running and sleeping.
    depth(): number;
    // Installs the reader of the settings whose `blob_max` bounds what it holds.
    limit_attach(settings_get: (id: string) => unknown): void;
    // Records and notes as the header says, held until `audit_open`.
    audit_attach(): void;
    // Posts the held records and notes in order, and each later one at once.
    audit_open(): void;
  }
}
