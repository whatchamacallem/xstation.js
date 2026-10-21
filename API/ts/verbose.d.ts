declare namespace verbose {
  // Writes one line to the ring of `verbose_ring` lines and hands it to
  // the sink.
  function log(text: string): void;

  // The last `count` lines of the ring, oldest first.
  function history_get(count: number): lines.VerboseLine[];

  // The one consumer of new lines: the thread's queue, which batches
  // them into `verbose.put` when `debug` is on.
  function sink_set(fn: (line: lines.VerboseLine) => void): void;
}
