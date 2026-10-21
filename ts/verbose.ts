// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The verbose lines of one thread, which has no verbose level: the ring of
// the latest lines, trimmed to the `verbose_ring` setting from the first line
// on, and the one sink that receives every line.

namespace verbose {
  // The constants of this module.
  const constants = Object.freeze({
    ring_setting: "verbose_ring",
  });

  // The ring and the sink of the verbose lines of one thread.
  export class LineRing {
    private readonly ring: lines.VerboseLine[] = [];
    private sink: ((line: lines.VerboseLine) => void) | undefined;
    private readonly size_get: () => unknown;

    // Takes the reader of the ring size, which is read again for each line.
    constructor(size_get: () => unknown) {
      this.size_get = size_get;
    }

    // Writes a line to the ring, trimmed to the size, then to the sink.
    log(text: string): void {
      const size = this.ring_size();
      const line = Object.freeze({ at: utility.time_now(), text });
      this.ring.push(line);
      this.ring_trim(size);
      const sink = this.sink;
      if (sink !== undefined) {
        sink(line);
      }
    }

    // The last lines of the ring, as many as asked for, oldest first.
    history_get(count: number): lines.VerboseLine[] {
      if (!Number.isInteger(count) || count < 0) {
        throw new Error(i18n("verbose.count_invalid", count));
      }
      return this.ring.slice(Math.max(0, this.ring.length - count));
    }

    // Sets the one sink, which gets every line written after this call.
    sink_set(fn: (line: lines.VerboseLine) => void): void {
      if (this.sink !== undefined) {
        throw new Error(i18n("verbose.sink_twice"));
      }
      this.sink = fn;
    }

    // The ring size from the settings, which must be a whole number of lines.
    private ring_size(): number {
      const size = this.size_get();
      if (typeof size !== "number" || !Number.isInteger(size) || size < 0) {
        throw new Error(i18n("verbose.ring_invalid", size));
      }
      return size;
    }

    // Drops the oldest lines until the ring holds at most the size.
    private ring_trim(size: number): void {
      if (this.ring.length > size) {
        this.ring.splice(0, this.ring.length - size);
      }
    }
  }

  // The lines of this thread, whose ring size is the `verbose_ring` setting.
  const thread_ring = new LineRing(() =>
    settings.settings_get(constants.ring_setting)
  );

  // Writes one line to the ring and hands it to the sink.
  export function log(text: string): void {
    thread_ring.log(text);
  }

  // The last `count` lines of the ring, oldest first.
  export function history_get(count: number): lines.VerboseLine[] {
    return thread_ring.history_get(count);
  }

  // Sets the one consumer of new lines, which is the queue of the thread.
  export function sink_set(fn: (line: lines.VerboseLine) => void): void {
    thread_ring.sink_set(fn);
  }
}

Object.freeze(verbose);
