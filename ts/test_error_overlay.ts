// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the overlay text, run against stubs of the document so that the
// test page is not replaced. Handlers and the Reload button need a real page.
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

  // Runs `overlay_show` of a new screen while the document methods are stubs.
  export class TestOverlay extends unittest.TestCase {
    // The text each call of the `document.write` stub was given.
    written: string[] = [];

    // How many times the `document.close` stub ran.
    closed = 0;

    // The two document methods the stubs replace, saved by `setUp`.
    saved: Pick<Document, "write" | "close"> | null = null;

    // Saves the two document methods and replaces them with recording stubs.
    override setUp(): void {
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

    // A second fault leaves the first on screen and stops the app only once.
    test_first_only(): void {
      const fault_screen = new error_overlay.FaultScreen();
      const stops: number[] = [];
      fault_screen.stop_register(() => {
        stops.push(this.written.length);
      });
      fault_screen.overlay_show("first", "stack");
      fault_screen.overlay_show("second", "stack");
      this.assertEqual(this.written.length, 1);
      this.assertTrue(this.written[0].startsWith("<pre>first\nstack</pre>"));
      this.assertEqual(this.closed, 1);
      this.assertEqual(stops.join(","), "1");
    }

    // The message and the stack sit in a `pre` as text, not as markup.
    test_escaped_text(): void {
      new error_overlay.FaultScreen().overlay_show("a<b>&c", "d>e&amp;");
      this.assertEqual(this.written.length, 1);
      const html = this.written[0];
      this.assertTrue(
        html.startsWith("<pre>a&lt;b&gt;&amp;c\nd&gt;e&amp;amp;</pre>")
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
    // A second stop function is refused.
    test_stop_twice(): void {
      const fault_screen = new error_overlay.FaultScreen();
      fault_screen.stop_register(() => {});
      this.assertEqual(
        message_thrown(this, () => fault_screen.stop_register(() => {})),
        "The stop function was registered twice"
      );
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds its three routines and the screen class.
    test_frozen_names(): void {
      const names = [
        "FaultScreen",
        "overlay_install",
        "overlay_show",
        "stop_register",
      ];
      this.assertTrue(Object.isFrozen(error_overlay));
      this.assertEqual(
        Object.keys(error_overlay).sort().join(","),
        names.join(",")
      );
    }
  }
}
Object.freeze(test_error_overlay);
