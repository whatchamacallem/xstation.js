// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the wire port's end, group C, on the headless page that ttyd
// serves: `wire_end` on an open socket, which sends its line and calls its
// function at the server's close, and `wire_end` on a socket already
// closed, by the server or by `wire_close`, which calls its function at once
// and sends nothing. Each point opens a real `wire.WirePort` at the page's
// address to the block's own server through ttyd's tty 1, which runs the
// echo main loop, its replies streaming into a real, empty
// `substrate.CacheFiles([])`. A point waits for its server's close before
// the next point opens a port, so that the next server finds the root's lock
// free; the last point closes its port itself, a close the port reports to
// no one. The block writes its own points as they arrive, through
// `block_start`, its plan the number of points, and `block_end` of the
// runner it is handed. A point with no verdict within the gold's
// `point_seconds` fails, naming what it waited for, and a point that comes
// to a second verdict throws. The lines the points send and expect and the
// close code are the gold of test_settings.json; an `error` line's `stack`,
// and each `stack` down its `cause` chain, is compared by its first line
// only, as line cases compare it.

namespace test_wire_end {
  // The gold of this block, the milliseconds of a second, a stack's break.
  const constants = Object.freeze({
    gold_id: "typescript.test_wire_end",
    second_ms: 1000,
    stack_break: "\n",
  });

  // What a point calls with its verdict: no difference, or the first one.
  type PointEnd = (difference: string | undefined) => void;

  // One point of the block: its name and the function that runs it.
  interface PointEntry {
    readonly name: string;
    readonly run: (point: PointRun) => void;
  }

