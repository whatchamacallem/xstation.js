// The read only debug overlays of ttys 1 and up on the UI thread: a `pre` per
// tty, ctrl n toggling tty n. ctrl 1 shows the end of the audit, which the
// page asks of the server at each show by `audit.tail`, its count the setting
// `audit_entries`; each hide empties the `pre`, so the page holds the text
// only while it is shown, and a text that comes after the hide is dropped. A
// shown overlay's end is kept at the bottom of the view of the element that
// scrolls it, the container or one above it, as `debug` on the engine page.

declare namespace overlay {
  class Overlay {
    constructor(container: HTMLElement);
    // Shows the `pre` of a tty when hidden, hides and empties it when shown.
    overlay_toggle(tty: number): boolean;
    // Shows a text in the shown `pre` of a tty, its end in view.
    text_show(tty: number, text: string): void;
  }
}
