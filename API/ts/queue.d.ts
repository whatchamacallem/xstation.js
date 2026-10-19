declare namespace queue {
  // The owners a line can have: the two threads, the server, and the
  // ports that turn a platform event into a reply line.
  type ThreadName =
    | "ui"
    | "ai"
    | "server"
    | "http"
    | "media"
    | "console"
    | "dom";

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

  // Type prefix to owner: `"kv."` to `"ai"` on the UI thread, `"kv."`
  // to `"server"` on the AI thread for the forwarded form, and so on.
  type OwnerTable = { [prefix: string]: ThreadName };

  // The task manager of one thread: one line dispatched at a time, a
  // handler run to completion, sleeping tasks woken by a line of their
  // `then_type` once every awaited reply is in. Every submit, dispatch,
  // sleep, wake and reply is a verbose line at level 2.
  class TaskQueue {
    // `synchronous` is the debug mode of 4.2: the queue runs every task
    // it holds to completion before reading the next input from a port.
    constructor(thread: ThreadName, owners: OwnerTable, synchronous: boolean);
    // Connects the port that reaches the named thread.
    port_add(thread: ThreadName, port: Port): void;
    // Submits a request. Returns its `i`; the reply arrives as a wake of
    // the handler that sleeps on it. The caller's blob buffers are
    // detached after the call.
    task_submit(line: lines.Line): number;
    // Posts a notification; nothing answers it.
    line_notify(line: lines.Line): void;
    // Passes a line received from one port, whose owner is another
    // thread, to that owner's port unchanged.
    line_forward(line: lines.Line): void;
    // The number of tasks waiting, running and sleeping, for the stress
    // test and the synchronous mode check.
    depth(): number;
  }
}