  // A copy of a value of this block's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(harness.gold_get(`${constants.gold_id}.${name}`));
  }

  // A copy of a line of this block's gold.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A wire port at the page's address, its blobs to an empty cache.
  function port_make(): wire.WirePort {
    return new wire.WirePort(
      location.href,
      new substrate.CacheFiles([]),
      harness.setting_get,
    );
  }

  // A copy of a line or a cause, each `stack` down its chain cut to line one.
  function stacks_cut(value: { [key: string]: unknown }): {
    [key: string]: unknown;
  } {
    const cut = { ...value };
    if (typeof cut.stack === "string") {
      cut.stack = cut.stack.split(constants.stack_break)[0];
    }
    if (typeof cut.cause === "object" && cut.cause !== null) {
      cut.cause = stacks_cut(cut.cause as { [key: string]: unknown });
    }
    return cut;
  }

  // The JSON text of a value with the keys of each object in order.
  function text_sorted(value: unknown): string {
    return JSON.stringify(value, (_key, item: unknown) =>
      typeof item === "object" && item !== null && !Array.isArray(item)
        ? Object.fromEntries(
            Object.entries(item).sort(([first], [second]) =>
              first < second ? -1 : first > second ? 1 : 0,
            ),
          )
        : item,
    );
  }

  // How the lines that came differ from those expected, if they do.
  function lines_compare(
    came: readonly lines.Line[],
    expected: readonly lines.Line[],
  ): string | undefined {
    const seen = text_sorted(came.map(stacks_cut));
    const owed = text_sorted(expected.map(stacks_cut));
    if (seen === owed) {
      return undefined;
    }
    return `the lines that came are ${seen}, expected ${owed}`;
  }

  // One point as it runs: what it waits for, then its verdict, once.
  class PointRun {
    readonly #name: string;
    readonly #seconds: number;
    readonly #end: PointEnd;
    readonly #timer: number;
    // What the point waits for, which a verdict at its seconds names.
    #waiting = "";
    #ended = false;

    // Takes the point's name, its seconds and what takes its verdict.
    constructor(name: string, seconds: number, end: PointEnd) {
      this.#name = name;
      this.#seconds = seconds;
      this.#end = end;
      this.#timer = setTimeout(
        () => this.#seconds_up(),
        seconds * constants.second_ms,
      );
    }

    // Notes what the point waits for from now on.
    wait_note(what: string): void {
      this.#waiting = what;
    }

    // Takes the verdict, once: passed with no difference, else failed.
    point_end(difference: string | undefined): void {
      if (this.#ended) {
        throw new Error(
          `the point ${this.#name} came to a second verdict: ` +
            String(difference),
        );
      }
      this.#ended = true;
      clearTimeout(this.#timer);
      this.#end(difference);
    }

    // Fails the point, naming what it still waits for.
    #seconds_up(): void {
      this.point_end(
        `no verdict within ${this.#seconds} s, waiting for ${this.#waiting}`,
      );
    }
  }

  // The verdict a close receiver gives a point whose close it must not hear.
  function close_unexpected(code: number, had_error: boolean): string {
    return `the close receiver got the code ${code}, error ${had_error}`;
  }

  // `wire_end` on an open socket: the line goes, `fn` runs at the close.
  function end_waits(point: PointRun): void {
    const port = port_make();
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    port.close_receive((code, had_error) => {
      point.point_end(close_unexpected(code, had_error));
    });
    point.wait_note("tap.start");
    port.wire_open(() => {
      // The page answers once the first line's message is taken, as in use.
      queueMicrotask(() => {
        port.line_post(gold_line("first_reply"), []);
        point.wait_note("the server's close after the report");
        let returned = false;
        port.wire_end(gold_line("report"), () => {
          point.point_end(
            returned
              ? lines_compare(came, [])
              : "wire_end called its function at once, before the close",
          );
        });
        returned = true;
      });
    });
  }

  // `wire_end` once the server has closed the socket: `fn` runs at once.
  function end_closed(point: PointRun): void {
    const port = port_make();
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    port.close_receive((code, had_error) => {
      queueMicrotask(() => {
        let ends = 0;
        port.wire_end(gold_line("report"), () => {
          ends += 1;
        });
        const close = text_sorted([code, had_error]);
        const owed = text_sorted([gold_value("close_lost"), true]);
        const differences = [
          ends === 1
            ? undefined
            : `wire_end called its function ${ends} times at once`,
          close === owed
            ? undefined
            : `the close receiver got ${close}, expected ${owed}`,
          lines_compare(came, [gold_line("unserved_error")]),
        ];
        point.point_end(differences.find((text) => text !== undefined));
      });
    });
    point.wait_note("tap.start");
    port.wire_open(() => {
      queueMicrotask(() => {
        port.line_post(gold_line("first_reply"), []);
        port.line_post(gold_line("unserved"), []);
        point.wait_note("the server's error line and close");
      });
    });
  }

  // `wire_end` after `wire_close`: `fn` runs at once and nothing is sent.
  function close_ended(point: PointRun): void {
    const port = port_make();
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    // Called after the verdict, it throws as a second verdict.
    port.close_receive((code, had_error) => {
      point.point_end(close_unexpected(code, had_error));
    });
    point.wait_note("tap.start");
    port.wire_open(() => {
      queueMicrotask(() => {
        port.wire_close();
        let ends = 0;
        // A line sent on the closing socket would throw here.
        port.wire_end(gold_line("report"), () => {
          ends += 1;
        });
        point.point_end(
          ends === 1
            ? lines_compare(came, [])
            : `wire_end called its function ${ends} times at once`,
        );
      });
    });
  }

  // The points, in order, the last the one whose close no one hears.
  const points: readonly PointEntry[] = Object.freeze([
    { name: "end_waits", run: end_waits },
    { name: "end_closed", run: end_closed },
    { name: "close_ended", run: close_ended },
  ]);

  // Runs the points from `index` on, to the first failed if failfast.
  function points_run(
    runner: tap_producer.TAPTestRunner,
    tracker: tap_producer.Tracker,
    name: string,
    index: number,
    then: () => void,
  ): void {
    if (index === points.length) {
      then();
      return;
    }
    const entry = points[index];
    const seconds = gold_value("point_seconds") as number;
    const point = new PointRun(entry.name, seconds, (difference) => {
      if (difference === undefined) {
        tracker.add_ok(name, entry.name);
      } else {
        tracker.add_not_ok(name, entry.name, "", difference);
      }
      if (difference !== undefined && runner.failfast) {
        then();
      } else {
        points_run(runner, tracker, name, index + 1, then);
      }
    });
    entry.run(point);
  }

  // Runs this block as `name` of the runner, then `done` with its verdict.
  export function block_run(
    runner: tap_producer.TAPTestRunner,
    name: string,
    done: (passed: boolean) => void,
  ): void {
    const tracker = runner.block_start(name, points.length);
    points_run(runner, tracker, name, 0, () => done(runner.block_end(name)));
  }
}

Object.freeze(test_wire_end);
