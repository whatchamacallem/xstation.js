// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the AI worker with a queue double, a port double and a wire
// double: the owner table, the synchronous mode, the wire's tap in its full
// and sized forms, the note of tty 1, the relays of the console and of the
// settings, called through the handlers they register, and the cascade of a
// fault sent as an `error` line by `wire_end`, the worker's own and the UI's.
// The lines the tests send and expect and the texts of the notes and throws
// are those of the gold record, test_settings.json. `tap_start` runs once
// per worker, at bring up, which is its integration test, so no test here
// calls it.

namespace test_worker_ai {
  // The values the tests use.
  const constants = Object.freeze({
    // A `blob_max` a test puts, a value chosen by its writer.
    put_blob_max: 7,
    // The bytes of the payload of `{"text": ""}`, around the text.
    text_payload_bytes: 11,
    // The id the queue double answers for a request, chosen by its writer.
    submit_id: 41,
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // The port `error_send` and `fault_register` take, by their signature.
  type EndPort = Parameters<typeof worker_ai.error_send>[0];

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
      harness.gold_get(`typescript.test_worker_ai.${name}`),
    );
  }

  // A text of this module's gold, a run time `{n}` left for the test to fill.
  function gold_text(name: string): string {
    return harness.gold_get(
      `typescript.test_worker_ai.texts.${name}`,
    ) as string;
  }

  // A copy of a line of this module's gold, a run time part set on the copy.
  function gold_line(name: string): lines.Line {
    return gold_value(`lines.${name}`) as lines.Line;
  }

  // The error the function throws, and an error of its own when it doesn't.
  function thrown_get(fn: () => unknown): Error {
    try {
      fn();
    } catch (error) {
      if (error instanceof Error) {
        return error;
      }
      throw error;
    }
    throw new Error("Nothing was thrown.");
  }

  // A port double: it keeps what is posted and hands lines to its receiver.
  class PortDouble implements queue.Port {
    readonly posted: lines.Line[] = [];
    private receiver: ((line: lines.Line) => void) | undefined;

    // Keeps a posted line.
    line_post(line: lines.Line, _transfer: ArrayBuffer[]): void {
      this.posted.push(line);
    }

    // Takes the receiver.
    line_receive(fn: (line: lines.Line) => void): void {
      this.receiver = fn;
    }

    // Hands a line to the receiver as if it came on this port.
    line_send(line: lines.Line): void {
      const receiver = this.receiver;
      if (receiver === undefined) {
        throw new Error("The port double has no receiver.");
      }
      receiver(line);
    }
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

  // A wire double: it keeps each line `wire_end` sends, then calls back.
  class WireDouble {
    readonly ended: lines.Line[] = [];
    // The number of lines kept when each callback ran.
    readonly called: number[] = [];

