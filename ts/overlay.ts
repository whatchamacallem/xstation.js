// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The read only debug overlays of ttys 1 and up: one `pre` for each tty,
// hidden until toggled, holding a text only while it is shown and emptied at
// each hide. A shown overlay's end is kept at the bottom of the view of the
// element that scrolls it, the container or one above it.
namespace overlay {
  // The overlays inside a container, each the `pre` of a tty.
  export class Overlay {
    private container: HTMLElement;
    private entries = new Map<number, HTMLPreElement>();

    // Takes the container the overlays go in.
    constructor(container: HTMLElement) {
      this.container = container;
    }

    // Shows the `pre` of a tty when hidden, hides and empties it when shown.
    overlay_toggle(tty: number): boolean {
      const pre = this.entry_get(tty);
      pre.hidden = !pre.hidden;
      if (pre.hidden) {
        pre.textContent = "";
      } else {
        this.end_show(pre);
      }
      return !pre.hidden;
    }

    // Shows a text in the shown `pre` of a tty, its end in view.
    text_show(tty: number, text: string): void {
      const pre = this.entry_get(tty);
      // Hidden before the text came, the overlay keeps nothing.
      if (pre.hidden) {
        return;
      }
      pre.textContent = text;
      this.end_show(pre);
    }

    // Scrolls whatever scrolls a shown `pre` so that it ends at the bottom.
    private end_show(pre: HTMLPreElement): void {
      pre.scrollIntoView({ block: "end" });
    }

    // The `pre` of a tty, made hidden in the container on first use.
    private entry_get(tty: number): HTMLPreElement {
      let pre = this.entries.get(tty);
      if (pre === undefined) {
        pre = this.container.ownerDocument.createElement("pre");
        pre.hidden = true;
        this.container.append(pre);
        this.entries.set(tty, pre);
      }
      return pre;
    }
  }
}
Object.freeze(overlay);
