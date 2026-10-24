// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the error overlay, run in both streams, each the cases of its own
// thread: the screen and the stop function on the main thread, against stubs
// of the document so that the test page is not replaced, and the report
// function in the AI worker. The handlers and the Reload button need a real
// page.
namespace test_error_overlay {
  // The reasons of the skips.
  const constants = Object.freeze({
    main_only: "The screen and the stop function run on the main thread.",
    worker_only: "The report function runs in the AI worker.",
  });

  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // Skips a case of the main thread where there is no document.
  function main_need(test: unittest.TestCase): void {
    if (typeof document === "undefined") {
      test.skipTest(constants.main_only);
    }
  }

  // Skips a case of the AI worker where there is a document.
  function worker_need(test: unittest.TestCase): void {
    if (typeof document !== "undefined") {
      test.skipTest(constants.worker_only);
    }
  }

  // Runs a new screen on the main thread while the document methods are stubs.
  export class TestOverlay extends unittest.TestCase {
    // The text each call of the `document.write` stub was given.
    written: string[] = [];

    // How many times the `document.close` stub ran.
    closed = 0;

    // The two document methods the stubs replace, saved by `setUp`.
    saved: Pick<Document, "write" | "close"> | null = null;

    // Saves the two document methods and replaces them with recording stubs.
    override setUp(): void {
      main_need(this);
      this.saved = { write: document.write, close: document.close };
      document.write = (...text: string[]): void => {
        this.written.push(...text);
      };
      document.close = (): void => {
        this.closed += 1;
      };
    }

    // Puts the two document methods back.
    override tearDown(): void {
      const saved = this.saved as Pick<Document, "write" | "close">;
      document.write = saved.write;
      document.close = saved.close;
    }

    // The screen is written once and the document is closed once.
    test_write_once(): void {
      new error_overlay.FaultScreen().overlay_show("message", "stack");
      this.assertEqual(this.written.length, 1);
      this.assertEqual(this.closed, 1);
    }

    // A second show leaves the first fault on screen.
    test_first_only(): void {
      const fault_screen = new error_overlay.FaultScreen();
      fault_screen.overlay_show("first", "stack");
      fault_screen.overlay_show("second", "stack");
      this.assertEqual(this.written.length, 1);
      this.assertTrue(this.written[0].startsWith("<pre>first\nstack</pre>"));
      this.assertEqual(this.closed, 1);
    }

    // Showing a fault runs no stop function.
    test_show_unstopped(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const stops: unknown[] = [];
      fault_screen.stop_register((thrown) => {
        stops.push(thrown);
      });
      fault_screen.overlay_show("message", "stack");
      this.assertEqual(this.written.length, 1);
      this.assertEqual(stops.length, 0);
    }

    // The stop function runs after the screen with the thrown value, once.
    test_stop_after(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const stops: number[] = [];
      const values: unknown[] = [];
      fault_screen.stop_register((thrown) => {
        stops.push(this.written.length);
        values.push(thrown);
      });
      const first = new Error("first");
      fault_screen.fault_take(first, null);
      fault_screen.fault_take(new Error("second"), null);
      this.assertEqual(this.written.length, 1);
      this.assertTrue(this.written[0].startsWith("<pre>first\n"));
      this.assertEqual(stops.join(","), "1");
      this.assertEqual(values.length, 1);
      this.assertTrue(values[0] === first);
    }

    // A resource that failed to load is a fault, an Error of its text.
    test_resource_thrown(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const values: unknown[] = [];
      fault_screen.stop_register((thrown) => {
        values.push(thrown);
      });
      const image = document.createElement("img");
      image.setAttribute("src", "missing.png");
      fault_screen.resource_take(image);
      const text = 'Failed to load img src="missing.png"';
      this.assertEqual(values.length, 1);
      this.assertTrue(values[0] instanceof Error);
      this.assertEqual((values[0] as Error).message, text);
      this.assertTrue(this.written[0].startsWith(`<pre>${text}\n`));
    }

    // The message and the stack sit in a `pre` as text, not as markup.
    test_escaped_text(): void {
      new error_overlay.FaultScreen().overlay_show("a<b>&c", "d>e&amp;");
      this.assertEqual(this.written.length, 1);
      const html = this.written[0];
      this.assertTrue(
        html.startsWith("<pre>a&lt;b&gt;&amp;c\nd&gt;e&amp;amp;</pre>"),
      );
      this.assertFalse(html.includes("<b>"));
    }

