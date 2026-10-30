// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the error overlay in the AI worker: the report function and the
// `fault` lines a recording `post` gets, the first fault only, a fault met
// while the report waits under the first one's cascade. The screen and the
// stop function are tested on the main thread.
namespace test_error_overlay_worker {
  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // The report of a fault of the AI worker, posted by a recording `post`.
  export class TestReport extends unittest.TestCase {
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
}
Object.freeze(test_error_overlay_worker);
