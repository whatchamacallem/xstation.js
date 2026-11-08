// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the AI worker on the UI side, in a page load of its own, where no
// bring up has registered the types its relays register. A relay runs on a
// real queue of thread `ai` in synchronous mode, its lanes linked local ports
// whose far ends are the test's, so the whole exchange runs within the test's
// call. The far end of `server` answers a request with the gold's reply, as
// the server does, since the AI side handles `settings.put` too. `tap_start`
// runs once per worker, at bring up, whose line cases are
// `test_integrate_worker_ai`, so no test here calls it. The relay of the
// console's opening, which needs the console on tty 0, is the module
// `test_worker_ai_console`, of group C.

namespace test_worker_ai {
  // The values the tests use.
  const constants = Object.freeze({
    // A `blob_max` a test puts, a value chosen by its writer.
    put_blob_max: 7,
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

  // A line of the console lane with its payload and, given text, one blob.
  function console_line(
    type: string,
    payload: FieldTable,
    text?: string,
  ): lines.Line {
    const header = jslb.header_make(type, { full: settings.names_full() });
    const blobs =
      text === undefined ? [] : [jslb.blob_make(utility.utf8_encode(text))];
    return jslb.line_make(header, blobs, payload);
  }

  // The type of a line, then the text of its blob when it has one.
  function line_texts(line: lines.Line): string[] {
    const type = jslb.field_get(line[0], "type") as string;
    const blob = line[1] as lines.BlobHeader | undefined;
    if (blob === undefined) {
      return [type];
    }
    const data = jslb.field_get(blob, "data") as Uint8Array;
    return [type, utility.utf8_decode(data)];
  }

  // A writer, its port linked to the test's end, its UI and what it passes.
  function writer_make(): {
    writer: worker_ai.ConsoleWriter;
    end: LaneEnd;
    ui: lines.Line[];
    back: lines.Line[];
  } {
    const near = new queue.LocalPort();
    const end = end_link(near);
    const ui: lines.Line[] = [];
    const back: lines.Line[] = [];
    const writer = new worker_ai.ConsoleWriter(near, (line) => {
      ui.push(line);
    });
    writer.line_receive((line) => {
      back.push(line);
    });
    return { writer, end, ui, back };
  }

  // Sends tty 0's output of the text from the test's end to the writer.
  function output_send(end: LaneEnd, text: string): void {
    end.port.line_post(console_line("console.output", {}, "0" + text), []);
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
        "console.busy": "ui",
        "console.idle": "ui",
        "audit.": "server",
        "audit.tail": "ai",
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
      const debug = (): boolean => true;
      this.assertTrue(worker_ai.synchronous_read(synchronous, debug));
      const plain = reader_from({ queue_synchronous: false });
      this.assertFalse(worker_ai.synchronous_read(plain, debug));
      const error = thrown_get(() =>
        worker_ai.synchronous_read(synchronous, () => false),
      );
      this.assertEqual(
        error.message,
        gold_text("worker_ai_synchronous_release"),
      );
    }
  }

  // The relays of the UI's console close, of the settings and of the tail.
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
      this.assertEqual(full_of(kept[0]), switches.debug_on());
      this.assertEqual(ui.came, []);
      this.assertEqual(tasks.depth(), 0);
    }

    // The UI's `audit.tail` goes to the server, and its text comes back.
    test_tail_relayed(): void {
      const tasks = tasks_make();
      const ui = lane_make(tasks, "ui");
      const near = new queue.LocalPort();
      const server = new queue.LocalPort(near);
      const kept: lines.Line[] = [];
      // The server's end: it keeps the request and answers it with the gold.
      server.line_receive((line) => {
        kept.push(line);
        const reply = gold_line("audit_tail_reply");
        server.line_post(
          dispatch.reply_make(line, jslb.payload_of(reply)),
          [],
        );
      });
      tasks.port_add("server", near);
      worker_ai.tail_register(tasks, dispatch.handler_register);
      ui.port.line_post(gold_line("audit_tail_request"), []);
      this.assertEqual(kept, [gold_line("audit_tail_copy")]);
      this.assertEqual(full_of(kept[0]), switches.debug_on());
      this.assertEqual(ui.came, [gold_line("audit_tail_answer")]);
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
      this.assertEqual(full_of(line), switches.debug_on());
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

  // tty 0's one writer: the AI's lines and the view's held through a turn.
  export class TestWriter extends unittest.TestCase {
    // The AI's text goes one message per line a newline ends, in order.
    test_lines_cut(): void {
      const { writer, end } = writer_make();
      writer.line_post(console_line("console.write", { text: "a\nb" }), []);
      writer.line_post(console_line("console.write", { text: "c\nd\n" }), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.input", "0a\n"],
        ["console.input", "0bc\n"],
        ["console.input", "0d\n"],
      ]);
    }

    // The text after the last newline waits for the write that ends it.
    test_rest_held(): void {
      const { writer, end } = writer_make();
      writer.line_post(
        console_line("console.write", { text: "echo par" }),
        [],
      );
      this.assertEqual(end.came, []);
      writer.line_post(console_line("console.write", { text: "tial\n" }), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.input", "0echo partial\n"],
      ]);
    }

    // Outside a turn the view's line goes as it came.
    test_view_passed(): void {
      const { writer, end } = writer_make();
      writer.line_post(console_line("console.input", {}, "0ls\r"), []);
      this.assertEqual(end.came.map(line_texts), [["console.input", "0ls\r"]]);
    }

