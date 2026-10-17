declare namespace log {
  // Installs the capture of `console.*`, `self.onerror` and
  // `unhandledrejection` on this thread. `forward` receives batches to
  // send on as `log.put`; `fault` receives the first uncaught error.
  function log_install(
    thread: lines.Fault["thread"],
    forward: (lines: lines.LogLine[]) => void,
    fault: (fault: lines.Fault) => void
  ): void;

  function log_write(level: number, text: string): void;

  function log_tail(count: number): lines.LogLine[];

  // Builds a `fault` payload from any thrown value, with its cause chain
  // in the stack text.
  function fault_make(thread: lines.Fault["thread"], error: unknown): lines.Fault;
}
