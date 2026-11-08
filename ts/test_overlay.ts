// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the debug overlays, run on containers that are not in the page,
// and of the scrolling that keeps a shown overlay's end in view, run on a
// container of a fixed size put in the page and taken out after, or on one
// inside it that does not scroll, as `overlays` sits in `debug` on the engine
// page. The line count of a tall text and the size of the scrolling container
// are read from the gold.
namespace test_overlay {
  // A copy of a value of this module's gold, which the harness keeps frozen.
  function gold_value(name: string): unknown {
    return structuredClone(
      harness.gold_get(`typescript.test_overlay.${name}`),
    );
  }

  // A text of a tty whose lines overflow the scrolling container.
  function tall_text(tty: number): string {
    const count = gold_value("tall_count") as number;
    const lines: string[] = [];
    for (let index = 0; index < count; index += 1) {
      lines.push(`tty ${tty} line ${index}`);
    }
    return lines.join("\n");
  }

  // A container that is not in the page, so the live page is not touched.
  function container_make(): HTMLElement {
    return document.createElement("div");
  }

  // The `pre` elements of a container, in document order.
  function pre_list(container: HTMLElement): HTMLPreElement[] {
    return Array.from(container.querySelectorAll("pre"));
  }

  // How far the end of a `pre` lies below its container's visible bottom.
  function end_below(container: HTMLElement, pre: HTMLPreElement): number {
    const box = container.getBoundingClientRect();
    const bottom = box.top + container.clientTop + container.clientHeight;
    return pre.getBoundingClientRect().bottom - bottom;
  }

  // The elements an overlay makes and the text it shows.
  export class TestOverlay extends unittest.TestCase {
    // Nothing is made before the first use of a tty.
    test_no_elements(): void {
      const container = container_make();
      new overlay.Overlay(container);
      this.assertEqual(container.childNodes.length, 0);
    }

    // The first toggle of a tty makes one shown `pre`, empty, of text only.
    test_first_toggle(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      this.assertTrue(instance.overlay_toggle(1));
      const pres = pre_list(container);
      this.assertEqual(pres.length, 1);
      this.assertTrue(pres[0].parentElement === container);
      this.assertFalse(pres[0].hidden);
      this.assertEqual(pres[0].textContent, "");
      this.assertFalse(pres[0].hasAttribute("contenteditable"));
    }

    // A text shown replaces the last, as one text and no element.
    test_text_shown(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, "a\nb");
      const pre = pre_list(container)[0];
      this.assertEqual(pre.textContent, "a\nb");
      instance.text_show(1, "c");
      this.assertEqual(pre.textContent, "c");
      this.assertEqual(pre.childElementCount, 0);
    }

    // Later texts and toggles of the same tty reuse its `pre`.
    test_pre_reused(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      const first = pre_list(container)[0];
      instance.text_show(1, "a");
      instance.overlay_toggle(1);
      instance.overlay_toggle(1);
      instance.text_show(1, "b");
      this.assertEqual(container.childNodes.length, 1);
      this.assertTrue(pre_list(container)[0] === first);
    }

    // The text is shown as text, so markup in it makes no element.
    test_text_escaped(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      const text = '<b id="x">bold</b> &amp; <i>';
      instance.overlay_toggle(1);
      instance.text_show(1, text);
      const pre = pre_list(container)[0];
      this.assertEqual(pre.textContent, text);
      this.assertEqual(pre.childElementCount, 0);
      this.assertEqual(container.querySelectorAll("b, i").length, 0);
      this.assertTrue(pre.innerHTML.includes("&lt;b"));
      this.assertTrue(pre.innerHTML.includes("&amp;amp;"));
    }

