declare namespace verbose {
  // Writes a line to the ring of `verbose_ring` lines, then to the sink.
  function log(text: string): void;

  // The last `count` lines of the ring, oldest first.
  function history_get(count: number): lines.VerboseLine[];

  // The one sink, the thread's queue, batching `verbose.put` in debug mode.
  function sink_set(fn: (line: lines.VerboseLine) => void): void;
}
