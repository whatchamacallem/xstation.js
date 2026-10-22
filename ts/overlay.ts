// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The read only debug overlays of ttys 1 and up: one `pre` for each tty
// holding its last rendered lines, newest last, hidden until toggled. A shown
// overlay's newest line is kept at the bottom of the container's view.
namespace overlay {
  // The constants of this module.
  const constants = Object.freeze({
    ring_minimum: 1,
    line_separator: "\n",
  });

  // The `pre` of one tty and the lines it shows, oldest first.
  interface OverlayEntry {
    pre: HTMLPreElement;
    lines: string[];
  }

  // The overlays inside a container, each keeping the last lines of a tty.
  export class Overlay {
    private container: HTMLElement;
    private ring: number;
    private entries = new Map<number, OverlayEntry>();

    // Takes the container the overlays go in and the lines kept for each tty.
    constructor(container: HTMLElement, ring: number) {
      if (!Number.isInteger(ring) || ring < constants.ring_minimum) {
        throw new Error(i18n("overlay.ring_invalid", ring));
      }
      this.container = container;
      this.ring = ring;
    }

    // Appends a rendered line to the ring of a tty and rewrites its `pre`.
    line_add(tty: number, text: string): void {
      const entry = this.entry_get(tty);
      entry.lines.push(text);
      if (entry.lines.length > this.ring) {
        entry.lines.shift();
      }
      entry.pre.textContent = entry.lines.join(constants.line_separator);
      this.end_show(entry.pre);
    }

    // Shows the `pre` of a tty when it is hidden and hides it when shown.
    overlay_toggle(tty: number): void {
      const entry = this.entry_get(tty);
      entry.pre.hidden = !entry.pre.hidden;
      this.end_show(entry.pre);
    }

    // Scrolls the container so that a shown `pre` ends at its visible bottom.
    private end_show(pre: HTMLPreElement): void {
      // A hidden `pre` shows no line, and the toggle that shows it scrolls.
      if (pre.hidden) {
        return;
      }
      const container = this.container;
      const box = container.getBoundingClientRect();
      const bottom = box.top + container.clientTop + container.clientHeight;
      container.scrollTop += pre.getBoundingClientRect().bottom - bottom;
    }

    // The entry of a tty, made hidden in the container on first use.
    private entry_get(tty: number): OverlayEntry {
      let entry = this.entries.get(tty);
      if (entry === undefined) {
        const pre = this.container.ownerDocument.createElement("pre");
        pre.hidden = true;
        this.container.append(pre);
        entry = { pre, lines: [] };
        this.entries.set(tty, entry);
      }
      return entry;
    }
  }
}
Object.freeze(overlay);