    // Nothing is put in the page: the container and its `pre` stay detached.
    test_stays_detached(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, "a");
      this.assertFalse(container.isConnected);
      this.assertFalse(pre_list(container)[0].isConnected);
    }
  }

  // Showing and hiding the overlay of a tty, which holds text only shown.
  export class TestToggle extends unittest.TestCase {
    // A toggle shows a hidden `pre`, a second hides it, each saying which.
    test_toggle_twice(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      this.assertTrue(instance.overlay_toggle(1));
      const pre = pre_list(container)[0];
      this.assertFalse(pre.hidden);
      this.assertFalse(instance.overlay_toggle(1));
      this.assertTrue(pre.hidden);
    }

    // A hide empties the `pre`, so the next show starts empty.
    test_hide_empties(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, "a");
      instance.overlay_toggle(1);
      const pre = pre_list(container)[0];
      this.assertEqual(pre.textContent, "");
      instance.overlay_toggle(1);
      this.assertFalse(pre.hidden);
      this.assertEqual(pre.textContent, "");
    }

    // A text that comes after the hide is dropped.
    test_hidden_dropped(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.overlay_toggle(1);
      instance.text_show(1, "late");
      const pre = pre_list(container)[0];
      this.assertTrue(pre.hidden);
      this.assertEqual(pre.textContent, "");
      instance.overlay_toggle(1);
      this.assertEqual(pre.textContent, "");
    }

    // A text before any toggle makes the `pre` hidden and keeps nothing.
    test_text_first(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.text_show(2, "early");
      const pres = pre_list(container);
      this.assertEqual(pres.length, 1);
      this.assertTrue(pres[0].hidden);
      this.assertEqual(pres[0].textContent, "");
    }
  }

  // Two ttys of one overlay object share a container and nothing else.
  export class TestSeparation extends unittest.TestCase {
    // Each tty has its own `pre`, made in the order of first use.
    test_separate_pres(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(2);
      instance.overlay_toggle(1);
      instance.text_show(2, "two");
      instance.text_show(1, "one");
      const pres = pre_list(container);
      this.assertEqual(pres.length, 2);
      this.assertEqual(pres[0].textContent, "two");
      this.assertEqual(pres[1].textContent, "one");
    }

    // A toggle shows or hides and empties only the `pre` of its own tty.
    test_toggles_independent(): void {
      const container = container_make();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.overlay_toggle(2);
      instance.text_show(1, "a");
      instance.text_show(2, "x");
      const pres = pre_list(container);
      instance.overlay_toggle(2);
      this.assertFalse(pres[0].hidden);
      this.assertEqual(pres[0].textContent, "a");
      this.assertTrue(pres[1].hidden);
      this.assertEqual(pres[1].textContent, "");
    }

    // Two overlay objects on two containers share nothing.
    test_objects_independent(): void {
      const first = container_make();
      const second = container_make();
      const first_overlay = new overlay.Overlay(first);
      const second_overlay = new overlay.Overlay(second);
      first_overlay.overlay_toggle(1);
      first_overlay.text_show(1, "a");
      second_overlay.text_show(1, "b");
      this.assertEqual(pre_list(first)[0].textContent, "a");
      this.assertFalse(pre_list(first)[0].hidden);
      this.assertEqual(pre_list(second)[0].textContent, "");
      this.assertTrue(pre_list(second)[0].hidden);
    }
  }

  // The end of a shown overlay, kept at the bottom of the view.
  export class TestScroll extends unittest.TestCase {
    // The container of a fixed size, made in `setUp`.
    #container: HTMLElement | undefined = undefined;

    // Puts in the page a container of a fixed size that scrolls.
    setUp(): void {
      const container = document.createElement("div");
      Object.assign(container.style, {
        position: "fixed",
        top: "0px",
        left: "0px",
        width: `${gold_value("container_width") as number}px`,
        height: `${gold_value("container_height") as number}px`,
        overflow: "auto",
      });
      document.body.append(container);
      this.#container = container;
    }

    // Takes the container out of the page.
    tearDown(): void {
      this.container_get().remove();
    }

    // The container of this test.
    container_get(): HTMLElement {
      return this.#container as HTMLElement;
    }

    // Asserts that the end of the `pre` is at the container's visible bottom.
    end_assert(pre: HTMLPreElement): void {
      const below = end_below(this.container_get(), pre);
      this.assertTrue(Math.abs(below) < 1, `the pre ends ${below} px below`);
    }

    // Each text shown brings the overlay's end into view.
    test_text_scrolls(): void {
      const container = this.container_get();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, tall_text(1));
      const pre = pre_list(container)[0];
      this.assertTrue(container.scrollTop > 0);
      this.end_assert(pre);
      container.scrollTop = 0;
      instance.text_show(1, tall_text(1));
      this.end_assert(pre);
    }

    // A show brings its `pre` into view below a tall one.
    test_toggle_scrolls(): void {
      const container = this.container_get();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, tall_text(1));
      container.scrollTop = 0;
      instance.overlay_toggle(2);
      this.end_assert(pre_list(container)[1]);
    }

    // A text dropped by a hidden overlay leaves the view where it is.
    test_hidden_still(): void {
      const container = this.container_get();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.text_show(1, tall_text(1));
      container.scrollTop = 0;
      instance.text_show(2, tall_text(2));
      this.assertEqual(container.scrollTop, 0);
    }

    // A text shown in the upper of two shown overlays brings it into view.
    test_upper_overlay(): void {
      const container = this.container_get();
      const instance = new overlay.Overlay(container);
      instance.overlay_toggle(1);
      instance.overlay_toggle(2);
      instance.text_show(1, tall_text(1));
      instance.text_show(2, tall_text(2));
      const [upper, lower] = pre_list(container);
      this.end_assert(lower);
      instance.text_show(1, tall_text(1));
      this.end_assert(upper);
    }

    // In a container that does not scroll, the element above it is scrolled.
    test_inner_container(): void {
      const scroller = this.container_get();
      const inner = document.createElement("div");
      scroller.append(inner);
      const instance = new overlay.Overlay(inner);
      instance.overlay_toggle(1);
      instance.text_show(1, tall_text(1));
      const pre = pre_list(inner)[0];
      this.assertTrue(scroller.scrollTop > 0);
      this.end_assert(pre);
      scroller.scrollTop = 0;
      instance.text_show(1, tall_text(1));
      this.end_assert(pre);
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