    // Keeps the line, then calls back as the server's close of the wire does.
    wire_end(line: lines.Line, fn: () => void): void {
      this.ended.push(line);
      this.called.push(this.ended.length);
      fn();
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

  // A settings reader of the test's own values, else of `settings.json`.
  function reader_from(values: FieldTable): (id: string) => unknown {
    return (id: string) =>
      Object.hasOwn(values, id) ? values[id] : harness.setting_get(id);
  }

  // The live settings a relay changes, two values of `settings.json`.
  function settings_live(): settings.Settings {
    const live: FieldTable = {
      blob_max: harness.setting_get("blob_max"),
      line_max: harness.setting_get("line_max"),
    };
    return live as unknown as settings.Settings;
  }

  // A cascade of two failures, the first innermost.
  function cascade_make(): lines.ErrorCause {
    return {
      message: "The read failed.",
      stack: "Error: The read failed.\n    at read",
      cause: { message: "The file is gone.", stack: "" },
    };
  }

  // The owner table of the AI thread.
  export class TestOwnerTables extends unittest.TestCase {
    // The console's lines go here, to its port or to the UI, the rest out.
    test_routes(): void {
      this.assertEqual(worker_ai.owners_make(), {
        "ai.": "ai",
        "tools.": "ai",
        "kv.": "ai",
        "doc.": "ai",
        "db.": "ai",
        "turn.": "ai",
        "sql.": "ai",
        "settings.put": "ai",
        "console.": "ai",
        "console.input": "console",
        "console.output": "ui",
        "console.exit": "ui",
        "verbose.": "server",
        "tap.": "server",
        fault: "ai",
      });
    }
  }

  // Synchronous mode, which only debug mode may set.
  export class TestQueueMode extends unittest.TestCase {
    // Read in debug mode, it is refused outside it.
    test_debug_only(): void {
      const synchronous = reader_from({ queue_synchronous: true });
      this.assertTrue(worker_ai.synchronous_read(synchronous));
      const plain = reader_from({ queue_synchronous: false });
      this.assertFalse(worker_ai.synchronous_read(plain));
      const release = reader_from({ debug: false, queue_synchronous: true });
      const error = thrown_get(() => worker_ai.synchronous_read(release));
      this.assertEqual(
        error.message,
        gold_text("worker_ai_synchronous_release"),
      );
    }
  }

  // The tap that notes the wire's lines, whole or by their sizes.
  export class TestWireTap extends unittest.TestCase {
    // Each line is noted as sent or received and passes unchanged.
    test_both_ways(): void {
      const inner = new PortDouble();
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      const sent = gold_line("kv_list_first");
      tap.line_post(sent, []);
      this.assertTrue(inner.posted[0] === sent);
      const taken: lines.Line[] = [];
      tap.line_receive((line) => {
        taken.push(line);
      });
      const received = gold_line("kv_list_reply");
      inner.line_send(received);
      this.assertTrue(taken[0] === received);
      this.assertEqual(notes, [
        gold_text("worker_ai_overlay_sent_first"),
        gold_text("worker_ai_overlay_received"),
      ]);
    }

    // A line whose rendering would not fit a verbose entry is noted by sizes.
    test_sizes_noted(): void {
      const inner = new PortDouble();
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      const line_max = harness.setting_get("line_max") as number;
      // A line of a payload text of `line_max` characters and a blob of 3.
      const sized = (): lines.Line => {
        const line = gold_line("kv_put_sized");
        line.text = "x".repeat(line_max);
        Object.assign(line[1] as lines.BlobHeader, { d: new Uint8Array(3) });
        return line;
      };
      const sent = sized();
      tap.line_post(sent, []);
      this.assertTrue(inner.posted[0] === sent);
      const taken: lines.Line[] = [];
      tap.line_receive((line) => {
        taken.push(line);
      });
      const received = sized();
      inner.line_send(received);
      this.assertTrue(taken[0] === received);
      const payload = String(line_max + constants.text_payload_bytes);
      this.assertEqual(notes, [
        gold_text("worker_ai_overlay_sent_sized").replaceAll("{1}", payload),
        gold_text("worker_ai_overlay_received_sized").replaceAll(
          "{1}",
          payload,
        ),
      ]);
    }

    // The page's view forwarded as `verbose.put` passes and is not noted.
    test_forward_unshown(): void {
      const inner = new PortDouble();
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      for (const name of ["verbose_put_full", "verbose_put"]) {
        const put = gold_line(name);
        tap.line_post(put, []);
        this.assertTrue(inner.posted[inner.posted.length - 1] === put);
      }
      const sent = gold_line("kv_list_second");
      tap.line_post(sent, []);
      this.assertEqual(inner.posted.length, 3);
      this.assertEqual(notes, [gold_text("worker_ai_overlay_sent_second")]);
    }

    // A note goes to the overlay of tty 1 on the UI and to the log.
    test_note_logged(): void {
      const tasks = tasks_make([]);
      const logged: string[] = [];
      const note = worker_ai.note_make(queue_of(tasks), (text) => {
        logged.push(text);
      });
      const text = gold_text("worker_ai_overlay_sent_empty");
      note(text);
      this.assertEqual(tasks.notified.length, 1);
      const [shown, owner] = tasks.notified[0];
      const expected = gold_line("overlay_line");
      expected.text = text;
      this.assertEqual(shown, expected);
      this.assertEqual(owner, "ui");
      this.assertEqual(full_of(shown), harness.setting_get("debug"));
      this.assertEqual(logged, [text]);
    }
  }

  // The relays of the UI's console opening and close, and of the settings.
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

    // The UI's close closes the console port once and is answered at once.
    test_console_closed(): void {
      const tasks = tasks_make([]);
      let closes = 0;
      worker_ai.console_register(queue_of(tasks), register_route, () => {
        closes += 1;
      });
      const request = gold_line("console_close_request");
      const answer = routed_get("console.close")(request);
      this.assertEqual(closes, 1);
      this.assertEqual(tasks.submitted.length, 0);
      this.assertEqual(tasks.notified.length, 0);
      this.assertEqual(answer, gold_line("console_close_answer"));
    }

    // A notice of new settings changes the live value, goes to the server.
    test_settings_sent(): void {
      const id = constants.submit_id;
      const tasks = tasks_make([id]);
      const live = settings_live();
      worker_ai.settings_register(queue_of(tasks), register_route, live);
      const value = settings_live();
      value.blob_max = constants.put_blob_max;
      const notice = gold_line("settings_put_notice");
      notice.settings = value;
      const sleep = routed_get("settings.put")(notice);
      this.assertEqual(live, value);
      this.assertEqual(tasks.submitted.length, 1);
      const [put, owner] = tasks.submitted[0];
      const expected = gold_line("settings_put_copy");
      expected.settings = value;
      this.assertEqual(put, expected);
      this.assertEqual(owner, "server");
      this.assertEqual(full_of(put), harness.setting_get("debug"));
      const slept = gold_value("lines.settings_sleep") as dispatch.Sleep;
      slept.wait_ids = [id];
      this.assertEqual(sleep, slept);
      const reply = gold_line("settings_put_reply");
      Object.assign(reply[0], { reply: id });
      const wake = gold_line("settings_put_wake");
      wake.replies = [reply];
      this.assertEqual(routed_get("worker.settings_put")(wake), undefined);
      this.assertEqual(tasks.notified.length, 0);
    }
  }

