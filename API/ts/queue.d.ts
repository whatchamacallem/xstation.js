// The task manager of one thread, the one synchronization tool: one line
// dispatched at a time, a handler run to completion, sleeping tasks woken by a
// line of their `then_type` once every awaited reply is in.
//
// The lines of each input run in the order they come, in both modes, and a
// wake runs in its last reply's place, before every line that came after that
// reply. The blob bytes it holds are bounded by `blob_max`, the largest
// database: a blob streamed to a cache file counts nothing, so a database of
// `blob_max` with its cache files passes through.
//
// A handler's `dispatch.Failure` is answered first: its reply is posted, then
// the queue fails with its error. A handler that submitted requests it does
// not sleep on fails with `queue.wait_missing`, that error its `cause`, so its
// own message is kept. An `error` line stops a queue with `queue.error_line`,
// the line's `cause` entries rebuilt as Errors, so the sender's cascade is
// kept whole.
//
// Two linked `LocalPort`s join two queues of one thread, so a line posted at
// one end runs on the other queue within the post.

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

  // Whether a verbose line of the text fits one `verbose.put` of the thread.
  function entry_fits(
    thread: "ui" | "ai",
    text: string,
    line_max: number,
  ): boolean;

  // The verbose lines of a thread waiting to go out as `verbose.put` lines.
  class VerboseBatch {
    // Takes the thread, the reader of the settings and that of debug mode.
    constructor(
      thread: ThreadName,
      settings_get: (id: string) => unknown,
      debug_on: () => boolean,
    );
    // Keeps a line in debug mode while no batch is going out.
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
    // Installs the verbose sink, its settings and the reader of debug mode.
    sink_attach(
      sink_set: (fn: (line: lines.VerboseLine) => void) => void,
      settings_get: (id: string) => unknown,
      debug_on: () => boolean,
    ): void;
  }
}
