// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests the line cases on the real ports of a real task manager: a queue on
// thread `ai` that owns the type prefix `line_case_test.`, whose handlers are
// this file's own functions, and a MessageChannel with a `queue.ThreadPort`
// at each end, the queue's at one and the test's at the other. Each run of
// `line_case.block_run` writes its block through a runner of its own into a
// list of lines, the writer of `set_stream`, and the test adds one point when
// that stream equals the stream of the gold and the verdict is as stated: a
// run of cases that pass, a run whose cases fail by design, each a different
// way, and that run again with failfast. The block is written as its points
// arrive, through `block_start` and `block_end` of the runner it is handed.

namespace test_line_case {
  // The names of the gold, the threads, the types and the handlers' version.
  const constants = Object.freeze({
    gold_id: "typescript.test_line_case",
    block_name: "test_line_case",
    thread: "ai" as const,
    test_thread: "ui" as const,
    owner_prefix: "line_case_test.",
    echo_type: "line_case_test.echo",
    note_type: "line_case_test.note",
    handle_type: "line_case_test.handle",
    handler_version: 0,
    synchronous_setting: "queue_synchronous",
  });

  // One run of the block: its cases, failfast, its stream and its verdict.
  interface RunEntry {
    readonly name: string;
    readonly cases: string;
    readonly failfast: boolean;
    readonly stream: string;
    readonly passed: boolean;
  }

  // The runs, each one point of this block, in order.
  const runs: readonly RunEntry[] = Object.freeze([
    {
      name: "cases_passing",
      cases: "passing",
      failfast: false,
      stream: "passing",
      passed: true,
    },
    {
      name: "cases_graded",
      cases: "graded",
      failfast: false,
      stream: "graded",
      passed: false,
    },
    {
      name: "failfast_stops",
      cases: "graded",
      failfast: true,
      stream: "failfast",
      passed: false,
    },
  ]);

  // The handle a `handle` request names, and the size of its blob.
  interface HandleRequest {
    handle: string;
    size: number;
  }

  // Registers the handlers of the queue, the test's own functions.
  function handlers_register(): void {
    dispatch.handler_register(
      constants.echo_type,
      constants.handler_version,
      (line) =>
        dispatch.reply_make(
          line,
          jslb.payload_of(line),
          jslb.headers_of(line).slice(1) as lines.BlobHeader[],
        ),
    );
    dispatch.handler_register(
      constants.note_type,
      constants.handler_version,
      () => undefined,
    );
    dispatch.handler_register(
      constants.handle_type,
      constants.handler_version,
      (line) => {
        const asked = jslb.payload_of(line) as unknown as HandleRequest;
        const blob: lines.BlobHeader = { s: asked.size, d: asked.handle };
        return dispatch.reply_make(line, {}, [blob]);
      },
    );
  }

  // A real queue with a real port to the test's thread, and the test's end.
  function topology_build(): queue.ThreadPort {
    const synchronous = harness.setting_get(
      constants.synchronous_setting,
    ) as boolean;
    const owners = { [constants.owner_prefix]: constants.thread };
    const tasks = new queue.TaskQueue(constants.thread, owners, synchronous);
    const channel = new MessageChannel();
    tasks.port_add(constants.test_thread, new queue.ThreadPort(channel.port2));
    return new queue.ThreadPort(channel.port1);
  }

  // The first line where the stream differs from the gold's, if any.
  function stream_difference(
    actual: readonly string[],
    expected: readonly string[],
  ): string | undefined {
    const count = Math.max(actual.length, expected.length);
    for (let index = 0; index < count; index += 1) {
      if (actual[index] !== expected[index]) {
        return (
          `line ${index + 1} is ${JSON.stringify(actual[index])}, ` +
          `expected ${JSON.stringify(expected[index])}`
        );
      }
    }
    return undefined;
  }

  // How a run differs from its gold stream or its stated verdict, if it does.
  function run_difference(
    run: RunEntry,
    written: readonly string[],
    stream: readonly string[],
    passed: boolean,
  ): string | undefined {
    const difference = stream_difference(written, stream);
    if (difference !== undefined) {
      return difference;
    }
    if (passed !== run.passed) {
      return `the verdict is ${passed}, expected ${run.passed}`;
    }
    return undefined;
  }

  // Runs one run of the block into a list, then adds its point and says if ok.
  function run_check(
    tracker: tap_producer.Tracker,
    run: RunEntry,
    then: (ok: boolean) => void,
  ): void {
    const written: string[] = [];
    const runner = new tap_producer.TAPTestRunner(run.failfast);
    runner.set_stream((text) => written.push(text));
    const id = `${constants.gold_id}.${run.cases}`;
    line_case.block_run(
      runner,
      constants.block_name,
      id,
      topology_build,
      (passed) => {
        runner.run_end();
        const stream = harness.gold_get(
          `${constants.gold_id}.streams.${run.stream}`,
        ) as string[];
        const difference = run_difference(run, written, stream, passed);
        if (difference === undefined) {
          tracker.add_ok(constants.block_name, run.name);
        } else {
          tracker.add_not_ok(constants.block_name, run.name, "", difference);
        }
        then(difference === undefined);
      },
    );
  }

  // Runs the runs from `index` on, to the first failed with failfast, then ends.
  function runs_check(
    runner: tap_producer.TAPTestRunner,
    tracker: tap_producer.Tracker,
    index: number,
    then: () => void,
  ): void {
    if (index === runs.length) {
      then();
      return;
    }
    run_check(tracker, runs[index], (ok) => {
      if (ok || !runner.failfast) {
        runs_check(runner, tracker, index + 1, then);
      } else {
        then();
      }
    });
  }

  // Runs this block as `name` of the runner, then `done` with its verdict.
  export function block_run(
    runner: tap_producer.TAPTestRunner,
    name: string,
    done: (passed: boolean) => void,
  ): void {
    handlers_register();
    const tracker = runner.block_start(name);
    runs_check(runner, tracker, 0, () => done(runner.block_end(name)));
  }
}
Object.freeze(test_line_case);
