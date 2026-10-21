declare namespace dispatch {
  // A handler gets the line and returns the reply without a header,
  // nothing for a notification, or a sleep. It is synchronous.
  type Reply = { [key: string]: unknown } | undefined;

  // A sleep: the handler's state, the ids of the requests it submitted,
  // and the type of the line the queue enqueues, with a `lines.Wake`
  // payload, once every reply has arrived.
  interface Sleep {
    state: unknown;
    wait_ids: number[];
    then_type: string;
  }

  function task_sleep(
    state: unknown,
    wait_ids: number[],
    then_type: string,
  ): Sleep;

  type Handler = (line: lines.Line) => Reply | Sleep;

  // Registers `fn` for one type and version. A second registration of
  // the same pair throws.
  function handler_register(type: string, version: number, fn: Handler): void;

  // Calls the handler by type and version. Throws on an unknown pair.
  function line_dispatch(line: lines.Line): Reply | Sleep;

  // Builds a reply to `line` with `r` set and the payload and blobs given.
  function reply_make(
    line: lines.Line,
    payload: { [key: string]: unknown },
    blobs?: lines.BlobHeader[],
  ): lines.Line;

  // The one `error` line for a throw: `message`, `stack`, `r` when the
  // request had `i`.
  function error_make(line: lines.Line | undefined, error: Error): lines.Line;

  // The next `i` for the port, from 1.
  function id_next(port: string): number;
}