    // A view's line inside the AI's turn waits until its idle, then goes.
    test_view_held(): void {
      const { writer, end, ui } = writer_make();
      output_send(end, "$ ");
      writer.line_post(console_line("console.busy", {}), []);
      writer.line_post(console_line("console.input", {}, "0echo view\r"), []);
      writer.line_post(console_line("console.write", { text: "yes\n" }), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.busy"],
        ["console.input", "0yes\n"],
      ]);
      writer.line_post(console_line("console.idle", {}), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.busy"],
        ["console.input", "0yes\n"],
        ["console.idle"],
        ["console.input", "0echo view\r"],
      ]);
      this.assertEqual(ui.map(line_texts), [
        ["console.busy"],
        ["console.idle"],
      ]);
    }

    // The AI's turn waits while the person's command runs, until the prompt.
    test_turn_waits(): void {
      const { writer, end, ui } = writer_make();
      output_send(end, "$ ");
      writer.line_post(console_line("console.input", {}, "0sleep 1\r"), []);
      writer.line_post(console_line("console.busy", {}), []);
      writer.line_post(
        console_line("console.write", { text: "echo hi\n" }),
        [],
      );
      output_send(end, "sleep 1\r\n");
      this.assertEqual(end.came.map(line_texts), [
        ["console.input", "0sleep 1\r"],
      ]);
      this.assertEqual(ui, []);
      output_send(end, "$ ");
      this.assertEqual(end.came.map(line_texts), [
        ["console.input", "0sleep 1\r"],
        ["console.busy"],
        ["console.input", "0echo hi\n"],
      ]);
      this.assertEqual(ui.map(line_texts), [["console.busy"]]);
    }

    // The person's line inside their own command goes while the AI waits.
    test_view_own(): void {
      const { writer, end, ui } = writer_make();
      output_send(end, "$ ");
      writer.line_post(console_line("console.input", {}, "0read x\r"), []);
      writer.line_post(console_line("console.busy", {}), []);
      writer.line_post(console_line("console.input", {}, "0yes\r"), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.input", "0read x\r"],
        ["console.input", "0yes\r"],
      ]);
      this.assertEqual(ui, []);
    }

    // A prompt split across two messages of output still concludes tty 0.
    test_prompt_split(): void {
      const { writer, end, ui } = writer_make();
      writer.line_post(console_line("console.busy", {}), []);
      output_send(end, "$");
      this.assertEqual(ui, []);
      output_send(end, " ");
      this.assertEqual(ui.map(line_texts), [["console.busy"]]);
    }

    // A tty 0 opened anew has shown no prompt, so the AI's turn waits.
    test_open_unconcluded(): void {
      const { writer, end, ui } = writer_make();
      output_send(end, "$ ");
      writer.line_post(console_line("console.open", {}), []);
      writer.line_post(console_line("console.busy", {}), []);
      this.assertEqual(end.came.map(line_texts), [["console.open"]]);
      this.assertEqual(ui, []);
    }

    // A read in a waiting turn goes after the busy with the time it has left.
    test_read_waits(): void {
      const { writer, end } = writer_make();
      const seconds = 5;
      writer.line_post(console_line("console.busy", {}), []);
      writer.line_post(
        console_line("console.read", {
          until: "$ ",
          timeout_seconds: seconds,
        }),
        [],
      );
      this.assertEqual(end.came, []);
      output_send(end, "$ ");
      this.assertEqual(end.came.map(line_texts), [
        ["console.busy"],
        ["console.read"],
      ]);
      const payload = jslb.payload_of(end.came[1]);
      this.assertEqual(payload.until, "$ ");
      const left = payload.timeout_seconds as number;
      this.assertTrue(left > 0 && left <= seconds);
    }

    // A turn the AI ends before it started sends nothing, then or later.
    test_waiting_ended(): void {
      const { writer, end, ui } = writer_make();
      writer.line_post(console_line("console.busy", {}), []);
      writer.line_post(
        console_line("console.write", { text: "echo no\n" }),
        [],
      );
      writer.line_post(console_line("console.idle", {}), []);
      output_send(end, "$ ");
      this.assertEqual(end.came, []);
      this.assertEqual(ui, []);
    }

    // Reads and openings pass on as they came.
    test_others_passed(): void {
      const { writer, end } = writer_make();
      const read = console_line("console.read", {
        until: "$ ",
        timeout_seconds: 1,
      });
      writer.line_post(read, []);
      writer.line_post(console_line("console.open", {}), []);
      this.assertEqual(end.came.map(line_texts), [
        ["console.read"],
        ["console.open"],
      ]);
      this.assertEqual(end.came[0], read);
    }

    // A second busy within a turn, or an idle outside one, throws.
    test_turn_refused(): void {
      const { writer } = writer_make();
      const idle = thrown_get(() =>
        writer.line_post(console_line("console.idle", {}), []),
      );
      this.assertEqual(idle.message, gold_text("worker_ai_idle_unheld"));
      writer.line_post(console_line("console.busy", {}), []);
      const busy = thrown_get(() =>
        writer.line_post(console_line("console.busy", {}), []),
      );
      this.assertEqual(busy.message, gold_text("worker_ai_busy_twice"));
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the names of its surface.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(worker_ai));
      this.assertEqual(Object.keys(worker_ai).sort(), [
        "ConsoleWriter",
        "console_attach",
        "console_register",
        "error_send",
        "fault_register",
        "owners_make",
        "settings_register",
        "synchronous_read",
        "tail_register",
        "tap_start",
      ]);
    }
  }
}

Object.freeze(test_worker_ai);
