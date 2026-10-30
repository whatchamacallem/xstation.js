// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the AI worker on the UI side, in a page load of its own, where no
// bring up has registered the types its relays register: the owner table,
// the synchronous mode, the wire's tap in its full and sized forms, the note
// of tty 1, the relays of the console's close and of the settings, and the
// cascade of a fault sent as an `error` line by the end function `tap_start`
// takes, the worker's own and the UI's. A relay runs on a real queue of
// thread `ai` in synchronous mode, its handlers registered through the real
// dispatch, its lanes linked local ports whose far ends are the test's, so
// the whole exchange runs within the test's call: the test posts the UI's
// lines at the far end of `ui` and reads what comes back there, and the far
// end of `server` keeps each line and answers a request with the gold's
// reply, as the server does, since the AI side handles `settings.put` too.
// The tap's inner port is one of a linked pair, and the end function is the
// test's own. The lines the tests send and expect and the texts of the notes
// and throws are those of the gold record, test_settings.json. `tap_start`
// runs once per worker, at bring up, whose line cases are
// `test_integrate_worker_ai`, so no test here calls it. The relay of the
// console's opening, which needs the console on tty 0, is the module
// `test_worker_ai_console`, of group C.

namespace test_worker_ai {
  // The values the tests use.
  const constants = Object.freeze({
    // A `blob_max` a test puts, a value chosen by its writer.
    put_blob_max: 7,
    // The bytes of the payload of `{"text": ""}`, around the text.
    text_payload_bytes: 11,
  });

  // An object of fields by name.
  type FieldTable = { [key: string]: unknown };

  // The test's end of a lane: its linked local port and the lines that came.
  interface LaneEnd {
    port: queue.LocalPort;
    came: lines.Line[];
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

  // Links the test's end to a local port, the end keeping each line that came.
  function end_link(near: queue.LocalPort): LaneEnd {
    const port = new queue.LocalPort(near);
    const came: lines.Line[] = [];
    port.line_receive((line) => {
      came.push(line);
    });
    return { port, came };
  }

  // Joins the queue to the thread by linked local ports, one end the test's.
  function lane_make(
    tasks: queue.TaskQueue,
    thread: queue.ThreadName,
  ): LaneEnd {
    const near = new queue.LocalPort();
    const end = end_link(near);
    tasks.port_add(thread, near);
    return end;
  }

  // The AI thread's real queue in synchronous mode, by the worker's owners.
  function tasks_make(): queue.TaskQueue {
    return new queue.TaskQueue("ai", worker_ai.owners_make(), true);
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
      const inner = new queue.LocalPort();
      const far = end_link(inner);
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      const sent = gold_line("kv_list_first");
      tap.line_post(sent, []);
      this.assertTrue(far.came[0] === sent);
      const taken: lines.Line[] = [];
      tap.line_receive((line) => {
        taken.push(line);
      });
      const received = gold_line("kv_list_reply");
      far.port.line_post(received, []);
      this.assertTrue(taken[0] === received);
      this.assertEqual(notes, [
        gold_text("worker_ai_overlay_sent_first"),
        gold_text("worker_ai_overlay_received"),
      ]);
    }

    // A line whose rendering would not fit a verbose entry is noted by sizes.
    test_sizes_noted(): void {
      const inner = new queue.LocalPort();
      const far = end_link(inner);
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
      this.assertTrue(far.came[0] === sent);
      const taken: lines.Line[] = [];
      tap.line_receive((line) => {
        taken.push(line);
      });
      const received = sized();
      far.port.line_post(received, []);
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
      const inner = new queue.LocalPort();
      const far = end_link(inner);
      const notes: string[] = [];
      const tap = new worker_ai.WireTap(inner, (text) => {
        notes.push(text);
      });
      for (const name of ["verbose_put_full", "verbose_put"]) {
        const put = gold_line(name);
        tap.line_post(put, []);
        this.assertTrue(far.came[far.came.length - 1] === put);
      }
      const sent = gold_line("kv_list_second");
      tap.line_post(sent, []);
      this.assertEqual(far.came.length, 3);
      this.assertEqual(notes, [gold_text("worker_ai_overlay_sent_second")]);
    }

