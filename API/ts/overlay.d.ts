declare namespace overlay {
  // The read only debug overlays of ttys 1 and up on the UI thread: a
  // <pre> per tty holding the last `verbose_ring` rendered lines in both
  // directions, newest last, fed by `overlay.line`. ctrl-n toggles tty n.
  class Overlay {
    constructor(container: HTMLElement, ring: number);
    line_add(tty: number, text: string): void;
    overlay_toggle(tty: number): void;
  }
}
