declare namespace dispatch {
  // A handler gets the line and returns the reply without a header, or
  // nothing for a notification. On the WASM thread a handler is
  // synchronous; on the AI thread it may return a promise, and every
  // database access inside it is a task of its own.
  type Reply = { [key: string]: unknown } | undefined;
  type Handler = (line: lines.Line) => Reply | Promise<Reply>;

  function handler_register(type: string, version: number, fn: Handler): void;

  // Calls the handler by type and version. Throws on an unknown pair.
  function line_dispatch(line: lines.Line): Reply | Promise<Reply>;

  function reply_make(
    line: lines.Line,
    payload: { [key: string]: unknown },
    blobs?: lines.BlobHeader[]
  ): lines.Line;

  function error_make(line: lines.Line | undefined, error: Error): lines.Line;

  // The next `i` for the port, from 1.
  function id_next(port: string): number;
}