    // A note goes to the overlay of tty 1 on the UI and to the log.
    test_note_logged(): void {
      const tasks = tasks_make();
      const ui = lane_make(tasks, "ui");
      const logged: string[] = [];
      const note = worker_ai.note_make(tasks, (text) => {
        logged.push(text);
      });
      const text = gold_text("worker_ai_overlay_sent_empty");
      note(text);
      this.assertEqual(ui.came.length, 1);
      const [shown] = ui.came;
      const expected = gold_line("overlay_line");
      expected.text = text;
      this.assertEqual(shown, expected);
      this.assertEqual(full_of(shown), harness.setting_get("debug"));
      this.assertEqual(logged, [text]);
    }
  }

  // The relays of the UI's console close and of the settings.
  export class TestRelays extends unittest.TestCase {
    // The UI's close closes the console port once and is answered at once.
    test_console_closed(): void {
      const tasks = tasks_make();
      const ui = lane_make(tasks, "ui");
      let closes = 0;
      worker_ai.console_register(tasks, dispatch.handler_register, () => {
        closes += 1;
      });
      ui.port.line_post(gold_line("console_close_request"), []);
      this.assertEqual(closes, 1);
      this.assertEqual(ui.came, [gold_line("console_close_answer")]);
      this.assertEqual(tasks.depth(), 0);
    }

    // A notice of new settings changes the live value, goes to the server.
    test_settings_sent(): void {
      const tasks = tasks_make();
      const ui = lane_make(tasks, "ui");
      const near = new queue.LocalPort();
      const server = new queue.LocalPort(near);
      const kept: lines.Line[] = [];
      // The server's end: it keeps the request and answers it with the gold.
      server.line_receive((line) => {
        kept.push(line);
        const reply = gold_line("settings_put_reply");
        server.line_post(
          dispatch.reply_make(line, jslb.payload_of(reply)),
          [],
        );
      });
      tasks.port_add("server", near);
      const live = settings_live();
      worker_ai.settings_register(tasks, dispatch.handler_register, live);
      const value = settings_live();
      value.blob_max = constants.put_blob_max;
      const notice = gold_line("settings_put_notice");
      notice.settings = value;
      ui.port.line_post(notice, []);
      this.assertEqual(live, value);
      const expected = gold_line("settings_put_copy");
      expected.settings = value;
      this.assertEqual(kept, [expected]);
      this.assertEqual(full_of(kept[0]), harness.setting_get("debug"));
      this.assertEqual(ui.came, []);
      this.assertEqual(tasks.depth(), 0);
    }
  }

  // A fault's cascade sent to the server as an `error` line by the end.
  export class TestFaults extends unittest.TestCase {
    // The cascade goes as one `error` line, its `cause` only when present.
    test_error_sent(): void {
      const ended: lines.Line[] = [];
      const done: number[] = [];
      // The test's own end: it keeps the line, then calls back at once.
      const end: worker_ai.ServerEnd = (line, fn) => {
        ended.push(line);
        fn();
      };
      const cascade = cascade_make();
      worker_ai.error_send(end, cascade, () => {
        done.push(ended.length);
      });
      this.assertEqual(ended.length, 1);
      const [line] = ended;
      this.assertEqual(full_of(line), harness.setting_get("debug"));
      for (const name of ["i", "id", "r", "reply"]) {
        this.assertFalse(Object.hasOwn(line[0], name), name);
      }
      this.assertEqual(line, { ...gold_line("error_full"), ...cascade });
      this.assertEqual(done, [1]);
      const alone = { message: "The read failed.", stack: "" };
      worker_ai.error_send(end, alone, () => {
        done.push(ended.length);
      });
      this.assertEqual(ended[1], { ...gold_line("error_full"), ...alone });
      this.assertFalse(Object.hasOwn(ended[1], "cause"));
      this.assertEqual(done, [1, 2]);
    }

    // The UI's `fault` is sent on as that `error` line, then closes once.
    test_fault_sent(): void {
      const tasks = tasks_make();
      const ui = lane_make(tasks, "ui");
      const ended: lines.Line[] = [];
      // The number of lines kept when each callback ran.
      const called: number[] = [];
      // The test's own end: it keeps the line, then calls back at once.
      const end: worker_ai.ServerEnd = (line, fn) => {
        ended.push(line);
        called.push(ended.length);
        fn();
      };
      let closes = 0;
      worker_ai.fault_register(dispatch.handler_register, end, () => {
        closes += 1;
      });
      const cascade = cascade_make();
      ui.port.line_post(Object.assign(gold_line("fault_ui"), cascade), []);
      this.assertEqual(ended, [{ ...gold_line("error_full"), ...cascade }]);
      this.assertEqual(called, [1]);
      this.assertEqual(closes, 1);
      this.assertEqual(ui.came, []);
      this.assertEqual(tasks.depth(), 0);
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
