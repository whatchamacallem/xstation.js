// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the error overlay on the main thread: the screen, which the real
// `document.write` writes into the block's own page load, replacing it, and
// the stop function. A write erases the page's window listeners, so each
// case installs the page's fault handlers again right after it, and a fault
// of a later case still reaches the driver as the realm's own. The report
// function is tested in the AI worker, in a block of its own. The handlers
// and the Reload button's click need a page of their own.
namespace test_error_overlay {
  // The message of the error a function throws, failing the test if none.
  function message_thrown(test: unittest.TestCase, fn: () => unknown): string {
    try {
      fn();
    } catch (error) {
      return (error as Error).message;
    }
    return test.fail("Nothing was thrown.");
  }

  // Runs a call that writes the screen, then installs the handlers it erased.
  function screen_write(write: () => void): void {
    write();
    error_overlay.overlay_install();
  }

  // The texts of the `pre` elements of the document, in order.
  function pre_texts(): string[] {
    return Array.from(
      document.querySelectorAll("pre"),
      (pre) => pre.textContent as string,
    );
  }

  // The screens the real document shows, written by `document.write`.
  export class TestOverlay extends unittest.TestCase {
    // The screen replaces the page, and the document is closed after it.
    test_write_once(): void {
      screen_write(() =>
        new error_overlay.FaultScreen().overlay_show("message", "stack"),
      );
      this.assertEqual(
        document.body.innerHTML,
        '<pre>message\nstack</pre><button onclick="location.reload()">' +
          "Reload</button>",
      );
      this.assertEqual(document.head.childElementCount, 0);
      this.assertEqual(document.readyState, "complete");
    }

    // A second show leaves the first fault on screen.
    test_first_only(): void {
      const fault_screen = new error_overlay.FaultScreen();
      screen_write(() => fault_screen.overlay_show("first", "stack"));
      fault_screen.overlay_show("second", "stack");
      this.assertEqual(pre_texts(), ["first\nstack"]);
      this.assertEqual(document.querySelectorAll("button").length, 1);
      this.assertEqual(document.readyState, "complete");
    }

    // Showing a fault runs no stop function.
    test_show_unstopped(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const stops: unknown[] = [];
      fault_screen.stop_register((thrown) => {
        stops.push(thrown);
      });
      screen_write(() => fault_screen.overlay_show("unstopped", "stack"));
      this.assertEqual(pre_texts(), ["unstopped\nstack"]);
      this.assertEqual(stops.length, 0);
    }

    // The stop function runs after the screen with the thrown value, once.
    test_stop_after(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const shown: string[][] = [];
      const values: unknown[] = [];
      fault_screen.stop_register((thrown) => {
        shown.push(pre_texts());
        values.push(thrown);
      });
      const first = new Error("stopped");
      screen_write(() => fault_screen.fault_take(first, null));
      fault_screen.fault_take(new Error("second"), null);
      const screen = `stopped\n${first.stack as string}`;
      this.assertEqual(pre_texts(), [screen]);
      this.assertEqual(shown, [[screen]]);
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
      // A document with no window loads nothing, so no fetch of it is made.
      const inert = document.implementation.createHTMLDocument("");
      const image = inert.createElement("img");
      image.setAttribute("src", "missing.png");
      screen_write(() => fault_screen.resource_take(image));
      const text = 'Failed to load img src="missing.png"';
      this.assertEqual(values.length, 1);
      this.assertTrue(values[0] instanceof Error);
      this.assertEqual((values[0] as Error).message, text);
      const stack = (values[0] as Error).stack as string;
      this.assertEqual(pre_texts(), [`${text}\n${stack}`]);
    }

    // The message and the stack sit in a `pre` as text, not as markup.
    test_escaped_text(): void {
      screen_write(() =>
        new error_overlay.FaultScreen().overlay_show("a<b>&c", "d>e&amp;"),
      );
      this.assertEqual(pre_texts(), ["a<b>&c\nd>e&amp;"]);
      const pre = document.querySelector("pre") as HTMLPreElement;
      this.assertEqual(pre.childElementCount, 0);
      this.assertEqual(document.querySelector("b"), null);
    }

    // A button follows the text and reloads the page when clicked.
    test_reload_button(): void {
      screen_write(() =>
        new error_overlay.FaultScreen().overlay_show("reload", "stack"),
      );
      const buttons = Array.from(document.querySelectorAll("button"));
      this.assertEqual(buttons.length, 1);
      const pre = document.querySelector("pre") as HTMLPreElement;
      this.assertTrue(pre.nextElementSibling === buttons[0]);
      this.assertEqual(
        buttons[0].getAttribute("onclick"),
        "location.reload()",
      );
      this.assertEqual(buttons[0].textContent, "Reload");
      this.assertEqual(buttons[0].nextSibling, null);
    }
  }

  // The registration of the stop function, which touches no document.
  export class TestStop extends unittest.TestCase {
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
