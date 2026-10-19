// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the debug overlays, run on containers that are not in the page.
namespace test_overlay {
  // A container that is not in the page, so the live page is not touched.
  function container_make(): HTMLElement {
    return document.createElement("div");
  }

  // The `pre` elements of a container, in document order.
  function pre_list(container: HTMLElement): HTMLPreElement[] {
    return Array.from(container.querySelectorAll("pre"));
  }

  // The ring of an overlay, the order of its lines and the elements it makes.
  export class TestOverlay extends unittest.TestCase {
    // A ring that is not a whole number of at least one is refused.
    test_ring_invalid(): void {
      const container = container_make();
      const rings = [0, -1, 1.5, NaN, Infinity];
      for (const ring of rings) {
        this.assertRaises(Error, () => new overlay.Overlay(container, ring));
      }
    }

    // Nothing is made before the first use of a tty.
    test_no_elements(): void {
      const container = container_make();
      new overlay.Overlay(container, 3);
      this.assertEqual(container.childNodes.length, 0);
    }

    // The first line of a tty makes one hidden `pre` holding only text.
    test_first_use(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "first");
      const pres = pre_list(container);
      this.assertEqual(pres.length, 1);
      this.assertTrue(pres[0].parentElement === container);
      this.assertTrue(pres[0].hidden);
      this.assertEqual(pres[0].textContent, "first");
      this.assertEqual(pres[0].childElementCount, 0);
      this.assertFalse(pres[0].hasAttribute("contenteditable"));
    }

    // Later lines and toggles of the same tty reuse its `pre`.
    test_pre_reused(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      const first = pre_list(container)[0];
      instance.line_add(1, "b");
      instance.overlay_toggle(1);
      this.assertEqual(container.childNodes.length, 1);
      this.assertTrue(pre_list(container)[0] === first);
    }

    // The lines are in the order added, joined by line feeds, newest last.
    test_line_order(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.line_add(1, "b");
      instance.line_add(1, "c");
      this.assertEqual(pre_list(container)[0].textContent, "a\nb\nc");
    }

    // A line above the ring drops the oldest line, one at a time.
    test_oldest_dropped(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      for (const text of ["a", "b", "c"]) {
        instance.line_add(1, text);
      }
      this.assertEqual(pre_list(container)[0].textContent, "a\nb\nc");
      instance.line_add(1, "d");
      this.assertEqual(pre_list(container)[0].textContent, "b\nc\nd");
      instance.line_add(1, "e");
      this.assertEqual(pre_list(container)[0].textContent, "c\nd\ne");
    }

