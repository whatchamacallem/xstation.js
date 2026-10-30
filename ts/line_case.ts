// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The line cases of a block, the infrastructure for testing a module that
// serves JSLB lines through a port. The block's suite builds the module's
// real topology and hands over the test's end of the lane, a real
// `queue.ThreadPort`. The gold of the block's id lists its cases under
// `cases`, each naming lines of the gold under `lines`, whose blob headers
// hold their bytes in `d` as base64. Each case's lines go out through the
// test's end, every line that comes back is collected, and one point is
// added when as many lines came as the case expects, or when its seconds are
// up, so a case that expects none waits its seconds. The point is `ok` when
// the lines that came equal the expected lines in order: the header and the
// payload by value, each blob header but `d` by value, and each blob's bytes
// by their size and `utility.sha256_hex`. Otherwise it is `not ok` with one
// diagnostic line naming the first difference, a line still missing or a
// line not expected. With the runner's failfast the first failed point ends
// the cases. The block is written through `block_start` and `block_end` of
// the runner. A line that comes once the last point is in throws. A case
// never answers a request the module makes.

namespace line_case {
  // The keys of a block's gold and the field of a blob's bytes.
  const constants = Object.freeze({
    cases_key: "cases",
    lines_key: "lines",
    data_field: "d",
    second_ms: 1000,
  });

  // One case of the gold: the names of the lines sent and expected, a wait.
  export interface Case {
    name: string;
    send: string[];
    expect: string[];
    seconds: number;
  }

  // What a block of line cases exports: builds the topology, the test's end.
  export type TopologyBuild = () => queue.ThreadPort;

  // The case that runs: its gold, the lines it expects, those that came.
  interface CaseState {
    readonly test: Case;
    readonly expected: lines.Line[];
    readonly came: lines.Line[];
    timer: number | undefined;
  }

