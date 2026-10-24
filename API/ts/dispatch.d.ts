// The handlers of one thread by line type and version. A handler is
// synchronous: it returns the reply line, nothing for a notification, a sleep,
// or a failure, which is a reply its request gets before the queue fails
// with the failure's error, so an answer is never lost to the fault after it.
//
// `error_make` writes a cascade as nested `cause` entries: the error's own
// `message` and `stack`, then under `cause` its `cause`, and so on, the first
// failure innermost. A thrown value or a `cause` that is not an Error is
// written as its text with an empty stack. An `error` line that answers a
// line takes that line's name form, and one that answers none takes the form
// `settings.names_full()` picks, full names before the settings exist.
//
// The reply of a `Failure` is checked as a reply is: for a request it gets
// the request's `i` as its `r`, and for a line with no `i`, as a wake, it
// must already answer a request by its `r`.

declare namespace dispatch {
  // A reply line, or nothing for a notification.
  type Reply = lines.Line | undefined;

  // A sleep: the state, the requests submitted, the wake type once all reply.
  interface Sleep {
    state: unknown;
    wait_ids: number[];
    then_type: string;
  }

  // A reply the queue posts before it fails with `error`.
  interface Failure {
    reply: lines.Line;
    error: Error;
  }

  function task_sleep(
    state: unknown,
    wait_ids: number[],
    then_type: string,
  ): Sleep;

  function failure_make(reply: lines.Line, error: Error): Failure;

  type Handler = (line: lines.Line) => Reply | Sleep | Failure;

  // Registers `fn` for one type and version. A second registration throws.
  function handler_register(type: string, version: number, fn: Handler): void;

  // Calls the handler by type and version. Throws on an unknown pair.
  function line_dispatch(line: lines.Line): Reply | Sleep | Failure;

  // Builds a reply to `line` with `r` set and the payload and blobs given.
  function reply_make(
    line: lines.Line,
    payload: { [key: string]: unknown },
    blobs?: lines.BlobHeader[],
  ): lines.Line;

  // The one `error` line for a throw, its cascade under `cause`.
  function error_make(
    line: lines.Line | undefined,
    error: unknown,
  ): lines.Line;

  // The cascade of an error as the payload `error_make` writes.
  function cause_make(error: unknown): lines.ErrorCause;

  // The next `i` for the port, from 102: 101 is the first line's.
  function id_next(port: string): number;
}
