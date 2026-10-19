// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the overlay text, run against stubs of the document so that the
// test page is not replaced. Handlers and the Reload button need a real page.
namespace test_error_overlay {
  // Runs `overlay_show` while `document.write` and `document.close` are stubs.
  export class TestOverlay extends unittest.TestCase {
    written: string[] = [];
    closed = 0;
    write_original = document.write;
    close_original = document.close;

    // Replaces the two document methods with stubs that record their calls.
    override setUp(): void {
      document.write = (...text: string[]): void => {
        this.written.push(...text);
      };
      document.close = (): void => {
        this.closed += 1;
      };
    }

    // Puts the two document methods back.
    override tearDown(): void {
      document.write = this.write_original;
      document.close = this.close_original;
    }

    // The screen is written once and the document is closed once.
    test_write_once(): void {
      error_overlay.overlay_show("message", "stack");
      this.assertEqual(this.written.length, 1);
      this.assertEqual(this.closed, 1);
    }

    // The message and the stack sit in a `pre` as text, not as markup.
    test_escaped_text(): void {
      error_overlay.overlay_show("a<b>&c", "d>e&amp;");
      this.assertEqual(this.written.length, 1);
      const html = this.written[0];
      this.assertTrue(
        html.startsWith("<pre>a&lt;b&gt;&amp;c\nd&gt;e&amp;amp;</pre>")
      );
      this.assertFalse(html.includes("<b>"));
    }

    // A button follows the text and reloads the page when clicked.
    test_reload_button(): void {
      error_overlay.overlay_show("message", "stack");
      this.assertEqual(this.written.length, 1);
      const html = this.written[0];
      this.assertTrue(html.includes('<button onclick="location.reload()">'));
      this.assertTrue(html.endsWith("Reload</button>"));
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the three routines of its declaration.
    test_frozen_names(): void {
      const names = ["overlay_install", "overlay_show", "stop_register"];
      this.assertTrue(Object.isFrozen(error_overlay));
      this.assertEqual(
        Object.keys(error_overlay).sort().join(","),
        names.join(",")
      );
    }
  }
}
Object.freeze(test_error_overlay);
