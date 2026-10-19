declare namespace verbose {
  // Sets the level: 0 only what must be said, 1 progress, 2 everything,
  // including every task queue event and every substrate call.
  function level_set(level: number): void;

  // Writes one line to the ring of `verbose_ring` lines and hands it to
  // the sink. Lines above the level are not written.
  function log(level: number, text: string): void;

  // The last `count` lines of the ring, oldest first.
  function history_get(count: number): lines.VerboseLine[];

  // The one consumer of new lines: the thread's queue, which batches
  // them into `verbose.put` when `debug` and `verbose_forward` are on.
  function sink_set(fn: (line: lines.VerboseLine) => void): void;
}