    // A button follows the text and reloads the page when clicked.
    test_reload_button(): void {
      new error_overlay.FaultScreen().overlay_show("message", "stack");
      this.assertEqual(this.written.length, 1);
      const html = this.written[0];
      this.assertTrue(html.includes('<button onclick="location.reload()">'));
      this.assertTrue(html.endsWith("Reload</button>"));
    }
  }

  // The registration of the stop function, which touches no document.
  export class TestStop extends unittest.TestCase {
    // The stop function belongs to the main thread.
    override setUp(): void {
      main_need(this);
    }

    // A second stop function is refused.
    test_stop_twice(): void {
      const fault_screen = new error_overlay.FaultScreen();
      fault_screen.stop_register(() => {});
      this.assertEqual(
        message_thrown(this, () => fault_screen.stop_register(() => {})),
        "The stop function was registered twice",
      );
    }
  }

  // The report of a fault of the AI worker, posted by a recording `post`.
  export class TestReport extends unittest.TestCase {
    // The report function belongs to the AI worker.
    override setUp(): void {
      worker_need(this);
    }

    // The report gets the thrown value and `done`, which posts the cascade.
    test_report_done(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const posted: object[] = [];
      const values: unknown[] = [];
      const dones: (() => void)[] = [];
      fault_screen.report_register((thrown, done) => {
        values.push(thrown);
        dones.push(done);
      });
      const inner = new Error("inner");
      const middle = new Error("middle", { cause: inner });
      const thrown = new Error("outer", { cause: middle });
      fault_screen.fault_take(thrown, (line) => {
        posted.push(line);
      });
      this.assertEqual(values.length, 1);
      this.assertTrue(values[0] === thrown);
      this.assertEqual(posted.length, 0);
      dones[0]();
      this.assertEqual(posted, [
        {
          0: { type: "fault" },
          thread: "ai",
          message: "outer",
          stack: thrown.stack,
          cause: {
            message: "middle",
            stack: middle.stack,
            cause: { message: "inner", stack: inner.stack },
          },
        },
      ]);
    }

    // With no report function the line is posted at once, the first only.
    test_posted_at_once(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const posted: object[] = [];
      const post = (line: object): void => {
        posted.push(line);
      };
      fault_screen.fault_take("plain", post);
      fault_screen.fault_take(new Error("later"), post);
      this.assertEqual(posted, [
        { 0: { type: "fault" }, thread: "ai", message: "plain", stack: "" },
      ]);
    }

    // A fault while the report waits posts at once, the first under its cause.
    test_fault_waiting(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const posted: object[] = [];
      const dones: (() => void)[] = [];
      const post = (line: object): void => {
        posted.push(line);
      };
      fault_screen.report_register((_thrown, done) => {
        dones.push(done);
      });
      const first = new Error("first");
      const second = new Error("second", { cause: "a text cause" });
      fault_screen.fault_take(first, post);
      fault_screen.fault_take(second, post);
      const expected = {
        0: { type: "fault" },
        thread: "ai",
        message: "second",
        stack: second.stack,
        cause: {
          message: "a text cause",
          stack: "",
          cause: { message: "first", stack: first.stack },
        },
      };
      this.assertEqual(posted, [expected]);
      fault_screen.fault_take(new Error("third"), post);
      dones[0]();
      this.assertEqual(posted, [expected]);
      this.assertEqual(dones.length, 1);
    }

    // A report that throws is a fault met while it waits, posted at once.
    test_report_thrown(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const posted: object[] = [];
      const first = new Error("first");
      const thrown = new Error("report");
      fault_screen.report_register(() => {
        throw thrown;
      });
      fault_screen.fault_take(first, (line) => {
        posted.push(line);
      });
      this.assertEqual(posted, [
        {
          0: { type: "fault" },
          thread: "ai",
          message: "report",
          stack: thrown.stack,
          cause: { message: "first", stack: first.stack },
        },
      ]);
    }

    // A second report function is refused.
    test_report_twice(): void {
      const fault_screen = new error_overlay.FaultScreen();
      fault_screen.report_register(() => {});
      this.assertEqual(
        message_thrown(this, () => fault_screen.report_register(() => {})),
        "The report function was registered twice",
      );
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds its four routines and the screen class.
    test_frozen_names(): void {
      const names = [
        "FaultScreen",
        "overlay_install",
        "overlay_show",
        "report_register",
        "stop_register",
      ];
      this.assertTrue(Object.isFrozen(error_overlay));
      this.assertEqual(
        Object.keys(error_overlay).sort().join(","),
        names.join(","),
      );
    }
  }
}
Object.freeze(test_error_overlay);
