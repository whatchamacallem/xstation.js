// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the AI worker's relay of the console's opening, group C: the UI's
// `console.open` goes to the console port on tty 0 and its token comes back.
// A queue double and a register double stand in the queue and the dispatch,
// as no realm without ttyd has the console on tty 0, so this module runs
// only on the ttyd page. The lines the test sends and expects are the gold
// of test_settings.json.

namespace test_worker_ai_console {
  // The values the tests use.
  const constants = Object.freeze({
    // The id the queue double answers for a request, chosen by its writer.
    submit_id: 41,
  });

  // A line and the owner it was given to the queue for.
  type Owned = [lines.Line, queue.ThreadName | undefined];

  // The handlers the code under test registered, by line type.
  const routed = new Map<string, dispatch.Handler>();

  // A register that keeps each handler in `routed`, checked at version 0.
  function register_route(
    type: string,
    version: number,
    fn: dispatch.Handler,
  ): void {
    if (version !== 0) {
      throw new Error(`${type} was registered at version ${String(version)}.`);
    }
    routed.set(type, fn);
  }

  // The handler registered for a type, which must have been registered.
  function routed_get(type: string): dispatch.Handler {
    const fn = routed.get(type);
    if (fn === undefined) {
      throw new Error(`No handler was registered for ${type}.`);
    }
    return fn;
  }

  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_worker_ai_console.${name}`),
    );
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // A queue double: it answers the ids the test picks and keeps each line.
  class TasksDouble {
    readonly submitted: Owned[] = [];
    readonly notified: Owned[] = [];
    private readonly ids: number[];

    // Takes the ids `task_submit` answers, in order.
    constructor(ids: number[]) {
      this.ids = [...ids];
    }

    // Keeps the request and its owner, and answers the next id picked.
    task_submit(line: lines.Line, owner?: queue.ThreadName): number {
      const id = this.ids.shift();
      if (id === undefined) {
        throw new Error("The queue double has no id left to answer.");
      }
      this.submitted.push([line, owner]);
      return id;
    }

    // Keeps the notification and its owner.
    line_notify(line: lines.Line, owner?: queue.ThreadName): void {
      this.notified.push([line, owner]);
    }
  }

  // A queue double answering the ids given, with no handler routed.
  function tasks_make(ids: number[]): TasksDouble {
    routed.clear();
    return new TasksDouble(ids);
  }

  // The queue double as the queue the code under test takes.
  function queue_of(tasks: TasksDouble): queue.TaskQueue {
    return tasks as unknown as queue.TaskQueue;
  }

  // Whether a line was built in full names, as `settings.names_full()` says.
  function full_of(line: lines.Line): boolean {
    return Object.hasOwn(line[0], "type");
  }

  // The relay of the UI's console opening.
  export class TestRelays extends unittest.TestCase {
    // The UI's opening goes to the console port, and its token comes back.
    test_console_opened(): void {
      const id = constants.submit_id;
      const tasks = tasks_make([id]);
      let closes = 0;
      worker_ai.console_register(queue_of(tasks), register_route, () => {
        closes += 1;
      });
      const request = gold_line("console_open_request");
      const sleep = routed_get("console.open")(request);
      this.assertEqual(tasks.submitted.length, 1);
      const [opening, owner] = tasks.submitted[0];
      this.assertEqual(opening, gold_line("console_open_copy"));
      this.assertEqual(owner, "console");
      this.assertEqual(full_of(opening), harness.setting_get("debug"));
      this.assertTrue(opening !== request);
      const expected = gold_value("lines.console_sleep") as dispatch.Sleep;
      expected.state = { request };
      expected.wait_ids = [id];
      this.assertEqual(sleep, expected);
      const reply = gold_line("console_open_reply");
      Object.assign(reply[0], { reply: id });
      const wake = gold_line("console_opened_wake");
      wake.state = (sleep as dispatch.Sleep).state;
      wake.replies = [reply];
      const answer = routed_get("worker.console_opened")(wake);
      this.assertEqual(answer, gold_line("console_open_answer"));
      this.assertEqual(tasks.notified.length, 0);
      this.assertEqual(closes, 0);
    }
  }
}

Object.freeze(test_worker_ai_console);
