// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The verbose lines of one thread: the level, the ring of the latest lines
// and the one sink that receives each line the level keeps.

namespace verbose {
  // The constants of this module.
  const constants = Object.freeze({
    level_max: 2,
    ring_setting: "verbose_ring",
  });

  // The level, the ring and the sink of the verbose lines of one thread.
  export class LineRing {
    private level: number | undefined;
    private readonly ring: lines.VerboseLine[] = [];
    private sink: ((line: lines.VerboseLine) => void) | undefined;
    private readonly size_get: () => unknown;

    // Takes the reader of the ring size, which is used once a level is set.
    constructor(size_get: () => unknown) {
      this.size_get = size_get;
    }

    // Sets the level and trims the ring to the size the settings give.
    level_set(level: number): void {
      this.level_check(level);
      const size = this.ring_size();
      this.level = level;
      this.ring_trim(size);
    }

    // Writes a line to the ring and the sink unless it is above the level.
    log(level: number, text: string): void {
      this.level_check(level);
      const current = this.level;
      if (current !== undefined && level > current) {
        return;
      }
      const size = current === undefined ? undefined : this.ring_size();
      const line = Object.freeze({ at: utility.time_now(), level, text });
      this.ring.push(line);
      if (size !== undefined) {
        this.ring_trim(size);
      }
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

    // Throws unless the level is a whole number from 0 to the highest.
    private level_check(level: number): void {
      if (
        !Number.isInteger(level) ||
        level < 0 ||
        level > constants.level_max
      ) {
        throw new Error(
          i18n("verbose.level_invalid", level, constants.level_max)
        );
      }
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

  // Sets the level: 0 only what must be said, 1 progress, 2 everything.
  export function level_set(level: number): void {
    thread_ring.level_set(level);
  }

  // Writes one line to the ring and the sink unless it is above the level.
  export function log(level: number, text: string): void {
    thread_ring.log(level, text);
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
