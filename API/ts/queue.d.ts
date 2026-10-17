declare namespace queue {
  type ThreadName = "ui" | "ai" | "wasm" | "server";

  // A port carries lines one way each direction, in order.
  interface Port {
    line_post(line: lines.Line, transfer: ArrayBuffer[]): void;
    line_receive(fn: (line: lines.Line) => void): void;
  }

  // Same thread: `line_post` calls the receiver at once.
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

  // Type prefix to owner thread: `"kv."` to `"wasm"` on the AI thread,
  // `"ai."` to `"ai"` on the UI thread, and so on.
  type OwnerTable = { [prefix: string]: ThreadName };

  class TaskQueue {
    constructor(thread: ThreadName, owners: OwnerTable);
    // Connects the port that reaches the named thread.
    port_add(thread: ThreadName, port: Port): void;
    // Runs the handler here when this thread owns the type, else posts
    // to the owner and resolves with its reply. The caller's blob
    // buffers are detached after the call.
    task_submit(line: lines.Line): Promise<lines.Line>;
    // Posts a notification; nothing resolves.
    line_notify(line: lines.Line): void;
    // The number of tasks waiting and running, for the stress test.
    depth(): number;
  }
}
