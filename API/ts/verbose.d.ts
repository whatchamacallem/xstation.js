declare namespace verbose {
  // The ring and the sink of the verbose lines of one thread.
  class LineRing {
    // Takes the reader of the ring size, which is read again for each line.
    constructor(size_get: () => unknown);
    // Writes a line to the ring, trimmed to the size, then to the sink.
    log(text: string): void;
    // The last lines of the ring, as many as asked for, oldest first.
    history_get(count: number): lines.VerboseLine[];
    // Sets the one sink, which gets every line written after this call.
    sink_set(fn: (line: lines.VerboseLine) => void): void;
  }

  // Writes a line to the ring of `verbose_ring` lines, then to the sink.
  function log(text: string): void;

  // The last `count` lines of the ring, oldest first.
  function history_get(count: number): lines.VerboseLine[];

  // The one sink, the thread's queue, batching `verbose.put` in debug mode.
  function sink_set(fn: (line: lines.VerboseLine) => void): void;
}