  // Whether the value is a plain object, from a literal or a clone of one.
  function object_plain(value: unknown): value is { [key: string]: unknown } {
    if (typeof value !== "object" || value === null) {
      return false;
    }
    const prototype: unknown = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  // Whether two values of a line are equal, arrays and objects by content.
  function value_equal(first: unknown, second: unknown): boolean {
    if (first === second) {
      return true;
    }
    if (Array.isArray(first) && Array.isArray(second)) {
      const items: readonly unknown[] = first;
      const others: readonly unknown[] = second;
      return (
        items.length === others.length &&
        items.every((item, index) => value_equal(item, others[index]))
      );
    }
    if (object_plain(first) && object_plain(second)) {
      const keys = Object.keys(first);
      return (
        keys.length === Object.keys(second).length &&
        keys.every(
          (key) =>
            Object.hasOwn(second, key) && value_equal(first[key], second[key]),
        )
      );
    }
    return false;
  }

  // The fields of a blob header but its bytes.
  function fields_kept(blob: unknown): { [key: string]: unknown } {
    return Object.fromEntries(
      Object.entries(blob as { [key: string]: unknown }).filter(
        ([name]) => name !== constants.data_field,
      ),
    );
  }

  // A copy of a gold line, each blob's base64 `d` made into its bytes.
  function line_read(id: string, name: string): lines.Line {
    const line = structuredClone(
      harness.gold_get(`${id}.${constants.lines_key}.${name}`),
    ) as lines.Line;
    const blobs = jslb.headers_of(line).slice(1) as lines.BlobHeader[];
    for (const [index, blob] of blobs.entries()) {
      const text = blob.d;
      if (typeof text !== "string") {
        throw new Error(i18n("line_case.blob_text", index + 1, name));
      }
      blob.d = utility.base64_decode(text);
    }
    return line;
  }

  // The first difference of a line that came from the one expected, if any.
  function line_compare(
    number: number,
    expected: lines.Line,
    came: lines.Line,
  ): string | undefined {
    if (!value_equal(came[0], expected[0])) {
      return i18n(
        "line_case.header_differs",
        number,
        utility.json_text(came[0]),
        utility.json_text(expected[0]),
      );
    }
    const payload = jslb.payload_of(came);
    const wanted = jslb.payload_of(expected);
    if (!value_equal(payload, wanted)) {
      return i18n(
        "line_case.payload_differs",
        number,
        utility.json_text(payload),
        utility.json_text(wanted),
      );
    }
    const blobs = jslb.headers_of(came).slice(1) as lines.BlobHeader[];
    const owed = jslb.headers_of(expected).slice(1) as lines.BlobHeader[];
    if (blobs.length !== owed.length) {
      throw new Error("internal error");
    }
    for (const [index, blob] of blobs.entries()) {
      const kept = fields_kept(blob);
      const owed_kept = fields_kept(owed[index]);
      if (!value_equal(kept, owed_kept)) {
        return i18n(
          "line_case.blob_differs",
          number,
          index + 1,
          utility.json_text(kept),
          utility.json_text(owed_kept),
        );
      }
      const data = blob.d;
      if (!(data instanceof Uint8Array)) {
        return i18n("line_case.bytes_missing", number, index + 1);
      }
      const owed_data = owed[index].d as Uint8Array;
      const digest = utility.sha256_hex(data);
      const owed_digest = utility.sha256_hex(owed_data);
      if (data.length !== owed_data.length || digest !== owed_digest) {
        return i18n(
          "line_case.bytes_differ",
          number,
          index + 1,
          data.length,
          digest,
          owed_data.length,
          owed_digest,
        );
      }
    }
    return undefined;
  }

  // The first difference of the lines that came from those expected, if any.
  function difference_find(state: CaseState): string | undefined {
    const { expected, came } = state;
    const count = Math.max(expected.length, came.length);
    for (let index = 0; index < count; index += 1) {
      const number = index + 1;
      if (index >= came.length) {
        return i18n(
          "line_case.line_missing",
          number,
          state.test.seconds,
          jslb.line_render(expected[index]),
        );
      }
      if (index >= expected.length) {
        return i18n(
          "line_case.line_unexpected",
          number,
          jslb.line_render(came[index]),
        );
      }
      const difference = line_compare(number, expected[index], came[index]);
      if (difference !== undefined) {
        return difference;
      }
    }
    return undefined;
  }

  // The cases of one block, run one at a time through the test's end.
  class CaseRun {
    readonly #runner: tap_producer.TAPTestRunner;
    readonly #name: string;
    readonly #id: string;
    readonly #tracker: tap_producer.Tracker;
    readonly #port: queue.ThreadPort;
    readonly #cases: readonly Case[];
    readonly #done: (passed: boolean) => void;
    // The index of the next case to run.
    #next = 0;
    // The case that runs, until its point is added.
    #state: CaseState | undefined = undefined;
    // Whether a point failed, which with failfast ends the cases.
    #failed = false;

    // Takes the block, its runner and tracker, the test's end and the cases.
    constructor(
      runner: tap_producer.TAPTestRunner,
      name: string,
      id: string,
      tracker: tap_producer.Tracker,
      port: queue.ThreadPort,
      cases: readonly Case[],
      done: (passed: boolean) => void,
    ) {
      this.#runner = runner;
      this.#name = name;
      this.#id = id;
      this.#tracker = tracker;
      this.#port = port;
      this.#cases = cases;
      this.#done = done;
    }

    // Takes the lines that come back, then runs the first case.
    cases_start(): void {
      this.#port.line_receive((line) => this.#line_take(line));
      this.#case_next();
    }

    // Sends the next case's lines, or ends the block after the last case.
    #case_next(): void {
      const index = this.#next;
      if (
        index === this.#cases.length ||
        (this.#failed && this.#runner.failfast)
      ) {
        this.#done(this.#runner.block_end(this.#name));
        return;
      }
      this.#next = index + 1;
      const test = this.#cases[index];
      const expected = test.expect.map((name) => line_read(this.#id, name));
      const sent = test.send.map((name) => line_read(this.#id, name));
      const state: CaseState = { test, expected, came: [], timer: undefined };
      this.#state = state;
      state.timer = setTimeout(
        () => this.#point_add(state),
        test.seconds * constants.second_ms,
      );
      for (const line of sent) {
        this.#port.line_post(line, []);
      }
    }

    // Keeps a line that came, and adds the point once all expected came.
    #line_take(line: lines.Line): void {
      const state = this.#state;
      if (state === undefined) {
        throw new Error(
          i18n("line_case.line_late", this.#name, jslb.line_render(line)),
        );
      }
      state.came.push(line);
      if (state.came.length === state.expected.length) {
        clearTimeout(state.timer);
        this.#point_add(state);
      }
    }

    // Adds the point of the case, `ok` when the lines came as expected.
    #point_add(state: CaseState): void {
      this.#state = undefined;
      const difference = difference_find(state);
      if (difference === undefined) {
        this.#tracker.add_ok(this.#name, state.test.name);
      } else {
        this.#failed = true;
        this.#tracker.add_not_ok(this.#name, state.test.name, "", difference);
      }
      this.#case_next();
    }
  }

  // Runs the cases of gold `id` as block `name`, then `done` with the verdict.
  export function block_run(
    runner: tap_producer.TAPTestRunner,
    name: string,
    id: string,
    build: TopologyBuild,
    done: (passed: boolean) => void,
  ): void {
    const cases = harness.gold_get(`${id}.${constants.cases_key}`) as Case[];
    const tracker = runner.block_start(name);
    const port = build();
    new CaseRun(runner, name, id, tracker, port, cases, done).cases_start();
  }
}
Object.freeze(line_case);