  // A fault's cascade sent to the server as an `error` line by `wire_end`.
  export class TestFaults extends unittest.TestCase {
    // The cascade goes as one `error` line, its `cause` only when present.
    test_error_sent(): void {
      const wire = new WireDouble();
      const done: number[] = [];
      const port = wire as unknown as EndPort;
      const cascade = cascade_make();
      worker_ai.error_send(port, cascade, () => {
        done.push(wire.ended.length);
      });
      this.assertEqual(wire.ended.length, 1);
      const [line] = wire.ended;
      this.assertEqual(full_of(line), harness.setting_get("debug"));
      for (const name of ["i", "id", "r", "reply"]) {
        this.assertFalse(Object.hasOwn(line[0], name), name);
      }
      this.assertEqual(line, { ...gold_line("error_full"), ...cascade });
      this.assertEqual(done, [1]);
      const alone = { message: "The read failed.", stack: "" };
      worker_ai.error_send(port, alone, () => {
        done.push(wire.ended.length);
      });
      this.assertEqual(wire.ended[1], {
        ...gold_line("error_full"),
        ...alone,
      });
      this.assertFalse(Object.hasOwn(wire.ended[1], "cause"));
      this.assertEqual(done, [1, 2]);
    }

    // The UI's `fault` is sent on as that `error` line, then closes once.
    test_fault_sent(): void {
      routed.clear();
      const wire = new WireDouble();
      const port = wire as unknown as EndPort;
      let closes = 0;
      worker_ai.fault_register(register_route, port, () => {
        closes += 1;
      });
      const cascade = cascade_make();
      const line = Object.assign(gold_line("fault_ui"), cascade);
      this.assertEqual(routed_get("fault")(line), undefined);
      this.assertEqual(wire.ended.length, 1);
      this.assertEqual(wire.ended[0], {
        ...gold_line("error_full"),
        ...cascade,
      });
      this.assertEqual(wire.called, [1]);
      this.assertEqual(closes, 1);
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(worker_ai));
      this.assertEqual(Object.keys(worker_ai).sort(), [
        "WireTap",
        "console_register",
        "error_send",
        "fault_register",
        "note_make",
        "owners_make",
        "settings_register",
        "synchronous_read",
        "tap_start",
      ]);
    }
  }
}

Object.freeze(test_worker_ai);
