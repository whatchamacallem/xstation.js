// The task manager of one thread, the one synchronization tool: its ports,
// the owner table, one line dispatched at a time, a handler run to
// completion, sleeping tasks woken by a line of their `then_type` once every
// awaited reply is in, the verbose sink of the thread, and in debug mode a
// verbose line for every submit, dispatch, sleep, wake and reply.
//
// The blob bytes it holds are bounded by `blob_max`, the largest database:
// a held line counts the blobs it holds in memory, `line_bytes`, so a blob
// streamed to a cache file counts nothing and a database of `blob_max` with
// its cache files passes through as long as the lines' bytes are streamed.
//
// A handler's `dispatch.Failure` is answered first: its reply is posted, then
// the queue fails with its error. When that handler submitted requests it
// does not sleep on, the queue fails with `queue.wait_missing` whose `cause`
// is the failure's error, so the handler's own message is kept.
//
// An `error` line that reaches a queue stops it with `queue.error_line`,
// which names the line's `message` and `stack` and holds the line's own
// `cause` entries rebuilt as Errors under its `cause`, so the sender's
// cascade is kept whole.
//
// A wake line is built in the form `settings.names_full()` picks.

declare namespace queue {
  // The owners a line can have: the threads, the server and the ports.
  type ThreadName =
    "ui" | "ai" | "server" | "http" | "media" | "console" | "dom";

  // A port carries lines one way each direction, in order.
  interface Port {
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Same thread: `line_post` queues the line on the receiver's queue.
  class LocalPort implements Port {
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

  // Whether a verbose line of the text fits one `verbose.put` of the thread.
  function entry_fits(
    thread: "ui" | "ai",
    text: string,
    line_max: number,
  ): boolean;

  // The verbose lines of a thread waiting to go out as `verbose.put` lines.
  class VerboseBatch {
    constructor(thread: ThreadName, settings_get: (id: string) => unknown);
    // Keeps a line while `debug` is true and no batch is going out.
    line_add(line: lines.VerboseLine): void;
    // Posts the kept lines in order as `verbose.put` lines below `line_max`.
    batch_send(post: (line: lines.Line) => void): void;
  }

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
    // Installs the verbose sink and the settings that bound and trace it.
    sink_attach(
      sink_set: (fn: (line: lines.VerboseLine) => void) => void,
      settings_get: (id: string) => unknown,
    ): void;
  }
}