    // A ring of one holds only the newest line.
    test_single_ring(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 1);
      instance.line_add(1, "a");
      instance.line_add(1, "b");
      this.assertEqual(pre_list(container)[0].textContent, "b");
    }

    // The text is shown as text, so markup in a line makes no element.
    test_text_escaped(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      const text = '<b id="x">bold</b> &amp; <i>';
      instance.line_add(1, text);
      const pre = pre_list(container)[0];
      this.assertEqual(pre.textContent, text);
      this.assertEqual(pre.childElementCount, 0);
      this.assertEqual(container.querySelectorAll("b, i").length, 0);
      this.assertTrue(pre.innerHTML.includes("&lt;b"));
      this.assertTrue(pre.innerHTML.includes("&amp;amp;"));
    }

    // A line with no characters still counts toward the ring.
    test_empty_line(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 2);
      instance.line_add(1, "a");
      instance.line_add(1, "");
      instance.line_add(1, "");
      this.assertEqual(pre_list(container)[0].textContent, "\n");
    }

    // Nothing is put in the page: the container and its `pre` stay detached.
    test_stays_detached(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.overlay_toggle(1);
      this.assertFalse(container.isConnected);
      this.assertFalse(pre_list(container)[0].isConnected);
    }
  }

  // Showing and hiding the overlay of a tty.
  export class TestToggle extends unittest.TestCase {
    // A toggle shows a hidden `pre` and a second toggle hides it again.
    test_toggle_twice(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      const pre = pre_list(container)[0];
      this.assertTrue(pre.hidden);
      instance.overlay_toggle(1);
      this.assertFalse(pre.hidden);
      instance.overlay_toggle(1);
      this.assertTrue(pre.hidden);
    }

    // A line added to a shown overlay does not hide it.
    test_shown_kept(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.overlay_toggle(1);
      instance.line_add(1, "b");
      const pre = pre_list(container)[0];
      this.assertFalse(pre.hidden);
      this.assertEqual(pre.textContent, "a\nb");
    }

    // The lines added while hidden are kept for when the overlay is shown.
    test_hidden_lines(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.line_add(1, "b");
      instance.overlay_toggle(1);
      instance.overlay_toggle(1);
      instance.line_add(1, "c");
      instance.overlay_toggle(1);
      const pre = pre_list(container)[0];
      this.assertFalse(pre.hidden);
      this.assertEqual(pre.textContent, "a\nb\nc");
    }

    // A toggle before any line makes the `pre` and shows it, empty.
    test_first_toggle(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.overlay_toggle(2);
      const pres = pre_list(container);
      this.assertEqual(pres.length, 1);
      this.assertFalse(pres[0].hidden);
      this.assertEqual(pres[0].textContent, "");
      instance.line_add(2, "a");
      this.assertEqual(pre_list(container).length, 1);
      this.assertEqual(pres[0].textContent, "a");
    }
  }

  // Two ttys of one overlay object share a container and nothing else.
  export class TestSeparation extends unittest.TestCase {
    // Each tty has its own `pre`, made in the order of first use.
    test_separate_pres(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(2, "two");
      instance.line_add(1, "one");
      const pres = pre_list(container);
      this.assertEqual(pres.length, 2);
      this.assertEqual(pres[0].textContent, "two");
      this.assertEqual(pres[1].textContent, "one");
    }

    // Lines added to one tty do not appear in the other.
    test_lines_independent(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.line_add(2, "x");
      instance.line_add(1, "b");
      const pres = pre_list(container);
      this.assertEqual(pres[0].textContent, "a\nb");
      this.assertEqual(pres[1].textContent, "x");
    }

    // Each tty has its own ring, so a full ring costs the other tty nothing.
    test_rings_independent(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 2);
      instance.line_add(1, "a");
      instance.line_add(2, "x");
      instance.line_add(1, "b");
      instance.line_add(1, "c");
      const pres = pre_list(container);
      this.assertEqual(pres[0].textContent, "b\nc");
      this.assertEqual(pres[1].textContent, "x");
    }

    // A toggle changes only the `pre` of its own tty.
    test_toggles_independent(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container, 3);
      instance.line_add(1, "a");
      instance.line_add(2, "x");
      const pres = pre_list(container);
      instance.overlay_toggle(2);
      this.assertTrue(pres[0].hidden);
      this.assertFalse(pres[1].hidden);
      instance.overlay_toggle(1);
      instance.overlay_toggle(2);
      this.assertFalse(pres[0].hidden);
      this.assertTrue(pres[1].hidden);
    }

    // Two overlay objects on two containers share nothing.
    test_objects_independent(): void {
      const first = container_make();
      const second = container_make();
      const first_overlay = new overlay.Overlay(first, 3);
      const second_overlay = new overlay.Overlay(second, 3);
      first_overlay.line_add(1, "a");
      second_overlay.overlay_toggle(1);
      this.assertEqual(pre_list(first)[0].textContent, "a");
      this.assertTrue(pre_list(first)[0].hidden);
      this.assertEqual(pre_list(second)[0].textContent, "");
      this.assertFalse(pre_list(second)[0].hidden);
    }
  }

  // The shape of the module object.
  export class TestSurface extends unittest.TestCase {
    // The module is frozen and holds the one class of its declaration.
    test_frozen_names(): void {
      this.assertTrue(Object.isFrozen(overlay));
      this.assertEqual(Object.keys(overlay).join(","), "Overlay");
    }
  }
}
Object.freeze(test_overlay);
